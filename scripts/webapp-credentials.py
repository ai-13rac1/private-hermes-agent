#!/usr/bin/env python3
"""Explicit operator workflow: create or rotate webapp login credentials."""
import argparse
from deployment import ROOT

parser = argparse.ArgumentParser()
parser.add_argument('--rotate', action='store_true', help='Replace password and signing key, invalidating all sessions')
args = parser.parse_args()
from auth import initialize_credentials
if initialize_credentials(ROOT, rotate=args.rotate):
    print('Generated webapp password in config/webapp/password (0600); credentials were not printed.')
    if args.rotate:
        print('Apply rotation with make up to reprovision and recreate Hermes.')
else:
    print('Existing webapp credentials preserved.')
