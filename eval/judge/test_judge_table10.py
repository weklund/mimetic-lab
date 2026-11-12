"""Tests for the C-T10 judge (contract v0.2.2).

Tests focus on incomplete trial handling, reruns, determinism checks,
and the INCOMPLETE verdict.
"""
import contextlib
import copy
import hashlib
import io
import json
import os
import tempfile
import unittest

import judge_table10 as J10
import judge_common as JC

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def patch_n_steps(n_steps=8):
    """Decorator to patch J10.N_STEPS for test fixtures."""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            saved = J10.N_STEPS
            try:
                J10.N_STEPS = n_steps
                return func(self, *args, **kwargs)
            finally:
                J10.N_STEPS = saved
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def make_trial(variant, gamma, N, seed, n_steps_planned=8, steps_completed=None,
               timed_out=False, generative=True, timeout_seconds=600.0, host="test-host",
               rerun_of=None, expulsion_steps=None):
    """Build a minimal C-T10 trial.
    
    Defaults to short 8-step series for fast ensemble tests. Completeness means
    steps_completed == n_steps_planned and timed_out == false.
    """
    if steps_completed is None:
        steps_completed = n_steps_planned
    if expulsion_steps is None:
        expulsion_steps = [2, 4] if generative and steps_completed > 4 else []
    
    trial_id = f"table10-g{gamma:.2f}-N{N}-v{variant}-s{seed}"
    
    # All required per-step series per eval/trial-schema.md and DETERMINISM_ARRAYS
    # top_targets: avoid self-targets (agent i targets agent (i+1) % N)
    targets = [(i + 1) % N for i in range(N)]
    series = {
        "t": list(range(steps_completed)),
        "n_alive": [N] * steps_completed,
        "alive_ids": [list(range(N))] * steps_completed,
        "system_tension": [1.0 + 0.01 * i for i in range(steps_completed)],
        "modal_agreement": [0.8] * steps_completed,
        "eligible_count": [N] * steps_completed,
        "eligible_ids": [list(range(N))] * steps_completed,
        "top_targets": [targets[:] for _ in range(steps_completed)],
        "received_aggression": [[0.1] * N] * steps_completed,
        "aggression_gini": [0.1] * steps_completed,
        "top_target_share": [0.15] * steps_completed,
        "convergence_ratio": [0.9] * steps_completed,
        "aggression_entropy": [2.5] * steps_completed,
        "top_R": [0.05] * steps_completed,
        "mean_R": [0.03] * steps_completed,
    }
    
    viability = {
        "min_silence": 500,
        "predicate": "D7",
        "n_expulsions": 2 if generative else 0,
        "pct_consumed": 0.3 if generative else 0.6,
        "n_alive": N - 2 if generative else N,
        "status": "genuine_exhaustion" if generative else "still_cycling",
        "self_exhausted": generative,
        "generative": generative,
        "first_peace": None,
        "first_reconverge": None,
        "peak_modal": 0.95,
        "n_fragments": 1,
        "largest_fragment": N,
        "expulsion_steps": expulsion_steps,
        "med_gap": 500 if generative else None,
    }
    
    return {
        "contract_version": "0.2.2",
        "trial_id": trial_id,
        "ensemble_id": "table10",
        "script": "exp_small_n_viability.py",
        "source_repo": "https://github.com/maxwell-black/mimetic-desire-simulation",
        "source_sha": J10.PINNED_SHA,
        "paper": "Black 2026, A Computational Test of Girard's Scapegoat Mechanism",
        "draft": "18",
        "variant": variant,
        "source_mode": "object" if variant in ("AC", "LM") else "status",
        "spread_mode": "attention" if variant in ("AC", "RA") else "linear",
        "N": N,
        "k": max(6, min(int(N * 0.12), 20)),
        "rewire_prob": 0.15,
        "alpha": 0.15,
        "gamma": gamma,
        "aggression_decay": 0.03,
        "expulsion_mode": "unanimity_adaptive",
        "expulsion_threshold": None,
        "unanimity_threshold": 0.95 if N >= 20 else min(0.95, (N - 1) / N),
        "unanimity_cooldown": 5,
        "n_steps_planned": n_steps_planned,
        "steps_completed": steps_completed,
        "seed": seed,
        "timed_out": timed_out,
        "timeout_seconds": timeout_seconds,
        "host": host,
        "rerun_of": rerun_of,
        "python_version": "3.12.0",
        "packages": {"numpy": "2.0.0", "networkx": "3.3", "scipy": "1.14.0"},
        "command": "python exp_small_n_viability.py",
        "started_at": "2026-11-12T10:00:00-05:00",
        "ended_at": "2026-11-12T10:10:00-05:00",
        "series": series,
        "expulsion_events": [],
        "catharsis_events": [],
        "viability": viability,
        "viability_D7_paper": None,
    }


def make_ensemble_small():
    """Build a small test ensemble: AC at gamma=1.05, N=5 (published 25% = 5/20 viable).
    
    NOTE: This creates only 1 cell. Per BLOCKER 1, a full official C-T10 ensemble
    requires all 48 published cells. This helper is for testing specific behaviors
    but will FAIL the overall C-T10 verdict due to missing cells.
    """
    trials = {}
    for i, seed in enumerate(J10.SEEDS):
        # Make 5 viable, 15 non-viable to match published 25%
        generative = i < 5
        trial = make_trial("AC", 1.05, 5, seed, generative=generative)
        trials[trial["trial_id"]] = trial
    
    manifest = {
        "contract_version": "0.2.2",
        "ensemble_id": "table10",
        "source_sha": J10.PINNED_SHA,
        "script": "exp_small_n_viability.py",
        "trial_ids": sorted(trials.keys()),
    }
    
    return manifest, trials


def make_ensemble_full():
    """Build a complete test ensemble with all 48 published AC/RA cells.
    
    Each cell has exactly 20 seeds with the published viability rate.
    """
    trials = {}
    for (variant, gamma, N), pub_pct in J10.PUB_TABLE10.items():
        # Calculate how many viable trials needed for this published percent
        n_viable = (pub_pct * 20) // 100
        for i, seed in enumerate(J10.SEEDS):
            generative = i < n_viable
            trial = make_trial(variant, gamma, N, seed, generative=generative)
            trials[trial["trial_id"]] = trial
    
    manifest = {
        "contract_version": "0.2.2",
        "ensemble_id": "table10",
        "source_sha": J10.PINNED_SHA,
        "script": "exp_small_n_viability.py",
        "trial_ids": sorted(trials.keys()),
    }
    
    return manifest, trials


class Table10NStepsValidation(unittest.TestCase):
    """Tests for n_steps_planned == 5000 validation."""
    
    def run_judge(self, manifest, trials):
        with tempfile.TemporaryDirectory() as d:
            traces = os.path.join(d, "table10")
            os.makedirs(os.path.join(traces, "trials"))
            
            write_text(os.path.join(traces, "manifest.json"), json.dumps(manifest))
            for stem, trial in trials.items():
                write_text(os.path.join(traces, "trials", stem + ".json"), json.dumps(trial))
            
            out = os.path.join(d, "result.json")
            with contextlib.redirect_stdout(io.StringIO()):
                code = J10.main([traces, out])
            
            result = J10.load_json_strict(J10.read_bytes(out))
        
        return result, code
    
    def test_short_n_steps_fails_without_patch(self):
        """Full 48-cell ensemble at n_steps_planned = steps_completed = 8 FAILS without N_STEPS patch.
        
        Judge requires n_steps_planned == 5000. Do NOT patch N_STEPS for this test.
        """
        manifest, trials = make_ensemble_full()
        
        # All trials have n_steps_planned = steps_completed = 8 from make_trial defaults
        # This should FAIL because judge requires n_steps_planned == 5000
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(code, 1)
        
        # Should have trial.metadata issues
        metadata_issues = [i for i in result["issues"] if i["code"] == "trial.metadata" and "n_steps_planned" in i["detail"]]
        self.assertGreater(len(metadata_issues), 0)
    
    def test_default_fixture_passes_with_patch(self):
        """Default fixture with N_STEPS patched to 8 PASSes."""
        saved_n_steps = J10.N_STEPS
        try:
            J10.N_STEPS = 8  # Patch to match fixture
            manifest, trials = make_ensemble_full()
            
            result, code = self.run_judge(manifest, trials)
            
            self.assertEqual(result["verdict"], "PASS")
            self.assertEqual(code, 0)
        finally:
            J10.N_STEPS = saved_n_steps


