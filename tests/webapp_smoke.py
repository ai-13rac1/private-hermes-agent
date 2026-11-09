#!/usr/bin/env python3
"""Pinned-image ingress qualification; simulated TLS, no Funnel enrollment or inference."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import smoke

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'components/webapp'))
from auth import hash_password
from settings import Settings, proxy_config

PROJECT = 'private-hermes-webapp-test'
smoke.COMPOSE = ['docker', 'compose', '-p', PROJECT, '-f', 'compose.yaml',
                 '-f', 'compose.funnel.yaml',
                 '-f', 'tests/compose.yaml', '-f', 'tests/webapp-compose.yaml']


def http(path, headers=None, data=None):
    try:
        response = urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:19120' + path,
                                          headers=headers or {}, data=data), timeout=3)
        return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def wait_ready():
    for attempt in range(120):
        try:
            if http('/login')[0] == 200:
                return
        except OSError:
            pass
        time.sleep(1)
    raise RuntimeError('Native gateway webapp did not become ready')


def browser_checks(password_path, mode="full"):
    browser_python = os.environ.get('WEBAPP_BROWSER_PYTHON', sys.executable)
    if not Path(browser_python).is_file():
        raise RuntimeError('Set WEBAPP_BROWSER_PYTHON to a Python environment with Playwright and Chromium; see docs/webapp.md')
    subprocess.run([browser_python, str(ROOT / 'tests/webapp_browser.py'), str(password_path), mode], check=True)


def run_suite():
    browser_python = os.environ.get('WEBAPP_BROWSER_PYTHON', sys.executable)
    ready = subprocess.run([browser_python, '-c',
        'from pathlib import Path; from playwright.sync_api import sync_playwright; '        'p=sync_playwright().start(); assert Path(p.chromium.executable_path).is_file(); p.stop()'],
        capture_output=True)
    if ready.returncode:
        raise RuntimeError('Install tests/requirements-browser.txt and Chromium, then set WEBAPP_BROWSER_PYTHON; see docs/webapp.md')
    failed = True
    with tempfile.TemporaryDirectory(prefix='private-hermes-ingress-') as directory:
        folder = Path(directory)
        # Only disposable credentials enter this project, never operator auth files.
        password = secrets.token_urlsafe(32)
        auth = {'password_hash': hash_password(password), 'secret': secrets.token_urlsafe(48)}
        (folder / 'auth.json').write_text(json.dumps(auth))
        (folder / 'password').write_text(password)
        values = dict(funnel_enabled='true', webapp_bind='127.0.0.1',
                      webapp_port='19120', webapp_username='admin', funnel_host='webapp-test.example.ts.net',
                      funnel_port='10000', tailscale_hostname='private-hermes')
        (folder / 'proxy.cfg').write_text(proxy_config(Settings.read(values)))
        tls = folder / 'tls'
        tls.mkdir()
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-keyout', str(tls / 'key.pem'), '-out', str(tls / 'cert.pem'),
                        '-subj', '/CN=webapp-test.example.ts.net', '-addext',
                        'subjectAltName=DNS:webapp-test.example.ts.net'], check=True, capture_output=True)
        (tls / 'key.pem').chmod(0o644)  # disposable fixture key; readable by unprivileged TLS server
        os.environ.update(WEBAPP_PORT='19120', WEBAPP_USERNAME='admin',
                          TAILSCALE_FUNNEL_ENABLED='true', TAILSCALE_FUNNEL_HOST='webapp-test.example.ts.net',
                          TAILSCALE_FUNNEL_PORT='10000', TS_AUTHKEY='',
                          WEBAPP_TEST_AUTH=str(folder / 'auth.json'), WEBAPP_TEST_PROXY=str(folder / 'proxy.cfg'),
                          WEBAPP_TEST_TLS=str(tls))
        try:
            print('Starting real pinned Hermes with local and simulated HTTPS ingress...', flush=True)
            smoke.compose('down', '--volumes', '--remove-orphans')
            smoke.compose('up', '-d', '--no-build', '--wait', '--wait-timeout', '600')
            assert not smoke.compose('ps', '-q', 'tailscale').stdout.strip(), 'Real Tailscale must never start in tests'
            wait_ready()
            assert not smoke.compose('ps', '-q', 'x402_treazury').stdout.strip(), 'Unprepared research service must not start'
            smoke.python('hermes', "from hermes_cli.config import load_config,load_env; assert not any(k.startswith('x402_treazury_') for k in load_config().get('mcp_servers',{})); assert not load_env().get('X402_TREAZURY_MCP_TOKEN')")
            print('PASS: fresh authenticated Hermes webapp starts without wallet or research MCP registration', flush=True)
            smoke.compose('exec', '-T', '--user', '10005:10005', 'webapp-proxy', 'python3', '-c', """import pathlib,socket
