"""Reject grants that could accidentally turn MCP access into host/VM access."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('policy', Path(__file__).parents[1] / 'docker/network.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class MCPPolicyTests(unittest.TestCase):
    def grants(self, value):
        with patch.object(Path, 'read_text', return_value=json.dumps(value)):
            return policy.mcp_grants()

    def test_no_grants_by_default(self):
        self.assertEqual(self.grants([]), [])

    def test_exact_selected_service_is_accepted(self):
        self.assertEqual(len(self.grants([{'ip': '10.203.84.10', 'port': 8000}])), 1)

    def test_host_vm_router_and_reserved_addresses_are_rejected(self):
        for address in ('172.17.0.1', '192.168.65.254', '127.0.0.1', '169.254.169.254',
                        '10.203.80.3', '10.203.84.0', '10.203.84.1', '10.203.84.2',
                        '10.203.84.255', '::1', 'example.com', '10.203.84.10/24'):
            with self.subTest(address=address), self.assertRaises(ValueError):
                self.grants([{'ip': address, 'port': 8000}])

    def test_ambiguous_or_broad_grants_are_rejected(self):
        for value in ({}, ['10.203.84.10'], [{'ip': '10.203.84.10'}],
                      [{'ip': '10.203.84.10', 'port': 8000, 'allow_all': True}]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.grants(value)
        for port in (True, 0, -1, 65536, '8000', '*', [8000, 8001]):
            with self.subTest(port=port), self.assertRaises(ValueError):
                self.grants([{'ip': '10.203.84.10', 'port': port}])


if __name__ == '__main__':
    unittest.main()
