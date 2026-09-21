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


if __name__ == '__main__':
    unittest.main()
