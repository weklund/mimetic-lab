#!/usr/bin/env python3
"""Official C-T2 judge (eval contract v0.2): Black 2026 Table 2.

Scores ONLY from trial JSON files + manifest.json. Deterministic, no network.
Does not modify traces. Usage:
    python3 judge_table2.py [TRACE_DIR] [OUT_JSON]
"""
import json, math, os, sys, hashlib
from fractions import Fraction
import numpy as np

# Default traces live under the repo (often via Git LFS, not ordinary git blobs).
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", ".."))
_DEFAULT_TRACES = os.path.join(_REPO, "eval", "traces", "v0.2", "table2")
TRACE_DIR = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_TRACES
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(_HERE, "table2-result.json")
PINNED_SHA = "89e7bbb57db62e3c830a8ca672a0805080df3970"
GAMMAS = [0.75, 0.90, 0.95, 1.00, 1.01, 1.02, 1.05, 1.08, 1.10, 1.15, 1.25, 1.50, 2.00]
SEEDS = [42 + r * 1000 for r in range(8)]
N_STEPS = 600
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
TOL = 1e-12


def time_to_95(modal_series, threshold=0.95, consecutive=10):
    # Verbatim from reproduce_table_2.py @ pinned SHA (0-based index).
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
    # Same formula as GirardSimulation._gini.
    v = np.asarray(values, dtype=float)
    if v.size == 0:
        return 0.0
    s = float(np.sum(v))
    if s <= 0.0:
        return 0.0
    sv = np.sort(v); n = sv.size; idx = np.arange(1, n + 1, dtype=float)
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


def r3(x):
    return None if x is None else float(f"{x:.3f}")  # same rounding as the script's .3f print


