module

public import Mathlib.Data.Fintype.Basic
public import Mathlib.Data.Finset.Basic
public import Mathlib.Combinatorics.SimpleGraph.Basic
public import Mathlib.Combinatorics.SimpleGraph.Finite
public import Mathlib.Data.Nat.Basic
public import Mathlib.Data.Int.Basic
public import Mathlib.Algebra.Order.Ring.Int
public import Mathlib.Algebra.Order.Ring.Abs
public import Mathlib.Algebra.Order.BigOperators.Group.Finset
public import Mathlib.Algebra.BigOperators.Ring.Finset
public import Mathlib.Order.WellFounded
public import Mathlib.Tactic.Ring
public import Batteries.Logic

/-
Copyright (c) 2026 Wes Eklund. All rights reserved.
Released under MIT license.

Authors: Cursor Cloud Agent

# Majority Imitation: Binary Labels and Period-2 Convergence

This file formalizes deterministic majority imitation on binary labels,
addressing claim O5 in `claims/claims.yaml`.

## Epistemic limitations

This formalization proves theorems about the stated model: finite simple graphs
with binary labels (0 or 1), synchronous update, and deterministic majority rule
(each agent adopts the strict majority of its neighbors and keeps its own label
on a tie). It does NOT prove claims about Girard's anthropological theory (G4)
or about continuous hostility, multiplying attraction, or scapegoat mechanisms.

**Formalization delta relative to G4:**
- Discrete binary labels, not continuous hostility
- Deterministic synchronous update, not a recruitment process whose pull
  multiplies with the number already polarized
- No objects and no acquisitive rivalry stage; agents copy labels directly
- No scapegoat-specific mechanism
- What is proved here is that every trajectory of this binary majority rule
  eventually has period dividing 2 (a fixed point or a 2-cycle), together with
  explicit split fixed points, so unanimity is not inevitable under this rule.
  This is not G4's inevitable unanimity (see O6 for the split examples).

A pass upgrades only this formalization of the majority rule, never G4 or any Girard claim.

## Assumptions

1. The graph is finite, simple (undirected, no self-loops, no multi-edges),
   and fixed (no growth or rewiring).
2. Each vertex holds a binary label (value in {0, 1}).
3. Update is synchronous: all vertices compute their new label based on the
   current state, then all update simultaneously.
4. The majority rule: each agent adopts the bit held by a strict majority of
   its neighbors. On a tie (exactly half of neighbors hold each label, or the
   agent has zero neighbors), the agent keeps its own label.

## Main results

1. **Period dividing 2** (Goles-Olivos): `period_at_most_2`. From any initial
   state the trajectory eventually has period dividing 2, a fixed point or a
   2-cycle.

2. **Explicit split fixed points**: concrete small graphs and states that are
   fixed and not unanimous, proved by `decide`.

3. **Corollary**: there exist a graph and an initial state such that unanimity
   never occurs (uses the fixed point proofs).
-/

@[expose] public section

namespace MajorityImitation

variable {V : Type*}

/-- Binary label: 0 or 1 -/
abbrev BinaryLabel := Fin 2

/-- A state assigns a binary label to each vertex -/
def State (V : Type*) := V → BinaryLabel

/-- The majority rule: adopt the bit held by a strict majority of neighbors,
    or keep own label on a tie. -/
def majorityRule (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V]
    (s : State V) (v : V) : BinaryLabel :=
  let neighbors := G.neighborFinset v
  letI : DecidablePred fun u => s u = 0 := fun _ => inferInstance
  letI : DecidablePred fun u => s u = 1 := fun _ => inferInstance
  let zeros := neighbors.filter (fun u => s u = 0)
  let ones := neighbors.filter (fun u => s u = 1)
  if zeros.card > ones.card then 0
  else if ones.card > zeros.card then 1
  else s v

/-- Synchronous update: all vertices update simultaneously -/
def step (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V] (s : State V) : State V :=
  fun v => majorityRule G s v

/-- A state is a fixed point if stepping yields the same state -/
def isFixedPoint (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V] (s : State V) : Prop :=
  ∀ v, step G s v = s v

