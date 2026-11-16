"""Pytest for export_v02.py. Default mode is compared to the pre-change exporter.

The Black checkout is not vendored. Set BLACK_REPO, or place the pinned
checkout at /tmp/mimetic-desire-simulation (or eval/.cache/mimetic-desire-simulation).
"""
import ast
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXPORTER = ROOT / "eval" / "wrappers" / "export_v02.py"
GOLDEN = ROOT / "eval" / "wrappers" / "fixtures" / "export_v02_cb8494ba.py"
GOLDEN_SHA = "cb8494ba1ba242224a134c187f82461696f832ae1255c4aa2f2853a0eab8d2c5"
PINNED_SHA = "89e7bbb57db62e3c830a8ca672a0805080df3970"
SMALL_N_SHA = "7306d1d5e9dfbad2d50240f350d1ed499d88fcb97bd919c58a2846160a32c178"
JUDGE_DIR = ROOT / "eval" / "judge"

TIMESTAMP = re.compile(rb"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}")

PROBE = textwrap.dedent("""\
    def main():
        from small_n_utils import run_unanimity_triggered
        run_unanimity_triggered(5, 1.05, "AC", n_steps=20, seed=42)
    """)

TABLE10_DRIVER = textwrap.dedent("""\
    import os
    import time

    def main():
        cut = os.environ.get("EXPORT_FORCE_CUT")
        if cut:
            state = {"n": 0}
            limit = int(cut)
            def clock():
                state["n"] += 1
                if state["n"] <= limit + 1:
                    return 0.0
                return 1.0e12
            time.monotonic = clock
        from small_n_utils import run_unanimity_triggered
        run_unanimity_triggered(5, 1.05, "AC", n_steps=5000, seed=42)
    """)

SPY = textwrap.dedent("""\
    import builtins
    import inspect
    import os

    _real_import = builtins.__import__

    def _wrap(mod):
        fn = getattr(mod, "run_unanimity_triggered", None)
        if fn is None or getattr(fn, "_export_spy", False):
            return
        def spy(*a, **k):
            bound = inspect.signature(fn).bind(*a, **k)
            bound.apply_defaults()
            with open(os.environ["EXPORT_TIMEOUT_SPY"], "a", encoding="utf-8") as fh:
                fh.write(repr(bound.arguments["timeout_seconds"]) + "\\n")
            return fn(*a, **k)
        spy._export_spy = True
        spy.__wrapped__ = fn
        mod.run_unanimity_triggered = spy

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        mod = _real_import(name, globals, locals, fromlist, level)
        if name == "small_n_utils":
            _wrap(mod)
        return mod

    builtins.__import__ = _import
    """)


def black_checkout():
    candidates = []
    if os.environ.get("BLACK_REPO"):
        candidates.append(Path(os.environ["BLACK_REPO"]))
    candidates.append(Path("/tmp/mimetic-desire-simulation"))
    candidates.append(ROOT / "eval" / ".cache" / "mimetic-desire-simulation")
    for path in candidates:
        marker = path / "small_n_utils.py"
        if marker.is_file() and hashlib.sha256(marker.read_bytes()).hexdigest() == SMALL_N_SHA:
            return path
    pytest.skip("pinned Black checkout not found; set BLACK_REPO")


def make_repo(tmp_path, script_name, body):
    src = black_checkout()
    repo = tmp_path / "repo"
    repo.mkdir()
    for name in os.listdir(src):
        if name.endswith(".py"):
            os.symlink(src / name, repo / name)
    dest = repo / script_name
    if dest.is_symlink() or dest.exists():
        dest.unlink()
    dest.write_text(body)
    return repo


def run_export(exporter, repo, script, ensemble, out, extra=None, env=None):
    cmd = [
        sys.executable, str(exporter), str(repo), script, ensemble, str(out),
        "--source-sha", PINNED_SHA, "--command", "export-test",
    ]
    if extra:
        cmd.extend(extra)
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return proc


