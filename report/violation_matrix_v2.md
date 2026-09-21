# Client-centric consistency outcome matrix — audited v2

## 1. Scope and headline result

- **Evidence set:** 13 completed runs using evidence schema `randomized-cassandra-evidence-v3`.
- **Main trials:** 12,780 randomized client histories across RYW, MR, MW and WFR.
- **Deployment:** three Cassandra replicas, one datacenter, `NetworkTopologyStrategy`, replication factor 3.
- **Routing:** every application operation independently selected a coordinator from the client-reachable candidate set.
- **Scenarios:** normal operation, one abrupt node failure, and a 2+1 internode network partition.
- **Matrix notation:** `write consistency/read consistency`.
- **Supplemental controls:** 250 read-repair and 125 timestamp trials were audited separately and are excluded from this matrix.

### Academic assessment

- [x] **Evidence completeness:** all 13 runs pass the independent verifier; scheduled case counts, unique keys, operation order, consistency levels, routing records, fault records and stored verdicts are valid.
- [x] **Results are meaningful:** violations occur only during network partitions and only where the tested consistency levels permit non-overlapping or causally unordered visibility.
- [x] **Availability results are expected:** `ALL` cannot complete with one of three replicas unavailable; `QUORUM` can complete on the two-node side but not through an isolated coordinator.
- [x] **Strong-overlap observation is expected:** no violation was observed for `QUORUM/QUORUM`; this is evidence for the tested histories, not proof of general causal consistency.
- [x] **Fault injection is supported by logs:** all partition episodes recorded reachable CQL endpoints, installed cuts, positive DROP counters and recovery; all node-failure episodes recorded a stopped victim, failure detection and recovery.
- [!] **One plausible outlier:** one `ONE/ONE` MR history under partition ended in a CL `ONE` read timeout. This is possible during transient partition/failure-detector activity, but it is not a deterministic quorum-unavailability result and should be identified as an isolated timeout.
- [!] **Inference limit:** `no_violation_observed` means the finite history did not contain the defined witness. It does not establish that Cassandra guarantees the model in all executions.

## 2. Experimental coverage and comparability

| Property | Audited value | Interpretation |
|---|---:|---|
| Completed main runs | 13/13 | No incomplete run contributes to the matrix. |
| Main trials | 12,780 | All expected trial identifiers and keys are present. |
| Node-failure episodes | 125/125 verified | Victim stopped, survivors detected failure, then all three recovered. |
| Partition episodes | 125/125 verified | Intended 2+1 cut, three client-reachable endpoints, packet drops and recovery recorded. |
| Partition trials spanning both sides | 2,689/4,260 (63.12%) | Random routing produced substantial cross-partition exposure. |
| Node-failure operations routed to victim | 0/12,780 | The client candidate set correctly removed the stopped endpoint. |
| Partition operations with all three candidates | 12,780/12,780 | The client could still choose either side of the database partition. |
| Verdict/oracle recomputation | 12,780/12,780 match | Stored classifications agree with `src/checks.py`. |
| Malformed/other outcomes | 0 | No result depends on malformed evidence or an unknown reason. |

### Pooling rules

- The four session workloads, verdict oracle, routing layer and worker have identical recorded SHA-256 hashes in all 13 runs.
- The runs span four Git revisions because orchestration and reporting changed; the measured workload and classification code remained identical.
- Five smoke runs used 1 round and 5 core configurations.
- One full run used 10 rounds and the same 5 core configurations.
- Six full runs used 10 rounds and all 9 configurations.
- The latest full run used 50 rounds and all 9 configurations.
- Therefore, each core matrix cell has 125 attempts, while each later-added configuration cell has 110 attempts. Raw counts must be interpreted with their cell totals.
- Trials within one fault episode share the same injected fault. The design contains 125 independent node-failure episodes and 125 independent partition episodes, not 4,260 independent fault injections.

## 3. Aggregate outcomes by scenario

| Scenario | viol | ok | inc:err | inc:dep | inc:succ | Total | Main interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
| Normal | 0 | 4,259 | 0 | 1 | 0 | 4,260 | Stable cluster; one WFR dependency read at weak consistency did not observe its producer write. |
| Node failure | 0 | 2,000 | 2,260 | 0 | 0 | Non-`ALL` histories completed; every history requiring `ALL` became unavailable. |
| Network partition | 194 | 778 | 3,038 | 90 | 160 | Weak successful histories exposed stale or reordered visibility; quorum/ALL requests often could not complete. |
| **All scenarios** | **194** | **7,037** | **5,298** | **91** | **160** | **12,780** | Availability and safety are reported separately. |