status=dict(line.split(':',1) for line in pathlib.Path('/proc/1/status').read_text().splitlines() if ':' in line)
assert set(status['Uid'].split())=={'10005'}, status['Uid']
for key in ('CapInh','CapPrm','CapEff','CapBnd','CapAmb'):
 assert int(status[key].strip(),16)==0, (key,status[key])
with socket.create_connection(('10.203.85.2',9120),timeout=2): pass
for host,port in (('10.203.85.2',22),('10.203.87.2',10000),('10.203.83.3',8337),('10.203.82.3',2222),('1.1.1.1',443),('192.168.1.1',80),('169.254.169.254',80)):
 try: socket.create_connection((host,port),timeout=.4)
 except OSError: pass
 else: raise AssertionError(('Proxy escaped fixed backend',host,port))
""")
            # Probe from the Funnel side: only its HTTPS-semantics listener is reachable.
            smoke.python('tls-fixture', """import socket
with socket.create_connection(('10.203.87.3',8443),timeout=2): pass
try: socket.create_connection(('10.203.87.3',19120),timeout=.4)
except OSError: pass
else: raise AssertionError('Funnel reached localhost frontend')
""")
            smoke.compose('restart', 'webapp-proxy')
            wait_ready()
            print('PASS: consolidated proxy drops all capabilities; fixed-backend egress and separate local/Funnel listeners survive restart', flush=True)
            for path in ('/api/config', '/api/fs/list?path=/workspace', '/api/fs/read-text?path=/workspace/test.txt',
                         '/api/fs/download?path=/workspace/test.txt', '/api/webapp/socket-ticket?socket=host-terminal'):
                code, _ = http(path)
                assert code in (401, 403), (path, code)
            for host in ('attacker.invalid', 'localhost:1', 'localhost:19120.attacker.invalid'):
                assert http('/login', headers={'Host': host})[0] == 421, host
            print('PASS: real native auth guards API/file/ticket routes; exact Host enforcement rejects forged authorities', flush=True)
            browser_checks(folder / 'password')
            smoke.compose('restart', 'hermes')
            wait_ready()
            browser_checks(folder / 'password', 'restart')
            password = secrets.token_urlsafe(32)
            auth = {'password_hash': hash_password(password), 'secret': secrets.token_urlsafe(48)}
            (folder / 'auth.json').write_text(json.dumps(auth))
            (folder / 'password').write_text(password)
            smoke.compose('run', '--rm', 'setup')
            smoke.compose('restart', 'hermes')
            wait_ready()
            browser_checks(folder / 'password', 'rotation')
            smoke.python('hermes', "from pathlib import Path; assert Path('/tmp/webapp-browser-proof').read_text().strip()=='browser-terminal'")
            smoke.python('executor', "from pathlib import Path; assert not Path('/tmp/webapp-browser-proof').exists(); assert Path('/workspace/webapp-browser-file.txt').read_text()=='browser file proof'")
            smoke.python('executor', """import pathlib,socket
for path in ('/run/webapp/auth.json','/opt/data/config.yaml','/run/tailscale/tailscaled.sock'):
 assert not pathlib.Path(path).exists(),path
for host,port in (('10.203.85.2',9120),('10.203.85.3',8080),('10.203.85.3',19120),('10.203.87.3',8443)):
 try: socket.create_connection((host,port),timeout=.5)
 except OSError: pass
 else: raise AssertionError('Executor reached private ingress')
