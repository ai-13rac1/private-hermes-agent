"""Networkless MCP token and Hermes configuration provisioning; no wallet access."""
import os
from pathlib import Path
import secrets
import tempfile
import yaml
from research_endpoints import ADDRESS, ENDPOINTS


def publish(path, text, uid, mode):
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(text)
    try:
        os.chown(temporary, uid, uid)
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)



auth = Path('/research-auth')
os.chown(auth, 10003, 10003)
auth.chmod(0o700)
token_path = auth / 'token'
if not token_path.exists():
    publish(token_path, secrets.token_urlsafe(32) + '\n', 10003, 0o600)
token = token_path.read_text().strip()
if not token or any(c.isspace() for c in token):
    raise SystemExit('Existing research MCP token is invalid; it was not replaced')

home = Path('/agent-data')
config_path = home / 'config.yaml'
config = yaml.safe_load(config_path.read_text())
servers = config.setdefault('mcp_servers', {})
for name, port in ENDPOINTS.items():
    key = 'research_' + name
    entry = {'url': f'http://{ADDRESS}:{port}/mcp',
             'headers': {'Authorization': 'Bearer ${X402_TREAZURY_MCP_TOKEN}'}}
    if key in servers and (not isinstance(servers[key], dict) or servers[key].get('url') != entry['url'] or servers[key].get('headers', {}).get('Authorization') != entry['headers']['Authorization']):
        raise SystemExit(f'Existing {key} configuration differs; review it before provisioning')
    servers.setdefault(key, entry)

# Copy only the MCP bearer token, never treasury or wallet credentials, into
# Hermes's profile secrets. Preserve unrelated existing .env entries.
env_path = home / '.env'
lines = env_path.read_text().splitlines() if env_path.exists() else []
lines = [line for line in lines if not line.lstrip().startswith(('X402_TREAZURY_MCP_TOKEN=', 'export X402_TREAZURY_MCP_TOKEN='))]
lines.append('X402_TREAZURY_MCP_TOKEN=' + token)
publish(env_path, '\n'.join(lines) + '\n', 10000, 0o600)
publish(config_path, yaml.safe_dump(config, sort_keys=False), 10000, 0o600)
print('Provisioned 12 research MCP endpoints and their bearer token; wallet state was not accessed.')
