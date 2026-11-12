"""
Tests for opinion dynamics enumeration.

These tests verify:
1. The three named O6 configurations are split fixed points
2. O5 period-at-most-2 holds on enumerated binary ensemble
3. Voter schedule dependency (bipartite vs non-bipartite)
"""

import unittest
import networkx as nx
from .majority import (
    majority_binary_step,
    majority_vertex_step,
    enumerate_binary_majority,
    classify_trajectory
)
from .voter import analyze_absorbing_states, test_schedule_dependency
from .graphs import generate_all_connected_graphs, count_connected_graphs


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
    
    def test_small_graphs_period_at_most_2(self):
        """Enumerate small graphs and verify period at most 2."""
        max_n = 6
        
        for n in range(1, max_n + 1):
            graph_count = 0
            
            for G in generate_all_connected_graphs(n):
                graph_count += 1
                
                if graph_count > 50 and n >= 5:
                    break
                
                result = enumerate_binary_majority(G)
                
                self.assertEqual(
                    result['period_gt_2'], 0,
                    f"Found period > 2 on graph with {n} nodes. "
                    f"Counterexamples: {result['counterexamples']}"
                )
                
                total = (result['unanimous_fixed'] + result['split_fixed'] + 
                        result['period_2'] + result['period_gt_2'] + result['unknown'])
                self.assertEqual(
                    total, result['total_configs'],
                    f"Classification counts don't sum correctly for n={n}"
                )


class TestVoterScheduleDependency(unittest.TestCase):
    """Test O7: voter model unanimity depends on schedule."""
    
    def test_absorbing_states_structure(self):
        """Verify that connected graphs have only unanimous absorbing states."""
        for n in [3, 4, 5]:
            G = nx.cycle_graph(n)
            result = analyze_absorbing_states(G)
            
            self.assertTrue(result['connected'])
            self.assertEqual(result['absorbing_states'], 2)
            self.assertEqual(result['description'], 'All-0 and all-1 (unanimous states)')
    
    def test_bipartite_synchronous_non_absorption(self):
        """
        Verify that synchronous voter on a bipartite graph can fail to absorb.
        
        This test uses randomness, so we run multiple trials and expect
        that at least some fail to absorb within a reasonable time.
        """
        G = nx.cycle_graph(4)
        self.assertTrue(nx.is_bipartite(G), "4-cycle should be bipartite")
        
        results = test_schedule_dependency(G, num_trials=50)
        
        self.assertTrue(results['bipartite'])
        
        sync_rate = results['results']['synchronous']['absorption_rate']
        lazy_rate = results['results']['lazy']['absorption_rate']
        
        self.assertLess(
            sync_rate, 1.0,
            "Synchronous voter on bipartite graph should not always absorb quickly"
        )
        
        self.assertGreater(
            lazy_rate, 0.0,
            "Lazy voter should absorb with positive probability"
        )


class TestEnumerationCounts(unittest.TestCase):
    """Verify enumeration completeness with known counts."""
    
    def test_graph_counts(self):
        """Verify graph counts against known values."""
        known_counts = {
            1: 1,
            2: 1,
            3: 4,
            4: 38
        }
        
        for n, expected in known_counts.items():
            actual = count_connected_graphs(n)
            self.assertEqual(
                actual, expected,
                f"Connected graph count mismatch for n={n}"
            )
    
    def test_binary_assignment_counts(self):
        """Verify binary assignment counts are 2^n."""
        for n in range(1, 7):
            G = nx.complete_graph(n)
            result = enumerate_binary_majority(G)
            
            expected = 2 ** n
            self.assertEqual(
                result['total_configs'], expected,
                f"Binary assignment count should be 2^{n} = {expected}"
            )


if __name__ == '__main__':
    unittest.main()
