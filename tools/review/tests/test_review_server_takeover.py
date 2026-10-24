"""포트 인계가 다른 프로그램과 작업 프로세스를 종료하지 않는지 검증한다."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from tools.review.common.review_server_takeover import release_review_server_port


class ReviewTakeoverTests(unittest.TestCase):
    def test_foreign_listener_is_preserved(self):
        current_process_mock = Mock()
        current_process_mock.parent.return_value = None
        with patch('tools.review.common.review_server_takeover.psutil.Process', return_value=current_process_mock), patch('tools.review.common.review_server_takeover.matches_review_server', return_value=False), patch('tools.review.common.review_server_takeover.psutil.net_connections', return_value=[SimpleNamespace(pid=123, status='LISTEN', laddr=SimpleNamespace(port=8770))]):
            with self.assertRaisesRegex(RuntimeError, '다른 프로그램'):
                release_review_server_port(8770, Path('/workspace/serve.py'))
        current_process_mock.send_signal.assert_not_called()

    def test_owned_listener_is_stopped(self):
        current_process_mock = Mock(pid=123)
        current_process_mock.parent.return_value = None
        with patch('tools.review.common.review_server_takeover.psutil.Process', return_value=current_process_mock), patch('tools.review.common.review_server_takeover.matches_review_server', return_value=True), patch('tools.review.common.review_server_takeover.psutil.net_connections', return_value=[SimpleNamespace(pid=123, status='LISTEN', laddr=SimpleNamespace(port=8770))]), patch('tools.review.common.review_server_takeover.psutil.wait_procs', return_value=([], [])):
            release_review_server_port(8770, Path('/workspace/serve.py'))
        current_process_mock.send_signal.assert_called_once()

    def test_python_option_preserves_owned_script_identity(self):
        from tools.review.common.review_server_takeover import matches_review_server
        import os
        current_process_mock = Mock()
        current_process_mock.cmdline.return_value = ['/usr/bin/python', '-u', '/workspace/serve.py', '--watch']
        current_process_mock.uids.return_value = SimpleNamespace(real=os.getuid())
        self.assertTrue(matches_review_server(current_process_mock, Path('/workspace/serve.py')))
        self.assertFalse(matches_review_server(current_process_mock, Path('/workspace/other.py')))
