module

public import Mathlib.Data.Fintype.Basic
public import Mathlib.Data.Finset.Basic
public import Mathlib.Combinatorics.SimpleGraph.Basic
public import Mathlib.Combinatorics.SimpleGraph.Finite
public import Mathlib.Data.Nat.Basic
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

/-- Main theorem: Period at most 2 (Goles-Olivos style).
    From any initial state, the trajectory eventually reaches a fixed point
    or alternates between exactly 2 states.
    
    The proof strategy is via an energy function that strictly decreases
    until we reach a periodic orbit of length at most 2. This is the standard
    Goles-Olivos argument using a Lyapunov function.
    
    Leaving this unproved does not upgrade O5, which remains reported-by-source. -/
proof_wanted period_at_most_2 (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] [DecidableEq V]
    (s0 : State V) :
    ∃ n : ℕ, isFixedPoint G ((step G)^[n] s0) ∨
             (∀ k : ℕ, (step G)^[n+k+2] s0 = (step G)^[n+k] s0)

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
