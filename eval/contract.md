# Evaluation contract v0.2

Mimetic Proofs and Mimetic Simulation. Source of truth: public repo [weklund/mimetic-lab](https://github.com/weklund/mimetic-lab).

A pass is evidence that a specified model, under stated assumptions and a pinned source SHA, exhibits a specified property. It is not a proof that Girard's anthropology is true, and it is not a verdict on Girard.

## Roles

- Mimetic Simulation produces traces and runs experiments. It does not score official contract traces.
- Mimetic Proofs owns properties, pass/fail criteria, and statistical confidence bounds, and judges traces.
- If the two disagree on what counts as a pass, both stop and let Mimetic Lab decide.
- Neither invents new philosophical claims. Thresholds and predicates come from published code and from Black 2026 `paper_draft_18.md`, not from new numbers.

## Source

Maxwell Black, "A Computational Test of Girard's Scapegoat Mechanism" (2026), `paper_draft_18.md`, and `girard_2x2_v3.py` / `small_n_utils.py`, from [maxwell-black/mimetic-desire-simulation](https://github.com/maxwell-black/mimetic-desire-simulation). Official first-milestone runs use the published `reproduce_*.py` and viability scripts, built-in seeds (`42 + r * 1000`), and do not modify published source. Wrappers, harness, and exports live in `weklund/mimetic-lab`.

Every ensemble names the full git SHA actually run. Predicates are those of that SHA.

## Operational rule for paper-versus-code mismatches

When prose and the script that produced a table disagree, reproduction of that table uses the script. The mismatch is reported, not silently "fixed." A prose-only variant may be scored only as a separately labeled predicate, never as the Table-N reproduction.

Known mismatches at v0.2:

1. Section 3.11.2 says genuine self-exhaustion is "no expulsions for the final 2000+ steps." `classify_exhaustion` in `small_n_utils.py` uses `min_silence=500` (no reconvergence to the adaptive threshold, and at least 500 steps after the last expulsion). Table 10 was produced by `exp_small_n_viability.py`, so **C-T10 uses `min_silence=500`**. A 2000-step silence predicate, if scored, is labeled `D7-prose` and is not used to pass or fail Table 10.
2. Table 11's caption says convergence is modal agreement >= 0.95, but `exp_small_n_phase_boundary.py` uses `adaptive_unanimity_threshold(N)` sustained for 10 steps. **C-T11 uses the script.** At N >= 20 the two coincide; at N < 20 they do not (at N=5 the ceiling is 0.80, so 0.95 is impossible).

## Definitions

**D1. Modal-target agreement** (Black Sections 2.3, 2.4; `record_metrics` / `get_modal_target`).

- T_i = argmax_j A_i(j), self-targeting excluded.
- Living set L_t. Eligible set A_t = {i in L_t : sum_j A_i(j) >= 10^{-8}} (code uses `>= 1e-8`; Simulation's write-up said `>`). The judge uses the code: `>= 1e-8`.
- Modal target t* = mode({T_i : i in A_t}).
- Agreement = |{i in A_t : T_i = t*}| / |A_t|, or 0 if A_t is empty.
- Ceiling is (N-1)/N. The eventual victim is still in L_t (and may vote in A_t) at the instant agreement is measured; they are the modal target, not excluded from the agent set. After expulsion they leave L_t.

**D2. Converged, no-expulsion phase boundary** (Tables 2, 2b; Sections 2.3, 3.2). `time_to_95`: t95 is the first t such that agreement[t+k] >= 0.95 for all k in 0..9; else null. A trial converged iff t95 is not null. T = 10 is published. The series is recorded at the end of each step, length = steps completed.

**D3. Converged, small-N phase boundary** (Table 11). Same as D2, but the threshold is `adaptive_unanimity_threshold(N) = min(0.95, (N-1)/N)` for N > 1, else 1.0, sustained 10 consecutive steps.

**D4. Table 2 summary stats.** Peak modal = max(agreement). Final modal = mean of the last 50 agreement values. Peak gini = max(aggression_gini). Median t95 is the median of t95 over converged trials only.

**D5. System tension.** M_t = sum_v R(v), total received aggression over living agents (code: `system_tension`). This is not called tau. In Black, tau is the expulsion threshold on received aggression R(v*), default 8.0 (Table 1, Appendix C.7), a trigger, not the tension measure.

**D6. Immediate catharsis** (Table 1 caption, Section 3.5, `catharsis_events`). For an expulsion at step t, fractional_drop = (M_{t-} - M_{t+}) / M_{t-} after zeroing aggression to and from the expelled agent, or 0 if M_{t-} = 0 (code also floors at 0). Horizon k = 0 (immediate). There is no published multi-step k, and this contract does not invent one. For the unanimity-triggered runner, which bypasses `step_expulsion`, the wrapper must compute D6 the same way.

**D7. Generative founding murder** (Table 10 operational definition). A trial is generative iff all three hold, using official `classify_exhaustion` with `min_silence=500`:

1. status == `genuine_exhaustion` (no reconvergence to the adaptive threshold after the last expulsion, and at least 500 remaining steps),
2. pct_consumed < 0.50,
3. n_expulsions >= 1.

Cooldown is 5. Trigger is Use 2 below. **D7-prose** replaces (1) with "no expulsions in the final 2000+ steps" and is not the Table 10 predicate.

A **trial** is one seeded run: the tuple (script, variant, N, gamma, seed).

## Properties

**P-conv (unanimous polarization / Black convergence).** Single-trial predicate is D2 or D3, according to the ensemble. This is Black's published convergence claim about hostility targeting. Sack Def. 2 (obj(i) = obj(med(i))) is not applied to Black traces in this milestone and is not mapped into one. A Sack analogue, if added later, will be a separately labeled property.

Two published uses of D1:

- Use 1, convergence: D2, usually with expulsion disabled (Tables 2, 2b).
- Use 2, unanimity-triggered expulsion (Sections 3.8, 3.11.1): expulsion fires when agreement >= theta, 5-step cooldown. For N >= 20, theta = 0.95. For smaller N, theta(N) = min(0.95, (N-1)/N). This is the trigger for Table 10 and violence-topology tables, not a post-hoc pass on those traces (at a trigger instant the inequality holds by construction).

**P-drop (tension drop after victimization).** Applies only to traces with at least one expulsion. Table 2 and 2b have expulsion disabled, so P-drop is N/A there. Immediate: D6, k = 0. There is no single invented pass delta. Ensemble targets, when reproducing those tables, are the published means: Table 1 (10 runs, gamma=2.0, tau=8.0, 600 steps) mean catharsis LM 5.6%, AC 29.6%, RL 6.3%, RA 36.7%; Section 3.6 Regime 2 (tau=500): "total system tension collapses by roughly 95%." Table 4 peace is a different metric (consecutive steps with agreement < 0.50 after the first expulsion; median 17 steps at tau=500) and is reported separately, not as P-drop.

**P-gen (generative founding murder).** Single-trial: D7.

## Ensemble claims (first milestone)

Official seeds: `42 + r * 1000`. Variant is AC unless noted. Reproduction pass is a match to the published table as specified below, not a new population-rate test.

**C-T2 (reproduce Table 2).** Script `reproduce_table_2.py`: AC, N=50, k=6, p=0.15, alpha=0.15, no expulsion, 8 runs, 600 steps, gammas [0.75, 0.90, 0.95, 1.00, 1.01, 1.02, 1.05, 1.08, 1.10, 1.15, 1.25, 1.50, 2.00]. Pass iff for every gamma: converged count k equals the published count (0 for gamma <= 1.01; 1 for 1.02; 8 for gamma >= 1.05); median t95 among converged, when published, equals the published integer (421 at 1.02; then 116, 74, 62, 43, 30, 29, 30); mean peak modal, mean final modal, their sds, and mean peak gini match after rounding to the printed 3 decimals. This table has no 1.03 row and locates the N=50 boundary in [1.02, 1.05].

**C-T2b (reproduce Table 2b; first target for the [1.02, 1.03] and sharpening claims).** Script `reproduce_table_2b.py`: AC, no expulsion, 20 runs, 800 steps, gammas [1.01, 1.02, 1.03, 1.04, 1.05], N in [50, 100, 200], k = max(6, min(int(N*0.12), 20)) forced even (k=6, 12, 20). Pass iff converged counts match published rates exactly:

- N=50: 0% at 1.01, 10% (2/20) at 1.02, 90% (18/20) at 1.03, 100% (20/20) at >= 1.04.
- N=100 and N=200: 0% at <= 1.02, 100% at >= 1.03.

Sharpening passes if that pattern holds (fuzzy interval at N=50, step between 1.02 and 1.03 at N >= 100). Also check published median t95 at gamma=1.05: 88, 98, 102 for N=50, 100, 200. Table 2b as printed stops at N=200. The README and Section 3.11.3 mention N=500; that is a separate run to confirm, not numbers already in Table 2b. C-T2b is the first ensemble target for the invariant-boundary claim, not C-T2.

**C-T10 (reproduce Table 10).** Script `exp_small_n_viability.py`: AC and RA, N in {5, 10, 15, 20, 25, 30, 35, 40}, gamma in {1.05, 1.5, 2.0}, 20 seeds, 5000 steps, Use 2, cooldown 5. Viability index = fraction of trials satisfying D7. Pass iff each cell, as k/20, matches the published percent:

- AC 1.05: 25, 75, 65, 90, 95, 85, 85, 90
- AC 1.50: 0, 0, 55, 60, 90, 85, 95, 95
- AC 2.00: 0, 5, 50, 65, 85, 70, 90, 80
- RA 1.05: 0, 25, 85, 85, 60, 80, 90, 80
- RA 1.50: 0, 0, 25, 65, 80, 85, 100, 90
- RA 2.00: 0, 0, 30, 75, 80, 95, 90, 65

The qualitative "generative window around N=15 to 50" is described only after these cells match, without new claims. Table 10 stops at N=40. Section 3.9 / Table 8 at N=50 uses a different protocol (threshold-triggered, tau=8, 10,000 steps) and is not pooled with Table 10. Linear controls (LM, RL) are reported if exported; the paper says they produce zero expulsions at N >= 15.

**C-T11 (small-N phase boundary, if run).** Script `exp_small_n_phase_boundary.py`, D3. gamma-star = lowest tested gamma with >= 50% convergence. Published: N=5..40, gamma-star 1.03, 1.03, 1.05, 1.04, 1.03, 1.03, 1.03, 1.03, paper range [1.03, 1.05].

**C-inv-full (phase boundary invariant for N=5 to 500).** Composite: C-T11 for N=5 to 40, C-T2b for N=50 to 200, and a named official no-expulsion sweep for N=500 if and when Simulation runs it. C-T2b alone is not a pass on N=5 to 500.

**C-T1 (catharsis means, if run).** Table 1, 10 runs, gamma=2.0, tau=8.0, 600 steps. Ensemble mean fractional_drop (D6) matches published LM 5.6%, AC 29.6%, RL 6.3%, RA 36.7% after rounding to the printed 1 decimal. Not part of the Table 2 / 2b first delivery.

## Statistics

For every ensemble cell the judge reports k, n, the rate, and a 95% Clopper-Pearson confidence interval. That interval is a report, not an extra fail condition.

Official n is 8 or 20. Even 8/8 has a 95% lower bound around 0.63. This contract does **not** fail a reproduction because that lower bound is below a p*. There is no p* on these official published sample sizes. Reproduction pass is match to the published table, as above. A p* rule (CI lower bound >= p*) will be pre-registered only for a later, larger, pre-registered ensemble, never set after looking at official n=8 or n=20 results.

## Trace schema

One trial file plus an ensemble manifest. JSON metadata and events; per-step arrays may live in the same JSON or in a sibling NPZ. UTF-8 JSON, no NaN or Infinity (use null). Published source is not edited. Wrappers live in this repo.

Layout:

```
eval/traces/v0.2/
  <ensemble_id>/          # e.g. table2, table2b, table10, table11, table1
    manifest.json
    trials/<trial_id>.json
    trials/<trial_id>.npz   # optional, if series are not inline
eval/summaries/<ensemble_id>.json   # optional claimed-vs-reproduced notes
```

`trial_id` = `{ensemble_id}-g{gamma}-N{N}-v{variant}-s{seed}`.

**manifest.json**

- contract_version: `"0.2"`
- ensemble_id, paper (`Black 2026, A Computational Test of Girard's Scapegoat Mechanism`), draft (`18`)
- source_repo, source_sha (full SHA actually run)
- script, python_version, packages (numpy, networkx, scipy at least)
- command, started_at, ended_at (ISO-8601)
- trial_ids: list
- For each trial or in a `cells` list: table, N, gamma, variant, n, claimed_k or claimed_rate, so the judge can attach a Clopper-Pearson interval to the published cell

**trial JSON, required metadata**

- contract_version, trial_id, ensemble_id, script, source_sha, draft
- variant (`LM` | `AC` | `RL` | `RA`), source_mode (`object` | `status`), spread_mode (`linear` | `attention`)
- N, k, rewire_prob, alpha, gamma, aggression_decay
- expulsion_mode (`none` | `threshold` | `unanimity_adaptive`)
- expulsion_threshold (null if none), unanimity_threshold (null if none), unanimity_cooldown (null if none)
- n_steps_planned, steps_completed, seed, timed_out
- python_version, packages, command, started_at, ended_at

**Per-step arrays** (length = steps_completed; enough for Proofs to recompute D1 and D2 independently). Field names may be either the code names or the names below; the manifest or trial must be consistent, and the judge accepts this mapping:

| Contract name | Code / Simulation name | Content |
| --- | --- | --- |
| modal_agreement | modal_agreement | D1 |
| eligible_agents | eligible_count | \|A_t\| |
| eligible_ids | eligible_ids | ids in A_t (optional but useful) |
| top_targets | T_i per eligible agent | enough to recompute the mode |
| system_tension | M, system_tension | D5 |
| n_active_agents | n_alive | \|L_t\| |
| alive_ids | alive_ids | ids in L_t |
| received_aggression | R(v) for each living v | enough to recompute M and D6 |
| aggression_gini | aggression_gini | |
| aggression_max_share | top_target_share | |
| convergence_ratio | convergence_ratio | |
| aggression_entropy | aggression_entropy | |
| top_target_aggression | top_R | |
| mean_aggression | mean_R | |
| modal_target_id | | optional |

Full N by N aggression, and desire vectors, are not required for this milestone. If a later Sack analogue needs them, they will be requested on a subset.

If arrays are in a sibling NPZ, the JSON has `"series": {"$npz": "<trial_id>.npz"}` with the same array names. Metadata and events stay in the JSON. Prefer all-JSON when small (Table 2 will be).

**Events**

- expulsion_events: list of {step, victim_id, received_aggression} (t, victim_id, R(v*))
- catharsis_events: list of {step, victim_id, M_pre, M_post, fractional_drop} where fractional_drop is D6 (M_pre and M_post are system tension before and after zeroing, not the expulsion threshold)

For Table 2 / 2b, both lists are empty and `viability` is null.

**viability** (required for Table 10 and other unanimity-triggered runs), official fields:

- n_expulsions, pct_consumed, n_alive, status, self_exhausted, first_peace, first_reconverge, peak_modal, n_fragments, largest_fragment, expulsion_steps, med_gap

`status` is exactly one of: `genuine_exhaustion`, `still_cycling`, `censored`, `no_expulsions`, `timeout`.

## Judge

Mimetic Proofs runs the judge on the exported files and returns, per claim, pass or fail, the per-cell k and published k, rounded continuous metrics versus published values, and 95% Clopper-Pearson intervals as a report. Simulation may include claimed-vs-reproduced numbers in `eval/summaries/` for its own report; those are not the official score.
