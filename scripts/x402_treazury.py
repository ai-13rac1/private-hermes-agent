#!/usr/bin/env python3
"""Deployment-side staged onboarding; no wallet secrets leave its container."""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from deployment import ROOT, compose, settings
from provisioning import ensure_storage, initialize_research_config


@contextmanager
def operation_lock(root):
    folder = Path(root) / 'config/x402_treazury'
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'operation.lock').open('a') as lock:
        os.chmod(lock.name, 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('Another deployment/onboarding operation is running.') from error
        yield


class Controller:
    def __init__(self, command, root=ROOT):
        self.command, self.root = command, Path(root)

    def call(self, *arguments, **kwargs):
        return subprocess.run([*self.command, *arguments], cwd=self.root, text=True, check=True, **kwargs)

    def admin(self, action, capture=False):
        return self.call('run', '--rm', '-T', '--no-deps', 'x402_treazury-admin', action,
                         capture_output=capture)

    def inspect(self):
        return json.loads(self.admin('inspect', capture=True).stdout)

    def running(self, service):
        return self.call('ps', '-q', '--status', 'running', service, capture_output=True).stdout.strip()

    def configure(self, mode):
        result = self.call('run', '--rm', '-T', '--no-deps', 'setup', 'mcp', mode,
                           capture_output=True)
        return json.loads(result.stdout)['changed']

    def client(self, action, check=True):
        script = (self.root / 'components/x402_treazury/mcp-client.py').read_text()
        return subprocess.run([*self.command, 'exec', '-T', '--user', '10000:10000', 'hermes',
                               '/opt/hermes/.venv/bin/python', '-c', script, action],
                              cwd=self.root, text=True, capture_output=True, check=check)

    def disconnect(self):
        if self.configure('disconnect') and self.running('hermes'):
            self.reload()

    def reload(self):
        while self.running('hermes'):
            result = self.client('reload', check=False)
            if result.returncode == 0:
                return
            if result.returncode != 75:
                raise RuntimeError('Hermes MCP reload failed; research remains disconnected. ' + (result.stderr or '').strip())
            time.sleep(1)
        raise RuntimeError('Hermes stopped before its MCP configuration could reload')

    def wallet_command(self, action):
        # Detached execution keeps Compose's interrupt handler from escalating
        # to SIGKILL after its ordinary shutdown timeout. We own graceful stop.
        project = json.loads(self.call('config', '--format', 'json', capture_output=True).stdout)['name']
        name = project + '-x402-onboarding'
        interrupted = []
        previous = {}
        logs = None
        started = finished = False
        def cancel(signum, _frame):
            interrupted.append(signum)
            subprocess.run(['docker', 'stop', '--timeout', '-1', name], cwd=self.root, check=False)
        try:
            # A retained container signals a prior interrupted/failed cleanup;
            # never remove or overwrite it implicitly.
            previous = {sig: signal.signal(sig, cancel) for sig in (signal.SIGINT, signal.SIGTERM)}
            self.call('run', '-d', '-T', '--no-deps', '--name', name, '--entrypoint', 'python3',
                      'x402_treazury-setup', '/opt/onboarding.py', action, capture_output=True)
            started = True
            if interrupted:
                cancel(interrupted[0], None)
            logs = subprocess.Popen(['docker', 'logs', '--follow', name], cwd=self.root)
            result = subprocess.run(['docker', 'wait', name], cwd=self.root, text=True,
                                    capture_output=True, check=True)
            code = int(result.stdout.strip())
            finished = True
            logs.wait()
            if interrupted or code:
                raise RuntimeError(f'x402_treazury {action} stopped (exit {code}); inspect status before retrying.')
        finally:
            if started and not finished:
                subprocess.run(['docker', 'stop', '--timeout', '-1', name], cwd=self.root, check=False)
            for sig, handler in previous.items():
                signal.signal(sig, handler)
            if logs and logs.poll() is None:
                logs.terminate()
                logs.wait()
            # Non-forced removal refuses a still-running financial operation.
            if started:
                subprocess.run(['docker', 'rm', name], cwd=self.root, check=False, capture_output=True)

    def initialize(self):
        state = self.inspect()
        if not state['wallet_absent'] and not state['wallet_valid']:
            raise RuntimeError(state['reason'])
        self.call('up', '-d', '--wait', '--no-deps', 'tor', 'agent-net')
        self.wallet_command('init')

    def prepare(self):
        if not self.running('hermes'):
            raise RuntimeError('Start Hermes with make up before preparing research services.')
        if self.inspect()['prepared']:
            self.activate()
            return
        self.disconnect()
        self.call('stop', '--timeout', '-1', 'x402_treazury')
        self.admin('disconnected')
        self.wallet_command('prepare')
        self.activate()

    def activate(self):
        if not self.running('hermes'):
            raise RuntimeError('Start Hermes with make up before connecting research services.')
        state = self.inspect()
        if not state['prepared']:
            raise RuntimeError(state['reason'] + ' Run make x402_treazury-prepare when ready.')
        try:
            self.configure('token')
            self.call('up', '-d', '--no-deps', 'x402_treazury')
            print('Waiting for authenticated research MCP initialization (Ctrl-C leaves Hermes available).', flush=True)
            initial_restarts = None
            while True:
                identifier = self.running('x402_treazury')
                if not identifier:
                    raise RuntimeError('Research service exited before MCP readiness; inspect its logs.')
                restarts = subprocess.check_output(['docker', 'inspect', identifier, '--format', '{{.RestartCount}}'], text=True)
                initial_restarts = int(restarts) if initial_restarts is None else initial_restarts
                if int(restarts) > initial_restarts:
                    raise RuntimeError('Research service restarted before MCP readiness; inspect its logs.')
                probe = self.client('probe', check=False)
                if probe.returncode == 0:
                    break
                if probe.returncode != 75:
                    raise RuntimeError('Research MCP probe failed; endpoints were not connected.')
                time.sleep(1)
            self.configure('connect')
            self.reload()
            self.admin('connected')
            print('Research services prepared and connected to Hermes.', flush=True)
        except (Exception, KeyboardInterrupt):
            self.configure('disconnect')
            if self.running('hermes'):
                self.client('reload', check=False)
            self.admin('activation-failed')
            raise

    def startup(self):
        try:
            state = self.inspect()
            if state['prepared']:
                self.activate()
            else:
                if self.running('x402_treazury'):
                    self.call('stop', '--timeout', '-1', 'x402_treazury')
                print('Research preparation pending: ' + state['reason'] + '\n'
                      'Use make x402_treazury-init, then make x402_treazury-prepare. Hermes is available.')
        except Exception as error:
            print('Hermes is available; research activation failed: ' + str(error), file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('init', 'status', 'prepare'))
    args = parser.parse_args()
    controller = Controller(compose(settings()))
    initialize_research_config(controller.command, ROOT)
    ensure_storage(controller.command)
    if args.action == 'status':
        controller.admin('status')
    else:
        with operation_lock(ROOT):
            if args.action == 'init':
                controller.initialize()
            else:
                controller.prepare()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, KeyboardInterrupt) as error:
        print(str(error) or 'Interrupted; wallet journals were retained.', file=sys.stderr)
        sys.exit(1)
