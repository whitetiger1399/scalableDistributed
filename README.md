# Cassandra client-centric consistency project

## What this project is about

This project studies **client-centric consistency** in a replicated Apache Cassandra 5.0.9 cluster. A client that writes a value and later reads it (possibly through a different coordinator) may or may not see its own or a monotonic view of the data, depending on the write/read consistency levels and on faults in the cluster. We measure when those guarantees hold and when they break.

The application never picks a database node. It submits a read or write to a client API, and the Cassandra Python driver's `TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc="dc1"))` chooses the coordinator. With three nodes and replication factor 3, every node holds a replica, so `ONE`, `QUORUM`, and `ALL` control how many replicas must respond — not which node is used.

## What we are testing

Four client-centric consistency models:

| Model | Meaning | Workload |
|---|---|---|
| RYW | Read-your-writes | One client writes `a=1`, then reads the row |
| MR | Monotonic reads | A producer writes `a=1`; one client reads twice |
| MW | Monotonic writes | One client writes `a=1` then `b=1`; an observer reads both |
| WFR | Writes-follow-reads | A producer writes `a=1`; a client reads `a`, writes `b=1`; an observer reads both |

Each model runs under **9 write/read consistency pairs** (every combination of `ONE`, `QUORUM`, `ALL`) and **3 scenarios**: normal operation, an abrupt node failure (SIGKILL), and an internode network partition. Two supplemental controls also run: a `BLOCKING` vs `NONE` read-repair comparison, and a decreasing-timestamp control.

A run produces three kinds of outcome per history: **violation** (a concrete counterexample to the model), **no_violation_observed** (finite evidence of no break), or **inconclusive** (an operation failed or a prerequisite was not met — availability evidence, never counted as a violation).

## Setup / architecture

- **Cluster:** three Cassandra 5.0.9 containers on a private Docker network (`compose.yaml`), one datacenter `dc1`, `NetworkTopologyStrategy` RF=3. Hinted handoff is disabled so faults produce observable divergence.
- **Client:** a separate container (`Dockerfile.client`) with `cassandra-driver` 3.29.2. It runs inside the Compose network; no database port is published to the host.
- **Faults:** node failure via `docker compose kill -s SIGKILL`; network partition via a project-scoped `iptables LAB_FAULT` chain that drops internode ports 7000/7001 while keeping CQL 9042 reachable.

### Repository layout

| Path | Purpose |
|---|---|
| `compose.yaml`, `Dockerfile.*` | Three-node cluster + client container |
| `config/cassandra_driver_experiments.json` | The experiment configuration |
| `experiments/` | Config validation, workloads (RYW/MR/MW/WFR), fault injection, controls |
| `src/` | Client API/transport (`worker.py`), consistency oracles (`checks.py`), routing evidence (`routing.py`) |
| `scripts/run_randomized.py` | Runner (plan, run, recover, resume) |
| `scripts/verify_randomized.py` | Independent evidence validator |
| `scripts/run_blocks.sh` | Optional block-by-block runner |
| `tests/` | Unit tests (synthetic fixtures, no database) |
| `results/<run>/` | One immutable evidence directory per run |

## Prerequisites

- Docker Engine or Docker Desktop with Compose v2, ~8 GB memory and 4 CPU cores.
- Python 3.9+ on the host.
- Docker containers must be allowed `NET_ADMIN` (used only by the three lab containers for the `LAB_FAULT` chain).

All commands below run from the repository root. On this setup the project lives under WSL, so run them inside a WSL/Linux shell.

## How to run the code, step by step

### Step 1 — Run the unit tests (no Docker)

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

These check the code logic against synthetic fixtures. They do not measure a real cluster.

### Step 2 — Validate the plan (no Docker)

```sh
python3 scripts/run_randomized.py \
  --config config/cassandra_driver_experiments.json \
  --seed 20260927 \
  --plan-only
```

Prints the planned attempt counts and validates the configuration. It does not build containers or contact Cassandra. With the default 100-round config this is 10,800 main + 200 read-repair + 100 timestamp = 11,100 attempts.

### Step 3 — Smoke run (real cluster, few repetitions)

Use this to confirm Docker, the cluster, and fault injection all work before a long run:

```sh
python3 scripts/run_randomized.py \
  --config config/cassandra_driver_experiments.json \
  --smoke --repetitions 1 --seed 1001
```

Smoke evidence is for QA only, not for the report. Do not treat a `profile: smoke` run as submission evidence.

### Step 4 — Full run

```sh
python3 scripts/run_randomized.py \
  --config config/cassandra_driver_experiments.json \
  --seed 20260927
```

The runner builds the images, starts the cluster, checks health and schema, then runs the shuffled scenario rounds (with node-failure and partition episodes), the read-repair controls, and the timestamp controls, writing evidence to `results/cassandra_policy_<UTC>_<seed>/`. A completion marker is written only after all expected attempts exist.

Do not stop the run because an operation returns `Unavailable` or times out — those are valid measured outcomes. Monitor progress from another terminal with:

```sh
tail -f results/cassandra_policy_<run>/events.jsonl
```

### Step 5 — Verify the evidence

Always pass the exact result directory (the verifier never picks a "latest" run):

```sh
python3 scripts/verify_randomized.py results/cassandra_policy_<run>
```

It recomputes every verdict and checks coverage, routing evidence, fault proof, and counts. It prints `INVALID:` and exits nonzero on any problem. Do not edit saved evidence to make it pass — fix the cause and run again.

### If a run is interrupted

Restart the cluster and clear project firewall rules (idempotent, safe to repeat):

```sh
python3 scripts/run_randomized.py --config config/cassandra_driver_experiments.json --recover
```

If the main phase completed but the controls did not, continue them without repeating main histories:

```sh
python3 scripts/run_randomized.py --resume results/cassandra_policy_<incomplete-run>
```

### Shut down the lab

```sh
docker compose down       # stop containers, keep data volumes
docker compose down -v     # also delete Cassandra data (destructive)
```

## Reading the results

Each `results/<run>/` directory contains:

- `completion.json` — final counts, verdict tallies, timing, and `completed: true/false`;
- `trials.json` — every main history with its verdict, reason, and coverage;
- `faults.json` — per-episode fault, detection, and recovery evidence;
- `read_repair.json`, `timestamp_control.json` — control outcomes;
- `plan.json`, `seeds.json`, `environment.json` — the exact config, random streams, and provenance;
- `events.jsonl` — append-only lifecycle journal.

Notation is **write/read**, e.g. `QUORUM/ONE`. A `no_violation_observed` result is a finite observation, not a proof of a universal guarantee. The deployment uses three containers on one host with RF=3 and hints disabled, so it does not model independent-machine failures, multiple datacenters, concurrent writers, or throughput scaling.

## Notes on the results directories

`results/` may contain runs from two routing designs, distinguished by the `evidence_schema` in each run's `completion.json`:

- `cassandra-driver-policy-evidence-v4` — the current design (driver `TokenAwarePolicy` chooses the coordinator), directories named `cassandra_policy_*`.


