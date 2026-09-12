# Cassandra client-centric consistency project

Three Cassandra 5.0.9 containers (one datacenter, replication factor 3), a Python client, controlled faults, raw histories, and a reproducible PDF report. Submission deadline: **27 September 2026**. Maximum group size: **three**.

## Reproduce

Prerequisites: Docker Engine/Desktop with Compose v2, about 8 GB assigned to Docker, 4 CPU cores, internet for initial image builds, and host Python 3.9+. The cluster publishes no host ports. Fault injection requires `NET_ADMIN` only inside the three lab containers.

```sh
python3 scripts/lab.py up
python3 scripts/lab.py run --repeats 5
python3 -m venv .venv
.venv/bin/pip install -r requirements-report.txt
.venv/bin/python scripts/build_report.py
python3 -m unittest discover -s tests -v
python3 scripts/lab.py down
```

Initial startup is sequential and can take several minutes. The full experiment includes ten read-repair trials with network transitions and also takes several minutes. `run` creates a fresh UTC-stamped results directory and unique keys; earlier results are retained. Report generation selects the latest **completed** run. Pass `--results results/<run>` to select another run. The generator validates the saved histories and renders every PDF page into `report/qa/` for visual review.

If a macOS Docker installation has a broken Compose plugin symlink but includes the executable, use:

```sh
export COMPOSE_BIN=/Applications/Docker.app/Contents/Resources/cli-plugins/docker-compose
```

For interrupted runs, `python3 scripts/lab.py heal` restarts n3 and removes this project's firewall rules. `down` removes the lab containers/network but keeps database volumes. It does not touch unrelated containers. To reset the database deliberately, `docker compose down -v` deletes **this project's** volumes. Do not run experiments concurrently against the same lab.

## Files

| File | Purpose |
|---|---|
| `compose.yaml`, `Dockerfile.*` | Reproducible deployment; base images pinned by digest |
| `src/worker.py` | Coordinator-pinned CQL operations, explicit CLs, no driver retries |
| `src/checks.py` | Finite-history violation checks |
| `scripts/lab.py` | Startup, SIGKILL, storage-port partitions, recovery and evidence |
| `report/predictions.md` | Predictions written before measurements |
| `scripts/build_report.py` | Generates PDF and Markdown directly from completed results |
| `results/<run>/trials.json` | Raw matrix histories; failures retained |
| `results/<run>/read_repair.json` | BLOCKING/NONE comparison |
| `results/<run>/timestamp_control.json` | Deliberately decreasing timestamp control |
| `results/<run>/faults.json` | Node status and packet-drop evidence |
| `results/<run>/environment.json` | Runtime versions and image metadata |

To validate saved evidence independently of Docker, run `python3 scripts/verify_results.py results/<run>`. It checks trial counts, unique keys, successful initialization, sequential timing, requested consistency levels and recalculated verdicts.

## Interpretation

Configuration names are **write/read**, e.g. `QUORUM/ONE`. Trials cover read-your-writes (RYW), monotonic reads (MR), monotonic writes (MW), and writes-follow-reads (WFR). MW/WFR search for a visible successor without its predecessor in the same row; they do not reconstruct the complete replica execution order. Timeouts and unavailable operations are **inconclusive**, never counted as safety violations.

Hints are intentionally disabled to preserve divergent versions between controlled fault phases. No scheduled anti-entropy repair runs. These are experimental settings, not deployment recommendations. `read_repair=BLOCKING` is used in the main matrix; the focused control also uses `NONE`. A client session is a logical ordered history and may use several driver connections.

Before submission, fill in the course and up to three member names/IDs in `report/authors.json`, regenerate the report, and review the report and evidence as a group. AI assistance is disclosed in the report. Upload the PDF and the reproduction archive to Canvas; the scripts do not submit anything.
