"""실제 작업을 건드리지 않는 공용 대기열 우선 실행 검사."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.review.common import gpu_job_queue
from tools.review.common.management_gateway import resolve_management_command


class QueuePriorityContractTests(unittest.TestCase):
    def test_wan_fun_prepare_priority_preview_requires_verified_owner(self):
        from tools.review.domains.hermes_agent.priority_observer import preview_hermes_queue_priority
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_workflow_root=Path(current_temporary_directory)
            current_queue_root=current_workflow_root/'.tmp'/'gpu-queue'
            current_queue_root.mkdir(parents=True)
            current_job_directory=current_workflow_root/'.tmp'/'test'/'wan22-fun-control'/'2026-11-20_20-02-00-abcdef12'
            current_job_directory.mkdir(parents=True)
            (current_job_directory/'status.json').write_text(json.dumps({'status':'queued'}))
            (current_job_directory/'gpu-command.json').write_text(json.dumps({'service':'wan-fun-prepare'}))
            (current_queue_root/'ticket.json').write_text(json.dumps({'pid':os.getpid(),'path':str(current_job_directory)}))
            with patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_workflow_root),patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_root):
                current_queue_jobs=gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)['jobs']
                self.assertEqual(current_queue_jobs[0]['source_service'],'wan22-fun-control')
                current_snapshot_record={'queue':{'status':'available','jobs':current_queue_jobs}}
                with patch('tools.review.domains.hermes_agent.management_observer.read_hermes_management_snapshot',return_value=current_snapshot_record):
                    self.assertEqual(preview_hermes_queue_priority('wan22-fun-control',current_job_directory.name)['job_id'],current_job_directory.name)
                    current_queue_jobs[0].pop('source_service')
                    with self.assertRaises(ValueError):preview_hermes_queue_priority('wan22-fun-control',current_job_directory.name)
                self.assertFalse((current_queue_root/'priority-order').exists())
        with self.assertRaises(ValueError):resolve_management_command('wan22-fun-control','prioritize',{'id':'2026-11-20_20-02-00-prepare'})

    def test_priority_order_and_running_rejection(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_queue_directory = Path(current_temp_directory) / 'queue'
            current_queue_directory.mkdir()
            for current_job_index in range(3):
                current_job_directory = Path(current_temp_directory) / f'job-{current_job_index}'
                current_job_directory.mkdir()
                (current_job_directory / 'status.json').write_text(json.dumps({'status':'queued'}))
                (current_queue_directory / f'{current_job_index}.json').write_text(json.dumps({'pid':os.getpid(),'path':str(current_job_directory)}))
            with patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', current_queue_directory):
                gpu_job_queue.prioritize_waiting_generation('job-2')
                self.assertEqual([current_ticket_path.name for current_ticket_path in gpu_job_queue.read_priority_tickets()], ['2.json','0.json','1.json'])
                gpu_job_queue.prioritize_waiting_generation('job-1')
                self.assertEqual([current_ticket_path.name for current_ticket_path in gpu_job_queue.read_priority_tickets()], ['1.json','2.json','0.json'])
                (Path(current_temp_directory)/'job-0/status.json').write_text(json.dumps({'status':'running'}))
                with self.assertRaises(ValueError):
                    gpu_job_queue.prioritize_waiting_generation('job-0')

    def test_priority_rejects_other_service_and_unverified_shared_source(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_root=Path(current_temp_directory)
            current_queue_directory=current_root/'.tmp/gpu-queue'
            current_queue_directory.mkdir(parents=True)
            current_job_directory=current_root/'.tmp/test/kimodo/job-1'
            current_job_directory.mkdir(parents=True)
            (current_job_directory/'status.json').write_text(json.dumps({'status':'queued'}))
            (current_job_directory/'gpu-command.json').write_text(json.dumps({'service':'image'}))
            (current_queue_directory/'one.json').write_text(json.dumps({'pid':os.getpid(),'path':str(current_job_directory)}))
            with patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root),patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_directory):
                with self.assertRaises(ValueError):gpu_job_queue.prioritize_waiting_generation('job-1','wan22-vace')
                self.assertFalse((current_queue_directory/'priority-order').exists())
                self.assertEqual(gpu_job_queue.prioritize_waiting_generation('job-1','kimodo')['queue_position'],1)
                current_before=(current_queue_directory/'priority-order').read_text()
                current_bad_directory=current_root/'.tmp/test/other/job-2'
                current_bad_directory.mkdir(parents=True)
                (current_bad_directory/'status.json').write_text(json.dumps({'status':'queued'}))
                (current_bad_directory/'gpu-command.json').write_text(json.dumps({'service':'image'}))
                (current_queue_directory/'two.json').write_text(json.dumps({'pid':os.getpid(),'path':str(current_bad_directory)}))
                with self.assertRaises(ValueError):gpu_job_queue.prioritize_waiting_generation('job-2','kimodo')
                self.assertEqual((current_queue_directory/'priority-order').read_text(),current_before)

    def test_dedicated_priority_requires_registered_job_root(self):
        from tools.review.domains.hermes_agent.priority_observer import preview_hermes_queue_priority
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_queue_root=current_root_path/'.tmp/gpu-queue'
            current_queue_root.mkdir(parents=True)
            current_job_root=current_root_path/'.tmp/test/music-heartmula/2026-11-18_12-00-00-12345678'
            current_job_root.mkdir(parents=True)
            (current_job_root/'status.json').write_text(json.dumps({'status':'queued'}))
            (current_job_root/'gpu-command.json').write_text(json.dumps({'service':'music-heartmula'}))
            current_ticket_path=current_queue_root/'ticket.json'
            current_ticket_path.write_text(json.dumps({'pid':os.getpid(),'path':str(current_job_root)}))
            with patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root_path),patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_root):
                current_jobs=gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)['jobs']
                self.assertEqual(current_jobs[0]['source_service'],'music-heartmula')
                current_snapshot={'queue':{'status':'available','jobs':current_jobs}}
                with patch('tools.review.domains.hermes_agent.management_observer.read_hermes_management_snapshot',return_value=current_snapshot):
                    self.assertEqual(preview_hermes_queue_priority('music-heartmula',current_job_root.name)['job_id'],current_job_root.name)
                    current_jobs[0].pop('source_service')
                    with self.assertRaises(ValueError):preview_hermes_queue_priority('music-heartmula',current_job_root.name)
                current_wrong_root=current_root_path/'.tmp/test/other/job-2'
                current_wrong_root.mkdir(parents=True)
                (current_wrong_root/'status.json').write_text(json.dumps({'status':'queued'}))
                (current_wrong_root/'gpu-command.json').write_text(json.dumps({'service':'music-heartmula'}))
                (current_queue_root/'wrong.json').write_text(json.dumps({'pid':os.getpid(),'path':str(current_wrong_root)}))
                with self.assertRaises(ValueError):gpu_job_queue.prioritize_waiting_generation('job-2','music-heartmula')
                self.assertFalse((current_queue_root/'priority-order').exists())

    def test_gateway_priority_binds_requested_service(self):
        from tools.review.common.management_gateway import execute_management_command
        current_job_identifier='2026-10-09_21-13-20-1a356bbd'
        with patch.object(gpu_job_queue,'prioritize_waiting_generation',return_value={'id':current_job_identifier}) as current_priority_mock,patch('tools.review.common.management_transport.send_management_json_response'):
            execute_management_command('kimodo','prioritize',{'id':current_job_identifier},gateway_request_handler=object(),service_handler_values={})
        current_priority_mock.assert_called_once_with(current_job_identifier,'kimodo')

    def test_hermes_priority_preview_requires_unique_verified_owner(self):
        from tools.review.domains.hermes_agent.priority_observer import preview_hermes_queue_priority
        current_job_identifier='2026-10-09_21-13-20-1a356bbd'
        current_ticket={'id':current_job_identifier,'service':'image','source_service':'kimodo','ticket_revision':'a'*64}
        current_snapshot={'queried_at':'mock','queue':{'status':'available','jobs':[current_ticket]}}
        with patch('tools.review.domains.hermes_agent.management_observer.read_hermes_management_snapshot',return_value=current_snapshot),patch.object(gpu_job_queue,'prioritize_waiting_generation') as current_priority_mock:
            current_result=preview_hermes_queue_priority('kimodo',current_job_identifier)
            self.assertEqual(current_result['queue_position'],1)
            current_ticket.pop('source_service')
            with self.assertRaises(ValueError):preview_hermes_queue_priority('kimodo',current_job_identifier)
            current_ticket['source_service']='wan22-vace'
            with self.assertRaises(ValueError):preview_hermes_queue_priority('kimodo',current_job_identifier)
            current_ticket['source_service']='kimodo'
            current_snapshot['queue']['jobs'].append(current_ticket.copy())
            with self.assertRaises(ValueError):preview_hermes_queue_priority('kimodo',current_job_identifier)
            current_snapshot['queue']['status']='unavailable'
            with self.assertRaises(ValueError):preview_hermes_queue_priority('kimodo',current_job_identifier)
            current_priority_mock.assert_not_called()

    def test_hermes_retired_services_cannot_preview_or_reorder_queue(self):
        from tools.review.domains.hermes_agent import priority_observer, priority_operations
        from tools.review.domains.hermes_agent.capabilities import list_management_service_registration
        current_job = '2026-10-09_21-13-20-1a356bbd'
        current_records = {item['service']:item for item in list_management_service_registration()['services']}
        with tempfile.TemporaryDirectory() as current_temp, patch.object(priority_operations,'PRIORITY_RECEIPT_ROOT',Path(current_temp)), patch('tools.review.domains.hermes_agent.management_observer.read_hermes_management_snapshot') as current_snapshot, patch.object(gpu_job_queue,'prioritize_waiting_generation') as current_priority:
            for current_service in ('character-animation','music-minimax','music-magenta'):
                with self.subTest(service=current_service):
                    current_record = current_records[current_service]
                    self.assertNotIn('hermes-priority-submit',current_record['hermes_links'])
                    self.assertTrue(any(item['command']=='prioritize' for item in current_record['conditional_limitations']))
                    with self.assertRaisesRegex(ValueError,'폐기'):
                        priority_observer.preview_hermes_queue_priority(current_service,current_job)
                    with self.assertRaisesRegex(ValueError,'폐기'):
                        priority_operations.submit_hermes_priority_once('request_123',current_service,current_job,'a'*64)
            current_snapshot.assert_not_called()
            current_priority.assert_not_called()
            self.assertFalse(list(Path(current_temp).glob('*.json')))
        self.assertIn('hermes-priority-submit',current_records['kimodo']['hermes_links'])

    def test_priority_rejects_replaced_ticket_without_changing_order(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_root=Path(current_temp_directory)
            current_queue_directory=current_root/'.tmp/gpu-queue'
            current_queue_directory.mkdir(parents=True)
            current_job_directory=current_root/'.tmp/test/kimodo/job-1'
            current_job_directory.mkdir(parents=True)
            (current_job_directory/'status.json').write_text(json.dumps({'status':'queued'}))
            (current_job_directory/'gpu-command.json').write_text(json.dumps({'service':'image'}))
            current_ticket=current_queue_directory/'ticket.json'
            current_ticket.write_text(json.dumps({'pid':os.getpid(),'path':str(current_job_directory)}))
            current_revision=gpu_job_queue.fingerprint_gpu_queue_ticket(current_ticket)
            current_ticket.write_text(json.dumps({'pid':os.getpid(),'path':str(current_job_directory),'changed':True}))
            with patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root),patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_directory):
                with self.assertRaises(ValueError):gpu_job_queue.prioritize_waiting_generation('job-1','kimodo',current_revision)
                self.assertFalse((current_queue_directory/'priority-order').exists())
                current_revision=gpu_job_queue.fingerprint_gpu_queue_ticket(current_ticket)
                self.assertEqual(gpu_job_queue.prioritize_waiting_generation('job-1','kimodo',current_revision)['queue_position'],1)

    def test_queue_snapshot_rejects_ticket_changed_during_read(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_root=Path(current_temp_directory)
            current_job=current_root/'.tmp/test/kimodo/job-1'
            current_job.mkdir(parents=True)
            (current_job/'status.json').write_text(json.dumps({'status':'queued'}))
            (current_job/'gpu-command.json').write_text(json.dumps({'service':'image'}))
            current_ticket=current_root/'ticket.json'
            current_ticket.write_text(json.dumps({'pid':os.getpid(),'path':str(current_job)}))
            with patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root),patch.object(gpu_job_queue,'read_priority_tickets',return_value=[current_ticket]),patch.object(gpu_job_queue,'fingerprint_gpu_queue_ticket',side_effect=['a'*64,'b'*64]):
                with self.assertRaises(ValueError):gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)

    def test_ticket_start_identity_checks_pid_reuse_and_keeps_legacy(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_root=Path(current_temp_directory)
            current_queue=current_root/'.tmp/gpu-queue'
            current_queue.mkdir(parents=True)
            current_job=current_root/'.tmp/test/kimodo/job-1'
            current_job.mkdir(parents=True)
            (current_job/'status.json').write_text(json.dumps({'status':'queued'}))
            (current_job/'gpu-command.json').write_text(json.dumps({'service':'image'}))
            current_ticket=current_queue/'ticket.json'
            current_start=Path(f'/proc/{os.getpid()}/stat').read_text().rpartition(') ')[2].split()[19]
            current_record={'pid':os.getpid(),'path':str(current_job),'pid_start_token':current_start,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
            current_ticket.write_text(json.dumps(current_record))
            with patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root),patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue):
                current_observed=gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)['jobs'][0]
                self.assertEqual(current_observed['executor_identity'],'verified')
                self.assertNotIn('pid_start_token',current_observed)
                self.assertNotIn('boot_id',current_observed)
                current_original_boot=current_record['boot_id']
                current_record['boot_id']='00000000-0000-0000-0000-000000000000'
                current_ticket.write_text(json.dumps(current_record))
                with self.assertRaisesRegex(ValueError,'부팅 신원'):gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)
                self.assertIsNone(gpu_job_queue.select_runnable_ticket(999999,'vram'))
                current_record['boot_id']=current_original_boot
                current_ticket.write_text(json.dumps(current_record))
                current_revision=gpu_job_queue.fingerprint_gpu_queue_ticket(current_ticket)
                current_record['pid_start_token']=str(int(current_start)+1)
                current_ticket.write_text(json.dumps(current_record))
                with self.assertRaisesRegex(ValueError,'신원'):gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)
                self.assertIsNone(gpu_job_queue.select_runnable_ticket(999999,'vram'))
                with self.assertRaisesRegex(ValueError,'신원'):gpu_job_queue.prioritize_waiting_generation('job-1','kimodo',gpu_job_queue.fingerprint_gpu_queue_ticket(current_ticket))
                self.assertFalse((current_queue/'priority-order').exists())
                for current_bad_field,current_bad_value in (('pid_start_token',None),('boot_id',None),('pid_start_token',True)):
                    current_bad_record={'pid':os.getpid(),'path':str(current_job),'pid_start_token':current_start,'boot_id':current_original_boot}
                    current_bad_record[current_bad_field]=current_bad_value
                    current_ticket.write_text(json.dumps(current_bad_record))
                    with self.assertRaisesRegex(ValueError,'식별 정보'):gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)
                    self.assertIsNone(gpu_job_queue.select_runnable_ticket(999999,'vram'))
                    with self.assertRaisesRegex(ValueError,'식별 정보'):gpu_job_queue.prioritize_waiting_generation('job-1','kimodo',gpu_job_queue.fingerprint_gpu_queue_ticket(current_ticket))
                self.assertFalse((current_queue/'priority-order').exists())
                current_record['pid_start_token']=current_start
                current_record.pop('boot_id')
                current_ticket.write_text(json.dumps(current_record))
                self.assertEqual(gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)['jobs'][0]['executor_identity'],'unverified')
                current_record.pop('pid_start_token')
                current_ticket.write_text(json.dumps(current_record))
                self.assertEqual(gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)['jobs'][0]['executor_identity'],'unverified')
                self.assertEqual(gpu_job_queue.prioritize_waiting_generation('job-1','kimodo',gpu_job_queue.fingerprint_gpu_queue_ticket(current_ticket))['queue_position'],1)

    def test_invalid_ticket_pid_never_queries_or_reorders_processes(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_root=Path(current_temp_directory)
            current_queue=current_root/'.tmp/gpu-queue'
            current_queue.mkdir(parents=True)
            current_job=current_root/'.tmp/test/kimodo/job-1'
            current_job.mkdir(parents=True)
            (current_job/'status.json').write_text(json.dumps({'status':'queued'}))
            (current_job/'gpu-command.json').write_text(json.dumps({'service':'image'}))
            current_ticket=current_queue/'ticket.json'
            with patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root),patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue),patch.object(gpu_job_queue.os,'kill') as current_kill_mock:
                for current_bad_pid in (0,-1,True,'12',None,10**100):
                    current_ticket.write_text(json.dumps({'pid':current_bad_pid,'path':str(current_job)}))
                    with self.assertRaisesRegex(ValueError,'PID'):gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)
                    self.assertIsNone(gpu_job_queue.select_runnable_ticket(999999,'vram'))
                    with self.assertRaisesRegex(ValueError,'PID'):gpu_job_queue.prioritize_waiting_generation('job-1','kimodo',gpu_job_queue.fingerprint_gpu_queue_ticket(current_ticket))
                current_kill_mock.assert_not_called()
                self.assertFalse((current_queue/'priority-order').exists())

    def test_missing_live_ticket_job_files_are_not_reported_as_empty_queue(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_root=Path(current_temp_directory)
            current_job=current_root/'.tmp/test/kimodo/job-1'
            current_job.mkdir(parents=True)
            current_ticket=current_root/'ticket.json'
            current_ticket.write_text(json.dumps({'pid':os.getpid(),'path':str(current_job)}))
            with patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root),patch.object(gpu_job_queue,'read_priority_tickets',return_value=[current_ticket]):
                self.assertEqual(gpu_job_queue.list_waiting_gpu_jobs(),{'jobs':[]})
                with self.assertRaisesRegex(ValueError,'작업 기록'):
                    gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)
                (current_job/'status.json').write_text(json.dumps({'status':'queued'}))
                with self.assertRaisesRegex(ValueError,'작업 기록'):
                    gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)
                (current_job/'gpu-command.json').write_text(json.dumps({'service':'image'}))
                self.assertEqual(gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)['jobs'][0]['id'],'job-1')
                for current_bad_status in ('unknown','unexpected',None):
                    (current_job/'status.json').write_text(json.dumps({'status':current_bad_status}))
                    self.assertEqual(gpu_job_queue.list_waiting_gpu_jobs(),{'jobs':[]})
                    with self.assertRaisesRegex(ValueError,'상태'):
                        gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)
                (current_job/'status.json').write_text(json.dumps({'status':'running'}))
                self.assertEqual(gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True),{'jobs':[]})

    def test_stale_ticket_receipt_never_reorders_or_retries(self):
        from tools.review.domains.hermes_agent import priority_operations
        current_job='2026-10-09_21-13-20-1a356bbd'
        with tempfile.TemporaryDirectory() as current_temp:
            current_root=Path(current_temp)
            current_queue=current_root/'queue'
            current_queue.mkdir()
            current_job_directory=current_root/'generators/kimodo/outputs'/current_job
            current_job_directory.mkdir(parents=True)
            (current_job_directory/'status.json').write_text(json.dumps({'status':'queued'}))
            (current_job_directory/'gpu-command.json').write_text(json.dumps({'service':'image'}))
            current_ticket=current_queue/'ticket.json'
            current_ticket.write_text(json.dumps({'pid':os.getpid(),'path':str(current_job_directory)}))
            current_revision=gpu_job_queue.fingerprint_gpu_queue_ticket(current_ticket)
            current_ticket.write_text(json.dumps({'pid':os.getpid(),'path':str(current_job_directory),'changed':True}))
            with patch.object(priority_operations,'PRIORITY_RECEIPT_ROOT',current_root/'receipts'),patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root),patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue):
                with self.assertRaises(ValueError):priority_operations.submit_hermes_priority_once('request_stale','kimodo',current_job,current_revision)
                self.assertEqual(priority_operations.read_hermes_priority_receipt('request_stale')['state'],'unknown')
                self.assertFalse((current_queue/'priority-order').exists())
                current_repeat=priority_operations.submit_hermes_priority_once('request_stale','kimodo',current_job,current_revision)
                self.assertTrue(current_repeat['duplicate'])
                self.assertEqual(current_repeat['state'],'unknown')
                self.assertFalse((current_queue/'priority-order').exists())

    def test_malformed_priority_receipt_and_boolean_queue_position_fail_closed(self):
        from tools.review.domains.hermes_agent import priority_operations
        current_job='2026-10-09_21-13-20-1a356bbd'
        current_record={'version':True,'id':'request_bool','service':'kimodo','job_id':current_job,'ticket_revision':'a'*64,'state':'completed'}
        with self.assertRaises(ValueError):priority_operations.inspect_hermes_priority_receipt(current_record,'request_bool')
        with tempfile.TemporaryDirectory() as current_temp,patch.object(priority_operations,'PRIORITY_RECEIPT_ROOT',Path(current_temp)),patch.object(gpu_job_queue,'prioritize_waiting_generation',return_value={'id':current_job,'status':'queued','queue_position':True}) as current_mock:
            with self.assertRaises(ValueError):priority_operations.submit_hermes_priority_once('request_bool','kimodo',current_job,'a'*64)
            self.assertEqual(priority_operations.read_hermes_priority_receipt('request_bool')['state'],'unknown')
            self.assertTrue(priority_operations.submit_hermes_priority_once('request_bool','kimodo',current_job,'a'*64)['duplicate'])
            current_mock.assert_called_once()

    def test_hermes_priority_receipt_is_idempotent_and_recovers_unknown(self):
        from concurrent.futures import ThreadPoolExecutor
        from tools.review.domains.hermes_agent import priority_operations
        current_job='2026-10-09_21-13-20-1a356bbd'
        current_revision='a'*64
        current_response={'id':current_job,'status':'queued','queue_position':1}
        with tempfile.TemporaryDirectory() as current_temp,patch.object(priority_operations,'PRIORITY_RECEIPT_ROOT',Path(current_temp)),patch.object(gpu_job_queue,'prioritize_waiting_generation',return_value=current_response) as current_priority_mock:
            with ThreadPoolExecutor(max_workers=4) as current_executor:
                current_results=list(current_executor.map(lambda _:priority_operations.submit_hermes_priority_once('request_123','kimodo',current_job,current_revision),range(4)))
            self.assertEqual(sum(not item['duplicate'] for item in current_results),1)
            current_priority_mock.assert_called_once_with(current_job,'kimodo',current_revision)
            self.assertEqual(priority_operations.read_hermes_priority_receipt('request_123')['state'],'completed')
            with self.assertRaises(ValueError):priority_operations.submit_hermes_priority_once('request_123','kimodo',current_job,'b'*64)
            self.assertEqual(current_priority_mock.call_count,1)
        with tempfile.TemporaryDirectory() as current_temp,patch.object(priority_operations,'PRIORITY_RECEIPT_ROOT',Path(current_temp)),patch.object(gpu_job_queue,'prioritize_waiting_generation',side_effect=OSError('response lost')) as current_priority_mock:
            with self.assertRaises(OSError):priority_operations.submit_hermes_priority_once('request_456','kimodo',current_job,current_revision)
            self.assertEqual(priority_operations.read_hermes_priority_receipt('request_456')['state'],'unknown')
            self.assertTrue(priority_operations.submit_hermes_priority_once('request_456','kimodo',current_job,current_revision)['duplicate'])
            current_priority_mock.assert_called_once()

    def test_hermes_priority_preserves_changed_receipt(self):
        from tools.review.domains.hermes_agent import priority_operations
        current_job_identifier='2026-10-09_21-13-20-1a356bbd'
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_receipt_path=Path(current_directory_name)/'priority_changed_123.json'
            def change_current_receipt(current_job_value,current_service_value,current_revision_value):
                current_record_value=json.loads(current_receipt_path.read_text())
                current_record_value['external_change']='preserve'
                current_receipt_path.write_text(json.dumps(current_record_value))
                return {'id':current_job_value,'status':'queued','queue_position':1}
            with patch.object(priority_operations,'PRIORITY_RECEIPT_ROOT',Path(current_directory_name)),patch.object(gpu_job_queue,'prioritize_waiting_generation',side_effect=change_current_receipt) as current_priority_mock:
                with self.assertRaisesRegex(ValueError,'접수 기록이 변경'):
                    priority_operations.submit_hermes_priority_once('priority_changed_123','kimodo',current_job_identifier,'a'*64)
                self.assertEqual(json.loads(current_receipt_path.read_text())['external_change'],'preserve')
                self.assertEqual(json.loads(current_receipt_path.read_text())['state'],'dispatching')
                current_priority_mock.assert_called_once()

    def test_hermes_priority_different_id_does_not_repeat_unknown(self):
        from tools.review.domains.hermes_agent import priority_operations
        current_job_identifier='2026-10-09_21-13-20-1a356bbd'
        with tempfile.TemporaryDirectory() as current_directory_name,patch.object(priority_operations,'PRIORITY_RECEIPT_ROOT',Path(current_directory_name)),patch.object(gpu_job_queue,'prioritize_waiting_generation',side_effect=OSError('response lost')) as current_priority_mock:
            with self.assertRaises(OSError):priority_operations.submit_hermes_priority_once('priority_original_123','kimodo',current_job_identifier,'a'*64)
            with self.assertRaisesRegex(ValueError,'기존 우선 실행 접수'):
                priority_operations.submit_hermes_priority_once('priority_different_123','kimodo',current_job_identifier,'a'*64)
            self.assertEqual(priority_operations.read_hermes_priority_receipt('priority_original_123')['state'],'unknown')
            current_priority_mock.assert_called_once()

    def test_hermes_priority_different_ids_race_once(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        from tools.review.domains.hermes_agent import priority_operations
        current_job_identifier='2026-10-09_21-13-20-1a356bbd'
        current_start_barrier=threading.Barrier(3)
        with tempfile.TemporaryDirectory() as current_directory_name,patch.object(priority_operations,'PRIORITY_RECEIPT_ROOT',Path(current_directory_name)),patch.object(gpu_job_queue,'prioritize_waiting_generation',return_value={'id':current_job_identifier,'status':'queued','queue_position':1}) as current_priority_mock:
            def submit_racing_priority(current_index_value):
                current_start_barrier.wait(timeout=5)
                try:
                    return priority_operations.submit_hermes_priority_once(f'priority_race_{current_index_value:03d}','kimodo',current_job_identifier,'a'*64)['state']
                except ValueError as current_error_value:
                    return str(current_error_value)
            with ThreadPoolExecutor(max_workers=3) as current_executor_value:
                current_result_values=list(current_executor_value.map(submit_racing_priority,range(3)))
            self.assertEqual(current_result_values.count('completed'),1)
            self.assertEqual(sum('기존 우선 실행 접수' in current_result_value for current_result_value in current_result_values),2)
            current_priority_mock.assert_called_once()

    def test_hermes_priority_corrupt_receipt_blocks_dispatch(self):
        from tools.review.domains.hermes_agent import priority_operations
        current_job_identifier='2026-10-09_21-13-20-1a356bbd'
        with tempfile.TemporaryDirectory() as current_directory_name:
            (Path(current_directory_name)/'priority_corrupt_123.json').write_text('{')
            with patch.object(priority_operations,'PRIORITY_RECEIPT_ROOT',Path(current_directory_name)),patch.object(gpu_job_queue,'prioritize_waiting_generation') as current_priority_mock:
                with self.assertRaises(ValueError):priority_operations.submit_hermes_priority_once('priority_new_123','kimodo',current_job_identifier,'a'*64)
                current_priority_mock.assert_not_called()
                self.assertFalse((Path(current_directory_name)/'priority_new_123.json').exists())

    def test_hermes_priority_submission_uses_only_isolated_ticket(self):
        from tools.review.domains.hermes_agent import priority_operations
        current_job='2026-10-09_21-13-20-1a356bbd'
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_root=Path(current_temp_directory)
            current_queue=current_root/'.tmp/gpu-queue'
            current_queue.mkdir(parents=True)
            current_job_directory=current_root/'.tmp/test/kimodo'/current_job
            current_job_directory.mkdir(parents=True)
            (current_job_directory/'status.json').write_text(json.dumps({'status':'queued'}))
            (current_job_directory/'gpu-command.json').write_text(json.dumps({'service':'image'}))
            current_ticket=current_queue/'ticket.json'
            current_ticket.write_text(json.dumps({'pid':os.getpid(),'path':str(current_job_directory)}))
            current_revision=gpu_job_queue.fingerprint_gpu_queue_ticket(current_ticket)
            with patch.object(priority_operations,'PRIORITY_RECEIPT_ROOT',current_root/'receipts'),patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root),patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue):
                current_result=priority_operations.submit_hermes_priority_once('request_789','kimodo',current_job,current_revision)
                self.assertEqual(current_result['state'],'completed')
                self.assertTrue(priority_operations.submit_hermes_priority_once('request_789','kimodo',current_job,current_revision)['duplicate'])
                self.assertEqual(json.loads((current_queue/'priority-order').read_text())['ticket.json'],-1)

    def test_gateway_priority_route(self):
        self.assertEqual(resolve_management_command('kimodo','prioritize',{'id':'2026-10-09_21-13-20-1a356bbd'}), ('POST','/kimodo/history/2026-10-09_21-13-20-1a356bbd/prioritize'))
        with self.assertRaises(ValueError):
            resolve_management_command('kimodo','prioritize',{'id':'../invalid'})
