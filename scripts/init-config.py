#!/usr/bin/env python3
"""Initialize local operator configuration without replacing existing settings."""
from pathlib import Path
import os
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'components/webapp'))
from auth import initialize_credentials
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'components/provisioning'))
from storage import initialize as initialize_storage


def initialize(root):
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
    initialize_credentials(root)


if __name__ == '__main__':
    initialize(Path(__file__).resolve().parents[1])
    from deployment import render, settings
    render(settings())
    print('Initialized local configuration; existing settings and application volumes preserved.')
    print('Webapp password: config/webapp/password (0600); credentials were not printed.')