instance isFixedPoint_decidable (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V] (s : State V) :
    Decidable (isFixedPoint G s) := by
  unfold isFixedPoint
  haveI : DecidablePred fun v => step G s v = s v := fun v => inferInstance
  exact Fintype.decidableForallFintype

/-- A state is unanimous if all vertices have the same label -/
def isUnanimous {V : Type*} [Nonempty V] (s : State V) : Prop :=
  ∃ b : BinaryLabel, ∀ v : V, s v = b

/-- The 4-vertex path graph: edges 0-1, 1-2, 2-3 and no others -/
def pathGraph4 : SimpleGraph (Fin 4) :=
  SimpleGraph.fromRel fun i j =>
    (i = 0 ∧ j = 1) ∨ (i = 1 ∧ j = 0) ∨
    (i = 1 ∧ j = 2) ∨ (i = 2 ∧ j = 1) ∨
    (i = 2 ∧ j = 3) ∨ (i = 3 ∧ j = 2)

instance : DecidableRel pathGraph4.Adj := fun i j => by
  unfold pathGraph4 SimpleGraph.fromRel
  infer_instance

/-- The state (0,0,1,1) on the 4-vertex path -/
def splitStatePath4 : State (Fin 4)
  | 0 => 0
  | 1 => 0
  | 2 => 1
  | 3 => 1

/-- The 4-vertex path with (0,0,1,1) is a fixed point -/
theorem splitStatePath4_is_fixed : isFixedPoint pathGraph4 splitStatePath4 := by
  decide

/-- The 4-vertex path with (0,0,1,1) is not unanimous -/
theorem splitStatePath4_not_unanimous : ¬isUnanimous splitStatePath4 := by
  unfold isUnanimous splitStatePath4
  intro ⟨b, h⟩
  have h0 : (0 : Fin 2) = b := h 0
  have h2 : (1 : Fin 2) = b := h 2
  subst h0
  simp at h2

/-- Two triangles joined by edge 2-3: {0,1,2} form a triangle, {3,4,5} form a triangle -/
def twoTrianglesGraph : SimpleGraph (Fin 6) :=
  SimpleGraph.fromRel fun i j =>
    (i = 0 ∧ j = 1) ∨ (i = 1 ∧ j = 0) ∨
    (i = 0 ∧ j = 2) ∨ (i = 2 ∧ j = 0) ∨
    (i = 1 ∧ j = 2) ∨ (i = 2 ∧ j = 1) ∨
    (i = 2 ∧ j = 3) ∨ (i = 3 ∧ j = 2) ∨
    (i = 3 ∧ j = 4) ∨ (i = 4 ∧ j = 3) ∨
    (i = 3 ∧ j = 5) ∨ (i = 5 ∧ j = 3) ∨
    (i = 4 ∧ j = 5) ∨ (i = 5 ∧ j = 4)

instance : DecidableRel twoTrianglesGraph.Adj := fun i j => by
  unfold twoTrianglesGraph SimpleGraph.fromRel
  infer_instance

/-- The state (0,0,0,1,1,1) on two triangles -/
def splitStateTwoTriangles : State (Fin 6)
  | 0 => 0
  | 1 => 0
  | 2 => 0
  | 3 => 1
  | 4 => 1
  | 5 => 1

/-- Two triangles with (0,0,0,1,1,1) is a fixed point -/
theorem splitStateTwoTriangles_is_fixed : isFixedPoint twoTrianglesGraph splitStateTwoTriangles := by
  decide

/-- Two triangles with (0,0,0,1,1,1) is not unanimous -/
theorem splitStateTwoTriangles_not_unanimous : ¬isUnanimous splitStateTwoTriangles := by
  unfold isUnanimous splitStateTwoTriangles
  intro ⟨b, h⟩
  have h0 : (0 : Fin 2) = b := h 0
  have h3 : (1 : Fin 2) = b := h 3
  subst h0
  simp at h3

/-- Map a binary label to a spin in `{+1, -1}`. -/
def toSpin (b : BinaryLabel) : ℤ :=
  if b = 0 then -1 else 1

lemma toSpin_zero : toSpin 0 = -1 := by simp [toSpin]

lemma toSpin_one : toSpin 1 = 1 := by simp [toSpin]

lemma abs_toSpin (b : BinaryLabel) : |toSpin b| = 1 := by
  match b with
  | 0 => simp [toSpin]
  | 1 => simp [toSpin]

