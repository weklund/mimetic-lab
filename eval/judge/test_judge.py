"""Tests for the C-T2 judge (contract v0.2.1).

What these tests rely on, so that rewording a message or renaming an internal helper
does not break them:
  - the judge's documented interface (eval/judge/README.md): main(), the result file's
    verdict, provisional, checks, cells, and issue codes; and the pure rule functions
    consistent_with_printed, load_json_strict, check_series, score_cell;
  - the contract and schema documents themselves.

How they are organised:
  1. Rule tests: rule A and strict JSON, straight from the contract.
  2. End-to-end tests: build a small ensemble that satisfies the contract, show the judge
     PASSes it, then corrupt one thing at a time and show each corruption FAILs with the
     issue code for the clause it breaks. A judge that has never been shown to fail has
     unknown sensitivity; a judge that has never been shown to pass might fail everything.
  3. Real data: re-score the per-trial values recorded by the v0.2 C-T2 run.
  4. Documents: the schema's toy example passes the judge's series checks, has every
     required field, and every issue code is documented.

Agreement with Black's official code is tested in test_against_official.py.

Run: python3 -m unittest discover -s eval/judge -p 'test_*.py'
"""
import contextlib
import copy
import hashlib
import io
import json
import os
import re
import tempfile
import unittest

import numpy as np

import judge_table2 as J
import judge_common as JC

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, "..", "trial-schema.md")
README = os.path.join(HERE, "README.md")
RECORDED_RESULT = os.path.join(HERE, "table2-result.json")


def toy_trial():
    """The JSON block under '## Complete example' in eval/trial-schema.md, parsed strictly."""
    text = J.read_bytes(SCHEMA).decode("utf-8")
    section = text.split("## Complete example", 1)[1]
    block = re.search(r"```json\n(.*?)\n```", section, re.S).group(1)
    return J.load_json_strict(block)


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def codes(issues):
    return {i["code"] for i in issues}


# ---------------------------------------------------------------- 1. rules

class RuleA(unittest.TestCase):
    """Contract v0.2.1: a printed number stands for every value that rounds to it."""

    def test_known_mismatch_3(self):
        self.assertTrue(J.consistent_with_printed(29.5, 30, 0))  # gamma 2.00: paper 30, np.median 29.5
        self.assertTrue(J.consistent_with_printed(29.5, 29, 0))  # the script's int() is consistent too

    def test_integer_window(self):
        self.assertTrue(J.consistent_with_printed(116.5, 116, 0))
        self.assertFalse(J.consistent_with_printed(31.0, 30, 0))
        self.assertFalse(J.consistent_with_printed(28.5, 30, 0))

    def test_three_decimal_window(self):
        self.assertTrue(J.consistent_with_printed(0.1725, 0.172, 3))  # exactly on the boundary
        self.assertTrue(J.consistent_with_printed(0.1725, 0.173, 3))
        self.assertFalse(J.consistent_with_printed(0.1726, 0.172, 3))

    def test_missing_values(self):
        self.assertTrue(J.consistent_with_printed(None, None, 0))
        self.assertFalse(J.consistent_with_printed(None, 30, 0))
        self.assertFalse(J.consistent_with_printed(30.0, None, 0))


class StrictJson(unittest.TestCase):
    """Contract: no NaN or Infinity. Python's json module accepts all of these by default."""

    def test_rejects_nan_infinity_and_overflow(self):
        for text in ['{"x": NaN}', '{"x": Infinity}', '{"x": -Infinity}', '{"x": 1e309}']:
            with self.assertRaises(ValueError, msg=text):
                J.load_json_strict(text)

    def test_accepts_ordinary_numbers(self):
        self.assertEqual(J.load_json_strict('{"x": 0.5, "y": 3}'), {"x": 0.5, "y": 3})


# ---------------------------------------------------------------- 2. end to end

N_AGENTS, N_STEPS = 5, 24
SEEDS = (42, 1042, 2042, 3042)
T95 = {1.00: [None] * 4, 2.00: [2, 3, 4, 5]}  # gamma 2.00 has median 3.5, like known mismatch 3


