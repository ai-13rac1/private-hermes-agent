#!/usr/bin/env python3
"""Exercise editable policy with the real image, offline and unfunded."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from provisioning import initialize_research_config


def docker(*args, check=True):
    return subprocess.run(['docker', *args], check=check, capture_output=True, text=True)


def main():
    identity = 'private-hermes-config-test-' + uuid.uuid4().hex
    image = 'private-hermes-x402_treazury:local'
    with tempfile.TemporaryDirectory(prefix=identity) as folder:
        root = Path(folder)
        initialize_research_config(['docker', 'compose', '-f', 'compose.yaml'], root)
        directory = root / 'config/x402_treazury'
        path = directory / 'research_desk.toml'
        original = path.read_text()
        docker('volume', 'create', identity)
        try:
            docker('run', '--rm', '--network', 'none', '--user', '0:0',
                   '--mount', f'type=volume,src={identity},dst=/var/lib/x402',
                   '--entrypoint', 'chown', image, '10003:10003', '/var/lib/x402')
            docker('run', '-d', '--name', identity, '--network', 'none', '--read-only',
                   '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
                   '--tmpfs', '/tmp:mode=1777',
                   '--mount', f'type=volume,src={identity},dst=/var/lib/x402',
                   '--mount', f'type=bind,src={directory},dst=/opt/x402/examples/deployments,readonly',
                   '--entrypoint', 'sleep', image, 'infinity')

            def execute(*args, check=True):
                return docker('exec', identity, *args, check=check)

            def inspect():
                return json.loads(execute('python3', '/opt/onboarding.py', 'inspect').stdout)

            def policy():
                return json.loads(execute('x402_treazury', 'config', 'show').stdout)

            def publish(text):
                temporary = directory / 'edited.toml'
                temporary.write_text(text)
                temporary.chmod(0o644)
                temporary.replace(path)

            assert policy()['servers']['web']['wallet'] == 'general'
            denied = execute('python3', '-c', "from pathlib import Path; Path('/opt/x402/examples/deployments/research_desk.toml').write_text('bad')", check=False)
            assert denied.returncode and 'Read-only file system' in denied.stderr
            assert inspect()['wallet_absent']
            execute('x402_treazury', 'wallet', 'init', '--birthday', '1', '--json')
            assert not inspect()['prepared']
            # Controlled completion represents historical preparation only. No
            # bootstrap, warm, serve, funded operations or network run here.
            execute('python3', '-c', "import sys; sys.path.insert(0,'/opt'); import onboarding as o; c,b,f=o.context(); o.write_record({'schema':1,'treasury_id':o.wallet(c),'fingerprint':f,'completed':['bootstrap','catalogs']})")
            assert inspect()['prepared']
            changed = original.replace('wallets.general', 'wallets.research').replace('wallet = "general"', 'wallet = "research"')
            publish(changed)
            assert policy()['servers']['web']['wallet'] == 'research'
            assert inspect()['prepared']
            preview = json.loads(execute('x402_treazury', 'wallet', 'preview', '--json').stdout)
            assert 'research' in preview['managed'] and 'general' not in preview['managed']
            # The native rename route is offline and reaches the same store;
            # wallet init creates no saved managed groups, so source is absent.
            rename = execute('x402_treazury', 'wallet', 'rename', 'general', 'research', check=False)
            assert rename.returncode and 'source wallet group does not exist' in rename.stderr.lower(), rename.stderr
            docker('restart', identity)
            assert policy()['servers']['web']['wallet'] == 'research'
            assert inspect()['prepared']
            cases = (
                (changed.replace('socks_endpoint = "unix:/run/tor-x402_treazury/socks"', 'socks_endpoint = "127.0.0.1:9050"'), 'private Tor'),
                (changed.replace('listen = "127.0.0.1:3011"', 'listen = "0.0.0.0:3011"'), 'loopback'),
                (changed.replace('state_dir = "/var/lib/x402/state"', 'state_dir = "/tmp/state"'), 'state/key'),
                (changed.replace('bearer_token_env = "X402_TREAZURY_MCP_TOKEN"', 'bearer_token_env = "OTHER_TOKEN"'), 'loopback'),
            )
            for text, reason in cases:
                publish(text)
                state = inspect()
                assert not state['prepared'] and reason in state['reason'], state
            publish('invalid TOML [')
            assert execute('x402_treazury', 'config', 'show', check=False).returncode
            assert not inspect()['prepared']
            path.unlink()
            assert execute('x402_treazury', 'config', 'show', check=False).returncode
            publish(changed)
            assert inspect()['prepared']
            initialize_research_config(['docker', 'compose', '-f', 'compose.yaml'], root)
            assert path.read_text() == changed
            print('PASS: real-image policy edits, relative providers, read-only mount, atomic replacement/restart, historical gate, forbidden/malformed/missing config, offline preview/rename error path and seed preservation')
        finally:
            docker('rm', '-f', identity, check=False)
            docker('volume', 'rm', identity)


if __name__ == '__main__':
    main()
