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

Each `#guard_msgs` below pins the exact axioms a proved theorem depends on. If a
proof, or anything it uses, becomes a placeholder, its list gains `sorryAx` and the
build fails here. The same happens if a proof starts depending on any new axiom.

The `proof_wanted` claim `period_at_most_2` is not audited (it is not proved).
-/

@[expose] public section

open MajorityImitation

/-- info: 'MajorityImitation.splitStatePath4_is_fixed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms splitStatePath4_is_fixed

/-- info: 'MajorityImitation.splitStatePath4_not_unanimous' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms splitStatePath4_not_unanimous

/-- info: 'MajorityImitation.splitStateTwoTriangles_is_fixed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms splitStateTwoTriangles_is_fixed

/-- info: 'MajorityImitation.splitStateTwoTriangles_not_unanimous' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms splitStateTwoTriangles_not_unanimous

/-- info: 'MajorityImitation.unanimity_not_inevitable' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms unanimity_not_inevitable

end