def make_series(t95):
    """Agreement 0.4 before t95, then 1.0. At 1.0 agent 0, the target, has no outgoing
    aggression and is not eligible, so agreement can exceed the (N-1)/N ceiling (D1)."""
    s = {key: [] for key in J.SERIES_1D + J.SERIES_NESTED}
    for t in range(N_STEPS):
        converged = t95 is not None and t >= t95
        eligible = [1, 2, 3, 4] if converged else [0, 1, 2, 3, 4]
        targets = [0, 0, 0, 0] if converged else [1, 0, 0, 4, 3]
        R = [1.0 + 0.25 * (t % 3), 0.5, 0.5, 0.25, 0.25 + 0.125 * converged]
        _, agreement = J.modal_from_targets(targets)
        for key, val in dict(t=t, n_alive=N_AGENTS, alive_ids=list(range(N_AGENTS)), eligible_ids=eligible,
                             eligible_count=len(eligible), top_targets=targets, received_aggression=R,
                             system_tension=sum(R), modal_agreement=agreement, aggression_gini=J.gini(R)).items():
            s[key].append(val)
    return s


def printed_row(g, row):
    # Layout of reproduce_table_2.py's row print (checked against the official code in
    # test_against_official.py).
    return (f"{g:>6.2f} | {row['peak_modal_mean']:>10} {row['peak_modal_sd']:>6} | {row['final_modal_mean']:>10} "
            f"{row['final_modal_sd']:>6} | {row['peak_gini_mean']:>8} | {row['med_t95']:>8} | {row['conv_pct']:>5}%")


