"""Verify operator config preservation and Compose credential separation."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('init_config', ROOT / 'scripts/init-config.py')
init_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(init_config)


class OperatorConfigurationTests(unittest.TestCase):
    def seed(self, root):
        (root / '.env.example').write_text('VENICE_API_KEY=\nBASE_RPC_URL=\n')
        defaults = root / 'components/network'
        defaults.mkdir(parents=True)
        (defaults / 'mcp-allowlist.json').write_text('[]\n')

    def test_existing_settings_survive_initialization_and_repeated_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.seed(root)
            original = '# Preserve quoted settings\nVENICE_API_KEY="private value"\nOTHER_SETTING=yes\n'
            (root / '.env').write_text(original)
            (root / '.env').chmod(0o640)
            policy = root / 'config/network/mcp-allowlist.json'
            policy.parent.mkdir(parents=True)
            custom = '[{"ip":"10.203.84.10","port":8000}]\n'
            policy.write_text(custom)
            init_config.initialize(root)
            first = (root / '.env').read_text()
            auth = (root / 'config/webapp/auth.json').read_bytes()
            password = (root / 'config/webapp/password').read_bytes()
            self.assertEqual(first, original)
            init_config.initialize(root)
            self.assertEqual((root / '.env').read_text(), first)
            self.assertEqual((root / 'config/webapp/auth.json').read_bytes(), auth)
            self.assertEqual((root / 'config/webapp/password').read_bytes(), password)
            self.assertEqual(policy.read_text(), custom)
            self.assertEqual((root / '.env').stat().st_mode & 0o777, 0o640)

    def test_fresh_initialization_copies_defaults_and_protects_env(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.seed(root)
            init_config.initialize(root)
            self.assertEqual((root / '.env').read_text(), (root / '.env.example').read_text())
            self.assertEqual((root / '.env').stat().st_mode & 0o777, 0o600)
            self.assertEqual((root / 'config/network/mcp-allowlist.json').read_text(), '[]\n')
            for name in ('auth.json', 'password'):
                self.assertEqual((root / 'config/webapp' / name).stat().st_mode & 0o777, 0o600)
            # Verify the saved password actually matches the native hash.
            import base64, hashlib
            credentials = json.loads((root / 'config/webapp/auth.json').read_text())
            password = (root / 'config/webapp/password').read_text().strip()
            _, n, r, p, salt, digest = credentials['password_hash'].split('$')
            calculated = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt),
                                         n=int(n), r=int(r), p=int(p), dklen=32)
            self.assertEqual(calculated, base64.b64decode(digest))

    def test_compose_passes_credentials_only_to_their_intended_services(self):
        provider_keys = ('VENICE_API_KEY', 'NEARAI_API_KEY', 'CHUTES_API_KEY',
                         'TINFOIL_API_KEY', 'NANOGPT_API_KEY', 'PHALA_API_KEY')
        secrets = {key: 'test-only-' + key for key in (*provider_keys, 'BASE_RPC_URL', 'TS_AUTHKEY')}
        environment = dict(os.environ, **secrets)
        result = subprocess.run(['docker', 'compose', '-f', 'compose.yaml', '-f', 'compose.funnel.yaml', '--profile', '*', 'config', '--format', 'json'],
                                cwd=ROOT, env=environment, text=True,
                                capture_output=True, check=True)
        services = json.loads(result.stdout)['services']
        for name, service in services.items():
            supplied = service.get('environment', {})
            expected = set(provider_keys) if name == 'teep' else {'BASE_RPC_URL'} if name in ('x402_treazury', 'x402_treazury-admin', 'x402_treazury-job') else {'TS_AUTHKEY'} if name == 'tailscale' else set()
            self.assertEqual(set(secrets) & set(supplied), expected, name)
            for key in expected:
                self.assertEqual(supplied[key], secrets[key])
            self.assertNotIn('env_file', service)
        auth_recipients = [name for name, service in services.items()
                           if any(mount.get('target') == '/run/webapp/auth.json'
                                  for mount in service.get('volumes', []))]
        self.assertEqual(auth_recipients, ['bootstrap'])
        self.assertNotIn('webapp-setup', services)
        self.assertIn('webapp-proxy', services)
        self.assertEqual(services['x402_treazury-job']['restart'], 'no')
        self.assertEqual(services['x402_treazury-job']['stop_grace_period'], '-1s')
        self.assertEqual(services['hermes']['image'], services['configure']['image'])
        self.assertTrue(services['hermes']['image'].startswith('nousresearch/hermes-agent@sha256:'))


if __name__ == '__main__':
    unittest.main()
