# Judges

Official scorers for the evaluation contract ([`../contract.md`](../contract.md)). Mimetic Proofs runs them; Simulation does not score official traces.

| File | What it is |
|---|---|
| `judge_table2.py` | Official C-T2 judge (Table 2), contract v0.2.1 |
| `table2-result.json`, `table2-report.md` | The recorded C-T2 run (judge v0.2, traces on the shared box; see the report) |
| `rescore_from_result.py` | Not a judge. Re-applies the v0.2.1 cell rules to per-trial values recorded in a result file |
| `check_trace_hashes.py` | Confirms archived trial files are byte-identical to the ones a recorded run scored |
| `black_reference.py` | Test helper: loads Black's official metric code from a checkout at the pinned SHA |
| `test_judge.py`, `test_against_official.py` | Tests (below) |

## Running

```bash
python3 eval/judge/judge_table2.py eval/traces/v0.2/table2 eval/judge/table2-result.json
```

Exit status 0 means PASS, 1 means FAIL. The judge fails closed: a missing file, malformed trace, non-finite number, or internal error is a FAIL, never a crash, and the result file is replaced atomically so an earlier PASS cannot survive.

## Result format

The result file is strict JSON (no NaN or Infinity). Fields other tools may rely on:

| Field | Meaning |
|---|---|
| `verdict` | `"PASS"` or `"FAIL"` |
| `provisional` | List of reasons the verdict cannot be official yet (for example, no saved script stdout). Empty when every comparison ran. |
| `checks` | `a_k_matches_published_all_cells`, `b_continuous_consistent_with_paper_all_cells`, `c_t95_recomputed_matches_recorded_series`, `d_med_t95_consistent_with_paper_all_cells`, `e_matches_script_output_all_cells` (`null` when no stdout was saved), `no_issues`, and the maximum recompute discrepancies |
| `legacy_checks_v0_2` | The v0.2 literal checks, kept for the record. Not part of the verdict. |
| `cells` | One object per published row: `gamma`, `k`, `published_k`, `cell_pass`, `checks`, medians under each rounding rule, computed and published values, `expected_script_row`, `script_row_diff`, Clopper-Pearson interval (report only), and per-trial values |
| `issues` | List of `{code, where, t, detail}`. `code` is stable and listed below; `where` is the trial id or null; `t` is the step or null; `detail` is human-readable and may change wording. |
| `paper_vs_script_notes` | Reported paper-versus-script differences (known mismatch 3) |
| `trial_file_sha256` | SHA-256 of every trial file read |
| `fatal_error` | Present only when the judge could not run |

A PASS requires every cell to pass and `issues` to be empty.

## Issue codes

| Code | Contract clause | Raised when |
|---|---|---|
| `fatal` | Judge | The judge could not run (missing file, unreadable input, internal error) |
| `manifest.field` | Trace schema, manifest | A manifest field is missing or wrong (contract version, source SHA, cells) |
| `ensemble.trial_files` | Trace schema, layout | Trial files on disk do not match the expected count or `manifest.trial_ids` |
| `ensemble.seeds` | C-T2 | A cell does not have exactly the official seeds |
| `trial.json` | Trace schema | A trial file is not strict JSON (NaN, Infinity, or a literal such as `1e309`) |
| `trial.metadata` | C-T2, trial metadata | A metadata field is missing or differs from the C-T2 configuration |
| `series.shape` | Trace schema, series | A required series is missing, not a list, of the wrong length, or has wrong element types |
| `series.t` | Trace schema, series | `series.t` is not `0..n_steps-1` |
| `ids.alive_count` | Trace schema, series | `len(alive_ids[t]) != n_alive[t]`, or `n_alive` differs from N in a no-expulsion run |
| `ids.alive_duplicate` | Trace schema, series | `alive_ids[t]` repeats an id |
| `ids.alive_outside_population` | Trace schema, series | `alive_ids[t]` has an id outside `0..N-1` |
| `ids.eligible_count` | D1 | `len(eligible_ids[t]) != eligible_count[t]` |
| `ids.eligible_duplicate` | D1 | `eligible_ids[t]` repeats an id |
| `ids.eligible_not_alive` | D1 | `eligible_ids[t]` has an id not in `alive_ids[t]` |
| `ids.target_not_alive` | D1 | `top_targets[t]` has a target not in `alive_ids[t]` |
| `ids.self_target` | D1 | An eligible agent's top target is itself |
| `align.received_aggression` | D5 | `received_aggression[t]` is not aligned with `alive_ids[t]` |
| `align.targets` | D1 | `eligible_ids[t]` and `top_targets[t]` differ in length |
| `D1.agreement` | D1 | Recorded `modal_agreement` differs from agreement recomputed from `top_targets` |
| `D1.modal_target_id` | D1 | Recorded `modal_target_id` differs from the first-seen modal target |
| `D2.t95_series` | D2 | t95 from recomputed agreement differs from t95 of the recorded series |
| `D5.tension` | D5 | Recorded `system_tension` differs from `sum(received_aggression)` |
| `gini.series` | D4 | Recorded `aggression_gini` differs from the official gini of `received_aggression` |
| `script.stdout` | C-T2, script reference | The saved script stdout is missing, fails its SHA-256, or lacks a row |
| `script.row` | C-T2, script reference | A printed row of the unmodified script differs from the judge's recomputation |
| `v022.incomplete` | v0.2.2 incomplete trials | An incomplete trial (timed_out or steps_completed != n_steps_planned) after allowed rerun |
| `v022.multiple_reruns` | v0.2.2 rerun limit | More than one labeled rerun for the same seed |
| `v022.determinism` | v0.2.2 determinism check | Incomplete trial's per-step arrays do not match the completed rerun's prefix |
| `viability.evidence` | C-T10, D7 | A `viability` field disagrees with what the trial's own series and `expulsion_events` give: the official Use 2 trigger replayed on `modal_agreement`, the living set after each expulsion, `n_expulsions`, `n_alive`, `pct_consumed`, or official `classify_exhaustion` (`min_silence=500`). The cell counts a seed as viable only from this recomputation. |

## Tests

```bash
python3 -m unittest discover -s eval/judge -p 'test_*.py'
```

- `test_judge.py` builds a small ensemble that meets the contract and shows the judge PASSes it, then corrupts one thing at a time and shows each corruption FAILs with the issue code above. It also re-scores the recorded C-T2 per-trial values (all 13 cells pass under v0.2.1) and checks the schema's toy example. Tests assert on verdicts, `checks`, and issue codes, never on message wording.
- `test_against_official.py` runs the judge's `time_to_95`, agreement, and gini, and its stdout parser, against Black's own code at the pinned SHA on thousands of generated inputs, and checks that the schema's toy example is exactly what the official `record_metrics` writes. Nothing from Black's repository is copied here: point `BLACK_REPO` at a checkout of `maxwell-black/mimetic-desire-simulation` at `89e7bbb57db62e3c830a8ca672a0805080df3970`. The loader checks both files' SHA-256 before use. Without a checkout these tests skip; CI sets `REQUIRE_OFFICIAL=1` so they cannot skip there.

When you add a check to the judge, add its issue code here, a corruption test that triggers it, and make sure the valid-ensemble test still passes.
