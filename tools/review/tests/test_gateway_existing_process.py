"""기존 게이트웨이 확인은 동의한 대상에만 종료 신호를 보낸다."""
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from tools.review.common.gateway_existing_process import confirm_existing_gateway


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