class Table10Basic(unittest.TestCase):
    """Basic C-T10 judge tests."""
    
    def run_judge(self, manifest, trials):
        """Run judge on an ensemble."""
        with tempfile.TemporaryDirectory() as d:
            traces = os.path.join(d, "table10")
            os.makedirs(os.path.join(traces, "trials"))
            
            write_text(os.path.join(traces, "manifest.json"), json.dumps(manifest))
            for stem, trial in trials.items():
                write_text(os.path.join(traces, "trials", stem + ".json"), json.dumps(trial))
            
            out = os.path.join(d, "result.json")
            with contextlib.redirect_stdout(io.StringIO()):
                code = J10.main([traces, out])
            
            result = J10.load_json_strict(J10.read_bytes(out))
        
        return result, code
    
    @patch_n_steps(8)
    def test_full_ensemble_passes(self):
        """BLOCKER 1: All 48 cells required for PASS."""
        manifest, trials = make_ensemble_full()
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "PASS", f"Issues: {result.get('issues', [])}")
        self.assertEqual(code, 0)
        self.assertEqual(len(result["cells"]), 48)
        self.assertTrue(result["checks"]["all_48_cells_present"])
        
        # Check a few cells
        ac_105_5 = next(c for c in result["cells"] if c["variant"] == "AC" and c["gamma"] == 1.05 and c["N"] == 5)
        self.assertEqual(ac_105_5["n_complete"], 20)
        self.assertEqual(ac_105_5["n_incomplete"], 0)
        self.assertEqual(ac_105_5["computed_percent"], 25)
        self.assertEqual(ac_105_5["published_percent"], 25)
        self.assertEqual(ac_105_5["verdict"], "PASS")
    
    @patch_n_steps(8)
    def test_single_cell_fails_missing_cells(self):
        """BLOCKER 1: A single correct cell must not yield C-T10 PASS."""
        manifest, trials = make_ensemble_small()
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(code, 1)
        self.assertFalse(result["checks"]["all_48_cells_present"])
        
        # The one cell present should be correct
        cell = result["cells"][0]
        self.assertEqual(cell["n_viable"], 5)
        self.assertEqual(cell["computed_percent"], 25)
        self.assertEqual(cell["verdict"], "PASS")  # Cell passes but ensemble fails
        
        # Check for missing cell issues
        missing_issues = [i for i in result["issues"] if "missing from ensemble" in i["detail"]]
        self.assertEqual(len(missing_issues), 47)  # 48 - 1 = 47 missing
    
    def test_wrong_viability_count_fails(self):
        """A cell with wrong k/20 fails."""
        manifest, trials = make_ensemble_full()
        
        # Change one trial in AC/1.05/N5 to make 6 viable instead of 5
        trial_id = "table10-g1.05-N5-vAC-s5042"
        trials[trial_id]["viability"]["generative"] = True
        trials[trial_id]["viability"]["n_expulsions"] = 2
        trials[trial_id]["viability"]["pct_consumed"] = 0.3
        trials[trial_id]["viability"]["status"] = "genuine_exhaustion"
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(code, 1)
        
        # Find the affected cell
        cell = next(c for c in result["cells"] if c["variant"] == "AC" and c["gamma"] == 1.05 and c["N"] == 5)
        self.assertEqual(cell["n_viable"], 6)
        self.assertEqual(cell["computed_percent"], 30)
        self.assertEqual(cell["verdict"], "FAIL")


class Table10UnlabeledRerun(unittest.TestCase):
    """BLOCKER 2: Tests for unlabeled reruns (more than one rerun_of=null for a seed)."""
    
    def run_judge(self, manifest, trials):
        with tempfile.TemporaryDirectory() as d:
            traces = os.path.join(d, "table10")
            os.makedirs(os.path.join(traces, "trials"))
            
            write_text(os.path.join(traces, "manifest.json"), json.dumps(manifest))
            for stem, trial in trials.items():
                write_text(os.path.join(traces, "trials", stem + ".json"), json.dumps(trial))
            
            out = os.path.join(d, "result.json")
            with contextlib.redirect_stdout(io.StringIO()):
                code = J10.main([traces, out])
            
            result = J10.load_json_strict(J10.read_bytes(out))
        
        return result, code
    
    @patch_n_steps(8)
    def test_incomplete_original_plus_unlabeled_complete_first_order(self):
        """Incomplete original + unlabeled complete second run, complete stem first -> FAIL.
        
        Both filename orders must FAIL with ensemble.cells issue.
        """
        manifest, trials = make_ensemble_full()
        
        # Make original incomplete
        orig_id = "table10-g1.05-N5-vAC-s42"
        trials[orig_id]["timed_out"] = True
        trials[orig_id]["steps_completed"] = 5
        for key in trials[orig_id]["series"]:
            trials[orig_id]["series"][key] = trials[orig_id]["series"][key][:5]
        
        # Add unlabeled complete second run (rerun_of=null, not a labeled rerun)
        # Use filename that sorts after original (z prefix)
        second_id = "table10-g1.05-N5-vAC-s42-zunlabeled"
        second_trial = make_trial("AC", 1.05, 5, 42, generative=True)
        second_trial["trial_id"] = second_id
        second_trial["rerun_of"] = None  # NOT a labeled rerun
        trials[second_id] = second_trial
        manifest["trial_ids"].append(second_id)
        
        result, code = self.run_judge(manifest, trials)
        
        # Must FAIL (not PASS or INCOMPLETE)
        self.assertEqual(result["verdict"], "FAIL")
        
        # Must have ensemble.cells issue about multiple originals
        cell = next(c for c in result["cells"] if c["variant"] == "AC" and c["gamma"] == 1.05 and c["N"] == 5)
        multi_orig_issues = [i for i in cell["issues"] 
                            if i["code"] == "ensemble.cells" and "rerun_of=null" in i["detail"] and "42" in i["detail"]]
        self.assertGreater(len(multi_orig_issues), 0)
    
    @patch_n_steps(8)
    def test_incomplete_original_plus_unlabeled_complete_reverse_order(self):
        """Incomplete original + unlabeled complete second run, complete stem reversed -> FAIL.
        
        Both filename orders must FAIL with ensemble.cells issue.
        """
        manifest, trials = make_ensemble_full()
        
        # Make original incomplete
        orig_id = "table10-g1.05-N5-vAC-s42"
        trials[orig_id]["timed_out"] = True
        trials[orig_id]["steps_completed"] = 5
        for key in trials[orig_id]["series"]:
            trials[orig_id]["series"][key] = trials[orig_id]["series"][key][:5]
        
        # Add unlabeled complete second run (rerun_of=null)
        # Use filename that sorts BEFORE original (a prefix)
        second_id = "table10-g1.05-N5-vAC-s42-aunlabeled"
        second_trial = make_trial("AC", 1.05, 5, 42, generative=True)
        second_trial["trial_id"] = second_id
        second_trial["rerun_of"] = None  # NOT a labeled rerun
        trials[second_id] = second_trial
        manifest["trial_ids"].append(second_id)
        
        result, code = self.run_judge(manifest, trials)
        
        # Must FAIL (not PASS or INCOMPLETE)
        self.assertEqual(result["verdict"], "FAIL")
        
        # Must have ensemble.cells issue about multiple originals
        cell = next(c for c in result["cells"] if c["variant"] == "AC" and c["gamma"] == 1.05 and c["N"] == 5)
        multi_orig_issues = [i for i in cell["issues"] 
                            if i["code"] == "ensemble.cells" and "rerun_of=null" in i["detail"] and "42" in i["detail"]]
        self.assertGreater(len(multi_orig_issues), 0)


class Table10Seeds(unittest.TestCase):
    """BLOCKER 2: Tests for seed validation."""
    
    def run_judge(self, manifest, trials):
        with tempfile.TemporaryDirectory() as d:
            traces = os.path.join(d, "table10")
            os.makedirs(os.path.join(traces, "trials"))
            
            write_text(os.path.join(traces, "manifest.json"), json.dumps(manifest))
            for stem, trial in trials.items():
                write_text(os.path.join(traces, "trials", stem + ".json"), json.dumps(trial))
            
            out = os.path.join(d, "result.json")
            with contextlib.redirect_stdout(io.StringIO()):
                code = J10.main([traces, out])
            
            result = J10.load_json_strict(J10.read_bytes(out))
        
        return result, code
    
    @patch_n_steps(8)
    def test_duplicate_seed_no_missing_fails(self):
        """BLOCKER 2: Two complete originals for seed 42 with no seed 1042 must FAIL.
        
        Two complete trials with rerun_of=null for the same seed is a structural defect.
        It is not a valid rerun. The cell must not report PASS.
        """
        manifest, trials = make_ensemble_full()
        
        # Add a second complete original for seed 42 (both with rerun_of=null)
        original_id = "table10-g1.05-N5-vAC-s42"
        trial_42_dup = make_trial("AC", 1.05, 5, 42, generative=True)
        trial_42_dup["trial_id"] = "table10-g1.05-N5-vAC-s42-dup"
        trial_42_dup["rerun_of"] = None  # Not a labeled rerun
        trials[trial_42_dup["trial_id"]] = trial_42_dup
        
        # Remove seed 1042
        del trials["table10-g1.05-N5-vAC-s1042"]
        
        manifest["trial_ids"] = sorted(trials.keys())
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        
        # Check for missing seed issue
        cell = next(c for c in result["cells"] if c["variant"] == "AC" and c["gamma"] == 1.05 and c["N"] == 5)
        self.assertNotEqual(cell["verdict"], "PASS", "Cell must not PASS with duplicate originals and missing seed")
        
        # Check for seed structure issues
        missing_seed_issues = [i for i in cell["issues"] if "missing seeds" in i["detail"] and "1042" in i["detail"]]
        self.assertGreater(len(missing_seed_issues), 0, "Must report missing seed 1042")
        
        # Check for duplicate originals issue (rerun_of=null)
        duplicate_originals_issues = [i for i in cell["issues"] 
                                     if "rerun_of=null" in i["detail"] and "42" in i["detail"]]
        self.assertGreater(len(duplicate_originals_issues), 0, "Must report duplicate rerun_of=null trials for seed 42")


