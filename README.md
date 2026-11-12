# Mimetic Lab

A laboratory for experiments in mimetic theory and computational social science.

The question, the method, the milestones, and the process are in [`ROADMAP.md`](ROADMAP.md) (proposed). The claims under test, each with what would make it fail, are in [`claims/claims.yaml`](claims/claims.yaml); the scheme is [`claims/README.md`](claims/README.md). Nothing in this repository is evidence that Girard's anthropology is true; see the epistemic limit in the claim map.

## Projects

### Formal Verification: Sack's Mimetic Theory ([`lean/`](lean/))

Lean 4 formalization of theorems from Graham Alexander Sack's "Geometries of Desire: Simulating Rene Girard's Mimetic Theory" (2021).

**Main result**: Theorem 1 (Convergence of Desire). In equilibrium, all nodes in a minimum mutual mediator set have the same object of desire. This is agreement at a fixed point, not a claim that any dynamics reach it. Theorems 1 to 5 are proved in Sack's wording; one weak-component corollary (claim S4) is stated.

See [`lean/README.md`](lean/README.md) for status, how "proved" is checked, build instructions, and epistemic limitations. Claims S1 to S4 in [`claims/claims.yaml`](claims/claims.yaml) record what each proof does and does not establish.

### Reproduction: Black 2026 ([`eval/`](eval/))

An evaluation contract ([`eval/contract.md`](eval/contract.md)), a trial schema, judges, and archived traces for reproducing Maxwell Black's 2026 simulation tables from his unmodified code at a pinned commit. A judge PASS is a statement about Black's model, and upgrades a B claim only.

### The lab's own model ([`eval/models/`](eval/models/))

[`minimal-model-v0.md`](eval/models/minimal-model-v0.md) specifies the smallest model with all four stages of Girard's cycle, each with an ablation switch, and the experiments, predictions, and formal targets for it. Claims L1 and L2. Not yet implemented.

## License

MIT License, Copyright (c) 2026 Wes Eklund
