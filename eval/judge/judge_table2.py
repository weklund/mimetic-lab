#!/usr/bin/env python3
"""Official C-T2 judge (eval contract v0.2.1): Black 2026 Table 2.

Scores ONLY from trial JSON files, manifest.json, and the unmodified script's saved
stdout. Deterministic, no network. Does not modify traces.

Fails closed: a missing file, a malformed trace, a non-finite number, or any
exception produces a FAIL result. The result is written atomically, so an earlier
PASS can never survive on disk next to a run that failed.

The result format and the issue codes are documented in eval/judge/README.md.

Usage:
    python3 judge_table2.py [TRACE_DIR] [OUT_JSON]

Exit status is 0 on PASS and 1 on FAIL.
"""
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field

import numpy as np

JUDGE_VERSION = "0.2.1"
CONTRACT = "eval contract v0.2.1, C-T2"
# Table 2 traces exported under v0.2 are valid v0.2.1 traces: v0.2.1 changed scoring
# rules and added optional manifest fields, not the Table 2 trial schema.
ACCEPTED_TRACE_VERSIONS = ("0.2", "0.2.1")

# Default traces live under the repo (often via Git LFS, not ordinary git blobs).
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", ".."))
_DEFAULT_TRACES = os.path.join(_REPO, "eval", "traces", "v0.2", "table2")
_DEFAULT_OUT = os.path.join(_HERE, "table2-result.json")

PINNED_SHA = "89e7bbb57db62e3c830a8ca672a0805080df3970"
GAMMAS = [0.75, 0.90, 0.95, 1.00, 1.01, 1.02, 1.05, 1.08, 1.10, 1.15, 1.25, 1.50, 2.00]
SEEDS = [42 + r * 1000 for r in range(8)]
N_STEPS = 600
N_AGENTS = 50
N_TRIALS = len(GAMMAS) * len(SEEDS)
# Published Table 2, paper_draft_18.md: (peak, peak_sd, final, final_sd, peak_gini, med_t95, k)
PUB = {
    0.75: (0.125, 0.017, 0.098, 0.017, 0.100, None, 0),
    0.90: (0.150, 0.020, 0.122, 0.027, 0.103, None, 0),
    0.95: (0.172, 0.032, 0.136, 0.029, 0.104, None, 0),
    1.00: (0.240, 0.074, 0.194, 0.057, 0.115, None, 0),
    1.01: (0.305, 0.118, 0.218, 0.071, 0.132, None, 0),
    1.02: (0.463, 0.260, 0.356, 0.221, 0.166, 421, 1),
    1.05: (0.980, 0.000, 0.980, 0.000, 0.810, 116, 8),
    1.08: (0.980, 0.000, 0.980, 0.000, 0.881, 74, 8),
    1.10: (0.980, 0.000, 0.980, 0.000, 0.906, 62, 8),
    1.15: (0.980, 0.000, 0.980, 0.000, 0.937, 43, 8),
    1.25: (0.980, 0.000, 0.980, 0.000, 0.959, 30, 8),
    1.50: (0.980, 0.000, 0.980, 0.000, 0.970, 29, 8),
    2.00: (0.980, 0.000, 0.980, 0.000, 0.972, 30, 8),
}
CONTINUOUS = ["peak_modal_mean", "peak_modal_sd", "final_modal_mean", "final_modal_sd", "peak_gini_mean"]
CONTINUOUS_DECIMALS = 3  # Table 2 prints means and sds to 3 decimals
MEDIAN_DECIMALS = 0      # Table 2 prints median t95 as an integer

# Tolerances for recomputing recorded series from their parts. The official traces agree
# exactly; these leave room for floating-point summation order.
TOL_MODAL = 1e-12
TOL_TENSION_REL = 1e-9  # relative to max(1, |recorded|)
TOL_GINI = 1e-9
MAX_ISSUES_PER_TRIAL = 20

