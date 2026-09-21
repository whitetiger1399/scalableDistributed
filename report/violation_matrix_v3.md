# Client-centric consistency outcome matrix — driver-policy v3

## 1. Scope and headline result

- **Evidence run:** `20260921T081729Z_000000000135283f` only.
- **Evidence schema:** `cassandra-driver-policy-evidence-v4`; independent verifier: **pass**.
- **Execution:** 2026-09-21T08:17:29.170624+00:00 to 2026-09-21T09:12:26.561533+00:00 (54.96 minutes).
- **System:** Apache Cassandra 5.0.9, three nodes in `dc1`, `NetworkTopologyStrategy`, replication factor 3; Python driver 3.29.2.
- **Routing policy:** `TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc="dc1"))`; every measured statement supplied keyspace `lab` and its partition routing key.
- **Coverage:** 1,080 main histories = 3 scenarios × 9 write/read configurations × 4 models × 10 rounds.
- **Result:** 0 violations, 637 no-violation observations, and 443 inconclusive histories caused by operation errors.
- **Supplemental controls:** 20 read-repair and 10 timestamp trials are reported separately.

### Academic assessment

- [x] **Complete and internally valid:** the completion marker contains all expected trials, and `scripts/verify_randomized.py` accepted identifiers, operation ordering, routing evidence, fault evidence, verdict recomputation, and controls.
- [x] **Availability behavior is meaningful:** every node-failure history containing `ALL` was inconclusive; partition errors were dominated by `ALL` and isolated-side `QUORUM` requests.
- [x] **Normal-operation behavior is coherent:** all 360 histories completed without a witness.
- [!] **Zero violations require a coverage qualification:** only 2/360 partition histories crossed between the isolated node and majority component, and both had operation errors.
- [!] **Driver-policy implication:** 357/360 partition histories used one coordinator throughout. Token-aware routing with the default `shuffle_replicas=False` presents a stable replica order for one routing key, so successive operations usually selected the same first live replica.
- [!] **Conclusion boundary:** this run establishes availability outcomes for the tested faults, but provides little power to expose client-centric violations that require operations to observe different partition components.

## 2. Compatibility with the earlier matrix

- `violation_matrix_v2.md` pools 13 runs from `randomized-cassandra-evidence-v3`, where the harness independently sampled a coordinator for every operation.
- This run uses `cassandra-driver-policy-evidence-v4`, where the real driver chooses the coordinator from its token-aware query plan.
- The routing intervention changed the probability of crossing a partition from substantial to 2/360 histories in this run.
- Therefore this v3 document analyzes the new run separately. Pooling its raw counts with v2 would confound consistency level with coordinator-selection policy.

## 3. Aggregate outcomes by scenario

| Scenario | viol | ok | inc:err | Total | ok rate | inc:err rate | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
| Normal | 0 | 360 | 0 | 360 | 100.00% | 0.00% | All operations completed; no finite-history witness appeared. |
| Node Failure | 0 | 160 | 200 | 360 | 44.44% | 55.56% | The two surviving replicas served ONE/QUORUM; histories containing ALL failed. |
| Network Partition | 0 | 117 | 243 | 360 | 32.50% | 67.50% | One-side histories often completed; ALL and isolated-side QUORUM requests failed. |
| **All scenarios** | **0** | **637** | **443** | **1080** | **58.98%** | **41.02%** | Availability and safety remain separate outcomes. |

- All 443 inconclusive histories have reason `operation_error`; there are no dependency, successor, malformed, or other exclusions.
- The overall 0% violation count is not a guarantee rate because 41.02% of histories were not evaluable and almost no partition histories crossed the cut.

## 4. Inconclusive-operation audit

| Scenario and cause | Error operations | Histories affected | Expected? | Explanation |
|---|---:|---:|---|---|
| Node failure: `ALL` unavailable | 360 | 200 | Yes | RF=3 with one stopped replica cannot satisfy `ALL`; histories can contain multiple failed operations. |
| Partition: `ALL` unavailable | 360 | 200 | Yes | Neither a two-node nor a one-node component can contact all three replicas. |
| Partition: `QUORUM` unavailable | 118 | 41 | Yes | A coordinator on the isolated side sees one live replica and cannot satisfy two responses. |
| Partition: read timeout | 2 | 2 | Plausible transient | One CL `ONE` and one CL `QUORUM` read timed out; these are conservatively inconclusive. |

