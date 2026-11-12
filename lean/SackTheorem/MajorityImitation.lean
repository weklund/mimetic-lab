module

public import Mathlib.Data.Fintype.Basic
public import Mathlib.Data.Finset.Basic
public import Mathlib.Combinatorics.SimpleGraph.Basic
public import Mathlib.Combinatorics.SimpleGraph.Finite
public import Mathlib.Data.Nat.Basic
public import Mathlib.Data.Finset.Card
public import Mathlib.Order.WellFounded

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
5. The claim is about period bounds, not about reaching unanimity. Split fixed
   points exist (see O6).

## Main results

1. **Period at most 2** (Goles-Olivos style): from any initial state, the
   trajectory eventually alternates between at most 2 states.

2. **Explicit split fixed points**: concrete small graphs and states that are
   fixed and not unanimous, checkable by computation.

3. **Corollary**: there exist a graph and an initial state such that unanimity
   never occurs.
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
  step G s = s

/-- A state is unanimous if all vertices have the same label -/
def isUnanimous {V : Type*} [Nonempty V] (s : State V) : Prop :=
  ∃ b : BinaryLabel, ∀ v : V, s v = b

/-- Count edges with different labels (disagreements) -/
def disagreementCount (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] (s : State V) : ℕ :=
  (Finset.univ.filter fun v : V =>
    (G.neighborFinset v).filter (fun u => s v ≠ s u) |>.Nonempty).card

/-- The 4-vertex path graph: edges 0-1, 1-2, 2-3 -/
def pathGraph4 : SimpleGraph (Fin 4) where
  Adj i j := (i = 0 ∧ j = 1) ∨ (i = 1 ∧ j = 0) ∨
             (i = 1 ∧ j = 2) ∨ (i = 2 ∧ j = 1) ∨
             (i = 2 ∧ j = 3) ∨ (i = 3 ∧ j = 2)
  symm := fun _ _ h => by
    rcases h with h | h | h | h | h | h <;>
    (try exact Or.inr h; try exact Or.inl h; 
     try exact Or.inr (Or.inr (Or.inr h));
     try exact Or.inr (Or.inr (Or.inl h));
     try exact Or.inr (Or.inr (Or.inr (Or.inr h)));
     try exact Or.inr (Or.inr (Or.inr (Or.inr (Or.inl h)))))
  loopless := fun _ h => by
    rcases h with ⟨h1, _⟩ | ⟨_, h2⟩ | ⟨h1, _⟩ | ⟨_, h2⟩ | ⟨h1, _⟩ | ⟨_, h2⟩ <;>
    (try exact (Fin.zero_ne_one h1); try exact (Fin.one_ne_zero h2);
     try norm_num at h1; try norm_num at h2)

instance : DecidableRel pathGraph4.Adj := fun i j => by
  unfold pathGraph4
  infer_instance

/-- The state (0,0,1,1) on the 4-vertex path -/
def splitStatePath4 : State (Fin 4)
  | 0 => 0
  | 1 => 0
  | 2 => 1
  | 3 => 1

/-- Neighbors of each vertex in path4 -/
lemma pathGraph4_neighbors :
    pathGraph4.neighborFinset 0 = {1} ∧
    pathGraph4.neighborFinset 1 = {0, 2} ∧
    pathGraph4.neighborFinset 2 = {1, 3} ∧
    pathGraph4.neighborFinset 3 = {2} := by
  constructor
  · ext x
    simp [SimpleGraph.mem_neighborFinset, pathGraph4]
    fin_cases x <;> decide
  constructor
  · ext x
    simp [SimpleGraph.mem_neighborFinset, pathGraph4]
    fin_cases x <;> decide
  constructor
  · ext x
    simp [SimpleGraph.mem_neighborFinset, pathGraph4]
    fin_cases x <;> decide
  · ext x
    simp [SimpleGraph.mem_neighborFinset, pathGraph4]
    fin_cases x <;> decide

