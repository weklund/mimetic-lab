#!/usr/bin/env python3
"""Official C-T10 judge (eval contract v0.2.2): Black 2026 Table 10.

Scores ONLY from trial JSON files and manifest.json. Handles incomplete trials,
reruns, and determinism checks per contract v0.2.2. Deterministic, no network.
Does not modify traces.

Fails closed: a missing file, a malformed trace, a non-finite number, or any
exception produces a FAIL result. The result is written atomically.

Usage:
    python3 judge_table10.py [TRACE_DIR] [OUT_JSON]

Exit status is 0 on PASS and 1 on FAIL or INCOMPLETE.
"""
import hashlib
import json
import math
import os
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from judge_common import (
    check_v022_required_fields, is_trial_complete, check_determinism_prefix,
    check_events_prefix
)

JUDGE_VERSION = "0.2.2"
CONTRACT = "eval contract v0.2.2, C-T10"
ACCEPTED_TRACE_VERSIONS = ("0.2", "0.2.1", "0.2.2")

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", ".."))
_DEFAULT_TRACES = os.path.join(_REPO, "eval", "traces", "v0.2", "table10")
_DEFAULT_OUT = os.path.join(_HERE, "table10-result.json")

PINNED_SHA = "89e7bbb57db62e3c830a8ca672a0805080df3970"
N_STEPS = 5000
SEEDS = [42 + r * 1000 for r in range(20)]

# Published Table 10 viability rates (percent of 20 seeds that satisfy D7)
# Contract: Pass iff all 20 seeds are complete and k/20 matches the published percent
PUB_TABLE10 = {
    # (variant, gamma, N): published_percent
    ("AC", 1.05, 5): 25, ("AC", 1.05, 10): 75, ("AC", 1.05, 15): 65, ("AC", 1.05, 20): 90,
    ("AC", 1.05, 25): 95, ("AC", 1.05, 30): 85, ("AC", 1.05, 35): 85, ("AC", 1.05, 40): 90,
    ("AC", 1.50, 5): 0, ("AC", 1.50, 10): 0, ("AC", 1.50, 15): 55, ("AC", 1.50, 20): 60,
    ("AC", 1.50, 25): 90, ("AC", 1.50, 30): 85, ("AC", 1.50, 35): 95, ("AC", 1.50, 40): 95,
    ("AC", 2.00, 5): 0, ("AC", 2.00, 10): 5, ("AC", 2.00, 15): 50, ("AC", 2.00, 20): 65,
    ("AC", 2.00, 25): 85, ("AC", 2.00, 30): 70, ("AC", 2.00, 35): 90, ("AC", 2.00, 40): 80,
    ("RA", 1.05, 5): 0, ("RA", 1.05, 10): 25, ("RA", 1.05, 15): 85, ("RA", 1.05, 20): 85,
    ("RA", 1.05, 25): 60, ("RA", 1.05, 30): 80, ("RA", 1.05, 35): 90, ("RA", 1.05, 40): 80,
    ("RA", 1.50, 5): 0, ("RA", 1.50, 10): 0, ("RA", 1.50, 15): 25, ("RA", 1.50, 20): 65,
    ("RA", 1.50, 25): 80, ("RA", 1.50, 30): 85, ("RA", 1.50, 35): 100, ("RA", 1.50, 40): 90,
    ("RA", 2.00, 5): 0, ("RA", 2.00, 10): 0, ("RA", 2.00, 15): 30, ("RA", 2.00, 20): 75,
    ("RA", 2.00, 25): 80, ("RA", 2.00, 30): 95, ("RA", 2.00, 35): 90, ("RA", 2.00, 40): 65,
}

# Arrays to check for determinism (all required per-step arrays from eval/trial-schema.md)
# Contract names are used; modal_target_id is checked when present
DETERMINISM_ARRAYS = [
    "t", "n_alive", "alive_ids", "system_tension", "modal_agreement",
    "eligible_count", "eligible_ids", "top_targets", "received_aggression",
    "aggression_gini", "top_target_share", "convergence_ratio", "aggression_entropy",
    "top_R", "mean_R"
]