- Partition error totals are 480 failed operations across 243 histories. One history may contain several errors.
- A timeout does not prove that no replica applied or returned a mutation, so the oracle correctly avoids a safety verdict.

## 5. Outcomes by client-centric model

| Model | Attempts | viol | ok | inc:err | Evaluable | Finding |
|---|---:|---:|---:|---:|---:|---|
| RYW | 270 | 0 | 160 | 110 | 160 | No stale-after-own-write witness observed; cross-component exposure was insufficient. |
| MR | 270 | 0 | 159 | 111 | 159 | No newer-to-older regression observed; most operations stayed at one coordinator. |
| MW | 270 | 0 | 158 | 112 | 158 | No successor-without-predecessor witness observed; no evaluable cross-cut history occurred. |
| WFR | 270 | 0 | 160 | 110 | 160 | No dependency-order witness observed; one weak partition history timed out. |

### Interpretation against predictions

- **RYW and MR:** weak configurations may violate these models across divergent replicas, but this run rarely changed partition sides within a history.
- **MW and WFR:** Cassandra quorum overlap is not a general causal-order guarantee. Zero witnesses here reflects the executed routes, not proof that these models hold universally.
- **QUORUM/QUORUM:** successful histories showed no witness, consistent with the registered workload-specific expectation.
- **Any configuration containing ALL:** successful histories were impossible during either fault, which matches Cassandra quorum arithmetic.

## 6. Network-partition outcomes by consistency configuration

| Configuration (W/R) | viol | ok | inc:err | Evaluable | Assessment |
|---|---:|---:|---:|---:|---|
| ONE/ONE | 0 | 39 | 1 | 39 | 39/40 completed, but same-side routing prevented a meaningful cross-cut weak-consistency test. |
| ONE/QUORUM | 0 | 26 | 14 | 26 | Quorum failed when the selected coordinator was isolated; no witness observed among completions. |
| ONE/ALL | 0 | 0 | 40 | 0 | Expected unavailability because the configuration contains ALL. |
| QUORUM/ONE | 0 | 25 | 15 | 25 | Quorum writes on the isolated side failed; completed histories stayed within a viable component. |
| QUORUM/QUORUM | 0 | 27 | 13 | 27 | Successful majority-side histories agreed; isolated-side operations were unavailable. |
| QUORUM/ALL | 0 | 0 | 40 | 0 | Expected unavailability because the configuration contains ALL. |
| ALL/ONE | 0 | 0 | 40 | 0 | Expected unavailability because the configuration contains ALL. |
| ALL/QUORUM | 0 | 0 | 40 | 0 | Expected unavailability because the configuration contains ALL. |
| ALL/ALL | 0 | 0 | 40 | 0 | Expected unavailability because the configuration contains ALL. |

### Exact violation cells

- **None.** No cell contained a violation witness.
- This is a valid description of the run, but the 2/360 cross-cut coverage prevents a strong safety inference for weak configurations.

## 7. Driver routing evidence

### Selected coordinators

| Scenario | Operation | n1 | n2 | n3 | Total |
|---|---|---:|---:|---:|---:|
| Normal | Read | 184 | 158 | 198 | 540 |
| Normal | Write | 183 | 166 | 191 | 540 |
| Node Failure | Read | 128 | 171 | 241 | 540 |
| Node Failure | Write | 132 | 171 | 237 | 540 |
| Network Partition | Read | 161 | 179 | 200 | 540 |
| Network Partition | Write | 169 | 167 | 204 | 540 |

### Within-history route diversity

| Scenario | One coordinator only | More than one coordinator | Crossed the 2\|1 cut |
|---|---:|---:|---:|
| Normal | 354 | 6 | N/A |
| Node failure | 358 | 2 | N/A |
| Network partition | 357 | 3 | 2 |

- Every recorded operation listed all three metadata-visible local replicas as eligible and attempted exactly one coordinator; retries and speculative execution were disabled.
- No node-failure operation selected the stopped node as its coordinator.
- The two cross-cut partition histories were `ALL/QUORUM MR` and `ONE/QUORUM MW`; both were inconclusive because a quorum operation failed.
- The driver behavior is internally consistent: `TokenAwarePolicy` first yields replicas for the supplied routing key, and its default does not shuffle that replica list. With RF=3 on three nodes, every node is a replica, but a key still has a stable first replica.

### Consequence for the experiment

- This setup accurately measures Cassandra Python-driver policy behavior.
- It does not provide the route diversity needed for a strong counterexample search across partition components.
- More trials alone may improve coverage slowly, but it does not remove the structural preference for the same first replica for a key. Future comparisons should treat routing policy as an experimental factor and retain this run unchanged.

