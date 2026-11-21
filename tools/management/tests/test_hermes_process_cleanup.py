import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from unittest.mock import patch
from tools.management.common.gpu_job_queue import stop_hermes_worker_process_group, recover_stale_hermes_reservation, is_gpu_queue_executor_alive


class HermesProcessCleanupTests(unittest.TestCase):
    def test_gpu_reservation_lock_rejects_fifo_and_symlink(self):
        from tools.management.common import gpu_job_queue
        from tools.management.domains.hermes_agent.writer_reservation import hold_writer_reservation_queue_lock
        with tempfile.TemporaryDirectory() as current_root_name:
            current_root_path=Path(current_root_name)
            (current_root_path/'active').mkdir()
            current_lock_path=current_root_path/'execution.lock'
            with patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_root_path):
                os.mkfifo(current_lock_path)
                with self.assertRaises((OSError,ValueError)):
                    with hold_writer_reservation_queue_lock():self.fail('FIFO 잠금을 허용했습니다.')
                current_lock_path.unlink()
                (current_root_path/'target').write_text('')
                current_lock_path.symlink_to(current_root_path/'target')
                with self.assertRaises((OSError,ValueError)):
                    with hold_writer_reservation_queue_lock():self.fail('심볼릭 링크 잠금을 허용했습니다.')
                current_lock_path.unlink()
                with hold_writer_reservation_queue_lock() as current_active_root:
                    self.assertEqual(current_active_root,current_root_path/'active')

    def test_oversized_recovery_receipts_never_stop_process(self):
        from tools.management.domains.hermes_agent import generator_reservation_recovery,writer_reservation
        from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore,HERMES_DELEGATION_RECORD_MAXIMUM_BYTES
        with tempfile.TemporaryDirectory() as current_root_name:
            current_root_path=Path(current_root_name)
            (current_root_path/'request_123.json').write_bytes(b'x'*(HERMES_DELEGATION_RECORD_MAXIMUM_BYTES+1))
            current_store_value=HermesDelegationStore(current_root_path)
            with patch('tools.management.common.gpu_job_queue.stop_hermes_worker_process_group') as current_stop_mock:
                with patch.object(generator_reservation_recovery,'HermesDelegationStore',return_value=current_store_value):
                    with self.assertRaises(ValueError):generator_reservation_recovery.recover_generator_reservation_once('request_123','kimodo','job-1','a'*64,True)
                with patch.object(writer_reservation,'HermesDelegationStore',return_value=current_store_value):
                    with self.assertRaises(ValueError):writer_reservation.recover_writer_reservation_once('request_123','job-1','a'*64,True)
                current_stop_mock.assert_not_called()

    def test_generator_recovery_receipt_rejects_damaged_identity(self):
        from tools.management.domains.hermes_agent.generator_reservation_recovery import inspect_generator_recovery_receipt
        current_receipt={'version':13,'id':'recovery_request_123','service':'music-heartmula','job_id':'job_123','review_sha256':'a'*64,'state':'completed'}
        self.assertEqual(inspect_generator_recovery_receipt(current_receipt,'recovery_request_123')['state'],'completed')
        for current_bad_record in ({**current_receipt,'service':'writer-agent'},{**current_receipt,'service':'unknown'},
                {**current_receipt,'job_id':'../other'},{**current_receipt,'review_sha256':'not-a-hash'},
                {**current_receipt,'version':True},{**current_receipt,'extra':'field'}):
            with self.subTest(receipt=current_bad_record),self.assertRaises(ValueError):
                inspect_generator_recovery_receipt(current_bad_record,'recovery_request_123')

    def test_zombie_and_reused_pid_are_not_live_executors(self):
        hermes_child_process = subprocess.Popen([sys.executable, '-c', 'pass'])
        try:
            os.waitid(os.P_PID, hermes_child_process.pid, os.WEXITED | os.WNOWAIT)
            self.assertFalse(is_gpu_queue_executor_alive(hermes_child_process.pid))
        finally:
            hermes_child_process.wait()
        self.assertFalse(is_gpu_queue_executor_alive(os.getpid(), 'not-the-current-start-time'))
        self.assertTrue(is_gpu_queue_executor_alive(os.getpid()))

    def test_stale_reservation_without_group_stays_blocked(self):
        self.assertFalse(recover_stale_hermes_reservation({'service':'hermes-agent'}))
        hermes_pid_descriptor = os.open('/dev/null', os.O_RDONLY)
        with patch('tools.management.common.gpu_job_queue.open_verified_hermes_process_group', return_value=hermes_pid_descriptor), patch('tools.management.common.gpu_job_queue.stop_hermes_worker_process_group') as hermes_stop_mock:
            self.assertTrue(recover_stale_hermes_reservation({'service':'hermes-agent', 'worker_pgid':12345}))
            hermes_stop_mock.assert_called_once_with(12345, hermes_pid_descriptor)

    def test_recovered_orphan_is_marked_failed(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_root_path = Path(hermes_temporary_root)
            hermes_job_path = hermes_root_path / '.tmp/test/job'
            hermes_job_path.mkdir(parents=True)
            (hermes_job_path / 'status.json').write_text('{"status":"running"}')
            hermes_pid_descriptor = os.open('/dev/null', os.O_RDONLY)
            with patch('tools.management.common.gpu_job_queue.WORKFLOW_ROOT_DIRECTORY', hermes_root_path), patch('tools.management.common.gpu_job_queue.open_verified_hermes_process_group', return_value=hermes_pid_descriptor), patch('tools.management.common.gpu_job_queue.stop_hermes_worker_process_group'):
                self.assertTrue(recover_stale_hermes_reservation({'service':'hermes-agent', 'worker_pgid':12345, 'path':str(hermes_job_path)}))
            self.assertEqual(json.loads((hermes_job_path / 'status.json').read_text())['status'], 'failed')

    def test_orphaned_child_is_stopped_before_release(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_child_file = Path(hermes_temporary_root) / 'child.pid'
            hermes_parent_code = "import pathlib,subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); pathlib.Path(sys.argv[1]).write_text(str(p.pid))"
            hermes_parent_process = subprocess.Popen([sys.executable, '-c', hermes_parent_code, str(hermes_child_file)], start_new_session=True)
            hermes_pid_descriptor = os.pidfd_open(hermes_parent_process.pid)
            self.assertEqual(hermes_parent_process.wait(timeout=5), 0)
            hermes_child_identifier = int(hermes_child_file.read_text())
            try:
                stop_hermes_worker_process_group(hermes_parent_process.pid, hermes_pid_descriptor)
                hermes_stat_path = Path(f'/proc/{hermes_child_identifier}/stat')
                if hermes_stat_path.exists():
                    self.assertIn(hermes_stat_path.read_text().rpartition(') ')[2].split()[0], ('Z', 'X'))
            finally:
                os.close(hermes_pid_descriptor)
                try:
                    os.kill(hermes_child_identifier, 9)
                except ProcessLookupError:
                    pass

    def test_other_service_group_identity_is_observed_without_stopping_process(self):
        import json
        import tempfile
        from tools.management.domains.hermes_agent.management_observer import read_hermes_gpu_reservation_snapshot
        current_process_token='b'*32
        current_worker_environment=dict(os.environ,SLIME_HERMES_PROCESS_TOKEN=current_process_token)
        current_worker_process=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],env=current_worker_environment,start_new_session=True)
        try:
            current_worker_fields=Path(f'/proc/{current_worker_process.pid}/stat').read_text().rpartition(') ')[2].split()
            with tempfile.TemporaryDirectory() as current_temp_name:
                current_active_root=Path(current_temp_name)/'active'
                current_active_root.mkdir()
                current_record={'service':'image','pid':os.getpid(),'pid_start_token':'0','required_memory_mib':1000,'worker_pgid':current_worker_process.pid,'worker_start_token':current_worker_fields[19],'worker_process_token':current_process_token}
                (current_active_root/'job.json').write_text(json.dumps(current_record))
                current_observed=read_hermes_gpu_reservation_snapshot(current_temp_name)['records'][0]
                self.assertEqual(current_observed['state'],'cleanup_unverified')
                self.assertEqual(current_observed['worker_leader'],'verified_running')
                self.assertNotIn(current_process_token,str(current_observed))
                self.assertIsNone(current_worker_process.poll())
                current_record['worker_process_token']='c'*32
                (current_active_root/'job.json').write_text(json.dumps(current_record))
                self.assertEqual(read_hermes_gpu_reservation_snapshot(current_temp_name)['records'][0]['worker_leader'],'unverified')
                self.assertIsNone(current_worker_process.poll())
        finally:
            if current_worker_process.poll() is None:
                current_worker_process.terminate()
                current_worker_process.wait(timeout=5)

    def test_writer_recovery_receipt_rejects_corrupt_identity(self):
        from tools.management.domains.hermes_agent.writer_reservation import inspect_writer_recovery_receipt
        current_record_value={'version':12,'id':'request_123','job_id':'20261118-120000-12345678','preview_sha256':'a'*64,'state':'completed'}
        self.assertEqual(inspect_writer_recovery_receipt(current_record_value,'request_123')['state'],'completed')
        for current_changed_values in ({'job_id':'../invalid'},{'preview_sha256':'bad'},{'id':'other'},{'version':True},{'extra':'unexpected'}):
            with self.subTest(changed=current_changed_values),self.assertRaises(ValueError):
                inspect_writer_recovery_receipt({**current_record_value,**current_changed_values},'request_123')

    def test_unknown_recovery_receipt_is_not_dispatched_again(self):
        from unittest.mock import patch
        from tools.management.common import gpu_job_queue
        from tools.management.domains.hermes_agent import writer_reservation,generator_reservation_recovery
        from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore
        current_job_identifier='20261118-120000-12345678'
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_store_value=HermesDelegationStore(Path(current_directory_name))
            current_writer_record={'version':12,'id':'writer_recovery_123','job_id':current_job_identifier,'preview_sha256':'a'*64,'state':'dispatching'}
            current_generator_record={'version':13,'id':'generator_recovery_123','service':'music-heartmula','job_id':'job_123','review_sha256':'b'*64,'state':'dispatching'}
            current_store_value.resolve_delegation_record_path(current_writer_record['id']).write_text(json.dumps(current_writer_record))
            current_store_value.resolve_delegation_record_path(current_generator_record['id']).write_text(json.dumps(current_generator_record))
            with patch.object(writer_reservation,'HermesDelegationStore',return_value=current_store_value),patch.object(generator_reservation_recovery,'HermesDelegationStore',return_value=current_store_value),patch.object(gpu_job_queue,'stop_hermes_worker_process_group') as current_stop_mock:
                current_writer_result=writer_reservation.recover_writer_reservation_once('writer_recovery_123',current_job_identifier,'a'*64,True)
                current_generator_result=generator_reservation_recovery.recover_generator_reservation_once('generator_recovery_123','music-heartmula','job_123','b'*64,True)
                self.assertEqual((current_writer_result['state'],current_writer_result['duplicate']),('unknown',True))
                self.assertEqual((current_generator_result['state'],current_generator_result['duplicate']),('unknown',True))
                current_stop_mock.assert_not_called()

    def test_writer_recovery_does_not_complete_changed_receipt(self):
        from contextlib import nullcontext
        from unittest.mock import patch
        from tools.management.common import gpu_job_queue
        from tools.management.domains.hermes_agent import writer_reservation
        from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_active_root=current_root_path/'active'
            current_active_root.mkdir()
            current_record_path=current_active_root/'reservation.json'
            current_record_path.write_text(json.dumps({'worker_pgid':123,'pid':456}))
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            current_request_identifier='recovery_123'
            current_job_identifier='20261118-120000-12345678'
            current_receipt_path=current_store_value.resolve_delegation_record_path(current_request_identifier)
            def current_find_record(current_active_value,current_job_value):
                return current_record_path,json.loads(current_record_path.read_text())
            def current_change_receipt(current_process_group,current_descriptor):
                current_receipt_value=json.loads(current_receipt_path.read_text())
                current_receipt_value['extra']='changed'
                current_receipt_path.write_text(json.dumps(current_receipt_value))
            with patch.object(writer_reservation,'HermesDelegationStore',return_value=current_store_value),patch.object(writer_reservation,'hold_writer_reservation_queue_lock',side_effect=lambda:nullcontext(current_active_root)),patch.object(writer_reservation,'find_writer_reservation_record',side_effect=current_find_record),patch.object(writer_reservation,'inspect_writer_reservation_record',side_effect=lambda *args:({'recoverable':True,'preview_sha256':'a'*64},os.open('/dev/null',os.O_RDONLY))),patch.object(writer_reservation,'is_writer_executor_definitely_absent',return_value=True),patch.object(gpu_job_queue,'stop_hermes_worker_process_group',side_effect=current_change_receipt):
                with self.assertRaisesRegex(ValueError,'접수 기록이 변경'):
                    writer_reservation.recover_writer_reservation_once(current_request_identifier,current_job_identifier,'a'*64,True)
            current_receipt_value=json.loads(current_receipt_path.read_text())
            self.assertEqual(current_receipt_value['state'],'dispatching')
            self.assertEqual(current_receipt_value['extra'],'changed')

    def test_dedicated_gpu_reservation_requires_owned_job_path(self):
        from unittest.mock import patch
        from tools.management.common import gpu_job_queue
        from tools.management.domains.hermes_agent.reservation_observer import inspect_generator_reservation_identity
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_workflow_root=Path(current_directory_name)
            current_queue_root=current_workflow_root/'queue'
            current_active_root=current_queue_root/'active'
            current_active_root.mkdir(parents=True)
            current_job_root=current_workflow_root/'.tmp/test/music-heartmula/job_123'
            current_job_root.mkdir(parents=True)
            current_record_value={'service':'music-heartmula','path':str(current_job_root),'required_memory_mib':1}
            current_record_path=current_active_root/'reservation.json'
            current_record_path.write_text(json.dumps(current_record_value))
            with patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_root),patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_workflow_root):
                self.assertEqual(inspect_generator_reservation_identity('music-heartmula','job_123')['service'],'music-heartmula')
                current_expression_root=current_workflow_root/'.tmp/test/flux-expression-generator/job_123'
                current_expression_root.mkdir(parents=True)
                current_record_value.update(service='flux-expression',path=str(current_expression_root))
                current_record_path.write_text(json.dumps(current_record_value))
                self.assertEqual(inspect_generator_reservation_identity('flux-expression','job_123')['service'],'flux-expression')
                current_record_value.update(service='music-heartmula',path=str(current_workflow_root/'elsewhere/job_123'))
                current_record_path.write_text(json.dumps(current_record_value))
                with self.assertRaisesRegex(ValueError,'원 서비스'):
                    inspect_generator_reservation_identity('music-heartmula','job_123')

    def test_qwen_reservation_identity_requires_matching_original_service(self):
        from unittest.mock import patch
        from tools.management.common import gpu_job_queue
        from tools.management.domains.hermes_agent.reservation_observer import inspect_generator_reservation_identity
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_workflow_root=Path(current_directory_name)
            current_queue_root=current_workflow_root/'queue'
            current_active_root=current_queue_root/'active'
            current_active_root.mkdir(parents=True)
            current_record_path=current_active_root/'reservation.json'
            with patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_root),patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_workflow_root):
                for current_service_name,current_other_service,current_directory_name in (('qwen-21','qwen-21-circular','qwen-image-21'),('qwen-21-circular','qwen-21','qwen-image-21-circular'),('mannequin-generator','prop-generator','mannequin-generator'),('prop-generator','vegetation-generator','prop-generator'),('vegetation-generator','prop-generator','vegetation-generator'),('expression','seamless-tile','expression-generator'),('seamless-tile','expression','seamless-tile-generator'),('floor-tile','expression','qwen-image-2512/floor-tile'),('billboard-generator','building-generator','billboard-generator'),('building-generator','billboard-generator','building-generator')):
                    with self.subTest(service=current_service_name):
                        current_job_root=current_workflow_root/'.tmp/test'/current_directory_name/'job_123'
                        current_job_root.mkdir(parents=True)
                        current_record_value={'service':'image','path':str(current_job_root),'required_memory_mib':1}
                        current_record_path.write_text(json.dumps(current_record_value))
                        current_result_value=inspect_generator_reservation_identity(current_service_name,'job_123')
                        self.assertEqual(current_result_value['service'],current_service_name)
                        self.assertFalse(current_result_value['review_ready'])
                        with self.assertRaisesRegex(ValueError,'원 서비스'):
                            inspect_generator_reservation_identity(current_other_service,'job_123')
                        self.assertEqual(json.loads(current_record_path.read_text()),current_record_value)

    def test_absent_generator_group_requires_review_and_rechecks_before_release(self):
        from tools.management.common import gpu_job_queue
        from tools.management.domains.hermes_agent import generator_reservation_recovery, reservation_observer
        from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore
        with tempfile.TemporaryDirectory() as current_temp_name:
            current_root_path=Path(current_temp_name)
            current_queue_root=current_root_path/'queue'
            current_active_root=current_queue_root/'active'
            current_active_root.mkdir(parents=True)
            current_job_path=current_root_path/'.tmp/test/wan22-fun-control/job_123'
            current_job_path.mkdir(parents=True)
            current_group_id=2147483646
            current_reservation={'service':'wan-fun','path':str(current_job_path),'pid':2147483645,'pid_start_token':'123',
                'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'required_memory_mib':1000,
                'worker_pgid':current_group_id,'worker_start_token':'123','worker_process_token':'a'*32}
            current_record_path=current_active_root/'reservation.json'
            current_record_path.write_text(json.dumps(current_reservation))
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            with patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_root), patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root_path), patch.object(generator_reservation_recovery,'HermesDelegationStore',return_value=current_store_value), patch.object(gpu_job_queue,'stop_hermes_worker_process_group') as current_stop_mock:
                current_review=reservation_observer.inspect_generator_reservation_identity('wan22-fun-control','job_123')
                self.assertTrue(current_review['review_ready'])
                self.assertEqual(current_review['worker_leader'],'group_absent')
                with self.assertRaisesRegex(ValueError,'별도 그룹'):
                    generator_reservation_recovery.recover_generator_reservation_once('recovery_no_check','wan22-fun-control','job_123',current_review['review_sha256'],False)
                self.assertTrue(current_record_path.exists())
                with patch.object(generator_reservation_recovery,'is_generator_process_group_absent',return_value=False):
                    with self.assertRaisesRegex(ValueError,'그룹 부재'):
                        generator_reservation_recovery.recover_generator_reservation_once('recovery_race','wan22-fun-control','job_123',current_review['review_sha256'],True)
                self.assertTrue(current_record_path.exists())
                current_record_path.write_text(json.dumps(current_reservation))
                current_result=generator_reservation_recovery.recover_generator_reservation_once('recovery_success','wan22-fun-control','job_123',current_review['review_sha256'],True)
                self.assertEqual(current_result['state'],'completed')
                self.assertFalse(current_record_path.exists())
                current_stop_mock.assert_not_called()

    def test_absent_group_fails_closed_on_bad_identity_or_live_group(self):
        from tools.management.domains.hermes_agent.reservation_observer import is_generator_process_group_absent
        current_record={'worker_pgid':os.getpgrp(),'worker_start_token':'123','worker_process_token':'a'*32,
                        'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
        self.assertFalse(is_generator_process_group_absent(current_record))
        for current_change in ({'worker_pgid':2147483646,'boot_id':'bad'}, {'worker_pgid':2147483646,'worker_process_token':'bad'}, {'worker_pgid':2147483646,'worker_start_token':'bad'}):
            self.assertFalse(is_generator_process_group_absent({**current_record,**current_change}))

    def test_generator_recovery_rechecks_review_and_preserves_unrelated_process(self):
        from tools.management.common import gpu_job_queue
        from tools.management.domains.hermes_agent import generator_reservation_recovery
        from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore
        from tools.management.domains.hermes_agent.reservation_observer import inspect_generator_reservation_identity
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_queue_root=current_root_path/'queue'
            current_active_root=current_queue_root/'active'
            current_active_root.mkdir(parents=True)
            current_job_root=current_root_path/'.tmp/test/music-heartmula/job_123'
            current_job_root.mkdir(parents=True)
            current_environment_record={**os.environ,'SLIME_HERMES_PROCESS_TOKEN':'a'*32}
            current_worker_process=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],env=current_environment_record,start_new_session=True)
            current_other_process=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)
            try:
                current_worker_path=Path('/proc')/str(current_worker_process.pid)
                current_deadline_value=time.monotonic()+5
                while b'SLIME_HERMES_PROCESS_TOKEN=' not in (current_worker_path/'environ').read_bytes():
                    if time.monotonic()>current_deadline_value:self.fail('격리 작업자 환경 준비 실패')
                    time.sleep(.01)
                current_start_token=(current_worker_path/'stat').read_text().rpartition(') ')[2].split()[19]
                current_record_value={'service':'music-heartmula','path':str(current_job_root),'required_memory_mib':1,'pid':99999999,'pid_start_token':'1','worker_pgid':current_worker_process.pid,'worker_start_token':current_start_token,'worker_process_token':'a'*32}
                current_record_path=current_active_root/'reservation.json'
                current_record_path.write_text(json.dumps(current_record_value))
                with patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_root),patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root_path),patch.object(generator_reservation_recovery,'HermesDelegationStore',return_value=HermesDelegationStore(current_root_path/'receipts')):
                    current_review_record=inspect_generator_reservation_identity('music-heartmula','job_123')
                    self.assertTrue(current_review_record['review_ready'])
                    current_digest_value=current_review_record['review_sha256']
                    with self.assertRaises(ValueError):
                        generator_reservation_recovery.recover_generator_reservation_once('recovery_request_123','music-heartmula','job_123',current_digest_value,False)
                    current_record_value['required_memory_mib']=2
                    current_record_path.write_text(json.dumps(current_record_value))
                    with self.assertRaises(ValueError):
                        generator_reservation_recovery.recover_generator_reservation_once('recovery_request_123','music-heartmula','job_123',current_digest_value,True)
                    self.assertIsNone(current_worker_process.poll())
                    current_digest_value=inspect_generator_reservation_identity('music-heartmula','job_123')['review_sha256']
                    current_result_value=generator_reservation_recovery.recover_generator_reservation_once('recovery_request_123','music-heartmula','job_123',current_digest_value,True)
                    self.assertEqual(current_result_value['state'],'completed')
                    self.assertTrue(generator_reservation_recovery.recover_generator_reservation_once('recovery_request_123','music-heartmula','job_123',current_digest_value,True)['duplicate'])
                    self.assertEqual(generator_reservation_recovery.read_generator_recovery_receipt('recovery_request_123')['state'],'completed')
                self.assertFalse(current_record_path.exists())
                self.assertIsNotNone(current_worker_process.poll())
                self.assertIsNone(current_other_process.poll())
            finally:
                for current_process_value in (current_worker_process,current_other_process):
                    if current_process_value.poll() is None:current_process_value.kill()
                    current_process_value.wait(timeout=5)

    def test_generator_recovery_failure_retains_reservation_and_never_retries(self):
        from tools.management.common import gpu_job_queue
        from tools.management.domains.hermes_agent import generator_reservation_recovery
        from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore
        from tools.management.domains.hermes_agent.reservation_observer import inspect_generator_reservation_identity
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_queue_root=current_root_path/'queue'
            current_active_root=current_queue_root/'active'
            current_active_root.mkdir(parents=True)
            current_job_root=current_root_path/'.tmp/test/music-heartmula/job_456'
            current_job_root.mkdir(parents=True)
            current_environment_record={**os.environ,'SLIME_HERMES_PROCESS_TOKEN':'b'*32}
            current_worker_process=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],env=current_environment_record,start_new_session=True)
            try:
                current_worker_path=Path('/proc')/str(current_worker_process.pid)
                current_deadline_value=time.monotonic()+5
                while b'SLIME_HERMES_PROCESS_TOKEN=' not in (current_worker_path/'environ').read_bytes():
                    if time.monotonic()>current_deadline_value:self.fail('격리 작업자 환경 준비 실패')
                    time.sleep(.01)
                current_start_token=(current_worker_path/'stat').read_text().rpartition(') ')[2].split()[19]
                current_record_value={'service':'music-heartmula','path':str(current_job_root),'required_memory_mib':1,'pid':99999999,'pid_start_token':'1','worker_pgid':current_worker_process.pid,'worker_start_token':current_start_token,'worker_process_token':'b'*32}
                current_record_path=current_active_root/'reservation.json'
                current_record_path.write_text(json.dumps(current_record_value))
                with patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_root),patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root_path),patch.object(generator_reservation_recovery,'HermesDelegationStore',return_value=HermesDelegationStore(current_root_path/'receipts')),patch.object(gpu_job_queue,'stop_hermes_worker_process_group',side_effect=OSError('test failure')) as current_stop_mock:
                    current_digest_value=inspect_generator_reservation_identity('music-heartmula','job_456')['review_sha256']
                    with self.assertRaises(OSError):
                        generator_reservation_recovery.recover_generator_reservation_once('recovery_request_456','music-heartmula','job_456',current_digest_value,True)
                    self.assertTrue(current_record_path.exists())
                    self.assertEqual(json.loads(current_record_path.read_text())['recovery_in_progress'],'recovery_request_456')
                    self.assertEqual(generator_reservation_recovery.read_generator_recovery_receipt('recovery_request_456')['state'],'unknown')
                    current_repeat_record=generator_reservation_recovery.recover_generator_reservation_once('recovery_request_456','music-heartmula','job_456',current_digest_value,True)
                    self.assertEqual(current_repeat_record['state'],'unknown')
                    self.assertTrue(current_repeat_record['duplicate'])
                    current_stop_mock.assert_called_once()
                    self.assertIsNone(current_worker_process.poll())
            finally:
                if current_worker_process.poll() is None:current_worker_process.kill()
                current_worker_process.wait(timeout=5)

    def test_generator_reservation_inspection_is_unique_and_never_stops_worker(self):
        import json
        import tempfile
        import threading
        from unittest.mock import patch
        from tools.management.common import gpu_job_queue as current_queue_module
        from tools.management.domains.hermes_agent.reservation_observer import inspect_generator_reservation_identity
        current_token='d'*32
        current_worker=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],env=dict(os.environ,SLIME_HERMES_PROCESS_TOKEN=current_token),start_new_session=True)
        try:
            current_fields=Path(f'/proc/{current_worker.pid}/stat').read_text().rpartition(') ')[2].split()
            with tempfile.TemporaryDirectory() as current_temp:
                current_root=Path(current_temp)
                current_queue=current_root/'.tmp/gpu-queue'
                current_active=current_queue/'active'
                current_active.mkdir(parents=True)
                current_job=current_root/'.tmp/test/kimodo/2026-11-18_12-00-00-12345678'
                current_job.mkdir(parents=True)
                current_record={'service':'image','path':str(current_job),'pid':99999999,'pid_start_token':'0','required_memory_mib':1024,'worker_pgid':current_worker.pid,'worker_start_token':current_fields[19],'worker_process_token':current_token}
                current_file=current_active/'one.json'
                current_file.write_text(json.dumps(current_record))
                with patch.object(current_queue_module,'GPU_QUEUE_DIRECTORY',current_queue),patch.object(current_queue_module,'WORKFLOW_ROOT_DIRECTORY',current_root):
                    for current_attempt in range(200):
                        current_result=inspect_generator_reservation_identity('kimodo',current_job.name)
                        if current_result['worker_leader']=='verified_running':break
                        threading.Event().wait(0.01)
                    self.assertEqual(current_result['executor'],'not_observed')
                    self.assertEqual(current_result['worker_leader'],'verified_running')
                    self.assertTrue(current_result['review_ready'])
                    self.assertRegex(current_result['review_sha256'],r'^[a-f0-9]{64}$')
                    current_initial_digest=current_result['review_sha256']
                    current_record['required_memory_mib']=1025
                    current_file.write_text(json.dumps(current_record))
                    self.assertNotEqual(inspect_generator_reservation_identity('kimodo',current_job.name)['review_sha256'],current_initial_digest)
                    current_record['recovery_in_progress']='pending'
                    current_file.write_text(json.dumps(current_record))
                    self.assertFalse(inspect_generator_reservation_identity('kimodo',current_job.name)['review_ready'])
                    current_record.pop('recovery_in_progress')
                    current_file.write_text(json.dumps(current_record))
                    self.assertNotIn(current_token,str(current_result))
                    self.assertNotIn(str(current_root),str(current_result))
                    self.assertIsNone(current_worker.poll())
                    current_record['pid']=os.getpid()
                    current_record['pid_start_token']=Path(f'/proc/{os.getpid()}/stat').read_text().rpartition(') ')[2].split()[19]
                    current_file.write_text(json.dumps(current_record))
                    self.assertEqual(inspect_generator_reservation_identity('kimodo',current_job.name)['executor'],'unverified')
                    current_record['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
                    current_file.write_text(json.dumps(current_record))
                    self.assertEqual(inspect_generator_reservation_identity('kimodo',current_job.name)['executor'],'observed')
                    with patch.object(current_queue_module,'inspect_gpu_ticket_executor_identity',side_effect=ValueError('unreadable')):
                        self.assertEqual(inspect_generator_reservation_identity('kimodo',current_job.name)['executor'],'unverified')
                    with patch.object(current_queue_module.os,'kill',side_effect=PermissionError('denied')):
                        self.assertEqual(inspect_generator_reservation_identity('kimodo',current_job.name)['executor'],'unverified')
                    current_record['pid']=10**100
                    current_file.write_text(json.dumps(current_record))
                    self.assertEqual(inspect_generator_reservation_identity('kimodo',current_job.name)['executor'],'unverified')
                    self.assertIsNone(current_worker.poll())
                    with self.assertRaises(ValueError):inspect_generator_reservation_identity('dwpose',current_job.name)
                    (current_active/'two.json').write_text(json.dumps(current_record))
                    with self.assertRaisesRegex(ValueError,'유일'):inspect_generator_reservation_identity('kimodo',current_job.name)
                    self.assertTrue(current_file.exists())
                    self.assertIsNone(current_worker.poll())
        finally:
            if current_worker.poll() is None:
                current_worker.terminate()
                current_worker.wait(timeout=5)

    def test_recovery_requires_matching_process_identity(self):
        hermes_process_token = 'a' * 32
        hermes_process_environment = dict(os.environ, SLIME_HERMES_PROCESS_TOKEN=hermes_process_token)
        hermes_worker_process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], env=hermes_process_environment, start_new_session=True)
        try:
            import threading
            current_environment_path=Path(f'/proc/{hermes_worker_process.pid}/environ')
            for current_attempt in range(200):
                if ('SLIME_HERMES_PROCESS_TOKEN='+hermes_process_token).encode() in current_environment_path.read_bytes().split(b'\0'):break
                threading.Event().wait(0.01)
            else:self.fail('격리 작업자 환경이 준비되지 않았습니다.')
            hermes_stat_fields = Path(f'/proc/{hermes_worker_process.pid}/stat').read_text().rpartition(') ')[2].split()
            hermes_reservation_record = {'service':'hermes-agent', 'worker_pgid':hermes_worker_process.pid, 'worker_start_token':hermes_stat_fields[19], 'worker_process_token':'b' * 32}
            self.assertFalse(recover_stale_hermes_reservation(hermes_reservation_record))
            self.assertIsNone(hermes_worker_process.poll())
            hermes_reservation_record['worker_process_token'] = hermes_process_token
            hermes_reservation_record['worker_start_token'] = 'not-the-start-token'
            self.assertFalse(recover_stale_hermes_reservation(hermes_reservation_record))
            self.assertIsNone(hermes_worker_process.poll())
            hermes_reservation_record['worker_start_token'] = hermes_stat_fields[19]
            self.assertTrue(recover_stale_hermes_reservation(hermes_reservation_record))
            self.assertNotEqual(hermes_worker_process.wait(timeout=5), 0)
        finally:
            if hermes_worker_process.poll() is None:
                hermes_worker_process.kill()
                hermes_worker_process.wait()


if __name__ == '__main__':
    unittest.main()
