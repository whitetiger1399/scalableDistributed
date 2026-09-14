"""Randomized abrupt node-failure scenario definition."""
import random


def choose_victim(nodes, rng):
    return rng.choice(sorted(nodes))


def description():
    return "Select one Cassandra container uniformly per round, SIGKILL it, wait for two-survivor failure detection, run the randomized client cases, restart the same container, and verify recovery."
