"""Common judge utilities for contract v0.2.2 and later.

Shared functions for handling incomplete trials, reruns, and determinism checks.
"""
import itertools
import math
import os
import pickle
import zipfile

try:
    import numpy as np
    from numpy.lib import format as npformat
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def _is_num(x):
    """Check if x is a number (int or float, but not bool)."""
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _is_int(x):
    """Check if x is an integer (but not bool)."""
    return isinstance(x, int) and not isinstance(x, bool)


def is_trial_complete(trial):
    """Check if a trial is complete per contract v0.2.2.
    
    Complete means timed_out == false AND steps_completed == n_steps_planned.
    Returns (is_complete, reason_if_incomplete).
    """
    timed_out = trial.get("timed_out")
    steps_completed = trial.get("steps_completed")
    n_steps_planned = trial.get("n_steps_planned")
    
    if not isinstance(timed_out, bool):
        return False, "timed_out is not a boolean"
    if not _is_int(steps_completed):
        return False, "steps_completed is not an integer"
    if not _is_int(n_steps_planned):
        return False, "n_steps_planned is not an integer"
    
    if timed_out:
        return False, f"timed_out=true"
    if steps_completed != n_steps_planned:
        return False, f"steps_completed={steps_completed} != n_steps_planned={n_steps_planned}"
    
    return True, None


def check_v022_required_fields(trial, issues_list, where=None):
    """Check that required v0.2.2 fields are present in a trial.
    
    For official v0.2.2 trials (including reruns), timeout_seconds and host are required.
    rerun_of must be present (null or a string trial_id).
    
    Adds issues to issues_list if fields are missing or invalid.
    Returns True if all checks pass, False otherwise.
    """
    all_ok = True
    
    # timeout_seconds: required, must be a positive number
    timeout_seconds = trial.get("timeout_seconds")
    if timeout_seconds is None:
        issues_list.append({
            "code": "trial.metadata",
            "where": where,
            "t": None,
            "detail": "timeout_seconds is required for official v0.2.2 trials"
        })
        all_ok = False
    elif not _is_num(timeout_seconds) or timeout_seconds <= 0:
        issues_list.append({
            "code": "trial.metadata",
            "where": where,
            "t": None,
            "detail": f"timeout_seconds must be a positive number, got {timeout_seconds!r}"
        })
        all_ok = False
    
    # host: required, must be a non-empty string
    host = trial.get("host")
    if host is None:
        issues_list.append({
            "code": "trial.metadata",
            "where": where,
            "t": None,
            "detail": "host is required for official v0.2.2 trials"
        })
        all_ok = False
    elif not isinstance(host, str) or not host.strip():
        issues_list.append({
            "code": "trial.metadata",
            "where": where,
            "t": None,
            "detail": f"host must be a non-empty string, got {host!r}"
        })
        all_ok = False
    
    # rerun_of: must be present (null or a string)
    if "rerun_of" not in trial:
        issues_list.append({
            "code": "trial.metadata",
            "where": where,
            "t": None,
            "detail": "rerun_of field is missing (must be null or a trial_id string)"
        })
        all_ok = False
    else:
        rerun_of = trial.get("rerun_of")
        if rerun_of is not None and (not isinstance(rerun_of, str) or not rerun_of.strip()):
            issues_list.append({
                "code": "trial.metadata",
                "where": where,
                "t": None,
                "detail": f"rerun_of must be null or a non-empty string, got {rerun_of!r}"
            })
            all_ok = False
    
    return all_ok


