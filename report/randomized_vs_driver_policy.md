# Previous randomized routing versus Cassandra driver-policy routing

## 1. Main difference

The two experiment designs differ mainly in **who selects the Cassandra coordinator**:

- In the previous setup, the experiment harness independently selected a random coordinator for every read and write.
- In the new setup, the Cassandra Python driver selects the coordinator using `TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc="dc1"))`.

## 2. Design comparison

| Area | Previous randomized setup | New driver-policy setup |
|---|---|---|
| Coordinator selection | The experiment harness randomly selected a node for every operation | The Cassandra Python driver selects the coordinator |
| Routing policy | Uniform and independent random selection | `TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc="dc1"))` |
| Client control | The test client effectively selected a random coordinator | The client supplies contact points and a routing key; the driver selects the coordinator |
| Consecutive operations | Frequently reached different nodes | Usually reached the same preferred replica |
| Partition-key handling | Token ownership did not affect coordinator selection | The routing key allows the driver to prefer replicas responsible for the key |
| Failed-node handling | The harness removed the stopped node from its candidate set | The driver uses its host and connection state to select an available coordinator |
| Network-partition handling | Every client operation could independently reach either partition side | The driver is unaware of the injected cut, but stable replica ordering usually keeps one history on one side |
| Retry policy | Controlled by the experiment implementation | `FallthroughRetryPolicy`; the driver does not retry a failed request automatically |
| Speculative execution | Disabled or absent | Explicitly disabled with `NoSpeculativeExecutionPolicy` |
| Realism | Synthetic randomized routing used for adversarial coverage | Closer to standard Cassandra application behavior |
| Cross-partition exposure | High because each operation was independently randomized | Very low because one routing key normally has a stable first replica |
| Ability to expose violations | Strong counterexample search | More realistic routing but weaker exposure to divergent partition components |
| Evidence schema | `randomized-cassandra-evidence-v3` | `cassandra-driver-policy-evidence-v4` |
| Result-directory prefix | `randomized_<run-id>` | `cassandra_policy_<run-id>` |

## 3. Previous randomized setup

- Every read and write independently sampled `n1`, `n2`, or `n3` from the client-reachable nodes.
- A logical client could write through `n1` and immediately read through `n3`.
- During a 2|1 network partition, successive operations frequently crossed between the majority and isolated components.
- This design provided strong coverage for stale reads, read regressions, and missing dependency-order witnesses.
- Across the 13 runs audited in `violation_matrix_v2.md`, 2,689 of 4,260 partition histories crossed the partition boundary.
- The setup observed violations of RYW, MR, MW, and WFR under weak consistency configurations.
- Its main limitation is that ordinary Cassandra applications normally allow the database driver to choose coordinators.

## 4. New Cassandra driver-policy setup

- Application operations use a normal Cassandra driver session.
- Every measured statement includes keyspace `lab` and the partition routing key.
- `TokenAwarePolicy` places replicas for the supplied key first in the query plan.
- The policy's default `shuffle_replicas=False` setting preserves a stable ordering of replicas for a key.
- Because successive operations in a history use the same key, they usually select the same first available replica.
- `DCAwareRoundRobinPolicy` restricts preferred coordinators to the configured local datacenter, `dc1`.
- During node failure, the driver selects a surviving coordinator based on its host and connection state.
- During a network partition, all three CQL endpoints remain client-reachable, but the coordinator may be unable to contact enough replicas for `QUORUM` or `ALL`.
- The latest driver-policy run recorded only 2 of 360 partition histories crossing the 2|1 cut.
- It observed zero violations, but the limited cross-partition exposure prevents a strong consistency conclusion.

## 5. Observed routing comparison

| Routing measurement | Previous pooled runs | New driver-policy run |
|---|---:|---:|
| Evidence runs | 13 | 1 |
| Main trials | 12,780 | 1,080 |
| Network-partition histories | 4,260 | 360 |
| Histories spanning both partition sides | 2,689 | 2 |
| Cross-partition rate | 63.12% | 0.56% |
| Partition histories using more than one coordinator | Frequent | 3 of 360 |
| Observed violations | 194 | 0 |
| Inconclusive histories | 5,549 across all three reason categories | 443 operation errors |

The previous inconclusive total contains operation errors, dependency-not-observed outcomes, and successor-not-observed outcomes. All 443 inconclusive outcomes in the new run were caused by operation errors.

## 6. What RF=3 means in both setups