class Table10Incomplete(unittest.TestCase):
    """Tests for incomplete trials and INCOMPLETE verdict."""
    
    def run_judge(self, manifest, trials):
        with tempfile.TemporaryDirectory() as d:
            traces = os.path.join(d, "table10")
            os.makedirs(os.path.join(traces, "trials"))
            
            write_text(os.path.join(traces, "manifest.json"), json.dumps(manifest))
            for stem, trial in trials.items():
                write_text(os.path.join(traces, "trials", stem + ".json"), json.dumps(trial))
            
            out = os.path.join(d, "result.json")
            with contextlib.redirect_stdout(io.StringIO()):
                code = J10.main([traces, out])
            
            result = J10.load_json_strict(J10.read_bytes(out))
        
        return result, code
    
    @patch_n_steps(8)
    def test_timed_out_trial_is_incomplete(self):
        """A trial with timed_out=true is incomplete."""
        manifest, trials = make_ensemble_full()
        
        # Make one trial timed out
        trial_id = "table10-g1.05-N5-vAC-s42"
        trials[trial_id]["timed_out"] = True
        trials[trial_id]["steps_completed"] = 5
        # Truncate series
        for key in trials[trial_id]["series"]:
            trials[trial_id]["series"][key] = trials[trial_id]["series"][key][:5]
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "INCOMPLETE")
        self.assertEqual(code, 1)
        
        cell = next(c for c in result["cells"] if c["variant"] == "AC" and c["gamma"] == 1.05 and c["N"] == 5)
        self.assertEqual(cell["n_complete"], 19)
        self.assertEqual(cell["n_incomplete"], 1)
        self.assertIn(42, cell["incomplete_seeds"])
        self.assertEqual(cell["verdict"], "INCOMPLETE")
    
    @patch_n_steps(8)
    def test_incomplete_steps_is_incomplete(self):
        """A trial with steps_completed < n_steps_planned is incomplete."""
        manifest, trials = make_ensemble_full()
        
        # Make one trial incomplete
        trial_id = "table10-g1.05-N5-vAC-s42"
        trials[trial_id]["timed_out"] = False
        trials[trial_id]["steps_completed"] = 5
        # Truncate series
        for key in trials[trial_id]["series"]:
            trials[trial_id]["series"][key] = trials[trial_id]["series"][key][:5]
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "INCOMPLETE")
        cell = next(c for c in result["cells"] if c["variant"] == "AC" and c["gamma"] == 1.05 and c["N"] == 5)
        self.assertEqual(cell["n_incomplete"], 1)
        self.assertEqual(cell["verdict"], "INCOMPLETE")
    
    @patch_n_steps(8)
    def test_incomplete_trial_not_counted_as_viable_or_nonviable(self):
        """An incomplete trial is not counted in k/20."""
        manifest, trials = make_ensemble_small()
        
        # Make one viable trial incomplete
        trial_id = "table10-g1.05-N5-vAC-s42"  # This was viable
        trials[trial_id]["timed_out"] = True
        trials[trial_id]["steps_completed"] = 5
        for key in trials[trial_id]["series"]:
            trials[trial_id]["series"][key] = trials[trial_id]["series"][key][:5]
        
        result, code = self.run_judge(manifest, trials)
        
        cell = result["cells"][0]
        # Should have 19 complete (not 20), and n_viable should not count the incomplete one
        self.assertEqual(cell["n_complete"], 19)
        self.assertEqual(cell["n_viable"], 4)  # 5 were viable, but 1 is incomplete
        self.assertIsNone(cell["computed_percent"])  # Can't compute percent with incomplete
        self.assertEqual(cell["verdict"], "INCOMPLETE")
    
    @patch_n_steps(8)
    def test_second_timeout_yields_incomplete(self):
        """A labeled rerun that is itself incomplete yields overall INCOMPLETE, not FAIL.
        
        First run incomplete, labeled rerun also incomplete -> overall INCOMPLETE,
        issue v022.incomplete (not v022.rerun_invalid), seed appears once in incomplete_seeds.
        """
        manifest, trials = make_ensemble_full()
        
        # Make original trial incomplete
        incomplete_id = "table10-g1.05-N5-vAC-s42"
        trials[incomplete_id]["timed_out"] = True
        trials[incomplete_id]["steps_completed"] = 5
        for key in trials[incomplete_id]["series"]:
            trials[incomplete_id]["series"][key] = trials[incomplete_id]["series"][key][:5]
        
        # Add an incomplete rerun
        rerun_id = "table10-g1.05-N5-vAC-s42-rerun"
        rerun = make_trial("AC", 1.05, 5, 42, n_steps_planned=8, steps_completed=6, timed_out=True, generative=True)
        rerun["trial_id"] = rerun_id
        rerun["rerun_of"] = incomplete_id
        trials[rerun_id] = rerun
        manifest["trial_ids"].append(rerun_id)
        
        result, code = self.run_judge(manifest, trials)
        
        # Should be INCOMPLETE, not FAIL
        self.assertEqual(result["verdict"], "INCOMPLETE")
        
        cell = next(c for c in result["cells"] if c["variant"] == "AC" and c["gamma"] == 1.05 and c["N"] == 5)
        self.assertEqual(cell["n_incomplete"], 1)
        self.assertIn(42, cell["incomplete_seeds"])
        
        # Check that seed 42 appears only once in incomplete_seeds
        self.assertEqual(cell["incomplete_seeds"].count(42), 1)
        
        # Should have v022.incomplete issue, not v022.rerun_invalid
        incomplete_issues = [i for i in result["issues"] if i["code"] == "v022.incomplete"]
        rerun_invalid_issues = [i for i in result["issues"] if i["code"] == "v022.rerun_invalid"]
        self.assertGreater(len(incomplete_issues), 0)
        self.assertEqual(len(rerun_invalid_issues), 0)


