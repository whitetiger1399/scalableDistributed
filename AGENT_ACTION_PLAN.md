# Cassandra project review and agent action plan

Review date: 19 September 2026. Reviewed baseline: commit `c8be689`, plus the untracked `Project_Assignment.md` supplied in this workspace.

**Status update, 19 September 2026:** implementation was subsequently authorized. The codebase now implements the remediation items in this plan. Unit and integration status must still be taken from current test output and verified evidence, not from this planning document. Historical measurements remain preserved and separate.

## 1. Assessment and review boundaries

The project has a suitable three-node replicated Cassandra deployment and a useful randomized-coordinator design, but the redesigned experiment-to-report pipeline is not ready for submission. Execution blockers, incomplete evidence validation, and a report generator still tied to the old design must be resolved before collecting the new measurements. Passing the current unit tests does not establish that fault injection or the complete pipeline works.

Reviewed: assignment, README, status document, randomized methodology, Docker definitions, configuration, all experiment modules, routing and worker code, classifiers, runner/verifier/report scripts, unit tests, and the historical result inventory. `Project.md`, although mentioned in the IDE context, is absent from this checkout. PDF appearance and archive reproducibility were not independently validated in this review.

Read-only checks performed:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`: all **9 tests passed**.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_randomized.py --plan-only`: **600 main + 20 read-repair + 10 timestamp = 630 planned trials**. This does not execute Cassandra queries.
- Historical files contain **300 main histories, 10 read-repair histories, and one timestamp-control history** represented by three operations, consistent with `WORK_IN_PROGRESS.md`.
- No randomized measurement directory is present in the reviewed inventory. Historical outcomes must not be relabelled as randomized outcomes.

Findings below are static code findings unless explicitly identified as executed checks. File line references refer to the reviewed baseline.

## 2. Requirements coverage

| Requirement | Current evidence | Remaining work |
|---|---|---|
| Replicated distributed database | Three Cassandra 5.0.9 containers, RF=3, one datacenter | Verify live schema/configuration and capture runtime provenance for each new run |
| Tunable consistency and predictions | Five write/read pairs; BLOCKING/NONE controls; written predictions | Bind predictions to redesigned workloads and remove fixed-route assumptions from the new report |
| RYW, MR, MW, WFR experiments | Workloads and finite-history classifiers exist | Define semantic scope precisely; handle missing data; strengthen MW/WFR interpretation |
| Normal, node failure, partition | Implemented schedules and project-scoped injection helpers | Fix failure detection, verify partitions, and guarantee cleanup |
| Random operations; customer cannot select nodes | Application API delegates every operation to a seeded random router | Preserve routing evidence and state that coordinators, not serving replicas, are randomized |
| At least ten trials per experiment case | Default schedule plans ten per main cell and control variant | Actually execute and independently validate; distinguish attempts, evaluable histories, and setup failures |
| Configurable, separately understandable experiments | JSON configuration and module skeletons | Wire or reject settings; move actual workloads out of central conditionals |
| PDF with results, explanations, citations and AI disclosure | Historical report and methodology PDF exist | Generate a redesigned report from verified randomized results |
| Reproducible source/scripts/instructions | Historical package exists | Include new modules/config in archive and test extraction/reproduction |
| Group/submission details | Deadline documented as 27 September 2026 | Fill course and up to three member details; group reviews and submits to Canvas |

The assignment explicitly permits several containers on one machine. Multi-host deployment, extra datacenters, and throughput scaling benchmarks are optional extensions, not missing mandatory requirements.

## 3. Sound choices to preserve

- Keep random selection with replacement for each operation. Selecting the same coordinator twice is valid; do not force different nodes or select seeds after inspecting outcomes.
- Keep the application API free of node arguments. Backend endpoint pinning implements the router's choice and does not itself violate this requirement.
- Keep explicit consistency levels, disabled driver retries/speculation, fresh trial data, successful ALL initialization, and separate setup/application operations.
- Keep timeouts and unavailable requests distinct from consistency violations. Preserve every measured attempt, including inconvenient outcomes.
- Keep partition rules scoped to the lab containers and `LAB_FAULT` chain, persistent volumes on crash, and historical artifacts separated by design version.

## 4. Prioritized findings and actions

### G01 — P0: Failure detection compares node names with IP addresses

