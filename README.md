# Cassandra client-centric consistency project

Three Cassandra 5.0.9 containers (one datacenter, replication factor 3), a Python client, controlled faults, raw histories, and a reproducible PDF report. Submission deadline: **27 September 2026**. Maximum group size: **three**.

## Reproduce

Prerequisites: Docker Engine/Desktop with Compose v2, about 8 GB assigned to Docker, 4 CPU cores, internet for initial image builds, and host Python 3.9+. The cluster publishes no host ports. Fault injection requires `NET_ADMIN` only inside the three lab containers.

```sh
export COMPOSE_BIN=/Applications/Docker.app/Contents/Resources/cli-plugins/docker-compose  # macOS if needed
export DOCKER_BIN=/Applications/Docker.app/Contents/Resources/bin/docker                    # macOS if needed
python3 scripts/run_randomized.py --plan-only
python3 scripts/run_randomized.py --config config/randomized_experiments.json
python3 -m venv .venv
.venv/bin/pip install -r requirements-report.txt
.venv/bin/python scripts/verify_randomized.py results/randomized_<run>
.venv/bin/python scripts/build_report.py --results results/randomized_<run>
python3 -m unittest discover -s tests -v
python3 scripts/run_randomized.py --recover
```

Initial startup is sequential and can take several minutes. The randomized default registers 600 main trials (10 rounds × 5 consistency configurations × 4 models × 3 scenarios), 20 read-repair trials and 10 timestamp controls. Each application read and write is routed independently by a random gateway; the application has no node argument. `--plan-only` validates the configuration and prints the exact counts without Docker. `--seed` enables replay of routing and case-order choices. `--repetitions N` changes the number of rounds, but N must be at least 10.

If a macOS Docker installation has a broken Compose plugin symlink but includes the executable, use:

```sh
export COMPOSE_BIN=/Applications/Docker.app/Contents/Resources/cli-plugins/docker-compose
export DOCKER_BIN=/Applications/Docker.app/Contents/Resources/bin/docker
```

For interrupted runs, `python3 scripts/run_randomized.py --recover` idempotently restarts all three nodes, removes this project's firewall rules, and verifies membership. The runner also heals faults in `finally` blocks and uses a project lock to reject concurrent controllers. `docker compose down` removes the lab containers/network but keeps database volumes. To reset the database deliberately, `docker compose down -v` deletes **this project's** volumes.

## Files

| File | Purpose |
|---|---|
| `compose.yaml`, `Dockerfile.*` | Reproducible deployment; base images pinned by digest |
| `src/worker.py` | Random-gateway operations, explicit CLs, CQL readiness probes, no retries |
| `src/checks.py` | Robust finite-history verdicts, reasons, and coverage |
| `scripts/run_randomized.py` | Parameterized runner, durable evidence, fault lifecycle and recovery |
| `scripts/build_plan_pdf.py` | Renders the detailed registered methodology to PDF |
| `scripts/verify_randomized.py` | Validates completed randomized-run evidence |
| `experiments/workloads/*.py` | Separate executable RYW, MR, MW and WFR histories |
| `experiments/configuration.py` | Shared validated configuration contract |
| `experiments/*.py` | Session, node-failure, partition, read-repair and timestamp definitions |
| `experiments/faults.py` | Project-scoped SIGKILL, iptables partition, detection and recovery |
| `scripts/lab.py` | Legacy runner; use only with the archived historical source |
| `report/predictions.md` | Predictions written before measurements |
| `scripts/build_report.py` | Generates PDF and Markdown directly from completed results |
| `results/<run>/trials.json` | Raw matrix histories; failures retained |
| `results/<run>/read_repair.json` | BLOCKING/NONE comparison |
| `results/<run>/timestamp_control.json` | Deliberately decreasing timestamp control |
| `results/<run>/faults.json` | Node status and packet-drop evidence |
| `results/<run>/environment.json` | Runtime versions and image metadata |

To validate old fixed-route evidence, run `python3 scripts/verify_results.py results/<run>`. To validate a completed redesigned run, run `python3 scripts/verify_randomized.py results/randomized_<run>`. The randomized verifier checks trial counts, at least ten attempts per case, fresh keys, operation order, random-routing metadata, and supplemental-control counts.

The detailed randomized protocol, trial accounting, coordinator-versus-replica distinction, node-failure procedure, network-partition rules, and acceptance checks are in [docs/randomized-experiment-plan.md](docs/randomized-experiment-plan.md). The redesigned runner atomically checkpoints every episode and supplemental attempt and appends a durable event journal. It records routing candidates, random draws, actual coordinators, logical clients, fault commands, membership views, packet counters, cleanup and recovery barriers.

The methodology is also available as [report/Randomized_Experiment_Plan.pdf](report/Randomized_Experiment_Plan.pdf). Edit `config/randomized_experiments.json` to select experiment types and scenarios. A full run rejects fewer than 10 repetitions. An explicit `--smoke --repetitions N` run may use fewer attempts and is labelled as a smoke profile rather than submission evidence.

## Interpretation

Configuration names are **write/read**, e.g. `QUORUM/ONE`. Trials cover read-your-writes (RYW), monotonic reads (MR), monotonic writes (MW), and writes-follow-reads (WFR). MW/WFR search for a visible successor without its predecessor in the same row; they do not reconstruct the complete replica execution order. Timeouts and unavailable operations are **inconclusive**, never counted as safety violations.

Hints are intentionally disabled to preserve divergent versions between controlled fault phases. No scheduled anti-entropy repair runs. These are experimental settings, not deployment recommendations. `read_repair=BLOCKING` is used in the main matrix; the focused control also uses `NONE`. A client session is a logical ordered history and may use several driver connections.

Before submission, fill in the course and up to three member names/IDs in `report/authors.json`, regenerate the report, and review the report and evidence as a group. AI assistance is disclosed in the report. Upload the PDF and the reproduction archive to Canvas; the scripts do not submit anything.
