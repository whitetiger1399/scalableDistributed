# Execution, fault injection, and evidence guide

This guide explains what the Cassandra driver-policy runner does and how to operate it. It contains no experiment outcomes.

## Lifecycle of a run

The runner creates a uniquely named `results/cassandra_policy_<UTC>_<seed>/` directory. It immediately writes an incomplete `completion.json`, the normalized plan, seed streams, environment details, source hashes, and a durable `events.jsonl` journal. A run remains incomplete unless every required phase finishes and its exact count checks pass.

The project lock prevents concurrent runners from injecting conflicting faults. The lock file may remain on disk; concurrency is controlled by the operating-system lock held on the file.

## Cluster startup and schema barrier

Docker Compose starts n1, then n2 after n1 is healthy, then n3 after n2 is healthy. The client container can start independently. The runner waits until every Cassandra observer sees three `UN` members before issuing schema operations.

The schema phase:

1. creates keyspace `lab` using `NetworkTopologyStrategy` and RF=3;
2. creates table `lab.blocking` with `read_repair=BLOCKING`;
3. creates table `lab.no_repair` with `read_repair=NONE`;
4. disables speculative retry for both tables;
5. reads release version, datacenter, rack, and host ID from every node;
6. reads keyspace replication and table options from every node; and
7. performs a native CQL readiness probe against every endpoint.

Existing `CREATE IF NOT EXISTS` objects are accepted only when inspection matches the expected table settings. Schema errors stop the run before measured histories.

## Cassandra driver coordinator routing

Every worker receives all configured contact points. The application API accepts a key, value, and consistency level but no node. For every measured operation, the Python driver chooses the coordinator with `TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc="dc1"))`.

Each statement sets keyspace `lab` and the encoded partition key as its routing key. The token-aware policy therefore prefers replicas, and the DC-aware child policy orders usable local hosts. Because RF=3 equals the three-node cluster size, all nodes are replicas for every experiment key. The driver—not the experiment controller—selects among hosts it considers available.

Each operation records:

- logical client ID and role;
- operation kind and sequence number;
- requested consistency level;
- policy name, local datacenter, operation index, driver-eligible hosts, attempted hosts, and selected coordinator;
- partition routing key;
- actual coordinator reported by the driver on success;
- query parameters, including the run-scoped key and mutation timestamp;
- wall-clock start/end values and monotonic duration; and
- returned value or exact error type/message.

Driver retries, consistency downgrades, and speculative execution are disabled. An operation is never rerouted because of its returned value or error.

## Main scenario round

Each round randomizes scenario order. Each scenario block creates one case for every selected consistency pair/model combination and shuffles those cases. All block keys are unique to the run, scenario, round, pair, and model.

Before a block, every key is initialized to `(a=0,b=0)` at consistency `ALL` while the cluster is healthy. The runner checks the exact number of initialization responses and requires every one to succeed. Initialization is setup evidence, not a measured application history.

### Normal operation

The runner immediately executes the shuffled histories against the healthy three-node cluster. It records every client-side endpoint probe and driver routing decision.

### Abrupt node failure

For every failure block:

1. sample one victim uniformly from n1, n2, and n3 using the fault RNG stream;
2. record its service name, container ID, IP, running state, and command start time;
3. execute `docker compose kill -s SIGKILL <victim>` without `nodetool drain`;
4. inspect the same stopped container and require `running=false`;
5. poll `nodetool status` through both survivors;
6. parse numeric membership addresses and require both survivors to report the exact victim IP as `DN`, with two remaining `UN` members, in consecutive observations;
7. start a new worker; its driver connects through the surviving contact points and excludes the stopped host;
8. execute and save all histories without retrying errors;
9. restart the same service with its persistent volume; and
10. wait until all observers report all three members `UN`.

If detection fails, the episode is a setup failure. The runner enters cleanup in `finally`, saves the incomplete episode and error, and does not manufacture measured trials.

This scenario represents an established Cassandra-process crash with retained storage. It does not represent disk loss, a lost physical host, graceful drain, or a crash precisely during an in-flight request.

### Internode network partition

For every partition block:

1. sample one isolated node uniformly;
2. inspect current container IPs;
3. create a project-only `LAB_FAULT` chain if absent;
4. place one jump to it at the beginning of each Cassandra container's `OUTPUT` chain;
5. add bilateral DROP rules for source and destination TCP ports 7000/7001 on both edges crossing the 2|1 cut;
6. require the saved blocked-peer graph and DROP-rule count to match the intended cut;
7. wait the configured stabilization interval;
8. prove that all three CQL endpoints remain reachable to the client;
9. save membership views and execute shuffled histories while the driver determines which of the three client-reachable nodes are eligible;
10. save post-workload rules and verbose packet counters;
11. delete only rules in `LAB_FAULT` and its project jump; and
12. verify three-node recovery.