The phrase “write to a node” refers to sending the request to a **coordinator**. It does not mean that Cassandra stores the mutation only on that coordinator.

The request flow in both experiment designs is:

```text
Application
    │
    ▼
Selected coordinator
    │
    ▼
Coordinator sends the mutation to the replicas
    │
    ▼
Consistency level determines how many responses are required
```

The database behavior is the same in both designs:

- The replication factor is 3.
- The cluster contains exactly three Cassandra nodes.
- Therefore, all three nodes are replicas for every experiment key.
- A coordinator normally forwards a write to all replicas that it can reach.
- The write consistency level controls how many acknowledgements are required before the client sees success.
- `ONE` requires one replica acknowledgement.
- `QUORUM` requires two replica acknowledgements.
- `ALL` requires acknowledgements from all three replicas.
- The read consistency level similarly controls how many replicas must participate in a read.

Consequently, the previous setup did not randomly choose the only node that would store the data. It randomly chose the coordinator that received the client request. Cassandra still controlled replica communication and storage.

### Normal operation

When all three replicas are reachable, a successful write is normally delivered to all three replicas even when the requested consistency level is `ONE`. The client can return after the required acknowledgement count is reached, while slower replica work may finish afterward.

The statement that data will “eventually replicate to all three nodes” is generally reasonable during healthy operation, but it is not an unconditional guarantee for every fault execution. During a failure or partition, some replicas may not receive the mutation.

This experiment disables hinted handoff. Therefore, a replica that misses a write is not guaranteed to receive it later through a stored hint. Convergence may instead require a successful read repair, explicit repair, or another later mutation.

## 7. What changed in the new setup

The replication factor, replica set, consistency levels, Cassandra write path, and Cassandra read path did not change. The changed component is the method used to select the **coordinator**.

### Previous setup

```text
Operation 1 → harness randomly chooses n1
Operation 2 → harness independently chooses n3
Operation 3 → harness independently chooses n2
```

- Every operation made a fresh independent coordinator choice.
- Operations on the same key frequently reached different coordinators.
- During a partition, one logical client could easily move between the majority and isolated sides.
- This made it more likely that the client would observe replicas with different versions of the data.

### New setup

```text
Operation 1 → driver prefers the first replica for key K
Operation 2 → driver usually prefers the same replica for key K
Operation 3 → driver usually prefers the same replica for key K
```

- The application provides the routing key but does not select a node.
- The driver calculates the replicas for that routing key.
- `TokenAwarePolicy` places those replicas first in its query plan.
- The default stable replica ordering normally gives the same key the same preferred coordinator.
- The driver changes coordinator when the preferred host is unavailable, is marked down, or cannot be used.

Because RF=3 equals the cluster size, every node is a replica. Token awareness does not reduce the replica set below three nodes, but the stable ordering still creates a strong preference for one coordinator for a particular key.

## 8. Expected experimental difference

| Scenario | Previous randomized coordinator | New driver-selected coordinator | Expected result difference |
|---|---|---|---|
| Normal operation | Operations move among healthy coordinators | Operations normally stay with one preferred coordinator | Both should usually show no violations because replicas can communicate and converge |
| One node stopped | Harness removes the stopped node and samples a survivor | Driver detects or skips the unusable host and selects a survivor | Similar consistency results: `ONE` and `QUORUM` can complete; `ALL` cannot |
| 2\|1 network partition | Successive operations frequently cross partition sides | Successive operations for one key normally stay on one side | New setup should expose far fewer stale or reordered observations |
| Coordinator on majority side | Randomly occurs per operation | Stable preferred coordinator may remain on majority side | `ONE` and `QUORUM` can usually complete |
| Coordinator on isolated side | Randomly occurs per operation | Stable preferred coordinator may remain isolated | `ONE` may complete locally; `QUORUM` and `ALL` fail |
| Cross-cut client history | Common | Rare | Previous setup has a much higher chance of producing a consistency violation witness |

The two designs should produce broadly similar **availability rules** because Cassandra quorum arithmetic did not change. They can produce very different **observed consistency results** because the route sequence determines whether a client sees divergent replicas.

## 9. Expected difference by consistency model

| Consistency model | Previous randomized setup | New driver-policy setup |
|---|---|---|
| Read-your-writes (RYW) | Frequently tested a write and later read through different coordinators | Usually performed the write and read through the same preferred replica |
| Monotonic reads (MR) | Successive reads could move from a current partition side to a stale side | Successive reads normally remained on the same coordinator |
| Monotonic writes (MW) | Predecessor and successor writes could reach different partition components | Both writes normally followed the same token-aware coordinator preference |
| Writes-follow-reads (WFR) | Dependency read, dependent write, and observer read frequently used different coordinators | The stable replica order usually kept the dependency history within one component |

