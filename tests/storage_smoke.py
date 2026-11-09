#!/usr/bin/env python3
"""Qualify native database storage and persistence through ordinary Compose down."""
import json
import secrets
import subprocess
import smoke


smoke.COMPOSE = ['docker', 'compose', '-p', 'private-hermes-storage-test',
                 '-f', 'compose.yaml', '-f', 'tests/compose.yaml']


def main():
    marker = secrets.token_hex(16)
    targets = [('configure', '/opt/hermes/.venv/bin/python', '/opt/data'),
               ('x402_treazury-admin', 'python3', '/var/lib/x402')]
    with smoke.storage_fixture():
        try:
            smoke.compose('run', '--rm', '-T', '--no-deps', 'storage-init')
            for service, interpreter, root in targets:
                script = """import sqlite3, sys
from pathlib import Path
root=Path(sys.argv[1]); marker=sys.argv[2]
with sqlite3.connect(root/'persistence-test.sqlite') as db:
 db.execute('PRAGMA journal_mode=WAL')
 db.execute('CREATE TABLE proof(value)')
 db.execute('INSERT INTO proof VALUES(?)',(marker,))
 db.commit()
(root/'persistence-test.txt').write_text(marker)
"""
                smoke.compose('run', '--rm', '-T', '--no-deps', '--entrypoint', interpreter,
                              service, '-c', script, root, marker)
            smoke.compose('down', '--timeout', '-1')
            for name in ('hermes-data', 'x402_treazury-data'):
                result = subprocess.run(['docker', 'volume', 'inspect',
                                         'private-hermes-storage-test_' + name],
                                        text=True, capture_output=True, check=True)
                assert json.loads(result.stdout)[0]['Labels']['com.docker.compose.project'] == 'private-hermes-storage-test'
            # Recreating the initializer and application containers must reuse
            # the same data; initialization must preserve existing files.
            smoke.compose('run', '--rm', '-T', '--no-deps', 'storage-init')
            for service, interpreter, root in targets:
                script = """import sqlite3, sys
from pathlib import Path
root=Path(sys.argv[1]); marker=sys.argv[2]
assert (root/'persistence-test.txt').read_text()==marker
with sqlite3.connect(root/'persistence-test.sqlite') as db:
 assert db.execute('SELECT value FROM proof').fetchall()==[(marker,)]
"""
                smoke.compose('run', '--rm', '-T', '--no-deps', '--entrypoint', interpreter,
                              service, '-c', script, root, marker)
            print('PASS: native volume locks enforced; files and SQLite data survive Compose down and container recreation', flush=True)
        finally:
            # Only this disposable test project is deliberately erased.
            smoke.compose('down', '--volumes', '--remove-orphans')


if __name__ == '__main__':
    main()
