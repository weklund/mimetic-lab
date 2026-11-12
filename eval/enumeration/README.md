# Opinion Dynamics Enumeration

Exhaustive enumeration of small network opinion dynamics for O5, O6, O7.

Part of issue #14 item 2.

## Modules

- `graphs.py`: Generate all connected simple undirected graphs on n nodes
- `majority.py`: Binary and vertex-valued majority rule dynamics
- `voter.py`: Voter model under different schedules
- `generate_report.py`: Generate the enumeration report
- `test_enumeration.py`: Tests verifying O5, O6, O7 properties

## Running Tests

```bash
python3 -m pip install networkx
python3 -m unittest discover -s eval/enumeration -p 'test_*.py' -v
```

## Generating the Report

```bash
python3 -m eval.enumeration.generate_report > eval/enumeration/REPORT.md
```

## What the Tests Verify

1. **O6 named configurations**: The three split fixed points are verified
2. **O5 period bound**: All trajectories reach fixed point or 2-cycle (fails if period > 2 found)
3. **O7 schedule dependency**: Voter model unanimity depends on schedule
4. **Enumeration completeness**: Graph counts match known values

## Epistemic Status

These results are about the stated models (O5, O6, O7), not about Girard's theory. Each stands_in_for G4 with its own formalization_delta. A pass here upgrades only the relevant O claim, never G4 or Girard.

See REPORT.md for full findings.