def main():
    issues = []
    man = json.load(open(os.path.join(TRACE_DIR, "manifest.json")))
    if man.get("contract_version") != "0.2": issues.append(f"manifest contract_version={man.get('contract_version')}")
    if man.get("source_sha") != PINNED_SHA: issues.append(f"manifest source_sha={man.get('source_sha')}")
    tdir = os.path.join(TRACE_DIR, "trials")
    files = sorted(f for f in os.listdir(tdir) if f.endswith(".json"))
    if len(files) != 104: issues.append(f"trial file count {len(files)} != 104")
    if len(man.get("trial_ids", [])) != 104: issues.append("manifest trial_ids != 104")
    if set(man.get("trial_ids", [])) != {f[:-5] for f in files}: issues.append("manifest trial_ids != files on disk")
    if len(man.get("cells", [])) != 13: issues.append(f"manifest cells {len(man.get('cells', []))} != 13")

    by_gamma = {g: [] for g in GAMMAS}
    max_modal_diff = 0.0; max_tension_rel = 0.0; max_gini_diff = 0.0
    modal_id_mismatch = 0; elig_count_mismatch = 0
    sha256 = {}
    for f in files:
        path = os.path.join(tdir, f)
        raw = open(path, "rb").read(); sha256[f] = hashlib.sha256(raw).hexdigest()
        tr = json.loads(raw)
        tid = tr.get("trial_id")
        def chk(cond, msg):
            if not cond: issues.append(f"{tid}: {msg}")
        chk(tid == f[:-5], "trial_id != filename")
        expect = dict(contract_version="0.2", ensemble_id="table2", script="reproduce_table_2.py",
                      source_sha=PINNED_SHA, draft="18", variant="AC", source_mode="object",
                      spread_mode="attention", N=50, k=6, rewire_prob=0.15, alpha=0.15,
                      aggression_decay=0.03, expulsion_mode="none", expulsion_threshold=None,
                      n_steps_planned=N_STEPS, steps_completed=N_STEPS, timed_out=False,
                      viability=None, viability_D7_paper=None, expulsion_events=[], catharsis_events=[])
        for key, val in expect.items():
            chk(key in tr, f"missing key {key}")
            if key in tr: chk(tr[key] == val, f"{key}={tr[key]!r} expected {val!r}")
        g = tr.get("gamma"); chk(g in by_gamma, f"gamma {g} not in grid")
        chk(tr.get("seed") in SEEDS, f"seed {tr.get('seed')} not in 42+r*1000")
        chk(tid == f"table2-g{g:.2f}-N50-vAC-s{tr.get('seed')}", "trial_id pattern")
        s = tr["series"]
        for key in ["t", "n_alive", "alive_ids", "system_tension", "modal_agreement", "eligible_count",
                    "eligible_ids", "top_targets", "received_aggression", "aggression_gini"]:
            chk(key in s and len(s[key]) == N_STEPS, f"series.{key} missing or len != {N_STEPS}")
        chk(s["t"] == list(range(N_STEPS)), "series.t != 0..599")
        chk(all(n == 50 for n in s["n_alive"]), "n_alive != 50 somewhere")

        recomputed = []
        for t in range(N_STEPS):
            el, tt = s["eligible_ids"][t], s["top_targets"][t]
            if len(el) != len(tt): issues.append(f"{tid} t={t}: eligible_ids/top_targets length mismatch")
            if len(el) != s["eligible_count"][t]: elig_count_mismatch += 1
            if any(a == b for a, b in zip(el, tt)): issues.append(f"{tid} t={t}: self-target")
            m, a = modal_from_targets(tt)
            recomputed.append(a)
            if "modal_target_id" in s and s["modal_target_id"][t] != m: modal_id_mismatch += 1
            max_modal_diff = max(max_modal_diff, abs(a - s["modal_agreement"][t]))
            R = s["received_aggression"][t]
            M = float(np.sum(np.asarray(R, dtype=float))); Mr = s["system_tension"][t]
            max_tension_rel = max(max_tension_rel, abs(M - Mr) / max(abs(Mr), 1e-300))
            max_gini_diff = max(max_gini_diff, abs(gini(R) - s["aggression_gini"][t]))
        # Official inputs: recomputed agreement; gini from recorded series (cross-checked above).
        by_gamma[g].append(dict(
            trial_id=tid, seed=tr["seed"],
            t95=time_to_95(recomputed),
            t95_recorded_series=time_to_95(s["modal_agreement"]),
            peak_modal=max(recomputed), final_modal=float(np.mean(recomputed[-50:])),
            peak_gini=max(s["aggression_gini"]),
            scipy=tr.get("packages", {}).get("scipy")))

    if max_modal_diff > TOL: issues.append(f"recomputed vs recorded modal_agreement max diff {max_modal_diff}")
    if modal_id_mismatch: issues.append(f"modal_target_id tie-break mismatches: {modal_id_mismatch}")
    if elig_count_mismatch: issues.append(f"eligible_count != len(eligible_ids): {elig_count_mismatch}")

    cells = []; notes = []
    all_k = all_cont = all_med_script = all_med_paper = True
    for g in GAMMAS:
        runs = sorted(by_gamma[g], key=lambda r: r["seed"])
        if [r["seed"] for r in runs] != SEEDS: issues.append(f"gamma {g}: seeds {[r['seed'] for r in runs]}")
        n = len(runs)
        pk = [r["peak_modal"] for r in runs]; fn = [r["final_modal"] for r in runs]; pg = [r["peak_gini"] for r in runs]
        t95s = [r["t95"] for r in runs]; conv = [t for t in t95s if t is not None]
        k = len(conv)
        med_np = float(np.median(conv)) if conv else None
        med_int = int(np.median(conv)) if conv else None
        med_round = int(round(med_np)) if conv else None  # Python round: half to even
        med_half_up = int(math.floor(med_np + 0.5)) if conv else None
        comp = dict(peak_modal_mean=float(np.mean(pk)), peak_modal_sd=float(np.std(pk)),
                    final_modal_mean=float(np.mean(fn)), final_modal_sd=float(np.std(fn)),
                    peak_gini_mean=float(np.mean(pg)))
        p = PUB[g]
        pub = dict(peak_modal_mean=p[0], peak_modal_sd=p[1], final_modal_mean=p[2], final_modal_sd=p[3],
                   peak_gini_mean=p[4], med_t95=p[5], k=p[6])
        rounded = {key: r3(v) for key, v in comp.items()}
        cont_match = {key: rounded[key] == pub[key] for key in rounded}
        k_match = (k == pub["k"])
        med_script_match_paper = (med_int == pub["med_t95"])
        cont_ok = all(cont_match.values())
        all_k &= k_match; all_cont &= cont_ok; all_med_paper &= med_script_match_paper
        conv_pct = f"{(k / n) * 100:>5.0f}%"
        cell = dict(gamma=g, n=n, k=k, published_k=pub["k"], k_match=k_match,
                    raw_t95=t95s, converged_t95_sorted=sorted(conv),
                    raw_t95_from_recorded_series=[r["t95_recorded_series"] for r in runs],
                    median_t95_np=med_np, median_t95_script_int=med_int,
                    median_t95_round_half_even=med_round, median_t95_round_half_up=med_half_up,
                    published_med_t95=pub["med_t95"], med_t95_match_paper=med_script_match_paper,
                    computed=comp, computed_rounded_3dp=rounded, published=pub, continuous_match=cont_match,
                    continuous_all_match=cont_ok, conv_pct_script_format=conv_pct,
                    clopper_pearson_95=clopper_pearson(k, n),
                    per_trial=[dict(trial_id=r["trial_id"], seed=r["seed"], t95=r["t95"], peak_modal=r["peak_modal"],
                                    final_modal=r["final_modal"], peak_gini=r["peak_gini"]) for r in runs])
        if not med_script_match_paper:
            notes.append(dict(gamma=g, kind="paper_vs_script_med_t95",
                              paper=pub["med_t95"], script_int_np_median=med_int, np_median=med_np,
                              converged_t95_sorted=sorted(conv),
                              rule="Contract: reproduction of a table uses the script; mismatch reported, not fixed."))
        cells.append(cell)

    # (c) script-style med t95 equals official script definition by construction (same function, same
    # int(np.median)); verify independently that t95 from recorded series agrees with recomputed.
    for c in cells:
        if c["raw_t95"] != c["raw_t95_from_recorded_series"]:
            all_med_script = False; issues.append(f"gamma {c['gamma']}: t95 recomputed vs recorded series differ")

    scipy_vals = sorted({str(r["scipy"]) for g in GAMMAS for r in by_gamma[g]})
    schema_ok = not issues
    # Verdict: contract C-T2 literal rule requires paper med t95 integers; operational rule says the
    # script governs when prose and script disagree. Report both, apply the operational rule.
    paper_only_med_mismatch = all_k and all_cont and all_med_script and not all_med_paper
    verdict_literal = all_k and all_cont and all_med_paper and schema_ok
    verdict_operational = all_k and all_cont and all_med_script and schema_ok
    result = dict(
        judge="judge_table2.py", contract="eval contract v0.2, C-T2", trace_dir=TRACE_DIR,
        pinned_sha=PINNED_SHA, manifest_sha=man.get("source_sha"), n_trials=len(files),
        packages_scipy_values=scipy_vals, manifest_packages=man.get("packages"),
        checks=dict(
            a_k_matches_published_all_cells=all_k,
            b_continuous_3dp_match_all_cells=all_cont,
            c_med_t95_matches_official_script_definition=all_med_script,
            d_med_t95_matches_paper_integer_all_cells=all_med_paper,
            note_round_half_even_median_matches_paper_all_cells=all(
                c["median_t95_round_half_even"] == c["published_med_t95"] for c in cells),
            schema_and_metadata_ok=schema_ok,
            recompute_modal_agreement_max_abs_diff=max_modal_diff,
            recompute_modal_target_id_mismatches=modal_id_mismatch,
            recompute_system_tension_max_rel_diff=max_tension_rel,
            recompute_gini_max_abs_diff=max_gini_diff,
        ),
        verdict_literal_paper_integers=("PASS" if verdict_literal else "FAIL"),
        verdict=("PASS" if verdict_operational else "FAIL"),
        verdict_basis=("Operational rule: script governs table reproduction; paper-vs-script mismatches reported."
                       + (" Only deviation from paper is med t95 integers listed in notes." if paper_only_med_mismatch else "")),
        assumptions=[
            "Agreement recomputed from series.eligible_ids/top_targets; ties broken as official record_metrics (first-seen target wins); agreement value is tie-invariant.",
            "Eligibility (sum A_i >= 1e-8) is taken as recorded in eligible_ids; raw aggression matrices are not in traces, so eligibility itself is not recomputed.",
            "Peak gini taken from recorded aggression_gini, cross-checked by recomputing gini from received_aggression with the official formula.",
            "3-decimal match compares f'{x:.3f}' of computed value with the printed published value.",
            "Clopper-Pearson 95% via exact binomial-CDF bisection (scipy not installed); report only.",
        ],
        issues=issues, paper_vs_script_notes=notes, cells=cells, trial_file_sha256=sha256,
    )
    with open(OUT, "w") as fh:
        json.dump(result, fh, indent=1)
    print(json.dumps({k: result[k] for k in ["verdict", "verdict_literal_paper_integers", "checks", "issues", "paper_vs_script_notes", "packages_scipy_values"]}, indent=1))
    for c in cells:
        r = c["computed_rounded_3dp"]
        print(f"{c['gamma']:>5.2f} k={c['k']}/{c['n']} pub={c['published_k']} med={c['median_t95_script_int']} np={c['median_t95_np']} pub_med={c['published_med_t95']} "
              f"pk={r['peak_modal_mean']}({r['peak_modal_sd']}) fn={r['final_modal_mean']}({r['final_modal_sd']}) g={r['peak_gini_mean']} "
              f"cont={c['continuous_all_match']} CI=[{c['clopper_pearson_95'][0]:.4f},{c['clopper_pearson_95'][1]:.4f}] t95={c['raw_t95']}")


if __name__ == "__main__":
    main()
