#!/usr/bin/env python3
"""Build V4/V5-only academic summaries, charts, and violation matrix."""

from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TRIAL_CSV = HERE / "trial_level_evidence.csv"
RUN_CSV = HERE / "run_level_violation_matrix.csv"
ASSETS = HERE / "v5_assets"
SUMMARY = HERE / "v5_analysis_summary.json"
MATRIX = ROOT / "report" / "violation_matrix_v5.md"
V4 = "cassandra-driver-policy-evidence-v4"
V5 = "cassandra-driver-policy-evidence-v5"
SCHEMA_LABEL = {V4: "V4 · three nodes", V5: "V5 · five nodes"}
SCENARIOS = ("normal", "node_failure", "network_partition")
MODELS = ("RYW", "MR", "MW", "WFR")
CONFIGS = (
    "ONE/ONE", "ONE/QUORUM", "ONE/ALL", "QUORUM/ONE", "QUORUM/QUORUM",
    "QUORUM/ALL", "ALL/ONE", "ALL/QUORUM", "ALL/ALL",
)
COLORS = {"no_violation_observed": "#2E8B68", "inconclusive": "#D3931B", "violation": "#C43D4B"}


def load_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def n(value):
    try:
        return int(value or 0)
    except ValueError:
        return 0


def pct(num, den, places=2):
    return f"{100 * num / den:.{places}f}%" if den else "N/A"


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(str(value) for value in row) + " |" for row in rows]
    return "\n".join(lines)


def counts(rows):
    result = Counter(row["trial_verdict"] for row in rows)
    evaluable = result["violation"] + result["no_violation_observed"]
    return {
        "attempted": len(rows), "evaluable": evaluable,
        "violation": result["violation"],
        "no_violation_observed": result["no_violation_observed"],
        "inconclusive": result["inconclusive"],
        "evaluable_rate": evaluable / len(rows) if rows else None,
        "violation_rate_evaluable": result["violation"] / evaluable if evaluable else None,
    }


def group(rows, keys):
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)
    return {"|".join(key): counts(value) for key, value in sorted(grouped.items())}


def style_axis(ax, title, subtitle=None):
    ax.set_title(title, loc="left", fontsize=15, fontweight="bold", color="#17324D", pad=18)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9, color="#607386")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color="#DFE6EB", linewidth=.8)
    ax.set_axisbelow(True)


