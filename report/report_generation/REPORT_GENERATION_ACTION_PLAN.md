# Cassandra Client-Centric Consistency Report Generation Plan

## 1. Purpose and current status

This document is a **planning and review artifact only**. It defines how to turn the existing draft report and saved experiment evidence into the final academic report. It does not alter the draft DOCX, calculate new results, create CSV files, redraw figures, or run experiments.

Planning source reviewed:

- `report/draft/Cassandra_Client_Centric_Consistency_Report_Code_Formatted.docx`
- The experiment design and evidence identifiers listed in Section 2
- Current repository configuration and execution code, used only to check that the proposed report structure matches the implementation

The draft contains a useful conceptual foundation and detailed implementation notes. Its result sections are still placeholders, its section numbering needs repair, and its architecture figures do not accurately show the deployed containers or Cassandra's per-request coordinator role.

## 2. Fixed evidence boundary

Only measured evidence from the following two designs may appear in result counts, charts, examples, or conclusions.

| Setup | Design ID | Evidence schema | Routing policy |
|---|---|---|---|
| Previous randomized setup | `random-coordinator-v2` | `randomized-cassandra-evidence-v3` | Harness-controlled independent random coordinator |
| Cassandra token-aware setup | `cassandra-driver-policy-v3` | `cassandra-driver-policy-evidence-v4` | `TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc="dc1"))` |

Evidence rules:

- Include a run only when `completion.json` records `completed: true` and the run passes the validator appropriate to its evidence schema.
- Record every included run ID in a run manifest. Do not silently select runs.
- Exclude smoke tests, abandoned runs, partially resumed runs that never completed, and evidence from any other design or schema.
- Preserve the two setups as separate populations. Do not pool their counts into a single violation rate because their coordinator-selection mechanisms produce different exposure.
- Treat repository logs as the sole source for measured outcomes. Cassandra documentation and academic sources may support theoretical expectations, but they may not supply or replace observations.
- Label every result as measured, derived from measured data, or theoretical interpretation.

## 3. Review of the current DOCX draft

### 3.1 Material strengths to retain

- Clear motivation for tunable consistency and the four client-centric models.
- Correct emphasis that an operation failure is different from an observed consistency violation.
- Useful descriptions of RF=3, fault injection, recovery, and reproducibility.
- Detailed implementation material that can support an appendix.
- Explicit AI-usage disclosure.
- Recognition that routing influences which histories are observed but does not itself provide a session guarantee.

### 3.2 Structural gaps to correct

- Repair repeated section numbers in Section 2.
- Move Section 10.2 and 10.3 so they follow the Section 10 heading.
- Replace placeholder values such as `[N]`, `[%]`, `[ms]`, and “to be added later.”
- Replace future-tense result and conclusion language with evidence-based past tense after analysis is complete.
- Move the blank 108-row result matrix out of the main narrative. Keep detailed cells in CSV and, if required, a compact appendix.
- Reduce long code listings in the main report. Retain only short excerpts that explain routing, consistency levels, verdict calculation, and fault injection; link the complete source in the reproduction package.
- Standardize scenario names as `normal`, `node_failure`, and `network_partition`.
- Add an explicit cross-design comparison section rather than mixing the two routing designs in one matrix.

### 3.3 Technical statements to reconcile with the implementation

- Use `NetworkTopologyStrategy`, keyspace `lab`, and the exact saved Cassandra version. Remove the outdated `SimpleStrategy`/`consistency_lab` installation example unless it is clearly marked as historical.
- State that the driver setup uses both token-aware and data-center-aware routing. The current draft incorrectly says data-center awareness is unnecessary.
- Describe the query implementation accurately: partition routing keys are supplied through statements; do not claim prepared statements unless the final source actually uses them.
- Define a Cassandra coordinator as the Cassandra node that receives a particular client request. Do not draw a permanent fourth “Coordinator node.”
- Do not describe cluster health after healing as proof that previously divergent rows converged. Hints are disabled, and convergence requires direct data evidence.
- Replace generic “success” labels with `no_violation_observed`, `violation`, or `inconclusive`.
- Describe the actual MW and WFR oracle, including predecessor/successor state and the logical-client relationship used by the workload.
- Keep primary trial verdicts separate from operation-level exception types so a single history is not counted more than once.

