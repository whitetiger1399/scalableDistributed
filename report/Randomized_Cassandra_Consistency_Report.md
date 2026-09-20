# Client-centric consistency in Apache Cassandra

- Course: [Course name]
- Member 1: [Member 1 name / student ID]
- Member 2: [Member 2 name / student ID, if applicable]
- Member 3: [Member 3 name / student ID, if applicable]

Evidence run: `randomized_20260920T035710Z_000000000135283f`; schema `randomized-cassandra-evidence-v3`; profile `full`.

## Abstract

We tested read-your-writes (RYW), monotonic reads (MR), monotonic writes (MW), and writes-follow-reads (WFR) on a three-node Cassandra 5.0.9 cluster. Every application operation independently selected a random CQL coordinator from the endpoints reachable to the client. The verified evidence contains 600 main histories, 20 read-repair attempts, and 10 timestamp controls. Main results comprise 13 violation witnesses, 418 completed histories without a witness, and 169 inconclusive histories.

## System and installation

The deployment uses three Docker containers in one datacenter (`dc1`) with NetworkTopologyStrategy replication factor 3. All three nodes own replicas for every experiment key. Cassandra is 5.0.9; the Python client image is 3.11.13 and uses cassandra-driver 3.29.2. Base images are pinned by digest. Hinted handoff is deliberately disabled, driver retries and speculative execution are disabled, and main tables use `read_repair=BLOCKING`.

Install Docker Compose, allocate about 8 GB and four CPU cores, then run `python3 scripts/run_randomized.py --plan-only` followed by `python3 scripts/run_randomized.py --config config/randomized_experiments.json`. Validate using `python3 scripts/verify_randomized.py <run>` and build this report with `python3 scripts/build_report.py --results <run>`.

## Configuration and predictions

Configuration names are write/read levels. With RF=3, strict acknowledgement overlap for the restricted visibility test requires W+R>3. Quorum overlap does not establish general causal consistency or replica application order. Availability is reported independently from safety: a timeout or Unavailable response is inconclusive, not a consistency violation.

| Write/read | RYW | MR with BLOCKING | MW/WFR observable |
|---|---|---|---|
| ONE/ONE | May return a stale value | Regression possible | Missing dependency possible |
| QUORUM/ONE | Stale read possible | Regression possible | No general causal guarantee |
| ONE/QUORUM | No strict W+R>RF overlap | BLOCKING quorum reads should not regress | No general causal guarantee |
| QUORUM/QUORUM | Expected for successful restricted histories | Should not regress | No witness expected in restricted history |
| ALL/ALL | Expected for successful operations | Expected | No witness expected in restricted history |

These predictions were registered before the randomized measurements. Random routing may select the same coordinator repeatedly; this is a valid random outcome and was not filtered.

## Experimental method

The full matrix uses 10 attempts for every selected model/configuration/scenario cell. Each trial starts with a unique key initialized to `(a=0,b=0)` at ALL. RYW tests write then read by one logical client. MR performs a producer write then two reads by one client. MW and WFR search for the observable counterexample `(a=0,b=1)`, where a successor is visible without its predecessor. This is a finite dependency-visibility test; it does not reconstruct every replica's execution order.

The router draws independently with replacement for every operation and saves the selected endpoint, candidate set, draw number, requested consistency level, actual coordinator, timing and response. Logical client identities preserve session order even when operations use different backend connections.

For node failure, the runner samples a victim, records its container ID/IP, sends SIGKILL, proves the container stopped, and waits until both survivors report that exact IP as down in consecutive membership observations. It then runs the histories, restarts the same container with its volume retained, and waits for all three nodes to be healthy.

For the network partition, the runner samples an isolated node and installs bilateral DROP rules for internode TCP ports 7000/7001 in a project-only OUTPUT chain. CQL 9042 remains available. It verifies all three client endpoints before measurement, saves membership views and post-workload packet counters, removes only project rules, and verifies recovery.

## Results

