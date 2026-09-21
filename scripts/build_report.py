#!/usr/bin/env python3
"""Build the Cassandra-driver-policy report and reproduction archive."""
import argparse
from collections import Counter, defaultdict
import hashlib
import html
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_randomized import verify


def load(path):
    return json.loads(path.read_text())


def markdown_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join("---" for _ in headers) + "|"]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def build_markdown(run, validation):
    plan = load(run / "plan.json")
    env = load(run / "environment.json")
    completion = load(run / "completion.json")
    trials = load(run / "trials.json")
    repairs = load(run / "read_repair.json")
    timestamps = load(run / "timestamp_control.json")
    faults = load(run / "faults.json")
    authors = load(ROOT / "report/authors.json") if (ROOT / "report/authors.json").exists() else {}
    totals = Counter(trial["verdict"] for trial in trials)
    reasons = Counter(trial.get("reason") or "evaluable" for trial in trials)
    grouped = defaultdict(Counter)
    for trial in trials:
        grouped[(trial["scenario"], trial["config"], trial["model"])][trial["verdict"]] += 1
    result_rows = []
    for case, values in sorted(grouped.items()):
        result_rows.append([*case, sum(values.values()), values["violation"],
                            values["no_violation_observed"], values["inconclusive"]])
    repair_rows = []
    for setting in ("BLOCKING", "NONE"):
        selected = [item for item in repairs if item["case"]["setting"] == setting]
        counts = Counter(item["verdict"] for item in selected)
        repair_rows.append([setting, len(selected), counts["regression"],
                            counts["no_regression_observed"], counts["inconclusive"]])
    timestamp_counts = Counter(item["verdict"] for item in timestamps)
    victim_counts = Counter(record.get("fault", {}).get("node") for record in faults
                            if record.get("scenario") == "node_failure")
    isolated_counts = Counter(record.get("fault", {}).get("isolated") for record in faults
                              if record.get("scenario") == "network_partition")
    member_lines = []
    if authors.get("course"):
        member_lines.append(f"- Course: {authors['course']}")
    for index, member in enumerate(authors.get("members", []), 1):
        if member:
            member_lines.append(f"- Member {index}: {member}")
    if not member_lines:
        member_lines = ["- Course and group details: complete `report/authors.json` before submission."]
    predictions = [
        ["ONE/ONE", "May return a stale value", "Regression possible", "Missing dependency possible"],
        ["QUORUM/ONE", "Stale read possible", "Regression possible", "No general causal guarantee"],
        ["ONE/QUORUM", "No strict W+R>RF overlap", "BLOCKING quorum reads should not regress", "No general causal guarantee"],
        ["QUORUM/QUORUM", "Expected for successful restricted histories", "Should not regress", "No witness expected in restricted history"],
        ["ALL/ALL", "Expected for successful operations", "Expected", "No witness expected in restricted history"],
    ]
    lines = [
        "# Client-centric consistency in Apache Cassandra",
        "",
        *member_lines,
        "",
        f"Evidence run: `{run.name}`; schema `{validation['evidence_schema']}`; profile `{plan['profile']}`.",
        "",
        "## Abstract",
        "",
        f"We tested read-your-writes (RYW), monotonic reads (MR), monotonic writes (MW), and writes-follow-reads (WFR) on a three-node Cassandra 5.0.9 cluster. Every application operation delegated coordinator selection to the Python driver's token-aware, datacenter-aware policy. The verified evidence contains {len(trials)} main histories, {len(repairs)} read-repair attempts, and {len(timestamps)} timestamp controls. Main results comprise "
        f"{totals['violation']} violation witnesses, {totals['no_violation_observed']} completed histories without a witness, and {totals['inconclusive']} inconclusive histories.",
        "",
        "## System and installation",
        "",
        "The deployment uses three Docker containers in one datacenter (`dc1`) with NetworkTopologyStrategy replication factor 3. All three nodes own replicas for every experiment key. Cassandra is 5.0.9; the Python client image is 3.11.13 and uses cassandra-driver 3.29.2. Base images are pinned by digest. Hinted handoff is deliberately disabled, driver retries and speculative execution are disabled, and main tables use `read_repair=BLOCKING`.",
        "",
        "Install Docker Compose, allocate about 8 GB and four CPU cores, then run `python3 scripts/run_randomized.py --plan-only` followed by `python3 scripts/run_randomized.py --config config/cassandra_driver_experiments.json`. Validate using `python3 scripts/verify_randomized.py <run>` and build this report with `python3 scripts/build_report.py --results <run>`.",
        "",
        "## Configuration and predictions",
        "",
        "Configuration names are write/read levels. With RF=3, strict acknowledgement overlap for the restricted visibility test requires W+R>3. Quorum overlap does not establish general causal consistency or replica application order. Availability is reported independently from safety: a timeout or Unavailable response is inconclusive, not a consistency violation.",
        "",
        markdown_table(["Write/read", "RYW", "MR with BLOCKING", "MW/WFR observable"], predictions),
        "",
        "These predictions were registered before measurement. Driver routing may select the same coordinator repeatedly; coordinator choices were not filtered or overridden.",
        "",
        "## Experimental method",
        "",
        f"The {plan['profile']} matrix uses {plan['rounds']} attempt{'s' if plan['rounds'] != 1 else ''} for every selected model/configuration/scenario cell. Each trial starts with a unique key initialized to `(a=0,b=0)` at ALL. RYW tests write then read by one logical client. MR performs a producer write then two reads by one client. MW and WFR search for the observable counterexample `(a=0,b=1)`, where a successor is visible without its predecessor. This is a finite dependency-visibility test; it does not reconstruct every replica's execution order.",
        "",
        "The application supplies a partition routing key but no coordinator. TokenAwarePolicy first considers local replicas, while DCAwareRoundRobinPolicy supplies the local-datacenter ordering and fallback. Evidence saves driver-eligible hosts, attempted hosts, actual coordinator, requested consistency level, timing and response. Retries and speculative execution are disabled. Logical client identities preserve session order when coordinators change.",
        "",
        "For node failure, the runner samples a victim, records its container ID/IP, sends SIGKILL, proves the container stopped, and waits until both survivors report that exact IP as down in consecutive membership observations. It then runs the histories, restarts the same container with its volume retained, and waits for all three nodes to be healthy.",
        "",
        "For the network partition, the runner samples an isolated node and installs bilateral DROP rules for internode TCP ports 7000/7001 in a project-only OUTPUT chain. CQL 9042 remains available. It verifies all three client endpoints before measurement, saves membership views and post-workload packet counters, removes only project rules, and verifies recovery.",
        "",
        "## Results",
        "",
        markdown_table(["Scenario", "Write/read", "Model", "Attempts", "Violations", "No witness", "Inconclusive"], result_rows),
        "",
        "Outcome denominators: " + ", ".join(f"{key}={value}" for key, value in sorted(reasons.items())) + ".",
        "",
        "### Supplemental controls",
        "",
        markdown_table(["Read repair", "Attempts", "Regressions", "No regression", "Inconclusive"], repair_rows),
        "",
        f"Timestamp reversal: expected={timestamp_counts['expected']}, unexpected={timestamp_counts['unexpected']}, inconclusive={timestamp_counts['inconclusive']}. The control writes value 1 at T+100, then value 2 at T+50; Cassandra should retain the higher-timestamp value.",
        "",
        f"Random crash victims: {dict(victim_counts)}. Random partitioned nodes: {dict(isolated_counts)}.",
        "",
        "## Discussion and limitations",
        "",
        "A violation row is a concrete counterexample to the stated observable predicate under the recorded conditions. A no-witness row is only a finite observation. Inconclusive histories remain availability evidence and are never treated as safe histories. The report should compare the table above with the registered predictions; unexpected outcomes require inspection of their raw operations and fault episode before interpretation.",
        "",
        "The three containers share one physical host, RF equals node count, hints are disabled, and only one datacenter is tested. The experiments do not model disk loss, independent host failures, multi-datacenter latency, concurrent writers, arbitrary clock skew, or horizontal throughput scaling. Ten attempts meet the assignment minimum but offer limited statistical power. Cases within one fault episode share conditions and are not independent fault realizations. MW/WFR results concern the two-cell observable only and must not be generalized to universal causal consistency.",
        "",
        "## Reproducibility, sources, and AI use",
        "",
        f"The evidence validator accepted the evidence schema, all {validation['main_trials']} main histories, exact per-case coverage, {validation['read_repair_trials']} read-repair attempts, {validation['timestamp_trials']} timestamp controls, routing metadata, setup/fault links and recomputed verdicts. Runtime revision information and dirty-worktree status are preserved in `environment.json`; the root and derived random seeds are in `seeds.json`. The archive includes the selected evidence, configuration, experiment modules, source, tests, instructions and report.",
        "",
        "Sources: Apache Cassandra [Dynamo architecture](https://cassandra.apache.org/doc/5.0/cassandra/architecture/dynamo.html), [read repair](https://cassandra.apache.org/doc/5.0/cassandra/managing/operating/read_repair.html), [hints](https://cassandra.apache.org/doc/5.0/cassandra/managing/operating/hints.html), and [CQL DML](https://cassandra.apache.org/doc/5.0/cassandra/developing/cql/dml.html); DataStax Python driver 3.29 [load-balancing policies](https://docs.datastax.com/en/developer/python-driver/3.29/api/cassandra/policies/). Docker and Python package versions are recorded in the project Dockerfiles and requirements.",
        "",
        "OpenAI Codex assisted with design review, implementation, documentation lookup, code generation, testing, experiment orchestration, evidence validation, analysis and report generation. Database outcomes in this report come only from the verified saved evidence; AI did not invent or replace measurements. Group members must review the code, results and interpretations before submission.",
        "",
        f"Completion time: {completion.get('completed_utc')}. Root seed: {env.get('root_seed')}.",
    ]
    return "\n".join(lines) + "\n"


