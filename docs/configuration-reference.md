# Cassandra driver-policy experiment configuration reference

The runner reads the file passed with `--config`, applies any command-line repetition override, and validates the complete effective configuration before starting Docker. Use `config/cassandra_driver_experiments.json` for the retained three-node deployment or `config/cassandra_driver_expanded_experiments.json` for the five-node deployment. Unknown routing policies, experiment/model/scenario values, duplicates, empty lists, unsupported deployment settings, and inconsistent options fail immediately.

## Default configuration

```json
{
  "design": "cassandra-driver-policy-v3",
  "cluster": {
    "profile": "three_node",
    "compose_file": "compose.yaml",
    "nodes": ["n1", "n2", "n3"]
  },
  "routing": {
    "policy": "token_aware_dc_aware",
    "local_dc": "dc1"
  },
  "seed": null,
  "repetitions": 100,
  "rounds": 100,
  "models": ["RYW", "MR", "MW", "WFR"],
  "consistency_configs": [
    "ONE/ONE", "ONE/QUORUM", "ONE/ALL",
    "QUORUM/ONE", "QUORUM/QUORUM", "QUORUM/ALL",
    "ALL/ONE", "ALL/QUORUM", "ALL/ALL"
  ],
  "scenarios": ["normal", "node_failure", "network_partition"],
  "enabled_experiments": [
    "session_guarantees",
    "node_failure",
    "network_partition",
    "read_repair",
    "timestamp_control"
  ],
  "faults": {
    "failure_detection_timeout_seconds": 90,
    "recovery_timeout_seconds": 600,
    "partition_stabilization_seconds": 15,
    "partition_hold_seconds": 15,
    "post_recovery_settle_seconds": 20,
    "cql_port": 9042,
    "internode_ports": [7000, 7001],
    "node_failure_count": 1,
    "partition_strategy": "isolate_one"
  },
  "database": {
    "replication_factor": 3,
    "read_repair_tables": {
      "blocking": "BLOCKING",
      "no_repair": "NONE"
    },
    "hints_enabled": false
  }
}
```

JSON keys and string values are case-sensitive. JSON does not allow comments or trailing commas.

## Top-level fields

### `design`

A nonempty design identifier saved in keys, evidence, and provenance. Letters, digits, hyphens, and underscores are appropriate; the normalized value must be a safe identifier. Change it when experiment semantics or the evidence schema change materially. Do not change it only to relabel old evidence.

Default: `cassandra-driver-policy-v3`.

### `cluster`

The cluster object selects the complete deployment profile:

| Field | Three-node profile | Expanded profile |
|---|---|---|
| `profile` | `three_node` | `five_node` |
| `compose_file` | `compose.yaml` | `compose.expanded.yaml` |
| `nodes` | `n1`, `n2`, `n3` | `n1`, `n2`, `n3`, `n4`, `n5` |

Old saved V4 plans without this object normalize to the three-node defaults. The Compose filename must identify a repository-root Compose YAML file, and node names must be unique safe service identifiers. The same node list controls client contact points, membership cardinality, fault rules, endpoint probes, and recovery.

### `routing`

The routing object is fixed for this design:

```json
{
  "policy": "token_aware_dc_aware",
  "local_dc": "dc1"
}
```

- `TokenAwarePolicy` uses the statement keyspace and partition routing key to prefer replicas.
- `DCAwareRoundRobinPolicy` orders hosts in the configured local datacenter and supplies fallback ordering.
- With RF=3 on three nodes, every node is a replica. With RF=3 on five nodes, each key has three replica nodes and two non-replica nodes; token-aware ordering therefore has a meaningful locality choice.
- The driver excludes hosts it considers down. The experiment controller never supplies a preferred coordinator.
- Retries and speculative execution remain disabled so one logical operation is not silently repeated elsewhere.

### `seed`

Either `null` or an integer.

- `null`: the runner obtains a new 64-bit root seed from operating-system randomness.
- Integer: the configured value is used unless `--seed` is supplied.
- `--seed N`: overrides the file for that invocation.

The runner derives independent case-order, fault-victim, and topology seeds using SHA-256 and saves them in `seeds.json`. Reusing a seed reconstructs those experiment choices. Coordinator selection is controlled by live driver policy state and is not seed-replayable. A seed also cannot reproduce Cassandra timing, failure-detection timing, or distributed responses exactly.

### `repetitions` and `rounds`

Both must be integers and must be equal. One round contributes one main attempt to every selected scenario/configuration/model cell.

