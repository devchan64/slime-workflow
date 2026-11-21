"""작가 중지 요청이 격리된 실제 CPU 프로세스에 도달하는지 검증한다."""
import json
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

from generators.writer_agent.documents import save_yaml_document
from generators.writer_agent.jobs import read_process_identity
from generators.writer_agent.management import WriterAgentManager
from workflow.tests.test_kimodo_cache_queue_integration import execute_isolated_queue_job


class WriterCancelQueueIntegrationTests(unittest.TestCase):
    def test_cancellation_stops_worker_child_that_ignores_term(self):
        import signal
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_job_root=current_root_path/'job'
            current_job_root.mkdir()
            current_worker_path=current_root_path/'worker.py'
            current_child_code="import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); print('ready',flush=True); time.sleep(30)"
            current_worker_path.write_text("import pathlib,subprocess,sys,time\np=pathlib.Path(sys.argv[1]); c=subprocess.Popen([sys.executable,'-c',sys.argv[2]],stdout=subprocess.PIPE,text=True); c.stdout.readline(); (p/'child-pid').write_text(str(c.pid))\nwhile not (p/'release').exists():time.sleep(.05)\n")
            (current_job_root/'status.json').write_text(json.dumps({'status':'queued'}))
            (current_job_root/'gpu-command.json').write_text(json.dumps({'service':'writer-agent','command':[sys.executable,str(current_worker_path),str(current_job_root),current_child_code]}))
            current_queue_path=current_root_path/'queue'
            current_queue_process=multiprocessing.get_context('fork').Process(target=execute_isolated_queue_job,args=(str(current_queue_path),str(current_job_root)))
            current_child_identifier=None
            current_child_identity=None
            try:
                current_queue_process.start()
                current_deadline_value=time.monotonic()+8
                while not (current_job_root/'child-pid').exists():
                    if time.monotonic()>current_deadline_value:self.fail('격리 자식 프로세스 시작 실패')
                    time.sleep(.05)
                current_child_identifier=int((current_job_root/'child-pid').read_text())
                current_child_identity=read_process_identity(current_child_identifier)
                (current_job_root/'cancel.request').touch()
                current_queue_process.join(timeout=8)
                self.assertEqual(current_queue_process.exitcode,0)
                self.assertIsNone(read_process_identity(current_child_identifier),'중지 후 자식이 살아 있습니다')
                self.assertEqual(list((current_queue_path/'active').glob('*.json')),[])
            finally:
                (current_job_root/'cancel.request').touch()
                (current_job_root/'release').touch()
                if current_queue_process.pid is not None:
                    current_queue_process.join(timeout=4)
                    if current_queue_process.is_alive():
                        current_queue_process.terminate()
                        current_queue_process.join(timeout=4)
                if current_child_identifier and current_child_identity and read_process_identity(current_child_identifier)==current_child_identity:
                    os.kill(current_child_identifier,signal.SIGKILL)

    def test_dead_writer_executor_preserves_reservation_and_blocks_other_job(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_gpu_reservation_snapshot
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_queue_path=current_root_path/'queue'
            current_writer_job=current_root_path/'20261118-120000-12345678'
            current_image_job=current_root_path/'image'
            current_worker_path=current_root_path/'worker.py'
            current_worker_path.write_text("import os,pathlib,sys,time\np=pathlib.Path(sys.argv[1]);(p/'worker-pid').write_text(str(os.getpid()));(p/'started').touch()\nwhile not (p/'release').exists():time.sleep(.05)\n")
            for current_job_path,current_service_name in ((current_writer_job,'writer-agent'),(current_image_job,'image')):
                current_job_path.mkdir()
                (current_job_path/'status.json').write_text(json.dumps({'status':'queued'}))
                (current_job_path/'gpu-command.json').write_text(json.dumps({'service':current_service_name,'command':[sys.executable,str(current_worker_path),str(current_job_path)]}))
            current_context=multiprocessing.get_context('fork')
            current_writer_process=current_context.Process(target=execute_isolated_queue_job,args=(str(current_queue_path),str(current_writer_job)))
            current_image_process=current_context.Process(target=execute_isolated_queue_job,args=(str(current_queue_path),str(current_image_job)))
            def wait_for_test_condition(current_condition_value,current_failure_message):
                current_deadline_value=time.monotonic()+8
                while not current_condition_value():
                    if time.monotonic()>current_deadline_value:self.fail(current_failure_message)
                    time.sleep(.05)
            current_worker_identifier=None
            current_worker_identity=None
            try:
                current_writer_process.start()
                wait_for_test_condition(lambda:(current_writer_job/'started').exists(),'작가 작업자 시작 실패')
                current_worker_identifier=int((current_writer_job/'worker-pid').read_text())
                current_worker_identity=read_process_identity(current_worker_identifier)
                current_writer_process.kill()
                current_writer_process.join(timeout=5)
                self.assertIsNotNone(current_writer_process.exitcode)
                current_image_process.start()
                wait_for_test_condition(lambda:json.loads((current_image_job/'status.json').read_text()).get('queue_position')==1,'생성 작업 대기 실패')
                self.assertFalse((current_image_job/'started').exists())
                current_reservation_record=read_hermes_gpu_reservation_snapshot(current_queue_path)['records'][0]
                self.assertEqual(current_reservation_record['state'],'cleanup_unverified')
                self.assertEqual(current_reservation_record['job_id'],current_writer_job.name)
                self.assertEqual(current_reservation_record['worker_leader'],'verified_running')
                self.assertNotIn('worker_pgid',current_reservation_record)
                self.assertNotIn('worker_process_token',current_reservation_record)
                from unittest.mock import patch
                from workflow.common import gpu_job_queue as current_queue_module
                from workflow.domains.hermes_agent.writer_reservation import preview_writer_reservation_recovery
                with patch.object(current_queue_module,'GPU_QUEUE_DIRECTORY',current_queue_path):
                    current_preview_record=preview_writer_reservation_recovery(current_writer_job.name)
                self.assertTrue(current_preview_record['recoverable'])
                self.assertEqual(len(current_preview_record['preview_sha256']),64)
                self.assertNotIn(str(current_worker_identifier),str(current_preview_record))
                self.assertEqual(read_process_identity(current_worker_identifier),current_worker_identity)
                (current_image_job/'cancel.request').touch()
                current_image_process.join(timeout=5)
                self.assertEqual(current_image_process.exitcode,0)
                self.assertEqual(len(list((current_queue_path/'active').glob('*.json'))),1)
            finally:
                (current_writer_job/'release').touch()
                (current_image_job/'cancel.request').touch()
                (current_image_job/'release').touch()
                if current_worker_identifier and current_worker_identity:
                    current_cleanup_deadline=time.monotonic()+3
                    while read_process_identity(current_worker_identifier)==current_worker_identity and time.monotonic()<current_cleanup_deadline:
                        time.sleep(.05)
                    if read_process_identity(current_worker_identifier)==current_worker_identity:
                        import signal
                        os.kill(current_worker_identifier,signal.SIGKILL)
                for current_process_value in (current_writer_process,current_image_process):
                    if current_process_value.pid is not None:
                        current_process_value.join(timeout=4)
                        if current_process_value.is_alive():
                            current_process_value.terminate()
                            current_process_value.join(timeout=4)

    def test_verified_stale_writer_recovery_stops_only_expected_group(self):
        import signal
        import subprocess
        from unittest.mock import patch
        from workflow.common import gpu_job_queue
        from workflow.domains.hermes_agent import writer_reservation
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_queue_path=current_root_path/'queue'
            current_job_root=current_root_path/'20261118-120000-12345678'
            current_job_root.mkdir()
            current_worker_path=current_root_path/'worker.py'
            current_worker_path.write_text("import os,pathlib,sys,time\np=pathlib.Path(sys.argv[1]); (p/'worker-pid').write_text(str(os.getpid())); (p/'started').touch()\nwhile not (p/'release').exists():time.sleep(.05)\n")
            (current_job_root/'status.json').write_text(json.dumps({'status':'queued'}))
            (current_job_root/'gpu-command.json').write_text(json.dumps({'service':'writer-agent','command':[sys.executable,str(current_worker_path),str(current_job_root)]}))
            current_queue_process=multiprocessing.get_context('fork').Process(target=execute_isolated_queue_job,args=(str(current_queue_path),str(current_job_root)))
            current_unrelated_process=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)
            current_worker_identifier=None
            current_worker_identity=None
            try:
                current_queue_process.start()
                current_deadline_value=time.monotonic()+8
                while not (current_job_root/'started').exists():
                    if time.monotonic()>current_deadline_value:self.fail('격리 작가 시작 실패')
                    time.sleep(.05)
                current_worker_identifier=int((current_job_root/'worker-pid').read_text())
                current_worker_identity=read_process_identity(current_worker_identifier)
                current_queue_process.kill()
                current_queue_process.join(timeout=5)
                with patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_path),patch.object(writer_reservation,'HermesDelegationStore',return_value=HermesDelegationStore(current_root_path/'receipts')):
                    current_preview_value=writer_reservation.preview_writer_reservation_recovery(current_job_root.name)
                    self.assertTrue(current_preview_value['recoverable'])
                    with self.assertRaises(ValueError):writer_reservation.recover_writer_reservation_once('recovery_request_123',current_job_root.name,current_preview_value['preview_sha256'],False)
                    with self.assertRaises(ValueError):writer_reservation.recover_writer_reservation_once('recovery_request_123',current_job_root.name,'a'*64,True)
                    current_result_value=writer_reservation.recover_writer_reservation_once('recovery_request_123',current_job_root.name,current_preview_value['preview_sha256'],True)
                    self.assertEqual(current_result_value['state'],'completed')
                    self.assertTrue(writer_reservation.recover_writer_reservation_once('recovery_request_123',current_job_root.name,current_preview_value['preview_sha256'],True)['duplicate'])
                    self.assertEqual(writer_reservation.read_writer_recovery_receipt('recovery_request_123')['state'],'completed')
                self.assertIsNone(read_process_identity(current_worker_identifier))
                self.assertIsNone(current_unrelated_process.poll())
                self.assertEqual(list((current_queue_path/'active').glob('*.json')),[])
            finally:
                (current_job_root/'release').touch()
                if current_queue_process.pid is not None:
                    current_queue_process.join(timeout=4)
                    if current_queue_process.is_alive():
                        current_queue_process.terminate()
                        current_queue_process.join(timeout=4)
                if current_worker_identifier and current_worker_identity and read_process_identity(current_worker_identifier)==current_worker_identity:
                    os.kill(current_worker_identifier,signal.SIGKILL)
                current_unrelated_process.terminate()
                current_unrelated_process.wait(timeout=5)

    def test_live_writer_cancellation_releases_queue_and_preserves_document(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_documents_root=current_root_path/'docs'
            (current_documents_root/'ideas').mkdir(parents=True)
            current_document_path=current_documents_root/'ideas/original.md'
            current_document_path.write_text('원문 보존')
            current_workspace_path=current_root_path/'workspace.yaml'
            save_yaml_document(current_workspace_path,{'schema_version':1,'document_root':str(current_documents_root),'state_root':str(current_root_path/'state'),'write_roots':['ideas'],'excluded_roots':[],'protected_paths':[],'catalog_path':None})
            current_job_identifier='20261118-120000-12345678'
            current_job_root=current_root_path/'state/jobs'/current_job_identifier
            current_job_root.mkdir(parents=True)
            save_yaml_document(current_job_root/'status.yaml',{'id':current_job_identifier,'stage':'reasoning'})
            save_yaml_document(current_job_root/'request.yaml',{'mode':'write','prompt':'시험'})
            (current_job_root/'status.json').write_text(json.dumps({'status':'queued'}))
            current_worker_path=current_root_path/'worker.py'
            current_worker_path.write_text("import os,pathlib,sys,time\np=pathlib.Path(sys.argv[1]);(p/'worker-pid').write_text(str(os.getpid()))\nwhile not (p/'release').exists():time.sleep(.05)\n")
            (current_job_root/'gpu-command.json').write_text(json.dumps({'service':'writer-agent','command':[sys.executable,str(current_worker_path),str(current_job_root)]}))
            current_queue_path=current_root_path/'queue'
            current_context=multiprocessing.get_context('fork')
            current_queue_process=current_context.Process(target=execute_isolated_queue_job,args=(str(current_queue_path),str(current_job_root)))
            try:
                current_queue_process.start()
                current_deadline_value=time.monotonic()+8
                while not (current_job_root/'worker-pid').exists():
                    if time.monotonic()>current_deadline_value:self.fail('격리 작업자 시작 실패')
                    time.sleep(.05)
                current_worker_pid=int((current_job_root/'worker-pid').read_text())
                (current_job_root/'queue-process.json').write_text(json.dumps({'pid':current_queue_process.pid,'identity':read_process_identity(current_queue_process.pid)}))
                current_manager_value=WriterAgentManager(current_workspace_path)
                current_cancel_record=current_manager_value.request_writer_cancellation(current_job_identifier)
                self.assertTrue(current_cancel_record['cancel_requested'])
                current_queue_process.join(timeout=8)
                self.assertEqual(current_queue_process.exitcode,0)
                self.assertEqual(json.loads((current_job_root/'status.json').read_text())['status'],'cancelled')
                self.assertEqual(current_manager_value.read_writer_detail(current_job_identifier)['status']['stage'],'interrupted')
                self.assertIsNone(read_process_identity(current_worker_pid))
                self.assertEqual(list((current_queue_path/'active').glob('*.json')),[])
                self.assertEqual(current_document_path.read_text(),'원문 보존')
            finally:
                (current_job_root/'release').touch()
                (current_job_root/'cancel.request').touch()
                if current_queue_process.pid is not None:
                    current_queue_process.join(timeout=4)
                    if current_queue_process.is_alive():
                        current_queue_process.terminate()
                        current_queue_process.join(timeout=4)