| Scenario | Write/read | Model | Attempts | Violations | No witness | Inconclusive |
|---|---|---|---|---|---|---|
| network_partition | ALL/ALL | MR | 10 | 0 | 0 | 10 |
| network_partition | ALL/ALL | MW | 10 | 0 | 0 | 10 |
| network_partition | ALL/ALL | RYW | 10 | 0 | 0 | 10 |
| network_partition | ALL/ALL | WFR | 10 | 0 | 0 | 10 |
| network_partition | ONE/ONE | MR | 10 | 2 | 7 | 1 |
| network_partition | ONE/ONE | MW | 10 | 2 | 4 | 4 |
| network_partition | ONE/ONE | RYW | 10 | 4 | 6 | 0 |
| network_partition | ONE/ONE | WFR | 10 | 0 | 5 | 5 |
| network_partition | ONE/QUORUM | MR | 10 | 0 | 4 | 6 |
| network_partition | ONE/QUORUM | MW | 10 | 0 | 4 | 6 |
| network_partition | ONE/QUORUM | RYW | 10 | 1 | 2 | 7 |
| network_partition | ONE/QUORUM | WFR | 10 | 0 | 2 | 8 |
| network_partition | QUORUM/ONE | MR | 10 | 1 | 4 | 5 |
| network_partition | QUORUM/ONE | MW | 10 | 0 | 5 | 5 |
| network_partition | QUORUM/ONE | RYW | 10 | 3 | 3 | 4 |
| network_partition | QUORUM/ONE | WFR | 10 | 0 | 3 | 7 |
| network_partition | QUORUM/QUORUM | MR | 10 | 0 | 3 | 7 |
| network_partition | QUORUM/QUORUM | MW | 10 | 0 | 3 | 7 |
| network_partition | QUORUM/QUORUM | RYW | 10 | 0 | 3 | 7 |
| network_partition | QUORUM/QUORUM | WFR | 10 | 0 | 0 | 10 |
| node_failure | ALL/ALL | MR | 10 | 0 | 0 | 10 |
| node_failure | ALL/ALL | MW | 10 | 0 | 0 | 10 |
| node_failure | ALL/ALL | RYW | 10 | 0 | 0 | 10 |
| node_failure | ALL/ALL | WFR | 10 | 0 | 0 | 10 |
| node_failure | ONE/ONE | MR | 10 | 0 | 10 | 0 |
| node_failure | ONE/ONE | MW | 10 | 0 | 10 | 0 |
| node_failure | ONE/ONE | RYW | 10 | 0 | 10 | 0 |
| node_failure | ONE/ONE | WFR | 10 | 0 | 10 | 0 |
| node_failure | ONE/QUORUM | MR | 10 | 0 | 10 | 0 |
| node_failure | ONE/QUORUM | MW | 10 | 0 | 10 | 0 |
| node_failure | ONE/QUORUM | RYW | 10 | 0 | 10 | 0 |
| node_failure | ONE/QUORUM | WFR | 10 | 0 | 10 | 0 |
| node_failure | QUORUM/ONE | MR | 10 | 0 | 10 | 0 |
| node_failure | QUORUM/ONE | MW | 10 | 0 | 10 | 0 |
| node_failure | QUORUM/ONE | RYW | 10 | 0 | 10 | 0 |
| node_failure | QUORUM/ONE | WFR | 10 | 0 | 10 | 0 |
| node_failure | QUORUM/QUORUM | MR | 10 | 0 | 10 | 0 |
| node_failure | QUORUM/QUORUM | MW | 10 | 0 | 10 | 0 |
| node_failure | QUORUM/QUORUM | RYW | 10 | 0 | 10 | 0 |
| node_failure | QUORUM/QUORUM | WFR | 10 | 0 | 10 | 0 |
| normal | ALL/ALL | MR | 10 | 0 | 10 | 0 |
| normal | ALL/ALL | MW | 10 | 0 | 10 | 0 |
| normal | ALL/ALL | RYW | 10 | 0 | 10 | 0 |
| normal | ALL/ALL | WFR | 10 | 0 | 10 | 0 |
| normal | ONE/ONE | MR | 10 | 0 | 10 | 0 |
| normal | ONE/ONE | MW | 10 | 0 | 10 | 0 |
| normal | ONE/ONE | RYW | 10 | 0 | 10 | 0 |
| normal | ONE/ONE | WFR | 10 | 0 | 10 | 0 |
| normal | ONE/QUORUM | MR | 10 | 0 | 10 | 0 |
| normal | ONE/QUORUM | MW | 10 | 0 | 10 | 0 |
| normal | ONE/QUORUM | RYW | 10 | 0 | 10 | 0 |
| normal | ONE/QUORUM | WFR | 10 | 0 | 10 | 0 |
| normal | QUORUM/ONE | MR | 10 | 0 | 10 | 0 |
| normal | QUORUM/ONE | MW | 10 | 0 | 10 | 0 |
| normal | QUORUM/ONE | RYW | 10 | 0 | 10 | 0 |
| normal | QUORUM/ONE | WFR | 10 | 0 | 10 | 0 |
| normal | QUORUM/QUORUM | MR | 10 | 0 | 10 | 0 |
| normal | QUORUM/QUORUM | MW | 10 | 0 | 10 | 0 |
| normal | QUORUM/QUORUM | RYW | 10 | 0 | 10 | 0 |
| normal | QUORUM/QUORUM | WFR | 10 | 0 | 10 | 0 |

