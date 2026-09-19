#!/usr/bin/env python3
"""Independently validate a completed randomized-run evidence directory."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from checks import evaluate
from experiments.configuration import expected_main_trials, normalize
from experiments import read_repair, timestamp_control

SCHEMA = "randomized-cassandra-evidence-v3"


class EvidenceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def load(path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise EvidenceError(f"missing evidence file: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"invalid JSON in {path.name}: {exc}") from exc


def expected_case_counter(plan):
    if "session_guarantees" not in plan["enabled_experiments"]:
        return Counter()
    return Counter((scenario, pair, model)
                   for scenario in plan["scenarios"]
                   for pair in plan["consistency_configs"]
                   for model in plan["models"]
                   for _ in range(plan["rounds"]))


def verify_initialization(record, expected, keys=None):
    require(isinstance(record, dict), "initialization must be an object")
    records = record.get("records")
    require(isinstance(records, list) and len(records) == expected,
            f"initialization must contain {expected} records")
    require(all(item.get("status") == "ok" for item in records),
            "initialization contains an unsuccessful operation")
    require(all(item.get("cl") == "ALL" for item in records),
            "initialization did not use ALL")
    if keys is not None:
        observed = [next((value for value in item.get("params", []) if value in keys), None)
                    for item in records]
        require(Counter(observed) == Counter(keys), "initialization key coverage mismatch")


def verify_operation(operation, key, expected_cl, sequence):
    require(operation.get("sequence") == sequence, "operation sequence is incorrect")
    require(operation.get("cl") == expected_cl, "operation consistency level is incorrect")
    require(key in operation.get("params", []), "operation does not reference its trial key")
    require(operation.get("start_ns", 1) <= operation.get("end_ns", 0), "operation time is reversed")
    route = operation.get("routing")
    require(isinstance(route, dict), "operation lacks routing evidence")
    require(route.get("selected_node") in route.get("candidates", []), "selected route is not a candidate")
    require(len(route.get("candidates", [])) == len(set(route.get("candidates", []))),
            "routing candidates contain duplicates")
    require(isinstance(route.get("draw"), int) and route["draw"] >= 0,
            "routing draw is invalid")
    require(operation.get("node") == route.get("selected_node"), "requested node differs from selected route")
    if operation.get("status") == "ok":
        require(operation.get("coordinator"), "successful operation lacks actual coordinator")
    require(isinstance(operation.get("client_id"), str), "operation lacks logical client identity")


def verify_trial(trial):
    required = {"trial_id", "scenario", "round", "config", "model", "key",
                "operations", "verdict", "reason", "coverage", "episode_id"}
    require(required <= set(trial), f"trial missing fields: {sorted(required - set(trial))}")
    write_cl, read_cl = trial["config"].split("/")
    operations = trial["operations"]
    expected_kinds = {
        "RYW": ["write", "read"], "MR": ["write", "read", "read"],
        "MW": ["write", "write", "read"], "WFR": ["write", "read", "write", "read"]
    }[trial["model"]]
    require(len(operations) == len(expected_kinds), "history has an incorrect operation count")
    previous_end = None
    for index, (operation, kind) in enumerate(zip(operations, expected_kinds)):
        require(operation.get("kind") == kind, "history operation kind is incorrect")
        expected_cl = write_cl if kind == "write" else read_cl
        verify_operation(operation, trial["key"], expected_cl, index)
        if previous_end is not None:
            require(previous_end <= operation["start_ns"], "history operations overlap or are reordered")
        previous_end = operation["end_ns"]
    calculated = evaluate(trial["model"], operations)
    require(trial["verdict"] == calculated["verdict"], "stored verdict differs from recomputed verdict")
    require(trial["reason"] == calculated["reason"], "stored reason differs from recomputed reason")
    require(trial["coverage"] == calculated["coverage"], "stored coverage differs from recomputed coverage")


def verify_faults(faults, plan, trials):
    expected_episodes = len(plan["scenarios"]) * plan["rounds"] if "session_guarantees" in plan["enabled_experiments"] else 0
    require(len(faults) == expected_episodes, "fault/episode record count mismatch")
    trial_episodes = Counter(trial["episode_id"] for trial in trials)
    for record in faults:
        scenario = record.get("scenario")
        episode_id = record.get("episode_id")
        require(trial_episodes[episode_id] == len(plan["models"]) * len(plan["consistency_configs"]),
                f"episode {episode_id} has incomplete trial coverage")
        schedule = record.get("schedule", [])
        verify_initialization(record.get("initialization"), len(schedule),
                              [case.get("key") for case in schedule])
        episode_trials = record.get("trials", [])
        draws = [operation["routing"]["draw"] for trial in episode_trials
                 for operation in trial.get("operations", [])]
        require(draws == list(range(len(draws))),
                f"episode {episode_id} routing draws are not continuous")
        require("recovery_error" not in record, f"episode {episode_id} failed recovery")
        if scenario == "node_failure":
            fault = record.get("fault") or {}
            require(fault.get("after", {}).get("running") is False, "victim exit was not proved")
            observations = fault.get("detection", {}).get("observations", [])
            require(observations and observations[-1].get("matching"), "survivors did not prove victim down")
            require(record.get("recovery"), "node-failure episode lacks recovery evidence")
        elif scenario == "network_partition":
            fault = record.get("fault") or {}
            require(fault.get("isolated") in {"n1", "n2", "n3"}, "partition lacks isolated node")
            require(all(item.get("reachable") for item in fault.get("client_probe", [])) and
                    len(fault.get("client_probe", [])) == 3,
                    "partition did not preserve all CQL endpoints")
            require(record.get("post_workload_partition"), "partition lacks post-workload counters")
            require(record.get("recovery"), "partition episode lacks recovery evidence")


def verify_controls(run, plan, completion):
    repairs = load(run / "read_repair.json")
    timestamps = load(run / "timestamp_control.json")
    require(len(repairs) == read_repair.expected_trials(plan), "read-repair count mismatch")
    require(len(timestamps) == timestamp_control.expected_trials(plan), "timestamp-control count mismatch")
    repair_ids = [item.get("case", {}).get("attempt_id") for item in repairs]
    require(len(repair_ids) == len(set(repair_ids)), "duplicate read-repair attempt ID")
    for item in repairs:
        verify_initialization(item.get("initialization"), 1, [item.get("case", {}).get("key")])
        require(item.get("case", {}).get("setting") in {"BLOCKING", "NONE"}, "unknown read-repair setting")
        require(item.get("verdict") in {"regression", "no_regression_observed", "inconclusive"},
                "invalid read-repair verdict")
        require("recovery_error" not in item, "read-repair cleanup failed")
    timestamp_ids = [item.get("case", {}).get("attempt_id") for item in timestamps]
    require(len(timestamp_ids) == len(set(timestamp_ids)), "duplicate timestamp attempt ID")
    for item in timestamps:
        verify_initialization(item.get("initialization"), 1, [item.get("case", {}).get("key")])
        require(item.get("verdict") in {"expected", "unexpected", "inconclusive"},
                "invalid timestamp verdict")
        require(item.get("timestamps", [0, 0])[0] > item.get("timestamps", [0, 0])[1],
                "timestamp control did not reverse application order")
    require(completion.get("read_repair_trials") == len(repairs), "completion repair count mismatch")
    require(completion.get("timestamp_trials") == len(timestamps), "completion timestamp count mismatch")
    return repairs, timestamps


def verify(run):
    plan = normalize(load(run / "plan.json"), full=load(run / "plan.json").get("profile") != "smoke")
    completion = load(run / "completion.json")
    environment = load(run / "environment.json")
    trials = load(run / "trials.json")
    faults = load(run / "faults.json")
    require(completion.get("completed") is True, "run is not complete")
    require(completion.get("evidence_schema") == SCHEMA, "unsupported completion evidence schema")
    require(environment.get("evidence_schema") == SCHEMA, "unsupported environment evidence schema")
    require(completion.get("run_id") == environment.get("run_id"), "run identity mismatch")
    expected = expected_main_trials(plan)
    require(len(trials) == expected == completion.get("main_trials"), "main trial count mismatch")
    identifiers = [trial.get("trial_id") for trial in trials]
    require(len(identifiers) == len(set(identifiers)), "duplicate main trial ID")
    keys = [trial.get("key") for trial in trials]
    require(len(keys) == len(set(keys)), "main trial keys are not unique")
    observed = Counter((trial.get("scenario"), trial.get("config"), trial.get("model")) for trial in trials)
    require(observed == expected_case_counter(plan), "main trial case coverage mismatch")
    for trial in trials:
        verify_trial(trial)
    verify_faults(faults, plan, trials)
    repairs, timestamps = verify_controls(run, plan, completion)
    case_rows = [{"scenario": scenario, "config": pair, "model": model, "attempts": count}
                 for (scenario, pair, model), count in sorted(observed.items())]
    return {"valid": True, "evidence_schema": SCHEMA, "main_trials": len(trials),
            "cases": case_rows, "verdicts": dict(Counter(t["verdict"] for t in trials)),
            "read_repair_trials": len(repairs), "timestamp_trials": len(timestamps)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    try:
        print(json.dumps(verify(parser.parse_args().results), indent=2, sort_keys=True))
    except EvidenceError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        raise SystemExit(1)
