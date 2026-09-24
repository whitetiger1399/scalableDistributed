#!/usr/bin/env python3
"""Build a V4-only academic violation matrix, summary, and charts."""
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
ASSETS = HERE / "v7_assets"
SUMMARY = HERE / "v7_analysis_summary.json"
MATRIX = ROOT / "report" / "violation_matrix_v7.md"
SCHEMA = "cassandra-driver-policy-evidence-v4"
SCENARIOS = ("normal", "node_failure", "network_partition")
MODELS = ("RYW", "MR", "MW", "WFR")
CONFIGS = ("ONE/ONE", "ONE/QUORUM", "ONE/ALL", "QUORUM/ONE", "QUORUM/QUORUM",
           "QUORUM/ALL", "ALL/ONE", "ALL/QUORUM", "ALL/ALL")
COLORS = {"no_violation_observed": "#2E8B68", "inconclusive": "#D3931B", "violation": "#C43D4B"}


def load(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def counts(rows):
    c = Counter(r["trial_verdict"] for r in rows)
    evaluable = c["violation"] + c["no_violation_observed"]
    return {"attempted": len(rows), "evaluable": evaluable, "violation": c["violation"],
            "no_violation_observed": c["no_violation_observed"], "inconclusive": c["inconclusive"]}


def pct(a, b, places=2):
    return f"{100*a/b:.{places}f}%" if b else "N/A"


def table(headers, rows):
    result = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    result.extend("| " + " | ".join(str(v) for v in row) + " |" for row in rows)
    return "\n".join(result)


def style(ax, title, subtitle):
    ax.set_title(title, loc="left", fontsize=15, fontweight="bold", color="#17324D", pad=18)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9, color="#607386")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color="#DFE6EB", linewidth=.8)
    ax.set_axisbelow(True)


def chart_scenarios(rows):
    groups = [counts([r for r in rows if r["scenario"] == s]) for s in SCENARIOS]
    totals = np.array([g["attempted"] for g in groups], dtype=float)
    left = np.zeros(3)
    fig, ax = plt.subplots(figsize=(10.5, 5.2), dpi=180)
    labels = [s.replace("_", " ") for s in SCENARIOS]
    for outcome in ("no_violation_observed", "inconclusive", "violation"):
        raw = np.array([g[outcome] for g in groups])
        values = raw * 100 / totals
        ax.barh(labels, values, left=left, color=COLORS[outcome], label=outcome.replace("_", " "))
        for i, (value, number) in enumerate(zip(values, raw)):
            if value >= 3:
                ax.text(left[i] + value/2, i, f"{number:,}\n{value:.1f}%", ha="center", va="center",
                        fontsize=8, fontweight="bold", color="white" if outcome != "inconclusive" else "#17324D")
        left += values
    for i, group in enumerate(groups):
        ax.text(101, i, f"n={group['attempted']:,}", va="center", color="#17324D", fontweight="bold", fontsize=8.5)
        if group["violation"]:
            ax.text(99.2, i-.27, f"viol.={group['violation']}", ha="right", color="#9B2634", fontweight="bold", fontsize=8)
    style(ax, "V4 outcome composition by scenario", "Completed full-profile three-node driver-policy runs")
    ax.set_xlim(0, 114); ax.set_xlabel("Share of histories (%)")
    ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(.5, -.24))
    fig.tight_layout(); path = ASSETS / "15_v4_outcomes_by_scenario.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white"); plt.close(fig); return path


def chart_models(rows):
    values=[]; labels=[]; violations=[]
    for model in MODELS:
        c=counts([r for r in rows if r["model"]==model])
        labels.append(model); violations.append(c["violation"])
        values.append(100*c["violation"]/c["evaluable"] if c["evaluable"] else 0)
    fig,ax=plt.subplots(figsize=(8.5,4.8),dpi=180)
    bars=ax.bar(labels,values,color=["#1779BA","#94A8B8","#94A8B8","#94A8B8"])
    ceiling=max(values) if max(values) else 1
    ax.set_ylim(0,ceiling*1.28)
    for bar,rate,num in zip(bars,values,violations):
        ax.text(bar.get_x()+bar.get_width()/2,rate+ceiling*.035,f"{rate:.3f}%\n({num} witnesses)",ha="center",fontsize=8,fontweight="bold")
    style(ax,"V4 observed violation rate by model","Violations divided by evaluable histories; zero is not proof of a guarantee")
    ax.set_ylabel("Violations / evaluable histories (%)")
    fig.tight_layout(); path=ASSETS/"16_v4_model_violation_rates.png"
    fig.savefig(path,bbox_inches="tight",facecolor="white"); plt.close(fig); return path


