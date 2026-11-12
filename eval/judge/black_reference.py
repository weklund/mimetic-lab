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

load_table10() does the same for the Table 10 runner in small_n_utils.py. Testing the
runner means running Black's model, so it compiles the model's definitions (imports,
module constants, GirardConfig, GirardSimulation and the small_n_utils functions) from
the pinned sources. Module-level code other than definitions is never run, and nothing
is imported from the checkout by name. The model needs networkx.
"""
import ast
import hashlib
import os
import sys
import types
from collections import defaultdict
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple

import numpy as np

PINNED_SHA = "89e7bbb57db62e3c830a8ca672a0805080df3970"
PINNED_FILES = {
    "reproduce_table_2.py": "675b238d5663c256616b574076005064164264f80e35fd60126f3e0d1960699a",
    "girard_2x2_v3.py": "4c9ffcf6d9118e524da7bce8de55cac5e0b5e3392db5ac349942182cde980be8",
    "small_n_utils.py": "7306d1d5e9dfbad2d50240f350d1ed499d88fcb97bd919c58a2846160a32c178",
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


# Top-level statements load_table10 compiles. Anything else at module level is refused.
_DEFINITION_NODES = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign)


def _definitions(name, skip_import_from=()):
    """Compile only the definition statements of a pinned source file into a fresh namespace."""
    tree = ast.parse(_source(name))
    body = []
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  # docstring
        if isinstance(node, ast.ImportFrom) and node.module in skip_import_from:
            continue
        if not isinstance(node, _DEFINITION_NODES):
            raise RuntimeError(f"{name}: unexpected top-level {type(node).__name__} at line {node.lineno}")
        body.append(node)
    return compile(ast.Module(body=body, type_ignores=[]), name, "exec")


def _exec_definitions(name, module_name, inject, skip_import_from=()):
    """Run a file's definitions in a private module namespace and return that namespace.

    @dataclass looks the class's module up in sys.modules, so the module is registered
    there only while the definitions run, under a private name, and removed after.
    """
    code = _definitions(name, skip_import_from)
    module = types.ModuleType(module_name)
    module.__dict__.update(inject)
    sys.modules[module_name] = module
    try:
        exec(code, module.__dict__)
    finally:
        sys.modules.pop(module_name, None)
    return module.__dict__


def load_table10():
    """Return the official Table 10 functions from small_n_utils.py at the pinned SHA.

    adaptive_unanimity_threshold and classify_exhaustion are pure functions.
    run_unanimity_triggered runs the official model (girard_2x2_v3.GirardSimulation).
    Call only when available() is ok. Raises RuntimeError if networkx is missing.
    """
    ok, reason = available()
    if not ok:
        raise RuntimeError(reason)
    try:
        import networkx  # noqa: F401  (the official model imports it)
    except ImportError as exc:
        raise RuntimeError("networkx is required to run the official Table 10 model") from exc

    model = _exec_definitions("girard_2x2_v3.py", "black_girard_2x2_v3", {})
    utils = _exec_definitions("small_n_utils.py", "black_small_n_utils",
                              {k: model[k] for k in ("GirardConfig", "GirardSimulation", "VARIANT_MAP")},
                              skip_import_from=("girard_2x2_v3",))
    return SimpleNamespace(adaptive_unanimity_threshold=utils["adaptive_unanimity_threshold"],
                           classify_exhaustion=utils["classify_exhaustion"],
                           run_unanimity_triggered=utils["run_unanimity_triggered"])
