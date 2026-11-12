"""Differential tests: the judge against Black's official code at the pinned SHA.

The judge reimplements time_to_95, the modal-target agreement, and gini, and parses the
script's printed table. Comments saying "same as the official code" are not evidence;
these tests are. Each runs the official function (loaded by black_reference, never
copied into this repo) and the judge's on the same inputs.

Needs a checkout of maxwell-black/mimetic-desire-simulation at the pinned SHA:
    BLACK_REPO=/path/to/checkout python3 -m unittest discover -s eval/judge -p 'test_*.py'
Without one these tests are skipped, unless REQUIRE_OFFICIAL=1 (set in CI), which makes
a missing checkout a failure.
"""
import os
import random
import re
import unittest

import numpy as np

import black_reference as B
import judge_table2 as J
from test_judge import toy_trial

OK, WHY = B.available()
if not OK and os.environ.get("REQUIRE_OFFICIAL") == "1":
    raise RuntimeError(f"REQUIRE_OFFICIAL=1 but the official code is unavailable: {WHY}")
OFFICIAL = B.load() if OK else None

# Aggression snapshots for the schema's toy example. Row i is the aggression agent i
# directs at each agent; the diagonal is never read. All five agents are alive.
TOY_SNAPSHOTS = [
    [[0, 0.2, 0.1, 0.1, 0.1], [0.125, 0, 0, 0, 0], [0.125, 0, 0, 0, 0], [0.125, 0, 0, 0, 0], [0.125, 0, 0, 0, 0]],
    [[0, 0.1, 0.05, 0.05, 0.1], [0.2, 0, 0, 0, 0], [0.2, 0, 0, 0, 0], [0.2, 0, 0, 0, 0], [0, 0.1, 0.1, 0.1, 0]],
    [[0, 0.2, 0.1, 0.1, 0.1], [0.2, 0, 0, 0, 0.05], [0.2, 0, 0, 0, 0], [0.2, 0, 0.1, 0, 0], [0.2, 0, 0, 0.05, 0]],
]
# Schema field -> official history series.
SCHEMA_TO_OFFICIAL = dict(
    n_alive="n_active_agents", system_tension="system_tension", modal_agreement="modal_agreement",
    eligible_count="eligible_agents", aggression_gini="aggression_gini", top_target_share="aggression_max_share",
    convergence_ratio="convergence_ratio", aggression_entropy="aggression_entropy",
    top_R="top_target_aggression", mean_R="mean_aggression")


def export_step(A, alive):
    """Build one step of trace fields from an aggression state, per the schema's definitions."""
    n = len(alive)
    alive_ids = [i for i in range(n) if alive[i]]
    received = [float(sum(A[o][v] for o in alive_ids if o != v)) for v in alive_ids]
    eligible_ids, top_targets = [], []
    for i in alive_ids:
        targets = [j for j in alive_ids if j != i]
        if not targets:
            continue
        vec = np.asarray([A[i][j] for j in targets], dtype=float)
        if float(np.sum(vec)) < 1e-8:  # eligibility cutoff, as the schema states
            continue
        eligible_ids.append(i)
        top_targets.append(targets[int(np.argmax(vec))])  # ties: first living target in alive order
    return alive_ids, received, eligible_ids, top_targets


def random_state(rng, n):
    """Random aggression with ties (values on a coarse grid), dead agents, and silent rows."""
    A = [[rng.choice([0.0, 0.0, 0.1, 0.2, 0.25, 0.5]) for _ in range(n)] for _ in range(n)]
    alive = [rng.random() > 0.2 for _ in range(n)]
    for i in range(n):
        if rng.random() < 0.15:
            A[i] = [0.0] * n  # ineligible: no outgoing aggression
    return A, alive