def load_series(trial, trial_dir):
    """Load series from a trial, handling both inline JSON and NPZ offload.
    
    Per eval/trial-schema.md: series may be inline as {"array": [...]} or offloaded
    as {"$npz": "<trial_id>.npz"}. NPZ uses object arrays of 1-d arrays for nested
    series, with the same array names as inline JSON.
    
    Args:
        trial: dict with 'series' field
        trial_dir: directory containing the trial file and any NPZ
    
    Returns:
        (series_dict, error_message) where series_dict has arrays as lists,
        or (None, error_message) on error
    """
    series_field = trial.get("series")
    if not isinstance(series_field, dict):
        return None, "series is not a dict"
    
    # Check if it's NPZ offload
    if "$npz" in series_field:
        if not HAS_NUMPY:
            return None, "series uses NPZ but numpy is not available"

        npz_name = series_field["$npz"]
        if not isinstance(npz_name, str):
            return None, f"$npz value is not a string: {npz_name!r}"

        # Restrict to bare filename in trials/ (no path traversal)
        if "/" in npz_name or "\\" in npz_name or npz_name.startswith("."):
            return None, f"$npz must be a bare filename, not a path: {npz_name!r}"

        npz_path = os.path.join(trial_dir, npz_name)
        if not os.path.isfile(npz_path):
            return None, f"NPZ file not found: {npz_name}"

        try:
            return read_npz_series(npz_path), None
        except Exception as exc:
            return None, f"Failed to load NPZ {npz_name}: {exc}"
    else:
        # Inline series
        return series_field, None


# Pickled classes an exporter NPZ may reference. The schema's nested series are object
# arrays of 1-d numeric arrays, which numpy can only store by pickling. Unpickling an
# arbitrary file can run arbitrary code, so object arrays are read with an unpickler
# that refuses every class except the ones needed to rebuild plain numeric ndarrays.
_NPZ_PICKLE_ALLOWED = {
    ("numpy._core.multiarray", "_reconstruct"),
    ("numpy.core.multiarray", "_reconstruct"),
    ("numpy._core.multiarray", "scalar"),
    ("numpy.core.multiarray", "scalar"),
    ("numpy", "ndarray"),
    ("numpy", "dtype"),
}


class _NumpyOnlyUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) not in _NPZ_PICKLE_ALLOWED:
            raise pickle.UnpicklingError(f"NPZ pickle references {module}.{name}, which is not allowed")
        return super().find_class(module, name)


def _read_npy_member(fp):
    """Read one .npy member. Object arrays go through _NumpyOnlyUnpickler."""
    version = npformat.read_magic(fp)
    if version == (1, 0):
        shape, fortran, dtype = npformat.read_array_header_1_0(fp)
    elif version in ((2, 0), (3, 0)):
        shape, fortran, dtype = npformat.read_array_header_2_0(fp)
    else:
        raise ValueError(f"unsupported .npy version {version}")
    if dtype.hasobject:
        arr = _NumpyOnlyUnpickler(fp).load()
        if not isinstance(arr, np.ndarray) or arr.shape != tuple(shape):
            raise ValueError("object array does not match its header")
        return arr
    count = int(np.prod(shape)) if shape else 1
    data = fp.read(count * dtype.itemsize)
    if len(data) != count * dtype.itemsize:
        raise ValueError("truncated array data")
    arr = np.frombuffer(data, dtype=dtype, count=count)
    return arr.reshape(shape, order="F" if fortran else "C")


def _to_python(value):
    """Plain Python numbers and lists, so _is_int and JSON-style equality behave as for inline series."""
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject:
            return [_to_python(x) for x in value]
        if value.dtype.kind not in "iuf":
            raise ValueError(f"unsupported array dtype {value.dtype}")
        return value.tolist()
    if value is None or (isinstance(value, (int, float)) and not isinstance(value, bool)):
        return value
    if isinstance(value, np.generic) and value.dtype.kind in "iuf":
        return value.item()
    raise ValueError(f"unsupported value of type {type(value).__name__} in NPZ")


def read_npz_series(npz_path):
    """Read every array in an exporter NPZ as Python lists, without unrestricted unpickling."""
    series = {}
    with zipfile.ZipFile(npz_path) as zf:
        for member in zf.namelist():
            if not member.endswith(".npy"):
                raise ValueError(f"unexpected NPZ member {member!r}")
            with zf.open(member) as fp:
                series[member[:-4]] = _to_python(_read_npy_member(fp))
    return series


