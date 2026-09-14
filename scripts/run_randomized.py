#!/usr/bin/env python3
"""Run the randomized-coordinator Cassandra experiment plan."""
import argparse
import datetime as dt
import json
import os
import random
import secrets
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))

from experiments.common import expected_main_trials
from experiments import session_guarantees, node_failure, network_partition, read_repair, timestamp_control
from experiments.faults import NODES, clear_partition, compose, kill_node, membership, restart_node, set_graph, set_partition, wait_failure, wait_healthy

def load_config(path):
    with open(path) as handle:
        config = json.load(handle)
    if config["repetitions"] < 10:
        raise ValueError("repetitions must be at least 10")
    if config["rounds"] < 10:
        raise ValueError("rounds must be at least 10")
    if config["repetitions"] != config["rounds"]:
        raise ValueError("repetitions and rounds must match: one randomized case per round")
    required = {"RYW", "MR", "MW", "WFR"}
    if set(config["models"]) != required:
        raise ValueError("models must contain exactly RYW, MR, MW, WFR")
    allowed = {"session_guarantees", "node_failure", "network_partition", "read_repair", "timestamp_control"}
    unknown = set(config.get("enabled_experiments", ())) - allowed
    if unknown:
        raise ValueError(f"unknown enabled experiment types: {sorted(unknown)}")
    if any(s not in {"normal", "node_failure", "network_partition"} for s in config["scenarios"]):
        raise ValueError("scenarios must be normal, node_failure, or network_partition")
    if "node_failure" in config["scenarios"] and "node_failure" not in config["enabled_experiments"]:
        raise ValueError("node_failure scenario is listed but node_failure experiment is disabled")
    if "network_partition" in config["scenarios"] and "network_partition" not in config["enabled_experiments"]:
        raise ValueError("network_partition scenario is listed but network_partition experiment is disabled")
    return config


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def worker(request):
    # The client container reads one JSON request and writes one JSON response.
    result = compose("exec", "-T", "client", "python", "src/worker.py", data=json.dumps(request))
    return json.loads(result)


def initialize(schedule, seed, timestamp, table="blocking"):
    items = [{"key": case["key"], "table": table} for case in schedule]
    return worker({"action": "init", "items": items, "ts": timestamp, "seed": seed})


def application_batch(schedule, seed, timestamp):
    return worker({"action": "batch", "schedule": schedule, "ts": timestamp, "seed": seed})


def assert_initialization(response):
    if not isinstance(response, dict) or any(r["status"] != "ok" for r in response.get("records", [])):
        raise RuntimeError("initialization failed: " + json.dumps(response))


