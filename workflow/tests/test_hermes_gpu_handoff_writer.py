"""작가 작업공간과 GPU 예약의 관측만 격리 검증한다."""
from contextlib import nullcontext
import json
import hashlib
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch, Mock

from generators.writer_agent.documents import save_yaml_document
from workflow.domains.hermes_agent.gpu_handoff_writer import inspect_writer_workspace, inspect_writer_target_release

JOB = '20261122-130000-abcdef12'


class WriterHandoffObservationTests(unittest.TestCase):
    def test_writer_proposal_commands_require_session_and_explicit_confirmation(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        from workflow.common.management_gateway import resolve_management_command
        session='a'*32;job='2026-11-18_00-00-00-12345678';identifier='writer_'+hashlib.sha256(json.dumps([session,job],separators=(',',':')).encode()).hexdigest();bound={'request':{'mode':'write','prompt':'test'},'workspace_fingerprint':'c'*64}
        with TemporaryDirectory() as directory:
            root=Path(directory);sessions=HermesSessionStore(root/'sessions');sessions.create_session_record(session)
            sessions.append_session_request(session,'request_12345678','test');sessions.attach_session_job(session,'request_12345678',job)
            manager=HermesServiceManager(hermes_storage_root=root/'jobs',hermes_session_root=root/'sessions')
            request={'session_id':session,'request_id':identifier,'job_id':job,'snapshot':'d'*64,'offset':0,'request':bound,'confirmed':True}
            answer='HERMES_WRITER_PROPOSAL\n{"mode":"write","prompt":"test"}\nEND_HERMES_WRITER_PROPOSAL'
            page={'messages':[{'job_id':job,'session_job_unique':True,'job':{'status':{'status':'completed'},'final_response':answer,'final_response_truncated':False}}]}
            with patch.object(manager,'read_hermes_session_view_locked',return_value=page),patch('workflow.domains.hermes_agent.gpu_handoff_writer.submit_bound_writer_once',return_value={'state':'accepted','job_id':JOB}) as submit:
                self.assertEqual(manager.execute_hermes_command('hermes-writer-proposal-submit',request)['job_id'],JOB)
                submit.assert_called_once()
                with self.assertRaises(ValueError):manager.execute_hermes_command('hermes-writer-proposal-submit',{**request,'confirmed':False})
                with self.assertRaises(ValueError):manager.execute_hermes_command('hermes-writer-proposal-submit',{**request,'request_id':'bad'})
                with self.assertRaisesRegex(ValueError,'작업 종류'):
                    manager.execute_hermes_command('hermes-writer-proposal-submit',{**request,'request':{**bound,'request':{'mode':'deduplicate','prompt':'test'}}})
            self.assertEqual(resolve_management_command('hermes-agent','hermes-writer-proposal-submit',request)[0],'POST')

    def test_writer_proposal_handoff_and_direct_race_has_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from workflow.domains.hermes_agent.gpu_handoff_writer import submit_bound_writer_once,ensure_writer_target_unclaimed
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore,_canonical_input
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        with TemporaryDirectory() as directory:
            root=Path(directory);handoffs=GpuHandoffStore(root/'handoffs');receipts=HermesDelegationStore(root/'receipts')
            payload={'request':{'mode':'write','prompt':'test'},'workspace_fingerprint':'b'*64}
            session='a'*32;request_id='writer_test_123';barrier=Barrier(2);submit=Mock(return_value={'id':JOB})
            def direct():
                barrier.wait()
                try:return submit_bound_writer_once(request_id,session,payload,handoff_store=handoffs,delegation_store=receipts,submit=submit,validate=Mock())['state']
                except ValueError:return 'blocked'
            def handoff():
                barrier.wait()
                try:return handoffs.approve(request_id,session,'writer-agent',hashlib.sha256(_canonical_input(payload)).hexdigest(),target_request=payload,resident_id='resident_123',confirmed=True,precommit_check=lambda:ensure_writer_target_unclaimed(request_id,receipts))['state']
                except ValueError:return 'blocked'
            with ThreadPoolExecutor(max_workers=2) as pool:
                a=pool.submit(direct);b=pool.submit(handoff);states={a.result(),b.result()}
            self.assertIn(states,({'accepted','blocked'},{'approved','blocked'}))
            self.assertLessEqual(submit.call_count,1)

    def test_direct_writer_receipt_blocks_later_handoff_and_duplicate_submit(self):
        from workflow.domains.hermes_agent.gpu_handoff_writer import submit_bound_writer_once,ensure_writer_target_unclaimed
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        with TemporaryDirectory() as directory:
            root=Path(directory);handoffs=GpuHandoffStore(root/'handoffs');receipts=HermesDelegationStore(root/'receipts')
            request_id='writer_test_123';session='a'*32
            payload={'request':{'mode':'write','prompt':'test'},'workspace_fingerprint':'b'*64}
            submit=Mock(return_value={'id':JOB});validate=Mock()
            first=submit_bound_writer_once(request_id,session,payload,handoff_store=handoffs,delegation_store=receipts,submit=submit,validate=validate)
            second=submit_bound_writer_once(request_id,session,payload,handoff_store=handoffs,delegation_store=receipts,submit=submit,validate=validate)
            self.assertEqual(first['state'],'accepted');self.assertTrue(second['duplicate']);submit.assert_called_once()
            with handoffs.hold_delegation_storage_lock(),self.assertRaisesRegex(ValueError,'접수 기록'):
                ensure_writer_target_unclaimed(request_id,receipts)
            with self.assertRaises(ValueError):
                submit_bound_writer_once(request_id,session,{**payload,'request':{'mode':'write','prompt':'changed'}},handoff_store=handoffs,delegation_store=receipts,submit=submit,validate=validate)
            submit.assert_called_once()

    def test_open_handoff_blocks_direct_writer_submission(self):
        from workflow.domains.hermes_agent.gpu_handoff_writer import submit_bound_writer_once
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore,_canonical_input
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        with TemporaryDirectory() as directory:
            root=Path(directory);handoffs=GpuHandoffStore(root/'handoffs');receipts=HermesDelegationStore(root/'receipts')
            payload={'request':{'mode':'write','prompt':'test'},'workspace_fingerprint':'b'*64}
            session='a'*32;request_id='writer_test_123'
            handoffs.approve(request_id,session,'writer-agent',hashlib.sha256(_canonical_input(payload)).hexdigest(),target_request=payload,resident_id='resident_123',confirmed=True)
            submit=Mock(return_value={'id':JOB})
            with self.assertRaisesRegex(ValueError,'양도'):
                submit_bound_writer_once(request_id,session,payload,handoff_store=handoffs,delegation_store=receipts,submit=submit,validate=Mock())
            submit.assert_not_called()

    def test_workspace_uses_running_writer_service_config(self):
        with TemporaryDirectory() as temporary:
            root=Path(temporary); documents=root/'documents'; state=root/'state'
            documents.mkdir(); state.mkdir(); config=root/'custom.yaml'
            save_yaml_document(config,{'schema_version':1,'document_root':str(documents),'state_root':str(state),
                                       'write_roots':['drafts'],'excluded_roots':[],'protected_paths':[],'catalog_path':None})
            with patch('workflow.domains.hermes_agent.writer_operations.call_hermes_writer_service',return_value={'configured':True,'config_path':str(config)}) as service:
                result=inspect_writer_workspace()
                self.assertEqual(result['document_root'],str(documents))
                self.assertEqual(result['state_root'],str(state))
                service.assert_called_once_with('writer-state',{})
            with patch('workflow.domains.hermes_agent.writer_operations.call_hermes_writer_service',return_value={'configured':True,'config_path':'relative.yaml'}):
                with self.assertRaises(ValueError): inspect_writer_workspace()

    def test_status_exposes_writer_summary_without_workspace_payload(self):
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
        from workflow.domains.hermes_agent.service import HermesServiceManager
        payload={'request':{'mode':'write','prompt':'초안'},'workspace_fingerprint':'a'*64}
        digest=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with TemporaryDirectory() as temporary:
            root=Path(temporary);store=GpuHandoffStore(root/'handoffs')
            store.approve('request_123','a'*32,'writer-agent',digest,target_request=payload,resident_id='resident_123',confirmed=True)
            manager=HermesServiceManager(root/'jobs',root/'sessions')
            with patch('workflow.domains.hermes_agent.gpu_handoff_store.GpuHandoffStore',return_value=store), \
                 patch('workflow.domains.hermes_agent.session_store.HermesSessionStore.read_session_record',return_value={'id':'a'*32}):
                result=manager.execute_hermes_command('hermes-gpu-handoff-status',{'session_id':'a'*32,'request_id':'request_123'})
            self.assertNotIn('target_request',result)
            self.assertEqual(result['target_summary']['prompt'],'초안')
            self.assertEqual(result['target_summary']['mode'],'write')

    def test_writer_review_rejects_changed_workspace_before_submission(self):
        from workflow.domains.hermes_agent.gpu_handoff_writer import validate_bound_writer_request
        request={'request':{'mode':'write','prompt':'초안'},'workspace_fingerprint':'a'*64}
        with patch('workflow.domains.hermes_agent.gpu_handoff_writer.inspect_writer_workspace',return_value={'fingerprint':'b'*64}), \
             patch('workflow.domains.hermes_agent.writer_operations.validate_hermes_writer_request') as validate:
            with self.assertRaisesRegex(ValueError,'작업공간이 변경'):
                validate_bound_writer_request(request)
            validate.assert_not_called()

    def test_writer_receipt_tracks_existing_review_without_applying_document(self):
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        from workflow.domains.hermes_agent.gpu_handoff_controller import advance_gpu_handoff
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
        from workflow.domains.hermes_agent.gpu_handoff_writer import WriterHandoffAdapter
        payload={'request':{'mode':'write','prompt':'새 초안'},'workspace_fingerprint':'a'*64}
        digest=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with TemporaryDirectory() as temporary:
            store=GpuHandoffStore(Path(temporary)/'handoffs');receipts=HermesDelegationStore(Path(temporary)/'receipts')
            store.approve('request_123','a'*32,'writer-agent',digest,target_request=payload,resident_id='resident_123',confirmed=True)
            calls=[]
            def writer(command,request):
                calls.append((command,request))
                return {'id':JOB}
            def gateway(command,request):
                if command=='hermes-writer-status':
                    return {'receipt':receipts.read_service_delegation(request['request_id'],'writer-agent'),'job':{'stage':'review'}}
                raise AssertionError(command)
            adapter=WriterHandoffAdapter(gateway=gateway,delegation_store=receipts)
            with patch.object(adapter,'ensure_release_requested'),patch.object(adapter,'inspect_release',return_value='released'), \
                 patch('workflow.domains.hermes_agent.gpu_handoff_writer.validate_bound_writer_request'), \
                 patch('workflow.domains.hermes_agent.writer_operations.call_hermes_writer_service',side_effect=writer), \
                 patch('workflow.domains.hermes_agent.gpu_handoff_writer.inspect_writer_target_release',return_value=True):
                advance_gpu_handoff(store,'request_123',adapter)
                row=advance_gpu_handoff(store,'request_123',adapter)
                self.assertEqual(row['job_id'],JOB)
                self.assertEqual(advance_gpu_handoff(store,'request_123',adapter)['state'],'reload_queued')
            self.assertEqual(calls,[('writer-submit-bound',payload)])

    def test_writer_bound_submission_freezes_reviewed_workspace(self):
        from generators.writer_agent.management import WriterAgentManager
        from generators.writer_agent.documents import load_workspace_config
        with TemporaryDirectory() as temporary:
            root=Path(temporary);documents=root/'documents';state=root/'state';documents.mkdir();state.mkdir()
            config=root/'workspace.yaml'
            data={'schema_version':1,'document_root':str(documents),'state_root':str(state),
                  'write_roots':['drafts'],'excluded_roots':[],'protected_paths':[],'catalog_path':None}
            save_yaml_document(config,data)
            fingerprint=inspect_writer_workspace(config)['fingerprint']
            manager=WriterAgentManager(config)
            observed=[]
            def launch(command,directory,service,**kwargs):
                frozen=Path(command[command.index('--config')+1])
                self.assertEqual(load_workspace_config(frozen)['write_roots'],['drafts'])
                save_yaml_document(config,{**data,'write_roots':['other']})
                observed.append(load_workspace_config(frozen)['write_roots'])
                return Mock(pid=os.getpid())
            with patch.object(manager,'read_workspace_state',return_value={'active_job':None}), \
                 patch('generators.writer_agent.management.prepare.RUNTIME_PYTHON_PATH',Path(sys.executable)), \
                 patch('generators.writer_agent.management.inspect_detached_preparation',return_value=None), \
                 patch('generators.writer_agent.management.launch_gpu_process',side_effect=launch), \
                 patch('generators.writer_agent.management.threading.Thread'):
                result=manager.launch_writer_process({'mode':'write','prompt':'새 문서 제안'},expected_workspace_fingerprint=fingerprint)
                self.assertTrue(result['id'])
                self.assertEqual(observed,[['drafts']])
                with self.assertRaisesRegex(ValueError,'작업공간이 변경'):
                    manager.launch_writer_process({'mode':'write','prompt':'새 문서 제안'},expected_workspace_fingerprint=fingerprint)

    def test_workspace_change_and_active_reservation_prevent_reload(self):
        with TemporaryDirectory() as temporary:
            root=Path(temporary);documents=root/'documents';state=root/'state';queue=root/'queue'
            documents.mkdir();state.mkdir();queue.mkdir()
            config=root/'workspace.yaml'
            data={'schema_version':1,'document_root':str(documents),'state_root':str(state),
                  'write_roots':['drafts'],'excluded_roots':[],'protected_paths':[],'catalog_path':None}
            save_yaml_document(config,data)
            fingerprint=inspect_writer_workspace(config)['fingerprint']
            job=state/'jobs'/JOB;job.mkdir(parents=True)
            (job/'status.json').write_text(json.dumps({'status':'completed'}))
            save_yaml_document(job/'status.yaml',{'id':JOB,'stage':'completed'})
            reservation=queue/'reservation.json'
            reservation.write_text(json.dumps({'path':str(job.resolve()),'service':'writer-agent'}))
            with patch('workflow.domains.hermes_agent.gpu_handoff_writer._gpu_idle_fresh',return_value=True), \
                 patch('workflow.domains.hermes_agent.gpu_handoff_writer.hold_writer_reservation_queue_lock',side_effect=lambda:nullcontext(queue)):
                self.assertIs(inspect_writer_target_release(JOB,'completed',fingerprint,config_path=config),False)
                reservation.unlink()
                self.assertIs(inspect_writer_target_release(JOB,'completed',fingerprint,config_path=config),True)
                self.assertIsNone(inspect_writer_target_release(JOB,'failed',fingerprint,config_path=config))
                data['write_roots']=['other'];save_yaml_document(config,data)
                self.assertIsNone(inspect_writer_target_release(JOB,'completed',fingerprint,config_path=config))

    def test_writer_config_path_change_during_observation_prevents_reload(self):
        with TemporaryDirectory() as temporary:
            root=Path(temporary); documents=root/'documents'; state=root/'state'; queue=root/'queue'
            documents.mkdir(); state.mkdir(); queue.mkdir(); config=root/'workspace.yaml'
            save_yaml_document(config,{'schema_version':1,'document_root':str(documents),'state_root':str(state),
                                       'write_roots':['drafts'],'excluded_roots':[],'protected_paths':[],'catalog_path':None})
            fingerprint=inspect_writer_workspace(config)['fingerprint']
            job=state/'jobs'/JOB;job.mkdir(parents=True)
            (job/'status.json').write_text(json.dumps({'status':'completed'}))
            save_yaml_document(job/'status.yaml',{'id':JOB,'stage':'completed'})
            with patch('workflow.domains.hermes_agent.gpu_handoff_writer._gpu_idle_fresh',return_value=True), \
                 patch('workflow.domains.hermes_agent.gpu_handoff_writer.hold_writer_reservation_queue_lock',side_effect=lambda:nullcontext(queue)), \
                 patch('workflow.domains.hermes_agent.gpu_handoff_writer.current_writer_config_path',side_effect=[config,root/'other.yaml']):
                self.assertIsNone(inspect_writer_target_release(JOB,'completed',fingerprint))

    def test_workspace_observation_does_not_create_missing_state_root(self):
        with TemporaryDirectory() as temporary:
            root=Path(temporary);documents=root/'documents';documents.mkdir();config=root/'workspace.yaml'
            save_yaml_document(config,{'schema_version':1,'document_root':str(documents),'state_root':str(root/'missing'),
                                       'write_roots':['drafts'],'excluded_roots':[],'protected_paths':[],'catalog_path':None})
            with self.assertRaises(ValueError):inspect_writer_workspace(config)
            self.assertFalse((root/'missing').exists())


if __name__ == '__main__': unittest.main()
