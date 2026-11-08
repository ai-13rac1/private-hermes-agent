#!/usr/bin/env python3
"""Select optional ingress layers from validated .env settings; never enable them implicitly."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from deployment import ROOT, compose, render, settings
from auth import validate


def run(command, **kwargs):
    return subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def capture(command):
    return run(command, text=True, capture_output=True).stdout.strip()


def stop_funnel(all_command):
    identifier = capture(all_command + ['ps', '-q', '--status', 'running', 'tailscale'])
    if identifier:
        result = subprocess.run(all_command + ['exec', '-T', 'tailscale', 'tailscale',
                               '--socket=/tmp/tailscaled.sock', 'funnel', 'reset'],
                                cwd=ROOT, text=True, capture_output=True)
        run(all_command + ['stop', 'tailscale', 'funnel-ingress'])
        if result.returncode:
            raise RuntimeError('Stopped Tailscale, but could not confirm persistent Funnel reset. Inspect the node before re-enabling.')
    run(all_command + ['stop', 'tailscale', 'funnel-ingress'])
    run(all_command + ['rm', '-f', 'tailscale', 'funnel-ingress'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('build', 'up', 'down', 'config', 'compose'))
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == 'down':
        # Shutdown must remain available even after an invalid operator edit.
        os.environ.update(WEBAPP_ENABLED='false', TAILSCALE_FUNNEL_ENABLED='false',
                          WEBAPP_BIND='127.0.0.1', WEBAPP_PORT='9120', WEBAPP_USERNAME='admin',
                          TAILSCALE_FUNNEL_HOST='', TAILSCALE_FUNNEL_PORT='443',
                          TAILSCALE_HOSTNAME='private-hermes')
    config = settings()
    command = compose(config)
    all_command = compose(config, all_ingress=True)
    if args.action == 'compose':
        if not args.arguments:
            raise ValueError('Provide a Compose command after compose')
        run(command + args.arguments)
    elif args.action == 'config':
        run(command + ['config', '--quiet'])
    elif args.action == 'build':
        run(command + ['build'])
    elif args.action == 'down':
        try:
            stop_funnel(all_command)
        finally:
            run(all_command + ['down'])
    else:
        run([sys.executable, 'scripts/preflight.py', *(['--ingress'] if config.enabled else []),
             *(['--funnel'] if config.funnel else [])])
        if config.enabled:
            path = ROOT / 'config/webapp/auth.json'
            if not path.is_file():
                raise RuntimeError('Run make webapp-credentials before enabling the webapp.')
            validate(json.loads(path.read_text()))
            render(config)
        if not config.funnel:
            stop_funnel(all_command)
        current = capture(all_command + ['ps', '-q', 'agent-net'])
        running_gateway = bool(capture(all_command + ['ps', '-q', '--status', 'running', 'hermes']))
        if current:
            env = json.loads(capture(['docker', 'inspect', current, '--format', '{{json .Config.Env}}']))
            previously_enabled = 'PRIVATE_HERMES_WEBAPP=1' in env
            if previously_enabled != config.enabled:
                # Consumers must be recreated with their namespace owner.
                run(all_command + ['stop', 'hermes', 'x402_treazury', 'agent-net'])
                run(all_command + ['rm', '-f', 'hermes', 'x402_treazury', 'agent-net'])
        if not config.enabled:
            run(all_command + ['stop', 'webapp-publisher', 'webapp-proxy'])
            run(all_command + ['rm', '-f', 'webapp-publisher', 'webapp-proxy'])
        infrastructure = ['bootstrap', 'tor', 'agent-net', 'executor-net', 'executor', 'teep',
                          'x402_treazury-setup', 'x402_treazury']
        if config.enabled:
            infrastructure += ['webapp-setup']
        run(command + ['up', '-d', '--wait', *infrastructure])
        if config.enabled:
            run(command + ['up', '-d', '--wait', '--no-deps', '--force-recreate',
                           'webapp-setup', 'webapp-proxy', 'webapp-publisher'])
        if config.enabled or running_gateway:
            run(command + ['up', '-d', '--no-deps', '--force-recreate', 'hermes'])
        if config.funnel:
            run(command + ['up', '-d', 'tailscale'])


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError) as error:
        raise SystemExit(str(error))
