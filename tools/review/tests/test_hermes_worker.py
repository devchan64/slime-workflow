import json
import os
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import Mock, patch

from tools.review.domains.hermes_agent import worker as hermes_worker_module
from tools.review.domains.hermes_agent import runtime_integrity as hermes_runtime_module


class HermesWorkerTests(unittest.TestCase):
    def setUp(self):
        current_trial_directory = tempfile.TemporaryDirectory()
        self.addCleanup(current_trial_directory.cleanup)
        current_trial_root = Path(current_trial_directory.name)
        current_python_path = current_trial_root / '.venv/bin/python'
        current_python_path.parent.mkdir(parents=True)
        current_python_path.touch()
        current_root_patch = patch.object(hermes_worker_module, 'WORKFLOW_ROOT_DIRECTORY', current_trial_root)
        current_root_patch.start()
        self.addCleanup(current_root_patch.stop)

    def test_changed_audit_runner_blocks_independent_verification(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_job_path = Path(hermes_temporary_root) / 'job'
            hermes_job_path.mkdir()
            (hermes_job_path / 'request.json').write_text(json.dumps({'prompt':'test', 'verification_modules':['tools.review.tests.test_hermes_service']}))
            hermes_runtime_path = Path(hermes_temporary_root) / 'runtime'
            hermes_runtime_path.mkdir()
            (hermes_runtime_path / 'prepared.json').write_text(json.dumps({'server_binary_sha256':'digest', 'runtime_library_paths':[]}))
            hermes_server_mock = Mock()
            hermes_agent_mock = Mock()
            hermes_agent_mock.wait.return_value = 0
            def create_mock_workspace(source_repository_path, snapshot_workspace_path):
                snapshot_workspace_path.mkdir()
                return {'baseline_commit':'a' * 40}
            hermes_previous_directory = os.getcwd()
            try:
                with patch.object(hermes_worker_module, 'RUNTIME_INSTALL_ROOT', hermes_runtime_path), patch.object(hermes_worker_module, 'wait_hermes_gpu_reservation'), patch.object(hermes_worker_module, 'verify_hermes_model_integrity'), patch.object(hermes_worker_module, 'verify_hermes_runtime_integrity'), patch.object(hermes_worker_module, 'calculate_file_digest', return_value='digest'), patch.object(hermes_worker_module, 'copy_snapshot_source_files', side_effect=create_mock_workspace), patch.object(hermes_worker_module, 'hash_hermes_verification_controls', side_effect=[{'runner':'before'}, {'runner':'after'}]), patch.object(hermes_worker_module, 'collect_snapshot_change_diff', return_value=b'diff'), patch.object(hermes_worker_module.subprocess, 'Popen', side_effect=[hermes_server_mock, hermes_agent_mock]), patch.object(hermes_worker_module, 'wait_worker_model_ready', return_value='offloaded 1/1 layers to GPU'), patch.object(hermes_worker_module.threading.Thread, 'start'), patch.object(hermes_worker_module, 'execute_hermes_independent_verification') as hermes_verify_mock:
                    with self.assertRaisesRegex(RuntimeError, '실행기가 변경'):
                        hermes_worker_module.execute_hermes_gpu_job(hermes_job_path)
                    hermes_verify_mock.assert_not_called()
            finally:
                os.chdir(hermes_previous_directory)
            hermes_result_record = json.loads((hermes_job_path / 'result.json').read_text())
            self.assertEqual(hermes_result_record['verification']['status'], 'failed')
            self.assertTrue(hermes_result_record['partial'])

    def test_verification_control_hashes_detect_changes_and_symlinks(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_workspace_path = Path(hermes_temporary_root)
            hermes_control_path = hermes_workspace_path / 'tools/review/tests'
            hermes_control_path.mkdir(parents=True)
            (hermes_control_path / 'run_management_audit.py').write_text('original')
            (hermes_control_path / 'run_music_regression.py').write_text('original')
            hermes_original_hashes = hermes_worker_module.hash_hermes_verification_controls(hermes_workspace_path)
            (hermes_control_path / 'run_music_regression.py').write_text('changed')
            self.assertNotEqual(hermes_original_hashes, hermes_worker_module.hash_hermes_verification_controls(hermes_workspace_path))
            (hermes_control_path / 'run_music_regression.py').unlink()
            (hermes_control_path / 'run_music_regression.py').symlink_to('/etc/passwd')
            with self.assertRaisesRegex(ValueError, '심볼릭 링크'):
                hermes_worker_module.hash_hermes_verification_controls(hermes_workspace_path)

    def test_verification_failure_marks_agent_output_partial(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_job_path = Path(hermes_temporary_root) / 'job'
            hermes_job_path.mkdir()
            hermes_module_values = ['tools.review.tests.test_hermes_service']
            (hermes_job_path / 'request.json').write_text(json.dumps({'prompt':'test', 'verification_modules':hermes_module_values}))
            hermes_runtime_path = Path(hermes_temporary_root) / 'runtime'
            hermes_runtime_path.mkdir()
            (hermes_runtime_path / 'prepared.json').write_text(json.dumps({'server_binary_sha256':'digest', 'runtime_library_paths':[]}))
            hermes_server_mock = Mock()
            hermes_agent_mock = Mock()
            hermes_agent_mock.wait.return_value = 0
            hermes_baseline_record = {'baseline_commit':'a' * 40}
            def create_mock_workspace(source_repository_path, snapshot_workspace_path):
                snapshot_workspace_path.mkdir()
                return hermes_baseline_record
            def fail_mock_verification(*verification_argument_values):
                hermes_server_mock.terminate.assert_called_once()
                return {'status':'failed', 'modules':hermes_module_values, 'exit_code':1}
            hermes_previous_directory = os.getcwd()
            try:
                with patch.dict(os.environ, {'HERMES_PRIVATE_TEST_VALUE':'must-not-inherit', 'SLIME_HERMES_PROCESS_TOKEN':'a' * 32}), patch.object(hermes_worker_module, 'RUNTIME_INSTALL_ROOT', hermes_runtime_path), patch.object(hermes_worker_module, 'wait_hermes_gpu_reservation'), patch.object(hermes_worker_module, 'verify_hermes_model_integrity'), patch.object(hermes_worker_module, 'verify_hermes_runtime_integrity'), patch.object(hermes_worker_module, 'calculate_file_digest', return_value='digest'), patch.object(hermes_worker_module, 'copy_snapshot_source_files', side_effect=create_mock_workspace), patch.object(hermes_worker_module, 'hash_hermes_verification_controls', return_value={'runner':'hash'}), patch.object(hermes_worker_module, 'collect_snapshot_change_diff', return_value=b'diff'), patch.object(hermes_worker_module.subprocess, 'Popen', side_effect=[hermes_server_mock, hermes_agent_mock]) as hermes_launch_mock, patch.object(hermes_worker_module, 'wait_worker_model_ready', return_value='offloaded 1/1 layers to GPU'), patch.object(hermes_worker_module.threading.Thread, 'start'), patch.object(hermes_worker_module, 'execute_hermes_independent_verification', side_effect=fail_mock_verification):
                    with self.assertRaisesRegex(RuntimeError, '독립 회귀 검증'):
                        hermes_worker_module.execute_hermes_gpu_job(hermes_job_path)
                    self.assertNotIn('HERMES_PRIVATE_TEST_VALUE', hermes_launch_mock.call_args_list[1].kwargs['env'])
                    self.assertNotIn('SLIME_HERMES_PROCESS_TOKEN', hermes_launch_mock.call_args_list[1].kwargs['env'])
            finally:
                os.chdir(hermes_previous_directory)
            hermes_result_record = json.loads((hermes_job_path / 'result.json').read_text())
            self.assertTrue(hermes_result_record['partial'])
            self.assertEqual(hermes_result_record['verification']['status'], 'failed')
            self.assertEqual((hermes_job_path / 'change.diff').read_bytes(), b'diff')

    def test_independent_verifier_reports_failure_and_timeout(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_job_path = Path(hermes_temporary_root)
            hermes_module_values = ['tools.review.tests.test_hermes_service']
            with patch.dict(os.environ, {'HERMES_PRIVATE_TEST_VALUE':'must-not-inherit'}), patch.object(hermes_worker_module.subprocess, 'run', return_value=Mock(returncode=1)) as hermes_run_mock:
                hermes_result_record = hermes_worker_module.execute_hermes_independent_verification(hermes_job_path, hermes_job_path, hermes_job_path, hermes_module_values)
                self.assertEqual(hermes_result_record['status'], 'failed')
                self.assertEqual(hermes_run_mock.call_args.args[0][-2:], ['--module', hermes_module_values[0]])
                self.assertNotIn('HERMES_PRIVATE_TEST_VALUE', hermes_run_mock.call_args.kwargs['env'])
            with patch.object(hermes_worker_module.subprocess, 'run', side_effect=subprocess.TimeoutExpired('audit', 300)):
                hermes_timeout_record = hermes_worker_module.execute_hermes_independent_verification(hermes_job_path, hermes_job_path, hermes_job_path, hermes_module_values)
                self.assertEqual(hermes_timeout_record['status'], 'timed_out')
                self.assertIn('시간 초과', (hermes_job_path / 'verification.log').read_text())

    def test_worker_requires_matching_gpu_reservation(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_job_path = Path(hermes_temporary_root) / 'job'
            hermes_job_path.mkdir()
            hermes_reservation_path = Path(hermes_temporary_root) / 'reservation.json'
            hermes_start_token = Path('/proc/self/stat').read_text().rpartition(') ')[2].split()[19]
            hermes_process_token = 'a' * 32
            hermes_reservation_path.write_text(json.dumps({'path':str(hermes_job_path), 'service':'hermes-agent', 'worker_pgid':os.getpgrp(), 'worker_start_token':hermes_start_token, 'worker_process_token':hermes_process_token}))
            with patch.dict('os.environ', {'SLIME_GPU_RESERVATION_PATH':str(hermes_reservation_path), 'SLIME_HERMES_PROCESS_TOKEN':hermes_process_token}):
                hermes_worker_module.wait_hermes_gpu_reservation(hermes_job_path)
            with patch.dict('os.environ', {}, clear=True), self.assertRaisesRegex(RuntimeError, '예약 없이'):
                hermes_worker_module.wait_hermes_gpu_reservation(hermes_job_path)

    def test_runtime_rejects_modified_or_untracked_source(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_runtime_path = Path(hermes_temporary_root)
            subprocess.run(['git', 'init', '-q', str(hermes_runtime_path)], check=True)
            subprocess.run(['git', '-C', str(hermes_runtime_path), 'config', 'user.email', 'test@localhost'], check=True)
            subprocess.run(['git', '-C', str(hermes_runtime_path), 'config', 'user.name', 'Test'], check=True)
            (hermes_runtime_path / 'agent.py').write_text('original')
            (hermes_runtime_path / '.gitignore').write_text('.venv/\n')
            subprocess.run(['git', '-C', str(hermes_runtime_path), 'add', 'agent.py', '.gitignore'], check=True)
            subprocess.run(['git', '-C', str(hermes_runtime_path), 'commit', '-qm', 'initial'], check=True)
            hermes_revision_value = subprocess.check_output(['git', '-C', str(hermes_runtime_path), 'rev-parse', 'HEAD'], text=True).strip()
            (hermes_runtime_path / '.venv/bin').mkdir(parents=True)
            (hermes_runtime_path / '.venv/bin/python').write_text('')
            (hermes_runtime_path / 'prepared-local.json').write_text(json.dumps({'revision':hermes_revision_value, 'release':hermes_runtime_module.HERMES_RUNTIME_RELEASE, 'source':hermes_runtime_module.HERMES_RUNTIME_SOURCE}))
            with patch.object(hermes_runtime_module, 'HERMES_RUNTIME_REVISION', hermes_revision_value):
                hermes_runtime_module.verify_hermes_runtime_integrity(hermes_runtime_path)
                (hermes_runtime_path / 'agent.py').write_text('changed')
                with self.assertRaisesRegex(ValueError, '소스에 수정'):
                    hermes_runtime_module.verify_hermes_runtime_integrity(hermes_runtime_path)
                (hermes_runtime_path / 'agent.py').write_text('original')
                (hermes_runtime_path / 'extra.py').write_text('new')
                with self.assertRaisesRegex(ValueError, '소스에 수정'):
                    hermes_runtime_module.verify_hermes_runtime_integrity(hermes_runtime_path)

    def test_interrupted_model_start_preserves_partial_diff(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_job_path = Path(hermes_temporary_root) / 'job'
            hermes_job_path.mkdir()
            (hermes_job_path / 'request.json').write_text('{"prompt":"test"}')
            hermes_runtime_path = Path(hermes_temporary_root) / 'runtime'
            hermes_runtime_path.mkdir()
            (hermes_runtime_path / 'prepared.json').write_text(json.dumps({'server_binary_sha256':'digest', 'runtime_library_paths':[]}))
            hermes_agent_path = Path(hermes_temporary_root) / 'agent'
            (hermes_agent_path / '.venv/bin').mkdir(parents=True)
            (hermes_agent_path / '.venv/bin/python').write_text('')
            hermes_baseline_record = {'baseline_commit':'a' * 40}
            hermes_server_mock = Mock()
            def create_mock_workspace(source_repository_path, snapshot_workspace_path):
                snapshot_workspace_path.mkdir()
                return hermes_baseline_record
            with patch.object(hermes_worker_module, 'RUNTIME_INSTALL_ROOT', hermes_runtime_path), patch.object(hermes_worker_module, 'HERMES_RUNTIME_DIRECTORY', hermes_agent_path), patch.object(hermes_worker_module, 'wait_hermes_gpu_reservation'), patch.object(hermes_worker_module, 'verify_hermes_model_integrity'), patch.object(hermes_worker_module, 'verify_hermes_runtime_integrity'), patch.object(hermes_worker_module, 'calculate_file_digest', return_value='digest'), patch.object(hermes_worker_module, 'copy_snapshot_source_files', side_effect=create_mock_workspace), patch.object(hermes_worker_module, 'collect_snapshot_change_diff', return_value=b'partial diff'), patch.object(hermes_worker_module.subprocess, 'Popen', return_value=hermes_server_mock), patch.object(hermes_worker_module, 'wait_worker_model_ready', side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    hermes_worker_module.execute_hermes_gpu_job(hermes_job_path)
            self.assertEqual((hermes_job_path / 'change.diff').read_bytes(), b'partial diff')
            hermes_result_record = json.loads((hermes_job_path / 'result.json').read_text())
            self.assertTrue(hermes_result_record['partial'])
            self.assertIsNone(hermes_result_record['agent_exit_code'])
            hermes_server_mock.terminate.assert_called_once()
            hermes_server_mock.wait.assert_called_once()


if __name__ == '__main__':
    unittest.main()
