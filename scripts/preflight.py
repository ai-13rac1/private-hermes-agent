#!/usr/bin/env python3
"""Read-only checks for required Docker features and conflicting address pools."""
import ipaddress
import json
import re
import subprocess
import sys


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def version(value):
    match = re.match(r'v?(\d+)\.(\d+)\.(\d+)', value)
    if not match:
        raise SystemExit('Cannot recognize engine/Compose version: ' + value)
    return tuple(map(int, match.groups()))


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else 'private-hermes'
    if version(output('docker', 'version', '--format', '{{.Server.Version}}')) < (28, 0, 0):
        raise SystemExit('Docker Engine 28+ is required for isolated bridge gateway mode.')
    if version(output('docker', 'compose', 'version', '--short')) < (2, 36, 0):
        raise SystemExit('Docker Compose 2.36+ is required for this deployment.')
    config = json.loads(output('docker', 'compose', '-p', project, 'config', '--format', 'json'))
    selected = [ipaddress.ip_network(c['subnet']) for n in config['networks'].values()
                for c in n.get('ipam', {}).get('config', []) if 'subnet' in c]
    identifiers = output('docker', 'network', 'ls', '-q').split()
    existing = json.loads(output('docker', 'network', 'inspect', *identifiers)) if identifiers else []
    for network in existing:
        if network.get('Labels', {}).get('com.docker.compose.project') == project:
            continue
        for entry in network.get('IPAM', {}).get('Config') or []:
            if not entry.get('Subnet'):
                continue
            occupied = ipaddress.ip_network(entry['Subnet'])
            for candidate in selected:
                if candidate.version == occupied.version and candidate.overlaps(occupied):
                    raise SystemExit(f'Address conflict: {candidate} overlaps {network["Name"]} ({occupied}). Stop the test/normal stack or coordinate a new address plan; no network was changed.')
    print('Docker features and address pools checked.')


if __name__ == '__main__':
    main()
