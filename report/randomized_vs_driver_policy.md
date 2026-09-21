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

## 6. Effect on consistency-model testing

| Consistency model | Previous randomized setup | New driver-policy setup |
|---|---|---|
| Read-your-writes (RYW) | Frequently tested a write and later read through different coordinators | Usually performed the write and read through the same preferred replica |
| Monotonic reads (MR) | Successive reads could move from a current partition side to a stale side | Successive reads normally remained on the same coordinator |
| Monotonic writes (MW) | Predecessor and successor writes could reach different partition components | Both writes normally followed the same token-aware coordinator preference |
| Writes-follow-reads (WFR) | Dependency read, dependent write, and observer read frequently used different coordinators | The stable replica order usually kept the dependency history within one component |

## 7. Fault-scenario interpretation

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

## 8. Advantages and limitations

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

## 9. Academic interpretation

- The previous experiment answers: **What can happen when successive client operations reach independently selected coordinators?**
- The new experiment answers: **What does a client observe when Cassandra's standard token-aware driver policy chooses coordinators?**
- The previous setup offers stronger adversarial coverage.
- The new setup offers stronger operational realism.
- The outcome counts should remain separate because the coordinator-selection policy changes the probability of observing divergent replicas.
- Zero violations in the new run means **no violation was observed along the routes that the driver selected**.
- It does not prove that Cassandra guarantees RYW, MR, MW, or WFR for every execution or consistency configuration.

## 10. Related project evidence

- Previous pooled results: `report/violation_matrix_v2.md`.
- New driver-policy results: `report/violation_matrix_v3.md`.
- Previous configuration: `config/randomized_experiments.json`.
- New configuration: `config/cassandra_driver_experiments.json`.
- Driver-policy design: `docs/cassandra-driver-policy-plan.md`.
- New evidence run: `results/cassandra_policy_20260921T081729Z_000000000135283f/`.
