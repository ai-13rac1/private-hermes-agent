#!/usr/bin/env python3
"""Disposable Podman-default desktop qualification; production guard is unchanged."""
import argparse
import json
import os
import subprocess
import sys
import uuid
import smoke

from deployment import check_engine, compose_base, compose_files, engine, engine_command

OVERLAY = 'tests/podman-desktop-compose.yaml'
IMAGE = 'private-hermes-executor-podman-desktop-trial:local'


def trial_compose(funnel=False, webapp=False):
    files = ['tests/compose.yaml']
    if webapp:
        files.append('tests/webapp-compose.yaml')
    files.append(OVERLAY)
    project = 'private-hermes-webapp-test' if webapp else 'private-hermes-test'
    return [*compose_base(), '-p', project, *compose_files(funnel, extra=files)]


def sandbox():
    """Use the exact desktop image, with no host state or external networking."""
    name = 'private-hermes-podman-sandbox-' + uuid.uuid4().hex[:12]
    code = r'''import glob,json,os,pathlib,re,socket,subprocess
status=dict(line.split(':',1) for line in pathlib.Path('/proc/self/status').read_text().splitlines() if ':' in line)
assert os.getuid()==10000
assert all(int(status[key].strip(),16)==0 for key in ('CapEff','CapPrm','CapInh','CapAmb'))
assert int(status['CapBnd'].strip(),16)==0x400c0, status['CapBnd']
assert status['NoNewPrivs'].strip()=='1' and status['Seccomp'].strip()=='2'
for directory in ('/tmp/home','/tmp/runtime'):
 pathlib.Path(directory).mkdir(mode=0o700,exist_ok=True)
chrome=glob.glob('/opt/playwright/chromium-*/chrome-linux*/chrome')[0]
result=subprocess.run([chrome,'--headless','--disable-gpu','--no-first-run',
 '--disable-background-networking','--allow-chrome-scheme-url',
 '--user-data-dir=/tmp/chromium-profile','--dump-dom','chrome://sandbox'],capture_output=True,text=True)
assert result.returncode==0,result.stderr[-5000:]
text=re.sub('<[^>]*>',' ',result.stdout)
assert re.search(r'Layer 1 Sandbox\s+Namespace',text),text[-4000:]
for layer in ('PID namespaces','Network namespaces','Seccomp-BPF sandbox'):
 assert re.search(re.escape(layer)+r'\s+Yes',text),text[-4000:]
print('PASS: Chromium namespace, PID/network namespace and seccomp-BPF sandbox diagnostics',flush=True)
probe="""import os,socket
fd=os.open('/proc/self/ns/net',os.O_RDONLY)
try: os.setns(fd,0)
except PermissionError: pass
else: raise AssertionError('joined parent network namespace')
try: socket.socket(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_TCP)
except PermissionError: pass
else: raise AssertionError('raw socket in parent network namespace')
"""
result=subprocess.run(['unshare','-Ur','python3','-c',probe],capture_output=True,text=True)
assert result.returncode==0,result.stderr[-2000:]
print('PASS: user-namespace root cannot join or create raw sockets in parent namespace',flush=True)
print(json.dumps({'chromium':subprocess.check_output([chrome,'--version'],text=True).strip(),
 'uid':os.getuid(),'capabilities':status['CapEff'].strip(),'seccomp':status['Seccomp'].strip(),
 'no_new_privileges':status['NoNewPrivs'].strip()}),flush=True)
'''
    identifier = None
    try:
        identifier = subprocess.check_output([*engine_command(), 'create', '--name', name,
            '--network', 'none', '--cap-drop', 'ALL',
            '--cap-add', 'SETUID', '--cap-add', 'SETGID', '--cap-add', 'SYS_CHROOT',
            '--security-opt', 'no-new-privileges=true', '--read-only',
            '--tmpfs', '/tmp:mode=1777,notmpcopyup', '--tmpfs', '/run:mode=0755,notmpcopyup',
            '-e', 'HOME=/tmp/home', '-e', 'XDG_RUNTIME_DIR=/tmp/runtime',
            '--entrypoint', 'setpriv', IMAGE, '--reuid=10000', '--regid=10000',
            '--clear-groups', 'python3', '-c', code], text=True).strip()
        inspection = json.loads(subprocess.check_output([*engine_command(), 'inspect', identifier], text=True))[0]
        options = inspection['HostConfig'].get('SecurityOpt') or []
        assert not any(option.startswith('seccomp=') for option in options), options
        assert inspection['HostConfig']['NetworkMode'] == 'none'
        info = json.loads(subprocess.check_output([*engine_command(), 'info', '--format', 'json'], text=True))
        security = info['host']['security']
        assert security['seccompEnabled'] and security['seccompProfilePath'] != 'unconfined', security
        print('Native default policy:', security['seccompProfilePath'], flush=True)
        subprocess.run([*engine_command(), 'start', '--attach', identifier], check=True)
        state = json.loads(subprocess.check_output([*engine_command(), 'inspect', identifier], text=True))[0]['State']
        assert state['ExitCode'] == 0, state
    finally:
        if identifier:
            cleanup = subprocess.run([*engine_command(), 'rm', '--force', '--volumes', identifier],
                                     capture_output=True, text=True)
            if cleanup.returncode:
                print('Sandbox cleanup failed:', cleanup.stderr, file=sys.stderr, flush=True)
                if sys.exc_info()[0] is None:
                    cleanup.check_returncode()


def main():
    if engine() != 'podman':
        raise SystemExit('This experimental qualification requires CONTAINER_ENGINE=podman.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('sandbox', 'core', 'browser', 'webapp'), nargs='?', default='sandbox')
    phase = parser.parse_args().phase
    check_engine()
    os.environ['COMPUTER_USE_ENABLED'] = 'true'
    # Standalone build/model rendering needs no disposable storage mounts.
    smoke.COMPOSE = [*compose_base(), '-p', 'private-hermes-test',
                     *compose_files(False, extra=(OVERLAY,))]
    model = json.loads(smoke.compose('config', '--format', 'json').stdout)
    executor = model['services']['executor']
    assert executor['image'] == IMAGE
    assert executor['security_opt'] == ['no-new-privileges:true'], executor['security_opt']
    assert executor['cap_drop'] == ['ALL']
    assert set(executor['cap_add']) == {'SETUID','SETGID','SYS_CHROOT'}
    subprocess.run([*smoke.COMPOSE, 'build', 'executor'], check=True)
    if phase == 'sandbox':
        sandbox()
    elif phase == 'core':
        smoke.COMPOSE = trial_compose()
        smoke.main()
    elif phase == 'browser':
        import browser_use_smoke
        smoke.COMPOSE = trial_compose()
        with smoke.storage_fixture():
            failed = True
            try:
                smoke.start_stack()
                browser_use_smoke.check()
                browser_use_smoke.missing_harness()
                failed = False
            finally:
                if failed and os.environ.get('KEEP_FAILED_TEST_STACK') == '1':
                    print('Retained disposable browser stack: private-hermes-test', flush=True)
                else:
                    smoke.compose('down', '--volumes', '--remove-orphans', check=False)
    else:
        import webapp_smoke  # Imports set COMPOSE; select the trial after that.
        smoke.COMPOSE = trial_compose(funnel=True, webapp=True)
        sys.argv.append('--browser-only')
        webapp_smoke.main()


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(error.stdout or '', error.stderr or '', flush=True)
        raise
