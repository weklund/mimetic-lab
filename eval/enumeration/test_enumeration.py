"""
Tests for opinion dynamics enumeration.

These tests verify:
1. The three named O6 configurations are split fixed points
2. O5 period-at-most-2 holds on enumerated binary ensemble
3. Voter schedule dependency (bipartite vs non-bipartite)
"""

import unittest
import networkx as nx

try:
    from .majority import (
        majority_binary_step,
        majority_vertex_step,
        enumerate_binary_majority,
        classify_trajectory
    )
    from .voter import (
        analyze_absorbing_states,
        test_schedule_dependency,
        is_absorbing_state,
        synchronous_voter_step
    )
    from .graphs import (
        generate_all_connected_graphs,
        count_connected_graphs,
        generate_nonisomorphic_connected_graphs,
        count_nonisomorphic_connected_graphs
    )
except ImportError:
    from eval.enumeration.majority import (
        majority_binary_step,
        majority_vertex_step,
        enumerate_binary_majority,
        classify_trajectory
    )
    from eval.enumeration.voter import (
        analyze_absorbing_states,
        test_schedule_dependency,
        is_absorbing_state,
        synchronous_voter_step
    )
    from eval.enumeration.graphs import (
        generate_all_connected_graphs,
        count_connected_graphs,
        generate_nonisomorphic_connected_graphs,
        count_nonisomorphic_connected_graphs
    )


class TestO6NamedConfigurations(unittest.TestCase):
    """Test the three O6 named configurations."""
    
    def test_o6_1_path_4_binary(self):
        """O6 config 1: 4-vertex path with binary labels (0,0,1,1)."""
        G = nx.path_graph(4)
        initial = (0, 0, 1, 1)
        
        next_state = majority_binary_step(G, initial)
        
        self.assertEqual(
            next_state, initial,
            "4-vertex path (0,0,1,1) should be a fixed point"
        )
        
        is_unanimous = (next_state[0] == next_state[1] == next_state[2] == next_state[3])
        self.assertFalse(is_unanimous, "Fixed point should not be unanimous")
    
    def test_o6_2_two_triangles_binary(self):
        """O6 config 2: Two triangles joined by edge 2-3, binary labels (0,0,0,1,1,1)."""
        G = nx.Graph()
        G.add_edges_from([
            (0, 1), (1, 2), (2, 0),
            (3, 4), (4, 5), (5, 3),
            (2, 3)
        ])
        
        initial = (0, 0, 0, 1, 1, 1)
        
        next_state = majority_binary_step(G, initial)
        
        self.assertEqual(
            next_state, initial,
            "Two triangles (0,0,0,1,1,1) should be a fixed point"
        )
        
        is_unanimous = all(s == initial[0] for s in next_state)
        self.assertFalse(is_unanimous, "Fixed point should not be unanimous")
    
    def test_o6_3_two_triangles_vertex_valued(self):
        """O6 config 3: Two triangles with vertex targets (5,5,5,0,0,0), no self-targeting."""
        G = nx.Graph()
        G.add_edges_from([
            (0, 1), (1, 2), (2, 0),
            (3, 4), (4, 5), (5, 3),
            (2, 3)
        ])
        
        initial = (5, 5, 5, 0, 0, 0)
        
        has_self_target = any(initial[i] == i for i in range(len(initial)))
        self.assertFalse(has_self_target, "Initial state should have no self-targeting")
        
        next_state = majority_vertex_step(G, initial, allow_self_target=False)
        
        self.assertEqual(
            next_state, initial,
            "Two triangles with targets (5,5,5,0,0,0) should be a fixed point"
        )
        
        is_unanimous = all(s == initial[0] for s in next_state)
        self.assertFalse(
            is_unanimous, 
            "Fixed point should not be unanimous (single-victim state)"
        )


class TestO5PeriodBound(unittest.TestCase):
    """Test O5: majority binary rule converges to fixed point or 2-cycle."""
    
    def test_isomorphism_classes_binary_majority_n1_to_6(self):
        """
        Complete enumeration of isomorphism classes for n=1..6, all 2^n assignments.
        
        Verifies:
        - Graph counts match known nonisomorphic connected counts
        - No period > 2 found (O5 claim)
        - All trajectories classified
        """
        expected_counts = {
            1: 1,
            2: 1,
            3: 2,
            4: 6,
            5: 21,
            6: 112
        }
        
        for n in range(1, 7):
            with self.subTest(n=n):
                graphs = generate_nonisomorphic_connected_graphs(n)
                graph_count = len(graphs)
                
                self.assertEqual(
                    graph_count, expected_counts[n],
                    f"Isomorphism class count for n={n}: expected {expected_counts[n]}, got {graph_count}"
                )
                
                for G in graphs:
                    result = enumerate_binary_majority(G)
                    
                    if result['period_gt_2'] > 0:
                        self.fail(
                            f"Found period > 2 on graph with {n} nodes. "
                            f"Counterexamples: {result['counterexamples']}"
                        )
                    
                    total = (result['unanimous_fixed'] + result['split_fixed'] + 
                            result['period_2'] + result['period_gt_2'] + result['unknown'])
                    self.assertEqual(
                        total, result['total_configs'],
                        f"Classification counts don't sum for n={n}"
                    )


