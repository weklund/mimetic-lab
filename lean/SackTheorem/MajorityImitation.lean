module

public import Mathlib.Data.Fintype.Basic
public import Mathlib.Data.Finset.Basic
public import Mathlib.Combinatorics.SimpleGraph.Basic
public import Mathlib.Combinatorics.SimpleGraph.Finite
public import Mathlib.Data.Nat.Basic
public import Mathlib.Data.Int.Basic
public import Mathlib.Algebra.Order.Ring.Int
public import Batteries.Util.ProofWanted

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
- This is only the period bound for the binary rule, not G4's inevitable
  unanimity (see O6 for split fixed points)

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

1. **Period at most 2** (Goles-Olivos style): stated as `proof_wanted`. The full
   proof requires an energy (Lyapunov) function argument. Leaving this unproved
   does not upgrade O5, which remains reported-by-source.

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

/-- Map binary label to spin in {-1, +1} -/
def toSpin (b : BinaryLabel) : ℤ :=
  if b = 0 then -1 else 1

/-- Inverse: map spin back to binary label (sign function) -/
def fromSpin (z : ℤ) : BinaryLabel :=
  if z < 0 then 0 else 1

lemma toSpin_zero : toSpin 0 = -1 := rfl
lemma toSpin_one : toSpin 1 = 1 := by decide

/-- toSpin values are ±1 -/
lemma toSpin_abs (b : BinaryLabel) : toSpin b = -1 ∨ toSpin b = 1 := by
  match b with
  | 0 => left; rfl
  | 1 => right; decide

/-- The local field at vertex v: h_v(s) = 2 * (sum of spins of neighbors) + spin of v.
    This encodes edge weight 2 and self weight 1, implementing keep-own-on-tie. -/