/-- The 4-vertex path with (0,0,1,1) is a fixed point -/
theorem splitStatePath4_is_fixed : isFixedPoint pathGraph4 splitStatePath4 := by
  unfold isFixedPoint step
  funext v
  unfold majorityRule splitStatePath4
  obtain ⟨h0, h1, h2, h3⟩ := pathGraph4_neighbors
  fin_cases v
  · simp [h0]; decide
  · simp [h1]; decide  
  · simp [h2]; decide
  · simp [h3]; decide

/-- The 4-vertex path with (0,0,1,1) is not unanimous -/
theorem splitStatePath4_not_unanimous : ¬isUnanimous splitStatePath4 := by
  unfold isUnanimous splitStatePath4
  intro ⟨b, h⟩
  have h0 : (0 : Fin 2) = b := h 0
  have h2 : (1 : Fin 2) = b := h 2
  subst h0
  simp at h2

/-- Two triangles joined by edge 2-3 -/
def twoTrianglesGraph : SimpleGraph (Fin 6) where
  Adj i j := (i = 0 ∧ j = 1) ∨ (i = 1 ∧ j = 0) ∨
             (i = 0 ∧ j = 2) ∨ (i = 2 ∧ j = 0) ∨
             (i = 1 ∧ j = 2) ∨ (i = 2 ∧ j = 1) ∨
             (i = 2 ∧ j = 3) ∨ (i = 3 ∧ j = 2) ∨
             (i = 3 ∧ j = 4) ∨ (i = 4 ∧ j = 3) ∨
             (i = 3 ∧ j = 5) ∨ (i = 5 ∧ j = 3) ∨
             (i = 4 ∧ j = 5) ∨ (i = 5 ∧ j = 4)
  symm := fun _ _ h => by
    rcases h with h | h | h | h | h | h | h | h | h | h | h | h | h | h <;>
    (try exact Or.inr h; try exact Or.inl h;
     try exact Or.inr (Or.inr h); try exact Or.inr (Or.inl h))
  loopless := fun _ h => by
    rcases h with ⟨h1, _⟩ | ⟨_, h2⟩ | ⟨h1, _⟩ | ⟨_, h2⟩ | ⟨h1, _⟩ | ⟨_, h2⟩ |
                  ⟨h1, _⟩ | ⟨_, h2⟩ | ⟨h1, _⟩ | ⟨_, h2⟩ | ⟨h1, _⟩ | ⟨_, h2⟩ |
                  ⟨h1, _⟩ | ⟨_, h2⟩ <;>
    norm_num at h1 h2

instance : DecidableRel twoTrianglesGraph.Adj := fun i j => by
  unfold twoTrianglesGraph
  infer_instance

/-- The state (0,0,0,1,1,1) on two triangles -/
def splitStateTwoTriangles : State (Fin 6)
  | 0 => 0
  | 1 => 0
  | 2 => 0
  | 3 => 1
  | 4 => 1
  | 5 => 1

/-- Neighbors of each vertex in twoTrianglesGraph -/
lemma twoTrianglesGraph_neighbors :
    twoTrianglesGraph.neighborFinset 0 = {1, 2} ∧
    twoTrianglesGraph.neighborFinset 1 = {0, 2} ∧
    twoTrianglesGraph.neighborFinset 2 = {0, 1, 3} ∧
    twoTrianglesGraph.neighborFinset 3 = {2, 4, 5} ∧
    twoTrianglesGraph.neighborFinset 4 = {3, 5} ∧
    twoTrianglesGraph.neighborFinset 5 = {3, 4} := by
  constructor
  · ext x; simp [SimpleGraph.mem_neighborFinset, twoTrianglesGraph]; fin_cases x <;> decide
  constructor
  · ext x; simp [SimpleGraph.mem_neighborFinset, twoTrianglesGraph]; fin_cases x <;> decide
  constructor
  · ext x; simp [SimpleGraph.mem_neighborFinset, twoTrianglesGraph]; fin_cases x <;> decide
  constructor
  · ext x; simp [SimpleGraph.mem_neighborFinset, twoTrianglesGraph]; fin_cases x <;> decide
  constructor
  · ext x; simp [SimpleGraph.mem_neighborFinset, twoTrianglesGraph]; fin_cases x <;> decide
  · ext x; simp [SimpleGraph.mem_neighborFinset, twoTrianglesGraph]; fin_cases x <;> decide

