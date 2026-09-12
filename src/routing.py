"""Seeded random routing, separate from the application workload."""
import random


class RandomRouter:
    def __init__(self, seed, candidates):
        self.rng = random.Random(seed)
        self.candidates = sorted(candidates)
        self.draw = 0

    def select(self):
        if not self.candidates:
            raise RuntimeError('No client-reachable CQL endpoint')
        node = self.rng.choice(self.candidates)
        result = dict(selected_node=node, candidates=list(self.candidates), draw=self.draw)
        self.draw += 1
        return result
