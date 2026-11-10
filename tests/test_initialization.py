"""Recover interrupted file publication without replacing authoritative identities."""
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'components/webapp'))
import auth

spec = importlib.util.spec_from_file_location('bootstrap_keys', ROOT / 'components/provisioning/bootstrap.py')
bootstrap = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'hermes_yaml': Mock()}):
    spec.loader.exec_module(bootstrap)


class CredentialRetryTests(unittest.TestCase):
    def test_interruption_before_auth_publish_reuses_saved_password(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_write = auth.write_private
            def interrupt(path, value):
                if path.name == 'auth.json':
                    raise OSError('interrupted before auth publication')
                real_write(path, value)
            with patch.object(auth, 'write_private', side_effect=interrupt):
                with self.assertRaises(OSError):
                    auth.initialize_credentials(root)
            password = (root / 'config/webapp/password').read_bytes()
            self.assertTrue(auth.initialize_credentials(root))
            self.assertEqual((root / 'config/webapp/password').read_bytes(), password)
            credentials = json.loads((root / 'config/webapp/auth.json').read_text())
            self.assertTrue(auth.password_matches(password.decode().strip(), credentials['password_hash']))
            original = (root / 'config/webapp/auth.json').read_bytes()
            self.assertFalse(auth.initialize_credentials(root))
            self.assertEqual((root / 'config/webapp/auth.json').read_bytes(), original)
            for name in ('password', 'auth.json'):
                self.assertEqual((root / 'config/webapp' / name).stat().st_mode & 0o777, 0o600)

    def test_interrupted_rotation_reconciles_saved_password_without_changing_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            auth.initialize_credentials(root)
            path = root / 'config/webapp/auth.json'
            original = path.read_bytes()
            real_write = auth.write_private
            def interrupt(destination, value):
                if destination == path:
                    raise OSError('interrupted')
                real_write(destination, value)
            with patch.object(auth, 'write_private', side_effect=interrupt), self.assertRaises(OSError):
                auth.initialize_credentials(root, rotate=True)
            self.assertEqual(path.read_bytes(), original)
            password = (path.parent / 'password').read_text().strip()
            auth.initialize_credentials(root)
            repaired = json.loads(path.read_text())
            self.assertEqual(repaired['secret'], json.loads(original)['secret'])
            self.assertTrue(auth.password_matches(password, repaired['password_hash']))
            auth.initialize_credentials(root, rotate=True)
            self.assertNotEqual(json.loads(path.read_text())['secret'], repaired['secret'])

    def test_failed_atomic_publication_preserves_old_file_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private'
            path.write_text('existing value')
            with patch.object(auth.os, 'replace', side_effect=OSError('interrupted')), self.assertRaises(OSError):
                auth.write_private(path, 'new value')
            self.assertEqual(path.read_text(), 'existing value')
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_missing_password_preserves_usable_auth_and_explains_optional_rotation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            auth.initialize_credentials(root)
            path = root / 'config/webapp/auth.json'
            original = path.read_bytes()
            (path.parent / 'password').unlink()
            warning = io.StringIO()
            with contextlib.redirect_stderr(warning):
                self.assertFalse(auth.initialize_credentials(root))
            self.assertIn('authentication remains usable', warning.getvalue())
            self.assertIn('make webapp-rotate', warning.getvalue())
            self.assertEqual(path.read_bytes(), original)
            auth.initialize_credentials(root, rotate=True)
            self.assertNotEqual(path.read_bytes(), original)


class SSHKeyRetryTests(unittest.TestCase):
    def test_missing_public_sidecar_preserves_private_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory) / 'id_ed25519'
            bootstrap.key(private)
            original = private.read_bytes()
            public = private.with_name(private.name + '.pub')
            identity = public.read_text().split()[:2]
            public.unlink()
            bootstrap.key(private)
            self.assertEqual(private.read_bytes(), original)
            self.assertEqual(public.read_text().split()[:2], identity)
            complete = public.read_bytes()
            bootstrap.key(private)
            self.assertEqual(public.read_bytes(), complete)
            private.write_text('invalid private key')
            public.unlink()
            with self.assertRaises(subprocess.CalledProcessError):
                bootstrap.key(private)
            self.assertEqual(private.read_text(), 'invalid private key')
            self.assertFalse(public.exists())
