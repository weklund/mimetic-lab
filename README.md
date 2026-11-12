# Mimetic Lab

A laboratory for experiments in mimetic theory and computational social science.

## Projects

### Formal Verification: Sack's Mimetic Theory ([`lean/`](lean/))

Lean 4 formalization of theorems from Graham Alexander Sack's "Geometries of Desire: Simulating Rene Girard's Mimetic Theory" (2021).

**Main result**: Theorem 1 (Convergence of Desire). In equilibrium, all nodes in a minimum mutual mediator set have the same object of desire. This is agreement at a fixed point, not a claim that any dynamics reach it. Theorems 1, 2, 4, and 5 are proved; Theorem 3 is stated in Sack's wording and not yet proved.

See [`lean/README.md`](lean/README.md) for status, how "proved" is checked, build instructions, and epistemic limitations. Claims S1 to S4 in [`claims/claims.yaml`](claims/claims.yaml) record what each proof does and does not establish.

### Future Work

This repository will also hold simulation code and experiments related to:
- Mimetic Simulation (Black 2026 and related work)
- Additional computational models of mimetic desire

## License

MIT License, Copyright (c) 2026 Wes Eklund
