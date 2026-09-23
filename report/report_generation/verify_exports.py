#!/usr/bin/env python3
"""Reconcile generated report CSVs with their manifest and each other."""

from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


def main() -> None:
    manifest = json.loads((HERE / "export_manifest.json").read_text())
    trial_path = HERE / "trial_level_evidence.csv"
    run_path = HERE / "run_level_violation_matrix.csv"
    expected_trial_hash = manifest["files"][trial_path.name]["sha256"]
    expected_run_hash = manifest["files"][run_path.name]["sha256"]
    assert sha256(trial_path) == expected_trial_hash, "trial CSV hash differs from manifest"
    assert sha256(run_path) == expected_run_hash, "run CSV hash differs from manifest"

    run_rows = list(read_csv(run_path))
    assert len(run_rows) == manifest["run_rows"]
    runs = {row["run_id"]: row for row in run_rows}
    assert len(runs) == len(run_rows), "run IDs are not unique"

    record_counts = Counter()
    main_trial_counts = Counter()
    record_type_counts = Counter()
    outcomes = defaultdict(Counter)
    trial_ids = defaultdict(set)
    record_rows = 0
    for row in read_csv(trial_path):
        record_rows += 1
        run_id = row["run_id"]
        assert run_id in runs, f"trial references absent run: {run_id}"
        record_counts[run_id] += 1
        record_type_counts[row["record_type"]] += 1
        if row["record_type"] == "main_trial":
            main_trial_counts[run_id] += 1
            outcomes[run_id][row["trial_verdict"]] += 1
        assert row["trial_id"] not in trial_ids[run_id], f"duplicate trial ID in {run_id}"
        trial_ids[run_id].add(row["trial_id"])
        assert row["design_id"] == runs[run_id]["design_id"]
        assert row["evidence_schema"] == runs[run_id]["evidence_schema"]
        assert row["included_in_analysis"] == runs[run_id]["included_in_analysis"]

    assert record_rows == manifest["record_rows"]
    assert sum(main_trial_counts.values()) == manifest["main_trial_rows"]
    assert dict(sorted(record_type_counts.items())) == manifest["record_type_counts"]
    for run_id, run in runs.items():
        assert record_counts[run_id] == int(run["total_exported_record_rows"])
        assert main_trial_counts[run_id] == int(run["saved_main_trials"])
        assert outcomes[run_id]["violation"] == int(run["violation_count"])
        assert outcomes[run_id]["no_violation_observed"] == int(run["no_violation_observed_count"])
        assert outcomes[run_id]["inconclusive"] == int(run["inconclusive_count"])

    eligible = sum(row["included_in_analysis"] == "true" for row in run_rows)
    assert eligible == manifest["eligible_runs"]
    assert len(run_rows) - eligible == manifest["excluded_runs"]
    print(json.dumps({
        "valid": True,
        "run_rows": len(run_rows),
        "record_rows": record_rows,
        "main_trial_rows": sum(main_trial_counts.values()),
        "record_type_counts": dict(sorted(record_type_counts.items())),
        "eligible_runs": eligible,
        "excluded_runs": len(run_rows) - eligible,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