# Contract aliases: allow prefix match when one side uses the alias
SERIES_ALIASES = {
    "eligible_agents": "eligible_count",
    "n_active_agents": "n_alive",
    "aggression_max_share": "top_target_share",
}


def _resolve_alias(name, series_dict):
    """Resolve a series name, checking both canonical and alias."""
    if name in series_dict:
        return name
    # Check if an alias exists in the series
    for alias, canonical in SERIES_ALIASES.items():
        if canonical == name and alias in series_dict:
            return alias
        if alias == name and canonical in series_dict:
            return canonical
    return None


def check_determinism_prefix(incomplete_trial, complete_trial, arrays_to_check, trial_dir):
    """Check that incomplete trial's arrays match the prefix of complete trial's arrays.
    
    Per contract v0.2.2: the incomplete run's per-step arrays must equal the first 
    steps_completed steps of the completed rerun. Uses exact equality.
    
    Supports contract aliases: eligible_agents ↔ eligible_count,
    n_active_agents ↔ n_alive, aggression_max_share ↔ top_target_share.
    A prefix matches if one side uses the alias and the other the canonical name.
    
    Args:
        incomplete_trial: dict with 'series' and 'steps_completed'
        complete_trial: dict with 'series' and 'steps_completed'
        arrays_to_check: list of required array names (from schema)
        trial_dir: directory containing trial files and NPZ files
    
    Returns:
        (matches, mismatches) where:
        - matches is True if all arrays match exactly
        - mismatches is a dict of {array_name: details} for arrays that don't match
    """
    incomplete_steps = incomplete_trial.get("steps_completed")
    complete_steps = complete_trial.get("steps_completed")
    
    if not _is_int(incomplete_steps) or not _is_int(complete_steps):
        return False, {"error": "steps_completed not an integer"}
    
    if incomplete_steps > complete_steps:
        return False, {"error": f"incomplete has more steps ({incomplete_steps}) than complete ({complete_steps})"}
    
    # Load series (handles both inline and NPZ)
    incomplete_series, inc_err = load_series(incomplete_trial, trial_dir)
    if inc_err:
        return False, {"error": f"incomplete trial: {inc_err}"}
    
    complete_series, comp_err = load_series(complete_trial, trial_dir)
    if comp_err:
        return False, {"error": f"complete trial: {comp_err}"}
    
    mismatches = {}
    
    # Check all required arrays plus any optional ones both sides have
    all_arrays = set(arrays_to_check)
    for key in incomplete_series:
        if key in complete_series:
            all_arrays.add(key)
    
    for array_name in all_arrays:
        # Resolve aliases
        inc_key = _resolve_alias(array_name, incomplete_series)
        comp_key = _resolve_alias(array_name, complete_series)
        
        inc_array = incomplete_series.get(inc_key) if inc_key else None
        comp_array = complete_series.get(comp_key) if comp_key else None
        
        if inc_array is None:
            if array_name in arrays_to_check:
                mismatches[array_name] = "missing in incomplete trial"
            continue
        if comp_array is None:
            if array_name in arrays_to_check:
                mismatches[array_name] = "missing in complete trial"
            continue
        
        if not isinstance(inc_array, list) or not isinstance(comp_array, list):
            mismatches[array_name] = "not a list"
            continue
        
        if len(inc_array) != incomplete_steps:
            mismatches[array_name] = f"incomplete array length {len(inc_array)} != steps_completed {incomplete_steps}"
            continue
        
        if len(comp_array) != complete_steps:
            mismatches[array_name] = f"complete array length {len(comp_array)} != steps_completed {complete_steps}"
            continue
        
        # Compare the prefix - use exact equality per contract "must equal"
        prefix = comp_array[:incomplete_steps]
        
        # For nested arrays (lists of lists), need element-by-element comparison
        if incomplete_steps > 0 and isinstance(inc_array[0], list):
            if not _nested_arrays_equal_exact(inc_array, prefix):
                mismatches[array_name] = f"nested array mismatch in first {incomplete_steps} steps"
        else:
            # For simple arrays, use exact equality
            if not _arrays_equal_exact(inc_array, prefix):
                mismatches[array_name] = f"mismatch in first {incomplete_steps} steps"
    
    return len(mismatches) == 0, mismatches


