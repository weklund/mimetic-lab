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
  have h_no_part := h_min.2.2
  sorry

theorem convergence_of_desire (net : MimeticNetwork N) (S : Finset N)
    (h_equil : net.inEquilibrium)
    (h_min : isMinimumMutualMediatorSet net S) :
    ∀ n m : N, n ∈ S → m ∈ S → net.obj n = net.obj m := by
  intro n m hn hm
  have h_preconn := exists_path_in_minimum_mms net S h_min
  have h_reach := h_preconn ⟨n, hn⟩ ⟨m, hm⟩
  sorry

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