### 3.4 Architecture-figure gaps

The two embedded figures are useful sketches, but the final figures need these corrections:

- The coordinator is currently drawn as a separate service. It must be shown as a role assumed by `n1`, `n2`, or `n3` for each request.
- The deployed `client` container is missing or is represented as a host-only Python environment.
- The host-side orchestration script, Docker Compose control path, client container, Cassandra network, persistent volumes, fault commands, and mounted results directory need distinct boundaries.
- Arrows currently suggest that a permanent coordinator replicates directly to all nodes. The replacement must distinguish client-to-coordinator CQL traffic from Cassandra replica/internode traffic.
- The diagrams need a legend and separate control, query, replication, fault, and evidence flows.
- Text is crowded and partly clipped. The final figures need consistent spacing, alignment, type size, and accessible color use.

## 4. Target report argument

The report should answer five questions in order:

1. **What was tested?** A three-node Cassandra 5.0.9 cluster with RF=3, nine read/write consistency-level combinations, four client-centric models, and three operating scenarios.
2. **How were requests routed?** First through independent harness-selected coordinators, then through Cassandra-driver token-aware and data-center-aware policy.
3. **What was predicted?** Predictions should follow replica acknowledgement requirements, quorum intersection, failure topology, and the exact client-history oracle.
4. **What was observed?** Present violations, no-violation observations, inconclusive histories, exception causes, and routing exposure separately.
5. **Why do the setups differ?** Explain how the routing policy changes the opportunity to observe stale or cross-partition histories without claiming that routing alone changes Cassandra's consistency guarantees.

## 5. Evidence-to-CSV work plan

**Implemented consolidation:** the later implementation request specified two user-facing CSV files. The logical datasets described below are therefore consolidated into `trial_level_evidence.csv` and `run_level_violation_matrix.csv` in this folder. Source paths, hashes, record types, fault fields, operation fields, control fields, and run metadata preserve the same traceability without requiring readers to join several files. `README.md` documents the implemented schema.

### 5.1 Run manifest

Create `report/data/run_manifest.csv` as the evidence index.

Required columns:

`setup`, `design_id`, `evidence_schema`, `run_id`, `result_directory`, `completed`, `validator_status`, `started_utc`, `ended_utc`, `duration_minutes`, `root_seed`, `rounds`, `expected_main_trials`, `observed_main_trials`, `included`, `exclusion_reason`

Acceptance checks:

- Every result directory matching either design is represented.
- Every included run is complete and validated.
- Trial counts in the manifest agree with `completion.json` and `trials.json`.
- Exclusions are explicit and reproducible.

### 5.2 Trial-level dataset

Create `report/data/main_trials.csv`, with one row per client-centric history.

Required fields:

- Provenance: setup, design ID, evidence schema, run ID, episode ID, round, trial ID, seed identifiers.
- Experimental cell: scenario, read CL, write CL, model.
- Result: verdict, primary reason, violation Boolean, inconclusive Boolean.
- Exposure: coordinator sequence, distinct coordinator count, partition side sequence, cross-side Boolean where available.
- Timing: trial start/end or duration where saved.
- Trace link: source JSON filename and stable record identifier.

Do not flatten several operation exceptions into several trial outcomes. Each trial must have one primary verdict.

### 5.3 Operation-level dataset

Create `report/data/operations.csv`, with one row per read or write attempt.

Required fields:

`setup`, `run_id`, `episode_id`, `trial_id`, `operation_index`, `logical_client`, `operation_type`, `key`, `requested_cl`, `selected_or_attempted_hosts`, `actual_coordinator`, `routing_key_present`, `success`, `exception_class`, `exception_message_category`, `latency_ms`, `observed_value`, `source_file`

This dataset explains availability and routing. It must not be used to inflate the number of consistency trials.

### 5.4 Fault and recovery dataset

Create `report/data/fault_episodes.csv`, with one row per scenario episode.

Required fields:

`setup`, `run_id`, `episode_id`, `scenario`, `round`, `fault_target`, `partition_groups`, `fault_start_utc`, `fault_ready_utc`, `workload_start_utc`, `workload_end_utc`, `healing_start_utc`, `recovery_confirmed_utc`, `recovery_status`, `source_file`

