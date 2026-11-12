"""
Voter model dynamics for O7.

Implements voter model under different schedules:
- Synchronous (deterministic analysis of absorbing states)
- Lazy synchronous (for bipartite graphs)
- Asynchronous (single random update per step)
"""

from typing import Tuple, Set
import random
import networkx as nx


def is_absorbing_state(state: Tuple[int, ...]) -> bool:
    """Check if a state is unanimous (absorbing for connected graphs)."""
    return all(s == state[0] for s in state)


def synchronous_voter_step(G: nx.Graph, opinions: Tuple[int, ...]) -> Tuple[int, ...]:
    """
    One synchronous voter step: each agent copies a random neighbor's opinion.
    
    For deterministic analysis, this simulates one possible outcome.
    
    Args:
        G: Graph
        opinions: Current opinion tuple
        
    Returns:
        New opinion tuple
    """
    n = G.number_of_nodes()
    new_opinions = []
    
    for v in range(n):
        neighbors = list(G.neighbors(v))
        if neighbors:
            chosen = random.choice(neighbors)
            new_opinions.append(opinions[chosen])
        else:
            new_opinions.append(opinions[v])
    
    return tuple(new_opinions)


def lazy_synchronous_voter_step(G: nx.Graph, opinions: Tuple[int, ...]) -> Tuple[int, ...]:
    """
    One lazy synchronous voter step: with probability 1/2, keep own opinion.
    
    Args:
        G: Graph
        opinions: Current opinion tuple
        
    Returns:
        New opinion tuple
    """
    n = G.number_of_nodes()
    new_opinions = []
    
    for v in range(n):
        if random.random() < 0.5:
            new_opinions.append(opinions[v])
        else:
            neighbors = list(G.neighbors(v))
            if neighbors:
                chosen = random.choice(neighbors)
                new_opinions.append(opinions[chosen])
            else:
                new_opinions.append(opinions[v])
    
    return tuple(new_opinions)


def analyze_absorbing_states(G: nx.Graph) -> dict:
    """
    Analyze absorbing states for voter model on a connected graph.
    
    For continuous-time, lazy, or asynchronous voter on a connected graph,
    the absorbing states are the unanimous states.
    
    Args:
        G: Connected graph
        
    Returns:
        Dictionary with absorbing state structure
    """
    n = G.number_of_nodes()
    
    return {
        'n': n,
        'connected': nx.is_connected(G),
        'bipartite': nx.is_bipartite(G),
        'absorbing_states': 2,
        'description': 'All-0 and all-1 (unanimous states)'
    }


def simulate_voter_trajectory(
    G: nx.Graph,
    initial: Tuple[int, ...],
    schedule: str = 'synchronous',
    max_steps: int = 10000
) -> dict:
    """
    Simulate one voter model trajectory.
    
    Args:
        G: Graph
        initial: Initial opinion configuration
        schedule: 'synchronous', 'lazy', or 'asynchronous'
        max_steps: Maximum steps to simulate
        
    Returns:
        Dictionary with trajectory outcome
    """
    state = initial
    
    if schedule == 'synchronous':
        step_fn = lambda g, s: synchronous_voter_step(g, s)
    elif schedule == 'lazy':
        step_fn = lambda g, s: lazy_synchronous_voter_step(g, s)
    elif schedule == 'asynchronous':
        step_fn = lambda g, s: asynchronous_voter_step(g, s)
    else:
        raise ValueError(f"Unknown schedule: {schedule}")
    
    for step in range(max_steps):
        if is_absorbing_state(state):
            return {
                'absorbed': True,
                'unanimous': True,
                'steps': step,
                'final_state': state
            }
        
        state = step_fn(G, state)
    
    return {
        'absorbed': False,
        'unanimous': False,
        'steps': max_steps,
        'final_state': state
    }


def asynchronous_voter_step(G: nx.Graph, opinions: Tuple[int, ...]) -> Tuple[int, ...]:
    """
    One asynchronous voter step: pick one random agent to update.
    
    Args:
        G: Graph
        opinions: Current opinion tuple
        
    Returns:
        New opinion tuple
    """
    n = G.number_of_nodes()
    opinions_list = list(opinions)
    
    v = random.randint(0, n - 1)
    neighbors = list(G.neighbors(v))
    
    if neighbors:
        chosen = random.choice(neighbors)
        opinions_list[v] = opinions[chosen]
    
    return tuple(opinions_list)


def test_schedule_dependency(G: nx.Graph, num_trials: int = 100) -> dict:
    """
    Test voter model under different schedules to verify schedule dependency.
    
    Args:
        G: Graph (should be bipartite for interesting behavior)
        num_trials: Number of random trajectories to simulate
        
    Returns:
        Dictionary with results by schedule
    """
    n = G.number_of_nodes()
    is_bipartite = nx.is_bipartite(G)
    
    results = {}
    
    for schedule in ['synchronous', 'lazy', 'asynchronous']:
        absorbed_count = 0
        total_steps = 0
        
        for trial in range(num_trials):
            initial = tuple(random.randint(0, 1) for _ in range(n))
            
            if is_absorbing_state(initial):
                continue
            
            result = simulate_voter_trajectory(G, initial, schedule, max_steps=5000)
            
            if result['absorbed']:
                absorbed_count += 1
                total_steps += result['steps']
        
        avg_steps = total_steps / absorbed_count if absorbed_count > 0 else None
        
        results[schedule] = {
            'absorbed_count': absorbed_count,
            'absorption_rate': absorbed_count / num_trials,
            'avg_steps_to_absorption': avg_steps
        }
    
    return {
        'n': n,
        'bipartite': is_bipartite,
        'results': results
    }
