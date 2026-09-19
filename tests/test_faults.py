import unittest
from unittest.mock import patch

from experiments.faults import parse_status, wait_failure

STATUS = """Datacenter: dc1
===============
Status=Up/Down
|/ State=Normal/Leaving/Joining/Moving
-- Address Load Tokens Owns Host ID Rack
UN 172.20.0.2 100 KiB 16 100.0% aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa rack1
DN 172.20.0.3 100 KiB 16 100.0% bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb rack1
UN 172.20.0.4 100 KiB 16 100.0% cccccccc-cccc-cccc-cccc-cccccccccccc rack1
"""


class FaultTests(unittest.TestCase):
    def test_status_parser_uses_address_and_host_id(self):
        rows = parse_status(STATUS)
        self.assertEqual(rows['172.20.0.3']['state'], 'DN')
        self.assertEqual(rows['172.20.0.3']['host_id'], 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')

    @patch('experiments.faults.membership', return_value=STATUS)
    def test_failure_detection_matches_victim_ip(self, _membership):
        result = wait_failure('n2', '172.20.0.3', timeout_seconds=.1, consecutive=1)
        self.assertEqual(result['victim_ip'], '172.20.0.3')
        self.assertTrue(result['observations'][-1]['matching'])

    @patch('experiments.faults.membership', return_value=STATUS)
    def test_failure_detection_rejects_wrong_down_node(self, _membership):
        with self.assertRaises(TimeoutError):
            wait_failure('n2', '172.20.0.9', timeout_seconds=0, consecutive=1)


if __name__ == '__main__':
    unittest.main()
