#!/usr/bin/env python3
"""Execute the auditable randomized-coordinator Cassandra experiment suite."""
import argparse
from collections import Counter
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import secrets
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from checks import evaluate
from experiments import node_failure, network_partition, read_repair, session_guarantees, timestamp_control
from experiments.configuration import expected_main_trials, normalize
from experiments.faults import (NODES, clear_partition, compose, kill_node, membership,
                                partition_snapshot, recover_all, restart_node, set_graph,
                                set_partition, wait_failure, wait_healthy)

EVIDENCE_SCHEMA = "randomized-cassandra-evidence-v3"


class Progress:
    """Print durable, line-oriented progress for long experiment runs."""

    def __init__(self, total, stream=None):
        self.total = total
        self.completed = 0
        self.stream = stream or sys.stdout

    def show(self, experiment, detail, advance=0):
        self.completed += advance
        if self.completed > self.total:
            raise RuntimeError("progress count exceeds planned experiment count")
        percent = 100.0 if self.total == 0 else (100.0 * self.completed / self.total)
        width = 30
        filled = width if self.total == 0 else int(width * self.completed / self.total)
        bar = "#" * filled + "-" * (width - filled)
        print(f"[progress] [{bar}] {percent:6.2f}% "
              f"({self.completed}/{self.total}) | {experiment} | {detail}",
              file=self.stream, flush=True)


def load_config(path, full=True, repetitions=None):
    raw = json.loads(path.read_text())
    if repetitions is not None:
        raw["repetitions"] = repetitions
        raw["rounds"] = repetitions
    return normalize(raw, full=full)


def atomic_save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")
    os.replace(temporary, path)


class Evidence:
    def __init__(self, directory):
        self.directory = directory
        self.journal = directory / "events.jsonl"

    def event(self, kind, **fields):
        record = {"event": kind, "time_ns": time.time_ns(), **fields}
        with self.journal.open("a") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return record

    def save(self, name, value):
        atomic_save(self.directory / name, value)


def derived_seed(root, label):
    digest = hashlib.sha256(f"{root}:{label}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def worker(request, config):
    payload = dict(request)
    payload.update(nodes=list(NODES), cql_port=config["faults"]["cql_port"])
    if payload.get("action") == "schema":
        payload["database"] = config["database"]
    result = compose("exec", "-T", "client", "python", "src/worker.py",
                     data=json.dumps(payload), timeout=180)
    return json.loads(result)


def require_records(response, expected, label):
    if not isinstance(response, dict):
        raise RuntimeError(f"{label}: response is not an object")
    records = response.get("records")
    if not isinstance(records, list) or len(records) != expected:
        raise RuntimeError(f"{label}: expected {expected} records, got {len(records or [])}")
    errors = [record for record in records if record.get("status") != "ok"]
    if errors:
        raise RuntimeError(f"{label}: {len(errors)} operations failed: {json.dumps(errors)}")
    return response


def initialize(schedule, seed, timestamp, config, table="blocking"):
    items = [{"key": case["key"], "table": case.get("table", table)} for case in schedule]
    response = worker({"action": "init", "items": items, "ts": timestamp, "seed": seed}, config)
    return require_records(response, len(items), "initialization")


def environment(config, seed, run_id):
    def output(args):
        result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=30)
        return {"command": args, "returncode": result.returncode,
                "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    source_files = [ROOT / name for name in ("README.md", "WORK_IN_PROGRESS.md",
                    "Project_Assignment.md", "AGENT_ACTION_PLAN.md", "compose.yaml",
                    "Dockerfile.cassandra", "Dockerfile.client", "requirements-report.txt",
                    "report/predictions.md", "report/authors.json")]
    for directory in ("config", "docs", "experiments", "src", "scripts", "tests"):
        source_files.extend(path for path in (ROOT / directory).rglob("*")
                            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc")
    manifest = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(set(source_files))}
    return {
        "evidence_schema": EVIDENCE_SCHEMA, "design": config["design"], "run_id": run_id,
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "root_seed": seed,
        "python": sys.version, "platform": sys.platform,
        "git_revision": output(["git", "rev-parse", "HEAD"]),
        "git_status": output(["git", "status", "--short"]),
        "docker_compose": output(([os.environ.get("COMPOSE_BIN")] if os.environ.get("COMPOSE_BIN")
                                  else [os.environ.get("DOCKER_BIN", "docker"), "compose"]) + ["version"]),
        "source_manifest_sha256": manifest,
        "effective_config": config,
    }


