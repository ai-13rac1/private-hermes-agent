"""Setup failure must block startup; wallet status must remain independent."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import provisioning


class ProvisioningTests(unittest.TestCase):
    def test_diff_direction_and_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'config/x402_treazury/research_desk.toml'
            path.parent.mkdir(parents=True)
            path.write_text('cap = 2\n')
            path.chmod(0o640)
            output = io.StringIO()
            with patch.object(provisioning, 'packaged_research_config', return_value=b'cap = 1\n'), redirect_stdout(output):
                provisioning.research_config_diff([], folder)
            self.assertIn('--- packaged default', output.getvalue())
            self.assertIn('+++ saved config', output.getvalue())
            self.assertIn('-cap = 1\n+cap = 2', output.getvalue())
            self.assertEqual(path.read_text(), 'cap = 2\n')
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            self.assertEqual(list(path.parent.iterdir()), [path])
            with patch.object(provisioning, 'packaged_research_config', return_value=b'cap = 2\n'), redirect_stdout(output := io.StringIO()):
                provisioning.research_config_diff([], folder)
            self.assertIn('matches packaged defaults', output.getvalue())

    def test_diff_failure_is_visible_and_only_automatic_report_is_advisory(self):
        error = provisioning.subprocess.CalledProcessError(1, ['docker'])
        for failure in (FileNotFoundError('missing saved config'), error):
            with self.subTest(failure=failure), patch.object(provisioning, 'research_config_diff', side_effect=failure):
                with redirect_stderr(output := io.StringIO()):
                    provisioning.report_research_config_diff([])
                self.assertIn('comparison unavailable', output.getvalue())
                self.assertIn('make x402_treazury-config-diff', output.getvalue())
                with self.assertRaises(type(failure)):
                    provisioning.research_config_diff([])

    def test_research_config_seed_preserves_operator_file_and_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            model = json.dumps({'services': {'x402_treazury': {'image': 'test-image'}}})
            with patch.object(provisioning.subprocess, 'check_output', side_effect=[model, b'version=1\n']) as call:
                provisioning.initialize_research_config(['docker', 'compose'], root)
            extraction = call.call_args.args[0]
            self.assertIn('none', extraction)
            self.assertNotIn('--volume', extraction)
            path = root / 'config/x402_treazury/research_desk.toml'
            self.assertEqual(path.read_text(), 'version=1\n')
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)
            path.write_text('# operator edit\n')
            path.chmod(0o640)
            with patch.object(provisioning.subprocess, 'check_output') as call:
                provisioning.initialize_research_config(['docker', 'compose'], root)
            call.assert_not_called()
            self.assertEqual(path.read_text(), '# operator edit\n')
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_failed_extraction_does_not_create_config_and_can_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            model = json.dumps({'services': {'x402_treazury': {'image': 'test-image'}}})
            error = provisioning.subprocess.CalledProcessError(1, ['docker'])
            with patch.object(provisioning.subprocess, 'check_output', side_effect=[model, error]):
                with self.assertRaises(provisioning.subprocess.CalledProcessError):
                    provisioning.initialize_research_config(['docker', 'compose'], root)
            self.assertFalse((root / 'config/x402_treazury/research_desk.toml').exists())

    def test_failed_canonical_setup_reports_logs_and_exit_code(self):
        with patch.object(provisioning.subprocess, 'run') as run, \
                patch.object(provisioning.subprocess, 'check_output', side_effect=['setup-id\n', '7\n']):
            with self.assertRaisesRegex(RuntimeError, 'Offline setup failed.*exit 7'):
                provisioning.initialize_setup(['docker', 'compose'])
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0][-1], 'setup')
        self.assertEqual(run.call_args_list[1].args[0][-4:], ['logs', '--tail', '40', 'setup'])



if __name__ == '__main__':
    unittest.main()
