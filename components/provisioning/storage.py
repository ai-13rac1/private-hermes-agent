"""Persistent bind/volume layout; trusted init sets directory ownership only."""
import os
import fcntl
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
import tempfile

# Keep application identities unchanged. Parent directories belong to the host
# operator and are never mounted into application containers.
LAYOUT = {
    'executor/home': (10000, 10000, 0o755),
    'executor/workspace': (10000, 10000, 0o755),
    'ssh/agent': (10000, 10000, 0o700),
    'ssh/executor': (0, 0, 0o755),
    'x402_treazury-auth': (10003, 10003, 0o700),
    'tor': (101, 102, 0o700),
    'tailscale': (0, 0, 0o700),
}


def directory(path, create=False):
    if create:
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            pass
    if not stat.S_ISDIR(path.lstat().st_mode):
        raise ValueError(f'Persistent storage path must be a directory, not a symlink: {path}')


def initialize(root, ownership=False):
    root = Path(root)
    directory(root, create=not ownership)
    # This parent remains host-owned, protecting leaves whose application needs
    # require traversal by its own root and unprivileged processes.
    root.chmod(0o700)
    for relative, (uid, gid, mode) in LAYOUT.items():
        leaf = root
        for part in Path(relative).parts:
            leaf /= part
            directory(leaf, create=not ownership)
        if ownership:
            current = leaf.stat()
            if (current.st_uid, current.st_gid) != (uid, gid):
                os.chown(leaf, uid, gid, follow_symlinks=False)
            if stat.S_IMODE(current.st_mode) != mode:
                leaf.chmod(mode)


def verify_filesystem(root):
    """Refuse live state on filesystems that cannot enforce lock exclusion."""
    root = Path(root)
    directory(root)
    with tempfile.TemporaryDirectory(prefix='.filesystem-check-', dir=root) as folder:
        lock = Path(folder) / 'exclusive.lock'
        with lock.open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run([sys.executable, __file__, '--lock-probe', str(lock)])
            if result.returncode != 9:
                raise RuntimeError('Persistent filesystem does not enforce interprocess file locks. '
                                   'Live database/wallet storage cannot start here; fix Docker file sharing '
                                   'or retain native Docker volumes with exported backups.')
        database = Path(folder) / 'probe.sqlite'
        with sqlite3.connect(database) as connection:
            connection.execute('PRAGMA journal_mode=WAL')
            connection.execute('CREATE TABLE probe(value)')
            connection.commit()
            connection.execute('BEGIN IMMEDIATE')
            result = subprocess.run([sys.executable, __file__, '--sqlite-probe', str(database)])
            if result.returncode != 9:
                raise RuntimeError('Persistent filesystem does not enforce SQLite writer locks; live state cannot start here.')


def initialize_volume(root, uid, gid, mode):
    root = Path(root)
    directory(root)
    verify_filesystem(root)
    os.chown(root, uid, gid, follow_symlinks=False)
    root.chmod(mode)


if __name__ == '__main__':
    if sys.argv[1] == '--check-filesystem':
        verify_filesystem(sys.argv[2])
        print('PASS: fresh-file flock and SQLite WAL writer exclusion enforced.')
    elif sys.argv[1] == '--lock-probe':
        with open(sys.argv[2], 'a') as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                sys.exit(9)
    elif sys.argv[1] == '--sqlite-probe':
        with sqlite3.connect(sys.argv[2], timeout=0) as connection:
            try:
                connection.execute('BEGIN IMMEDIATE')
            except sqlite3.OperationalError as error:
                if error.sqlite_errorcode == sqlite3.SQLITE_BUSY:
                    sys.exit(9)
                raise
    else:
        initialize(sys.argv[1], ownership=True)
        initialize_volume(sys.argv[2], 10000, 10000, 0o755)
        initialize_volume(sys.argv[3], 10003, 10003, 0o700)
        print('Persistent bind directories and database volumes prepared; existing files were not changed.')
