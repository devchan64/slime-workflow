"""실제 GPU 작업 없이 메모리 대기·중지·실패·재개 계약 검증."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from workflow.common import gpu_job_queue as queue_module

class GpuJobQueueTests(unittest.TestCase):
    def test_minimax_h3_image_uses_exclusive_confined_reservation(self):
        service = 'minimax-h3-image'
        self.assertIn(service, queue_module.GPU_EXCLUSIVE_SERVICES)
        self.assertEqual(queue_module.GPU_MEMORY_REQUIREMENTS[service], 81920)
        self.assertTrue(queue_module.is_dedicated_gpu_source_verifiable(service))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job = root / '.tmp/test/minimax-h3-image/example'
            job.mkdir(parents=True)
            self.assertEqual(queue_module.identify_dedicated_gpu_reservation_source(str(job), service, root), service)
            other = root / '.tmp/test/minimax-h3-i2v/example'
            other.mkdir(parents=True)
            self.assertIsNone(queue_module.identify_dedicated_gpu_reservation_source(str(other), service, root))
            link = job.parent / 'linked'
            link.symlink_to(other, target_is_directory=True)
            self.assertIsNone(queue_module.identify_dedicated_gpu_reservation_source(str(link), service, root))

    def test_minimax_h3_image_keeps_memory_floor_after_small_run(self):
        from workflow.common.gpu_memory_history import estimate_required_memory
        with patch('workflow.common.gpu_memory_history.load_recent_observations', return_value=[]), \
             patch('workflow.common.gpu_memory_history.summarize_memory_observations', return_value={
                 'peak_memory_mib': 1024, 'usable_runs': 1, 'retained_runs': 1,
             }):
            self.assertEqual(estimate_required_memory('minimax-h3-image', 81920)['required_memory_mib'], 81920)

    def test_minimax_h3_experiment_has_exclusive_reservation_and_confined_source(self):
        service = 'minimax-h3-experiment'
        self.assertIn(service, queue_module.GPU_EXCLUSIVE_SERVICES)
        self.assertEqual(queue_module.GPU_MEMORY_REQUIREMENTS[service], 81920)
        self.assertTrue(queue_module.is_dedicated_gpu_source_verifiable(service))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job = root / '.tmp/test/minimax-h3-experiment/example'
            job.mkdir(parents=True)
            self.assertEqual(queue_module.identify_dedicated_gpu_reservation_source(str(job), service, root), service)
            self.assertIsNone(queue_module.identify_dedicated_gpu_reservation_source(str(job.parent.parent / 'other' / job.name), service, root))

    def test_release_selection_respects_earlier_chat_admission(self):
        import os
        with tempfile.TemporaryDirectory() as temporary_directory:
            root_directory = Path(temporary_directory)
            job_directory = root_directory / 'generation'
            job_directory.mkdir()
            (job_directory / 'gpu-command.json').write_text(json.dumps({'service':'image', 'command':['worker']}))
            ticket_path = root_directory / f'{2:020d}-{os.getpid()}.json'
            ticket_path.write_text(json.dumps({'path':str(job_directory), 'pid':os.getpid()}))
            admission_record = {'session_id':'b'*32, 'resident_id':'start_' + 'a'*64, 'order_ns':1}
            with patch.object(queue_module, 'read_priority_tickets', return_value=[ticket_path]), \
                 patch.object(queue_module, 'read_gpu_priority_order', return_value={}), \
                 patch.object(queue_module, 'inspect_gpu_ticket_executor_identity', return_value='verified'), \
                 patch.object(queue_module, 'estimate_required_memory', return_value={'required_memory_mib':80}), \
                 patch.object(queue_module, 'identify_execution_command', return_value='test'), \
                 patch.object(queue_module, 'identify_hermes_memory_profile', return_value='test'), \
                 patch('workflow.common.gpu_chat_admission.list_live_chat_admissions', return_value=[admission_record]):
                self.assertIsNone(queue_module.select_ticket_after_resident_release(20, 100, 'vram', 'a'*32, 20000, 20000))
                with patch.object(queue_module, 'read_gpu_priority_order', return_value={ticket_path.name:-1}):
                    self.assertEqual(queue_module.select_ticket_after_resident_release(20, 100, 'vram', 'a'*32, 20000, 20000), ticket_path)

    def test_release_selection_respects_priority_and_cancelled_tickets(self):
        import os
        with tempfile.TemporaryDirectory() as temporary_directory:
            root_directory = Path(temporary_directory)
            candidate_directories = [root_directory / 'first', root_directory / 'second']
            ticket_paths = []
            for ticket_index, candidate_directory in enumerate(candidate_directories):
                candidate_directory.mkdir()
                (candidate_directory / 'gpu-command.json').write_text(json.dumps({'service':'image', 'command':['worker']}))
                candidate_ticket = root_directory / f'{ticket_index + 1:020d}-{os.getpid()}.json'
                candidate_ticket.write_text(json.dumps({'path':str(candidate_directory), 'pid':os.getpid()}))
                ticket_paths.append(candidate_ticket)
            with patch.object(queue_module, 'read_priority_tickets', return_value=ticket_paths), \
                 patch.object(queue_module, 'inspect_gpu_ticket_executor_identity', return_value='verified'), \
                 patch.object(queue_module, 'estimate_required_memory', return_value={'required_memory_mib':80}), \
                 patch.object(queue_module, 'identify_execution_command', return_value='test'), \
                 patch('workflow.common.gpu_chat_admission.list_live_chat_admissions', return_value=[]):
                self.assertEqual(queue_module.select_ticket_after_resident_release(20, 100, 'vram', 'a'*32, 20000, 20000), ticket_paths[0])
                (candidate_directories[0] / 'cancel.request').touch()
                self.assertEqual(queue_module.select_ticket_after_resident_release(20, 100, 'vram', 'a'*32, 20000, 20000), ticket_paths[1])
                (candidate_directories[1] / 'pause.request').touch()
                self.assertIsNone(queue_module.select_ticket_after_resident_release(20, 100, 'vram', 'a'*32, 20000, 20000))

    def test_release_candidate_must_be_newly_runnable_generation(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            job_directory = Path(temporary_directory) / 'job'
            job_directory.mkdir()
            ticket_path = Path(temporary_directory) / 'ticket.json'
            ticket_path.write_text(json.dumps({'path':str(job_directory)}))
            command_path = job_directory / 'gpu-command.json'
            command_path.write_text(json.dumps({'service':'image'}))
            with patch.object(queue_module, 'select_runnable_ticket', side_effect=[None, ticket_path]):
                self.assertEqual(queue_module.select_ticket_after_resident_release(10, 100, 'vram', 'a'*32, 20, 30), ticket_path)
            with patch.object(queue_module, 'select_runnable_ticket', side_effect=[ticket_path]):
                self.assertIsNone(queue_module.select_ticket_after_resident_release(10, 100, 'vram', 'a'*32, 20, 30))
            command_path.write_text(json.dumps({'service':'hermes-agent'}))
            with patch.object(queue_module, 'select_runnable_ticket', side_effect=[None, ticket_path]), \
                 patch.object(queue_module, 'is_hermes_resident_job', return_value=False):
                self.assertIsNone(queue_module.select_ticket_after_resident_release(10, 100, 'vram', 'a'*32, 20, 30))
            with patch.object(queue_module, 'select_runnable_ticket', side_effect=[None, ticket_path]), \
                 patch.object(queue_module, 'is_hermes_resident_job', return_value=True), \
                 patch.object(queue_module, 'read_hermes_queue_session', return_value='b'*32):
                self.assertEqual(queue_module.select_ticket_after_resident_release(10, 100, 'vram', 'a'*32, 20, 30), ticket_path)
            with patch.object(queue_module, 'select_runnable_ticket', side_effect=[None, ticket_path]), \
                 patch.object(queue_module, 'is_hermes_resident_job', return_value=True), \
                 patch.object(queue_module, 'read_hermes_queue_session', return_value='a'*32):
                self.assertIsNone(queue_module.select_ticket_after_resident_release(10, 100, 'vram', 'a'*32, 20, 30))
            with self.assertRaises(ValueError):
                queue_module.select_ticket_after_resident_release(100, 10, 'vram', 'a'*32, 20, 30)
            with patch.object(queue_module, 'select_runnable_ticket', side_effect=[None, ticket_path]) as selection_mock:
                command_path.write_text(json.dumps({'service':'image'}))
                self.assertEqual(queue_module.select_ticket_after_resident_release(10, 100, 'vram', ['a'*32, 'b'*32], 20, 30), ticket_path)
                self.assertEqual(selection_mock.call_args_list[0].args[2:4], (['hermes-agent', 'hermes-agent'], ['a'*32, 'b'*32]))
            with self.assertRaises(ValueError):
                queue_module.select_ticket_after_resident_release(10, 100, 'vram', ['a'*32, 'a'*32], 20, 30)

    def test_kimodo_concurrency_limit_does_not_block_other_images(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kimodo = root / '.tmp/test/kimodo/job-1'
            other = root / '.tmp/test/other/job-2'
            kimodo.mkdir(parents=True)
            other.mkdir(parents=True)
            for job in (kimodo, other):
                (job / 'gpu-command.json').write_text(json.dumps({'command':['python'], 'service':'image'}))
            ticket = root / 'ticket.json'
            ticket.write_text(json.dumps({'pid':os.getpid(), 'path':str(kimodo)}))
            with patch.object(queue_module, 'WORKFLOW_ROOT_DIRECTORY', root), patch.object(queue_module, 'read_priority_tickets', return_value=[ticket]), patch.object(queue_module, 'estimate_required_memory', return_value={'required_memory_mib':1}):
                self.assertEqual(queue_module.select_runnable_ticket(100,'vram',active_kimodo_count=1), ticket)
                self.assertIsNone(queue_module.select_runnable_ticket(100,'vram',active_kimodo_count=2))
                ticket.write_text(json.dumps({'pid':os.getpid(), 'path':str(other)}))
                self.assertEqual(queue_module.select_runnable_ticket(100,'vram',active_kimodo_count=2), ticket)

    def test_resume_extra_validation_runs_under_locks_and_preserves_failed_job(self):
        import fcntl
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_path=Path(current_directory_name)/'job'
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text('{}')
            (current_job_path/'status.json').write_text('{"status":"failed"}')
            (current_job_path/'gpu-command.json').write_text(json.dumps({'command':['worker'],'service':'image'}))
            (current_job_path/'cancel.request').touch()
            current_fingerprint_value=queue_module.fingerprint_resume_job_records(current_job_path)
            def reject_current_resume(current_observed_path):
                self.assertEqual(current_observed_path,current_job_path)
                for current_lock_name in ('resume.lock','execution.lock'):
                    with (current_job_path/current_lock_name).open('a') as current_lock_stream:
                        with self.assertRaises(BlockingIOError):fcntl.flock(current_lock_stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
                raise ValueError('키프레임 변경')
            with patch.object(queue_module,'launch_gpu_process') as current_launch_mock:
                with self.assertRaisesRegex(ValueError,'키프레임 변경'):
                    queue_module.resume_gpu_generation(current_job_path,expected_resume_fingerprint=current_fingerprint_value,expected_resume_service='image',expected_resume_command=['worker'],resume_validation_callback=reject_current_resume)
                self.assertEqual(json.loads((current_job_path/'status.json').read_text())['status'],'failed')
                self.assertTrue((current_job_path/'cancel.request').exists())
                current_launch_mock.assert_not_called()
                with self.assertRaises(ValueError):queue_module.resume_gpu_generation(current_job_path,resume_validation_callback=reject_current_resume)

    def test_resume_and_cancel_reject_symlink_lock_without_touching_target(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_path=current_root_path/'job'
            current_job_path.mkdir()
            current_target_path=current_root_path/'target'
            current_target_path.write_text('unchanged')
            (current_job_path/'resume.lock').symlink_to(current_target_path)
            for current_operation in (queue_module.resume_gpu_generation,queue_module.cancel_gpu_generation):
                with self.subTest(current_operation=current_operation.__name__),self.assertRaisesRegex(ValueError,'심볼릭 링크'):
                    current_operation(current_job_path)
            self.assertEqual(current_target_path.read_text(),'unchanged')
            self.assertFalse((current_job_path/'status.json').exists())

    def test_priority_access_error_is_not_treated_as_absent(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_queue_path=Path(current_directory_name)
            current_priority_path=current_queue_path/'priority-order'
            current_priority_path.write_text('{"ticket.json":-1}')
            current_read_text=Path.read_text
            def reject_priority_read(current_path_value,*current_arguments,**current_keywords):
                if current_path_value==current_priority_path:raise PermissionError('unreadable')
                return current_read_text(current_path_value,*current_arguments,**current_keywords)
            with patch.object(queue_module,'GPU_QUEUE_DIRECTORY',current_queue_path),patch.object(Path,'exists',return_value=False),patch.object(Path,'read_text',autospec=True,side_effect=reject_priority_read),patch.object(queue_module,'write_record_atomically') as current_write_mock:
                with self.assertRaises(PermissionError):queue_module.read_priority_tickets()
                with self.assertRaises(PermissionError):queue_module.prioritize_waiting_generation('job-1')
                self.assertIsNone(queue_module.select_runnable_ticket(1024,'vram'))
                current_write_mock.assert_not_called()
            self.assertEqual(current_priority_path.read_text(),'{"ticket.json":-1}')
            current_priority_path.unlink()
            with patch.object(queue_module,'GPU_QUEUE_DIRECTORY',current_queue_path):
                self.assertEqual(queue_module.read_gpu_priority_order(),{})
            with patch.object(queue_module,'GPU_QUEUE_DIRECTORY',current_queue_path/'not-yet-created'):
                self.assertEqual(queue_module.read_priority_tickets(),[])
                self.assertEqual(queue_module.list_waiting_gpu_jobs(include_source_identity=True),{'jobs':[]})

    def test_missing_job_record_does_not_hide_unreadable_ticket(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_path=current_root_path/'job-1'
            current_job_path.mkdir()
            current_ticket_path=current_root_path/'ticket.json'
            current_ticket_path.write_text(json.dumps({'pid':123,'path':str(current_job_path)}))
            with patch.object(queue_module,'read_priority_tickets',return_value=[current_ticket_path]),patch.object(queue_module.os,'kill'),patch.object(queue_module,'fingerprint_gpu_queue_ticket',return_value='a'*64),patch.object(Path,'exists',return_value=False),patch.object(Path,'lstat',side_effect=PermissionError('unreadable')):
                self.assertIsNone(queue_module.select_runnable_ticket(1024,'vram'))
                with self.assertRaises(PermissionError):queue_module.list_waiting_gpu_jobs(include_source_identity=True)
            current_ticket_path.unlink()
            with patch.object(queue_module,'read_priority_tickets',return_value=[current_ticket_path]),patch.object(queue_module,'fingerprint_gpu_queue_ticket',return_value='a'*64):
                self.assertIsNone(queue_module.select_runnable_ticket(1024,'vram'))
                self.assertEqual(queue_module.list_waiting_gpu_jobs(include_source_identity=True),{'jobs':[]})

    def test_waiting_control_error_or_pause_cannot_start_or_prioritize(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_path=current_root_path/'job-1'
            current_job_path.mkdir()
            (current_job_path/'status.json').write_text('{"status":"queued"}')
            (current_job_path/'gpu-command.json').write_text(json.dumps({'service':'image','command':['python','worker.py']}))
            current_ticket_path=current_root_path/'ticket.json'
            current_ticket_path.write_text(json.dumps({'pid':123,'path':str(current_job_path)}))
            current_lstat_method=Path.lstat
            def reject_cancel_stat(current_path_value,*current_arguments,**current_keywords):
                if current_path_value==current_job_path/'cancel.request':raise PermissionError('unreadable')
                return current_lstat_method(current_path_value,*current_arguments,**current_keywords)
            with patch.object(queue_module,'GPU_QUEUE_DIRECTORY',current_root_path),patch.object(queue_module,'read_priority_tickets',return_value=[current_ticket_path]),patch.object(queue_module.os,'kill'),patch.object(Path,'exists',return_value=False),patch.object(Path,'lstat',autospec=True,side_effect=reject_cancel_stat),patch.object(queue_module,'write_record_atomically') as current_write_mock:
                self.assertIsNone(queue_module.select_runnable_ticket(1024,'vram'))
                with self.assertRaises(PermissionError):queue_module.prioritize_waiting_generation('job-1')
                current_write_mock.assert_not_called()
            (current_job_path/'pause.request').touch()
            with patch.object(queue_module,'read_priority_tickets',return_value=[current_ticket_path]),patch.object(queue_module.os,'kill'):
                self.assertIsNone(queue_module.select_runnable_ticket(1024,'vram'))

    def test_cancel_request_preserves_queued_state_and_cancels_paused_record(self):
        for current_status_value in ('queued','running','paused'):
            with self.subTest(status=current_status_value),tempfile.TemporaryDirectory() as current_directory_name:
                current_job_path=Path(current_directory_name)
                (current_job_path/'status.json').write_text(json.dumps({'status':current_status_value}))
                with patch.object(queue_module.os,'kill') as current_kill_mock,patch.object(queue_module.os,'killpg') as current_group_mock:
                    current_result_value=queue_module.cancel_gpu_generation(current_job_path)
                self.assertTrue(current_result_value['cancel_requested'])
                self.assertTrue((current_job_path/'cancel.request').is_file())
                current_saved_status=json.loads((current_job_path/'status.json').read_text())['status']
                self.assertEqual(current_saved_status,'cancelled' if current_status_value=='paused' else current_status_value)
                current_kill_mock.assert_not_called()
                current_group_mock.assert_not_called()
                if current_status_value=='paused':
                    with self.assertRaises(ValueError):queue_module.cancel_gpu_generation(current_job_path)

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

    def test_hermes_parallel_only_distinct_known_sessions_with_capacity(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job = root / 'job'; job.mkdir()
            (job / 'gpu-command.json').write_text(json.dumps({'command':['python','worker.py'],'service':'hermes-agent'}))
            request = job / 'request.json'
            request.write_text(json.dumps({'context':{'session_id':'b'*32}}))
            ticket = root / 'ticket.json'; ticket.write_text(json.dumps({'pid':os.getpid(),'path':str(job)}))
            with patch.object(queue_module,'read_priority_tickets',return_value=[ticket]), patch.object(queue_module,'estimate_required_memory',return_value={'required_memory_mib':16}):
                self.assertEqual(queue_module.select_runnable_ticket(16,'vram',['hermes-agent'],['a'*32]),ticket)
                self.assertIsNone(queue_module.select_runnable_ticket(15,'vram',['hermes-agent'],['a'*32]))
                self.assertIsNone(queue_module.select_runnable_ticket(100,'vram',['hermes-agent'],['b'*32]))
                self.assertIsNone(queue_module.select_runnable_ticket(100,'vram',['hermes-agent','hermes-agent'],['a'*32,'c'*32]))
                self.assertIsNone(queue_module.select_runnable_ticket(100,'vram',['hermes-agent'],[None]))
                self.assertEqual(queue_module.select_runnable_ticket(100,'vram',['hermes-agent','image'],['a'*32]),ticket)
                self.assertIsNone(queue_module.select_runnable_ticket(100,'vram',['management-setup'],[]))
                request.write_text(json.dumps({'context':{'session_id':'invalid'}}))
                self.assertIsNone(queue_module.select_runnable_ticket(100,'vram',['hermes-agent'],['a'*32]))

    def test_waiting_same_session_does_not_block_other_session(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); tickets=[]
            for index, session in enumerate(('a'*32, 'b'*32)):
                job=root / str(index);job.mkdir()
                (job/'gpu-command.json').write_text(json.dumps({'command':['python','worker.py'],'service':'hermes-agent'}))
                (job/'request.json').write_text(json.dumps({'context':{'session_id':session}}))
                ticket=root / f'{index}.json';ticket.write_text(json.dumps({'pid':os.getpid(),'path':str(job)}));tickets.append(ticket)
            with patch.object(queue_module,'read_priority_tickets',return_value=tickets), patch.object(queue_module,'estimate_required_memory',return_value={'required_memory_mib':16}):
                self.assertEqual(queue_module.select_runnable_ticket(16,'vram',['hermes-agent'],['a'*32]),tickets[1])
                self.assertEqual(queue_module.select_runnable_ticket(16,'vram',[],[]),tickets[0])

    def test_hermes_can_run_with_active_work_when_memory_allows(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_root_path = Path(current_temp_directory)
            current_job_path = current_root_path / 'job'
            current_job_path.mkdir()
            (current_job_path / 'gpu-command.json').write_text(json.dumps({'command': ['python', 'worker.py'], 'service': 'hermes-agent'}))
            current_ticket_path = current_root_path / 'ticket.json'
            import os
            current_ticket_path.write_text(json.dumps({'pid': os.getpid(), 'path': str(current_job_path)}))
            with patch.object(queue_module, 'read_priority_tickets', return_value=[current_ticket_path]), patch.object(queue_module, 'estimate_required_memory', return_value={'required_memory_mib': 1}):
                self.assertEqual(queue_module.select_runnable_ticket(100, 'vram', ['image']), current_ticket_path)
                self.assertIsNone(queue_module.select_runnable_ticket(100, 'vram', ['hermes-agent']))
                self.assertEqual(queue_module.select_runnable_ticket(100, 'vram', []), current_ticket_path)

    def test_active_hermes_allows_other_waiting_work_with_capacity(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job = root / 'job'; job.mkdir()
            (job / 'gpu-command.json').write_text(json.dumps({'command':['python','worker.py'], 'service':'image'}))
            ticket = root / 'ticket.json'; ticket.write_text(json.dumps({'pid':os.getpid(), 'path':str(job)}))
            with patch.object(queue_module, 'read_priority_tickets', return_value=[ticket]), patch.object(queue_module, 'estimate_required_memory', return_value={'required_memory_mib':16}):
                self.assertEqual(queue_module.select_runnable_ticket(16, 'vram', ['hermes-agent'], ['a'*32]), ticket)
                self.assertIsNone(queue_module.select_runnable_ticket(15, 'vram', ['hermes-agent'], ['a'*32]))

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
        from workflow.common import gpu_memory_history
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
        current_memory_query_patch = patch('workflow.common.generation_telemetry.subprocess.check_output',return_value='')
        current_memory_query_patch.start()
        self.addCleanup(current_memory_query_patch.stop)

    def test_generator_runs_with_hermes_reservation_when_capacity_allows(self):
        import os
        current_active_root = queue_module.GPU_QUEUE_DIRECTORY / 'active'
        current_active_root.mkdir(parents=True)
        current_reservation_path = current_active_root / 'hermes-test.json'
        current_reservation_path.write_text(json.dumps({'pid':os.getpid(), 'service':'hermes-agent', 'required_memory_mib':1}))
        current_worker_mock = Mock(returncode=0)
        current_worker_mock.poll.return_value = 0
        with patch.object(queue_module, 'read_gpu_memory', return_value=(24000, 20000)), patch.object(queue_module.subprocess, 'Popen', return_value=current_worker_mock) as current_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path), 0)
        current_launch_mock.assert_called_once()
        self.assertEqual(json.loads((self.current_job_path / 'status.json').read_text())['status'], 'completed')
        self.assertTrue(current_reservation_path.exists())

    def test_new_other_service_records_verifiable_worker_group(self):
        import os
        import sys
        import threading
        (self.current_job_path/'gpu-command.json').write_text(json.dumps({'command':[sys.executable,'-c','import time; time.sleep(60)'],'service':'anny'}))
        current_observations=[]
        def inspect_and_cancel(current_wait_seconds):
            if current_observations:
                threading.Event().wait(min(current_wait_seconds,0.05))
                return
            current_records=list((queue_module.GPU_QUEUE_DIRECTORY/'active').glob('*.json'))
            self.assertEqual(len(current_records),1)
            current_record=json.loads(current_records[0].read_text())
            self.assertEqual(len(current_record['worker_process_token']),32)
            current_descriptor=None
            for current_attempt in range(200):
                current_descriptor=queue_module.open_verified_hermes_process_group(current_record)
                if current_descriptor is not None:break
                threading.Event().wait(0.01)
            self.assertIsNotNone(current_descriptor)
            os.close(current_descriptor)
            current_observations.append(True)
            queue_module.cancel_gpu_generation(self.current_job_path)
        with patch.object(queue_module,'read_gpu_memory',return_value=(24000,20000)),patch.object(queue_module.time,'sleep',side_effect=inspect_and_cancel):
            queue_module.execute_queued_generation(self.current_job_path)
        self.assertEqual(current_observations,[True])
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'cancelled')

    def test_dead_other_executor_does_not_release_live_child_reservation(self):
        import os
        import subprocess
        import sys
        current_active_root=queue_module.GPU_QUEUE_DIRECTORY/'active'
        current_active_root.mkdir(parents=True)
        current_child_process=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True)
        self.addCleanup(lambda: current_child_process.wait(timeout=5) if current_child_process.poll() is not None else (current_child_process.terminate(),current_child_process.wait(timeout=5)))
        current_reservation_path=current_active_root/'orphan.json'
        current_reservation_path.write_text(json.dumps({'pid':os.getpid(),'pid_start_token':'0','service':'image','required_memory_mib':1024,'worker_pgid':current_child_process.pid}))
        current_observations=[]
        def cancel_after_observation(current_wait_seconds):
            self.assertIsNone(current_child_process.poll())
            self.assertTrue(current_reservation_path.exists())
            self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'queued')
            current_worker_mock.assert_not_called()
            current_observations.append(True)
            queue_module.cancel_gpu_generation(self.current_job_path)
        with patch.object(queue_module,'read_gpu_memory',return_value=(24000,20000)),patch.object(queue_module.time,'sleep',side_effect=cancel_after_observation),patch.object(queue_module.subprocess,'Popen') as current_worker_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
        self.assertEqual(current_observations,[True])
        self.assertTrue(current_reservation_path.exists())
        self.assertIsNone(current_child_process.poll())

    def test_unreadable_reservation_directory_blocks_worker_launch(self):
        current_active_root=queue_module.GPU_QUEUE_DIRECTORY/'active'
        current_iterdir_method=Path.iterdir
        current_observations=[]
        def reject_active_listing(current_path_value,*current_arguments,**current_keywords):
            if current_path_value==current_active_root:raise PermissionError('unreadable')
            return current_iterdir_method(current_path_value,*current_arguments,**current_keywords)
        def cancel_after_observation(current_wait_seconds):
            self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'queued')
            current_launch_mock.assert_not_called()
            current_observations.append(True)
            queue_module.cancel_gpu_generation(self.current_job_path)
        with patch.object(Path,'iterdir',autospec=True,side_effect=reject_active_listing),patch.object(queue_module,'read_gpu_memory',return_value=(24000,20000)),patch.object(queue_module.time,'sleep',side_effect=cancel_after_observation),patch.object(queue_module.subprocess,'Popen') as current_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
        self.assertEqual(current_observations,[True])

    def test_unreadable_reservation_identity_does_not_fail_or_release_other_job(self):
        import os
        current_active_root=queue_module.GPU_QUEUE_DIRECTORY/'active'
        current_active_root.mkdir(parents=True)
        current_reservation_path=current_active_root/'unreadable.json'
        current_reservation_path.write_text(json.dumps({'pid':os.getpid(),'service':'image','required_memory_mib':1024}))
        current_observations=[]
        def cancel_after_observation(current_wait_seconds):
            self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'queued')
            self.assertTrue(current_reservation_path.exists())
            current_worker_mock.assert_not_called()
            current_observations.append(True)
            queue_module.cancel_gpu_generation(self.current_job_path)
        with patch.object(queue_module,'read_gpu_memory',return_value=(24000,20000)),patch.object(queue_module,'is_gpu_queue_executor_alive',side_effect=PermissionError('unavailable')),patch.object(queue_module.time,'sleep',side_effect=cancel_after_observation),patch.object(queue_module.subprocess,'Popen') as current_worker_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
        self.assertEqual(current_observations,[True])
        self.assertTrue(current_reservation_path.exists())
        (self.current_job_path/'cancel.request').unlink(missing_ok=True)
        current_observations.clear()
        with patch.object(queue_module,'read_gpu_memory',return_value=(24000,20000)),patch.object(queue_module,'is_gpu_queue_executor_alive',return_value=False),patch.object(queue_module,'recover_stale_hermes_reservation',side_effect=OSError('recovery failed')),patch.object(queue_module.time,'sleep',side_effect=cancel_after_observation),patch.object(queue_module.subprocess,'Popen') as current_worker_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
        self.assertEqual(current_observations,[True])
        self.assertTrue(current_reservation_path.exists())

    def test_malformed_active_reservation_blocks_other_work_without_deletion(self):
        import os
        current_active_root=queue_module.GPU_QUEUE_DIRECTORY/'active'
        current_active_root.mkdir(parents=True)
        current_reservation_path=current_active_root/'corrupt.json'
        current_bad_job=Path(self.temporary_job_root.name)/'bad-reservation-job'
        current_bad_job.mkdir()
        (current_bad_job/'gpu-command.json').write_text('{invalid')
        for current_bad_record in ([],{'pid':10**100,'required_memory_mib':1},{'pid':True,'required_memory_mib':1},{'pid':os.getpid()},{'pid':os.getpid(),'required_memory_mib':-1},{'pid':os.getpid(),'required_memory_mib':1,'pid_start_token':None},{'pid':os.getpid(),'required_memory_mib':1,'path':42},{'pid':os.getpid(),'required_memory_mib':1,'path':str(current_bad_job)}):
            with self.subTest(record=current_bad_record):
                current_reservation_path.write_text(json.dumps(current_bad_record))
                (self.current_job_path/'cancel.request').unlink(missing_ok=True)
                current_observations=[]
                def cancel_after_observation(current_wait_seconds):
                    current_status=json.loads((self.current_job_path/'status.json').read_text())
                    self.assertEqual(current_status['status'],'queued')
                    self.assertEqual(json.loads(current_reservation_path.read_text()),current_bad_record)
                    current_worker_mock.assert_not_called()
                    current_observations.append(True)
                    queue_module.cancel_gpu_generation(self.current_job_path)
                with patch.object(queue_module,'read_gpu_memory',return_value=(24000,20000)),patch.object(queue_module.time,'sleep',side_effect=cancel_after_observation),patch.object(queue_module.subprocess,'Popen') as current_worker_mock:
                    self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
                self.assertEqual(current_observations,[True])
                self.assertTrue(current_reservation_path.exists())

    def test_corrupt_other_ticket_preserves_waiting_job_and_can_cancel(self):
        current_queue=queue_module.GPU_QUEUE_DIRECTORY
        current_queue.mkdir()
        current_ticket=current_queue/'00000000000000000000.json'
        current_ticket.write_text('{broken')
        current_waits=[]
        def cancel_waiting_after_observation(current_wait_seconds):
            current_status=json.loads((self.current_job_path/'status.json').read_text())
            self.assertEqual(current_status['status'],'queued')
            self.assertTrue(current_ticket.exists())
            current_worker_mock.assert_not_called()
            current_waits.append(True)
            queue_module.cancel_gpu_generation(self.current_job_path)
        with patch.object(queue_module,'read_gpu_memory',return_value=(24000,20000)),patch.object(queue_module.time,'sleep',side_effect=cancel_waiting_after_observation),patch.object(queue_module.subprocess,'Popen') as current_worker_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
        self.assertEqual(current_waits,[True])
        self.assertTrue(current_ticket.exists())
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'cancelled')

    def test_corrupt_priority_order_preserves_waiting_job_and_can_cancel(self):
        current_queue=queue_module.GPU_QUEUE_DIRECTORY
        current_queue.mkdir()
        current_priority=current_queue/'priority-order'
        for current_bad_content in ('{bad','[]','{"ticket.json":"bad"}','{"ticket.json":true}'):
            current_priority.write_text(current_bad_content)
            with self.assertRaises(ValueError):queue_module.read_priority_tickets()
        def cancel_waiting_after_observation(current_wait_seconds):
            current_status=json.loads((self.current_job_path/'status.json').read_text())
            self.assertEqual(current_status['status'],'queued')
            self.assertIn('순서를 확인할 수 없어',current_status['message'])
            self.assertEqual(current_priority.read_text(),'{bad')
            current_worker_mock.assert_not_called()
            current_gpu_mock.assert_not_called()
            queue_module.cancel_gpu_generation(self.current_job_path)
        current_priority.write_text('{bad')
        with patch.object(queue_module,'read_gpu_memory') as current_gpu_mock,patch.object(queue_module.time,'sleep',side_effect=cancel_waiting_after_observation),patch.object(queue_module.subprocess,'Popen') as current_worker_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
        self.assertEqual(current_priority.read_text(),'{bad')
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'cancelled')

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

    def test_hermes_worker_model_conflict_survives_queue_finalization(self):
        import os
        (self.current_job_path/'gpu-command.json').write_text(json.dumps({'command':['python','hermes-worker'],'service':'hermes-agent'}))
        current_worker_mock = Mock(pid=os.getpid(),returncode=1)
        current_error_text = 'Hermes 모델이 준비 또는 사용 중이어서 작업을 시작하지 못했습니다.'
        def record_worker_failure():
            (self.current_job_path/'status.json').write_text(json.dumps({'status':'failed','error':current_error_text}))
            return 1
        current_worker_mock.poll.side_effect = record_worker_failure
        current_fd_value = os.open('/dev/null',os.O_RDONLY)
        with patch.object(queue_module,'read_gpu_memory',return_value=(98304,98304)), patch.object(queue_module.subprocess,'Popen',return_value=current_worker_mock), patch.object(queue_module.os,'pidfd_open',return_value=current_fd_value), patch.object(queue_module,'stop_hermes_worker_process_group'), patch.object(queue_module,'start_animate_memory_guard',return_value=(Mock(),Mock(),{})):
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),1)
        current_status_record = json.loads((self.current_job_path/'status.json').read_text())
        self.assertEqual(current_status_record, {'status':'failed','error':current_error_text})

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

    def test_minimax_h3_experiment_uses_group_host_memory_guard(self):
        (self.current_job_path/'gpu-command.json').write_text(json.dumps({'command':['python','h3-worker'],'service':'minimax-h3-experiment'}))
        current_worker_mock=Mock(returncode=0)
        current_worker_mock.poll.return_value=0
        with patch.object(queue_module,'read_gpu_memory',return_value=(98304,98304)), patch.object(queue_module.subprocess,'Popen',return_value=current_worker_mock), patch.object(queue_module,'start_animate_memory_guard',return_value=(Mock(),Mock(),{})) as guard:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
            guard.assert_called_once_with(current_worker_mock,current_include_group=True,current_swap_aware=True)

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

    def test_unavailable_gpu_memory_never_launches_worker(self):
        for current_memory_values in ((OSError('GPU 조회 실패'),), ((24000, 20000), OSError('GPU 재조회 실패'))):
            with self.subTest(observations=current_memory_values):
                (self.current_job_path/'status.json').write_text('{"status":"queued"}')
                with patch.object(queue_module,'read_gpu_memory',side_effect=current_memory_values),patch.object(queue_module.subprocess,'Popen') as current_worker_mock:
                    self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),1)
                    current_worker_mock.assert_not_called()
                current_status_value=json.loads((self.current_job_path/'status.json').read_text())
                self.assertEqual(current_status_value['status'],'failed')
                self.assertIn('GPU',current_status_value['error'])
                self.assertEqual(list((queue_module.GPU_QUEUE_DIRECTORY/'active').glob('*.json')),[])

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

    def test_loading_hermes_host_reservation_protects_other_gpu_work(self):
        import os
        temporary_root_path = Path(self.temporary_job_root.name)
        resident_job_directory = temporary_root_path / '.local/hermes-agent/residents/start_existing'
        resident_job_directory.mkdir(parents=True)
        (resident_job_directory / 'request.json').write_text(json.dumps({'context':{'session_id':'a' * 32}}))
        active_reservation_directory = queue_module.GPU_QUEUE_DIRECTORY / 'active'
        active_reservation_directory.mkdir(parents=True)
        (active_reservation_directory / 'existing.json').write_text(json.dumps({'pid':os.getpid(), 'service':'hermes-agent', 'path':str(resident_job_directory), 'worker_pgid':os.getpid(), 'required_memory_mib':0}))
        observed_wait_records = []
        def stop_after_host_wait(wait_interval_seconds):
            observed_wait_records.append(json.loads((self.current_job_path / 'status.json').read_text()))
            queue_module.cancel_gpu_generation(self.current_job_path)
        host_available_memory_mib = queue_module.HOST_MEMORY_RESERVE_KIB // 1024 + queue_module.HERMES_RESIDENT_HOST_FLOOR_MIB - 1
        with patch.object(queue_module, 'WORKFLOW_ROOT_DIRECTORY', temporary_root_path), \
             patch.object(queue_module, 'read_gpu_memory_domain', return_value='vram'), \
             patch.object(queue_module, 'read_gpu_memory', return_value=(98304, 80000)), \
             patch.object(queue_module, 'read_host_available_memory', return_value=host_available_memory_mib), \
             patch.object(queue_module, 'read_worker_group_rss_kib', return_value=0), \
             patch.object(queue_module.time, 'sleep', side_effect=stop_after_host_wait), \
             patch.object(queue_module.subprocess, 'Popen') as worker_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path), 0)
            worker_launch_mock.assert_not_called()
        self.assertEqual(observed_wait_records[0]['reserved_host_memory_mib'], queue_module.HERMES_RESIDENT_HOST_FLOOR_MIB)
        self.assertEqual(observed_wait_records[0]['available_memory_mib'], 0)
        self.assertIn('시스템 메모리', observed_wait_records[0]['message'])

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

    def test_resume_fingerprint_rejects_changed_records_before_side_effects(self):
        current_request_path=self.current_job_path/'request.json'
        current_request_path.write_text('{"prompt":"original"}')
        (self.current_job_path/'status.json').write_text('{"status":"cancelled"}')
        (self.current_job_path/'cancel.request').touch()
        current_review_fingerprint=queue_module.fingerprint_resume_job_records(self.current_job_path)
        for current_changed_name,current_changed_bytes in (('request.json',b'{"prompt":"changed"}'),('status.json',b'{"status":"failed"}'),('gpu-command.json',b'{}')):
            current_changed_path=self.current_job_path/current_changed_name
            current_original_bytes=current_changed_path.read_bytes()
            current_changed_path.write_bytes(current_changed_bytes)
            with self.subTest(current_changed_name=current_changed_name),patch.object(queue_module,'launch_gpu_process') as current_launch_mock:
                with self.assertRaisesRegex(ValueError,'변경됐습니다'):
                    queue_module.resume_gpu_generation(self.current_job_path,expected_resume_fingerprint=current_review_fingerprint)
                current_launch_mock.assert_not_called()
                self.assertTrue((self.current_job_path/'cancel.request').exists())
            current_changed_path.write_bytes(current_original_bytes)
        with patch.object(queue_module,'launch_gpu_process') as current_launch_mock:
            self.assertEqual(queue_module.resume_gpu_generation(self.current_job_path,expected_resume_fingerprint=current_review_fingerprint)['status'],'queued')
            current_launch_mock.assert_called_once()

    def test_verified_resume_requires_all_records_and_rejects_symlinks(self):
        current_request_path=self.current_job_path/'request.json'
        current_request_path.write_text('{"prompt":"original"}')
        (self.current_job_path/'status.json').write_text('{"status":"failed"}')
        current_review_fingerprint=queue_module.fingerprint_resume_job_records(self.current_job_path)
        for current_record_name in ('request.json','status.json','gpu-command.json'):
            current_record_path=self.current_job_path/current_record_name
            current_original_bytes=current_record_path.read_bytes()
            current_record_path.unlink()
            with self.subTest(current_record_name=current_record_name),patch.object(queue_module,'launch_gpu_process') as current_launch_mock:
                with self.assertRaises(ValueError):queue_module.fingerprint_resume_job_records(self.current_job_path)
                with self.assertRaises(ValueError):queue_module.resume_gpu_generation(self.current_job_path,{'command':['other'],'service':'image'},current_review_fingerprint)
                current_launch_mock.assert_not_called()
            current_record_path.write_bytes(current_original_bytes)
        current_request_path.unlink()
        current_request_path.symlink_to(self.current_job_path/'status.json')
        with self.assertRaises(ValueError):queue_module.fingerprint_resume_job_records(self.current_job_path)

    def test_resume_rechecks_record_after_executor_lock(self):
        import fcntl
        current_request_path=self.current_job_path/'request.json'
        current_request_path.write_text('{"prompt":"original"}')
        (self.current_job_path/'status.json').write_text('{"status":"failed"}')
        (self.current_job_path/'cancel.request').touch()
        current_review_fingerprint=queue_module.fingerprint_resume_job_records(self.current_job_path)
        current_original_flock=fcntl.flock
        def mutate_before_execution_lock(current_lock_handle,current_lock_flags):
            if current_lock_flags & fcntl.LOCK_NB:
                current_request_path.write_text('{"prompt":"changed"}')
            return current_original_flock(current_lock_handle,current_lock_flags)
        with patch.object(queue_module.fcntl,'flock',side_effect=mutate_before_execution_lock),patch.object(queue_module,'launch_gpu_process') as current_launch_mock:
            with self.assertRaisesRegex(ValueError,'변경됐습니다'):
                queue_module.resume_gpu_generation(self.current_job_path,expected_resume_fingerprint=current_review_fingerprint)
            current_launch_mock.assert_not_called()
            self.assertTrue((self.current_job_path/'cancel.request').exists())
            self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'failed')

    def test_verified_resume_rejects_other_gpu_service(self):
        (self.current_job_path/'request.json').write_text('{}')
        (self.current_job_path/'status.json').write_text('{"status":"failed"}')
        (self.current_job_path/'cancel.request').touch()
        current_review_fingerprint=queue_module.fingerprint_resume_job_records(self.current_job_path)
        with patch.object(queue_module,'launch_gpu_process') as current_launch_mock:
            with self.assertRaisesRegex(ValueError,'서비스가'):
                queue_module.resume_gpu_generation(self.current_job_path,expected_resume_fingerprint=current_review_fingerprint,expected_resume_service='music-heartmula')
            current_launch_mock.assert_not_called()
            self.assertTrue((self.current_job_path/'cancel.request').exists())

    def test_verified_resume_rejects_unexpected_worker_command(self):
        (self.current_job_path/'request.json').write_text('{}')
        (self.current_job_path/'status.json').write_text('{"status":"failed"}')
        (self.current_job_path/'cancel.request').touch()
        current_review_fingerprint=queue_module.fingerprint_resume_job_records(self.current_job_path)
        with patch.object(queue_module,'launch_gpu_process') as current_launch_mock:
            with self.assertRaisesRegex(ValueError,'검증된 작업 명령'):
                queue_module.resume_gpu_generation(self.current_job_path,expected_resume_fingerprint=current_review_fingerprint,expected_resume_command=['different-worker'])
            current_launch_mock.assert_not_called()
            self.assertTrue((self.current_job_path/'cancel.request').exists())

    def test_resume_preview_rejects_record_changed_during_validation(self):
        current_request_path=self.current_job_path/'request.json'
        current_request_path.write_text('{"prompt":"original"}')
        (self.current_job_path/'status.json').write_text('{"status":"failed"}')
        current_command_record=json.loads((self.current_job_path/'gpu-command.json').read_text())
        def mutate_during_validation(current_request_record):
            current_request_path.write_text('{"prompt":"changed"}')
        with patch.object(queue_module,'launch_gpu_process') as current_launch_mock:
            with self.assertRaisesRegex(ValueError,'검토 중'):
                queue_module.preview_gpu_resume_records(self.current_job_path,current_command_record['service'],current_command_record['command'],mutate_during_validation)
            current_launch_mock.assert_not_called()

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

    def test_resume_locked_preflight_rejection_preserves_records(self):
        import fcntl
        current_status_record={'status':'failed','error':'old error'}
        (self.current_job_path/'status.json').write_text(json.dumps(current_status_record))
        (self.current_job_path/'cancel.request').write_text('original')
        def reject_reviewed_preflight(current_job_directory):
            with (current_job_directory/'execution.lock').open('a') as current_other_lock:
                with self.assertRaises(BlockingIOError):fcntl.flock(current_other_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            raise ValueError('검토 지문이 변경됐습니다')
        with patch.object(queue_module,'launch_gpu_process') as current_launch_mock:
            with self.assertRaisesRegex(ValueError,'검토 지문'):
                queue_module.resume_gpu_generation(self.current_job_path,resume_locked_preflight_callback=reject_reviewed_preflight)
            current_launch_mock.assert_not_called()
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text()),current_status_record)
        self.assertEqual((self.current_job_path/'cancel.request').read_text(),'original')
        with self.assertRaises(ValueError):queue_module.resume_gpu_generation(self.current_job_path,resume_locked_preflight_callback='invalid')

    def test_resume_rejects_unsafe_command_after_locked_preflight(self):
        import os
        current_command_path = self.current_job_path / 'gpu-command.json'
        for current_unsafe_kind in ('symlink', 'fifo', 'oversized'):
            with self.subTest(kind=current_unsafe_kind):
                (self.current_job_path / 'status.json').write_text(json.dumps({'status': 'failed'}))
                current_command_path.unlink(missing_ok=True)
                current_command_path.write_text(json.dumps({'command': ['worker'], 'service': 'image'}))
                def replace_reviewed_command(current_job_directory):
                    current_command_path.unlink()
                    if current_unsafe_kind == 'symlink':
                        current_command_path.symlink_to(current_job_directory / 'status.json')
                    elif current_unsafe_kind == 'fifo':
                        os.mkfifo(current_command_path)
                    else:
                        with current_command_path.open('wb') as current_command_stream:
                            current_command_stream.truncate(1024 * 1024 + 1)
                with patch.object(queue_module, 'launch_gpu_process') as current_launch_mock:
                    with self.assertRaises(ValueError):
                        queue_module.resume_gpu_generation(self.current_job_path, resume_locked_preflight_callback=replace_reviewed_command)
                    current_launch_mock.assert_not_called()
                self.assertEqual(json.loads((self.current_job_path / 'status.json').read_text())['status'], 'failed')

    def test_resume_log_open_failure_preserves_terminal_status(self):
        current_status_record={'status':'failed','error':'original failure'}
        (self.current_job_path/'status.json').write_text(json.dumps(current_status_record))
        (self.current_job_path/'worker.log').mkdir()
        for current_marker_name in ('cancel.request','pause.request','stage-pause.json'):
            (self.current_job_path/current_marker_name).write_text('unchanged')
        with patch.object(queue_module,'launch_gpu_process') as current_launch_mock:
            with self.assertRaises(OSError):queue_module.resume_gpu_generation(self.current_job_path)
            current_launch_mock.assert_not_called()
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text()),current_status_record)
        for current_marker_name in ('cancel.request','pause.request','stage-pause.json'):
            self.assertEqual((self.current_job_path/current_marker_name).read_text(),'unchanged')

    def test_resume_rejects_log_symlink_and_fifo_without_mutation(self):
        import os
        current_status_record={'status':'failed','error':'original failure'}
        (self.current_job_path/'status.json').write_text(json.dumps(current_status_record))
        current_log_path=self.current_job_path/'worker.log'
        current_marker_path=self.current_job_path/'cancel.request'
        current_marker_path.write_text('unchanged')
        current_external_path=Path(self.temporary_job_root.name)/'external.log'
        current_external_path.write_text('untouched')
        for current_log_kind in ('symlink','fifo'):
            with self.subTest(kind=current_log_kind):
                if current_log_kind=='symlink':current_log_path.symlink_to(current_external_path)
                else:os.mkfifo(current_log_path)
                with patch.object(queue_module,'launch_gpu_process') as current_launch_mock:
                    with self.assertRaises((OSError,ValueError)):queue_module.resume_gpu_generation(self.current_job_path)
                    current_launch_mock.assert_not_called()
                self.assertEqual(json.loads((self.current_job_path/'status.json').read_text()),current_status_record)
                self.assertEqual(current_marker_path.read_text(),'unchanged')
                self.assertEqual(current_external_path.read_text(),'untouched')
                current_log_path.unlink()

    def test_resume_prelaunch_error_does_not_leave_queued_status(self):
        (self.current_job_path/'status.json').write_text('{"status":"failed"}')
        with patch.object(queue_module,'launch_gpu_process',side_effect=OSError('command record write failed')) as current_launch_mock:
            with self.assertRaisesRegex(OSError,'command record write failed'):
                queue_module.resume_gpu_generation(self.current_job_path)
        current_launch_mock.assert_called_once()
        current_status_record=json.loads((self.current_job_path/'status.json').read_text())
        self.assertEqual(current_status_record['status'],'failed')
        self.assertIn('command record write failed',current_status_record['error'])

    def test_resume_command_record_write_failure_never_spawns(self):
        (self.current_job_path/'status.json').write_text('{"status":"failed"}')
        current_original_write=queue_module.write_record_atomically
        def reject_command_write(current_record_path,current_record_value):
            if Path(current_record_path).name=='gpu-command.json':raise OSError('command write failed')
            return current_original_write(current_record_path,current_record_value)
        with patch.object(queue_module,'write_record_atomically',side_effect=reject_command_write),patch.object(queue_module.subprocess,'Popen') as current_spawn_mock:
            with self.assertRaisesRegex(OSError,'command write failed'):
                queue_module.resume_gpu_generation(self.current_job_path)
            current_spawn_mock.assert_not_called()
        self.assertEqual(json.loads((self.current_job_path/'status.json').read_text())['status'],'failed')

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

    def test_pause_is_honored_while_waiting_to_publish_ticket(self):
        import fcntl
        queue_module.GPU_QUEUE_DIRECTORY.mkdir()
        with (queue_module.GPU_QUEUE_DIRECTORY / 'execution.lock').open('a') as occupied_lock_handle:
            fcntl.flock(occupied_lock_handle, fcntl.LOCK_EX)
            def request_pause_while_waiting(wait_interval_seconds):
                (self.current_job_path / 'pause.request').touch()
            with patch.object(queue_module.time, 'sleep', side_effect=request_pause_while_waiting), \
                 patch.object(queue_module.subprocess, 'Popen') as worker_launch_mock:
                self.assertEqual(queue_module.execute_queued_generation(self.current_job_path), 0)
                worker_launch_mock.assert_not_called()
        self.assertEqual(json.loads((self.current_job_path / 'status.json').read_text())['status'], 'paused')
        self.assertFalse(list(queue_module.GPU_QUEUE_DIRECTORY.glob('*.json')))

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

    def test_new_and_reloaded_tickets_keep_executor_start_identity(self):
        import os
        current_expected_start=Path(f'/proc/{os.getpid()}/stat').read_text().rpartition(') ')[2].split()[19]
        current_original_write=queue_module.write_record_atomically
        def cancel_after_ticket(current_path,current_record):
            current_original_write(current_path,current_record)
            if isinstance(current_record,dict) and 'pid' in current_record and 'path' in current_record:
                (self.current_job_path/'cancel.request').touch()
        with patch.object(queue_module,'write_record_atomically',side_effect=cancel_after_ticket) as current_write_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
        current_ticket_records=[current_call.args[1] for current_call in current_write_mock.call_args_list if isinstance(current_call.args[1],dict) and 'pid' in current_call.args[1] and 'path' in current_call.args[1]]
        self.assertEqual(len(current_ticket_records),1)
        self.assertEqual(current_ticket_records[0]['pid_start_token'],current_expected_start)
        self.assertEqual(current_ticket_records[0]['boot_id'],Path('/proc/sys/kernel/random/boot_id').read_text().strip())
        current_queue=queue_module.GPU_QUEUE_DIRECTORY
        for current_with_token in (False,True):
            current_ticket=current_queue/'inherited.json'
            current_record={'pid':os.getpid(),'path':str(self.current_job_path)}
            if current_with_token:current_record['pid_start_token']=current_expected_start
            current_ticket.write_text(json.dumps(current_record))
            with patch.dict(os.environ,{'SLIME_GPU_QUEUE_TICKET':str(current_ticket)}):
                self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)

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
        for current_file_name in ('gpu_job_queue.py','gpu_memory_history.py','host_memory_guard.py','gpu_chat_admission.py'):
            (current_source_root/current_file_name).write_text('initial')
        with patch.object(queue_module,'__file__',str(current_source_root/'gpu_job_queue.py')):
            current_initial_revision=queue_module.calculate_queue_revision()
            (current_source_root/'host_memory_guard.py').write_text('updated host reserve')
            self.assertNotEqual(queue_module.calculate_queue_revision(),current_initial_revision)
            current_after_guard_revision=queue_module.calculate_queue_revision()
            (current_source_root/'gpu_memory_history.py').write_text('updated estimate')
            self.assertNotEqual(queue_module.calculate_queue_revision(),current_after_guard_revision)
            current_after_estimate_revision=queue_module.calculate_queue_revision()
            (current_source_root/'gpu_chat_admission.py').write_text('updated chat admission')
            self.assertNotEqual(queue_module.calculate_queue_revision(),current_after_estimate_revision)

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
        current_launcher_code="import os,sys; from pathlib import Path; from workflow.common import gpu_job_queue as q; q.__file__=sys.argv[1]; q.calculate_queue_revision=lambda:'new'; sys.argv=[sys.argv[1],'--job-dir',sys.argv[3]]; print('original-pid='+str(os.getpid()),flush=True); q.reload_waiting_executor(Path(os.environ['TEST_QUEUE_TICKET']),'old')"
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
        from workflow.common import gpu_memory_history
        gpu_memory_history.save_memory_observation('image','previous',7538,3,'completed',command_identity_name='run_qwen_21_reference.py:1280x1280:steps=4:references=0:offload=none-full-v1')
        (self.current_job_path/'request.json').write_text(json.dumps({'width':1280,'height':1280,'steps':4}))
        (self.current_job_path/'gpu-command.json').write_text(json.dumps({'command':['python','run_qwen_21_reference.py'],'service':'image'}))
        worker_process_mock = Mock(returncode=0)
        worker_process_mock.poll.return_value = 0
        with patch.object(queue_module,'read_gpu_memory',return_value=(8151,7599)),patch.object(queue_module.subprocess,'Popen',return_value=worker_process_mock) as worker_launch_mock:
            self.assertEqual(queue_module.execute_queued_generation(self.current_job_path),0)
            worker_launch_mock.assert_called_once()

    def test_observed_peak_blocks_insufficient_free_memory(self):
        from workflow.common import gpu_memory_history
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