""")
            print('PASS: browser terminal executes in agent container; file API uses SSH; executor cannot reach private ingress or credentials', flush=True)
            # Financial preparation is represented by a controlled result here;
            # serving is the real unfunded Rust fixture, with native Hermes RPC.
            sys.path.insert(0, str(ROOT / 'scripts'))
            from x402_treazury import Controller
            controller = Controller(smoke.COMPOSE)
            # Exercise detached runner exit-status/cleanup with a genuinely
            # absent wallet: production preparation must fail before funding.
            try:
                controller.wallet_command('prepare')
            except RuntimeError as error:
                assert 'exit 1' in str(error), error
            else:
                raise AssertionError('Missing wallet did not stop preparation')
            assert http('/login')[0] == 200
            print('PASS: detached preparation reports failure and cleans up without touching a wallet or stopping Hermes', flush=True)
            # An unrelated MCP entry must survive activation and disconnection.
            smoke.compose('run', '--rm', '-T', '--no-deps', '--entrypoint', '/opt/hermes/.venv/bin/python',
                          'setup', '-c',
                          "from pathlib import Path; import hermes_yaml as yaml; p=Path('/opt/data/config.yaml'); c=yaml.safe_load(p.read_text()); c.setdefault('mcp_servers',{})['unrelated']={'url':'http://10.203.84.10:8000/mcp'}; p.write_text(yaml.safe_dump(c,sort_keys=False))")
            controller.inspect = lambda: {'prepared': True}
            controller.activate()
            smoke.python('hermes', "from hermes_cli.config import load_config; assert len([k for k in load_config()['mcp_servers'] if k.startswith('x402_treazury_')])==12")
            controller.disconnect()
            smoke.compose('stop', '--timeout', '-1', 'x402_treazury')
            smoke.python('hermes', "from hermes_cli.config import load_config; assert not any(k.startswith('x402_treazury_') for k in load_config()['mcp_servers']); assert load_config()['mcp_servers']['unrelated']['url']=='http://10.203.84.10:8000/mcp'")
            assert http('/login')[0] == 200
            print('PASS: staged fixture activation probes twelve real MCP endpoints and reloads/disconnects native Hermes without restarting it', flush=True)
            # A missing provider must fail startup instead of serving an unguarded UI.
            smoke.python('hermes', """from hermes_cli.web_server import app, _configure_auth_gate
from hermes_cli.dashboard_auth import clear_providers
clear_providers()
try: _configure_auth_gate('0.0.0.0',False,None,None)
except SystemExit: pass
else: raise AssertionError('Missing authentication provider did not refuse startup')
""")
            # Invalid credentials must never replace the authenticated profile.
            (folder / 'auth.json').write_text('{}')
            result = smoke.compose('run', '--rm', 'setup', check=False)
            assert result.returncode != 0, 'Invalid credentials were accepted'
            smoke.python('hermes', "from hermes_cli.config import load_config; assert load_config()['webapp']['enabled'] is True")
            smoke.compose('stop','webapp-proxy')
            try:
                http('/login')
            except OSError:
                pass
            else:
                raise AssertionError('Stopped ingress remained reachable')
            print('PASS: invalid credentials refuse provisioning; stopping ingress closes local access; no real Tailscale node was enrolled', flush=True)
            failed = False
        except subprocess.CalledProcessError as error:
            # Logs may include gateway metadata, but test credentials are never printed.
            print((error.stdout or '')[-4000:], (error.stderr or '')[-4000:], flush=True)
            print(smoke.compose('logs','--tail','12','hermes','webapp-proxy','setup','tls-fixture',check=False).stdout, flush=True)
            raise
        finally:
            if failed and os.getenv('KEEP_FAILED_TEST_STACK') == '1':
                print('Retained disposable ingress project; fixture files are under ' + directory, flush=True)
                # Preserve files while debugging; no operator secrets are present.
                import shutil
                shutil.copytree(folder, Path('/tmp/private-hermes-ingress-debug'), dirs_exist_ok=True)
            else:
                smoke.compose('down','--volumes','--remove-orphans',check=False)


def main():
    with smoke.storage_fixture():
        run_suite()


if __name__ == '__main__':
    main()
