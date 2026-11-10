#!/usr/bin/env python3
"""Initialize local operator configuration without replacing existing settings."""
from pathlib import Path
import argparse
import os
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'components/webapp'))
from auth import initialize_credentials
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'components/provisioning'))
from storage import initialize as initialize_storage


def initialize(root, wallet_only=False):
    root = Path(root)
    env = root / '.env'
    if not env.exists():
        with open(env, 'x', opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
            stream.write((root / '.env.example').read_text())

    target = root / 'config/network/mcp-allowlist.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        source = root / 'components/network/mcp-allowlist.json'
        with target.open('xb') as stream:
            stream.write(source.read_bytes())
        shutil.copymode(source, target)
    if not target.is_file():
        raise SystemExit('config/network/mcp-allowlist.json must be a file')
    initialize_storage(root / 'data')
    (root / 'config/webapp').mkdir(parents=True, exist_ok=True)
    if not wallet_only:
        initialize_credentials(root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wallet', action='store_true', help='Prepare wallet host paths without webapp settings or credentials')
    args = parser.parse_args()
    initialize(Path(__file__).resolve().parents[1], wallet_only=args.wallet)
    if not args.wallet:
        from deployment import render, settings
        render(settings())
    print('Initialized local configuration; existing settings and application volumes preserved.')
    if not args.wallet:
        print('Webapp password: config/webapp/password (0600); credentials were not printed.')
