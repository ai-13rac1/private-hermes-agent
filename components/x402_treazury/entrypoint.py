"""Load the shared MCP bearer token without putting it in command arguments."""
import os
from pathlib import Path
import sys

path = Path('/run/x402_treazury-auth/token')
arguments = sys.argv[1:]
if not arguments or arguments[0] not in ('serve', 'wallet', 'catalog', 'config', 'build-info', '--help', '--version', '-h', '-V'):
    raise SystemExit('Specify a supported command; serving requires staged preparation.')
if arguments[0] == 'serve' and arguments != ['serve']:
    raise SystemExit('Serving must use the prepared deployment configuration without command overrides.')
if path.exists():
    token = path.read_text().strip()
    if not token:
        raise SystemExit('Research MCP token file is empty')
    os.environ['X402_TREAZURY_MCP_TOKEN'] = token
elif sys.argv[1:] == ['serve']:
    raise SystemExit('Provision the shared x402_treazury MCP token before serving')
if sys.argv[1:] == ['serve']:
    from onboarding import serve
    try:
        serve()
    except Exception as error:
        print(error, file=sys.stderr)
        sys.exit(1)
else:
    os.execvp('x402_treazury', ['x402_treazury', *sys.argv[1:]])