@unittest.skipUnless(OK, WHY)
class AgainstOfficial(unittest.TestCase):
    def test_time_to_95(self):
        rng = random.Random(0)
        for _ in range(3000):
            series = [rng.choice([0.9, 0.94, 0.949999, 0.95, 0.96, 1.0]) for _ in range(rng.randint(0, 40))]
            for consecutive in (1, 3, 10):
                self.assertEqual(J.time_to_95(series, consecutive=consecutive),
                                 OFFICIAL.time_to_95(series, consecutive=consecutive))

    def test_gini(self):
        rng = np.random.default_rng(1)
        cases = [np.array([]), np.zeros(4), np.array([3.0])]
        cases += [rng.choice([0.0, 0.1, 0.5, 2.0], size=rng.integers(1, 60)) for _ in range(500)]
        for v in cases:
            self.assertEqual(J.gini(v), OFFICIAL.gini(v))

    def test_trace_built_per_schema_reproduces_record_metrics(self):
        """For random states, a trace step exported per the schema has the agreement, eligible
        count, tension, and gini the official record_metrics writes, and passes the judge."""
        rng = random.Random(2)
        for _ in range(400):
            n = rng.randint(2, 12)
            A, alive = random_state(rng, n)
            official = OFFICIAL.record(A, alive)
            alive_ids, received, eligible_ids, top_targets = export_step(A, alive)
            _, agreement = J.modal_from_targets(top_targets)
            self.assertEqual(agreement, official["modal_agreement"])
            self.assertEqual(len(eligible_ids), official["eligible_agents"])
            self.assertAlmostEqual(sum(received), official["system_tension"], places=12)
            self.assertAlmostEqual(J.gini(received), official["aggression_gini"], places=12)
            series = dict(t=[0], n_alive=[len(alive_ids)], alive_ids=[alive_ids], eligible_ids=[eligible_ids],
                          eligible_count=[official["eligible_agents"]], top_targets=[top_targets],
                          received_aggression=[received], system_tension=[official["system_tension"]],
                          modal_agreement=[official["modal_agreement"]],
                          aggression_gini=[official["aggression_gini"]])
            issues, _, _ = J.check_series(series, n_steps=1, n_agents=n)
            self.assertEqual(issues, [])

    def test_stdout_parser_reads_the_official_row_format(self):
        rng = random.Random(3)
        for _ in range(500):
            values = dict(gamma=rng.choice(J.GAMMAS), pk_m=rng.random(), pk_sd=rng.random() / 3,
                          fn_m=rng.random(), fn_sd=rng.random() / 3, pk_g=rng.random(),
                          t95_str=rng.choice(["--", "7", "29", "421", "1203"]), conv_rate=rng.randint(0, 8) / 8)
            line = OFFICIAL.format_row(**values)
            rows = J.parse_table2_stdout("header\n" + line + "\n")
            self.assertEqual(list(rows), [f"{values['gamma']:.2f}"], line)
            row = rows[f"{values['gamma']:.2f}"]
            self.assertEqual(row["peak_modal_mean"], f"{values['pk_m']:.3f}")
            self.assertEqual(row["final_modal_sd"], f"{values['fn_sd']:.3f}")
            self.assertEqual(row["med_t95"], values["t95_str"])
            self.assertEqual(row["conv_pct"], f"{values['conv_rate'] * 100:.0f}")

    def test_judge_expected_row_equals_what_the_script_prints(self):
        """score_cell's expected_script_row matches the official print for the same per-trial values."""
        rng = random.Random(4)
        for _ in range(200):
            g = rng.choice(J.GAMMAS)
            runs = [dict(seed=s, t95=rng.choice([None, rng.randint(5, 600)]), peak_modal=rng.random(),
                         final_modal=rng.random(), peak_gini=rng.random()) for s in J.SEEDS]
            cell = J.score_cell(g, runs)
            conv = [r["t95"] for r in runs if r["t95"] is not None]
            med = int(np.median(conv)) if conv else None  # the script's own line, checked below
            line = OFFICIAL.format_row(gamma=g, pk_m=np.mean([r["peak_modal"] for r in runs]),
                                pk_sd=np.std([r["peak_modal"] for r in runs]),
                                fn_m=np.mean([r["final_modal"] for r in runs]),
                                fn_sd=np.std([r["final_modal"] for r in runs]),
                                pk_g=np.mean([r["peak_gini"] for r in runs]),
                                t95_str=str(med) if med is not None else "--", conv_rate=len(conv) / len(runs))
            printed = J.parse_table2_stdout(line)[f"{g:.2f}"]
            self.assertEqual(printed, cell["expected_script_row"])
            self.assertTrue(J.score_cell(g, runs, script_row=printed)["checks"]["matches_script_output"])

    def test_script_truncates_the_median(self):
        # Known mismatch 3 rests on this line of reproduce_table_2.py at the pinned SHA.
        self.assertRegex(OFFICIAL.table2_main_source,
                         re.escape("med_t95 = int(np.median(converged)) if converged else None"))

    def test_schema_toy_is_official_output(self):
        toy = toy_trial()["series"]
        for t, A in enumerate(TOY_SNAPSHOTS):
            official = OFFICIAL.record(A, [True] * 5)
            for schema_name, official_name in SCHEMA_TO_OFFICIAL.items():
                # The toy prints at most 4 decimals: rule A at 4 decimals.
                self.assertTrue(J.consistent_with_printed(official[official_name], toy[schema_name][t], 4),
                                f"t={t} {schema_name}: toy {toy[schema_name][t]} official {official[official_name]}")
            alive_ids, received, eligible_ids, top_targets = export_step(A, [True] * 5)
            self.assertEqual(toy["alive_ids"][t], alive_ids)
            self.assertEqual(toy["eligible_ids"][t], eligible_ids)
            self.assertEqual(toy["top_targets"][t], top_targets)
            for printed, value in zip(toy["received_aggression"][t], received, strict=True):
                self.assertTrue(J.consistent_with_printed(value, printed, 4))


if __name__ == "__main__":
    unittest.main()
