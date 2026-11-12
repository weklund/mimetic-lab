module

import SackTheorem.MimeticNetwork

/-!
# Axiom audit

`lake build` succeeds even when a proof is an unfinished placeholder: the first CI run
on this formalization passed with four of them. So "fully proved" cannot be a README
claim. Each `#guard_msgs` below pins the exact axioms a proved theorem depends on. If a
proof, or anything it uses, becomes a placeholder, its list gains `sorryAx` and the build
fails here. The same happens if a proof starts depending on any new axiom.

Unproved statements are `proof_wanted`, which nothing can use, so they never reach a
proof. `propext`, `Classical.choice`, and `Quot.sound` are Lean's standard axioms.

When you add a theorem, add its line here.
-/

/-- info: 'MimeticTheory.exists_path_in_minimum_mms' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms MimeticTheory.exists_path_in_minimum_mms

/-- info: 'MimeticTheory.walk_same_obj' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms MimeticTheory.walk_same_obj

/-- info: 'MimeticTheory.convergence_of_desire' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms MimeticTheory.convergence_of_desire

/-- info: 'MimeticTheory.convergence_on_weak_component' does not depend on any axioms -/
#guard_msgs in
#print axioms MimeticTheory.convergence_on_weak_component

/-- info: 'MimeticTheory.non_identity_of_desire' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms MimeticTheory.non_identity_of_desire

/-- info: 'MimeticTheory.unique_narcissist_of_weakly_connected' does not depend on any axioms -/
#guard_msgs in
#print axioms MimeticTheory.unique_narcissist_of_weakly_connected

/-- info: 'MimeticTheory.existence_equilibrium_no_narcissism_only_if' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms MimeticTheory.existence_equilibrium_no_narcissism_only_if

/-- info: 'MimeticTheory.existence_equilibrium_no_narcissism_if' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms MimeticTheory.existence_equilibrium_no_narcissism_if

/-- info: 'MimeticTheory.existence_equilibrium_with_narcissism' does not depend on any axioms -/
#guard_msgs in
#print axioms MimeticTheory.existence_equilibrium_with_narcissism

/-- info: 'MimeticTheory.number_of_objects_bound' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms MimeticTheory.number_of_objects_bound
