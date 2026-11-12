"""
Exhaustive enumeration of small network opinion dynamics.

This module enumerates all connected simple undirected graphs on n = 1..N nodes
and classifies trajectories under different opinion dynamics rules:
- O5: Majority rule (binary labels)
- O6: Majority rule (vertex-valued labels)
- O7: Voter model (schedule-dependent)

Part of issue #14 item 2.
"""