class Table10Reruns(unittest.TestCase):
    """Tests for reruns and determinism checks."""
    
    def run_judge(self, manifest, trials):
        with tempfile.TemporaryDirectory() as d:
            traces = os.path.join(d, "table10")
            os.makedirs(os.path.join(traces, "trials"))
            
            write_text(os.path.join(traces, "manifest.json"), json.dumps(manifest))
            for stem, trial in trials.items():
                write_text(os.path.join(traces, "trials", stem + ".json"), json.dumps(trial))
            
            out = os.path.join(d, "result.json")
            with contextlib.redirect_stdout(io.StringIO()):
                code = J10.main([traces, out])
            
            result = J10.load_json_strict(J10.read_bytes(out))
        
        return result, code
    
    @patch_n_steps(8)
    def test_successful_rerun_with_determinism_check(self):
        """A rerun that matches the incomplete prefix passes determinism check."""
        manifest, trials = make_ensemble_full()
        
        # Make original trial incomplete
        incomplete_id = "table10-g1.05-N5-vAC-s42"
        trials[incomplete_id]["timed_out"] = True
        trials[incomplete_id]["steps_completed"] = 5
        # Truncate series
        for key in trials[incomplete_id]["series"]:
            trials[incomplete_id]["series"][key] = trials[incomplete_id]["series"][key][:5]
        
        # Add a completed rerun
        rerun_id = "table10-g1.05-N5-vAC-s42-rerun"
        rerun = make_trial("AC", 1.05, 5, 42, generative=True)
        rerun["trial_id"] = rerun_id
        rerun["rerun_of"] = incomplete_id
        # Make sure series prefix matches (both are short 8-step trials now)
        trials[rerun_id] = rerun
        manifest["trial_ids"].append(rerun_id)
        
        result, code = self.run_judge(manifest, trials)
        
        # Should pass because rerun is complete and matches
        self.assertEqual(result["verdict"], "PASS")
        cell = next(c for c in result["cells"] if c["variant"] == "AC" and c["gamma"] == 1.05 and c["N"] == 5)
        self.assertEqual(cell["n_complete"], 20)  # 19 original complete + 1 rerun
        self.assertEqual(cell["n_incomplete"], 0)
        self.assertEqual(cell["n_reruns"], 1)
        self.assertEqual(cell["determinism_failures"], 0)
    
    @patch_n_steps(8)
    def test_rerun_determinism_mismatch_keeps_seed_incomplete(self):
        """A rerun whose prefix doesn't match keeps the seed incomplete."""
        manifest, trials = make_ensemble_full()
        
        # Make original trial incomplete
        incomplete_id = "table10-g1.05-N5-vAC-s42"
        trials[incomplete_id]["timed_out"] = True
        trials[incomplete_id]["steps_completed"] = 5
        for key in trials[incomplete_id]["series"]:
            trials[incomplete_id]["series"][key] = trials[incomplete_id]["series"][key][:5]
        
        # Add a rerun with a mismatch
        rerun_id = "table10-g1.05-N5-vAC-s42-rerun"
        rerun = make_trial("AC", 1.05, 5, 42, generative=True)
        rerun["trial_id"] = rerun_id
        rerun["rerun_of"] = incomplete_id
        # Introduce a mismatch in modal_agreement at step 2
        rerun["series"]["modal_agreement"][2] = 0.9  # Different from 0.8
        trials[rerun_id] = rerun
        manifest["trial_ids"].append(rerun_id)
        
        result, code = self.run_judge(manifest, trials)
        
        # Should be INCOMPLETE because determinism check failed
        self.assertEqual(result["verdict"], "INCOMPLETE")
        cell = next(c for c in result["cells"] if c["variant"] == "AC" and c["gamma"] == 1.05 and c["N"] == 5)
        self.assertEqual(cell["n_incomplete"], 1)  # Seed 42 stays incomplete
        self.assertEqual(cell["n_complete"], 19)  # Failed rerun not counted
        self.assertEqual(cell["determinism_failures"], 1)
        
        # Check that there's a determinism issue
        issues = [i for i in result["issues"] if i["code"] == "v022.determinism"]
        self.assertEqual(len(issues), 1)
    
    @patch_n_steps(8)
    def test_multiple_reruns_for_same_seed_fails(self):
        """At most one labeled rerun per seed."""
        manifest, trials = make_ensemble_small()
        
        # Make original incomplete
        incomplete_id = "table10-g1.05-N5-vAC-s42"
        trials[incomplete_id]["timed_out"] = True
        trials[incomplete_id]["steps_completed"] = 3000
        for key in trials[incomplete_id]["series"]:
            trials[incomplete_id]["series"][key] = trials[incomplete_id]["series"][key][:3000]
        
        # Add TWO reruns
        for i in range(2):
            rerun_id = f"table10-g1.05-N5-vAC-s42-rerun{i+1}"
            rerun = make_trial("AC", 1.05, 5, 42, generative=True)
            rerun["trial_id"] = rerun_id
            rerun["rerun_of"] = incomplete_id
            trials[rerun_id] = rerun
            manifest["trial_ids"].append(rerun_id)
        
        result, code = self.run_judge(manifest, trials)
        
        # Should fail with multiple_reruns issue
        self.assertEqual(result["verdict"], "FAIL")
        issues = [i for i in result["issues"] if i["code"] == "v022.multiple_reruns"]
        self.assertEqual(len(issues), 1)
    
    def test_rerun_of_complete_trial_is_invalid(self):
        """BLOCKER 3: A rerun should only be for an incomplete trial."""
        manifest, trials = make_ensemble_small()
        
        # Original trial is complete
        original_id = "table10-g1.05-N5-vAC-s42"
        # Keep it complete (timed_out=False, steps_completed=5000)
        
        # Add a rerun claiming to rerun it
        rerun_id = "table10-g1.05-N5-vAC-s42-rerun"
        rerun = make_trial("AC", 1.05, 5, 42, generative=True)
        rerun["trial_id"] = rerun_id
        rerun["rerun_of"] = original_id
        trials[rerun_id] = rerun
        manifest["trial_ids"].append(rerun_id)
        
        result, code = self.run_judge(manifest, trials)
        
        # Should have an issue that rerun targets a complete trial
        issues = [i for i in result["issues"] if i["code"] == "v022.rerun_invalid"]
        self.assertGreater(len(issues), 0)
    
    def test_single_trial_with_rerun_of_is_invalid(self):
        """BLOCKER 3: Single trial with rerun_of but no incomplete original is invalid."""
        manifest, trials = make_ensemble_small()
        
        # Replace seed 42's trial with a "rerun" that has no incomplete original
        del trials["table10-g1.05-N5-vAC-s42"]
        
        rerun_id = "table10-g1.05-N5-vAC-s42-rerun"
        rerun = make_trial("AC", 1.05, 5, 42, generative=True)
        rerun["trial_id"] = rerun_id
        rerun["rerun_of"] = "table10-g1.05-N5-vAC-s42-original"  # Non-existent
        trials[rerun_id] = rerun
        manifest["trial_ids"] = sorted(trials.keys())
        
        result, code = self.run_judge(manifest, trials)
        
        # Should have v022.rerun_invalid issue
        issues = [i for i in result["issues"] if i["code"] == "v022.rerun_invalid"]
        self.assertGreater(len(issues), 0)


class Table10CriticalIssues(unittest.TestCase):
    """BLOCKER 3: Any issue except v022.incomplete and v022.determinism is fatal."""
    
    def run_judge(self, manifest, trials):
        with tempfile.TemporaryDirectory() as d:
            traces = os.path.join(d, "table10")
            os.makedirs(os.path.join(traces, "trials"))
            
            write_text(os.path.join(traces, "manifest.json"), json.dumps(manifest))
            for stem, trial in trials.items():
                write_text(os.path.join(traces, "trials", stem + ".json"), json.dumps(trial))
            
            out = os.path.join(d, "result.json")
            with contextlib.redirect_stdout(io.StringIO()):
                code = J10.main([traces, out])
            
            result = J10.load_json_strict(J10.read_bytes(out))
        
        return result, code
    
    @patch_n_steps(8)
    def test_ghost_manifest_entry_plus_timeout_fails(self):
        """Ghost manifest entry + one timed-out seed -> FAIL, not INCOMPLETE."""
        manifest, trials = make_ensemble_full()
        
        # Add a ghost trial_id
        manifest["trial_ids"].append("table10-g1.05-N5-vAC-s99")
        
        # Make one trial timed out
        trial_id = "table10-g1.05-N5-vAC-s42"
        trials[trial_id]["timed_out"] = True
        trials[trial_id]["steps_completed"] = 5
        for key in trials[trial_id]["series"]:
            trials[trial_id]["series"][key] = trials[trial_id]["series"][key][:5]
        
        result, code = self.run_judge(manifest, trials)
        
        # Must FAIL, not INCOMPLETE (ensemble.trial_files cannot be fixed by rerun)
        self.assertEqual(result["verdict"], "FAIL")
        
        # Must have ensemble.trial_files issue
        file_issues = [i for i in result["issues"] if i["code"] == "ensemble.trial_files"]
        self.assertGreater(len(file_issues), 0)
    
    @patch_n_steps(8)
    def test_wrong_manifest_sha_plus_timeout_fails(self):
        """Wrong manifest source_sha + one timed-out seed -> FAIL, not INCOMPLETE."""
        manifest, trials = make_ensemble_full()
        
        # Set wrong source_sha
        manifest["source_sha"] = "0000000000000000000000000000000000000000"
        
        # Make one trial timed out
        trial_id = "table10-g1.05-N5-vAC-s42"
        trials[trial_id]["timed_out"] = True
        trials[trial_id]["steps_completed"] = 5
        for key in trials[trial_id]["series"]:
            trials[trial_id]["series"][key] = trials[trial_id]["series"][key][:5]
        
        result, code = self.run_judge(manifest, trials)
        
        # Must FAIL, not INCOMPLETE (manifest.field cannot be fixed by rerun)
        self.assertEqual(result["verdict"], "FAIL")
        
        # Must have manifest.field issue
        manifest_issues = [i for i in result["issues"] if i["code"] == "manifest.field"]
        self.assertGreater(len(manifest_issues), 0)


class Table10ManifestValidation(unittest.TestCase):
    """Tests for manifest and trial file validation."""
    
    def run_judge(self, manifest, trials):
        with tempfile.TemporaryDirectory() as d:
            traces = os.path.join(d, "table10")
            os.makedirs(os.path.join(traces, "trials"))
            
            write_text(os.path.join(traces, "manifest.json"), json.dumps(manifest))
            for stem, trial in trials.items():
                write_text(os.path.join(traces, "trials", stem + ".json"), json.dumps(trial))
            
            out = os.path.join(d, "result.json")
            with contextlib.redirect_stdout(io.StringIO()):
                code = J10.main([traces, out])
            
            result = J10.load_json_strict(J10.read_bytes(out))
        
        return result, code
    
    def test_extra_trial_file_on_disk(self):
        """Trial file on disk but not in manifest trial_ids raises ensemble.trial_files.
        
        On full 48-cell fixture, extra file -> overall FAIL with ensemble.trial_files.
        """
        manifest, trials = make_ensemble_full()
        
        # Add an extra trial file that's not in manifest
        extra_trial = make_trial("AC", 1.05, 5, 99, generative=False)
        extra_trial["trial_id"] = "table10-g1.05-N5-vAC-s99"
        trials[extra_trial["trial_id"]] = extra_trial
        # Don't add to manifest["trial_ids"]
        
        result, code = self.run_judge(manifest, trials)
        
        # Should FAIL with ensemble.trial_files issue
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(code, 1)
        file_issues = [i for i in result["issues"] if i["code"] == "ensemble.trial_files"]
        self.assertGreater(len(file_issues), 0)
    
    @patch_n_steps(8)
    def test_missing_trial_file_on_disk(self):
        """Trial in manifest but missing on disk raises ensemble.trial_files.
        
        On full 48-cell fixture, ghost trial_id -> overall FAIL with ensemble.trial_files.
        """
        manifest, trials = make_ensemble_full()
        
        # Add a ghost trial_id to manifest but don't create the file
        manifest["trial_ids"].append("table10-g1.05-N5-vAC-s99")
        
        result, code = self.run_judge(manifest, trials)
        
        # Should FAIL with ensemble.trial_files issue
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(code, 1)
        file_issues = [i for i in result["issues"] if i["code"] == "ensemble.trial_files"]
        self.assertGreater(len(file_issues), 0)
    
    @patch_n_steps(8)
    def test_lm_rl_presence_does_not_fail(self):
        """LM and RL trials are report-only; their presence must not fail C-T10.
        
        They must be reported (not dropped) but do not affect the verdict.
        Absence is not required for PASS.
        """
        manifest, trials = make_ensemble_full()
        
        # Add some LM and RL trials
        lm_rl_count = 0
        for variant in ["LM", "RL"]:
            for seed in [42, 1042]:
                trial = make_trial(variant, 1.05, 5, seed, generative=False)
                trials[trial["trial_id"]] = trial
                manifest["trial_ids"].append(trial["trial_id"])
                lm_rl_count += 1
        
        result, code = self.run_judge(manifest, trials)
        
        # Should still PASS - LM/RL presence doesn't affect verdict
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(code, 0)
        
        # Should have exactly 48 AC/RA cells
        self.assertEqual(len(result["cells"]), 48)
        
        # LM/RL should be reported, not dropped
        self.assertIn("report_only", result)
        self.assertEqual(len(result["report_only"]), lm_rl_count)
        
        # Check that they're in report_only
        lm_trials = [t for t in result["report_only"] if t["variant"] == "LM"]
        rl_trials = [t for t in result["report_only"] if t["variant"] == "RL"]
        self.assertEqual(len(lm_trials), 2)
        self.assertEqual(len(rl_trials), 2)
    
    @patch_n_steps(8)
    def test_no_lm_rl_still_passes(self):
        """Absence of LM/RL is not required for PASS."""
        manifest, trials = make_ensemble_full()
        
        result, code = self.run_judge(manifest, trials)
        
        # Should PASS without LM/RL
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(code, 0)
        self.assertEqual(len(result["cells"]), 48)
        self.assertEqual(len(result.get("report_only", [])), 0)
    
    @patch_n_steps(8)
    def test_missing_required_series_fails(self):
        """A trial missing required series arrays is a structural FAIL."""
        manifest, trials = make_ensemble_full()
        
        # Remove a required series array from one trial
        trial_id = "table10-g1.05-N5-vAC-s42"
        del trials[trial_id]["series"]["top_target_share"]
        
        result, code = self.run_judge(manifest, trials)
        
        # Should FAIL (structural/metadata failure)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(code, 1)
        
        # Check for trial.metadata issue about missing series
        metadata_issues = [i for i in result["issues"] 
                          if i["code"] == "trial.metadata" and "top_target_share" in i["detail"]]
        self.assertGreater(len(metadata_issues), 0)