def render_pdf(markdown, pdf):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    story = []
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("# "):
            story.append(Paragraph(line[2:], styles["Title"]))
        elif line.startswith("## "):
            story.append(Spacer(1, 5)); story.append(Paragraph(line[3:], styles["Heading1"]))
        elif line.startswith("### "):
            story.append(Paragraph(line[4:], styles["Heading2"]))
        elif line.startswith("| "):
            table_lines = []
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index]); index += 1
            index -= 1
            rows = [[cell.strip() for cell in item.strip("|").split("|")] for item in table_lines]
            rows.pop(1)
            data = [[Paragraph(html.escape(cell), styles["Small"]) for cell in row] for row in rows]
            width = (A4[0] - 30 * mm) / len(data[0])
            table = Table(data, colWidths=[width] * len(data[0]), repeatRows=1)
            table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#dce6f1")),
                ("GRID", (0,0), (-1,-1), .35, colors.grey), ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3)]))
            story.append(table)
        elif line.startswith("- "):
            story.append(Paragraph("• " + line[2:], styles["BodyText"]))
        elif line.strip():
            safe = html.escape(line.replace("`", ""))
            story.append(Paragraph(safe, styles["BodyText"]))
        else:
            story.append(Spacer(1, 4))
        index += 1

    def footer(canvas, document):
        canvas.saveState(); canvas.setFont("Helvetica", 8); canvas.setFillColor(colors.grey)
        canvas.drawString(15 * mm, 10 * mm, "Cassandra driver-policy consistency experiments")
        canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, str(document.page)); canvas.restoreState()
    doc = SimpleDocTemplate(str(pdf), pagesize=A4, rightMargin=15*mm, leftMargin=15*mm,
                            topMargin=14*mm, bottomMargin=16*mm,
                            title="Client-centric consistency in Apache Cassandra")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def verify_source_manifest(environment):
    recorded = environment.get("source_manifest_sha256")
    if not isinstance(recorded, dict) or not recorded:
        raise ValueError("evidence lacks a source manifest")
    changed = []
    for relative, expected in recorded.items():
        path = ROOT / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual != expected:
            changed.append(relative)
    if changed:
        raise ValueError("current source differs from measured source: " + ", ".join(changed))


