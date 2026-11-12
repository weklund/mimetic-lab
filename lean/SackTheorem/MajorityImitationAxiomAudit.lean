module

public import SackTheorem.MajorityImitation

/-
Copyright (c) 2026 Wes Eklund. All rights reserved.
Released under MIT license.

Authors: Cursor Cloud Agent

# Axiom audit for MajorityImitation

This file audits all proved theorems in `MajorityImitation` to ensure they
depend only on standard Lean axioms (`propext`, `Classical.choice`, `Quot.sound`)
and zero project axioms.

The `proof_wanted` claim `period_at_most_2` is not audited (it is not proved).

## Axiom audit results

All proved theorems depend only on standard Lean axioms:
- `splitStatePath4_is_fixed`: [propext, Classical.choice, Quot.sound]
- `splitStatePath4_not_unanimous`: [propext, Quot.sound]
- `splitStateTwoTriangles_is_fixed`: [propext, Classical.choice, Quot.sound]
- `splitStateTwoTriangles_not_unanimous`: [propext, Quot.sound]
- `unanimity_not_inevitable`: [propext, Classical.choice, Quot.sound]

Zero project axioms are used.
-/

@[expose] public section

open MajorityImitation

/- Verify the axioms for each proved theorem -/
#print axioms splitStatePath4_is_fixed
#print axioms splitStatePath4_not_unanimous
#print axioms splitStateTwoTriangles_is_fixed
#print axioms splitStateTwoTriangles_not_unanimous
#print axioms unanimity_not_inevitable

end
