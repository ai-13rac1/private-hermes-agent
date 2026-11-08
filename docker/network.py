"""Own the agent/executor network namespaces and a separate transparent router.

Only this trusted service has NET_ADMIN. Application containers share its
namespace, but have neither network administration nor raw-packet capability.
"""
import ipaddress
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

# Block non-public IPv4 destinations even when applications use literal IPs or
# public DNS returns a private answer. Explicit service grants precede this list.
DENIED = (
    '0.0.0.0/8', '10.0.0.0/8', '100.64.0.0/10', '127.0.0.0/8',
    '169.254.0.0/16', '172.16.0.0/12', '192.0.0.0/24', '192.0.2.0/24',
    '192.88.99.0/24', '192.168.0.0/16', '198.18.0.0/15',
    '198.51.100.0/24', '203.0.113.0/24', '224.0.0.0/3',
)


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def connected():
    routes = json.loads(run('ip', '-j', '-4', 'route', 'show', 'scope', 'link', capture_output=True).stdout)
    return [r['dst'] for r in routes if r.get('dst') and r['dst'] != 'default']


def apply(raw, nat, incoming, outgoing):
    # The namespace is exclusively managed here. Restores are atomic per table.
    # Drop policies close any gaps across tables and on reinitialization.
    for binary in ('iptables', 'ip6tables'):
        for chain in ('INPUT', 'OUTPUT', 'FORWARD'):
            run(binary, '-P', chain, 'DROP')
    text = '\n'.join([
        '*raw', ':PREROUTING ACCEPT [0:0]', ':OUTPUT ACCEPT [0:0]', *raw, 'COMMIT',
        '*nat', ':PREROUTING ACCEPT [0:0]', ':INPUT ACCEPT [0:0]',
        ':OUTPUT ACCEPT [0:0]', ':POSTROUTING ACCEPT [0:0]', *nat, 'COMMIT',
        '*filter', ':INPUT DROP [0:0]', ':OUTPUT DROP [0:0]', ':FORWARD DROP [0:0]',
        '-A INPUT -i lo -j ACCEPT', '-A OUTPUT -o lo -j ACCEPT',
        '-A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT',
        '-A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT',
        *incoming, *outgoing, 'COMMIT', '',
    ])
    run('iptables-restore', input=text)
    run('ip6tables-restore', input='\n'.join([
        '*filter', ':INPUT DROP [0:0]', ':OUTPUT DROP [0:0]', ':FORWARD DROP [0:0]',
        '-A INPUT -i lo -j ACCEPT', '-A OUTPUT -o lo -j ACCEPT', 'COMMIT', '',
    ]))


def deny(chain, networks):
    return [f'-A {chain} -d {network} -j DROP' for network in networks]


def mcp_grants():
    entries = json.loads(Path('/etc/private-hermes/mcp-allowlist.json').read_text())
    if not isinstance(entries, list):
        raise ValueError('MCP allowlist must be a list')
    rules = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {'ip', 'port'}:
            raise ValueError('Each MCP grant must contain only ip and port')
        address = ipaddress.IPv4Address(entry['ip'])
        port = entry['port']
        if address not in ipaddress.IPv4Network('10.203.84.0/24') or int(address) & 255 in (0, 1, 2, 255):
            raise ValueError('MCP grants must target service addresses on mcp-access')
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('MCP port must be an integer from 1 to 65535')
        rules.append(f'-A OUTPUT -d {address}/32 -p tcp --dport {port} -j ACCEPT')
    return rules


def tunnel(name, local, remote, address):
    present = subprocess.run(['ip', 'link', 'show', name], capture_output=True).returncode == 0
    if not present:
        run('ip', 'tunnel', 'add', name, 'mode', 'gre', 'local', local, 'remote', remote, 'ttl', '64')
    run('ip', 'addr', 'replace', address, 'dev', name)
    run('ip', 'link', 'set', name, 'mtu', '1400', 'up')


