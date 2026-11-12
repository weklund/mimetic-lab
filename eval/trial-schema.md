# Evaluation contract v0.2: complete trial and manifest schema

This is the rest of the per-trial object. Implement from this document. Layout `eval/traces/v0.2/` is preferred; `eval/traces/v0.1/` is accepted if already in use. UTF-8 JSON, no NaN or Infinity (use `null`). Do not pre-score.

`trial_id` = `{ensemble_id}-g{gamma}-N{N}-v{variant}-s{seed}`

Example: `table2-g1.02-N50-vAC-s42`

Gamma in the id may use the decimal form without trailing zeros beyond what is needed (1.02, 1.5, 2.0). Be consistent within an ensemble.

## Directory layout

```
eval/traces/v0.2/
  <ensemble_id>/
    manifest.json
    trials/<trial_id>.json
    trials/<trial_id>.npz    # optional; only if series are not inline
```

## manifest.json (required)

```json
{
  "contract_version": "0.2",
  "ensemble_id": "table2",
  "paper": "Black 2026, A Computational Test of Girard's Scapegoat Mechanism",
  "draft": "18",
  "source_repo": "https://github.com/maxwell-black/mimetic-desire-simulation",
  "source_sha": "<full 40-char SHA actually run>",
  "script": "reproduce_table_2.py",
  "python_version": "3.12.x",
  "packages": {"numpy": "x.y.z", "networkx": "x.y.z", "scipy": "x.y.z"},
  "command": "<exact command>",
  "started_at": "2026-11-11T19:00:00-05:00",
  "ended_at": "2026-11-11T19:20:00-05:00",
  "trial_ids": ["table2-g1.02-N50-vAC-s42"],
  "cells": [
    {
      "table": "2",
      "N": 50,
      "gamma": 1.02,
      "variant": "AC",
      "n": 8,
      "claimed_k": 1,
      "claimed_rate": 0.125,
      "claimed_median_t95": 421,
      "trial_ids": ["table2-g1.02-N50-vAC-s42"]
    }
  ]
}
```

`cells` is required. Each cell is one published (table, N, gamma, variant) group. `claimed_k` is the published converged or generative count. `claimed_rate` is `claimed_k / n`. `claimed_median_t95` is required when the paper prints it, else `null`. `trial_ids` on a cell lists the trials that belong to it.

## Trial JSON: required metadata

Every field below is required. Use `null` where a field does not apply (never omit the key).

| Field | Type | Notes |
| --- | --- | --- |
| contract_version | string | `"0.2"` |
| trial_id | string | as above |
| ensemble_id | string | `table2`, `table2b`, `table10`, `table11`, `table1`, or a clearly labeled extension id |
| script | string | published script name |
| source_repo | string | URL |
| source_sha | string | full SHA actually run |
| paper | string | as in the manifest |
| draft | string | `"18"` |
| variant | string | `LM` \| `AC` \| `RL` \| `RA` |
| source_mode | string | `object` \| `status` |
| spread_mode | string | `linear` \| `attention` |
| N | int | |
| k | int | mean degree |
| rewire_prob | number | |
| alpha | number | |
| gamma | number | |
| aggression_decay | number | |
| expulsion_mode | string | `none` \| `threshold` \| `unanimity_adaptive` |
| expulsion_threshold | number or null | Black's tau; null if not threshold mode |
| unanimity_threshold | number or null | Use-2 theta actually applied; null if expulsion_mode is not `unanimity_adaptive` |
| unanimity_cooldown | int or null | 5 when used, else null |
| n_steps_planned | int | |
| steps_completed | int | length of every 1-d series |
| seed | int | official: `42 + r * 1000` |
| timed_out | bool | |
| python_version | string | |
| packages | object | at least numpy, networkx, scipy, versions as strings |
| command | string | |
| started_at | string | ISO-8601 with offset |
| ended_at | string | ISO-8601 with offset |

Official `VARIANT_MAP` in `girard_2x2_v3.py`: LM = (`object`, `linear`), AC = (`object`, `attention`), RL = (`status`, `linear`), RA = (`status`, `attention`). `source_mode` and `spread_mode` must match this map for the stated variant. AC is object plus attention, not status.

## Trial JSON: series (required, unless offloaded to NPZ)

