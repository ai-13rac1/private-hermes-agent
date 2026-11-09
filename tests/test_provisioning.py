"""Setup failure must block startup; wallet status must remain independent."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import provisioning


class ProvisioningTests(unittest.TestCase):
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

    def test_wallet_maintenance_reuses_successful_setup_without_initializing_again(self):
        with patch.object(provisioning.subprocess, 'run') as run, \
                patch.object(provisioning.subprocess, 'check_output', side_effect=[
                    'setup-id\n', json.dumps({'Status': 'exited', 'ExitCode': 0})]):
            provisioning.ensure_storage(['docker', 'compose'])
        run.assert_not_called()

    def test_failed_or_absent_setup_only_prepares_storage_for_wallet_maintenance(self):
        for results in ([''], ['setup-id\n', json.dumps({'Status': 'exited', 'ExitCode': 1})]):
            with self.subTest(results=results), patch.object(provisioning.subprocess, 'run') as run, \
                    patch.object(provisioning.subprocess, 'check_output', side_effect=results):
                provisioning.ensure_storage(['docker', 'compose'])
                self.assertEqual(run.call_args.args[0][-2:], ['setup', 'storage'])


if __name__ == '__main__':
    unittest.main()
