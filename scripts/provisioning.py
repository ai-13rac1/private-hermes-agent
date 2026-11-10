"""Run the canonical offline setup service and check its actual exit status."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
from deployment import ROOT


def setup_container(command):
    return subprocess.check_output([*command, 'ps', '-a', '-q', 'setup'], cwd=ROOT, text=True).strip()


def initialize_setup(command):
    # --wait expects a running/healthy service and can reject a successfully
    # exited one-shot. Wait for this container's exit status explicitly instead.
    subprocess.run([*command, 'up', '-d', '--no-deps', '--force-recreate', 'setup'], cwd=ROOT, check=True)
    identifier = setup_container(command)
    if not identifier:
        raise RuntimeError('Setup container was not created')
    code = int(subprocess.check_output(['docker', 'wait', identifier], cwd=ROOT, text=True).strip())
    if code:
        subprocess.run([*command, 'logs', '--tail', '40', 'setup'], cwd=ROOT, check=False)
        raise RuntimeError(f'Offline setup failed (exit {code}); application startup was not attempted.')


def initialize_research_config(command, root=ROOT):
    """Seed operator policy from the built image without mounting private state."""
    path = Path(root) / 'config/x402_treazury/research_desk.toml'
    if path.exists():
        if not path.is_file():
            raise RuntimeError('config/x402_treazury/research_desk.toml must be a file')
        return
    model = json.loads(subprocess.check_output(
        [*command, '--profile', 'x402_treazury', 'config', '--format', 'json'],
        cwd=ROOT, text=True))
    image = model['services']['x402_treazury']['image']
    content = subprocess.check_output(
        ['docker', 'run', '--rm', '--pull', 'never', '--network', 'none', '--entrypoint', 'cat', image,
         '/opt/x402/examples/deployments/research_desk.toml'], cwd=ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Treasury UID 10003 needs read access; the host-owned config parent can
    # remain private. Mount the leaf directory only, read-only in containers.
    path.parent.chmod(0o755)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.research-config-', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), 0o644)
            try:
                os.link(temporary, path)
            except FileExistsError:
                if not path.is_file():
                    raise RuntimeError('config/x402_treazury/research_desk.toml must be a file')
        finally:
            temporary.unlink()
