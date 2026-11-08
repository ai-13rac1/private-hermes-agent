"""Load the shared MCP bearer token without putting it in command arguments."""
import os
from pathlib import Path
import sys

path = Path('/run/x402_treazury-auth/token')
if path.exists():
    token = path.read_text().strip()
    if not token:
        raise SystemExit('Research MCP token file is empty')
    os.environ['X402_TREAZURY_MCP_TOKEN'] = token
elif sys.argv[1:] == ['serve']:
    raise SystemExit('Provision the shared x402_treazury MCP token before serving')
os.execvp('x402_treazury', ['x402_treazury', *sys.argv[1:]])