# Every issue the judge can raise
ISSUE_CODES = {
    "fatal": "The judge could not run (missing file, unreadable input, internal error).",
    "manifest.field": "A manifest field is missing or has the wrong value.",
    "ensemble.trial_files": "Trial files on disk do not match expected.",
    "ensemble.cells": "Cell configuration does not match C-T10 published structure.",
    "trial.json": "A trial file is not strict JSON (NaN, Infinity, or an overflowing literal).",
    "trial.metadata": "A trial metadata field is missing or wrong for C-T10.",
    "viability.missing": "viability object is missing or malformed.",
    "viability.d7": "viability D7 computation is inconsistent.",
    "v022.incomplete": "Incomplete trial (timed_out or steps != n_steps_planned) after allowed rerun.",
    "v022.multiple_reruns": "More than one labeled rerun for the same seed.",
    "v022.determinism": "Incomplete trial's arrays do not match completed rerun's prefix.",
    "v022.rerun_invalid": "A rerun does not target an incomplete trial or violates rerun rules.",
}

MAX_ISSUES_PER_TRIAL = 20


def issue(code, detail, where=None):
    assert code in ISSUE_CODES, code
    return dict(code=code, where=where, detail=detail)


def _reject_constant(name):
    raise ValueError(f"non-finite JSON constant {name} (contract: use null)")


def _parse_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"non-finite number {text!r} (contract: use null)")
    return value


def load_json_strict(raw):
    """Parse JSON, rejecting NaN, Infinity, and overflowing literals."""
    return json.loads(raw, parse_float=_parse_float, parse_constant=_reject_constant)


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _display_path(path):
    absolute = os.path.abspath(path)
    if absolute == _REPO or absolute.startswith(_REPO + os.sep):
        return os.path.relpath(absolute, _REPO)
    return path


def check_viability_d7(viability, trial_id):
    """Check that viability D7 is correctly computed.
    
    D7: status == "genuine_exhaustion" AND pct_consumed < 0.50 AND n_expulsions >= 1
    Returns (is_valid, issues_list, is_generative)
    """
    issues = []
    if not isinstance(viability, dict):
        issues.append(issue("viability.missing", "viability is not a dict", trial_id))
        return False, issues, None
    
    status = viability.get("status")
    pct_consumed = viability.get("pct_consumed")
    n_expulsions = viability.get("n_expulsions")
    generative = viability.get("generative")
    
    # Check required fields
    if status not in ("genuine_exhaustion", "still_cycling", "censored", "no_expulsions", "timeout"):
        issues.append(issue("viability.missing", f"invalid status {status!r}", trial_id))
    if not _is_num(pct_consumed) or pct_consumed < 0 or pct_consumed > 1:
        issues.append(issue("viability.missing", f"invalid pct_consumed {pct_consumed!r}", trial_id))
    if not _is_int(n_expulsions) or n_expulsions < 0:
        issues.append(issue("viability.missing", f"invalid n_expulsions {n_expulsions!r}", trial_id))
    if not isinstance(generative, bool):
        issues.append(issue("viability.missing", f"generative is not a bool", trial_id))
    
    if issues:
        return False, issues, None
    
    # Recompute D7
    d7_holds = (status == "genuine_exhaustion" and pct_consumed < 0.50 and n_expulsions >= 1)
    
    if d7_holds != generative:
        issues.append(issue(
            "viability.d7",
            f"D7 recomputed as {d7_holds} but generative={generative} "
            f"(status={status}, pct_consumed={pct_consumed}, n_expulsions={n_expulsions})",
            trial_id
        ))
        return False, issues, d7_holds
    
    return True, [], d7_holds