This table must distinguish:

- Node failure: container stopped, detection wait, workload while stopped, restart, health verification.
- Network partition: firewall rules inserted on Cassandra internode ports, partition stabilization, workload while split, rule removal, health verification.

### 5.5 Control-experiment datasets

Create:

- `report/data/read_repair_trials.csv`
- `report/data/timestamp_control_trials.csv`

Keep these controls outside the main client-centric trial denominator. Their purpose, execution status, and outcomes should appear in a short validation subsection.

### 5.6 Derived report tables

Generate these only from the validated CSVs:

- `outcomes_by_cell.csv`: setup × scenario × read CL × write CL × model.
- `availability_by_cell.csv`: attempted, completed, operation-error, timeout, unavailable, other exception.
- `routing_exposure.csv`: actual coordinator distribution, distinct-coordinator histories, same-side/cross-side partition histories.
- `reason_breakdown.csv`: violation reasons and inconclusive reasons with counts and percentages.
- `run_totals.csv`: reconciliation totals for each included run.

All percentages must show numerator and denominator. Use `N/A` when the denominator is zero.

## 6. Result classification and academic interpretation

### 6.1 Outcome vocabulary

Use these terms consistently:

| Outcome | Meaning |
|---|---|
| Violation | The required observations completed and the recorded history contradicted the model oracle. |
| No violation observed | The required observations completed and that trial did not contradict the oracle. This is empirical evidence, not a proof of guarantee. |
| Inconclusive: operation error | A required operation did not return a usable result. |
| Inconclusive: dependency not observed | The WFR precondition was not established, so the dependent-write test could not be evaluated. |
| Inconclusive: successor not observed | The MW observation did not expose the successor state needed by the oracle. |
| Excluded run/episode | Evidence integrity, completion, or validation requirements were not met. Excluded data is reported in the manifest, not in outcome totals. |

### 6.2 Assessment markers

Every compact result row should contain one assessment marker and a one-sentence comment.

| Marker | Label | Use |
|---|---|---|
| ☑ | Expected | The observation follows the registered prediction and Cassandra semantics. |
| ◩ | Plausible | The observation is consistent with Cassandra behavior, but the logs do not establish one unique cause. |
| ☐ | Insufficient exposure | Too few evaluable or cross-coordinator/cross-partition histories support a strong comparison. |
| ⚠ | Unexpected | The observation conflicts with the prediction and requires trace-level investigation. |

These markers assess agreement with a prediction. They do not score Cassandra as passing or failing an “industry standard.”

### 6.3 Theoretical comparison frame

Build the expectation table before interpreting results. For RF=3:

- `ONE` requires one replica response and generally favors availability while allowing non-overlapping reads and writes.
- `QUORUM` requires two replica responses. A read/write pair has intersecting acknowledgement sets when `R + W > RF`, but this alone must not be presented as a complete causal-session guarantee for every workload.
- `ALL` requires all three replicas and therefore loses availability when any required replica is unreachable.
- During a one-node failure, `ONE` and `QUORUM` may remain available; `ALL` should commonly fail while the node is unavailable.
- During a 2+1 partition, `QUORUM` can be satisfied only from the two-node side; `ONE` can be satisfied on either side; `ALL` cannot be satisfied until healing.
- Token-aware routing prefers replicas for the partition key and the DC-aware child policy orders local-DC hosts. It changes routing and fault exposure, not consistency-level acknowledgement rules.
- Random coordinator selection deliberately samples more coordinator paths. It can expose histories the stable driver ordering rarely selects, especially during a partition.

The final wording must be checked against authoritative Cassandra and DataStax Python driver documentation and cited. Documentation supports interpretation only; it is not experimental evidence.

## 7. Explaining violations and inconclusive trials

### 7.1 Trace-level causal procedure

For every non-zero violation category and every large inconclusive category:

1. Select representative trials from the CSV using stable IDs.
2. Reconstruct the ordered operation history from the episode JSON.
3. Confirm the requested CL, actual coordinator, attempted hosts, returned values, timestamps, and fault state.
4. Recompute the oracle independently from the saved operations.
5. Check whether the history crossed coordinators or partition sides.
6. State the strongest conclusion supported by the evidence.
7. If the exact internal replica response is not logged, label the causal explanation as plausible rather than proven.

