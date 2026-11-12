"""Common judge utilities for contract v0.2.2 and later.

Shared functions for handling incomplete trials, reruns, and determinism checks.
"""
import math


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


def check_determinism_prefix(incomplete_trial, complete_trial, arrays_to_check):
    """Check that incomplete trial's arrays match the prefix of complete trial's arrays.
    
    Per contract v0.2.2: the incomplete run's per-step arrays must equal the first 
    steps_completed steps of the completed rerun.
    
    Args:
        incomplete_trial: dict with 'series' and 'steps_completed'
        complete_trial: dict with 'series' and 'steps_completed'
        arrays_to_check: list of array names to check (e.g., ['modal_agreement', 'system_tension'])
    
    Returns:
        (matches, mismatches) where:
        - matches is True if all arrays match
        - mismatches is a dict of {array_name: details} for arrays that don't match
    """
    incomplete_steps = incomplete_trial.get("steps_completed")
    complete_steps = complete_trial.get("steps_completed")
    
    if not _is_int(incomplete_steps) or not _is_int(complete_steps):
        return False, {"error": "steps_completed not an integer"}
    
    if incomplete_steps > complete_steps:
        return False, {"error": f"incomplete has more steps ({incomplete_steps}) than complete ({complete_steps})"}
    
    incomplete_series = incomplete_trial.get("series", {})
    complete_series = complete_trial.get("series", {})
    
    if not isinstance(incomplete_series, dict) or not isinstance(complete_series, dict):
        return False, {"error": "series is not a dict"}
    
    mismatches = {}
    
    for array_name in arrays_to_check:
        inc_array = incomplete_series.get(array_name)
        comp_array = complete_series.get(array_name)
        
        if inc_array is None:
            mismatches[array_name] = "missing in incomplete trial"
            continue
        if comp_array is None:
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
        
        # Compare the prefix
        prefix = comp_array[:incomplete_steps]
        
        # For nested arrays (lists of lists), need element-by-element comparison
        if incomplete_steps > 0 and isinstance(inc_array[0], list):
            if not _nested_arrays_equal(inc_array, prefix):
                mismatches[array_name] = f"nested array mismatch in first {incomplete_steps} steps"
        else:
            # For simple arrays, check with tolerance for floats
            if not _arrays_equal(inc_array, prefix):
                mismatches[array_name] = f"mismatch in first {incomplete_steps} steps"
    
    return len(mismatches) == 0, mismatches


def _arrays_equal(arr1, arr2, tol=1e-12):
    """Compare two arrays element-by-element with tolerance for floats."""
    if len(arr1) != len(arr2):
        return False
    
    for a, b in zip(arr1, arr2, strict=True):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if not math.isfinite(a) or not math.isfinite(b):
                if a != b:  # NaN != NaN, inf == inf
                    return False
            elif abs(a - b) > tol:
                return False
        elif isinstance(a, list) and isinstance(b, list):
            if not _arrays_equal(a, b, tol):
                return False
        else:
            if a != b:
                return False
    
    return True


def _nested_arrays_equal(arr1, arr2, tol=1e-12):
    """Compare two nested arrays (list of lists) element-by-element."""
    if len(arr1) != len(arr2):
        return False
    
    for sub1, sub2 in zip(arr1, arr2, strict=True):
        if not isinstance(sub1, list) or not isinstance(sub2, list):
            if sub1 != sub2:
                return False
        elif not _arrays_equal(sub1, sub2, tol):
            return False
    
    return True
