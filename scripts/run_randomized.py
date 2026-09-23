#!/usr/bin/env python3
"""Execute the auditable Cassandra-driver-policy experiment suite."""
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

EVIDENCE_SCHEMA = "cassandra-driver-policy-evidence-v4"


class Progress:
    """Print durable, line-oriented progress for long experiment runs."""

    def __init__(self, total, stream=None, completed=0):
        self.total = total
        self.completed = completed
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


def timing_fields(started_utc, started_monotonic, previous_minutes=0.0):
    """Return one consistent set of wall-clock and elapsed run timestamps."""
    ended_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    elapsed_minutes = previous_minutes + max(0.0, (time.monotonic() - started_monotonic) / 60.0)
    return {
        "started_utc": started_utc,
        "ended_utc": ended_utc,
        "completion_time_minutes": round(elapsed_minutes, 6),
    }


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


def load_json(path):
    return json.loads(path.read_text())


def valid_repair_checkpoint(record):
    return (record.get("verdict") in {"regression", "no_regression_observed", "inconclusive"}
            and "recovery_error" not in record
            and isinstance(record.get("initialization"), dict)
            and all(isinstance(record.get(field), dict)
                    for field in ("write", "first", "second")))


def valid_timestamp_checkpoint(record):
    return (record.get("verdict") in {"expected", "unexpected", "inconclusive"}
            and isinstance(record.get("initialization"), dict)
            and isinstance(record.get("result"), dict))


def checkpoint_prefix(records, expected_ids, validator, label):
    """Return the valid ordered prefix and the tail that must be retried."""
    if len(records) > len(expected_ids):
        raise RuntimeError(f"{label} has more records than the saved plan")
    for index, record in enumerate(records):
        attempt_id = record.get("case", {}).get("attempt_id")
        if attempt_id != expected_ids[index]:
            raise RuntimeError(
                f"{label} checkpoint order mismatch at {index}: "
                f"{attempt_id!r} != {expected_ids[index]!r}"
            )
        if not validator(record):
            return records[:index], records[index:]
    return records, []


