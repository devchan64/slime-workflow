"""실제 GPU 작업 없이 메모리 대기·중지·실패·재개 계약 검증."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from tools.review.common import gpu_job_queue as queue_module

class GpuJobQueueTests(unittest.TestCase):
    def test_shared_environment_preparation_waits_for_other_jobs_and_blocks_new_work(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_root_path = Path(current_temp_directory)
            current_job_path = current_root_path / 'job'
            current_job_path.mkdir()
            (current_job_path / 'gpu-command.json').write_text(json.dumps({'command': ['python', 'prepare_worker.py'], 'service': 'wan-fun-prepare'}))
            current_ticket_path = current_root_path / 'ticket.json'
            import os
            current_ticket_path.write_text(json.dumps({'pid': os.getpid(), 'path': str(current_job_path)}))
            with patch.object(queue_module, 'read_priority_tickets', return_value=[current_ticket_path]), patch.object(queue_module, 'estimate_required_memory', return_value={'required_memory_mib': 1}):
                self.assertIsNone(queue_module.select_runnable_ticket(100, 'vram', ['wan-fun']))
                self.assertIsNone(queue_module.select_runnable_ticket(100, 'vram', ['image']))
                self.assertIsNone(queue_module.select_runnable_ticket(100, 'vram', ['wan-fun-prepare']))
                self.assertEqual(queue_module.select_runnable_ticket(100, 'vram', []), current_ticket_path)

    def test_kimodo_cache_check_is_exclusive_with_active_work(self):
        import os
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_root_path=Path(current_temp_directory)
            current_job_path=current_root_path/'job'
            current_job_path.mkdir()
            (current_job_path/'gpu-command.json').write_text(json.dumps({'command':['python','worker.py'],'service':'kimodo-cache-check'}))
            current_ticket_path=current_root_path/'ticket.json'
            current_ticket_path.write_text(json.dumps({'pid':os.getpid(),'path':str(current_job_path)}))
            with patch.object(queue_module,'read_priority_tickets',return_value=[current_ticket_path]),patch.object(queue_module,'estimate_required_memory',return_value={'required_memory_mib':1}):
                self.assertIsNone(queue_module.select_runnable_ticket(100,'vram',['image']))
                self.assertIsNone(queue_module.select_runnable_ticket(100,'vram',['kimodo-cache-check']))
                self.assertEqual(queue_module.select_runnable_ticket(100,'vram',[]),current_ticket_path)
            with patch.object(queue_module,'read_priority_tickets') as current_ticket_mock:
                self.assertIsNone(queue_module.select_runnable_ticket(100,'vram',['kimodo-cache-check']))
                current_ticket_mock.assert_not_called()

    def test_hermes_queue_is_exclusive_with_active_work(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_root_path = Path(current_temp_directory)
            current_job_path = current_root_path / 'job'
            current_job_path.mkdir()
            (current_job_path / 'gpu-command.json').write_text(json.dumps({'command': ['python', 'worker.py'], 'service': 'hermes-agent'}))
            current_ticket_path = current_root_path / 'ticket.json'
            import os
            current_ticket_path.write_text(json.dumps({'pid': os.getpid(), 'path': str(current_job_path)}))
            with patch.object(queue_module, 'read_priority_tickets', return_value=[current_ticket_path]), patch.object(queue_module, 'estimate_required_memory', return_value={'required_memory_mib': 1}):
                self.assertIsNone(queue_module.select_runnable_ticket(100, 'vram', ['image']))
                self.assertIsNone(queue_module.select_runnable_ticket(100, 'vram', ['hermes-agent']))
                self.assertEqual(queue_module.select_runnable_ticket(100, 'vram', []), current_ticket_path)

    def test_active_hermes_blocks_other_waiting_work(self):
        with patch.object(queue_module, 'read_priority_tickets') as current_ticket_mock:
            self.assertIsNone(queue_module.select_runnable_ticket(100, 'vram', ['hermes-agent']))
            current_ticket_mock.assert_not_called()

    def setUp(self):
        self.temporary_job_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_job_root.cleanup)
        self.current_job_path = Path(self.temporary_job_root.name)/'job'
        self.current_job_path.mkdir()
        current_service_patch = patch.dict(queue_module.GPU_MEMORY_REQUIREMENTS, {'anny': 2048})
        current_service_patch.start()
        self.addCleanup(current_service_patch.stop)
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
        current_host_memory_patch = patch.object(queue_module,'read_host_available_memory',return_value=100000)
        current_host_memory_patch.start()
        self.addCleanup(current_host_memory_patch.stop)
        current_domain_patch = patch.object(queue_module,'read_gpu_memory_domain',return_value='gtt')
        current_domain_patch.start()
        self.addCleanup(current_domain_patch.stop)
        self.signal_handler_patch = patch('signal.signal')
        self.signal_handler_patch.start()
        self.addCleanup(self.signal_handler_patch.stop)
        # 작업 프로세스 대역과 메모리 조회 subprocess가 서로 간섭하지 않게 한다.
        current_memory_query_patch = patch('tools.review.common.generation_telemetry.subprocess.check_output',return_value='')
        current_memory_query_patch.start()
        self.addCleanup(current_memory_query_patch.stop)

    def test_generator_waits_until_hermes_reservation_released(self):
        import os
        current_active_root = queue_module.GPU_QUEUE_DIRECTORY / 'active'
        current_active_root.mkdir(parents=True)
        current_reservation_path = current_active_root / 'hermes-test.json'
        current_reservation_path.write_text(json.dumps({'pid':os.getpid(), 'service':'hermes-agent', 'required_memory_mib':1}))
        current_worker_mock = Mock(returncode=0)
        current_worker_mock.poll.return_value = 0
        current_observations = []
        def release_test_reservation(current_wait_seconds):
            current_status_record = json.loads((self.current_job_path / 'status.json').read_text())
            self.assertEqual(current_status_record['status'], 'queued')
            current_launch_mock.assert_not_called()
            self.assertTrue(current_reservation_path.exists())
            current_observations.append('blocked')
            current_reservation_path.unlink()
        with patch.object(queue_module, 'read_gpu_memory', return_value=(24000, 20000)), patch.object(queue_module.time, 'sleep', side_effect=release_test_reservation), patch.object(queue_module.subprocess, 'Popen', return_value=current_worker_mock) as current_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path), 0)
        self.assertEqual(current_observations, ['blocked'])
        current_launch_mock.assert_called_once()
        self.assertEqual(json.loads((self.current_job_path / 'status.json').read_text())['status'], 'completed')
        self.assertEqual(list(current_active_root.glob('*.json')), [])

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
        current_status_record=json.loads((self.current_job_path/'status.json').read_text())
        self.assertEqual(current_status_record['status'],'completed')
        self.assertIn('completed_at',current_status_record)

    def test_animate_guard_failure_is_recorded_as_failed(self):
        current_worker_path = queue_module.WORKFLOW_ROOT_DIRECTORY/'generators/wan_animate2/worker.py'
        (self.current_job_path/'gpu-command.json').write_text(json.dumps({'command':['python',str(current_worker_path)],'service':'image'}))
        (self.current_job_path/'request.json').write_text(json.dumps({'frames': 65}))
        current_worker_mock = Mock(returncode=-9)
        current_worker_mock.poll.return_value = -9
        current_event_mock = Mock()
        current_thread_mock = Mock()
        current_guard_result = {'error':'시스템 RAM 보호: 테스트'}
        with patch.object(queue_module,'read_gpu_memory',return_value=(98304,98304)), patch.object(queue_module.subprocess,'Popen',return_value=current_worker_mock), patch.object(queue_module,'start_animate_memory_guard',return_value=(current_event_mock,current_thread_mock,current_guard_result)):
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),-9)
        current_status_record = json.loads((self.current_job_path/'status.json').read_text())
        self.assertEqual(current_status_record['status'],'failed')
        self.assertIn('시스템 RAM 보호',current_status_record['error'])

    def test_kimodo_uses_host_memory_guard_and_records_failure(self):
        current_worker_path = queue_module.WORKFLOW_ROOT_DIRECTORY / 'generators/kimodo/worker.py'
        (self.current_job_path / 'gpu-command.json').write_text(json.dumps({'command':['python',str(current_worker_path)], 'service':'image'}))
        current_worker_mock = Mock(returncode=-9)
        current_worker_mock.poll.return_value = -9
        current_guard_event = Mock()
        current_guard_thread = Mock()
        with patch.object(queue_module, 'read_gpu_memory', return_value=(98304, 98304)), patch.object(queue_module.subprocess, 'Popen', return_value=current_worker_mock), patch.object(queue_module, 'start_animate_memory_guard', return_value=(current_guard_event, current_guard_thread, {'error':'시스템 RAM 보호: 시험'})) as current_guard_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path), -9)
        current_guard_mock.assert_called_once_with(current_worker_mock)
        current_status_record = json.loads((self.current_job_path / 'status.json').read_text())
        self.assertEqual(current_status_record['status'], 'failed')
        self.assertIn('시스템 RAM 보호', current_status_record['error'])

    def test_flux_workers_use_host_memory_guard_and_record_failure(self):
        for current_runner_name in ('run_flux_image.py','run_flux_expression.py'):
            with self.subTest(runner=current_runner_name):
                current_worker_path = queue_module.WORKFLOW_ROOT_DIRECTORY / 'generators/image' / current_runner_name
                (self.current_job_path / 'gpu-command.json').write_text(json.dumps({'command':['python',str(current_worker_path)],'service':'flux-image'}))
                (self.current_job_path / 'status.json').write_text('{"status":"running"}')
                (self.current_job_path / 'request.json').write_text(json.dumps({'width':512, 'height':512, 'steps':16, 'images':[]}))
                current_worker_mock = Mock(returncode=-9)
                current_worker_mock.poll.return_value = -9
                current_guard_event, current_guard_thread = Mock(), Mock()
                with patch.dict(queue_module.GPU_MEMORY_REQUIREMENTS, {'flux-image':2048}), patch.object(queue_module,'read_gpu_memory',return_value=(98304,98304)), patch.object(queue_module.subprocess,'Popen',return_value=current_worker_mock), patch.object(queue_module,'start_animate_memory_guard',return_value=(current_guard_event,current_guard_thread,{'error':'시스템 RAM 보호: 시험'})) as current_guard_mock:
                    self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),-9)
                current_guard_mock.assert_called_once_with(current_worker_mock)
                current_status_record = json.loads((self.current_job_path / 'status.json').read_text())
                self.assertEqual(current_status_record['status'],'failed')
                self.assertIn('시스템 RAM 보호',current_status_record['error'])

    def test_audio_and_translation_use_host_memory_guard(self):
        for current_worker_name,current_service_name in (('generators/music/worker.py','music-heartmula'),('generators/music/worker.py','sfx-dasheng-audiogen'),('generators/prompt_translation/worker.py','prompt-translation')):
            with self.subTest(service=current_service_name):
                current_worker_path=queue_module.WORKFLOW_ROOT_DIRECTORY/current_worker_name
                current_command_values=['python','-u',str(current_worker_path)] if current_service_name!='prompt-translation' else ['python',str(current_worker_path)]
                (self.current_job_path/'gpu-command.json').write_text(json.dumps({'command':current_command_values,'service':current_service_name}))
                (self.current_job_path/'status.json').write_text('{"status":"running"}')
                current_worker_mock=Mock(returncode=-9)
                current_worker_mock.poll.return_value=-9
                current_guard_event,current_guard_thread=Mock(),Mock()
                with patch.object(queue_module,'read_gpu_memory',return_value=(98304,98304)),patch.object(queue_module.subprocess,'Popen',return_value=current_worker_mock),patch.object(queue_module,'start_animate_memory_guard',return_value=(current_guard_event,current_guard_thread,{'error':'시스템 RAM 보호: 시험'})) as current_guard_mock:
                    self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),-9)
                if current_service_name=='prompt-translation':
                    current_guard_mock.assert_called_once_with(current_worker_mock,current_include_group=True)
                else:
                    current_guard_mock.assert_called_once_with(current_worker_mock)
                current_status_record=json.loads((self.current_job_path/'status.json').read_text())
                self.assertEqual(current_status_record['status'],'failed')
                self.assertIn('시스템 RAM 보호',current_status_record['error'])

    def test_hermes_uses_pidfd_group_memory_guard(self):
        import os
        (self.current_job_path/'gpu-command.json').write_text(json.dumps({'command':['python','hermes-worker'],'service':'hermes-agent'}))
        current_worker_mock=Mock(pid=os.getpid(),returncode=-9)
        current_worker_mock.poll.return_value=-9
        current_fd_value=os.open('/dev/null',os.O_RDONLY)
        with patch.object(queue_module,'read_gpu_memory',return_value=(98304,98304)),patch.object(queue_module.subprocess,'Popen',return_value=current_worker_mock),patch.object(queue_module.os,'pidfd_open',return_value=current_fd_value),patch.object(queue_module.signal,'pidfd_send_signal') as current_signal_mock,patch.object(queue_module,'stop_hermes_worker_process_group') as current_cleanup_mock,patch.object(queue_module,'start_animate_memory_guard',return_value=(Mock(),Mock(),{'error':'시스템 RAM 보호: 시험'})) as current_guard_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),-9)
            current_callback=current_guard_mock.call_args.kwargs['current_terminate_callback']
            self.assertTrue(current_guard_mock.call_args.kwargs['current_include_group'])
            current_callback()
            current_signal_mock.assert_any_call(current_fd_value,queue_module.signal.SIGKILL,None,queue_module.HERMES_PIDFD_GROUP_FLAG)
            self.assertTrue(current_cleanup_mock.called)
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'failed')

    def test_kimodo_build_uses_group_memory_guard_and_records_failure(self):
        current_worker_path=queue_module.WORKFLOW_ROOT_DIRECTORY/'generators/kimodo/migraphx_build_worker.py'
        (self.current_job_path/'gpu-command.json').write_text(json.dumps({'command':['python',str(current_worker_path)],'service':'image'}))
        current_worker_mock=Mock(returncode=-9)
        current_worker_mock.poll.return_value=-9
        with patch.object(queue_module,'read_gpu_memory',return_value=(98304,98304)),patch.object(queue_module.subprocess,'Popen',return_value=current_worker_mock),patch.object(queue_module,'start_animate_memory_guard',return_value=(Mock(),Mock(),{'error':'시스템 RAM 보호: 시험'})) as current_guard_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),-9)
        current_guard_mock.assert_called_once_with(current_worker_mock,current_include_group=True)
        current_status_record=json.loads((self.current_job_path/'status.json').read_text())
        self.assertEqual(current_status_record['status'],'failed')
        self.assertIn('시스템 RAM 보호',current_status_record['error'])

    def test_writer_cancel_pidfd_failure_preserves_reservation(self):
        import os
        (self.current_job_path/'gpu-command.json').write_text(json.dumps({'command':['python','worker.py'],'service':'writer-agent'}))
        current_worker_mock=Mock(pid=os.getpid(),returncode=-9)
        current_worker_mock.poll.side_effect=[None,0]
        def launch_test_worker(*current_args,**current_kwargs):
            (self.current_job_path/'cancel.request').touch()
            return current_worker_mock
        with patch.object(queue_module,'read_gpu_memory',return_value=(98304,98304)),patch.object(queue_module.subprocess,'Popen',side_effect=launch_test_worker),patch.object(queue_module.os,'pidfd_open',side_effect=OSError('pidfd failure')):
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),1)
        current_reservation_paths=list((queue_module.GPU_QUEUE_DIRECTORY/'active').glob('*.json'))
        self.assertEqual(len(current_reservation_paths),1)
        current_reservation_record=json.loads(current_reservation_paths[0].read_text())
        self.assertIs(current_reservation_record['cleanup_unverified'],True)
        self.assertFalse(queue_module.recover_stale_hermes_reservation(current_reservation_record))
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'failed')

    def test_writer_worker_uses_group_memory_guard(self):
        (self.current_job_path/'gpu-command.json').write_text(json.dumps({'command':['python','-m','generators.writer_agent.jobs'],'service':'writer-agent'}))
        current_worker_mock=Mock(returncode=-9)
        current_worker_mock.poll.return_value=-9
        with patch.object(queue_module,'read_gpu_memory',return_value=(98304,98304)),patch.object(queue_module.subprocess,'Popen',return_value=current_worker_mock),patch.object(queue_module,'start_animate_memory_guard',return_value=(Mock(),Mock(),{'error':'시스템 RAM 보호: 시험'})) as current_guard_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),-9)
        current_guard_mock.assert_called_once_with(current_worker_mock,current_include_group=True)
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'failed')

    def test_wan_fun_uses_host_memory_guard(self):
        current_worker_path=queue_module.WORKFLOW_ROOT_DIRECTORY/'generators/wan_fun/worker.py'
        (self.current_job_path/'gpu-command.json').write_text(json.dumps({'command':['python',str(current_worker_path)],'service':'anny'}))
        (self.current_job_path/'request.json').write_text(json.dumps({'width':832,'height':480,'frames':113}))
        current_worker_mock=Mock(returncode=0)
        current_worker_mock.poll.return_value=0
        current_event_mock=Mock()
        current_thread_mock=Mock()
        with patch.object(queue_module,'read_gpu_memory',return_value=(98304,90000)),patch.object(queue_module.subprocess,'Popen',return_value=current_worker_mock),patch.object(queue_module,'start_animate_memory_guard',return_value=(current_event_mock,current_thread_mock,{})) as current_guard_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
            current_guard_mock.assert_called_once_with(current_worker_mock)

    def test_wan_vace_uses_host_memory_guard(self):
        current_worker_path = queue_module.WORKFLOW_ROOT_DIRECTORY/'generators/wan_vace/worker.py'
        (self.current_job_path/'gpu-command.json').write_text(json.dumps({'command':['python',str(current_worker_path)],'service':'image'}))
        (self.current_job_path/'request.json').write_text(json.dumps({'width':832,'height':480,'frames':65,'model_profile':'official-bf16-resident-v1'}))
        current_worker_mock = Mock(returncode=0)
        current_worker_mock.poll.return_value = 0
        with patch.object(queue_module,'read_gpu_memory',return_value=(98304,98304)), patch.object(queue_module.subprocess,'Popen',return_value=current_worker_mock), patch.object(queue_module,'start_animate_memory_guard',return_value=(Mock(),Mock(),{})) as current_guard_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
            current_guard_mock.assert_called_once_with(current_worker_mock)

    def test_insufficient_total_memory_fails_explicitly(self):
        with patch.object(queue_module,'read_gpu_memory',return_value=(1000,1000)),patch.object(queue_module.subprocess,'Popen') as worker_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),1)
            worker_launch_mock.assert_not_called()
        self.assertIn('요구량',json.loads((self.current_job_path/'status.json').read_text())['error'])

    def test_system_available_memory_limits_gpu_queue(self):
        def check_waiting_memory(current_delay_seconds):
            current_status_record=json.loads((self.current_job_path/'status.json').read_text())
            self.assertEqual(current_status_record['free_memory_mib'],20000)
            self.assertEqual(current_status_record['host_available_memory_mib'],1000)
            self.assertEqual(current_status_record['available_memory_mib'],0)
            queue_module.cancel_gpu_generation(self.current_job_path)
        with patch.object(queue_module,'read_gpu_memory',return_value=(24000,20000)),patch.object(queue_module,'read_host_available_memory',return_value=1000),patch.object(queue_module.time,'sleep',side_effect=check_waiting_memory),patch.object(queue_module.subprocess,'Popen') as current_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
            current_launch_mock.assert_not_called()

    def test_shared_gtt_preserves_host_reserve_before_launch(self):
        current_host_reserve=queue_module.HOST_MEMORY_RESERVE_KIB//1024
        self.assertEqual(queue_module.calculate_gpu_pool_capacity('gtt',20000,current_host_reserve+1000),1000)
        self.assertEqual(queue_module.calculate_gpu_pool_capacity('gtt',20000,current_host_reserve-1),0)
        def check_waiting_memory(current_delay_seconds):
            current_status_record=json.loads((self.current_job_path/'status.json').read_text())
            self.assertEqual(current_status_record['available_memory_mib'],1000)
            current_launch_mock.assert_not_called()
            queue_module.cancel_gpu_generation(self.current_job_path)
        with patch.object(queue_module,'read_gpu_memory',return_value=(24000,20000)),patch.object(queue_module,'read_host_available_memory',return_value=current_host_reserve+1000),patch.object(queue_module.time,'sleep',side_effect=check_waiting_memory),patch.object(queue_module.subprocess,'Popen') as current_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
            current_launch_mock.assert_not_called()

    def test_gtt_host_reserve_and_active_reservation_are_both_respected(self):
        import os
        current_active_root=queue_module.GPU_QUEUE_DIRECTORY/'active'
        current_active_root.mkdir(parents=True)
        current_reservation_path=current_active_root/'existing.json'
        current_reservation_path.write_text(json.dumps({'pid':os.getpid(),'service':'image','required_memory_mib':4096}))
        current_host_reserve=queue_module.HOST_MEMORY_RESERVE_KIB//1024
        current_worker_mock=Mock(returncode=0)
        current_worker_mock.poll.return_value=0
        current_wait_count=[]
        def release_test_reservation(current_delay_seconds):
            current_status_record=json.loads((self.current_job_path/'status.json').read_text())
            self.assertEqual(current_status_record['status'],'queued')
            self.assertEqual(current_status_record['host_available_memory_mib'],current_host_reserve+5000)
            self.assertEqual(current_status_record['reserved_memory_mib'],4096)
            self.assertEqual(current_status_record['available_memory_mib'],904)
            current_launch_mock.assert_not_called()
            current_reservation_path.unlink()
            current_wait_count.append(1)
        with patch.object(queue_module,'read_gpu_memory',return_value=(24000,20000)),patch.object(queue_module,'read_host_available_memory',return_value=current_host_reserve+5000),patch.object(queue_module.time,'sleep',side_effect=release_test_reservation),patch.object(queue_module.subprocess,'Popen',return_value=current_worker_mock) as current_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
            current_launch_mock.assert_called_once()
        self.assertEqual(len(current_wait_count),1)
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'completed')

    def test_vram_pool_is_not_limited_to_gtt_host_available(self):
        current_worker_mock=Mock(returncode=0)
        current_worker_mock.poll.return_value=0
        with patch.object(queue_module,'read_gpu_memory',return_value=(98304,90000)),patch.object(queue_module,'read_gpu_memory_domain',return_value='vram'),patch.object(queue_module,'read_host_available_memory',return_value=15000),patch.object(queue_module.subprocess,'Popen',return_value=current_worker_mock) as current_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
            current_launch_mock.assert_called_once()

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

    def test_queue_revision_tracks_host_memory_guard_changes(self):
        current_source_root=Path(self.temporary_job_root.name)/'queue-sources'
        current_source_root.mkdir()
        for current_file_name in ('gpu_job_queue.py','gpu_memory_history.py','host_memory_guard.py'):
            (current_source_root/current_file_name).write_text('initial')
        with patch.object(queue_module,'__file__',str(current_source_root/'gpu_job_queue.py')):
            current_initial_revision=queue_module.calculate_queue_revision()
            (current_source_root/'host_memory_guard.py').write_text('updated host reserve')
            self.assertNotEqual(queue_module.calculate_queue_revision(),current_initial_revision)
            current_after_guard_revision=queue_module.calculate_queue_revision()
            (current_source_root/'gpu_memory_history.py').write_text('updated estimate')
            self.assertNotEqual(queue_module.calculate_queue_revision(),current_after_guard_revision)

    def test_real_waiting_reload_preserves_pid_ticket_and_arguments(self):
        import os
        import subprocess
        import sys
        current_test_root=Path(self.temporary_job_root.name)/'real-reload'
        current_test_root.mkdir()
        current_ticket_path=current_test_root/'00000000000000000123.json'
        current_ticket_bytes=b'{"existing":"ticket"}\n'
        current_ticket_path.write_bytes(current_ticket_bytes)
        current_shim_path=current_test_root/'replacement.py'
        current_shim_path.write_text("import json,os,sys; print(json.dumps({'pid':os.getpid(),'ticket':os.environ.get('SLIME_GPU_QUEUE_TICKET'),'args':sys.argv[1:]}))")
        current_launcher_code="import os,sys; from pathlib import Path; from tools.review.common import gpu_job_queue as q; q.__file__=sys.argv[1]; q.calculate_queue_revision=lambda:'new'; sys.argv=[sys.argv[1],'--job-dir',sys.argv[3]]; print('original-pid='+str(os.getpid()),flush=True); q.reload_waiting_executor(Path(os.environ['TEST_QUEUE_TICKET']),'old')"
        current_environment_values=dict(os.environ,TEST_QUEUE_TICKET=str(current_ticket_path))
        current_process_result=subprocess.run([sys.executable,'-c',current_launcher_code,str(current_shim_path),str(current_ticket_path),'isolated-job'],env=current_environment_values,capture_output=True,text=True,timeout=10)
        self.assertEqual(current_process_result.returncode,0,current_process_result.stderr)
        current_output_lines=current_process_result.stdout.splitlines()
        self.assertEqual(len(current_output_lines),2)
        current_original_pid=int(current_output_lines[0].removeprefix('original-pid='))
        current_result_record=json.loads(current_output_lines[1])
        self.assertEqual(current_result_record['pid'],current_original_pid)
        self.assertEqual(current_result_record['ticket'],str(current_ticket_path.resolve()))
        self.assertEqual(current_result_record['args'],['--job-dir','isolated-job'])
        self.assertEqual(current_ticket_path.read_bytes(),current_ticket_bytes)

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
        gpu_memory_history.save_memory_observation('image','previous',7538,3,'completed',command_identity_name='run_qwen_21_reference.py:1280x1280:steps=4:references=0:offload=none-full-v1')
        (self.current_job_path/'request.json').write_text(json.dumps({'width':1280,'height':1280,'steps':4}))
        (self.current_job_path/'gpu-command.json').write_text(json.dumps({'command':['python','run_qwen_21_reference.py'],'service':'image'}))
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
