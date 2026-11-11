"""Run inside disposable Hermes; exercise actual remote browser_exec, no inference."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import threading
import time

import model_tools
from tools import browser_use_cli as browser
from tools.bot_desktop import runtime, placement, lease
from tools.environments import streams
from tools.registry import registry
from hermes_cli import private_browser_use as remote


def decoded(value):
    return json.loads(value) if isinstance(value, str) else value


def run(code, name='fixture', **kw):
    result = decoded(browser.browser_exec(code, session=name, task_id='browser-fixture', **kw))
    assert not result.get('error'), result
    assert result.get('success', result.get('_multimodal')), result
    return result


assert browser.browser_exec_available()
assert registry.get_entry('browser_exec')
assert all(not registry.get_entry(n) for n in ('browser_cdp', 'browser_dialog', 'browser_vault'))
assert runtime.start().running
registered = decoded(registry.dispatch('browser_exec', {'code':'print("registry-remote")',
                                  'session':'registry-fixture'}, task_id='browser-fixture'))
assert registered.get('output','').strip() == 'registry-remote', registered
env = placement.terminal_environment()
native_screenshot = browser._native_screenshot_result
browser._native_screenshot_result = lambda *args: None  # Separate screenshot staging from provider choice.
server = streams.open_stream(env, ['python3', '-u', '-c', r'''
from http.server import BaseHTTPRequestHandler,HTTPServer
class Page(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200)
  self.send_header('Content-Type','text/html')
  self.end_headers()
  self.wfile.write(b'<title>executor-browser-fixture</title><input id="entry"><button onclick="document.title=document.querySelector(\'#entry\').value">save</button><a download="proof.txt" href="data:text/plain,executor-download">download</a>')
 def log_message(self,*args): pass
s=HTTPServer(('127.0.0.1',0),Page)
print(s.server_port,flush=True)
s.serve_forever()
'''])
port = int(server.stdout.readline())
try:
    result = run('import os,pathlib,subprocess,json\n'
                 'assert os.getuid()==10000\n'
                 'assert not any(k in os.environ for k in ["NEARAI_API_KEY","OPENAI_API_KEY","HERMES_HOME","BROWSER_USE_API_KEY"])\n'
                 'assert not pathlib.Path("/opt/hermes").exists()\n'
                 'assert not pathlib.Path("/opt/data").exists()\n'
                 'assert not pathlib.Path("/var/lib/x402").exists()\n'
                 'status=pathlib.Path("/proc/self/status").read_text()\n'
                 'assert "CapEff:\\t0000000000000000" in status and "CapPrm:\\t0000000000000000" in status\n'
                 'assert "NoNewPrivs:\\t1" in status\n'
                 'assert subprocess.check_output(["id","-u"]).strip()==b"10000"\n'
                 'pathlib.Path("python-marker").write_text("executor-python")\n'
                 'print("remote-only",os.getcwd())')
    assert 'remote-only' in result['output']
    workspace = result['workspace']
    assert not Path(workspace, 'python-marker').exists()
    assert streams.run_in(env, ['cat', workspace + '/python-marker']).stdout == b'executor-python'
    result = run(f'new_tab("http://127.0.0.1:{port}/")\nprint(page_info())')
    assert 'executor-browser-fixture' in result['output'], result
    filled = run('cdp("Target.activateTarget",targetId=current_tab()["targetId"])\nfill_input("#entry","typed-in-executor")\njs("document.querySelector(\'button\').click()")\nprint(js("JSON.stringify({title:document.title,value:document.querySelector(\'#entry\').value})"))')
    assert 'typed-in-executor' in filled['output'], filled
    title = run('print(js("document.title"))')
    assert 'typed-in-executor' in title['output'], title
    download = run('js("document.querySelector(\'a\').click()")\n'
                   'import time,pathlib,os\n'
                   'p=pathlib.Path(os.environ["BH_DOWNLOAD_DIR"])/"proof.txt"\n'
                   'for _ in range(50):\n'
                   ' if p.exists(): break\n'
                   ' time.sleep(.1)\n'
                   'assert p.read_text()=="executor-download"\nprint(str(p))')
    assert '/workspace/browser-use/downloads/proof.txt' in download['output'], download
    shot = run('print(capture_screenshot())')
    p = Path(shot['screenshot_path'])
    assert p.is_file() and p.read_bytes().startswith(b'\x89PNG'), shot
    assert '/cache/browser-use/screenshots/' in str(p)
    # Chromium's live absolute socket symlink must not break intended native
    # file sync. Its profile remains authoritative in the executor bind data.
    from hermes_constants import get_hermes_home
    synced = Path(get_hermes_home()) / 'cache' / 'documents' / 'browser-sync-fixture.txt'
    synced.parent.mkdir(parents=True, exist_ok=True)
    synced.write_text('initial fixture')
    env._sync_manager.sync(force=True)
    pairs = [(host, path) for host, path in env._sync_manager._get_files_fn() if host == str(synced)]
    assert len(pairs) == 1, pairs
    target = pairs[0][1]
    changed = streams.run_in(env, ['python3','-c',
                          'from pathlib import Path; import sys; Path(sys.argv[1]).write_text("changed in executor")', target])
    assert changed.returncode == 0, changed.stderr.decode()
    with tempfile.NamedTemporaryFile(suffix='.tar') as archive:
        env._ssh_bulk_download(Path(archive.name))
        with tarfile.open(archive.name) as data:
            names = data.getnames()
        assert not any('/bot-desktop/browser-profile' in name for name in names)
        assert target.lstrip('/') in names
    env._sync_manager.sync_back()
    assert synced.read_text() == 'changed in executor'
    env._sync_manager.sync(force=True)  # Acknowledge the pulled version before native exit cleanup.
    (p.parent.parent / 'fixture-artifacts.json').write_text(json.dumps({
        'screenshot': str(p), 'download': '/workspace/browser-use/downloads/proof.txt'}))
    assert run('print(js("document.title"))')['output'] == 'typed-in-executor\n'
    # Native named tabs are distinct, while their browser profile remains shared.
    run(f'new_tab("http://127.0.0.1:{port}/")', name='second')
    assert 'executor-browser-fixture' in run('print(js("document.title"))', name='second')['output']
    assert 'typed-in-executor' in run('print(js("document.title"))')['output']
    for task, name in [('unnamed-one', ''), ('unnamed-two', ''), ('literal-default', 'default')]:
        value = decoded(browser.browser_exec(f'new_tab("http://127.0.0.1:{port}/")\njs("document.title=\'{task}\'")',
                                            session=name, task_id=task))
        assert value.get('success'), value
    for task, name in [('unnamed-one', ''), ('unnamed-two', ''), ('literal-default', 'default')]:
        value = decoded(browser.browser_exec('print(js("document.title"))', session=name, task_id=task))
        assert task in value.get('output', ''), value
    # Cold calls for one identity serialize daemon creation and model execution.
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda n: run(f'print({n})', name='concurrent'), range(2)))
    assert {r['output'].strip() for r in results} == {'0', '1'}
    # A printed gateway-looking path is fetched from the executor, never read locally.
    canary = Path('/tmp/browser-agent-canary.png')
    canary.write_bytes(b'gateway-secret')
    output = run('print("/tmp/browser-agent-canary.png")')
    assert 'screenshot_path' not in output
    assert b'gateway-secret' not in json.dumps(output).encode()
    same_path = run('print(capture_screenshot("/tmp/browser-agent-canary.png"))')
    assert Path(same_path['screenshot_path']).read_bytes().startswith(b'\x89PNG'), same_path
    assert canary.read_bytes() == b'gateway-secret'
    run('from pathlib import Path\n'
        'Path("agent_helpers.py").write_text("def fixture_helper():\\n import os; return os.getuid()\\n")\n'
        'Path(".env").write_text("BU_CDP_WS=ws://10.203.83.3:8337\\nBH_TELEMETRY=1\\n")')
    daemon = run('from browser_harness import _ipc,admin\nprint(_ipc.pid_path(admin.NAME).read_text())', name='daemon-crash')
    raw = daemon['output'].strip()
    pid = json.loads(raw)['pid'] if raw.startswith('{') else int(raw)
    assert streams.run_in(env, ['kill', '-KILL', str(pid)]).returncode == 0
    helpers = run('import os\nassert fixture_helper()==10000\n'
                  'assert os.environ["BU_CDP_WS"].startswith("ws://127.0.0.1:")\n'
                  'assert os.environ["BH_TELEMETRY"]=="0"\nprint("remote-helpers")', name='daemon-crash')
    assert 'remote-helpers' in helpers['output']
    run('from pathlib import Path\nPath("agent_helpers.py").unlink()\nPath(".env").unlink()')
    from tools import vision_tools
    vision_tools._should_use_native_vision_fast_path = lambda: True
    browser._native_screenshot_result = native_screenshot
    attached = run('print(capture_screenshot())')
    assert attached.get('_multimodal'), attached
    assert attached['content'][1]['image_url']['url'].startswith('data:image/'), attached
    browser._native_screenshot_result = lambda *args: None
    traceback = decoded(browser.browser_exec('# first\n# second\nraise RuntimeError("fixture-trace")', session='trace'))
    assert traceback.get('exit_code') != 0 and 'line 3' in traceback.get('stderr',''), traceback
    lease.acquire('browser-fixture-human')
    denied = decoded(browser.browser_exec('raise AssertionError("must not run")', session='fixture'))
    assert denied.get('code') == 'human_has_control', denied
    lease.release('browser-fixture-human')
    # Native thread-scoped stop closes just this identity and reports uncertainty.
    from tools.interrupt import set_interrupt
    set_interrupt(True)
    try:
        denied = decoded(browser.browser_exec('import time; time.sleep(30)', session='cancelled', task_id='browser-fixture'))
        assert 'interrupted' in denied.get('error',''), denied
    finally:
        set_interrupt(False)
    assert run('print("retry-after-cancel")', name='cancelled')['output'].strip() == 'retry-after-cancel'
    worker = {}
    def active_call():
        worker['tid'] = threading.get_ident()
        return decoded(browser.browser_exec(
            'import subprocess,pathlib,time\n'
            'p=subprocess.Popen(["python3","-c","import time; time.sleep(30)"])\n'
            'pathlib.Path("/workspace/browser-active-child").write_text(str(p.pid))\n'
            'time.sleep(30)\npathlib.Path("/workspace/browser-cancel-failed").touch()',
            session='active-cancel', task_id='browser-fixture'))
    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        work = pool.submit(active_call)
        for _ in range(100):
            pid = streams.run_in(env, ['cat', '/workspace/browser-active-child'], timeout=10)
            if pid.returncode == 0:
                break
            time.sleep(.1)
        else:
            raise AssertionError('Active browser child did not start')
        key = browser._backend_cache_key('browser-fixture', 'active-cancel', sidecar=True)
        owner = remote._sessions[key].process
        set_interrupt(True, thread_id=worker['tid'])
        try:
            stopped = work.result(timeout=20)
            assert 'interrupted' in stopped.get('error',''), stopped
            owner.wait(timeout=20)
            probe = streams.run_in(env, ['python3', '-c',
                'from pathlib import Path; p=Path("/proc/' + pid.stdout.decode().strip() + '/status"); '
                'assert not p.exists() or "State:\\tZ" in p.read_text(); '
                'assert not Path("/workspace/browser-cancel-failed").exists()'])
            assert probe.returncode == 0, probe.stderr.decode()
        finally:
            set_interrupt(False, thread_id=worker['tid'])
    assert 'typed-in-executor' in run('print(js("document.title"))')['output']
    # Native timeout likewise stops the affected session; completed workspace files survive.
    timed = decoded(browser.browser_exec('import time; time.sleep(30)', session='timeout', timeout_s=5))
    assert 'timed out' in timed.get('error',''), timed
    retry = decoded(browser.browser_exec('print("retry-after-timeout")', session='timeout'))
    assert retry.get('output','').strip() == 'retry-after-timeout', retry
    # Explicit unsupported settings fail before any model code or external route.
    from tools import browser_session_cloud
    section = browser_session_cloud.browser_section
    try:
        for setting in ({'cloud_provider':'browser-use'}, {'engine':'lightpanda'},
                        {'use_real_profile':True}, {'cdp_url':'http://10.203.83.3:8337'}):
            browser_session_cloud.browser_section = lambda: {**section(), **setting}
            refused = decoded(browser.browser_exec('raise AssertionError("must not execute")'))
            assert refused.get('error') and 'executor Chromium' in refused['error'], refused
    finally:
        browser_session_cloud.browser_section = section
    network = run('import urllib.request,json,socket\n'
                  'assert json.load(urllib.request.urlopen("https://check.torproject.org/api/ip",timeout=90))["IsTor"]\n'
                  'for address in [("10.203.83.3",8337),("10.203.85.2",80),("192.168.65.2",80),("169.254.169.254",80)]:\n'
                  ' s=socket.socket(); s.settimeout(1)\n'
                  ' try: s.connect(address)\n'
                  ' except OSError: pass\n'
                  ' else: raise AssertionError(address)\n'
                  ' finally: s.close()\n'
                  'print("tor-only")', name='network')
    assert 'tor-only' in network['output'], network
    # Exercise EOF specifically while real native daemon startup is pending.
    # A fixture-only rendezvous delays startup; production has no such hook.
    child_env = json.loads(run('import os,json\nprint(json.dumps(dict(os.environ)))')['output'])
    for key, suffix in [('BH_HOME',''), ('BH_CONFIG_DIR',''), ('BH_RUNTIME_DIR','/r'), ('BH_TMP_DIR','/t')]:
        child_env[key] = '/tmp/bh/startup-cancel' + suffix
    child_env['BU_NAME'] = 'startup-cancel'
    delayed = '''import runpy,time
from pathlib import Path
from browser_harness import admin
start=admin.ensure_daemon
def delayed():
 Path('/workspace/browser-startup-entered').touch()
 while not Path('/workspace/browser-startup-continue').exists(): time.sleep(.05)
 start()
admin.ensure_daemon=delayed
runpy.run_path('/opt/private-hermes/browser-session.py',run_name='__main__')
'''
    owner = streams.open_stream(env, ['env', '-i', *(k+'='+v for k,v in child_env.items()),
                                '/opt/browser-harness/bin/python', '-u', '-c', delayed])
    owner.stdin.write((json.dumps({'code':'from pathlib import Path; Path("/workspace/browser-startup-code-ran").touch()',
                                  'timeout':30})+'\n').encode())
    owner.stdin.flush()
    for _ in range(100):
        entered = streams.run_in(env, ['test','-f','/workspace/browser-startup-entered'])
        if entered.returncode == 0:
            break
        time.sleep(.1)
    else:
        raise AssertionError('Startup cancellation rendezvous not reached')
    owner.stdin.close()
    assert streams.run_in(env, ['touch','/workspace/browser-startup-continue']).returncode == 0
    owner.wait(timeout=90)
    startup = json.loads(owner.stdout.readline())
    assert 'not launched' in startup.get('error',''), startup
    assert streams.run_in(env, ['test','!','-e','/workspace/browser-startup-code-ran']).returncode == 0
    # Abrupt gateway-worker death closes SSH via the native owner-death supervisor.
    program = ('import json,os; from tools.browser_use_cli import browser_exec; '
               'r=browser_exec(' + repr('import os,json\nfrom browser_harness import _ipc,admin\n'
                   'raw=_ipc.pid_path(admin.NAME).read_text()\n'
                   'pid=json.loads(raw)["pid"] if raw.startswith("{") else int(raw)\n'
                   'print(json.dumps({"owner":os.getppid(),"daemon":pid}))') +
               ',session="owner-death",task_id="owner-death"); '
               'print(r,flush=True); os._exit(0)')
    result = subprocess.run([sys.executable, '-c', program], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stderr
    identities = json.loads(json.loads(result.stdout)['output'])
    for _ in range(100):
        gone = streams.run_in(env, ['python3', '-c',
            'from pathlib import Path; ids=' + repr(list(identities.values())) + '; '
            'assert all(not (p:=Path(f"/proc/{i}/status")).exists() or "State:\\tZ" in p.read_text() for i in ids)'])
        if gone.returncode == 0:
            break
        time.sleep(.1)
    else:
        raise AssertionError('Remote owner/daemon survived gateway owner death')
    # Native cleanup tears down the corresponding persistent SSH/harness owner.
    key = browser._backend_cache_key('browser-fixture', 'fixture', sidecar=True)
    owner = remote._sessions[key].process
    from tools.browser_session_lifecycle import cleanup_single_session
    cleanup_single_session(key)
    owner.wait(timeout=20)
    assert key not in remote._sessions
    print('PASS: remote Python/child placement, Chromium DOM/type/download/capture, named/unnamed sessions, concurrent startup, '
          'screenshot staging/vision, native cache sync, takeover, active/startup cancellation, timeout/retry, daemon crash, '
          'owner death, Tor/forbidden paths and native cleanup')
finally:
    lease.release('browser-fixture-human')
    remote.close()
    server.kill()
    server.wait()
