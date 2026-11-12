# Sack's Mimetic Theory: Formal Verification in Lean 4

This directory contains a formalization of theorems from Graham Alexander Sack's paper:

> Sack, G.A. (2021). Geometries of Desire: Simulating Rene Girard's Mimetic Theory. 
> In: Yang, Z., von Briesen, E. (eds) Proceedings of the 2020 Conference of The 
> Computational Social Science Society of the Americas. Springer Proceedings in 
> Complexity. Springer, Cham. https://doi.org/10.1007/978-3-030-83418-0_13

## What is Proved

### Definitions

1. **Mimetic Network**: A finite graph where each node has exactly one outgoing object link and one outgoing mediation link (functions `obj, med : N → N`).

2. **Equilibrium**: A state where for every node n, the node and its mediator desire the same object: `obj(n) = obj(med(n))`.

3. **Mutual Mediator Set (MMS)**: A subset closed under the mediation function.

4. **Minimum Mutual Mediator Set**: An MMS that cannot be partitioned into two nonempty disjoint MMSs.

### Theorems

**Theorem 1 — Convergence of Desire** (Main Result, **COMPLETE PROOF**):
In equilibrium, all nodes in a minimum mutual mediator set have the same object of desire.

**Theorem 2 — Non-Identity of Desire** (**COMPLETE PROOF**):
If object self-links are not permitted, all nodes in a minimum MMS in equilibrium desire an object outside that set.

**Theorem 3 — Existence of Equilibrium without Narcissism** (Statement Only):
If self-links are not permitted, equilibrium exists iff N can be partitioned into at least two disjoint MMSs. (Sack's sketch proves only the "only if" direction; full iff proof requires additional work.)

**Theorem 4 — Existence of Equilibrium with Narcissism** (Complete Proof):
If self-links are permitted, equilibrium always exists (all nodes can desire the same object).

**Theorem 5 — Number of Objects of Desire in Equilibrium** (Statement Only):
The number of distinct objects of desire in equilibrium is bounded by the number of minimum MMSs in a partition.

## Epistemic Limitations

**This formalization proves theorems about Sack's graph-theoretic model under the stated assumptions. It does NOT prove that Girard's anthropological theory of mimetic desire is empirically true, nor does it validate the claim that human desire operates according to these mathematical structures.**

## Assumptions

The proofs rely on:

1. Nodes are finite (`Fintype N`)
2. Each node has exactly one outgoing object link and one outgoing mediation link
3. Equilibrium is defined as: `∀ n, obj(n) = obj(med(n))`
4. A Minimum MMS is defined by the partition condition (cannot be split into two nonempty disjoint MMSs)
5. The proof of Theorem 1 uses that minimum implies the underlying undirected mediation graph is connected

## Building

Requires [elan](https://github.com/leanprover/elan) (the Lean version manager) and Lean 4.

```bash
# Install dependencies (done automatically by lake)
lake update

# Build the project
lake build
```

## Files

- `SackTheorem/MimeticNetwork.lean` — Main formalization
- `lakefile.toml` — Lake build configuration
- `lean-toolchain` — Lean version specification

## Gaps

- **existence_equilibrium_no_narcissism_only_if** (Theorem 3): Sack's sketch proves the "only if" direction. The full iff statement requires proving sufficiency (if partitionable, then equilibrium exists).

- **number_of_objects_bound** (Theorem 5): The counting argument is stated but not proven.

**The main results (Theorems 1 and 2) are complete with rigorous proofs, no `sorry` statements.**

## License

MIT License, Copyright (c) 2026 Wes Eklund
