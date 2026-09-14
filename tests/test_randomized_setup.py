import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from experiments.common import cases, expected_main_trials
from experiments.node_failure import choose_victim
from experiments.network_partition import choose_isolated, crossing_edges
from routing import RandomRouter


class RandomizedSetupTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'config/randomized_experiments.json').read_text())

    def test_default_counts_are_at_least_ten(self):
        self.assertGreaterEqual(self.config['repetitions'], 10)
        self.assertEqual(expected_main_trials(self.config), 600)

    def test_router_is_seeded_and_operation_local(self):
        left = RandomRouter(44, ('n1', 'n2', 'n3'))
        right = RandomRouter(44, ('n1', 'n2', 'n3'))
        a = [left.select() for _ in range(20)]
        b = [right.select() for _ in range(20)]
        self.assertEqual(a, b)
        self.assertEqual([x['draw'] for x in a], list(range(20)))
        self.assertTrue(all(set(x['candidates']) == {'n1','n2','n3'} for x in a))

    def test_case_order_is_randomized_without_losing_coverage(self):
        rows = cases(self.config, 0, 'normal', random.Random(12))
        self.assertEqual(len(rows), 20)
        self.assertEqual({r['model'] for r in rows}, set(self.config['models']))
        self.assertEqual({r['config'] for r in rows}, set(self.config['consistency_configs']))

    def test_fault_victims_are_from_cluster(self):
        rng = random.Random(9)
        self.assertIn(choose_victim(('n1','n2','n3'), rng), ('n1','n2','n3'))
        isolated = choose_isolated(('n1','n2','n3'), rng)
        self.assertEqual(len(crossing_edges(('n1','n2','n3'), isolated)), 2)


if __name__ == '__main__':
    unittest.main()
