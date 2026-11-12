# Sack's Mimetic Theory: Formal Verification in Lean 4

This directory formalizes the appendix theorems of Graham Alexander Sack's paper:

> Sack, G.A. (2021). Geometries of Desire: Simulating Rene Girard's Mimetic Theory.
> In: Yang, Z., von Briesen, E. (eds) Proceedings of the 2020 Conference of The
> Computational Social Science Society of the Americas. Springer Proceedings in
> Complexity. Springer, Cham. https://doi.org/10.1007/978-3-030-83418-0_13

These are claims S1 to S4 in [`claims/claims.yaml`](../claims/claims.yaml). A proof here upgrades only the S claim it proves, never a Girard (G) claim.

## Epistemic limitations

**This formalization proves theorems about Sack's graph-theoretic model under the stated assumptions. It does NOT prove that Girard's anthropological theory of mimetic desire is empirically true, nor that human desire operates according to these mathematical structures.** A verified model is a verified design; it says nothing about whether people behave like it. The model has no scarcity, rivalry, crisis, or scapegoat, and nothing here claims otherwise.

## Definitions

1. **Mimetic network** (Sack Def. 1): every node has exactly one outgoing object link and one outgoing mediation link (functions `obj, med : N → N`). Objects are nodes; persons and things are not distinguished.
2. **Equilibrium** (Def. 2): every node desires what its mediator desires, `obj n = obj (med n)`.
3. **Mutual mediator set, MMS** (Def. 3): a set closed under `med`.
4. **Minimum MMS** (Def. 4): a nonempty MMS that cannot be partitioned into two nonempty disjoint MMSs. "Minimum" means indecomposable, not smallest: a whole weak component and its mediation cycle alone both qualify. Every theorem below holds under either reading.

A node may be its own mediator (`med n = n`, Sack's self-mediators) and may desire itself (`obj n = n`, narcissism). Theorems that exclude self-desire say so.

**Equilibrium is a fixed point, not an attractor.** "Convergence of Desire" means agreement at equilibrium, not convergence over time. Nothing here says any dynamics reach equilibrium, and Sack's own three-agent run cycles and never does (notes 5 and 6).

## Status

| Sack | Lean name | Status |
|---|---|---|
| Theorem 1, Convergence of Desire | `convergence_of_desire` | **Proved.** In equilibrium, all nodes of a minimum MMS desire the same object. |
| Theorem 1 on weak components (claim S1's wording) | `convergence_on_weak_component` | **Proved.** In equilibrium, nodes in the same weak component of the mediation graph desire the same object. |
| Theorem 2, Non-Identity of Desire | `non_identity_of_desire` | **Proved.** Without self-desire, every node of a minimum MMS in equilibrium desires a node outside it. |
| Theorem 3, Existence without Narcissism, "only if" | `existence_equilibrium_no_narcissism_only_if` | **Proved.** In Sack's words: without self-desire, an equilibrium implies a partition into at least two nonempty disjoint MMSs. Needs `[Nonempty N]`. |
| Theorem 3, "if" | `existence_equilibrium_no_narcissism_if` | **Proved.** Constructs an object assignment from a partition: nodes of part A desire a fixed node of part B, all other nodes desire a fixed node of A. This yields no self-desire (parts are disjoint) and equilibrium (each part is closed under med). |
| Theorem 3 with minimum MMS parts | `existence_equilibrium_no_narcissism_only_if_minimum` | **Stated, not proved** (`proof_wanted`). Equivalent to Sack's form; needs showing that each weak component is a minimum MMS and that all weak components partition the nodes. Left unproved due to technical subtleties with decidability and equivalence closure structure. |
| Theorem 4, Existence with Narcissism | `existence_equilibrium_with_narcissism` | **Proved.** Sack's witness: everyone desires one node, which therefore desires itself. True for a trivial reason; its content is the contrast with Theorem 3. |
| Theorem 5, Number of Objects | `number_of_objects_bound` | **Proved.** In equilibrium, the number of distinct objects is at most the number of parts in any cover of the nodes by minimum MMSs (disjointness not needed). Claim S4's weak-component form follows once weak components are shown to be minimum MMSs. |
| (lab's reading, not Sack) | `unique_narcissist_of_weakly_connected` | **Proved.** On a weakly connected mediation graph in equilibrium, exactly one node desires itself and every node desires it. This is why Theorem 3 needs two components once self-desire is excluded. In Girard's vocabulary it is the coquette; that reading is the lab's. |

### How "proved" is checked

`lake build` succeeds even with a `sorry` in a proof; the first CI run of this formalization passed with four. So "proved" is checked mechanically, not asserted here:

- Unproved statements are `proof_wanted` (from Batteries), which nothing can use in a proof.
- [`SackTheorem/AxiomAudit.lean`](SackTheorem/AxiomAudit.lean) pins, with `#guard_msgs`, the exact axioms each proved theorem depends on. Any `sorryAx`, or any new axiom, fails the build. Add a line there for every new theorem.
- The library builds with `warningAsError = true` (`lakefile.toml`), so "declaration uses `sorry`", or any other warning, fails the build at the source line.
- CI also rejects any `sorry` or `admit` in the Lean sources.

The files use Lean's module system (`module`, `public import`, `@[expose] public section`), as Mathlib does. That is what lets the build be warning-free.

## Building

Requires [elan](https://github.com/leanprover/elan) (the Lean version manager). The toolchain is pinned in `lean-toolchain` (Lean and Mathlib `v4.35.0`).

```bash
cd lean
lake exe cache get   # download prebuilt Mathlib for the pinned manifest
lake build           # builds the library and the axiom audit
```

Run `lake update` only when you mean to move dependencies, and commit the resulting `lake-manifest.json`. CI builds exactly what the manifest pins.

## Files

- `SackTheorem/MimeticNetwork.lean`: definitions, proofs, and `proof_wanted` statements
- `SackTheorem/AxiomAudit.lean`: axiom pins for every proved theorem
- `lakefile.toml`, `lake-manifest.json`, `lean-toolchain`: build configuration

## License

MIT License, Copyright (c) 2026 Wes Eklund
