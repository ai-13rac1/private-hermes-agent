"""Keep x402_treazury deployment adaptation narrow and reject upstream layout drift."""
import importlib.util
from pathlib import Path
import sys
import tomllib
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'components/x402_treazury'))
from endpoints import ENDPOINTS
spec = importlib.util.spec_from_file_location('x402_treazury_render', Path(__file__).parents[1] / 'components/x402_treazury/render-config.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


def example():
    text = '''version=1
[network]
mode="tor"
socks_endpoint = "127.0.0.1:9150"
socks_auth="tor_extended"
[treasury]
state_dir = "old-state"
[wallets.web]
mode="zcash_rotation"
max_api_payment_usdc="0.50"
[sources.test]
extends="../../providers/example.toml"
send_tools=[{to="web"}]
'''
    for name, port in ENDPOINTS.items():
        text += f'''\n[servers.{name}]
listen = "127.0.0.1:{port}"
allowed_hosts = ["host.docker.internal", "127.0.0.1"]
bearer_token_env="X402_TREAZURY_MCP_TOKEN"
wallet="web"
'''
    return text


class X402TreazuryRendererTests(unittest.TestCase):
    def test_policy_and_source_selection_are_preserved(self):
        before = tomllib.loads(example())
        after = tomllib.loads(renderer.render(example()))
        for field in ('sources', 'wallets'):
            self.assertEqual(before[field], after[field])
        self.assertEqual(after['network']['socks_auth'], 'tor_extended')
        self.assertEqual(after['network']['mode'], 'tor')
        self.assertEqual(after['network']['socks_endpoint'], 'unix:/run/tor-x402_treazury/socks')
        self.assertEqual(after['treasury']['state_dir'], '/var/lib/x402/state')
        self.assertEqual(after['servers']['web']['listen'], '127.0.0.1:3010')
        self.assertEqual(after['servers']['web']['allowed_hosts'], ['127.0.0.1'])

    def test_non_tor_policy_is_rejected(self):
        with self.assertRaises(ValueError):
            renderer.render(example().replace('mode="tor"', 'mode="direct"'))

    def test_listener_changes_require_review(self):
        for replacement in ('127.0.0.1:9999', '0.0.0.0:3010'):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                renderer.render(example().replace('127.0.0.1:3010', replacement))


if __name__ == '__main__':
    unittest.main()
