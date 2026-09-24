"""Seeded internode partition scenario definition."""
import random


def choose_isolated(nodes, rng):
    return rng.choice(sorted(nodes))


def crossing_edges(nodes, isolated):
    return [(isolated, node) for node in sorted(nodes) if node != isolated]


def choose_groups(nodes, rng, strategy="isolate_one", group_sizes=None):
    """Return two seeded partition groups for either supported topology."""
    nodes = sorted(nodes)
    if strategy == "isolate_one":
        isolated = choose_isolated(nodes, rng)
        return [isolated], [node for node in nodes if node != isolated]
    if strategy == "balanced_random":
        shuffled = list(nodes)
        rng.shuffle(shuffled)
        left_size, right_size = group_sizes
        if left_size + right_size != len(shuffled):
            raise ValueError("partition group sizes do not match node count")
        return sorted(shuffled[:left_size]), sorted(shuffled[left_size:])
    raise ValueError(f"unsupported partition strategy: {strategy}")


def edges_between(groups):
    left, right = groups
    return [(a, b) for a in left for b in right]


def description():
    return "Choose one isolated node per round, drop both directions of internode ports 7000/7001, retain CQL 9042 and client reachability, run cases, then remove only the project fault rules."