def run_plan(config, output, seed):
    rng = random.Random(seed)
    output.mkdir(parents=True, exist_ok=False)
    save(output / "plan.json", config)
    save(output / "seeds.json", {"root": seed, "routing": seed ^ 0x13579BDF,
                                 "case_order": seed ^ 0x2468ACE0, "faults": seed ^ 0x55AA55AA})
    save(output / "experiment_catalog.json", {
        "session_guarantees": session_guarantees.description(),
        "node_failure": node_failure.description(),
        "network_partition": network_partition.description(),
        "read_repair": read_repair.description(),
        "timestamp_control": timestamp_control.description(),
        "expected_main_trials": expected_main_trials(config),
        "expected_read_repair_trials": read_repair.expected_trials(config),
        "expected_timestamp_trials": timestamp_control.expected_trials(config),
    })
    schema = worker({"action": "schema"})
    save(output / "initial_cluster.json", {"membership": membership("n1"), "healthy": wait_healthy(600), "schema": schema})
    all_trials = []
    fault_records = []
    scenarios = config["scenarios"] if "session_guarantees" in config["enabled_experiments"] else []
    for scenario in scenarios:
        for round_no in range(config["rounds"]):
            schedule = session_guarantees.build_round(config, round_no, scenario, rng)
            round_seed = rng.getrandbits(64)
            timestamp = time.time_ns() // 1000
            initialization = initialize(schedule, round_seed, timestamp)
            assert_initialization(initialization)
            record = {"scenario": scenario, "round": round_no, "schedule": schedule,
                      "initialization": initialization, "seed": round_seed}
            if scenario == "node_failure" and "node_failure" in config["enabled_experiments"]:
                victim = node_failure.choose_victim(NODES, rng)
                record["fault"] = kill_node(victim)
                record["fault"]["victim"] = victim
                record["fault"]["detection"] = wait_failure(victim, config["faults"]["failure_detection_timeout_seconds"])
            elif scenario == "network_partition" and "network_partition" in config["enabled_experiments"]:
                isolated = network_partition.choose_isolated(NODES, rng)
                record["fault"] = set_partition(isolated, config["faults"]["internode_ports"])
                time.sleep(config["faults"]["partition_stabilization_seconds"])
                record["fault"]["isolated"] = isolated
            batch = application_batch(schedule, round_seed ^ 0xA5A5A5A5, timestamp + 1000000)
            trials = batch.get("records", [])
            all_trials.extend(trials)
            record["trials"] = trials
            save(output / f"{scenario}_round_{round_no:02}.json", record)
            if scenario == "node_failure" and "node_failure" in config["enabled_experiments"]:
                restart_node(record["fault"]["victim"])
                record["recovery"] = wait_healthy(config["faults"]["recovery_timeout_seconds"])
            elif scenario == "network_partition" and "network_partition" in config["enabled_experiments"]:
                clear_partition()
                record["recovery"] = wait_healthy(config["faults"]["recovery_timeout_seconds"])
            fault_records.append(record)
            save(output / "trials.json", all_trials)
    save(output / "faults.json", fault_records)
    # Supplemental read-repair and timestamp controls are separate experiment types.
    repairs = []
    repair_rounds = range(config["rounds"]) if "read_repair" in config["enabled_experiments"] else []
    for round_no in repair_rounds:
        for table, setting in read_repair.settings(config):
            key = f"{config['design']}:read_repair:r{round_no}:{table}"
            case = {"key": key, "model": "MR", "config": "QUORUM/QUORUM", "scenario": "read_repair",
                    "round": round_no, "table": table, "setting": setting}
            init = initialize([case], rng.getrandbits(64), time.time_ns() // 1000, table)
            if not isinstance(init, dict) or any(r["status"] != "ok" for r in init.get("records", [])):
                raise RuntimeError("read-repair initialization failed")
            full_cut = list(__import__('itertools').combinations(NODES, 2))
            set_graph(full_cut, config["faults"]["internode_ports"])
            time.sleep(config["faults"]["partition_hold_seconds"])
            write = worker({"action": "ops", "seed": rng.getrandbits(64), "operations":
                            [{"kind":"write", "key":key, "column":"a", "value":1,
                              "ts":time.time_ns()//1000, "cl":"ONE", "table":table}]})
            pair1 = ("n1", "n2")
            set_graph([edge for edge in full_cut if set(edge) != set(pair1)], config["faults"]["internode_ports"])
            first = worker({"action":"ops", "seed":rng.getrandbits(64), "operations":
                            [{"kind":"read","key":key,"cl":"QUORUM","table":table}]})
            pair2 = ("n2", "n3")
            set_graph([edge for edge in full_cut if set(edge) != set(pair2)], config["faults"]["internode_ports"])
            second = worker({"action":"ops", "seed":rng.getrandbits(64), "operations":
                             [{"kind":"read","key":key,"cl":"QUORUM","table":table}]})
            repairs.append({"case": case, "initialization": init, "write": write,
                            "first": first, "second": second,
                            "pair_sequence": [pair1, pair2]})
            clear_partition()
            wait_healthy(config["faults"]["recovery_timeout_seconds"])
    save(output / "read_repair_plan.json", repairs)
    timestamps = []
    timestamp_rounds = range(config["rounds"]) if "timestamp_control" in config["enabled_experiments"] else []
    for round_no in timestamp_rounds:
        key = f"{config['design']}:timestamp:r{round_no}"
        ts = time.time_ns() // 1000
        case = {"key": key, "table": "blocking"}
        init = initialize([case], rng.getrandbits(64), ts)
        operations = [
            {"kind":"write","key":key,"column":"a","value":1,"ts":ts+100,"cl":"ALL"},
            {"kind":"write","key":key,"column":"a","value":2,"ts":ts+50,"cl":"ALL"},
            {"kind":"read","key":key,"cl":"ALL"},
        ]
        result = worker({"action":"ops","seed":rng.getrandbits(64),"operations":operations})
        timestamps.append({"round":round_no,"case":case,"initialization":init,"result":result})
    save(output / "timestamp_control_plan.json", timestamps)
    save(output / "completion.json", {"completed": True, "main_trials": len(all_trials),
                                       "expected_main_trials": expected_main_trials(config),
                                       "read_repair_trials": len(repairs), "timestamp_trials": len(timestamps),
                                       "utc": dt.datetime.now(dt.timezone.utc).isoformat()})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/randomized_experiments.json")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--plan-only", action="store_true", help="validate and print counts without Docker")
    parser.add_argument("--repetitions", type=int, default=None, help="override repetitions and rounds; minimum 10")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.repetitions is not None:
        config["repetitions"] = args.repetitions
        config["rounds"] = args.repetitions
        if args.repetitions < 10:
            parser.error("--repetitions must be at least 10")
    seed = args.seed if args.seed is not None else secrets.randbits(64)
    if args.plan_only:
        print(json.dumps({"seed": seed, "main_trials": expected_main_trials(config),
                          "read_repair_trials": read_repair.expected_trials(config),
                          "timestamp_trials": timestamp_control.expected_trials(config),
                          "total_trials": expected_main_trials(config) + read_repair.expected_trials(config) + timestamp_control.expected_trials(config),
                          "per_case_repetitions": config["rounds"]}, indent=2))
        return
    compose("up", "-d", "--build")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "results" / ("randomized_" + stamp)
    print(run_plan(config, output, seed))


if __name__ == "__main__":
    main()