**Evidence:** `experiments/faults.py:61` checks whether `victim` such as `n2` occurs in a `DN` row. Saved `results/20260912T063741Z/initial_cluster.json` shows numeric addresses in `nodetool status`. `scripts/run_randomized.py:103` waits on this predicate before measuring.

**Impact:** With that status format, a correctly killed node will not satisfy detection. The round times out instead of producing the required failure histories.

**Proposed actions:** Resolve and persist the victim's container ID, IP and Cassandra host ID before killing it. Parse membership columns and match the expected identity exactly from both survivors. Require a documented number of consecutive matching observations, retain all observations, and separately prove that the container exited.

**Acceptance:** Fixtures using numeric addresses detect each possible victim, reject the wrong down node and incomplete membership, and time out with preserved diagnostics. A later integration check demonstrates detection and recovery for n1, n2 and n3.

### G02 — P0: Fault lifecycle is not exception-safe or bounded

**Evidence:** `scripts/run_randomized.py:99–119` and `:134–152` clean up only on the successful path. `experiments/faults.py:12` has no subprocess timeout. `scripts/lab.py` and the README recovery procedure restart only n3, although randomized victims can be any node.

**Impact:** A worker exception, detection timeout, interruption, or hanging command can leave nodes down or partitions installed and contaminate subsequent runs.

**Proposed actions:** Introduce one fault-lifecycle owner with durable state, bounded commands, `try/finally` cleanup and interruption handling. Record cleanup errors without hiding the original failure. Provide an idempotent recovery command for all lab nodes and this project's firewall rules. Add a run lock to prevent concurrent controllers. Support recovery after an uncatchable process kill through the saved journal.

**Acceptance:** Inject failures at each lifecycle stage in tests; verify recovery is attempted and the run remains incomplete. A repeated recovery operation must be harmless and must leave unrelated Docker/firewall resources alone.

### G03 — P0: The randomized verifier crashes and permits incomplete evidence

**Evidence:** `scripts/verify_randomized.py:19,40` uses tuple keys in `json.dumps`, which rejects them. Its count check verifies only observed groups, not the exact expected case set. It does not recompute verdicts, validate initialization, or validate fault establishment. It also expects main trials even when session experiments are disabled.

**Proposed actions:** Use structured case rows in JSON output. Derive expectations from the same validated configuration contract as the planner, but independently check recorded histories. Require exact case identities and counts, unique trial/attempt IDs, operation shapes and CLs, valid setup/fault links, and recomputed verdicts. Verify enabled controls and all selected variants. Do not rely on assertions that disappear under optimized Python execution.

**Acceptance:** A valid fixture exits successfully with parseable JSON. Missing cases, duplicate histories, wrong CLs, altered verdicts, absent fault evidence, failed initialization and truncated controls fail with specific diagnostics. A controls-only configuration validates correctly.

### G04 — P0: The report and archive pipeline still targets the old design

**Evidence:** `scripts/build_report.py:41` selects completion files and then requires the old `environment.json` layout. The randomized runner does not produce that layout. Report prose still describes fixed nodes and five repetitions. Packaging at `scripts/build_report.py:264` includes `src`, `scripts`, and `tests` but omits the new `experiments` and `config` directories. README invokes this generator after the randomized runner.

**Proposed actions:** Require an explicit run and supported evidence-schema/design version. Refuse incomplete or invalid runs. Generate tables and prose from that run's configuration and verified records. Package every required module, config, source snapshot, documentation and raw evidence. Regenerate checksums against the final package; retain historical reports with clear labels.

**Acceptance:** A randomized fixture generates a consistent report; old and incomplete runs cannot masquerade as the redesign. Extract the package into a clean directory and check imports, planning, verification and report regeneration. Visually inspect every final PDF page.

### G05 — P1: MW/WFR checks are narrower than the assignment's general guarantees

**Evidence:** `src/worker.py:117–125` writes two cells in one row; `src/checks.py:14–18` searches for a visible successor without its predecessor. README already acknowledges that this does not reconstruct replica execution order.

**Impact:** A finite dependency-visibility witness is useful, but observing both cells does not establish general monotonic-write or writes-follow-reads ordering. Reconciled query results do not reveal every replica's execution history. Increasing timestamps on different cells do not themselves enforce causal delivery.