# Every issue the judge can raise. Codes are stable; their wording in `detail` is not.
ISSUE_CODES = {
    "fatal": "The judge could not run (missing file, unreadable input, internal error).",
    "manifest.field": "A manifest field is missing or has the wrong value.",
    "ensemble.trial_files": "Trial files on disk do not match the expected count or manifest.trial_ids.",
    "ensemble.seeds": "A gamma cell does not have exactly the official seeds 42 + r*1000, r = 0..7.",
    "trial.json": "A trial file is not strict JSON (NaN, Infinity, or an overflowing literal).",
    "trial.metadata": "A trial metadata field is missing or differs from the C-T2 configuration.",
    "series.shape": "A required series is missing, not a list, of the wrong length, or has wrong element types.",
    "series.t": "series.t is not 0..N_STEPS-1.",
    "ids.alive_count": "len(alive_ids[t]) != n_alive[t], or n_alive differs from N in a no-expulsion run.",
    "ids.alive_duplicate": "alive_ids[t] repeats an id.",
    "ids.alive_outside_population": "alive_ids[t] has an id outside 0..N-1.",
    "ids.eligible_count": "len(eligible_ids[t]) != eligible_count[t].",
    "ids.eligible_duplicate": "eligible_ids[t] repeats an id.",
    "ids.eligible_not_alive": "eligible_ids[t] has an id not in alive_ids[t].",
    "ids.target_not_alive": "top_targets[t] has a target not in alive_ids[t].",
    "ids.self_target": "An eligible agent's top target is itself.",
    "align.received_aggression": "received_aggression[t] is not aligned with alive_ids[t].",
    "align.targets": "eligible_ids[t] and top_targets[t] differ in length.",
    "D1.agreement": "Recorded modal_agreement differs from agreement recomputed from top_targets (D1).",
    "D1.modal_target_id": "Recorded modal_target_id differs from the first-seen modal target (D1).",
    "D2.t95_series": "t95 from recomputed agreement differs from t95 of the recorded series (D2).",
    "D5.tension": "Recorded system_tension differs from sum(received_aggression) (D5).",
    "gini.series": "Recorded aggression_gini differs from the official gini of received_aggression.",
    "script.stdout": "The saved script stdout is missing, fails its SHA-256, or cannot be parsed.",
    "script.row": "A row of the unmodified script's printed table differs from the judge's recomputation.",
}

SERIES_1D = ["t", "n_alive", "system_tension", "modal_agreement", "eligible_count", "aggression_gini"]
SERIES_INT_1D = ["t", "n_alive", "eligible_count"]
SERIES_NESTED = ["alive_ids", "eligible_ids", "top_targets", "received_aggression"]

TABLE2_EXPECT = dict(
    ensemble_id="table2", script="reproduce_table_2.py", source_sha=PINNED_SHA, draft="18",
    variant="AC", source_mode="object", spread_mode="attention", N=N_AGENTS, k=6,
    rewire_prob=0.15, alpha=0.15, aggression_decay=0.03, expulsion_mode="none",
    expulsion_threshold=None, n_steps_planned=N_STEPS, steps_completed=N_STEPS, timed_out=False,
    viability=None, viability_D7_paper=None, expulsion_events=[], catharsis_events=[])


@dataclass(frozen=True)
class EnsembleSpec:
    """What one published table's ensemble must look like. TABLE2 is the C-T2 instance."""
    ensemble_id: str
    gammas: tuple
    seeds: tuple
    n_steps: int
    n_agents: int
    pub: dict                 # gamma -> (peak, peak_sd, final, final_sd, peak_gini, med_t95, k)
    expect: dict = field(default_factory=dict)  # trial metadata that must match exactly
    trial_id_format: str = "table2-g{gamma:.2f}-N{n_agents}-vAC-s{seed}"

    @property
    def n_trials(self):
        return len(self.gammas) * len(self.seeds)


TABLE2 = EnsembleSpec(ensemble_id="table2", gammas=tuple(GAMMAS), seeds=tuple(SEEDS), n_steps=N_STEPS,
                      n_agents=N_AGENTS, pub=PUB, expect=TABLE2_EXPECT)

# One data row of reproduce_table_2.py's printed table, as its print statement formats it:
#   f"{gamma:>6.2f} | {pk_m:>10.3f} {pk_sd:>6.3f} | {fn_m:>10.3f} {fn_sd:>6.3f} | "
#   f"{pk_g:>8.3f} | {t95_str:>8} | {conv_rate*100:>5.0f}%"
STDOUT_ROW = re.compile(r"^\s*(\d+\.\d{2}) \| +(\S+) +(\S+) \| +(\S+) +(\S+) \| +(\S+) \| +(\S+) \| +(\d+)%\s*$")


def issue(code, detail, where=None, t=None):
    assert code in ISSUE_CODES, code
    return dict(code=code, where=where, t=t, detail=detail)


# ---------------------------------------------------------------- parsing

def _parse_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"non-finite number {text!r} (contract: use null)")
    return value


def _reject_constant(name):
    raise ValueError(f"non-finite JSON constant {name} (contract: use null)")


