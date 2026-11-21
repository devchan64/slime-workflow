"""실제 GPU 작업 없이 RAM 보호와 오류 처리를 검증한다."""
import signal
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from workflow.common import host_memory_guard as guard_module


class HostMemoryGuardTests(unittest.TestCase):
    def test_memory_field_requires_valid_units(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_memory_path = Path(current_directory_name) / 'memory'
            current_memory_path.write_text('MemAvailable: 123 kB\n')
            self.assertEqual(guard_module.read_memory_field_kib(current_memory_path, 'MemAvailable'), 123)
            current_memory_path.write_text('MemAvailable: -1 kB\n')
            with self.assertRaises(ValueError):
                guard_module.read_memory_field_kib(current_memory_path, 'MemAvailable')
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

    def test_group_rss_includes_children_and_excludes_other_groups(self):
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_proc_root=Path(current_temp_name)
            for current_process_id,current_group_id,current_rss_value in ((1234,1234,1000),(1235,1234,9000),(1236,9999,80000)):
                current_process_root=current_proc_root/str(current_process_id)
                current_process_root.mkdir()
                (current_process_root/'stat').write_text(f'{current_process_id} (worker) S 1 {current_group_id} 0')
                (current_process_root/'status').write_text(f'VmRSS: {current_rss_value} kB\n')
            (current_proc_root/'1236'/'stat').write_text('unreadable unrelated record')
            with patch.object(guard_module,'Path',side_effect=lambda current_path_value:current_proc_root if str(current_path_value)=='/proc' else Path(current_path_value)),patch.object(guard_module.os,'getpgid',side_effect=lambda current_process_id:{1234:1234,1235:1234,1236:9999}[current_process_id]):
                self.assertEqual(guard_module.read_worker_group_rss_kib(1234),10000)
                with self.assertRaises(ValueError):guard_module.read_worker_group_rss_kib(7777)

    def test_live_isolated_process_group_rss_includes_child(self):
        import os
        import subprocess
        import sys
        current_child_code="import time; data=bytearray(16*1024*1024); print('ready',flush=True); time.sleep(30)"
        current_parent_code="import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c',sys.argv[1]],stdout=subprocess.PIPE,text=True); p.stdout.readline(); print(p.pid,flush=True); time.sleep(30)"
        current_parent_process=subprocess.Popen([sys.executable,'-c',current_parent_code,current_child_code],stdout=subprocess.PIPE,text=True,start_new_session=True)
        try:
            current_child_identifier=int(current_parent_process.stdout.readline().strip())
            self.assertEqual(os.getpgid(current_child_identifier),current_parent_process.pid)
            current_parent_rss=guard_module.read_memory_field_kib(f'/proc/{current_parent_process.pid}/status','VmRSS')
            current_child_rss=guard_module.read_memory_field_kib(f'/proc/{current_child_identifier}/status','VmRSS')
            current_group_rss=guard_module.read_worker_group_rss_kib(current_parent_process.pid)
            self.assertGreaterEqual(current_group_rss,current_parent_rss+current_child_rss-1024)
        finally:
            try:
                os.killpg(current_parent_process.pid,signal.SIGKILL)
            except ProcessLookupError:
                pass
            current_parent_process.wait(timeout=5)
            current_parent_process.stdout.close()

    def test_live_pidfd_guard_stops_only_isolated_group(self):
        import os
        import subprocess
        import sys
        from workflow.common.gpu_job_queue import HERMES_PIDFD_GROUP_FLAG,stop_hermes_worker_process_group
        current_child_code="import time; print('ready',flush=True); time.sleep(30)"
        current_parent_code="import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c',sys.argv[1]],stdout=subprocess.PIPE,text=True); p.stdout.readline(); print(p.pid,flush=True); time.sleep(30)"
        current_parent_process=subprocess.Popen([sys.executable,'-c',current_parent_code,current_child_code],stdout=subprocess.PIPE,text=True,start_new_session=True)
        current_other_process=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=True)
        current_pid_descriptor=None
        try:
            current_child_identifier=int(current_parent_process.stdout.readline().strip())
            current_pid_descriptor=os.pidfd_open(current_parent_process.pid)
            current_guard_result={}
            current_original_reader=guard_module.read_memory_field_kib
            def read_isolated_test_memory(current_file_path,current_field_name):
                if str(current_file_path)=='/proc/meminfo':
                    return 1
                return current_original_reader(current_file_path,current_field_name)
            with patch.object(guard_module,'read_memory_field_kib',side_effect=read_isolated_test_memory),patch.object(guard_module,'HOST_WORKER_MINIMUM_RSS_KIB',1):
                guard_module.monitor_animate_host_memory(current_parent_process,threading.Event(),current_guard_result,True,lambda:signal.pidfd_send_signal(current_pid_descriptor,signal.SIGKILL,None,HERMES_PIDFD_GROUP_FLAG))
            self.assertNotEqual(current_parent_process.wait(timeout=5),0)
            stop_hermes_worker_process_group(current_parent_process.pid,current_pid_descriptor)
            current_child_stat=Path(f'/proc/{current_child_identifier}/stat')
            if current_child_stat.exists():
                self.assertIn(current_child_stat.read_text().rpartition(') ')[2].split()[0],('Z','X'))
            self.assertIsNone(current_other_process.poll())
            self.assertIn('시스템 RAM 보호',current_guard_result['error'])
        finally:
            if current_pid_descriptor is not None:
                os.close(current_pid_descriptor)
            if current_parent_process.poll() is None:
                os.killpg(current_parent_process.pid,signal.SIGKILL)
                current_parent_process.wait(timeout=5)
            if current_other_process.poll() is None:
                current_other_process.terminate()
                current_other_process.wait(timeout=5)
            current_parent_process.stdout.close()

    def test_unreadable_group_member_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_proc_root=Path(current_temp_name)
            current_process_root=current_proc_root/'1234'
            current_process_root.mkdir()
            (current_process_root/'stat').write_text('1234 (worker) S 1 1234 0')
            (current_process_root/'status').write_text('invalid status')
            with patch.object(guard_module,'Path',side_effect=lambda current_path_value:current_proc_root if str(current_path_value)=='/proc' else Path(current_path_value)),patch.object(guard_module.os,'getpgid',return_value=1234):
                with self.assertRaises(ValueError):guard_module.read_worker_group_rss_kib(1234)

    def test_group_rss_protects_against_child_memory_pressure(self):
        current_worker_mock=Mock(pid=1234)
        current_worker_mock.poll.return_value=None
        current_guard_result={}
        with patch.object(guard_module,'read_memory_field_kib',return_value=1024),patch.object(guard_module,'read_worker_group_rss_kib',return_value=9*1024*1024) as current_group_mock,patch.object(guard_module.os,'killpg') as current_kill_mock:
            guard_module.monitor_animate_host_memory(current_worker_mock,threading.Event(),current_guard_result,True)
        current_group_mock.assert_called_once_with(1234)
        current_kill_mock.assert_called_once_with(1234,signal.SIGKILL)
        self.assertIn('시스템 RAM 보호',current_guard_result['error'])

    def test_supplied_stable_group_terminator_is_used(self):
        current_worker_mock=Mock(pid=1234)
        current_worker_mock.poll.return_value=None
        current_terminate_mock=Mock()
        current_guard_result={}
        with patch.object(guard_module,'read_memory_field_kib',return_value=1024),patch.object(guard_module,'read_worker_group_rss_kib',return_value=9*1024*1024),patch.object(guard_module.os,'killpg') as current_kill_mock:
            guard_module.monitor_animate_host_memory(current_worker_mock,threading.Event(),current_guard_result,True,current_terminate_mock)
        current_terminate_mock.assert_called_once_with()
        current_kill_mock.assert_not_called()
        self.assertIn('시스템 RAM 보호',current_guard_result['error'])

    def test_measurement_failure_fails_closed(self):
        current_worker_mock = Mock(pid=1234)
        current_worker_mock.poll.return_value = None
        current_guard_result = {}
        with patch.object(guard_module, 'read_memory_field_kib', side_effect=OSError('접근 불가')), patch.object(guard_module.os, 'killpg') as current_kill_mock:
            guard_module.monitor_animate_host_memory(current_worker_mock, threading.Event(), current_guard_result)
        current_kill_mock.assert_called_once_with(1234, signal.SIGKILL)
        self.assertIn('감시 실패', current_guard_result['error'])

    def test_worker_finishing_before_signal_is_not_marked_failed(self):
        current_worker_mock=Mock(pid=1234)
        current_worker_mock.poll.side_effect=[None,0]
        current_guard_result={}
        with patch.object(guard_module,'read_memory_field_kib',side_effect=[1024,9*1024*1024]),patch.object(guard_module.os,'killpg') as current_kill_mock:
            guard_module.monitor_animate_host_memory(current_worker_mock,threading.Event(),current_guard_result)
        self.assertEqual(current_guard_result,{})
        current_kill_mock.assert_not_called()

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
