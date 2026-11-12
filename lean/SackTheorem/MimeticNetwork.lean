/-
Copyright (c) 2026 Wes Eklund. All rights reserved.
Released under MIT license.

Authors: Cursor Cloud Agent

# Sack's Mimetic Theory: Geometries of Desire

This file formalizes the appendix theorems of:
Sack, G.A. (2021). Geometries of Desire: Simulating Rene Girard's Mimetic Theory.
In: Yang, Z., von Briesen, E. (eds) Proceedings of the 2020 Conference of The
Computational Social Science Society of the Americas. Springer Proceedings in
Complexity. Springer, Cham. https://doi.org/10.1007/978-3-030-83418-0_13

These are claims S1 to S4 in `claims/claims.yaml`.

## Epistemic limitations

This formalization proves theorems about Sack's graph-theoretic model of mimetic
desire under the assumptions encoded below. It does NOT prove that Girard's
anthropological theory is empirically true, nor that human desire operates
according to these mathematical structures. A verified model is a verified
design; it says nothing about whether people behave like it. The model has no
scarcity, rivalry, crisis, or scapegoat, and nothing here claims otherwise.

## Assumptions

1. Nodes are finite (`Fintype N`).
2. Each node has exactly one outgoing object link and one outgoing mediation link
   (total functions `obj, med : N → N`). Objects are nodes: persons and things are
   not distinguished (Sack, note 7).
