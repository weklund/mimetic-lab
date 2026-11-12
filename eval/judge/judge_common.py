"""Common judge utilities for contract v0.2.2 and later.

Shared functions for handling incomplete trials, reruns, and determinism checks.
"""
import math
import os

try:
    import numpy as np
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
            # Object arrays require allow_pickle, but path is restricted to trial_dir
            npz_data = np.load(npz_path, allow_pickle=True)
            series = {}
            for key in npz_data.files:
                arr = npz_data[key]
                # Convert numpy arrays to lists
                if arr.dtype == object:
                    # Object array of 1-d arrays (for nested series like alive_ids)
                    series[key] = [list(x) if hasattr(x, '__iter__') and not isinstance(x, str) else x 
                                   for x in arr]
                else:
                    # Regular numeric array
                    series[key] = arr.tolist()
            npz_data.close()
            return series, None
        except Exception as exc:
            return None, f"Failed to load NPZ {npz_name}: {exc}"
    else:
        # Inline series
        return series_field, None


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
    ids.self_target.
    """
    issues = []
    
    if not isinstance(series, dict):
        return False, [{"code": "trial.metadata", "where": trial_id, "detail": "series is not a dict"}]
    
    alive_ids = series.get("alive_ids", [])
    eligible_ids = series.get("eligible_ids", [])
    top_targets = series.get("top_targets", [])
    n_alive = series.get("n_alive", [])
    eligible_count = series.get("eligible_count", [])
    
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
        
        # ids.self_target
        if len(eligible) == len(tt):
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


def check_events_prefix(incomplete_trial, complete_trial, incomplete_steps):
    """Check that events in the incomplete prefix match between incomplete and complete trials.
    
    Events whose step < steps_completed must match exactly. Checks expulsion_events,
    catharsis_events, and viability.expulsion_steps.
    
    Returns:
        (matches, mismatches) where mismatches lists event types that don't match
    """
    mismatches = []
    
    # Check expulsion_events
    inc_expulsions = incomplete_trial.get("expulsion_events", [])
    comp_expulsions = complete_trial.get("expulsion_events", [])
    
    inc_prefix_expulsions = [e for e in inc_expulsions if e.get("step", -1) < incomplete_steps]
    comp_prefix_expulsions = [e for e in comp_expulsions if e.get("step", -1) < incomplete_steps]
    
    if inc_prefix_expulsions != comp_prefix_expulsions:
        mismatches.append("expulsion_events")
    
    # Check catharsis_events
    inc_catharsis = incomplete_trial.get("catharsis_events", [])
    comp_catharsis = complete_trial.get("catharsis_events", [])
    
    inc_prefix_catharsis = [e for e in inc_catharsis if e.get("step", -1) < incomplete_steps]
    comp_prefix_catharsis = [e for e in comp_catharsis if e.get("step", -1) < incomplete_steps]
    
    if inc_prefix_catharsis != comp_prefix_catharsis:
        mismatches.append("catharsis_events")
    
    # Check viability.expulsion_steps
    inc_viab = incomplete_trial.get("viability", {})
    comp_viab = complete_trial.get("viability", {})
    
    if isinstance(inc_viab, dict) and isinstance(comp_viab, dict):
        inc_exp_steps = inc_viab.get("expulsion_steps", [])
        comp_exp_steps = comp_viab.get("expulsion_steps", [])
        
        if isinstance(inc_exp_steps, list) and isinstance(comp_exp_steps, list):
            inc_prefix_steps = [s for s in inc_exp_steps if s < incomplete_steps]
            comp_prefix_steps = [s for s in comp_exp_steps if s < incomplete_steps]
            
            if inc_prefix_steps != comp_prefix_steps:
                mismatches.append("viability.expulsion_steps")
    
    return len(mismatches) == 0, mismatches