class Table10NPZ(unittest.TestCase):
    """Tests for NPZ series offload."""
    
    def run_judge(self, manifest, trials, npz_files=None):
        with tempfile.TemporaryDirectory() as d:
            traces = os.path.join(d, "table10")
            trials_dir = os.path.join(traces, "trials")
            os.makedirs(trials_dir)
            
            write_text(os.path.join(traces, "manifest.json"), json.dumps(manifest))
            for stem, trial in trials.items():
                write_text(os.path.join(trials_dir, stem + ".json"), json.dumps(trial))
            
            # Write NPZ files if provided
            if npz_files and HAS_NUMPY:
                for npz_name, arrays in npz_files.items():
                    npz_path = os.path.join(trials_dir, npz_name)
                    np.savez(npz_path, **arrays)
            
            out = os.path.join(d, "result.json")
            with contextlib.redirect_stdout(io.StringIO()):
                code = J10.main([traces, out])
            
            result = J10.load_json_strict(J10.read_bytes(out))
        
        return result, code
    
    @unittest.skipUnless(HAS_NUMPY, "numpy not available")
    @patch_n_steps(8)
    def test_npz_prefix_match(self):
        """NPZ offload: prefix match with real .npz file."""
        manifest, trials = make_ensemble_full()
        
        # Make original trial incomplete with NPZ offload
        incomplete_id = "table10-g1.05-N5-vAC-s42"
        incomplete_trial = trials[incomplete_id]
        incomplete_trial["timed_out"] = True
        incomplete_trial["steps_completed"] = 5
        
        # Create NPZ arrays (truncated to 5 steps)
        npz_arrays = {}
        for key, val in incomplete_trial["series"].items():
            if key == "t":
                npz_arrays[key] = np.array(val[:5])
            elif key in ["alive_ids", "eligible_ids", "top_targets", "received_aggression"]:
                # Nested arrays
                npz_arrays[key] = np.array([np.array(x) for x in val[:5]], dtype=object)
            else:
                npz_arrays[key] = np.array(val[:5])
        
        # Replace series with NPZ reference
        incomplete_trial["series"] = {"$npz": f"{incomplete_id}.npz"}
        
        # Add a completed rerun
        rerun_id = "table10-g1.05-N5-vAC-s42-rerun"
        rerun = make_trial("AC", 1.05, 5, 42, generative=True)
        rerun["trial_id"] = rerun_id
        rerun["rerun_of"] = incomplete_id
        trials[rerun_id] = rerun
        manifest["trial_ids"].append(rerun_id)
        
        npz_files = {f"{incomplete_id}.npz": npz_arrays}
        
        result, code = self.run_judge(manifest, trials, npz_files)
        
        # Should PASS
        self.assertEqual(result["verdict"], "PASS")
        cell = next(c for c in result["cells"] if c["variant"] == "AC" and c["gamma"] == 1.05 and c["N"] == 5)
        self.assertEqual(cell["determinism_failures"], 0)
    
    @unittest.skipUnless(HAS_NUMPY, "numpy not available")
    @patch_n_steps(8)
    def test_npz_prefix_mismatch(self):
        """NPZ offload: prefix mismatch detected."""
        manifest, trials = make_ensemble_full()
        
        # Make original trial incomplete with NPZ offload
        incomplete_id = "table10-g1.05-N5-vAC-s42"
        incomplete_trial = trials[incomplete_id]
        incomplete_trial["timed_out"] = True
        incomplete_trial["steps_completed"] = 5
        
        # Create NPZ arrays with a mismatch
        npz_arrays = {}
        for key, val in incomplete_trial["series"].items():
            if key == "t":
                npz_arrays[key] = np.array(val[:5])
            elif key in ["alive_ids", "eligible_ids", "top_targets", "received_aggression"]:
                npz_arrays[key] = np.array([np.array(x) for x in val[:5]], dtype=object)
            else:
                arr = np.array(val[:5])
                if key == "modal_agreement":
                    arr[2] = 0.9  # Introduce mismatch
                npz_arrays[key] = arr
        
        incomplete_trial["series"] = {"$npz": f"{incomplete_id}.npz"}
        
        # Add a completed rerun
        rerun_id = "table10-g1.05-N5-vAC-s42-rerun"
        rerun = make_trial("AC", 1.05, 5, 42, generative=True)
        rerun["trial_id"] = rerun_id
        rerun["rerun_of"] = incomplete_id
        trials[rerun_id] = rerun
        manifest["trial_ids"].append(rerun_id)
        
        npz_files = {f"{incomplete_id}.npz": npz_arrays}
        
        result, code = self.run_judge(manifest, trials, npz_files)
        
        # Should be INCOMPLETE due to determinism failure
        self.assertEqual(result["verdict"], "INCOMPLETE")
        cell = next(c for c in result["cells"] if c["variant"] == "AC" and c["gamma"] == 1.05 and c["N"] == 5)
        self.assertEqual(cell["determinism_failures"], 1)
    
    @patch_n_steps(8)
    @patch_n_steps(8)
    def test_npz_missing_file_fails(self):
        """Complete trial with {"$npz": "nothere.npz"} -> FAIL with trial.metadata."""
        manifest, trials = make_ensemble_full()
        
        # Make a trial with NPZ reference to missing file
        trial_id = "table10-g1.05-N5-vAC-s42"
        trials[trial_id]["series"] = {"$npz": "nothere.npz"}
        
        result, code = self.run_judge(manifest, trials)
        
        # Should FAIL (not skip, not PASS)
        self.assertEqual(result["verdict"], "FAIL")
        
        # Should have trial.metadata issue about loading series
        metadata_issues = [i for i in result["issues"] 
                          if i["code"] == "trial.metadata" and "load series" in i["detail"]]
        self.assertGreater(len(metadata_issues), 0)
    
    @unittest.skipUnless(HAS_NUMPY, "numpy not available")
    @patch_n_steps(8)
    @unittest.skipUnless(HAS_NUMPY, "numpy not available")
    def test_npz_missing_required_series(self):
        """NPZ offload missing required array = trial.metadata FAIL."""
        manifest, trials = make_ensemble_full()
        
        # Make one trial with NPZ that omits top_target_share
        trial_id = "table10-g1.05-N5-vAC-s42"
        trial = trials[trial_id]
        
        # Create NPZ arrays without top_target_share
        npz_arrays = {}
        for key, val in trial["series"].items():
            if key == "top_target_share":
                continue  # Omit this required array
            elif key == "t":
                npz_arrays[key] = np.array(val)
            elif key in ["alive_ids", "eligible_ids", "top_targets", "received_aggression"]:
                npz_arrays[key] = np.array([np.array(x) for x in val], dtype=object)
            else:
                npz_arrays[key] = np.array(val)
        
        # Replace series with NPZ reference
        trial["series"] = {"$npz": f"{trial_id}.npz"}
        
        npz_files = {f"{trial_id}.npz": npz_arrays}
        
        result, code = self.run_judge(manifest, trials, npz_files)
        
        # Should FAIL with trial.metadata issue
        self.assertEqual(result["verdict"], "FAIL")
        metadata_issues = [i for i in result["issues"] 
                          if i["code"] == "trial.metadata" and "top_target_share" in i["detail"]]
        self.assertGreater(len(metadata_issues), 0)
    
    @patch_n_steps(8)
    def test_series_wrong_length_fails(self):
        """Trial with mean_R of length 1 (not steps_completed) -> FAIL with trial.metadata."""
        manifest, trials = make_ensemble_full()
        
        # Make one trial with wrong-length series
        trial_id = "table10-g1.05-N5-vAC-s42"
        trials[trial_id]["series"]["mean_R"] = [0.03]  # Length 1, should be 8
        
        result, code = self.run_judge(manifest, trials)
        
        # Should FAIL
        self.assertEqual(result["verdict"], "FAIL")
        
        # Should have trial.metadata issue about length
        metadata_issues = [i for i in result["issues"] 
                          if i["code"] == "trial.metadata" and "length" in i["detail"] and "mean_R" in i["detail"]]
        self.assertGreater(len(metadata_issues), 0)
    
    @patch_n_steps(8)
    def test_empty_inline_series_fails(self):
        """Trial with series: {} -> FAIL with trial.metadata, not PASS, not zero issues.
        
        Empty dict is falsy, so guard must be 'is not None' not just truthiness check.
        """
        manifest, trials = make_ensemble_full()
        
        # Make one trial with empty inline series
        trial_id = "table10-g1.05-N5-vAC-s42"
        trials[trial_id]["series"] = {}
        
        result, code = self.run_judge(manifest, trials)
        
        # Should FAIL (not PASS, not zero issues)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertNotEqual(code, 0)
        
        # Should have trial.metadata issues for missing required arrays
        metadata_issues = [i for i in result["issues"] if i["code"] == "trial.metadata"]
        self.assertGreater(len(metadata_issues), 0, "Must have trial.metadata issues for missing arrays")
        
        # Check at least one mentions a missing required array
        missing_array_issues = [i for i in metadata_issues if "missing" in i["detail"].lower()]
        self.assertGreater(len(missing_array_issues), 0, "Must report missing required arrays")
    
    @patch_n_steps(8)
    @unittest.skipUnless(HAS_NUMPY, "numpy not available")
    def test_empty_npz_fails(self):
        """Trial offloading to real empty .npz (no arrays) -> FAIL with trial.metadata."""
        manifest, trials = make_ensemble_full()
        
        # Make one trial with NPZ reference to empty file
        trial_id = "table10-g1.05-N5-vAC-s42"
        trial = trials[trial_id]
        
        # Create empty NPZ (no arrays)
        npz_arrays = {}
        
        # Replace series with NPZ reference
        trial["series"] = {"$npz": f"{trial_id}.npz"}
        
        npz_files = {f"{trial_id}.npz": npz_arrays}
        
        result, code = self.run_judge(manifest, trials, npz_files)
        
        # Should FAIL
        self.assertEqual(result["verdict"], "FAIL")
        
        # Should have trial.metadata issues for missing required arrays
        metadata_issues = [i for i in result["issues"] if i["code"] == "trial.metadata"]
        self.assertGreater(len(metadata_issues), 0, "Must have trial.metadata issues for missing arrays")

    @unittest.skipUnless(HAS_NUMPY, "numpy not available")
    @patch_n_steps(8)
    def test_npz_object_array_int64_passes(self):
        """BLOCKER: Official export_v02.py NPZ layout (object array of 1-d np.int64) must PASS.
        
        export_v02.py writes nested ID series as: o = np.empty(len(v), dtype=object);
        for i, row in enumerate(v): o[i] = np.asarray(row, dtype=np.int64).reshape(-1)
        This yields object array where each element is a 1-d np.int64 array.
        
        Ragged case: alive 5 then 4 after a death, targets aligned and not self.
        """
        manifest, trials = make_ensemble_full()
        
        trial_id = "table10-g1.05-N5-vAC-s42"
        trial = trials[trial_id]
        
        # Build ragged series: 5 alive at step 0, 4 alive after step 3 (death at step 3)
        # Steps 0-2: all 5 alive
        # Step 3: agent 4 dies
        # Steps 4-7: 4 alive (0,1,2,3)
        series = trial["series"]
        for t in range(8):
            if t < 3:
                series["alive_ids"][t] = [0, 1, 2, 3, 4]
                series["n_alive"][t] = 5
                series["eligible_ids"][t] = [0, 1, 2, 3, 4]
                series["eligible_count"][t] = 5
                # No self-targets: agent i -> (i+1) % 5
                series["top_targets"][t] = [1, 2, 3, 4, 0]
            else:
                # Agent 4 died
                series["alive_ids"][t] = [0, 1, 2, 3]
                series["n_alive"][t] = 4
                series["eligible_ids"][t] = [0, 1, 2, 3]
                series["eligible_count"][t] = 4
                # No self-targets: agent i -> (i+1) % 4
                series["top_targets"][t] = [1, 2, 3, 0]
        
        # Create NPZ with official export_v02.py layout: object array of 1-d np.int64 arrays
        npz_arrays = {}
        for key, val in series.items():
            if key in ("alive_ids", "eligible_ids", "top_targets"):
                # Exact export_v02.py layout for nested ID series
                o = np.empty(len(val), dtype=object)
                for i, row in enumerate(val):
                    o[i] = np.asarray(row, dtype=np.int64).reshape(-1)
                npz_arrays[key] = o
            elif key == "received_aggression":
                # Same layout, but float64
                o = np.empty(len(val), dtype=object)
                for i, row in enumerate(val):
                    o[i] = np.asarray(row, dtype=np.float64).reshape(-1)
                npz_arrays[key] = o
            elif key in ("t", "n_alive", "eligible_count"):
                npz_arrays[key] = np.array(val, dtype=np.int64)
            else:
                npz_arrays[key] = np.array(val, dtype=np.float64)
        
        # Replace series with NPZ reference
        trial["series"] = {"$npz": f"{trial_id}.npz"}
        
        npz_files = {f"{trial_id}.npz": npz_arrays}
        result, code = self.run_judge(manifest, trials, npz_files)
        
        # Must PASS with ragged object array of int64
        self.assertEqual(result["verdict"], "PASS")
        
        # Check cell verdict
        cell = next(c for c in result["cells"] if c["variant"] == "AC" and c["gamma"] == 1.05 and c["N"] == 5)
        self.assertEqual(cell["verdict"], "PASS")

    @unittest.skipUnless(HAS_NUMPY, "numpy not available")
    @patch_n_steps(8)
    def test_npz_object_array_self_target_fails(self):
        """BLOCKER: Official NPZ layout with self-target must FAIL with ids.self_target.
        
        Same official export_v02.py layout, but with a self-target. Must FAIL with
        ids.self_target, not only series.shape at step 0.
        """
        manifest, trials = make_ensemble_full()
        
        trial_id = "table10-g1.05-N5-vAC-s42"
        trial = trials[trial_id]
        
        # Build series with self-target at step 3: agent 1 targets itself
        series = trial["series"]
        series["alive_ids"][3] = [0, 1, 2]
        series["n_alive"][3] = 3
        series["eligible_ids"][3] = [0, 1, 2]
        series["eligible_count"][3] = 3
        series["top_targets"][3] = [2, 1, 0]  # agent 1 -> 1 (self-target)
        
        # Create NPZ with official export_v02.py layout
        npz_arrays = {}
        for key, val in series.items():
            if key in ("alive_ids", "eligible_ids", "top_targets"):
                o = np.empty(len(val), dtype=object)
                for i, row in enumerate(val):
                    o[i] = np.asarray(row, dtype=np.int64).reshape(-1)
                npz_arrays[key] = o
            elif key == "received_aggression":
                o = np.empty(len(val), dtype=object)
                for i, row in enumerate(val):
                    o[i] = np.asarray(row, dtype=np.float64).reshape(-1)
                npz_arrays[key] = o
            elif key in ("t", "n_alive", "eligible_count"):
                npz_arrays[key] = np.array(val, dtype=np.int64)
            else:
                npz_arrays[key] = np.array(val, dtype=np.float64)
        
        trial["series"] = {"$npz": f"{trial_id}.npz"}
        
        npz_files = {f"{trial_id}.npz": npz_arrays}
        result, code = self.run_judge(manifest, trials, npz_files)
        
        # Must FAIL with ids.self_target
        self.assertEqual(result["verdict"], "FAIL")
        issues = [i for i in result["issues"]
                 if i["code"] == "trial.metadata" and "ids.self_target" in i["detail"]]
        self.assertGreater(len(issues), 0)

    @unittest.skipUnless(HAS_NUMPY, "numpy not available")
    @patch_n_steps(8)
    def test_npz_uniform_object_array_passes(self):
        """Should-fix: Uniform-length object array of 1-d int64 rows must PASS.
        
        Same as ragged test but all rows have length 5 (no deaths). Official layout.
        """
        manifest, trials = make_ensemble_full()
        
        trial_id = "table10-g1.05-N5-vAC-s42"
        trial = trials[trial_id]
        
        # All 8 steps: 5 alive, no self-targets
        series = trial["series"]
        for t in range(8):
            series["alive_ids"][t] = [0, 1, 2, 3, 4]
            series["n_alive"][t] = 5
            series["eligible_ids"][t] = [0, 1, 2, 3, 4]
            series["eligible_count"][t] = 5
            series["top_targets"][t] = [1, 2, 3, 4, 0]  # No self-targets
        
        # Create NPZ with official export_v02.py layout
        npz_arrays = {}
        for key, val in series.items():
            if key in ("alive_ids", "eligible_ids", "top_targets"):
                o = np.empty(len(val), dtype=object)
                for i, row in enumerate(val):
                    o[i] = np.asarray(row, dtype=np.int64).reshape(-1)
                npz_arrays[key] = o
            elif key == "received_aggression":
                o = np.empty(len(val), dtype=object)
                for i, row in enumerate(val):
                    o[i] = np.asarray(row, dtype=np.float64).reshape(-1)
                npz_arrays[key] = o
            elif key in ("t", "n_alive", "eligible_count"):
                npz_arrays[key] = np.array(val, dtype=np.int64)
            else:
                npz_arrays[key] = np.array(val, dtype=np.float64)
        
        trial["series"] = {"$npz": f"{trial_id}.npz"}
        
        npz_files = {f"{trial_id}.npz": npz_arrays}
        result, code = self.run_judge(manifest, trials, npz_files)
        
        # Must PASS
        self.assertEqual(result["verdict"], "PASS")