3. A node may be its own mediator (`med n = n`, Sack's self-mediators) and may
   desire itself (`obj n = n`, narcissism). Theorems that exclude self-desire say so.
4. Equilibrium is a fixed point: `obj n = obj (med n)` for every node. It is not an
   attractor, and nothing here says any dynamics reach it. Sack's own three-agent
   run cycles and never does (notes 5 and 6).
5. A minimum mutual mediator set (MMS) is a nonempty set, closed under mediation,
   that cannot be partitioned into two nonempty disjoint closed sets (Sack's
   Definition 4). "Minimum" means indecomposable, not smallest: a whole weak
   component and its mediation cycle alone both qualify. The theorems hold under
   either reading.
6. Unproved statements are `proof_wanted`, not theorems with a placeholder proof, so
   nothing can use them. `SackTheorem/AxiomAudit.lean` pins the axioms of every proved
   theorem, and CI rejects placeholder proofs outright.
-/

import Mathlib.Data.Fintype.Basic
import Mathlib.Data.Finset.Basic
import Mathlib.Logic.Relation
import Mathlib.Combinatorics.SimpleGraph.Connectivity.Connected
import Mathlib.Combinatorics.SimpleGraph.Basic
import Batteries.Util.ProofWanted

namespace MimeticTheory

variable {N : Type*} [Fintype N] [DecidableEq N]

/-- Sack's Definition 1: every node has one object link and one mediation link. -/
structure MimeticNetwork (N : Type*) where
  obj : N → N
  med : N → N

/-- Sack's Definition 2: every node desires what its mediator desires. -/
def MimeticNetwork.inEquilibrium (net : MimeticNetwork N) : Prop :=
  ∀ n : N, net.obj n = net.obj (net.med n)

/-- Sack's Definition 3: a set closed under mediation. -/
def isMutualMediatorSet (net : MimeticNetwork N) (S : Finset N) : Prop :=
  ∀ n ∈ S, net.med n ∈ S

/-- Sack's Definition 4: a nonempty mutual mediator set that cannot be split into two
nonempty disjoint mutual mediator sets. -/
def isMinimumMutualMediatorSet (net : MimeticNetwork N) (S : Finset N) : Prop :=
  isMutualMediatorSet net S ∧
  S.Nonempty ∧
  ∀ (S₁ S₂ : Finset N), S₁.Nonempty → S₂.Nonempty →
    isMutualMediatorSet net S₁ → isMutualMediatorSet net S₂ →
    S₁ ∩ S₂ = ∅ → S₁ ∪ S₂ = S → False

/-- The undirected mediation graph on `S`: `a` and `b` are adjacent when one mediates
the other. Self-mediation (`med a = a`) is not an edge. -/
def medSymGraph (net : MimeticNetwork N) (S : Finset N) : SimpleGraph S where
  Adj a b := a ≠ b ∧ (net.med a.val = b.val ∨ net.med b.val = a.val)
  symm := ⟨fun _ _ h => ⟨h.1.symm, h.2.symm⟩⟩
  loopless := ⟨fun _ h => h.1 rfl⟩

/-- **The mediation relation** `i ↦ med i`. Its equivalence closure relates exactly the
nodes in the same weakly connected component of the mediation graph. -/
def MimeticNetwork.medRel (net : MimeticNetwork N) (i j : N) : Prop :=
  net.med i = j

omit [Fintype N] in
/-- A minimum mutual mediator set is connected in the undirected mediation graph. -/
lemma exists_path_in_minimum_mms (net : MimeticNetwork N) (S : Finset N)
    (h_min : isMinimumMutualMediatorSet net S) :
    (medSymGraph net S).Preconnected := by
  intro a b
  by_contra h_not_reach
  have h_min_mut := h_min.1
  have h_nonempty := h_min.2.1
  have h_no_part := h_min.2.2
  classical
  let C : Finset N := S.filter (fun n => ∃ (hn : n ∈ S), 
    (medSymGraph net S).Reachable ⟨n, hn⟩ a)
  have hC_nonempty : C.Nonempty := by
    use a.val
    simp only [C, Finset.mem_filter]
    exact ⟨a.property, ⟨a.property, SimpleGraph.Reachable.refl a⟩⟩
  have hC_not_all : C ≠ S := by
    intro h_eq
    have hb_in_C : b.val ∈ C := by rw [h_eq]; exact b.property
    simp only [C, Finset.mem_filter] at hb_in_C
    obtain ⟨_, hb_wit, hb_reach⟩ := hb_in_C
    exact h_not_reach (hb_reach.symm)
  have hC_mut : isMutualMediatorSet net C := by
    intro x hx
    simp only [C, Finset.mem_filter] at hx ⊢
    obtain ⟨hx_S, ⟨hx_S_wit, hx_reach⟩⟩ := hx
    have hmed_S : net.med x ∈ S := h_min_mut x hx_S
    refine ⟨hmed_S, ⟨hmed_S, ?_⟩⟩
    by_cases h_eq : net.med x = x
    · have : (⟨net.med x, hmed_S⟩ : S) = (⟨x, hx_S_wit⟩ : S) := Subtype.ext h_eq
      rw [this]
      exact hx_reach
    · have h_neq : (⟨x, hx_S_wit⟩ : S) ≠ (⟨net.med x, hmed_S⟩ : S) := by
        intro h_contra
        have : x = net.med x := congr_arg Subtype.val h_contra
        exact h_eq this.symm
      have h_adj : (medSymGraph net S).Adj ⟨x, hx_S_wit⟩ ⟨net.med x, hmed_S⟩ := by
        constructor
        · exact h_neq
        · left
          rfl
      have h_adj_reach := h_adj.symm.reachable
      exact h_adj_reach.trans hx_reach
  let C_comp : Finset N := S \ C
  have hC_comp_mut : isMutualMediatorSet net C_comp := by
    intro x hx
    simp only [C_comp, Finset.mem_sdiff, C, Finset.mem_filter] at hx ⊢
    obtain ⟨hx_S, hx_not_C⟩ := hx
    have hmed_S : net.med x ∈ S := h_min_mut x hx_S
    refine ⟨hmed_S, ?_⟩
    intro hmed_C
    apply hx_not_C
    obtain ⟨_, ⟨hmed_S_wit, hmed_reach⟩⟩ := hmed_C
    refine ⟨hx_S, ⟨hx_S, ?_⟩⟩
    by_cases h_eq : net.med x = x
    · have : (⟨x, hx_S⟩ : S) = (⟨net.med x, hmed_S_wit⟩ : S) := Subtype.ext h_eq.symm
      rw [this]
      exact hmed_reach
    · have h_neq : (⟨net.med x, hmed_S_wit⟩ : S) ≠ (⟨x, hx_S⟩ : S) := by
        intro h_contra
        have : net.med x = x := congr_arg Subtype.val h_contra
        exact h_eq this
      have h_adj : (medSymGraph net S).Adj ⟨net.med x, hmed_S_wit⟩ ⟨x, hx_S⟩ := by
        constructor
        · exact h_neq
        · right
          rfl
      have h_adj_reach := h_adj.symm.reachable
      exact h_adj_reach.trans hmed_reach
  have hC_comp_nonempty : C_comp.Nonempty := by
    use b.val
    simp only [C_comp, Finset.mem_sdiff, C, Finset.mem_filter]
    refine ⟨b.property, ?_⟩
    intro ⟨_, ⟨_, hb_reach⟩⟩
    exact h_not_reach hb_reach.symm
  have h_disj : C ∩ C_comp = ∅ := by
    simp only [C_comp, Finset.inter_sdiff_self]
  have h_union : C ∪ C_comp = S := by
    ext x
    simp only [C_comp, Finset.mem_union, Finset.mem_sdiff]
    constructor
    · intro h
      cases h with
      | inl hC =>
        simp only [C, Finset.mem_filter] at hC
        exact hC.1
      | inr hComp => exact hComp.1
    · intro hx
      by_cases hC : x ∈ C
      · left; exact hC
      · right; exact ⟨hx, hC⟩
  exact h_no_part C C_comp hC_nonempty hC_comp_nonempty hC_mut hC_comp_mut h_disj h_union

omit [Fintype N] [DecidableEq N] in
/-- In equilibrium the object of desire is constant along any path of the undirected
mediation graph. -/
lemma walk_same_obj (net : MimeticNetwork N) (S : Finset N)
    (h_equil : net.inEquilibrium) (a b : S) :
    (medSymGraph net S).Reachable a b → net.obj a.val = net.obj b.val := by
  intro h_reach
  rw [SimpleGraph.reachable_iff_reflTransGen] at h_reach
  induction h_reach with
  | refl => rfl
  | tail _ h_adj ih =>
    rw [ih]
    clear ih
    simp only [medSymGraph] at h_adj
    obtain ⟨_, h_or⟩ := h_adj
    cases h_or with
    | inl h =>
      rw [← h, h_equil]
    | inr h =>
      rw [← h, ← h_equil]


omit [Fintype N] in
/-- **Sack's Theorem 1 (Convergence of Desire).** In equilibrium, all nodes in a minimum
mutual mediator set desire the same object.

"Convergence" here is agreement at a fixed point, not convergence over time. The theorem
assumes equilibrium and says nothing about whether the dynamics reach it; Sack's
three-agent example cycles (notes 5 and 6). -/
theorem convergence_of_desire (net : MimeticNetwork N) (S : Finset N)
    (h_equil : net.inEquilibrium)
    (h_min : isMinimumMutualMediatorSet net S) :
    ∀ n m : N, n ∈ S → m ∈ S → net.obj n = net.obj m := by
  intro n m hn hm
  have h_preconn := exists_path_in_minimum_mms net S h_min
  have h_reach := h_preconn ⟨n, hn⟩ ⟨m, hm⟩
  exact walk_same_obj net S h_equil ⟨n, hn⟩ ⟨m, hm⟩ h_reach

omit [Fintype N] [DecidableEq N] in
/-- **Claim S1, as worded in `claims/claims.yaml`.** In equilibrium, any two nodes in the
same weakly connected component of the mediation graph (related by the equivalence
closure of `i ~ med i`) desire the same object.

This is Theorem 1 stated on weak components instead of minimum mutual mediator sets,
so it does not depend on which reading of Sack's Definition 4 is used. -/
theorem convergence_on_weak_component (net : MimeticNetwork N)
    (h_equil : net.inEquilibrium) {a b : N}
    (h : Relation.EqvGen net.medRel a b) :
    net.obj a = net.obj b := by
  induction h with
  | rel x y hxy =>
    have hxy' : net.med x = y := hxy
    subst hxy'
    exact h_equil x
  | refl x => rfl
  | symm x y _ ih => exact ih.symm
  | trans x y z _ _ ih₁ ih₂ => exact ih₁.trans ih₂

omit [Fintype N] in
/-- **Sack's Theorem 2 (Non-Identity of Desire).** If no node desires itself, then in
equilibrium every node of a minimum mutual mediator set desires a node outside it. -/
theorem non_identity_of_desire (net : MimeticNetwork N) (S : Finset N)
    (h_equil : net.inEquilibrium)
    (h_min : isMinimumMutualMediatorSet net S)
    (h_no_self : ∀ n : N, net.obj n ≠ n) :
    ∀ n ∈ S, net.obj n ∉ S := by
  intro n hn h_obj_in_S
  have h_conv := convergence_of_desire net S h_equil h_min
  have h_all_same := h_conv n (net.obj n) hn h_obj_in_S
  have h_obj_eq : net.obj (net.obj n) = net.obj n := by
    rw [← h_all_same]
  exact h_no_self (net.obj n) h_obj_eq

omit [Fintype N] [DecidableEq N] in
/-- **The single narcissist** (the lab's reading, not one of Sack's theorems). If the
mediation graph is weakly connected and the network is in equilibrium, exactly one node
desires itself, and every node desires that node.

This is why Theorem 3 needs at least two components once self-desire is excluded: a
connected network in equilibrium always has its one self-desiring node. In Girard's
vocabulary that node is the coquette, the model who desires herself and so draws
everyone's desire. The reading is the lab's, recorded because it explains the theorem,
not because Sack states it. -/
theorem unique_narcissist_of_weakly_connected [Nonempty N] (net : MimeticNetwork N)
    (h_equil : net.inEquilibrium)
    (h_conn : ∀ a b : N, Relation.EqvGen net.medRel a b) :
    ∃ o : N, (∀ n, net.obj n = o) ∧ ∀ n, net.obj n = n ↔ n = o := by
  obtain ⟨n₀⟩ := ‹Nonempty N›
  have hall : ∀ n, net.obj n = net.obj n₀ := fun n =>
    convergence_on_weak_component net h_equil (h_conn n n₀)
  refine ⟨net.obj n₀, hall, fun n => ⟨fun h => h.symm.trans (hall n), fun h => ?_⟩⟩
  rw [h]
  exact hall (net.obj n₀)

/-- **Sack's Theorem 3 (Existence of Equilibrium without Narcissism), "only if".** If no
node desires itself and the network is in equilibrium, the nodes can be partitioned into
at least two nonempty, disjoint mutual mediator sets.

Stated in Sack's words: the parts are mutual mediator sets, not minimum ones, and there
is no further hypothesis. `[Nonempty N]` is needed: for an empty node type the
hypotheses hold vacuously and no such partition exists.

Not yet proved. `unique_narcissist_of_weakly_connected` supplies the key step (a
connected network in equilibrium has a self-desiring node); what remains is building the
partition {weak component of some node, its complement}. -/
proof_wanted existence_equilibrium_no_narcissism_only_if [Nonempty N]
    (net : MimeticNetwork N)
    (h_equil : net.inEquilibrium)
    (h_no_self : ∀ n : N, net.obj n ≠ n) :
    ∃ partition : Finset (Finset N),
      2 ≤ partition.card ∧
      (∀ S ∈ partition, S.Nonempty ∧ isMutualMediatorSet net S) ∧
      (∀ S₁ ∈ partition, ∀ S₂ ∈ partition, S₁ ≠ S₂ → S₁ ∩ S₂ = ∅) ∧
      (Finset.univ : Finset N) = partition.biUnion id

/-- **Sack's Theorem 3, "if".** If the nodes can be partitioned into at least two
nonempty, disjoint sets closed under `med`, some object assignment is in equilibrium
with no node desiring itself.

Sack's sketch proves only the other direction. This one is a short construction: pick
two parts A and B, let every node of A desire a node of B and every other node desire a
node of A. Not yet proved. -/
proof_wanted existence_equilibrium_no_narcissism_if (med : N → N)
    (partition : Finset (Finset N)) (h_card : 2 ≤ partition.card)
    (h_parts : ∀ S ∈ partition, S.Nonempty ∧ ∀ n ∈ S, med n ∈ S)
    (h_disj : ∀ S₁ ∈ partition, ∀ S₂ ∈ partition, S₁ ≠ S₂ → S₁ ∩ S₂ = ∅)
    (h_cover : (Finset.univ : Finset N) = partition.biUnion id) :
    ∃ obj : N → N, (MimeticNetwork.mk obj med).inEquilibrium ∧ ∀ n, obj n ≠ n

/-- Theorem 3 "only if" with minimum mutual mediator sets as the parts, the form the
first draft of this file stated. It is equivalent to Sack's form (both say the mediation
graph has at least two weak components). Not yet proved: it needs the lemma that every
weak component is a minimum mutual mediator set. -/
proof_wanted existence_equilibrium_no_narcissism_only_if_minimum [Nonempty N]
    (net : MimeticNetwork N)
    (h_equil : net.inEquilibrium)
    (h_no_self : ∀ n : N, net.obj n ≠ n) :
    ∃ partition : Finset (Finset N),
      2 ≤ partition.card ∧
      (∀ S ∈ partition, isMinimumMutualMediatorSet net S) ∧
      (∀ S₁ ∈ partition, ∀ S₂ ∈ partition, S₁ ≠ S₂ → S₁ ∩ S₂ = ∅) ∧
      (Finset.univ : Finset N) = partition.biUnion id

