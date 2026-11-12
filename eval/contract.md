# Evaluation contract v0.2.2

Mimetic Proofs and Mimetic Simulation. Source of truth: public repo [weklund/mimetic-lab](https://github.com/weklund/mimetic-lab).

**Status: v0.2.2, proposed 2026-11-12.** This is a contract amendment after Table 10 results were seen. Lab will record a formal decision on this PR. Exports may carry contract_version "0.2.2" and are scored under v0.2.2 only after the Lab decision. v0.2.1 (rule A, after the v0.2 C-T2 run) remains separately pending and this version does not adopt or decide v0.2.1. Until the Lab decides, v0.2 stays in force. See the changelog.

A pass is evidence that a specified model, under stated assumptions and a pinned source SHA, exhibits a specified property. It is not a proof that Girard's anthropology is true, and it is not a verdict on Girard.

## Roles

- Mimetic Simulation produces traces and runs experiments. It does not score official contract traces.
- Mimetic Proofs owns properties, pass/fail criteria, and statistical confidence bounds, and judges traces.
- If the two disagree on what counts as a pass, both stop and let Mimetic Lab decide.
- A change to what counts as a pass, made after results have been seen, is a contract amendment even when Simulation and Proofs agree on it. Their agreement does not settle it: the producer and the judge share a stake in the outcome. Mimetic Lab decides, and the changelog records that the change came after the results.
- A Lab decision is an approving GitHub review, or a commit, by Wes whose text begins `Lab decision:`. Review bots that post from Wes's account (the Mimetic Reviewer) are not the Lab.
- Neither invents new philosophical claims. Thresholds and predicates come from published code and from Black 2026 `paper_draft_18.md`, not from new numbers.

## Source

Maxwell Black, "A Computational Test of Girard's Scapegoat Mechanism" (2026), `paper_draft_18.md`, and `girard_2x2_v3.py` / `small_n_utils.py`, from [maxwell-black/mimetic-desire-simulation](https://github.com/maxwell-black/mimetic-desire-simulation). Official first-milestone runs use the published `reproduce_*.py` and viability scripts, built-in seeds (`42 + r * 1000`), and do not modify published source. Wrappers, harness, and exports live in `weklund/mimetic-lab`.

Every ensemble names the full git SHA actually run. Predicates are those of that SHA.

## Claim map

This contract scores model claims in [`claims/claims.yaml`](../claims/claims.yaml). The names below that come from Girard (unanimity, catharsis, founding murder) are Black's operational labels for trace predicates. A pass upgrades only the matching B claim (claim-map rule 2), never a G claim.

| Contract item | Claim | Stands in for | Delta to read with it |
|---|---|---|---|
| C-T2 (gamma > 1.01 rows), C-T2b, C-composite; P-conv | B1 (phase boundary), sub-claims B1a, B1c | G4 | G4's Black-2026 delta: "inevitable" weakened to "above a gamma threshold"; unanimity is modal agreement, not total participation |
| C-T2 (gamma <= 1.00 rows) | B2 (linear transmission never converges) | G4 | B2 holds only for the tested grid and horizon |
| C-T10; P-gen; D7 | B4 (self-exhaustion viability) | G6 | G6's Black-2026 delta: transient catharsis, no sacred; `min_silence = 500` weakens "durable" further |
| C-T1; P-drop; D6 | none yet | G6 (catharsis) | Reported against G6's delta. No B claim is upgraded by a C-T1 pass until one is written |

## Operational rule for paper-versus-code mismatches

When prose and the script that produced a table disagree, reproduction of that table uses the script. The mismatch is reported, not silently "fixed." A prose-only variant may be scored only as a separately labeled predicate, never as the Table-N reproduction.

Known mismatches at v0.2.1:

1. Section 3.11.2 says genuine self-exhaustion is "no expulsions for the final 2000+ steps." `classify_exhaustion` in `small_n_utils.py` uses `min_silence=500` (no reconvergence to the adaptive threshold, and at least 500 steps after the last expulsion). Table 10 was produced by `exp_small_n_viability.py`, so **C-T10 uses `min_silence=500`**. A second predicate, **D7-paper**, uses the same D7 conditions with `min_silence=2000` (section 3.11.2). Simulation exports `viability_D7_paper` on every Table 10 trial so the mismatch can be reported empirically. D7-paper is never used to pass or fail C-T10.
2. Table 11's caption says convergence is modal agreement >= 0.95, but `exp_small_n_phase_boundary.py` uses `adaptive_unanimity_threshold(N)` sustained for 10 steps. **C-T11 uses the script.** At N >= 20 the two coincide; at N < 20 they do not. At N=5, when every living agent is eligible, the ceiling is 0.80, so 0.95 can be reached only at an instant when the modal target is not eligible and does not vote (see D1).
3. Table 2's median t95 at gamma 2.00. The paper prints 30. `reproduce_table_2.py` prints `int(np.median(...))`, which is 29 for the converged t95 values 14, 20, 23, 29, 30, 30, 31, 42 (np.median 29.5). The paper's integers match round-half-even of np.median in all 13 cells; `int()` matches 12. Only this cell tells the two rules apart. Resolved by rule A, under which both 29 and 30 are consistent with 29.5. Found after the v0.2 C-T2 run (see the changelog).

## Comparing with printed numbers (rule A)

A printed number is a rounded value. Reproduction compares in the unrounded domain: a reproduced value v matches a printed value p iff |v - p| <= half a unit in p's last printed place (0.5 for an integer, 0.0005 for 3 decimals, 0.05 for 1 decimal), plus 1e-12 for floating-point representation. A printed value that is absent matches only an absent reproduced value. Counts (k, n) are integers and must match exactly.

The window has the same width as an exact match under any single rounding rule. It is centred on the printed value, which is how a reader takes a rounded number, so it does not loosen the test and does not require guessing which rounding step produced the paper. It also removes floating-point sensitivity at .xxx5 boundaries. Rule A applies to every reproduction claim below.

The unmodified script's own printed output is compared field by field, as text, with what the judge recomputes from the traces (C-T2). That comparison is exact, because both format the same floats the same way.

## Definitions

**D1. Modal-target agreement** (Black Sections 2.3, 2.4; `record_metrics` / `get_modal_target`).

- T_i = argmax_j A_i(j) over living j, self-targeting excluded; ties go to the first living target in alive order (`np.argmax`, as `record_metrics`).
- Living set L_t. Eligible set A_t = {i in L_t : sum_j A_i(j) >= 10^{-8}} (code uses `>= 1e-8`; Simulation's write-up said `>`). The judge uses the code: `>= 1e-8`.
- Modal target t* = mode({T_i : i in A_t}).
- Agreement = |{i in A_t : T_i = t*}| / |A_t|, or 0 if A_t is empty.
- Ceiling. If t* is in A_t it cannot vote for itself, so agreement is at most (|A_t| - 1) / |A_t|; that is (N-1)/N when every living agent is eligible. If t* is not in A_t, every eligible agent can target it and agreement can reach 1.0. The eventual victim is still in L_t at the instant agreement is measured; they are the modal target, not excluded from the agent set, and they vote if eligible. After expulsion they leave L_t. On Table 2's converged runs the recorded peak is 0.980 = 49/50, so there the victim was eligible and voting.

**D2. Converged, no-expulsion phase boundary** (Tables 2, 2b; Sections 2.3, 3.2). `time_to_95`: t95 is the first t such that agreement[t+k] >= 0.95 for all k in 0..9; else null. A trial converged iff t95 is not null. T = 10 is published. The series is recorded at the end of each step, length = steps completed.

**D3. Converged, small-N phase boundary** (Table 11). Same as D2, but the threshold is `adaptive_unanimity_threshold(N) = min(0.95, (N-1)/N)` for N > 1, else 1.0, sustained 10 consecutive steps.

**D4. Table 2 summary stats.** Peak modal = max(agreement). Final modal = mean of the last 50 agreement values. Peak gini = max(aggression_gini), where aggression_gini is the official `_gini` of received aggression. Median t95 is the median of t95 over converged trials only.

**D5. System tension.** M_t = sum_v R(v), total received aggression over living agents (code: `system_tension`). This is not called tau. In Black, tau is the expulsion threshold on received aggression R(v*), default 8.0 (Table 1, Appendix C.7), a trigger, not the tension measure.

**D6. Immediate catharsis** (Table 1 caption, Section 3.5, `catharsis_events`). For an expulsion at step t, fractional_drop = (M_{t-} - M_{t+}) / M_{t-} after zeroing aggression to and from the expelled agent, or 0 if M_{t-} = 0 (code also floors at 0). Horizon k = 0 (immediate). There is no published multi-step k, and this contract does not invent one. For the unanimity-triggered runner, which bypasses `step_expulsion`, the wrapper must compute D6 the same way. Traces carry the received-aggression vectors immediately before and after zeroing, so the judge recomputes M_{t-} and M_{t+} instead of trusting them.

**D7. Self-exhaustion viability** (Table 10 predicate; Black's label: "generative founding murder"). A trial is viable iff all three hold, using official `classify_exhaustion` with `min_silence=500`:

1. status == `genuine_exhaustion` (no reconvergence to the adaptive threshold after the last expulsion, and at least 500 remaining steps),
2. pct_consumed < 0.50,
3. n_expulsions >= 1.

Cooldown is 5. Trigger is Use 2 below. See Incomplete trials (wall-clock timeout) for the handling of incomplete trials. **D7-paper** is the same three conditions with `min_silence=2000`, matching section 3.11.2. It is reported on every Table 10 trial and is not the Table 10 predicate.

The label is Black's. In Girard, the founding murder is generative because the killing founds the sacred, myth, and ritual, and because the community does not know it has a scapegoat. D7 measures none of these; the model has no sacred (G6's Black-2026 delta). It also weakens "durable": D7 asks for 500 silent steps where section 3.11.2's prose says 2000+. A D7 pass upgrades B4, not G6.

A **trial** is one seeded run: the tuple (script, variant, N, gamma, seed).

## Incomplete trials (wall-clock timeout)

A wall-clock timeout in `run_unanimity_triggered` is a hang safety net, not a theoretical outcome. The official docstring already says that. A trial that stops on that net is incomplete and is not a cell outcome. The official trial is a run of the same pinned SHA, script, and seed that completes all `n_steps_planned` steps. Pass/fail does not use `status == timeout` as a D7 or cell result. If a completed rerun is needed, it is labeled in the manifest, and the incomplete run is cited only in a fact note. If a seed still cannot complete after a labeled rerun, it remains incomplete and is reported, not scored as a timeout outcome.

A cell with any incomplete seed after the labeled rerun has no verdict (INCOMPLETE). C-T10 cannot PASS while any cell is INCOMPLETE. Do not use k/19, and do not count an incomplete seed as a non-viable trial in a k/20.

Complete means timed_out == false and steps_completed == n_steps_planned.

At most one labeled rerun per seed.

A rerun must use the same pinned SHA, unmodified published script, and seed. It may run on different hardware or under lower load. Because the timeout is a hang safety net and not a model parameter, the harness may pass a larger timeout_seconds than the official default. The manifest records timeout_seconds and the host for every official trial, including a rerun. Do not edit the published script.

Determinism check: the incomplete run's per-step arrays must equal the first steps_completed steps of the completed rerun. If they do not match, the rerun is not the official trial for that seed, and the seed stays incomplete, with the mismatch in the fact note.

This rule applies to C-T10 and to any ensemble that uses official `run_unanimity_triggered`. It is a general rule about incomplete trials, not a rule written to pick a cell result.

## Properties

**P-conv (unanimous polarization / Black convergence).** Single-trial predicate is D2 or D3, according to the ensemble. This is Black's published convergence claim about hostility targeting. Sack Def. 2 (obj(i) = obj(med(i))) is not applied to Black traces in this milestone and is not mapped into one. A Sack analogue, if added later, will be a separately labeled property.

Two published uses of D1:

- Use 1, convergence: D2, usually with expulsion disabled (Tables 2, 2b).
- Use 2, unanimity-triggered expulsion (Sections 3.8, 3.11.1): expulsion fires when agreement >= theta, 5-step cooldown. For N >= 20, theta = 0.95. For smaller N, theta(N) = min(0.95, (N-1)/N). This is the trigger for Table 10 and violence-topology tables, not a post-hoc pass on those traces (at a trigger instant the inequality holds by construction).

**P-drop (tension drop after victimization).** Applies only to traces with at least one expulsion. Table 2 and 2b have expulsion disabled, so P-drop is N/A there. Immediate: D6, k = 0. There is no single invented pass delta. Ensemble targets, when reproducing those tables, are the published means: Table 1 (10 runs, gamma=2.0, tau=8.0, 600 steps) mean catharsis LM 5.6%, AC 29.6%, RL 6.3%, RA 36.7%; Section 3.6 Regime 2 (tau=500): "total system tension collapses by roughly 95%." Table 4 peace is a different metric (consecutive steps with agreement < 0.50 after the first expulsion; median 17 steps at tau=500) and is reported separately, not as P-drop.

**P-gen (self-exhaustion viability; Black's "generative founding murder").** Single-trial: D7.

## Ensemble claims (first milestone)

Official seeds: `42 + r * 1000`. Variant is AC unless noted. Reproduction pass is a match to the published table as specified below, under rule A, not a new population-rate test.

**C-T2 (reproduce Table 2).** Script `reproduce_table_2.py`: AC, N=50, k=6, p=0.15, alpha=0.15, no expulsion, 8 runs, 600 steps, gammas [0.75, 0.90, 0.95, 1.00, 1.01, 1.02, 1.05, 1.08, 1.10, 1.15, 1.25, 1.50, 2.00]. Pass iff for every gamma: converged count k equals the published count (0 for gamma <= 1.01; 1 for 1.02; 8 for gamma >= 1.05); the median t95 among converged trials, when published, is consistent under rule A with the published integer (421 at 1.02; then 116, 74, 62, 43, 30, 29, 30); mean peak modal, mean final modal, their sds, and mean peak gini are consistent under rule A with the printed 3 decimals; and every field of the unmodified script's printed row (saved stdout) equals what the judge recomputes from the traces. This table has no 1.03 row and locates the N=50 boundary in [1.02, 1.05].

**C-T2b (reproduce Table 2b; first target for the [1.02, 1.03] and sharpening claims).** Script `reproduce_table_2b.py`: AC, no expulsion, 20 runs, 800 steps, gammas [1.01, 1.02, 1.03, 1.04, 1.05], N in [50, 100, 200], k = max(6, min(int(N*0.12), 20)) forced even (k=6, 12, 20). Pass iff converged counts match published rates exactly:

- N=50: 0% at 1.01, 10% (2/20) at 1.02, 90% (18/20) at 1.03, 100% (20/20) at >= 1.04.
- N=100 and N=200: 0% at <= 1.02, 100% at >= 1.03.

Sharpening passes if that pattern holds (fuzzy interval at N=50, step between 1.02 and 1.03 at N >= 100). Also check published median t95 at gamma=1.05: 88, 98, 102 for N=50, 100, 200, under rule A. Table 2b as printed stops at N=200. The README and Section 3.11.3 mention N=500, but there is no official no-expulsion sweep at N=500 in the published repo; see C-composite. C-T2b is the first ensemble target for the boundary claim, not C-T2.

**C-T10 (reproduce Table 10).** Script `exp_small_n_viability.py`: AC and RA, N in {5, 10, 15, 20, 25, 30, 35, 40}, gamma in {1.05, 1.5, 2.0}, 20 seeds, 5000 steps, Use 2, cooldown 5. Viability index = fraction of trials satisfying D7. See Incomplete trials (wall-clock timeout) for the handling of timeouts. Pass iff, for each cell, all 20 seeds are complete and k/20 matches the published percent. A cell with any incomplete seed after the labeled rerun has no verdict (INCOMPLETE), and C-T10 cannot PASS while any cell is INCOMPLETE:

- AC 1.05: 25, 75, 65, 90, 95, 85, 85, 90
- AC 1.50: 0, 0, 55, 60, 90, 85, 95, 95
- AC 2.00: 0, 5, 50, 65, 85, 70, 90, 80
- RA 1.05: 0, 25, 85, 85, 60, 80, 90, 80
- RA 1.50: 0, 0, 25, 65, 80, 85, 100, 90
- RA 2.00: 0, 0, 30, 75, 80, 95, 90, 65

The qualitative "generative window around N=15 to 50" is described only after these cells match, without new claims. Table 10 stops at N=40. Section 3.9 / Table 8 at N=50 uses a different protocol (threshold-triggered, tau=8, 10,000 steps) and is not pooled with Table 10. Linear controls (LM, RL) are reported if exported; the paper says they produce zero expulsions at N >= 15.

**C-T11 (small-N phase boundary, if run).** Script `exp_small_n_phase_boundary.py`, D3. gamma-star = lowest tested gamma with >= 50% convergence. Published: N=5..40, gamma-star 1.03, 1.03, 1.05, 1.04, 1.03, 1.03, 1.03, 1.03, paper range [1.03, 1.05].

**C-composite (phase boundary at the 11 tested sizes, first milestone).** Composite of two tables with two gamma-star definitions: C-T11 at the eight published sizes N = 5, 10, ..., 40 (lowest gamma with >= 50% convergence, adaptive threshold) and C-T2b at N = 50, 100, 200 (exact rates, threshold 0.95). It is a composite over these sizes and definitions, not one invariant, and says nothing about sizes in between. C-T2b alone is not a pass on the tested sizes from N=5 to 200 without C-T11, and nothing here is a pass on N=500. B1's review flags already record that the paper's "invariant from 5 to 500" mixes three gamma-star definitions.

There is no official no-expulsion gamma sweep at N=500 in the published repo (`phase_boundary_large_N.py` and `reproduce_table_2b.py` both stop at N=200). The N=500 scripts (`exp1_ultralong_n500.py`, `unanimity_trigger_N_gamma.py`, `self_exhaustion_interpolation.py`) are unanimity-triggered or self-exhaustion runs, not the phase-boundary sweep. The N=5 to 500 sentence in the paper (Appendix G, and 3.11.3 citing 3.2) is therefore not backed by a first-milestone official table. This contract does not invent a substitute table, and does not treat an N=500 run as C-T2b.

After official C-T2, C-T2b, C-T10, and Table 11 runs, Simulation may run a clearly labeled **extension** at N=500 with the Table 2b protocol (AC, no expulsion, 20 seeds `42+r*1000`, 800 steps, same gamma grid, k=20). That extension is not an official published table. It is scored, if at all, as a separate labeled claim, never as C-T2b.

**C-T1 (catharsis means, if run).** Table 1, 10 runs, gamma=2.0, tau=8.0, 600 steps. Ensemble mean fractional_drop (D6) is consistent under rule A with published LM 5.6%, AC 29.6%, RL 6.3%, RA 36.7% (1 decimal). Its manifest cells carry `claimed_k` and `claimed_rate` as null, and no binomial interval is attached. Not part of the Table 2 / 2b first delivery.

## Statistics

For every ensemble cell with a published count the judge reports k, n, the rate, and a 95% Clopper-Pearson confidence interval. That interval is a report, not an extra fail condition.

Official n is 8 or 20. Even 8/8 has a 95% lower bound around 0.63. This contract does **not** fail a reproduction because that lower bound is below a p*. There is no p* on these official published sample sizes. Reproduction pass is match to the published table, as above. A p* rule (CI lower bound >= p*) will be pre-registered only for a later, larger, pre-registered ensemble, never set after looking at official n=8 or n=20 results.

## Trace schema

One trial file plus an ensemble manifest, and the unmodified script's saved stdout. Full field definitions are in [`trial-schema.md`](trial-schema.md). JSON metadata and events; per-step arrays may live in the same JSON or in a sibling NPZ. UTF-8 JSON, no NaN or Infinity (use null). Published source is not edited. Wrappers live in this repo.

Layout:

```
eval/traces/v0.2/
  <ensemble_id>/          # e.g. table2, table2b, table10, table11, table1
    manifest.json
    script_stdout.txt     # verbatim stdout of the unmodified published script
    trials/<trial_id>.json
    trials/<trial_id>.npz   # optional, if series are not inline
eval/summaries/<ensemble_id>.json   # optional claimed-vs-reproduced notes
```

`trial_id` = `{ensemble_id}-g{gamma}-N{N}-v{variant}-s{seed}`.

**manifest.json**

- contract_version: `"0.2.2"` for ensembles exported under this amendment; `"0.2.1"` and `"0.2"` remain accepted for traces already exported under them
- ensemble_id, paper (`Black 2026, A Computational Test of Girard's Scapegoat Mechanism`), draft (`18`)
- source_repo, source_sha (full SHA actually run)
- script, python_version, packages (numpy, networkx, scipy at least)
- command, started_at, ended_at (ISO-8601)
- trial_ids: list
- For each trial or in a `cells` list: table, N, gamma, variant, n, claimed_k or claimed_rate (null for continuous-metric cells), so the judge can attach a Clopper-Pearson interval to a published count
- script_stdout_file and script_stdout_sha256: the saved stdout of the unmodified script for this run

**trial JSON, required metadata**

- contract_version, trial_id, ensemble_id, script, source_sha, draft
- variant (`LM` | `AC` | `RL` | `RA`), source_mode (`object` | `status`), spread_mode (`linear` | `attention`). Official VARIANT_MAP: LM = (object, linear), AC = (object, attention), RL = (status, linear), RA = (status, attention). These two fields must match the map for the stated variant.
- N, k, rewire_prob, alpha, gamma, aggression_decay
- expulsion_mode (`none` | `threshold` | `unanimity_adaptive`)
- expulsion_threshold (null if none), unanimity_threshold (null if none), unanimity_cooldown (null if none)
- n_steps_planned, steps_completed, seed, timed_out (see Incomplete trials (wall-clock timeout) for handling of incomplete runs)
- timeout_seconds, host (required for every official trial, including a rerun; see Incomplete trials (wall-clock timeout))
- rerun_of (null or the trial_id of the incomplete run this is a labeled rerun of; see Incomplete trials (wall-clock timeout))
- python_version, packages, command, started_at, ended_at

**Per-step arrays** (length = steps_completed; enough for Proofs to recompute D1 and D2 independently). Field names may be either the code names or the names below; the manifest or trial must be consistent, and the judge accepts this mapping:

| Contract name | Code / Simulation name | Content |
| --- | --- | --- |
| modal_agreement | modal_agreement | D1 |
| eligible_agents | eligible_count | \|A_t\| |
| eligible_ids | eligible_ids | ids in A_t, unique, a subset of alive_ids |
| top_targets | T_i per eligible agent | enough to recompute the mode |
| system_tension | M, system_tension | D5 |
| n_active_agents | n_alive | \|L_t\| |
| alive_ids | alive_ids | ids in L_t |
| received_aggression | R(v) for each living v | enough to recompute M |
| aggression_gini | aggression_gini | |
| aggression_max_share | top_target_share | |
| convergence_ratio | convergence_ratio | |
| aggression_entropy | aggression_entropy | base 2 |
| top_target_aggression | top_R | |
| mean_aggression | mean_R | |
| modal_target_id | | optional |

Full N by N aggression, and desire vectors, are not required for this milestone. If a later Sack analogue needs them, they will be requested on a subset.

If arrays are in a sibling NPZ, the JSON has `"series": {"$npz": "<trial_id>.npz"}` with the same array names. Metadata and events stay in the JSON. Prefer all-JSON when small (Table 2 will be).

**Events**

- expulsion_events: list of {step, victim_id, received_aggression} (t, victim_id, R(v*))
- catharsis_events: list of {step, victim_id, M_pre, M_post, fractional_drop, event_alive_ids, received_aggression_pre, received_aggression_post}, where fractional_drop is D6, M_pre and M_post are system tension before and after zeroing (not the expulsion threshold), and the three vectors let the judge recompute both sums. Required before Table 1 or Table 10 traces are generated.

For Table 2 / 2b, both lists are empty and `viability` is null.

**viability** (required for Table 10 and other unanimity-triggered runs), official fields:

- n_expulsions, pct_consumed, n_alive, status, self_exhausted, first_peace, first_reconverge, peak_modal, n_fragments, largest_fragment, expulsion_steps, med_gap

`status` is exactly one of: `genuine_exhaustion`, `still_cycling`, `censored`, `no_expulsions`, `timeout`. See Incomplete trials (wall-clock timeout) for the handling of `timeout` status.

**Archive.** Traces that back an official verdict are committed under `eval/traces/` through Git LFS (see `.gitattributes`), or attached to a GitHub release, with their SHA-256 recorded in the judge result. `eval/judge/check_trace_hashes.py` confirms the archived files are the ones scored.

## Judge

Mimetic Proofs runs the judge on the exported files and returns, per claim, pass or fail, the per-cell k and published k, continuous metrics against published values under rule A, the comparison with the script's printed output, and 95% Clopper-Pearson intervals as a report. Simulation may include claimed-vs-reproduced numbers in `eval/summaries/` for its own report; those are not the official score.

Each judge:

- validates structure and identities before computing anything, and rejects NaN, Infinity, and overflowing literals;
- fails closed: any malformed input or internal error is a FAIL, written atomically over any earlier result;
- reports every problem with a stable issue code (listed in [`judge/README.md`](judge/README.md));
- marks its verdict provisional when an input it compares against, such as the saved script stdout, is missing;
- ships with tests that show it passing a valid ensemble and failing each corruption, and tests that check its metric functions against Black's own code at the pinned SHA. A check that has never been shown to fail is not evidence.

**Official verdict.** A verdict is official only when (1) the judge returns PASS or FAIL with no provisional reasons, (2) the traces it scored are retrievable from this repo and match the recorded hashes, and (3) any rule changed after results were seen has a Lab decision recorded here.

## Current results

- **C-T2: PASS pending Lab decision on v0.2.1. Not yet official.** The v0.2 judge returned PASS on its operational rule and FAIL on line 76's literal paper integers (one cell, gamma 2.00 median). Under v0.2.1 rule A, all 13 cells pass on a re-score of the per-trial values that run recorded (`eval/judge/rescore_from_result.py`). Remaining for official status: the Lab decision on v0.2.1; the traces archived in this repo and matching the recorded SHA-256 hashes; the script's stdout saved and the v0.2.1 judge re-run on the archived traces.

## Changelog

- 2026-11-11 v0.2: first agreed contract; C-T2 judge and result.
- 2026-11-11 v0.2.1 (proposed; Lab decision pending). **Changed after the v0.2 C-T2 run was seen:** rule A for printed numbers replaces exact equality with printed integers and 3-decimal strings; known mismatch 3 (Table 2 median at gamma 2.00). Also: amendment and Lab sign-off rules in Roles; claim-map links; D1 tie rule and exact ceiling; known mismatch 2 qualified; D7 and P-gen relabeled as Black's terms, linked to G6 and B4; C-inv-full renamed C-composite and scoped to the 11 tested sizes and two definitions; C-T1 cells may have null counts; script stdout saved and compared field by field; catharsis events carry pre- and post-zeroing vectors; archive and official-verdict conditions; judge requirements (fail closed, issue codes, tests against the official code).
- 2026-11-12 v0.2.2 (proposed; Lab decision pending). **Contract amendment after Table 10 results were seen.** Incomplete trials (wall-clock timeout): a wall-clock timeout in `run_unanimity_triggered` is a hang safety net, not a cell outcome. An incomplete trial is not used as a D7 or cell result. The official trial completes all `n_steps_planned` steps (complete means timed_out == false and steps_completed == n_steps_planned). If a completed rerun is needed, it is labeled in the manifest (at most one labeled rerun per seed), and the incomplete run is cited only in a fact note. A rerun must use the same pinned SHA, unmodified published script, and seed; it may run on different hardware or under lower load, and the harness may pass a larger timeout_seconds. The manifest records timeout_seconds and the host for every official trial, including a rerun. Determinism check: the incomplete run's per-step arrays must equal the first steps_completed steps of the completed rerun; if they do not match, the rerun is not the official trial for that seed, and the seed stays incomplete, with the mismatch in the fact note. If a seed still cannot complete after the labeled rerun, it remains incomplete and is reported, not scored as a timeout outcome. A cell with any incomplete seed after the labeled rerun has no verdict (INCOMPLETE). C-T10 cannot PASS while any cell is INCOMPLETE. Do not use k/19, and do not count an incomplete seed as a non-viable trial in a k/20. This rule applies to C-T10 and any ensemble using official `run_unanimity_triggered`. It is a general rule about incomplete trials, not a rule written to pick a cell result. Exports may carry contract_version "0.2.2" and are scored under v0.2.2 only after the Lab decision. v0.2.1 remains separately pending.
