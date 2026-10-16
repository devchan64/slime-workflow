"""실제 GPU 작업 없이 메모리 대기·중지·실패·재개 계약 검증."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from tools.review.common import gpu_job_queue as queue_module

class GpuJobQueueTests(unittest.TestCase):
    def setUp(self):
        self.temporary_job_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_job_root.cleanup)
        self.current_job_path = Path(self.temporary_job_root.name)/'job'
        self.current_job_path.mkdir()
        (self.current_job_path/'status.json').write_text('{"status":"running"}')
        (self.current_job_path/'gpu-command.json').write_text(json.dumps({'command':['test-worker'],'service':'anny'}))
        self.queue_path_patch = patch.object(queue_module,'GPU_QUEUE_DIRECTORY',Path(self.temporary_job_root.name)/'queue')
        self.queue_path_patch.start()
        self.addCleanup(self.queue_path_patch.stop)
        from tools.review.common import gpu_memory_history
        self.memory_history_patch = patch.object(gpu_memory_history,'MEMORY_HISTORY_DIRECTORY',Path(self.temporary_job_root.name)/'memory')
        self.memory_history_patch.start()
        self.addCleanup(self.memory_history_patch.stop)
        self.worker_memory_patch = patch.object(queue_module,'read_worker_memory',return_value=0)
        self.worker_memory_patch.start()
        self.addCleanup(self.worker_memory_patch.stop)
        self.signal_handler_patch = patch('signal.signal')
        self.signal_handler_patch.start()
        self.addCleanup(self.signal_handler_patch.stop)
        # 작업 프로세스 대역과 메모리 조회 subprocess가 서로 간섭하지 않게 한다.
        current_memory_query_patch = patch('tools.review.common.generation_telemetry.subprocess.check_output',return_value='')
        current_memory_query_patch.start()
        self.addCleanup(current_memory_query_patch.stop)

    def test_memory_wait_can_be_cancelled_without_launch(self):
        def cancel_waiting_job(_):
            current_status_record=json.loads((self.current_job_path/'status.json').read_text())
            self.assertEqual(current_status_record['status'],'queued')
            self.assertEqual(current_status_record['queue_position'],1)
            queue_module.cancel_gpu_generation(self.current_job_path)
        with patch.object(queue_module,'read_gpu_memory',return_value=(24000,1000)),patch.object(queue_module.time,'sleep',side_effect=cancel_waiting_job),patch.object(queue_module.subprocess,'Popen') as worker_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
            worker_launch_mock.assert_not_called()
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'cancelled')
        self.assertEqual(list(queue_module.GPU_QUEUE_DIRECTORY.glob('*.json')),[])

    def test_memory_recovery_starts_worker_and_keeps_result(self):
        worker_process_mock=Mock(returncode=0)
        worker_process_mock.poll.return_value=0
        with patch.object(queue_module,'read_gpu_memory',side_effect=[(24000,1000),(24000,1000),(24000,8000),(24000,8000)]),patch.object(queue_module.time,'sleep'),patch.object(queue_module.subprocess,'Popen',return_value=worker_process_mock) as worker_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
            worker_launch_mock.assert_called_once()
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'completed')

    def test_insufficient_total_memory_fails_explicitly(self):
        with patch.object(queue_module,'read_gpu_memory',return_value=(1000,1000)),patch.object(queue_module.subprocess,'Popen') as worker_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),1)
            worker_launch_mock.assert_not_called()
        self.assertIn('요구량',json.loads((self.current_job_path/'status.json').read_text())['error'])

    def test_available_memory_admits_job_alongside_active_reservation(self):
        active = queue_module.GPU_QUEUE_DIRECTORY/'active'
        active.mkdir(parents=True)
        import os
        (active/'existing.json').write_text(json.dumps({'pid':os.getpid(),'required_memory_mib':4096}))
        worker=Mock(returncode=0)
        worker.poll.return_value=0
        with patch.object(queue_module,'read_gpu_memory',return_value=(8151,4000)),patch.object(queue_module,'read_worker_memory',return_value=3000),patch.object(queue_module.subprocess,'Popen',return_value=worker) as launch:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
            launch.assert_called_once()
        self.assertEqual(len(list(active.glob('*.json'))),1)

    def test_reservation_prevents_oversubscription_before_model_load(self):
        active = queue_module.GPU_QUEUE_DIRECTORY/'active'
        active.mkdir(parents=True)
        import os
        (active/'existing.json').write_text(json.dumps({'pid':os.getpid(),'required_memory_mib':6144}))
        with patch.object(queue_module,'read_gpu_memory',return_value=(10000,8000)),patch.object(queue_module.time,'sleep',side_effect=lambda _:queue_module.cancel_gpu_generation(self.current_job_path)),patch.object(queue_module.subprocess,'Popen') as launch:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
            launch.assert_not_called()

    def test_resume_preserves_existing_artifacts_and_prevents_duplicate(self):
        (self.current_job_path/'status.json').write_text('{"status":"cancelled"}')
        (self.current_job_path/'result.png').write_bytes(b'preserved')
        with patch.object(queue_module.subprocess,'Popen'):
            self.assertEqual(queue_module.resume_gpu_generation(self.current_job_path)['status'],'queued')
            with self.assertRaises(ValueError):queue_module.resume_gpu_generation(self.current_job_path)
        self.assertEqual((self.current_job_path/'result.png').read_bytes(),b'preserved')

    def test_legacy_resume_prepares_command_only_after_acceptance(self):
        import fcntl
        current_command_path = self.current_job_path / 'gpu-command.json'
        current_command_path.unlink()
        legacy_command_record = {'command': ['legacy-worker'], 'service': 'image'}
        with patch.object(queue_module.subprocess, 'Popen') as current_launch_mock:
            with self.assertRaises(ValueError):
                queue_module.resume_gpu_generation(self.current_job_path, legacy_command_record)
            self.assertFalse(current_command_path.exists())
            (self.current_job_path / 'status.json').write_text('{"status":"failed"}')
            (self.current_job_path / 'cancel.request').touch()
            with (self.current_job_path / 'execution.lock').open('a') as current_execution_handle:
                fcntl.flock(current_execution_handle, fcntl.LOCK_EX)
                with self.assertRaisesRegex(ValueError, '최종 기록 저장'):
                    queue_module.resume_gpu_generation(self.current_job_path, legacy_command_record)
                self.assertFalse(current_command_path.exists())
                self.assertTrue((self.current_job_path / 'cancel.request').exists())
                current_launch_mock.assert_not_called()
            self.assertEqual(queue_module.resume_gpu_generation(self.current_job_path, legacy_command_record)['status'], 'queued')
            self.assertEqual(json.loads(current_command_path.read_text()), legacy_command_record)
            current_launch_mock.assert_called_once()

    def test_invalid_resume_command_preserves_status_and_markers(self):
        current_invalid_records = [[], {}, {'command': ['worker']},
            {'command': ['worker'], 'service': 'image', 'extra': True},
            {'command': 'worker', 'service': 'image'}, {'command': [], 'service': 'image'},
            {'command': [''], 'service': 'image'}, {'command': ['worker', 3], 'service': 'image'},
            {'command': ['worker\x00'], 'service': 'image'}, {'command': ['worker'], 'service': None}]
        for current_invalid_record in current_invalid_records:
            with self.subTest(record=current_invalid_record), patch.object(queue_module, 'launch_gpu_process') as current_launch_mock:
                (self.current_job_path / 'status.json').write_text('{"status":"paused"}')
                for current_marker_name in ('cancel.request', 'pause.request', 'stage-pause.json'):
                    (self.current_job_path / current_marker_name).write_text('preserve')
                (self.current_job_path / 'gpu-command.json').write_text(json.dumps(current_invalid_record))
                with self.assertRaisesRegex(ValueError, '재개 실행 명령'):
                    queue_module.resume_gpu_generation(self.current_job_path)
                current_launch_mock.assert_not_called()
                self.assertEqual(json.loads((self.current_job_path / 'status.json').read_text()), {'status': 'paused'})
                for current_marker_name in ('cancel.request', 'pause.request', 'stage-pause.json'):
                    self.assertEqual((self.current_job_path / current_marker_name).read_text(), 'preserve')
                self.assertFalse((self.current_job_path / 'worker.log').exists())

    def test_resume_waits_for_previous_executor_finalization(self):
        import fcntl
        for current_status_name in ('failed', 'cancelled', 'paused'):
            with self.subTest(status=current_status_name):
                (self.current_job_path / 'status.json').write_text(json.dumps({'status':current_status_name}))
                (self.current_job_path / 'cancel.request').touch()
                with (self.current_job_path / 'execution.lock').open('a') as current_execution_handle, patch.object(queue_module, 'launch_gpu_process') as current_launch_mock:
                    fcntl.flock(current_execution_handle, fcntl.LOCK_EX)
                    with self.assertRaisesRegex(ValueError, '최종 기록 저장'):
                        queue_module.resume_gpu_generation(self.current_job_path)
                    current_launch_mock.assert_not_called()
                    self.assertEqual(json.loads((self.current_job_path / 'status.json').read_text())['status'], current_status_name)
                    self.assertTrue((self.current_job_path / 'cancel.request').exists())
                def verify_released_execution_lock(*current_arguments, **current_options):
                    with (self.current_job_path / 'execution.lock').open('a') as current_new_handle:
                        fcntl.flock(current_new_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with patch.object(queue_module, 'launch_gpu_process', side_effect=verify_released_execution_lock) as current_launch_mock:
                    self.assertEqual(queue_module.resume_gpu_generation(self.current_job_path)['status'], 'queued')
                    current_launch_mock.assert_called_once()
                self.assertFalse((self.current_job_path / 'cancel.request').exists())

    def test_launch_failure_is_terminal(self):
        with patch.object(queue_module.subprocess,'Popen',side_effect=OSError('spawn failed')):
            with self.assertRaises(OSError):queue_module.launch_gpu_process(['test'],self.current_job_path,'anny')
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'failed')

    def test_global_lock_waits_even_when_memory_is_free(self):
        import fcntl
        queue_module.GPU_QUEUE_DIRECTORY.mkdir()
        with (queue_module.GPU_QUEUE_DIRECTORY/'execution.lock').open('a') as occupied_lock_handle:
            fcntl.flock(occupied_lock_handle,fcntl.LOCK_EX)
            with patch.object(queue_module,'read_gpu_memory',return_value=(24000,24000)),patch.object(queue_module.time,'sleep',side_effect=lambda _:queue_module.cancel_gpu_generation(self.current_job_path)),patch.object(queue_module.subprocess,'Popen') as worker_launch_mock:
                queue_module.execute_queued_generation(self.current_job_path)
                worker_launch_mock.assert_not_called()
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'cancelled')

    def test_running_cancel_terminates_worker_group(self):
        worker_process_mock=Mock(pid=123,returncode=-15)
        worker_process_mock.poll.return_value=None
        def start_cancelled_worker(*command_arguments,**process_options):
            (self.current_job_path/'cancel.request').touch()
            return worker_process_mock
        def finish_cancelled_worker(*wait_arguments,**wait_options):
            worker_process_mock.poll.return_value=-15
            return -15
        worker_process_mock.wait.side_effect=finish_cancelled_worker
        with patch.object(queue_module,'read_gpu_memory',return_value=(24000,24000)),patch.object(queue_module.subprocess,'Popen',side_effect=start_cancelled_worker),patch.object(queue_module.os,'killpg') as terminate_group_mock:
            queue_module.execute_queued_generation(self.current_job_path)
            terminate_group_mock.assert_called_once()
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'cancelled')

    def test_later_job_runs_when_earlier_job_does_not_fit(self):
        import os
        earlier_job_path = Path(self.temporary_job_root.name)/'earlier'
        earlier_job_path.mkdir()
        (earlier_job_path/'gpu-command.json').write_text(json.dumps({'command':['large-worker'],'service':'image'}))
        queue_module.GPU_QUEUE_DIRECTORY.mkdir()
        earlier_ticket_path = queue_module.GPU_QUEUE_DIRECTORY/'00000000000000000000.json'
        earlier_ticket_path.write_text(json.dumps({'pid':os.getpid(),'path':str(earlier_job_path)}))
        worker_process_mock = Mock(returncode=0)
        worker_process_mock.poll.return_value = 0
        with patch.object(queue_module,'read_gpu_memory',return_value=(8151,4000)),patch.object(queue_module.subprocess,'Popen',return_value=worker_process_mock) as worker_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
            self.assertEqual(worker_launch_mock.call_args.args[0],['test-worker'])
            self.assertIn('SLIME_GPU_RESERVATION_PATH',worker_launch_mock.call_args.kwargs['env'])
        self.assertTrue(earlier_ticket_path.exists())

    def test_first_fitting_ticket_keeps_order_and_skips_cancelled(self):
        import os
        queue_module.GPU_QUEUE_DIRECTORY.mkdir()
        ticket_paths = []
        for index, service in enumerate(['image','anny','momask']):
            job_directory_path = Path(self.temporary_job_root.name)/str(index)
            job_directory_path.mkdir()
            (job_directory_path/'gpu-command.json').write_text(json.dumps({'command':['worker'],'service':service}))
            ticket_file_path = queue_module.GPU_QUEUE_DIRECTORY/f'{index:020d}.json'
            ticket_file_path.write_text(json.dumps({'pid':os.getpid(),'path':str(job_directory_path)}))
            ticket_paths.append(ticket_file_path)
        self.assertEqual(queue_module.select_runnable_ticket(7000),ticket_paths[0])
        self.assertEqual(queue_module.select_runnable_ticket(5000),ticket_paths[1])
        self.assertIsNone(queue_module.select_runnable_ticket(1000))
        (Path(self.temporary_job_root.name)/'1/cancel.request').touch()
        self.assertEqual(queue_module.select_runnable_ticket(5000),ticket_paths[2])

    def test_waiting_reload_preserves_process_and_ticket(self):
        ticket_file_path = Path(self.temporary_job_root.name)/'ticket.json'
        with patch.object(queue_module,'calculate_queue_revision',return_value='new'),patch.object(queue_module.os,'execve') as replacement_process_mock:
            queue_module.reload_waiting_executor(ticket_file_path,'old')
            replacement_process_mock.assert_called_once()
            self.assertEqual(replacement_process_mock.call_args.args[2]['SLIME_GPU_QUEUE_TICKET'],str(ticket_file_path.resolve()))
        with patch.object(queue_module,'calculate_queue_revision',return_value='same'),patch.object(queue_module.os,'execve') as replacement_process_mock:
            queue_module.reload_waiting_executor(ticket_file_path,'same')
            replacement_process_mock.assert_not_called()

    def test_observed_peak_admits_job_without_extra_margin(self):
        from tools.review.common import gpu_memory_history
        gpu_memory_history.save_memory_observation('image','previous',7538,3,'completed',command_identity_name='run_qwen_2512.py:1280x1280:steps=4:references=0')
        (self.current_job_path/'request.json').write_text(json.dumps({'width':1280,'height':1280,'steps':4}))
        (self.current_job_path/'gpu-command.json').write_text(json.dumps({'command':['python','run_qwen_2512.py'],'service':'image'}))
        worker_process_mock = Mock(returncode=0)
        worker_process_mock.poll.return_value = 0
        with patch.object(queue_module,'read_gpu_memory',return_value=(8151,7599)),patch.object(queue_module.subprocess,'Popen',return_value=worker_process_mock) as worker_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
            worker_launch_mock.assert_called_once()

    def test_observed_peak_blocks_insufficient_free_memory(self):
        from tools.review.common import gpu_memory_history
        gpu_memory_history.save_memory_observation('anny','previous',6202,3,'completed',command_identity_name='test-worker')
        with patch.object(queue_module,'read_gpu_memory',return_value=(8151,6100)),patch.object(queue_module.time,'sleep',side_effect=lambda _:queue_module.cancel_gpu_generation(self.current_job_path)),patch.object(queue_module.subprocess,'Popen') as worker_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
            worker_launch_mock.assert_not_called()

    def test_paused_stage_releases_queue_and_resumes_without_losing_result(self):
        worker_process_mock=Mock(returncode=0)
        worker_process_mock.poll.return_value=0
        (self.current_job_path/'stage-pause.json').write_text('{"completed":1}')
        (self.current_job_path/'grid-input.png').write_bytes(b'preserved')
        with patch.object(queue_module,'read_gpu_memory',return_value=(24000,24000)),patch.object(queue_module.subprocess,'Popen',return_value=worker_process_mock):
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'paused')
        with patch.object(queue_module.subprocess,'Popen'):
            queue_module.resume_gpu_generation(self.current_job_path)
            with self.assertRaises(ValueError):
                queue_module.resume_gpu_generation(self.current_job_path)
        self.assertFalse((self.current_job_path/'stage-pause.json').exists())
        self.assertEqual((self.current_job_path/'grid-input.png').read_bytes(),b'preserved')

    def test_pause_waiting_job_does_not_start_gpu_worker(self):
        (self.current_job_path/'pause.request').touch()
        with patch.object(queue_module.subprocess,'Popen') as worker_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
        worker_launch_mock.assert_not_called()
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'paused')
