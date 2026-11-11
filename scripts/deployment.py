"""Compose handles dotenv interpolation; this module validates feature settings."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'components/webapp'))
from settings import Settings, proxy_config


def settings():
    result = subprocess.run(['docker', 'compose', '-f', 'compose.yaml', 'config', '--format', 'json'],
                            cwd=ROOT, text=True, capture_output=True, check=True)
    return Settings.read(json.loads(result.stdout)['x-deployment'])


def compose(config, all_ingress=False):
    command = ['docker', 'compose', '-f', 'compose.yaml']
    if config.funnel or all_ingress:
        command += ['-f', 'compose.funnel.yaml']
    return command


def maintenance_compose(all_ingress=False, executor_build=False):
    # These operations must not start ingress, inference or the agent with
    # placeholders. Actual treasury policy remains in its mounted configuration.
    # Compose still interpolates unused services and publications.
    os.environ.update(TAILSCALE_FUNNEL_ENABLED='false', WEBAPP_EXTERNAL_CONTENT='off',
                      WEBAPP_BIND='127.0.0.1', WEBAPP_PORT='9120', WEBAPP_USERNAME='admin',
                      TAILSCALE_FUNNEL_HOST='', TAILSCALE_FUNNEL_PORT='443',
                      TAILSCALE_HOSTNAME='private-hermes', TEEP_HOST_PORT='8337', TEEP_SERVE_ARGS='')
    if not executor_build:
        # Saved-state inspection/shutdown do not select or build an executor.
        # An invalid optional desktop preference must not block those operations.
        os.environ['COMPUTER_USE_ENABLED'] = 'false'
    command = ['docker', 'compose', '-f', 'compose.yaml']
    if all_ingress:
        command += ['-f', 'compose.funnel.yaml']
    return command


def maintenance_command(arguments):
    if not arguments:
        return False
    if arguments[0] in ('build', 'logs', 'ps', 'top', 'port', 'exec', 'stop', 'down', 'rm', 'kill', 'pause', 'unpause'):
        return True
    # Explicit networkless maintenance jobs; do not normalize arbitrary launches.
    if arguments[0] != 'run' or '--no-deps' not in arguments:
        return False
    options = iter(arguments[1:])
    for value in options:
        if value in ('--rm', '--no-deps', '-T'):
            continue
        if value in ('--entrypoint', '--volume', '-v', '--env', '-e', '--user', '-u', '--name', '--workdir', '-w'):
            if next(options, None) is None:
                return False
            continue
        return value in ('hermes-config', 'setup-storage', 'mcp-config',
                         'x402_treazury-inspect', 'x402_treazury-admin')
    return False


def render(config):
    path = ROOT / 'config/webapp/proxy.cfg'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(proxy_config(config))
