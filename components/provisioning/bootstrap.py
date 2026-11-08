"""Networkless, idempotent provisioning of separate SSH trust and data volumes."""
import os
import shutil
import subprocess
import tempfile
import yaml
from pathlib import Path


def directory(path, uid=0, mode=0o700):
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    os.chown(target, uid, uid)
    target.chmod(mode)
    return target


def key(path):
    if not path.exists():
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(path)], check=True)


agent = directory("/agent-ssh", 10000)
executor = directory("/executor-auth", 0, 0o755)
key(agent / "id_ed25519")
key(executor / "ssh_host_ed25519_key")
for path in agent.iterdir():
    os.chown(path, 10000, 10000)
    path.chmod(0o600)
authorized = executor / "authorized_keys"
authorized.write_text((agent / "id_ed25519.pub").read_text())
authorized.chmod(0o644)
known = agent / "known_hosts"
known.write_text("[10.203.82.3]:2222 " + (executor / "ssh_host_ed25519_key.pub").read_text())
os.chown(known, 10000, 10000)
known.chmod(0o600)
data = directory("/agent-data", 10000, 0o755)
config = data / "config.yaml"
if not config.exists():
    shutil.copyfile("/opt/hermes-config.yaml", config)
    os.chown(config, 10000, 10000)
    config.chmod(0o600)
else:
    try:
        existing = yaml.safe_load(config.read_text())
        valid = (existing.get('terminal', {}).get('backend') == 'ssh'
                 and existing.get('model', {}).get('provider') == 'custom'
                 and existing.get('model', {}).get('base_url') == 'http://10.203.83.3:8337/v1')
    except Exception:
        valid = False
    if not valid:
        raise SystemExit('Hermes config must set terminal.backend=ssh, model.provider=custom, and model.base_url=http://10.203.83.3:8337/v1. Edit settings with: docker compose run --rm configure set <key> <value>.')
    print('Hermes SSH/teep configuration validated.')
# Deployment enablement controls the browser listener across ordinary restarts.
webapp_enabled = os.environ.get('PRIVATE_HERMES_WEBAPP_ENABLED', 'false')
if webapp_enabled not in ('true', 'false'):
    raise SystemExit('WEBAPP_ENABLED must be exactly true or false')
if webapp_enabled == 'false':
    document = yaml.safe_load(config.read_text())
    if document.get('webapp', {}).get('enabled'):
        document['webapp']['enabled'] = False
        with tempfile.NamedTemporaryFile(mode='w', dir=data, delete=False) as stream:
            temporary = Path(stream.name)
            yaml.safe_dump(document, stream, sort_keys=False)
        try:
            os.chown(temporary, 10000, 10000)
            temporary.chmod(0o600)
            os.replace(temporary, config)
        finally:
            temporary.unlink(missing_ok=True)
directory("/executor-home", 10000, 0o755)
directory("/executor-work", 10000, 0o755)
print("Provisioned SSH client trust, executor identity, and separate workspaces.")
