# Cassandra driver-policy consistency experiments

## 1. Routing semantics

- The application API accepts keys, values and consistency levels; it has no node or coordinator parameter.
- The Python driver 3.29.2 selects coordinators with `TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc="dc1"))`.
- Every measured `SimpleStatement` carries keyspace `lab` and the encoded text partition key as its routing key.
- Token-aware routing prefers local replicas. With three nodes and RF=3, all three nodes are replicas for every experiment key.
- The DC-aware child policy orders usable local hosts and supplies fallback hosts.
- The experiment does not inspect a result and then reroute it.
- `FallthroughRetryPolicy` disables driver retries and `NoSpeculativeExecutionPolicy` disables duplicate speculative requests.
- Case order, fault victims and topology changes remain seeded; coordinator selection belongs to driver state and is not seed-replayable.

## 2. Evidence recorded per operation

- Policy name and local datacenter.
- Driver-visible eligible local hosts immediately before execution.
- Monotonic operation index within the worker.
- Partition routing key.
- Attempted hosts reported by the response future.
- Actual coordinator reported by the response future.
- Requested consistency level, query, parameters, timing, value or exact exception.
- Logical client, role and sequence position.

The evidence schema is `cassandra-driver-policy-evidence-v4`. Evidence from `randomized-cassandra-evidence-v3` is methodologically different and must not be merged with a driver-policy run.

## 3. Fault behavior

### Node failure

1. Initialize fresh keys at `ALL` while all replicas are healthy.
2. Randomly choose one Cassandra container and stop it with `SIGKILL`.
3. Require both survivors to report the victim down in consecutive membership observations.
4. Start a fresh worker. Its driver connects through the surviving contact points and marks the stopped host unavailable.
5. Execute the shuffled cases using driver-selected coordinators.
6. Expect `ONE` and `QUORUM` to remain available; expect every operation requiring `ALL` to fail or time out.
7. Restart the victim and require three healthy members before the next block.

### Network partition

1. Initialize fresh keys at `ALL` while healthy.
2. Randomly choose one node for the one-node component.
3. Block internode TCP 7000/7001 across the 2+1 cut while leaving CQL 9042 open.
4. Prove that all three CQL endpoints remain directly reachable from the client.
5. Start a fresh worker with all three contact points. Driver host and connection state determine query plans; the controller does not supply the isolated node to the driver.
6. Expect `ONE` to be able to complete on either side, `QUORUM` to complete only through a coordinator that can use the two-node component, and `ALL` to be unavailable.
7. Save firewall rules and packet counters, heal the cut and require recovery.

## 4. Interpretation

- A successful operation is classified from the returned values and acknowledged writes.
- `Unavailable`, timeout and connection failures are availability evidence and make the logical history inconclusive.
- A driver-selected coordinator change can expose stale state during a partition, but the experiment does not claim the coordinator served the value from its own local replica.
- Token awareness does not by itself provide session or causal consistency. It chooses a coordinator near a replica; Cassandra consistency level and replica reachability determine acknowledgement and read behavior.
- With RF=3 on a three-node cluster, every node is a replica, so token-aware preference cannot reduce the candidate replica set below the whole cluster. The experiment still reproduces the production control boundary: the application delegates coordinator selection to the driver.

## 5. Reproduction

```sh
python3 scripts/run_randomized.py \
  --config config/cassandra_driver_experiments.json \
  --seed 20260927 \
  --plan-only

python3 scripts/run_randomized.py \
  --config config/cassandra_driver_experiments.json \
  --seed 20260927
```

Validate only the resulting `results/cassandra_policy_<UTC>_<seed>/` directory:

```sh
python3 scripts/verify_randomized.py results/cassandra_policy_<UTC>_<seed>
```

## 6. Primary documentation

- [Python driver load-balancing policies](https://docs.datastax.com/en/developer/python-driver/3.29/api/cassandra/policies/)
- [Python driver statements and routing keys](https://docs.datastax.com/en/developer/python-driver/3.29/api/cassandra/query/)
- [Cassandra Dynamo architecture and tunable consistency](https://cassandra.apache.org/doc/5.0/cassandra/architecture/dynamo.html)
- [Cassandra read repair](https://cassandra.apache.org/doc/5.0/cassandra/managing/operating/read_repair.html)
