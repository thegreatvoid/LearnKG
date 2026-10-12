"""Stage 5: turn scores into a consistent edge set (DAG for Prerequisite/Part-of, no mixed labels per pair)."""

import networkx as nx


def best_edges(scores, threshold: float):
    """One relation per unordered pair: the highest-scoring (direction, type) at or above threshold."""
    chosen = {}
    for (s, t), rels in scores.items():
        for rel, sc in rels.items():
            key = frozenset((s, t))
            if sc >= threshold and (key not in chosen or sc > chosen[key][3]):
                chosen[key] = (s, t, rel, sc)
    return list(chosen.values())


def enforce_dag(edges, relation: str):
    """Drops the lowest-scoring edge of each cycle among `relation` edges. Returns (kept, dropped)."""
    own = [e for e in edges if e[2] == relation]
    other = [e for e in edges if e[2] != relation]
    G = nx.DiGraph()
    for s, t, _, sc in own:
        G.add_edge(s, t, score=sc)
    dropped = []
    while True:
        try:
            cyc = nx.find_cycle(G)
        except nx.NetworkXNoCycle:
            break
        u, v = min(cyc, key=lambda e: G.edges[e]["score"])
        dropped.append((u, v, relation, G.edges[(u, v)]["score"]))
        G.remove_edge(u, v)
    kept = [(s, t, relation, G.edges[(s, t)]["score"]) for s, t in G.edges]
    return other + kept, dropped


def make_consistent(scores, threshold: float):
    edges = best_edges(scores, threshold)
    all_dropped = []
    for rel in ("Prerequisite", "Part-of"):
        edges, dropped = enforce_dag(edges, rel)
        all_dropped += dropped
    return edges, all_dropped