## 8. Fault-injection audit

| Fault target | n1 | n2 | n3 | Total episodes | Verification |
|---|---:|---:|---:|---:|---|
| Killed node | 5 | 3 | 2 | 10 | SIGKILL, survivor detection, restart, three-node recovery |
| Isolated node | 2 | 3 | 5 | 10 | Bilateral internode DROP rules, CQL reachability, packet counters, cleanup, recovery |

- Node failure used `docker compose kill -s SIGKILL <victim>`, waited until both survivors reported the victim down, ran 36 histories, restarted the victim, and required all nodes to return UN.
- Network partition installed bilateral `iptables` DROP rules for internode ports 7000/7001 across the sampled 2|1 cut while leaving CQL 9042 reachable.
- The verifier confirmed all 10 node-failure and all 10 partition episodes, including initialization and recovery evidence.

## 9. Supplemental controls

### Read-repair control

| Setting | Regression | No regression observed | inc:err | Total | Evaluable | Assessment |
|---|---:|---:|---:|---:|---:|---|
| BLOCKING | 0 | 1 | 9 | 10 | 1 | Only 1/10 attempts was evaluable; no comparative inference is justified. |
| NONE | 0 | 1 | 9 | 10 | 1 | Only 1/10 attempts was evaluable; no comparative inference is justified. |

- Eighteen of 20 repair controls were inconclusive, so this run does not demonstrate the expected contrast between `BLOCKING` and `NONE`.
- All 10 timestamp controls returned the value carrying the larger Cassandra timestamp, as expected.

## 10. Detailed outcome matrix

Legend: **viol** = violation; **ok** = no violation observed; **inc:err** = timeout/unavailable. `inc:dep`, `inc:succ`, malformed, and other are zero in every cell.