**Proposed actions:** State formal session orders and observable predicates for all four models. Give producer, dependent client and observer explicit logical IDs. Explain exactly which operational interpretation MW/WFR test and which claims remain untested. If claiming replica application-order guarantees, add separate instrumentation with a justified mapping from events to that guarantee; otherwise narrow the claim. Consider separately labelled cross-key dependency histories as an extension, with an oracle that avoids artifacts from independent observer reads.

**Acceptance:** Every reported conclusion names the tested predicate and assumptions. No report claims universal causality or all-replica ordering solely from successful two-cell reads. Missing-dependency witnesses and no-witness histories are explained separately.

### G06 — P1: Predictions need to separate visibility, ordering and availability

**Evidence:** `report/predictions.md` still assumes n3 is killed and fixed partition routes. The redesigned methodology improves this, but its MW/WFR entries often say only that no general ordering claim follows.

**Proposed actions:** Freeze a versioned prediction matrix before measurement. For RF=3, explain acknowledgement-set overlap: ONE/ONE, QUORUM/ONE and ONE/QUORUM lack the strict `W+R>3` condition; QUORUM/QUORUM and ALL/ALL satisfy it for the restricted acknowledged-write visibility test. This is not a general causal-consistency proof. Cassandra documents both replica coordination and timestamp reconciliation. [S1, S3]

For the actual sequential two-cell workload with successful quorum writes and quorum reads, predict no missing-predecessor witness under the stated single-writer, increasing-timestamp assumptions; retain the narrower interpretation. Distinguish MR's successful quorum-read behavior with BLOCKING from write/read overlap. [S2]

Derive availability separately: one crashed replica leaves two usable replicas; ONE and QUORUM can complete while ALL cannot. In a stabilized 2|1 partition, a quorum operation requires the two-node component; a CQL-reachable isolated coordinator may still fail the requested CL. Under ideal uniform routing across all three endpoints, an operation requiring quorum selects the majority with probability 2/3; this is a routing calculation, not a measured success rate or independence guarantee for whole histories.

**Acceptance:** Each selected model/configuration/scenario has a falsifiable workload-specific prediction, assumptions, expected unavailable cases and an explanation of what would contradict it.

### G07 — P1: Missing rows can crash the classifier; reasons and coverage are lost

**Evidence:** `src/checks.py:8–17` indexes read values directly, although `Transport.execute` returns `None` for no rows. The methodology explicitly treats a missing row as a possible stale observation. `inconclusive_reason` exists but is never attached to worker results. MR's first write is labelled client rather than the documented producer.

**Proposed actions:** Validate history shape and typed read outcomes before classification. Distinguish absent rows/cells, malformed evidence and request errors; do not indiscriminately convert missing values to zero. Under verified initialization and no deletes/TTL, define how an absent row participates in RYW/MR and predecessor checks. Record reason codes, logical roles, MR first-read exposure, WFR dependency exposure and MW/WFR successor exposure.

**Acceptance:** Tests cover missing rows, null cells, malformed/short histories, unobserved dependencies and ambiguous write timeouts without crashing or fabricating a violation. Reports include both total-attempt and evaluable-history denominators.

### G08 — P1: Configuration advertises settings the runtime does not honor

**Evidence:** `config/randomized_experiments.json` contains seed, RF, CQL port, hints and table settings. `src/worker.py:16,63,100–101` hardcodes nodes, port, RF and table definitions; Dockerfile hardcodes hints off. `scripts/run_randomized.py:189` ignores the configured seed. `load_config` requires all four models and weakly validates other fields.

**Proposed actions:** Define one typed configuration contract and normalized effective configuration. Wire supported options through every layer, or reject unsupported changes explicitly. Permit selected models/types for exploratory runs while requiring full assignment coverage for a submission profile. Reject duplicates, empty selections, invalid consistency pairs, invalid identifiers and inconsistent enablement. Replace duplicate rounds/repetitions knobs with one clear per-case count or document their precise relationship. Keep a distinctly labelled smoke profile separate from full runs.

**Acceptance:** A nondefault configuration changes actual behavior or fails before Docker starts; nothing is silently ignored. Planner, runner, verifier and report agree on counts. A full profile enforces at least ten attempts per selected case. Fixed three-node deployment is an acceptable explicit constraint.

### G09 — P1: Actual workload implementations are not separated by experiment

**Evidence:** `experiments/*.py` mostly provide descriptions, selection and accounting. The four model workloads remain in `src/worker.py:113–128`; both supplemental controls are embedded in `scripts/run_randomized.py:123–168`.

