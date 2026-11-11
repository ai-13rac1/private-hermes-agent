#!/usr/bin/env python3
"""Desktop checks inside the disposable SSH/network smoke project; no inference."""
from pathlib import Path
import json
import os
import subprocess
import smoke


def check():
    fixture = Path(__file__).parent / 'fixtures/computer-use.py'
    try:
        result = smoke.python('hermes', fixture.read_text())
    except subprocess.CalledProcessError as error:
        print(error.stdout, error.stderr, flush=True)
        raise RuntimeError('Disposable desktop fixture failed; see diagnostics above') from None
    print(result.stdout, flush=True)


def switching_checks():
    """Exercise native persistence and dependency loss in the existing test project."""
    smoke.python('executor', "from pathlib import Path; p=Path('/home/runner/.hermes/bot-desktop/browser-profile'); p.mkdir(parents=True,exist_ok=True); (p/'fixture-state').write_text('preserved')")
    proof = """import hashlib,json
from pathlib import Path
print(json.dumps({p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (
'/run/executor-auth/ssh_host_ed25519_key.pub', '/workspace/computer-use-marker',
'/home/runner/.hermes/bot-desktop/browser-profile/fixture-state')}))
"""
    original = json.loads(smoke.python('executor', proof).stdout)
    for enabled in ('false', 'true'):
        environment = dict(os.environ, COMPUTER_USE_ENABLED=enabled)
        smoke.compose('build', 'executor', env=environment)
        smoke.compose('up', '-d', '--wait', '--no-deps', 'executor', 'hermes', env=environment)
        assert json.loads(smoke.python('executor', proof).stdout) == original
        result = smoke.python('hermes', """import model_tools
from hermes_bootstrap import PRIVATE_HERMES_COMPUTER_USE
from tools.registry import registry
from tools.computer_use.tool import check_computer_use_requirements
assert bool(registry.get_entry('computer_use')) == PRIVATE_HERMES_COMPUTER_USE
assert check_computer_use_requirements() == PRIVATE_HERMES_COMPUTER_USE
""")
    # Reattach after executor recreation, then prove dependency loss gives a
    # scoped error rather than consulting the gateway's local desktop packages.
    smoke.python('hermes', "from tools.bot_desktop import runtime; assert runtime.start().running")
    smoke.compose('stop', 'executor')
    smoke.python('hermes', """from tools.computer_use.tool import check_computer_use_requirements
from tools.bot_desktop import runtime
assert not check_computer_use_requirements()
try: runtime.start()
except (OSError,RuntimeError) as e: assert 'SSH' in str(e) or 'sandbox' in str(e) or 'executor' in str(e), str(e)
else: raise AssertionError('desktop started with executor stopped')
""")
    smoke.compose('up', '-d', '--wait', '--no-deps', 'executor')
    smoke.python('hermes', "from tools.bot_desktop import runtime; assert runtime.start().running")
    assert json.loads(smoke.python('executor', proof).stdout) == original
    print('PASS: on/off/on builds preserve executor identity, workspace and browser state; SSH loss refuses desktop and restart recovers', flush=True)


if __name__ == '__main__':
    import sys
    os.environ['COMPUTER_USE_ENABLED'] = 'true'
    if '--desktop-only' not in sys.argv:
        smoke.main()
    else:
        with smoke.storage_fixture():
            failed = True
            try:
                smoke.start_stack()
                check()
                switching_checks()
                failed = False
            except Exception:
                print(smoke.compose('logs', '--tail', '10', 'executor', check=False).stdout)
                raise
            finally:
                if not failed or os.getenv('KEEP_FAILED_TEST_STACK') != '1':
                    smoke.compose('down', '--volumes', '--remove-orphans', check=False)