### 7.2 Model-specific evidence

| Model | Violation evidence to show | Key interpretation question |
|---|---|---|
| RYW | Successful write followed by a successful read that returns an older value | Did the read contact a replica path that did not expose the acknowledged write? |
| MR | Two successful ordered reads where the later read returns an older version | Did routing move the client to a less-current replica view? |
| MW | Ordered writes followed by an observation of the successor without the predecessor | Was the prerequisite write absent from the observed state? |
| WFR | A client observes a dependency, another client performs the dependent write, and a later observation exposes the write without its dependency | Did the recorded history establish the dependency before judging the final state? |

### 7.3 Inconclusive-cause hierarchy

Report inconclusive histories in this order:

1. Cassandra unavailability exception.
2. Read timeout.
3. Write timeout.
4. Connection or host-resolution failure.
5. Other operation error.
6. Dependency not observed.
7. Successor not observed.

Where the saved exception does not identify a unique cause, report the saved class/category and avoid guessing. Cluster or Docker process failures belong in run-exclusion and limitations sections unless a complete validated run retained them as trial-level evidence.

## 8. Main result presentation

### 8.1 Compact summary table

Use one table per routing setup with rows grouped by scenario and CL pair. Keep model-level detail in a heatmap or appendix when the table would be too wide.

Recommended columns:

`Scenario | Read/Write CL | Evaluable | Violations | Inconclusive | Violation rate among evaluable | Availability rate | Assessment | Comment`

### 8.2 Required figures

- Outcome composition by setup and scenario: violation, no violation observed, inconclusive.
- Violation-rate heatmap by CL pair and model, faceted by scenario and setup.
- Inconclusive-reason chart by scenario and CL pair.
- Coordinator/routing exposure chart showing one-coordinator, multi-coordinator, and cross-partition histories.
- Availability-versus-safety comparison with the denominator stated on the figure.

Use counts on or beside plots. Do not use a chart if the corresponding sample is too small; show a compact table and mark insufficient exposure.

### 8.3 Cross-design comparison

The comparison must separate three questions:

- Did the two setups create comparable experiment cells and trial counts?
- Did they create comparable coordinator and partition-side exposure?
- Given that exposure, how did violation, evaluability, and operation-error counts differ?

Do not infer that token-aware routing provides a stronger client-centric guarantee merely from fewer observed violations. First show whether the policy produced fewer cross-coordinator or cross-partition histories.

## 9. Architecture visual redesign

### 9.1 Shared visual language

Use official or clearly licensed marks for Windows, macOS, Docker, Apache Cassandra, WSL/Linux, and Python. Keep marks in the architecture figures and a small technology strip; do not repeat logos in every result table.

Use these visual encodings consistently:

- Solid blue arrow: CQL request/response on port 9042.
- Solid purple arrow: Cassandra internode and replica traffic on ports 7000/7001.
- Dashed gray arrow: orchestration and Docker Compose control.
- Red interruption symbol: stopped container or injected partition rule.
- Green document arrow: evidence written to the mounted `results/` directory.
- Cassandra node badge: “coordinator for this request” when selected.

Every figure needs a legend, figure number, concise caption, and alt text. Do not rely on color alone.

### 9.2 Windows architecture figure

Containment layers, outside to inside:

1. Windows 10/11 host.
2. WSL2 Linux environment.
3. Docker Desktop/Engine and Compose project.
4. Docker network `lab`.
5. Containers `client`, `n1`, `n2`, and `n3`.
6. Named volumes for each Cassandra node.

Show the host/WSL controller invoking Compose, the client container submitting CQL, one Cassandra node becoming coordinator per request, coordinator-to-replica traffic, fault commands changing a container or its internode rules, and evidence returning through the bind-mounted repository.

### 9.3 macOS architecture figure

Containment layers, outside to inside:

1. macOS host and terminal/IDE.
2. Host-side Python orchestration process.
3. Docker Desktop Linux VM.
4. Compose project and Docker network `lab`.
5. Containers `client`, `n1`, `n2`, and `n3`.
6. Named Cassandra volumes and bind-mounted repository/results path.

