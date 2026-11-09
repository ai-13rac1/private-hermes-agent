#!/usr/bin/env python3
"""Apply validated deployment settings; Funnel is never enabled implicitly."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from deployment import ROOT, compose, render, settings
from auth import validate
from x402_treazury import Controller, operation_lock


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
        run(all_command + ['stop', 'tailscale'])
        if result.returncode:
            raise RuntimeError('Stopped Tailscale, but could not confirm persistent Funnel reset. Inspect the node before re-enabling.')
    run(all_command + ['stop', 'tailscale'])
    run(all_command + ['rm', '-f', 'tailscale'])


def main_unlocked():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('build', 'up', 'down', 'config', 'compose'))
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == 'down':
        # Shutdown must remain available even after an invalid operator edit.
        os.environ.update(TAILSCALE_FUNNEL_ENABLED='false',
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
        run(command + ['--profile', '*', 'build'])
    elif args.action == 'down':
        try:
            stop_funnel(all_command)
        finally:
            run(all_command + ['down', '--timeout', '-1'])
    else:
        run([sys.executable, 'scripts/preflight.py', *(['--funnel'] if config.funnel else [])])
        path = ROOT / 'config/webapp/auth.json'
        if not path.is_file():
            raise RuntimeError('Run make init before starting the stack.')
        validate(json.loads(path.read_text()))
        render(config)
        if not config.funnel:
            stop_funnel(all_command)
        # A changed bind-mounted credential file does not itself recreate a
        # completed container. Always apply current settings before startup.
        run(command + ['up', '-d', '--wait', '--no-deps', '--force-recreate', 'bootstrap'])
        infrastructure = ['tor', 'agent-net', 'executor-net', 'executor', 'teep']
        run(command + ['up', '-d', '--wait', *infrastructure])
        controller = Controller(command, ROOT)
        # This gateway is about to be recreated and reads the disconnected
        # configuration at boot; do not wait on an old gateway's control RPC.
        controller.configure('disconnect')
        run(command + ['up', '-d', '--no-deps', '--force-recreate', 'webapp-proxy', 'hermes'])
        if config.funnel:
            run(command + ['up', '-d', 'tailscale'])
        controller.startup()


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('up', 'down'):
        with operation_lock(ROOT):
            main_unlocked()
    else:
        main_unlocked()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError) as error:
        raise SystemExit(str(error))