def _arrays_equal_exact(arr1, arr2):
    """Compare two arrays element-by-element with exact equality."""
    if len(arr1) != len(arr2):
        return False
    
    for a, b in zip(arr1, arr2, strict=True):
        if isinstance(a, list) and isinstance(b, list):
            if not _arrays_equal_exact(a, b):
                return False
        else:
            if a != b:
                return False
    
    return True


def _nested_arrays_equal_exact(arr1, arr2):
    """Compare two nested arrays (list of lists) element-by-element with exact equality."""
    if len(arr1) != len(arr2):
        return False
    
    for sub1, sub2 in zip(arr1, arr2, strict=True):
        if not isinstance(sub1, list) or not isinstance(sub2, list):
            if sub1 != sub2:
                return False
        elif not _arrays_equal_exact(sub1, sub2):
            return False
    
    return True


def check_id_integrity(series, trial_id, n_agents):
    """Check per-step ID integrity: full Table 2 ID checks per contract v0.2.2.
    
    Returns (valid, issues_list) where issues use trial.metadata code.
    Checks all Table 2 ID issues: ids.alive_count, ids.alive_duplicate, ids.alive_outside_population,
    ids.eligible_count, ids.eligible_duplicate, ids.eligible_not_alive, ids.target_not_alive,
    ids.self_target, align.targets.
    Supports contract aliases: n_active_agents ↔ n_alive, eligible_agents ↔ eligible_count.
    """
    issues = []
    
    if not isinstance(series, dict):
        return False, [{"code": "trial.metadata", "where": trial_id, "detail": "series is not a dict"}]
    
    # Resolve aliases using _resolve_alias
    alive_ids_key = _resolve_alias("alive_ids", series)
    eligible_ids_key = _resolve_alias("eligible_ids", series)
    top_targets_key = _resolve_alias("top_targets", series)
    n_alive_key = _resolve_alias("n_alive", series)  # also accepts n_active_agents
    eligible_count_key = _resolve_alias("eligible_count", series)  # also accepts eligible_agents
    
    alive_ids = series.get(alive_ids_key, []) if alive_ids_key else []
    eligible_ids = series.get(eligible_ids_key, []) if eligible_ids_key else []
    top_targets = series.get(top_targets_key, []) if top_targets_key else []
    n_alive = series.get(n_alive_key, []) if n_alive_key else []
    eligible_count = series.get(eligible_count_key, []) if eligible_count_key else []
    
    # Non-list check: do not silently skip
    if not isinstance(alive_ids, list):
        issues.append({
            "code": "trial.metadata",
            "where": trial_id,
            "detail": "alive_ids is not a list"
        })
        return False, issues
    
    if not isinstance(eligible_ids, list):
        issues.append({
            "code": "trial.metadata",
            "where": trial_id,
            "detail": "eligible_ids is not a list"
        })
        return False, issues
    
    if not isinstance(top_targets, list):
        issues.append({
            "code": "trial.metadata",
            "where": trial_id,
            "detail": "top_targets is not a list"
        })
        return False, issues
    
    if not isinstance(n_alive, list):
        issues.append({
            "code": "trial.metadata",
            "where": trial_id,
            "detail": "n_alive is not a list"
        })
        return False, issues
    
    if not isinstance(eligible_count, list):
        issues.append({
            "code": "trial.metadata",
            "where": trial_id,
            "detail": "eligible_count is not a list"
        })
        return False, issues
    
    steps = min(len(alive_ids), len(eligible_ids), len(top_targets), len(n_alive), len(eligible_count))
    population = set(range(n_agents))
    
    for t in range(steps):
        if t >= len(alive_ids) or t >= len(eligible_ids) or t >= len(top_targets):
            continue
            
        alive = alive_ids[t]
        eligible = eligible_ids[t]
        tt = top_targets[t]
        
        if not isinstance(alive, list):
            issues.append({
                "code": "trial.metadata",
                "where": trial_id,
                "detail": f"alive_ids[{t}] is not a list"
            })
            break
        
        if not isinstance(eligible, list):
            issues.append({
                "code": "trial.metadata",
                "where": trial_id,
                "detail": f"eligible_ids[{t}] is not a list"
            })
            break
        
        if not isinstance(tt, list):
            issues.append({
                "code": "trial.metadata",
                "where": trial_id,
                "detail": f"top_targets[{t}] is not a list"
            })
            break
        
        # Check for non-integer IDs (Table 2: series.shape)
        if not all(_is_int(x) for x in alive):
            issues.append({
                "code": "trial.metadata",
                "where": trial_id,
                "detail": f"series.shape: alive_ids has non-integer at step {t}"
            })
            break
        
        if not all(_is_int(x) for x in eligible):
            issues.append({
                "code": "trial.metadata",
                "where": trial_id,
                "detail": f"series.shape: eligible_ids has non-integer at step {t}"
            })
            break
        
        if not all(_is_int(x) for x in tt):
            issues.append({
                "code": "trial.metadata",
                "where": trial_id,
                "detail": f"series.shape: top_targets has non-integer at step {t}"
            })
            break
        
        alive_set = set(alive)
        
        # ids.alive_count
        if len(alive) != n_alive[t]:
            issues.append({
                "code": "trial.metadata",
                "where": trial_id,
                "detail": f"ids.alive_count: len(alive_ids) != n_alive at step {t}"
            })
            break
        
        # ids.alive_duplicate
        if len(alive_set) != len(alive):
            issues.append({
                "code": "trial.metadata",
                "where": trial_id,
                "detail": f"ids.alive_duplicate: duplicate alive_ids at step {t}"
            })
            break
        
        # ids.alive_outside_population
        if not alive_set <= population:
            issues.append({
                "code": "trial.metadata",
                "where": trial_id,
                "detail": f"ids.alive_outside_population: alive_ids outside 0..{n_agents-1} at step {t}"
            })
            break
        
        # ids.eligible_count
        if len(eligible) != eligible_count[t]:
            issues.append({
                "code": "trial.metadata",
                "where": trial_id,
                "detail": f"ids.eligible_count: len(eligible_ids) != eligible_count at step {t}"
            })
            break
        
        # ids.eligible_duplicate
        if len(set(eligible)) != len(eligible):
            issues.append({
                "code": "trial.metadata",
                "where": trial_id,
                "detail": f"ids.eligible_duplicate: duplicate eligible_ids at step {t}"
            })
            break
        
        # ids.eligible_not_alive
        if not set(eligible) <= alive_set:
            issues.append({
                "code": "trial.metadata",
                "where": trial_id,
                "detail": f"ids.eligible_not_alive: eligible_ids not all in alive_ids at step {t}"
            })
            break
        
        # ids.target_not_alive
        if not set(tt) <= alive_set:
            issues.append({
                "code": "trial.metadata",
                "where": trial_id,
                "detail": f"ids.target_not_alive: top_targets not all in alive_ids at step {t}"
            })
            break
        
        # align.targets: eligible_ids and top_targets must have same length
        if len(eligible) != len(tt):
            issues.append({
                "code": "trial.metadata",
                "where": trial_id,
                "detail": f"align.targets: eligible_ids/top_targets length mismatch at step {t}"
            })
            break
        
        # ids.self_target: only check when aligned
        for a, b in zip(eligible, tt, strict=True):
            if a == b:
                issues.append({
                    "code": "trial.metadata",
                    "where": trial_id,
                    "detail": f"ids.self_target: eligible agent targets itself at step {t}"
                })
                break
        if issues:
            break
    
    return len(issues) == 0, issues


