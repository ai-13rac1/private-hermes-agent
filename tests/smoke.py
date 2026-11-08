#!/usr/bin/env python3
"""Qualify actual Hermes SSH/Python execution and the isolated Compose topology.

Separate project, dummy teep key, no inference. Uses a disposable proxy health
endpoint, a real MCP client against an SSE fixture, and explicit forbidden peers.
"""
import json
import os
import subprocess
import time

COMPOSE = ['docker', 'compose', '-p', 'private-hermes-test', '-f', 'compose.yaml', '-f', 'tests/compose.yaml']


def compose(*args, check=True, **kwargs):
    return subprocess.run(COMPOSE + list(args), check=check, text=True, capture_output=True, **kwargs)


def execute(service, *args, user=None, check=True):
    options = ['exec', '-T']
    if user:
        options += ['--user', user]
    return compose(*options, service, *args, check=check)


def curl(service, url, check=True):
    return execute(service, 'curl', '--noproxy', '*', '-fsS', '--connect-timeout', '3', '--max-time', '35', url,
                   user='10000:10000' if service == 'executor' else None, check=check)


def python(service, code, check=True):
    interpreter = '/opt/hermes/.venv/bin/python' if service == 'hermes' else 'python3'
    return execute(service, interpreter, '-c', code, user='10000:10000' if service == 'executor' else None, check=check)


def eventually(operation, attempts=4):
    for attempt in range(attempts):
        try:
            return operation()
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            if attempt == attempts - 1:
                raise
            time.sleep(2)


def main():
    failed = True
    try:
        print('Starting isolated test stack...', flush=True)
        compose('up', '-d', '--no-build', '--wait', '--wait-timeout', '600')
        for service in ('hermes', 'executor'):
            response = eventually(lambda: json.loads(curl(service, 'https://check.torproject.org/api/ip').stdout))
            assert response['IsTor'] is True
        assert json.loads(curl('teep', 'https://check.torproject.org/api/ip').stdout)['IsTor'] is False
        assert json.loads(curl('hermes', 'http://10.203.83.3:8337/health').stdout)['status'] == 'ok'
        print('PASS: agent and executor use Tor; single-service teep uses direct egress', flush=True)

        # Prove the forbidden peer exists and listens: failure cannot be mistaken
        # for protection merely because the target service is absent.
        assert curl('fixture', 'http://127.0.0.1:111').stdout == 'ok'
        assert curl('fixture', 'http://127.0.0.1:8001').stdout == 'ok'
        python('fixture', "import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.settimeout(2); s.sendto(b'probe',('127.0.0.1',111)); assert s.recv(1024)==b'rpcbind-open'")
        for service in ('hermes', 'executor'):
            for host in ('10.203.80.10', '172.17.0.1', '192.168.65.1', '192.168.65.2', '192.168.65.254', '169.254.169.254'):
                assert curl(service, f'http://{host}:111', check=False).returncode != 0, (service, host)
            python(service, """import socket
for host in ('10.203.80.10', '172.17.0.1', '192.168.65.254'):
 s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.settimeout(.3)
 try:
  s.connect((host,111)); s.send(b'blocked'); s.recv(1024)
 except (TimeoutError, OSError): pass
 else: raise AssertionError('UDP reached prohibited peer')
 finally: s.close()
""")
            assert curl(service, 'http://[fd00::1]:111', check=False).returncode != 0
        for service in ('agent-net', 'executor-net'):
            rules = execute(service, 'iptables', '-L', 'OUTPUT', '-nvx').stdout
            assert any('DROP' in line and int(line.split()[0]) > 0 for line in rules.splitlines() if line.split() and line.split()[0].isdigit())
        assert curl('executor', 'http://10.203.83.3:8337/health', check=False).returncode != 0
        assert curl('executor', 'http://10.203.82.2:8642', check=False).returncode != 0
        print('PASS: host/VM, rpcbind TCP/UDP, IPv6, executor-to-agent and executor-to-teep blocked', flush=True)

        # The pinned known-host entry and readonly key are consumed by Hermes's
        # actual SSH backend, not a substitute SSH client or a local shell.
        terminal = python('hermes', """import json
from tools.terminal_tool import terminal_tool
result=json.loads(terminal_tool('id -u; printenv AGENT_ONLY_SENTINEL || echo absent', task_id='qualification'))
print(json.dumps(result))
assert '10000' in str(result) and 'absent' in str(result), result
assert 'must-not-reach-executor' not in str(result)
""")
        print(terminal.stdout.strip(), flush=True)
        result = python('hermes', """import json
from tools.code_execution_tool import execute_code
r=json.loads(execute_code("import os; print('REMOTE_EXECUTION', os.getuid()); print(os.path.exists('/run/agent-ssh/id_ed25519'))", task_id='qualification'))
print(json.dumps(r))
assert 'REMOTE_EXECUTION 10000' in str(r), r
assert 'False' in str(r), r
""")
        print(result.stdout.strip(), flush=True)
        python('executor', "import pathlib; c=pathlib.Path('/proc/self/status').read_text(); assert 'CapEff:\\t0000000000000000' in c")
        for service in ('hermes', 'executor'):
            python(service, """import socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.settimeout(.5)
try:
 s.sendto(bytes.fromhex('123401000001000000000000076578616d706c6503636f6d0000010001'),('127.0.0.11',53))
 s.recv(4096)
except (OSError, TimeoutError): pass
else: raise AssertionError('Docker embedded DNS bypass')
""")
        print('PASS: actual Hermes terminal and execute_code run remotely without agent keys; code has no capabilities; embedded DNS blocked', flush=True)

        # Actual MCP SDK initialize/list/call over streamed HTTP/SSE.
        python('hermes', """import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
async def main():
 async with streamable_http_client('http://10.203.84.10:8000/mcp') as (read,write,*_):
  async with ClientSession(read,write) as session:
   await session.initialize()
   tools=await session.list_tools()
   assert tools.tools[0].name=='echo'
   response=await session.call_tool('echo', {'text':'streaming-ok'})
   assert response.content[0].text=='streaming-ok'
asyncio.run(main())
""")
        assert curl('hermes', 'http://10.203.84.10:8001', check=False).returncode != 0
        assert curl('executor', 'http://10.203.84.10:8000', check=False).returncode != 0
        print('PASS: selected MCP streaming port works; unselected port and executor MCP access blocked', flush=True)

        compose('stop', 'tor')
        for service in ('hermes', 'executor'):
            assert curl(service, 'https://check.torproject.org/api/ip', check=False).returncode != 0
        curl('hermes', 'http://10.203.83.3:8337/health')
        curl('hermes', 'http://10.203.84.10:8000/health')
        print('PASS: Tor outage blocks public egress while local teep/MCP stay available', flush=True)
        failed = False
    except subprocess.CalledProcessError as error:
        print(error.stdout, error.stderr, flush=True)
        print(compose('logs', '--tail', '20', 'tor', 'agent-net', 'executor-net', 'executor', check=False).stdout)
        raise
    finally:
        if failed and os.getenv('KEEP_FAILED_TEST_STACK') == '1':
            print('Failed test stack retained for diagnosis: private-hermes-test', flush=True)
        else:
            compose('down', '--volumes', '--remove-orphans', check=False)


if __name__ == '__main__':
    main()
