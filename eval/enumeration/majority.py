"""
Majority rule dynamics for O5 and O6.

Implements:
- Binary majority rule (O5): labels in {0, 1}
- Vertex-valued majority rule (O6): labels are vertex indices
"""

from typing import Tuple, List, Set, Optional
import networkx as nx


def majority_binary_step(G: nx.Graph, labels: Tuple[int, ...]) -> Tuple[int, ...]:
    """
    One synchronous step of binary majority rule (O5).
    
    Each agent adopts the bit held by a strict majority of its neighbors.
    On a tie, the agent keeps its own label.
    
    Args:
        G: Undirected graph
        labels: Tuple of binary labels (0 or 1) for each node
        
    Returns:
        New label tuple after one step
    """
    n = G.number_of_nodes()
    new_labels = []
    
    for v in range(n):
        neighbors = list(G.neighbors(v))
        
        if not neighbors:
            new_labels.append(labels[v])
            continue
        
        neighbor_labels = [labels[u] for u in neighbors]
        count_ones = sum(neighbor_labels)
        count_zeros = len(neighbor_labels) - count_ones
        
        if count_ones > count_zeros:
            new_labels.append(1)
        elif count_zeros > count_ones:
            new_labels.append(0)
        else:
            new_labels.append(labels[v])
    
    return tuple(new_labels)


def majority_vertex_step(
    G: nx.Graph, 
    targets: Tuple[int, ...],
    allow_self_target: bool = True
) -> Tuple[int, ...]:
    """
    One synchronous step of vertex-valued majority rule (O6).
    
    Each agent adopts the target held by a strict majority of its neighbors.
    On a tie, the agent keeps its own target.
    
    Args:
        G: Undirected graph
        targets: Tuple of target vertex indices for each node
        allow_self_target: Whether self-targeting is allowed
        
    Returns:
        New target tuple after one step
    """
    n = G.number_of_nodes()
    new_targets = []
    
    for v in range(n):
        neighbors = list(G.neighbors(v))
        
        if not neighbors:
            new_targets.append(targets[v])
            continue
        
        neighbor_targets = [targets[u] for u in neighbors]
        
        target_counts = {}
        for t in neighbor_targets:
            target_counts[t] = target_counts.get(t, 0) + 1
        
        max_count = max(target_counts.values())
        candidates = [t for t, c in target_counts.items() if c == max_count]
        
        if len(candidates) == 1 and max_count > len(neighbor_targets) / 2:
            new_target = candidates[0]
        else:
            new_target = targets[v]
        
        if not allow_self_target and new_target == v:
            new_targets.append(targets[v])
        else:
            new_targets.append(new_target)
    
    return tuple(new_targets)


def classify_trajectory(
    G: nx.Graph,
    initial: Tuple[int, ...],
    step_fn,
    max_steps: int = 1000
) -> dict:
    """
    Classify a trajectory from an initial state.
    
    Args:
        G: Graph
        initial: Initial state (labels or targets)
        step_fn: Function that takes (G, state) and returns next state
        max_steps: Maximum steps to simulate
        
    Returns:
        Dictionary with classification:
        - 'type': 'unanimous_fixed', 'split_fixed', 'cycle', 'unknown'
        - 'period': Period of cycle (1 for fixed point, >1 for cycle)
        - 'states': States in the attractor
        - 'unanimous': Whether the attractor is unanimous
        - 'steps_to_attractor': Steps until attractor detected
    """
    seen = {initial: 0}
    trajectory = [initial]
    state = initial
    
    for step in range(1, max_steps + 1):
        state = step_fn(G, state)
        
        if state in seen:
            cycle_start = seen[state]
            cycle_states = trajectory[cycle_start:]
            period = len(cycle_states)
            
            unanimous = all(s[0] == s[i] for s in cycle_states for i in range(len(s)))
            
            if period == 1:
                if unanimous:
                    return {
                        'type': 'unanimous_fixed',
                        'period': 1,
                        'states': cycle_states,
                        'unanimous': True,
                        'steps_to_attractor': cycle_start
                    }
                else:
                    return {
                        'type': 'split_fixed',
                        'period': 1,
                        'states': cycle_states,
                        'unanimous': False,
                        'steps_to_attractor': cycle_start
                    }
            else:
                return {
                    'type': 'cycle',
                    'period': period,
                    'states': cycle_states,
                    'unanimous': unanimous,
                    'steps_to_attractor': cycle_start
                }
        
        seen[state] = step
        trajectory.append(state)
    
    return {
        'type': 'unknown',
        'period': None,
        'states': [],
        'unanimous': False,
        'steps_to_attractor': None
    }