def package(run, outputs, prefix="driver_policy"):
    include = [ROOT / name for name in ("README.md", "WORK_IN_PROGRESS.md", "Project_Assignment.md",
               "AGENT_ACTION_PLAN.md", "compose.yaml", "Dockerfile.cassandra", "Dockerfile.client",
               "requirements-report.txt", "report/predictions.md", "report/authors.json")]
    for directory in ("config", "docs", "experiments", "src", "scripts", "tests"):
        include.extend(path for path in (ROOT / directory).rglob("*")
                       if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc")
    include.extend(path for path in run.rglob("*") if path.is_file())
    include.extend(outputs)
    unique = sorted(set(include))
    sums = "".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT)}\n"
                   for path in unique)
    checksum = ROOT / f"report/{prefix}_SHA256SUMS.txt"
    checksum.write_text(sums)
    archive = ROOT / f"report/{prefix}_submission.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in unique + [checksum]:
            bundle.write(path, path.relative_to(ROOT))
    return checksum, archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True,
                        help="explicit driver-policy evidence directory; latest-run selection is forbidden")
    parser.add_argument("--allow-smoke", action="store_true",
                        help="render a clearly labelled smoke artifact for integration testing")
    args = parser.parse_args()
    run = args.results.resolve()
    validation = verify(run)
    plan = load(run / "plan.json")
    if plan.get("profile") != "full" and not args.allow_smoke:
        parser.error("refusing a submission report from smoke evidence; use --allow-smoke only for QA")
    verify_source_manifest(load(run / "environment.json"))
    report_dir = ROOT / "report"
    report_dir.mkdir(exist_ok=True)
    prefix = "Driver_Policy" if plan.get("profile") == "full" else "Smoke_Driver_Policy"
    markdown_path = report_dir / f"{prefix}_Cassandra_Consistency_Report.md"
    pdf_path = report_dir / f"{prefix}_Cassandra_Consistency_Report.pdf"
    markdown = build_markdown(run, validation)
    markdown_path.write_text(markdown)
    render_pdf(markdown, pdf_path)
    try:
        import fitz
        qa = report_dir / "qa_driver_policy"
        qa.mkdir(exist_ok=True)
        document = fitz.open(pdf_path)
        for number, page in enumerate(document, 1):
            page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2)).save(qa / f"page-{number:02}.png")
    except ImportError:
        pass
    checksum, archive = package(run, [markdown_path, pdf_path], prefix.lower())
    print(json.dumps({"report": str(pdf_path), "markdown": str(markdown_path),
                      "checksums": str(checksum), "archive": str(archive),
                      "validation": validation}, indent=2))


if __name__ == "__main__":
    main()