def ensemble_bytes(out, ensemble):
    base = Path(out) / ensemble
    manifest = (base / "manifest.json").read_bytes()
    trials = {p.name: p.read_bytes() for p in sorted((base / "trials").glob("*.json"))}
    return manifest, trials


def mask(raw):
    return TIMESTAMP.sub(b"TIMESTAMP", raw)


def load_trials(out, ensemble):
    base = Path(out) / ensemble
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    trials = {}
    for path in sorted((base / "trials").glob("*.json")):
        trials[path.name[:-5]] = json.loads(path.read_text(encoding="utf-8"))
    return manifest, trials


def spy_env(spy_dir, spy_file, extra=None):
    env = os.environ.copy()
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(spy_dir) + (os.pathsep + prev if prev else "")
    env["EXPORT_TIMEOUT_SPY"] = str(spy_file)
    if extra:
        env.update(extra)
    spy_file.write_text("")
    return env


def install_spy(tmp_path):
    spy_dir = tmp_path / "spy"
    spy_dir.mkdir()
    (spy_dir / "sitecustomize.py").write_text(SPY)
    return spy_dir, tmp_path / "spy-log.txt"


def spied_values(spy_file):
    text = spy_file.read_text(encoding="utf-8").strip()
    assert text, "official function was not called"
    return [ast.literal_eval(line) for line in text.splitlines()]


def test_default_mode_matches_golden_exporter(tmp_path):
    """Default output matches a run of the exporter at sha256 cb8494ba, aside from wall-clock stamps."""
    assert hashlib.sha256(GOLDEN.read_bytes()).hexdigest() == GOLDEN_SHA
    repo = make_repo(tmp_path, "probe.py", PROBE)
    golden = run_export(GOLDEN, repo, "probe.py", "probe", tmp_path / "golden")
    new = run_export(EXPORTER, repo, "probe.py", "probe", tmp_path / "new")
    assert golden.returncode == 0, golden.stderr
    assert new.returncode == 0, new.stderr
    g_man, g_trials = ensemble_bytes(tmp_path / "golden", "probe")
    n_man, n_trials = ensemble_bytes(tmp_path / "new", "probe")
    assert mask(g_man) == mask(n_man)
    assert {name: mask(raw) for name, raw in g_trials.items()} == {name: mask(raw) for name, raw in n_trials.items()}
    manifest, trials = load_trials(tmp_path / "new", "probe")
    assert manifest["contract_version"] == "0.2"
    for key in ("exporter_sha256", "timeout_seconds", "host", "rerun_of"):
        assert key not in manifest
    trial = next(iter(trials.values()))
    assert trial["contract_version"] == "0.2"
    for key in ("timeout_seconds", "host", "rerun_of", "exporter_sha256"):
        assert key not in trial


def test_v022_arrays_equal_default_arrays(tmp_path):
    repo = make_repo(tmp_path, "probe.py", PROBE)
    default = run_export(EXPORTER, repo, "probe.py", "probe", tmp_path / "default")
    v022 = run_export(
        EXPORTER, repo, "probe.py", "probe", tmp_path / "v022",
        extra=["--contract", "0.2.2", "--timeout-seconds", "30"],
    )
    assert default.returncode == 0, default.stderr
    assert v022.returncode == 0, v022.stderr
    d_man, d_trials = load_trials(tmp_path / "default", "probe")
    v_man, v_trials = load_trials(tmp_path / "v022", "probe")
    assert d_man["contract_version"] == "0.2"
    assert v_man["contract_version"] == "0.2.2"
    assert v_man["exporter_sha256"] == hashlib.sha256(EXPORTER.read_bytes()).hexdigest()
    assert v_man["timeout_seconds"] == 30
    assert v_man["host"] == socket.gethostname()
    assert v_man["rerun_of"] is None
    assert set(d_trials) == set(v_trials)
    for tid, old in d_trials.items():
        new = v_trials[tid]
        assert new["series"] == old["series"]
        assert new["expulsion_events"] == old["expulsion_events"]
        assert new["catharsis_events"] == old["catharsis_events"]
        assert new["viability"] == old["viability"]
        assert new["steps_completed"] == old["steps_completed"]
        assert new["timed_out"] is False
        assert new["timeout_seconds"] == 30
        assert new["host"] == socket.gethostname()
        assert new["rerun_of"] is None
        assert new["contract_version"] == "0.2.2"