- Full profile: minimum 10.
- Smoke profile: minimum 1 when `--smoke` is explicit.
- `--repetitions N`: sets both fields after reading the file.

The duplicate names are retained for compatibility, but they describe the same value. A mismatch is rejected.

### `models`

A nonempty, duplicate-free list chosen from:

| Value | Workload |
|---|---|
| `RYW` | One logical client writes `a=1`, then reads the row |
| `MR` | A producer writes `a=1`; one logical client reads twice |
| `MW` | One logical client writes predecessor `a=1`, then successor `b=1`; an observer reads both |
| `WFR` | A producer writes `a=1`; a dependent client reads `a`, writes `b=1`, and an observer reads both |

A full session-guarantee run must contain exactly all four models. A smoke run may select a subset to debug a specific workload.

### `consistency_configs`

A nonempty, duplicate-free list of `WRITE/READ` pairs. Each side must currently be one of `ONE`, `QUORUM`, or `ALL`.

Examples:

- `ONE/ONE`: weak write acknowledgement and weak read response;
- `QUORUM/ONE`: quorum write followed by single-replica-response read;
- `ONE/QUORUM`: weak write acknowledgement followed by quorum read;
- `QUORUM/QUORUM`: overlapping acknowledgement/response sets for RF=3; and
- `ALL/ALL`: all three replicas must respond to successful operations.

Order affects schedule construction before per-block shuffling but does not alter the required case set. Unsupported Cassandra consistency names are rejected rather than passed through silently.

### `scenarios`

A nonempty, duplicate-free list chosen from:

| Value | Behavior |
|---|---|
| `normal` | All nodes in the selected cluster profile are healthy |
| `node_failure` | Random Cassandra container is killed with SIGKILL and detected before measurement |
| `network_partition` | The configured partition strategy blocks all cross-group internode edges while retaining all CQL endpoints |

If `node_failure` is listed, `enabled_experiments` must contain `node_failure`. The same rule applies to `network_partition`.

### `enabled_experiments`

A nonempty, duplicate-free list chosen from:

| Value | Effect |
|---|---|
| `session_guarantees` | Runs the selected model/configuration/scenario main matrix |
| `node_failure` | Permits the node-failure main scenario |
| `network_partition` | Permits the partition main scenario |
| `read_repair` | Runs `BLOCKING` and `NONE` supplemental attempts |
| `timestamp_control` | Runs decreasing-timestamp controls |

Disabling `session_guarantees` makes the expected main count zero. Scenario values are still validated, and a listed fault scenario still requires its matching fault experiment flag. For a clear controls-only profile, remove fault scenarios that are not used and retain at least one valid scenario because configuration lists may not be empty.

## `faults` fields

### `failure_detection_timeout_seconds`

Maximum time to wait after SIGKILL for every surviving node to report the exact victim IP as down. The detector requires consecutive matching observations. A timeout is a setup failure; the block is not counted as a measured main attempt.

Default: 90 seconds.

Increase this on slow hosts. Reducing it can make valid Cassandra failure detection fail nondeterministically.

### `recovery_timeout_seconds`

Maximum time to wait for all configured nodes to return to healthy membership after restarting a victim or clearing a partition.

Default: 600 seconds.

This is a membership-readiness barrier for fresh-key experiments. It is not proof that every historical divergent replica value has converged.

### `partition_stabilization_seconds`

Delay after installing or changing partition rules and before measured operations.

Default: 15 seconds.

The runner also checks the intended rule graph and CQL reachability. This delay allows existing internode connections and failure views to react to the new graph. Keep one registered value for all measured attempts.

### `partition_hold_seconds`

Delay during the read-repair control after all Cassandra nodes are mutually cut and before the minority ONE write phase continues.

Default: 15 seconds.

This reduces ambiguity from old in-flight messages. It does not prove that the network has no buffered traffic.

### `cql_port`

Native Cassandra client port. The current Compose deployment and worker support exactly `9042`; any other value is rejected.

### `internode_ports`

Nonempty integer list of Cassandra internode ports blocked across a partition edge.

Default: `[7000, 7001]`.

The project creates bilateral rules matching source and destination ports for every cross-cut peer. Do not add CQL port 9042; the intended experiment keeps client access to both partition sides.

### `node_failure_count`

Must currently be `1`. A victim is sampled uniformly from the configured nodes. Supporting simultaneous node failures would require a separate detection and recovery oracle.

### `partition_strategy` and `partition_group_sizes`