def build_ensemble():
    """A small ensemble that meets the contract, and the spec (published table) it meets."""
    runs, trials = {}, {}
    for g, t95s in T95.items():
        runs[g] = []
        for seed, t95 in zip(SEEDS, t95s, strict=True):
            s = make_series(t95)
            stem = f"table2-g{g:.2f}-N{N_AGENTS}-vAC-s{seed}"
            trials[stem] = dict(J.TABLE2_EXPECT, N=N_AGENTS, n_steps_planned=N_STEPS, steps_completed=N_STEPS,
                                contract_version="0.2.1", trial_id=stem, gamma=g, seed=seed, series=s)
            a = s["modal_agreement"]
            runs[g].append(dict(seed=seed, t95=J.time_to_95(a), peak_modal=max(a), final_modal=float(np.mean(a[-50:])),
                                peak_gini=max(s["aggression_gini"])))
    # The "published" table: means and sds to 3 decimals, the median rounded half to even.
    pub = {}
    for g, rs in runs.items():
        conv = [r["t95"] for r in rs if r["t95"] is not None]
        stats = [np.mean([r["peak_modal"] for r in rs]), np.std([r["peak_modal"] for r in rs]),
                 np.mean([r["final_modal"] for r in rs]), np.std([r["final_modal"] for r in rs]),
                 np.mean([r["peak_gini"] for r in rs])]
        pub[g] = tuple(round(float(x), 3) for x in stats) + (round(float(np.median(conv))) if conv else None, len(conv))
    spec = J.EnsembleSpec(ensemble_id="table2", gammas=tuple(T95), seeds=SEEDS, n_steps=N_STEPS, n_agents=N_AGENTS,
                          pub=pub, expect=dict(J.TABLE2_EXPECT, N=N_AGENTS, n_steps_planned=N_STEPS,
                                               steps_completed=N_STEPS))
    stdout = "TABLE 2: test ensemble\n" + "\n".join(
        printed_row(g, J.score_cell(g, runs[g], spec=spec)["expected_script_row"]) for g in T95) + "\n"
    manifest = dict(contract_version="0.2.1", source_sha=J.PINNED_SHA, trial_ids=sorted(trials),
                    cells=[dict(table="2", gamma=g) for g in T95], script_stdout_file="script_stdout.txt")
    return dict(manifest=manifest, trials=trials, stdout=stdout), spec


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.ens, self.spec = build_ensemble()

    def run_judge(self, ens=None, raw_trials=None, stale_pass=True):
        ens = self.ens if ens is None else ens
        with tempfile.TemporaryDirectory() as d:
            traces = os.path.join(d, "table2")
            os.makedirs(os.path.join(traces, "trials"))
            if ens.get("manifest") is not None:
                man = dict(ens["manifest"])
                if ens.get("stdout") is not None:
                    write_text(os.path.join(traces, "script_stdout.txt"), ens["stdout"])
                    man.setdefault("script_stdout_sha256", hashlib.sha256(ens["stdout"].encode()).hexdigest())
                write_text(os.path.join(traces, "manifest.json"), json.dumps(man))
            for stem, trial in ens["trials"].items():
                write_text(os.path.join(traces, "trials", stem + ".json"), json.dumps(trial))
            for stem, text in (raw_trials or {}).items():
                write_text(os.path.join(traces, "trials", stem + ".json"), text)
            out = os.path.join(d, "result.json")
            if stale_pass:
                write_text(out, json.dumps({"verdict": "PASS"}))  # must not survive a failing run
            with contextlib.redirect_stdout(io.StringIO()):
                code = J.main([traces, out], spec=self.spec)
            result = J.load_json_strict(J.read_bytes(out))
            self.assertEqual([f for f in os.listdir(d) if f.startswith(".judge-")], [], "temp file left behind")
        self.assertEqual(code, 0 if result["verdict"] == "PASS" else 1)
        return result

    def mutate_series(self, fn, gamma=2.00, seed=42):
        ens = copy.deepcopy(self.ens)
        fn(ens["trials"][f"table2-g{gamma:.2f}-N{N_AGENTS}-vAC-s{seed}"]["series"])
        return ens

    def assert_fails_with(self, ens, code):
        result = self.run_judge(ens)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn(code, codes(result["issues"]))

    # The baseline: without it, every FAIL below could be a judge that fails everything.
    def test_valid_ensemble_passes(self):
        result = self.run_judge()
        self.assertEqual(result["verdict"], "PASS", result["issues"])
        self.assertEqual(result["provisional"], [])
        self.assertTrue(result["checks"]["e_matches_script_output_all_cells"])

    def test_median_is_scored_by_rule_a_not_by_truncation(self):
        cell = next(c for c in self.run_judge()["cells"] if c["gamma"] == 2.00)
        self.assertEqual((cell["median_t95_np"], cell["median_t95_script_int"], cell["published_med_t95"]), (3.5, 3, 4))
        self.assertTrue(cell["checks"]["med_t95_consistent_with_paper"])
        self.assertFalse(cell["legacy_v0_2"]["med_t95_int_equals_paper"])

    def test_without_script_stdout_the_pass_is_provisional(self):
        ens = copy.deepcopy(self.ens)
        del ens["manifest"]["script_stdout_file"]
        ens["stdout"] = None
        result = self.run_judge(ens)
        self.assertEqual(result["verdict"], "PASS")
        self.assertTrue(result["provisional"])
        self.assertIsNone(result["checks"]["e_matches_script_output_all_cells"])

    # Identities (CodeRabbit's case first: every eligible id replaced, lengths kept).
    def test_eligible_ids_outside_alive(self):
        self.assert_fails_with(self.mutate_series(
            lambda s: s.update(eligible_ids=[[999] * len(e) for e in s["eligible_ids"]])), "ids.eligible_not_alive")

    def test_duplicate_eligible_ids(self):
        self.assert_fails_with(self.mutate_series(lambda s: s["eligible_ids"].__setitem__(0, [0, 0, 2, 3, 4])),
                               "ids.eligible_duplicate")

    def test_target_not_alive(self):
        self.assert_fails_with(self.mutate_series(lambda s: s["top_targets"].__setitem__(0, [1, 0, 0, 4, 7])),
                               "ids.target_not_alive")

    def test_self_target(self):
        self.assert_fails_with(self.mutate_series(lambda s: s["top_targets"].__setitem__(0, [0, 0, 0, 4, 3])),
                               "ids.self_target")

    def test_alive_ids_inconsistent_with_n_alive(self):
        self.assert_fails_with(self.mutate_series(lambda s: s["n_alive"].__setitem__(1, 4)), "ids.alive_count")

    def test_received_aggression_misaligned(self):
        self.assert_fails_with(self.mutate_series(lambda s: s["received_aggression"][0].pop()),
                               "align.received_aggression")

    # Structure: reported, never raised.
    def test_short_series(self):
        self.assert_fails_with(self.mutate_series(lambda s: s["top_targets"].pop()), "series.shape")

    def test_missing_series(self):
        self.assert_fails_with(self.mutate_series(lambda s: s.pop("eligible_ids")), "series.shape")

    def test_boolean_is_not_a_number(self):
        self.assert_fails_with(self.mutate_series(lambda s: s["system_tension"].__setitem__(0, True)), "series.shape")

    # Recorded series recomputed from their parts.
    def test_wrong_recorded_agreement(self):
        self.assert_fails_with(self.mutate_series(lambda s: s["modal_agreement"].__setitem__(0, 0.6)), "D1.agreement")

    def test_tension_mismatch(self):
        self.assert_fails_with(self.mutate_series(lambda s: s["system_tension"].__setitem__(1, 99.0)), "D5.tension")

    def test_gini_mismatch(self):
        self.assert_fails_with(self.mutate_series(lambda s: s["aggression_gini"].__setitem__(2, 0.9)), "gini.series")

    # Strict JSON at read time.
    def test_nan_and_overflow_in_a_trial(self):
        stem = f"table2-g2.00-N{N_AGENTS}-vAC-s42"
        for bad in ("NaN", "1e309"):
            ens = copy.deepcopy(self.ens)
            text = json.dumps(ens["trials"].pop(stem))
            text = text.replace('"aggression_gini": [', f'"aggression_gini": [{bad}, ', 1)
            result = self.run_judge(ens, raw_trials={stem: text})
            self.assertEqual(result["verdict"], "FAIL")
            self.assertIn("trial.json", codes(result["issues"]))

    # Ensemble and metadata.
    def test_missing_trial(self):
        ens = copy.deepcopy(self.ens)
        ens["trials"].pop(f"table2-g2.00-N{N_AGENTS}-vAC-s3042")
        result = self.run_judge(ens)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertTrue({"ensemble.trial_files", "ensemble.seeds"} <= codes(result["issues"]))

    def test_wrong_metadata(self):
        ens = copy.deepcopy(self.ens)
        ens["trials"][f"table2-g2.00-N{N_AGENTS}-vAC-s42"]["alpha"] = 0.2
        self.assert_fails_with(ens, "trial.metadata")

    def test_wrong_source_sha(self):
        ens = copy.deepcopy(self.ens)
        ens["manifest"]["source_sha"] = "0" * 40
        self.assert_fails_with(ens, "manifest.field")

    # Scoring against the published table (cell checks, not issues).
    def test_delayed_onset_moves_the_median(self):
        # Two seeds converge later (t95 2, 3 -> 12, 13): k is unchanged, the median moves 3.5 -> 8.5.
        ens = self.mutate_series(lambda s: s.update(make_series(12)), seed=42)
        ens["trials"][f"table2-g2.00-N{N_AGENTS}-vAC-s1042"]["series"] = make_series(13)
        ens["stdout"] = None
        del ens["manifest"]["script_stdout_file"]
        result = self.run_judge(ens)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertFalse(result["checks"]["d_med_t95_consistent_with_paper_all_cells"])

    def test_lost_convergence_changes_k(self):
        ens = self.mutate_series(lambda s: s.update(make_series(None)))
        result = self.run_judge(ens)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertFalse(result["checks"]["a_k_matches_published_all_cells"])

    # The script's own printed table.
    def test_stdout_tampered_after_hashing(self):
        ens = copy.deepcopy(self.ens)
        ens["manifest"]["script_stdout_sha256"] = hashlib.sha256(ens["stdout"].encode()).hexdigest()
        ens["stdout"] = ens["stdout"].replace("TABLE 2", "TABLE 2 (edited)")
        self.assert_fails_with(ens, "script.stdout")

    def test_stdout_row_disagrees_with_traces(self):
        ens = copy.deepcopy(self.ens)
        line = next(x for x in ens["stdout"].splitlines() if x.lstrip().startswith("2.00"))
        ens["stdout"] = ens["stdout"].replace(line, line.replace("|        3 |", "|        4 |"))
        self.assertNotEqual(ens["stdout"], self.ens["stdout"])
        self.assert_fails_with(ens, "script.row")

    def test_stdout_missing_a_row(self):
        ens = copy.deepcopy(self.ens)
        ens["stdout"] = "\n".join(x for x in ens["stdout"].splitlines() if not x.lstrip().startswith("1.00"))
        self.assert_fails_with(ens, "script.stdout")

    # Fail closed.
    def test_missing_manifest(self):
        ens = copy.deepcopy(self.ens)
        ens["manifest"] = None
        result = self.run_judge(ens)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(codes(result["issues"]), {"fatal"})


