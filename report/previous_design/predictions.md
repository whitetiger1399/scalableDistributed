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

Normal operation: all configurations should usually complete without witnesses; a rare transient anomaly at weak settings remains possible. Killing n3: operations through surviving nodes should complete for ONE and QUORUM, while ALL cannot obtain three responses. A failed/timed-out write might still change some replicas; classify affected trials as inconclusive.

Partition {n1,n2}|{n3}: first write and first read use n1; the second read/write uses n3. ONE/ONE should expose all four anomalies. QUORUM/ONE should expose RYW and MR; its successor write is unavailable, so MW/WFR are inconclusive. Configurations with quorum reads cannot finish the isolated read. ALL writes cannot finish on either side. Report operation availability separately from safety verdicts.

Read-repair control: initialize all replicas at zero; isolate n3 and write one at ONE; read QUORUM on {n2,n3}; then read QUORUM on {n1,n2}. With BLOCKING the first read should copy the value to n2 and prevent regression. With NONE the reads may return one then zero. The preliminary weak write deliberately creates a minority-only version; this is not the same as the main uniform-consistency matrix.

Timestamp control: ALL write a=1 at timestamp T+100; later ALL write a=2 at T+50; ALL read should return a=1. This intentionally violates the increasing-timestamp assumption and illustrates timestamp conflict resolution, not a defect in quorum acknowledgement.

Sources: Apache Cassandra [Dynamo](https://cassandra.apache.org/doc/stable/cassandra/architecture/dynamo.html), [read repair](https://cassandra.apache.org/doc/stable/cassandra/managing/operating/read_repair.html), and [CQL DML](https://cassandra.apache.org/doc/stable/cassandra/developing/cql/dml.html). Predictions beyond these documented mechanisms are our deductions for the specified schedules.