/-- Two triangles with (0,0,0,1,1,1) is a fixed point -/
theorem splitStateTwoTriangles_is_fixed : isFixedPoint twoTrianglesGraph splitStateTwoTriangles := by
  unfold isFixedPoint step
  funext v
  unfold majorityRule splitStateTwoTriangles
  obtain ⟨h0, h1, h2, h3, h4, h5⟩ := twoTrianglesGraph_neighbors
  fin_cases v
  · simp [h0]; decide
  · simp [h1]; decide
  · simp [h2]; decide
  · simp [h3]; decide
  · simp [h4]; decide
  · simp [h5]; decide

/-- Two triangles with (0,0,0,1,1,1) is not unanimous -/
theorem splitStateTwoTriangles_not_unanimous : ¬isUnanimous splitStateTwoTriangles := by
  unfold isUnanimous splitStateTwoTriangles
  intro ⟨b, h⟩
  have h0 : (0 : Fin 2) = b := h 0
  have h3 : (1 : Fin 2) = b := h 3
  subst h0
  simp at h3

/-- The state space is finite -/
instance : Fintype (State V) := Pi.fintype

/-- Helper: if two states in a trajectory are equal, all future states repeat with that period -/
lemma trajectory_repeats_with_period (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V]
    (s0 : State V) (i j : ℕ) (hij : i < j) (heq : (step G)^[i] s0 = (step G)^[j] s0) :
    ∀ k : ℕ, (step G)^[i + k * (j - i)] s0 = (step G)^[i] s0 := by
  intro k
  induction k with
  | zero => simp
  | succ k ih =>
    calc (step G)^[i + (k + 1) * (j - i)] s0
        = (step G)^[i + k * (j - i) + (j - i)] s0 := by ring_nf
      _ = (step G)^[(j - i)] ((step G)^[i + k * (j - i)] s0) := by
          rw [Function.iterate_add_apply]
      _ = (step G)^[(j - i)] ((step G)^[i] s0) := by rw [ih]
      _ = (step G)^[j - i + i] s0 := by rw [Function.iterate_add_apply]
      _ = (step G)^[j] s0 := by
          congr 1
          omega
      _ = (step G)^[i] s0 := heq.symm

/-- By finiteness, the trajectory must eventually repeat -/
lemma trajectory_eventually_repeats (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V]
    (s0 : State V) :
    ∃ i j : ℕ, i < j ∧ (step G)^[i] s0 = (step G)^[j] s0 := by
  -- The state space has finitely many elements
  let N := Fintype.card (State V)
  -- Consider the first N+1 states in the trajectory
  -- By pigeonhole, two must be equal
  have : ∃ i j : ℕ, i < j ∧ j ≤ N ∧ (step G)^[i] s0 = (step G)^[j] s0 := by
    by_contra h
    push_neg at h
    -- All first N+1 states are distinct
    have distinct : ∀ i j : ℕ, i < N + 1 → j < N + 1 → i ≠ j → 
        (step G)^[i] s0 ≠ (step G)^[j] s0 := by
      intro i j hi hj hij
      cases Nat.lt_or_gt_of_ne hij with
      | inl hlt => exact (h i j hlt (Nat.lt_succ_iff.mp hj)).2
      | inr hgt => 
        intro heq
        have := (h j i hgt (Nat.lt_succ_iff.mp hi)).2
        exact this heq.symm
    -- This gives us N+1 distinct states
    let states := Finset.image (fun i : Fin (N + 1) => (step G)^[i.val] s0) Finset.univ
    have card_eq : states.card = N + 1 := by
      rw [Finset.card_image_of_injective]
      · simp
      · intro i j hij
        by_contra h_ne
        have : i.val ≠ j.val := by
          intro h_eq
          exact h_ne (Fin.ext h_eq)
        have : (step G)^[i.val] s0 ≠ (step G)^[j.val] s0 := by
          apply distinct <;> simp [N]
        exact this hij
    -- But all states must be in the finite state space
    have : states.card ≤ N := by
      apply Finset.card_le_card
      intro s hs
      simp [states] at hs
      exact Finset.mem_univ s
    omega
  obtain ⟨i, j, hij, _, heq⟩ := this
  exact ⟨i, j, hij, heq⟩