| Model | Config (W/R) | Scenario | viol | ok | inc:err | cell total |
|---|---|---|---:|---:|---:|---:|
| RYW | ONE/ONE | normal | 0 | 10 | 0 | 10 |
| RYW | ONE/ONE | node_failure | 0 | 10 | 0 | 10 |
| RYW | ONE/ONE | network_partition | 0 | 10 | 0 | 10 |
| RYW | ONE/QUORUM | normal | 0 | 10 | 0 | 10 |
| RYW | ONE/QUORUM | node_failure | 0 | 10 | 0 | 10 |
| RYW | ONE/QUORUM | network_partition | 0 | 8 | 2 | 10 |
| RYW | ONE/ALL | normal | 0 | 10 | 0 | 10 |
| RYW | ONE/ALL | node_failure | 0 | 0 | 10 | 10 |
| RYW | ONE/ALL | network_partition | 0 | 0 | 10 | 10 |
| RYW | QUORUM/ONE | normal | 0 | 10 | 0 | 10 |
| RYW | QUORUM/ONE | node_failure | 0 | 10 | 0 | 10 |
| RYW | QUORUM/ONE | network_partition | 0 | 6 | 4 | 10 |
| RYW | QUORUM/QUORUM | normal | 0 | 10 | 0 | 10 |
| RYW | QUORUM/QUORUM | node_failure | 0 | 10 | 0 | 10 |
| RYW | QUORUM/QUORUM | network_partition | 0 | 6 | 4 | 10 |
| RYW | QUORUM/ALL | normal | 0 | 10 | 0 | 10 |
| RYW | QUORUM/ALL | node_failure | 0 | 0 | 10 | 10 |
| RYW | QUORUM/ALL | network_partition | 0 | 0 | 10 | 10 |
| RYW | ALL/ONE | normal | 0 | 10 | 0 | 10 |
| RYW | ALL/ONE | node_failure | 0 | 0 | 10 | 10 |
| RYW | ALL/ONE | network_partition | 0 | 0 | 10 | 10 |
| RYW | ALL/QUORUM | normal | 0 | 10 | 0 | 10 |
| RYW | ALL/QUORUM | node_failure | 0 | 0 | 10 | 10 |
| RYW | ALL/QUORUM | network_partition | 0 | 0 | 10 | 10 |
| RYW | ALL/ALL | normal | 0 | 10 | 0 | 10 |
| RYW | ALL/ALL | node_failure | 0 | 0 | 10 | 10 |
| RYW | ALL/ALL | network_partition | 0 | 0 | 10 | 10 |
| MR | ONE/ONE | normal | 0 | 10 | 0 | 10 |
| MR | ONE/ONE | node_failure | 0 | 10 | 0 | 10 |
| MR | ONE/ONE | network_partition | 0 | 10 | 0 | 10 |
| MR | ONE/QUORUM | normal | 0 | 10 | 0 | 10 |
| MR | ONE/QUORUM | node_failure | 0 | 10 | 0 | 10 |
| MR | ONE/QUORUM | network_partition | 0 | 6 | 4 | 10 |
| MR | ONE/ALL | normal | 0 | 10 | 0 | 10 |
| MR | ONE/ALL | node_failure | 0 | 0 | 10 | 10 |
| MR | ONE/ALL | network_partition | 0 | 0 | 10 | 10 |
| MR | QUORUM/ONE | normal | 0 | 10 | 0 | 10 |
| MR | QUORUM/ONE | node_failure | 0 | 10 | 0 | 10 |
| MR | QUORUM/ONE | network_partition | 0 | 7 | 3 | 10 |
| MR | QUORUM/QUORUM | normal | 0 | 10 | 0 | 10 |
| MR | QUORUM/QUORUM | node_failure | 0 | 10 | 0 | 10 |
| MR | QUORUM/QUORUM | network_partition | 0 | 6 | 4 | 10 |
| MR | QUORUM/ALL | normal | 0 | 10 | 0 | 10 |
| MR | QUORUM/ALL | node_failure | 0 | 0 | 10 | 10 |
| MR | QUORUM/ALL | network_partition | 0 | 0 | 10 | 10 |
| MR | ALL/ONE | normal | 0 | 10 | 0 | 10 |
| MR | ALL/ONE | node_failure | 0 | 0 | 10 | 10 |
| MR | ALL/ONE | network_partition | 0 | 0 | 10 | 10 |
| MR | ALL/QUORUM | normal | 0 | 10 | 0 | 10 |
| MR | ALL/QUORUM | node_failure | 0 | 0 | 10 | 10 |
| MR | ALL/QUORUM | network_partition | 0 | 0 | 10 | 10 |
| MR | ALL/ALL | normal | 0 | 10 | 0 | 10 |
| MR | ALL/ALL | node_failure | 0 | 0 | 10 | 10 |
| MR | ALL/ALL | network_partition | 0 | 0 | 10 | 10 |
| MW | ONE/ONE | normal | 0 | 10 | 0 | 10 |
| MW | ONE/ONE | node_failure | 0 | 10 | 0 | 10 |
| MW | ONE/ONE | network_partition | 0 | 10 | 0 | 10 |
| MW | ONE/QUORUM | normal | 0 | 10 | 0 | 10 |
| MW | ONE/QUORUM | node_failure | 0 | 10 | 0 | 10 |
| MW | ONE/QUORUM | network_partition | 0 | 5 | 5 | 10 |
| MW | ONE/ALL | normal | 0 | 10 | 0 | 10 |
| MW | ONE/ALL | node_failure | 0 | 0 | 10 | 10 |
| MW | ONE/ALL | network_partition | 0 | 0 | 10 | 10 |
| MW | QUORUM/ONE | normal | 0 | 10 | 0 | 10 |
| MW | QUORUM/ONE | node_failure | 0 | 10 | 0 | 10 |
| MW | QUORUM/ONE | network_partition | 0 | 5 | 5 | 10 |
| MW | QUORUM/QUORUM | normal | 0 | 10 | 0 | 10 |
| MW | QUORUM/QUORUM | node_failure | 0 | 10 | 0 | 10 |
| MW | QUORUM/QUORUM | network_partition | 0 | 8 | 2 | 10 |
| MW | QUORUM/ALL | normal | 0 | 10 | 0 | 10 |
| MW | QUORUM/ALL | node_failure | 0 | 0 | 10 | 10 |
| MW | QUORUM/ALL | network_partition | 0 | 0 | 10 | 10 |
| MW | ALL/ONE | normal | 0 | 10 | 0 | 10 |
| MW | ALL/ONE | node_failure | 0 | 0 | 10 | 10 |
| MW | ALL/ONE | network_partition | 0 | 0 | 10 | 10 |
| MW | ALL/QUORUM | normal | 0 | 10 | 0 | 10 |
| MW | ALL/QUORUM | node_failure | 0 | 0 | 10 | 10 |
| MW | ALL/QUORUM | network_partition | 0 | 0 | 10 | 10 |
| MW | ALL/ALL | normal | 0 | 10 | 0 | 10 |
| MW | ALL/ALL | node_failure | 0 | 0 | 10 | 10 |
| MW | ALL/ALL | network_partition | 0 | 0 | 10 | 10 |
| WFR | ONE/ONE | normal | 0 | 10 | 0 | 10 |
| WFR | ONE/ONE | node_failure | 0 | 10 | 0 | 10 |
| WFR | ONE/ONE | network_partition | 0 | 9 | 1 | 10 |
| WFR | ONE/QUORUM | normal | 0 | 10 | 0 | 10 |
| WFR | ONE/QUORUM | node_failure | 0 | 10 | 0 | 10 |
| WFR | ONE/QUORUM | network_partition | 0 | 7 | 3 | 10 |
| WFR | ONE/ALL | normal | 0 | 10 | 0 | 10 |
| WFR | ONE/ALL | node_failure | 0 | 0 | 10 | 10 |
| WFR | ONE/ALL | network_partition | 0 | 0 | 10 | 10 |
| WFR | QUORUM/ONE | normal | 0 | 10 | 0 | 10 |
| WFR | QUORUM/ONE | node_failure | 0 | 10 | 0 | 10 |
| WFR | QUORUM/ONE | network_partition | 0 | 7 | 3 | 10 |
| WFR | QUORUM/QUORUM | normal | 0 | 10 | 0 | 10 |
| WFR | QUORUM/QUORUM | node_failure | 0 | 10 | 0 | 10 |
| WFR | QUORUM/QUORUM | network_partition | 0 | 7 | 3 | 10 |
| WFR | QUORUM/ALL | normal | 0 | 10 | 0 | 10 |
| WFR | QUORUM/ALL | node_failure | 0 | 0 | 10 | 10 |
| WFR | QUORUM/ALL | network_partition | 0 | 0 | 10 | 10 |
| WFR | ALL/ONE | normal | 0 | 10 | 0 | 10 |
| WFR | ALL/ONE | node_failure | 0 | 0 | 10 | 10 |
| WFR | ALL/ONE | network_partition | 0 | 0 | 10 | 10 |
| WFR | ALL/QUORUM | normal | 0 | 10 | 0 | 10 |
| WFR | ALL/QUORUM | node_failure | 0 | 0 | 10 | 10 |
| WFR | ALL/QUORUM | network_partition | 0 | 0 | 10 | 10 |
| WFR | ALL/ALL | normal | 0 | 10 | 0 | 10 |
| WFR | ALL/ALL | node_failure | 0 | 0 | 10 | 10 |
| WFR | ALL/ALL | network_partition | 0 | 0 | 10 | 10 |