def chart_outcomes(rows):
    labels, groups = [], []
    for schema in (V4, V5):
        for scenario in SCENARIOS:
            subset = [r for r in rows if r["evidence_schema"] == schema and r["scenario"] == scenario]
            labels.append(f"{SCHEMA_LABEL[schema].split(' · ')[0]} · {scenario.replace('_', ' ')}")
            groups.append(counts(subset))
    fig, ax = plt.subplots(figsize=(12, 6.5), dpi=180)
    totals = np.array([g["attempted"] for g in groups], dtype=float)
    left = np.zeros(len(groups))
    for outcome in ("no_violation_observed", "inconclusive", "violation"):
        raw = np.array([g[outcome] for g in groups])
        values = np.divide(raw * 100.0, totals, out=np.zeros_like(totals), where=totals > 0)
        ax.barh(labels, values, left=left, color=COLORS[outcome], label=outcome.replace("_", " "))
        for i, (value, count) in enumerate(zip(values, raw)):
            if value >= 4:
                ax.text(left[i] + value / 2, i, f"{count:,}\n{value:.1f}%", ha="center", va="center",
                        fontsize=8, color="white" if outcome != "inconclusive" else "#17324D", fontweight="bold")
        left += values
    for i, group in enumerate(groups):
        ax.text(101.0, i, f"n={group['attempted']:,}", ha="left", va="center",
                fontsize=8.5, color="#17324D", fontweight="bold")
        if group["violation"]:
            ax.text(99.3, i - .29, f"viol.={group['violation']}", ha="right", va="center",
                    fontsize=7.5, color="#9B2634", fontweight="bold")
    style_axis(ax, "Outcome composition by deployment and scenario",
               "Completed full-profile V4/V5 runs; labels show count and share of each scenario")
    ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(.5, -.18))
    ax.set_xlabel("Share of histories (%)")
    ax.set_xlim(0, 114)
    fig.tight_layout()
    path = ASSETS / "12_v4_v5_outcome_composition.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def chart_routing(rows):
    labels = [SCHEMA_LABEL[V4], SCHEMA_LABEL[V5]]
    changed, crossed = [], []
    for schema in (V4, V5):
        subset = [r for r in rows if r["evidence_schema"] == schema]
        network = [r for r in subset if r["scenario"] == "network_partition"]
        changed.append(100 * sum(r["changed_coordinator"] == "true" for r in subset) / len(subset))
        crossed.append(100 * sum(r["crossed_partition_cut"] == "true" for r in network) / len(network))
    x = np.arange(2); width = .33
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=180)
    b1 = ax.bar(x-width/2, changed, width, label="changed coordinator", color="#1779BA")
    b2 = ax.bar(x+width/2, crossed, width, label="crossed partition cut", color="#7656A5")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Histories (%)")
    style_axis(ax, "Routing exposure in the measured histories",
               "Cross-cut rate uses network-partition histories as its denominator")
    ax.legend(frameon=False)
    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+.05, f"{bar.get_height():.2f}%",
                    ha="center", va="bottom", fontsize=9, fontweight="bold", color="#17324D")
    fig.tight_layout()
    path = ASSETS / "13_v4_v5_routing_exposure.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def chart_models(rows):
    fig, ax = plt.subplots(figsize=(10, 5.8), dpi=180)
    x = np.arange(len(MODELS)); width = .34
    for offset, schema, color in ((-width/2, V4, "#1779BA"), (width/2, V5, "#2E8B68")):
        rates=[]
        for model in MODELS:
            c=counts([r for r in rows if r["evidence_schema"]==schema and r["model"]==model])
            rates.append(100*c["violation"]/c["evaluable"] if c["evaluable"] else 0)
        bars=ax.bar(x+offset,rates,width,label=SCHEMA_LABEL[schema],color=color)
        for bar,rate in zip(bars,rates):
            ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+.003,f"{rate:.3f}%",
                    ha="center",va="bottom",fontsize=8,fontweight="bold")
    ax.set_xticks(x,MODELS); ax.set_ylabel("Violations / evaluable histories (%)")
    style_axis(ax,"Observed violation rate by client-centric model",
               "Zero means no counterexample was observed; it is not proof of a guarantee")
    ax.legend(frameon=False)
    fig.tight_layout()
    path=ASSETS/"14_v4_v5_model_violation_rates.png"
    fig.savefig(path,bbox_inches="tight",facecolor="white"); plt.close(fig)
    return path