def load_json_strict(raw):
    """Parse JSON, rejecting NaN, Infinity, and literals such as 1e309 that overflow to inf.

    Python's json module accepts all of these by default; the contract forbids them.
    """
    return json.loads(raw, parse_float=_parse_float, parse_constant=_reject_constant)


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def parse_table2_stdout(text):
    """Rows of reproduce_table_2.py's printed table, keyed by the printed gamma string."""
    rows = {}
    for line in text.splitlines():
        m = STDOUT_ROW.match(line)
        if m:
            g, pk, pk_sd, fn, fn_sd, pg, t95, pct = m.groups()
            rows[g] = dict(peak_modal_mean=pk, peak_modal_sd=pk_sd, final_modal_mean=fn, final_modal_sd=fn_sd,
                           peak_gini_mean=pg, med_t95=t95, conv_pct=pct)
    return rows


# ---------------------------------------------------------------- metrics

def time_to_95(modal_series, threshold=0.95, consecutive=10):
    # Same as reproduce_table_2.time_to_95 @ pinned SHA (0-based index); see test_against_official.py.
    n = len(modal_series)
    for t in range(n - consecutive + 1):
        if all(modal_series[t + k] >= threshold for k in range(consecutive)):
            return t
    return None


def modal_from_targets(top_targets):
    """Match girard_2x2_v3.record_metrics: counts dict in encounter order
    (eligible agents in alive order), modal = max(counts, key=counts.get),
    i.e. ties go to the target first seen. Agreement value is tie-invariant."""
    if not top_targets:
        return None, 0.0
    counts = {}
    for j in top_targets:
        counts[j] = counts.get(j, 0) + 1
    m = max(counts, key=counts.get)
    return m, counts[m] / len(top_targets)


def gini(values):
    # Same formula as GirardSimulation._gini @ pinned SHA; see test_against_official.py.
    v = np.asarray(values, dtype=float)
    if v.size == 0:
        return 0.0
    s = float(np.sum(v))
    if s <= 0.0:
        return 0.0
    sv = np.sort(v)
    n = sv.size
    idx = np.arange(1, n + 1, dtype=float)
    return float((2.0 * np.sum(idx * sv) - (n + 1.0) * np.sum(sv)) / (n * s))


def _binom_cdf(k, n, p):  # P(X <= k)
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def clopper_pearson(k, n, alpha=0.05):
    """Exact CP interval via bisection on the binomial CDF (equivalent to beta quantiles)."""
    def bisect(f, lo=0.0, hi=1.0):
        for _ in range(200):
            mid = (lo + hi) / 2
            if f(mid):
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else bisect(lambda p: 1 - _binom_cdf(k - 1, n, p) >= alpha / 2)
    upper = 1.0 if k == n else bisect(lambda p: _binom_cdf(k, n, p) <= alpha / 2)
    return [lower, upper]


def consistent_with_printed(value, printed, decimals):
    """Rule A (contract v0.2.1): a printed number stands for every value that rounds to it.

    Pass iff |value - printed| <= half a unit in the last printed place. The window has the
    same width as an exact match under any single rounding rule, centred on the printed
    value. A missing printed value matches only a missing reproduced value.
    """
    if printed is None or value is None:
        return printed is None and value is None
    return abs(value - printed) <= 0.5 * 10.0 ** (-decimals) + 1e-12


# ---------------------------------------------------------------- per-trial checks

class _Issues:
    """Collect issues for one trial, capped so a systematic fault does not flood the result."""

    def __init__(self, where):
        self.where = where
        self.items = []
        self.dropped = 0

    def add(self, code, detail, t=None):
        if len(self.items) < MAX_ISSUES_PER_TRIAL:
            self.items.append(issue(code, detail, self.where, t))
        else:
            self.dropped += 1

    def __bool__(self):
        return bool(self.items) or self.dropped > 0

    def as_list(self):
        out = list(self.items)
        if self.dropped:
            out.append(issue(self.items[-1]["code"], f"... and {self.dropped} more issues in this trial", self.where))
        return out