def _event_list_error(events, name, limit=None):
    """Return an error string if events is not a list of {step: int, ...} objects, else None."""
    if not isinstance(events, list):
        return f"{name} is not a list"
    for k, e in enumerate(events):
        if not isinstance(e, dict) or not _is_int(e.get("step")):
            return f"{name}[{k}] is not an object with an integer step"
        if limit is not None and not 0 <= e["step"] < limit:
            return f"{name}[{k}] has step {e['step']} outside 0..{limit - 1}"
    return None


def check_events_prefix(incomplete_trial, complete_trial, incomplete_steps):
    """Check that events in the incomplete prefix match between incomplete and complete trials.

    Events whose step < steps_completed must match exactly. Checks expulsion_events,
    catharsis_events, and viability.expulsion_steps. An incomplete trial cannot have an
    event at or after its own steps_completed, so such an event is a mismatch, as is any
    malformed event list.

    Returns:
        (matches, mismatches) where mismatches lists the event types that don't match
    """
    mismatches = []
    if not _is_int(incomplete_steps):
        return False, ["steps_completed"]

    for name in ("expulsion_events", "catharsis_events"):
        inc = incomplete_trial.get(name, [])
        comp = complete_trial.get(name, [])
        if (_event_list_error(inc, name, limit=incomplete_steps) is not None
                or _event_list_error(comp, name) is not None):
            mismatches.append(name)
            continue
        if inc != [e for e in comp if e["step"] < incomplete_steps]:
            mismatches.append(name)

    inc_viab = incomplete_trial.get("viability")
    comp_viab = complete_trial.get("viability")
    if isinstance(inc_viab, dict) and isinstance(comp_viab, dict):
        inc_steps = inc_viab.get("expulsion_steps", [])
        comp_steps = comp_viab.get("expulsion_steps", [])
        if (not isinstance(inc_steps, list) or not isinstance(comp_steps, list)
                or not all(_is_int(x) for x in inc_steps + comp_steps)
                or any(x >= incomplete_steps for x in inc_steps)
                or inc_steps != [x for x in comp_steps if x < incomplete_steps]):
            mismatches.append("viability.expulsion_steps")

    return len(mismatches) == 0, mismatches


