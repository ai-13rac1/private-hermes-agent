#!/usr/bin/env python3
"""Test the real x402 MCP server and its secrets/network boundary; no paid calls."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import smoke

sys.path.insert(0, str(Path(__file__).parents[1] / 'docker'))
from research_endpoints import ADDRESS, ENDPOINTS

smoke.COMPOSE = ['docker', 'compose', '-p', 'private-hermes-research-test',
                 '-f', 'compose.yaml', '-f', 'tests/compose.yaml']


def main():
    failed = True
    try:
        print('Validating the production research configuration offline...', flush=True)
        command = ['docker', 'run', '--rm', '--network', 'none', 'private-hermes-research:local']
        production = json.loads(subprocess.check_output(command + ['config', 'show'], text=True))
        assert set(production['servers']) == set(ENDPOINTS)
        identity = json.loads(subprocess.check_output(command + ['build-info'], text=True))
        assert identity['source_revision'] == 'e1420b6364726e0c1a9d69dda72a15d8253a2b8b'
        assert identity['source_dirty'] is False
        print('PASS: pinned release identity and production research config validated without wallet/catalog I/O', flush=True)
        smoke.compose('up', '-d', '--no-build', '--wait', '--wait-timeout', '600')
        # No new readiness policy in production: just allow test listeners to
        # finish startup, reporting server failure rather than making paid probes.
        for attempt in range(30):
            ready = smoke.python('hermes', """import socket
for port in range(3010,3022):
 with socket.create_connection(('127.0.0.1',port),timeout=1): pass
""", check=False)
            if ready.returncode == 0:
                break
            if attempt == 29:
                raise RuntimeError('Research test listeners failed to start')
            time.sleep(1)

        # Native Hermes configuration and its dynamic bearer placeholders.
        smoke.python('hermes', """from hermes_cli.config import load_config, load_env
c=load_config(); env=load_env()
assert env.get('X402_TREAZURY_MCP_TOKEN')
for name,port in zip(('web','science','health','social','business','finance','property','security','world','travel','toolbox','shopping'),range(3010,3022)):
 entry=c['mcp_servers']['research_'+name]
 assert entry['url']==f'http://127.0.0.1:{port}/mcp'
assert c['terminal']['backend']=='ssh'
""")
        smoke.python('hermes', """import asyncio, json
from hermes_cli.config import load_env
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client, create_mcp_http_client
async def main():
 token=load_env()['X402_TREAZURY_MCP_TOKEN']
 for port in range(3010,3022):
  async with create_mcp_http_client(headers={'Authorization':'Bearer '+token}) as client:
   async with streamable_http_client(f'http://127.0.0.1:{port}/mcp',http_client=client) as (read,write):
    async with ClientSession(read,write) as session:
     await session.initialize()
     tools=await session.list_tools()
     assert tools.tools
     if port==3010:
      assert len(tools.tools)==1
      tool=tools.tools[0]
      response=await session.call_tool(tool.name,{})
      payload=''.join(getattr(c,'text','') for c in response.content)
      assert not response.is_error, payload
      assert '\"IsTor\":true' in ''.join(payload.split()), payload
asyncio.run(main())
""")
        print('PASS: authenticated initialize/list on all 12 real MCP listeners; free Rust API call exits through Tor', flush=True)

        smoke.python('hermes', """import urllib.request, urllib.error
for port in range(3010,3022):
 try: urllib.request.urlopen(f'http://127.0.0.1:{port}/mcp')
 except urllib.error.HTTPError as e: assert e.code==401
 else: raise AssertionError('Unauthenticated MCP request accepted')
""")
        smoke.python('executor', """import os, pathlib, socket
assert not os.getenv('X402_TREAZURY_MCP_TOKEN')
for path in ('/opt/data/.env','/run/research-auth/token','/var/lib/x402/state','/home/runner/.hermes/.env'):
 assert not pathlib.Path(path).exists(), path
for host in ('127.0.0.1','10.203.80.2','10.203.82.2'):
 for port in (3010,3021):
  try: s=socket.create_connection((host,port),timeout=.5)
  except OSError: pass
  else: s.close(); raise AssertionError('Executor reached a research MCP listener')
""")
        smoke.python('hermes', """import json
from tools.code_execution_tool import execute_code
r=json.loads(execute_code('''import os, pathlib, hermes_tools
assert not os.getenv("X402_TREAZURY_MCP_TOKEN")
assert not pathlib.Path("/opt/data/.env").exists()
r=hermes_tools._call("mcp_research_toolbox_raw_call",{})
assert "not available" in str(r), r
print("MCP_RPC_DENIED")''',task_id='research-isolation'))
assert 'MCP_RPC_DENIED' in str(r), r
""")
        smoke.python('hermes', """import pathlib, socket
assert not pathlib.Path('/run/research-auth/token').exists()
assert not pathlib.Path('/var/lib/x402/state').exists()
try: socket.socket(socket.AF_UNIX).connect('/run/tor-research/socks')
except OSError: pass
else: raise AssertionError('Agent gained the research Tor socket mount')
""")
        # Verify no SSH channel can turn the connection into an MCP tunnel.
        policy = smoke.execute('executor', '/usr/sbin/sshd', '-T').stdout
        assert 'allowtcpforwarding no' in policy
        assert 'permittunnel no' in policy
        print('PASS: unauthenticated access and code RPC denied; executor lacks secrets, wallet mounts and MCP network access', flush=True)
        smoke.compose('stop', 'tor')
        smoke.python('research-desk', """import socket
try: socket.socket(socket.AF_UNIX).connect('/run/tor-research/socks')
except OSError: pass
else: raise AssertionError('Stopped Tor still accepted a SOCKS connection')
""")
        assert smoke.curl('hermes', 'https://check.torproject.org/api/ip', check=False).returncode != 0
        assert json.loads(smoke.curl('hermes', 'http://10.203.83.3:8337/health').stdout)['status']=='ok'
        failed = False
        print('PASS: Tor outage has no direct fallback; local inference remains available', flush=True)
    except Exception as error:
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stdout, error.stderr, flush=True)
        print(smoke.compose('logs','--tail','25','research-desk','research-setup','tor',check=False).stdout, flush=True)
        raise
    finally:
        if failed and os.getenv('KEEP_FAILED_TEST_STACK') == '1':
            print('Retained test project: private-hermes-research-test', flush=True)
        else:
            smoke.compose('down','--volumes','--remove-orphans',check=False)


if __name__ == '__main__':
    main()
