# Outcome matrix — model x config x scenario (ALL runs, every status)

Aggregated over **all 36 runs** regardless of completion status (21 completed, 15 incomplete/failed), for a total of **74240 main trials** classified.

> **Caveat:** Unlike `violation_matrix.md` (completed runs only), this file also includes incomplete runs (`completed: false`) whose trial sets are partial or aborted. Cell totals are therefore **not** uniform or directly comparable across configurations; use this table for a complete inventory of observed outcomes, not for rate comparisons.

Legend: **viol**=violation, **ok**=no violation observed, **inc:err**=inconclusive timeout/unavailable, **inc:dep**=dependency not observed, **inc:succ**=successor not observed, **inc:mal**=malformed, **inc:oth**=other.

Runs included:

- cassandra_policy_20260919T094231Z_0000000001352837 (0 trials, incomplete)
- cassandra_policy_20260919T094326Z_0000000001352837 (20 trials, incomplete)
- cassandra_policy_20260919T094446Z_0000000001352837 (60 trials, completed)
- cassandra_policy_20260919T095158Z_0000000001352838 (0 trials, incomplete)
- cassandra_policy_20260919T095446Z_0000000001352839 (60 trials, completed)
- cassandra_policy_20260919T100144Z_000000000135283a (60 trials, completed)
- cassandra_policy_20260919T100850Z_000000000135283b (60 trials, completed)
- cassandra_policy_20260919T101330Z_000000000135283f (600 trials, incomplete)
- cassandra_policy_20260919T135936Z_e9f0cc36454d5986 (60 trials, completed)
- cassandra_policy_20260919T145454Z_b46ec5216eb8950d (1116 trials, incomplete)
- cassandra_policy_20260920T000159Z_36915629d2b6f5ad (1080 trials, completed)
- cassandra_policy_20260920T010744Z_0977bac4dcb260ac (1080 trials, completed)
- cassandra_policy_20260920T021504Z_dc8094a55ebf425f (1080 trials, completed)
- cassandra_policy_20260920T032029Z_4d1c6194b3309a6b (1080 trials, completed)
- cassandra_policy_20260920T035710Z_000000000135283f (600 trials, completed)
- cassandra_policy_20260920T042616Z_b3e212c5ede5c29f (1080 trials, completed)
- cassandra_policy_20260920T053335Z_294f018e9c417b5c (252 trials, incomplete)
- cassandra_policy_20260920T061739Z_e6f386623a3b950e (1080 trials, completed)
- cassandra_policy_20260920T072816Z_cb13c5a6420fa31f (288 trials, incomplete)
- cassandra_policy_20260920T085839Z_0623ed68272cbc84 (432 trials, incomplete)
- cassandra_policy_20260920T124703Z_0000000001352841 (10800 trials, incomplete)
- cassandra_policy_20260920T223912Z_000000000135283f (2412 trials, incomplete)
- cassandra_policy_20260921T000348Z_000000000135283f (5400 trials, completed)
- cassandra_policy_20260921T041419Z_000000000135283f (828 trials, incomplete)
- cassandra_policy_20260921T061911Z_000000000135283f (36 trials, incomplete)
- cassandra_policy_20260921T064120Z_000000000135283f (36 trials, incomplete)
- cassandra_policy_20260921T080423Z_000000000135283f (36 trials, incomplete)
- cassandra_policy_20260921T080637Z_00000000000003e9 (108 trials, completed)
- cassandra_policy_20260921T081729Z_000000000135283f (1080 trials, completed)
- cassandra_policy_20260921T095705Z_000000000135283f (10800 trials, completed)
- cassandra_policy_20260921T233512Z_000000000135283f (10800 trials, completed)
- cassandra_policy_20260922T093902Z_000000000135283f (10800 trials, completed)
- cassandra_policy_20260922T231838Z_000000000135283f (10800 trials, completed)
- cassandra_policy_20260924T100220Z_00000000000003e9 (108 trials, completed)
- cassandra_policy_20260924T102238Z_00000000000003e9 (0 trials, incomplete)
- cassandra_policy_20260924T102734Z_00000000000003e9 (108 trials, completed)

