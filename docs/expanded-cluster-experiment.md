# Expanded five-node Cassandra experiment

## Purpose

The earlier three-node design uses RF=3, so every Cassandra node is a replica for every experiment key. Token-aware routing has no non-replica node to avoid, and the saved runs show very few coordinator changes. This limits the schedules capable of exposing MR, MW, and WFR counterexamples.

The expanded profile increases topology diversity without changing the consistency-level matrix:

| Property | Retained profile | Expanded profile |
|---|---:|---:|
| Cassandra nodes | 3 | 5 |
| Replication factor | 3 | 3 |
| Replicas per key | 3 of 3 | 3 of 5 |
| Partition topology | Seeded 1\|2 | Seeded 2\|3 |
| Cross-cut edges | 2 | 6 |
| Routing policy | Token-aware/DC-aware | Token-aware/DC-aware |
| Main histories at 100 rounds | 10,800 | 10,800 |
| Read-repair control | Enabled | Disabled |
| Timestamp control | Enabled | Enabled |

The five-node profile should produce more variation in replica-aware query plans because the driver's three preferred replicas are now a subset of the five local hosts. The 2|3 partition also creates multiple possible replica distributions across the cut. This increases counterexample exposure; it does not make a violation inevitable.

## Files

- `compose.yaml`: retained three-node deployment.
- `config/cassandra_driver_experiments.json`: retained three-node experiment.
- `compose.expanded.yaml`: separate five-node deployment and volumes.
- `config/cassandra_driver_expanded_experiments.json`: expanded experiment.

The two Compose files have different project names. Stop the unused deployment so Docker does not run both clusters concurrently.

## Fault model

### Node failure

One victim is sampled uniformly from the five configured services. The runner records its container identity and IP, sends `SIGKILL`, and waits until all four survivors report that exact IP as `DN` in consecutive observations. After the episode, it restarts the same container and waits until every observer sees five `UN` members.

Because RF remains 3, a failed node is not necessarily a replica for every trial key. This is expected and represents a real distributed placement effect. Replica membership is recorded per operation.

### Network partition

For every partition episode, the seeded fault RNG shuffles the five nodes and divides them into groups of two and three. The controller installs bilateral `DROP` rules for TCP ports 7000 and 7001 on every cross-group edge. Port 9042 remains reachable from the client container.

Before measurement, the runner checks:

- both groups cover all configured nodes without overlap;
- every node has the expected number of blocked peers;
- every peer contributes source-port and destination-port rules; and
- all five CQL endpoints remain reachable.

The saved evidence contains the two groups, blocked-peer map, installed rules, membership views, client probes, and post-workload packet counters.

## Routing evidence

Every measured operation records:

- `eligible_nodes`: live local-DC hosts known to the driver;
- `replica_nodes`: Cassandra metadata's RF=3 replica set for the operation's partition key;
- `selected_node`: actual coordinator chosen by the driver;
- `selected_is_replica`: whether the coordinator owns a replica for that key; and
- `attempted_nodes`: driver hosts attempted by the request future.

Use these fields to compare violations with coordinator changes, replica changes, and partition-side crossings. A larger cluster should not be described as providing weaker consistency by itself; it changes the schedules and placements sampled by the experiment.

## Commands

Validate the expanded full plan without Docker:

```sh
python3 scripts/run_randomized.py \
  --config config/cassandra_driver_expanded_experiments.json \
  --seed 20260927 \
  --plan-only
```

Run a one-round integration smoke test:

```sh
python3 scripts/run_randomized.py \
  --config config/cassandra_driver_expanded_experiments.json \
  --smoke \
  --repetitions 1 \
  --seed 1001
```

Run the full experiment:

```sh
python3 scripts/run_randomized.py \
  --config config/cassandra_driver_expanded_experiments.json \
  --seed 20260927
```

Recover the five-node deployment after interruption:

```sh
python3 scripts/run_randomized.py \
  --config config/cassandra_driver_expanded_experiments.json \
  --recover
```

Validate a completed V5 run:

```sh
python3 scripts/verify_randomized.py results/cassandra_policy_<expanded-run-id>
```

## Interpretation rules

- Compare the four models using evaluable histories; keep unavailable and timeout histories in a separate availability denominator.
- Stratify results by consistency pair, partition-side crossing, coordinator change, and replica-set relation.
- Do not pool three-node V4 and five-node V5 histories into one rate without retaining deployment profile as a factor.
- Absence of MR, MW, or WFR violations remains finite negative evidence, not proof of a guarantee.
- More violations in the expanded profile would show greater counterexample exposure under that topology, not that adding nodes directly weakens Cassandra's consistency levels.