def check_series(s, n_steps, n_agents, where=None):
    """Validate one trial's series and recompute D1, D5 and gini from their parts.

    Structural checks run first. If any fails, no series is indexed and `recomputed` is
    None. Returns (issues, recomputed_agreement, stats).
    """
    issues = _Issues(where)
    stats = dict(max_modal_diff=0.0, max_tension_rel=0.0, max_gini_diff=0.0, modal_id_mismatch=0)
    if not isinstance(s, dict):
        issues.add("series.shape", "series is not an object")
        return issues.as_list(), None, stats

    # 1. Structure: present, a list, the right length, the right element types.
    for key in SERIES_1D + SERIES_NESTED:
        v = s.get(key)
        if not isinstance(v, list) or len(v) != n_steps:
            issues.add("series.shape", f"series.{key} missing, not a list, or len != {n_steps}")
    has_modal_id = "modal_target_id" in s
    if has_modal_id and (not isinstance(s["modal_target_id"], list) or len(s["modal_target_id"]) != n_steps):
        issues.add("series.shape", f"series.modal_target_id not a list of len {n_steps}")
    if issues:
        return issues.as_list(), None, stats
    for key in SERIES_1D:
        if not all(_is_num(x) for x in s[key]):
            issues.add("series.shape", f"series.{key} has a non-number")
    for key in SERIES_INT_1D:
        if not all(_is_int(x) for x in s[key]):
            issues.add("series.shape", f"series.{key} has a non-integer")
    for t in range(n_steps):
        alive, el, tt, R = (s[key][t] for key in SERIES_NESTED)
        if not all(isinstance(v, list) for v in (alive, el, tt, R)):
            issues.add("series.shape", "nested series entry is not a list", t)
            continue
        if not all(_is_int(x) for x in alive + el + tt):
            issues.add("series.shape", "alive_ids, eligible_ids or top_targets has a non-integer id", t)
        if not all(_is_num(x) for x in R):
            issues.add("series.shape", "received_aggression has a non-number", t)
    if issues:
        return issues.as_list(), None, stats

    # 2. Identities and alignment.
    if s["t"] != list(range(n_steps)):
        issues.add("series.t", f"series.t != 0..{n_steps - 1}")
    population = set(range(n_agents))
    for t in range(n_steps):
        alive, el, tt, R = (s[key][t] for key in SERIES_NESTED)
        alive_set = set(alive)
        if len(alive) != s["n_alive"][t]:
            issues.add("ids.alive_count", "len(alive_ids) != n_alive", t)
        if len(alive_set) != len(alive):
            issues.add("ids.alive_duplicate", "duplicate alive_ids", t)
        if not alive_set <= population:
            issues.add("ids.alive_outside_population", f"alive_ids outside 0..{n_agents - 1}", t)
        if len(R) != len(alive):
            issues.add("align.received_aggression", "received_aggression not aligned with alive_ids", t)
        if len(el) != s["eligible_count"][t]:
            issues.add("ids.eligible_count", "len(eligible_ids) != eligible_count", t)
        if len(set(el)) != len(el):
            issues.add("ids.eligible_duplicate", "duplicate eligible_ids", t)
        if not set(el) <= alive_set:
            issues.add("ids.eligible_not_alive", "eligible_ids not all in alive_ids", t)
        if not set(tt) <= alive_set:
            issues.add("ids.target_not_alive", "top_targets not all in alive_ids", t)
        if len(el) != len(tt):
            issues.add("align.targets", "eligible_ids/top_targets length mismatch", t)
        elif any(a == b for a, b in zip(el, tt, strict=True)):
            issues.add("ids.self_target", "an eligible agent targets itself", t)

    # 3. Recompute D1 (agreement), D5 (tension) and gini; compare with recorded values.
    recomputed = []
    tension_bad = gini_bad = 0
    for t in range(n_steps):
        m, a = modal_from_targets(s["top_targets"][t])
        recomputed.append(a)
        stats["max_modal_diff"] = max(stats["max_modal_diff"], abs(a - s["modal_agreement"][t]))
        if has_modal_id and s["modal_target_id"][t] != m:
            stats["modal_id_mismatch"] += 1
        R = s["received_aggression"][t]
        M = float(np.sum(np.asarray(R, dtype=float)))
        Mr = float(s["system_tension"][t])
        stats["max_tension_rel"] = max(stats["max_tension_rel"], abs(M - Mr) / max(abs(Mr), 1e-300))
        if abs(M - Mr) > TOL_TENSION_REL * max(1.0, abs(Mr)):
            tension_bad += 1
        gd = abs(gini(R) - s["aggression_gini"][t])
        stats["max_gini_diff"] = max(stats["max_gini_diff"], gd)
        if gd > TOL_GINI:
            gini_bad += 1
    if stats["max_modal_diff"] > TOL_MODAL:
        issues.add("D1.agreement", f"max abs diff {stats['max_modal_diff']}")
    if stats["modal_id_mismatch"]:
        issues.add("D1.modal_target_id", f"{stats['modal_id_mismatch']} steps")
    if tension_bad:
        issues.add("D5.tension", f"{tension_bad} steps (max rel diff {stats['max_tension_rel']})")
    if gini_bad:
        issues.add("gini.series", f"{gini_bad} steps (max abs diff {stats['max_gini_diff']})")
    return issues.as_list(), recomputed, stats