def test_v022_requires_explicit_timeout(tmp_path):
    repo = make_repo(tmp_path, "probe.py", PROBE)
    missing = run_export(
        EXPORTER, repo, "probe.py", "probe", tmp_path / "out",
        extra=["--contract", "0.2.2"],
    )
    assert missing.returncode != 0
    assert "timeout-seconds" in missing.stderr
    assert not (tmp_path / "out" / "probe" / "manifest.json").exists()

    zero = run_export(
        EXPORTER, repo, "probe.py", "probe", tmp_path / "zero",
        extra=["--contract", "0.2.2", "--timeout-seconds", "0"],
    )
    assert zero.returncode != 0
    assert "positive" in zero.stderr

    stray = run_export(
        EXPORTER, repo, "probe.py", "probe", tmp_path / "stray",
        extra=["--timeout-seconds", "5"],
    )
    assert stray.returncode != 0
    assert "0.2.2" in stray.stderr


def test_recorded_timeout_equals_argument_passed(tmp_path):
    """The trial records the timeout_seconds value the official function received."""
    repo = make_repo(tmp_path, "probe.py", PROBE)
    spy_dir, spy_file = install_spy(tmp_path)
    default = run_export(
        EXPORTER, repo, "probe.py", "probe", tmp_path / "default",
        env=spy_env(spy_dir, spy_file),
    )
    assert default.returncode == 0, default.stderr
    assert spied_values(spy_file) == [None]

    passed = 7.5
    v022 = run_export(
        EXPORTER, repo, "probe.py", "probe", tmp_path / "v022",
        extra=["--contract", "0.2.2", "--timeout-seconds", str(passed)],
        env=spy_env(spy_dir, spy_file),
    )
    assert v022.returncode == 0, v022.stderr
    seen = spied_values(spy_file)
    assert seen == [passed]
    _manifest, trials = load_trials(tmp_path / "v022", "probe")
    for trial in trials.values():
        assert trial["timeout_seconds"] == seen[0]
        assert trial["timeout_seconds"] == passed


