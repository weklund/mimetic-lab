"""
Contract v0.2 trace exporter for Maxwell Black's official scripts (UNMODIFIED).

Loads an official script as a module, installs PASS-THROUGH wrappers on published
functions (each calls the original and returns its result untouched), snapshots
extra state that official code does not store, then calls the script's own main().
No model code, parameters, seeds, RNG draws or control flow are changed. All
snapshot reads use side-effect-free official helpers (_alive_ids,
_received_aggression_vector) or a verbatim copy of record_metrics' modal loop.

Usage:
  python3 export_v02.py <repo_dir> <script.py> <ensemble_id> <out_root> [--command "..."]
Writes <out_root>/<ensemble_id>/manifest.json and trials/<trial_id>.json.
"""
import sys, os, json, math, inspect, time, datetime, platform, dataclasses, functools, importlib.util, argparse
from typing import Dict, List

ap = argparse.ArgumentParser()
ap.add_argument("repo"); ap.add_argument("script"); ap.add_argument("ensemble_id"); ap.add_argument("out_root")
ap.add_argument("--command", default=" ".join(sys.argv))
ap.add_argument("--source-sha", required=True)
ap.add_argument("--npz", action="store_true",
                help="offload series to trials/<trial_id>.npz (contract v0.2 NPZ offload, object layout)")
ARGS = ap.parse_args()

REPO = os.path.abspath(ARGS.repo)
sys.path.insert(0, REPO)
os.chdir(REPO)
import numpy as np
import networkx as nx
import girard_2x2_v3 as G

CONTRACT = "0.2"
PAPER = "Black 2026, A Computational Test of Girard's Scapegoat Mechanism"
DRAFT = "18"
SOURCE_REPO = "https://github.com/maxwell-black/mimetic-desire-simulation"
ENS = ARGS.ensemble_id
OUT = os.path.join(ARGS.out_root, ENS)
os.makedirs(os.path.join(OUT, "trials"), exist_ok=True)

def _pkgs():
    out = {"numpy": np.__version__, "networkx": nx.__version__}
    try:
        import scipy; out["scipy"] = scipy.__version__
    except ImportError:
        out["scipy"] = "not installed"   # contract: strings only; official model code does not import scipy
    return out
PACKAGES = _pkgs()
PYVER = platform.python_version()
def now(): return datetime.datetime.now().astimezone().isoformat(timespec="seconds")

REV_VARIANT = {v: k for k, v in G.VARIANT_MAP.items()}
def gstr(g): return f"{float(g):.2f}"
def make_trial_id(gamma, N, variant, seed): return f"{ENS}-g{gstr(gamma)}-N{int(N)}-v{variant}-s{int(seed)}"

# ---------------------------------------------------------------------------
# Snapshot: verbatim copy of the eligible/top-target loop in official
# GirardSimulation.record_metrics (and small_n_utils.get_modal_target; same rule,
# same tie-break: first-encountered max). Read-only.
# ---------------------------------------------------------------------------
def snapshot(sim):
    alive, received = sim._received_aggression_vector()
    eligible_ids, top_targets = [], []
    thresh = 1e-8
    for i in alive:
        targets = [j for j in alive if j != i]
        if not targets:
            continue
        vec = sim.aggression[i][targets]
        if float(np.sum(vec)) < thresh:
            continue
        eligible_ids.append(int(i))
        top_targets.append(int(targets[int(np.argmax(vec))]))
    if top_targets:
        counts: Dict[int, int] = {}
        for j in top_targets:
            counts[j] = counts.get(j, 0) + 1
        mt = max(counts, key=counts.get)
        ma = float(counts[mt] / len(eligible_ids))
    else:
        mt, ma = None, 0.0
    return {"alive": [int(a) for a in alive], "received": [float(x) for x in received],
            "M": float(np.sum(received)), "eligible_ids": eligible_ids,
            "top_targets": top_targets, "modal_target_id": mt, "modal_agreement": ma}

def _new_collector():
    return {"t": [], "alive_ids": [], "received_aggression": [], "eligible_ids": [],
            "top_targets": [], "modal_target_id": [], "chk_modal": [],
            "system_tension_snap": [], "catharsis": [], "started_at": now()}

def _col(sim):
    c = getattr(sim, "_v02", None)
    if c is None:
        c = _new_collector(); sim._v02 = c   # extra attribute only; never read by model code
    return c

