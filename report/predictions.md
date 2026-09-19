# Predictions recorded before execution

The unit of analysis is a sequential logical client that may change coordinators. Each key has one writer, no deletion/TTL and increasing, explicitly supplied mutation timestamps. RYW and MR compare a single cell. MW and WFR use separate predecessor/successor columns in one row and test for a visible successor without its predecessor. These are counterexample searches, not full proofs of session guarantees.

RF=3. Configuration names below are **write/read**. A successful quorum write and quorum read intersect, but quorum intersection does not impose a dependency order at every replica. Do not call QUORUM/QUORUM universally causal.

| Write/read | RYW prediction | MR prediction with BLOCKING | MW/WFR prediction |
|---|---|---|---|
| ONE/ONE | May fail | May fail | Dependency visibility may fail |
| QUORUM/ONE | May fail | May fail | No general replica-order guarantee; tested isolated successor cannot succeed |
| ONE/QUORUM | May fail because 1+2=3 | Successive quorum reads should not regress | No general replica-order guarantee; tested isolated observer cannot succeed |
| QUORUM/QUORUM | Holds for acknowledged writes under stated assumptions | Successive quorum reads should not regress | No general replica-order guarantee; this workload should show no completed witness |
| ALL/ALL | Holds under stated assumptions | Holds for successful reads | Completed sequential operations should show no dependency-visibility violation in this workload |

Normal operation: all configurations should usually complete without witnesses; a rare transient anomaly at weak settings remains possible. During each failure round, one of n1/n2/n3 is sampled independently. A new worker's CQL readiness probe excludes the stopped endpoint and routes randomly across the two reachable coordinators. ONE and QUORUM can complete, while ALL cannot obtain three replica responses. A failed/timed-out write might still change replicas; classify the history as inconclusive.

Network partition: one node is sampled as the 1-node component and every operation independently samples any CQL-reachable coordinator. ONE may complete on either side. A QUORUM operation can complete only when its coordinator can communicate with the 2-node component; with uniform routing this is a per-operation 2/3 routing probability, not a whole-history success prediction. ALL cannot complete on either side. Weak histories may expose stale reads or missing dependencies when successive random routes cross components. Report availability separately from safety.

Read-repair control: initialize all replicas at zero, cut all internode links, and issue a random-coordinator ONE write. Construct a random two-node component containing the recorded write coordinator, then a second overlapping two-node component, while reads continue to use random coordinators. An attempt is evaluable only if both QUORUM reads complete and the first exposes the new value. With BLOCKING, an evaluable first read should repair its contacted stale replica and prevent regression through the overlap. With NONE, regression remains possible. Failure to observe a regression in ten attempts is not proof of a guarantee.

Timestamp control: ALL write a=1 at timestamp T+100; later ALL write a=2 at T+50; ALL read should return a=1. This intentionally violates the increasing-timestamp assumption and illustrates timestamp conflict resolution, not a defect in quorum acknowledgement.

Sources: Apache Cassandra [Dynamo](https://cassandra.apache.org/doc/stable/cassandra/architecture/dynamo.html), [read repair](https://cassandra.apache.org/doc/stable/cassandra/managing/operating/read_repair.html), and [CQL DML](https://cassandra.apache.org/doc/stable/cassandra/developing/cql/dml.html). Predictions beyond these documented mechanisms are our deductions for the specified schedules.
