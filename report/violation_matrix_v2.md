# Outcome matrix — model x config x scenario (ALL completed runs)

Aggregated over **13 completed runs**, **12780 main trials** total. Cell counts are raw trial counts; different runs contributed different numbers of trials (smoke vs full), so totals per cell vary.

Legend: **viol**=violation, **ok**=no violation observed, **inc:err**=inconclusive timeout/unavailable, **inc:dep**=dependency not observed, **inc:succ**=successor not observed, **inc:mal**=malformed, **inc:oth**=other.

Runs included:

- randomized_20260919T094446Z_0000000001352837 (60 trials)
- randomized_20260919T095446Z_0000000001352839 (60 trials)
- randomized_20260919T100144Z_000000000135283a (60 trials)
- randomized_20260919T100850Z_000000000135283b (60 trials)
- randomized_20260919T135936Z_e9f0cc36454d5986 (60 trials)
- randomized_20260920T000159Z_36915629d2b6f5ad (1080 trials)
- randomized_20260920T010744Z_0977bac4dcb260ac (1080 trials)
- randomized_20260920T021504Z_dc8094a55ebf425f (1080 trials)
- randomized_20260920T032029Z_4d1c6194b3309a6b (1080 trials)
- randomized_20260920T035710Z_000000000135283f (600 trials)
- randomized_20260920T042616Z_b3e212c5ede5c29f (1080 trials)
- randomized_20260920T061739Z_e6f386623a3b950e (1080 trials)
- randomized_20260921T000348Z_000000000135283f (5400 trials)

| Model | Config (W/R) | Scenario | viol | ok | inc:err | inc:dep | inc:succ | inc:mal | inc:oth | cell total |
|---|---|---|---|---|---|---|---|---|---|---|
| RYW | ONE/ONE | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | ONE/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | ONE/ONE | network_partition | 51 | 74 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | ONE/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | ONE/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | ONE/QUORUM | network_partition | 22 | 61 | 42 | 0 | 0 | 0 | 0 | 125 |
| RYW | ONE/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| RYW | ONE/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | ONE/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | QUORUM/ONE | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | QUORUM/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | QUORUM/ONE | network_partition | 19 | 64 | 42 | 0 | 0 | 0 | 0 | 125 |
| RYW | QUORUM/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | QUORUM/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | QUORUM/QUORUM | network_partition | 0 | 53 | 72 | 0 | 0 | 0 | 0 | 125 |
| RYW | QUORUM/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| RYW | QUORUM/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | QUORUM/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | ALL/ONE | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| RYW | ALL/ONE | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | ALL/ONE | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | ALL/QUORUM | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| RYW | ALL/QUORUM | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | ALL/QUORUM | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| RYW | ALL/ALL | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| RYW | ALL/ALL | node_failure | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
| RYW | ALL/ALL | network_partition | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
| MR | ONE/ONE | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | ONE/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | ONE/ONE | network_partition | 28 | 96 | 1 | 0 | 0 | 0 | 0 | 125 |
| MR | ONE/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | ONE/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | ONE/QUORUM | network_partition | 0 | 55 | 70 | 0 | 0 | 0 | 0 | 125 |
| MR | ONE/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MR | ONE/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | ONE/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | QUORUM/ONE | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | QUORUM/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | QUORUM/ONE | network_partition | 15 | 62 | 48 | 0 | 0 | 0 | 0 | 125 |
| MR | QUORUM/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | QUORUM/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | QUORUM/QUORUM | network_partition | 0 | 41 | 84 | 0 | 0 | 0 | 0 | 125 |
| MR | QUORUM/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MR | QUORUM/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | QUORUM/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | ALL/ONE | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MR | ALL/ONE | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | ALL/ONE | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | ALL/QUORUM | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MR | ALL/QUORUM | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | ALL/QUORUM | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MR | ALL/ALL | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MR | ALL/ALL | node_failure | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
| MR | ALL/ALL | network_partition | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
| MW | ONE/ONE | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | ONE/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | ONE/ONE | network_partition | 31 | 38 | 0 | 0 | 56 | 0 | 0 | 125 |
| MW | ONE/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | ONE/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | ONE/QUORUM | network_partition | 15 | 41 | 38 | 0 | 31 | 0 | 0 | 125 |
| MW | ONE/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MW | ONE/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | ONE/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | QUORUM/ONE | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | QUORUM/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | QUORUM/ONE | network_partition | 0 | 40 | 64 | 0 | 21 | 0 | 0 | 125 |
| MW | QUORUM/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | QUORUM/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | QUORUM/QUORUM | network_partition | 0 | 44 | 81 | 0 | 0 | 0 | 0 | 125 |
| MW | QUORUM/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MW | QUORUM/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | QUORUM/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | ALL/ONE | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MW | ALL/ONE | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | ALL/ONE | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | ALL/QUORUM | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| MW | ALL/QUORUM | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | ALL/QUORUM | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| MW | ALL/ALL | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| MW | ALL/ALL | node_failure | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
| MW | ALL/ALL | network_partition | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
| WFR | ONE/ONE | normal | 0 | 124 | 0 | 1 | 0 | 0 | 0 | 125 |
| WFR | ONE/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | ONE/ONE | network_partition | 13 | 29 | 0 | 49 | 34 | 0 | 0 | 125 |
| WFR | ONE/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | ONE/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | ONE/QUORUM | network_partition | 0 | 30 | 70 | 17 | 8 | 0 | 0 | 125 |
| WFR | ONE/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| WFR | ONE/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | ONE/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | QUORUM/ONE | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | QUORUM/ONE | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | QUORUM/ONE | network_partition | 0 | 29 | 62 | 24 | 10 | 0 | 0 | 125 |
| WFR | QUORUM/QUORUM | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | QUORUM/QUORUM | node_failure | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | QUORUM/QUORUM | network_partition | 0 | 21 | 104 | 0 | 0 | 0 | 0 | 125 |
| WFR | QUORUM/ALL | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| WFR | QUORUM/ALL | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | QUORUM/ALL | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | ALL/ONE | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| WFR | ALL/ONE | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | ALL/ONE | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | ALL/QUORUM | normal | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| WFR | ALL/QUORUM | node_failure | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | ALL/QUORUM | network_partition | 0 | 0 | 110 | 0 | 0 | 0 | 0 | 110 |
| WFR | ALL/ALL | normal | 0 | 125 | 0 | 0 | 0 | 0 | 0 | 125 |
| WFR | ALL/ALL | node_failure | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
| WFR | ALL/ALL | network_partition | 0 | 0 | 125 | 0 | 0 | 0 | 0 | 125 |