# ---------------------------------------------------------------------------
# D7 from evidence. Copies of official small_n_utils.adaptive_unanimity_threshold and
# classify_exhaustion at the pinned SHA; test_against_official.py checks them against
# the pinned source. The judge recomputes the viability fields from the trial's own
# series and events instead of trusting the exporter's summary.
# ---------------------------------------------------------------------------

def adaptive_unanimity_threshold(n_eligible):
    if n_eligible <= 1:
        return 1.0
    return min(0.95, (n_eligible - 1) / n_eligible)


def classify_exhaustion_status(modal_series, expulsion_steps, n_steps, n_alive, min_silence=500):
    """Official classify_exhaustion, returning only the status string."""
    if not expulsion_steps:
        return "no_expulsions"
    last_exp = expulsion_steps[-1]
    remaining = n_steps - last_exp - 1
    final_thresh = adaptive_unanimity_threshold(n_alive)
    for t in range(last_exp + 1, n_steps):
        if modal_series[t] >= final_thresh:
            return "still_cycling"
    if remaining >= min_silence:
        return "genuine_exhaustion"
    return "censored"


def check_viability_evidence(trial, series, min_silence):
    """Recompute the D7 inputs from a trial's series and expulsion events.

    Checks, against the evidence in the same trial:
      - expulsion_events: integer steps, strictly increasing, inside the run; distinct
        victims inside the population;
      - the official Use 2 trigger: every expulsion happens exactly when official
        run_unanimity_triggered would expel (modal agreement at or above the adaptive
        threshold for the living count, cooldown passed, more than 2 alive), and of the
        modal target when modal_target_id is recorded; no step where the trigger held
        goes without an expulsion;
      - alive_ids and n_alive drop by exactly the expelled victims, one step after each
        expulsion (series are recorded at the start of a step, before the trigger);
      - viability.expulsion_steps, n_expulsions, n_alive, pct_consumed;
      - viability.status: official classify_exhaustion for a complete trial.

    Returns (problems, generative). problems is a list of strings, empty when the
    viability object agrees with the evidence. generative is D7 recomputed from the
    evidence (False for an incomplete trial), or None when it cannot be recomputed.
    """
    N = trial.get("N")
    steps = trial.get("steps_completed")
    viab = trial.get("viability")
    if not _is_int(N) or not _is_int(steps) or not isinstance(viab, dict) or not isinstance(series, dict):
        return ["N, steps_completed, viability or series is missing or malformed"], None

    events = trial.get("expulsion_events")
    err = _event_list_error(events, "expulsion_events", limit=steps)
    if err:
        return [err], None
    exp_steps = [e["step"] for e in events]
    victims = [e.get("victim_id") for e in events]
    if any(b <= a for a, b in itertools.pairwise(exp_steps)):
        return ["expulsion_events steps are not strictly increasing"], None
    if not all(_is_int(v) and 0 <= v < N for v in victims) or len(set(victims)) != len(victims):
        return ["expulsion_events victim_id values are not distinct ids inside the population"], None

    modal = series.get("modal_agreement")
    n_alive_key = _resolve_alias("n_alive", series)
    n_alive = series.get(n_alive_key) if n_alive_key else None
    alive_ids = series.get("alive_ids")
    for name, arr in (("modal_agreement", modal), ("n_alive", n_alive), ("alive_ids", alive_ids)):
        if not isinstance(arr, list) or len(arr) != steps:
            return [f"series {name} is missing or does not have steps_completed entries"], None
    if not all(_is_num(x) and math.isfinite(x) for x in modal):
        return ["series modal_agreement has a non-numeric or non-finite entry"], None

    problems = []

    # Living set: everyone, minus each victim from the step after its expulsion.
    alive = set(range(N))
    by_step = dict(zip(exp_steps, victims))
    for t in range(steps):
        row = alive_ids[t]
        if not isinstance(row, list) or set(row) != alive or len(row) != len(alive) or n_alive[t] != len(alive):
            problems.append(f"alive_ids/n_alive at step {t} do not equal the population minus earlier victims")
            break
        if t in by_step:
            alive.discard(by_step[t])

    # Official Use 2 trigger, replayed on the recorded series.
    cooldown = trial.get("unanimity_cooldown")
    targets = series.get("modal_target_id")
    if not _is_int(cooldown):
        problems.append("unanimity_cooldown is missing or not an integer")
    elif not problems:
        if targets is not None and (not isinstance(targets, list) or len(targets) != steps):
            problems.append("series modal_target_id does not have steps_completed entries")
            targets = None
        since = cooldown + 1
        for t in range(steps):
            fires = (modal[t] >= adaptive_unanimity_threshold(n_alive[t]) and since > cooldown
                     and n_alive[t] > 2 and (targets is None or targets[t] is not None))
            if fires != (t in by_step):
                problems.append(f"expulsion schedule differs from the official trigger at step {t}")
                break
            if fires and targets is not None and targets[t] != by_step[t]:
                problems.append(f"victim at step {t} is not the modal target")
                break
            since = 0 if fires else since + 1

    n_exp = len(exp_steps)
    n_alive_final = N - n_exp
    pct = (N - n_alive_final) / N
    if viab.get("expulsion_steps") != exp_steps:
        problems.append("viability.expulsion_steps differs from expulsion_events")
    if viab.get("n_expulsions") != n_exp:
        problems.append(f"viability.n_expulsions={viab.get('n_expulsions')!r}, events give {n_exp}")
    if viab.get("n_alive") != n_alive_final:
        problems.append(f"viability.n_alive={viab.get('n_alive')!r}, events give {n_alive_final}")
    if viab.get("pct_consumed") != pct:
        problems.append(f"viability.pct_consumed={viab.get('pct_consumed')!r}, events give {pct!r}")

    complete, _ = is_trial_complete(trial)
    if not complete:
        return problems, False
    status = classify_exhaustion_status(modal, exp_steps, steps, n_alive_final, min_silence)
    if viab.get("status") != status:
        problems.append(f"viability.status={viab.get('status')!r}, official classify_exhaustion gives {status!r}")
    generative = status == "genuine_exhaustion" and pct < 0.50 and n_exp >= 1
    return problems, generative
