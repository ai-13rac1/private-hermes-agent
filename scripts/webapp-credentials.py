#!/usr/bin/env python3
"""Explicit operator workflow: create or rotate webapp login credentials."""
import argparse
import json
import os
import secrets
from deployment import ROOT, settings
from auth import hash_password, validate

parser = argparse.ArgumentParser()
parser.add_argument('--rotate', action='store_true', help='Replace password and signing key, invalidating all sessions')
args = parser.parse_args()
settings()  # reject malformed configuration even before generating credentials
folder = ROOT / 'config/webapp'
folder.mkdir(parents=True, exist_ok=True)
path = folder / 'auth.json'
if path.exists() and not args.rotate:
    validate(json.loads(path.read_text()))
    print('Existing webapp credentials preserved. Use --rotate for a new password and signing key.')
else:
    password = secrets.token_urlsafe(32)
    credentials = {'password_hash': hash_password(password), 'secret': secrets.token_urlsafe(48)}
    for destination, value in ((path, json.dumps(credentials) + '\n'), (folder / 'password', password + '\n')):
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(value)
        destination.chmod(0o600)
    print('Generated webapp password in config/webapp/password (0600); credentials were not printed.')
    if args.rotate:
        print('Apply rotation with make up to reprovision and recreate Hermes.')
