"""
Graph generation for exhaustive enumeration.

Generates all connected simple undirected graphs on n nodes.
Uses networkx for graph representation and isomorphism testing.
"""

import itertools
from typing import Iterator, List, Tuple
import networkx as nx


def generate_all_connected_graphs(n: int) -> Iterator[nx.Graph]:
    """
    Generate all connected simple undirected labeled graphs on n nodes.
    
    This generates all possible edge sets for n labeled nodes (0..n-1)
    and yields only those that produce connected graphs.
    
    For n nodes, there are at most n*(n-1)/2 possible edges.
    We enumerate all 2^(n*(n-1)/2) possible edge sets and filter for connectivity.
    
    Args:
        n: Number of nodes (labeled 0, 1, ..., n-1)
        
    Yields:
        Connected networkx graphs with n nodes
    """
    if n == 0:
        return
    
    if n == 1:
        G = nx.Graph()
        G.add_node(0)
        yield G
        return
    
    nodes = list(range(n))
    possible_edges = list(itertools.combinations(nodes, 2))
    
    for num_edges in range(n - 1, len(possible_edges) + 1):
        for edge_subset in itertools.combinations(possible_edges, num_edges):
            G = nx.Graph()
            G.add_nodes_from(nodes)
            G.add_edges_from(edge_subset)
            
            if nx.is_connected(G):
                yield G


def count_connected_graphs(n: int) -> int:
    """Count total number of connected labeled graphs on n nodes."""
    return sum(1 for _ in generate_all_connected_graphs(n))


def generate_nonisomorphic_connected_graphs(n: int) -> List[nx.Graph]:
    """
    Generate one representative from each isomorphism class of connected graphs on n nodes.
    
    This is more efficient for large n but returns unlabeled (non-isomorphic) representatives.
    For completeness verification, we use all labeled graphs.
    
    Args:
        n: Number of nodes
        
    Returns:
        List of representative graphs (one per isomorphism class)
    """
    if n == 0:
        return []
    
    if n == 1:
        G = nx.Graph()
        G.add_node(0)
        return [G]
    
    seen_graphs = []
    
    for G in generate_all_connected_graphs(n):
        is_new = True
        for H in seen_graphs:
            if nx.is_isomorphic(G, H):
                is_new = False
                break
        
        if is_new:
            seen_graphs.append(G.copy())
    
    return seen_graphs
