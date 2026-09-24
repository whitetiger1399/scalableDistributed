# Report evidence exports

This folder contains the report-generation plan and normalized evidence for the approved Cassandra driver-policy experiment families. Historical harness-randomized results are excluded from these exports.

| Setup | Design ID | Evidence schema |
|---|---|---|
| Three-node token-aware driver | `cassandra-driver-policy-v3` | `cassandra-driver-policy-evidence-v4` |
| Five-node expanded token-aware driver | `cassandra-driver-policy-expanded-v1` | `cassandra-driver-policy-evidence-v5` |

No other design or evidence schema is exported.

## Files

| File | Purpose |
|---|---|
| `REPORT_GENERATION_ACTION_PLAN.md` | Reviewed plan for completing the academic report. |
| `trial_level_evidence.csv` | One row for every saved main history, read-repair control, and timestamp control, including records from partial runs. |
| `run_level_violation_matrix.csv` | One row per run with metadata, outcome totals, per-scenario/model/configuration columns, and a complete cell matrix. |
| `export_manifest.json` | Approved evidence families, row counts, eligibility totals, and SHA-256 hashes. |
| `export_evidence.py` | Reproducible CSV generator. It reads `results/` and does not modify it. |
| `verify_exports.py` | Reconciles both CSVs and checks their hashes against the manifest. |

## Current export coverage

- Matching V4/V5 runs: **13**
- Total trial/control records in the frozen export: **54,465**
- Main client-centric trials: **53,172**
- Read-repair controls: **822**
- Timestamp controls: **471**
- Analysis-eligible completed full-profile runs: **7**
- Excluded incomplete or smoke-profile runs: **6**
- Main trials in the report aggregate: **50,760**

Partial and smoke-profile runs are intentionally retained for auditability. Report aggregates require `included_in_analysis=true`, `record_type=main_trial`, and `run_profile=full`.

## Trial-level schema

The trial CSV is organized into readable column groups.

### Evidence identity

- `export_schema`
- `setup`
- `design_id`
- `evidence_schema`
- `routing_policy_label`
- `run_id`
- Source result directory, source files, and SHA-256 hashes

These fields provide a complete route from a CSV row back to the saved JSON evidence.

`record_type` separates `main_trial`, `read_repair_control`, and `timestamp_control`. `experiment_type` identifies the main operating scenario or the specific control experiment. Only rows with `included_in_main_violation_matrix=true` belong in the client-centric violation matrix.

### Run metadata

- Completion and analysis-inclusion flags
- Structural validation status and exclusion reason
- Profile, start/end time, duration, seed, Git revision, platform, and Python version
- Configured rounds/repetitions, replication factor, and hinted-handoff setting

### Trial identity and outcome

- `trial_id`, `episode_id`, scenario, round, attempt, model, configuration, and key
- Separate write/read consistency levels
- Verdict, reason, and explicit violation/no-violation/inconclusive flags
- Canonical `outcome_class`; control outcomes use a `control_` prefix
- Oracle coverage flags

### Routing and availability summary

- Operation success/error counts and error classes
- Coordinator-node and endpoint sequence
- Distinct coordinator count and whether the history changed coordinators
- Whether a network-partition history crossed the configured cut (1|2 for V4 and 2|3 for V5)
- Whether a node-failure history routed to the failed node
- Trial timestamps and duration

### Fault metadata

- Episode timestamps and stabilization delay
- Failed or isolated node and majority-side nodes
- CQL client-probe counts
- Recovery and post-workload partition evidence flags
- Compact fault and health JSON fields

### Ordered operations

The maximum session history contains four operations. Columns prefixed with `op1_` through `op4_` preserve their order and include:

- Sequence, operation kind, role, logical client, consistency level, and status
- Error class/message, selected node, coordinator endpoint, and latency
- Start/end timestamps, query, parameters, returned value, and routing key
- Driver/harness routing policy and selected/candidate/eligible/attempted hosts
- Replica-set evidence and whether the selected coordinator is a replica (V5)
- An `extra_json` field for any unrecognized operation properties

Empty `op4_` fields are expected for two-operation and three-operation models.

## Run-level violation matrix schema

Each row represents one run ID. It includes:

- Complete source metadata from `completion.json`, `environment.json`, and `plan.json`
- Completion, inclusion, count, and identifier-integrity checks
- Total violation, no-violation-observed, and inconclusive counts
- Inconclusive reason and operation-exception breakdowns
- Coordinator, route-diversity, partition-crossing, and fault-target counts
- Fixed numeric columns for every scenario, model, and consistency configuration
- `outcomes_by_cell_json`, keyed as `scenario|write/read CL|model`, for the complete per-run matrix
- All violation trial IDs and hashes of the primary source files

The configuration notation is always **write consistency/read consistency**.

## Inclusion and validation semantics

`included_in_analysis=true` requires all of the following:

1. The design/evidence-schema pair is approved.
2. `completion.json` records `completed: true`.
3. Completion and environment identities agree.
4. Saved, declared, and plan-derived trial counts agree.
5. Trial IDs and trial keys are unique.
6. Every saved trial is a JSON object.

These are export-level structural checks. They do not replace the experiment-specific oracle and fault validator. The final report should additionally record the appropriate independent-validator result before freezing its run manifest.

## Regenerate

From the repository root:

```bash
python3 report/report_generation/export_evidence.py
python3 report/report_generation/verify_exports.py
```

Custom source and output directories can be supplied:

```bash
python3 report/report_generation/export_evidence.py \
  --results /path/to/results \
  --output /path/to/output
```

The exporter overwrites only its three generated artifacts: the two CSVs and `export_manifest.json`.

## Filtering examples

Completed full-profile evidence for report analysis:

```python
import pandas as pd

trials = pd.read_csv("report/report_generation/trial_level_evidence.csv", low_memory=False)
eligible = trials[
    (trials["included_in_analysis"] == True)
    & (trials["record_type"] == "main_trial")
    & (trials["run_profile"] == "full")
]
```

All violation traces from the token-aware setup:

```python
driver_violations = eligible[
    (eligible["setup"] == "cassandra_token_aware")
    & (eligible["trial_verdict"] == "violation")
]
```

Run-level result table:

```python
runs = pd.read_csv("report/report_generation/run_level_violation_matrix.csv", low_memory=False)
report_runs = runs[runs["included_in_analysis"] == True]
```

CSV fields can legally contain quoted line breaks from Cassandra exception messages, platform metadata, and saved JSON. Therefore, use a CSV parser rather than `wc -l` to determine row counts.