# ---------------- record_metrics (record_history=True path) ----------------
_orig_record_metrics = G.GirardSimulation.record_metrics
@functools.wraps(_orig_record_metrics)
def record_metrics(self, *a, **k):
    out = _orig_record_metrics(self, *a, **k)
    c = _col(self); s = snapshot(self)
    c["t"].append(len(c["t"]))
    c["alive_ids"].append(s["alive"]); c["received_aggression"].append(s["received"])
    c["eligible_ids"].append(s["eligible_ids"]); c["top_targets"].append(s["top_targets"])
    c["modal_target_id"].append(s["modal_target_id"]); c["chk_modal"].append(s["modal_agreement"])
    c["system_tension_snap"].append(s["M"])
    return out
G.GirardSimulation.record_metrics = record_metrics

# ---------------- step_expulsion (threshold mode) ----------------
_orig_step_expulsion = G.GirardSimulation.step_expulsion
@functools.wraps(_orig_step_expulsion)
def step_expulsion(self, *a, **k):
    if self.cfg.expulsion_threshold is None:
        return _orig_step_expulsion(self, *a, **k)
    n_before = len(self.history["expulsion_events"])
    pre = self._received_aggression_by_alive()           # post-decay, pre-zeroing (same call as official)
    M_pre = float(sum(pre.values())) if pre else 0.0
    out = _orig_step_expulsion(self, *a, **k)
    if len(self.history["expulsion_events"]) > n_before:
        post = self._received_aggression_by_alive()
        M_post = float(sum(post.values())) if post else 0.0
        step, victim, _ = self.history["catharsis_events"][-1]
        _col(self)["catharsis"].append({"step": int(step), "victim_id": int(victim),
                                        "M_pre": M_pre, "M_post": M_post,
                                        "official_drop": float(self.history["catharsis_events"][-1][2])})
    return out
G.GirardSimulation.step_expulsion = step_expulsion

def _fd(M_pre, M_post):
    return max(0.0, (M_pre - M_post) / M_pre) if M_pre > 0.0 else 0.0

TRIAL_IDS: List[str] = []
CELLS: Dict[tuple, List[str]] = {}

def _check_finite(o, path="$"):
    if isinstance(o, float) and not math.isfinite(o):
        raise ValueError(f"non-finite at {path}")
    if isinstance(o, dict):
        for k2, v in o.items(): _check_finite(v, f"{path}.{k2}")
    elif isinstance(o, list):
        for i, v in enumerate(o): _check_finite(v, f"{path}[{i}]")

import hashlib
DIGESTS: Dict[str, str] = {}
RERUNS: List[str] = []
def _digest(d):
    # everything except wall-clock timestamps
    body = {k2: v for k2, v in d.items() if k2 not in ("started_at", "ended_at")}
    return hashlib.sha256(json.dumps(body, sort_keys=True, allow_nan=False).encode()).hexdigest()

NPZ_NESTED = ("alive_ids", "eligible_ids", "top_targets", "received_aggression")
NPZ_INT = ("t", "n_alive", "eligible_count")
def _write_npz(tid, series):
    arrs = {}
    for k2, v in series.items():
        if k2 in NPZ_NESTED:
            dt = np.float64 if k2 == "received_aggression" else np.int64
            o = np.empty(len(v), dtype=object)
            for i, row in enumerate(v): o[i] = np.asarray(row, dtype=dt).reshape(-1)
            arrs[k2] = o
        elif k2 == "modal_target_id":
            if any(x is None for x in v):   # int or null: object array, None where A_t is empty
                o = np.empty(len(v), dtype=object); o[:] = v; arrs[k2] = o
            else:
                arrs[k2] = np.asarray(v, dtype=np.int64)
        else:
            arrs[k2] = np.asarray(v, dtype=(np.int64 if k2 in NPZ_INT else np.float64))
    np.savez_compressed(os.path.join(OUT, "trials", tid + ".npz"), **arrs)

