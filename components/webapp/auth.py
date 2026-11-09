"""Native Hermes scrypt hash format; generated secrets stay in private files."""
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets


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


def initialize_credentials(root, rotate=False):
    """Generate only missing credentials; rotation is an explicit operator action."""
    folder = Path(root) / 'config/webapp'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'auth.json'
    if path.exists() and not rotate:
        validate(json.loads(path.read_text()))
        return False
    password = secrets.token_urlsafe(32)
    credentials = {'password_hash': hash_password(password), 'secret': secrets.token_urlsafe(48)}
    for destination, value in ((path, json.dumps(credentials) + '\n'),
                               (folder / 'password', password + '\n')):
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(value)
        destination.chmod(0o600)
    return True
