"""기존 게이트웨이 확인은 동의한 대상에만 종료 신호를 보낸다."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from tools.review.common.gateway_existing_process import confirm_existing_gateway, matches_gateway_script_path


class GatewayExistingProcessTests(unittest.TestCase):
    def test_unused_port_continues(self):
        with patch('socket.create_connection', side_effect=ConnectionRefusedError):
            self.assertTrue(confirm_existing_gateway(8771, Path('/repo'), MagicMock()))

    def test_confirmation_controls_termination(self):
        for selected_answer_text in ('n', 'y'):
            with self.subTest(answer=selected_answer_text), patch('socket.create_connection', side_effect=[MagicMock(), ConnectionRefusedError]), patch('tools.review.common.gateway_existing_process.urlopen'), patch('json.load', return_value={'role': 'management-gateway', 'pid': 123}), patch.object(Path, 'read_bytes', return_value=b'python\0/repo/tools/review/gateway_server.py\0'), patch.object(Path, 'stat') as process_stat_mock, patch('os.getuid', return_value=1000), patch('sys.stdin.isatty', return_value=True), patch('builtins.input', return_value=selected_answer_text), patch('os.kill') as process_signal_mock:
                process_stat_mock.return_value.st_uid = 1000
                self.assertEqual(confirm_existing_gateway(8771, Path('/repo'), MagicMock()), selected_answer_text == 'y')
                self.assertEqual(process_signal_mock.call_count, int(selected_answer_text == 'y'))

    def test_relative_and_absolute_script_identity(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            workflow_root_directory = Path(temporary_directory_name) / 'repo'
            workflow_root_directory.mkdir()
            existing_process_path = Path(temporary_directory_name) / 'process'
            existing_process_path.mkdir()
            (existing_process_path / 'cwd').symlink_to(workflow_root_directory, target_is_directory=True)
            expected_script_path = workflow_root_directory / 'tools/review/gateway_server.py'
            for current_script_argument in (str(expected_script_path), 'tools/review/gateway_server.py', './tools/review/gateway_server.py'):
                current_command_bytes = b'python\0' + current_script_argument.encode() + b'\0'
                self.assertTrue(matches_gateway_script_path(current_command_bytes, existing_process_path, workflow_root_directory))
            for current_command_bytes in (b'python\0/other/tools/review/gateway_server.py\0', b'python\0-c\0tools/review/gateway_server.py\0', b'python\0other.py\0' + str(expected_script_path).encode()):
                self.assertFalse(matches_gateway_script_path(current_command_bytes, existing_process_path, workflow_root_directory))
            (existing_process_path / 'cwd').unlink()
            (existing_process_path / 'cwd').symlink_to(Path(temporary_directory_name), target_is_directory=True)
            self.assertFalse(matches_gateway_script_path(b'python\0tools/review/gateway_server.py\0', existing_process_path, workflow_root_directory))
