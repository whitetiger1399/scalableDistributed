# Cassandra client-centric consistency project

This project studies client-centric consistency in a replicated Apache Cassandra 5.0.9 cluster. It tests read-your-writes (RYW), monotonic reads (MR), monotonic writes (MW), and writes-follow-reads (WFR) under normal operation, an abrupt Cassandra-node failure, and an internode network partition.

The application never chooses a Cassandra node. It submits a read or write to a customer-facing client API, and the Cassandra Python driver's `TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc="dc1"))` selects the coordinator. Every measured statement supplies its partition routing key. Cassandra then chooses the replicas involved in the request. With three nodes and replication factor 3, every node stores a replica; `ONE`, `QUORUM`, and `ALL` control the number of required replica responses, not a specific storage node.

The current three-node full plan contains 11,100 attempts:

- 10,800 main histories: 100 rounds × 3 scenarios × 9 write/read consistency pairs × 4 models;
- 200 read-repair attempts: 100 using `BLOCKING` and 100 using `NONE`; and
- 100 decreasing-timestamp controls.

No result is accepted merely because the runner exits. A separate verifier checks exact coverage, initialization, operation order, driver-policy evidence, routing keys, actual coordinators, consistency levels, fault evidence, cleanup, controls, and recomputed verdicts. The report builder accepts only explicit, complete, verified evidence.

## Repository layout

| Path | Purpose |
|---|---|
| `compose.yaml` | Three Cassandra services and one client service on a private Docker network |
| `compose.expanded.yaml` | Separate five-node Cassandra deployment with its own Compose project and volumes |
| `Dockerfile.cassandra` | Pinned Cassandra 5.0.9 image, `iptables`, and hints-disabled experiment setting |
| `Dockerfile.client` | Pinned Python client and cassandra-driver 3.29.2 |
| `config/cassandra_driver_experiments.json` | Main driver-policy experiment configuration |
| `config/cassandra_driver_expanded_experiments.json` | Five-node/RF=3 exposure experiment with seeded 2|3 partitions |
| `config/randomized_experiments.json` | Historical uniform-random-routing configuration; incompatible with the new evidence schema |
| `experiments/configuration.py` | Shared configuration validation and count calculation |
| `experiments/workloads/` | Separate RYW, MR, MW, and WFR operation schedules |
| `experiments/faults.py` | SIGKILL, failure detection, partition rules, cleanup, and recovery |
| `experiments/read_repair.py` | Read-repair control schedule and topology choices |
| `experiments/timestamp_control.py` | Decreasing-timestamp control schedule |
| `src/routing.py` | Evidence recorder for eligible, replica, attempted, and selected coordinator hosts |
| `src/worker.py` | Customer API, CQL transport, schema checks, and operation recording |
| `src/checks.py` | Finite-history verdicts, reason codes, and coverage fields |
| `scripts/run_randomized.py` | Planner and experiment runner |
| `scripts/verify_randomized.py` | Independent evidence validator |
| `scripts/build_report.py` | Verified-evidence PDF/Markdown report and reproduction archive builder |
| `tests/` | Classifier, configuration, routing, fault-parser, and verifier tests |
| `docs/cassandra-driver-policy-plan.md` | Current driver-policy rationale and protocol |
| `docs/expanded-cluster-experiment.md` | Five-node rationale, fault topology, evidence fields, commands, and interpretation rules |
| `docs/randomized-experiment-plan.md` | Historical uniform-random-routing protocol |
| `docs/configuration-reference.md` | Every configuration field, allowed value, and effect |
| `docs/execution-guide.md` | Operational phases, fault injection, recovery, and troubleshooting |
| `report/predictions.md` | Predictions registered before a measured run |
| `report/authors.json` | Course and group-member information used by the report |
| `results/cassandra_policy_<run>/` | One immutable evidence directory per driver-policy run |

The old fixed-coordinator and uniform-random artifacts are retained for provenance. Do not use `scripts/lab.py` with the redesigned worker, and do not combine evidence schema v3 with driver-policy evidence schema v4.

## Prerequisites