### Percentage view

- **Normal:** 99.98% `ok`, 0% violations, 0% operation errors.
- **Node failure:** 46.95% `ok`, 53.05% operation errors, 0% violations.
- **Network partition:** 4.55% violations, 18.26% `ok`, 71.31% operation errors, 2.11% dependency-not-observed and 3.76% successor-not-observed.
- **All trials:** 1.52% violations, 55.06% `ok`, and 43.42% inconclusive.
- The all-trial violation percentage is not a consistency guarantee rate: it includes normal executions and operations that could not complete.

## 4. Why 5,298 histories are inconclusive errors

### Error distribution

| Scenario/configuration pattern | `inc:err` | Expected? | Reason |
|---|---:|---|---|
| Normal operation | 0 | Yes | All replicas and coordinators were available. |
| Node failure, any config containing `ALL` | 2,260 | Yes | RF=3 and `ALL` requires acknowledgements/responses from all three replicas. |
| Node failure, only `ONE`/`QUORUM` | 0 | Yes | The two surviving replicas satisfy `QUORUM`; `ONE` needs one response. |
| Partition, any config containing `ALL` | 2,260 | Yes | Neither the two-node nor one-node component can reach all three replicas. |
| Partition, non-`ALL` configs containing `QUORUM` | 777 | Yes | A request coordinated on the isolated side cannot collect two replica responses. |
| Partition, `ONE/ONE` | 1 | Plausible outlier | One MR read timed out after receiving zero responses during a partition episode. |

### Logged exception evidence

- Node-failure error operations are `Unavailable` at consistency `ALL`.
- Partition errors are dominated by `Unavailable` at `ALL` or `QUORUM`.
- Partition logs also contain 23 read-timeout and 15 write-timeout operation records.
- Operation-error records can outnumber inconclusive histories because a multi-operation history can contain more than one failed request.
- A timeout is conservatively inconclusive: Cassandra may have applied a timed-out write on some replicas, so the experiment does not treat it as rolled back.
- These 5,298 histories measure the availability cost of stronger consistency during failure; they are neither violations nor successful consistency observations.

## 5. Client-centric model findings

| Model | Attempts | Operation errors | Other coverage exclusions | Witness-exposed histories | Violations | Violation rate among witness-exposed | Assessment |
|---|---:|---:|---:|---:|---:|---:|---|
| RYW | 3,195 | 1,286 | 0 | 1,909 | 92 | 4.82% | Expected failures under partition with weak/non-overlapping W/R. |
| MR | 3,195 | 1,333 | 88 first reads did not expose the new value | 1,774 | 43 | 2.42% | Regressions appear only with read `ONE`; none with read `QUORUM` or `ALL`. |
| MW | 3,195 | 1,313 | 108 successors not observed | 1,774 | 46 | 2.59% | Visible successor without predecessor occurs under weak writes/reads across partition sides. |
| WFR | 3,195 | 1,366 | 91 dependencies + 52 successors not observed | 1,686 | 13 | 0.77% | Completed witness appears only at `ONE/ONE`; stronger cases often unavailable or did not expose prerequisites. |

### Model-specific interpretation

- **RYW:** violations at `ONE/ONE`, `ONE/QUORUM` and `QUORUM/ONE` are expected because `W + R` is not greater than RF=3 in these cases. `QUORUM/QUORUM` has an overlap (`2 + 2 > 3`) and produced no witness.
- **MR:** all 43 regressions used read `ONE`. The absence of regressions with read `QUORUM` agrees with quorum overlap plus `BLOCKING` read repair for this workload.
- **MW:** quorum intersection alone does not create a general causal-order guarantee. The 15 `ONE/QUORUM` witnesses are meaningful: separate ONE writes can reach different replicas, and the final quorum read can expose the successor without the predecessor.
- **WFR:** a valid WFR witness requires the dependency read and successor to be observed. The 91 dependency and 52 successor exclusions prevent false violation claims.
- **No malformed outcomes:** all witnesses were computed from structurally valid, sequential operation histories.

## 6. Network-partition safety results

Only the network-partition scenario produced violations.

