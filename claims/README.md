# Claim map: scheme and rules

Status: draft v0.2.1, 2026-11-11. Working file for the lab. Edit claims in `claims.yaml`; this file only defines the scheme.

## Epistemic limit

Formal methods can prove that a model behaves as claimed. Simulation can test whether stated dynamics appear under stated assumptions. Neither can show that Girard's anthropology is true or that it is the best available theory. Every claim here is about a precisely stated proposition, model, or text, never about the theory as a whole.

## Why this scheme

When this scheme was written (vault checked 2026-11-11, commit 62e9777), the Second Brain vault held no existing claim map, no notes on Girard, Sack, or Black, and no formalization scheme. This is therefore the smallest scheme that keeps claims falsifiable, not an adaptation of an existing one.

## Fields (one record per claim)

| Field | Meaning |
|---|---|
| `id` | Stable ID. Prefix: `G` Girard text, `B` Black model, `S` Sack model, `O` other literature, `W` Wes. Never reuse an ID. |
| `priority` | `P0` needed by a first milestone, `P1` supports a milestone, `P2` later. |
| `milestone` | `M1-black-phase-boundary`, `M2-sack-lean`, or `later`. |
| `kind` | `textual` (claim about what a text says), `empirical` (about the world), `model` (about a stated model), `theorem` (provable in a stated formal system). |
| `statement` | Wording precise enough to pass or fail. |
| `source` | Work, edition, page or section. Mark `locator: incomplete` when not checked against the primary text. |
| `assumptions` | What the claim needs to hold. |
| `counterexample` | What observation, run, or proof would make it fail. |
| `formalization_delta` | For each existing model: what it drops, adds, or weakens relative to the source claim. |
| `status` | `stated`, `locator-incomplete`, `reported-by-source`, `reproduced`, `failed-reproduction`, `proved-in-lean`, `refuted`. |

## Rules

1. A `model` or `theorem` claim must name the model it is about and link the `G` or `W` claim it stands in for, with the delta written out.
2. A passing reproduction or proof upgrades only that `B` or `S` claim. It never upgrades a `G` claim.
3. Quotes come only from sources someone on the lab actually opened; secondhand page numbers are marked `via`. Private journal wording is not quoted on the public map until Wes says so.
4. Change log entries go at the bottom of `claims.yaml`.
