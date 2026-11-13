"""Validate the same interpolation inputs that Compose passthrough launches."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import deployment
import stack


class PassthroughSettingsTests(unittest.TestCase):
    def setUp(self):
        self.provider = deployment.compose_base()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for name in ('compose.yaml', 'compose.executor.yaml', 'compose.funnel.yaml',
                     'compose.podman.yaml', 'compose.podman.funnel.yaml'):
            shutil.copyfile(ROOT / name, self.root / name)
        self.environment = dict(os.environ)
        for name in tuple(self.environment):
            if name.startswith(('WEBAPP_', 'TAILSCALE_', 'TEEP_', 'COMPOSE_')):
                self.environment.pop(name)
        self.environment['COMPUTER_USE_ENABLED'] = 'false'

    def launch(self, selected, arguments, error=None):
        # The selected provider renders both engine models without launching them.
        # The final launch and network mutation are mocked, not model parsing.
        with patch.dict(os.environ, self.environment, clear=True), \
                patch.object(deployment, 'ROOT', self.root), \
                patch.object(deployment, 'engine', return_value=selected), \
                patch.object(deployment, 'compose_base', return_value=self.provider), \
                patch.object(stack, 'compose_base', return_value=self.provider), \
                patch.object(sys, 'argv', ['stack.py', 'compose', *arguments]), \
                patch.object(stack, 'run') as run, patch.object(stack, 'prepare_launch') as prepare, patch.object(stack, 'check_bind_sources'):
            if error:
                with self.assertRaisesRegex(ValueError, error):
                    stack.main_unlocked()
                run.assert_not_called()
                prepare.assert_not_called()
                return
            stack.main_unlocked()
            command = run.call_args.args[0]
            model = json.loads(subprocess.check_output([*command[:-1], 'config', '--format', 'json'],
                                                      cwd=self.root, text=True))
        if '--dry-run' in arguments:
            prepare.assert_not_called()
        else:
            self.assertEqual(prepare.call_args.args[0], command[:-1])
        return command, model

    def test_supplied_inputs_choose_funnel_for_both_engine_models(self):
        for selected in ('docker', 'podman'):
            for source in ('env-file', 'project-directory', 'file'):
                with self.subTest(engine=selected, source=source):
                    (self.root / '.env').write_text('TAILSCALE_FUNNEL_ENABLED=false\n')
                    inputs = self.root / 'inputs'
                    inputs.mkdir(exist_ok=True)
                    content = ('TAILSCALE_FUNNEL_ENABLED=true\n'
                               'TAILSCALE_FUNNEL_HOST=fixture.example.ts.net\n')
                    if source == 'env-file':
                        (inputs / 'alternate.env').write_text(content)
                        arguments = ['--env-file', str(inputs / 'alternate.env')]
                        # Unrelated root policy must not veto this valid file.
                        (self.root / '.env').write_text('WEBAPP_BIND=invalid\n')
                    elif source == 'project-directory':
                        (inputs / '.env').write_text(content)
                        shutil.copyfile(self.root / 'compose.executor.yaml', inputs / 'compose.executor.yaml')
                        arguments = ['--project-directory', str(inputs)]
                    else:
                        override = inputs / 'policy.yaml'
                        override.write_text('x-deployment:\n  funnel_enabled: "true"\n'
                                            '  funnel_host: fixture.example.ts.net\n')
                        arguments = ['-f', str(override)]
                    command, model = self.launch(selected, [*arguments, 'up'])
                    self.assertIn('compose.funnel.yaml', command)
                    self.assertIn('tailscale', model['services'])
                    self.assertIn('funnel-link', model['networks'])
                    if selected == 'podman':
                        files = [v for k, v in zip(command, command[1:]) if k == '-f']
                        self.assertEqual(files[-2:], ['compose.podman.yaml', 'compose.podman.funnel.yaml'])

    def test_alternate_non_loopback_binding_is_rejected_before_launch(self):
        (self.root / '.env').write_text('WEBAPP_BIND=127.0.0.1\n')
        alternate = self.root / 'alternate.env'
        alternate.write_text('WEBAPP_BIND=0.0.0.0\n')
        for selected in ('docker', 'podman'):
            with self.subTest(engine=selected):
                self.launch(selected, ['--env-file', str(alternate), 'up'], 'IPv4 loopback')

    def test_dry_run_validates_supplied_inputs_without_preparation(self):
        (self.root / '.env').write_text('WEBAPP_BIND=invalid\n')
        alternate = self.root / 'alternate.env'
        alternate.write_text('WEBAPP_BIND=127.0.0.1\nWEBAPP_PORT=19120\n')
        for selected in ('docker', 'podman'):
            with self.subTest(engine=selected):
                _, model = self.launch(selected, ['--dry-run', '--env-file', str(alternate), 'up'])
                self.assertEqual(model['services']['webapp-proxy']['ports'][0]['published'], '19120')