- Docker Engine or Docker Desktop with Compose v2;
- approximately 8 GB memory for the three-node profile, or 10–12 GB for the five-node profile, and four CPU cores allocated to Docker;
- internet access for the first image build;
- Python 3.9 or newer on the host;
- about 2 GB free disk space for images, raw evidence, rendered pages, and archives; and
- permission for Docker containers to use `NET_ADMIN`. This capability is granted only to the three lab Cassandra containers and is used only for their project-scoped `LAB_FAULT` chains.

The cluster publishes no database port to the host. The client runs inside the Compose network. Do not run two experiment controllers against the same cluster; the runner enforces a project lock.

### macOS Docker paths

If `docker` and the Compose plugin are not on `PATH`, define both executable locations before running project commands:

```sh
export DOCKER_BIN=/Applications/Docker.app/Contents/Resources/bin/docker
export COMPOSE_BIN=/Applications/Docker.app/Contents/Resources/cli-plugins/docker-compose
```

Start Docker Desktop and wait until its engine reports ready. On Linux or a standard Docker installation, leave these variables unset.

## One-time host setup

Create a report environment and install the pinned report dependencies:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-report.txt
```

The experiment client dependency is installed inside `Dockerfile.client`; it does not need to be installed in the host environment.

Run the local tests before using Docker:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

These tests validate code behavior using synthetic fixtures. They are not database measurements and cannot replace a Cassandra run.

## Prepare a measured run

Complete these steps before starting Cassandra. The runner records SHA-256 hashes of the source and documentation, and the report builder refuses to package changed source with old measurements.

1. Fill in `report/authors.json` with the course and up to three group members.
2. Review and finalize `report/predictions.md` before viewing new outcomes.
3. Review `config/cassandra_driver_experiments.json` and the field-by-field [configuration reference](docs/configuration-reference.md).
4. Ensure the working source, instructions, predictions, and configuration are the exact versions to accompany the evidence.
5. Do not edit hashed source files between the measured run and report generation. If a code, configuration, prediction, author, or documented-method change is required, create a new run afterward.

Validate the full plan without starting Docker:

```sh
python3 scripts/run_randomized.py \
  --config config/cassandra_driver_experiments.json \
  --seed 20260927 \
  --plan-only
```

Expected planning counts are 10,800 main, 200 read-repair, 100 timestamp, and 11,100 total attempts. `--plan-only` validates only the plan; it does not build containers or contact Cassandra.

## Choose the cluster profile

Cluster size is selected by the configuration file. The runner reads `cluster.nodes` and `cluster.compose_file`, then applies the same list to startup, client contact points, health checks, fault injection, recovery, and evidence.

Use the retained three-node/RF=3 setup:

```sh
python3 scripts/run_randomized.py \
  --config config/cassandra_driver_experiments.json \
  --seed 20260927
```

Use the expanded five-node/RF=3 setup:

```sh
python3 scripts/run_randomized.py \
  --config config/cassandra_driver_expanded_experiments.json \
  --seed 20260927
```

The expanded Compose file has a separate project name and persistent volumes. Stop the other profile before starting a run to avoid consuming memory with both clusters:

```sh
docker compose -f compose.yaml down
docker compose -f compose.expanded.yaml down
```

The expanded profile uses five Cassandra nodes but keeps RF=3. Each key therefore has three replicas and two non-replica nodes. Its seeded `balanced_random` fault divides the cluster into random groups of two and three nodes for each partition episode. All six cross-group internode edges are blocked bilaterally while CQL remains reachable. The operation evidence records `replica_nodes`, `selected_node`, and `selected_is_replica` so routing changes can be separated from replica placement.

This profile increases opportunities to observe coordinator changes and split replica sets. It cannot guarantee violations: a violation still requires the right replica placement, coordinator sequence, successful operations, and timing. The expanded profile omits the specialized three-node read-repair control because that control's two-node quorum-component topology is defined only for three nodes.

## Optional integration smoke run

Use a smoke run after changing orchestration, Docker images, fault handling, or report code. It exercises the real cluster with fewer repetitions and is labelled `profile: smoke`:

```sh
python3 scripts/run_randomized.py \
  --config config/cassandra_driver_experiments.json \
  --smoke \
  --repetitions 1 \
  --seed 1001
```

`--smoke` is the only mode that permits fewer than ten attempts per case. Smoke evidence is not assignment evidence. The report builder refuses it unless `--allow-smoke` is supplied explicitly for QA:

```sh
.venv/bin/python scripts/build_report.py \
  --results results/cassandra_policy_<smoke-run> \
  --allow-smoke
