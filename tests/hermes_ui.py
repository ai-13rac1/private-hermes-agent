#!/usr/bin/env python3
"""Focused native renderer qualification in the disposable derived build stage."""
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from deployment import engine_command  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'private-hermes-webapp-build:qualification'
# The runtime image omits this file, imported by an upstream TypeScript test.
# Copied verbatim from source 2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19:
# tests/fixtures/session-resume-active-turn.json. Not used by runtime services.
FIXTURE = ROOT / 'tests/fixtures/session-resume-active-turn.json'
WORKSPACE = '/opt/hermes/.build/webapp-workspace/apps/desktop'


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def main():
    run(*engine_command(), 'build', '--target', 'webapp-build', '-f', 'components/hermes/Dockerfile', '-t', IMAGE, '.')
    # The full native TypeScript tree exhausted Node's default 2 GiB heap on
    # this target. This compiler-only setting does not limit runtime containers.
    run(*engine_command(), 'run', '--rm', '--network', 'none', '--cap-drop', 'ALL',
        '--mount', f'type=bind,source={FIXTURE},target=/run/public-fixture.json,readonly',
        '--entrypoint', '/bin/sh', '--workdir', WORKSPACE, IMAGE, '-c',
        'mkdir -p ../../tests/fixtures && '
        'cp /run/public-fixture.json ../../tests/fixtures/session-resume-active-turn.json && '
        'exec node --max-old-space-size=4096 ../../node_modules/typescript/bin/tsc -p tsconfig.json --noEmit')
    run(*engine_command(), 'run', '--rm', '--network', 'none', '--cap-drop', 'ALL',
        '--entrypoint', 'node', '--workdir', WORKSPACE, IMAGE,
        '../../node_modules/vitest/vitest.mjs', 'run', '--project', 'ui',
        'src/hooks/use-media-image.test.tsx', 'src/lib/media.remote.test.ts',
        'src/app/chat/right-rail/preview-pane.test.tsx')
    print('PASS: full renderer TypeScript check and focused native media/preview tests')


if __name__ == '__main__':
    main()
