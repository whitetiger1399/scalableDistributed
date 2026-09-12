# Current snapshot status

This snapshot contains the completed original Cassandra experiment project and an **in-progress randomized-routing redesign** requested afterward.

## Completed original experiments

- Three Cassandra 5.0.9 nodes, five write/read consistency configurations, and three operating scenarios.
- 300 main trials, 10 read-repair controls, and one timestamp control.
- Original results are in `results/20260912T063741Z/`.
- The existing PDFs describe those original measurements, not the randomized redesign.
- `report/previous_design/submission.zip` contains the complete, tested original source and reproduction package.

## Randomized redesign in progress

- `src/routing.py` introduces a seeded random routing layer.
- `src/worker.py` now exposes application reads and writes without node arguments; the routing layer independently selects client-reachable coordinators.
- `src/checks.py` now checks the writes-follow-reads prerequisite directly.
- The orchestration script, tests, verifier, predictions, and report generator still need integration with the new worker interface.
- **The current checkout is not yet an end-to-end runnable randomized experiment suite.** New randomized results have not been collected, and the requested minimum of 10 trials per experiment type has not yet been executed.

This status is explicit so that the existing measured results are not mistaken for validation of the unfinished redesign.