class Table10Aliases(unittest.TestCase):
    """Tests for contract alias support."""
    
    def run_judge(self, manifest, trials):
        with tempfile.TemporaryDirectory() as d:
            traces = os.path.join(d, "table10")
            os.makedirs(os.path.join(traces, "trials"))
            
            write_text(os.path.join(traces, "manifest.json"), json.dumps(manifest))
            for stem, trial in trials.items():
                write_text(os.path.join(traces, "trials", stem + ".json"), json.dumps(trial))
            
            out = os.path.join(d, "result.json")
            with contextlib.redirect_stdout(io.StringIO()):
                code = J10.main([traces, out])
            
            result = J10.load_json_strict(J10.read_bytes(out))
        
        return result, code
    
    @patch_n_steps(8)
    def test_alias_prefix_match(self):
        """Contract aliases: eligible_agents ↔ eligible_count, n_active_agents ↔ n_alive,
        aggression_max_share ↔ top_target_share. Prefix matches when one uses alias."""
        manifest, trials = make_ensemble_full()
        
        # Make original trial incomplete
        incomplete_id = "table10-g1.05-N5-vAC-s42"
        trials[incomplete_id]["timed_out"] = True
        trials[incomplete_id]["steps_completed"] = 5
        # Truncate and use aliases
        for key in list(trials[incomplete_id]["series"].keys()):
            trials[incomplete_id]["series"][key] = trials[incomplete_id]["series"][key][:5]
        # Rename to aliases
        trials[incomplete_id]["series"]["eligible_agents"] = trials[incomplete_id]["series"].pop("eligible_count")
        trials[incomplete_id]["series"]["n_active_agents"] = trials[incomplete_id]["series"].pop("n_alive")
        trials[incomplete_id]["series"]["aggression_max_share"] = trials[incomplete_id]["series"].pop("top_target_share")
        
        # Add a completed rerun with canonical names
        rerun_id = "table10-g1.05-N5-vAC-s42-rerun"
        rerun = make_trial("AC", 1.05, 5, 42, generative=True)
        rerun["trial_id"] = rerun_id
        rerun["rerun_of"] = incomplete_id
        trials[rerun_id] = rerun
        manifest["trial_ids"].append(rerun_id)
        
        result, code = self.run_judge(manifest, trials)
        
        # Should PASS - aliases match canonical names
        self.assertEqual(result["verdict"], "PASS")
        cell = next(c for c in result["cells"] if c["variant"] == "AC" and c["gamma"] == 1.05 and c["N"] == 5)
        self.assertEqual(cell["determinism_failures"], 0)


