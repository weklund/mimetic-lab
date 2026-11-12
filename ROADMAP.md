# Roadmap

Status: proposed v0, 2026-11-12. This becomes the lab's roadmap when Wes merges it with a review beginning "Lab decision:". Until then nothing here changes how any claim is scored.

## Purpose

Mimetic Lab asks one question: which of Rene Girard's claims survive when they are stated precisely enough to fail?

The method is to build the smallest computational model in which Girard's cycle (borrowed desire, rivalry over an object that cannot be shared, convergence of hostility on one member of the group, peace after the expulsion) emerges from stated micro rules instead of being assumed; to find which rules carry the weight; to derive predictions that differ from neighbouring theories; and to test at least one of them against data.

Two further goals follow from that work and are reasons to do it: a working intuition for the ideas that transfers to new situations, and, if the model earns it, a bridge to the imitation models already used in finance and conflict studies.

## What this lab can and cannot establish

A simulation shows that a set of micro rules is sufficient to produce a macro pattern. It cannot show that people follow those rules. The claim map's epistemic limit stands: nothing here is evidence that Girard's anthropology is true. Scale does not change this; a run at N = 50,000 and a run at N = 50 are both statements about the model.

What the lab can establish, claim by claim:

1. Coherence. Do the pieces fall together? That is Girard's own standard; in the Cayley interviews (2001) he says he has no philosophy and asks whether the pieces fit. A model in which the cycle emerges from the rules passes this test. A model in which a stage must be assumed fails it for that stage: Black assumes G3, Paes programs the victim.
2. Load bearing assumptions. Which rules, when removed, remove the outcome. The `depends_on` field of the claim map records this.
3. Differential predictions. Where a Girardian reading predicts something its neighbours do not: who the victim is, whether peace follows, whether recognising the mechanism dissolves it.
4. Theorems about the model, in Lean, where a universal statement is worth the cost.
5. One empirical test, with the expected result written on the claim map before the data is opened.

## Milestones

| ID | Question | Done when | Stop rule | Status on 2026-11-12 |
|---|---|---|---|---|
| M1-black-phase-boundary | Does Black's code produce Black's tables? | C-T2 and C-T10 verdicts issued under an accepted contract, traces archived. | After the verdicts, no judge or contract work unless a bug changes a verdict. | C-T2 traces archived (PR #28); v0.2.1 Lab decision pending. C-T10 judges merged (PR #29); traces not archived. |
| M2-sack-lean | Do Sack's appendix theorems hold? | Done: S1 to S3 proved, S4 stated. | Stop now. S4's lemma and the minimum set form of Theorem 3 are optional. | Done. |
| M3-literature-map | What has already been formalized or tested under other names? | Every claim O8 to O21 opened by a person, moved off `locator-incomplete`, with its delta to a G claim confirmed or corrected. | No wholesale reproductions. Dock one figure only when M4 needs it. | Drafted from Claude's memory (claim map v0.2.5). None opened. |
| M4-minimal-model | In the smallest model with all four stages, which rules let the cycle emerge? | (1) `eval/models/minimal-model-v0.md` implemented with every ablation switch; (2) experiment E0 settles L1; (3) experiment E2 settles L2; (4) one of T1, T2 proved in Lean; (5) docked to Black on one figure (E1). | Fill the ablation table, then stop. No mechanism is added unless a claim on the map needs it. | Spec drafted. L1 and L2 stated. T1 and T2 checked exhaustively to n = 7, not proved. |
| M5-assumption-audit | For every model on the map, which Girardian claims are inputs and which are outputs? | Every `model` and `theorem` claim (B, S, O, L) has `depends_on` with origin and role. | Table filled. | B claims done (PR #27). Sack, Paes, O8 to O21, L1, L2 open. |
| M6-empirical-test | Does one differential prediction hold in data? | One prediction (P1, the victim question, preferred) tested on one dataset, with the expected result for each rival theory recorded on the map before the data is opened, and the result recorded whatever it is. | One test. A second needs a Lab decision. | Not started. Candidate data in the spec. |
| M7-write-up | What survived? | A synthesis in the repo and in the vault stating, claim by claim, what was proved, reproduced, refuted, or left open. | The lab pauses after M7. | Not started. |

Order: M1 and M3 now, in parallel. M4 starts when M3 has opened the threshold and conformist sources (O8, O11). M5 runs alongside M4. M6 after E2. M7 last.

## Process

1. Every PR names in its first line the milestone and the claim it serves. A PR that serves none is closed, not reviewed.
2. One reviewer per PR, named in the PR. CodeRabbit may run; it is not that reviewer. Two review rounds at most, then the Lab merges, closes, or reassigns with a new scope.
3. A Lab decision says what happens next, not only "hold".
4. Agents work from issues. An agent answers a review by amending the PR under review, not by opening another PR.
5. Judge and contract code is frozen when M1 closes, except for a bug that changes a verdict.
6. A claim drafted from an assistant's memory is `locator-incomplete` until a person opens the source. Its statement may plan work; it is not evidence.
7. Claim map rule 2 stands: a passing proof or reproduction upgrades the B, S, O, or L claim it is about, never a G claim.

## Methodology references

These describe the method and are not claims about mimesis, so they are not on the claim map. All are from Claude's memory on 2026-11-12; verify before citing.

1. Epstein, Generative Social Science (Princeton University Press, 2006). Generative sufficiency: a mechanism that grows the pattern explains it as sufficient, not as necessary or true.
2. Grimm and others, "Pattern-oriented modeling of agent-based complex systems: lessons from ecology," Science 310 (2005). A model should reproduce several patterns at several scales at once.
3. Axtell, Axelrod, Epstein, and Cohen, "Aligning simulation models: a case study and results," Computational and Mathematical Organization Theory 1 (1996). Docking, which is what M1 is.
4. Grimm and others, the ODD protocol for describing agent based models (Ecological Modelling, 2006; updated 2010 and 2020). The spec in `eval/models` follows its headings.

## Change log

- 2026-11-12 v0: proposed, with claim map v0.2.5 (O8 to O21, L1, L2, O6 delta corrected) and the minimal model spec v0.