```

Never rename a smoke directory or edit its `plan.json` to make it appear to be a full run.

## Run the full experiment

Use an explicit seed so the intended case order, routes, fault victims, and topology choices can be audited:

```sh
python3 scripts/run_randomized.py \
  --config config/cassandra_driver_experiments.json \
  --seed 20260927
```

The runner performs these phases:

1. build and start the images and containers;
2. wait until all three Cassandra nodes report healthy membership;
3. create and inspect the keyspace and tables on every node;
4. run the configured shuffled scenario rounds, with successful ALL initialization before each block;
5. for a node-failure block, sample a victim, send SIGKILL, prove that exact container stopped, wait for both survivors to report its IP down, run the block, restart the same container, and verify recovery;
6. for a partition block, sample one isolated node, add bilateral internode DROP rules while retaining CQL access, verify the intended 2|1 graph, run the block, record packet counters, remove only project rules, and verify recovery;
7. run the `BLOCKING` and `NONE` read-repair controls through seeded overlapping quorum components while the driver chooses coordinators;
8. run the decreasing-timestamp controls; and
9. write a completion marker only after all expected attempts exist.

Schema creation is idempotent. After cluster health is established, the runner retries schema
creation and inspection up to ten times at three-second intervals to allow startup schema
agreement to settle. Every response is retained in `initial_cluster.json`; if all attempts fail,
the runner writes `schema_failure.json` and reports the failing nodes, queries, values, and errors.

The runner prints line-oriented progress to the terminal. Each line shows a progress bar,
overall percentage and completed/total attempt count, followed by the current experiment,
scenario or setting, round, and completion verdict where applicable. Main session-guarantee
progress advances after each 20-case scenario batch; read-repair and timestamp-control progress
advance after every attempt. Setup, fault detection, and recovery messages retain the current
percentage because they do not count as measured attempts. Example:

```text
[progress] [#-----------------------------]   1.95% (108/5550) | session_guarantees | finished scenario=node_failure, round=1/50, saved_trials=36
```

The evidence journal remains available for monitoring from another terminal without modifying files:

```sh
tail -f results/cassandra_policy_<run>/events.jsonl
```

To count durably saved main histories:

```sh
jq length results/cassandra_policy_<run>/trials.json
```

Do not stop a run merely because an operation returns `Unavailable`, times out, or produces an unexpected value. Those are measured outcomes. Stop only for operational reasons; interrupted or setup-failed runs remain incomplete and must not be reported as complete.

## Recover after interruption

If a run is interrupted, Docker exits, or the host restarts, start Docker and run:

```sh
python3 scripts/run_randomized.py \
  --config config/cassandra_driver_experiments.json \
  --recover
```

Recovery starts all three Cassandra containers, removes only rules in the project `LAB_FAULT` chain, and waits for all three nodes to return to healthy membership. It does not change an incomplete run into a complete run and does not delete its partial evidence.

If the incomplete run has a complete main phase, resume its remaining read-repair and timestamp controls with the saved plan and seed:

```sh
python3 scripts/run_randomized.py \
  --resume results/cassandra_policy_<incomplete-run>
```

Resume performs project-scoped recovery, validates all main checkpoints, retains the ordered valid control prefix, archives any invalid tail, restores the topology RNG from the saved seed and retained choices, and continues at the first missing or invalid control attempt. It refuses an incomplete main phase, a completed run, mismatched IDs, duplicate checkpoints, or inconsistent seeds. Do not combine `--resume` with configuration, seed, repetition, smoke, plan, or recovery overrides.

If `.cassandra-policy-run.lock` exists after a crash, it is not sufficient evidence that a controller is active: the operating-system lock, rather than the file's existence, controls concurrency.

## Validate evidence

Always pass the exact result directory. The verifier never selects a “latest” run:

```sh
python3 scripts/verify_randomized.py \
  results/cassandra_policy_<full-run>
```

A valid full run must have:

- `completed: true` and the supported evidence schema;
- exactly ten histories for every selected scenario/configuration/model cell;
- unique trial IDs and run-scoped keys;
- successful, matching ALL initialization;
- ordered operations with the requested consistency levels and logical-client IDs;
- one auditable driver-policy decision per operation, including routing key, eligible hosts, attempted hosts, and actual coordinator;
- recomputed verdicts, reasons, and coverage equal to stored values;
- exact fault-episode coverage, victim/partition proof, and recovery evidence;
- the configured number of attempts per read-repair setting; and
- the configured number of timestamp controls.

The verifier exits nonzero and prints `INVALID:` when any requirement fails. Do not edit raw JSON to make a failed run pass. Correct the implementation or environment and perform a new run.

## Build the PDF and reproduction archive

Generate the submission artifacts only from a verified full run:

```sh
.venv/bin/python scripts/build_report.py \
  --results results/cassandra_policy_<full-run>
```

The builder verifies the evidence again, checks that every source hash matches the measured source, and writes:

- `report/Driver_Policy_Cassandra_Consistency_Report.pdf`;
- `report/Driver_Policy_Cassandra_Consistency_Report.md`;
- `report/driver_policy_SHA256SUMS.txt`;
- `report/driver_policy_submission.zip`; and
- rendered PDF pages under `report/qa_driver_policy/` for visual inspection.

Inspect every rendered page, check member/course information, and review the interpretation as a group. The archive contains the selected run, code, configuration, experiment modules, tests, predictions, documentation, author metadata, report, and checksum manifest.

## Shut down or reset the lab

Stop and remove containers and the project network while preserving Cassandra volumes:

```sh
docker compose down
```

On macOS with the explicit Compose executable:

```sh
"$COMPOSE_BIN" -f compose.yaml down
```

Delete the three project data volumes only when a deliberate clean reset is required:

```sh
docker compose down -v
```

`down -v` permanently deletes the lab's Cassandra data. Result directories and reports in the workspace are not Docker volumes and are not removed.

## Configuration overview

The default file is `config/cassandra_driver_experiments.json`. JSON does not support comments; keep explanations in documentation. Important relationships are:

- `repetitions` and `rounds` must be equal;
- a full profile requires at least 10 and all four consistency models;
- a smoke profile may use fewer repetitions and a subset of models;
- scenario names, model names, experiment names, and consistency levels are case-sensitive;
- `node_failure` and `network_partition` scenarios require their matching experiment type to be enabled;
- the current Docker deployment intentionally supports only RF=3, CQL port 9042, hints disabled, and the two declared read-repair tables; and
- unsupported settings fail before Docker starts rather than being silently ignored.

See [docs/configuration-reference.md](docs/configuration-reference.md) for examples of a full profile, a quick smoke profile, enabling/disabling experiment families, seed behavior, timing fields, validation errors, and trial-count formulas.

## Interpretation boundaries

Configuration notation is **write consistency/read consistency**, for example `QUORUM/ONE`. A successful quorum write and quorum read overlap for RF=3, but overlap alone does not prove general causal consistency.

RYW and MR compare observed versions of cell `a`. MW and WFR use predecessor cell `a` and successor cell `b` and search for a visible successor without its predecessor. This is an observable counterexample test; it does not reconstruct every replica's internal application order. A “no violation observed” outcome is a finite observation, not a proof. Operation errors and unmet prerequisites are inconclusive and are also availability evidence.

The deployment uses three containers on one physical host, one datacenter, RF equal to node count, disabled hints, sequential single-writer histories, and controlled faults. It does not establish multi-host failure independence, multi-datacenter behavior, concurrent-writer semantics, permanent storage loss, or horizontal throughput scalability.

## Submission checklist

- [ ] No more than three group members are listed.
- [ ] Predictions and configuration were frozen before the measured run.
- [ ] The full run has at least ten attempts per required case.
- [ ] `scripts/verify_randomized.py` accepts the selected full run.
- [ ] The PDF was generated from that explicit run and every page was inspected.
- [ ] The report explains architecture, versions, installation, settings, predictions, design, node failure, partition injection, results, limitations, sources, and AI assistance.
- [ ] The reproduction archive extracts successfully and its SHA-256 manifest is checked.
- [ ] Group members reviewed the code and interpretations.
- [ ] The PDF and reproduction archive are uploaded to Canvas by 27 September 2026.

The scripts do not upload files or submit to Canvas.
