import subprocess
import unittest
from unittest.mock import Mock

from gui.serve import REVIEW_SERVER_SHUTDOWN_SECONDS, stop_review_watch_server


class ReviewWatchShutdownTests(unittest.TestCase):
    def test_slow_shutdown_is_given_time(self):
        process = Mock()
        process.poll.return_value = None
        stop_review_watch_server(process)
        process.wait.assert_called_once_with(timeout=REVIEW_SERVER_SHUTDOWN_SECONDS)
        process.kill.assert_not_called()

    def test_timeout_kills_and_reaps_server(self):
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired('server', 30), 0]
        stop_review_watch_server(process)
        process.kill.assert_called_once_with()
        self.assertEqual(process.wait.call_count, 2)

    def test_ctrl_c_kills_server_and_propagates_interrupt(self):
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [KeyboardInterrupt(), 0]
        with self.assertRaises(KeyboardInterrupt):
            stop_review_watch_server(process)
        process.kill.assert_called_once_with()
        self.assertEqual(process.wait.call_count, 2)