def check_trial_metadata(tr, stem, expect_variant, expect_gamma, expect_n):
    """Check trial metadata for C-T10."""
    issues = []
    
    if not isinstance(tr, dict):
        issues.append(issue("trial.metadata", "trial is not a JSON object", stem))
        return issues
    
    if tr.get("trial_id") != stem:
        issues.append(issue("trial.metadata", f"trial_id {tr.get('trial_id')!r} != filename", stem))
    
    contract_version = tr.get("contract_version")
    if contract_version not in ACCEPTED_TRACE_VERSIONS:
        issues.append(issue(
            "trial.metadata",
            f"contract_version={contract_version!r} not in {ACCEPTED_TRACE_VERSIONS}",
            stem
        ))
    
    # For v0.2.2, check required fields
    if contract_version == "0.2.2":
        check_v022_required_fields(tr, issues, where=stem)
    
    # C-T10 expected values
    if tr.get("source_sha") != PINNED_SHA:
        issues.append(issue("trial.metadata", f"source_sha {tr.get('source_sha')!r} != {PINNED_SHA}", stem))
    if tr.get("script") != "exp_small_n_viability.py":
        issues.append(issue("trial.metadata", f"script {tr.get('script')!r} != exp_small_n_viability.py", stem))
    if tr.get("expulsion_mode") != "unanimity_adaptive":
        issues.append(issue("trial.metadata", f"expulsion_mode {tr.get('expulsion_mode')!r} != unanimity_adaptive", stem))
    if tr.get("n_steps_planned") != N_STEPS:
        issues.append(issue("trial.metadata", f"n_steps_planned {tr.get('n_steps_planned')!r} != {N_STEPS}", stem))
    
    if tr.get("variant") != expect_variant:
        issues.append(issue("trial.metadata", f"variant {tr.get('variant')!r} != {expect_variant}", stem))
    if tr.get("gamma") != expect_gamma:
        issues.append(issue("trial.metadata", f"gamma {tr.get('gamma')!r} != {expect_gamma}", stem))
    if tr.get("N") != expect_n:
        issues.append(issue("trial.metadata", f"N {tr.get('N')!r} != {expect_n}", stem))
    
    seed = tr.get("seed")
    if not _is_int(seed) or seed not in SEEDS:
        issues.append(issue("trial.metadata", f"seed {seed!r} not in official seeds", stem))
    
    return issues


@dataclass
class CellResult:
    """Result for one (variant, gamma, N) cell."""
    variant: str
    gamma: float
    N: int
    n_seeds: int
    published_percent: int
    
    # Completeness tracking
    n_complete: int = 0
    n_incomplete: int = 0
    incomplete_seeds: List[int] = field(default_factory=list)
    
    # Viability tracking (only for complete trials)
    n_viable: int = 0
    viable_seeds: List[int] = field(default_factory=list)
    
    # Rerun tracking
    n_reruns: int = 0
    rerun_pairs: List[Tuple[int, str, str]] = field(default_factory=list)  # (seed, incomplete_id, rerun_id)
    determinism_failures: List[Tuple[int, Dict]] = field(default_factory=list)  # (seed, mismatches)
    
    # Issues
    issues: List[dict] = field(default_factory=list)
    
    def verdict(self) -> str:
        """Return PASS, FAIL, or INCOMPLETE."""
        if self.n_incomplete > 0:
            return "INCOMPLETE"
        if self.n_complete == self.n_seeds:
            computed_pct = int((self.n_viable / self.n_seeds) * 100)
            if computed_pct == self.published_percent:
                return "PASS"
        return "FAIL"
    
    def to_dict(self):
        return {
            "variant": self.variant,
            "gamma": self.gamma,
            "N": self.N,
            "n_seeds": self.n_seeds,
            "published_percent": self.published_percent,
            "published_k": self.published_percent * self.n_seeds // 100,
            "n_complete": self.n_complete,
            "n_incomplete": self.n_incomplete,
            "incomplete_seeds": sorted(self.incomplete_seeds),
            "n_viable": self.n_viable,
            "viable_seeds": sorted(self.viable_seeds),
            "computed_percent": int((self.n_viable / self.n_seeds) * 100) if self.n_complete == self.n_seeds else None,
            "n_reruns": self.n_reruns,
            "determinism_failures": len(self.determinism_failures),
            "verdict": self.verdict(),
            "issues": self.issues,
        }


