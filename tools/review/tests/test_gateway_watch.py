"""게이트웨이 watch 옵션·감시 경계·재시작 연결 계약."""
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.review.common import gateway_watch, management_process
from tools.review.gateway_server import parse_gateway_arguments


class GatewayWatchTests(unittest.TestCase):
    def test_watch_option_preserves_server_arguments(self):
        argument_record_values = parse_gateway_arguments(['--watch', '--port', '9871', '--writer-agent-config', '/tmp/writer config.yaml'])
        self.assertTrue(argument_record_values.watch)
        self.assertEqual(argument_record_values.port, 9871)
        self.assertEqual(argument_record_values.writer_agent_config, Path('/tmp/writer config.yaml'))
        self.assertFalse(parse_gateway_arguments([]).watch)

    def test_snapshot_tracks_create_edit_delete_but_excludes_ui_and_results(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            source_root_directory = Path(temporary_directory_name)
            initial_snapshot_values = gateway_watch.snapshot_gateway_watch_paths([source_root_directory])
            for ignored_relative_path in ('ui/app.py', '.tmp/job/status.json', '__pycache__/worker.py', 'tests/test_worker.py', 'gradio_process.py', 'management_launcher.py', 'manager.html'):
                ignored_source_path = source_root_directory/ignored_relative_path
                ignored_source_path.parent.mkdir(parents=True, exist_ok=True)
                ignored_source_path.write_text('ignored')
            self.assertEqual(gateway_watch.snapshot_gateway_watch_paths([source_root_directory]), initial_snapshot_values)
            source_module_path = source_root_directory/'service.py'
            source_module_path.write_text('first')
            created_snapshot_values = gateway_watch.snapshot_gateway_watch_paths([source_root_directory])
            self.assertNotEqual(created_snapshot_values, initial_snapshot_values)
            source_module_path.write_text('changed service')
            self.assertNotEqual(gateway_watch.snapshot_gateway_watch_paths([source_root_directory]), created_snapshot_values)
            source_module_path.unlink()
            self.assertEqual(gateway_watch.snapshot_gateway_watch_paths([source_root_directory]), initial_snapshot_values)

    def test_missing_writer_configuration_creation_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            writer_config_path = Path(temporary_directory_name)/'workspace.yaml'
            previous_source_snapshot = gateway_watch.snapshot_gateway_watch_paths([writer_config_path])
            writer_config_path.write_text('schema_version: 1')
            self.assertNotEqual(previous_source_snapshot, gateway_watch.snapshot_gateway_watch_paths([writer_config_path]))

    def test_watch_restarts_only_when_requested_and_keeps_arguments(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(management_process, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), patch.object(gateway_watch, 'run_logged_management_command', side_effect=[True, False]) as run_command_mock, contextlib.redirect_stdout(io.StringIO()):
            gateway_watch.run_gateway_watch_mode(9871, Path('/tmp/writer config.yaml'))
        self.assertEqual(run_command_mock.call_count, 2)
        for current_call_value in run_command_mock.call_args_list:
            self.assertNotIn('--watch', current_call_value.args[0])
            self.assertEqual(current_call_value.args[0][-4:], ['--port', '9871', '--writer-agent-config', '/tmp/writer config.yaml'])

    def test_process_restart_terminates_child_and_returns_restart_signal(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(management_process, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), contextlib.redirect_stdout(io.StringIO()):
            launcher_trace_logger = management_process.ManagementLaunchLogger('test')
            try:
                self.assertTrue(management_process.run_logged_management_command([sys.executable, '-c', 'import time; time.sleep(30)'], launcher_trace_logger, lambda: True))
                self.assertIn('/restart ', launcher_trace_logger.output_log_path.read_text())
            finally:
                launcher_trace_logger.close_launch_log()

    def test_failed_start_does_not_loop_or_hide_error(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(management_process, 'WORKFLOW_ROOT_DIRECTORY', Path(temporary_directory_name)), patch.object(gateway_watch, 'run_logged_management_command', side_effect=subprocess.CalledProcessError(1, ['gateway'])) as run_command_mock, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(subprocess.CalledProcessError):
                gateway_watch.run_gateway_watch_mode(9871)
            run_command_mock.assert_called_once()
