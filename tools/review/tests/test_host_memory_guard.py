"""실제 GPU 작업 없이 RAM 보호와 오류 처리를 검증한다."""
import signal
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools.review.common import host_memory_guard as guard_module


class HostMemoryGuardTests(unittest.TestCase):
    def test_memory_field_requires_valid_units(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_memory_path = Path(current_directory_name) / 'memory'
            current_memory_path.write_text('MemAvailable: 123 kB\n')
            self.assertEqual(guard_module.read_memory_field_kib(current_memory_path, 'MemAvailable'), 123)
            current_memory_path.write_text('MemAvailable: 123 MB\n')
            with self.assertRaises(ValueError):
                guard_module.read_memory_field_kib(current_memory_path, 'MemAvailable')
            with self.assertRaises(ValueError):
                guard_module.read_memory_field_kib(current_memory_path, 'VmRSS')

    def test_low_available_memory_kills_only_worker_group(self):
        current_worker_mock = Mock(pid=1234)
        current_worker_mock.poll.return_value = None
        current_guard_result = {}
        with patch.object(guard_module, 'read_memory_field_kib', side_effect=[1024, 9 * 1024 * 1024]), patch.object(guard_module.os, 'killpg') as current_kill_mock:
            guard_module.monitor_animate_host_memory(current_worker_mock, threading.Event(), current_guard_result)
        current_kill_mock.assert_called_once_with(1234, signal.SIGKILL)
        self.assertIn('시스템 RAM 보호', current_guard_result['error'])

    def test_measurement_failure_fails_closed(self):
        current_worker_mock = Mock(pid=1234)
        current_worker_mock.poll.return_value = None
        current_guard_result = {}
        with patch.object(guard_module, 'read_memory_field_kib', side_effect=OSError('접근 불가')), patch.object(guard_module.os, 'killpg') as current_kill_mock:
            guard_module.monitor_animate_host_memory(current_worker_mock, threading.Event(), current_guard_result)
        current_kill_mock.assert_called_once_with(1234, signal.SIGKILL)
        self.assertIn('감시 실패', current_guard_result['error'])

    def test_small_worker_is_not_stopped_by_external_pressure(self):
        current_worker_mock = Mock(pid=1234)
        current_worker_mock.poll.side_effect = [None, 0]
        with patch.object(guard_module, 'read_memory_field_kib', side_effect=[1024, 1024]), patch.object(guard_module.os, 'killpg') as current_kill_mock, patch.object(guard_module, 'HOST_MEMORY_POLL_SECONDS', 0):
            guard_module.monitor_animate_host_memory(current_worker_mock, threading.Event(), {})
        current_kill_mock.assert_not_called()

    def test_exiting_zombie_without_rss_is_not_reported_as_failure(self):
        current_worker_mock = Mock(pid=1234)
        current_worker_mock.poll.return_value = None
        current_guard_result = {}
        with patch.object(guard_module, 'read_memory_field_kib', side_effect=[1024, ValueError('VmRSS 누락')]), patch.object(guard_module.Path, 'read_text', return_value='Name:\tpython\nState:\tZ (zombie)\n'), patch.object(guard_module.os, 'killpg') as current_kill_mock:
            guard_module.monitor_animate_host_memory(current_worker_mock, threading.Event(), current_guard_result)
        self.assertEqual(current_guard_result, {})
        current_kill_mock.assert_not_called()