## 11. Reporting rules and limitations

- Interpret `no_violation_observed` as a finite observation, never a universal guarantee.
- Keep operation failures in availability totals and outside safety-witness denominators.
- Treat the 10 rounds as repeated fault episodes; histories within one episode share a fault realization.
- Do not pool these counts with v2 because coordinator assignment changed from independent harness sampling to driver-controlled token-aware routing.
- The cluster ran as containers on one physical host, so machine, rack, disk, clock, and datacenter failures were not independent.
- Hinted handoff was disabled; main tables used `BLOCKING` read repair; conclusions apply to these registered conditions.
- The read-repair control has inadequate evaluable coverage in this run.
- With only two cross-cut histories and neither evaluable, the run cannot test whether weak configurations preserve client-centric guarantees across divergent components.

### Evidence basis

- Run directory: `results/cassandra_policy_20260921T081729Z_000000000135283f/`.
- Primary records: `completion.json`, `environment.json`, `plan.json`, `trials.json`, `faults.json`, `read_repair.json`, `timestamp_control.json`, and 30 episode files.
- Independent audit: `python3 scripts/verify_randomized.py results/cassandra_policy_20260921T081729Z_000000000135283f`.
- Registered expectations: `report/predictions.md` and `docs/cassandra-driver-policy-plan.md`.
- Mechanism references: Apache Cassandra [Dynamo-style replication and tunable consistency](https://cassandra.apache.org/doc/stable/cassandra/architecture/dynamo.html), [read repair](https://cassandra.apache.org/doc/stable/cassandra/managing/operating/read_repair.html), and [CQL timestamp conflict resolution](https://cassandra.apache.org/doc/stable/cassandra/developing/cql/dml.html); DataStax Python driver [load-balancing policies](https://docs.datastax.com/en/developer/python-driver/3.29/api/cassandra/policies/).