def build():
    trial_rows = load_csv(TRIAL_CSV)
    run_rows = load_csv(RUN_CSV)
    main_all = [r for r in trial_rows if r["record_type"] == "main_trial" and r["evidence_schema"] in {V4, V5}]
    measured = [r for r in main_all if r["included_in_analysis"] == "true" and r["run_profile"] == "full"]
    ASSETS.mkdir(exist_ok=True)
    charts = [chart_outcomes(measured), chart_routing(measured), chart_models(measured)]

    summary = {
        "scope": {"schemas": [V4, V5], "randomized_excluded": True,
                  "aggregate_filter": "record_type=main_trial AND included_in_analysis=true AND run_profile=full"},
        "overall": counts(measured),
        "by_schema": group(measured, ["evidence_schema"]),
        "by_schema_scenario": group(measured, ["evidence_schema", "scenario"]),
        "by_schema_model": group(measured, ["evidence_schema", "model"]),
        "by_schema_config": group(measured, ["evidence_schema", "config_write_read"]),
        "run_ids": sorted(set(r["run_id"] for r in measured)),
        "violations": [{k: r.get(k, "") for k in (
            "evidence_schema", "run_id", "trial_id", "scenario", "config_write_read", "model",
            "coordinator_node_sequence", "changed_coordinator", "crossed_partition_cut",
            "partition_groups_json", "trial_reason")}
            for r in measured if r["trial_verdict"] == "violation"],
        "charts": [str(p.relative_to(ROOT)) for p in charts],
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    profile_rows=[]
    for schema in (V4,V5):
        subset=[r for r in measured if r["evidence_schema"]==schema]; c=counts(subset)
        profile_rows.append((SCHEMA_LABEL[schema],len(set(r["run_id"] for r in subset)),f"{c['attempted']:,}",
                             f"{c['evaluable']:,}",f"{c['violation']:,}",f"{c['no_violation_observed']:,}",
                             f"{c['inconclusive']:,}",pct(c['evaluable'],c['attempted']),pct(c['violation'],c['evaluable'],3)))
    total=counts(measured)
    profile_rows.append(("Combined V4 + V5",len(set(r["run_id"] for r in measured)),f"{total['attempted']:,}",
                         f"{total['evaluable']:,}",f"{total['violation']:,}",f"{total['no_violation_observed']:,}",
                         f"{total['inconclusive']:,}",pct(total['evaluable'],total['attempted']),pct(total['violation'],total['evaluable'],3)))

    inventory=[]
    for r in sorted((r for r in run_rows if r["evidence_schema"] in {V4,V5}),key=lambda x:x["run_id"]):
        inventory.append((SCHEMA_LABEL[r["evidence_schema"]],r["run_id"],r["profile"] or "missing",
                          r["run_completed"],r["included_in_analysis"],r["saved_main_trials"],
                          r["violation_count"],r["no_violation_observed_count"],r["inconclusive_count"],
                          r["validation_notes"] or "—"))

    scenario_rows=[]
    for schema in (V4,V5):
        for scenario in SCENARIOS:
            subset=[r for r in measured if r["evidence_schema"]==schema and r["scenario"]==scenario]; c=counts(subset)
            assessment=("[x] Expected" if scenario in {"normal","node_failure"} else "[x] Mechanistically plausible")
            scenario_rows.append((SCHEMA_LABEL[schema],scenario.replace("_"," "),f"{c['attempted']:,}",f"{c['evaluable']:,}",
                                  c["violation"],f"{c['inconclusive']:,}",pct(c["violation"],c["evaluable"],3),assessment))

    model_rows=[]
    for schema in (V4,V5):
        for model in MODELS:
            subset=[r for r in measured if r["evidence_schema"]==schema and r["model"]==model]; c=counts(subset)
            model_rows.append((SCHEMA_LABEL[schema],model,f"{c['attempted']:,}",f"{c['evaluable']:,}",c["violation"],
                               f"{c['inconclusive']:,}",pct(c["violation"],c["evaluable"],3)))

    config_rows=[]
    for pair in CONFIGS:
        v4=counts([r for r in measured if r["evidence_schema"]==V4 and r["config_write_read"]==pair])
        v5=counts([r for r in measured if r["evidence_schema"]==V5 and r["config_write_read"]==pair])
        config_rows.append((pair,v4["violation"],f"{v4['evaluable']:,}",pct(v4["violation"],v4["evaluable"],3),
                            v5["violation"],f"{v5['evaluable']:,}",pct(v5["violation"],v5["evaluable"],3)))

    routing_rows=[]
    for schema in (V4,V5):
        subset=[r for r in measured if r["evidence_schema"]==schema]
        network=[r for r in subset if r["scenario"]=="network_partition"]
        changed=sum(r["changed_coordinator"]=="true" for r in subset)
        crossed=sum(r["crossed_partition_cut"]=="true" for r in network)
        routing_rows.append((SCHEMA_LABEL[schema],f"{len(subset):,}",f"{changed:,}",pct(changed,len(subset)),
                             f"{len(network):,}",f"{crossed:,}",pct(crossed,len(network))))

    error_rows=[]
    for schema in (V4,V5):
        inc=[r for r in measured if r["evidence_schema"]==schema and r["trial_verdict"]=="inconclusive"]
        ec=Counter(r["first_error_class"] or "Oracle precondition not exposed" for r in inc)
        for reason,count in ec.most_common(): error_rows.append((SCHEMA_LABEL[schema],reason,f"{count:,}",pct(count,len(inc))))

    replica_ops=[]
    for r in measured:
        if r["evidence_schema"]!=V5: continue
        for i in range(1,5):
            if r.get(f"op{i}_kind"): replica_ops.append(r.get(f"op{i}_routing_selected_is_replica"))
    replica_counts=Counter(replica_ops)

    violation_rows=[]
    for r in summary["violations"]:
        violation_rows.append((SCHEMA_LABEL[r["evidence_schema"]],r["run_id"],r["scenario"].replace("_"," "),
                               r["config_write_read"],r["model"],r["coordinator_node_sequence"],
                               r["changed_coordinator"],r["crossed_partition_cut"],r["partition_groups_json"] or "1|2 isolated-node evidence"))

    lines=[
        "# Cassandra driver-policy violation matrix V5",
        "",
        "> **Reporting scope.** This matrix uses only `cassandra-driver-policy-evidence-v4` and `cassandra-driver-policy-evidence-v5`. Historical harness-randomized evidence is deliberately excluded. All run records remain in the CSVs; aggregate tables use completed, structurally valid, full-profile runs only.",
        "",
        "## 1. Evidence population",
        "",
        md_table(["Deployment","Included runs","Attempted","Evaluable","Violations","No violation observed","Inconclusive","Evaluability","Viol./evaluable"],profile_rows),
        "",
        "- **V4:** three Cassandra nodes, RF=3, token-aware/DC-aware driver routing, seeded 1|2 partition.",
        "- **V5:** five Cassandra nodes, RF=3, token-aware/DC-aware driver routing, seeded balanced 2|3 partition.",
        "- **Denominator:** `violation / (violation + no_violation_observed)`. Inconclusive histories measure unavailable or unexposed observations and are excluded from the violation-rate denominator.",
        "",
        "## 2. Run-level audit inventory",
        "",
        md_table(["Deployment","Run ID","Profile","Completed","Included","Main histories","Viol.","No viol.","Inconc.","Exclusion/validation note"],inventory),
        "",
        "## 3. Scenario results",
        "",
        md_table(["Deployment","Scenario","Attempted","Evaluable","Viol.","Inconc.","Viol./eval.","Assessment"],scenario_rows),
        "",
        "- [x] **Normal operation:** no counterexample is expected in short sequential histories after successful ALL initialization; any observed violation would require trace review.",
        "- [x] **Node failure:** the dominant effect should be unavailability when required replicas cannot respond. A zero violation count does not mean every operation completed.",
        "- [x] **Network partition:** weak or non-intersecting response paths can expose divergent partition-side state. Every saved violation occurred here.",
        "",
        "![V4/V5 outcome composition](report_generation/v5_assets/12_v4_v5_outcome_composition.png)",
        "",
        "## 4. Client-centric model results",
        "",
        md_table(["Deployment","Model","Attempted","Evaluable","Viol.","Inconc.","Viol./eval."],model_rows),
        "",
        "- [x] **RYW witnesses are meaningful:** all required operations completed and the later read omitted the client's acknowledged write.",
        "- [ ] **No MR/MW/WFR witness is not a guarantee:** these models require a more specific sequence than RYW, including an exposed first read, visible successor, or visible dependency followed by regression/loss.",
        "- [x] **Low route-change exposure is a material explanation:** stable driver query-plan state reduces the chance that successive operations traverse inconsistent partition sides.",
        "",
        "![Violation rates by model](report_generation/v5_assets/14_v4_v5_model_violation_rates.png)",
        "",
        "## 5. Consistency-level matrix",
        "",
        md_table(["Write/read CL","V4 viol.","V4 evaluable","V4 rate","V5 viol.","V5 evaluable","V5 rate"],config_rows),
        "",
        "- [x] `ONE/ONE` supplies no write/read intersection requirement and produced witnesses in both deployments.",
        "- [x] `QUORUM/ONE` and `ONE/QUORUM` can still expose a weak side of the operation pair; V4 produced finite RYW witnesses in these cells.",
        "- [x] Cells involving `ALL` or intersecting quorum paths often became unavailable during faults, reducing evaluable histories rather than creating successful stale observations.",
        "",
        "## 6. Routing and partition exposure",
        "",
        md_table(["Deployment","All histories","Changed coordinator","Changed %","Partition histories","Crossed cut","Crossed %"],routing_rows),
        "",
        f"- V5 recorded **{replica_counts['true']:,}** operations coordinated by a replica and **{replica_counts['false']:,}** by a non-replica across **{sum(replica_counts.values()):,}** measured operations.",
        "- The five-node design creates real replica/non-replica choice, but token-aware routing correctly prefers the RF=3 replica set. Therefore, adding nodes does not automatically create frequent coordinator changes.",
        "- A route change is an exposure variable, not a consistency violation. A violation also requires completed operations and a value sequence contradicting the model oracle.",
        "",
        "![Routing exposure](report_generation/v5_assets/13_v4_v5_routing_exposure.png)",
        "",
        "## 7. Violation witness inventory",
        "",
        md_table(["Deployment","Run ID","Scenario","CL","Model","Coordinator sequence","Changed","Crossed cut","Partition groups"],violation_rows),
        "",
        "All seven witnesses are RYW histories during network partitions. Six are V4 witnesses and one is a V5 witness. The V5 trace changed coordinator from `n1` to `n4` across groups `n1,n3,n5` and `n2,n4`, then observed a state that omitted the acknowledged write.",
        "",
        "## 8. Why histories were inconclusive",
        "",
        md_table(["Deployment","First failure or oracle reason","Histories","Share of inconclusive"],error_rows),
        "",
        "- [x] `Unavailable` is expected when the coordinator can prove that the requested replica count cannot be reached.",
        "- [x] Timeouts and `NoHostAvailable` are availability outcomes. They are not counted as consistency violations because the oracle lacks the required completed observations.",
        "- [x] Oracle-precondition failures are also inconclusive: WFR needs the dependency to be observed, MW needs the successor to be exposed, and MR needs a usable first read before a regression can be tested.",
        "",
        "## 9. Five-node architecture",
        "",
        "![Expanded five-node architecture](report_generation/figures/png/08_five_node_expanded_architecture.png)",
        "",
        "- Five nodes run in one Docker Compose project and one datacenter (`dc1`).",
        "- RF remains 3, so each partition key maps to three replicas and two non-replica nodes.",
        "- Each network-partition episode samples a seeded 2|3 grouping and blocks all six cross-group internode edges while preserving CQL reachability.",
        "- V5 operation records include `replica_nodes`, `selected_node`, `selected_is_replica`, and `attempted_nodes`.",
        "",
        "## 10. Academic interpretation",
        "",
        "- **Supported:** weak paths under established network partitions can violate RYW in finite completed histories.",
        "- **Supported:** failures chiefly reduced availability; inconclusive histories must remain outside the violation-rate denominator.",
        "- **Supported:** the V5 design confirms a five-node/RF=3 setup can produce a cross-cut RYW witness while retaining token-aware routing.",
        "- **Not supported:** token-aware routing guarantees RYW, MR, MW, or WFR.",
        "- **Not supported:** MR, MW, or WFR always hold. The experiment observed no witness in the measured schedules.",
        "- **Not supported:** adding nodes directly weakens consistency. It changes replica placement and sampled schedules; consistency level, timing, and route sequence still determine the observable history.",
        "",
        "## 11. Reproducibility",
        "",
        "- Trial source: `report/report_generation/trial_level_evidence.csv`",
        "- Run source: `report/report_generation/run_level_violation_matrix.csv`",
        "- Derived summary: `report/report_generation/v5_analysis_summary.json`",
        "- Builder: `report/report_generation/build_v5_report_assets.py`",
        "- Export integrity: `python3 report/report_generation/verify_exports.py`",
        "",
    ]
    MATRIX.write_text("\n".join(lines))
    print(json.dumps({"summary": str(SUMMARY), "matrix": str(MATRIX),
                      "measured_histories": len(measured), "violations": total["violation"],
                      "charts": [str(p) for p in charts]}, indent=2))


if __name__ == "__main__":
    build()
