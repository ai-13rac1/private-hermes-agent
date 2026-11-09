"""Run the canonical offline setup service and check its actual exit status."""
import json
import subprocess
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


def ensure_storage(command):
    identifier = setup_container(command)
    if identifier:
        state = json.loads(subprocess.check_output(['docker', 'inspect', identifier, '--format', '{{json .State}}'],
                                                  cwd=ROOT, text=True))
        if state['Status'] == 'exited' and state['ExitCode'] == 0:
            return
    # Wallet commands before first startup only need storage preparation. They
    # must not depend on valid Hermes configuration or initialize SSH/auth state.
    subprocess.run([*command, 'run', '--rm', '-T', '--no-deps', 'setup', 'storage'], cwd=ROOT, check=True)
