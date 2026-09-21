import json
import random
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from experiments.common import cases, expected_main_trials
from experiments.node_failure import choose_victim
from experiments.network_partition import choose_isolated, crossing_edges
from routing import DriverRoutingEvidence, POLICY_NAME
from scripts.run_randomized import timing_fields


class RandomizedSetupTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'config/cassandra_driver_experiments.json').read_text())

    def test_default_counts_are_at_least_ten(self):
        self.assertGreaterEqual(self.config['repetitions'], 10)
        expected = (len(self.config['scenarios']) * len(self.config['consistency_configs'])
                    * len(self.config['models']) * self.config['rounds'])
        self.assertEqual(expected_main_trials(self.config), expected)

    def test_routing_evidence_records_driver_choice_without_selecting_it(self):
        class Host:
            def __init__(self, address, is_up=True, datacenter='dc1'):
                self.address, self.is_up, self.datacenter = address, is_up, datacenter
        hosts = [Host('10.0.0.1'), Host('10.0.0.2'), Host('10.0.0.3', is_up=False)]
        evidence = DriverRoutingEvidence({'10.0.0.1':'n1','10.0.0.2':'n2','10.0.0.3':'n3'}, 'dc1')
        route = evidence.begin(hosts)
        evidence.finish(route, hosts[1], [hosts[1]])
        self.assertEqual(route['policy'], POLICY_NAME)
        self.assertEqual(route['operation_index'], 0)
        self.assertEqual(route['eligible_nodes'], ['n1', 'n2'])
        self.assertEqual(route['selected_node'], 'n2')
        self.assertEqual(route['attempted_nodes'], ['n2'])

    def test_case_order_is_randomized_without_losing_coverage(self):
        rows = cases(self.config, 'run-test', 0, 'normal', random.Random(12))
        expected_cases = len(self.config['consistency_configs']) * len(self.config['models'])
        self.assertEqual(len(rows), expected_cases)
        self.assertEqual({r['model'] for r in rows}, set(self.config['models']))
        self.assertEqual({r['config'] for r in rows}, set(self.config['consistency_configs']))
        self.assertEqual(len({r['key'] for r in rows}), expected_cases)

    def test_fault_victims_are_from_cluster(self):
        rng = random.Random(9)
        self.assertIn(choose_victim(('n1','n2','n3'), rng), ('n1','n2','n3'))
        isolated = choose_isolated(('n1','n2','n3'), rng)
        self.assertEqual(len(crossing_edges(('n1','n2','n3'), isolated)), 2)

    def test_completion_timing_has_start_end_and_elapsed_minutes(self):
        started_utc = '2026-09-21T08:00:00+00:00'
        timing = timing_fields(started_utc, time.monotonic() - 120)
        self.assertEqual(timing['started_utc'], started_utc)
        self.assertIn('ended_utc', timing)
        self.assertGreaterEqual(timing['completion_time_minutes'], 2.0)


if __name__ == '__main__':
    unittest.main()
