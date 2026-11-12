# C-T2 judge report: Black 2026, Table 2

## Verdict

**C-T2: PASS under the contract's script rule, with one paper mismatch reported.**

- (a) Converged count k matches the published count in all 13 cells.
- (b) All continuous metrics (mean peak modal, its sd, mean final modal, its sd, mean peak gini), rounded with the script's `.3f`, match the paper in all 13 cells.
- (c) Median t95, computed as the official script does (`int(np.median(converged))`), matches the script definition in all cells. t95 from the recomputed agreement equals t95 from the recorded series in all 104 trials.
- (d) Median t95 matches the paper integer in 12 of 13 cells. At gamma 2.00 the script gives 29 and the paper prints 30.

The C-T2 text lists 30 at gamma 2.00. Read literally, that one criterion fails in one cell. The contract says the script governs when it and the paper disagree. Under that rule this is a paper-vs-script mismatch to report, not a reproduction failure. If anyone reads line 76 of the contract as binding over the script rule, Mimetic Lab should decide. The judge records both: `verdict` = PASS (script rule) and `verdict_literal_paper_integers` = FAIL.

## Per-gamma comparison

Format: computed / paper. Peak and final are means with (sd). Script med = `int(np.median)`.

| gamma | k / pub k | script med t95 | np.median | paper med | peak modal | final modal | peak gini | CP 95% on k/8 |
|---|---|---|---|---|---|---|---|---|
| 0.75 | 0/8 / 0 | none | none | none | 0.125 (0.017) / 0.125 (0.017) | 0.098 (0.017) / 0.098 (0.017) | 0.100 / 0.100 | [0.000, 0.369] |
| 0.90 | 0/8 / 0 | none | none | none | 0.150 (0.020) / 0.150 (0.020) | 0.122 (0.027) / 0.122 (0.027) | 0.103 / 0.103 | [0.000, 0.369] |
| 0.95 | 0/8 / 0 | none | none | none | 0.172 (0.032) / 0.172 (0.032) | 0.136 (0.029) / 0.136 (0.029) | 0.104 / 0.104 | [0.000, 0.369] |
| 1.00 | 0/8 / 0 | none | none | none | 0.240 (0.074) / 0.240 (0.074) | 0.194 (0.057) / 0.194 (0.057) | 0.115 / 0.115 | [0.000, 0.369] |
| 1.01 | 0/8 / 0 | none | none | none | 0.305 (0.118) / 0.305 (0.118) | 0.218 (0.071) / 0.218 (0.071) | 0.132 / 0.132 | [0.000, 0.369] |
| 1.02 | 1/8 / 1 | 421 | 421.0 | 421 | 0.463 (0.260) / 0.463 (0.260) | 0.356 (0.221) / 0.356 (0.221) | 0.166 / 0.166 | [0.003, 0.527] |
| 1.05 | 8/8 / 8 | 116 | 116.5 | 116 | 0.980 (0.000) / same | 0.980 (0.000) / same | 0.810 / 0.810 | [0.631, 1.000] |
| 1.08 | 8/8 / 8 | 74 | 74.5 | 74 | 0.980 (0.000) / same | 0.980 (0.000) / same | 0.881 / 0.881 | [0.631, 1.000] |
| 1.10 | 8/8 / 8 | 62 | 62.0 | 62 | 0.980 (0.000) / same | 0.980 (0.000) / same | 0.906 / 0.906 | [0.631, 1.000] |
| 1.15 | 8/8 / 8 | 43 | 43.0 | 43 | 0.980 (0.000) / same | 0.980 (0.000) / same | 0.937 / 0.937 | [0.631, 1.000] |
| 1.25 | 8/8 / 8 | 30 | 30.5 | 30 | 0.980 (0.000) / same | 0.980 (0.000) / same | 0.959 / 0.959 | [0.631, 1.000] |
| 1.50 | 8/8 / 8 | 29 | 29.0 | 29 | 0.980 (0.000) / same | 0.980 (0.000) / same | 0.970 / 0.970 | [0.631, 1.000] |
| **2.00** | 8/8 / 8 | **29** | **29.5** | **30** | 0.980 (0.000) / same | 0.980 (0.000) / same | 0.972 / 0.972 | [0.631, 1.000] |