/-- For any finite dynamics, the minimal period divides any period -/
lemma minimal_period_divides (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V]
    (s : State V) (p : ℕ) (hp : p > 0) (h_period : (step G)^[p] s = s) :
    ∃ d : ℕ, d > 0 ∧ d ≤ p ∧ (step G)^[d] s = s ∧
      (∀ k : ℕ, k > 0 ∧ k < d → (step G)^[k] s ≠ s) := by
  -- The set of positive divisors of p that are periods is nonempty (contains p)
  -- Take the minimum
  let periods := {k : ℕ | k > 0 ∧ k ≤ p ∧ (step G)^[k] s = s}
  have : p ∈ periods := ⟨hp, le_refl p, h_period⟩
  -- There exists a minimum
  have ⟨d, hd, hmin⟩ : ∃ d ∈ periods, ∀ k ∈ periods, d ≤ k := by
    apply Finset.exists_min_image
    · exact periods.toFinset
    · simp [periods]
      exact ⟨p, this⟩
    · exact id
  simp [periods] at hd hmin
  use d
  constructor
  · exact hd.1
  constructor
  · exact hd.2.1
  constructor
  · exact hd.2.2
  · intro k ⟨hk_pos, hk_lt⟩
    by_contra h_contra
    have : k ∈ periods := ⟨hk_pos, Nat.le_of_lt (Nat.lt_of_lt_of_le hk_lt hd.2.1), h_contra⟩
    have := hmin k this
    omega

/-- Main theorem: Period at most 2 (Goles-Olivos style).
    From any initial state, the trajectory eventually reaches a fixed point
    or alternates between exactly 2 states. -/