| Configuration (W/R) | viol | ok | Inconclusive | Evaluable (`viol + ok`) | Violation rate | Expected-behaviour assessment |
|---|---:|---:|---:|---:|---:|---|
| ONE/ONE | 123 | 237 | 140 | 360 | 34.17% | Expected: either operation may complete on either partition side. |
| ONE/QUORUM | 37 | 187 | 276 | 224 | 16.52% | Expected: `1 + 2 = 3` gives no strict acknowledgement/read overlap; quorum succeeds only on the majority side. |
| QUORUM/ONE | 34 | 195 | 271 | 229 | 14.85% | Expected: a ONE read may use the isolated stale side; quorum writes require the majority side. |
| QUORUM/QUORUM | 0 | 159 | 341 | 159 | 0% observed | Expected for successful histories because quorum sets intersect; finite evidence, not proof. |
| Any config containing ALL | 0 | 0 | 2,260 | 0 | N/A | Expected unavailability: the partition prevents contacting all replicas. |

### Exact violation cells

| Model | Configuration | Violations | Reason the witness is possible |
|---|---|---:|---|
| RYW | ONE/ONE | 51 | A write can be acknowledged on one side and the following read can use the stale side. |
| RYW | ONE/QUORUM | 22 | A ONE write need not be included in a successful majority-side quorum read. |
| RYW | QUORUM/ONE | 19 | A successful quorum write can be followed by a ONE read on the isolated stale replica. |
| MR | ONE/ONE | 28 | Two independent ONE reads can move from a newer side to a stale side. |
| MR | QUORUM/ONE | 15 | The producer write can reach a quorum while later ONE reads cross from current to stale visibility. |
| MW | ONE/ONE | 31 | The observer can see the successor write without the predecessor. |
| MW | ONE/QUORUM | 15 | Independent ONE writes do not impose causal visibility; a quorum read can merge an exposed successor with a missing predecessor. |
| WFR | ONE/ONE | 13 | The dependency was observed before the successor write, but a later ONE observer saw only the successor. |

## 7. Random-routing and fault evidence

### Coordinator selection under partition

| Operation | n1 | n2 | n3 | Total | Assessment |
|---|---:|---:|---:|---:|---|
| Reads | 2,128 | 2,122 | 2,140 | 6,390 | Near-uniform routing; no node dominates. |
| Writes | 2,141 | 2,138 | 2,111 | 6,390 | Near-uniform routing; no node dominates. |

### Fault target coverage

| Fault role | n1 | n2 | n3 | Total episodes | Verification |
|---|---:|---:|---:|---:|---|
| Killed node | 43 | 44 | 38 | 125 | 125 stopped, detected and recovered. |
| Isolated node | 40 | 50 | 35 | 125 | 125 cuts installed, exercised and healed. |

- Consecutive operations selected different coordinators 5,628 times in normal operation, 4,271 times during node failure and 5,682 times during partition.
- All three CQL endpoints remained eligible during every network partition.
- The stopped endpoint was absent from every node-failure candidate set.
- Selection imbalance is retained as natural random variation; no outcome-dependent rerolling was used.

## 8. Per-run audit trail

Outcome columns below refer only to main trials. `err`, `dep` and `succ` are the three observed inconclusive reasons.