**Proposed actions:** Move RYW, MR, MW and WFR history construction and their expectations into distinct readable modules; give read-repair and timestamp controls their actual executable definitions. Keep transport, routing, configuration, fault lifecycle and orchestration shared. Use a registry that exposes each experiment's inputs, prerequisites, count formula, history and oracle. Avoid modules that merely wrap unchanged central conditionals.

**Acceptance:** A reader can understand and select one experiment from its module without tracing unrelated experiment branches. All definitions use the same customer API without node parameters.

### G10 — P1: Randomization is only partially auditable

**Evidence:** `scripts/run_randomized.py:73` writes derived routing/order/fault seeds, but execution instead uses one root RNG plus separately derived worker seeds. Main worker `health` and `seed` fields are discarded at `:110`. `probe()` is TCP-only and occurs once per worker. Cases are shuffled within fixed scenario blocks, not the round-wise scenario scheduling described in the methodology.

**Proposed actions:** Use real independent RNG streams for route selection, case order and faults; persist the streams actually consumed and each worker's context. Define whether candidate membership is fixed per block or refreshed and preserve that policy. Do not remove partitioned but CQL-reachable nodes based on controller knowledge or read results. Map requested node to actual coordinator address. Handle an empty candidate set as recorded availability evidence. Align scenario ordering with the registered plan and report route-change and fault-victim coverage.

**Acceptance:** A seed and saved candidate sets replay routing choices, but documentation does not promise identical distributed outcomes. Changing enabled workloads does not silently change independent fault streams. Repeated routes remain valid and no post-hoc seed filtering occurs.

### G11 — P1: Setup readiness and data isolation are insufficiently verified

**Evidence:** Schema responses at `scripts/run_randomized.py:85` are not checked. `assert_initialization` accepts empty records. Membership readiness only counts three UN lines. `CREATE IF NOT EXISTS` does not reconcile schema drift. Keys in `experiments/common.py` and supplemental controls omit a unique run ID.

**Proposed actions:** Verify expected identities, CQL readiness, schema agreement, RF, table options, hints and relevant timeouts before measurement. Require exact successful initialization coverage for expected keys. Use run/episode/trial-specific keys and monotonic mutation timestamps within each history. Keep setup reads out of the measured window because reads can repair data. Treat membership recovery and data convergence as different assertions; choose explicit recovery conditions appropriate to fresh-key experiments.

**Acceptance:** Empty initialization, wrong RF/table settings, a wrong member and stale schema fail setup. Reusing a database volume cannot reuse trial keys. Failed setup is retained but never counted as a valid measured attempt.

### G12 — P1: Partition establishment needs observable proof

**Evidence:** `experiments/faults.py:88–116` installs bilateral peer-IP rules in container OUTPUT chains for source/destination internode ports. Main execution sleeps 15 seconds; counters are captured at installation, not after the workload. There is no barrier proving the intended connectivity graph and retained client access.

**Proposed actions:** Record exact container/IP mapping, rules, command outcomes and phase timestamps. Block both directions between the isolated node and each peer on configured internode ports while leaving CQL 9042 accessible. Verify intended blocked and allowed paths, all membership views and client CQL access before measurement; collect counter deltas afterward. Use deadline-based checks with bounded commands rather than interpreting a fixed sleep as proof. Remove only project rules and verify healing.

**Acceptance:** Each partition episode proves its 2|1 topology, usable majority link and retained customer access to all nodes. A rule-installation failure is a setup failure. Document DROP-induced timeout behavior and that this is an internode partition, not a disconnected client or host outage.

### G13 — P1: Read-repair control has confounds and no outcome oracle

**Evidence:** `scripts/run_randomized.py:126–153` runs each table in separate episodes, hardcodes pairs `(n1,n2)` then `(n2,n3)`, changes graphs immediately before reads and stores no control verdict. Intermediate `set_graph` evidence is discarded. This differs from the methodology's intended controlled comparison.

**Proposed actions:** Specify and save a random permutation of topology identities independently of client routing. Establish the minority-value phase and each subsequent overlapping two-node component with measured barriers. Preserve the existing add-before-remove rule transition so there is no fully connected interval. Account for in-flight messages rather than assuming a partition erases them. Decide explicitly between paired table variants in shared episodes and separately randomized episodes; keep the count and analysis consistent. Never force a read to the favorable component: random routes that cannot finish remain visible outcomes.

