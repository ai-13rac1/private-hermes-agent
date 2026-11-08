"""Start all real MCP listeners without treasury state, funding, or paid APIs."""
import json
import os
from pathlib import Path
import secrets
from research_endpoints import ADDRESS, ENDPOINTS

spec = {
    'openapi': '3.0.3', 'info': {'title': 'Free Tor check', 'version': '1'},
    'paths': {'/api/ip': {'get': {'operationId': 'check_tor_exit',
              'responses': {'200': {'description': 'Tor exit status'}}}}},
}
Path('/tmp/tor-check.json').write_text(json.dumps(spec))
config = '''version=1
[network]
mode="tor"
socks_endpoint="unix:/run/tor-research/socks"
socks_auth="tor_extended"
[wallets.fixture]
mode="static"
private_key_env="RESEARCH_TEST_KEY"
max_api_payment_usdc="0.50"
[sources.torcheck]
spec="/tmp/tor-check.json"
base_url="https://check.torproject.org"
prefix="torcheck"
allow_http1=true
'''
for name, port in ENDPOINTS.items():
    config += f'''\n[servers.{name}]
listen="{ADDRESS}:{port}"
allowed_hosts=["{ADDRESS}"]
bearer_token_env="X402_TREAZURY_MCP_TOKEN"
wallet="fixture"
sources=["torcheck"]
'''
Path('/tmp/research-test.toml').write_text(config)
os.environ['X402_TREAZURY_MCP_TOKEN'] = Path('/run/research-auth/token').read_text().strip()
os.environ['RESEARCH_TEST_KEY'] = secrets.token_hex(32)
os.environ['X402_TREAZURY_CONFIG'] = '/tmp/research-test.toml'
os.execvp('x402_treazury', ['x402_treazury', 'serve'])