If series are inline, the trial has a `"series"` object whose arrays are JSON lists. If offloaded, `"series": {"$npz": "<trial_id>.npz"}` and the NPZ uses the same array names. Metadata and events always stay in the JSON. Prefer inline JSON for Table 2 (small).

All 1-d arrays have length `steps_completed`. `t[i]` is the completed-step index as the official runner records it (0-based: `t[0] == 0` after the first completed step). Nested lists are aligned as follows.

| Name | Shape | Required | Content |
| --- | --- | --- | --- |
| t | [T] int | yes | step index |
| n_alive | [T] int | yes | \|L_t\| |
| alive_ids | [T][n_alive[t]] int | yes | ids in L_t, stable order within a step |
| system_tension | [T] number | yes | M_t = sum_v R(v) over living agents |
| modal_agreement | [T] number | yes | D1 |
| eligible_count | [T] int | yes | \|A_t\| |
| eligible_ids | [T][eligible_count[t]] int | yes | ids in A_t, same order as top_targets |
| top_targets | [T][eligible_count[t]] int | yes | T_i for eligible_ids[t][i]; self-targeting excluded |
| received_aggression | [T][n_alive[t]] number | yes | R(v) for alive_ids[t][i]; enough to recompute M and D6 |
| aggression_gini | [T] number | yes | |
| top_target_share | [T] number | yes | also called aggression_max_share |
| convergence_ratio | [T] number | yes | as the official `record_metrics` writes it |
| aggression_entropy | [T] number | yes | |
| top_R | [T] number | yes | max received aggression among living |
| mean_R | [T] number | yes | mean received aggression among living |
| modal_target_id | [T] int or null | optional | t* at that step; null if A_t is empty |

Eligible cutoff is the code: agent i is eligible iff sum_j A_i(j) >= 1e-8, j living, self excluded.

Full N by N aggression and desire vectors are not required this milestone.

## Trial JSON: events (required keys, may be empty lists)

`expulsion_events`: list of objects, one per expulsion, in time order.

```json
{"step": 117, "victim_id": 4, "received_aggression": 8.31}
```

All three fields required. `step` is the same index as `t`. `received_aggression` is R(v*) at expulsion, before zeroing.

`catharsis_events`: list of objects, one per expulsion, same order.

```json
{"step": 117, "victim_id": 4, "M_pre": 40.0, "M_post": 28.16, "fractional_drop": 0.296}
```

All five fields required when the list is nonempty. `M_pre` and `M_post` are system tension before and after zeroing aggression to and from the expelled agent (D6). They are not the expulsion threshold. `fractional_drop = (M_pre - M_post) / M_pre`, or 0 if M_pre == 0 (code also floors at 0). Horizon k = 0 only. For unanimity-triggered runs that bypass `step_expulsion`, compute this the same way `step_expulsion` does (post-decay, pre- vs post-zeroing).

For Table 2 and 2b, both lists are `[]`.

## Trial JSON: viability (required key)

For Table 2, 2b, and other no-expulsion ensembles: `"viability": null` and `"viability_D7_paper": null`.

For Table 10 and other unanimity-triggered ensembles, both objects are required.

`viability` is the official Table 10 object, `classify_exhaustion` with `min_silence=500`. This is the only object used to pass or fail C-T10.

```json
{
  "min_silence": 500,
  "predicate": "D7",
  "n_expulsions": 3,
  "pct_consumed": 0.2,
  "n_alive": 16,
  "status": "genuine_exhaustion",
  "self_exhausted": true,
  "generative": true,
  "first_peace": 2100,
  "first_reconverge": null,
  "peak_modal": 0.97,
  "n_fragments": 1,
  "largest_fragment": 16,
  "expulsion_steps": [400, 900, 1500],
  "med_gap": 500
}
```

`status` is exactly one of: `genuine_exhaustion`, `still_cycling`, `censored`, `no_expulsions`, `timeout`.

`generative` is true iff D7 holds: `status == "genuine_exhaustion"` AND `pct_consumed < 0.50` AND `n_expulsions >= 1`. The judge will recompute `generative` from the other fields and the series; include it as a convenience, not as the official score.

`viability_D7_paper` has the same fields, with `"min_silence": 2000` and `"predicate": "D7-paper"`. Same D7 conditions otherwise. This is a labeled report of the section 3.11.2 wording. It is never used to pass or fail C-T10. Do not name it in a way that can be read as a change to C-T10.

Integer fields that do not occur (`first_peace`, `first_reconverge`, `med_gap`) are `null`.

