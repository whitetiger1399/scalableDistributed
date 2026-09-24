import json
from pathlib import Path
import unittest

from experiments.configuration import normalize

ROOT = Path(__file__).resolve().parents[1]


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads((ROOT/'config/cassandra_driver_experiments.json').read_text())

    def test_default_is_valid(self):
        self.assertEqual(normalize(self.raw)['profile'], 'full')

    def test_smoke_can_select_one_model(self):
        self.raw.update(models=['RYW'], rounds=1, repetitions=1)
        self.assertEqual(normalize(self.raw, full=False)['models'], ['RYW'])

    def test_unsupported_runtime_setting_is_rejected(self):
        self.raw['database']['replication_factor'] = 2
        with self.assertRaisesRegex(ValueError, 'replication_factor'):
            normalize(self.raw)

    def test_custom_coordinator_policy_is_rejected(self):
        self.raw['routing']['policy'] = 'uniform_random'
        with self.assertRaisesRegex(ValueError, 'routing'):
            normalize(self.raw)

    def test_duplicate_case_is_rejected(self):
        self.raw['models'].append('RYW')
        with self.assertRaisesRegex(ValueError, 'duplicates'):
            normalize(self.raw)

    def test_expanded_cluster_profile_is_valid(self):
        expanded = json.loads((ROOT/'config/cassandra_driver_expanded_experiments.json').read_text())
        normalized = normalize(expanded)
        self.assertEqual(normalized['cluster']['nodes'], ['n1', 'n2', 'n3', 'n4', 'n5'])
        self.assertEqual(normalized['faults']['partition_group_sizes'], [2, 3])

    def test_expanded_partition_sizes_must_cover_cluster(self):
        expanded = json.loads((ROOT/'config/cassandra_driver_expanded_experiments.json').read_text())
        expanded['faults']['partition_group_sizes'] = [2, 2]
        with self.assertRaisesRegex(ValueError, 'partition_group_sizes'):
            normalize(expanded)

    def test_read_repair_control_rejects_expanded_cluster(self):
        expanded = json.loads((ROOT/'config/cassandra_driver_expanded_experiments.json').read_text())
        expanded['enabled_experiments'].append('read_repair')
        with self.assertRaisesRegex(ValueError, 'three-node'):
            normalize(expanded)


if __name__ == '__main__':
    unittest.main()
