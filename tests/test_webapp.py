"""Ingress selection, exact hosts, credential format and Funnel publication gates."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'components/webapp'))
from settings import Settings, proxy_config
from auth import hash_password, validate

spec = importlib.util.spec_from_file_location('funnel', ROOT / 'components/tailscale/funnel.py')
funnel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(funnel)


def values(**changes):
    defaults = dict(funnel_enabled='false', webapp_bind='127.0.0.1',
                    webapp_port='9120', webapp_username='admin', funnel_host='',
                    funnel_port='443', tailscale_hostname='private-hermes')
    return {**defaults, **changes}



class WebappTests(unittest.TestCase):
    def test_invalid_or_inconsistent_settings_refuse_activation(self):
        for change in ({'funnel_enabled': '1'},
                       {'webapp_bind': '0.0.0.0'}, {'webapp_port': '9120;evil'},
                       {'funnel_enabled': 'true'}, {'funnel_host': '*.example.ts.net'},
                       {'funnel_host': 'example.ts.net\nattack'}, {'funnel_port': '80'},
                       {'webapp_username': 'admin\nuser'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                Settings.read(values(**change))

    def test_proxy_keeps_authorities_separate_and_removes_all_forwarded_headers(self):
        text = proxy_config(Settings.read(values()))
        self.assertIn('127.0.0.1:9120', text)
        self.assertNotIn('bind 10.203.87.3:8443', text)
        self.assertIn('http-request del-header x-forwarded- -m beg', text)
        self.assertIn('http-request del-header Forwarded', text)
        self.assertNotIn('option forwardfor', text)
        text = proxy_config(Settings.read(values(funnel_enabled='true', funnel_host='test.example.ts.net')))
        self.assertIn('test.example.ts.net:443 test.example.ts.net', text)
        self.assertIn('X-Forwarded-Proto https', text)
        self.assertIn('server agent 10.203.85.2:9120', text)

    def test_generated_native_hash_format_and_signing_secret_are_validated(self):
        credentials = {'password_hash': hash_password('disposable test password'), 'secret': 's' * 64}
        self.assertEqual(validate(credentials), credentials)
        with self.assertRaises(ValueError):
            validate({**credentials, 'secret': 'short'})

    def test_disabled_funnel_never_starts_containerboot(self):
        with patch.dict(funnel.os.environ, {'TAILSCALE_FUNNEL_ENABLED': 'false'}), patch.object(funnel.subprocess, 'Popen') as spawn:
            with self.assertRaises(SystemExit):
                funnel.main()
            spawn.assert_not_called()

    def test_funnel_checks_dns_before_publication_and_resets_on_shutdown(self):
        for actual, expected_error in [('wrong.example.ts.net', RuntimeError), ('test.example.ts.net', KeyboardInterrupt)]:
            child = Mock()
            child.poll.return_value = None
            commands = []
            def cli(*args, **kwargs):
                commands.append(args)
                return Mock(returncode=0, stdout=json.dumps({'BackendState': 'Running', 'Self': {'DNSName': actual + '.'}}))
            environment = {'TAILSCALE_FUNNEL_ENABLED': 'true', 'TAILSCALE_FUNNEL_HOST': 'test.example.ts.net',
                           'TAILSCALE_FUNNEL_PORT': '443', 'TS_AUTHKEY': 'test-only-key'}
            with patch.dict(funnel.os.environ, environment), patch.object(funnel.subprocess, 'Popen', return_value=child), patch.object(funnel, 'cli', side_effect=cli), patch.object(funnel, 'publish') as publish, patch.object(funnel.signal, 'signal'), patch.object(funnel.time, 'sleep', side_effect=KeyboardInterrupt):
                with self.assertRaises(expected_error):
                    funnel.main()
                writes = [call.args[0] for call in publish.call_args_list]
                self.assertEqual(writes[0], {})
                self.assertEqual(writes[-1], {})
                if actual.startswith('wrong'):
                    self.assertEqual(len(writes), 2)
                else:
                    self.assertEqual(writes[1], funnel.serve_config(actual, 443))
                self.assertIn(('funnel', 'reset'), commands)
                child.terminate.assert_called_once()


class ShutdownTests(unittest.TestCase):
    def test_shutdown_ignores_invalid_activation_settings_and_still_runs_down_after_reset_failure(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        import stack
        import os
        def selected():
            self.assertEqual(os.environ['TAILSCALE_FUNNEL_ENABLED'], 'false')
            return Settings.read(values())
        with patch.dict(os.environ, {'TAILSCALE_FUNNEL_ENABLED':'bad'}), patch.object(sys,'argv',['stack.py','down']), patch.object(stack,'settings',side_effect=selected), patch.object(stack,'stop_funnel',side_effect=RuntimeError('test reset failure')), patch.object(stack,'run') as run:
            with self.assertRaises(RuntimeError):
                stack.main()
            self.assertIn('down', run.call_args.args[0])
            self.assertNotIn('--volumes', run.call_args.args[0])
            self.assertNotIn('-v', run.call_args.args[0])

    def test_startup_reprovisions_auth_before_gateway_without_starting_funnel(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        import stack
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            auth_path = root / 'config/webapp/auth.json'
            auth_path.parent.mkdir(parents=True)
            credentials = {'password_hash':hash_password('test-only-password'),'secret':'s'*64}
            auth_path.write_text(json.dumps(credentials))
            with patch.object(sys,'argv',['stack.py','up']), patch.object(stack,'ROOT',root), patch.object(stack,'settings',return_value=Settings.read(values())), patch.object(stack,'render'), patch.object(stack,'stop_funnel') as disable, patch.object(stack,'run') as run, patch.object(stack,'Controller'):
                stack.main()
                commands = [call.args[0] for call in run.call_args_list]
                bootstrap = next(i for i,c in enumerate(commands) if '--force-recreate' in c and c[-1]=='bootstrap')
                gateway = next(i for i,c in enumerate(commands) if '--force-recreate' in c and c[-1]=='hermes')
                self.assertLess(bootstrap,gateway)
                self.assertTrue(any('--force-recreate' in c and 'webapp-proxy' in c for c in commands))
                self.assertFalse(any('up' in c and 'tailscale' in c for c in commands))
                self.assertNotIn(credentials['secret'],json.dumps(commands))
                disable.assert_called_once()