class Table10IDIntegrity(unittest.TestCase):
    """Tests for per-step ID integrity checks."""
    
    def run_judge(self, manifest, trials):
        with tempfile.TemporaryDirectory() as d:
            traces = os.path.join(d, "table10")
            os.makedirs(os.path.join(traces, "trials"))
            
            write_text(os.path.join(traces, "manifest.json"), json.dumps(manifest))
            for stem, trial in trials.items():
                write_text(os.path.join(traces, "trials", stem + ".json"), json.dumps(trial))
            
            out = os.path.join(d, "result.json")
            with contextlib.redirect_stdout(io.StringIO()):
                code = J10.main([traces, out])
            
            result = J10.load_json_strict(J10.read_bytes(out))
        
        return result, code
    
    @patch_n_steps(8)
    def test_duplicate_alive_ids_fails(self):
        """Trial with duplicate alive_ids must not PASS."""
        manifest, trials = make_ensemble_full()
        
        # Make one trial have duplicate alive_ids
        trial_id = "table10-g1.05-N5-vAC-s42"
        # Introduce duplicate at step 3: [0, 1, 2, 3, 3] instead of [0, 1, 2, 3, 4]
        trials[trial_id]["series"]["alive_ids"][3] = [0, 1, 2, 3, 3]
        
        result, code = self.run_judge(manifest, trials)
        
        # Should FAIL
        self.assertEqual(result["verdict"], "FAIL")
        
        # Should have trial.metadata issue about duplicate alive_ids
        metadata_issues = [i for i in result["issues"] 
                          if i["code"] == "trial.metadata" and "duplicate alive_ids" in i["detail"]]
        self.assertGreater(len(metadata_issues), 0)

    @patch_n_steps(8)
    def test_alive_count_mismatch_fails(self):
        """Lab probe: n_alive[3]=2 with 5 alive ids should FAIL."""
        manifest, trials = make_ensemble_full()
        
        trial_id = "table10-g1.05-N5-vAC-s42"
        # Step 3: n_alive=2 but alive_ids has 5 agents
        trials[trial_id]["series"]["n_alive"][3] = 2
        trials[trial_id]["series"]["alive_ids"][3] = [0, 1, 2, 3, 4]
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        issues = [i for i in result["issues"] 
                 if i["code"] == "trial.metadata" and "ids.alive_count" in i["detail"]]
        self.assertGreater(len(issues), 0)

    @patch_n_steps(8)
    def test_alive_outside_population_fails(self):
        """Lab probe: alive_ids[3]=[0,1,2,3,99] with n_agents=5 should FAIL."""
        manifest, trials = make_ensemble_full()
        
        trial_id = "table10-g1.05-N5-vAC-s42"
        # Step 3: include agent 99 outside 0..4
        trials[trial_id]["series"]["alive_ids"][3] = [0, 1, 2, 3, 99]
        trials[trial_id]["series"]["n_alive"][3] = 5
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        issues = [i for i in result["issues"] 
                 if i["code"] == "trial.metadata" and "ids.alive_outside_population" in i["detail"]]
        self.assertGreater(len(issues), 0)

    @patch_n_steps(8)
    def test_eligible_count_mismatch_fails(self):
        """eligible_count != len(eligible_ids) should FAIL."""
        manifest, trials = make_ensemble_full()
        
        trial_id = "table10-g1.05-N5-vAC-s42"
        # Step 3: eligible_count=2 but eligible_ids has 3 agents
        trials[trial_id]["series"]["eligible_count"][3] = 2
        trials[trial_id]["series"]["eligible_ids"][3] = [0, 1, 2]
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        issues = [i for i in result["issues"] 
                 if i["code"] == "trial.metadata" and "ids.eligible_count" in i["detail"]]
        self.assertGreater(len(issues), 0)

    @patch_n_steps(8)
    def test_eligible_duplicate_fails(self):
        """Duplicate eligible_ids should FAIL."""
        manifest, trials = make_ensemble_full()
        
        trial_id = "table10-g1.05-N5-vAC-s42"
        # Step 3: duplicate eligible ids
        trials[trial_id]["series"]["eligible_ids"][3] = [0, 1, 1]
        trials[trial_id]["series"]["eligible_count"][3] = 3
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        issues = [i for i in result["issues"] 
                 if i["code"] == "trial.metadata" and "ids.eligible_duplicate" in i["detail"]]
        self.assertGreater(len(issues), 0)

    @patch_n_steps(8)
    def test_target_not_alive_fails(self):
        """top_targets not all in alive_ids should FAIL."""
        manifest, trials = make_ensemble_full()
        
        trial_id = "table10-g1.05-N5-vAC-s42"
        # Step 3: target agent 4 who is not in alive_ids
        trials[trial_id]["series"]["alive_ids"][3] = [0, 1, 2]
        trials[trial_id]["series"]["n_alive"][3] = 3
        trials[trial_id]["series"]["eligible_ids"][3] = [0, 1, 2]
        trials[trial_id]["series"]["eligible_count"][3] = 3
        trials[trial_id]["series"]["top_targets"][3] = [1, 2, 4]  # 4 not in alive
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        issues = [i for i in result["issues"] 
                 if i["code"] == "trial.metadata" and "ids.target_not_alive" in i["detail"]]
        self.assertGreater(len(issues), 0)

    @patch_n_steps(8)
    def test_self_target_fails(self):
        """An eligible agent targeting itself should FAIL."""
        manifest, trials = make_ensemble_full()
        
        trial_id = "table10-g1.05-N5-vAC-s42"
        # Step 3: agent 1 targets itself
        trials[trial_id]["series"]["alive_ids"][3] = [0, 1, 2]
        trials[trial_id]["series"]["n_alive"][3] = 3
        trials[trial_id]["series"]["eligible_ids"][3] = [0, 1, 2]
        trials[trial_id]["series"]["eligible_count"][3] = 3
        trials[trial_id]["series"]["top_targets"][3] = [2, 1, 0]  # agent 1 -> 1
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        issues = [i for i in result["issues"] 
                 if i["code"] == "trial.metadata" and "ids.self_target" in i["detail"]]
        self.assertGreater(len(issues), 0)

    @patch_n_steps(8)
    def test_non_list_alive_ids_fails(self):
        """alive_ids not a list (silent skip probe) should FAIL."""
        manifest, trials = make_ensemble_full()
        
        trial_id = "table10-g1.05-N5-vAC-s42"
        # Replace alive_ids with non-list
        trials[trial_id]["series"]["alive_ids"] = "not a list"
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        issues = [i for i in result["issues"] 
                 if i["code"] == "trial.metadata" and "alive_ids is not a list" in i["detail"]]
        self.assertGreater(len(issues), 0)

    @patch_n_steps(8)
    def test_aliased_n_active_agents_with_self_target_fails(self):
        """BLOCKER 1: n_active_agents alias with self-targets must FAIL."""
        manifest, trials = make_ensemble_full()
        
        trial_id = "table10-g1.05-N5-vAC-s42"
        # Use n_active_agents alias, remove canonical n_alive
        trials[trial_id]["series"]["n_active_agents"] = trials[trial_id]["series"]["n_alive"]
        del trials[trial_id]["series"]["n_alive"]
        
        # Step 3: every eligible agent targets itself
        trials[trial_id]["series"]["alive_ids"][3] = [0, 1, 2]
        trials[trial_id]["series"]["n_active_agents"][3] = 3
        trials[trial_id]["series"]["eligible_ids"][3] = [0, 1, 2]
        trials[trial_id]["series"]["eligible_count"][3] = 3
        trials[trial_id]["series"]["top_targets"][3] = [0, 1, 2]  # all self-target
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        issues = [i for i in result["issues"] 
                 if i["code"] == "trial.metadata" and "ids.self_target" in i["detail"]]
        self.assertGreater(len(issues), 0)

    @patch_n_steps(8)
    def test_aliased_eligible_agents_with_self_target_fails(self):
        """BLOCKER 1: eligible_agents alias with self-targets must FAIL."""
        manifest, trials = make_ensemble_full()
        
        trial_id = "table10-g1.05-N5-vAC-s42"
        # Use eligible_agents alias, remove canonical eligible_count
        trials[trial_id]["series"]["eligible_agents"] = trials[trial_id]["series"]["eligible_count"]
        del trials[trial_id]["series"]["eligible_count"]
        
        # Step 3: every eligible agent targets itself
        trials[trial_id]["series"]["alive_ids"][3] = [0, 1, 2]
        trials[trial_id]["series"]["n_alive"][3] = 3
        trials[trial_id]["series"]["eligible_ids"][3] = [0, 1, 2]
        trials[trial_id]["series"]["eligible_agents"][3] = 3
        trials[trial_id]["series"]["top_targets"][3] = [0, 1, 2]  # all self-target
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        issues = [i for i in result["issues"] 
                 if i["code"] == "trial.metadata" and "ids.self_target" in i["detail"]]
        self.assertGreater(len(issues), 0)

    @patch_n_steps(8)
    def test_align_targets_length_mismatch_fails(self):
        """BLOCKER 2: top_targets length != eligible_ids length must FAIL."""
        manifest, trials = make_ensemble_full()
        
        trial_id = "table10-g1.05-N5-vAC-s42"
        # Step 3: top_targets length 1, eligible_ids length 3 (agent 0 targets itself)
        trials[trial_id]["series"]["alive_ids"][3] = [0, 1, 2]
        trials[trial_id]["series"]["n_alive"][3] = 3
        trials[trial_id]["series"]["eligible_ids"][3] = [0, 1, 2]
        trials[trial_id]["series"]["eligible_count"][3] = 3
        trials[trial_id]["series"]["top_targets"][3] = [0]  # length 1, agent 0 -> 0
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        issues = [i for i in result["issues"] 
                 if i["code"] == "trial.metadata" and "align.targets" in i["detail"]]
        self.assertGreater(len(issues), 0)

    @patch_n_steps(8)
    def test_non_integer_alive_ids_fails(self):
        """Should-fix: non-integer IDs must FAIL (series.shape)."""
        manifest, trials = make_ensemble_full()
        
        trial_id = "table10-g1.05-N5-vAC-s42"
        # Step 3: alive_ids includes 1.0 (float)
        trials[trial_id]["series"]["alive_ids"][3] = [0, 1.0, 2]
        trials[trial_id]["series"]["n_alive"][3] = 3
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        issues = [i for i in result["issues"] 
                 if i["code"] == "trial.metadata" and "series.shape" in i["detail"]]
        self.assertGreater(len(issues), 0)