omit [Fintype N] [DecidableEq N] in
/-- **Sack's Theorem 4 (Existence of Equilibrium with Narcissism).** When self-desire is
allowed, every mediation structure has an equilibrium.

The witness is Sack's: every node desires one node `c`, and so `c` desires itself. The
theorem is true for a trivial reason and carries little information alone. Its content
is the contrast with Theorem 3, where excluding self-desire makes existence depend on
the number of weak components. -/
theorem existence_equilibrium_with_narcissism {N : Type*} [Nonempty N]
    (med : N → N) :
    ∃ (obj : N → N), (MimeticNetwork.mk obj med).inEquilibrium := by
  obtain ⟨c⟩ := ‹Nonempty N›
  use (fun _ => c)
  intro n
  rfl

/-- **Sack's Theorem 5 (Number of Objects of Desire).** In equilibrium, the number of
distinct objects of desire is at most the number of parts in any cover of the nodes by
minimum mutual mediator sets.

Disjointness is not needed, so this is slightly stronger than a statement about
partitions. Claim S4 states the bound with weak components; that form follows once the
weak components are shown to be minimum mutual mediator sets. -/
theorem number_of_objects_bound (net : MimeticNetwork N)
    (h_equil : net.inEquilibrium)
    (partition : Finset (Finset N))
    (h_partition_mms : ∀ S ∈ partition, isMinimumMutualMediatorSet net S)
    (h_partition_cover : (Finset.univ : Finset N) = partition.biUnion id) :
    (Finset.image net.obj Finset.univ).card ≤ partition.card := by
  classical
  -- Every object is desired by the members of some part.
  have hex : ∀ o ∈ Finset.image net.obj Finset.univ,
      ∃ S ∈ partition, ∃ x ∈ S, net.obj x = o := by
    intro o ho
    obtain ⟨x, -, rfl⟩ := Finset.mem_image.mp ho
    have hx : x ∈ partition.biUnion id := by
      rw [← h_partition_cover]
      exact Finset.mem_univ x
    obtain ⟨S, hS, hxS⟩ := Finset.mem_biUnion.mp hx
    exact ⟨S, hS, x, hxS, rfl⟩
  -- Send each object to such a part. Two objects never share a part, because all
  -- members of a minimum mutual mediator set desire the same object (Theorem 1).
  let g : N → Finset N := fun o =>
    if h : ∃ S ∈ partition, ∃ x ∈ S, net.obj x = o then h.choose else ∅
  have hg : ∀ o, (∃ S ∈ partition, ∃ x ∈ S, net.obj x = o) →
      g o ∈ partition ∧ ∃ x ∈ g o, net.obj x = o := by
    intro o h
    have hgo : g o = h.choose := dite_eq_left h
    rw [hgo]
    exact h.choose_spec
  apply Finset.card_le_card_of_injOn g
  · intro o ho
    exact (hg o (hex o ho)).1
  · intro o₁ ho₁ o₂ ho₂ heq
    obtain ⟨hS₁, x₁, hx₁, h₁⟩ := hg o₁ (hex o₁ ho₁)
    obtain ⟨-, x₂, hx₂, h₂⟩ := hg o₂ (hex o₂ ho₂)
    rw [heq] at hx₁ hS₁
    rw [← h₁, ← h₂]
    exact convergence_of_desire net (g o₂) h_equil (h_partition_mms _ hS₁) x₁ x₂ hx₁ hx₂

end MimeticTheory