def test_forced_timeout_and_labeled_rerun(tmp_path):
    """A tiny forced timeout plus a labeled rerun passes structural and prefix checks."""
    sys.path.insert(0, str(JUDGE_DIR))
    import judge_common as JC
    import judge_table10 as J10

    repo = make_repo(tmp_path, "exp_small_n_viability.py", TABLE10_DRIVER)
    spy_dir, spy_file = install_spy(tmp_path)
    out = tmp_path / "ensemble"
    tiny = 0.001
    first = run_export(
        EXPORTER, repo, "exp_small_n_viability.py", "table10", out,
        extra=["--contract", "0.2.2", "--timeout-seconds", str(tiny)],
        env=spy_env(spy_dir, spy_file, {"EXPORT_FORCE_CUT": "12"}),
    )
    assert first.returncode == 0, first.stderr
    assert spied_values(spy_file) == [tiny]
    manifest, trials = load_trials(out, "table10")
    assert list(trials) == ["table10-g1.05-N5-vAC-s42"]
    incomplete_id = "table10-g1.05-N5-vAC-s42"
    incomplete = trials[incomplete_id]
    assert incomplete["timed_out"] is True
    assert incomplete["steps_completed"] == 12
    assert incomplete["n_steps_planned"] == 5000
    assert incomplete["script"] == "exp_small_n_viability.py"
    assert incomplete["timeout_seconds"] == tiny
    assert incomplete["host"] == socket.gethostname()
    assert incomplete["rerun_of"] is None
    assert manifest["contract_version"] == "0.2.2"
    assert manifest["timeout_seconds"] == tiny
    assert manifest["rerun_of"] is None
    assert manifest["exporter_sha256"] == hashlib.sha256(EXPORTER.read_bytes()).hexdigest()
    original_bytes = (out / "table10" / "trials" / f"{incomplete_id}.json").read_bytes()

    larger = 30.0
    second = run_export(
        EXPORTER, repo, "exp_small_n_viability.py", "table10", out,
        extra=["--contract", "0.2.2", "--timeout-seconds", str(larger), "--rerun-of", incomplete_id],
        env=spy_env(spy_dir, spy_file),
    )
    assert second.returncode == 0, second.stderr
    assert spied_values(spy_file) == [larger]
    assert (out / "table10" / "trials" / f"{incomplete_id}.json").read_bytes() == original_bytes

    manifest, trials = load_trials(out, "table10")
    rerun_id = incomplete_id + "-rerun"
    assert set(trials) == {incomplete_id, rerun_id}
    assert manifest["trial_ids"] == [incomplete_id, rerun_id]
    assert manifest["rerun_of"] == incomplete_id
    assert manifest["timeout_seconds"] == larger
    assert manifest["host"] == socket.gethostname()
    rerun = trials[rerun_id]
    assert rerun["trial_id"] == rerun_id
    assert rerun["rerun_of"] == incomplete_id
    assert rerun["script"] == "exp_small_n_viability.py"
    assert "/" not in rerun["script"]
    assert rerun["timed_out"] is False
    assert rerun["steps_completed"] == 5000
    assert rerun["n_steps_planned"] == 5000
    assert rerun["seed"] == 42
    assert rerun["timeout_seconds"] == larger
    assert rerun["timeout_seconds"] == spied_values(spy_file)[0]
    assert rerun["host"] == socket.gethostname()
    assert incomplete["timeout_seconds"] == tiny

    trial_dir = str(out / "table10" / "trials")
    for stem, trial in ((incomplete_id, incomplete), (rerun_id, rerun)):
        issues = []
        assert JC.check_v022_required_fields(trial, issues, where=stem) is True
        meta_issues = J10.check_trial_metadata(trial, stem, "AC", 1.05, 5, trial_dir)
        assert meta_issues == [], meta_issues

    matches, mismatches = JC.check_determinism_prefix(
        incomplete, rerun, J10.DETERMINISM_ARRAYS, trial_dir)
    assert matches, mismatches
    events_ok, event_mismatches = JC.check_events_prefix(
        incomplete, rerun, incomplete["steps_completed"])
    assert events_ok, event_mismatches
    assert any(event["step"] < incomplete["steps_completed"] for event in rerun["expulsion_events"])

    result = J10.judge(str(out / "table10"))
    structural = {
        "trial.metadata", "trial.json", "v022.determinism", "v022.rerun_invalid",
        "v022.multiple_reruns", "viability.evidence", "viability.d7", "viability.missing",
    }
    bad = [item for item in result["issues"] if item["code"] in structural]
    assert bad == [], bad
    cell = next(c for c in result["cells"] if c["variant"] == "AC" and c["gamma"] == 1.05 and c["N"] == 5)
    assert cell["n_reruns"] == 1
    assert cell["n_incomplete"] == 0
    assert cell["determinism_failures"] == 0
    assert cell["n_complete"] == 1


TWO_SEEDS = textwrap.dedent("""\
    def main():
        from small_n_utils import run_unanimity_triggered
        run_unanimity_triggered(5, 1.05, "AC", n_steps=8, seed=42)
        run_unanimity_triggered(5, 1.05, "AC", n_steps=8, seed=1042)
    """)