def check_metadata(tr, stem, spec=TABLE2):
    """Trial metadata against the ensemble spec. `stem` is the file name without .json."""
    issues = _Issues(stem)
    if not isinstance(tr, dict):
        issues.add("trial.metadata", "trial is not a JSON object")
        return issues.as_list()
    tid = tr.get("trial_id")
    if tid != stem:
        issues.add("trial.metadata", f"trial_id {tid!r} != filename")
    if tr.get("contract_version") not in ACCEPTED_TRACE_VERSIONS:
        issues.add("trial.metadata",
                   f"contract_version={tr.get('contract_version')!r} not in {ACCEPTED_TRACE_VERSIONS}")
    for key, val in spec.expect.items():
        if key not in tr:
            issues.add("trial.metadata", f"missing key {key}")
        elif tr[key] != val or (isinstance(val, bool) != isinstance(tr[key], bool)):
            issues.add("trial.metadata", f"{key}={tr[key]!r} expected {val!r}")
    g, seed = tr.get("gamma"), tr.get("seed")
    g_ok = _is_num(g) and g in spec.gammas
    seed_ok = _is_int(seed) and seed in spec.seeds
    if not g_ok:
        issues.add("trial.metadata", f"gamma {g!r} not in grid")
    if not seed_ok:
        issues.add("trial.metadata", f"seed {seed!r} not in the official seeds")
    if g_ok and seed_ok and tid != spec.trial_id_format.format(gamma=g, n_agents=spec.n_agents, seed=seed):
        issues.add("trial.metadata", f"trial_id does not follow {spec.trial_id_format}")
    return issues.as_list()


# ---------------------------------------------------------------- cell scoring

def score_cell(g, runs, script_row=None, spec=TABLE2):
    """Score one published gamma row from per-trial values.

    runs: dicts with seed, t95, t95_recorded_series (optional), peak_modal, final_modal, peak_gini.
    script_row: this gamma's row of the unmodified script's printed table (parse_table2_stdout),
    or None when the run's stdout was not saved.
    """
    n = len(runs)
    pk = [r["peak_modal"] for r in runs]
    fn = [r["final_modal"] for r in runs]
    pg = [r["peak_gini"] for r in runs]
    t95s = [r["t95"] for r in runs]
    conv = [t for t in t95s if t is not None]
    k = len(conv)
    med_np = float(np.median(conv)) if conv else None
    med_int = int(np.median(conv)) if conv else None   # what reproduce_table_2.py prints
    med_round = int(round(med_np)) if conv else None   # Python round: half to even
    med_half_up = int(math.floor(med_np + 0.5)) if conv else None
    comp = dict(peak_modal_mean=float(np.mean(pk)), peak_modal_sd=float(np.std(pk)),
                final_modal_mean=float(np.mean(fn)), final_modal_sd=float(np.std(fn)),
                peak_gini_mean=float(np.mean(pg)))
    p = spec.pub[g]
    pub = dict(peak_modal_mean=p[0], peak_modal_sd=p[1], final_modal_mean=p[2], final_modal_sd=p[3],
               peak_gini_mean=p[4], med_t95=p[5], k=p[6])
    printed_3dp = {key: f"{comp[key]:.3f}" for key in CONTINUOUS}  # the script's own formatting
    cont_interval = {key: consistent_with_printed(comp[key], pub[key], CONTINUOUS_DECIMALS) for key in CONTINUOUS}
    k_match = k == pub["k"]
    cont_ok = all(cont_interval.values())
    med_ok = consistent_with_printed(med_np, pub["med_t95"], MEDIAN_DECIMALS)
    # What the unmodified script would print for these per-trial values, field by field.
    expected_row = dict(printed_3dp, med_t95=str(med_int) if med_int is not None else "--",
                        conv_pct=f"{(k / n) * 100:.0f}" if n else None)
    if script_row is None:
        script_diff, script_ok = None, None
    else:
        script_diff = {key: dict(script=script_row.get(key), judge=val)
                       for key, val in expected_row.items() if script_row.get(key) != val}
        script_ok = not script_diff
    t95_series_ok = all(r.get("t95_recorded_series", r["t95"]) == r["t95"] for r in runs)
    cell_pass = k_match and cont_ok and med_ok and t95_series_ok and script_ok is not False
    return dict(
        gamma=g, n=n, k=k, published_k=pub["k"], cell_pass=cell_pass,
        checks=dict(k_match=k_match, continuous_consistent_with_paper=cont_ok,
                    med_t95_consistent_with_paper=med_ok, t95_recomputed_matches_recorded_series=t95_series_ok,
                    matches_script_output=script_ok),
        raw_t95=t95s, converged_t95_sorted=sorted(conv),
        raw_t95_from_recorded_series=[r.get("t95_recorded_series") for r in runs],
        median_t95_np=med_np, median_t95_script_int=med_int,
        median_t95_round_half_even=med_round, median_t95_round_half_up=med_half_up,
        published_med_t95=pub["med_t95"], expected_script_row=expected_row, script_row_diff=script_diff,
        computed=comp, published=pub, continuous_consistent=cont_interval,
        legacy_v0_2=dict(med_t95_int_equals_paper=(med_int == pub["med_t95"]),
                         continuous_3dp_string_match=all(float(printed_3dp[key]) == pub[key] for key in CONTINUOUS)),
        clopper_pearson_95=clopper_pearson(k, n) if n else None,
        per_trial=[dict(trial_id=r.get("trial_id"), seed=r["seed"], t95=r["t95"], peak_modal=r["peak_modal"],
                        final_modal=r["final_modal"], peak_gini=r["peak_gini"]) for r in runs])