| Run | Profile; configs × rounds | Trials | viol | ok | err | dep | succ | Independent verifier | Fault episodes |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| `20260919T094446Z_0000000001352837` | smoke; 5 × 1 | 60 | 1 | 39 | 15 | 2 | 3 | Pass | 1 node + 1 partition: pass |
| `20260919T095446Z_0000000001352839` | smoke; 5 × 1 | 60 | 0 | 43 | 16 | 1 | 0 | Pass | 1 node + 1 partition: pass |
| `20260919T100144Z_000000000135283a` | smoke; 5 × 1 | 60 | 2 | 46 | 10 | 1 | 1 | Pass | 1 node + 1 partition: pass |
| `20260919T100850Z_000000000135283b` | smoke; 5 × 1 | 60 | 2 | 44 | 14 | 0 | 0 | Pass | 1 node + 1 partition: pass |
| `20260919T135936Z_e9f0cc36454d5986` | smoke; 5 × 1 | 60 | 3 | 40 | 15 | 0 | 2 | Pass | 1 node + 1 partition: pass |
| `20260920T000159Z_36915629d2b6f5ad` | full; 9 × 10 | 1,080 | 17 | 584 | 455 | 8 | 16 | Pass | 10 node + 10 partition: pass |
| `20260920T010744Z_0977bac4dcb260ac` | full; 9 × 10 | 1,080 | 17 | 578 | 464 | 10 | 11 | Pass | 10 node + 10 partition: pass |
| `20260920T021504Z_dc8094a55ebf425f` | full; 9 × 10 | 1,080 | 15 | 582 | 461 | 9 | 13 | Pass | 10 node + 10 partition: pass |
| `20260920T032029Z_4d1c6194b3309a6b` | full; 9 × 10 | 1,080 | 18 | 573 | 472 | 8 | 9 | Pass | 10 node + 10 partition: pass |
| `20260920T035710Z_000000000135283f` | full; 5 × 10 | 600 | 13 | 418 | 150 | 8 | 11 | Pass | 10 node + 10 partition: pass |
| `20260920T042616Z_b3e212c5ede5c29f` | full; 9 × 10 | 1,080 | 17 | 580 | 462 | 5 | 16 | Pass | 10 node + 10 partition: pass |
| `20260920T061739Z_e6f386623a3b950e` | full; 9 × 10 | 1,080 | 15 | 592 | 460 | 5 | 8 | Pass | 10 node + 10 partition: pass |
| `20260921T000348Z_000000000135283f` | full; 9 × 50 | 5,400 | 74 | 2,918 | 2,304 | 34 | 70 | Pass | 50 node + 50 partition: pass |
| **Total** | — | **12,780** | **194** | **7,037** | **5,298** | **91** | **160** | **13/13 pass** | **125 + 125 pass** |

## 9. Supplemental controls excluded from the matrix

### Read-repair control

| Setting | Regression | No regression observed | Inconclusive operation error | Total | Interpretation |
|---|---:|---:|---:|---:|---|
| BLOCKING | 0 | 58 | 67 | 125 | No regression in evaluable histories, consistent with blocking repair. |
| NONE | 43 | 9 | 73 | 125 | 43/52 evaluable histories regressed, supporting the role of read repair. |

### Timestamp control

- **125/125** trials returned the value with the larger Cassandra timestamp even though it was issued first.
- This confirms last-write-wins timestamp resolution and explains why the main experiments use increasing explicit timestamps.

## 10. Limitations and reporting rules

- Treat violations as counterexamples to the tested model under the stated schedule; one valid witness is sufficient to show that a configuration does not guarantee the property in that scenario.
- Treat `ok` as “no violation observed,” never as proof of a universal guarantee.
- Exclude `inc:err`, `inc:dep` and `inc:succ` from witness-rate denominators; retain them when discussing availability and experimental coverage.
- The experiment randomizes coordinators. Cassandra still selects replicas internally, so “write at a node” means “send the request to that coordinator.”
- The deployment uses containers on one physical host; it does not reproduce independent-machine clock, disk, rack or datacenter failures.
- Hinted handoff is disabled and the main table uses `BLOCKING` read repair. Conclusions apply to that controlled configuration.
- Fault episodes contain multiple trial keys, so confidence calculations must account for clustering by episode rather than treating every trial as an independent fault realization.
- Unequal cell totals arise from the staged expansion from 5 to 9 configurations; compare rates or matched cells, not raw counts alone.

### Evidence and interpretive basis

