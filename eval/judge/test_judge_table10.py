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


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def make_trial(variant, gamma, N, seed, steps_completed=5000, timed_out=False,
               generative=True, timeout_seconds=600.0, host="test-host", rerun_of=None):
    """Build a minimal C-T10 trial."""
    trial_id = f"table10-g{gamma:.2f}-N{N}-v{variant}-s{seed}"
    
    # Simple series for testing
    series = {
        "t": list(range(steps_completed)),
        "n_alive": [N] * steps_completed,
        "alive_ids": [list(range(N))] * steps_completed,
        "system_tension": [1.0 + 0.01 * i for i in range(steps_completed)],
        "modal_agreement": [0.8] * steps_completed,
        "eligible_count": [N] * steps_completed,
        "eligible_ids": [list(range(N))] * steps_completed,
        "top_targets": [[0] * N] * steps_completed,
        "received_aggression": [[0.1] * N] * steps_completed,
        "aggression_gini": [0.1] * steps_completed,
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
        "expulsion_steps": [1000, 2000] if generative else [],
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
        "n_steps_planned": 5000,
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
    """Build a small test ensemble: AC at gamma=1.05, N=5 (published 25% = 5/20 viable)."""
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
    
    def test_valid_cell_passes(self):
        """A valid cell with correct k/20 passes."""
        manifest, trials = make_ensemble_small()
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(code, 0)
        self.assertEqual(len(result["cells"]), 1)
        
        cell = result["cells"][0]
        self.assertEqual(cell["variant"], "AC")
        self.assertEqual(cell["gamma"], 1.05)
        self.assertEqual(cell["N"], 5)
        self.assertEqual(cell["n_complete"], 20)
        self.assertEqual(cell["n_incomplete"], 0)
        self.assertEqual(cell["n_viable"], 5)
        self.assertEqual(cell["computed_percent"], 25)
        self.assertEqual(cell["published_percent"], 25)
        self.assertEqual(cell["verdict"], "PASS")
    
    def test_wrong_viability_count_fails(self):
        """A cell with wrong k/20 fails."""
        manifest, trials = make_ensemble_small()
        
        # Change one trial to make 6 viable instead of 5
        trial_id = "table10-g1.05-N5-vAC-s5042"
        trials[trial_id]["viability"]["generative"] = True
        trials[trial_id]["viability"]["n_expulsions"] = 2
        trials[trial_id]["viability"]["pct_consumed"] = 0.3
        trials[trial_id]["viability"]["status"] = "genuine_exhaustion"
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(code, 1)
        
        cell = result["cells"][0]
        self.assertEqual(cell["n_viable"], 6)
        self.assertEqual(cell["computed_percent"], 30)
        self.assertEqual(cell["verdict"], "FAIL")


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
    
    def test_timed_out_trial_is_incomplete(self):
        """A trial with timed_out=true is incomplete."""
        manifest, trials = make_ensemble_small()
        
        # Make one trial timed out
        trial_id = "table10-g1.05-N5-vAC-s42"
        trials[trial_id]["timed_out"] = True
        trials[trial_id]["steps_completed"] = 3000
        # Truncate series
        for key in trials[trial_id]["series"]:
            trials[trial_id]["series"][key] = trials[trial_id]["series"][key][:3000]
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "INCOMPLETE")
        self.assertEqual(code, 1)
        
        cell = result["cells"][0]
        self.assertEqual(cell["n_complete"], 19)
        self.assertEqual(cell["n_incomplete"], 1)
        self.assertIn(42, cell["incomplete_seeds"])
        self.assertEqual(cell["verdict"], "INCOMPLETE")
    
    def test_incomplete_steps_is_incomplete(self):
        """A trial with steps_completed < n_steps_planned is incomplete."""
        manifest, trials = make_ensemble_small()
        
        # Make one trial incomplete
        trial_id = "table10-g1.05-N5-vAC-s42"
        trials[trial_id]["timed_out"] = False
        trials[trial_id]["steps_completed"] = 3000
        # Truncate series
        for key in trials[trial_id]["series"]:
            trials[trial_id]["series"][key] = trials[trial_id]["series"][key][:3000]
        
        result, code = self.run_judge(manifest, trials)
        
        self.assertEqual(result["verdict"], "INCOMPLETE")
        cell = result["cells"][0]
        self.assertEqual(cell["n_incomplete"], 1)
        self.assertEqual(cell["verdict"], "INCOMPLETE")
    
    def test_incomplete_trial_not_counted_as_viable_or_nonviable(self):
        """An incomplete trial is not counted in k/20."""
        manifest, trials = make_ensemble_small()
        
        # Make one viable trial incomplete
        trial_id = "table10-g1.05-N5-vAC-s42"  # This was viable
        trials[trial_id]["timed_out"] = True
        trials[trial_id]["steps_completed"] = 3000
        for key in trials[trial_id]["series"]:
            trials[trial_id]["series"][key] = trials[trial_id]["series"][key][:3000]
        
        result, code = self.run_judge(manifest, trials)
        
        cell = result["cells"][0]
        # Should have 19 complete (not 20), and n_viable should not count the incomplete one
        self.assertEqual(cell["n_complete"], 19)
        self.assertEqual(cell["n_viable"], 4)  # 5 were viable, but 1 is incomplete
        self.assertIsNone(cell["computed_percent"])  # Can't compute percent with incomplete
        self.assertEqual(cell["verdict"], "INCOMPLETE")


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
    
    def test_successful_rerun_with_determinism_check(self):
        """A rerun that matches the incomplete prefix passes determinism check."""
        manifest, trials = make_ensemble_small()
        
        # Make original trial incomplete
        incomplete_id = "table10-g1.05-N5-vAC-s42"
        trials[incomplete_id]["timed_out"] = True
        trials[incomplete_id]["steps_completed"] = 3000
        # Truncate series
        for key in trials[incomplete_id]["series"]:
            trials[incomplete_id]["series"][key] = trials[incomplete_id]["series"][key][:3000]
        
        # Add a completed rerun
        rerun_id = "table10-g1.05-N5-vAC-s42-rerun"
        rerun = make_trial("AC", 1.05, 5, 42, generative=True)
        rerun["trial_id"] = rerun_id
        rerun["rerun_of"] = incomplete_id
        # Make sure series prefix matches
        for key in rerun["series"]:
            if len(rerun["series"][key]) >= 3000:
                # The first 3000 steps should match
                pass
        trials[rerun_id] = rerun
        manifest["trial_ids"].append(rerun_id)
        
        result, code = self.run_judge(manifest, trials)
        
        # Should pass because rerun is complete and matches
        self.assertEqual(result["verdict"], "PASS")
        cell = result["cells"][0]
        self.assertEqual(cell["n_complete"], 20)  # 19 original complete + 1 rerun
        self.assertEqual(cell["n_incomplete"], 0)
        self.assertEqual(cell["n_reruns"], 1)
        self.assertEqual(cell["determinism_failures"], 0)
    
    def test_rerun_determinism_mismatch_keeps_seed_incomplete(self):
        """A rerun whose prefix doesn't match keeps the seed incomplete."""
        manifest, trials = make_ensemble_small()
        
        # Make original trial incomplete
        incomplete_id = "table10-g1.05-N5-vAC-s42"
        trials[incomplete_id]["timed_out"] = True
        trials[incomplete_id]["steps_completed"] = 3000
        for key in trials[incomplete_id]["series"]:
            trials[incomplete_id]["series"][key] = trials[incomplete_id]["series"][key][:3000]
        
        # Add a rerun with a mismatch
        rerun_id = "table10-g1.05-N5-vAC-s42-rerun"
        rerun = make_trial("AC", 1.05, 5, 42, generative=True)
        rerun["trial_id"] = rerun_id
        rerun["rerun_of"] = incomplete_id
        # Introduce a mismatch in modal_agreement
        rerun["series"]["modal_agreement"][100] = 0.9  # Different from 0.8
        trials[rerun_id] = rerun
        manifest["trial_ids"].append(rerun_id)
        
        result, code = self.run_judge(manifest, trials)
        
        # Should be INCOMPLETE because determinism check failed
        self.assertEqual(result["verdict"], "INCOMPLETE")
        cell = result["cells"][0]
        self.assertEqual(cell["n_incomplete"], 1)  # Seed 42 stays incomplete
        self.assertEqual(cell["determinism_failures"], 1)
        
        # Check that there's a determinism issue
        issues = [i for i in result["issues"] if i["code"] == "v022.determinism"]
        self.assertEqual(len(issues), 1)
    
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
        """A rerun should only be for an incomplete trial."""
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