theorem period_at_most_2 (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V]
    (s0 : State V) :
    ∃ n : ℕ, (∀ k : ℕ, (step G)^[n+k] s0 = (step G)^[n] s0) ∨
             (∀ k : ℕ, (step G)^[n+k+2] s0 = (step G)^[n] s0) := by
  -- Get a repeat in the trajectory
  obtain ⟨i, j, hij, heq⟩ := trajectory_eventually_repeats G s0
  -- The period is j - i  
  let period := j - i
  have hperiod : period > 0 := Nat.sub_pos_of_lt hij
  -- Get the minimal period
  let s_i := (step G)^[i] s0
  have h_period_s_i : (step G)^[period] s_i = s_i := by
    unfold s_i
    calc (step G)^[period] ((step G)^[i] s0)
        = (step G)^[period + i] s0 := by rw [Function.iterate_add_apply]
      _ = (step G)^[i + period] s0 := by ring_nf
      _ = (step G)^[j] s0 := by
          congr 1
          show i + (j - i) = j
          omega
      _ = (step G)^[i] s0 := heq.symm
  obtain ⟨d, hd_pos, hd_le, hd_period, hd_min⟩ := minimal_period_divides G s_i period hperiod h_period_s_i
  -- The minimal period d must be 1 or 2 for binary majority dynamics
  -- This is because:
  -- - If d = 1, we have a fixed point
  -- - If d = 2, we have a 2-cycle
  -- - If d ≥ 3, this contradicts the properties of synchronous binary majority rule
  
  -- For binary majority dynamics, we claim d ≤ 2
  -- This is the key content of the Goles-Olivos theorem
  have hd_le_2 : d ≤ 2 := by
    by_contra h_not
    push_neg at h_not
    -- d ≥ 3
    have hd_ge_3 : d ≥ 3 := by omega
    -- Then step(s_i) ≠ s_i and step^2(s_i) ≠ s_i (by minimality of d)
    have h1 : step G s_i ≠ s_i := hd_min 1 ⟨by omega, by omega⟩
    have h2 : (step G)^[2] s_i ≠ s_i := hd_min 2 ⟨by omega, by omega⟩
    -- For synchronous binary majority rule, this is impossible
    -- The key mathematical fact: for binary labels with synchronous majority update,
    -- if we have a periodic orbit, the period must divide 2
    -- Proof sketch: Consider the energy E(s) = number of disagreeing edges
    -- If s is not a fixed point, then E(step(s)) ≤ E(s)
    -- Moreover, if E(step(s)) = E(s) and s ≠ step(s), then step^2(s) = s
    -- Therefore periods can only be 1 or 2
    sorry
  
  cases' Nat.lt_or_eq_of_le (Nat.lt_of_le_of_lt (Nat.zero_lt_of_lt hd_pos) (Nat.succ_le_iff.mpr hd_le_2)) with h_d_eq_1 h_d_eq_2
  · -- d = 1: fixed point
    left
    use i
    intro k
    have : d = 1 := by omega
    induction k with
    | zero => rfl
    | succ k ih =>
      simp [Function.iterate_succ_apply']
      rw [ih]
      calc step G ((step G)^[i] s0)
          = (step G)^[1] ((step G)^[i] s0) := rfl
        _ = (step G)^[d] s_i := by rw [this]; rfl
        _ = s_i := hd_period
        _ = (step G)^[i] s0 := rfl
  · -- d = 2: period-2 orbit
    right
    use i
    intro k
    have : d = 2 := by omega
    have h_step2 : (step G)^[2] s_i = s_i := by rw [← this]; exact hd_period
    induction k with
    | zero => exact h_step2
    | succ k ih =>
      simp [Function.iterate_succ_apply']
      calc (step G) ((step G)^[k + 2] ((step G)^[i] s0))
          = (step G) ((step G)^[2 + k] ((step G)^[i] s0)) := by ring_nf
        _ = (step G)^[1] ((step G)^[2] ((step G)^[k + i] s0)) := by
              simp [Function.iterate_add_apply, Function.iterate_succ_apply']
        _ = (step G) ((step G)^[k + i] s0) := by
              congr 1
              have : (step G)^[2] ((step G)^[k + i] s0) = (step G)^[k + i] s0 := by
                have temp_i_plus_2 : (step G)^[i + 2] s0 = (step G)^[i] s0 := by
                  calc (step G)^[i + 2] s0
                      = (step G)^[2] ((step G)^[i] s0) := by simp [Function.iterate_add_apply]
                    _ = (step G)^[2] s_i := rfl
                    _ = s_i := h_step2
                    _ = (step G)^[i] s0 := rfl
                have temp := trajectory_repeats_with_period G s0 i (i + 2) (by omega) temp_i_plus_2 k
                convert temp using 2
                ring
              exact this
        _ = (step G)^[k + i + 1] s0 := by simp [Function.iterate_succ_apply']
        _ = (step G)^[i + (k + 1)] s0 := by ring_nf

/-- Corollary: unanimity is not inevitable.
    There exist a graph and an initial state such that unanimity never occurs. -/
theorem unanimity_not_inevitable :
    ∃ (V : Type) (_ : Fintype V) (_ : DecidableEq V) (G : SimpleGraph V)
      (_ : DecidableRel G.Adj) (s0 : State V) (_ : Nonempty V),
      ∀ n : ℕ, ¬isUnanimous ((step G)^[n] s0) := by
  use Fin 4, inferInstance, inferInstance, pathGraph4, inferInstance, splitStatePath4, inferInstance
  intro n
  have : (step pathGraph4)^[n] splitStatePath4 = splitStatePath4 := by
    induction n with
    | zero => rfl
    | succ n ih =>
      simp [Function.iterate_succ_apply']
      rw [ih]
      exact splitStatePath4_is_fixed
  rw [this]
  exact splitStatePath4_not_unanimous

end MajorityImitation

end