### Read-your-writes

- A RYW violation requires a successful write followed by a read that does not return that write.
- Independent random routing makes it easier for the write and read to use different partition components.
- Stable driver routing makes the following read likely to return to the same coordinator and component as the write.
- Therefore, fewer RYW violations are expected in the new setup even though weak consistency still does not provide a universal RYW guarantee.

### Monotonic reads

- An MR violation requires the client to observe a newer value and later observe an older value.
- Random routing frequently moves the two reads between replicas with different states.
- Stable driver routing normally keeps both reads on the same preferred replica.
- Therefore, the new setup is less likely to expose read regression.

### Monotonic writes

- An MW witness requires an observer to see the successor write without seeing its predecessor.
- Independent routing makes it possible for predecessor and successor writes to reach different sides of a partition.
- Stable driver routing usually sends both writes through the same coordinator and reachable component.
- Therefore, the new setup is less likely to create or expose the required reordered visibility.

### Writes-follow-reads

- A WFR witness requires a client to read a dependency, issue a dependent write, and later expose the dependent write without the original dependency.
- Random routing gives each phase a greater chance of reaching a different component.
- Stable token-aware routing normally keeps the dependency chain on one preferred coordinator.
- Therefore, fewer WFR witnesses are expected in the new setup.

These expected reductions concern the probability of **observing a witness**. They do not convert weak consistency configurations into formal guarantees.

## 10. Fault-scenario interpretation

### Normal operation

- Both designs should normally complete operations without violations.
- All 360 normal histories in the new driver-policy run completed without a violation witness.

### Node failure

- With replication factor 3, the two surviving replicas can satisfy `ONE` and `QUORUM`.
- `ALL` cannot complete because it requires responses from all three replicas.
- The new driver-policy run did not select the stopped node as the actual coordinator for any measured operation.
- The 200 node-failure histories containing `ALL` were inconclusive because of expected unavailability.

### Network partition

- The previous setup frequently moved operations between the majority and isolated components, exposing divergent replica state.
- The new setup usually kept all operations for one key on the same preferred replica.
- `ALL` could not complete on either partition side.
- `QUORUM` could complete on the two-node side but not through a coordinator on the isolated side.
- Both cross-cut histories in the new run became inconclusive because a quorum operation failed.

## 11. Advantages and limitations

### Previous randomized setup

**Advantages**

- Strong coverage of different coordinators and partition components.
- Effective for finding counterexamples to client-centric consistency properties.
- Directly tests the effect of changing coordinators between operations.

**Limitations**

- The application harness controls coordinator selection more directly than a typical Cassandra application.
- Uniform independent routing does not reproduce the token-aware driver's normal preference for replicas.

### New driver-policy setup

**Advantages**

- Uses Cassandra's normal client-driver abstraction.
- Records the actual coordinator selected by the driver.
- Preserves token-aware, datacenter-aware, failure-aware routing behavior.
- Better represents how a typical application interacts with Cassandra.

**Limitations**

- Stable replica ordering produces little within-history coordinator diversity.
- Only 0.56% of partition histories crossed the partition boundary in the audited run.
- The run has little power to detect consistency violations requiring observations from divergent components.
- Increasing the trial count alone does not remove the structural preference for the same first replica.

## 12. Academic interpretation

- The previous experiment answers: **What can happen when successive client operations reach independently selected coordinators?**
- The new experiment answers: **What does a client observe when Cassandra's standard token-aware driver policy chooses coordinators?**
- The previous setup offers stronger adversarial coverage.
- The new setup offers stronger operational realism.
- The outcome counts should remain separate because the coordinator-selection policy changes the probability of observing divergent replicas.
- Zero violations in the new run means **no violation was observed along the routes that the driver selected**.
- It does not prove that Cassandra guarantees RYW, MR, MW, or WFR for every execution or consistency configuration.

## 13. Why token-aware routing is generally better

Token-aware routing is generally preferred because the client driver knows which Cassandra nodes store the partition being accessed. It can send the request directly to one of those replicas instead of choosing an unrelated coordinator.

### Main advantages

