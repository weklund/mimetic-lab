/-
Copyright (c) 2026 Wes Eklund. All rights reserved.
Released under MIT license.

Authors: Cursor Cloud Agent

# Sack's Mimetic Theory: Geometries of Desire

This file formalizes theorems from:
Sack, G.A. (2021). Geometries of Desire: Simulating Rene Girard's Mimetic Theory.
In: Yang, Z., von Briesen, E. (eds) Proceedings of the 2020 Conference of The
Computational Social Science Society of the Americas. Springer Proceedings in
Complexity. Springer, Cham. https://doi.org/10.1007/978-3-030-83418-0_13

## Epistemic Limitations

This formalization proves theorems about Sack's graph-theoretic model of mimetic
desire under the assumptions encoded below. It does NOT prove that Girard's
anthropological theory is empirically true, nor does it validate the claim that
human desire operates according to these mathematical structures.

## Assumptions

The proofs rely on:
1. Nodes are finite (Fintype N).
2. Each node has exactly one outgoing object link and one outgoing mediation link
   (modeled as total functions obj, med : N → N).
3. Equilibrium is defined as: for all nodes n, obj(n) = obj(med(n)).
4. A Minimum Mutual Mediator Set (MMS) is defined as a mutual mediator set
   (closed under mediation) that cannot be partitioned into two nonempty disjoint
   mutual mediator sets.
5. The proof of Theorem 1 requires that in a minimum MMS, the underlying
   undirected mediation graph is connected (proven as a lemma from minimality).
-/

import Mathlib.Data.Fintype.Basic
import Mathlib.Data.Finset.Basic
import Mathlib.Logic.Relation
import Mathlib.Combinatorics.SimpleGraph.Connectivity.Connected
import Mathlib.Combinatorics.SimpleGraph.Basic

namespace MimeticTheory

variable {N : Type*} [Fintype N] [DecidableEq N]

structure MimeticNetwork (N : Type*) where
  obj : N → N
  med : N → N

def MimeticNetwork.inEquilibrium (net : MimeticNetwork N) : Prop :=
  ∀ n : N, net.obj n = net.obj (net.med n)

def isMutualMediatorSet (net : MimeticNetwork N) (S : Finset N) : Prop :=
  ∀ n ∈ S, net.med n ∈ S

def isMinimumMutualMediatorSet (net : MimeticNetwork N) (S : Finset N) : Prop :=
  isMutualMediatorSet net S ∧
  S.Nonempty ∧
  ∀ (S₁ S₂ : Finset N), S₁.Nonempty → S₂.Nonempty →
    isMutualMediatorSet net S₁ → isMutualMediatorSet net S₂ →
    S₁ ∩ S₂ = ∅ → S₁ ∪ S₂ = S → False

def medSymGraph (net : MimeticNetwork N) (S : Finset N) : SimpleGraph S where
  Adj a b := a ≠ b ∧ (net.med a.val = b.val ∨ net.med b.val = a.val)
  symm := ⟨fun a b h => ⟨h.1.symm, h.2.symm⟩⟩
  loopless := ⟨fun a h => h.1 rfl⟩

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

theorem convergence_of_desire (net : MimeticNetwork N) (S : Finset N)
    (h_equil : net.inEquilibrium)
    (h_min : isMinimumMutualMediatorSet net S) :
    ∀ n m : N, n ∈ S → m ∈ S → net.obj n = net.obj m := by
  intro n m hn hm
  have h_preconn := exists_path_in_minimum_mms net S h_min
  have h_reach := h_preconn ⟨n, hn⟩ ⟨m, hm⟩
  exact walk_same_obj net S h_equil ⟨n, hn⟩ ⟨m, hm⟩ h_reach

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

theorem existence_equilibrium_no_narcissism_only_if (net : MimeticNetwork N)
    (h_equil : net.inEquilibrium)
    (h_no_self : ∀ n : N, net.obj n ≠ n)
    (h_partition : ∀ n : N, ∃ (S : Finset N), n ∈ S ∧ isMinimumMutualMediatorSet net S) :
    ∃ (partition : Finset (Finset N)),
      partition.card ≥ 2 ∧
      (∀ S ∈ partition, isMinimumMutualMediatorSet net S) ∧
      (∀ S₁ ∈ partition, ∀ S₂ ∈ partition, S₁ ≠ S₂ → S₁ ∩ S₂ = ∅) ∧
      (Finset.univ : Finset N) = partition.biUnion id := by
  sorry

omit [Fintype N] [DecidableEq N] in
theorem existence_equilibrium_with_narcissism {N : Type*}
    (net : MimeticNetwork N)
    (h_all_same : ∃ o : N, ∀ n : N, net.obj n = o) :
    net.inEquilibrium := by
  obtain ⟨o, ho⟩ := h_all_same
  intro n
  rw [ho n, ho (net.med n)]

theorem number_of_objects_bound (net : MimeticNetwork N)
    (h_equil : net.inEquilibrium)
    (partition : Finset (Finset N))
    (h_partition_mms : ∀ S ∈ partition, isMinimumMutualMediatorSet net S)
    (h_partition_disj : ∀ S₁ ∈ partition, ∀ S₂ ∈ partition, S₁ ≠ S₂ → S₁ ∩ S₂ = ∅)
    (h_partition_cover : (Finset.univ : Finset N) = partition.biUnion id) :
    (Finset.image net.obj Finset.univ).card ≤ partition.card := by
  sorry

end MimeticTheory