- Per-run evidence: `completion.json`, `environment.json`, `plan.json`, `trials.json`, `faults.json`, and the scenario-specific `episode_*.json` files in each listed result directory.
- Independent audit: `scripts/verify_randomized.py` recomputes verdicts and checks trial, routing, initialization, fault and control evidence.
- Registered expectations: `report/predictions.md` and `docs/randomized-experiment-plan.md`.
- Cassandra mechanisms: [Dynamo-style replication and tunable consistency](https://cassandra.apache.org/doc/stable/cassandra/architecture/dynamo.html), [read repair](https://cassandra.apache.org/doc/stable/cassandra/managing/operating/read_repair.html), and [CQL conflict resolution](https://cassandra.apache.org/doc/stable/cassandra/developing/cql/dml.html).

## 11. Detailed outcome matrix

Legend: **viol** = violation; **ok** = no violation observed; **inc:err** = timeout/unavailable; **inc:dep** = dependency not observed; **inc:succ** = successor not observed; **inc:mal** = malformed evidence; **inc:oth** = other.

| Model | Config (W/R) | Scenario | viol | ok | inc:err | inc:dep | inc:succ | inc:mal | inc:oth | cell total |
|---|---|---|---|---|---|---|---|---|---|---|
| RYW | ONE/ONE | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | ONE/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | ONE/ONE | network_partition | 51 | 74 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | ONE/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | ONE/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | ONE/QUORUM | network_partition | 22 | 61 | 42 | 0 | 0 | 0 | 0 | 125 |
| RYW | ONE/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| RYW | ONE/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | ONE/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | QUORUM/ONE | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | QUORUM/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | QUORUM/ONE | network_partition | 19 | 64 | 42 | 0 | 0 | 0 | 0 | 125 |
| RYW | QUORUM/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | QUORUM/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | QUORUM/QUORUM | network_partition | 0 | 53 | 72 | 0 | 0 | 0 | 0 | 125 |
| RYW | QUORUM/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| RYW | QUORUM/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | QUORUM/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | ALL/ONE | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| RYW | ALL/ONE | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | ALL/ONE | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | ALL/QUORUM | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| RYW | ALL/QUORUM | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | ALL/QUORUM | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | ALL/ALL | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | ALL/ALL | node_failure | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
| RYW | ALL/ALL | network_partition | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
| MR | ONE/ONE | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | ONE/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | ONE/ONE | network_partition | 28 | 96 | 1 | 0 | 0 | 0 | 0 | 125 |
| MR | ONE/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | ONE/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | ONE/QUORUM | network_partition | 0 | 55 | 70 | 0 | 0 | 0 | 0 | 125 |
| MR | ONE/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MR | ONE/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | ONE/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | QUORUM/ONE | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | QUORUM/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | QUORUM/ONE | network_partition | 15 | 62 | 48 | 0 | 0 | 0 | 0 | 125 |
| MR | QUORUM/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | QUORUM/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | QUORUM/QUORUM | network_partition | 0 | 41 | 84 | 0 | 0 | 0 | 0 | 125 |
| MR | QUORUM/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MR | QUORUM/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | QUORUM/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | ALL/ONE | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MR | ALL/ONE | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | ALL/ONE | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | ALL/QUORUM | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MR | ALL/QUORUM | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | ALL/QUORUM | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | ALL/ALL | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | ALL/ALL | node_failure | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
| MR | ALL/ALL | network_partition | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
| MW | ONE/ONE | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | ONE/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | ONE/ONE | network_partition | 31 | 38 | 0 | 0 | 56 | 0 | 0 | 125 |
| MW | ONE/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | ONE/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | ONE/QUORUM | network_partition | 15 | 41 | 38 | 0 | 31 | 0 | 0 | 125 |
| MW | ONE/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MW | ONE/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | ONE/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | QUORUM/ONE | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | QUORUM/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | QUORUM/ONE | network_partition | 0 | 40 | 64 | 0 | 21 | 0 | 0 | 125 |
| MW | QUORUM/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | QUORUM/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | QUORUM/QUORUM | network_partition | 0 | 44 | 81 | 0 | 0 | 0 | 0 | 125 |
| MW | QUORUM/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MW | QUORUM/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | QUORUM/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | ALL/ONE | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MW | ALL/ONE | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | ALL/ONE | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | ALL/QUORUM | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MW | ALL/QUORUM | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | ALL/QUORUM | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | ALL/ALL | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | ALL/ALL | node_failure | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
| MW | ALL/ALL | network_partition | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
| WFR | ONE/ONE | normal | 0 | 124 | 0 | 1 | 0 | 0 | 0 | 125 |
| WFR | ONE/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | ONE/ONE | network_partition | 13 | 29 | 0 | 49 | 34 | 0 | 0 | 125 |
| WFR | ONE/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | ONE/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | ONE/QUORUM | network_partition | 0 | 30 | 70 | 17 | 8 | 0 | 0 | 125 |
| WFR | ONE/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| WFR | ONE/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | ONE/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | QUORUM/ONE | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | QUORUM/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | QUORUM/ONE | network_partition | 0 | 29 | 62 | 24 | 10 | 0 | 0 | 125 |
| WFR | QUORUM/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | QUORUM/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | QUORUM/QUORUM | network_partition | 0 | 21 | 104 | 0 | 0 | 0 | 0 | 125 |
| WFR | QUORUM/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| WFR | QUORUM/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | QUORUM/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | ALL/ONE | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| WFR | ALL/ONE | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | ALL/ONE | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | ALL/QUORUM | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| WFR | ALL/QUORUM | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | ALL/QUORUM | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | ALL/ALL | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | ALL/ALL | node_failure | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
| WFR | ALL/ALL | network_partition | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