1. **Avoids an unnecessary network hop**

   - A non-token-aware client may send a request to a node that is not a replica for the key.
   - That coordinator must forward the request to the actual replicas.
   - A token-aware driver normally sends the request directly to a replica, avoiding this extra forwarding step.

2. **Reduces request latency**

   - Direct replica coordination usually requires less network communication.
   - Removing the extra coordinator-to-replica hop can reduce end-to-end read and write latency.
   - The improvement is more significant when nodes are separated by racks, availability zones, or datacenters.

3. **Reduces coordinator overhead**

   - A non-replica coordinator performs request parsing, replica discovery, forwarding, response collection, and result delivery without storing the requested partition locally.
   - Token-aware routing gives this work to a node already involved as a replica.
   - This reduces unnecessary CPU, connection, and network work across the cluster.

4. **Reduces internal network traffic**

   - Requests are less likely to travel through an unrelated Cassandra node before reaching the replicas.
   - Lower internal traffic leaves more capacity for replication, repair, compaction-related streaming, and application queries.

5. **Uses Cassandra's token-ring metadata**

   - The driver obtains token and topology metadata from Cassandra.
   - It hashes the statement's routing key and identifies the replicas responsible for that token.
   - Coordinator selection therefore reflects the actual data placement strategy.

6. **Combines with datacenter-aware routing**

   - This project wraps `DCAwareRoundRobinPolicy(local_dc="dc1")` inside `TokenAwarePolicy`.
   - The driver prefers a replica in the local datacenter.
   - This avoids unnecessary cross-datacenter coordination when a suitable local replica exists.

7. **Balances requests among relevant replicas**

   - Across many partition keys, different tokens map to different replica orderings.
   - Requests are distributed according to data ownership rather than through completely uninformed node selection.
   - The child policy provides fallback ordering when preferred replicas cannot be used.

8. **Responds to host availability**

   - The driver maintains host and connection state.
   - If a preferred replica is down or unusable, the query plan can move to another available host.
   - Applications do not need to maintain their own list of fault victims.

9. **Matches normal Cassandra application practice**

   - Applications ordinarily connect through a Cassandra driver instead of manually choosing a different node for every query.
   - Token-aware results therefore better represent production-style client behavior.

### Comparison

| Property | Non-token-aware routing | Token-aware routing |
|---|---|---|
| Knowledge of partition ownership | Does not use the statement's token to choose the coordinator | Uses the routing key and token metadata |
| Initial coordinator | May be an unrelated node | Normally one of the replicas for the key |
| Extra coordinator hop | Often required | Usually avoided |
| Internal network traffic | Higher | Usually lower |
| Coordinator work | May be performed by a node that does not store the partition | Usually performed by a relevant replica |
| Typical latency | May be higher | Usually lower |
| Datacenter locality | Depends on the underlying policy | Can combine replica awareness with local-datacenter preference |
| Production realism | Lower when the harness manually selects nodes | Higher for normal driver-based applications |
| Cross-node experiment coverage | Can be deliberately high | May repeatedly prefer the same replica for one key |

### Important limitation in this project

Token-aware routing is operationally better for typical Cassandra workloads, but “better” does not mean that it provides a stronger consistency level.

- Token awareness changes the coordinator-selection path.
- It does not change replication factor 3.
- It does not change the requested `ONE`, `QUORUM`, or `ALL` consistency level.
- It does not create formal RYW, MR, MW, or WFR guarantees.
- It can reduce the probability of observing a stale value because operations on one key often use the same preferred replica.
- That reduced observation probability must not be interpreted as a stronger database guarantee.

The performance advantage is also smaller in this particular deployment:

- The cluster has three nodes and RF=3.
- Every node is a replica for every experiment key.
- Therefore, even a randomly selected coordinator is already a replica.
- Token awareness cannot eliminate a non-replica coordinator hop because no non-replica Cassandra node exists in this topology.
- Its main observable effect here is stable coordinator preference for each key.

In a larger cluster where RF is lower than the number of nodes, token awareness provides a clearer routing advantage because many nodes do not store a given partition.

## 14. Related project evidence

- Previous pooled results: `report/violation_matrix_v2.md`.
- New driver-policy results: `report/violation_matrix_v3.md`.
- Previous configuration: `config/randomized_experiments.json`.
- New configuration: `config/cassandra_driver_experiments.json`.
- Driver-policy design: `docs/cassandra-driver-policy-plan.md`.
- New evidence run: `results/cassandra_policy_20260921T081729Z_000000000135283f/`.