def main_episode(config, evidence, run_id, scenario, round_no, rngs, all_trials,
                 fault_records, progress):
    schedule = session_guarantees.build_round(config, run_id, round_no, scenario, rngs["order"])
    progress.show("session_guarantees",
                  f"starting scenario={scenario}, round={round_no + 1}/{config['rounds']}, "
                  f"trials={len(schedule)}; initializing keys")
    timestamp = time.time_ns() // 1000
    init_seed = rngs["routing"].getrandbits(64)
    initialization = initialize(schedule, init_seed, timestamp, config)
    episode_id = f"main:{scenario}:{round_no}"
    record = {"episode_id": episode_id, "scenario": scenario, "round": round_no,
              "schedule": schedule, "initialization": initialization,
              "started_ns": time.time_ns(), "fault": None, "recovery": None}
    evidence.event("episode_initialized", episode_id=episode_id, scenario=scenario,
                   round=round_no, keys=[case["key"] for case in schedule])
    progress.show("session_guarantees",
                  f"scenario={scenario}, round={round_no + 1}/{config['rounds']}; "
                  "initialization complete")
    cleanup = None
    try:
        if scenario == "node_failure":
            victim = node_failure.choose_victim(NODES, rngs["faults"])
            progress.show("session_guarantees",
                          f"scenario={scenario}, round={round_no + 1}/{config['rounds']}; "
                          f"stopping {victim} and waiting for failure detection")
            fault = kill_node(victim)
            cleanup = ("node", victim)
            record["fault"] = fault
            fault["detection"] = wait_failure(victim, fault["identity"]["ip"],
                config["faults"]["failure_detection_timeout_seconds"])
        elif scenario == "network_partition":
            isolated = network_partition.choose_isolated(NODES, rngs["faults"])
            progress.show("session_guarantees",
                          f"scenario={scenario}, round={round_no + 1}/{config['rounds']}; "
                          f"installing partition with isolated_node={isolated}")
            fault = set_partition(isolated, config["faults"]["internode_ports"])
            cleanup = ("partition", isolated)
            expected_peers = {node: (2 if node == isolated else 1) for node in NODES}
            for node, peer_count in expected_peers.items():
                if len(fault["blocked"].get(node, [])) != peer_count:
                    raise RuntimeError("installed partition graph differs from intended 2|1 cut")
                if fault["rules"].get(node, "").count("-j DROP") < peer_count * 2:
                    raise RuntimeError("partition DROP rules are incomplete")
            if config["faults"]["partition_stabilization_seconds"]:
                time.sleep(config["faults"]["partition_stabilization_seconds"])
            probe = worker({"action": "probe"}, config)
            if len(probe) != len(NODES) or not all(item.get("reachable") for item in probe):
                raise RuntimeError("partition must retain CQL reachability to every node")
            fault.update(isolated=isolated, client_probe=probe,
                         established_ns=time.time_ns(), established_membership={n: membership(n) for n in NODES})
            record["fault"] = fault
        progress.show("session_guarantees",
                      f"scenario={scenario}, round={round_no + 1}/{config['rounds']}; "
                      f"running {len(schedule)} randomized trials")
        batch_seed = rngs["routing"].getrandbits(64)
        batch = worker({"action": "batch", "schedule": schedule,
                        "ts": timestamp + 1_000_000, "seed": batch_seed}, config)
        trials = batch.get("records") if isinstance(batch, dict) else None
        if not isinstance(trials, list) or len(trials) != len(schedule):
            raise RuntimeError(f"application batch returned {len(trials or [])}/{len(schedule)} histories")
        for trial in trials:
            trial.update(episode_id=episode_id, routing_seed=batch_seed,
                         worker_health=batch.get("health", []))
        record["trials"] = trials
        record["post_workload_partition"] = partition_snapshot() if scenario == "network_partition" else None
        all_trials.extend(trials)
        progress.show("session_guarantees",
                      f"finished scenario={scenario}, round={round_no + 1}/{config['rounds']}, "
                      f"saved_trials={len(trials)}",
                      advance=len(trials))
    except BaseException as exc:
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        evidence.event("episode_error", episode_id=episode_id, error=record["error"])
        raise
    finally:
        try:
            if cleanup and cleanup[0] == "node":
                progress.show("session_guarantees",
                              f"scenario={scenario}, round={round_no + 1}/{config['rounds']}; "
                              f"restarting {cleanup[1]} and verifying recovery")
                restart_node(cleanup[1])
                record["recovery"] = wait_healthy(config["faults"]["recovery_timeout_seconds"])
            elif cleanup and cleanup[0] == "partition":
                progress.show("session_guarantees",
                              f"scenario={scenario}, round={round_no + 1}/{config['rounds']}; "
                              "removing partition and verifying recovery")
                clear_partition()
                record["recovery"] = wait_healthy(config["faults"]["recovery_timeout_seconds"])
        except BaseException as recovery_error:
            record["recovery_error"] = {"type": type(recovery_error).__name__,
                                        "message": str(recovery_error)}
        record["ended_ns"] = time.time_ns()
        fault_records.append(record)
        evidence.save("trials.json", all_trials)
        evidence.save("faults.json", fault_records)
        evidence.save(f"episode_{scenario}_{round_no:02}.json", record)
        evidence.event("episode_saved", episode_id=episode_id,
                       trials=len(record.get("trials", [])),
                       recovered=(scenario == "normal" or bool(record.get("recovery"))))


