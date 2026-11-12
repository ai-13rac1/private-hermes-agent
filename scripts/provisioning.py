"""Run the canonical offline setup service and check its actual exit status."""
import difflib
import json
import os
from pathlib import Path
import subprocess
import sys
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


def packaged_research_config(command):
    """Read the rendered default from the selected local image, offline."""
    model = json.loads(subprocess.check_output(
        [*command, '--profile', 'x402_treazury', 'config', '--format', 'json'],
        cwd=ROOT, text=True))
    image = model['services']['x402_treazury']['image']
    return subprocess.check_output(
        ['docker', 'run', '--rm', '--pull', 'never', '--network', 'none', '--entrypoint', 'cat', image,
         '/opt/x402/examples/deployments/research_desk.toml'], cwd=ROOT)


def research_config_diff(command, root=ROOT):
    """Display textual differences without changing policy or wallet state."""
    path = Path(root) / 'config/x402_treazury/research_desk.toml'
    saved = path.read_text()
    packaged = packaged_research_config(command).decode('utf-8')
    # Normalize line endings and supply a terminator for readable final diff lines.
    changes = list(difflib.unified_diff(
        packaged.splitlines(), saved.splitlines(),
        fromfile='packaged default (local image)', tofile='saved config (config/x402_treazury/research_desk.toml)',
        lineterm=''))
    if changes:
        print('Differences from packaged defaults (includes intentional customization; saved config is preserved):')
        print('\n'.join(changes), flush=True)
    else:
        print('Research config matches packaged defaults.', flush=True)


def report_research_config_diff(command, root=ROOT):
    """Keep automatic comparison advisory, including when inspection fails."""
    try:
        research_config_diff(command, root)
    except (OSError, UnicodeError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f'Research config comparison unavailable: {error}. Retry make x402_treazury-config-diff.',
              file=sys.stderr, flush=True)


def initialize_research_config(command, root=ROOT):
    """Seed operator policy from the built image without mounting private state."""
    path = Path(root) / 'config/x402_treazury/research_desk.toml'
    if path.exists():
        if not path.is_file():
            raise RuntimeError('config/x402_treazury/research_desk.toml must be a file')
        return
    content = packaged_research_config(command)
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