Give the control its own oracle: prerequisites met, both quorum reads succeeded, first value observed, then regression/no regression. BLOCKING's documented monotonic quorum-read behavior and NONE's lack of that guarantee motivate the comparison; absence of a regression in ten random attempts is not proof of NONE safety. [S2]

**Acceptance:** Ten attempts per table variant, complete topology/route evidence and classification of every attempt. Report how often the first read exposed the minority update and how many read pairs were evaluable.

### G14 — P1: Timestamp control is collected but not checked

**Evidence:** `scripts/run_randomized.py:160–167` does not validate initialization or assign an outcome. It schedules ALL writes at T+100 and T+50, followed by an ALL read.

**Proposed actions:** Require successful setup and classify the deliberate timestamp reversal separately from the normal consistency assumptions. If both writes and read succeed, check that the higher-timestamp value wins. Preserve timeouts as inconclusive; distinguish an unexpected result from a routine main-suite RYW violation. Cassandra mutation timestamps determine conflict resolution, not application call order. [S3]

**Acceptance:** Ten independently identified controls with expected/unexpected/inconclusive outcomes and actual timestamp evidence.

### G15 — P1: Evidence can be lost and completion is too permissive

**Evidence:** Worker records return only after a whole batch. `save()` overwrites JSON non-atomically. Per-round files are saved before recovery fields are added. Controls are saved only after all their rounds. `completion.json` is emitted without an independent integrity check or setup/control validation.

**Proposed actions:** Append operation and lifecycle events durably, write atomic checkpoints, and link records using run/episode/trial/attempt IDs. Preserve worker health, schema responses, requested/actual coordinators, CLs, returned values, error details, fault evidence and recovery. Capture source snapshot/revision with dirty state, image digests, runtime versions and effective configuration. Separate execution-finished, evidence-valid and report-ready states; retain a useful partial record after interruption.

**Acceptance:** Interrupted runs retain completed operations and are rejected as complete. A full marker requires exact planned attempt coverage and valid setup evidence, not universal operation success. Unavailable measured requests remain legitimate recorded outcomes.

### G16 — P2: Trial accounting and analysis need stronger interpretation

**Evidence:** Main defaults schedule ten histories per model/configuration/scenario but share each fault episode across twenty cases. Existing tests exercise only small pure helpers and classifier examples.

**Proposed actions:** Report the unit of repetition explicitly and retain episode IDs. Summarize per case: scheduled attempts, valid setup, completed operations, evaluable histories, violations, no witness and reason-coded inconclusive outcomes. Report availability independently of safety, MR exposure and dependency exposure. Do not treat 200 histories sharing ten fault episodes as 200 independent fault realizations. Do not rerun until a preferred witness appears. If uncertainty intervals are added, state assumptions and account for episode clustering; ten trials primarily meet the requested minimum.

Add behavior-focused tests for G01–G15, especially lifecycle failure paths, malformed evidence, configuration variants and report compatibility. If latency is reported, separate connection/setup cost from query latency and use a monotonic duration clock; current lazy connections and wall-clock timings confound it.

**Acceptance:** All totals reconcile to raw evidence, conclusions distinguish observation from guarantee, and a clean end-to-end pipeline is validated before the registered full run.

## 5. Intended experiment inventory after remediation

These are future planned counts, not completed measurements.

| Experiment | Default cases | Attempts per case | Total |
|---|---:|---:|---:|
| RYW | 5 CL pairs × 3 scenarios | 10 | 150 |
| MR | 5 CL pairs × 3 scenarios | 10 | 150 |
| MW dependency visibility | 5 CL pairs × 3 scenarios | 10 | 150 |
| WFR dependency visibility | 5 CL pairs × 3 scenarios | 10 | 150 |
| Read repair | BLOCKING and NONE | 10 | 20 |
| Timestamp reversal | One control schedule | 10 | 10 |
| **Total** | | | **630** |

The main matrix has 60 cells with ten attempts each. It contains ten crash/restart episodes and ten main partition/heal episodes if each episode contains all twenty selected model/CL cases. Supplemental repair topology episodes must be counted separately, with the paired-versus-separate decision in G13 explicit. Operations, histories and fault episodes must never be reported interchangeably.

Errors after valid setup count as measured attempts and availability evidence. Failed setup does not. If an additional attempt is needed after failed setup, retain the failed record and give the replacement a new ID. Never promise ten successful ALL histories while a replica is unavailable.