def enumerate_binary_majority(G: nx.Graph) -> dict:
    """
    Enumerate all binary initial states and classify trajectories under O5.
    
    Args:
        G: Connected graph
        
    Returns:
        Dictionary with statistics and any notable trajectories
    """
    n = G.number_of_nodes()
    total = 2 ** n
    
    unanimous_fixed = 0
    split_fixed = 0
    period_2 = 0
    period_gt_2 = 0
    unknown = 0
    
    counterexamples = []
    
    for i in range(total):
        initial = tuple((i >> j) & 1 for j in range(n))
        
        result = classify_trajectory(
            G, initial, 
            lambda g, s: majority_binary_step(g, s)
        )
        
        if result['type'] == 'unanimous_fixed':
            unanimous_fixed += 1
        elif result['type'] == 'split_fixed':
            split_fixed += 1
        elif result['type'] == 'cycle':
            if result['period'] == 2:
                period_2 += 1
            else:
                period_gt_2 += 1
                counterexamples.append({
                    'initial': initial,
                    'period': result['period'],
                    'states': result['states']
                })
        else:
            unknown += 1
    
    return {
        'n': n,
        'total_configs': total,
        'unanimous_fixed': unanimous_fixed,
        'split_fixed': split_fixed,
        'period_2': period_2,
        'period_gt_2': period_gt_2,
        'unknown': unknown,
        'counterexamples': counterexamples
    }


def enumerate_vertex_majority(
    G: nx.Graph,
    allow_self_target: bool = True
) -> dict:
    """
    Enumerate all vertex-target initial states and classify trajectories under O6.
    
    Args:
        G: Connected graph
        allow_self_target: Whether to allow self-targeting in initial states
        
    Returns:
        Dictionary with statistics including self-target-by-majority config counts
    """
    n = G.number_of_nodes()
    
    unanimous_fixed = 0
    split_fixed = 0
    period_2 = 0
    period_gt_2 = 0
    unknown = 0
    configs_with_self_target_by_majority = 0
    
    def generate_initial_states():
        """Generate all valid initial target assignments."""
        if allow_self_target:
            for i in range(n ** n):
                targets = tuple((i // (n ** j)) % n for j in range(n))
                yield targets
        else:
            def generate_no_self(pos=0, current=()):
                if pos == n:
                    yield current
                    return
                for t in range(n):
                    if t != pos:
                        yield from generate_no_self(pos + 1, current + (t,))
            
            yield from generate_no_self()
    
    def check_self_target_by_majority(g, targets):
        """Check if any agent has a strict majority of neighbors targeting that agent."""
        for v in range(n):
            neighbors = list(g.neighbors(v))
            if not neighbors:
                continue
            
            neighbor_targets = [targets[u] for u in neighbors]
            target_counts = {}
            for t in neighbor_targets:
                target_counts[t] = target_counts.get(t, 0) + 1
            
            max_count = max(target_counts.values())
            
            if max_count > len(neighbor_targets) / 2:
                candidates = [t for t, c in target_counts.items() if c == max_count]
                if len(candidates) == 1 and candidates[0] == v:
                    return True
        
        return False
    
    total = 0
    for initial in generate_initial_states():
        total += 1
        
        if check_self_target_by_majority(G, initial):
            configs_with_self_target_by_majority += 1
        
        result = classify_trajectory(
            G, initial,
            lambda g, s: majority_vertex_step(g, s, allow_self_target)
        )
        
        if result['type'] == 'unanimous_fixed':
            unanimous_fixed += 1
        elif result['type'] == 'split_fixed':
            split_fixed += 1
        elif result['type'] == 'cycle':
            if result['period'] == 2:
                period_2 += 1
            else:
                period_gt_2 += 1
        else:
            unknown += 1
    
    return {
        'n': n,
        'total_configs': total,
        'unanimous_fixed': unanimous_fixed,
        'split_fixed': split_fixed,
        'period_2': period_2,
        'period_gt_2': period_gt_2,
        'unknown': unknown,
        'configs_with_self_target_by_majority': configs_with_self_target_by_majority
    }