The rules never block CQL port 9042 and never modify the host firewall. A coordinator on the isolated side may complete `ONE` but cannot reach a quorum. Cassandra or driver liveness state may affect later query plans; the controller never filters a host based on the intended partition side.

## Read-repair controls

For each round and table setting, the runner:

1. initializes one fresh key at ALL;
2. blocks every internode pair while keeping CQL access;
3. holds the full cut for the configured interval;
4. issues `a=1` at ONE through a driver-selected coordinator and records that selected node;
5. creates a random two-node component containing the write coordinator;
6. waits for stabilization and issues the first QUORUM read through a fresh driver query plan;
7. changes to an overlapping two-node component without a fully connected interval;
8. waits and issues the second QUORUM read through a fresh driver query plan;
9. records topology rules and post-workload counters; and
10. clears the partition and verifies recovery.

An attempt is evaluable only if both reads succeed and the first exposes `a=1`. The control records regression, no regression observed, or an inconclusive reason. Application reads are never forced to a component that can satisfy QUORUM.

## Timestamp control

For each round the runner initializes a fresh key, then independently routes:

1. ALL write `a=1` at timestamp `T+100`;
2. ALL write `a=2` at timestamp `T+50`; and
3. ALL read `a`.

This checks Cassandra's timestamp conflict resolution and is not pooled with the four client-centric model verdicts.

## Durable evidence files

| File | Contents |
|---|---|
| `plan.json` | Normalized effective configuration and profile |
| `seeds.json` | Root plus independently derived case-order, fault and topology streams |
| `environment.json` | Runtime commands/versions, git status, configuration, and source SHA-256 manifest |
| `initial_cluster.json` | Membership, schema operations/inspection, and CQL probes |
| `events.jsonl` | Append-only lifecycle journal flushed and fsynced after every event |
| `episode_<scenario>_<round>.json` | Per-main-block initialization, schedule, fault, histories, recovery, and errors |
| `trials.json` | Atomically checkpointed aggregate main histories |
| `faults.json` | Atomically checkpointed main episode records |
| `read_repair.json` | Atomically checkpointed supplemental repair attempts |
| `timestamp_control.json` | Atomically checkpointed timestamp controls |
| `completion.json` | Starts incomplete; changes to complete only after exact count checks |

Temporary `*.tmp` files are atomic-write intermediates. A partially written temporary file is not accepted by the verifier.

## Interruption and cleanup

The runner wraps every fault phase in cleanup logic. It also attempts global recovery when the top-level command exits with an exception or keyboard interruption. An uncatchable process kill, Docker-daemon failure, or host shutdown can prevent that cleanup, so run the explicit recovery command after Docker is available:

```sh
python3 scripts/run_randomized.py --recover
```

Recovery is idempotent and scoped to the project. It starts n1/n2/n3, removes project firewall rules, and waits for healthy membership. It does not delete volumes or evidence.

Never continue an interrupted result directory by manually adding JSON records. Start a new run after recovery. Preserve the incomplete directory because it documents the failed attempt.

## Verification and reporting boundary

The evidence verifier is intentionally separate from orchestration. It rebuilds expected case coverage from `plan.json`, rejects duplicate IDs/keys, checks initialization and every operation, recomputes verdicts, validates episode setup/recovery, and checks controls.

The report builder requires an explicit result path and invokes verification again. For a full report it also compares every recorded source hash with the current workspace. This prevents packaging edited code as though it produced older evidence.

A smoke report requires `--allow-smoke` and receives filenames beginning with `Smoke_Driver_Policy`. It is a pipeline QA artifact, not a submission report.

## Troubleshooting

### Docker command not found on macOS

Set both `DOCKER_BIN` and `COMPOSE_BIN` as shown in the README. The fault helper needs the Docker executable for inspection as well as the Compose executable for service operations.

### Cannot connect to Docker daemon

Start Docker Desktop and wait for the engine. Then run `--recover` before starting a new experiment. A run interrupted by daemon loss remains incomplete.

### Cluster does not become healthy

Inspect:

```sh
docker compose ps
docker compose logs n1 n2 n3
docker compose exec n1 nodetool status
```

Confirm Docker has enough memory. Do not reduce readiness requirements to make a failing cluster pass.

### Failure detection times out

Check the saved victim IP and survivor `nodetool status` observations in the episode file. On a slow host, increase `failure_detection_timeout_seconds` before a new registered run. Do not relabel a timeout episode as a node-failure measurement.

### Recovery times out

Run explicit recovery, inspect logs and membership, and start a new run. Recovery timeout means the next experiment block did not receive a valid healthy barrier.

### Verifier reports invalid evidence

Treat the verifier message as an evidence-integrity failure. Do not edit the saved evidence. Fix the cause and execute a new run. Common causes are incomplete runs, missing cases, altered source/evidence, failed cleanup, and mismatched control counts.

### Report builder says source differs

One or more hashed source, configuration, prediction, author, or documentation files changed after measurement. Restore the exact measured snapshot or perform a new full run from the intended final source. Do not add an override for submission generation.
