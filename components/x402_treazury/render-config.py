"""Adapt only deployment addresses/paths; preserve upstream authored selections."""
from pathlib import Path
import re
import sys
import tomllib
from endpoints import ADDRESS, ENDPOINTS


def render(source):
    before = tomllib.loads(source)
    servers = before['servers']
    expected = ENDPOINTS
    if {name: server['listen'] for name, server in servers.items()} != {name: f'{ADDRESS}:{port}' for name, port in expected.items()}:
        raise ValueError('Upstream x402_treazury endpoint inventory changed; review the integration')
    if before['network']['mode'] != 'tor':
        raise ValueError('Research desk must retain Tor mode')
    text, count = re.subn(r'^socks_endpoint = .*$', 'socks_endpoint = "unix:/run/tor-x402_treazury/socks"', source, flags=re.M)
    if count != 1:
        raise ValueError('Expected one SOCKS endpoint')
    text, count = re.subn(r'^state_dir = .*$', 'state_dir = "/var/lib/x402/state"', text, flags=re.M)
    if count != 1:
        raise ValueError('Expected one treasury state directory')
    text, count = re.subn(r'^allowed_hosts = .*$', f'allowed_hosts = ["{ADDRESS}"]', text, flags=re.M)
    if count != len(expected):
        raise ValueError('Expected an explicit Host allowlist for every endpoint')
    after = tomllib.loads(text)
    # All other fields, including financial authority and tool selections, must
    # remain structurally identical to the pinned upstream deployment.
    after['network']['socks_endpoint'] = before['network']['socks_endpoint']
    after['treasury']['state_dir'] = before['treasury']['state_dir']
    for name in expected:
        for field in ('listen', 'allowed_hosts'):
            after['servers'][name][field] = before['servers'][name][field]
    if after != before:
        raise ValueError('Rendering changed more than deployment addresses and state path')
    return text


if __name__ == '__main__':
    Path(sys.argv[2]).write_text(render(Path(sys.argv[1]).read_text()))
