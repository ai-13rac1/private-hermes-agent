"""Configure native webapp auth without mounting host credentials into Hermes."""
import json
import os
from pathlib import Path
import tempfile
import yaml
from auth import validate

credentials = validate(json.loads(Path('/run/webapp/auth.json').read_text()))
path = Path('/agent-data/config.yaml')
config = yaml.safe_load(path.read_text())
config['terminal'].update({'ssh_host': '10.203.82.3', 'ssh_port': 2222,
                           'ssh_user': 'runner', 'ssh_key': '/run/agent-ssh/id_ed25519'})
config['webapp'] = {'enabled': True, 'host': '0.0.0.0', 'port': 9120, 'public_url': ''}
dashboard = config.setdefault('dashboard', {})
dashboard['trusted_proxies'] = ['10.203.85.3']
dashboard['public_url'] = ''
dashboard['basic_auth'] = {'username': os.environ['WEBAPP_USERNAME'], **credentials}
dashboard['session_token_auth'] = {'enabled': False}
with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
    temporary = Path(stream.name)
    yaml.safe_dump(config, stream, sort_keys=False)
try:
    os.chown(temporary, 10000, 10000)
    temporary.chmod(0o600)
    os.replace(temporary, path)
finally:
    temporary.unlink(missing_ok=True)
print('Configured authenticated webapp; only the fixed proxy is trusted.')
