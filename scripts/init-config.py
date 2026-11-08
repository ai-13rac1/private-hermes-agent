#!/usr/bin/env python3
"""Initialize local operator configuration without replacing existing settings."""
from pathlib import Path
import os
import shutil


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
    (root / 'data').mkdir(exist_ok=True)


if __name__ == '__main__':
    initialize(Path(__file__).resolve().parents[1])
    print('Initialized .env and local config; existing settings and application volumes preserved.')
