# Current snapshot status

This snapshot contains the completed original Cassandra experiment project and the **parameterized randomized-routing redesign** requested afterward.

## Completed original experiments

- Three Cassandra 5.0.9 nodes, five write/read consistency configurations, and three operating scenarios.
- 300 main trials, 10 read-repair controls, and one timestamp control.
- Original results are in `results/20260912T063741Z/`.
- The existing PDFs describe those original measurements, not the randomized redesign.
- `report/previous_design/submission.zip` contains the complete, tested original source and reproduction package.

## Randomized redesign implementation

- `src/routing.py` introduces a seeded random routing layer.
- `src/worker.py` exposes application reads and writes without node arguments; the routing layer independently selects client-reachable coordinators for every operation.
- `config/randomized_experiments.json` controls repetitions, rounds, models, consistency configurations, scenarios, fault timing and enabled experiment types.
- `experiments/session_guarantees.py`, `node_failure.py`, `network_partition.py`, `read_repair.py`, `timestamp_control.py` separate experiment definitions and accounting.
- `experiments/faults.py` contains the exact project-scoped SIGKILL and iptables procedures.
- `scripts/run_randomized.py` executes 10 rounds by default: 600 main trials, 20 read-repair trials and 10 timestamp-control trials.
- `docs/randomized-experiment-plan.md` is the detailed registered methodology.
- The action-plan remediation is implemented: validated configuration, separate model workloads, IP-based crash detection, bounded and exception-safe fault handling, run locking, durable evidence, exact verification, and an explicit-run randomized report/archive builder.
- Automated tests cover classifiers, configuration, random routing, status parsing and failure identity matching.

The randomized implementation is ready for the project group to execute separately. A result directory is reportable only when its completion marker is true and `scripts/verify_randomized.py` accepts it. Partial, smoke, and historical fixed-coordinator directories must not be presented as completed randomized results.

This status is explicit so that the existing measured results are not mistaken for validation of the unfinished redesign.