Clopper-Pearson intervals are reported only. They are not a fail condition.

## The gamma 2.00 median

- Raw t95 by seed (42, 1042, ..., 7042): 31, 20, 29, 30, 23, 30, 14, 42.
- Sorted: 14, 20, 23, 29, 30, 30, 31, 42. `np.median` = (29 + 30) / 2 = 29.5. `int()` truncates to 29. The pinned script prints 29.
- The paper prints 30. Python `round(29.5)` (half to even) gives 30.
- Four cells have a .5 median: 116.5, 74.5, 30.5, 29.5. Half-to-even rounding gives 116, 74, 30, 30, which matches the paper in all 13 cells. `int()` matches in 12 of 13. Half-up rounding (117, 75, 31, 30) would match only 10 of 13. The paper's medians fit a `round()` step, but `reproduce_table_2.py` has always used `int(np.median(...))`: its only commit is the pinned SHA. This is an inference about how the paper number was made, not a finding.

## Recompute against the recorded series

- Agreement recomputed from `eligible_ids` and `top_targets` at all 62,400 steps (104 x 600): max abs diff from recorded `modal_agreement` = 0.0.
- Modal target ties are broken as in official `record_metrics`: counts are built in eligible-agent order and `max(counts, key=counts.get)` picks the first target seen. Recomputed modal target equals recorded `modal_target_id` at every step (0 mismatches). The agreement value does not depend on how ties are broken.
- `system_tension` vs the sum of `received_aggression`: max relative diff 0.0.
- Gini recomputed from `received_aggression` with the official `_gini` formula: max abs diff 0.0.
- `eligible_count` equals the length of `eligible_ids` everywhere. No agent targets itself.

## Schema and metadata

No issues. 104 trial files, matching `manifest.trial_ids`, 13 cells of 8. Seeds 42 + r x 1000, r = 0..7. Every trial has contract_version 0.2, source_sha 89e7bbb57db62e3c830a8ca672a0805080df3970 (the clone is at that HEAD), script reproduce_table_2.py, AC with object source and attention spread, N 50, k 6, rewire 0.15, alpha 0.15, aggression_decay 0.03, expulsion_mode none, expulsion_threshold null, 600 steps planned and completed, timed_out false, viability and viability_D7_paper null, empty event lists, all series length 600, t = 0..599, n_alive 50 throughout. `packages.scipy` = "not installed" in every trial and in the manifest. This is reported, not a failure.

## Assumptions

- Eligibility (sum of aggression from i to others >= 1e-8) is taken from the recorded `eligible_ids`. Traces do not include the raw aggression matrix, so the eligibility cutoff itself was not recomputed.
- Peak gini uses the recorded `aggression_gini`. It was cross-checked exactly against a recompute.
- Rounding uses `f"{x:.3f}"`, the same as the script's print. Several means sit exactly on a .xxx5 boundary (0.1725, 0.4625, 0.12175, 0.21795, 0.35585). Their 3-decimal result depends on binary floating point, the same as in the script. All of them match the paper.
- Clopper-Pearson is exact: bisection on the binomial CDF, which is equivalent to beta quantiles. It does not need scipy.
- Only the trial files, the manifest, and the official code and paper definitions were used. The summary file was not opened.

## Files

- Judge: `eval/judge/judge_table2.py` (`python3 eval/judge/judge_table2.py [TRACE_DIR] [OUT_JSON]`, deterministic, two runs gave identical output)
- Results: `eval/judge/table2-result.json` (also has per-trial values and SHA-256 hashes of each trial file)
- This report: `eval/judge/table2-report.md`
- Traces scored: `/workspace/mimetic-lab/eval/traces/v0.2/table2` on the shared box (not in this commit; to be archived with Git LFS)
