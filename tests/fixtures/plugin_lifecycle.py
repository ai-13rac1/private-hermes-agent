"""Disposable native-plugin lifecycle fixture; executed as UID 10000 in Hermes."""
import base64
import hashlib
from pathlib import Path
import subprocess
import sys
import zipfile

HOME = Path('/opt/data')
SOURCE = HOME / 'qualification-plugin-source'
NAME = 'qualification-plugin'
WHEEL = HOME / 'private_hermes_fixture_dep-1.0-py3-none-any.whl'


def git(*args):
    return subprocess.check_output(['git', '-C', str(SOURCE), *args], text=True).strip()


def version(number):
    (SOURCE / 'plugin.yaml').write_text(f'name: {NAME}\nversion: "{number}.0"\ndescription: Harmless persistence qualification\nprovides_hooks: [on_session_start]\n')
    (SOURCE / '__init__.py').write_text(f'''from private_hermes_fixture_dep import VALUE
def report(**kwargs):
    return "qualification-v{number}-" + VALUE
def register(ctx):
    ctx.register_hook("on_session_start", report)
''')
    (SOURCE / 'pyproject.toml').write_text(f'''[project]
name = "private-hermes-qualification-plugin"
version = "{number}.0"
dependencies = ["private-hermes-fixture-dep==1.0"]
[tool.uv.sources]
private-hermes-fixture-dep = {{path = "{WHEEL}"}}
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"
[tool.setuptools]
py-modules = []
''')
    git('add', '.')
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        'commit', '-m', f'Qualification version {number}')


def create():
    from hermes_cli.config import load_config, read_raw_config
    from hermes_cli.observability.shared_metrics_consent import consent_state
    from hermes_cli.observability.shared_metrics_send_config import resolve_send_config
    config = load_config()
    consent = consent_state(read_raw_config())
    assert consent['decided'] and not consent['enabled'] and not consent['send']
    resolved = resolve_send_config(config)
    assert not resolved.enabled and not resolved.send
    assert config['plugins']['auto_update_check_hours'] == 24
    assert config['plugins']['auto_apply'] is False
    print('PASS: native metrics collection/upload are disabled independently of plugin update notifications')
    files = {'private_hermes_fixture_dep.py': b'VALUE = "dependency-loaded"\n',
             'private_hermes_fixture_dep-1.0.dist-info/METADATA': b'Metadata-Version: 2.1\nName: private-hermes-fixture-dep\nVersion: 1.0\n',
             'private_hermes_fixture_dep-1.0.dist-info/WHEEL': b'Wheel-Version: 1.0\nGenerator: private-hermes-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n'}
    record = ''.join(f"{name},sha256={base64.urlsafe_b64encode(hashlib.sha256(body).digest()).decode().rstrip('=')},{len(body)}\n"
                     for name, body in files.items())
    record += 'private_hermes_fixture_dep-1.0.dist-info/RECORD,,\n'
    with zipfile.ZipFile(WHEEL, 'w') as wheel:
        for name, body in files.items():
            wheel.writestr(name, body)
        wheel.writestr('private_hermes_fixture_dep-1.0.dist-info/RECORD', record)
    SOURCE.mkdir()
    git('init', '-b', 'main')
    version(1)


def proof(number):
    from pm.environments import activate_dependencies, committed_venv
    root = Path('/opt/hermes')
    activate_dependencies(root)
    selected = committed_venv(root)
    assert selected and selected.is_relative_to(HOME / 'installs'), selected
    from private_hermes_fixture_dep import VALUE
    assert VALUE == 'dependency-loaded'
    from hermes_cli.plugins import discover_plugins, invoke_hook
    discover_plugins(force=True)
    assert f'qualification-v{number}-dependency-loaded' in invoke_hook('on_session_start')
    assert (HOME / 'plugins' / NAME / 'plugin.yaml').is_file()
    print(f'PASS: plugin v{number} and its fixture dependency load from persistent state')


if sys.argv[1] == 'create':
    create()
elif sys.argv[1] == 'update':
    version(2)
else:
    proof(int(sys.argv[1]))