class Table10BlackRepo(unittest.TestCase):
    """Tests requiring Black's official repo at pinned SHA."""
    
    def run_judge(self, manifest, trials):
        with tempfile.TemporaryDirectory() as d:
            traces = os.path.join(d, "table10")
            os.makedirs(os.path.join(traces, "trials"))
            
            write_text(os.path.join(traces, "manifest.json"), json.dumps(manifest))
            for stem, trial in trials.items():
                write_text(os.path.join(traces, "trials", stem + ".json"), json.dumps(trial))
            
            out = os.path.join(d, "result.json")
            with contextlib.redirect_stdout(io.StringIO()):
                code = J10.main([traces, out])
            
            result = J10.load_json_strict(J10.read_bytes(out))
        
        return result, code
    
    @unittest.skip("TODO: Official C-T10 runner test for issue #19 - needs real interrupt-at-k vs complete, not 10-vs-20")
    def test_short_run_unanimity_triggered(self):
        """TODO: Run C-T10 runner with real forced timeout (interrupt at step k < n_steps_planned).
        
        Issue #19 requires: a run PLANNED for N steps and INTERRUPTED at k (timed_out=true,
        steps_completed=k < n_steps_planned), compared with SAME seed run to COMPLETION
        (timed_out=false, steps_completed=n_steps_planned=N). The interrupted run's arrays
        must equal the first k steps of the completed run.
        
        Current black_reference.py only loads Table 2 helpers (time_to_95, gini, entropy).
        To implement this correctly needs:
        - Extend black_reference to load small_n_utils.run_unanimity_triggered under same
          SHA-256 pin and AST-only rule (hash source file, parse with ast, compile only
          what's needed, never run scripts)
        - Use timeout_seconds to actually interrupt: timed_out must be true, k < N
        - Compare prefixes
        - Skip only if Black absent; REQUIRE_OFFICIAL=1 must fail if Black missing
        """
        pass


class Table10ViabilityD7(unittest.TestCase):
    """Tests for D7 viability computation."""
    
    def test_d7_holds_when_all_conditions_met(self):
        """D7 holds when status=genuine_exhaustion, pct_consumed<0.5, n_expulsions>=1."""
        viability = {
            "status": "genuine_exhaustion",
            "pct_consumed": 0.3,
            "n_expulsions": 2,
            "generative": True,
        }
        valid, issues, is_generative = J10.check_viability_d7(viability, "test")
        self.assertTrue(valid)
        self.assertEqual(len(issues), 0)
        self.assertTrue(is_generative)
    
    def test_d7_fails_when_status_wrong(self):
        """D7 fails when status != genuine_exhaustion."""
        viability = {
            "status": "still_cycling",
            "pct_consumed": 0.3,
            "n_expulsions": 2,
            "generative": False,
        }
        valid, issues, is_generative = J10.check_viability_d7(viability, "test")
        self.assertTrue(valid)
        self.assertFalse(is_generative)
    
    def test_d7_fails_when_pct_consumed_too_high(self):
        """D7 fails when pct_consumed >= 0.5."""
        viability = {
            "status": "genuine_exhaustion",
            "pct_consumed": 0.6,
            "n_expulsions": 2,
            "generative": False,
        }
        valid, issues, is_generative = J10.check_viability_d7(viability, "test")
        self.assertTrue(valid)
        self.assertFalse(is_generative)
    
    def test_d7_fails_when_no_expulsions(self):
        """D7 fails when n_expulsions < 1."""
        viability = {
            "status": "genuine_exhaustion",
            "pct_consumed": 0.3,
            "n_expulsions": 0,
            "generative": False,
        }
        valid, issues, is_generative = J10.check_viability_d7(viability, "test")
        self.assertTrue(valid)
        self.assertFalse(is_generative)
    
    def test_d7_mismatch_raises_issue(self):
        """If computed D7 doesn't match generative field, raise issue."""
        viability = {
            "status": "genuine_exhaustion",
            "pct_consumed": 0.3,
            "n_expulsions": 2,
            "generative": False,  # Should be True
        }
        valid, issues, is_generative = J10.check_viability_d7(viability, "test")
        self.assertFalse(valid)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["code"], "viability.d7")


if __name__ == "__main__":
    unittest.main()
