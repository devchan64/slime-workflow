"""실행·설치 분리와 공용 실행기의 인자·실패·종료 계약."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import signal
import unittest
from unittest.mock import patch

from tools.review.common import management_launcher, management_process, management_setup


class ManagementLauncherTests(unittest.TestCase):
    def test_gui_source_argument_overrides_environment_without_duplicate(self):
        with patch.dict(os.environ, {'FRONTEND_REPOSITORY_PATH': '/unused/frontend', 'REVIEW_SERVER_PORT': '9890'}):
            selected_command_values = management_launcher.build_management_launch_command('gui', ['--root', '/tmp/review folder', '--port', '9891'])
        self.assertNotIn('--frontend-repo', selected_command_values)
        self.assertEqual(selected_command_values[-4:], ['--root', '/tmp/review folder', '--port', '9891'])
        self.assertNotIn('pip', selected_command_values)

    def test_gateway_does_not_require_frontend_or_gradio(self):
        with patch.dict(os.environ, {'FRONTEND_REPOSITORY_PATH': '/missing/frontend', 'MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH': '/missing/gradio', 'MANAGEMENT_GATEWAY_PORT': '9892'}):
            selected_command_values = management_launcher.build_management_launch_command('gateway', ['--writer-agent-config', '/tmp/config with spaces.yaml'])
        self.assertIn('9892', selected_command_values)
        self.assertEqual(selected_command_values[-1], '/tmp/config with spaces.yaml')

    def test_missing_environment_fails_without_installing(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.dict(os.environ, {'VIRTUAL_ENVIRONMENT_PATH': temporary_directory_name}), patch.object(management_launcher.subprocess, 'Popen') as command_process_mock:
            with self.assertRaisesRegex(ValueError, 'setup_management.sh'):
                management_launcher.build_management_launch_command('gateway', [])
            command_process_mock.assert_not_called()

    def test_relative_environment_uses_repository_root(self):
        with patch.dict(os.environ, {'MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH': '.tmp/custom environment'}):
            selected_environment_path = management_launcher.resolve_management_environment('MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH', '.venv-management')
        self.assertEqual(selected_environment_path, management_launcher.WORKFLOW_ROOT_DIRECTORY/'.tmp/custom environment')

    def test_setup_prepares_both_environments_only_when_requested(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.dict(os.environ, {'VIRTUAL_ENVIRONMENT_PATH': temporary_directory_name+'/runtime', 'MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH': temporary_directory_name+'/ui'}), patch.object(management_setup, 'run_logged_management_command') as run_command_mock:
            management_launcher.prepare_management_environments(None)
        command_argument_records = [current_call_value.args[0] for current_call_value in run_command_mock.call_args_list]
        self.assertEqual(sum('venv' in current_command_values for current_command_values in command_argument_records), 2)
        self.assertEqual(sum('pip' in current_command_values for current_command_values in command_argument_records), 2)

    def test_failure_preserves_output_and_exact_exit_code(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(management_process, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), contextlib.redirect_stdout(io.StringIO()):
            launcher_trace_logger = management_launcher.ManagementLaunchLogger('test')
            try:
                with self.assertRaises(subprocess.CalledProcessError) as command_error_context:
                    management_launcher.run_logged_management_command([sys.executable, '-c', 'print("실패 원인", flush=True); raise SystemExit(7)'], launcher_trace_logger)
                self.assertEqual(command_error_context.exception.returncode, 7)
                self.assertIn('실패 원인', launcher_trace_logger.output_log_path.read_text())
            finally:
                launcher_trace_logger.close_launch_log()

    def test_silent_command_emits_heartbeat(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(management_process, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), patch.object(management_process, 'LAUNCHER_HEARTBEAT_SECONDS', .05), contextlib.redirect_stdout(io.StringIO()):
            launcher_trace_logger = management_launcher.ManagementLaunchLogger('test')
            try:
                management_launcher.run_logged_management_command([sys.executable, '-c', 'import time; time.sleep(.3)'], launcher_trace_logger)
                self.assertIn('/heartbeat pid=', launcher_trace_logger.output_log_path.read_text())
            finally:
                launcher_trace_logger.close_launch_log()

    def test_gradio_configuration_does_not_import_process_launcher(self):
        subprocess.run([sys.executable, '-c', "import sys; import tools.review.common.gradio_process; assert 'tools.review.common.management_launcher' not in sys.modules; assert 'tools.review.common.management_process' not in sys.modules; assert 'tools.review.common.management_setup' not in sys.modules"], check=True)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux 프로세스 상태 검사')
    def test_stubborn_child_is_stopped_but_unrelated_session_survives(self):
        independent_process_handle = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], start_new_session=True)
        stubborn_process_identifier = None
        try:
            with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(management_process, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), contextlib.redirect_stdout(io.StringIO()):
                child_marker_path = Path(temporary_directory_name)/'child.pid'
                child_source_text = f"import os, signal, time; from pathlib import Path; signal.signal(signal.SIGTERM, signal.SIG_IGN); Path({str(child_marker_path)!r}).write_text(str(os.getpid())); time.sleep(30)"
                parent_source_text = "import subprocess, sys, time; from pathlib import Path; subprocess.Popen([sys.executable, '-c', " + repr(child_source_text) + "]); marker_path = Path(" + repr(str(child_marker_path)) + "); deadline_time = time.monotonic() + 5\nwhile not marker_path.exists() and time.monotonic() < deadline_time: time.sleep(.01)\nassert marker_path.exists()"
                launcher_trace_logger = management_process.ManagementLaunchLogger('test')
                try:
                    management_process.run_logged_management_command([sys.executable, '-c', parent_source_text], launcher_trace_logger)
                finally:
                    launcher_trace_logger.close_launch_log()
                stubborn_process_identifier = int(child_marker_path.read_text())
                child_status_path = Path(f'/proc/{stubborn_process_identifier}/stat')
                for cleanup_attempt_number in range(100):
                    if not child_status_path.exists() or child_status_path.read_text().split(') ')[1][0] == 'Z':
                        break
                    time.sleep(.01)
                else:
                    self.fail('종료된 부모가 남긴 자식이 실행 중입니다.')
                self.assertIsNone(independent_process_handle.poll())
        finally:
            if stubborn_process_identifier is not None:
                try:
                    os.kill(stubborn_process_identifier, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            independent_process_handle.terminate()
            independent_process_handle.wait(timeout=5)