def test_recovered_trial_is_registered_in_its_cell(tmp_path):
    """A trial file missing from the manifest is added to trial_ids and to its cell."""
    repo = make_repo(tmp_path, "probe.py", TWO_SEEDS)
    out = tmp_path / "ensemble"
    first = run_export(
        EXPORTER, repo, "probe.py", "probe", out,
        extra=["--contract", "0.2.2", "--timeout-seconds", "30"],
    )
    assert first.returncode == 0, first.stderr
    kept = "probe-g1.05-N5-vAC-s42"
    dropped = "probe-g1.05-N5-vAC-s1042"
    manifest_path = out / "probe" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["trial_ids"] = [tid for tid in manifest["trial_ids"] if tid != dropped]
    for cell in manifest["cells"]:
        cell["trial_ids"] = [tid for tid in cell["trial_ids"] if tid != dropped]
        cell["n"] = len(cell["trial_ids"])
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert (out / "probe" / "trials" / f"{dropped}.json").is_file()

    rerun = run_export(
        EXPORTER, repo, "probe.py", "probe", out,
        extra=["--contract", "0.2.2", "--timeout-seconds", "30", "--rerun-of", kept],
    )
    assert rerun.returncode == 0, rerun.stderr
    merged, _trials = load_trials(out, "probe")
    assert dropped in merged["trial_ids"]
    cell = next(c for c in merged["cells"] if c["N"] == 5 and c["gamma"] == 1.05 and c["variant"] == "AC")
    assert dropped in cell["trial_ids"]
    assert cell["trial_ids"].count(dropped) == 1
    assert cell["n"] == len(cell["trial_ids"])
    assert kept + "-rerun" in cell["trial_ids"]


def test_missing_manifest_recovers_trial_files(tmp_path):
    """A labeled rerun with no manifest.json still lists the trial files already on disk."""
    repo = make_repo(tmp_path, "probe.py", TWO_SEEDS)
    out = tmp_path / "ensemble"
    first = run_export(
        EXPORTER, repo, "probe.py", "probe", out,
        extra=["--contract", "0.2.2", "--timeout-seconds", "30"],
    )
    assert first.returncode == 0, first.stderr
    kept = "probe-g1.05-N5-vAC-s42"
    other = "probe-g1.05-N5-vAC-s1042"
    trials = out / "probe" / "trials"
    before = {name: (trials / f"{name}.json").read_bytes() for name in (kept, other)}
    (out / "probe" / "manifest.json").unlink()

    rerun = run_export(
        EXPORTER, repo, "probe.py", "probe", out,
        extra=["--contract", "0.2.2", "--timeout-seconds", "30", "--rerun-of", kept],
    )
    assert rerun.returncode == 0, rerun.stderr
    assert (trials / f"{kept}.json").read_bytes() == before[kept]
    assert (trials / f"{other}.json").read_bytes() == before[other]
    merged, _loaded = load_trials(out, "probe")
    rerun_id = kept + "-rerun"
    assert set(merged["trial_ids"]) == {kept, other, rerun_id}
    cell = next(c for c in merged["cells"] if c["N"] == 5 and c["gamma"] == 1.05 and c["variant"] == "AC")
    assert set(cell["trial_ids"]) == {kept, other, rerun_id}
    assert cell["n"] == 3


def test_second_labeled_rerun_does_not_overwrite_json_or_npz(tmp_path):
    """Refusing an existing labeled rerun leaves both the JSON and the NPZ unchanged."""
    repo = make_repo(tmp_path, "probe.py", PROBE)
    out = tmp_path / "ensemble"
    extra = ["--contract", "0.2.2", "--timeout-seconds", "30", "--npz"]
    first = run_export(EXPORTER, repo, "probe.py", "probe", out, extra=extra)
    assert first.returncode == 0, first.stderr
    tid = "probe-g1.05-N5-vAC-s42"
    rerun_extra = extra + ["--rerun-of", tid]
    second = run_export(EXPORTER, repo, "probe.py", "probe", out, extra=rerun_extra)
    assert second.returncode == 0, second.stderr
    trials = out / "probe" / "trials"
    paths = [
        trials / f"{tid}.json",
        trials / f"{tid}.npz",
        trials / f"{tid}-rerun.json",
        trials / f"{tid}-rerun.npz",
    ]
    assert all(path.is_file() for path in paths)
    before = {path: path.read_bytes() for path in paths}
    third = run_export(EXPORTER, repo, "probe.py", "probe", out, extra=rerun_extra)
    assert third.returncode != 0
    assert "refusing to overwrite" in third.stderr
    after = {path: path.read_bytes() for path in paths}
    assert after == before