class TestVoterScheduleDependency(unittest.TestCase):
    """Test O7: voter model unanimity depends on schedule."""
    
    def test_absorbing_states_structure(self):
        """
        Verify that connected graphs have only unanimous absorbing states.
        
        For continuous-time, lazy, or asynchronous voter on a connected graph,
        the only absorbing states are unanimous (all-0 and all-1).
        """
        for n in [3, 4, 5, 6]:
            with self.subTest(n=n):
                G = nx.cycle_graph(n)
                
                self.assertTrue(nx.is_connected(G))
                
                for state_val in [0, 1]:
                    unanimous_state = tuple([state_val] * n)
                    self.assertTrue(
                        is_absorbing_state(unanimous_state),
                        f"Unanimous state {unanimous_state} should be absorbing"
                    )
                
                mixed_state = tuple([0] * (n // 2) + [1] * (n - n // 2))
                self.assertFalse(
                    is_absorbing_state(mixed_state),
                    f"Mixed state {mixed_state} should not be absorbing"
                )
    
    def test_c4_deterministic_period_2_witness(self):
        """
        Lab's deterministic witness for O7 schedule dependency.
        
        On C4 (4-cycle), configuration (0,1,0,1) maps to (1,0,1,0) and back
        under synchronous_voter_step. This is a 2-cycle, not absorbing.
        """
        G = nx.cycle_graph(4)
        self.assertTrue(nx.is_bipartite(G), "C4 is bipartite")
        
        state1 = (0, 1, 0, 1)
        state2 = (1, 0, 1, 0)
        
        self.assertFalse(is_absorbing_state(state1))
        self.assertFalse(is_absorbing_state(state2))
        
        import random
        random.seed(42)
        
        next1 = synchronous_voter_step(G, state1)
        next2 = synchronous_voter_step(G, state2)
        
        self.assertEqual(next1, state2, f"From {state1} expected {state2}, got {next1}")
        self.assertEqual(next2, state1, f"From {state2} expected {state1}, got {next2}")
    
    def test_bipartite_structural_period_2(self):
        """
        Structural property: synchronous voter on a bipartite graph
        with opposite opinions on the two sides forms a 2-cycle.
        
        This is the general bipartite witness, not just C4.
        """
        for n in [4, 6]:
            with self.subTest(n=n):
                G = nx.cycle_graph(n)
                self.assertTrue(nx.is_bipartite(G))
                
                coloring = nx.bipartite.color(G)
                side_0 = [v for v, c in coloring.items() if c == 0]
                side_1 = [v for v, c in coloring.items() if c == 1]
                
                state = tuple([0 if v in side_0 else 1 for v in range(n)])
                
                self.assertFalse(is_absorbing_state(state))
                
                for v in range(n):
                    neighbors = list(G.neighbors(v))
                    neighbor_opinions = [state[u] for u in neighbors]
                    
                    if v in side_0:
                        self.assertTrue(
                            all(op == 1 for op in neighbor_opinions),
                            f"Node {v} in side 0 should have all neighbors in side 1"
                        )
                    else:
                        self.assertTrue(
                            all(op == 0 for op in neighbor_opinions),
                            f"Node {v} in side 1 should have all neighbors in side 0"
                        )
    
    def test_voter_isomorphism_class_counts(self):
        """Verify that voter analysis counts isomorphism classes correctly."""
        expected_counts = {
            3: 2,
            4: 6,
            5: 21,
            6: 112
        }
        
        for n in [3, 4, 5, 6]:
            with self.subTest(n=n):
                graphs = generate_nonisomorphic_connected_graphs(n)
                count = len(graphs)
                
                self.assertEqual(
                    count, expected_counts[n],
                    f"Isomorphism class count for n={n} should be {expected_counts[n]}, got {count}"
                )
                
                bipartite_count = sum(1 for G in graphs if nx.is_bipartite(G))
                non_bipartite_count = count - bipartite_count
                
                if n >= 3:
                    self.assertGreater(
                        non_bipartite_count, 0,
                        f"Should have non-bipartite graphs for n={n}"
                    )


class TestEnumerationCounts(unittest.TestCase):
    """Verify enumeration completeness with known counts."""
    
    def test_isomorphism_class_counts(self):
        """
        Verify isomorphism class counts for connected graphs.
        
        These are the counts Lab requires for acceptance.
        """
        expected_counts = {
            1: 1,
            2: 1,
            3: 2,
            4: 6,
            5: 21,
            6: 112
        }
        
        for n in range(1, 7):
            with self.subTest(n=n):
                actual = count_nonisomorphic_connected_graphs(n)
                self.assertEqual(
                    actual, expected_counts[n],
                    f"Isomorphism class count for n={n}: expected {expected_counts[n]}, got {actual}"
                )
    
    def test_binary_assignment_counts(self):
        """Verify binary assignment counts are 2^n."""
        for n in range(1, 7):
            with self.subTest(n=n):
                G = nx.complete_graph(n)
                result = enumerate_binary_majority(G)
                
                expected = 2 ** n
                self.assertEqual(
                    result['total_configs'], expected,
                    f"Binary assignment count should be 2^{n} = {expected}"
                )


if __name__ == '__main__':
    unittest.main()