def judge(trace_dir):
    """Judge Table 10 traces."""
    issues = []
    
    try:
        man = load_json_strict(read_bytes(os.path.join(trace_dir, "manifest.json")))
    except Exception as exc:
        return failure_result(trace_dir, f"Cannot read manifest: {exc}")
    
    if not isinstance(man, dict):
        issues.append(issue("manifest.field", "manifest is not a JSON object"))
        return result_from_issues(trace_dir, man, [], issues)
    
    if man.get("contract_version") not in ACCEPTED_TRACE_VERSIONS:
        issues.append(issue("manifest.field", f"contract_version={man.get('contract_version')!r}"))
    if man.get("source_sha") != PINNED_SHA:
        issues.append(issue("manifest.field", f"source_sha={man.get('source_sha')!r}"))
    
    # Load all trials
    tdir = os.path.join(trace_dir, "trials")
    if not os.path.isdir(tdir):
        issues.append(issue("fatal", "trials/ directory not found"))
        return result_from_issues(trace_dir, man, [], issues)
    
    files = sorted(f for f in os.listdir(tdir) if f.endswith(".json"))
    
    # Organize trials by cell and track reruns
    cells = {}
    trials = {}
    trial_sha256 = {}
    
    for fname in files:
        stem = fname[:-5]
        fpath = os.path.join(tdir, fname)
        raw = read_bytes(fpath)
        trial_sha256[fname] = hashlib.sha256(raw).hexdigest()
        
        try:
            tr = load_json_strict(raw)
        except ValueError as exc:
            issues.append(issue("trial.json", str(exc), stem))
            continue
        
        if not isinstance(tr, dict):
            issues.append(issue("trial.json", "not a JSON object", stem))
            continue
        
        variant = tr.get("variant")
        gamma = tr.get("gamma")
        N = tr.get("N")
        seed = tr.get("seed")
        
        if not (isinstance(variant, str) and _is_num(gamma) and _is_int(N) and _is_int(seed)):
            issues.append(issue("trial.metadata", "variant/gamma/N/seed missing or invalid", stem))
            continue
        
        cell_key = (variant, gamma, N)
        # LM and RL are report-only, not claimed. Don't fail on their presence.
        if cell_key not in PUB_TABLE10:
            if variant not in ("LM", "RL"):
                issues.append(issue("ensemble.cells", f"cell {cell_key} not in published Table 10", stem))
            continue  # Skip LM/RL and invalid cells
        
        if cell_key not in cells:
            cells[cell_key] = CellResult(
                variant=variant, gamma=gamma, N=N,
                n_seeds=len(SEEDS),
                published_percent=PUB_TABLE10[cell_key]
            )
        
        trials[stem] = tr
    
    # Check metadata and completeness
    for stem, tr in trials.items():
        variant = tr["variant"]
        gamma = tr["gamma"]
        N = tr["N"]
        cell_key = (variant, gamma, N)
        
        if cell_key not in cells:
            continue  # Already reported as invalid cell
        
        cell = cells[cell_key]
        cell.issues.extend(check_trial_metadata(tr, stem, variant, gamma, N))
        
        # Check viability
        viability = tr.get("viability")
        if viability is None:
            cell.issues.append(issue("viability.missing", "viability is null", stem))
            continue
        
        valid, viab_issues, is_generative = check_viability_d7(viability, stem)
        cell.issues.extend(viab_issues)
        
        # Check completeness
        is_complete, reason = is_trial_complete(tr)
        rerun_of = tr.get("rerun_of")
        
        if not is_complete:
            # This is an incomplete trial
            if rerun_of is not None:
                # This trial itself is marked as a rerun but is incomplete - error
                cell.issues.append(issue(
                    "v022.rerun_invalid",
                    f"trial marked as rerun (rerun_of={rerun_of!r}) but is incomplete: {reason}",
                    stem
                ))
            cell.n_incomplete += 1
            cell.incomplete_seeds.append(tr["seed"])
        else:
            # Complete trial
            cell.n_complete += 1
            if is_generative:
                cell.n_viable += 1
                cell.viable_seeds.append(tr["seed"])
            
            if rerun_of is not None:
                # This is a completed rerun
                cell.n_reruns += 1
                cell.rerun_pairs.append((tr["seed"], rerun_of, stem))
    
    # Check rerun rules and determinism
    for cell_key, cell in cells.items():
        # Group trials by seed
        seed_trials = {}
        for stem, tr in trials.items():
            if (tr["variant"], tr["gamma"], tr["N"]) != cell_key:
                continue
            seed = tr["seed"]
            if seed not in seed_trials:
                seed_trials[seed] = []
            seed_trials[seed].append((stem, tr))
        
        # BLOCKER 2: Check that all 20 official seeds are present (plus at most one rerun each)
        present_seeds = set(seed_trials.keys())
        expected_seeds = set(SEEDS)
        missing_seeds = expected_seeds - present_seeds
        unexpected_seeds = present_seeds - expected_seeds
        
        if missing_seeds:
            cell.issues.append(issue(
                "ensemble.cells",
                f"Cell {cell_key} missing seeds: {sorted(missing_seeds)}",
                f"{cell_key}"
            ))
        if unexpected_seeds:
            cell.issues.append(issue(
                "ensemble.cells",
                f"Cell {cell_key} has unexpected seeds: {sorted(unexpected_seeds)}",
                f"{cell_key}"
            ))
        
        # Check each seed
        for seed, seed_trial_list in seed_trials.items():
            if len(seed_trial_list) == 1:
                # Single trial for this seed
                stem, tr = seed_trial_list[0]
                is_complete, reason = is_trial_complete(tr)
                rerun_of = tr.get("rerun_of")
                
                # BLOCKER 3: A complete trial with rerun_of but no incomplete original is invalid
                if rerun_of is not None:
                    cell.issues.append(issue(
                        "v022.rerun_invalid",
                        f"trial {stem} has rerun_of={rerun_of!r} but no incomplete trial found for seed {seed}",
                        stem
                    ))
                elif not is_complete:
                    # Incomplete, no rerun provided
                    pass  # Already tracked in n_incomplete
            else:
                # Multiple trials for this seed - check rerun rules
                incomplete = [t for t in seed_trial_list if not is_trial_complete(t[1])[0]]
                reruns = [t for t in seed_trial_list if t[1].get("rerun_of") is not None]
                
                if len(reruns) > 1:
                    cell.issues.append(issue(
                        "v022.multiple_reruns",
                        f"seed {seed} has {len(reruns)} reruns, max 1 allowed",
                        f"{cell_key}-seed{seed}"
                    ))
                    # Don't process reruns if there are multiple - this is a hard fail
                    continue
                
                if len(reruns) == 1:
                    # Check determinism
                    rerun_stem, rerun_tr = reruns[0]
                    rerun_of_id = rerun_tr["rerun_of"]
                    
                    # Find the incomplete trial this reruns
                    incomplete_tr = None
                    for stem, tr in seed_trial_list:
                        if stem == rerun_of_id:
                            incomplete_tr = tr
                            break
                    
                    if incomplete_tr is None:
                        cell.issues.append(issue(
                            "v022.rerun_invalid",
                            f"rerun {rerun_stem} references {rerun_of_id!r} which is not found",
                            rerun_stem
                        ))
                    else:
                        # Check that rerun_of was actually incomplete
                        was_incomplete, _ = is_trial_complete(incomplete_tr)
                        if was_incomplete:
                            cell.issues.append(issue(
                                "v022.rerun_invalid",
                                f"rerun {rerun_stem} references {rerun_of_id!r} which was already complete",
                                rerun_stem
                            ))
                        
                        # Check determinism - arrays and events
                        rerun_is_complete, _ = is_trial_complete(rerun_tr)
                        incomplete_steps = incomplete_tr.get("steps_completed", 0)
                        
                        matches, mismatches = check_determinism_prefix(
                            incomplete_tr, rerun_tr, DETERMINISM_ARRAYS, tdir
                        )
                        events_match, event_mismatches = check_events_prefix(
                            incomplete_tr, rerun_tr, incomplete_steps
                        )
                        
                        all_mismatches = dict(mismatches)
                        if not events_match:
                            for event_type in event_mismatches:
                                all_mismatches[event_type] = "event mismatch"
                        
                        if all_mismatches:
                            cell.determinism_failures.append((seed, all_mismatches))
                            cell.issues.append(issue(
                                "v022.determinism",
                                f"seed {seed}: {list(all_mismatches.keys())} do not match",
                                rerun_stem
                            ))
                            # BLOCKER 5: Failed prefix - don't count rerun in n_complete/n_viable
                            # It was already counted, so decrement
                            if rerun_is_complete:
                                cell.n_complete -= 1
                                # Check if it was counted as viable
                                valid, _, is_gen = check_viability_d7(rerun_tr.get("viability"), rerun_stem)
                                if valid and is_gen and seed in cell.viable_seeds:
                                    cell.n_viable -= 1
                                    cell.viable_seeds.remove(seed)
                        elif rerun_is_complete and not all_mismatches:
                            # Successful rerun: remove this seed from incomplete list
                            if seed in cell.incomplete_seeds:
                                cell.incomplete_seeds.remove(seed)
                                cell.n_incomplete -= 1
                                # Rerun was already counted as complete and viable above
    
    # Overall verdict - BLOCKER 1: require all 48 published AC/RA cells
    all_issues = list(issues)
    for cell in cells.values():
        all_issues.extend(cell.issues)
        # Raise v022.incomplete for each still-incomplete seed
        for seed in cell.incomplete_seeds:
            all_issues.append(issue(
                "v022.incomplete",
                f"Seed {seed} incomplete after allowed rerun",
                f"{cell.variant}/g{cell.gamma}/N{cell.N}/s{seed}"
            ))
    
    # Check that all 48 claimed cells are present
    expected_cells = set(PUB_TABLE10.keys())
    present_cells = set(cells.keys())
    missing_cells = expected_cells - present_cells
    
    if missing_cells:
        for cell_key in sorted(missing_cells):
            all_issues.append(issue(
                "ensemble.cells",
                f"Required cell {cell_key} is missing from ensemble"
            ))
    
    any_incomplete = any(c.n_incomplete > 0 for c in cells.values())
    all_pass = all(c.verdict() == "PASS" for c in cells.values())
    all_cells_present = len(missing_cells) == 0
    
    # Critical issues that should cause FAIL even if there are incomplete trials
    critical_issue_codes = {"v022.multiple_reruns", "v022.rerun_invalid", "trial.metadata", "viability.d7"}
    has_critical_issues = any(i["code"] in critical_issue_codes for i in all_issues)
    
    if has_critical_issues or not all_cells_present:
        verdict = "FAIL"
    elif any_incomplete:
        verdict = "INCOMPLETE"
    elif all_pass and not all_issues:
        verdict = "PASS"
    else:
        verdict = "FAIL"
    
    return {
        "judge": "judge_table10.py",
        "judge_version": JUDGE_VERSION,
        "contract": CONTRACT,
        "trace_dir": _display_path(trace_dir),
        "pinned_sha": PINNED_SHA,
        "manifest_sha": man.get("source_sha"),
        "verdict": verdict,
        "n_cells": len(cells),
        "n_trials": len(trials),
        "checks": {
            "all_48_cells_present": all_cells_present,
            "any_cell_incomplete": any_incomplete,
            "all_cells_pass": all_pass,
            "no_issues": len(all_issues) == 0,
        },
        "statement": (
            "A C-T10 PASS is a judgment of Maxwell Black's model at pinned SHA "
            f"{PINNED_SHA}. It upgrades claim B4 only, never G6 or Girard."
        ),
        "cells": [c.to_dict() for c in sorted(cells.values(), key=lambda c: (c.variant, c.gamma, c.N))],
        "issues": all_issues,
        "trial_file_sha256": trial_sha256,
    }


