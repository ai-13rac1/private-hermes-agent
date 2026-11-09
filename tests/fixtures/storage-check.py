"""Check real persistent-filesystem locking, WAL, and atomic replacement as UID 10003."""
import fcntl
import os
from pathlib import Path
import sqlite3
import subprocess
import sys


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == 'lock':
            with open(sys.argv[2], 'a') as stream:
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    sys.exit(9)
        else:
            with sqlite3.connect(sys.argv[2], timeout=0) as connection:
                # A reader must work while another process owns the writer lock.
                assert connection.execute('SELECT count(*) FROM proof').fetchone()[0] == 0
                try:
                    connection.execute('BEGIN IMMEDIATE')
                except sqlite3.OperationalError as error:
                    assert error.sqlite_errorcode == sqlite3.SQLITE_BUSY
                    sys.exit(9)
        return
    root = Path('/var/lib/x402/filesystem-probe')
    root.mkdir(mode=0o700)
    lock = root / 'exclusive.lock'
    with lock.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = subprocess.run([sys.executable, __file__, 'lock', str(lock)])
        flock_enforced = result.returncode == 9
        print(f'Filesystem probe: competing flock exit={result.returncode}', flush=True)
    assert subprocess.run([sys.executable, __file__, 'lock', str(lock)]).returncode == 0
    database = root / 'proof.sqlite'
    with sqlite3.connect(database) as connection:
        database.chmod(0o600)
        assert connection.execute('PRAGMA journal_mode=WAL').fetchone()[0] == 'wal'
        connection.execute('CREATE TABLE proof(value)')
        connection.commit()
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('INSERT INTO proof VALUES(1)')
        result = subprocess.run([sys.executable, __file__, 'sqlite', str(database)])
        print(f'Filesystem probe: competing SQLite writer exit={result.returncode}', flush=True)
        assert result.returncode == 9, 'SQLite did not enforce its writer lock'
        connection.commit()
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT value FROM proof').fetchone()[0] == 1
    temporary = root / 'replace.tmp'
    with temporary.open('w') as stream:
        stream.write('atomic replacement proof')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(root / 'committed')
    assert (root / 'committed').read_text() == 'atomic replacement proof'
    assert os.getuid() == 10003
    assert flock_enforced, 'Filesystem did not enforce interprocess flock'
    print('PASS: persistent filesystem supports interprocess locks, SQLite WAL and atomic replacement')


if __name__ == '__main__':
    main()