def load_script_rows(trace_dir, man, issues, spec=TABLE2):
    """The unmodified script's printed table, from the stdout file the manifest names.

    Returns None when the manifest names no stdout file (the verdict is then provisional),
    or a dict keyed by gamma, possibly incomplete, with problems appended to `issues`.
    """
    name = man.get("script_stdout_file")
    if name is None:
        return None
    path = os.path.normpath(os.path.join(trace_dir, str(name)))
    if not path.startswith(os.path.normpath(trace_dir) + os.sep) or not os.path.isfile(path):
        issues.append(issue("script.stdout", f"script_stdout_file {name!r} not found inside the ensemble directory"))
        return {}
    raw = read_bytes(path)
    if hashlib.sha256(raw).hexdigest() != man.get("script_stdout_sha256"):
        issues.append(issue("script.stdout", "script_stdout_sha256 does not match the file"))
    parsed = parse_table2_stdout(raw.decode("utf-8", errors="replace"))
    rows = {}
    for g in spec.gammas:
        key = f"{g:.2f}"
        if key in parsed:
            rows[g] = parsed[key]
        else:
            issues.append(issue("script.stdout", f"no printed row for gamma {key}"))
    extra = sorted(set(parsed) - {f"{g:.2f}" for g in spec.gammas})
    if extra:
        issues.append(issue("script.stdout", f"printed rows for gammas not in the grid: {extra}"))
    return rows


# ---------------------------------------------------------------- judge

def _display_path(path):
    absolute = os.path.abspath(path)
    if absolute == _REPO or absolute.startswith(_REPO + os.sep):
        return os.path.relpath(absolute, _REPO)
    return path


