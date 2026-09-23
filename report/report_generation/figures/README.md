# Cassandra report figures

These figures were designed after reviewing the two embedded diagrams in `report/draft/Cassandra_Client_Centric_Consistency_Report_Code_Formatted.docx` and the requirements in `REPORT_GENERATION_ACTION_PLAN.md`.

The DOCX was not modified. The PNG files are standalone report assets.

## Final PNG figures

| Figure | Intended report role |
|---|---|
| `png/01_windows_deployment_architecture.png` | Replaces the draft Windows diagram. Shows Windows → WSL2 → Docker Desktop containment, host orchestration, client container, Cassandra nodes, volumes, request coordinator, traffic types, and evidence output. |
| `png/02_macos_deployment_architecture.png` | Replaces the draft macOS diagram. Shows the host controller, Docker Desktop Linux VM, mounted workspace, client container, Cassandra network, volumes, and coordinator role. |
| `png/03_routing_policy_comparison.png` | Compares harness-controlled independent random coordinators with the Cassandra driver's token-aware/DC-aware policy. |
| `png/04_fault_injection_architecture.png` | Explains normal operation, SIGKILL node failure, bilateral 2|1 internode partition, expected CL availability, and the recovery gate. |
| `png/05_experiment_evidence_pipeline.png` | Connects configuration, execution, Cassandra, raw logs, validation, trial CSV, run matrix, and academic report claims. |
| `png/06_client_centric_models.png` | Defines RYW, MR, MW, and WFR as ordered histories and shows the violation witness used by each oracle. |
| `png/07_token_aware_driver_policy_detail.png` | Shows the token-aware Python-driver path from routing key and Murmur3 token to replica ranking, local-DC query plan, coordinator selection, fallback order, replica contacts, and consistency-level boundary. |

All final PNGs are 2400 × 1467 pixels with a white background. Editable SVG sources are retained under `svg/`.

## Visual language

- Blue: CQL request/response on port 9042.
- Purple: Cassandra replica and internode traffic on ports 7000/7001.
- Dashed gray: orchestration and fault control.
- Green: evidence and report-data flow.
- Red: unavailable node or intentionally severed network path.
- Blue coordinator badge: the Cassandra node serving as coordinator for the illustrated request.

The coordinator is deliberately shown as a role on `n1`, `n2`, or `n3`. It is not drawn as a separate fourth Cassandra service.

## Brand marks

The diagrams use recognizable marks for Apache Cassandra, Docker, Apple, Python, Ubuntu, and Windows. SVG marks were obtained from the Simple Icons CDN where available:

- `https://cdn.simpleicons.org/apachecassandra/1287B1`
- `https://cdn.simpleicons.org/docker/2496ED`
- `https://cdn.simpleicons.org/apple/000000`
- `https://cdn.simpleicons.org/python/3776AB`
- `https://cdn.simpleicons.org/ubuntu/E95420`

The Windows four-pane mark is drawn geometrically in `build_figures.py`. Product names and marks remain the property of their respective owners and are used here for academic identification.

## Rebuild

Generate the editable SVG figures from the repository root:

```bash
python3 report/report_generation/figures/build_figures.py
```

The PNGs were rasterized on macOS with Quick Look at 2400 pixels, using a square render wrapper to prevent Quick Look from cropping the 18:11 source view box. The output was then cropped to the exact 2400 × 1467 report aspect ratio with Pillow.

## Report placement recommendation

- Deployment architecture section: Figures 1 and 2.
- Experimental design/routing section: Figure 3.
- Fault methodology section: Figure 4.
- Data collection and reproducibility section: Figure 5.
- Client-centric model definitions or methodology section: Figure 6.
- Token-aware driver implementation subsection: Figure 7.

Use the PNG files in the DOCX. Keep the SVG files as the editable source and for any future PDF-first workflow.