def derived_seed(root, label):
    digest = hashlib.sha256(f"{root}:{label}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def worker(request, config):
    payload = dict(request)
    payload.update(nodes=list(NODES), cql_port=config["faults"]["cql_port"],
                   routing=config["routing"])
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


def initialize(schedule, timestamp, config, table="blocking", attempts=4):
    """Establish fresh ALL-consistency setup rows.

    Initialization is administration, not a measured application session, so a
    transient setup-time WriteTimeout (a replica not yet servable after recovery)
    is retried against a re-confirmed healthy cluster with a fresh timestamp and
    seed. This never touches the measured trial batch.
    """
    items = [{"key": case["key"], "table": case.get("table", table)} for case in schedule]
    last_error = None
    for attempt in range(attempts):
        response = worker({"action": "init", "items": items,
                           "ts": timestamp + attempt}, config)
        try:
            return require_records(response, len(items), "initialization")
        except RuntimeError as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                break
            # Re-confirm the cluster can serve ALL writes before retrying.
            wait_healthy(config["faults"]["recovery_timeout_seconds"])
            settle_after_recovery(config)
    raise last_error


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


def settle_after_recovery(config):
    """Pause after a cluster reports healthy so ALL-consistency writes are servable."""
    seconds = config["faults"].get("post_recovery_settle_seconds", 0)
    if seconds:
        time.sleep(seconds)
    return seconds


def recover_with_retry(config, attempts=3):
    """Clear project firewall rules and confirm health, tolerating a transient
    nodetool/gossip hiccup during cleanup so a healed cluster is not mislabelled
    as a recovery failure."""
    last_error = None
    for attempt in range(attempts):
        try:
            clear_partition()
            wait_healthy(config["faults"]["recovery_timeout_seconds"])
            return
        except BaseException as exc:
            last_error = exc
            time.sleep(3)
    raise last_error


def main_episode(config, evidence, run_id, scenario, round_no, rngs, all_trials,
                 fault_records, progress):
    schedule = session_guarantees.build_round(config, run_id, round_no, scenario, rngs["order"])
    progress.show("session_guarantees",
                  f"starting scenario={scenario}, round={round_no + 1}/{config['rounds']}, "
                  f"trials={len(schedule)}; initializing keys")
    timestamp = time.time_ns() // 1000
    initialization = initialize(schedule, timestamp, config)
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
                      f"running {len(schedule)} driver-routed trials")
        batch = worker({"action": "batch", "schedule": schedule,
                        "ts": timestamp + 1_000_000}, config)
        trials = batch.get("records") if isinstance(batch, dict) else None
        if not isinstance(trials, list) or len(trials) != len(schedule):
            raise RuntimeError(f"application batch returned {len(trials or [])}/{len(schedule)} histories")
        for trial in trials:
            trial.update(episode_id=episode_id, routing_policy=config["routing"]["policy"],
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
                record["settled_seconds"] = settle_after_recovery(config)
            elif cleanup and cleanup[0] == "partition":
                progress.show("session_guarantees",
                              f"scenario={scenario}, round={round_no + 1}/{config['rounds']}; "
                              "removing partition and verifying recovery")
                clear_partition()
                record["recovery"] = wait_healthy(config["faults"]["recovery_timeout_seconds"])
                record["settled_seconds"] = settle_after_recovery(config)
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


def run_read_repair(config, evidence, run_id, rngs, progress, results=None):
    results = list(results or [])
    if "read_repair" not in config["enabled_experiments"]:
        evidence.save("read_repair.json", results)
        return results
    full_cut = [("n1", "n2"), ("n1", "n3"), ("n2", "n3")]
    completed_ids = {record["case"]["attempt_id"] for record in results}
    for round_no in range(config["rounds"]):
        for table, setting in read_repair.settings(config):
            attempt_id = f"repair:{round_no}:{table}"
            if attempt_id in completed_ids:
                continue
            key = f"{config['design']}:{run_id}:{attempt_id}"
            case = {"attempt_id": attempt_id, "round": round_no, "table": table,
                    "setting": setting, "key": key}
            record = {"case": case, "started_ns": time.time_ns()}
            progress.show("read_repair",
                          f"starting setting={setting}, round={round_no + 1}/{config['rounds']}")
            try:
                record["initialization"] = initialize([case], time.time_ns() // 1000,
                                                       config, table)
                record["full_cut"] = set_graph(full_cut, config["faults"]["internode_ports"])
                if config["faults"]["partition_hold_seconds"]:
                    time.sleep(config["faults"]["partition_hold_seconds"])
                write = worker({"action": "ops",
                    "operations": [read_repair.minority_write(
                        key, time.time_ns() // 1000, table)]}, config)
                record["write"] = write
                selected = write.get("records", [{}])[0].get("routing", {}).get("selected_node")
                if selected not in NODES:
                    raise RuntimeError("minority write did not identify its driver-selected coordinator")
                pair1, pair2 = read_repair.topology_pairs(selected, NODES, rngs["topology"])
                record["pair_sequence"] = [pair1, pair2]
                record["pair1_graph"] = set_graph([edge for edge in full_cut if set(edge) != set(pair1)],
                                                   config["faults"]["internode_ports"])
                time.sleep(config["faults"]["partition_stabilization_seconds"])
                first = worker({"action": "ops",
                    "operations": [read_repair.quorum_read(key, table)]}, config)
                record["first"] = first
                record["pair2_graph"] = set_graph([edge for edge in full_cut if set(edge) != set(pair2)],
                                                   config["faults"]["internode_ports"])
                time.sleep(config["faults"]["partition_stabilization_seconds"])
                second = worker({"action": "ops",
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
                    recover_with_retry(config)
                    record["recovery"] = wait_healthy(config["faults"]["recovery_timeout_seconds"])
                    record["settled_seconds"] = settle_after_recovery(config)
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


def run_timestamp_controls(config, evidence, run_id, rngs, progress, results=None):
    results = list(results or [])
    if "timestamp_control" not in config["enabled_experiments"]:
        evidence.save("timestamp_control.json", results)
        return results
    completed_ids = {record["case"]["attempt_id"] for record in results}
    for round_no in range(config["rounds"]):
        if f"timestamp:{round_no}" in completed_ids:
            continue
        progress.show("timestamp_control",
                      f"starting round={round_no + 1}/{config['rounds']}")
        key = f"{config['design']}:{run_id}:timestamp:{round_no}"
        ts = time.time_ns() // 1000
        case = {"attempt_id": f"timestamp:{round_no}", "round": round_no,
                "key": key, "table": "blocking"}
        initialization = initialize([case], ts, config)
        operations = timestamp_control.operations(key, ts, "blocking")
        result = worker({"action": "ops", "operations": operations}, config)
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


def _run_plan(config, output, seed, started_utc, started_monotonic):
    output.mkdir(parents=True, exist_ok=False)
    evidence = Evidence(output)
    run_id = output.name.removeprefix("cassandra_policy_")
    seeds = {name: derived_seed(seed, name) for name in ("order", "faults", "topology")}
    rngs = {name: random.Random(value) for name, value in seeds.items()}
    evidence.save("plan.json", config)
    evidence.save("seeds.json", {"root": seed, **seeds})
    evidence.save("environment.json", environment(config, seed, run_id))
    evidence.save("completion.json", {"completed": False, "evidence_schema": EVIDENCE_SCHEMA,
                                       "run_id": run_id, "started_utc": started_utc})
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
    settle_after_recovery(config)
    schema = worker({"action": "schema"}, config)
    if schema.get("status") != "ok" or not schema.get("records"):
        raise RuntimeError("schema creation/inspection failed")
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
        timing = timing_fields(started_utc, started_monotonic)
        completion = {"completed": True, "evidence_schema": EVIDENCE_SCHEMA, "run_id": run_id,
                      "profile": config["profile"], "main_trials": len(all_trials),
                      "expected_main_trials": expected, "read_repair_trials": len(repairs),
                      "timestamp_trials": len(timestamps),
                      "verdicts": dict(Counter(t["verdict"] for t in all_trials)),
                      "completed_utc": timing["ended_utc"], **timing}
        evidence.save("completion.json", completion)
        evidence.event("run_completed", **completion)
        progress.show("complete", f"evidence saved in {output}")
        return output
    except BaseException as exc:
        evidence.event("run_failed", error={"type": type(exc).__name__, "message": str(exc)})
        raise


def run_plan(config, output, seed):
    """Run a plan and leave timing plus terminal status in completion.json."""
    started_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    started_monotonic = time.monotonic()
    try:
        return _run_plan(config, output, seed, started_utc, started_monotonic)
    except BaseException as exc:
        # Setup errors occur before _run_plan's workload exception handler. Preserve
        # their terminal state as well so every created run directory is auditable.
        if output.is_dir():
            path = output / "completion.json"
            if path.exists():
                try:
                    completion = json.loads(path.read_text())
                except (OSError, json.JSONDecodeError):
                    completion = {}
            else:
                completion = {}
            if completion.get("completed") is not True:
                completion.update({
                    "completed": False,
                    "evidence_schema": EVIDENCE_SCHEMA,
                    "run_id": output.name.removeprefix("cassandra_policy_"),
                    "profile": config.get("profile"),
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                    **timing_fields(started_utc, started_monotonic),
                })
                atomic_save(path, completion)
        raise


def expected_repair_ids(config):
    if "read_repair" not in config["enabled_experiments"]:
        return []
    return [f"repair:{round_no}:{table}"
            for round_no in range(config["rounds"])
            for table, _ in read_repair.settings(config)]


def expected_timestamp_ids(config):
    if "timestamp_control" not in config["enabled_experiments"]:
        return []
    return [f"timestamp:{round_no}" for round_no in range(config["rounds"])]


def validate_completed_main_phase(config, trials, faults):
    expected = expected_main_trials(config)
    if len(trials) != expected:
        raise RuntimeError(
            f"resume supports a completed main phase; found {len(trials)}/{expected} trials"
        )
    trial_ids = [trial.get("trial_id") for trial in trials]
    if None in trial_ids or len(trial_ids) != len(set(trial_ids)):
        raise RuntimeError("main trial checkpoint has missing or duplicate IDs")
    expected_episodes = (len(config["scenarios"]) * config["rounds"]
                         if "session_guarantees" in config["enabled_experiments"] else 0)
    if len(faults) != expected_episodes:
        raise RuntimeError(
            f"resume supports a completed main phase; found {len(faults)}/{expected_episodes} episodes"
        )
    episode_ids = [record.get("episode_id") for record in faults]
    if None in episode_ids or len(episode_ids) != len(set(episode_ids)):
        raise RuntimeError("main episode checkpoint has missing or duplicate IDs")
    trials_per_episode = len(config["consistency_configs"]) * len(config["models"])
    for record in faults:
        if len(record.get("trials", [])) != trials_per_episode:
            raise RuntimeError(f"episode {record.get('episode_id')} is incomplete")
        if "recovery_error" in record:
            raise RuntimeError(f"episode {record.get('episode_id')} failed recovery")


def replay_topology_choices(records, rng):
    """Restore the topology RNG to the point after retained repair attempts."""
    for record in records:
        selected = record["write"]["records"][0]["routing"]["selected_node"]
        expected = read_repair.topology_pairs(selected, NODES, rng)
        observed = record.get("pair_sequence")
        if observed != [list(expected[0]), list(expected[1])]:
            raise RuntimeError(
                f"saved topology choice does not match seed for {record['case']['attempt_id']}"
            )


def refresh_resume_environment(config, seed, run_id, evidence):
    previous = load_json(evidence.directory / "environment.json")
    current = environment(config, seed, run_id)
    history = list(previous.get("execution_snapshots", []))
    if not history:
        history.append({
            "phase": "initial",
            "started_utc": previous.get("started_utc"),
            "git_revision": previous.get("git_revision"),
            "git_status": previous.get("git_status"),
            "docker_compose": previous.get("docker_compose"),
            "source_manifest_sha256": previous.get("source_manifest_sha256"),
        })
    history.append({
        "phase": "resume",
        "started_utc": current["started_utc"],
        "git_revision": current["git_revision"],
        "git_status": current["git_status"],
        "docker_compose": current["docker_compose"],
        "source_manifest_sha256": current["source_manifest_sha256"],
    })
    previous.update({
        "git_revision": current["git_revision"],
        "git_status": current["git_status"],
        "docker_compose": current["docker_compose"],
        "source_manifest_sha256": current["source_manifest_sha256"],
        "effective_config": config,
        "execution_snapshots": history,
    })
    evidence.save("environment.json", previous)


def resume_plan(output):
    """Continue controls in an incomplete run whose main phase is complete."""
    evidence = Evidence(output)
    completion_path = output / "completion.json"
    completion = load_json(completion_path)
    if completion.get("completed") is True:
        raise RuntimeError("run is already complete")
    if completion.get("evidence_schema") != EVIDENCE_SCHEMA:
        raise RuntimeError("run uses an unsupported evidence schema")
    raw_plan = load_json(output / "plan.json")
    config = normalize(raw_plan, full=raw_plan.get("profile") != "smoke")
    seeds = load_json(output / "seeds.json")
    seed = seeds.get("root")
    if not isinstance(seed, int):
        raise RuntimeError("run does not contain a valid root seed")
    expected_seeds = {name: derived_seed(seed, name) for name in ("order", "faults", "topology")}
    if any(seeds.get(name) != value for name, value in expected_seeds.items()):
        raise RuntimeError("saved derived seeds do not match the root seed")
    run_id = output.name.removeprefix("cassandra_policy_")
    if completion.get("run_id") != run_id:
        raise RuntimeError("completion run ID does not match the result directory")

    trials = load_json(output / "trials.json")
    faults = load_json(output / "faults.json")
    validate_completed_main_phase(config, trials, faults)

    repairs_raw = load_json(output / "read_repair.json") if (output / "read_repair.json").exists() else []
    repairs, discarded_repairs = checkpoint_prefix(
        repairs_raw, expected_repair_ids(config), valid_repair_checkpoint, "read-repair"
    )
    timestamps_raw = (load_json(output / "timestamp_control.json")
                      if (output / "timestamp_control.json").exists() else [])
    timestamps, discarded_timestamps = checkpoint_prefix(
        timestamps_raw, expected_timestamp_ids(config), valid_timestamp_checkpoint, "timestamp"
    )

    resume_started_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    resume_started_monotonic = time.monotonic()
    previous_minutes = float(completion.get("completion_time_minutes", 0.0))
    failures = list(completion.get("failure_history", []))
    if completion.get("error"):
        failures.append({
            "ended_utc": completion.get("ended_utc"),
            "completion_time_minutes": completion.get("completion_time_minutes"),
            "error": completion["error"],
        })
    resume_count = int(completion.get("resume_count", 0)) + 1
    completion.update({
        "completed": False,
        "resume_count": resume_count,
        "last_resumed_utc": resume_started_utc,
        "failure_history": failures,
    })
    for terminal_field in ("error", "ended_utc", "completed_utc"):
        completion.pop(terminal_field, None)
    evidence.save("completion.json", completion)
    evidence.event("run_resumed", run_id=run_id, resume_count=resume_count,
                   retained_main_trials=len(trials), retained_read_repair=len(repairs),
                   retained_timestamps=len(timestamps))

    archive_stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    discarded = {"read_repair": discarded_repairs, "timestamp_control": discarded_timestamps}
    if discarded_repairs or discarded_timestamps:
        evidence.save(f"resume_discarded_{archive_stamp}_{resume_count}.json", discarded)
        evidence.save("read_repair.json", repairs)
        evidence.save("timestamp_control.json", timestamps)
        evidence.event("resume_invalid_tail_archived",
                       read_repair=len(discarded_repairs),
                       timestamp_control=len(discarded_timestamps))

    total = (expected_main_trials(config) + read_repair.expected_trials(config)
             + timestamp_control.expected_trials(config))
    progress = Progress(total, completed=len(trials) + len(repairs) + len(timestamps))
    rngs = {name: random.Random(value) for name, value in expected_seeds.items()}
    replay_topology_choices(repairs, rngs["topology"])

    try:
        progress.show("resume", f"run={run_id}; restoring cluster health")
        recovery = recover_all(config["faults"]["recovery_timeout_seconds"])
        settle_after_recovery(config)
        schema = worker({"action": "schema"}, config)
        probe = worker({"action": "probe"}, config)
        if schema.get("status") != "ok" or not schema.get("records"):
            raise RuntimeError("resume schema creation/inspection failed")
        if len(probe) != len(NODES) or not all(item.get("reachable") for item in probe):
            raise RuntimeError("resume requires every CQL endpoint to be ready")
        evidence.save(f"resume_cluster_{archive_stamp}_{resume_count}.json",
                      {"resumed_utc": resume_started_utc, "recovery": recovery,
                       "schema": schema, "client_probe": probe})
        refresh_resume_environment(config, seed, run_id, evidence)
        progress.show("resume", f"cluster healthy; continuing after {len(repairs)} repair "
                      f"and {len(timestamps)} timestamp checkpoints")

        repairs = run_read_repair(config, evidence, run_id, rngs, progress, repairs)
        timestamps = run_timestamp_controls(config, evidence, run_id, rngs, progress, timestamps)
        if len(repairs) != read_repair.expected_trials(config):
            raise RuntimeError("read-repair attempt count mismatch after resume")
        if len(timestamps) != timestamp_control.expected_trials(config):
            raise RuntimeError("timestamp-control attempt count mismatch after resume")

        timing = timing_fields(completion["started_utc"], resume_started_monotonic,
                               previous_minutes)
        final = {
            "completed": True, "evidence_schema": EVIDENCE_SCHEMA, "run_id": run_id,
            "profile": config["profile"], "main_trials": len(trials),
            "expected_main_trials": expected_main_trials(config),
            "read_repair_trials": len(repairs), "timestamp_trials": len(timestamps),
            "verdicts": dict(Counter(trial["verdict"] for trial in trials)),
            "completed_utc": timing["ended_utc"], "resume_count": resume_count,
            "last_resumed_utc": resume_started_utc, "failure_history": failures,
            **timing,
        }
        evidence.save("completion.json", final)
        from scripts.verify_randomized import verify
        validation = verify(output)
        evidence.event("run_completed", **final, validation=validation)
        progress.show("complete", f"resumed evidence verified and saved in {output}")
        return output
    except BaseException as exc:
        timing = timing_fields(completion["started_utc"], resume_started_monotonic,
                               previous_minutes)
        completion.update({
            "completed": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
            "resume_count": resume_count,
            "last_resumed_utc": resume_started_utc,
            **timing,
        })
        evidence.save("completion.json", completion)
        evidence.event("run_resume_failed",
                       error={"type": type(exc).__name__, "message": str(exc)})
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
    parser.add_argument("--config", type=Path, default=ROOT / "config/cassandra_driver_experiments.json")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="allow fewer than ten attempts; never a submission run")
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--recover", action="store_true", help="restart all nodes and clear project firewall rules")
    parser.add_argument("--resume", type=Path,
                        help="continue controls in an incomplete result directory with a complete main phase")
    args = parser.parse_args()
    if args.resume and (args.plan_only or args.recover or args.seed is not None
                        or args.repetitions is not None or args.smoke):
        parser.error("--resume cannot be combined with --plan-only, --recover, --seed, "
                     "--repetitions, or --smoke; the saved plan and seed are authoritative")
    if args.resume:
        output = args.resume.resolve()
        if not output.is_dir():
            parser.error(f"resume directory does not exist: {output}")
        config = None
        seed = None
    else:
        config = load_config(args.config, full=not args.smoke, repetitions=args.repetitions)
        seed = args.seed if args.seed is not None else config.get("seed")
        seed = seed if seed is not None else secrets.randbits(64)
    if args.plan_only:
        print(json.dumps(plan_summary(config, seed), indent=2))
        return
    if args.recover:
        print(json.dumps(recover_all(config["faults"]["recovery_timeout_seconds"]), indent=2))
        return
    lock_path = ROOT / ".cassandra-policy-run.lock"
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error("another Cassandra-policy run holds the project lock")
        print("[runner] Building and starting the Docker Compose environment...", flush=True)
        compose("up", "-d", "--build", timeout=1800)
        print("[runner] Docker Compose environment started; beginning experiment setup.", flush=True)
        if args.resume:
            try:
                print(resume_plan(output))
            except BaseException:
                try:
                    saved_plan = load_json(output / "plan.json")
                    recover_all(saved_plan["faults"]["recovery_timeout_seconds"])
                except BaseException as cleanup_error:
                    print(f"automatic recovery failed: {cleanup_error}", file=sys.stderr)
                raise
            return
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = ROOT / "results" / f"cassandra_policy_{stamp}_{seed:016x}"
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