Outcome denominators: dependency_not_observed=8, evaluable=431, operation_error=150, successor_not_observed=11.

### Supplemental controls

| Read repair | Attempts | Regressions | No regression | Inconclusive |
|---|---|---|---|---|
| BLOCKING | 10 | 0 | 3 | 7 |
| NONE | 10 | 1 | 5 | 4 |

Timestamp reversal: expected=10, unexpected=0, inconclusive=0. The control writes value 1 at T+100, then value 2 at T+50; Cassandra should retain the higher-timestamp value.

Random crash victims: {'n3': 5, 'n1': 4, 'n2': 1}. Random partitioned nodes: {'n2': 5, 'n3': 2, 'n1': 3}.

## Discussion and limitations

A violation row is a concrete counterexample to the stated observable predicate under the recorded conditions. A no-witness row is only a finite observation. Inconclusive histories remain availability evidence and are never treated as safe histories. The report should compare the table above with the registered predictions; unexpected outcomes require inspection of their raw operations and fault episode before interpretation.

The three containers share one physical host, RF equals node count, hints are disabled, and only one datacenter is tested. The experiments do not model disk loss, independent host failures, multi-datacenter latency, concurrent writers, arbitrary clock skew, or horizontal throughput scaling. Ten attempts meet the assignment minimum but offer limited statistical power. Cases within one fault episode share conditions and are not independent fault realizations. MW/WFR results concern the two-cell observable only and must not be generalized to universal causal consistency.

## Reproducibility, sources, and AI use

The evidence validator accepted the evidence schema, all 600 main histories, exact per-case coverage, 20 read-repair attempts, 10 timestamp controls, routing metadata, setup/fault links and recomputed verdicts. Runtime revision information and dirty-worktree status are preserved in `environment.json`; the root and derived random seeds are in `seeds.json`. The archive includes the selected evidence, configuration, experiment modules, source, tests, instructions and report.

Sources: Apache Cassandra [Dynamo architecture](https://cassandra.apache.org/doc/5.0/cassandra/architecture/dynamo.html), [read repair](https://cassandra.apache.org/doc/5.0/cassandra/managing/operating/read_repair.html), [hints](https://cassandra.apache.org/doc/5.0/cassandra/managing/operating/hints.html), and [CQL DML](https://cassandra.apache.org/doc/5.0/cassandra/developing/cql/dml.html). Docker and Python package versions are recorded in the project Dockerfiles and requirements.

OpenAI Codex assisted with design review, implementation, documentation lookup, code generation, testing, experiment orchestration, evidence validation, analysis and report generation. Database outcomes in this report come only from the verified saved evidence; AI did not invent or replace measurements. Group members must review the code, results and interpretations before submission.

Completion time: 2026-09-20T04:33:34.797996+00:00. Root seed: 20260927.
