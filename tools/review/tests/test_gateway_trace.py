"""콘솔 연결 종료가 게이트웨이 요청 응답을 끊지 않는지 검증한다."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.review.gateway_server import create_gateway_trace_logger


class GatewayTraceTests(unittest.TestCase):
    def test_closed_console_keeps_file_logging(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_log_path = Path(current_directory_name)/'gateway.log'
            current_trace_logger = create_gateway_trace_logger(current_log_path)
            with patch('builtins.print', side_effect=BrokenPipeError) as current_console_mock:
                current_trace_logger('request', '첫 요청')
                current_trace_logger('request', '다음 요청')
            self.assertEqual(current_console_mock.call_count, 1)
            current_log_text = current_log_path.read_text()
            self.assertIn('첫 요청', current_log_text)
            self.assertIn('다음 요청', current_log_text)
            self.assertIn('console-detached', current_log_text)

    def test_file_logging_error_remains_explicit(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_trace_logger = create_gateway_trace_logger(Path(current_directory_name)/'missing'/'gateway.log')
            with self.assertRaises(FileNotFoundError):
                current_trace_logger('request', '기록 실패')
