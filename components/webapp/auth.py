"""Native Hermes scrypt hash format; generated secrets stay in private files."""
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
import hmac
import sys


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return 'scrypt$16384$8$1$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(digest).decode()


def validate(credentials):
    if set(credentials) != {'password_hash', 'secret'}:
        raise ValueError('Webapp credentials must contain password_hash and secret')
    scheme, n, r, p, salt, digest = credentials['password_hash'].split('$')
    if (scheme, n, r, p) != ('scrypt', '16384', '8', '1') or len(base64.b64decode(salt, validate=True)) != 16 or len(base64.b64decode(digest, validate=True)) != 32:
        raise ValueError('Invalid native Hermes password hash')
    if len(credentials['secret']) < 43 or not all(c.isalnum() or c in '_-' for c in credentials['secret']):
        raise ValueError('Invalid webapp session signing secret')
    return credentials


def write_private(path, value):
    """Publish one complete private file; retries need no transaction record."""
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def password_matches(password, encoded):
    _, n, r, p, salt, digest = encoded.split('$')
    calculated = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt),
                                n=int(n), r=int(r), p=int(p), dklen=32)
    return hmac.compare_digest(calculated, base64.b64decode(digest))


def initialize_credentials(root, rotate=False):
    """Preserve identity and reuse the saved password after interrupted writes."""
    folder = Path(root) / 'config/webapp'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'auth.json'
    password_path = folder / 'password'
    credentials = None
    if path.exists() and not rotate:
        credentials = validate(json.loads(path.read_text()))
        if not password_path.is_file() or not password_path.read_text().strip():
            print('Saved webapp password is missing or empty; existing authentication remains usable. '
                  'If you do not know the password, restore config/webapp/password from backup '
                  'or run make webapp-rotate explicitly.', file=sys.stderr)
            return False
    if password_path.exists() and not rotate:
        password = password_path.read_text().strip()
        if not password:
            raise ValueError('Saved webapp password is empty; restore it or run make webapp-rotate explicitly.')
    else:
        password = secrets.token_urlsafe(32)
        # Keep the recoverable value before its one-way hash. Initial creation
        # can then reuse it if interrupted before auth.json is published.
        write_private(password_path, password + '\n')
    if credentials and password_matches(password, credentials['password_hash']):
        return False
    credentials = {'password_hash': hash_password(password),
                   'secret': credentials['secret'] if credentials else secrets.token_urlsafe(48)}
    write_private(path, json.dumps(credentials) + '\n')
    return True
