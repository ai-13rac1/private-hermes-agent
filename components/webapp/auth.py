"""Native Hermes scrypt hash format; generated secrets stay in private files."""
import base64
import hashlib
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