/-- Local field `h_v(s) = 2 * (sum of neighbor spins) + spin(v)`.
Edge weight 2 and self weight 1 encode strict majority with keep-own-on-tie.
The field is never zero. -/
def localField (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (s : State V) (v : V) : ℤ :=
  2 * ∑ u ∈ G.neighborFinset v, toSpin (s u) + toSpin (s v)

lemma localField_ne_zero (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (s : State V) (v : V) : localField G s v ≠ 0 := by
  unfold localField
  match s v with
  | 0 =>
    simp only [toSpin]
    omega
  | 1 =>
    simp only [toSpin]
    omega

/-- `instDecidablePredComp` from Batteries, kept local so it does not leave this module. -/
local instance (s : State V) (b : BinaryLabel) : DecidablePred (fun u : V => s u = b) :=
  instDecidablePredComp (p := (· = b)) (f := s)

/-- Neighbor-spin sum equals `(number of neighbors labeled 1) - (number labeled 0)`. -/
lemma neighbor_spin_sum (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V]
    (s : State V) (v : V) :
    ∑ u ∈ G.neighborFinset v, toSpin (s u) =
      ((G.neighborFinset v).filter (fun u => s u = 1)).card -
        ((G.neighborFinset v).filter (fun u => s u = 0)).card := by
  classical
  let N := G.neighborFinset v
  let zeros := N.filter (fun u => s u = 0)
  let ones := N.filter (fun u => s u = 1)
  have hdisj : Disjoint zeros ones := by
    rw [Finset.disjoint_left]
    intro u hz ho
    simp only [Finset.mem_filter, zeros, ones] at hz ho
    exact absurd (hz.2.symm.trans ho.2) (by decide : (0 : Fin 2) ≠ 1)
  have hunion : zeros ∪ ones = N := by
    ext u
    constructor
    · intro hu
      simp only [Finset.mem_union, Finset.mem_filter, zeros, ones] at hu
      rcases hu with hu | hu
      · exact hu.1
      · exact hu.1
    · intro hu
      have hlabel : s u = 0 ∨ s u = 1 := by
        match s u with
        | 0 => left; rfl
        | 1 => right; rfl
      rcases hlabel with h0 | h1
      · simp [Finset.mem_union, Finset.mem_filter, zeros, ones, hu, h0]
      · simp [Finset.mem_union, Finset.mem_filter, zeros, ones, hu, h1]
  suffices ∑ u ∈ N, toSpin (s u) = (ones.card : ℤ) - (zeros.card : ℤ) by
    simpa [N, zeros, ones] using this
  rw [← hunion, Finset.sum_union hdisj]
  have hz : ∑ u ∈ zeros, toSpin (s u) = ∑ _u ∈ zeros, (-1 : ℤ) := by
    apply Finset.sum_congr rfl
    intro u hu
    simp only [Finset.mem_filter, zeros] at hu
    simp [hu.2, toSpin]
  have ho : ∑ u ∈ ones, toSpin (s u) = ∑ _u ∈ ones, (1 : ℤ) := by
    apply Finset.sum_congr rfl
    intro u hu
    simp only [Finset.mem_filter, ones] at hu
    simp [hu.2, toSpin]
  rw [hz, ho, Finset.sum_const, Finset.sum_const]
  simp only [nsmul_eq_mul]
  omega

/-- One step is the sign of the local field: strict majority when the neighbor
sum is nonzero, and the vertex's own label on a tie. -/
lemma step_eq_sign_localField (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V]
    (s : State V) (v : V) :
    toSpin (step G s v) = if localField G s v < 0 then -1 else 1 := by
  classical
  have hsum := neighbor_spin_sum G s v
  have hstep : step G s v =
      (if {u ∈ G.neighborFinset v | s u = 0}.card > {u ∈ G.neighborFinset v | s u = 1}.card then 0
        else if {u ∈ G.neighborFinset v | s u = 1}.card > {u ∈ G.neighborFinset v | s u = 0}.card then 1
        else s v) := by
    unfold step majorityRule
    dsimp
  rw [hstep]
  by_cases h0 : {u ∈ G.neighborFinset v | s u = 0}.card > {u ∈ G.neighborFinset v | s u = 1}.card
  · rw [ite_eq_left h0]
    have hfield : localField G s v < 0 := by
      unfold localField
      rw [hsum]
      match s v with
      | 0 => simp only [toSpin]; omega
      | 1 => simp only [toSpin]; omega
    rw [toSpin_zero, ite_eq_left hfield]
  · rw [ite_eq_right h0]
    by_cases h1 : {u ∈ G.neighborFinset v | s u = 1}.card > {u ∈ G.neighborFinset v | s u = 0}.card
    · rw [ite_eq_left h1]
      have hfield : 0 < localField G s v := by
        unfold localField
        rw [hsum]
        match s v with
        | 0 => simp only [toSpin]; omega
        | 1 => simp only [toSpin]; omega
      rw [toSpin_one, ite_eq_right (by omega : ¬ localField G s v < 0)]
    · rw [ite_eq_right h1]
      have heq : {u ∈ G.neighborFinset v | s u = 0}.card =
          {u ∈ G.neighborFinset v | s u = 1}.card := by omega
      have hfield : localField G s v = toSpin (s v) := by
        unfold localField
        rw [hsum, heq]
        ring
      rw [hfield]
      match s v with
      | 0 => rw [toSpin_zero, ite_eq_left (by decide : (-1 : ℤ) < 0)]
      | 1 => rw [toSpin_one, ite_eq_right (by decide : ¬ (1 : ℤ) < 0)]

/-- Sum of `g` over neighbors, written with an `if` so the two indices can be swapped. -/
lemma sum_neighbor_ite (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (v : V) (g : V → ℤ) :
    ∑ u ∈ G.neighborFinset v, g u = ∑ u : V, if G.Adj v u then g u else 0 := by
  classical
  rw [G.neighborFinset_eq_filter, Finset.sum_filter]

/-- The spin-field pairing is symmetric in its two states, because adjacency is symmetric. -/
lemma spin_field_symm (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (x y : State V) :
    ∑ v : V, toSpin (x v) * localField G y v =
      ∑ v : V, toSpin (y v) * localField G x v := by
  classical
  simp only [localField, mul_add, Finset.sum_add_distrib]
  have hself :
      ∑ v : V, toSpin (x v) * toSpin (y v) = ∑ v : V, toSpin (y v) * toSpin (x v) := by
    apply Finset.sum_congr rfl
    intro v _
    ring
  have hedge :
      ∑ v : V, toSpin (x v) * (2 * ∑ u ∈ G.neighborFinset v, toSpin (y u)) =
        ∑ v : V, toSpin (y v) * (2 * ∑ u ∈ G.neighborFinset v, toSpin (x u)) := by
    have hfactor : ∀ (a b : V → ℤ),
        ∑ v : V, a v * (2 * ∑ u ∈ G.neighborFinset v, b u) =
          2 * ∑ v : V, ∑ u ∈ G.neighborFinset v, a v * b u := by
      intro a b
      conv_lhs =>
        arg 2
        ext v
        rw [mul_left_comm (a v), Finset.mul_sum]
      rw [← Finset.mul_sum]
    rw [hfactor (fun v => toSpin (x v)) (fun v => toSpin (y v)),
      hfactor (fun v => toSpin (y v)) (fun v => toSpin (x v))]
    congr 1
    have hleft :
        ∑ v : V, ∑ u ∈ G.neighborFinset v, toSpin (x v) * toSpin (y u) =
          ∑ v : V, ∑ u : V, if G.Adj v u then toSpin (x v) * toSpin (y u) else 0 := by
      apply Finset.sum_congr rfl
      intro v _
      exact sum_neighbor_ite G v (fun u => toSpin (x v) * toSpin (y u))
    have hright :
        ∑ v : V, ∑ u ∈ G.neighborFinset v, toSpin (y v) * toSpin (x u) =
          ∑ v : V, ∑ u : V, if G.Adj v u then toSpin (y v) * toSpin (x u) else 0 := by
      apply Finset.sum_congr rfl
      intro v _
      exact sum_neighbor_ite G v (fun u => toSpin (y v) * toSpin (x u))
    rw [hleft, hright, Finset.sum_comm]
    apply Finset.sum_congr rfl
    intro u _
    apply Finset.sum_congr rfl
    intro v _
    by_cases h : G.Adj v u
    · have h' : G.Adj u v := (G.adj_comm v u).mp h
      simp [h, h']
      ring
    · have h' : ¬ G.Adj u v := fun hv => h ((G.adj_comm u v).mp hv)
      simp [h, h']
  -- Reassociate the factor-of-two sums back to the `localField` shape.
  calc ∑ v, toSpin (x v) * (2 * ∑ u ∈ G.neighborFinset v, toSpin (y u)) +
          ∑ v, toSpin (x v) * toSpin (y v)
      = ∑ v, toSpin (y v) * (2 * ∑ u ∈ G.neighborFinset v, toSpin (x u)) +
          ∑ v, toSpin (y v) * toSpin (x v) := by rw [hedge, hself]
    _ = ∑ v, toSpin (y v) * (2 * ∑ u ∈ G.neighborFinset v, toSpin (x u)) +
          ∑ v, toSpin (y v) * toSpin (x v) := rfl

/-- Energy of a consecutive pair: `E = - ∑_v σ_v(next) * h_v(curr)`. -/
def energy (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (s_curr s_next : State V) : ℤ :=
  - ∑ v : V, toSpin (s_next v) * localField G s_curr v

/-- `E(y, z) - E(x, y) = - ∑_v (σ_v(z) - σ_v(x)) * h_v(y)`. -/
lemma energy_difference (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (x y z : State V) :
    energy G y z - energy G x y =
      - ∑ v : V, (toSpin (z v) - toSpin (x v)) * localField G y v := by
  simp only [energy]
  have hsym := spin_field_symm G y x
  have hterm : ∀ v, toSpin (x v) * localField G y v - toSpin (z v) * localField G y v =
      -((toSpin (z v) - toSpin (x v)) * localField G y v) := by
    intro v
    ring
  calc -(∑ v, toSpin (z v) * localField G y v) - -(∑ v, toSpin (y v) * localField G x v)
      = (∑ v, toSpin (y v) * localField G x v) - (∑ v, toSpin (z v) * localField G y v) := by omega
    _ = (∑ v, toSpin (x v) * localField G y v) - (∑ v, toSpin (z v) * localField G y v) := by
        rw [hsym]
    _ = ∑ v, (toSpin (x v) * localField G y v - toSpin (z v) * localField G y v) := by
        rw [← Finset.sum_sub_distrib]
    _ = ∑ v, -((toSpin (z v) - toSpin (x v)) * localField G y v) := by
        simp_rw [hterm]
    _ = -∑ v, (toSpin (z v) - toSpin (x v)) * localField G y v := by
        rw [Finset.sum_neg_distrib]

/-- If `z = step y` and `z v ≠ x v`, the vertex contribution is at least 2.
`z v` is the sign of `h_v(y)`, so it points the same way as the field and the
spin gap is `±2`. -/
lemma energy_decrease_term (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V]
    (x y z : State V) (v : V) (hz : z = step G y) (hneq : z v ≠ x v) :
    (toSpin (z v) - toSpin (x v)) * localField G y v ≥ 2 := by
  have hsign : toSpin (z v) = if localField G y v < 0 then -1 else 1 := by
    rw [hz]
    exact step_eq_sign_localField G y v
  have hx : x v = 0 ∨ x v = 1 := by
    match x v with
    | 0 => left; rfl
    | 1 => right; rfl
  have hzv : z v = 0 ∨ z v = 1 := by
    match z v with
    | 0 => left; rfl
    | 1 => right; rfl
  rcases hx with hx | hx <;> rcases hzv with hzv | hzv
  · simp [hx, hzv] at hneq
  · have hxspin : toSpin (x v) = -1 := by simp [toSpin, hx]
    have hzspin : toSpin (z v) = 1 := by simp [toSpin, hzv]
    have hnot : ¬ localField G y v < 0 := by
      intro hlt
      have : toSpin (z v) = -1 := by simp [hsign, hlt]
      simp [hzspin] at this
    have hpos : 1 ≤ localField G y v := by
      have hne := localField_ne_zero G y v
      omega
    rw [hxspin, hzspin]
    omega
  · have hxspin : toSpin (x v) = 1 := by simp [toSpin, hx]
    have hzspin : toSpin (z v) = -1 := by simp [toSpin, hzv]
    have hlt : localField G y v < 0 := by
      by_contra hge
      have : toSpin (z v) = 1 := by simp [hsign, hge]
      simp [hzspin] at this
    rw [hxspin, hzspin]
    have : localField G y v ≤ -1 := by omega
    omega
  · simp [hx, hzv] at hneq

/-- Every vertex contribution is nonnegative along one step. -/
lemma energy_term_nonneg (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V]
    (x y z : State V) (v : V) (hz : z = step G y) :
    0 ≤ (toSpin (z v) - toSpin (x v)) * localField G y v := by
  by_cases h : z v = x v
  · simp [h]
  · have hge := energy_decrease_term G x y z v hz h
    omega

/-- `|h_v| ≤ 2 * degree(v) + 1`, so the energy is bounded below independently of time. -/
lemma energy_lower_bound (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (s_curr s_next : State V) :
    -(∑ v : V, (2 * (G.neighborFinset v).card + 1 : ℤ)) ≤ energy G s_curr s_next := by
  set bound : ℤ := ∑ v : V, (2 * (G.neighborFinset v).card + 1 : ℤ)
  have hterm : ∀ v, |toSpin (s_next v) * localField G s_curr v| ≤
      (2 * (G.neighborFinset v).card + 1 : ℤ) := by
    intro v
    unfold localField
    have hspin_next : |toSpin (s_next v)| = 1 := abs_toSpin _
    have hspin_curr : |toSpin (s_curr v)| = 1 := abs_toSpin _
    have hsum : |∑ u ∈ G.neighborFinset v, toSpin (s_curr u)| ≤ (G.neighborFinset v).card := by
      calc |∑ u ∈ G.neighborFinset v, toSpin (s_curr u)|
          _ ≤ ∑ u ∈ G.neighborFinset v, |toSpin (s_curr u)| := Finset.abs_sum_le_sum_abs _ _
          _ = ∑ _u ∈ G.neighborFinset v, (1 : ℤ) := by
              apply Finset.sum_congr rfl
              intro u _
              exact abs_toSpin (s_curr u)
          _ = (G.neighborFinset v).card := by simp
    rw [abs_mul, hspin_next, one_mul]
    calc |2 * ∑ u ∈ G.neighborFinset v, toSpin (s_curr u) + toSpin (s_curr v)|
        _ ≤ |2 * ∑ u ∈ G.neighborFinset v, toSpin (s_curr u)| + |toSpin (s_curr v)| := abs_add_le _ _
        _ = 2 * |∑ u ∈ G.neighborFinset v, toSpin (s_curr u)| + |toSpin (s_curr v)| := by
            rw [abs_mul, abs_of_nonneg (by omega : (0 : ℤ) ≤ 2)]
        _ ≤ 2 * (G.neighborFinset v).card + 1 := by
            rw [hspin_curr]
            have := hsum
            omega
  have hsum_le : |∑ v : V, toSpin (s_next v) * localField G s_curr v| ≤ bound := by
    calc |∑ v : V, toSpin (s_next v) * localField G s_curr v|
        _ ≤ ∑ v : V, |toSpin (s_next v) * localField G s_curr v| := Finset.abs_sum_le_sum_abs _ _
        _ ≤ ∑ v : V, (2 * (G.neighborFinset v).card + 1 : ℤ) :=
            Finset.sum_le_sum (fun v _ => hterm v)
        _ = bound := rfl
  unfold energy
  calc -bound
      _ ≤ -|∑ v : V, toSpin (s_next v) * localField G s_curr v| := neg_le_neg hsum_le
      _ ≤ -∑ v : V, toSpin (s_next v) * localField G s_curr v :=
          neg_le_neg (le_abs_self _)

/-- From any initial state, the trajectory eventually has period dividing 2:
a fixed point or a 2-cycle.

`period_at_most_2` proves that the period divides 2.

The fixed-point disjunct is kept on purpose so the statement matches O5.
It is redundant: a fixed point at time `n` already satisfies
`(step G)^[n+k+2] s0 = (step G)^[n+k] s0` for every `k`, so the first
disjunct implies the second. -/
theorem period_at_most_2 (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V]
    (s0 : State V) :
    ∃ n : ℕ, isFixedPoint G ((step G)^[n] s0) ∨
             (∀ k : ℕ, (step G)^[n+k+2] s0 = (step G)^[n+k] s0) := by
  classical
  let E : ℕ → ℤ := fun t => energy G ((step G)^[t] s0) ((step G)^[t + 1] s0)
  let B : ℤ := ∑ v : V, (2 * (G.neighborFinset v).card + 1 : ℤ)
  have h_bound : ∀ t, -B ≤ E t := by
    intro t
    simpa [E, B] using energy_lower_bound G ((step G)^[t] s0) ((step G)^[t + 1] s0)
  have h_step_succ : ∀ t, (step G)^[t + 1] s0 = step G ((step G)^[t] s0) := by
    intro t
    rw [Function.iterate_succ_apply']
  have h_drop_sum : ∀ t,
      E t - E (t + 1) =
        ∑ v : V, (toSpin ((step G)^[t + 2] s0 v) - toSpin ((step G)^[t] s0 v)) *
          localField G ((step G)^[t + 1] s0) v := by
    intro t
    have hdiff := energy_difference G ((step G)^[t] s0) ((step G)^[t + 1] s0) ((step G)^[t + 2] s0)
    calc E t - E (t + 1)
        _ = -(E (t + 1) - E t) := by omega
        _ = -(- ∑ v : V, (toSpin ((step G)^[t + 2] s0 v) - toSpin ((step G)^[t] s0 v)) *
              localField G ((step G)^[t + 1] s0) v) := by rw [hdiff]
        _ = ∑ v : V, (toSpin ((step G)^[t + 2] s0 v) - toSpin ((step G)^[t] s0 v)) *
              localField G ((step G)^[t + 1] s0) v := by simp
  have h_nonneg_sum : ∀ t, 0 ≤ E t - E (t + 1) := by
    intro t
    rw [h_drop_sum t]
    apply Finset.sum_nonneg
    intro v _
    exact energy_term_nonneg G ((step G)^[t] s0) ((step G)^[t + 1] s0) ((step G)^[t + 2] s0) v
      (h_step_succ (t + 1))
  have h_mono : ∀ t, E (t + 1) ≤ E t := by
    intro t
    have := h_nonneg_sum t
    omega
  have h_strict : ∀ t, (step G)^[t + 2] s0 ≠ (step G)^[t] s0 → E t - E (t + 1) ≥ 2 := by
    intro t hneq
    have hex : ∃ v, (step G)^[t + 2] s0 v ≠ (step G)^[t] s0 v := by
      by_contra h
      apply hneq
      funext v
      by_contra hv
      exact h ⟨v, hv⟩
    obtain ⟨v, hv⟩ := hex
    have hge := energy_decrease_term G ((step G)^[t] s0) ((step G)^[t + 1] s0)
      ((step G)^[t + 2] s0) v (h_step_succ (t + 1)) hv
    have hnn : ∀ w ∈ Finset.univ, 0 ≤
        (toSpin ((step G)^[t + 2] s0 w) - toSpin ((step G)^[t] s0 w)) *
          localField G ((step G)^[t + 1] s0) w := by
      intro w _
      exact energy_term_nonneg G _ _ _ w (h_step_succ (t + 1))
    calc E t - E (t + 1)
        _ = ∑ w : V, (toSpin ((step G)^[t + 2] s0 w) - toSpin ((step G)^[t] s0 w)) *
              localField G ((step G)^[t + 1] s0) w := h_drop_sum t
        _ ≥ (toSpin ((step G)^[t + 2] s0 v) - toSpin ((step G)^[t] s0 v)) *
              localField G ((step G)^[t + 1] s0) v :=
            Finset.single_le_sum hnn (Finset.mem_univ v)
        _ ≥ 2 := hge
  have h_shift_nonneg : ∀ t, 0 ≤ E t + B := fun t => by
    have := h_bound t
    omega
  let μ : ℕ → ℕ := fun t => (E t + B).toNat
  have hμ_mono : ∀ t, μ (t + 1) ≤ μ t := by
    intro t
    have hle : E (t + 1) + B ≤ E t + B := by
      have := h_mono t
      omega
    have : ((E (t + 1) + B).toNat : ℤ) ≤ (E t + B).toNat := by
      rw [Int.toNat_of_nonneg (h_shift_nonneg (t + 1)), Int.toNat_of_nonneg (h_shift_nonneg t)]
      exact hle
    exact Int.ofNat_le.mp this
  let n : ℕ := Function.argmin μ
  have hmin : ∀ t, μ n ≤ μ t := by
    intro t
    have hnot : ¬ μ t < μ n := by
      simpa [n] using Function.not_lt_argmin μ t
    omega
  have hμ_le : ∀ k, μ (n + k) ≤ μ n := by
    intro k
    induction k with
    | zero => exact le_rfl
    | succ k ih =>
      have hidx : n + (k + 1) = n + k + 1 := by omega
      rw [hidx]
      exact le_trans (hμ_mono (n + k)) ih
  have hμ_eq : ∀ k, μ (n + k) = μ (n + k + 1) := by
    intro k
    have h1 : μ (n + k + 1) ≤ μ (n + k) := hμ_mono (n + k)
    have h2 : μ n ≤ μ (n + k + 1) := hmin (n + k + 1)
    have h3 : μ (n + k) ≤ μ n := hμ_le k
    omega
  have hE_eq : ∀ k, E (n + k) = E (n + k + 1) := by
    intro k
    have hμ := hμ_eq k
    have ha := h_shift_nonneg (n + k)
    have hb := h_shift_nonneg (n + k + 1)
    have hcast : E (n + k) + B = E (n + k + 1) + B := by
      have : ((E (n + k) + B).toNat : ℤ) = (E (n + k + 1) + B).toNat := by
        simpa [μ] using congrArg (fun m : ℕ => (m : ℤ)) hμ
      rw [Int.toNat_of_nonneg ha, Int.toNat_of_nonneg hb] at this
      exact this
    omega
  use n
  right
  intro k
  by_contra hneq
  have hdrop := h_strict (n + k) hneq
  have hEq := hE_eq k
  omega

/-- Corollary: unanimity is not inevitable.
    There exist a graph and an initial state such that unanimity never occurs. -/
theorem unanimity_not_inevitable :
    ∃ (V : Type) (_ : Fintype V) (_ : DecidableEq V) (G : SimpleGraph V)
      (_ : DecidableRel G.Adj) (s0 : State V) (_ : Nonempty V),
      ∀ n : ℕ, ¬isUnanimous ((step G)^[n] s0) := by
  use Fin 4, inferInstance, inferInstance, pathGraph4, inferInstance, splitStatePath4, inferInstance
  intro n
  have h_fixed_state : ∀ m, (step pathGraph4)^[m] splitStatePath4 = splitStatePath4 := by
    intro m
    induction m with
    | zero => rfl
    | succ m ih =>
      rw [Function.iterate_succ_apply']
      rw [ih]
      have : isFixedPoint pathGraph4 splitStatePath4 := splitStatePath4_is_fixed
      unfold isFixedPoint at this
      funext v
      exact this v
  rw [h_fixed_state n]
  exact splitStatePath4_not_unanimous

/-- The complete graph on two vertices. -/
def edgeK2 : SimpleGraph (Fin 2) :=
  SimpleGraph.fromRel fun i j => i ≠ j

instance : DecidableRel edgeK2.Adj := fun i j => by
  unfold edgeK2 SimpleGraph.fromRel
  infer_instance

/-- The state `(0, 1)` on `K₂`. -/
def stateK2_01 : State (Fin 2)
  | 0 => 0
  | 1 => 1

/-- On `K₂`, the state `(0, 1)` is not fixed: one step swaps the labels, and two steps return it. -/
theorem k2_state01_period_exactly_two :
    step edgeK2 stateK2_01 0 = 1 ∧
    step edgeK2 stateK2_01 1 = 0 ∧
    ¬ isFixedPoint edgeK2 stateK2_01 ∧
    (step edgeK2)^[2] stateK2_01 = stateK2_01 := by
  refine ⟨by decide, by decide, by decide, ?_⟩
  funext v
  match v with
  | 0 => decide
  | 1 => decide

end MajorityImitation

end
