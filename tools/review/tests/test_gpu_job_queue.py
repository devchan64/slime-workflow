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
            worker_launch_mock.assert_called_once_with(['test-worker'],start_new_session=True)
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