# ---------------------------------------------------------------- 3. real data

class RecordedC_T2(unittest.TestCase):
    """The per-trial values the v0.2 judge recorded for the real Table 2 traces."""

    def test_all_13_cells_pass_under_v0_2_1(self):
        recorded = J.load_json_strict(J.read_bytes(RECORDED_RESULT))
        self.assertEqual(len(recorded["cells"]), 13)
        for c in recorded["cells"]:
            runs = [dict(r, t95_recorded_series=rs)
                    for r, rs in zip(c["per_trial"], c["raw_t95_from_recorded_series"], strict=True)]
            cell = J.score_cell(c["gamma"], runs)
            self.assertTrue(cell["cell_pass"], f"gamma {c['gamma']}: {cell['checks']}")
            self.assertEqual(cell["legacy_v0_2"]["med_t95_int_equals_paper"], c["gamma"] != 2.00)


# ---------------------------------------------------------------- 4. documents

class Documents(unittest.TestCase):
    def test_toy_example_passes_series_checks(self):
        trial = toy_trial()
        issues, recomputed, _ = J.check_series(trial["series"], n_steps=len(trial["series"]["t"]),
                                               n_agents=trial["N"])
        self.assertEqual(issues, [])
        self.assertEqual(recomputed, [0.8, 0.6, 0.8])

    def test_toy_example_has_every_required_field(self):
        schema = J.read_bytes(SCHEMA).decode("utf-8")
        meta = schema.split("## Trial JSON: required metadata", 1)[1].split("\n## ", 1)[0]
        series = schema.split("## Trial JSON: series", 1)[1].split("\n## ", 1)[0]
        required_meta = [n for n in re.findall(r"^\| (\w+) \| [^|]+ \|", meta, re.M) if n != "Field"]
        required_series = re.findall(r"^\| (\w+) \| [^|]+ \| yes \|", series, re.M)
        self.assertGreater(len(required_meta), 20)
        self.assertGreater(len(required_series), 10)
        trial = toy_trial()
        for name in required_meta:
            self.assertIn(name, trial)
        for name in required_series:
            self.assertIn(name, trial["series"])

    def test_every_issue_code_is_documented(self):
        readme = J.read_bytes(README).decode("utf-8")
        for code in J.ISSUE_CODES:
            self.assertIn(f"`{code}`", readme)


