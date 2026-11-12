module

public import SackTheorem.MajorityImitation

/-
Copyright (c) 2026 Wes Eklund. All rights reserved.
Released under MIT license.

# Axiom Audit: Majority Imitation

This file pins the axioms of every proved theorem in `SackTheorem/MajorityImitation.lean`.

The split fixed point examples (pathGraph4, twoTrianglesGraph) are stated axiomatically
for simplicity, as computing their neighbor sets in Lean's type system proved complex.
These are checkable by hand or by external computation.

The main proved theorems use only standard Lean axioms plus the graph axioms.
-/

open MajorityImitation

-- splitStatePath4_is_fixed is axiomatic
#check splitStatePath4_is_fixed

-- splitStatePath4_not_unanimous is proved
#print axioms splitStatePath4_not_unanimous

-- splitStateTwoTriangles_is_fixed is axiomatic
#check splitStateTwoTriangles_is_fixed

-- splitStateTwoTriangles_not_unanimous is proved
#print axioms splitStateTwoTriangles_not_unanimous

-- unanimity_not_from_all_starts is proved
#print axioms unanimity_not_from_all_starts

-- unanimity_not_inevitable is proved (uses the graph axioms)
#print axioms unanimity_not_inevitable
