# Thinner alternatives to Black's AC package (design v0)

Status: design only. Labeled extension, not an official ensemble.
Author: Mimetic Falsifier, 2026-11-12.
Official comparison still waits on a clean C-T2b (Table 2b, M1/B1).

This note specifies thinner rules to try against the published Black Table 2b setup. It covers alternatives 1-3 only (a G4 recruitment reading without objects, rivalry, or G3; random targeting; linear herding in the O7 voter-model family), which live under `eval/alternatives/`. It does not run them on official table paths, and it does not change `claims/claims.yaml`, `eval/contract.md`, judges, or official traces. If a result belongs on B1 assumptions, Mimetic Theory updates the claim map.

Lab recorded the first pre-registration on 2026-11-12, before any alternative run. Lab then recorded a refinement of that pre-registration on the same day (PR #26 review of head c0b4616), still before any alternative run. This text is that refinement. It addresses Reviewer's two blockers (PR #26 comment on d49764b), Reviewer's re-review of head c0b4616, and the should-fixes Lab listed, including the wide Alternative 1 sweep starting at 0.25.

Second Brain was queried before the first draft of this design (vault synced 2026-11-12). That first query found Girard concept pages and no notes that specify herding or random-targeting alternatives. There is no technical use of "herding" in the vault, and nothing framed as a non-Girardian foil. Reviewer's Second Brain follow-up for this PR, at vault commit bde78b6, is on the record (PR #26 comments). It records first-person Girard material (Hoover interview) describing a group-level recruitment process after object rivalry: neighbors move with the stronger of the two, then a second, a third, a fourth, easier and easier, gathering speed. The Things Hidden Book I, chapter 1, p. 26 sentence ("the power of mimetic attraction multiplies with the number of those polarized") is not in the vault, so this note does not cite the vault as reading that sentence as group-level recruitment or as individual salience. That is the same locator gap already recorded on G4 and on PR #17. The Alternative 1 rewording rests on the claim map's G4 delta (Black s4.1) and on that Hoover speech, not on a vault reading of the Things Hidden sentence. The vault does not classify a count-based herding rule (P(j) proportional to n_i(j)^gamma) as Girardian or as non-Girardian. Alternative 1 is therefore kept as a G4 recruitment reading without objects, rivalry, or G3, and a match is not treated as a finding about Girard's mechanism. The follow-up also records a limit, kept below: in Hoover, that recruitment sequence comes after object rivalry, and the vault neither claims nor denies that a recruitment-only rule without objects would still be the Girardian mechanism.

## Limits

- A matching outcome is an alternative generator of the same model output. It is not a disproof of Girard, not a status change on G4, and not a status change on B1. B1 is a claim about Black's AC variant, and only a rerun of that variant can pass or fail it. This is a judgment about generators of Black's Table 2b output, not a judgment that Girard's theory is true or false.
- If a thinner rule produces the same phenomena under the pre-registered uniqueness bar below, Black's AC package is not uniquely supported as the generator of that output. A match on Alternative 1 would mean the snowball stage alone, without the acquisitive stage (objects, rivalry, or G3), can generate the Table 2b pattern. Alternative 1 is not cleanly non-Girardian: it formalizes G4's snowball clause without the acquisitive stage. Whether a recruitment-only rule is still Girard's mechanism is not settled by Second Brain, and a match does not decide it. The affected reading is the uniqueness reading of B1: any use of B1 (or B2) as evidence that objects, rivalry, the G3 increment, or Black's individual-salience formalization of "multiplies" are necessary for a phase-boundary pattern. G4 itself is not upgraded or refuted. A match does not change G4 or B1 status, and it is not a judgment that Girard's theory is true or false.
- Reviewer's Second Brain follow-up at vault bde78b6 records Hoover's recruitment sequence as coming after object rivalry (people first polarize around objects, then imitate dislikes, then gather against one). The vault neither claims nor denies that a recruitment-only rule without objects would still be the Girardian mechanism. The amendment keeps that limit.
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

When all of agent t*'s neighbors already target t*, every neighbor weight on an allowed (non-self) target is zero, so t* falls back to a uniform draw over living non-self agents. Under this rule, t* never joins the mode by imitation. That is expected, and it is why the agreement ceiling is (N-1)/N. The near-consensus state is metastable, not absorbing: t* redraws uniformly to some j, and neighbors of t* then have n(j) >= 1 and can copy j. The uniform fallback injects noise that the D2 run-length test (ten consecutive steps at agreement >= 0.95) will see. A D2 pass is therefore a run-length result under that noise, not absorption.

## Pre-registered scoring

Bars declared before any alternative run. Lab recorded the first pre-registration on 2026-11-12, and recorded this refinement the same day, still before any run.

Alternative 1's gamma is convexity on integer neighbor counts (at most k = 6, 12, 20), not hostility salience on continuous h. The two parameters need not share a scale. On counts of 1 to 20, n^1.05 versus n^1.01 is only a few percent, so a miss on Black's published grid can coexist with a sharp, N-sharpening boundary at a different gamma. The bars are therefore split. Bar (a) is the uniqueness bar. Bar (b) is secondary.

**(a) Uniqueness bar: existence of a boundary.** Declared on the wide Alternative 1 sweep below, not on Black's published grid. A thinner rule produces "the same phenomena" if, on this protocol, it shows:

- a gamma interval with 0% convergence at and below some lower value, and 100% at and above some higher value, at each of N = 50, 100, 200;
- the convergence rate is non-decreasing in gamma across that transition. If the rate is not non-decreasing, report the non-monotone result as its own outcome; do not score it as a pass of (a);
- sharpening: width is the number of sweep points with rate strictly between 0% and 100%. Sharpening means the width at N = 100 and at N = 200 is no greater than the width at N = 50. The wide sweep is coarse (0.1 to 0.25 spacing), so a step (width 0) at every N is a likely shape and should not be over-read as a stronger result than it is. A step already at N = 50, with width no greater at larger N, still counts as a boundary; report the difference from the published B1a shape (fuzzy at N = 50, step at N = 100 and 200).

If the lowest sweep point is not 0% at some N, bar (a) is inconclusive on this sweep at that N, not a fail. Report the rate against gamma as it stands. A fail on (a), when the low end is 0% and the high end is not 100%, or when there is no 100% regime, means this alternative does not generate a phase-boundary pattern on the pre-registered wide sweep. That is a result, not a save of Black's AC package: other thinner rules can still be tried. A true no-pull low end would need a different rule (for example gamma approaching 0 with weight on targets no neighbor holds). This design does not add that rule.

**(b) Location match, secondary.** On the published Table 2b grid [1.01, 1.02, 1.03, 1.04, 1.05]: 0% at gamma <= 1.01 and 100% at gamma >= 1.04, at each N; the transition in [1.02, 1.03]; at N = 50, a fuzzy interval (neither 0% nor 100% at both 1.02 and 1.03, and the rate at 1.03 is at least the rate at 1.02); at N = 100 and N = 200, a step (0% at 1.02, 100% at 1.03). The rate must be non-decreasing in gamma across the grid; a non-monotone result is its own outcome, not a pass of (b). A fail on (b) says only that the alternative does not reproduce the boundary at the published gamma values. It is not a fail of the uniqueness bar, and it does not show the rule is "not a sufficient generator" of a phase-boundary pattern.

**Strict.** Exact published Table 2b rates on that same published grid: N=50 has 0%, 10%, 90%, 100% on those four columns; N=100 and N=200 have 0%, 0%, 100%, 100%. With 20 seeds, 10% is 2/20 and 90% is 18/20. A strict match is a surprise to report. It is not required for the uniqueness conclusion, and it sits under (b).

**Wide Alternative 1 gamma sweep (pre-registered).** Gamma in {0.25, 0.50, 0.75, 1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.75, 2.00, 2.25, 2.50, 2.75, 3.00}, at each of N = 50, 100, 200, same seeds, horizon, and graph as the shared protocol. This is the grid on which bar (a) is scored. The published five-point grid is still run, on the same seeds, for bar (b). The two grids share no required outcome: a boundary at, for example, 1.3 with 0% at 1.2 and 100% at 1.4 can pass (a) and fail (b). If the lowest point (0.25) is not 0% at a given N, bar (a) is inconclusive on this sweep at that N, not a fail: for any gamma > 0, n_i(j)^gamma is zero when no neighbor targets j, so the draw only picks targets neighbors already hold, and even 0.25 may coarsen toward consensus.

Random targeting has no gamma. It is scored on the published five-point grid as a flat control: bar (a) is not expected to hold, and a match would mean the criteria are not discriminating. This control is weak (uniform retargeting at rate 0.15 from uniform init will fail D2 almost surely), so a fail does not show that the criteria discriminate. It can stay. The stronger discrimination test is the wide Alternative 1 sweep: a rule that is 0% at the low end of that sweep and 100% at the high end, and is not flat, is doing work the random control cannot.

P-drop and P-gen are out of scope for this wave. Table 2b has expulsion disabled, so P-drop is N/A. Those properties can be designed after official Table 10 work is in a state Lab is willing to compare against.

## Alternative 1: G4 recruitment reading without objects, rivalry, or G3 (primary)

Alternative 1 is not cleanly non-Girardian: it formalizes G4's snowball clause without the acquisitive stage. Whether a recruitment-only rule is still Girard's mechanism is not settled by Second Brain, and a match does not decide it. It is kept as a G4 recruitment reading without objects, rivalry, or G3. It is a group-level recruitment rule: the pull on j grows with how many neighbors already target j. That rewording rests on the claim map's G4 formalization delta (Black s4.1 already records that "multiplies with the number of those polarized" may mean group-level recruitment, which the AC operator does not model) and on the Hoover speech cited above, not on a vault reading of the Things Hidden p. 26 sentence, which is not in the vault. The vault does not classify this count-based rule as Girardian or as non-Girardian. Alternative 1 keeps that snowball reading and drops objects, rivalry, the G3 increment, the hostility matrix, aggression decay, and throughput conservation.

Each agent i holds a target T_i in the living set, self-targeting forbidden. Let n_i(j) be the number of neighbors of i (in the same Watts-Strogatz graph) whose current target is j. The update schedule is synchronous from the start-of-step state: at each step, every agent reads the same target vector as it stood at the start of the step, and all draws are applied together at the end of the step. This is Lab's pick, the natural match to Black's step. At each step, independently given that start-of-step vector, each agent i, with probability alpha, draws a new target with

    P_i(j) proportional to n_i(j)^gamma    for living j != i,

and keeps T_i otherwise, where n_i(j) is computed from the start-of-step targets. If every neighbor weight is zero, the draw is uniform over living non-self agents. (That is the uniform fallback noted above, including when all neighbors target i.) A sequential sensitivity, if one is added later, must name the agent order and be labeled as a sensitivity; it is not part of this pre-registration.

Gamma here is convexity of count-based recruitment, not hostility salience. It is not assumed to share a scale with Black's gamma. The published five-point grid is run only for the secondary location check (b). The uniqueness question is asked on the wide sweep.

**Neighbor-restricted is the primary rule.** A global-count variant (n(j) over the whole population) is a pre-registered sensitivity, not the primary. It uses the same two grids. If only the global variant matches, say so; do not treat it as a pass of the primary.

This is the main uniqueness probe: if this G4 recruitment reading, without objects, rivalry, or G3, produces a phase-boundary pattern under bar (a), Black's AC package is not uniquely supported as the generator of that pattern. A match means the snowball stage alone can generate the Table 2b pattern. Whether a recruitment-only rule is still Girard's mechanism is not settled by Second Brain, and a match does not decide it.

## Alternative 2: random targeting (negative control)

Same graph, seeds, horizon, alpha, and synchronous start-of-step schedule. At each step, with probability alpha, agent i draws a uniform living non-self target (primary: global uniform; neighbor-uniform is a sensitivity), reading the start-of-step state; draws are applied together at the end of the step. There is no gamma in the rule. The published five-point grid is still run so a flat (gamma-independent) outcome is visible.

Expected result: bars (a) and (b) fail; few or no D2 convergences at these N and 800 steps. If this control matches, the pass/fail criteria are too weak and cannot support a uniqueness claim in either direction. As noted above, a fail is the expected and weak outcome; the wide Alternative 1 sweep is the stronger discrimination test.

## Alternative 3: linear herding (O7 voter-model family)

Alternative 1 with gamma fixed at 1, run once per N (not as a boundary test). This is the gamma = 1 slice of Alternative 1 and may share those runs with the wide sweep (same seeds and protocol). It is not a second independent test of that cell.

With gamma = 1, P_i(j) proportional to n_i(j) is "copy a random neighbor's target", lazy at rate alpha (the agent keeps T_i with probability 1 - alpha), with self-targets excluded. That is the O7 family already on the claim map (O7: "Voter-model unanimity depends on the update schedule"; formalization delta: adoption is a random copy of a neighbor, linear in the current count, with no objects or rivalry stage). Cross-reference O7 and its delta.

O7 records that, on a finite connected graph, consensus is absorbing for the voter model under the schedules it names. That result is about the rule without self-exclusion. Under this variant, self-exclusion and the uniform fallback make the (N-1)/N near-consensus state metastable, not absorbing. What decides a D2 outcome here is therefore a run-length result under that noise, versus the 800-step horizon (about 120 updates per agent at alpha = 0.15), not linearity as such. A D2 pass at 800 steps mostly measures the horizon. It does not show that B2 fails as a general fact about linear transmission. B2 itself (about Black's LM operator, and already recorded as holding only for the tested grid and horizon) is unchanged. The same synchronous start-of-step schedule is used (O7's claim is that unanimity depends on the schedule).

This alternative does not use bar (a) or bar (b), which are statements about a gamma sweep.

## G3 ablation (not in this PR)

A G3 ablation of Black's published AC operator (the 0.2 shared-desire increment set to 0) is a labeled Black ablation for issue 16. That work is Simulation's. It is not part of this design or this PR. Falsifier may point to it; Falsifier does not run it or include it under `eval/alternatives/`. Reviewer's degeneracy note on that ablation (if the increment is the only hostility source, setting it to 0 may yield identically zero hostility and a trivial D2 fail) is for Simulation, not this PR.

## Harness and coordination

- Same seeds policy and D2/D4 definitions as the contract, so a later official comparison can use the same judge ideas without scoring official paths.
- Manifest each run as a labeled extension: `ensemble` is one of `alt-herding-v0` (published grid, bar b), `alt-herding-wide-v0` (wide sweep, bar a), `alt-herding-global-v0`, `alt-herding-global-wide-v0`, `alt-random-v0`, `alt-linear-herding-v0`. `contract_version` must not be used to look like an official C-T2b export. Record the alternative id and the formalization delta.
- Scripts, when written, live under `eval/alternatives/` and must refuse to write to official trace directories.
- This design does not request Simulation to run the official reproduction, and it does not itself run on official table paths.
- Any commit goes up as a pull request. Do not merge. Send the PR to Mimetic Reviewer for a fidelity check. Reviewer's Second Brain follow-up at vault bde78b6 is on the record and is accounted for above, including the tighter-pass precisions: the Things Hidden p. 26 sentence is not in the vault, the rewording rests on the claim map's G4 delta and the Hoover speech, and the vault does not classify the herding rule as Girardian or as non-Girardian.

## Claims affected

| Alternative | If it meets uniqueness bar (a) | If it fails (a) |
|---|---|---|
| 1. G4 recruitment reading without objects, rivalry, or G3 | Black's AC package is not uniquely supported for a Table 2b-style phase-boundary output. A match means the snowball stage alone, without objects, rivalry, or G3, can generate that output. Alternative 1 is not cleanly non-Girardian: it formalizes G4's snowball clause without the acquisitive stage. Whether a recruitment-only rule is still Girard's mechanism is not settled by Second Brain, and a match does not decide it. Affected reading: the uniqueness reading of B1 (B1 as evidence that those AC ingredients, or Black's individual-salience formalization, are necessary for that pattern). B1 and G4 statuses unchanged. | If the lowest sweep point is not 0% at that N, bar (a) is inconclusive on this sweep at that N, not a fail. Otherwise: no such boundary on the pre-registered wide sweep. Other rules remain open. A fail on (b) alone is not this cell: it says the alternative does not reproduce the boundary at the published gamma values, not that it is "not a sufficient generator." |
| 2. Random targeting | Criteria are not discriminating. No uniqueness conclusion either way. A fail is expected and is a weak test; the wide Alternative 1 sweep is the stronger discrimination test. | Expected. Does not by itself show that the criteria can fail a non-flat rule. |
| 3. Linear herding (D2 at gamma = 1; O7 family) | Not scored on (a). A D2 pass at 800 steps mostly measures the horizon: under self-exclusion the (N-1)/N state is metastable, not absorbing, so a D2 pass is a run-length result under noise. It does not show that B2 fails as a general fact about linear transmission. B2 itself (about Black's LM) is unchanged. | A D2 fail at 800 steps is also mostly a horizon result, not a save of B2 as a general linear-transmission fact. Record peak modal against B2's 0.240. |

No alternative result upgrades or refutes G4. If a result belongs on B1 assumptions, or if Lab wants a new O- or extension-claim on the map, Mimetic Theory updates the claim map, not this file and not Falsifier.