def localField (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (s : State V) (v : V) : ℤ :=
  2 * (G.neighborFinset v).sum (fun u => toSpin (s u)) + toSpin (s v)

/-- The local field is always odd, hence never zero -/
lemma localField_odd (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (s : State V) (v : V) : Odd (localField G s v) := by
  unfold localField
  -- 2 * sum is even, toSpin is odd (either -1 or 1)
  have h_spin_odd : Odd (toSpin (s v)) := by
    rcases toSpin_abs (s v) with h | h <;> rw [h]
    · use -1; ring
    · use 0; ring
  have h_even : Even (2 * (G.neighborFinset v).sum (fun u => toSpin (s u))) := by
    use (G.neighborFinset v).sum (fun u => toSpin (s u))
    rfl
  obtain ⟨k1, hk1⟩ := h_even
  obtain ⟨k2, hk2⟩ := h_spin_odd
  use k1 + k2
  calc 2 * (G.neighborFinset v).sum (fun u => toSpin (s u)) + toSpin (s v)
    _ = 2 * k1 + (2 * k2 + 1) := by rw [hk1, hk2]
    _ = 2 * (k1 + k2) + 1 := by ring

lemma localField_ne_zero (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (s : State V) (v : V) : localField G s v ≠ 0 := by
  have := localField_odd G s v
  obtain ⟨k, hk⟩ := this
  rw [hk]
  omega

/-- Key lemma: the step function equals sign of local field.
    This is where the majority rule counting lives. -/
lemma step_eq_sign_localField (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V]
    (s : State V) (v : V) : toSpin (step G s v) = if localField G s v < 0 then -1 else 1 := by
  unfold step majorityRule localField
  let neighbors := G.neighborFinset v
  letI : DecidablePred fun u => s u = 0 := fun _ => inferInstance
  letI : DecidablePred fun u => s u = 1 := fun _ => inferInstance
  let zeros := neighbors.filter (fun u => s u = 0)
  let ones := neighbors.filter (fun u => s u = 1)
  
  -- Express the sum of spins in terms of zeros and ones
  have h_partition : neighbors = zeros ∪ ones := by
    ext u
    simp [zeros, ones]
    match s u with
    | 0 => constructor <;> intro <;> simp
    | 1 => constructor <;> intro <;> simp
  
  have h_disjoint : Disjoint zeros ones := by
    simp [Finset.disjoint_iff_ne, zeros, ones]
    intro a ha b hb
    simp at ha hb
    omega
  
  have h_sum : neighbors.sum (fun u => toSpin (s u)) = (ones.card : ℤ) - (zeros.card : ℤ) := by
    calc neighbors.sum (fun u => toSpin (s u))
      _ = (zeros ∪ ones).sum (fun u => toSpin (s u)) := by rw [← h_partition]
      _ = zeros.sum (fun u => toSpin (s u)) + ones.sum (fun u => toSpin (s u)) := by
          apply Finset.sum_union
          exact h_disjoint
      _ = zeros.sum (fun _ => (-1 : ℤ)) + ones.sum (fun _ => (1 : ℤ)) := by
          congr 1
          · apply Finset.sum_congr rfl
            intro u hu
            simp [zeros] at hu
            rw [hu.2]
            rfl
          · apply Finset.sum_congr rfl
            intro u hu
            simp [ones] at hu
            rw [hu.2]
            rfl
      _ = -(zeros.card : ℤ) + (ones.card : ℤ) := by simp
      _ = (ones.card : ℤ) - (zeros.card : ℤ) := by ring
  
  -- Now analyze the cases
  split_ifs with h1 h2
  · -- Case: zeros.card > ones.card
    -- Then output is 0, so toSpin = -1
    -- And h_v = 2 * (ones - zeros) + toSpin(s v) < 0
    have h_field : 2 * neighbors.sum (fun u => toSpin (s u)) + toSpin (s v) < 0 := by
      rw [h_sum]
      have : (zeros.card : ℤ) > (ones.card : ℤ) := Int.ofNat_lt.mpr h1
      rcases toSpin_abs (s v) with hs | hs <;> rw [hs] <;> omega
    simp [toSpin, h_field]
  · -- Case: ones.card > zeros.card
    -- Then output is 1, so toSpin = 1
    -- And h_v = 2 * (ones - zeros) + toSpin(s v) > 0
    have h_field : 2 * neighbors.sum (fun u => toSpin (s u)) + toSpin (s v) > 0 := by
      rw [h_sum]
      have : (ones.card : ℤ) > (zeros.card : ℤ) := Int.ofNat_lt.mpr h2
      rcases toSpin_abs (s v) with hs | hs <;> rw [hs] <;> omega
    have h_field_nonneg : 2 * neighbors.sum (fun u => toSpin (s u)) + toSpin (s v) >= 0 := by omega
    simp [toSpin, h_field, h_field_nonneg]
  · -- Case: tie (zeros.card = ones.card)
    -- Then output is s v
    -- And h_v = 2 * 0 + toSpin(s v) = toSpin(s v)
    push_neg at h1 h2
    have h_eq : zeros.card = ones.card := by omega
    have h_field : 2 * neighbors.sum (fun u => toSpin (s u)) + toSpin (s v) = toSpin (s v) := by
      rw [h_sum, h_eq]
      ring
    rcases toSpin_abs (s v) with hs | hs <;> rw [hs] at h_field ⊢
    · -- s v = 0, so toSpin (s v) = -1, field = -1 < 0
      have : toSpin 0 = -1 := rfl
      rw [← this] at h_field ⊢
      simp at h_field ⊢
      exact h_field
    · -- s v = 1, so toSpin (s v) = 1, field = 1 >= 0
      have : toSpin 1 = 1 := by decide
      rw [← this] at h_field ⊢
      simp at h_field ⊢
      constructor
      · omega
      · exact h_field

/-- Energy function on consecutive states: E(t) = -sum_v sigma_v(s_{t+1}) * h_v(s_t) -/
def energy (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (s_curr s_next : State V) : ℤ :=
  - Finset.univ.sum (fun v : V => toSpin (s_next v) * localField G s_curr v)

/-- Symmetry lemma: sum_v spin_v(x) * h_v(y) = sum_v spin_v(y) * h_v(x).
    This follows from the symmetry of the adjacency relation. -/
lemma energy_symmetric (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (x y : State V) :
    Finset.univ.sum (fun v => toSpin (x v) * localField G y v) =
    Finset.univ.sum (fun v => toSpin (y v) * localField G x v) := by
  unfold localField
  simp_rw [mul_add, mul_comm (toSpin _) (toSpin _), Finset.sum_add_distrib]
  congr 1
  · -- Show: sum_v toSpin(x v) * 2 * sum_u toSpin(y u) * adj = sum_v toSpin(y v) * 2 * sum_u toSpin(x u) * adj
    simp_rw [mul_comm _ 2, mul_assoc 2]
    congr 1
    -- This is the edge symmetry: sum over edges of spin(x_v) * spin(y_u) = sum over edges of spin(y_v) * spin(x_u)
    calc Finset.univ.sum (fun v => toSpin (x v) * (G.neighborFinset v).sum (fun u => toSpin (y u)))
      _ = Finset.univ.sum (fun v => (G.neighborFinset v).sum (fun u => toSpin (x v) * toSpin (y u))) := by
          congr; ext v; rw [Finset.mul_sum]
      _ = Finset.univ.sum (fun v => (G.neighborFinset v).sum (fun u => toSpin (y u) * toSpin (x v))) := by
          congr; ext v; congr; ext u; ring
      _ = Finset.univ.sum (fun v => (G.neighborFinset v).sum (fun u => toSpin (x v) * toSpin (y u))) := by
          congr; ext v; congr; ext u; ring
      _ = Finset.univ.sum (fun u => (G.neighborFinset u).sum (fun v => toSpin (x v) * toSpin (y u))) := by
          -- Swap the order of summation using edge symmetry
          rw [Finset.sum_comm]
          congr; ext u; congr; ext v
          by_cases h : G.Adj v u
          · simp [SimpleGraph.mem_neighborFinset, h, SimpleGraph.adj_comm.mp h]
          · have : ¬G.Adj u v := fun h' => h (SimpleGraph.adj_comm.mp h')
            simp [SimpleGraph.mem_neighborFinset, h, this]
      _ = Finset.univ.sum (fun u => toSpin (y u) * (G.neighborFinset u).sum (fun v => toSpin (x v))) := by
          congr; ext u; rw [← Finset.sum_mul]; congr; ext v; ring

/-- Energy difference: E(t+1) - E(t) = -sum_v (sigma_v(s_{t+2}) - sigma_v(s_t)) * h_v(s_{t+1}) -/
lemma energy_difference (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V]
    (s0 : State V) (t : ℕ) :
    let s_t := (step G)^[t] s0
    let s_t1 := (step G)^[t+1] s0
    let s_t2 := (step G)^[t+2] s0
    energy G s_t1 s_t2 - energy G s_t s_t1 =
    - Finset.univ.sum (fun v => (toSpin (s_t2 v) - toSpin (s_t v)) * localField G s_t1 v) := by
  unfold energy
  ring_nf
  congr 1
  calc Finset.univ.sum (fun v => toSpin (s_t1 v) * localField G s_t v) 
      - Finset.univ.sum (fun v => toSpin (s_t2 v) * localField G s_t1 v)
    _ = Finset.univ.sum (fun v => toSpin (s_t v) * localField G s_t1 v)
      - Finset.univ.sum (fun v => toSpin (s_t2 v) * localField G s_t1 v) := by
        congr 1
        exact energy_symmetric G s_t1 s_t
    _ = Finset.univ.sum (fun v => (toSpin (s_t v) - toSpin (s_t2 v)) * localField G s_t1 v) := by
        rw [← Finset.sum_sub_distrib]
        congr; ext v; ring

/-- If sigma_v(s_{t+2}) ≠ sigma_v(s_t), then sigma_v(s_{t+2}) = sign(h_v(s_{t+1})),
    so the contribution to the energy decrease is 2 * |h_v(s_{t+1})| >= 2. -/
lemma energy_decrease_term (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V]
    (s_t s_t1 s_t2 : State V) (v : V)
    (h_step1 : s_t1 = step G s_t)
    (h_step2 : s_t2 = step G s_t1)
    (h_neq : s_t2 v ≠ s_t v) :
    -(toSpin (s_t2 v) - toSpin (s_t v)) * localField G s_t1 v >= 2 := by
  -- By step lemma, toSpin (s_t2 v) = sign(h_v(s_t1))
  have h_sign : toSpin (s_t2 v) = if localField G s_t1 v < 0 then -1 else 1 := by
    rw [h_step2]
    exact step_eq_sign_localField G s_t1 v
  
  -- Since s_t2 v ≠ s_t v, we have toSpin (s_t2 v) ≠ toSpin (s_t v)
  have h_spin_neq : toSpin (s_t2 v) ≠ toSpin (s_t v) := by
    intro h_contra
    apply h_neq
    -- If spins are equal, labels are equal
    -- toSpin maps 0 to -1 and 1 to 1, so if spins are equal, labels are equal
    match s_t v, s_t2 v with
    | 0, 0 => rfl
    | 0, 1 => simp [toSpin] at h_contra
    | 1, 0 => simp [toSpin] at h_contra
    | 1, 1 => rfl
  
  -- The spins are ±1, and they differ, so one is 1 and one is -1
  rcases toSpin_abs (s_t v) with ht | ht <;> rcases toSpin_abs (s_t2 v) with ht2 | ht2
  · -- Both -1, contradiction
    rw [ht, ht2] at h_spin_neq; contradiction
  · -- s_t: -1, s_t2: 1, so difference is -2, and h_v > 0
    rw [ht, ht2] at h_sign h_spin_neq ⊢
    simp at h_sign
    have h_field_pos : localField G s_t1 v > 0 := by
      by_contra h_contra; push_neg at h_contra
      have : localField G s_t1 v < 0 := by
        have := localField_ne_zero G s_t1 v
        omega
      omega
    calc -(1 - (-1)) * localField G s_t1 v 
      _ = -2 * localField G s_t1 v := by ring
      _ >= 2 := by nlinarith
  · -- s_t: 1, s_t2: -1, so difference is 2, and h_v < 0
    rw [ht, ht2] at h_sign h_spin_neq ⊢
    simp at h_sign
    have h_field_neg : localField G s_t1 v < 0 := by omega
    calc -((-1) - 1) * localField G s_t1 v
      _ = 2 * localField G s_t1 v := by ring
      _ >= 2 := by nlinarith [localField_odd G s_t1 v]
  · -- Both 1, contradiction
    rw [ht, ht2] at h_spin_neq; contradiction

/-- Energy is bounded -/
lemma energy_bounded (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (s_curr s_next : State V) :
    |energy G s_curr s_next| ≤ Finset.univ.sum (fun v : V => 2 * (G.neighborFinset v).card + 1) := by
  unfold energy localField
  have h_bound : ∀ v, |toSpin (s_next v) * (2 * (G.neighborFinset v).sum (fun u => toSpin (s_curr u)) + toSpin (s_curr v))| 
      ≤ 2 * (G.neighborFinset v).card + 1 := by
    intro v
    -- |toSpin| = 1, |sum of spins| <= |neighborFinset|, so |field| <= 2*degree + 1
    have h_spin_bound : |toSpin (s_next v)| = 1 := by
      rcases toSpin_abs (s_next v) with h | h <;> rw [h]
      · norm_num
      · norm_num
    have h_sum_bound : |(G.neighborFinset v).sum (fun u => toSpin (s_curr u))| ≤ (G.neighborFinset v).card := by
      trans (G.neighborFinset v).sum (fun u => |toSpin (s_curr u)|)
      · exact Finset.abs_sum_le_sum_abs _ _
      · calc (G.neighborFinset v).sum (fun u => |toSpin (s_curr u)|)
          _ = (G.neighborFinset v).sum (fun _ => (1 : ℤ)) := by
              congr; ext u; rcases toSpin_abs (s_curr u) with h | h <;> rw [h] <;> norm_num
          _ = (G.neighborFinset v).card := Finset.sum_const_nat (fun _ _ => rfl)
    rw [abs_mul, h_spin_bound, one_mul]
    calc |2 * (G.neighborFinset v).sum (fun u => toSpin (s_curr u)) + toSpin (s_curr v)|
      _ ≤ |2 * (G.neighborFinset v).sum (fun u => toSpin (s_curr u))| + |toSpin (s_curr v)| := abs_add _ _
      _ = 2 * |(G.neighborFinset v).sum (fun u => toSpin (s_curr u))| + |toSpin (s_curr v)| := by rw [abs_mul]; norm_num
      _ ≤ 2 * (G.neighborFinset v).card + 1 := by
          have : |toSpin (s_curr v)| = 1 := by
            rcases toSpin_abs (s_curr v) with h | h <;> rw [h]
            · norm_num
            · norm_num
          rw [this]
          omega
  calc |energy G s_curr s_next|
    _ = |- Finset.univ.sum (fun v => toSpin (s_next v) * localField G s_curr v)| := rfl
    _ = |Finset.univ.sum (fun v => toSpin (s_next v) * localField G s_curr v)| := abs_neg _
    _ ≤ Finset.univ.sum (fun v => |toSpin (s_next v) * localField G s_curr v|) := Finset.abs_sum_le_sum_abs _ _
    _ = Finset.univ.sum (fun v => |toSpin (s_next v) * (2 * (G.neighborFinset v).sum (fun u => toSpin (s_curr u)) + toSpin (s_curr v))|) := rfl
    _ ≤ Finset.univ.sum (fun v => 2 * (G.neighborFinset v).card + 1) := Finset.sum_le_sum h_bound

/-- Main theorem: Period at most 2 (Goles-Olivos style).
    From any initial state, the trajectory eventually has period dividing 2:
    it reaches a fixed point or alternates between two states.
    
    The proof uses an integer energy function that is nonincreasing and strictly decreases
    when s(t+2) ≠ s(t). Since integer energy is bounded below, it eventually stabilizes,
    giving period 2.
    
    Note: The first disjunct (fixed point) is implied by the second (period dividing 2
    with k=0), but we keep both to match the Goles-Olivos statement. -/
theorem period_at_most_2 (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V]
    (s0 : State V) :
    ∃ n : ℕ, isFixedPoint G ((step G)^[n] s0) ∨
             (∀ k : ℕ, (step G)^[n+k+2] s0 = (step G)^[n+k] s0) := by
  classical
  -- Define the energy sequence
  let E : ℕ → ℤ := fun t => energy G ((step G)^[t] s0) ((step G)^[t+1] s0)
  
  -- Energy is bounded below
  let bound := Finset.univ.sum (fun v : V => 2 * (G.neighborFinset v).card + 1)
  have h_bounded : ∀ t, -(bound : ℤ) ≤ E t := by
    intro t
    have h_abs := energy_bounded G ((step G)^[t] s0) ((step G)^[t+1] s0)
    have h1 : |E t| ≤ (bound : ℤ) := by
      have : E t = energy G ((step G)^[t] s0) ((step G)^[t+1] s0) := rfl
      rw [this]
      exact h_abs
    linarith [neg_abs_le (E t)]
  
  -- Energy strictly decreases when s(t+2) ≠ s(t)
  have h_energy_dec : ∀ t, (step G)^[t+2] s0 ≠ (step G)^[t] s0 → E t - E (t+1) >= 2 := by
    intro t h_neq
    have h_diff := energy_difference G s0 t
    -- When s_{t+2} ≠ s_t, at least one vertex v has s_{t+2} v ≠ s_t v
    have : ∃ v, (step G)^[t+2] s0 v ≠ (step G)^[t] s0 v := by
      by_contra h_contra
      push_neg at h_contra
      apply h_neq
      funext v
      exact h_contra v
    obtain ⟨v, hv⟩ := this
    have h_term := energy_decrease_term G ((step G)^[t] s0) ((step G)^[t+1] s0) ((step G)^[t+2] s0) v rfl rfl hv
    -- By the difference formula: E(t+1) - E(t) = -sum_v (...)
    -- So E(t) - E(t+1) = sum_v (...)
    -- Each term for v with different labels contributes >= 2
    -- Each term is 0 when labels are same, >= 2 when different
    have h_terms_nonneg : ∀ w, - (toSpin ((step G)^[t+2] s0 w) - toSpin ((step G)^[t] s0 w)) * localField G ((step G)^[t+1] s0) w >= 0 := by
      intro w
      by_cases hw : (step G)^[t+2] s0 w = (step G)^[t] s0 w
      · simp [hw]
      · exact Int.le_of_lt (Int.add_one_le_iff.mp (energy_decrease_term G ((step G)^[t] s0) ((step G)^[t+1] s0) ((step G)^[t+2] s0) w rfl rfl hw))
    calc E t - E (t+1)
      _ = - (E (t+1) - E t) := by ring
      _ = - (- Finset.univ.sum (fun w => (toSpin ((step G)^[t+2] s0 w) - toSpin ((step G)^[t] s0 w)) * localField G ((step G)^[t+1] s0) w)) := by rw [← h_diff]
      _ = Finset.univ.sum (fun w => - (toSpin ((step G)^[t+2] s0 w) - toSpin ((step G)^[t] s0 w)) * localField G ((step G)^[t+1] s0) w) := by simp [Finset.sum_neg_distrib]; ring_nf
      _ ≥ - (toSpin ((step G)^[t+2] s0 v) - toSpin ((step G)^[t] s0 v)) * localField G ((step G)^[t+1] s0) v := by
          -- The sum is >= the v term since all other terms are >= 0
          have := Finset.single_le_sum (fun w _ => h_terms_nonneg w) (Finset.mem_univ v)
          exact this
      _ >= 2 := h_term
  
  -- If energy never stabilizes, it decreases without bound, contradicting boundedness
  by_cases h_exists : ∃ n, ∀ k, (step G)^[n+k+2] s0 = (step G)^[n+k] s0
  · obtain ⟨n, hn⟩ := h_exists
    use n
    right
    exact hn
  · -- No such n exists, so for all n, energy decreases at some point after n
    push_neg at h_exists
    -- Build a strictly decreasing subsequence by induction
    let f : ℕ → ℕ := fun i =>
      Nat.find (⟨0, h_exists i⟩ : ∃ k, (step G)^[i+k+2] s0 ≠ (step G)^[i+k] s0)
    -- At each step i, energy decreases by at least 2 at time i + f(i)
    have h_dec_at : ∀ i, E (i + f i) - E (i + f i + 1) >= 2 := by
      intro i
      exact h_energy_dec (i + f i) (Nat.find_spec (⟨0, h_exists i⟩ : ∃ k, (step G)^[i+k+2] s0 ≠ (step G)^[i+k] s0))
    -- This means E decreases without bound
    have : ∀ N : ℕ, ∃ t, E t < E 0 - 2 * N := by
      intro N
      induction N with
      | zero => use 0; omega
      | succ N ih =>
        obtain ⟨t, ht⟩ := ih
        use t + f t + 1
        have := h_dec_at t
        omega
    -- But E is bounded below by -bound, so for large enough N, we get a contradiction
    obtain ⟨t, ht⟩ := this (Int.toNat (E 0 + bound + 1))
    have h1 := h_bounded t
    have h2 := h_bounded 0
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

end MajorityImitation

end
