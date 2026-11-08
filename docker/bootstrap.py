"""Networkless, idempotent provisioning of separate SSH trust and data volumes."""
import os
import shutil
import subprocess
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
        raise SystemExit('Existing Hermes config is incompatible with SSH/teep isolation. Migrate it using the networkless config helper in README.md; it was not overwritten.')
    print('Existing compatible Hermes config preserved.')
directory("/executor-home", 10000, 0o755)
directory("/executor-work", 10000, 0o755)
print("Provisioned SSH client trust, executor identity, and separate workspaces.")
