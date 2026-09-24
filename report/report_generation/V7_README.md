# V7 report setup — Cassandra driver policy V4

This reporting setup is restricted to evidence schema `cassandra-driver-policy-evidence-v4` and design `cassandra-driver-policy-v3`.

## Analysis filter

A history contributes to the V7 aggregate only when all of the following hold:

- `evidence_schema == cassandra-driver-policy-evidence-v4`
- `record_type == main_trial`
- `included_in_analysis == true`
- `run_profile == full`

Incomplete and smoke-profile V4 runs remain in the run-level audit inventory but do not contribute to calculated results.

## Generated artifacts

| Artifact | Purpose |
|---|---|
| `../violation_matrix_v7.md` | Academic V4-only result matrix, interpretation, witness inventory, limitations, and detailed 108-cell outcome table. |
| `v7_analysis_summary.json` | Machine-readable V4-only aggregates and witness inventory. |
| `v7_assets/15_v4_outcomes_by_scenario.png` | Outcome composition for normal, node-failure, and network-partition scenarios. |
| `v7_assets/16_v4_model_violation_rates.png` | Evaluable violation rates for RYW, MR, MW, and WFR. |
| `v7_assets/17_v4_consistency_pair_rates.png` | Evaluable violation rates for all nine write/read consistency pairs. |
| `build_v7_report_assets.py` | Reproducible V7 matrix, summary, and chart generator. |

## Regenerate

Run from the repository root:

```bash
XDG_CACHE_HOME=/tmp MPLCONFIGDIR=/tmp/mpl-v7 \
  .venv/bin/python report/report_generation/build_v7_report_assets.py
```

The builder reads the normalized evidence CSVs and does not modify raw run evidence.

## Current frozen aggregate

- Included completed full-profile runs: **5**
- Main histories: **44,280**
- Evaluable histories: **26,160**
- Violations: **6**
- No violation observed: **26,154**
- Inconclusive: **18,120**

All six observed violations are RYW witnesses recorded during network partitions.