def judge(trace_dir, spec=TABLE2):
    issues = []
    man = load_json_strict(read_bytes(os.path.join(trace_dir, "manifest.json")))
    if not isinstance(man, dict):
        raise ValueError("manifest.json is not a JSON object")
    if man.get("contract_version") not in ACCEPTED_TRACE_VERSIONS:
        issues.append(issue("manifest.field", f"contract_version={man.get('contract_version')!r}"))
    if man.get("source_sha") != PINNED_SHA:
        issues.append(issue("manifest.field", f"source_sha={man.get('source_sha')!r}"))
    if not isinstance(man.get("cells"), list) or len(man["cells"]) != len(spec.gammas):
        issues.append(issue("manifest.field", f"cells must list {len(spec.gammas)} published cells"))
    tdir = os.path.join(trace_dir, "trials")
    files = sorted(f for f in os.listdir(tdir) if f.endswith(".json"))
    trial_ids = man.get("trial_ids")
    if len(files) != spec.n_trials:
        issues.append(issue("ensemble.trial_files", f"{len(files)} trial files, expected {spec.n_trials}"))
    if not isinstance(trial_ids, list) or len(trial_ids) != spec.n_trials:
        issues.append(issue("ensemble.trial_files", f"manifest.trial_ids must list {spec.n_trials} trials"))
    elif set(map(str, trial_ids)) != {f[:-5] for f in files}:
        issues.append(issue("ensemble.trial_files", "manifest.trial_ids != files on disk"))
    script_rows = load_script_rows(trace_dir, man, issues, spec)

    by_gamma = {g: [] for g in spec.gammas}
    agg = dict(max_modal_diff=0.0, max_tension_rel=0.0, max_gini_diff=0.0, modal_id_mismatch=0)
    sha256 = {}
    for f in files:
        stem = f[:-5]
        raw = read_bytes(os.path.join(tdir, f))
        sha256[f] = hashlib.sha256(raw).hexdigest()
        try:
            tr = load_json_strict(raw)
        except ValueError as exc:
            issues.append(issue("trial.json", str(exc), stem))
            continue
        issues.extend(check_metadata(tr, stem, spec))
        if not isinstance(tr, dict):
            continue
        s_issues, recomputed, stats = check_series(tr.get("series"), spec.n_steps, spec.n_agents, where=stem)
        issues.extend(s_issues)
        for key in ("max_modal_diff", "max_tension_rel", "max_gini_diff"):
            agg[key] = max(agg[key], stats[key])
        agg["modal_id_mismatch"] += stats["modal_id_mismatch"]
        g = tr.get("gamma")
        if recomputed is None or not _is_num(g) or g not in by_gamma or not _is_int(tr.get("seed")):
            continue  # this trial is missing from its cell, so the seeds check below fails
        s = tr["series"]
        if any(n != spec.n_agents for n in s["n_alive"]):
            issues.append(issue("ids.alive_count", f"n_alive != {spec.n_agents} somewhere (no-expulsion run)", stem))
        by_gamma[g].append(dict(
            trial_id=tr.get("trial_id"), seed=tr["seed"],
            t95=time_to_95(recomputed),
            t95_recorded_series=time_to_95(s["modal_agreement"]),
            peak_modal=max(recomputed), final_modal=float(np.mean(recomputed[-50:])),
            peak_gini=max(s["aggression_gini"]),
            scipy=tr.get("packages", {}).get("scipy") if isinstance(tr.get("packages"), dict) else None))

    cells, notes = [], []
    for g in spec.gammas:
        runs = sorted(by_gamma[g], key=lambda r: r["seed"])
        if [r["seed"] for r in runs] != list(spec.seeds):
            issues.append(issue("ensemble.seeds", f"gamma {g}: seeds {[r['seed'] for r in runs]}"))
        if not runs:
            continue
        cell = score_cell(g, runs, None if script_rows is None else script_rows.get(g, {}), spec)
        if not cell["checks"]["t95_recomputed_matches_recorded_series"]:
            issues.append(issue("D2.t95_series", f"gamma {g}"))
        if cell["checks"]["matches_script_output"] is False:
            issues.append(issue("script.row", f"gamma {g}: {cell['script_row_diff']}"))
        if cell["median_t95_script_int"] != cell["published_med_t95"]:
            notes.append(dict(
                gamma=g, kind="paper_vs_script_med_t95", paper=cell["published_med_t95"],
                script_int_np_median=cell["median_t95_script_int"], np_median=cell["median_t95_np"],
                converged_t95_sorted=cell["converged_t95_sorted"],
                rule_a_consistent=cell["checks"]["med_t95_consistent_with_paper"],
                rule=("Known mismatch 3. Rule A scores the printed integer as the interval of medians that round "
                      "to it. The script truncates with int(); the paper's integers match round-half-even.")))
        cells.append(cell)

    def all_cells(name):
        return len(cells) == len(spec.gammas) and all(c["checks"][name] for c in cells)

    def all_cells_legacy(name):
        return len(cells) == len(spec.gammas) and all(c["legacy_v0_2"][name] for c in cells)

    all_k = all_cells("k_match")
    all_cont = all_cells("continuous_consistent_with_paper")
    all_med = all_cells("med_t95_consistent_with_paper")
    all_t95_series = all_cells("t95_recomputed_matches_recorded_series")
    all_script = None if script_rows is None else all_cells("matches_script_output")
    no_issues = not issues
    verdict_pass = no_issues and all_k and all_cont and all_med and all_t95_series and all_script is not False

    provisional = []
    if script_rows is None:
        provisional.append("manifest.script_stdout_file not provided: the judge's recomputation was not compared "
                           "with the unmodified script's own printed table (contract v0.2.1, C-T2).")

    scipy_vals = sorted({str(r["scipy"]) for g in spec.gammas for r in by_gamma[g]})
    return dict(
        judge="judge_table2.py", judge_version=JUDGE_VERSION, contract=CONTRACT,
        trace_dir=_display_path(trace_dir), pinned_sha=PINNED_SHA, manifest_sha=man.get("source_sha"),
        n_trials=len(files), packages_scipy_values=scipy_vals, manifest_packages=man.get("packages"),
        verdict="PASS" if verdict_pass else "FAIL",
        provisional=provisional,
        checks=dict(
            a_k_matches_published_all_cells=all_k,
            b_continuous_consistent_with_paper_all_cells=all_cont,
            c_t95_recomputed_matches_recorded_series=all_t95_series,
            d_med_t95_consistent_with_paper_all_cells=all_med,
            e_matches_script_output_all_cells=all_script,
            no_issues=no_issues,
            recompute_modal_agreement_max_abs_diff=agg["max_modal_diff"],
            recompute_modal_target_id_mismatches=agg["modal_id_mismatch"],
            recompute_system_tension_max_rel_diff=agg["max_tension_rel"],
            recompute_gini_max_abs_diff=agg["max_gini_diff"],
        ),
        legacy_checks_v0_2=dict(
            d_int_median_equals_paper_integer_all_cells=all_cells_legacy("med_t95_int_equals_paper"),
            b_continuous_3dp_string_match_all_cells=all_cells_legacy("continuous_3dp_string_match"),
        ),
        verdict_basis=("Contract v0.2.1: counts match exactly; printed numbers are scored by rule A (half a unit "
                       "in the last printed place); every recorded series is recomputed from its parts within "
                       "stated tolerances; inputs are validated and the judge fails closed."),
        assumptions=[
            "Agreement recomputed from series.eligible_ids/top_targets; ties broken as official record_metrics "
            "(first-seen target wins); agreement value is tie-invariant.",
            "Eligibility (sum A_i >= 1e-8) is taken as recorded in eligible_ids; raw aggression matrices are not "
            "in traces, so eligibility itself is not recomputed. eligible_ids must be unique members of alive_ids.",
            "Peak gini taken from recorded aggression_gini, which must equal the official gini of "
            "received_aggression within 1e-9 at every step.",
            "Clopper-Pearson 95% via exact binomial-CDF bisection (scipy not needed); report only.",
        ],
        issues=issues, paper_vs_script_notes=notes, cells=cells, trial_file_sha256=sha256,
    )