## Complete example (toy, 3 steps, N=5, no expulsion)

A real Table 2 trial has N=50 and 600 steps; only the lengths change. This object is complete, not abbreviated.

```json
{
  "contract_version": "0.2",
  "trial_id": "table2-g1.02-N5-vAC-s42",
  "ensemble_id": "table2",
  "script": "reproduce_table_2.py",
  "source_repo": "https://github.com/maxwell-black/mimetic-desire-simulation",
  "source_sha": "89e7bbb57db62e3c830a8ca672a0805080df3970",
  "paper": "Black 2026, A Computational Test of Girard's Scapegoat Mechanism",
  "draft": "18",
  "variant": "AC",
  "source_mode": "object",
  "spread_mode": "attention",
  "N": 5,
  "k": 2,
  "rewire_prob": 0.15,
  "alpha": 0.15,
  "gamma": 1.02,
  "aggression_decay": 0.02,
  "expulsion_mode": "none",
  "expulsion_threshold": null,
  "unanimity_threshold": null,
  "unanimity_cooldown": null,
  "n_steps_planned": 3,
  "steps_completed": 3,
  "seed": 42,
  "timed_out": false,
  "python_version": "3.12.0",
  "packages": {"numpy": "2.0.0", "networkx": "3.3", "scipy": "1.14.0"},
  "command": "python reproduce_table_2.py",
  "started_at": "2026-11-11T19:00:00-05:00",
  "ended_at": "2026-11-11T19:00:01-05:00",
  "series": {
    "t": [0, 1, 2],
    "n_alive": [5, 5, 5],
    "alive_ids": [[0, 1, 2, 3, 4], [0, 1, 2, 3, 4], [0, 1, 2, 3, 4]],
    "system_tension": [1.0, 1.2, 1.5],
    "modal_agreement": [0.4, 0.6, 0.8],
    "eligible_count": [5, 5, 5],
    "eligible_ids": [[0, 1, 2, 3, 4], [0, 1, 2, 3, 4], [0, 1, 2, 3, 4]],
    "top_targets": [[1, 0, 0, 0, 0], [1, 0, 0, 0, 1], [1, 0, 0, 0, 0]],
    "received_aggression": [[0.5, 0.2, 0.1, 0.1, 0.1], [0.6, 0.2, 0.15, 0.15, 0.1], [0.8, 0.2, 0.2, 0.15, 0.15]],
    "aggression_gini": [0.2, 0.25, 0.3],
    "top_target_share": [0.5, 0.5, 0.53],
    "convergence_ratio": [0.4, 0.6, 0.8],
    "aggression_entropy": [1.4, 1.3, 1.2],
    "top_R": [0.5, 0.6, 0.8],
    "mean_R": [0.2, 0.24, 0.3],
    "modal_target_id": [0, 0, 0]
  },
  "expulsion_events": [],
  "catharsis_events": [],
  "viability": null,
  "viability_D7_paper": null
}
```

The numbers in this toy are illustrative, not published results. It is not a real AC trial and must not be copied as one. Official VARIANT_MAP: LM = (object, linear), AC = (object, attention), RL = (status, linear), RA = (status, attention). Real Table 2 trials use official GirardConfig (N=50, k=6, rewire_prob=0.15, alpha=0.15, aggression_decay=0.03, 600 steps) and the SHA actually run. The toy's N=5, 3 steps, and aggression_decay 0.02 are labeled illustration only.

## NPZ offload (optional)

When `"series": {"$npz": "<trial_id>.npz"}`:

- 1-d arrays are numeric (int64 or float64).
- Nested lists are saved as object arrays of 1-d arrays, or as two parallel arrays plus an offset/indptr (CSR-style) if you prefer; if you use offsets, also include a `"series_npz_layout"` string in the JSON (`"object"` or `"csr"`) and document the names. Prefer object arrays of 1-d arrays, names matching the table above.
- Do not put metadata or events in the NPZ.

## What the judge recomputes

From `eligible_ids`, `top_targets`, `n_alive`, and `modal_agreement`, the judge recomputes D1 and D2/D3 (T=10). From `received_aggression`, `alive_ids`, `system_tension`, and catharsis/expulsion events, it recomputes D5 and D6. From `viability` it evaluates D7 for C-T10, and from `viability_D7_paper` it reports D7-paper only. Simulation's own summaries, if present, are not the official score.