The caption should state that Cassandra Linux containers run inside Docker Desktop's managed VM while the orchestration command is started from macOS.

### 9.4 Routing-policy inset

Create a small two-panel figure:

- Randomized setup: the harness independently chooses an eligible Cassandra coordinator for each operation.
- Driver setup: the application supplies the partition key; token-aware policy prefers replicas and the DC-aware child policy orders local-DC hosts.

The inset should show that both paths still end at an ordinary Cassandra node acting as coordinator.

## 10. Proposed final report structure

| Section | Purpose | Primary artifact |
|---|---|---|
| Executive summary | State question, designs, major measured findings, and limits | Verified summary CSVs |
| 1. Objectives and research questions | Define the four client-centric models and comparison | Assignment + experiment definitions |
| 2. Cassandra background | Explain replication, coordinator role, CLs, and driver routing | Authoritative citations |
| 3. Deployment architecture | Show common cluster plus Windows/macOS containment | Redesigned figures |
| 4. Experimental designs | Compare random coordinator and token-aware routing | Design/evidence table |
| 5. Predictions | Register expected safety and availability by scenario/CL | Prediction matrix |
| 6. Method | Explain schedules, oracles, faults, recovery, repetitions, and controls | Code-linked procedure |
| 7. Evidence and analysis method | Define inclusion, CSV pipeline, verdicts, and denominators | Manifest + schemas |
| 8. Results | Present compact tables and figures for each setup | Derived CSVs |
| 9. Trace case studies | Walk through one violation and one inconclusive history | Episode JSON + operation CSV |
| 10. Cross-design discussion | Relate outcomes to routing exposure and Cassandra semantics | Comparison tables |
| 11. Limitations and validity | Bound what the experiment can establish | Evidence audit |
| 12. Reproduction | Give exact commands, versions, configuration, and file map | README + environment evidence |
| 13. Conclusion | Answer the research questions without overclaiming | Verified findings |
| References and AI disclosure | Cite sources and describe AI contribution | Citation list + disclosure |
| Appendices | Detailed matrices, selected code, schemas, and trace IDs | CSVs + repository links |

Suggested main-body length: approximately 18–24 pages, excluding appendices. Prefer figures and compact tables over the current multi-page empty matrix and long code listings.

## 11. Human-readable visual and editorial treatment

- Begin each results subsection with a one-sentence finding, then show the evidence table or chart.
- Add short “How to read this figure” captions where denominators or inconclusive outcomes are easy to misunderstand.
- Include one annotated history timeline for a violation and one for an unavailable/inconclusive trial.
- Use a restrained palette: Cassandra blue for cluster/data flow, neutral gray for orchestration, amber for inconclusive, and red for violations/faults.
- Use the same names, capitalization, and order for scenarios, consistency levels, and models everywhere.
- Add a small evidence tag to figures and tables, for example `Source: main_trials.csv; included run IDs in run_manifest.csv`.
- Keep conclusions close to their evidence and avoid decorative claims such as “proved consistency.”
- Preserve a human voice through direct explanations of what the group expected, what the traces showed, and what could not be determined.

## 12. Workstream assignments

These are implementation workstreams for a later report-generation phase. One person may own several workstreams, but each output should receive an independent check.

| Workstream/agent | Tasks | Deliverables | Acceptance condition |
|---|---|---|---|
| A. Evidence curator | Inventory runs, enforce design/schema boundary, run validators, freeze manifest | `run_manifest.csv`, exclusion log | All included totals reconcile and all exclusions have reasons |
| B. Data engineer | Convert JSON/JSONL evidence into normalized CSVs | Trial, operation, fault, control CSVs | Deterministic regeneration; no trial double counting |
| C. Results analyst | Produce cell aggregates, rates, uncertainty notes, and trace samples | Derived CSVs, result-table drafts | Every number traces to source rows and states its denominator |
| D. Cassandra reviewer | Build expectation matrix and review causal language | Prediction/assessment matrix, citation notes | Claims match RF=3, CL, fault topology, and routing semantics |
| E. Visual designer | Redraw Windows/macOS architecture and produce result figures | Two architecture figures, routing inset, charts | Correct containment and flows; labels remain readable at report size |
| F. Report editor | Restructure prose, insert results, shorten code sections, repair numbering | Revised DOCX | Complete narrative with no placeholders or contradictory terms |
| G. Reproducibility auditor | Check versions, commands, configs, paths, AI disclosure, and archive contents | Reproduction checklist | A clean environment can follow the documented procedure |
| H. Final QA reviewer | Recalculate sampled values and visually inspect every rendered page | QA log and sign-off checklist | No clipping, orphan headings, broken tables, or unsupported claims |