def failure_result(trace_dir, reason):
    return dict(judge="judge_table2.py", judge_version=JUDGE_VERSION, contract=CONTRACT,
                trace_dir=_display_path(trace_dir), verdict="FAIL", provisional=[], fatal_error=reason,
                issues=[issue("fatal", reason)])


def write_result_atomic(path, result):
    """Write strict JSON (no NaN or Infinity) via a temp file and rename."""
    text = json.dumps(result, indent=1, allow_nan=False)
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".judge-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def print_summary(result):
    keys = ["verdict", "provisional", "checks", "legacy_checks_v0_2", "fatal_error", "paper_vs_script_notes"]
    print(json.dumps({k: result[k] for k in keys if k in result}, indent=1))
    for i in result.get("issues", [])[:20]:
        step = "" if i["t"] is None else f" t={i['t']}"
        print(f"ISSUE {i['code']} {i['where'] or '-'}{step}: {i['detail']}")
    for c in result.get("cells", []):
        r = c["expected_script_row"]
        ci = c["clopper_pearson_95"]
        print(f"{c['gamma']:>5.2f} k={c['k']}/{c['n']} pub={c['published_k']} med={c['median_t95_script_int']} "
              f"np={c['median_t95_np']} pub_med={c['published_med_t95']} "
              f"pk={r['peak_modal_mean']}({r['peak_modal_sd']}) fn={r['final_modal_mean']}({r['final_modal_sd']}) "
              f"g={r['peak_gini_mean']} pass={c['cell_pass']} CI=[{ci[0]:.4f},{ci[1]:.4f}] t95={c['raw_t95']}")


def main(argv=None, spec=TABLE2):
    argv = sys.argv[1:] if argv is None else argv
    trace_dir = argv[0] if argv else _DEFAULT_TRACES
    out = argv[1] if len(argv) > 1 else _DEFAULT_OUT
    try:
        result = judge(trace_dir, spec)
    except Exception as exc:  # fail closed: any error is a FAIL, never a crash that leaves old output
        result = failure_result(trace_dir, f"{type(exc).__name__}: {exc}")
    try:
        write_result_atomic(out, result)
    except ValueError as exc:  # a non-finite value reached the result
        result = failure_result(trace_dir, f"result is not strict JSON: {exc}")
        write_result_atomic(out, result)
    print_summary(result)
    return 0 if result.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