def write_trial(d):
    tid = d["trial_id"]
    _check_finite(d)
    dg = _digest(d)
    if tid in DIGESTS:
        # official script re-ran the identical (script, variant, N, gamma, seed) trial
        # (exp_small_n_phase_boundary.py does a second pass for its gamma* summary).
        # Deterministic: must be bit-identical; keep the first file, record the rerun.
        if DIGESTS[tid] != dg:
            raise RuntimeError(f"rerun of {tid} is NOT identical to first run")
        RERUNS.append(tid)
        return
    DIGESTS[tid] = dg
    if ARGS.npz:
        _write_npz(tid, d["series"])
        d = dict(d); d["series"] = {"$npz": tid + ".npz"}
    with open(os.path.join(OUT, "trials", tid + ".json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    TRIAL_IDS.append(tid)
    CELLS.setdefault((d["N"], d["gamma"], d["variant"]), []).append(tid)

def base_meta(sim, variant, expulsion_mode, steps_completed, timed_out, started_at, theta=None, cooldown=None):
    cfg = sim.cfg
    return {
        "contract_version": CONTRACT, "trial_id": make_trial_id(cfg.salience_exponent, cfg.n_agents, variant, cfg.seed),
        "ensemble_id": ENS, "script": ARGS.script, "source_repo": SOURCE_REPO, "source_sha": ARGS.source_sha,
        "paper": PAPER, "draft": DRAFT, "variant": variant, "source_mode": sim.source, "spread_mode": sim.spread,
        "N": int(cfg.n_agents), "k": int(cfg.n_neighbors), "rewire_prob": float(cfg.rewire_prob),
        "alpha": float(cfg.alpha), "gamma": float(cfg.salience_exponent),
        "aggression_decay": float(cfg.aggression_decay), "expulsion_mode": expulsion_mode,
        "expulsion_threshold": (float(cfg.expulsion_threshold) if expulsion_mode == "threshold" else None),
        "unanimity_threshold": theta, "unanimity_cooldown": cooldown,
        "n_steps_planned": int(cfg.n_steps), "steps_completed": int(steps_completed), "seed": int(cfg.seed),
        "timed_out": bool(timed_out), "python_version": PYVER, "packages": PACKAGES, "command": ARGS.command,
        "started_at": started_at, "ended_at": now(),
    }

# ---------------- run (record_metrics path: Tables 2, 2b, 1, ...) ----------------
_orig_run = G.GirardSimulation.run
@functools.wraps(_orig_run)
def run(self, *a, **k):
    _col(self)
    out = _orig_run(self, *a, **k)
    if not self.record_history:
        return out
    c = self._v02; h = self.history
    T = len(h["modal_agreement"])
    assert len(c["t"]) == T, "snapshot/record_metrics length mismatch"
    # integrity: wrapper recomputation must equal what official record_metrics wrote
    assert c["chk_modal"] == list(h["modal_agreement"]), "modal_agreement mismatch"
    assert c["system_tension_snap"] == list(h["system_tension"]), "system_tension mismatch"
    assert [len(e) for e in c["eligible_ids"]] == list(h["eligible_agents"]), "eligible count mismatch"
    assert [len(a_) for a_ in c["alive_ids"]] == list(h["n_active_agents"]), "n_alive mismatch"
    variant = REV_VARIANT[(self.source, self.spread)]
    mode = "none" if self.cfg.expulsion_threshold is None else "threshold"
    d = base_meta(self, variant, mode, T, False, c["started_at"])
    d["series"] = {
        "t": list(range(T)),
        "n_alive": [int(x) for x in h["n_active_agents"]],
        "alive_ids": c["alive_ids"],
        "system_tension": [float(x) for x in h["system_tension"]],
        "modal_agreement": [float(x) for x in h["modal_agreement"]],
        "eligible_count": [int(x) for x in h["eligible_agents"]],
        "eligible_ids": c["eligible_ids"],
        "top_targets": c["top_targets"],
        "received_aggression": c["received_aggression"],
        "aggression_gini": [float(x) for x in h["aggression_gini"]],
        "top_target_share": [float(x) for x in h["aggression_max_share"]],
        "convergence_ratio": [float(x) for x in h["convergence_ratio"]],
        "aggression_entropy": [float(x) for x in h["aggression_entropy"]],
        "top_R": [float(x) for x in h["top_target_aggression"]],
        "mean_R": [float(x) for x in h["mean_aggression"]],
        "modal_target_id": c["modal_target_id"],
    }
    d["expulsion_events"] = [{"step": int(s), "victim_id": int(v), "received_aggression": float(r)}
                             for (s, v, r) in h["expulsion_events"]]
    cev = []
    for e in c["catharsis"]:
        fd = _fd(e["M_pre"], e["M_post"])
        assert fd == e["official_drop"], "catharsis drop mismatch vs official"
        cev.append({"step": e["step"], "victim_id": e["victim_id"], "M_pre": e["M_pre"],
                    "M_post": e["M_post"], "fractional_drop": fd})
    assert len(cev) == len(h["catharsis_events"])
    d["catharsis_events"] = cev
    d["viability"] = None
    d["viability_D7_paper"] = None
    write_trial(d)
    return out
G.GirardSimulation.run = run

# ---------------- unanimity-triggered runner (Tables 10, 11, ...) ----------------
try:
    import small_n_utils as S
except ImportError:
    S = None

if S is not None:
    _CTX = {"active": None}   # collector for the run_unanimity_triggered call in progress
    _orig_gmt = S.get_modal_target
    @functools.wraps(_orig_gmt)
    def get_modal_target(sim):
        res = _orig_gmt(sim)
        c = _CTX["active"]
        if c is not None:
            s = snapshot(sim)   # state at top of step: after previous step's decay/status, before trigger
            assert (s["modal_agreement"], s["modal_target_id"]) == (float(res[0]), res[1]) or \
                   (len(s["alive"]) < 2 and res == (0.0, None)), "get_modal_target mismatch"
            c["t"].append(len(c["t"]))
            c["alive_ids"].append(s["alive"]); c["received_aggression"].append(s["received"])
            c["eligible_ids"].append(s["eligible_ids"]); c["top_targets"].append(s["top_targets"])
            c["modal_target_id"].append(res[1]); c["chk_modal"].append(float(res[0]))
            c["system_tension_snap"].append(s["M"])
            rec = np.asarray(s["received"], dtype=float)
            c.setdefault("gini", []).append(G.GirardSimulation._gini(rec))
            c.setdefault("entropy", []).append(G.GirardSimulation._entropy(rec))
            c.setdefault("mean_R", []).append(float(np.mean(rec)) if rec.size > 0 else 0.0)
            c.setdefault("top_R", []).append(float(np.max(rec)) if rec.size > 0 else 0.0)
            tot = float(np.sum(rec))
            c.setdefault("share", []).append(float(np.max(rec) / tot) if (tot > 0.0 and rec.size > 0) else 0.0)
            if rec.size >= 2:
                sr = np.sort(rec)[::-1]
                cr = float(sr[0] / sr[1]) if sr[1] > 0.0 else (float(sr[0]) if sr[0] > 0.0 else 0.0)
            else:
                cr = 0.0
            c.setdefault("cr", []).append(cr)
            c.setdefault("sim", sim)
            c["pending"] = {"step": c["t"][-1], "alive": set(s["alive"]), "M_pre": s["M"],
                            "R": dict(zip(s["alive"], s["received"])), "sim": sim}
        return res
    S.get_modal_target = get_modal_target

    _orig_refresh = G.GirardSimulation._refresh_prestige
    @functools.wraps(_orig_refresh)
    def _refresh_prestige(self, *a, **k):
        c = _CTX["active"]
        if c is not None and c.get("pending") is not None and c["pending"]["sim"] is self:
            p = c.pop("pending")   # first call after trigger block in this step
            now_alive = set(self._alive_ids())
            gone = p["alive"] - now_alive
            if gone:
                assert len(gone) == 1
                v = gone.pop()
                post = self._received_aggression_by_alive()   # post-zeroing, same helper as step_expulsion
                M_post = float(sum(post.values())) if post else 0.0
                c["catharsis"].append({"step": p["step"], "victim_id": int(v), "M_pre": p["M_pre"],
                                       "M_post": M_post, "R_victim": float(p["R"][v])})
        return _orig_refresh(self, *a, **k)
    G.GirardSimulation._refresh_prestige = _refresh_prestige

    def _viab(res, modal, n_steps_eff, min_silence, predicate):
        if res["timed_out"]:
            status, se = "timeout", None
        else:
            status, se = S.classify_exhaustion(modal, res["expulsion_steps"], n_steps_eff, res["n_alive"],
                                               min_silence=min_silence)
        return {"min_silence": min_silence, "predicate": predicate,
                "n_expulsions": int(res["n_expulsions"]), "pct_consumed": float(res["pct_consumed"]),
                "n_alive": int(res["n_alive"]), "status": status, "self_exhausted": se,
                "generative": bool(status == "genuine_exhaustion" and res["pct_consumed"] < 0.50
                                   and res["n_expulsions"] >= 1),
                "first_peace": res["first_peace"], "first_reconverge": res["first_reconverge"],
                "peak_modal": float(res["peak_modal"]), "n_fragments": int(res["n_fragments"]),
                "largest_fragment": int(res["largest_fragment"]),
                "expulsion_steps": [int(x) for x in res["expulsion_steps"]],
                "med_gap": (None if res["med_gap"] is None else float(res["med_gap"]))}

    _orig_rut = S.run_unanimity_triggered
    @functools.wraps(_orig_rut)
    def run_unanimity_triggered(*a, **k):
        c = _new_collector(); _CTX["active"] = c
        try:
            res = _orig_rut(*a, **k)
        finally:
            _CTX["active"] = None
        c.pop("pending", None)
        if res["steps_completed"] == 0: raise RuntimeError("zero steps")
        assert c["chk_modal"] == [float(x) for x in c["chk_modal"]]
        T = len(c["t"]); assert T == res["steps_completed"]
        sim = c.get("sim")   # the official runner's own sim object, captured in get_modal_target
        assert sim is not None
        variant = REV_VARIANT[(sim.source, sim.spread)]
        bound = inspect.signature(_orig_rut).bind(*a, **k); bound.apply_defaults()
        cooldown = bound.arguments["cooldown"]
        d = base_meta(sim, variant, "unanimity_adaptive", T, res["timed_out"], c["started_at"],
                      theta=float(S.adaptive_unanimity_threshold(res["N"])), cooldown=int(cooldown))
        d["series"] = {
            "t": c["t"], "n_alive": [len(x) for x in c["alive_ids"]], "alive_ids": c["alive_ids"],
            "system_tension": c["system_tension_snap"], "modal_agreement": c["chk_modal"],
            "eligible_count": [len(x) for x in c["eligible_ids"]], "eligible_ids": c["eligible_ids"],
            "top_targets": c["top_targets"], "received_aggression": c["received_aggression"],
            "aggression_gini": c.get("gini", []), "top_target_share": c.get("share", []),
            "convergence_ratio": c.get("cr", []), "aggression_entropy": c.get("entropy", []),
            "top_R": c.get("top_R", []), "mean_R": c.get("mean_R", []),
            "modal_target_id": c["modal_target_id"],
        }
        assert [e["step"] for e in c["catharsis"]] == list(res["expulsion_steps"]), "expulsion step mismatch"
        d["expulsion_events"] = [{"step": e["step"], "victim_id": e["victim_id"],
                                  "received_aggression": e["R_victim"]} for e in c["catharsis"]]
        d["catharsis_events"] = [{"step": e["step"], "victim_id": e["victim_id"], "M_pre": e["M_pre"],
                                  "M_post": e["M_post"], "fractional_drop": _fd(e["M_pre"], e["M_post"])}
                                 for e in c["catharsis"]]
        d["viability"] = _viab(res, c["chk_modal"], T, 500, "D7")
        assert d["viability"]["status"] == res["status"], "viability status mismatch vs official"
        d["viability_D7_paper"] = _viab(res, c["chk_modal"], T, 2000, "D7-paper")
        write_trial(d)
        return res
    S.run_unanimity_triggered = run_unanimity_triggered

# ---------------------------------------------------------------------------
STARTED = now()
spec = importlib.util.spec_from_file_location("official_script", os.path.join(REPO, ARGS.script))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)      # __name__ != "__main__", so only defs run
# scripts that did `from small_n_utils import run_unanimity_triggered` bind at import; rebind to wrapper
if S is not None and getattr(mod, "run_unanimity_triggered", None) is _orig_rut:
    mod.run_unanimity_triggered = S.run_unanimity_triggered
mod.main()
ENDED = now()

# ---------------------------------------------------------------------------
CLAIMS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claims_v02.json")
claims = json.load(open(CLAIMS_PATH)).get(ENS, {}) if os.path.exists(CLAIMS_PATH) else {}
cells = []
for (N, g, v), tids in CELLS.items():
    cl = claims.get("cells", {}).get(f"N{N}-g{gstr(g)}-v{v}", {})
    cells.append({"table": claims.get("table"), "N": N, "gamma": g, "variant": v, "n": len(tids),
                  "claimed_k": cl.get("claimed_k"), "claimed_rate": cl.get("claimed_rate"),
                  "claimed_median_t95": cl.get("claimed_median_t95"), "trial_ids": tids})
manifest = {"contract_version": CONTRACT, "ensemble_id": ENS, "paper": PAPER, "draft": DRAFT,
            "source_repo": SOURCE_REPO, "source_sha": ARGS.source_sha, "script": ARGS.script,
            "python_version": PYVER, "packages": PACKAGES, "command": ARGS.command,
            "started_at": STARTED, "ended_at": ENDED, "trial_ids": TRIAL_IDS, "cells": cells}
_check_finite(manifest)
with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, allow_nan=False, indent=1)
print(f"[export_v02] wrote {len(TRIAL_IDS)} trials to {OUT}; identical official reruns skipped: {len(RERUNS)}",
      file=sys.stderr)
