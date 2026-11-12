#!/usr/bin/env python3
"""Check that archived trial files are byte-identical to the ones a judge run scored.

The judge records the SHA-256 of every trial file it reads (trial_file_sha256). Once
traces are archived in the repo, this script confirms they are the same files, so the
recorded verdict can be re-run from the repo alone.

Usage:
    python3 check_trace_hashes.py TRACE_DIR [RESULT_JSON]

Exit status is 0 when every recorded file is present and matches, 1 otherwise.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    trace_dir = argv[0]
    result_path = argv[1] if len(argv) > 1 else os.path.join(HERE, "table2-result.json")
    with open(result_path, encoding="utf-8") as fh:
        expected = json.load(fh)["trial_file_sha256"]
    tdir = os.path.join(trace_dir, "trials")
    on_disk = sorted(f for f in os.listdir(tdir) if f.endswith(".json")) if os.path.isdir(tdir) else []
    problems = []
    for name, digest in sorted(expected.items()):
        path = os.path.join(tdir, name)
        if not os.path.exists(path):
            problems.append(f"missing {name}")
        elif _sha256(path) != digest:
            problems.append(f"hash differs {name}")
    problems += [f"not in recorded run {name}" for name in on_disk if name not in expected]
    for p in problems:
        print(p)
    print(f"{len(expected) - sum(p.startswith(('missing', 'hash')) for p in problems)}/{len(expected)} recorded "
          f"trial files present and identical; {len(problems)} problems")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
