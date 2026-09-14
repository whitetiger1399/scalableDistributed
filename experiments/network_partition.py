"""Randomized internode partition scenario definition."""
import random


def choose_isolated(nodes, rng):
    return rng.choice(sorted(nodes))


def crossing_edges(nodes, isolated):
    return [(isolated, node) for node in sorted(nodes) if node != isolated]


def description():
    return "Choose one isolated node per round, drop both directions of internode ports 7000/7001, retain CQL 9042 and client reachability, run cases, then remove only the project fault rules."