| Model | Config (W/R) | Scenario | viol | ok | inc:err | inc:dep | inc:succ | inc:mal | inc:oth | cell total |
|---|---|---|---|---|---|---|---|---|---|---|
| RYW | ONE/ONE | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| RYW | ONE/ONE | node_failure | 0 | 697 | 0 | 0 | 0 | 0 | 0 | 697 |
| RYW | ONE/ONE | network_partition | 125 | 569 | 6 | 0 | 0 | 0 | 0 | 700 |
| RYW | ONE/QUORUM | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| RYW | ONE/QUORUM | node_failure | 0 | 697 | 0 | 0 | 0 | 0 | 0 | 697 |
| RYW | ONE/QUORUM | network_partition | 55 | 407 | 238 | 0 | 0 | 0 | 0 | 700 |
| RYW | ONE/ALL | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| RYW | ONE/ALL | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| RYW | ONE/ALL | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| RYW | QUORUM/ONE | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| RYW | QUORUM/ONE | node_failure | 0 | 696 | 1 | 0 | 0 | 0 | 0 | 697 |
| RYW | QUORUM/ONE | network_partition | 57 | 389 | 254 | 0 | 0 | 0 | 0 | 700 |
| RYW | QUORUM/QUORUM | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| RYW | QUORUM/QUORUM | node_failure | 0 | 697 | 0 | 0 | 0 | 0 | 0 | 697 |
| RYW | QUORUM/QUORUM | network_partition | 0 | 392 | 308 | 0 | 0 | 0 | 0 | 700 |
| RYW | QUORUM/ALL | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| RYW | QUORUM/ALL | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| RYW | QUORUM/ALL | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| RYW | ALL/ONE | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| RYW | ALL/ONE | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| RYW | ALL/ONE | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| RYW | ALL/QUORUM | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| RYW | ALL/QUORUM | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| RYW | ALL/QUORUM | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| RYW | ALL/ALL | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| RYW | ALL/ALL | node_failure | 0 | 0 | 697 | 0 | 0 | 0 | 0 | 697 |
| RYW | ALL/ALL | network_partition | 0 | 0 | 700 | 0 | 0 | 0 | 0 | 700 |
| MR | ONE/ONE | normal | 1 | 698 | 0 | 0 | 0 | 0 | 0 | 699 |
| MR | ONE/ONE | node_failure | 0 | 697 | 0 | 0 | 0 | 0 | 0 | 697 |
| MR | ONE/ONE | network_partition | 54 | 643 | 3 | 0 | 0 | 0 | 0 | 700 |
| MR | ONE/QUORUM | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| MR | ONE/QUORUM | node_failure | 0 | 696 | 1 | 0 | 0 | 0 | 0 | 697 |
| MR | ONE/QUORUM | network_partition | 0 | 409 | 291 | 0 | 0 | 0 | 0 | 700 |
| MR | ONE/ALL | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| MR | ONE/ALL | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| MR | ONE/ALL | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| MR | QUORUM/ONE | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| MR | QUORUM/ONE | node_failure | 0 | 696 | 1 | 0 | 0 | 0 | 0 | 697 |
| MR | QUORUM/ONE | network_partition | 37 | 410 | 253 | 0 | 0 | 0 | 0 | 700 |
| MR | QUORUM/QUORUM | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| MR | QUORUM/QUORUM | node_failure | 0 | 696 | 1 | 0 | 0 | 0 | 0 | 697 |
| MR | QUORUM/QUORUM | network_partition | 0 | 366 | 334 | 0 | 0 | 0 | 0 | 700 |
| MR | QUORUM/ALL | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| MR | QUORUM/ALL | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| MR | QUORUM/ALL | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| MR | ALL/ONE | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| MR | ALL/ONE | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| MR | ALL/ONE | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| MR | ALL/QUORUM | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| MR | ALL/QUORUM | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| MR | ALL/QUORUM | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| MR | ALL/ALL | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| MR | ALL/ALL | node_failure | 0 | 0 | 697 | 0 | 0 | 0 | 0 | 697 |
| MR | ALL/ALL | network_partition | 0 | 0 | 700 | 0 | 0 | 0 | 0 | 700 |
| MW | ONE/ONE | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| MW | ONE/ONE | node_failure | 1 | 696 | 0 | 0 | 0 | 0 | 0 | 697 |
| MW | ONE/ONE | network_partition | 74 | 494 | 3 | 0 | 129 | 0 | 0 | 700 |
| MW | ONE/QUORUM | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| MW | ONE/QUORUM | node_failure | 0 | 696 | 1 | 0 | 0 | 0 | 0 | 697 |
| MW | ONE/QUORUM | network_partition | 35 | 353 | 244 | 0 | 68 | 0 | 0 | 700 |
| MW | ONE/ALL | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| MW | ONE/ALL | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| MW | ONE/ALL | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| MW | QUORUM/ONE | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| MW | QUORUM/ONE | node_failure | 0 | 696 | 1 | 0 | 0 | 0 | 0 | 697 |
| MW | QUORUM/ONE | network_partition | 0 | 361 | 298 | 0 | 41 | 0 | 0 | 700 |
| MW | QUORUM/QUORUM | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| MW | QUORUM/QUORUM | node_failure | 0 | 697 | 0 | 0 | 0 | 0 | 0 | 697 |
| MW | QUORUM/QUORUM | network_partition | 0 | 382 | 318 | 0 | 0 | 0 | 0 | 700 |
| MW | QUORUM/ALL | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| MW | QUORUM/ALL | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| MW | QUORUM/ALL | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| MW | ALL/ONE | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| MW | ALL/ONE | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| MW | ALL/ONE | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| MW | ALL/QUORUM | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| MW | ALL/QUORUM | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| MW | ALL/QUORUM | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| MW | ALL/ALL | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| MW | ALL/ALL | node_failure | 0 | 0 | 697 | 0 | 0 | 0 | 0 | 697 |
| MW | ALL/ALL | network_partition | 0 | 0 | 700 | 0 | 0 | 0 | 0 | 700 |
| WFR | ONE/ONE | normal | 0 | 698 | 0 | 1 | 0 | 0 | 0 | 699 |
| WFR | ONE/ONE | node_failure | 0 | 695 | 0 | 1 | 1 | 0 | 0 | 697 |
| WFR | ONE/ONE | network_partition | 27 | 475 | 5 | 112 | 81 | 0 | 0 | 700 |
| WFR | ONE/QUORUM | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| WFR | ONE/QUORUM | node_failure | 0 | 697 | 0 | 0 | 0 | 0 | 0 | 697 |
| WFR | ONE/QUORUM | network_partition | 0 | 346 | 295 | 39 | 20 | 0 | 0 | 700 |
| WFR | ONE/ALL | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| WFR | ONE/ALL | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| WFR | ONE/ALL | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| WFR | QUORUM/ONE | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| WFR | QUORUM/ONE | node_failure | 0 | 697 | 0 | 0 | 0 | 0 | 0 | 697 |
| WFR | QUORUM/ONE | network_partition | 0 | 348 | 276 | 49 | 27 | 0 | 0 | 700 |
| WFR | QUORUM/QUORUM | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| WFR | QUORUM/QUORUM | node_failure | 0 | 697 | 0 | 0 | 0 | 0 | 0 | 697 |
| WFR | QUORUM/QUORUM | network_partition | 0 | 309 | 391 | 0 | 0 | 0 | 0 | 700 |
| WFR | QUORUM/ALL | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| WFR | QUORUM/ALL | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| WFR | QUORUM/ALL | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| WFR | ALL/ONE | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| WFR | ALL/ONE | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| WFR | ALL/ONE | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| WFR | ALL/QUORUM | normal | 0 | 673 | 0 | 0 | 0 | 0 | 0 | 673 |
| WFR | ALL/QUORUM | node_failure | 0 | 0 | 672 | 0 | 0 | 0 | 0 | 672 |
| WFR | ALL/QUORUM | network_partition | 0 | 0 | 675 | 0 | 0 | 0 | 0 | 675 |
| WFR | ALL/ALL | normal | 0 | 699 | 0 | 0 | 0 | 0 | 0 | 699 |
| WFR | ALL/ALL | node_failure | 0 | 0 | 697 | 0 | 0 | 0 | 0 | 697 |
| WFR | ALL/ALL | network_partition | 0 | 0 | 700 | 0 | 0 | 0 | 0 | 700 |
| **All** | **—** | **—** | **466** | **42542** | **30663** | **202** | **367** | **0** | **0** | **74240** |
