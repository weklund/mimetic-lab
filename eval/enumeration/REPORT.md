Starting enumeration (isomorphism classes)...
Enumerating binary majority (isomorphism classes) for n=1...
  Completed 1 isomorphism classes for n=1
Enumerating binary majority (isomorphism classes) for n=2...
  Completed 1 isomorphism classes for n=2
Enumerating binary majority (isomorphism classes) for n=3...
  Completed 2 isomorphism classes for n=3
Enumerating binary majority (isomorphism classes) for n=4...
  Completed 6 isomorphism classes for n=4
Enumerating binary majority (isomorphism classes) for n=5...
  Completed 21 isomorphism classes for n=5
Enumerating binary majority (isomorphism classes) for n=6...
  Completed 112 isomorphism classes for n=6
Enumerating vertex-valued majority (isomorphism classes) for n=1...
  Completed 1 isomorphism classes for n=1
Enumerating vertex-valued majority (isomorphism classes) for n=2...
  Completed 1 isomorphism classes for n=2
Enumerating vertex-valued majority (isomorphism classes) for n=3...
  Completed 2 isomorphism classes for n=3
Enumerating vertex-valued majority (isomorphism classes) for n=4...
  Completed 6 isomorphism classes for n=4
Analyzing voter model (isomorphism classes) for n=3...
  Completed 2 isomorphism classes for n=3
Analyzing voter model (isomorphism classes) for n=4...
  Completed 6 isomorphism classes for n=4
Analyzing voter model (isomorphism classes) for n=5...
  Completed 21 isomorphism classes for n=5
Analyzing voter model (isomorphism classes) for n=6...
  Completed 112 isomorphism classes for n=6
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

| n | Graphs | Total Configs | Unanimous Fixed | Split Fixed | 2-Cycles | Period > 2 | Unknown |
|---|--------|---------------|-----------------|-------------|----------|------------|---------|
| 1 | 1 | 2 | 2 | 0 | 0 | 0 | 0 |
| 2 | 1 | 4 | 2 | 0 | 2 | 0 | 0 |
| 3 | 2 | 16 | 14 | 0 | 2 | 0 | 0 |
| 4 | 6 | 96 | 66 | 6 | 24 | 0 | 0 |
| 5 | 21 | 672 | 520 | 50 | 102 | 0 | 0 |
| 6 | 112 | 7168 | 5240 | 542 | 1386 | 0 | 0 |

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

### Enumeration Results for Vertex-Valued

| n | Graphs | Total Configs | Unanimous Fixed | Split Fixed | 2-Cycles | Period > 2 | Unknown |
|---|--------|---------------|-----------------|-------------|----------|------------|---------|
| 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 | 1 | 1 | 0 | 1 | 0 | 0 | 0 |
| 3 | 2 | 16 | 0 | 16 | 0 | 0 | 0 |
| 4 | 6 | 486 | 0 | 452 | 34 | 0 | 0 |

### Self-Target Cases

| n | Configs with Self-Target-by-Majority | Total Configs | Rate |
|---|--------------------------------------|---------------|------|
| 1 | 0 | 0 | 0.0000 |
| 2 | 1 | 1 | 1.0000 |
| 3 | 14 | 16 | 0.8750 |
| 4 | 352 | 486 | 0.7243 |

**Note**: This is an exploration convention, not a sourced rule. Configurations
where a strict majority of an agent's neighbors target that agent. The enumeration
keeps the agent's own target in such cases.

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
| 3 | 2 | 1 | 1 |
| 4 | 6 | 3 | 3 |
| 5 | 21 | 5 | 16 |
| 6 | 112 | 17 | 95 |

The test suite verifies that:

- Connected graphs have only unanimous absorbing states
- Synchronous voter on a bipartite graph (4-cycle) does not always absorb
- Lazy voter has positive absorption probability

## Completeness

This enumeration uses connected isomorphism classes via nx.graph_atlas_g.

Known nonisomorphic connected graph counts (verified in tests):

- n=1: 1 class
- n=2: 1 class
- n=3: 2 classes
- n=4: 6 classes
- n=5: 21 classes
- n=6: 112 classes

All isomorphism classes enumerated for n=1..6 with all 2^n binary assignments (O5)
and all valid vertex-target assignments for n=1..4 (O6).

## Conclusion

These enumerations confirm the stated properties of O5, O6, and O7:

- O5: Binary majority reaches a fixed point or 2-cycle (no period > 2 found)
- O6: Split fixed points exist; self-target-by-majority configurations documented
- O7: Voter model unanimity is schedule-dependent

This is the exploration step before formal proof work (issue #15).
No claims about Girard or G4 follow from these results.