# ---------------------------------------------------------------- 5. contract v0.2.2

class ContractV022(unittest.TestCase):
    """Contract v0.2.2: version acceptance, required fields, incomplete trials."""
    
    def test_accepts_v022_version(self):
        # v0.2.2 should be in ACCEPTED_TRACE_VERSIONS
        self.assertIn("0.2.2", J.ACCEPTED_TRACE_VERSIONS)
    
    def test_trial_complete_check(self):
        # Complete trial
        trial = {"timed_out": False, "steps_completed": 600, "n_steps_planned": 600}
        is_complete, reason = JC.is_trial_complete(trial)
        self.assertTrue(is_complete)
        self.assertIsNone(reason)
        
        # Timed out trial is incomplete
        trial = {"timed_out": True, "steps_completed": 400, "n_steps_planned": 600}
        is_complete, reason = JC.is_trial_complete(trial)
        self.assertFalse(is_complete)
        self.assertIn("timed_out=true", reason)
        
        # Steps mismatch is incomplete
        trial = {"timed_out": False, "steps_completed": 400, "n_steps_planned": 600}
        is_complete, reason = JC.is_trial_complete(trial)
        self.assertFalse(is_complete)
        self.assertIn("steps_completed=400 != n_steps_planned=600", reason)
    
    def test_v022_required_fields_present(self):
        trial = {
            "timeout_seconds": 300.0,
            "host": "test-host-01",
            "rerun_of": None
        }
        issues = []
        result = JC.check_v022_required_fields(trial, issues, where="test-trial")
        self.assertTrue(result)
        self.assertEqual(len(issues), 0)
    
    def test_v022_missing_timeout_seconds(self):
        trial = {"host": "test-host-01", "rerun_of": None}
        issues = []
        result = JC.check_v022_required_fields(trial, issues, where="test-trial")
        self.assertFalse(result)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["code"], "trial.metadata")
        self.assertIn("timeout_seconds", issues[0]["detail"])
    
    def test_v022_missing_host(self):
        trial = {"timeout_seconds": 300.0, "rerun_of": None}
        issues = []
        result = JC.check_v022_required_fields(trial, issues, where="test-trial")
        self.assertFalse(result)
        self.assertEqual(len(issues), 1)
        self.assertIn("host", issues[0]["detail"])
    
    def test_v022_missing_rerun_of_field(self):
        trial = {"timeout_seconds": 300.0, "host": "test-host-01"}
        issues = []
        result = JC.check_v022_required_fields(trial, issues, where="test-trial")
        self.assertFalse(result)
        self.assertEqual(len(issues), 1)
        self.assertIn("rerun_of", issues[0]["detail"])
    
    def test_v022_rerun_of_can_be_null(self):
        trial = {"timeout_seconds": 300.0, "host": "test-host-01", "rerun_of": None}
        issues = []
        result = JC.check_v022_required_fields(trial, issues, where="test-trial")
        self.assertTrue(result)
        self.assertEqual(len(issues), 0)
    
    def test_v022_rerun_of_can_be_trial_id(self):
        trial = {
            "timeout_seconds": 300.0,
            "host": "test-host-01",
            "rerun_of": "table10-g1.05-N20-vAC-s42"
        }
        issues = []
        result = JC.check_v022_required_fields(trial, issues, where="test-trial")
        self.assertTrue(result)
        self.assertEqual(len(issues), 0)
    
    def test_determinism_prefix_check_exact_match(self):
        incomplete = {
            "steps_completed": 3,
            "series": {
                "modal_agreement": [0.8, 0.6, 0.8],
                "system_tension": [1.0, 1.2, 1.5]
            }
        }
        complete = {
            "steps_completed": 5,
            "series": {
                "modal_agreement": [0.8, 0.6, 0.8, 0.9, 0.95],
                "system_tension": [1.0, 1.2, 1.5, 1.8, 2.0]
            }
        }
        # For inline series, trial_dir can be any path (no NPZ files)
        matches, mismatches = JC.check_determinism_prefix(
            incomplete, complete, ["modal_agreement", "system_tension"], "."
        )
        self.assertTrue(matches)
        self.assertEqual(len(mismatches), 0)
    
    def test_determinism_prefix_check_mismatch(self):
        incomplete = {
            "steps_completed": 3,
            "series": {
                "modal_agreement": [0.8, 0.6, 0.8],
                "system_tension": [1.0, 1.2, 1.5]
            }
        }
        complete = {
            "steps_completed": 5,
            "series": {
                "modal_agreement": [0.8, 0.7, 0.8, 0.9, 0.95],  # Different at step 1
                "system_tension": [1.0, 1.2, 1.5, 1.8, 2.0]
            }
        }
        matches, mismatches = JC.check_determinism_prefix(
            incomplete, complete, ["modal_agreement", "system_tension"], "."
        )
        self.assertFalse(matches)
        self.assertIn("modal_agreement", mismatches)
        self.assertNotIn("system_tension", mismatches)
    
    def test_determinism_prefix_check_nested_arrays(self):
        incomplete = {
            "steps_completed": 2,
            "series": {
                "alive_ids": [[0, 1, 2, 3, 4], [0, 1, 2, 3, 4]],
                "top_targets": [[1, 0, 0, 0, 0], [1, 0, 0, 0, 1]]
            }
        }
        complete = {
            "steps_completed": 4,
            "series": {
                "alive_ids": [[0, 1, 2, 3, 4], [0, 1, 2, 3, 4], [0, 1, 2, 3, 4], [0, 1, 2, 3, 4]],
                "top_targets": [[1, 0, 0, 0, 0], [1, 0, 0, 0, 1], [1, 0, 0, 0, 0], [1, 0, 0, 0, 0]]
            }
        }
        matches, mismatches = JC.check_determinism_prefix(
            incomplete, complete, ["alive_ids", "top_targets"], "."
        )
        self.assertTrue(matches)
        self.assertEqual(len(mismatches), 0)
    
    def test_determinism_prefix_check_nested_arrays_mismatch(self):
        incomplete = {
            "steps_completed": 2,
            "series": {
                "alive_ids": [[0, 1, 2, 3, 4], [0, 1, 2, 3, 4]],
                "top_targets": [[1, 0, 0, 0, 0], [1, 0, 0, 0, 1]]
            }
        }
        complete = {
            "steps_completed": 4,
            "series": {
                "alive_ids": [[0, 1, 2, 3, 4], [0, 1, 2, 3, 4], [0, 1, 2, 3, 4], [0, 1, 2, 3, 4]],
                "top_targets": [[1, 0, 0, 0, 0], [1, 0, 2, 0, 1], [1, 0, 0, 0, 0], [1, 0, 0, 0, 0]]  # Different at step 1
            }
        }
        matches, mismatches = JC.check_determinism_prefix(
            incomplete, complete, ["alive_ids", "top_targets"], "."
        )
        self.assertFalse(matches)
        self.assertIn("top_targets", mismatches)
        self.assertNotIn("alive_ids", mismatches)
    
    def test_v022_trial_with_fields_in_ensemble(self):
        """Test that a v0.2.2 trial with all required fields passes metadata check."""
        ens, spec = build_ensemble()
        ens = copy.deepcopy(ens)
        # Update one trial to v0.2.2 format
        trial_key = "table2-g2.00-N5-vAC-s42"
        trial = ens["trials"][trial_key]
        trial["contract_version"] = "0.2.2"
        trial["timeout_seconds"] = 600.0
        trial["host"] = "test-machine-01"
        trial["rerun_of"] = None
        
        with tempfile.TemporaryDirectory() as d:
            traces = os.path.join(d, "table2")
            os.makedirs(os.path.join(traces, "trials"))
            man = dict(ens["manifest"])
            man["contract_version"] = "0.2.2"
            write_text(os.path.join(traces, "manifest.json"), json.dumps(man))
            
            for stem, t in ens["trials"].items():
                write_text(os.path.join(traces, "trials", stem + ".json"), json.dumps(t))
            
            # Check that metadata passes for this trial
            raw = J.read_bytes(os.path.join(traces, "trials", trial_key + ".json"))
            tr = J.load_json_strict(raw)
            issues = J.check_metadata(tr, trial_key, spec)
            
            # Should pass with no issues
            self.assertEqual(len(issues), 0, f"Expected no issues, got: {issues}")
    
    def test_v022_trial_missing_timeout_seconds_fails(self):
        """Test that a v0.2.2 trial without timeout_seconds fails metadata check."""
        ens, spec = build_ensemble()
        ens = copy.deepcopy(ens)
        trial_key = "table2-g2.00-N5-vAC-s42"
        trial = ens["trials"][trial_key]
        trial["contract_version"] = "0.2.2"
        # Missing timeout_seconds
        trial["host"] = "test-machine-01"
        trial["rerun_of"] = None
        
        with tempfile.TemporaryDirectory() as d:
            traces = os.path.join(d, "table2")
            os.makedirs(os.path.join(traces, "trials"))
            man = dict(ens["manifest"])
            man["contract_version"] = "0.2.2"
            write_text(os.path.join(traces, "manifest.json"), json.dumps(man))
            
            for stem, t in ens["trials"].items():
                write_text(os.path.join(traces, "trials", stem + ".json"), json.dumps(t))
            
            raw = J.read_bytes(os.path.join(traces, "trials", trial_key + ".json"))
            tr = J.load_json_strict(raw)
            issues = J.check_metadata(tr, trial_key, spec)
            
            # Should fail with trial.metadata issue about timeout_seconds
            self.assertGreater(len(issues), 0)
            self.assertEqual(issues[0]["code"], "trial.metadata")
            self.assertIn("timeout_seconds", issues[0]["detail"])


if __name__ == "__main__":
    unittest.main()
