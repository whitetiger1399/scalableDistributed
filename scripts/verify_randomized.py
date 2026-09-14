#!/usr/bin/env python3
"""Validate a completed randomized-run evidence directory."""
import argparse
import json
from collections import Counter
from pathlib import Path


def verify(run):
    plan = json.loads((run / "plan.json").read_text())
    completion = json.loads((run / "completion.json").read_text())
    trials = json.loads((run / "trials.json").read_text())
    expected = (len(plan["scenarios"]) * len(plan["consistency_configs"])
                * len(plan["models"]) * plan["rounds"])
    assert completion["completed"] is True
    assert completion["main_trials"] == expected == len(trials)
    assert plan["rounds"] >= 10
    assert plan["repetitions"] >= 10
    keys = Counter((t["scenario"], t["config"], t["model"]) for t in trials)
    assert all(count >= 10 for count in keys.values()), keys
    for trial in trials:
        operations = trial["operations"]
        assert operations
        assert trial["key"] in {p for op in operations for p in op["params"] if isinstance(p, str)}
        for before, after in zip(operations, operations[1:]):
            assert before["end_ns"] <= after["start_ns"]
        for operation in operations:
            assert "routing" in operation
            route = operation["routing"]
            assert route["selected_node"] in route["candidates"]
            assert route["draw"] >= 0
            assert operation["node"] == route["selected_node"]
            assert operation["start_ns"] <= operation["end_ns"]
    if "read_repair" in plan["enabled_experiments"]:
        assert completion["read_repair_trials"] >= 20
        assert len(json.loads((run / "read_repair_plan.json").read_text())) >= 20
    if "timestamp_control" in plan["enabled_experiments"]:
        assert completion["timestamp_trials"] >= 10
        assert len(json.loads((run / "timestamp_control_plan.json").read_text())) >= 10
    print(json.dumps({"main_trials": len(trials), "by_case": dict(keys),
                      "read_repair_trials": completion["read_repair_trials"],
                      "timestamp_trials": completion["timestamp_trials"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    verify(parser.parse_args().results)