def read_value(response, index, column):
    try:
        record = response["records"][index]
        value = record.get("value")
        return value.get(column) if record.get("status") == "ok" and isinstance(value, dict) else None
    except (KeyError, IndexError, TypeError):
        return None


def run_read_repair(config, evidence, run_id, rngs, progress):
    results = []
    if "read_repair" not in config["enabled_experiments"]:
        evidence.save("read_repair.json", results)
        return results
    full_cut = [("n1", "n2"), ("n1", "n3"), ("n2", "n3")]
    for round_no in range(config["rounds"]):
        for table, setting in read_repair.settings(config):
            attempt_id = f"repair:{round_no}:{table}"
            key = f"{config['design']}:{run_id}:{attempt_id}"
            case = {"attempt_id": attempt_id, "round": round_no, "table": table,
                    "setting": setting, "key": key}
            record = {"case": case, "started_ns": time.time_ns()}
            progress.show("read_repair",
                          f"starting setting={setting}, round={round_no + 1}/{config['rounds']}")
            try:
                record["initialization"] = initialize([case], rngs["routing"].getrandbits(64),
                                                       time.time_ns() // 1000, config, table)
                record["full_cut"] = set_graph(full_cut, config["faults"]["internode_ports"])
                if config["faults"]["partition_hold_seconds"]:
                    time.sleep(config["faults"]["partition_hold_seconds"])
                write = worker({"action": "ops", "seed": rngs["routing"].getrandbits(64),
                    "operations": [read_repair.minority_write(
                        key, time.time_ns() // 1000, table)]}, config)
                record["write"] = write
                selected = write.get("records", [{}])[0].get("routing", {}).get("selected_node")
                if selected not in NODES:
                    raise RuntimeError("minority write did not identify its random coordinator")
                pair1, pair2 = read_repair.topology_pairs(selected, NODES, rngs["topology"])
                record["pair_sequence"] = [pair1, pair2]
                record["pair1_graph"] = set_graph([edge for edge in full_cut if set(edge) != set(pair1)],
                                                   config["faults"]["internode_ports"])
                time.sleep(config["faults"]["partition_stabilization_seconds"])
                first = worker({"action": "ops", "seed": rngs["routing"].getrandbits(64),
                    "operations": [read_repair.quorum_read(key, table)]}, config)
                record["first"] = first
                record["pair2_graph"] = set_graph([edge for edge in full_cut if set(edge) != set(pair2)],
                                                   config["faults"]["internode_ports"])
                time.sleep(config["faults"]["partition_stabilization_seconds"])
                second = worker({"action": "ops", "seed": rngs["routing"].getrandbits(64),
                    "operations": [read_repair.quorum_read(key, table)]}, config)
                record["second"] = second
                first_record = first.get("records", [{}])[0]
                second_record = second.get("records", [{}])[0]
                if first_record.get("status") != "ok" or second_record.get("status") != "ok":
                    record.update(verdict="inconclusive", reason="operation_error")
                elif read_value(first, 0, "a") != 1:
                    record.update(verdict="inconclusive", reason="first_read_not_exposed")
                else:
                    record.update(verdict=("regression" if read_value(second, 0, "a") != 1 else "no_regression_observed"),
                                  reason=None)
                record["post_workload_partition"] = partition_snapshot()
            except BaseException as exc:
                record.update(verdict="setup_failure", reason=type(exc).__name__, error=str(exc))
                raise
            finally:
                try:
                    clear_partition()
                    record["recovery"] = wait_healthy(config["faults"]["recovery_timeout_seconds"])
                except BaseException as exc:
                    record["recovery_error"] = {"type": type(exc).__name__, "message": str(exc)}
                record["ended_ns"] = time.time_ns()
                results.append(record)
                evidence.save("read_repair.json", results)
                evidence.event("read_repair_saved", attempt_id=attempt_id,
                               verdict=record.get("verdict"))
                progress.show("read_repair",
                              f"finished setting={setting}, round={round_no + 1}/{config['rounds']}, "
                              f"verdict={record.get('verdict', 'error')}", advance=1)
    return results


def run_timestamp_controls(config, evidence, run_id, rngs, progress):
    results = []
    if "timestamp_control" not in config["enabled_experiments"]:
        evidence.save("timestamp_control.json", results)
        return results
    for round_no in range(config["rounds"]):
        progress.show("timestamp_control",
                      f"starting round={round_no + 1}/{config['rounds']}")
        key = f"{config['design']}:{run_id}:timestamp:{round_no}"
        ts = time.time_ns() // 1000
        case = {"attempt_id": f"timestamp:{round_no}", "round": round_no,
                "key": key, "table": "blocking"}
        initialization = initialize([case], rngs["routing"].getrandbits(64), ts, config)
        operations = timestamp_control.operations(key, ts, "blocking")
        result = worker({"action": "ops", "seed": rngs["routing"].getrandbits(64),
                         "operations": operations}, config)
        records = result.get("records", [])
        if len(records) != 3 or any(record.get("status") != "ok" for record in records):
            verdict, reason = "inconclusive", "operation_error"
        else:
            verdict = "expected" if read_value(result, 2, "a") == 1 else "unexpected"
            reason = None
        record = {"case": case, "initialization": initialization, "result": result,
                  "verdict": verdict, "reason": reason, "timestamps": [ts + 100, ts + 50]}
        results.append(record)
        evidence.save("timestamp_control.json", results)
        evidence.event("timestamp_saved", attempt_id=case["attempt_id"], verdict=verdict)
        progress.show("timestamp_control",
                      f"finished round={round_no + 1}/{config['rounds']}, verdict={verdict}",
                      advance=1)
    return results


def run_plan(config, output, seed):
    output.mkdir(parents=True, exist_ok=False)
    evidence = Evidence(output)
    run_id = output.name.replace("randomized_", "")
    seeds = {name: derived_seed(seed, name) for name in ("routing", "order", "faults", "topology")}
    rngs = {name: random.Random(value) for name, value in seeds.items()}
    evidence.save("plan.json", config)
    evidence.save("seeds.json", {"root": seed, **seeds})
    evidence.save("environment.json", environment(config, seed, run_id))
    evidence.save("completion.json", {"completed": False, "evidence_schema": EVIDENCE_SCHEMA,
                                       "run_id": run_id, "started_utc": dt.datetime.now(dt.timezone.utc).isoformat()})
    evidence.event("run_started", run_id=run_id, profile=config["profile"])
    total = (expected_main_trials(config) + read_repair.expected_trials(config)
             + timestamp_control.expected_trials(config))
    progress = Progress(total)
    progress.show("setup", f"run={run_id}, profile={config['profile']}, seed={seed}")
    progress.show("setup", "waiting for three-node Cassandra membership")
    ready_membership = wait_healthy(config["faults"]["recovery_timeout_seconds"])
    progress.show("setup", "cluster healthy; creating and checking schema")
    schema_attempts = []
    for attempt in range(1, 11):
        schema = worker({"action": "schema"}, config)
        schema_attempts.append(schema)
        if schema.get("status") == "ok" and schema.get("records"):
            break
        progress.show("setup", f"schema check attempt {attempt}/10 failed; retrying in 3 seconds")
        if attempt < 10:
            time.sleep(3)
    else:
        evidence.save("schema_failure.json", {"attempts": schema_attempts})
        failures = []
        for index, response in enumerate(schema_attempts, start=1):
            for record in response.get("records", []):
                if record.get("status") != "ok" or record.get("matches_expected") is False:
                    failures.append({"attempt": index, "node": record.get("node"),
                                     "query": record.get("query"), "status": record.get("status"),
                                     "error": record.get("error"), "message": record.get("message"),
                                     "value": record.get("value"),
                                     "expected": record.get("expected")})
        raise RuntimeError("schema creation/inspection failed after 10 attempts: "
                           + json.dumps(failures[-12:], default=str))
    initial = {"membership": ready_membership,
               "schema": schema, "schema_attempts": schema_attempts,
               "client_probe": worker({"action": "probe"}, config)}
    if not all(item.get("reachable") for item in initial["client_probe"]):
        raise RuntimeError("not every CQL endpoint is ready")
    evidence.save("initial_cluster.json", initial)
    progress.show("setup", "schema and client endpoint probes passed")
    all_trials, fault_records = [], []
    try:
        if "session_guarantees" in config["enabled_experiments"]:
            for round_no in range(config["rounds"]):
                scenarios = list(config["scenarios"])
                rngs["order"].shuffle(scenarios)
                for scenario in scenarios:
                    main_episode(config, evidence, run_id, scenario, round_no, rngs,
                                 all_trials, fault_records, progress)
        repairs = run_read_repair(config, evidence, run_id, rngs, progress)
        timestamps = run_timestamp_controls(config, evidence, run_id, rngs, progress)
        expected = expected_main_trials(config)
        if len(all_trials) != expected:
            raise RuntimeError(f"main trial count {len(all_trials)} != {expected}")
        if len(repairs) != read_repair.expected_trials(config):
            raise RuntimeError("read-repair attempt count mismatch")
        if len(timestamps) != timestamp_control.expected_trials(config):
            raise RuntimeError("timestamp-control attempt count mismatch")
        completion = {"completed": True, "evidence_schema": EVIDENCE_SCHEMA, "run_id": run_id,
                      "profile": config["profile"], "main_trials": len(all_trials),
                      "expected_main_trials": expected, "read_repair_trials": len(repairs),
                      "timestamp_trials": len(timestamps),
                      "verdicts": dict(Counter(t["verdict"] for t in all_trials)),
                      "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
        evidence.save("completion.json", completion)
        evidence.event("run_completed", **completion)
        progress.show("complete", f"evidence saved in {output}")
        return output
    except BaseException as exc:
        evidence.event("run_failed", error={"type": type(exc).__name__, "message": str(exc)})
        raise


def plan_summary(config, seed):
    main = expected_main_trials(config)
    repairs = read_repair.expected_trials(config)
    timestamps = timestamp_control.expected_trials(config)
    return {"seed": seed, "profile": config["profile"], "main_trials": main,
            "read_repair_trials": repairs, "timestamp_trials": timestamps,
            "total_trials": main + repairs + timestamps,
            "per_case_repetitions": config["rounds"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/randomized_experiments.json")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="allow fewer than ten attempts; never a submission run")
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--recover", action="store_true", help="restart all nodes and clear project firewall rules")
    args = parser.parse_args()
    config = load_config(args.config, full=not args.smoke, repetitions=args.repetitions)
    seed = args.seed if args.seed is not None else config.get("seed")
    seed = seed if seed is not None else secrets.randbits(64)
    if args.plan_only:
        print(json.dumps(plan_summary(config, seed), indent=2))
        return
    if args.recover:
        print(json.dumps(recover_all(config["faults"]["recovery_timeout_seconds"]), indent=2))
        return
    lock_path = ROOT / ".randomized-run.lock"
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error("another randomized run holds the project lock")
        print("[runner] Building and starting the Docker Compose environment...", flush=True)
        compose("up", "-d", "--build", timeout=1800)
        print("[runner] Docker Compose environment started; beginning experiment setup.", flush=True)
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = ROOT / "results" / f"randomized_{stamp}_{seed:016x}"
        try:
            print(run_plan(config, output, seed))
        except BaseException:
            try:
                recover_all(config["faults"]["recovery_timeout_seconds"])
            except BaseException as cleanup_error:
                print(f"automatic recovery failed: {cleanup_error}", file=sys.stderr)
            raise


if __name__ == "__main__":
    main()
