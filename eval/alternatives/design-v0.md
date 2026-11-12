# Thinner alternatives to Black's AC package (design v0)

Status: design only. Labeled extension, not an official ensemble.
Author: Mimetic Falsifier, 2026-11-12.
Official comparison still waits on a clean C-T2b (Table 2b, M1/B1).

This note specifies thinner, non-Girardian rules to try against the published Black Table 2b setup. It covers alternatives 1-3 only (plain herding, random targeting, linear herding), which live under `eval/alternatives/`. It does not run them on official table paths, and it does not change `claims/claims.yaml`, `eval/contract.md`, judges, or official traces. If a result belongs on B1 assumptions, Mimetic Theory updates the claim map.

Lab recorded this pre-registration on 2026-11-12, before any alternative run.

Second Brain was queried before this design (vault synced 2026-11-12). It has Girard concept pages and no notes that specify herding or random-targeting alternatives to the scapegoat mechanism. This design is therefore taken from the published Black setup in the opened source and the claim map, not from a vault scheme.

## Limits

- A matching outcome is an alternative generator of the same model output. It is not a disproof of Girard, not a status change on G4, and not a status change on B1. B1 is a claim about Black's AC variant, and only a rerun of that variant can pass or fail it.
- If a thinner rule produces the same phenomena under the pre-registered criteria below, the Girardian package is not uniquely supported as the generator of that output. The affected reading is any use of B1 (or B2) as evidence that objects, rivalry, the G3 increment, or hostility-based attention are necessary for the phase-boundary pattern. G4 itself is not upgraded or refuted.
- Official comparison against a scored official Black reproduction waits until C-T2b is clean. Prep and, later, labeled-extension runs are not that comparison.
- Do not write to `eval/traces/` official paths. Outputs, if any, go under `eval/alternatives/`.

## Opened source for Table 2b

Figures below are from the opened GitHub draft, not a new Lab rule. Opened: Black, draft v18 (Feb 2026), section 3.2, Table 2b, in `paper/paper_draft_18_github.md` at github.com/maxwell-black/mimetic-desire-simulation, HEAD `89e7bbb57db62e3c830a8ca672a0805080df3970` (2026-04-01). The published Contagion 33 (2026) version was not opened.

Table 2b as printed (caption: "Convergence rate by gamma and community size. 20 seeds per condition, 800 steps, no expulsion"):

| N   | gamma <= 1.01 | gamma = 1.02 | gamma = 1.03 | gamma >= 1.04 |
|-----|---------------|--------------|--------------|---------------|
| 50  | 0%            | 10%          | 90%          | 100%          |
| 100 | 0%            | 0%           | 100%         | 100%          |
| 200 | 0%            | 0%           | 100%         | 100%          |

The same section's prose, checked against those cells: at N = 50, 10% convergence at 1.02, 90% at 1.03, 100% at 1.04; at N >= 100, 0% at 1.02 and 100% at 1.03. Median t95 at gamma = 1.05 is 88, 98, and 102 for N = 50, 100, 200.

## Shared protocol (published Table 2b)

Taken from that opened table and its surrounding protocol, and from contract C-T2b, which records the same setup.

- Watts-Strogatz graph, rewire 0.15.
- N in {50, 100, 200}.
- k = max(6, min(int(N*0.12), 20)), forced even: k = 6, 12, 20.
- Seeds: `42 + r * 1000` for r = 0..19 (20 runs).
- Horizon: 800 steps. No expulsion.
- Gamma grid: [1.01, 1.02, 1.03, 1.04, 1.05].
- Convergence: contract D2. t95 is the first t such that agreement[t+k] >= 0.95 for all k in 0..9; a trial converged iff t95 is not null. Agreement is D1, including eligibility `>= 1e-8` and the official tie rule, applied to whatever target field the alternative uses.
- Also record D4 summaries (peak modal, final modal, their sds, peak gini when the alternative has a received-aggression vector; otherwise gini is N/A and is reported as such).
- Median t95 at gamma 1.05 is recorded and compared under rule A to the opened-source values 88, 98, 102 for N = 50, 100, 200. This is a secondary check, not the uniqueness test.

The mixing probability, where an alternative uses one, is alpha = 0.15, the published Black value, so a failure to converge is not explained by a different step size. Initialization: each agent draws a uniform random living non-self target.

## Pre-registered scoring

Two bars, both declared before any alternative run. Lab recorded this pre-registration on 2026-11-12.

**Qualitative (the uniqueness bar).** This bar is the published Table 2b pattern, cited from the opened table above, not a new rule. A thinner rule produces "the same phenomena" if, on this protocol, it shows that same pattern:

- 0% convergence at gamma <= 1.01 and 100% at gamma >= 1.04, at each of N = 50, 100, 200;
- the transition in [1.02, 1.03];
- at N = 50, a fuzzy interval (neither 0% nor 100% at both 1.02 and 1.03); at N = 100 and N = 200, a step (0% at 1.02, 100% at 1.03).

