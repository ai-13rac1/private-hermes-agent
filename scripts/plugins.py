#!/usr/bin/env python3
"""Manage persistent user plugins with Hermes's native CLI, as the agent UID."""
import subprocess
import sys
from deployment import ROOT, maintenance_compose


def main():
    command = maintenance_compose()
    running = subprocess.check_output([*command, 'ps', '-q', '--status', 'running', 'hermes'], cwd=ROOT, text=True).strip()
    if not running:
        raise SystemExit('Start the stack with make up before managing plugins.')
    terminal = [] if sys.stdin.isatty() and sys.stdout.isatty() else ['-T']
    result = subprocess.run([*command, 'exec', *terminal, '--user', '10000:10000', 'hermes',
                             '/opt/hermes/.venv/bin/hermes', 'plugins', *sys.argv[1:]], cwd=ROOT)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
