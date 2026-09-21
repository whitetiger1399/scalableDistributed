# Outcome matrix — model x config x scenario (ALL completed runs)

Aggregated over **12 completed runs**, **7380 main trials** total. Cell counts are raw trial counts; different runs contributed different numbers of trials (smoke vs full), so totals per cell vary.

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

| Model | Config (W/R) | Scenario | viol | ok | inc:err | inc:dep | inc:succ | inc:mal | inc:oth | cell total |
|---|---|---|---|---|---|---|---|---|---|---|
| RYW | ONE/ONE | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| RYW | ONE/ONE | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| RYW | ONE/ONE | network_partition | 31 | 44 | 0 | 0 | 0 | 0 | 0 | 75 |
| RYW | ONE/QUORUM | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| RYW | ONE/QUORUM | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| RYW | ONE/QUORUM | network_partition | 12 | 35 | 28 | 0 | 0 | 0 | 0 | 75 |
| RYW | ONE/ALL | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| RYW | ONE/ALL | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| RYW | ONE/ALL | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| RYW | QUORUM/ONE | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| RYW | QUORUM/ONE | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| RYW | QUORUM/ONE | network_partition | 9 | 38 | 28 | 0 | 0 | 0 | 0 | 75 |
| RYW | QUORUM/QUORUM | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| RYW | QUORUM/QUORUM | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| RYW | QUORUM/QUORUM | network_partition | 0 | 31 | 44 | 0 | 0 | 0 | 0 | 75 |
| RYW | QUORUM/ALL | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| RYW | QUORUM/ALL | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| RYW | QUORUM/ALL | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| RYW | ALL/ONE | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| RYW | ALL/ONE | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| RYW | ALL/ONE | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| RYW | ALL/QUORUM | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| RYW | ALL/QUORUM | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| RYW | ALL/QUORUM | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| RYW | ALL/ALL | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| RYW | ALL/ALL | node_failure | 0 | 0 | 75 | 0 | 0 | 0 | 0 | 75 |
| RYW | ALL/ALL | network_partition | 0 | 0 | 75 | 0 | 0 | 0 | 0 | 75 |
| MR | ONE/ONE | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MR | ONE/ONE | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MR | ONE/ONE | network_partition | 18 | 56 | 1 | 0 | 0 | 0 | 0 | 75 |
| MR | ONE/QUORUM | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MR | ONE/QUORUM | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MR | ONE/QUORUM | network_partition | 0 | 29 | 46 | 0 | 0 | 0 | 0 | 75 |
| MR | ONE/ALL | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| MR | ONE/ALL | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MR | ONE/ALL | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MR | QUORUM/ONE | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MR | QUORUM/ONE | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MR | QUORUM/ONE | network_partition | 10 | 34 | 31 | 0 | 0 | 0 | 0 | 75 |
| MR | QUORUM/QUORUM | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MR | QUORUM/QUORUM | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MR | QUORUM/QUORUM | network_partition | 0 | 25 | 50 | 0 | 0 | 0 | 0 | 75 |
| MR | QUORUM/ALL | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| MR | QUORUM/ALL | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MR | QUORUM/ALL | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MR | ALL/ONE | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| MR | ALL/ONE | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MR | ALL/ONE | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MR | ALL/QUORUM | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| MR | ALL/QUORUM | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MR | ALL/QUORUM | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MR | ALL/ALL | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MR | ALL/ALL | node_failure | 0 | 0 | 75 | 0 | 0 | 0 | 0 | 75 |
| MR | ALL/ALL | network_partition | 0 | 0 | 75 | 0 | 0 | 0 | 0 | 75 |
| MW | ONE/ONE | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MW | ONE/ONE | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MW | ONE/ONE | network_partition | 22 | 26 | 0 | 0 | 27 | 0 | 0 | 75 |
| MW | ONE/QUORUM | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MW | ONE/QUORUM | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MW | ONE/QUORUM | network_partition | 10 | 21 | 25 | 0 | 19 | 0 | 0 | 75 |
| MW | ONE/ALL | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| MW | ONE/ALL | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MW | ONE/ALL | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MW | QUORUM/ONE | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MW | QUORUM/ONE | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MW | QUORUM/ONE | network_partition | 0 | 25 | 37 | 0 | 13 | 0 | 0 | 75 |
| MW | QUORUM/QUORUM | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MW | QUORUM/QUORUM | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MW | QUORUM/QUORUM | network_partition | 0 | 29 | 46 | 0 | 0 | 0 | 0 | 75 |
| MW | QUORUM/ALL | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| MW | QUORUM/ALL | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MW | QUORUM/ALL | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MW | ALL/ONE | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| MW | ALL/ONE | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MW | ALL/ONE | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MW | ALL/QUORUM | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| MW | ALL/QUORUM | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MW | ALL/QUORUM | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| MW | ALL/ALL | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| MW | ALL/ALL | node_failure | 0 | 0 | 75 | 0 | 0 | 0 | 0 | 75 |
| MW | ALL/ALL | network_partition | 0 | 0 | 75 | 0 | 0 | 0 | 0 | 75 |
| WFR | ONE/ONE | normal | 0 | 74 | 0 | 1 | 0 | 0 | 0 | 75 |
| WFR | ONE/ONE | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| WFR | ONE/ONE | network_partition | 8 | 19 | 0 | 26 | 22 | 0 | 0 | 75 |
| WFR | ONE/QUORUM | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| WFR | ONE/QUORUM | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| WFR | ONE/QUORUM | network_partition | 0 | 16 | 42 | 12 | 5 | 0 | 0 | 75 |
| WFR | ONE/ALL | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| WFR | ONE/ALL | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| WFR | ONE/ALL | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| WFR | QUORUM/ONE | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| WFR | QUORUM/ONE | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| WFR | QUORUM/ONE | network_partition | 0 | 16 | 37 | 18 | 4 | 0 | 0 | 75 |
| WFR | QUORUM/QUORUM | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| WFR | QUORUM/QUORUM | node_failure | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| WFR | QUORUM/QUORUM | network_partition | 0 | 16 | 59 | 0 | 0 | 0 | 0 | 75 |
| WFR | QUORUM/ALL | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| WFR | QUORUM/ALL | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| WFR | QUORUM/ALL | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| WFR | ALL/ONE | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| WFR | ALL/ONE | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| WFR | ALL/ONE | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| WFR | ALL/QUORUM | normal | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |
| WFR | ALL/QUORUM | node_failure | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| WFR | ALL/QUORUM | network_partition | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 60 |
| WFR | ALL/ALL | normal | 0 | 75 | 0 | 0 | 0 | 0 | 0 | 75 |
| WFR | ALL/ALL | node_failure | 0 | 0 | 75 | 0 | 0 | 0 | 0 | 75 |
| WFR | ALL/ALL | network_partition | 0 | 0 | 75 | 0 | 0 | 0 | 0 | 75 |
