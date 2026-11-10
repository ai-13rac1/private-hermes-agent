"""Plugin management preserves native consent and the agent UID/network scope."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('plugin_command', ROOT / 'scripts/plugins.py')
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class PluginCommandTests(unittest.TestCase):
    def test_native_arguments_are_forwarded_without_automatic_consent_or_force(self):
        with patch.object(cli, 'maintenance_compose', return_value=['docker', 'compose']), \
                patch.object(cli.subprocess, 'check_output', return_value='agent-container\n'), \
                patch.object(cli.subprocess, 'run', return_value=subprocess.CompletedProcess([], 17)) as run, \
                patch.object(sys.stdin, 'isatty', return_value=False), patch.object(sys.stdout, 'isatty', return_value=False), \
                patch.object(sys, 'argv', ['plugins.py', 'install', 'owner/repo']):
            with self.assertRaises(SystemExit) as stopped:
                cli.main()
        self.assertEqual(stopped.exception.code, 17)
        self.assertEqual(run.call_args.args[0], ['docker', 'compose', 'exec', '-T', '--user', '10000:10000',
                         'hermes', '/opt/hermes/.venv/bin/hermes', 'plugins', 'install', 'owner/repo'])

    def test_stopped_agent_does_not_start_a_container_or_run_plugin_code(self):
        with patch.object(cli, 'maintenance_compose', return_value=['docker', 'compose']), \
                patch.object(cli.subprocess, 'check_output', return_value=''), patch.object(cli.subprocess, 'run') as run:
            with self.assertRaisesRegex(SystemExit, 'make up'):
                cli.main()
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
