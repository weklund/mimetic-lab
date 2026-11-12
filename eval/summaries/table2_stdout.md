# Table 2 official archive and stdout fact note

Date: 2026-11-12.

Official C-T2 traces, contract v0.2, pinned SHA `89e7bbb57db62e3c830a8ca672a0805080df3970`.

## Ensemble

104 trials, all complete, with series inlined in the trial JSON (no NPZ). Manifest sha256 `29010da3503331b953e6b030d8eebace72a86bae1b04acbda3af97cff99eaf1a`. This archive does not rewrite the official manifest or any trial file. File hashes of the official ensemble are in `eval/traces/v0.2/table2/SHA256SUMS`. Recorded run hashes, including `exporter_sha256`, are in `eval/traces/v0.2/table2/HASHES.json`.

## Exporter

The Table 2 export used `/workspace/mimetic-repro/bin/export_v02.py` at sha256 `a7589f4d19f72c89c324c9af3549bbfa797dafbfc2b0b7440aa1881c952b6014`, recorded in the run meta at start, without `--npz`. The exact source file of that hash was not retained. The canonical exporter on main (PR #23), sha256 `cb8494ba1ba242224a134c187f82461696f832ae1255c4aa2f2853a0eab8d2c5`, is the later NPZ-offload version and was not used for Table 2. A local snapshot named `export_v02.table2-a7589f4d.py` hashes to `f09d14865088060fae07ec439e7e655787cc59046857359c565cd3e80edb88dc` and is not the Table 2 exporter.

## Stdout

`script_stdout.txt` is the saved first official-script stdout, sha256 `d6da73cb73bb54dd6870912083420bbfafadd545ab7aa6768bd22f63da1e8c44`. It is byte-identical to both the first official harness run (`/workspace/mimetic-repro/runs/table_2/stdout.txt`) and the export run (`/workspace/mimetic-repro/runs/table_2_v02/stdout.txt`). Those stdout paths were not added as fields on the v0.2 manifest. The official manifest is left unchanged so recorded trial-file hashes stay valid.

## Report-only paper vs script note

At gamma 2.00, draft 18 prints median t95 as 30; the official script's integer median is 29. This is a script rule, not a model fail: reproduction of a table uses the script, and the mismatch is reported, not fixed.

## Scoring

This note does not score C-T2. A pass is a judgment of Black's model at the pinned SHA, not of Girard.
