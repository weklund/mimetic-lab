"""Black's official metric code, loaded from a checkout at the pinned SHA, for tests.

Nothing from Black's repository is copied into this one. Tests point BLACK_REPO at a
checkout of github.com/maxwell-black/mimetic-desire-simulation at the pinned SHA (CI
clones it), and this module:

1. checks the SHA-256 of the two source files, so a test can never run against a
   different version than the one the contract pins;
2. parses them with `ast` and compiles only the functions it needs (time_to_95,
   GirardSimulation._alive_ids, _received_aggression_vector, _gini, _entropy,
   record_metrics) and the f-string that prints one row of Table 2. The scripts
   themselves are never run.

The judge's reimplementations are then tested against this code on the same inputs.
"""
import ast
import hashlib
import os
from collections import defaultdict
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple

import numpy as np

PINNED_SHA = "89e7bbb57db62e3c830a8ca672a0805080df3970"
PINNED_FILES = {
    "reproduce_table_2.py": "675b238d5663c256616b574076005064164264f80e35fd60126f3e0d1960699a",
    "girard_2x2_v3.py": "4c9ffcf6d9118e524da7bce8de55cac5e0b5e3392db5ac349942182cde980be8",
}
_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CHECKOUT = os.path.join(_HERE, "..", ".cache", "mimetic-desire-simulation")
METHODS = ["_alive_ids", "_received_aggression_vector", "_gini", "_entropy", "record_metrics"]


def checkout_dir():
    return os.environ.get("BLACK_REPO", DEFAULT_CHECKOUT)


def available():
    """(ok, reason). ok is True only when both pinned files exist with the pinned hashes."""
    root = checkout_dir()
    for name, digest in PINNED_FILES.items():
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            return False, f"{path} not found; set BLACK_REPO to a checkout at {PINNED_SHA}"
        with open(path, "rb") as fh:
            actual = hashlib.sha256(fh.read()).hexdigest()
        if actual != digest:
            return False, f"{path} is not the version at {PINNED_SHA} (SHA-256 differs)"
    return True, ""


def _source(name):
    with open(os.path.join(checkout_dir(), name), encoding="utf-8") as fh:
        return fh.read()


def _namespace():
    return dict(np=np, Dict=Dict, List=List, Tuple=Tuple, Optional=Optional)


def load():
    """Return a namespace with the official functions. Call only when available() is ok."""
    ok, reason = available()
    if not ok:
        raise RuntimeError(reason)
    t2_src = _source("reproduce_table_2.py")
    t2 = ast.parse(t2_src)
    funcs = {n.name: n for n in t2.body if isinstance(n, ast.FunctionDef)}

    ns = _namespace()
    exec(compile(ast.Module(body=[funcs["time_to_95"]], type_ignores=[]), "reproduce_table_2.py", "exec"), ns)
    time_to_95 = ns["time_to_95"]

    # The print call whose f-string formats one gamma row of Table 2.
    row_fstring = None
    for node in ast.walk(funcs["main"]):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print"
                and node.args and isinstance(node.args[0], ast.JoinedStr)
                and any(isinstance(v, ast.FormattedValue) and isinstance(v.value, ast.Name)
                        and v.value.id == "gamma" for v in node.args[0].values)):
            row_fstring = node.args[0]
    if row_fstring is None:
        raise RuntimeError("Table 2 row print not found in reproduce_table_2.main")
    row_code = compile(ast.Expression(body=row_fstring), "reproduce_table_2.py", "eval")

    def format_row(**values):
        """Format one Table 2 row exactly as the official print statement does."""
        return eval(row_code, _namespace(), values)

    sim_src = ast.parse(_source("girard_2x2_v3.py"))
    cls = next(n for n in sim_src.body if isinstance(n, ast.ClassDef) and n.name == "GirardSimulation")
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in METHODS]
    if sorted(m.name for m in methods) != sorted(METHODS):
        raise RuntimeError("expected GirardSimulation methods not found")
    official_cls = ast.ClassDef(name="OfficialMetrics", bases=[], keywords=[], body=methods, decorator_list=[],
                                type_params=[])
    ns = _namespace()
    exec(compile(ast.fix_missing_locations(ast.Module(body=[official_cls], type_ignores=[])),
                 "girard_2x2_v3.py", "exec"), ns)
    OfficialMetrics = ns["OfficialMetrics"]

    def record(aggression, alive):
        """Run the official record_metrics on one state. aggression: n x n array; alive: n bools.

        Returns one value per history series (the official names)."""
        n = len(alive)
        sim = OfficialMetrics.__new__(OfficialMetrics)
        sim.graph = SimpleNamespace(nodes=lambda: list(range(n)))
        sim.alive = {i: bool(alive[i]) for i in range(n)}
        sim.aggression = {i: np.asarray(aggression[i], dtype=float) for i in range(n)}
        sim.history = defaultdict(list)
        sim.record_metrics()
        return {key: values[-1] for key, values in sim.history.items()}

    return SimpleNamespace(time_to_95=time_to_95, gini=OfficialMetrics._gini, entropy=OfficialMetrics._entropy,
                           record=record, format_row=format_row, table2_main_source=ast.get_source_segment(
                               t2_src, funcs["main"]))