**Strict.** Exact published Table 2b rates: N=50 has 0%, 10%, 90%, 100% on those four columns; N=100 and N=200 have 0%, 0%, 100%, 100%. With 20 seeds, 10% is 2/20 and 90% is 18/20. A strict match is a surprise to report. It is not required for the uniqueness conclusion.

A fail on the qualitative bar means this alternative does not generate the same phase-boundary output. That is a result, not a save of the Girardian package: other thinner rules can still be tried.

Random targeting has no gamma. It is scored on the same grid as a flat control: the qualitative bar is not expected to hold, and a match would mean the criteria are not discriminating.

P-drop and P-gen are out of scope for this wave. Table 2b has expulsion disabled, so P-drop is N/A. Those properties can be designed after official Table 10 work is in a state Lab is willing to compare against.

## Alternative 1: plain herding (primary)

No objects, no rivalry, no hostility matrix, no G3 increment, no aggression decay, no throughput conservation.

Each agent i holds a target T_i in the living set, self-targeting forbidden. Let n_i(j) be the number of neighbors of i (in the same Watts-Strogatz graph) whose current target is j. At each step, independently, each agent i, with probability alpha, draws a new target with

    P_i(j) proportional to n_i(j)^gamma    for living j != i,

and keeps T_i otherwise. If every neighbor weight is zero, the draw is uniform over living non-self agents.

Gamma here is convexity of count-based herding, not hostility salience. It is the same numeric grid so the question "does a phase boundary appear at the same place" is well posed, with that formalization delta written out.

**Neighbor-restricted is the primary rule.** A global-count variant (n(j) over the whole population) is a pre-registered sensitivity, not the primary. If only the global variant matches, say so; do not treat it as a pass of the primary.

This is the main uniqueness probe: if neighbor herding with a convex count exponent produces the qualitative Table 2b pattern, the Girardian package is not uniquely supported as the generator of that pattern.

## Alternative 2: random targeting (negative control)

Same graph, seeds, horizon, and alpha. At each step, with probability alpha, agent i draws a uniform living non-self target (primary: global uniform; neighbor-uniform is a sensitivity). There is no gamma in the rule. The same five-gamma grid is still run so a flat (gamma-independent) outcome is visible.

Expected result: the qualitative bar fails; few or no D2 convergences at these N and 800 steps. If this control matches, the pass/fail criteria are too weak and cannot support a uniqueness claim in either direction.

## Alternative 3: linear herding

Alternative 1 with gamma fixed at 1, run once per N (not on the five-gamma grid as a boundary test). This asks whether "linear transmission never converges" (B2) is a fact about Black's operator family or about herding more generally.

- If linear herding also never meets D2 here, B2-style non-convergence is not unique to Black's linear map, and is consistent with needing convexity in a thinner rule as well.
- If linear herding does meet D2, then B2 is specific to Black's operator and cannot be read as a general fact about linear transmission.

This alternative does not use the qualitative Table 2b bar, which is a statement about a gamma sweep.

## G3 ablation (not in this PR)

A G3 ablation of Black's published AC operator (the 0.2 shared-desire increment set to 0) is a labeled Black ablation for issue 16. That work is Simulation's. It is not part of this design or this PR. Falsifier may point to it; Falsifier does not run it or include it under `eval/alternatives/`.

## Harness and coordination

- Same seeds policy and D2/D4 definitions as the contract, so a later official comparison can use the same judge ideas without scoring official paths.
- Manifest each run as a labeled extension: `ensemble` is one of `alt-herding-v0`, `alt-herding-global-v0`, `alt-random-v0`, `alt-linear-herding-v0`. `contract_version` must not be used to look like an official C-T2b export. Record the alternative id and the formalization delta.
- Scripts, when written, live under `eval/alternatives/` and must refuse to write to official trace directories.
- This design does not request Simulation to run the official reproduction, and it does not itself run on official table paths.
- Any commit goes up as a pull request. Do not merge. Send the PR to Mimetic Reviewer for a fidelity check before treating the wording as final.

## Claims affected (if the qualitative bar is met)

| Alternative | If it meets the qualitative bar | If it fails it |
|---|---|---|
| 1. Plain herding | Girardian package not uniquely supported for the Table 2b phase-boundary output. Affected reading: B1 as evidence that objects, rivalry, G3, or hostility-based attention are necessary for that pattern. B1 and G4 statuses unchanged. | This thinner rule is not a sufficient generator. Other rules remain open. |
| 2. Random targeting | Criteria are not discriminating. No uniqueness conclusion either way. | Expected. Criteria can fail. |
| 3. Linear herding (D2 at gamma=1) | B2 cannot be read as a general fact about linear transmission. B2 itself (about Black's LM) is unchanged. | Consistent with convexity being needed even in a thinner herding rule. |

No alternative result upgrades or refutes G4. If a result belongs on B1 assumptions, or if Lab wants a new O- or extension-claim on the map, Mimetic Theory updates the claim map, not this file and not Falsifier.
