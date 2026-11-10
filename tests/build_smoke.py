#!/usr/bin/env python3
"""Artifact construction does not initialize or depend on disposable operator state."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix='private-hermes-build-test-') as folder:
        root = Path(folder)
        for name in ('Makefile', 'compose.yaml', 'compose.funnel.yaml', '.dockerignore'):
            shutil.copyfile(ROOT / name, root / name)
        for name in ('components', 'scripts'):
            shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns('__pycache__'))
        # Keep dotenv syntax parseable while command/policy values are invalid.
        (root / '.env').write_text("WEBAPP_EXTERNAL_CONTENT=invalid\nTEEP_HOST_PORT=invalid\nTEEP_SERVE_ARGS='\"'\n")
        (root / 'config').write_text('not a configuration directory')
        (root / 'data').write_text('not a storage directory')
        original = {name: (root / name).read_bytes() for name in ('.env', 'config', 'data')}
        environment = dict(os.environ, COMPOSE_PROJECT_NAME='private-hermes-build-fixture')
        result = subprocess.run(['make', 'build'], cwd=root, env=environment,
                                text=True, capture_output=True)
        if result.returncode:
            print(result.stdout, result.stderr)
            raise RuntimeError('Artifact-only fixture build failed')
        assert all((root / name).read_bytes() == value for name, value in original.items())
        assert not (root / '.operation.lock').exists()
        print('PASS: real Make image build succeeds despite invalid deployment policy/port/command and wrong-type operator paths; operator files remain unchanged')


if __name__ == '__main__':
    main()