## 6. Future node-failure and partition documentation checklist

For each **node-failure episode**, document: healthy baseline and ALL initialization; random victim selection; saved identity; `docker compose kill -s SIGKILL <victim>`; exited-container proof; both survivors' exact down-node observations; randomized application histories; restart of the same container with its volume retained; membership/CQL/schema recovery; cleanup outcome and elapsed phase times. State that this measures established process unavailability, not disk loss or an in-flight crash.

For each **partition episode**, document: healthy baseline and initialization; sampled isolated node; bilateral internode DROP rules and IPs; verified blocked/allowed edges; retained CQL reachability; membership views; application histories and post-workload counter deltas; project-only rule removal and recovery. For repair controls, document every graph transition separately. Administrative verification may target nodes, but measured customer operations must continue to route randomly.

Hints are deliberately disabled in this project. Document that this changes automatic catch-up behavior and limits generalization to default deployments; availability recovery alone does not establish convergence. Hints and repair have different roles in replica synchronization. [S4]

## 7. Ordered execution plan for a future implementation agent

1. **Freeze methodology:** address semantic scope and predictions (G05–G07), configuration contract and counts (G08), and control design (G13–G14). Preserve the original baseline and results. Deliver a reviewed specification before measurements.
2. **Repair execution foundations:** fix detection and lifecycle (G01–G02), then setup and partition barriers (G11–G12). Acceptance is successful fault/recovery testing, including injected controller failures.
3. **Make experiments inspectable and auditable:** implement separate workloads (G09), real RNG streams (G10), robust outcomes and durable evidence (G07, G15). Acceptance is deterministic schedule replay and useful interrupted-run records.
4. **Build the independent validation/report path:** address G03–G04 and G16 using valid and deliberately corrupted fixtures. Acceptance is a clean extracted-package smoke workflow with no dependence on unarchived files.
5. **Execute a separately labelled integration smoke run:** exercise every experiment/control and cleanup path. Smoke records are not final measurements. Fix any discovered defects before freezing source and predictions for the main run.
6. **Run the registered full matrix:** at least ten validly initialized attempts per selected case, without changing routes or seeds based on observed outcomes. Retain failures and all rerun provenance. Verify evidence before analysis.
7. **Prepare submission:** generate the PDF, experiment/repetition inventory and reproduction package from the verified run; inspect all PDF pages, verify hashes and archive completeness, fill member/course information, disclose AI assistance, and review as a group before Canvas submission on 27 September 2026.

Do not skip validation to preserve a planned execution date. If a step fails, mark the affected run incomplete and report the limitation accurately.

## 8. Optional extensions after the required pipeline works

- Mid-session failures or partitions to test continuity across topology changes; keep them distinct from steady-fault experiments.
- A separately registered default-driver routing comparison to assess how the custom random gateway differs from typical applications.
- Hints-enabled recovery, cross-key dependencies, concurrent writers and explicit clock-skew experiments, each with an appropriate oracle and new predictions.
- More physical failure domains or nodes exceeding RF to study non-replica coordinators and scaling. The present three-node RF=3 setup cannot establish horizontal throughput scalability or independent host-failure resilience.

## 9. Sources and attribution

Primary Cassandra documentation consulted for mechanism checks on 19 September 2026. These documentation URLs identify living documentation; the eventual report should preserve the version consulted alongside the actual Cassandra 5.0.9 environment. Code defects and proposed acceptance checks above are review conclusions, not documentation claims.

- **S1:** Apache Cassandra, [Dynamo architecture](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html): replication, coordination and consistency mechanisms.
- **S2:** Apache Cassandra, [Read repair](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/read_repair.html): monotonic quorum reads, BLOCKING versus NONE and repair scope.
- **S3:** Apache Cassandra, [CQL data manipulation](https://cassandra.apache.org/doc/latest/cassandra/developing/cql/dml.html): mutation timestamps and data manipulation semantics.
- **S4:** Apache Cassandra, [Hints](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/hints.html): replica catch-up and its relationship to repair.

Assignment authority: `Project_Assignment.md`. Implementation authority: reviewed source at `c8be689`, not aspirational prose in the methodology document. AI assistance: OpenAI Codex reviewed source and historical evidence, consulted documentation, ran the nine existing unit tests and the plan-only command, and drafted this action plan. No new database measurements were collected and none are invented here.
