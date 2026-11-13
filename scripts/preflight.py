#!/usr/bin/env python3
"""Read-only checks for required engine features and conflicting address pools."""
import argparse
import ipaddress
import json
import subprocess
import sys
import deployment
from deployment import compose_base, compose_files, engine, engine_command


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def check_engine():
    try:
        deployment.check_engine()
    except deployment.EngineError as error:
        raise SystemExit(str(error)) from None


def check_security_options(config):
    # Compose reads a seccomp profile file and sends its content through the
    # Docker-compatible API. Podman's API treats that value as a file path, so
    # the container cannot be created. Normal Podman services use native defaults.
    if engine() != 'podman':
        return
    for name, service in sorted(config['services'].items()):
        for option in service.get('security_opt') or []:
            if option.startswith('seccomp=') and option != 'seccomp=unconfined':
                raise SystemExit(f'Service {name} selects a custom seccomp profile ({option}). '
                                 'The Compose provider sends inline JSON, but Podman expects a host filename. '
                                 'Use the native Podman default without a seccomp override, or Docker for custom profiles.')


def subnets(network):
    # Docker reports IPAM.Config[].Subnet; native Podman inspect reports subnets[].subnet.
    entries = (network.get('IPAM') or {}).get('Config') or []
    found = [entry.get('Subnet') for entry in entries]
    found += [entry.get('subnet') for entry in network.get('subnets') or []]
    return [ipaddress.ip_network(value) for value in found if value]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project', nargs='?', default='private-hermes')
    parser.add_argument('--funnel', action='store_true')
    arguments = parser.parse_args()
    project = arguments.project
    check_engine()
    command = [*compose_base(), '-p', project, *compose_files(arguments.funnel)]
    config = json.loads(output(*command, 'config', '--format', 'json'))
    check_security_options(config)
    selected = [ipaddress.ip_network(c['subnet']) for n in config['networks'].values()
                for c in n.get('ipam', {}).get('config', []) if 'subnet' in c]
    identifiers = output(*engine_command(), 'network', 'ls', '-q').split()
    existing = json.loads(output(*engine_command(), 'network', 'inspect', *identifiers)) if identifiers else []
    for network in existing:
        labels = network.get('Labels') or network.get('labels') or {}
        if labels.get('com.docker.compose.project') == project:
            continue
        name = network.get('Name') or network.get('name')
        for occupied in subnets(network):
            for candidate in selected:
                if candidate.version == occupied.version and candidate.overlaps(occupied):
                    raise SystemExit(f'Address conflict: {candidate} overlaps {name} ({occupied}). Stop the test/normal stack or coordinate a new address plan; no network was changed.')
    print('Engine features and address pools checked.')


if __name__ == '__main__':
    main()
