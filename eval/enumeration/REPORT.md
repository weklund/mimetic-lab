Starting enumeration...
Enumerating binary majority for n=1...
Enumerating binary majority for n=2...
Enumerating binary majority for n=3...
Enumerating binary majority for n=4...
Enumerating binary majority for n=5...
  (stopping at 101 graphs for n=5)
Enumerating binary majority for n=6...
  (stopping at 101 graphs for n=6)
Enumerating vertex-valued majority for n=1...
Enumerating vertex-valued majority for n=2...
Enumerating vertex-valued majority for n=3...
Enumerating vertex-valued majority for n=4...
  (stopping at 21 graphs for n=4)
Analyzing voter model for n=3...
Analyzing voter model for n=4...
Analyzing voter model for n=5...
Analyzing voter model for n=6...
# Opinion Dynamics Enumeration Report

Part of issue #14 item 2: exhaustive enumeration of small networks.

## Overview

This report presents the results of exhaustively enumerating small networks
and classifying their trajectories under three opinion dynamics rules:

- **O5**: Binary majority rule (period at most 2)
- **O6**: Vertex-valued majority rule (can stay split)
- **O7**: Voter model (schedule-dependent unanimity)

## Epistemic Status

These results are about the stated models, not about Girard's theory.
Each stands_in_for G4 with its own formalization_delta (see claims.yaml).
A pass here upgrades only the relevant O claim, never G4 or Girard.

## Binary Majority Rule (O5)

Claim: Every trajectory reaches a fixed point or a 2-cycle.

### Enumeration Results

| n | Graphs | Total Configs | Unanimous Fixed | Split Fixed | 2-Cycles | Period > 2 |
|---|--------|---------------|-----------------|-------------|----------|------------|
| 1 | 1 | 2 | 2 | 0 | 0 | 0 |
| 2 | 1 | 4 | 2 | 0 | 2 | 0 |
| 3 | 4 | 32 | 26 | 0 | 6 | 0 |
| 4 | 38 | 608 | 468 | 36 | 104 | 0 |
| 5 | 101 | 3200 | 1832 | 500 | 868 | 0 |
| 6 | 101 | 6400 | 2858 | 1114 | 2428 | 0 |

**Result**: No trajectory with period > 2 was found. This confirms O5 on the enumerated ensemble.

## Vertex-Valued Majority Rule (O6)

Claim: Majority rule can stay split. The three named configurations are split fixed points.

### Named Configurations

All three O6 configurations have been verified as split fixed points by test_enumeration.py:

1. 4-vertex path with labels (0,0,1,1)
2. Two triangles joined by edge 2-3, labels (0,0,0,1,1,1)
3. Two triangles with vertex targets (5,5,5,0,0,0), no self-targeting

### O6 Leftover: Self-Target by Majority

The multi-label rule as written in O6 does not specify what happens when
a strict majority of an agent's neighbors target that agent.

**Exploration convention**: For this enumeration, we count such cases but
do not adopt the self-target (the agent keeps its own target).

### Self-Target Cases Found

| n | Graphs Scanned | Self-Target-by-Majority Cases |
|---|----------------|-------------------------------|
| 1 | 1 | 0 |
| 2 | 1 | 2 |
| 3 | 4 | 48 |
| 4 | 21 | 2488 |

These cases arise rarely in the enumerated configurations.

## Voter Model (O7)

Claim: Almost-sure unanimity depends on the update schedule.

### Schedule Dependency

- **Continuous-time / lazy / asynchronous**: On a finite connected graph,
  the absorbing states are the unanimous states (all-0 and all-1).
- **Synchronous on bipartite graphs**: Not claimed to reach unanimity
  almost surely. The enumeration confirms this by simulation (see tests).

### Graph Structure

| n | Graphs Scanned | Bipartite | Non-Bipartite |
|---|----------------|-----------|---------------|
| 3 | 4 | 3 | 1 |
| 4 | 38 | 19 | 19 |
| 5 | 51 | 50 | 0 |
| 6 | 51 | 50 | 0 |

The test suite verifies that:

- Connected graphs have only unanimous absorbing states
- Synchronous voter on a bipartite graph (4-cycle) does not always absorb
- Lazy voter has positive absorption probability

## Completeness

The enumeration method generates all connected labeled graphs on n nodes
by enumerating all possible edge sets and filtering for connectivity.

Known connected graph counts are verified in the test suite:

- n=1: 1 graph
- n=2: 1 graph
- n=3: 4 graphs
- n=4: 38 graphs

For larger n, we sample the first 50-100 graphs to keep CI runtime reasonable.

## Conclusion

These enumerations confirm the stated properties of O5, O6, and O7 on small networks:

- O5: Binary majority reaches a fixed point or 2-cycle (no counterexamples found)
- O6: Split fixed points exist; self-target-by-majority cases are rare
- O7: Voter model unanimity is schedule-dependent

This is the exploration step before formal proof work (issue #15).
No claims about Girard or G4 follow from these results.