- `isolate_one`: one seeded random node is isolated from all remaining nodes. This is the default for the retained three-node profile and produces a 1|2 cut.
- `balanced_random`: all configured nodes are shuffled with the fault RNG and split according to `partition_group_sizes`. The expanded profile uses `[2, 3]`, producing six bilateral cross-group edges per episode.

Both groups must be nonempty and their sizes must sum to the configured node count. The selected groups and exact rule graph are saved with each fault episode.

## `database` fields

### `replication_factor`

Both supplied profiles use exactly `3`. In the three-node profile every node stores every experiment key. In the five-node profile Cassandra places each key on three of the five nodes, allowing the experiment to observe replica-aware routing and partitions that split a key's replica set. The validator rejects other replication factors so the registered predictions remain tied to RF=3.

### `read_repair_tables`

The required mapping is:

```json
{
  "blocking": "BLOCKING",
  "no_repair": "NONE"
}
```

The main matrix uses table `blocking`. The focused control compares both tables. That specialized control currently requires the three-node profile, so it is omitted from the expanded configuration. Cassandra 5 stores `speculative_retry='NONE'` canonically as `NEVER`; schema inspection accounts for that representation.

### `hints_enabled`

Must be `false`. The Cassandra image disables hinted handoff so asynchronous catch-up does not erase controlled divergence during fault phases. This is an experiment setting, not a production recommendation. Supporting `true` would require a separate image/configuration and new predictions.

## Trial-count formulas

When `session_guarantees` is enabled:

```text
main = rounds × number of scenarios × number of consistency pairs × number of models
```

When `read_repair` is enabled:

```text
read_repair = rounds × number of read_repair_tables
```

When `timestamp_control` is enabled:

```text
timestamp = rounds
```

Current default:

```text
main        = 50 × 3 × 9 × 4 = 5,400
read repair = 50 × 2         =   100
timestamp   = 50             =    50
total                          5,550
```

Use `--plan-only` as the authoritative count check for an edited profile.

## Example: full submission profile

Use the default file and an explicit seed:

```sh
python3 scripts/run_randomized.py \
  --config config/cassandra_driver_experiments.json \
  --seed 20260927 \
  --plan-only

python3 scripts/run_randomized.py \
  --config config/cassandra_driver_experiments.json \
  --seed 20260927
```

Do not use `--smoke` for submission evidence.

## Example: targeted smoke profile

Copy the default JSON to a separately named file and edit only the diagnostic selections:

```json
{
  "design": "cassandra-driver-policy-v3",
  "routing": {
    "policy": "token_aware_dc_aware",
    "local_dc": "dc1"
  },
  "seed": 1001,
  "repetitions": 1,
  "rounds": 1,
  "models": ["RYW"],
  "consistency_configs": ["ONE/ONE", "QUORUM/QUORUM"],
  "scenarios": ["normal", "network_partition"],
  "enabled_experiments": ["session_guarantees", "network_partition"],
  "faults": {
    "failure_detection_timeout_seconds": 90,
    "recovery_timeout_seconds": 600,
    "partition_stabilization_seconds": 15,
    "partition_hold_seconds": 15,
    "cql_port": 9042,
    "internode_ports": [7000, 7001]
  },
  "database": {
    "replication_factor": 3,
    "read_repair_tables": {"blocking": "BLOCKING", "no_repair": "NONE"},
    "hints_enabled": false
  }
}
```

Run it only with `--smoke`:

```sh
python3 scripts/run_randomized.py \
  --config config/smoke-example.json \
  --smoke
```

This example schedules four main histories: 1 round × 2 scenarios × 2 consistency pairs × 1 model. It schedules no supplemental controls because they are not enabled.

## Common validation failures

| Message category | Cause | Correction |
|---|---|---|
| missing configuration fields | Required top-level field absent | Restore the field from the default schema |
| contains duplicates | Same model/scenario/pair/type repeated | Keep each selected item once |
| repetitions and rounds must match | Different values supplied | Set both to the same number or use `--repetitions` |
| full run requires at least 10 | Full invocation uses fewer rounds | Use 10+ or explicitly run a non-submission `--smoke` |
| submission profile must include all models | Full main profile omits a model | Restore RYW, MR, MW, and WFR |
| scenario requires experiment | Fault scenario listed but flag disabled | Enable the matching fault experiment or remove the scenario |
| deployment supports ... only | Config asks for unsupported RF/port/hints/schema | Use the fixed supported value or redesign all dependent layers |

Never bypass validation by editing the saved `plan.json`. The saved plan is evidence of what the runner accepted, not an input to retrofit after execution.