def chart_configs(rows):
    rates=[]; violations=[]
    for config in CONFIGS:
        c=counts([r for r in rows if r["config_write_read"]==config])
        rates.append(100*c["violation"]/c["evaluable"] if c["evaluable"] else 0); violations.append(c["violation"])
    fig,ax=plt.subplots(figsize=(11,5.2),dpi=180)
    bars=ax.bar(CONFIGS,rates,color=["#C43D4B" if n else "#8FA6B7" for n in violations])
    ax.tick_params(axis="x",rotation=35)
    ceiling=max(rates) if max(rates) else 1
    ax.set_ylim(0,ceiling*1.28)
    for bar,rate,num in zip(bars,rates,violations):
        ax.text(bar.get_x()+bar.get_width()/2,rate+ceiling*.035,f"{rate:.3f}%\n({num})",ha="center",fontsize=7.5,fontweight="bold")
    style(ax,"V4 observed violation rate by consistency pair","Configuration notation is write/read; labels include witness count")
    ax.set_ylabel("Violations / evaluable histories (%)")
    fig.tight_layout(); path=ASSETS/"17_v4_consistency_pair_rates.png"
    fig.savefig(path,bbox_inches="tight",facecolor="white"); plt.close(fig); return path


def build():
    trials = load(TRIAL_CSV); runs = load(RUN_CSV)
    all_v4 = [r for r in trials if r["evidence_schema"] == SCHEMA and r["record_type"] == "main_trial"]
    measured = [r for r in all_v4 if r["included_in_analysis"] == "true" and r["run_profile"] == "full"]
    run_v4 = [r for r in runs if r["evidence_schema"] == SCHEMA]
    ASSETS.mkdir(exist_ok=True)
    charts = [chart_scenarios(measured), chart_models(measured), chart_configs(measured)]

    overall=counts(measured)
    scenario_rows=[]
    for s in SCENARIOS:
        c=counts([r for r in measured if r["scenario"]==s])
        assessment="[x] Expected" if s!="network_partition" else "[x] Mechanistically plausible"
        scenario_rows.append((s.replace("_"," "),f"{c['attempted']:,}",f"{c['evaluable']:,}",c["violation"],
                              f"{c['no_violation_observed']:,}",f"{c['inconclusive']:,}",pct(c["violation"],c["evaluable"],3),assessment))
    model_rows=[]
    for m in MODELS:
        c=counts([r for r in measured if r["model"]==m])
        model_rows.append((m,f"{c['attempted']:,}",f"{c['evaluable']:,}",c["violation"],f"{c['no_violation_observed']:,}",
                           f"{c['inconclusive']:,}",pct(c["violation"],c["evaluable"],3)))
    config_rows=[]
    for config in CONFIGS:
        c=counts([r for r in measured if r["config_write_read"]==config])
        config_rows.append((config,f"{c['attempted']:,}",f"{c['evaluable']:,}",c["violation"],f"{c['inconclusive']:,}",pct(c["violation"],c["evaluable"],3)))
    inventory=[]
    for r in sorted(run_v4,key=lambda x:x["run_id"]):
        inventory.append((r["run_id"],r["profile"] or "missing",r["run_completed"],r["included_in_analysis"],
                          r["saved_main_trials"],r["violation_count"],r["no_violation_observed_count"],r["inconclusive_count"],r["validation_notes"] or "—"))
    violations=[r for r in measured if r["trial_verdict"]=="violation"]
    witness_rows=[(r["run_id"],r["trial_id"],r["config_write_read"],r["model"],r["coordinator_node_sequence"],
                   r["changed_coordinator"],r["crossed_partition_cut"],
                   r["trial_reason"] or "Later read omitted acknowledged write") for r in violations]
    inc=[r for r in measured if r["trial_verdict"]=="inconclusive"]
    error_counts=Counter(r["first_error_class"] or "Oracle precondition not exposed" for r in inc)
    error_rows=[(reason,f"{num:,}",pct(num,len(inc)),"Availability outcome" if reason!="Oracle precondition not exposed" else "Coverage exclusion") for reason,num in error_counts.most_common()]
    changed=sum(r["changed_coordinator"]=="true" for r in measured)
    partitions=[r for r in measured if r["scenario"]=="network_partition"]
    crossed=sum(r["crossed_partition_cut"]=="true" for r in partitions)

    cell_rows=[]; cell_summary={}
    for model in MODELS:
        for config in CONFIGS:
            for scenario in SCENARIOS:
                subset=[r for r in measured if r["model"]==model and r["config_write_read"]==config and r["scenario"]==scenario]
                c=counts(subset); key=f"{scenario}|{config}|{model}"; cell_summary[key]=c
                cell_rows.append((model,config,scenario.replace("_"," "),c["violation"],c["no_violation_observed"],
                                  c["inconclusive"],c["evaluable"],c["attempted"],pct(c["violation"],c["evaluable"],3)))

    summary={"scope":{"evidence_schema":SCHEMA,"design":"cassandra-driver-policy-v3",
                       "aggregate_filter":"record_type=main_trial AND included_in_analysis=true AND run_profile=full"},
             "overall":overall,"included_run_ids":sorted({r["run_id"] for r in measured}),
             "scenario":{s:counts([r for r in measured if r["scenario"]==s]) for s in SCENARIOS},
             "model":{m:counts([r for r in measured if r["model"]==m]) for m in MODELS},
             "configuration":{c:counts([r for r in measured if r["config_write_read"]==c]) for c in CONFIGS},
             "cells":cell_summary,"routing":{"changed_coordinator":changed,"crossed_partition_cut":crossed,
                       "partition_histories":len(partitions)},
             "violations":[{k:r.get(k,"") for k in ("run_id","trial_id","scenario","config_write_read","model","coordinator_node_sequence","trial_reason")} for r in violations],
             "charts":[str(p.relative_to(ROOT)) for p in charts]}
    SUMMARY.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")

    lines=[
        "# Cassandra driver-policy violation matrix V7 — V4 only", "",
        "> **Scope.** This document reports only `cassandra-driver-policy-evidence-v4` produced by design `cassandra-driver-policy-v3`. Aggregates use completed, structurally valid, full-profile runs. Smoke and incomplete V4 runs appear only in the audit inventory.", "",
        "## 1. Experimental setup", "",
        "- **Cluster:** three Cassandra nodes (`n1`, `n2`, `n3`) in one datacenter (`dc1`).",
        "- **Replication:** `NetworkTopologyStrategy`, RF=3; every node is a replica for each experiment key.",
        "- **Routing:** `TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc=\"dc1\"))`; the application supplies a routing key and does not select a coordinator.",
        "- **Scenarios:** normal operation, one abrupt node failure, and an established 1|2 internode network partition.",
        "- **Consistency pairs:** the notation is write/read consistency over `ONE`, `QUORUM`, and `ALL`.",
        "- **Models:** RYW, MR, MW, and WFR.", "",
        "![Three-node token-aware routing](report_generation/figures/png/07_token_aware_driver_policy_detail.png)", "",
        "## 2. Evidence population", "",
        table(["Included full runs","Attempted","Evaluable","Violations","No violation observed","Inconclusive","Evaluability","Viol./evaluable"],
              [(len(summary["included_run_ids"]),f"{overall['attempted']:,}",f"{overall['evaluable']:,}",overall["violation"],
                f"{overall['no_violation_observed']:,}",f"{overall['inconclusive']:,}",pct(overall["evaluable"],overall["attempted"]),pct(overall["violation"],overall["evaluable"],3))]), "",
        "- **Primary denominator:** `violation / (violation + no_violation_observed)`.",
        "- Inconclusive histories are retained for availability and coverage analysis but excluded from the violation-rate denominator.",
        "- A no-violation outcome describes one finite history; it is not proof of a universal Cassandra guarantee.", "",
        "## 3. Run-level audit inventory", "",
        table(["Run ID","Profile","Completed","Included","Main histories","Viol.","No viol.","Inconc.","Note"],inventory), "",
        "The five rows with `Included=true` form every aggregate below. The smoke run and four incomplete runs do not contribute to any result denominator.", "",
        "## 4. Outcomes by scenario", "",
        table(["Scenario","Attempted","Evaluable","Viol.","No viol.","Inconc.","Viol./eval.","Assessment"],scenario_rows), "",
        "- [x] **Normal operation:** all histories were evaluable and no counterexample was observed.",
        "- [x] **Node failure:** the dominant effect was unavailability when the required replica count could not be reached; no successful stale witness was recorded.",
        "- [x] **Network partition:** all six counterexamples occurred here and crossed the recorded cut.", "",
        "![Outcome composition](report_generation/v7_assets/15_v4_outcomes_by_scenario.png)", "",
        "## 5. Client-centric model findings", "",
        table(["Model","Attempted","Evaluable","Viol.","No viol.","Inconc.","Viol./eval."],model_rows), "",
        "- [x] **RYW:** six finite counterexamples show that token-aware routing does not itself provide read-your-writes across a partition.",
        "- [ ] **MR, MW, and WFR:** no counterexample was observed. This is not a guarantee; each oracle requires a specific completed regression or causal-visibility pattern.",
        "- Stable query-plan order and operation unavailability reduced the number of histories that changed coordinator and crossed the cut.", "",
        "![Model violation rates](report_generation/v7_assets/16_v4_model_violation_rates.png)", "",
        "## 6. Consistency-level results", "",
        table(["Write/read CL","Attempted","Evaluable","Viol.","Inconc.","Viol./eval."],config_rows), "",
        "- [x] `ONE/ONE` has no acknowledgement/read intersection requirement and produced three witnesses.",
        "- [x] `ONE/QUORUM` and `QUORUM/ONE` do not satisfy `W + R > RF` for RF=3 and produced one and two witnesses respectively.",
        "- [x] `QUORUM/QUORUM` satisfies `2 + 2 > 3` and produced no witness in the measured histories.",
        "- [x] Configurations involving `ALL` frequently became unavailable during faults, reducing evaluability instead of producing successful stale observations.", "",
        "![Consistency-pair violation rates](report_generation/v7_assets/17_v4_consistency_pair_rates.png)", "",
        "## 7. Routing and fault exposure", "",
        table(["All histories","Changed coordinator","Changed %","Partition histories","Crossed cut","Crossed %"],
              [(f"{len(measured):,}",f"{changed:,}",pct(changed,len(measured)),f"{len(partitions):,}",f"{crossed:,}",pct(crossed,len(partitions)))]), "",
        "- A coordinator change is an exposure variable, not a violation.",
        "- A valid counterexample also requires successful operations and a returned value sequence rejected by the model oracle.",
        "- All three nodes are replicas at RF=3; token awareness therefore ranks only replica nodes in this topology.", "",
        "## 8. Violation witness inventory", "",
        table(["Run ID","Trial ID","CL","Model","Coordinator sequence","Changed","Crossed cut","Oracle reason"],witness_rows), "",
        "All six witnesses are RYW histories during a network partition. Each changed coordinator and crossed the 1|2 fault cut before the later read omitted the acknowledged write.", "",
        "## 9. Why histories were inconclusive", "",
        table(["First failure or oracle reason","Histories","Share","Classification"],error_rows), "",
        "- [x] `Unavailable` is expected when the coordinator can prove that too few replicas are reachable for the requested consistency level.",
        "- [x] `ReadTimeout`, `WriteTimeout`, and `NoHostAvailable` are availability outcomes, not consistency violations.",
        "- [x] Missing oracle preconditions are coverage exclusions: the required successful dependency, successor, or first read was not exposed.", "",
        "## 10. Expected-behaviour assessment", "",
        "- **Expected:** zero normal-operation violations in these initialized short histories.",
        "- **Expected:** high fault-time unavailability for `ALL` and for requests unable to reach two replicas at `QUORUM`.",
        "- **Mechanistically plausible:** RYW witnesses at `ONE/ONE`, `ONE/QUORUM`, and `QUORUM/ONE` when successful operations use different partition sides.",
        "- **Supported:** token-aware routing changes coordinator selection but does not strengthen the selected consistency level.",
        "- **Not established:** MR, MW, or WFR always hold. Zero observed witnesses only bounds this measured workload.", "",
        "## 11. Limitations", "",
        "- Containers share one physical host and do not reproduce independent-machine clocks, disks, racks, or wide-area latency.",
        "- The five included runs have unequal sizes, so histories are pooled as finite evidence rather than treated as a balanced causal estimate.",
        "- Fault episodes contain many trial cells; histories inside one episode are not independent fault realizations.",
        "- The driver commonly retained a coordinator within a short history, producing only 344 coordinator-changing histories.",
        "- The finite oracles detect concrete witnesses; they do not exhaust all possible executions.", "",
        "## 12. Detailed outcome matrix", "",
        "Legend: **viol.** = violation; **no viol.** = no violation observed; **inconc.** = operation failure or missing oracle precondition.", "",
        table(["Model","Write/read CL","Scenario","Viol.","No viol.","Inconc.","Evaluable","Total","Viol./eval."],cell_rows), "",
        "## 13. Reproducibility", "",
        "- Trial source: `report/report_generation/trial_level_evidence.csv`", "- Run source: `report/report_generation/run_level_violation_matrix.csv`",
        "- Derived summary: `report/report_generation/v7_analysis_summary.json`", "- Builder: `report/report_generation/build_v7_report_assets.py`",
        "- Export integrity: `python3 report/report_generation/verify_exports.py`", "",
    ]
    MATRIX.write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"matrix":str(MATRIX),"summary":str(SUMMARY),"histories":len(measured),"violations":len(violations),"charts":[str(p) for p in charts]},indent=2))


if __name__ == "__main__":
    build()
