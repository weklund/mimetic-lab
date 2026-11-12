#!/usr/bin/env python3
"""Re-score recorded C-T2 cells under contract v0.2.1, without the traces.

NOT the official judge. The official verdict comes from judge_table2.py run on the
archived traces. This script exists because the v0.2 judge run's traces are not yet
in the repo: it takes the per-trial values that run recorded in table2-result.json
(t95, peak modal, final modal, peak gini per seed) and applies the v0.2.1 cell rules
(judge_table2.score_cell) to them. It cannot re-check trace structure, identities,
or the recorded series; only the official judge on the traces can.

Usage:
    python3 rescore_from_result.py [RESULT_JSON]
"""
import json
import os
import sys

import judge_table2 as J


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    path = argv[0] if argv else os.path.join(J._HERE, "table2-result.json")
    recorded = J.load_json_strict(J.read_bytes(path))
    rows, all_pass = [], True
    for c in recorded["cells"]:
        recorded_series = c.get("raw_t95_from_recorded_series") or [None] * len(c["per_trial"])
        runs = [dict(r, t95_recorded_series=rs) for r, rs in zip(c["per_trial"], recorded_series, strict=True)]
        cell = J.score_cell(c["gamma"], runs)
        all_pass &= cell["cell_pass"]
        rows.append(dict(gamma=cell["gamma"], k=cell["k"], published_k=cell["published_k"],
                         np_median=cell["median_t95_np"], script_int=cell["median_t95_script_int"],
                         paper_median=cell["published_med_t95"], checks=cell["checks"], cell_pass=cell["cell_pass"]))
    print(json.dumps(dict(source=os.path.basename(path), recorded_by=recorded.get("judge_version", "0.2"),
                          rescored_under=J.CONTRACT, all_cells_pass=all_pass, cells=rows), indent=1))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
