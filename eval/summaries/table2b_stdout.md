# Table 2b official archive and stdout fact note

Date: 2026-11-15.

Official C-T2b traces, contract v0.2, pinned SHA `89e7bbb57db62e3c830a8ca672a0805080df3970`.

## Ensemble

300 trials, all complete, with series inlined in the trial JSON (no NPZ). Manifest sha256 `35ce25a9ab5648db3fbd7c61442fb774e4744e51731ff2108455b004fe17c044`. This archive does not rewrite the official manifest or any trial file. File hashes of the official ensemble are in `eval/traces/v0.2/table2b/SHA256SUMS`. Recorded run hashes, including `exporter_sha256`, are in `eval/traces/v0.2/table2b/HASHES.json`.

## Exporter

The Table 2b export used `mimetic-repro/bin/export_v02.py` at sha256 `cb8494ba1ba242224a134c187f82461696f832ae1255c4aa2f2853a0eab8d2c5`, recorded in the run meta at start, without `--npz`. This is the canonical `eval/wrappers/export_v02.py` on main (PR #23); both files have this sha256. The export is labeled contract v0.2 because the canonical exporter hardcodes CONTRACT = "0.2". Contract line 182 keeps "0.2" accepted for traces already exported under it. The v0.2.2 timeout rule covers `run_unanimity_triggered`. Table 2b uses `run()`, so this ensemble was archived as v0.2 (Lab decision 2026-11-15).

## Stdout

`script_stdout.txt` is the saved first official-script stdout, sha256 `89cf75f8978bacfe99662efbade5f8d0db0245fcd9a776c369131ca0eb294e95`. It is byte-identical to both the first official harness run (`mimetic-repro/runs/table_2b/stdout.txt`) and the export run (`mimetic-repro/runs/table_2b_v02/stdout.txt`). Those stdout paths were not added as fields on the v0.2 manifest. The official manifest is left unchanged so recorded trial-file hashes stay valid.

## Report-only paper vs script note

Draft 18 Table 2b (at the pinned SHA, `paper/paper_draft_18.md`) groups rates as gamma <= 1.01, gamma = 1.02, gamma = 1.03, and gamma >= 1.04. The official script prints each of 1.01, 1.02, 1.03, 1.04, and 1.05. The printed convergence rates agree: N=50 is 0%, 10%, 90%, 100%, 100%; N=100 and N=200 are 0%, 0%, 100%, 100%, 100%. The paper's accompanying sentence gives median t95 at gamma 1.05 as 88, 98, and 102 for N=50, 100, and 200; the official script prints the same three integers. No numeric mismatch was found between the draft 18 Table 2b rates, that t95 sentence, and `script_stdout.txt`.

## Scoring

This note does not score C-T2b. A pass is a judgment of Black's model at the pinned SHA, not of Girard. This archive does not claim any G upgrade.
