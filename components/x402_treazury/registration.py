"""MCP token and Hermes registration operations for the offline setup service."""
import os
from pathlib import Path
import secrets
import tempfile
import hermes_yaml as yaml
from endpoints import ADDRESS, ENDPOINTS


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


def configure(mode, home, auth):
    if mode not in ('token', 'connect', 'disconnect'):
        raise SystemExit('Expected token, connect or disconnect')
    token = None
    if mode != 'disconnect':
        os.chown(auth, 10003, 10003)
        auth.chmod(0o700)
        token_path = auth / 'token'
        if not token_path.exists():
            publish(token_path, secrets.token_urlsafe(32) + '\n', 10003, 0o600)
        token = token_path.read_text().strip()
        if not token or any(c.isspace() for c in token):
            raise SystemExit('Existing x402_treazury MCP token is invalid; it was not replaced')

    config_path = home / 'config.yaml'
    config = yaml.safe_load(config_path.read_text())
    original = yaml.safe_dump(config, sort_keys=False)
    servers = config.setdefault('mcp_servers', {})
    for name, port in ENDPOINTS.items():
        key = 'x402_treazury_' + name
        if mode == 'disconnect':
            servers.pop(key, None)
            continue
        if mode == 'token':
            continue
        entry = {'url': f'http://{ADDRESS}:{port}/mcp',
                 'headers': {'Authorization': 'Bearer ${X402_TREAZURY_MCP_TOKEN}'}}
        if key in servers and (not isinstance(servers[key], dict) or servers[key].get('url') != entry['url'] or servers[key].get('headers', {}).get('Authorization') != entry['headers']['Authorization']):
            raise SystemExit(f'Existing {key} configuration differs; review it before provisioning')
        servers.setdefault(key, entry)

    # Copy only the MCP bearer token, never treasury or wallet credentials, into
    # Hermes's profile secrets. Preserve unrelated existing .env entries.
    env_path = home / '.env'
    old_env = env_path.read_text() if env_path.exists() else ''
    lines = old_env.splitlines()
    lines = [line for line in lines if not line.lstrip().startswith(('X402_TREAZURY_MCP_TOKEN=', 'export X402_TREAZURY_MCP_TOKEN='))]
    if token:
        lines.append('X402_TREAZURY_MCP_TOKEN=' + token)
    text = '\n'.join(lines) + ('\n' if lines else '')
    if text != old_env:
        publish(env_path, text, 10000, 0o600)
    updated = yaml.safe_dump(config, sort_keys=False)
    if updated != original:
        publish(config_path, updated, 10000, 0o600)
    return {'mode': mode, 'changed': updated != original or text != old_env}
