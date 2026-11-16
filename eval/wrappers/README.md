# Trace exporter

`export_v02.py` wraps an unmodified script from Maxwell Black's simulation and writes a contract trace. It does not score the trace.

Default mode is contract `0.2`. Omit `--contract`, or pass `--contract 0.2`. That mode does not take a timeout and does not add `timeout_seconds`, `host`, `rerun_of`, or `exporter_sha256`.

Contract `0.2.2` is opt-in and requires an explicit timeout:

```bash
python3 eval/wrappers/export_v02.py <repo_dir> <script.py> <ensemble_id> <out_root> \
  --source-sha <40-char SHA> \
  --contract 0.2.2 --timeout-seconds 120
```

`--timeout-seconds` is a positive finite number of seconds. The exporter passes that value through `run_unanimity_triggered`'s own `timeout_seconds` argument. The manifest `contract_version` is `0.2.2`. The manifest records `exporter_sha256` of this file at run start, plus `timeout_seconds`, `host`, and `rerun_of`. Each trial records `timeout_seconds`, `host`, and `rerun_of` (`null` unless this invocation is a labeled rerun).

A labeled rerun keeps the incomplete trial and writes a second file:

```bash
python3 eval/wrappers/export_v02.py <repo_dir> exp_small_n_viability.py table10 <out_root> \
  --source-sha <40-char SHA> \
  --contract 0.2.2 --timeout-seconds 600 \
  --rerun-of table10-g1.05-N10-vAC-s14042
```

The rerun file is `<trial_id>-rerun.json`. Its `script` field is the script name on the command line, so an official Table 10 rerun stays `exp_small_n_viability.py`. `--timeout-seconds` and `--rerun-of` are rejected unless `--contract 0.2.2` is set.