def result_from_issues(trace_dir, man, cells, issues):
    """Create a FAIL result from issues."""
    return {
        "judge": "judge_table10.py",
        "judge_version": JUDGE_VERSION,
        "contract": CONTRACT,
        "trace_dir": _display_path(trace_dir),
        "verdict": "FAIL",
        "cells": [c.to_dict() for c in cells] if cells else [],
        "issues": issues,
    }


def failure_result(trace_dir, reason):
    """Create a FAIL result with a fatal error."""
    return {
        "judge": "judge_table10.py",
        "judge_version": JUDGE_VERSION,
        "contract": CONTRACT,
        "trace_dir": _display_path(trace_dir),
        "verdict": "FAIL",
        "fatal_error": reason,
        "issues": [issue("fatal", reason)],
    }


def write_result_atomic(path, result):
    """Write strict JSON via temp file and rename."""
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
    """Print a summary of the result."""
    print(f"Verdict: {result['verdict']}")
    print(f"Cells: {result.get('n_cells', 0)}")
    print(f"Trials: {result.get('n_trials', 0)}")
    
    if result.get("fatal_error"):
        print(f"FATAL: {result['fatal_error']}")
    
    for issue in result.get("issues", [])[:20]:
        where = f" ({issue['where']})" if issue.get("where") else ""
        print(f"  {issue['code']}: {issue['detail']}{where}")
    
    for cell in result.get("cells", []):
        v_str = f"{cell['variant']}/{cell['gamma']}/{cell['N']}"
        status = f"{cell['n_complete']} complete, {cell['n_incomplete']} incomplete"
        viable = f"{cell['n_viable']}/{cell['n_seeds']} viable ({cell.get('computed_percent', '?')}%)"
        pub = f"published {cell['published_percent']}%"
        print(f"  {v_str}: {status}, {viable}, {pub} -> {cell['verdict']}")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    trace_dir = argv[0] if argv else _DEFAULT_TRACES
    out = argv[1] if len(argv) > 1 else _DEFAULT_OUT
    
    try:
        result = judge(trace_dir)
    except Exception as exc:
        result = failure_result(trace_dir, f"{type(exc).__name__}: {exc}")
    
    try:
        write_result_atomic(out, result)
    except ValueError as exc:
        result = failure_result(trace_dir, f"result is not strict JSON: {exc}")
        write_result_atomic(out, result)
    
    print_summary(result)
    return 0 if result.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
