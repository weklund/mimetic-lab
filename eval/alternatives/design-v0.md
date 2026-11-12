# Thinner alternatives to Black's AC package (design v0)

Status: design only. Labeled extension, not an official ensemble.
Author: Mimetic Falsifier, 2026-11-12.
Official comparison still waits on a clean C-T2b (Table 2b, M1/B1).

This note specifies thinner rules to try against the published Black Table 2b setup. It covers alternatives 1-3 only (a G4 recruitment reading without objects, rivalry, or G3; random targeting; linear herding in the O7 voter-model family), which live under `eval/alternatives/`. It does not run them on official table paths, and it does not change `claims/claims.yaml`, `eval/contract.md`, judges, or official traces. If a result belongs on B1 assumptions, Mimetic Theory updates the claim map.

Lab recorded the first pre-registration on 2026-11-12, before any alternative run. Lab then recorded a refinement of that pre-registration on the same day (PR #26 review of head c0b4616), still before any alternative run. This text is that refinement. It addresses Reviewer's two blockers (PR #26 comment on d49764b) and the should-fixes Lab listed.

Second Brain was queried before the first draft of this design (vault synced 2026-11-12). That first query found Girard concept pages and no notes that specify herding or random-targeting alternatives. Reviewer's Second Brain check recorded on PR #17 found Girard interview material describing a recruitment process that gathers speed (a second, a third, a fourth; easier and easier) rather than individual salience. This design accounts for that finding: Alternative 1 is framed as a G4 recruitment reading without objects, rivalry, or G3, not as a non-Girardian rule. Reviewer has asked Second Brain for a further vault reading of this passage; if that follow-up changes the framing, this wording can be amended again before any run.

## Limits

- A matching outcome is an alternative generator of the same model output. It is not a disproof of Girard, not a status change on G4, and not a status change on B1. B1 is a claim about Black's AC variant, and only a rerun of that variant can pass or fail it. This is a judgment about generators of Black's Table 2b output, not a judgment that Girard's theory is true or false.
- If a thinner rule produces the same phenomena under the pre-registered uniqueness bar below, Black's AC package is not uniquely supported as the generator of that output. A match on Alternative 1 would mean the snowball stage alone, without the acquisitive stage (objects, rivalry, or G3), can generate the output. It would not mean that a non-Girardian rule can. The affected reading is any use of B1 (or B2) as evidence that objects, rivalry, the G3 increment, or Black's individual-salience formalization of "multiplies" are necessary for a phase-boundary pattern. G4 itself is not upgraded or refuted.
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
- Convergence: contract D2. t95 is the first t such that agreement[t+k] >= 0.95 for all k in 0..9; a trial converged iff t95 is not null. Agreement is D1, mapped onto a single discrete target as spelled out below.
- Also record D4 summaries (peak modal, final modal, their sds, peak gini when the alternative has a received-aggression vector; otherwise gini is N/A and is reported as such). For Alternative 3, peak modal is also set against B2's published Table 2 peak modal of 0.240.
- Median t95 at gamma 1.05 is recorded and compared under rule A to the opened-source values 88, 98, 102 for N = 50, 100, 200. This is a secondary check, not the uniqueness test. Because Alternative 1's gamma is convexity on neighbor counts, not hostility salience, a match or miss on those three numbers carries little weight.

The mixing probability, where an alternative uses one, is alpha = 0.15, the published Black value, so a failure to converge is not explained by a different step size. Initialization: each agent draws a uniform random living non-self target.

### D1 on a single discrete target

D1's eligibility threshold and argmax tie rule were written for continuous hostility. Alternatives 1-3 hold a single discrete target T_i per agent, so the mapping is:

- Every living agent is eligible. The threshold `sum_j A_i(j) >= 1e-8` is vacuous: the agent already holds a target.
- The agent's reported target is T_i. There is no argmax over a hostility vector, and the official tie rule does not apply.
- Agreement at a step is the fraction of living eligible agents whose T_i equals the current modal target (the most frequent held target among the living).
- If the modal target is a living agent, self-targeting is forbidden, so agreement is at most (N-1)/N. That ceiling is still above 0.95 at N = 50, 100, and 200, so D2 remains reachable.

### Self-exclusion near consensus, and the uniform fallback

When all of agent t*'s neighbors already target t*, every neighbor weight on an allowed (non-self) target is zero, so t* falls back to a uniform draw over living non-self agents. Under this rule, t* never joins the mode by imitation. That is expected, and it is why the agreement ceiling is (N-1)/N. The uniform fallback also injects noise that the D2 run-length test (ten consecutive steps at agreement >= 0.95) will see.

## Pre-registered scoring

Bars declared before any alternative run. Lab recorded the first pre-registration on 2026-11-12, and recorded this refinement the same day, still before any run.

Alternative 1's gamma is convexity on integer neighbor counts (at most k = 6, 12, 20), not hostility salience on continuous h. The two parameters need not share a scale. On counts of 1 to 20, n^1.05 versus n^1.01 is only a few percent, so a miss on Black's published grid can coexist with a sharp, N-sharpening boundary at a different gamma. The bars are therefore split. Bar (a) is the uniqueness bar. Bar (b) is secondary.

**(a) Uniqueness bar: existence of a boundary.** Declared on the wide Alternative 1 sweep below, not on Black's published grid. A thinner rule produces "the same phenomena" if, on this protocol, it shows:

- a gamma interval with 0% convergence at and below some lower value, and 100% at and above some higher value, at each of N = 50, 100, 200;
- sharpening from N = 50 to N = 100 and 200: the transition is no wider at the larger N than at N = 50. A fuzzy interval at N = 50 (at least one grid point strictly between 0% and 100%, or neither endpoint of the transition 0% and 100%) and a step at N = 100 and 200 (0% at one grid point and 100% at the next) is the published B1a shape. A step already at N = 50, with a step no wider at larger N, still counts as a boundary; report the difference from B1a.

A fail on (a) means this alternative does not generate a phase-boundary pattern on the pre-registered wide sweep. That is a result, not a save of Black's AC package: other thinner rules can still be tried.

**(b) Location match, secondary.** On the published Table 2b grid [1.01, 1.02, 1.03, 1.04, 1.05]: 0% at gamma <= 1.01 and 100% at gamma >= 1.04, at each N; the transition in [1.02, 1.03]; at N = 50, a fuzzy interval (neither 0% nor 100% at both 1.02 and 1.03); at N = 100 and N = 200, a step (0% at 1.02, 100% at 1.03). A fail on (b) says only that the alternative does not reproduce the boundary at the published gamma values. It is not a fail of the uniqueness bar, and it does not show the rule is "not a sufficient generator" of a phase-boundary pattern.

**Strict.** Exact published Table 2b rates on that same published grid: N=50 has 0%, 10%, 90%, 100% on those four columns; N=100 and N=200 have 0%, 0%, 100%, 100%. With 20 seeds, 10% is 2/20 and 90% is 18/20. A strict match is a surprise to report. It is not required for the uniqueness conclusion, and it sits under (b).

**Wide Alternative 1 gamma sweep (pre-registered).** Gamma in {1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.75, 2.00, 2.25, 2.50, 2.75, 3.00}, at each of N = 50, 100, 200, same seeds, horizon, and graph as the shared protocol. This is the grid on which bar (a) is scored. The published five-point grid is still run, on the same seeds, for bar (b). The two grids share no required outcome: a boundary at, for example, 1.3 with 0% at 1.2 and 100% at 1.4 can pass (a) and fail (b).

Random targeting has no gamma. It is scored on the published five-point grid as a flat control: bar (a) is not expected to hold, and a match would mean the criteria are not discriminating. This control is weak (uniform retargeting at rate 0.15 from uniform init will fail D2 almost surely), so a fail does not show that the criteria discriminate. It can stay. The stronger discrimination test is the wide Alternative 1 sweep: a rule that is 0% at the low end of that sweep and 100% at the high end, and is not flat, is doing work the random control cannot.

P-drop and P-gen are out of scope for this wave. Table 2b has expulsion disabled, so P-drop is N/A. Those properties can be designed after official Table 10 work is in a state Lab is willing to compare against.

## Alternative 1: G4 recruitment reading without objects, rivalry, or G3 (primary)

This is not a non-Girardian rule. It is a group-level recruitment rule: the pull on j grows with how many neighbors already target j. The claim map's G4 formalization delta already records that Black s4.1 concedes "multiplies with the number of those polarized" may mean group-level recruitment, which the AC operator does not model. Alternative 1 keeps that snowball reading and drops objects, rivalry, the G3 increment, the hostility matrix, aggression decay, and throughput conservation.

Each agent i holds a target T_i in the living set, self-targeting forbidden. Let n_i(j) be the number of neighbors of i (in the same Watts-Strogatz graph) whose current target is j. At each step, independently, each agent i, with probability alpha, draws a new target with

    P_i(j) proportional to n_i(j)^gamma    for living j != i,

and keeps T_i otherwise. If every neighbor weight is zero, the draw is uniform over living non-self agents. (That is the uniform fallback noted above, including when all neighbors target i.)

Gamma here is convexity of count-based recruitment, not hostility salience. It is not assumed to share a scale with Black's gamma. The published five-point grid is run only for the secondary location check (b). The uniqueness question is asked on the wide sweep.

**Neighbor-restricted is the primary rule.** A global-count variant (n(j) over the whole population) is a pre-registered sensitivity, not the primary. It uses the same two grids. If only the global variant matches, say so; do not treat it as a pass of the primary.

This is the main uniqueness probe: if this G4 recruitment reading, without objects, rivalry, or G3, produces a phase-boundary pattern under bar (a), Black's AC package is not uniquely supported as the generator of that pattern. A match means the snowball stage alone can generate the output, not that a non-Girardian rule can.

## Alternative 2: random targeting (negative control)

Same graph, seeds, horizon, and alpha. At each step, with probability alpha, agent i draws a uniform living non-self target (primary: global uniform; neighbor-uniform is a sensitivity). There is no gamma in the rule. The published five-point grid is still run so a flat (gamma-independent) outcome is visible.

Expected result: bars (a) and (b) fail; few or no D2 convergences at these N and 800 steps. If this control matches, the pass/fail criteria are too weak and cannot support a uniqueness claim in either direction. As noted above, a fail is the expected and weak outcome; the wide Alternative 1 sweep is the stronger discrimination test.

## Alternative 3: linear herding (O7 voter-model family)

Alternative 1 with gamma fixed at 1, run once per N (not as a boundary test). This is the gamma = 1 slice of Alternative 1 and may share those runs with the wide sweep (same seeds and protocol). It is not a second independent test of that cell.

With gamma = 1, P_i(j) proportional to n_i(j) is "copy a random neighbor's target", lazy at rate alpha (the agent keeps T_i with probability 1 - alpha), with self-targets excluded. That is the O7 family already on the claim map (O7: "Voter-model unanimity depends on the update schedule"; formalization delta: adoption is a random copy of a neighbor, linear in the current count, with no objects or rivalry stage). Cross-reference O7 and its delta.

On a finite connected graph, consensus is absorbing for the voter model under the schedules O7 records. What decides a D2 outcome here is time to consensus versus the 800-step horizon (about 120 updates per agent at alpha = 0.15), not linearity as such. A D2 pass at 800 steps mostly measures the horizon. It does not show that B2 fails as a general fact about linear transmission. B2 itself (about Black's LM operator, and already recorded as holding only for the tested grid and horizon) is unchanged.

This alternative does not use bar (a) or bar (b), which are statements about a gamma sweep.

## G3 ablation (not in this PR)

A G3 ablation of Black's published AC operator (the 0.2 shared-desire increment set to 0) is a labeled Black ablation for issue 16. That work is Simulation's. It is not part of this design or this PR. Falsifier may point to it; Falsifier does not run it or include it under `eval/alternatives/`. Reviewer's degeneracy note on that ablation (if the increment is the only hostility source, setting it to 0 may yield identically zero hostility and a trivial D2 fail) is for Simulation, not this PR.

## Harness and coordination

- Same seeds policy and D2/D4 definitions as the contract, so a later official comparison can use the same judge ideas without scoring official paths.
- Manifest each run as a labeled extension: `ensemble` is one of `alt-herding-v0` (published grid, bar b), `alt-herding-wide-v0` (wide sweep, bar a), `alt-herding-global-v0`, `alt-herding-global-wide-v0`, `alt-random-v0`, `alt-linear-herding-v0`. `contract_version` must not be used to look like an official C-T2b export. Record the alternative id and the formalization delta.
- Scripts, when written, live under `eval/alternatives/` and must refuse to write to official trace directories.
- This design does not request Simulation to run the official reproduction, and it does not itself run on official table paths.
- Any commit goes up as a pull request. Do not merge. Send the PR to Mimetic Reviewer for a fidelity check before treating the wording as final.

## Claims affected

| Alternative | If it meets uniqueness bar (a) | If it fails (a) |
|---|---|---|
| 1. G4 recruitment reading without objects, rivalry, or G3 | Black's AC package is not uniquely supported for a Table 2b-style phase-boundary output. A match means the snowball stage alone, without objects, rivalry, or G3, can generate that output. It does not mean a non-Girardian rule can. Affected reading: B1 as evidence that those AC ingredients, or Black's individual-salience formalization, are necessary for that pattern. B1 and G4 statuses unchanged. | No such boundary on the pre-registered wide sweep. Other rules remain open. A fail on (b) alone is not this cell: it says only that the boundary is not at the published gamma values. |
| 2. Random targeting | Criteria are not discriminating. No uniqueness conclusion either way. A fail is expected and is a weak test; the wide Alternative 1 sweep is the stronger discrimination test. | Expected. Does not by itself show that the criteria can fail a non-flat rule. |
| 3. Linear herding (D2 at gamma = 1; O7 family) | Not scored on (a). A D2 pass at 800 steps mostly measures the horizon, given O7 (consensus is absorbing on finite connected graphs under the recorded schedules). It does not show that B2 fails as a general fact about linear transmission. B2 itself (about Black's LM) is unchanged. | A D2 fail at 800 steps is also mostly a horizon result, not a save of B2 as a general linear-transmission fact. Record peak modal against B2's 0.240. |

No alternative result upgrades or refutes G4. If a result belongs on B1 assumptions, or if Lab wants a new O- or extension-claim on the map, Mimetic Theory updates the claim map, not this file and not Falsifier.