def endpoint(role):
    agent = role == 'agent'
    gateway = '10.203.80.3' if agent else '10.203.81.3'
    outer = '10.203.80.2' if agent else '10.203.81.2'
    inner = '10.204.80.2' if agent else '10.204.81.2'
    peer = '10.204.80.1' if agent else '10.204.81.1'
    tunnel('tor-route', outer, gateway, inner + '/30')
    outgoing = [f'-A OUTPUT -d {gateway}/32 -p udp --dport 53 -j ACCEPT',
                f'-A OUTPUT -d {gateway}/32 -p gre -j ACCEPT']
    incoming = []
    if agent:
        outgoing += [
            '-A OUTPUT -d 10.203.83.3/32 -p tcp --dport 8337 -j ACCEPT',
            '-A OUTPUT -d 10.203.82.3/32 -p tcp --dport 2222 -j ACCEPT',
            *mcp_grants(),
        ]
    else:
        incoming += ['-A INPUT -s 10.203.82.2/32 -d 10.203.82.3/32 -p tcp --dport 2222 -j ACCEPT']
    outgoing += deny('OUTPUT', (*DENIED, *connected()))
    outgoing += ['-A OUTPUT -p tcp -j ACCEPT']
    # Drop embedded Docker DNS before its DNAT changes port 53. Also prevents
    # a loopback exception from admitting queries to Docker's resolver.
    apply(['-A OUTPUT -d 127.0.0.11/32 -j DROP'], [], incoming, outgoing)
    run('ip', 'route', 'replace', 'default', 'via', peer, 'dev', 'tor-route')
    Path('/tmp/network-ready').touch()
    print(f'{role}: firewall and default route installed', flush=True)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    while True:
        signal.pause()


def router():
    clients = [('10.203.80.2', '10.203.80.3', '10.204.80.2', '10.204.80.1'),
               ('10.203.81.2', '10.203.81.3', '10.204.81.2', '10.204.81.1')]
    for index, (client, gateway, inner, peer) in enumerate(clients):
        tunnel(f'client-{index}', gateway, client, peer + '/30')
    raw, nat, incoming = [], [], []
    networks = (*DENIED, *connected())
    for client, gateway, inner, peer in clients:
        # GRE carries the original public-destination packet inside an internal
        # IP packet. Docker's internal bridge drops public-destination Ethernet
        # frames even when their next hop is another container on that bridge.
        raw += [
            f'-A PREROUTING -s {client}/32 -d {gateway}/32 -p gre -j ACCEPT',
            f'-A PREROUTING -s {client}/32 -d {gateway}/32 -p udp --dport 53 -j ACCEPT',
        ]
        for source in (client, inner):
            raw += [f'-A PREROUTING -s {source}/32 -d {network} -j DROP' for network in networks]
        nat += [
            f'-A PREROUTING -s {client}/32 -d {gateway}/32 -p udp --dport 53 -j REDIRECT --to-ports 9053',
            f'-A PREROUTING -s {inner}/32 -p tcp -j REDIRECT --to-ports 9040',
        ]
        incoming += [
            f'-A INPUT -s {client}/32 -d {gateway}/32 -p gre -j ACCEPT',
            f'-A INPUT -s {inner}/32 -p tcp --dport 9040 -j ACCEPT',
            f'-A INPUT -s {client}/32 -p udp --dport 9053 -j ACCEPT',
        ]
    # The Tor process itself also cannot contact host, VM, or private networks.
    outgoing = [f'-A OUTPUT -d {client}/32 -p gre -j ACCEPT' for client, *_ in clients]
    outgoing += deny('OUTPUT', networks)
    outgoing += ['-A OUTPUT -m owner --uid-owner 101 -p tcp -j ACCEPT']
    apply(raw, nat, incoming, outgoing)
    state = Path('/var/lib/tor')
    state.mkdir(exist_ok=True)
    for base, dirs, files in os.walk(state):
        for path in [Path(base), *(Path(base) / p for p in dirs + files)]:
            os.chown(path, 101, 102, follow_symlinks=False)
    state.chmod(0o700)
    print('router: firewall installed; starting Tor without network capabilities', flush=True)
    config = '/etc/tor/torrc'
    if os.environ.get('PRIVATE_HERMES_RESEARCH_SOCKS', '0') == '1':
        socks = Path('/run/tor-research')
        os.chown(socks, 101, 102)
        socks.chmod(0o750)
        original = Path(config).read_text()
        if original.splitlines().count('SocksPort 0') != 1:
            raise ValueError('Expected one disabled SOCKS listener in the base Tor config')
        rendered = original.replace('SocksPort 0', 'SocksPort unix:/run/tor-research/socks IsolateSOCKSAuth GroupWritable RelaxDirModeCheck')
        config = '/tmp/research-torrc'
        Path(config).write_text(rendered)
    os.execvp('su-exec', ['su-exec', '101:102', '/usr/bin/tor', '-f', config])


if __name__ == '__main__':
    role = sys.argv[1]
    if role == 'router':
        router()
    elif role in ('agent', 'executor'):
        endpoint(role)
    else:
        raise SystemExit('Expected router, agent, or executor')
