#!/usr/bin/env python3
"""Export approved Cassandra experiment evidence to auditable CSV files.

The exporter is intentionally read-only with respect to results/. It includes
all saved trials from matching evidence families, while marking only complete,
structurally valid runs as eligible for aggregate analysis.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS = ROOT / "results"
DEFAULT_OUTPUT = Path(__file__).resolve().parent
EXPORT_SCHEMA = "report-evidence-export-v1"

APPROVED = {
    ("random-coordinator-v2", "randomized-cassandra-evidence-v3"): {
        "setup": "previous_randomized",
        "routing_policy": "harness_controlled_independent_random_coordinator",
    },
    ("cassandra-driver-policy-v3", "cassandra-driver-policy-evidence-v4"): {
        "setup": "cassandra_token_aware",
        "routing_policy": "TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc=dc1))",
    },
    ("cassandra-driver-policy-expanded-v1", "cassandra-driver-policy-evidence-v5"): {
        "setup": "cassandra_token_aware_expanded",
        "routing_policy": "TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc=dc1))",
    },
}

SCENARIOS = ("normal", "node_failure", "network_partition")
MODELS = ("RYW", "MR", "MW", "WFR")
CONFIGS = (
    "ONE/ONE", "ONE/QUORUM", "ONE/ALL",
    "QUORUM/ONE", "QUORUM/QUORUM", "QUORUM/ALL",
    "ALL/ONE", "ALL/QUORUM", "ALL/ALL",
)
OUTCOMES = ("violation", "no_violation_observed", "inconclusive")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def compact_json(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def truth(value: Any) -> str:
    if value is None or value == "":
        return ""
    return "true" if bool(value) else "false"


def join_values(values: Iterable[Any]) -> str:
    return "|".join(str(value) for value in values if value not in (None, ""))


def expected_trials(plan: dict[str, Any]) -> int | None:
    try:
        return (
            int(plan["rounds"])
            * len(plan["scenarios"])
            * len(plan["consistency_configs"])
            * len(plan["models"])
        )
    except (KeyError, TypeError, ValueError):
        return None


def outcome_key(verdict: Any) -> str:
    value = str(verdict or "missing")
    return value if value in OUTCOMES else "other"


def extract_version(environment: dict[str, Any], key: str) -> str:
    effective = environment.get("effective_config") or {}
    if isinstance(effective, dict) and effective.get(key) is not None:
        return str(effective[key])
    return ""


def slim_fault(fault: Any) -> dict[str, Any]:
    if not isinstance(fault, dict):
        return {}
    keep = ("action", "after", "blocked", "client_probe", "ips", "isolated", "groups",
            "partition_strategy", "established_ns")
    return {key: fault[key] for key in keep if key in fault}


def episode_index(directory: Path) -> tuple[dict[str, dict[str, Any]], str]:
    path = directory / "faults.json"
    records = read_json(path, [])
    if not isinstance(records, list):
        return {}, sha256(path)
    indexed = {}
    for record in records:
        if not isinstance(record, dict) or not record.get("episode_id"):
            continue
        fault = record.get("fault") or {}
        after = fault.get("after") if isinstance(fault, dict) else {}
        isolated = fault.get("isolated") if isinstance(fault, dict) else None
        groups = fault.get("groups") if isinstance(fault, dict) else None
        all_nodes = sorted((fault.get("blocked") or {}).keys()) if isinstance(fault, dict) else []
        majority = ([node for node in all_nodes if node != isolated] if isolated else
                    (max(groups, key=len) if isinstance(groups, list) and len(groups) == 2 else []))
        probes = fault.get("client_probe", []) if isinstance(fault, dict) else []
        indexed[str(record["episode_id"])] = {
            "episode_started_ns": record.get("started_ns"),
            "episode_ended_ns": record.get("ended_ns"),
            "fault_settled_seconds": record.get("settled_seconds"),
            "fault_action": fault.get("action") if isinstance(fault, dict) else None,
            "failed_node": after.get("node") if isinstance(after, dict) else None,
            "failed_node_running_after_fault": after.get("running") if isinstance(after, dict) else None,
            "isolated_node": isolated,
            "majority_nodes": majority,
            "partition_groups": groups,
            "client_probe_total": len(probes) if isinstance(probes, list) else None,
            "client_probe_reachable": sum(bool(item.get("reachable")) for item in probes if isinstance(item, dict)) if isinstance(probes, list) else None,
            "post_workload_partition_recorded": bool(record.get("post_workload_partition")),
            "recovery_recorded": bool(record.get("recovery")),
            "recovery_error": record.get("recovery_error"),
            "fault_summary": slim_fault(fault),
        }
    return indexed, sha256(path)


def run_identity(directory: Path) -> dict[str, Any] | None:
    completion = read_json(directory / "completion.json", {})
    environment = read_json(directory / "environment.json", {})
    plan = read_json(directory / "plan.json", {})
    design = completion.get("design") or environment.get("design") or plan.get("design")
    schema = completion.get("evidence_schema") or environment.get("evidence_schema")
    approved = APPROVED.get((design, schema))
    if not approved:
        return None
    trials = read_json(directory / "trials.json", [])
    if not isinstance(trials, list):
        trials = []
    read_repairs = read_json(directory / "read_repair.json", [])
    timestamps = read_json(directory / "timestamp_control.json", [])
    if not isinstance(read_repairs, list):
        read_repairs = []
    if not isinstance(timestamps, list):
        timestamps = []
    run_id = completion.get("run_id") or environment.get("run_id") or directory.name.split("_", 1)[-1]
    expected = expected_trials(plan)
    completed = completion.get("completed") is True
    declared = completion.get("main_trials")
    identifiers = [trial.get("trial_id") for trial in trials if isinstance(trial, dict)]
    keys = [trial.get("key") for trial in trials if isinstance(trial, dict)]
    notes = []
    if not completed:
        notes.append("completion_false")
    if completion.get("evidence_schema") not in (None, schema):
        notes.append("completion_schema_mismatch")
    if environment.get("evidence_schema") not in (None, schema):
        notes.append("environment_schema_mismatch")
    if completion.get("run_id") not in (None, run_id) or environment.get("run_id") not in (None, run_id):
        notes.append("run_id_mismatch")
    if completed and declared != len(trials):
        notes.append("completion_trial_count_mismatch")
    if completed and expected is not None and expected != len(trials):
        notes.append("plan_trial_count_mismatch")
    if completed and completion.get("read_repair_trials") is not None and completion.get("read_repair_trials") != len(read_repairs):
        notes.append("read_repair_count_mismatch")
    if completed and completion.get("timestamp_trials") is not None and completion.get("timestamp_trials") != len(timestamps):
        notes.append("timestamp_control_count_mismatch")
    if len(identifiers) != len(set(identifiers)):
        notes.append("duplicate_trial_id")
    if len(keys) != len(set(keys)):
        notes.append("duplicate_trial_key")
    if any(not isinstance(trial, dict) for trial in trials):
        notes.append("non_object_trial")
    eligible = completed and not notes
    return {
        "directory": directory,
        "setup": approved["setup"],
        "routing_policy_label": approved["routing_policy"],
        "design_id": design,
        "evidence_schema": schema,
        "run_id": str(run_id),
        "completion": completion,
        "environment": environment,
        "plan": plan,
        "trials": trials,
        "read_repairs": read_repairs,
        "timestamps": timestamps,
        "completed": completed,
        "expected_trials": expected,
        "eligible": eligible,
        "validation_notes": notes,
    }


def operation_columns(index: int) -> list[str]:
    prefix = f"op{index}_"
    return [prefix + name for name in (
        "sequence", "kind", "role", "client_id", "cl", "status", "error_class",
        "error_message", "node", "coordinator", "latency_ms", "start_ns", "end_ns",
        "query", "params_json", "value_json", "routing_key", "routing_policy",
        "routing_local_dc", "routing_draw", "routing_operation_index",
        "routing_selected_node", "routing_candidates", "routing_eligible_nodes",
        "routing_replica_nodes", "routing_selected_is_replica", "routing_attempted_nodes",
        "extra_json",
    )]


TRIAL_FIELDS = [
    "export_schema", "record_type", "experiment_type", "setup", "design_id", "evidence_schema", "routing_policy_label",
    "run_id", "source_result_directory", "source_trials_file", "source_trials_sha256",
    "source_record_file", "source_record_sha256",
    "source_faults_file", "source_faults_sha256", "run_completed", "included_in_analysis",
    "included_in_main_violation_matrix",
    "run_validation_status", "run_validation_notes", "run_profile", "run_started_utc",
    "run_ended_utc", "run_duration_minutes", "root_seed", "git_revision", "platform",
    "python_version", "configured_rounds", "configured_repetitions", "cluster_profile",
    "configured_nodes", "replication_factor",
    "hints_enabled", "trial_id", "episode_id", "scenario", "round", "attempt", "model",
    "config_write_read", "write_cl", "read_cl", "key", "trial_verdict", "trial_reason", "outcome_class",
    "is_violation", "is_no_violation_observed", "is_inconclusive", "coverage_evaluable",
    "coverage_dependency_exposed", "coverage_mr_first_read_exposed",
    "coverage_successor_exposed", "routing_seed", "trial_routing_policy", "operation_count",
    "successful_operation_count", "failed_operation_count", "operation_error_classes",
    "first_error_class", "first_error_message", "coordinator_node_sequence",
    "coordinator_endpoint_sequence", "distinct_coordinator_nodes", "changed_coordinator",
    "crossed_partition_cut", "routed_to_failed_node", "trial_start_ns", "trial_end_ns",
    "trial_duration_ms", "episode_started_ns", "episode_ended_ns", "fault_settled_seconds",
    "fault_action", "failed_node", "failed_node_running_after_fault", "isolated_node",
    "majority_nodes", "partition_groups_json", "client_probe_total", "client_probe_reachable",
    "post_workload_partition_recorded", "recovery_recorded", "recovery_error",
    "fault_summary_json", "worker_health_json", "trial_extra_json",
    "control_setting", "control_table", "control_timestamps_json", "control_metadata_json",
]
for _index in range(1, 5):
    TRIAL_FIELDS.extend(operation_columns(_index))


def flatten_operation(row: dict[str, Any], index: int, operation: dict[str, Any]) -> None:
    prefix = f"op{index}_"
    routing = operation.get("routing") or {}
    known = {
        "sequence", "kind", "role", "client_id", "cl", "status", "error", "message",
        "node", "coordinator", "latency_ms", "start_ns", "end_ns", "query", "params",
        "value", "routing_key", "routing",
    }
    values = {
        "sequence": operation.get("sequence"),
        "kind": operation.get("kind"),
        "role": operation.get("role"),
        "client_id": operation.get("client_id"),
        "cl": operation.get("cl"),
        "status": operation.get("status"),
        "error_class": operation.get("error"),
        "error_message": operation.get("message"),
        "node": operation.get("node"),
        "coordinator": operation.get("coordinator"),
        "latency_ms": operation.get("latency_ms"),
        "start_ns": operation.get("start_ns"),
        "end_ns": operation.get("end_ns"),
        "query": operation.get("query"),
        "params_json": compact_json(operation.get("params")),
        "value_json": compact_json(operation.get("value")),
        "routing_key": operation.get("routing_key"),
        "routing_policy": routing.get("policy"),
        "routing_local_dc": routing.get("local_dc"),
        "routing_draw": routing.get("draw"),
        "routing_operation_index": routing.get("operation_index"),
        "routing_selected_node": routing.get("selected_node"),
        "routing_candidates": join_values(routing.get("candidates", [])),
        "routing_eligible_nodes": join_values(routing.get("eligible_nodes", [])),
        "routing_replica_nodes": join_values(routing.get("replica_nodes", [])),
        "routing_selected_is_replica": truth(routing.get("selected_is_replica")),
        "routing_attempted_nodes": join_values(routing.get("attempted_nodes", [])),
        "extra_json": compact_json({key: value for key, value in operation.items() if key not in known}),
    }
    for name, value in values.items():
        row[prefix + name] = value


def trial_row(run: dict[str, Any], trial: dict[str, Any], episode: dict[str, Any],
              trials_hash: str, faults_hash: str, *, record_type: str = "main_trial",
              experiment_type: str | None = None, source_record_file: Path | None = None,
              source_record_hash: str = "", control_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    completion = run["completion"]
    environment = run["environment"]
    plan = run["plan"]
    operations = [item for item in trial.get("operations", []) if isinstance(item, dict)]
    statuses = Counter(str(operation.get("status") or "missing") for operation in operations)
    errors = Counter(str(operation.get("error")) for operation in operations if operation.get("error"))
    nodes = [
        (operation.get("routing") or {}).get("selected_node") or operation.get("node")
        for operation in operations
    ]
    nodes = [node for node in nodes if node]
    endpoints = [operation.get("coordinator") for operation in operations if operation.get("coordinator")]
    isolated = episode.get("isolated_node")
    groups = episode.get("partition_groups")
    crossed = ""
    if trial.get("scenario") == "network_partition":
        if isinstance(groups, list) and len(groups) == 2:
            sides = {index for index, group in enumerate(groups) if any(node in group for node in nodes)}
            crossed = truth(len(sides) > 1)
        elif isolated:
            crossed = truth(isolated in nodes and any(node != isolated for node in nodes))
    failed = episode.get("failed_node")
    starts = [operation.get("start_ns") for operation in operations if isinstance(operation.get("start_ns"), int)]
    ends = [operation.get("end_ns") for operation in operations if isinstance(operation.get("end_ns"), int)]
    start_ns = min(starts) if starts else None
    end_ns = max(ends) if ends else None
    config = str(trial.get("config") or "")
    write_cl, read_cl = (config.split("/", 1) + [""])[:2] if "/" in config else ("", "")
    coverage = trial.get("coverage") or {}
    first_error = next((operation for operation in operations if operation.get("status") != "ok"), {})
    known_trial = {
        "attempt", "config", "coverage", "episode_id", "key", "model", "operations", "reason",
        "round", "routing_seed", "routing_policy", "scenario", "trial_id", "verdict", "worker_health",
    }
    database = plan.get("database") or {}
    cluster = plan.get("cluster") or {"profile": "three_node", "nodes": ["n1", "n2", "n3"]}
    verdict = trial.get("verdict")
    if record_type == "main_trial":
        outcome_class = verdict
    elif verdict == "inconclusive":
        outcome_class = "control_inconclusive"
    else:
        outcome_class = f"control_{verdict}" if verdict else "control_missing"
    row = {
        "export_schema": EXPORT_SCHEMA,
        "record_type": record_type,
        "experiment_type": experiment_type or trial.get("scenario"),
        "setup": run["setup"],
        "design_id": run["design_id"],
        "evidence_schema": run["evidence_schema"],
        "routing_policy_label": run["routing_policy_label"],
        "run_id": run["run_id"],
        "source_result_directory": relative(run["directory"]),
        "source_trials_file": relative(run["directory"] / "trials.json"),
        "source_trials_sha256": trials_hash,
        "source_record_file": relative(source_record_file or (run["directory"] / "trials.json")),
        "source_record_sha256": source_record_hash or trials_hash,
        "source_faults_file": relative(run["directory"] / "faults.json"),
        "source_faults_sha256": faults_hash,
        "run_completed": truth(run["completed"]),
        "included_in_analysis": truth(run["eligible"]),
        "included_in_main_violation_matrix": truth(run["eligible"] and record_type == "main_trial"),
        "run_validation_status": "passed" if run["eligible"] else "excluded",
        "run_validation_notes": join_values(run["validation_notes"]),
        "run_profile": completion.get("profile") or plan.get("profile"),
        "run_started_utc": completion.get("started_utc") or environment.get("started_utc"),
        "run_ended_utc": completion.get("ended_utc") or completion.get("completed_utc"),
        "run_duration_minutes": completion.get("completion_time_minutes"),
        "root_seed": environment.get("root_seed") or plan.get("seed"),
        "git_revision": environment.get("git_revision"),
        "platform": environment.get("platform"),
        "python_version": environment.get("python"),
        "configured_rounds": plan.get("rounds"),
        "configured_repetitions": plan.get("repetitions"),
        "cluster_profile": cluster.get("profile"),
        "configured_nodes": join_values(cluster.get("nodes", [])),
        "replication_factor": database.get("replication_factor"),
        "hints_enabled": truth(database.get("hints_enabled")),
        "trial_id": trial.get("trial_id"),
        "episode_id": trial.get("episode_id"),
        "scenario": trial.get("scenario"),
        "round": trial.get("round"),
        "attempt": trial.get("attempt"),
        "model": trial.get("model"),
        "config_write_read": config,
        "write_cl": write_cl,
        "read_cl": read_cl,
        "key": trial.get("key"),
        "trial_verdict": trial.get("verdict"),
        "trial_reason": trial.get("reason"),
        "outcome_class": outcome_class,
        "is_violation": truth(trial.get("verdict") == "violation"),
        "is_no_violation_observed": truth(trial.get("verdict") == "no_violation_observed"),
        "is_inconclusive": truth(trial.get("verdict") == "inconclusive"),
        "coverage_evaluable": truth(coverage.get("evaluable")),
        "coverage_dependency_exposed": truth(coverage.get("dependency_exposed")),
        "coverage_mr_first_read_exposed": truth(coverage.get("mr_first_read_exposed")),
        "coverage_successor_exposed": truth(coverage.get("successor_exposed")),
        "routing_seed": trial.get("routing_seed"),
        "trial_routing_policy": trial.get("routing_policy"),
        "operation_count": len(operations),
        "successful_operation_count": statuses.get("ok", 0),
        "failed_operation_count": len(operations) - statuses.get("ok", 0),
        "operation_error_classes": compact_json(dict(sorted(errors.items()))),
        "first_error_class": first_error.get("error"),
        "first_error_message": first_error.get("message"),
        "coordinator_node_sequence": join_values(nodes),
        "coordinator_endpoint_sequence": join_values(endpoints),
        "distinct_coordinator_nodes": len(set(nodes)),
        "changed_coordinator": truth(len(set(nodes)) > 1),
        "crossed_partition_cut": crossed,
        "routed_to_failed_node": truth(bool(failed) and failed in nodes) if failed else "",
        "trial_start_ns": start_ns,
        "trial_end_ns": end_ns,
        "trial_duration_ms": round((end_ns - start_ns) / 1_000_000, 6) if start_ns is not None and end_ns is not None else "",
        "episode_started_ns": episode.get("episode_started_ns"),
        "episode_ended_ns": episode.get("episode_ended_ns"),
        "fault_settled_seconds": episode.get("fault_settled_seconds"),
        "fault_action": episode.get("fault_action"),
        "failed_node": failed,
        "failed_node_running_after_fault": truth(episode.get("failed_node_running_after_fault")),
        "isolated_node": isolated,
        "majority_nodes": join_values(episode.get("majority_nodes", [])),
        "partition_groups_json": compact_json(groups),
        "client_probe_total": episode.get("client_probe_total"),
        "client_probe_reachable": episode.get("client_probe_reachable"),
        "post_workload_partition_recorded": truth(episode.get("post_workload_partition_recorded")),
        "recovery_recorded": truth(episode.get("recovery_recorded")),
        "recovery_error": episode.get("recovery_error"),
        "fault_summary_json": compact_json(episode.get("fault_summary")),
        "worker_health_json": compact_json(trial.get("worker_health")),
        "trial_extra_json": compact_json({key: value for key, value in trial.items() if key not in known_trial}),
        "control_setting": (control_metadata or {}).get("setting"),
        "control_table": (control_metadata or {}).get("table"),
        "control_timestamps_json": compact_json((control_metadata or {}).get("timestamps")),
        "control_metadata_json": compact_json(control_metadata),
    }
    for index, operation in enumerate(operations[:4], 1):
        flatten_operation(row, index, operation)
    if record_type != "main_trial":
        row["is_violation"] = ""
        row["is_no_violation_observed"] = ""
        row["is_inconclusive"] = ""
    return row


def response_records(response: Any) -> list[dict[str, Any]]:
    if not isinstance(response, dict):
        return []
    records = response.get("records", [])
    return [record for record in records if isinstance(record, dict)] if isinstance(records, list) else []


def control_trial(run: dict[str, Any], kind: str, item: dict[str, Any], index: int,
                  source_hash: str) -> tuple[dict[str, Any], dict[str, Any]]:
    case = item.get("case") or {}
    if kind == "read_repair_control":
        operations = response_records(item.get("write")) + response_records(item.get("first")) + response_records(item.get("second"))
        setting = case.get("setting")
        config = "ONE/QUORUM"
        control_metadata = {
            "setting": setting,
            "table": case.get("table"),
            "recovery_error": item.get("recovery_error"),
            "started_ns": item.get("started_ns"),
            "ended_ns": item.get("ended_ns"),
        }
        health = (item.get("first") or {}).get("health", [])
        source = run["directory"] / "read_repair.json"
    else:
        operations = response_records(item.get("result"))
        config = "ALL/ALL"
        control_metadata = {
            "table": case.get("table"),
            "timestamps": item.get("timestamps"),
        }
        health = (item.get("result") or {}).get("health", [])
        source = run["directory"] / "timestamp_control.json"
    attempt_id = case.get("attempt_id") or f"{kind}:{index}"
    synthetic = {
        "attempt": index + 1,
        "config": config,
        "coverage": {"evaluable": item.get("verdict") != "inconclusive"},
        "episode_id": attempt_id,
        "key": case.get("key"),
        "model": "",
        "operations": operations,
        "reason": item.get("reason"),
        "round": case.get("round"),
        "routing_policy": item.get("routing_policy"),
        "scenario": kind,
        "trial_id": f"{run['run_id']}:{attempt_id}",
        "verdict": item.get("verdict"),
        "worker_health": health,
    }
    return synthetic, {
        "experiment_type": kind,
        "source": source,
        "source_hash": source_hash,
        "metadata": control_metadata,
    }


def dynamic_run_fields() -> list[str]:
    fields = []
    for scenario in SCENARIOS:
        for outcome in OUTCOMES:
            fields.append(f"scenario_{scenario}_{outcome}")
    for model in MODELS:
        for outcome in OUTCOMES:
            fields.append(f"model_{model}_{outcome}")
    for config in CONFIGS:
        safe = config.lower().replace("/", "_")
        for outcome in OUTCOMES:
            fields.append(f"config_{safe}_{outcome}")
    return fields


RUN_FIELDS = [
    "export_schema", "setup", "design_id", "evidence_schema", "routing_policy_label", "run_id",
    "source_result_directory", "run_completed", "included_in_analysis", "validation_status",
    "validation_notes", "profile", "started_utc", "ended_utc", "duration_minutes", "root_seed",
    "git_revision", "git_status", "platform", "python_version", "docker_compose_version",
    "source_manifest_sha256", "configured_rounds", "configured_repetitions", "cluster_profile",
    "configured_nodes", "configured_scenarios",
    "configured_models", "configured_consistency_levels", "replication_factor", "hints_enabled",
    "expected_trials_from_plan", "declared_main_trials", "saved_main_trials", "trial_count_matches_plan",
    "trial_count_matches_completion", "unique_trial_ids", "unique_trial_keys", "violation_count",
    "no_violation_observed_count", "inconclusive_count", "other_verdict_count", "evaluable_count",
    "operation_error_inconclusive_count", "dependency_not_observed_count", "successor_not_observed_count",
    "other_reason_count", "total_operations", "successful_operations", "failed_operations",
    "operation_error_classes_json", "coordinator_node_counts_json", "multi_coordinator_trials",
    "network_partition_trials", "cross_partition_trials", "node_failure_trials",
    "trials_routed_to_failed_node", "fault_episode_count", "node_failure_episode_count",
    "network_partition_episode_count", "failed_node_counts_json", "isolated_node_counts_json",
    "read_repair_trial_count", "timestamp_control_trial_count", "total_exported_record_rows",
    "control_outcomes_json", "violation_trial_ids_json",
    "outcomes_by_cell_json", "completion_json", "environment_json", "plan_json",
    "completion_sha256", "environment_sha256", "plan_sha256", "trials_sha256", "faults_sha256",
] + dynamic_run_fields()


def run_row(run: dict[str, Any], trial_rows: list[dict[str, Any]], episodes: dict[str, dict[str, Any]],
            trials_hash: str, faults_hash: str) -> dict[str, Any]:
    completion = run["completion"]
    environment = run["environment"]
    plan = run["plan"]
    verdicts = Counter(outcome_key(row.get("trial_verdict")) for row in trial_rows)
    reasons = Counter(str(row.get("trial_reason") or "none") for row in trial_rows)
    op_errors = Counter()
    coordinators = Counter()
    total_operations = successful = failed = 0
    for row in trial_rows:
        total_operations += int(row.get("operation_count") or 0)
        successful += int(row.get("successful_operation_count") or 0)
        failed += int(row.get("failed_operation_count") or 0)
        for index in range(1, 5):
            error = row.get(f"op{index}_error_class")
            node = row.get(f"op{index}_routing_selected_node") or row.get(f"op{index}_node")
            if error:
                op_errors[str(error)] += 1
            if node:
                coordinators[str(node)] += 1
    cell = defaultdict(Counter)
    for row in trial_rows:
        cell[(row.get("scenario"), row.get("config_write_read"), row.get("model"))][outcome_key(row.get("trial_verdict"))] += 1
    cell_json = {
        "|".join(str(value) for value in key): dict(sorted(counts.items()))
        for key, counts in sorted(cell.items(), key=lambda item: tuple(str(value) for value in item[0]))
    }
    failed_nodes = Counter(ep.get("failed_node") for ep in episodes.values() if ep.get("failed_node"))
    isolated_nodes = Counter(ep.get("isolated_node") for ep in episodes.values() if ep.get("isolated_node"))
    control_outcomes = Counter(
        f"read_repair:{item.get('verdict') or 'missing'}"
        for item in run["read_repairs"] if isinstance(item, dict)
    )
    control_outcomes.update(
        f"timestamp_control:{item.get('verdict') or 'missing'}"
        for item in run["timestamps"] if isinstance(item, dict)
    )
    identifiers = [row.get("trial_id") for row in trial_rows]
    keys = [row.get("key") for row in trial_rows]
    database = plan.get("database") or {}
    cluster = plan.get("cluster") or {"profile": "three_node", "nodes": ["n1", "n2", "n3"]}
    row = {
        "export_schema": EXPORT_SCHEMA,
        "setup": run["setup"],
        "design_id": run["design_id"],
        "evidence_schema": run["evidence_schema"],
        "routing_policy_label": run["routing_policy_label"],
        "run_id": run["run_id"],
        "source_result_directory": relative(run["directory"]),
        "run_completed": truth(run["completed"]),
        "included_in_analysis": truth(run["eligible"]),
        "validation_status": "passed" if run["eligible"] else "excluded",
        "validation_notes": join_values(run["validation_notes"]),
        "profile": completion.get("profile") or plan.get("profile"),
        "started_utc": completion.get("started_utc") or environment.get("started_utc"),
        "ended_utc": completion.get("ended_utc") or completion.get("completed_utc"),
        "duration_minutes": completion.get("completion_time_minutes"),
        "root_seed": environment.get("root_seed") or plan.get("seed"),
        "git_revision": environment.get("git_revision"),
        "git_status": environment.get("git_status"),
        "platform": environment.get("platform"),
        "python_version": environment.get("python"),
        "docker_compose_version": environment.get("docker_compose"),
        "source_manifest_sha256": environment.get("source_manifest_sha256"),
        "configured_rounds": plan.get("rounds"),
        "configured_repetitions": plan.get("repetitions"),
        "cluster_profile": cluster.get("profile"),
        "configured_nodes": join_values(cluster.get("nodes", [])),
        "configured_scenarios": join_values(plan.get("scenarios", [])),
        "configured_models": join_values(plan.get("models", [])),
        "configured_consistency_levels": join_values(plan.get("consistency_configs", [])),
        "replication_factor": database.get("replication_factor"),
        "hints_enabled": truth(database.get("hints_enabled")),
        "expected_trials_from_plan": run["expected_trials"],
        "declared_main_trials": completion.get("main_trials"),
        "saved_main_trials": len(trial_rows),
        "trial_count_matches_plan": truth(run["expected_trials"] == len(trial_rows)) if run["expected_trials"] is not None else "",
        "trial_count_matches_completion": truth(completion.get("main_trials") == len(trial_rows)) if completion.get("main_trials") is not None else "",
        "unique_trial_ids": truth(len(identifiers) == len(set(identifiers))),
        "unique_trial_keys": truth(len(keys) == len(set(keys))),
        "violation_count": verdicts["violation"],
        "no_violation_observed_count": verdicts["no_violation_observed"],
        "inconclusive_count": verdicts["inconclusive"],
        "other_verdict_count": verdicts["other"] + verdicts["missing"],
        "evaluable_count": sum(row.get("coverage_evaluable") == "true" for row in trial_rows),
        "operation_error_inconclusive_count": reasons["operation_error"],
        "dependency_not_observed_count": reasons["dependency_not_observed"],
        "successor_not_observed_count": reasons["successor_not_observed"],
        "other_reason_count": sum(count for reason, count in reasons.items() if reason not in {"none", "operation_error", "dependency_not_observed", "successor_not_observed"}),
        "total_operations": total_operations,
        "successful_operations": successful,
        "failed_operations": failed,
        "operation_error_classes_json": compact_json(dict(sorted(op_errors.items()))),
        "coordinator_node_counts_json": compact_json(dict(sorted(coordinators.items()))),
        "multi_coordinator_trials": sum(row.get("changed_coordinator") == "true" for row in trial_rows),
        "network_partition_trials": sum(row.get("scenario") == "network_partition" for row in trial_rows),
        "cross_partition_trials": sum(row.get("crossed_partition_cut") == "true" for row in trial_rows),
        "node_failure_trials": sum(row.get("scenario") == "node_failure" for row in trial_rows),
        "trials_routed_to_failed_node": sum(row.get("routed_to_failed_node") == "true" for row in trial_rows),
        "fault_episode_count": len(episodes),
        "node_failure_episode_count": sum(ep.get("failed_node") is not None for ep in episodes.values()),
        "network_partition_episode_count": sum(
            ep.get("isolated_node") is not None or bool(ep.get("partition_groups"))
            for ep in episodes.values()),
        "failed_node_counts_json": compact_json(dict(sorted(failed_nodes.items()))),
        "isolated_node_counts_json": compact_json(dict(sorted(isolated_nodes.items()))),
        "read_repair_trial_count": len(read_json(run["directory"] / "read_repair.json", [])),
        "timestamp_control_trial_count": len(read_json(run["directory"] / "timestamp_control.json", [])),
        "total_exported_record_rows": len(trial_rows) + len(run["read_repairs"]) + len(run["timestamps"]),
        "control_outcomes_json": compact_json(dict(sorted(control_outcomes.items()))),
        "violation_trial_ids_json": compact_json([row.get("trial_id") for row in trial_rows if row.get("trial_verdict") == "violation"]),
        "outcomes_by_cell_json": compact_json(cell_json),
        "completion_json": compact_json(completion),
        "environment_json": compact_json(environment),
        "plan_json": compact_json(plan),
        "completion_sha256": sha256(run["directory"] / "completion.json"),
        "environment_sha256": sha256(run["directory"] / "environment.json"),
        "plan_sha256": sha256(run["directory"] / "plan.json"),
        "trials_sha256": trials_hash,
        "faults_sha256": faults_hash,
    }
    for scenario in SCENARIOS:
        subset = [item for item in trial_rows if item.get("scenario") == scenario]
        counts = Counter(outcome_key(item.get("trial_verdict")) for item in subset)
        for outcome in OUTCOMES:
            row[f"scenario_{scenario}_{outcome}"] = counts[outcome]
    for model in MODELS:
        subset = [item for item in trial_rows if item.get("model") == model]
        counts = Counter(outcome_key(item.get("trial_verdict")) for item in subset)
        for outcome in OUTCOMES:
            row[f"model_{model}_{outcome}"] = counts[outcome]
    for config in CONFIGS:
        subset = [item for item in trial_rows if item.get("config_write_read") == config]
        counts = Counter(outcome_key(item.get("trial_verdict")) for item in subset)
        safe = config.lower().replace("/", "_")
        for outcome in OUTCOMES:
            row[f"config_{safe}_{outcome}"] = counts[outcome]
    return row


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
            count += 1
    return count


def export(results: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    directories = sorted({path.parent for path in results.glob("**/completion.json")})
    runs = [run for directory in directories if (run := run_identity(directory)) is not None]
    trial_path = output / "trial_level_evidence.csv"
    run_path = output / "run_level_violation_matrix.csv"
    run_rows = []
    record_count = 0
    main_trial_count = 0
    record_type_counts = Counter()
    with trial_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRIAL_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for run in runs:
            episodes, faults_hash = episode_index(run["directory"])
            trials_hash = sha256(run["directory"] / "trials.json")
            repair_hash = sha256(run["directory"] / "read_repair.json")
            timestamp_hash = sha256(run["directory"] / "timestamp_control.json")
            rows = []
            for trial in run["trials"]:
                if not isinstance(trial, dict):
                    continue
                row = trial_row(run, trial, episodes.get(str(trial.get("episode_id")), {}), trials_hash, faults_hash)
                writer.writerow({field: row.get(field, "") for field in TRIAL_FIELDS})
                rows.append(row)
                record_count += 1
                main_trial_count += 1
                record_type_counts["main_trial"] += 1
            for index, item in enumerate(run["read_repairs"]):
                if not isinstance(item, dict):
                    continue
                synthetic, metadata = control_trial(run, "read_repair_control", item, index, repair_hash)
                row = trial_row(
                    run, synthetic, {}, trials_hash, faults_hash,
                    record_type="read_repair_control", experiment_type=metadata["experiment_type"],
                    source_record_file=metadata["source"], source_record_hash=metadata["source_hash"],
                    control_metadata=metadata["metadata"],
                )
                writer.writerow({field: row.get(field, "") for field in TRIAL_FIELDS})
                record_count += 1
                record_type_counts["read_repair_control"] += 1
            for index, item in enumerate(run["timestamps"]):
                if not isinstance(item, dict):
                    continue
                synthetic, metadata = control_trial(run, "timestamp_control", item, index, timestamp_hash)
                row = trial_row(
                    run, synthetic, {}, trials_hash, faults_hash,
                    record_type="timestamp_control", experiment_type=metadata["experiment_type"],
                    source_record_file=metadata["source"], source_record_hash=metadata["source_hash"],
                    control_metadata=metadata["metadata"],
                )
                writer.writerow({field: row.get(field, "") for field in TRIAL_FIELDS})
                record_count += 1
                record_type_counts["timestamp_control"] += 1
            run_rows.append(run_row(run, rows, episodes, trials_hash, faults_hash))
    write_csv(run_path, RUN_FIELDS, run_rows)
    manifest = {
        "export_schema": EXPORT_SCHEMA,
        "approved_evidence_families": [
            {"design_id": design, "evidence_schema": schema, **metadata}
            for (design, schema), metadata in APPROVED.items()
        ],
        "run_rows": len(run_rows),
        "record_rows": record_count,
        "main_trial_rows": main_trial_count,
        "record_type_counts": dict(sorted(record_type_counts.items())),
        "eligible_runs": sum(row["included_in_analysis"] == "true" for row in run_rows),
        "excluded_runs": sum(row["included_in_analysis"] != "true" for row in run_rows),
        "files": {
            trial_path.name: {"sha256": sha256(trial_path), "rows": record_count},
            run_path.name: {"sha256": sha256(run_path), "rows": len(run_rows)},
        },
    }
    (output / "export_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(export(args.results.resolve(), args.output.resolve()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