## 13. Execution order and quality gates

### Gate 0 — Freeze scope

- [ ] Confirm the two permitted design/schema pairs.
- [ ] Create and review the run manifest.
- [ ] Freeze the included run IDs before calculating report totals.

### Gate 1 — Validate evidence

- [ ] Run the correct validator for every included run.
- [ ] Reconcile completion, trial, episode, fault, repair, and timestamp-control counts.
- [ ] Record code revision, configuration, seed, and dirty-worktree metadata.

### Gate 2 — Build auditable datasets

- [ ] Generate all normalized and derived CSVs deterministically.
- [ ] Check uniqueness keys and outcome exclusivity.
- [ ] Independently recompute a sample from raw episode JSON.

### Gate 3 — Lock interpretation

- [ ] Complete the theoretical prediction matrix before drafting conclusions.
- [ ] Assign Expected/Plausible/Insufficient exposure/Unexpected markers.
- [ ] Verify every causal statement against trace fields; qualify inferences.

### Gate 4 — Produce visuals

- [ ] Redraw the two platform architectures and routing inset.
- [ ] Generate plots only from frozen CSVs.
- [ ] Check labels, legends, denominators, captions, and accessibility.

### Gate 5 — Assemble the report

- [ ] Repair structure and numbering.
- [ ] Replace every placeholder.
- [ ] Move full matrices and long code to appendices or repository artifacts.
- [ ] Add citations, evidence tags, limitations, and AI disclosure.

### Gate 6 — Render and verify

- [ ] Render the final DOCX to PDF.
- [ ] Inspect every page at readable zoom.
- [ ] Confirm tables fit, figures are legible, headings stay with content, and code is not clipped.
- [ ] Recheck PDF page numbers, contents, hyperlinks, references, and final file hashes.

## 14. Final acceptance checklist

- [ ] Result evidence comes only from `random-coordinator-v2`/v3 and `cassandra-driver-policy-v3`/v4.
- [ ] Every included run is complete, validated, and listed.
- [ ] The two routing designs are reported separately before comparison.
- [ ] Every table and figure identifies its source CSV and denominator.
- [ ] Trial outcomes are mutually exclusive and operation errors are not double-counted.
- [ ] “No violation observed” is never presented as a proof of consistency.
- [ ] Routing exposure is shown before interpreting differences in violation counts.
- [ ] Node failure and network partition procedures match the actual implementation.
- [ ] The diagrams show a per-request Cassandra coordinator and the real client container.
- [ ] Exact software versions, CLs, RF, scenario timing, repetitions, and seeds are reported.
- [ ] Measured facts, derived values, and theoretical explanations are visibly distinguished.
- [ ] Limitations address topology size, single DC, Docker-host dependence, timing, routing exposure, disabled hints, and observational reach.
- [ ] The final DOCX and PDF contain no placeholders, broken numbering, clipped content, or unsupported conclusions.

## 15. Implementation status

- [x] Trial-level evidence CSV generated for main histories, read-repair controls, and timestamp controls.
- [x] Run-level violation matrix generated for all matching run IDs.
- [x] Export manifest, source hashes, schema guide, reusable exporter, and reconciliation checker added.
- [ ] Redraw the architecture figures.
- [ ] Edit and render the draft DOCX.
- [ ] Run additional experiments if later requested.

Page-level visual QA of the draft could not be completed in the current environment because a DOCX/PDF renderer was unavailable. The review covered extracted document text, OOXML structure, metadata, and both embedded architecture images. Full pagination and layout inspection is therefore a required final gate after the revised DOCX is rendered.
