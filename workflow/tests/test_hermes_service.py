import json
import base64
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

from workflow.domains.hermes_agent.service import HermesServiceManager
from workflow.common.management_gateway import resolve_management_command, identify_management_command


class HermesServiceTests(unittest.TestCase):
    @patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('workflow.domains.hermes_agent.service.launch_gpu_process')
    def test_session_explicit_model_persisted_and_retry_checked(self, launch, ready):
        session = 'a' * 32
        self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id':session})
        request = {'session_id':session, 'request_id':'model-request-001', 'prompt':'코드 수정', 'model_profile':'qwen3.8-27b'}
        result = self.hermes_service_manager.execute_hermes_command('hermes-session-submit', request)
        job = self.hermes_service_manager.hermes_storage_root / result['job_id']
        self.assertEqual(json.loads((job / 'request.json').read_text())['model_profile'], 'qwen3.8-27b')
        self.assertTrue(self.hermes_service_manager.execute_hermes_command('hermes-session-submit', request)['duplicate'])
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-session-submit', {**request, 'model_profile':'qwen3.5-4b'})
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-session-submit', {**request, 'request_id':'model-request-002', 'model_profile':'invalid'})
        (job / 'status.json').write_text('{"status":"completed"}')
        (job / 'hermes-events.jsonl').write_text(json.dumps({'type':'result', 'text':'완료'}, ensure_ascii=False))
        second = self.hermes_service_manager.execute_hermes_command('hermes-session-submit', {**request, 'request_id':'model-request-003', 'prompt':'안녕', 'model_profile':'qwen3.8-27b'})
        second_job = self.hermes_service_manager.hermes_storage_root / second['job_id']
        self.assertEqual(json.loads((second_job / 'request.json').read_text())['model_profile'], 'qwen3.8-27b')

    def test_flux_source_command_requires_exact_payload(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_job_record={'status':'queued','image':None,'result_status':'not_ready'}
        with patch('workflow.domains.hermes_agent.flux_profile_operations.read_hermes_flux_source_job',return_value=current_job_record) as current_reader_mock:
            current_result_value=self.hermes_service_manager.execute_hermes_command('hermes-flux-source-status',{'service':'flux-building','job_id':current_job_identifier})
            self.assertEqual(current_result_value,{'service':'flux-building','job_id':current_job_identifier,'job':current_job_record})
            current_reader_mock.assert_called_once_with('flux-building',current_job_identifier)
            with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-flux-source-status',{'service':'flux-building','job_id':current_job_identifier,'extra':True})

    def test_kimodo_resume_preflight_blocks_preparation_without_receipt(self):
        from workflow.domains.hermes_agent import kimodo_resume_operations
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_review_record={'service':'kimodo','job_id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'a'*64,'record_fingerprint':'b'*64,'keyframe_fingerprint':None}
        for current_availability_value,current_expected_reason in (('download_running','download_running'),('unknown','unavailable')):
            with self.subTest(current_availability_value=current_availability_value),tempfile.TemporaryDirectory() as current_directory_name:
                current_review_record['resume_availability']=current_availability_value
                with patch.object(kimodo_resume_operations,'KIMODO_RESUME_RECEIPT_ROOT',Path(current_directory_name)/'receipts'),patch.object(kimodo_resume_operations,'preview_hermes_kimodo_resume',return_value=current_review_record),patch.object(kimodo_resume_operations,'execute_remote_management_command') as current_gateway_mock:
                    current_result_value=kimodo_resume_operations.submit_hermes_kimodo_resume_once('request_123',current_job_identifier,'a'*64)
                    self.assertEqual((current_result_value['state'],current_result_value['reason']),('blocked',current_expected_reason))
                    self.assertEqual(kimodo_resume_operations.read_hermes_kimodo_resume_receipt('request_123')['state'],'not_found')
                    current_gateway_mock.assert_not_called()

    def test_kimodo_resume_idempotence_and_changed_review_without_gpu(self):
        from workflow.domains.hermes_agent import kimodo_resume_operations
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_review_record={'service':'kimodo','job_id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'a'*64,'record_fingerprint':'b'*64,'keyframe_fingerprint':'c'*64,'resume_availability':'available'}
        current_receipt_root=Path(self.hermes_temporary_root.name)/'kimodo-receipts'
        with patch.object(kimodo_resume_operations,'KIMODO_RESUME_RECEIPT_ROOT',current_receipt_root),patch.object(kimodo_resume_operations,'preview_hermes_kimodo_resume',return_value=current_review_record),patch.object(kimodo_resume_operations,'execute_remote_management_command',return_value={'id':current_job_identifier,'status':'queued'}) as current_submit_mock:
            current_result_value=kimodo_resume_operations.submit_hermes_kimodo_resume_once('request_123',current_job_identifier,'a'*64)
            self.assertEqual(current_result_value['state'],'accepted')
            current_submit_mock.assert_called_once_with('kimodo','resume-reviewed',{'id':current_job_identifier,'expected_resume_fingerprint':'b'*64,'keyframe_fingerprint':'c'*64})
            self.assertTrue(kimodo_resume_operations.submit_hermes_kimodo_resume_once('request_123',current_job_identifier,'a'*64)['duplicate'])
            with self.assertRaises(ValueError):kimodo_resume_operations.submit_hermes_kimodo_resume_once('request_456',current_job_identifier,'a'*64)
            current_submit_mock.assert_called_once()
            current_blocked_value=kimodo_resume_operations.submit_hermes_kimodo_resume_once('request_789',current_job_identifier,'d'*64)
            self.assertEqual((current_blocked_value['state'],current_blocked_value['reason']),('blocked','fingerprint_changed'))
            self.assertEqual(kimodo_resume_operations.read_hermes_kimodo_resume_receipt('request_789')['state'],'not_found')

    def test_kimodo_resume_lost_response_preserves_unknown_receipt(self):
        from workflow.domains.hermes_agent import kimodo_resume_operations
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_review_record={'service':'kimodo','job_id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'a'*64,'record_fingerprint':'b'*64,'keyframe_fingerprint':None,'resume_availability':'available'}
        with patch.object(kimodo_resume_operations,'KIMODO_RESUME_RECEIPT_ROOT',Path(self.hermes_temporary_root.name)/'kimodo-receipts'),patch.object(kimodo_resume_operations,'preview_hermes_kimodo_resume',return_value=current_review_record),patch.object(kimodo_resume_operations,'execute_remote_management_command',side_effect=OSError('lost')) as current_submit_mock:
            with self.assertRaises(OSError):kimodo_resume_operations.submit_hermes_kimodo_resume_once('request_123',current_job_identifier,'a'*64)
            self.assertEqual(kimodo_resume_operations.read_hermes_kimodo_resume_receipt('request_123')['state'],'unknown')
            self.assertEqual(kimodo_resume_operations.submit_hermes_kimodo_resume_once('request_123',current_job_identifier,'a'*64)['state'],'unknown')
            current_submit_mock.assert_called_once()

    def test_oversized_resume_receipt_blocks_other_dispatch(self):
        from workflow.domains.hermes_agent.delegation_store import HERMES_DELEGATION_RECORD_MAXIMUM_BYTES
        from workflow.domains.hermes_agent.resume_receipt_store import submit_resume_receipt_once
        from workflow.domains.hermes_agent.kimodo_resume_operations import validate_kimodo_resume_target
        current_receipt_root=Path(self.hermes_temporary_root.name)/'oversized-receipts'
        current_receipt_root.mkdir()
        (current_receipt_root/'request_prior.json').write_bytes(b'x'*(HERMES_DELEGATION_RECORD_MAXIMUM_BYTES+1))
        current_calls_list=[]
        with self.assertRaises(ValueError):
            submit_resume_receipt_once(current_receipt_root,'request_new','kimodo','2026-11-20_00-00-00-12345678','a'*64,validate_kimodo_resume_target,lambda *args:current_calls_list.append(args))
        self.assertEqual(current_calls_list,[])

    def test_resume_unknown_blocks_changed_fingerprint_for_same_job(self):
        from workflow.domains.hermes_agent.resume_receipt_store import submit_resume_receipt_once
        from workflow.domains.hermes_agent.kimodo_resume_operations import validate_kimodo_resume_target
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_other_identifier='2026-11-20_00-00-01-87654321'
        current_receipt_root=Path(self.hermes_temporary_root.name)/'unknown-receipts'
        def lose_resume_response(current_service_name,current_job_value,current_fingerprint_value):
            raise OSError('response lost')
        with self.assertRaises(OSError):
            submit_resume_receipt_once(current_receipt_root,'request_first','kimodo',current_job_identifier,'a'*64,validate_kimodo_resume_target,lose_resume_response)
        with patch('workflow.domains.hermes_agent.resume_receipt_store.write_record_atomically') as current_write_mock:
            with self.assertRaisesRegex(ValueError,r'결과가 확인되지 않은.*접수 ID: request_first'):
                submit_resume_receipt_once(current_receipt_root,'request_changed','kimodo',current_job_identifier,'b'*64,validate_kimodo_resume_target,lose_resume_response)
            current_write_mock.assert_not_called()
        def accept_resume_response(current_service_name,current_job_value,current_fingerprint_value):
            return {'id':current_job_value,'status':'queued'}
        current_result_value=submit_resume_receipt_once(current_receipt_root,'request_other','kimodo',current_other_identifier,'b'*64,validate_kimodo_resume_target,accept_resume_response)
        self.assertEqual(current_result_value['state'],'accepted')
        current_result_value=submit_resume_receipt_once(current_receipt_root,'request_later','kimodo',current_other_identifier,'c'*64,validate_kimodo_resume_target,accept_resume_response)
        self.assertEqual(current_result_value['state'],'accepted')

    def test_flux_resume_proposal_requires_complete_strict_answer(self):
        import json
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_flux_resume_proposal
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_proposal_value={'service':'flux-character','job_id':current_job_identifier,'expected_resume_fingerprint':'a'*64}
        current_answer_text='HERMES_FLUX_RESUME_PROPOSAL\n'+json.dumps(current_proposal_value)+'\nEND_HERMES_FLUX_RESUME_PROPOSAL'
        self.assertEqual(parse_hermes_flux_resume_proposal(current_answer_text),current_proposal_value)
        for current_invalid_text in (current_answer_text+'\n'+current_answer_text,current_answer_text.replace('flux-character','kimodo'),current_answer_text.replace('a'*64,'bad'),current_answer_text.replace('"service":', '"service":"flux-image","service":')):
            with self.subTest(answer=current_invalid_text),self.assertRaises(ValueError):parse_hermes_flux_resume_proposal(current_invalid_text)
        current_job_record={'status':{'status':'completed'},'final_response_truncated':False,'final_response':current_answer_text}
        with patch.object(self.hermes_service_manager,'resolve_hermes_job_path',return_value=Path('/unused')),patch.object(self.hermes_service_manager,'read_hermes_job_record',return_value=current_job_record):
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-flux-resume-proposal',{'id':current_job_identifier})['proposal'],current_proposal_value)
            current_job_record['final_response_truncated']=True
            with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-flux-resume-proposal',{'id':current_job_identifier})

    def test_flux_resume_service_dispatch_requires_exact_fields(self):
        from workflow.domains.hermes_agent import flux_resume_operations
        current_payload_value={'request_id':'flux_request_123','service':'flux-character','job_id':'2026-11-20_00-00-00-12345678','expected_resume_fingerprint':'a'*64}
        with patch.object(flux_resume_operations,'submit_hermes_flux_resume_once',return_value={'state':'accepted'}) as current_submit_mock:
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-flux-resume-submit',current_payload_value),{'state':'accepted'})
            current_submit_mock.assert_called_once_with(current_payload_value['request_id'],current_payload_value['service'],current_payload_value['job_id'],current_payload_value['expected_resume_fingerprint'])
            with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-flux-resume-submit',{**current_payload_value,'extra':True})
        with patch.object(flux_resume_operations,'read_hermes_flux_resume_receipt',return_value={'state':'unknown'}) as current_read_mock:
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-flux-resume-receipt',{'request_id':'flux_request_123'}),{'state':'unknown'})
            current_read_mock.assert_called_once_with('flux_request_123')

    def test_flux_resume_receipt_preflight_deduplicates_and_preserves_unknown(self):
        from workflow.domains.hermes_agent import flux_resume_operations
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_preview_value={'service':'flux-character','job_id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'a'*64,'resume_availability':'available'}
        with patch.object(flux_resume_operations,'FLUX_RESUME_RECEIPT_ROOT',Path(self.hermes_temporary_root.name)/'flux-receipts'),patch.object(flux_resume_operations,'preview_hermes_flux_resume',return_value=current_preview_value) as current_preview_mock,patch.object(flux_resume_operations,'execute_remote_management_command',return_value={'id':current_job_identifier,'status':'queued'}) as current_gateway_mock:
            for current_availability_value in ('download_running','unknown'):
                current_preview_value['resume_availability']=current_availability_value
                current_result_value=flux_resume_operations.submit_hermes_flux_resume_once('flux_request_123','flux-character',current_job_identifier,'a'*64)
                self.assertEqual(current_result_value['state'],'blocked')
                current_gateway_mock.assert_not_called()
            current_preview_value['resume_availability']='available'
            current_result_value=flux_resume_operations.submit_hermes_flux_resume_once('flux_request_123','flux-character',current_job_identifier,'a'*64)
            self.assertEqual(current_result_value['state'],'accepted')
            self.assertTrue(flux_resume_operations.submit_hermes_flux_resume_once('flux_request_123','flux-character',current_job_identifier,'a'*64)['duplicate'])
            current_gateway_mock.assert_called_once_with('flux-character','resume-reviewed',{'id':current_job_identifier,'expected_resume_fingerprint':'a'*64})
            current_other_identifier='2026-11-20_00-00-01-87654321'
            current_preview_value['job_id']=current_other_identifier
            current_gateway_mock.side_effect=OSError('response lost')
            with self.assertRaises(OSError):flux_resume_operations.submit_hermes_flux_resume_once('flux_request_lost','flux-character',current_other_identifier,'a'*64)
            self.assertEqual(flux_resume_operations.read_hermes_flux_resume_receipt('flux_request_lost')['state'],'unknown')
            with self.assertRaisesRegex(ValueError,'기존 접수'):
                flux_resume_operations.submit_hermes_flux_resume_once('flux_request_again','flux-character',current_other_identifier,'b'*64)

    def test_flux_resume_preview_validates_identity_and_never_submits(self):
        from workflow.domains.hermes_agent import flux_resume_operations
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_response_value={'service':'flux-character','id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'a'*64}
        with patch.object(flux_resume_operations,'execute_remote_management_command',return_value=current_response_value) as current_gateway_mock:
            current_result_value=self.hermes_service_manager.execute_hermes_command('hermes-flux-resume-preview',{'service':'flux-character','job_id':current_job_identifier})
            self.assertEqual(current_result_value['expected_resume_fingerprint'],'a'*64)
            current_gateway_mock.assert_called_once_with('flux-character','resume-preview',{'id':current_job_identifier})
        for current_invalid_value in ({**current_response_value,'id':'other'},{**current_response_value,'service':'flux-image'},{**current_response_value,'expected_resume_fingerprint':'bad'}):
            with self.subTest(response=current_invalid_value),patch.object(flux_resume_operations,'execute_remote_management_command',return_value=current_invalid_value),self.assertRaises(ValueError):
                flux_resume_operations.preview_hermes_flux_resume('flux-character',current_job_identifier)
        with self.assertRaises(ValueError):flux_resume_operations.preview_hermes_flux_resume('kimodo',current_job_identifier)

    def test_isolated_cleanup_preview_returns_only_summary(self):
        import json
        import socket
        import threading
        from workflow.domains.hermes_agent import cleanup_preview_observer,management_bridge
        current_client_socket,current_server_socket=socket.socketpair()
        current_summary_record={'service':'dwpose','job_count':1,'blocked_count':0,'status_counts':{'failed':1},'can_reset':True,'excludes_blocked':False}
        with current_client_socket,patch.object(cleanup_preview_observer,'read_hermes_cleanup_preview',return_value=current_summary_record) as current_preview_mock:
            current_thread=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,),daemon=True)
            current_thread.start()
            current_client_socket.sendall(b'cleanup-preview dwpose\n')
            current_response_record=json.loads(current_client_socket.makefile('rb').readline())
            current_thread.join(timeout=3)
            self.assertFalse(current_thread.is_alive())
            self.assertEqual(current_response_record,current_summary_record)
            current_preview_mock.assert_called_once_with('dwpose')

    def test_isolated_video_resume_preview_rejects_extra_fields(self):
        import json
        import socket
        import threading
        from workflow.domains.hermes_agent import video_resume_operations,management_bridge
        current_job_identifier='2026-11-20_00-00-00-12345678'
        for current_extra_value in (False,True):
            current_request_value={'service':'wan22-vace','job_id':current_job_identifier}
            if current_extra_value:current_request_value['execute']=True
            current_client_socket,current_server_socket=socket.socketpair()
            with current_client_socket,patch.object(video_resume_operations,'preview_hermes_video_resume',return_value={'job_id':current_job_identifier}) as current_preview_mock:
                current_thread=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,),daemon=True)
                current_thread.start()
                current_client_socket.sendall(('video-resume-preview '+json.dumps(current_request_value)+'\n').encode())
                current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                current_thread.join(timeout=3)
                self.assertFalse(current_thread.is_alive())
                if current_extra_value:
                    self.assertIn('error',current_response_value)
                    current_preview_mock.assert_not_called()
                else:
                    self.assertEqual(current_response_value['job_id'],current_job_identifier)
                    current_preview_mock.assert_called_once_with('wan22-vace',current_job_identifier)

    def test_isolated_flux_resume_preview_rejects_extra_fields(self):
        import json
        import socket
        import threading
        from workflow.domains.hermes_agent import flux_resume_operations,management_bridge
        current_job_identifier='2026-11-20_00-00-00-12345678'
        for current_extra_value in (False,True):
            current_request_value={'service':'flux-character','job_id':current_job_identifier}
            if current_extra_value:current_request_value['execute']=True
            current_client_socket,current_server_socket=socket.socketpair()
            with current_client_socket,patch.object(flux_resume_operations,'preview_hermes_flux_resume',return_value={'job_id':current_job_identifier}) as current_preview_mock:
                current_thread=threading.Thread(target=management_bridge.handle_hermes_observer_connection,args=(current_server_socket,),daemon=True)
                current_thread.start()
                current_client_socket.sendall(('flux-resume-preview '+json.dumps(current_request_value)+'\n').encode())
                current_response_value=json.loads(current_client_socket.makefile('rb').readline())
                current_thread.join(timeout=3)
                self.assertFalse(current_thread.is_alive())
                if current_extra_value:
                    self.assertIn('error',current_response_value)
                    current_preview_mock.assert_not_called()
                else:
                    self.assertEqual(current_response_value['job_id'],current_job_identifier)
                    current_preview_mock.assert_called_once_with('flux-character',current_job_identifier)

    def test_kimodo_resume_preview_validates_response_and_never_submits(self):
        from workflow.domains.hermes_agent import kimodo_resume_operations
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_response_record={'id':current_job_identifier,'service':'kimodo','status':'failed','expected_resume_fingerprint':'a'*64,'keyframe_fingerprint':None}
        with patch.object(kimodo_resume_operations,'execute_remote_management_command',return_value=current_response_record) as current_gateway_mock:
            current_result_value=self.hermes_service_manager.execute_hermes_command('hermes-kimodo-resume-preview',{'job_id':current_job_identifier})
            self.assertEqual(current_result_value['job_id'],current_job_identifier)
            self.assertIn('다시 검증',current_result_value['note'])
            current_gateway_mock.assert_called_once_with('kimodo','resume-preview',{'id':current_job_identifier})
        for current_bad_record in ({**current_response_record,'id':'other'},{**current_response_record,'service':'image'},{**current_response_record,'expected_resume_fingerprint':'bad'}):
            with self.subTest(current_bad_record=current_bad_record),patch.object(kimodo_resume_operations,'execute_remote_management_command',return_value=current_bad_record),self.assertRaises(ValueError):
                kimodo_resume_operations.preview_hermes_kimodo_resume(current_job_identifier)

    def test_model_preparation_proposal_requires_complete_untruncated_job(self):
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_answer_text='HERMES_MODEL_PREPARATION_PROPOSAL\n{"service":"flux-image"}\nEND_HERMES_MODEL_PREPARATION_PROPOSAL'
        current_job_record={'status':{'status':'completed'},'final_response_truncated':False,'final_response':current_answer_text}
        with patch.object(self.hermes_service_manager,'resolve_hermes_job_path',return_value=Path('/unused')), patch.object(self.hermes_service_manager,'read_hermes_job_record',return_value=current_job_record):
            current_result_value=self.hermes_service_manager.execute_hermes_command('hermes-model-preparation-proposal',{'id':current_job_identifier})
            self.assertEqual(current_result_value,{'job_id':current_job_identifier,'proposal':{'service':'flux-image'}})
            for current_bad_record in ({**current_job_record,'status':{'status':'running'}},{**current_job_record,'final_response_truncated':True},{key:value for key,value in current_job_record.items() if key!='final_response_truncated'}):
                with self.subTest(current_bad_record=current_bad_record),patch.object(self.hermes_service_manager,'read_hermes_job_record',return_value=current_bad_record),self.assertRaises(ValueError):
                    self.hermes_service_manager.execute_hermes_command('hermes-model-preparation-proposal',{'id':current_job_identifier})

    def test_cancel_response_names_the_resolved_job(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_job_path=self.hermes_service_manager.hermes_storage_root/current_job_identifier
        current_job_path.mkdir(parents=True)
        with patch('workflow.domains.hermes_agent.service.cancel_gpu_generation',return_value={'status':'queued','cancel_requested':True,'id':'wrong'}) as current_cancel_mock:
            current_response_record=self.hermes_service_manager.execute_hermes_command('hermes-cancel',{'id':current_job_identifier})
            self.assertEqual(current_response_record,{'id':current_job_identifier,'status':'queued','cancel_requested':True})
            current_cancel_mock.assert_called_once_with(current_job_path)

    def setUp(self):
        from workflow.common import gpu_job_queue
        self.hermes_temporary_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.hermes_temporary_root.cleanup)
        isolated_queue_patch = patch.object(gpu_job_queue, 'GPU_QUEUE_DIRECTORY', Path(self.hermes_temporary_root.name) / 'gpu-queue')
        isolated_queue_patch.start()
        self.addCleanup(isolated_queue_patch.stop)
        self.hermes_service_manager = HermesServiceManager(Path(self.hermes_temporary_root.name) / 'jobs', Path(self.hermes_temporary_root.name) / 'sessions')

    def test_legacy_generator_status_adds_failure_guidance(self):
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        current_job_identifier='2026-11-20_20-00-00-12345678'
        for current_command_name,current_receipt_method in (('hermes-delegation-job-status','read_delegation_status'),('hermes-flux-delegation-status','read_service_delegation')):
            with self.subTest(command=current_command_name),patch.object(HermesDelegationStore,current_receipt_method,return_value={'state':'accepted','job_id':current_job_identifier}),patch('workflow.common.management_gateway.execute_management_command',return_value={'id':current_job_identifier,'status':'failed','exit_code':1}):
                current_result_record=self.hermes_service_manager.execute_hermes_command(current_command_name,{'request_id':'request_123'})
                self.assertEqual(current_result_record['job']['failure_code'],'unclassified_failure')
                self.assertIn('원 서비스',current_result_record['job']['failure_reason'])
                self.assertEqual(current_result_record['job']['exit_code'],1)

    def test_legacy_anchor_history_discovery_explains_limits(self):
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration
        current_service_record=next(current_record for current_record in list_management_service_registration()['services'] if current_record['service']=='character-animation')
        current_limit_records={current_record['command']:current_record['note'] for current_record in current_service_record['conditional_limitations']}
        for current_command_name in ('anchor-history','anchor-load'):
            self.assertIn(current_command_name,current_service_record['commands'])
            self.assertIn('직접 연결하지 않는다',current_limit_records[current_command_name])
        self.assertIn('전체 순회',current_limit_records['anchor-history'])
        self.assertIn('숨김 여부를 확인하지 않는다',current_limit_records['anchor-load'])

    def test_legacy_sprite_project_discovery_explains_separate_history(self):
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration
        current_service_record=next(current_record for current_record in list_management_service_registration()['services'] if current_record['service']=='character-animation')
        current_limit_records={current_record['command']:current_record['note'] for current_record in current_service_record['conditional_limitations']}
        for current_command_name in ('sprite-history','sprite-load'):
            self.assertIn(current_command_name,current_service_record['commands'])
            self.assertIn('직접 연결하지 않는다',current_limit_records[current_command_name])
        self.assertIn('전체 문서',current_limit_records['sprite-history'])
        self.assertIn('등록 에셋',current_limit_records['sprite-load'])

    def test_archived_generator_history_does_not_imply_generate_support(self):
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration
        current_records={item['service']:item for item in list_management_service_registration()['services']}
        for current_service_name in ('qwen-21','mannequin-generator','floor-tile'):
            current_record=current_records[current_service_name]
            self.assertIn('hermes-generator-source-history',current_record['hermes_links'])
            self.assertFalse(any(item.startswith('hermes-delegate-') for item in current_record['hermes_links']))
            self.assertTrue(any(item['command']=='generate' and item['reason'] for item in current_record['gateway_blocked']+current_record['known_service_blocked']))

    def test_content_database_catalog_distinguishes_ledger_sync_from_retired_restore(self):
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration
        current_asset_record=next(current_record for current_record in list_management_service_registration()['services'] if current_record['service']=='map-assets')
        current_block_records={current_record['command']:current_record['reason'] for current_record in current_asset_record['gateway_blocked']}
        current_limit_notes={current_record['command']:current_record['note'] for current_record in current_asset_record['conditional_limitations']}
        self.assertIn('폐기된 파일 스냅샷',current_block_records['database-restore'])
        self.assertIn('세대별 스냅샷을 만들지 않고',current_limit_notes['database-snapshot'])
        self.assertIn('Hermes는 직접 실행하지 않는다',current_limit_notes['database-sync'])
        self.assertIn('hermes-content-database-status',current_asset_record['hermes_links'])

    def test_asset_service_catalog_distinguishes_editing_from_lifecycle_operations(self):
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration
        current_asset=next(current_record for current_record in list_management_service_registration()['services'] if current_record['service']=='map-assets')
        current_notes={current_item['command']:current_item['note'] for current_item in current_asset['conditional_limitations']}
        for current_command in ('building-register','building-retire','asset-crop','asset-retire'):
            self.assertIn(current_command,current_notes)
            self.assertIn('Hermes',current_notes[current_command])
        self.assertIn('hermes-building-save',current_asset['hermes_links'])
        self.assertIn('hermes-billboard-save',current_asset['hermes_links'])

    def test_character_service_distinguishes_review_history_and_registered_assets(self):
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration
        current_service_record=next(current_record for current_record in list_management_service_registration()['services'] if current_record['service']=='character-animation')
        current_notes_by_command={current_note_record['command']:current_note_record['note'] for current_note_record in current_service_record['conditional_limitations']}
        self.assertIn('등록부',current_notes_by_command['anchor-save'])
        self.assertIn('별도',current_notes_by_command['sprite-save'])
        self.assertIn('CPU',current_notes_by_command['sheet-auto'])
        self.assertIn('임시',current_notes_by_command['sheet-export'])
        self.assertIn('잠금',current_notes_by_command['sheet-update'])
        self.assertIn('hermes-sprite-save',current_service_record['hermes_links'])

    def test_audio_model_download_and_gpu_preparation_are_distinguished(self):
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration
        current_services_by_name={current_service_record['service']:current_service_record for current_service_record in list_management_service_registration()['services']}
        for current_service_name in ('music-heartmula','sfx-dasheng-audiogen'):
            with self.subTest(current_service_name=current_service_name):
                current_notes_by_command={current_limit_record['command']:current_limit_record['note'] for current_limit_record in current_services_by_name[current_service_name]['conditional_limitations']}
                self.assertIn('GPU 대기열',current_notes_by_command['prepare'])
                self.assertIn('download-model',current_notes_by_command['prepare'])
                self.assertIn('GPU 준비',current_notes_by_command['download-model'])

    def test_model_download_observer_filters_fields_and_is_discoverable(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_model_download_status
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration
        current_record_value={'model':'org/model','status':'running','bytes':42,'total_bytes':100,'pid':123,'stage':'private','path':'/private'}
        with patch('workflow.common.management_gateway.execute_management_command',return_value={'records':[current_record_value],'unavailable_count':0}) as current_gateway_mock:
            current_result_value=read_hermes_model_download_status()
            self.assertEqual(current_result_value['records'],[{'model':'org/model','status':'running','bytes':42,'total_bytes':100}])
            self.assertNotIn('/private',str(current_result_value))
            current_gateway_mock.assert_called_once_with('model-downloads','download-observe',{},unittest.mock.ANY)
        current_service_record=next(current_record for current_record in list_management_service_registration()['services'] if current_record['service']=='model-downloads')
        self.assertIn('hermes-model-download-status',current_service_record['hermes_links'])

    def test_service_catalog_discloses_kimodo_keyframe_write_boundaries(self):
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration
        current_kimodo_record=next(current_record for current_record in list_management_service_registration()['services'] if current_record['service']=='kimodo')
        current_limit_notes={current_item['command']:current_item['note'] for current_item in current_kimodo_record['conditional_limitations']}
        for current_command_name in ('keyframe-replace','keyframe-retire'):
            self.assertIn('Hermes는',current_limit_notes[current_command_name])
            self.assertIn('연결하지 않는다',current_limit_notes[current_command_name])
        self.assertIn('직접 실행하지 않는다',current_limit_notes['keyframe-save'])
        self.assertIn('별도 저장과 접수 확인',current_limit_notes['keyframe-save'])
        self.assertIn('중복',current_limit_notes['keyframe-save'])
        self.assertIn('.replaced',current_limit_notes['keyframe-replace'])
        self.assertIn('.retired',current_limit_notes['keyframe-retire'])
        self.assertIn('hermes-kimodo-keyframes',current_kimodo_record['hermes_links'])
        self.assertIn('hermes-kimodo-keyframe-preview',current_kimodo_record['hermes_links'])

    def test_service_catalog_discloses_kimodo_build_gpu_and_retry_limits(self):
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration
        current_records=list_management_service_registration()['services']
        current_kimodo=next(current_record for current_record in current_records if current_record['service']=='kimodo')
        current_notes={current_item['command']:current_item['note'] for current_item in current_kimodo['conditional_limitations']}
        self.assertIn('GPU 대기열',current_notes['migraphx-build-status'])
        self.assertIn('migraphx-build-observe',current_notes['migraphx-build-status'])
        self.assertIn('중복 방지',current_notes['migraphx-build'])
        self.assertIn('Hermes는 빌드 실행을 연결하지 않는다',current_notes['migraphx-build'])

    @patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('workflow.domains.hermes_agent.service.launch_gpu_process')
    def test_coding_context_retries_with_original_user_messages(self, launch, ready):
        session = 'e' * 32
        self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': session})
        for index, prompt in enumerate(('요구', '정정', '추가')):
            result = self.hermes_service_manager.execute_hermes_command('hermes-session-submit', {
                'session_id': session, 'request_id': f'context-req-{index}', 'prompt': prompt})
            job = self.hermes_service_manager.hermes_storage_root / result['job_id']
            (job / 'status.json').write_text('{"status":"completed"}')
            (job / 'hermes-events.jsonl').write_text(json.dumps({'type': 'result', 'text': '답변'}, ensure_ascii=False))
        request = {'session_id': session, 'request_id': 'context-code-123', 'prompt': '코드 수정해줘'}
        result = self.hermes_service_manager.execute_hermes_command('hermes-session-submit', request)
        record = json.loads((self.hermes_service_manager.hermes_storage_root / result['job_id'] / 'request.json').read_text())
        self.assertEqual(record['context']['context_mode'], 'coding')
        self.assertEqual([m['content'] for m in record['context']['messages'] if m['role'] == 'user'], ['요구', '정정', '추가'])
        self.assertTrue(result['context_truncated'])
        self.assertTrue(self.hermes_service_manager.execute_hermes_command('hermes-session-submit', request)['duplicate'])

    @patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('workflow.domains.hermes_agent.service.launch_gpu_process')
    def test_duplicate_submission_is_single_queue_job(self, hermes_launch_mock, hermes_ready_mock):
        hermes_request_record = {'request_id':'same-request-1234', 'prompt':'작은 테스트'}
        with ThreadPoolExecutor(max_workers=4) as hermes_thread_pool:
            hermes_result_values = list(hermes_thread_pool.map(lambda _: self.hermes_service_manager.execute_hermes_command('hermes-submit', hermes_request_record), range(4)))
        self.assertEqual(hermes_launch_mock.call_count, 1)
        self.assertEqual(len({hermes_result_record['id'] for hermes_result_record in hermes_result_values}), 1)
        self.assertEqual(sum(hermes_result_record['duplicate'] for hermes_result_record in hermes_result_values), 3)
        with self.assertRaisesRegex(ValueError, '다른 지시'):
            self.hermes_service_manager.execute_hermes_command('hermes-submit', {'request_id':'same-request-1234', 'prompt':'다른 테스트'})

    @patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('workflow.domains.hermes_agent.service.launch_gpu_process')
    def test_unknown_acceptance_is_not_relaunched(self, hermes_launch_mock, hermes_ready_mock):
        hermes_request_record = {'request_id':'unknown-request-1234', 'prompt':'테스트'}
        hermes_job_result = self.hermes_service_manager.execute_hermes_command('hermes-submit', hermes_request_record)
        hermes_job_status = self.hermes_service_manager.execute_hermes_command('hermes-detail', {'id':hermes_job_result['id']})
        self.assertEqual(hermes_job_status['status']['status'], 'unknown')
        self.assertTrue(self.hermes_service_manager.execute_hermes_command('hermes-submit', hermes_request_record)['duplicate'])
        hermes_launch_mock.assert_called_once()

    def test_read_only_management_observation_preserves_unknown_and_filters_fields(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_management_snapshot
        with patch('workflow.common.gpu_status.read_gpu_status', return_value={'status':'busy', 'processes':[{'command':'private'}], 'gtt_free_mib':123, 'vram_free_mib':456, 'unexpected':'private'}), patch('workflow.common.gpu_job_queue.list_waiting_gpu_jobs', return_value={'jobs':[{'id':'job-1', 'service':'kimodo', 'path':'private'}]}):
            hermes_observation_record = read_hermes_management_snapshot()
        self.assertEqual(hermes_observation_record['gpu']['status'], 'busy')
        self.assertIn('Kimodo 활성 상태는 기록 기준',hermes_observation_record['detail'])
        self.assertEqual(hermes_observation_record['gpu']['process_count'], 1)
        self.assertEqual(hermes_observation_record['queue']['jobs'], [{'id':'job-1', 'service':'kimodo','executor_identity':'unverified'}])
        self.assertNotIn('private', str(hermes_observation_record))
        with patch('workflow.common.gpu_status.read_gpu_status', side_effect=OSError('unavailable')), patch('workflow.common.gpu_job_queue.list_waiting_gpu_jobs', side_effect=OSError('unavailable')):
            hermes_observation_record = read_hermes_management_snapshot()
        self.assertEqual(hermes_observation_record['gpu']['status'], 'unavailable')
        self.assertEqual(hermes_observation_record['queue']['status'], 'unavailable')

    def test_management_gpu_runtime_error_preserves_queue(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_management_snapshot
        with patch('workflow.common.gpu_status.read_gpu_status',side_effect=RuntimeError('GPU unavailable')),patch('workflow.common.gpu_job_queue.list_waiting_gpu_jobs',return_value={'jobs':[{'id':'job-1','service':'kimodo'}]}):
            current_snapshot_value=read_hermes_management_snapshot()
        self.assertEqual(current_snapshot_value['gpu'],{'status':'unavailable'})
        self.assertEqual(current_snapshot_value['queue']['status'],'available')
        self.assertEqual(current_snapshot_value['queue']['jobs'][0]['id'],'job-1')

    def test_management_queue_runtime_error_is_unavailable(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_management_snapshot
        with patch('workflow.common.gpu_status.read_gpu_status',return_value={'status':'unavailable'}) as current_gpu_mock,patch('workflow.common.gpu_job_queue.list_waiting_gpu_jobs',side_effect=RuntimeError('path loop')):
            current_snapshot_value=read_hermes_management_snapshot()
        current_gpu_mock.assert_called_once_with()
        self.assertEqual(current_snapshot_value['queue'],{'status':'unavailable','jobs':[]})
        self.assertEqual(current_snapshot_value['gpu'],{'status':'unavailable'})

    def test_management_observation_rejects_inconsistent_gpu_without_hiding_queue(self):
        from workflow.domains.hermes_agent import management_observer
        current_bad_records=({'status':'idle','processes':[{'pid':1}]},{'status':'busy','processes':[]},{'status':'idle','processes':None},{'status':'busy','processes':[None]})
        with patch('workflow.common.gpu_job_queue.list_waiting_gpu_jobs',return_value={'jobs':[{'id':'job-1','service':'image'}]}),patch.object(management_observer,'inspect_hermes_model_status',return_value={}),patch.object(management_observer,'read_hermes_generator_snapshot',return_value={}),patch.object(management_observer,'read_hermes_gpu_reservation_snapshot',return_value={}),patch.object(management_observer,'read_hermes_recent_job_snapshot',return_value={}):
            for current_gpu_record in current_bad_records:
                with self.subTest(gpu=current_gpu_record),patch('workflow.common.gpu_status.read_gpu_status',return_value=current_gpu_record):
                    current_result_value=management_observer.read_hermes_management_snapshot()
                    self.assertEqual(current_result_value['gpu'],{'status':'unavailable'})
                    self.assertEqual(current_result_value['queue']['jobs'][0]['id'],'job-1')
                    self.assertEqual(current_result_value['memory_capacity']['status'],'unavailable')

    def test_management_queue_source_preserves_only_allowlisted_identity(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_management_snapshot
        current_jobs=[{'id':'job-1','service':'image','source_service':'kimodo','path':'/private/job'},{'id':'job-2','service':'image','source_service':'unknown-service','path':'/private/other'}]
        with patch('workflow.common.gpu_status.read_gpu_status',return_value={'status':'unavailable'}),patch('workflow.common.gpu_job_queue.list_waiting_gpu_jobs',return_value={'jobs':current_jobs}) as current_queue_mock:
            current_snapshot=read_hermes_management_snapshot()
        current_queue_mock.assert_called_once_with(include_source_identity=True,observation_limits=True)
        self.assertEqual(current_snapshot['queue']['jobs'],[{'id':'job-1','service':'image','source_service':'kimodo','executor_identity':'unverified'},{'id':'job-2','service':'image','executor_identity':'unverified'}])
        self.assertNotIn('/private/',str(current_snapshot))

    def test_capture_queue_source_is_preserved_only_for_matching_service(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_management_snapshot
        current_job_values=[{'id':'job-1','service':'review-capture','source_service':'review-capture','path':'/private/capture'},{'id':'job-2','service':'image','source_service':'review-capture','path':'/private/other'}]
        with patch('workflow.common.gpu_status.read_gpu_status',return_value={'status':'unavailable'}),patch('workflow.common.gpu_job_queue.list_waiting_gpu_jobs',return_value={'jobs':current_job_values}):
            current_snapshot_value=read_hermes_management_snapshot()
        self.assertEqual(current_snapshot_value['queue']['jobs'][0]['source_service'],'review-capture')
        self.assertNotIn('source_service',current_snapshot_value['queue']['jobs'][1])
        self.assertNotIn('/private/',str(current_snapshot_value))

    def test_capture_queue_links_only_verified_request_identity(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_management_snapshot
        current_job_values=[{'id':'2026-11-20_00-00-00-12345678','service':'review-capture','source_service':'review-capture'},{'id':'job-2','service':'image','source_service':'review-capture'}]
        with patch('workflow.common.gpu_status.read_gpu_status',return_value={'status':'unavailable'}),patch('workflow.common.gpu_job_queue.list_waiting_gpu_jobs',return_value={'jobs':current_job_values}),patch('workflow.domains.hermes_agent.capture_status.find_verified_capture_request_identity',return_value={'request_id':'request_123','capture_service':'map-review'}) as current_identity_mock:
            current_snapshot_value=read_hermes_management_snapshot()
        self.assertEqual(current_snapshot_value['queue']['jobs'][0]['request_id'],'request_123')
        self.assertNotIn('request_id',current_snapshot_value['queue']['jobs'][1])
        current_identity_mock.assert_called_once()

    def test_priority_service_requires_exact_contract_and_dispatches(self):
        current_payload={'request_id':'request_123','service':'kimodo','id':'2026-10-09_21-13-20-1a356bbd','ticket_revision':'a'*64}
        with patch('workflow.domains.hermes_agent.priority_operations.submit_hermes_priority_once',return_value={'state':'completed'}) as current_submit_mock:
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-priority-submit',current_payload)['state'],'completed')
            current_submit_mock.assert_called_once_with(current_payload['request_id'],current_payload['service'],current_payload['id'],current_payload['ticket_revision'])
            with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-priority-submit',{**current_payload,'extra':True})
            self.assertEqual(current_submit_mock.call_count,1)
        with patch('workflow.domains.hermes_agent.priority_operations.read_hermes_priority_receipt',return_value={'state':'unknown'}) as current_read_mock:
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-priority-receipt',{'request_id':'request_123'})['state'],'unknown')
            current_read_mock.assert_called_once_with('request_123')

    def test_management_status_uses_shared_observation_and_rejects_input(self):
        from workflow.domains.hermes_agent import management_observer
        current_snapshot_value = {'model': {'status': 'unavailable'}, 'gpu': {'status': 'busy'}, 'queue': {'status': 'available', 'jobs': []}}
        with patch.object(management_observer, 'read_hermes_management_snapshot', return_value=current_snapshot_value):
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-management-status', {}), current_snapshot_value)
        self.assertEqual(resolve_management_command('hermes-agent', 'hermes-management-status', {}), ('POST', '/hermes-agent/hermes-management-status'))
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-management-status', {'command':'prepare'})

    def test_model_inventory_filters_paths_and_handles_invalid_responses(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_model_inventory
        current_response_record = {'models': {'kimodo': {'count':2, 'total_bytes':123, 'incomplete':False, 'files':[{'path':'private/path'}]}}}
        with patch('workflow.common.management_gateway.execute_management_command', return_value=current_response_record) as current_gateway_mock:
            current_inventory_result = read_hermes_model_inventory()
        self.assertEqual(current_inventory_result['models'], [{'service':'kimodo', 'file_count':2, 'total_bytes':123, 'incomplete':False}])
        self.assertNotIn('private', str(current_inventory_result))
        self.assertEqual(current_gateway_mock.call_args.args[:3], ('model-downloads', 'download-inventory', {}))
        with patch('workflow.common.management_gateway.execute_management_command', return_value={'models': {'kimodo': {'count':True, 'total_bytes':3, 'incomplete':False}}}):
            self.assertEqual(read_hermes_model_inventory()['status'], 'unavailable')
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-model-inventory', {'path':'other'})
        self.assertEqual(resolve_management_command('hermes-agent', 'hermes-model-inventory', {}), ('POST', '/hermes-agent/hermes-model-inventory'))

    def test_service_registration_exposes_new_services_without_granting_execution(self):
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS
        with patch.dict(MANAGEMENT_SERVICE_COMMANDS, {'future-service': ('future-command',)}):
            current_catalog_record = self.hermes_service_manager.execute_hermes_command('hermes-service-registration', {})
        current_future_record = next(item for item in current_catalog_record['services'] if item['service'] == 'future-service')
        self.assertEqual(current_future_record['commands'], ['future-command'])
        self.assertEqual(current_future_record['availability'], 'unverified')
        self.assertEqual(current_future_record['gateway_blocked'],[])
        self.assertEqual(current_future_record['known_service_blocked'],[])
        self.assertEqual(current_future_record['conditional_limitations'],[])
        current_vace_record=next(item for item in current_catalog_record['services'] if item['service']=='wan22-vace')
        self.assertTrue(any(item['command']=='resume' and 'official-bf16-resident-v1' in item['note'] for item in current_vace_record['conditional_limitations']))
        current_fun_record=next(item for item in current_catalog_record['services'] if item['service']=='wan22-fun-control')
        self.assertEqual({item['command'] for item in current_fun_record['conditional_limitations']},{'generate','resume','history-delete','history-reset','active','history','status','logs','history-reset-preview'})
        current_music_record=next(item for item in current_catalog_record['services'] if item['service']=='music-magenta')
        current_music_blocks={item['command']:item['reason'] for item in current_music_record['known_service_blocked']}
        self.assertIn('generate',current_music_blocks)
        self.assertIn('resume',current_music_blocks)
        self.assertNotIn('history',current_music_blocks)
        current_animation_record=next(item for item in current_catalog_record['services'] if item['service']=='character-animation')
        current_animation_blocks={item['command']:item['reason'] for item in current_animation_record['known_service_blocked']}
        self.assertEqual(set(current_animation_blocks),{'generate','resume','record-alpha-vnccs'})
        self.assertIn('sheet-update',current_animation_record['commands'])
        from workflow.domains.character_animation.character_animation_jobs import execute_animation_command
        for current_command_name,current_reason_text in current_animation_blocks.items():
            with self.assertRaises(ValueError) as current_error_value:
                execute_animation_command(current_command_name,{})
            self.assertEqual(str(current_error_value.exception),current_reason_text)
        from workflow.domains.music.generation import MusicGenerationManager
        current_music_manager=MusicGenerationManager('music-magenta')
        for current_command_name in ('generate','resume'):
            with self.assertRaises(ValueError) as current_error_value:
                current_music_manager.execute_music_command(current_command_name,{})
            self.assertEqual(str(current_error_value.exception),current_music_blocks[current_command_name])
        current_retired_record=next(item for item in current_catalog_record['services'] if item['service']=='momask')
        self.assertEqual({item['command'] for item in current_retired_record['gateway_blocked']},set(current_retired_record['commands']))
        current_qwen_record=next(item for item in current_catalog_record['services'] if item['service']=='qwen-21')
        self.assertIn('generate',{item['command'] for item in current_qwen_record['gateway_blocked']})
        self.assertNotIn('history',{item['command'] for item in current_qwen_record['gateway_blocked']})
        for current_service_record in current_catalog_record['services']:
            for current_blocked_record in current_service_record['gateway_blocked']:
                with self.assertRaises(ValueError) as current_error_value:
                    resolve_management_command(current_service_record['service'],current_blocked_record['command'],{})
                self.assertEqual(str(current_error_value.exception),current_blocked_record['reason'])
        self.assertIn('실행 가능 여부', current_catalog_record['note'])
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-service-registration', {'service':'future-service'})
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('future-command', {})
        self.assertEqual(resolve_management_command('hermes-agent', 'hermes-service-registration', {}), ('POST', '/hermes-agent/hermes-service-registration'))

    def test_service_registration_search_uses_shared_catalog(self):
        current_search_result=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{'query':'음악','offset':0,'limit':10})
        self.assertTrue({'music-heartmula','sfx-dasheng-audiogen'} <= {current_record['service'] for current_record in current_search_result['services']})
        self.assertIsNone(current_search_result['next_offset'])
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{'limit':11})

    def test_kimodo_build_status_sanitizes_existing_service(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_kimodo_build_status
        with patch('workflow.common.management_gateway.execute_management_command',return_value={'status':'completed','cache_status':'unverified','id':'2026-11-18_00-00-00-12345678','error':'private path'}) as current_gateway_mock:
            current_status_value=self.hermes_service_manager.execute_hermes_command('hermes-kimodo-build-status',{})
        self.assertEqual(current_status_value['status'],'completed')
        self.assertEqual(current_status_value['build_status'],'completed')
        self.assertEqual(current_status_value['cache_status'],'unverified')
        self.assertNotIn('private',str(current_status_value))
        self.assertEqual(current_gateway_mock.call_args.args[:3],('kimodo','migraphx-build-observe',{}))
        with patch('workflow.common.management_gateway.execute_management_command',return_value={'status':'completed','cache_status':'unverified','id':'../private'}):
            self.assertEqual(read_hermes_kimodo_build_status()['status'],'unavailable')
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-kimodo-build-status',{'extra':True})

    def test_field_commands_require_exact_payloads(self):
        with patch('workflow.domains.hermes_agent.field_map_operations.load_hermes_field_map', return_value={'map':'moss-clearing'}) as current_load_mock:
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-field-load', {'map':'moss-clearing'})['map'],'moss-clearing')
            current_load_mock.assert_called_once_with('moss-clearing')
            with self.assertRaises(ValueError):
                self.hermes_service_manager.execute_hermes_command('hermes-field-load', {'map':'moss-clearing','path':'other'})
        self.assertEqual(resolve_management_command('hermes-agent','hermes-field-preview',{'draft':{}}), ('POST','/hermes-agent/hermes-field-preview'))

    def test_content_status_reports_only_local_map_mode_on_database_failure(self):
        import os
        from workflow.domains.hermes_agent.management_observer import read_hermes_content_database_status
        with patch('workflow.common.management_gateway.execute_management_command',side_effect=OSError('unavailable')):
            for current_environment_value,current_expected_mode in (('database','database'),('files','files')):
                with self.subTest(mode=current_environment_value),patch.dict(os.environ,{'SLIME_CONTENT_STORAGE':current_environment_value}):
                    current_result_value=read_hermes_content_database_status()
                    self.assertEqual(current_result_value['status'],'unavailable')
                    self.assertEqual(current_result_value['local_map_mode'],current_expected_mode)

    def test_content_database_status_sanitizes_and_rejects_inconsistent_data(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_content_database_status
        current_database_value = {'generation':9, 'snapshotGeneration':7, 'pending':True, 'latestSnapshot':{'generation':8,'state':'failed','leaseExpired':False,'error':'private secret','runId':'private'}}
        with patch('workflow.common.management_gateway.execute_management_command', return_value=current_database_value) as current_gateway_mock:
            current_result_value = self.hermes_service_manager.execute_hermes_command('hermes-content-database-status', {})
        self.assertEqual(current_result_value['ledger_generation'], 7)
        self.assertTrue(current_result_value['pending'])
        self.assertEqual(current_result_value['latest']['state'], 'failed')
        self.assertNotIn('private', str(current_result_value))
        self.assertEqual(current_gateway_mock.call_args.args[:3], ('map-assets','database-status',{}))
        with patch('workflow.common.management_gateway.execute_management_command', return_value={**current_database_value,'pending':False}):
            self.assertEqual(read_hermes_content_database_status()['status'], 'unavailable')
        with patch('workflow.common.management_gateway.execute_management_command', side_effect=RuntimeError('secret')):
            self.assertNotIn('secret',str(read_hermes_content_database_status()))
        with patch('workflow.common.management_gateway.execute_management_command', side_effect=ValueError('gateway error: SLIME_CONTENT_SERVICE_ORIGIN에 콘텐츠 API origin을 지정하세요. secret')):
            current_result_value=read_hermes_content_database_status()
            self.assertEqual(current_result_value['failure_reason'],'service_origin')
            self.assertNotIn('secret',str(current_result_value))
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-content-database-status', {'command':'database-restore'})
        self.assertEqual(resolve_management_command('hermes-agent','hermes-content-database-status',{}), ('POST','/hermes-agent/hermes-content-database-status'))

    def test_hermes_model_preparation_conflict_is_rejected_before_receipt(self):
        from workflow.common.model_prepare_process import hold_hermes_model_usage_guard
        from workflow.domains.hermes_agent.model_preparation_store import HermesModelPreparationStore
        current_trial_root = Path(self.hermes_temporary_root.name)
        current_store_value = HermesModelPreparationStore(current_trial_root / 'model-receipts')
        current_request_value = {'request_id': 'request_model_conflict', 'service': 'hermes-model'}
        with patch('workflow.domains.hermes_agent.service.WORKFLOW_ROOT_DIRECTORY', current_trial_root), patch('workflow.domains.hermes_agent.model_preparation_store.HermesModelPreparationStore', return_value=current_store_value), patch('workflow.common.hermes_model_download.inspect_hermes_model_files', return_value=False), patch('workflow.common.management_gateway.execute_management_command') as current_gateway_mock:
            with hold_hermes_model_usage_guard(current_trial_root):
                current_blocked_result = self.hermes_service_manager.execute_hermes_command('hermes-model-prepare', current_request_value)
                self.assertEqual(current_blocked_result, {**current_request_value, 'state':'blocked', 'reason':'model_in_use'})
            current_gateway_mock.assert_not_called()
            self.assertEqual(current_store_value.read_model_preparation_receipt('request_model_conflict', 'hermes-model')['state'], 'not_found')

    def test_hermes_model_gateway_rejects_unknown_preparation_state(self):
        from workflow.common.management_gateway import execute_management_command
        current_trial_root = Path(self.hermes_temporary_root.name)
        current_status_path = current_trial_root / '.local/model-preparation/hermes-model/status.json'
        current_status_path.parent.mkdir(parents=True)
        current_status_path.write_text('{broken')
        with patch('workflow.common.hermes_model_download.WORKFLOW_ROOT_DIRECTORY', current_trial_root), patch('workflow.common.hermes_model_download.inspect_hermes_model_files', return_value=True), patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready'), patch('workflow.common.model_prepare_process.start_registered_preparation') as current_start_mock, patch('workflow.common.management_transport.send_management_json_response', side_effect=lambda current_handler, current_status, current_body: current_body):
            current_status_record = execute_management_command('hermes-model','model-status',{},gateway_request_handler=object())
            self.assertEqual(current_status_record['preparation_status'], 'unknown')
            self.assertFalse(current_status_record['generation_ready'])
            self.assertIn('확인 불가',current_status_record['message'])
            with self.assertRaisesRegex(ValueError,'확인할 수 없어'):
                execute_management_command('hermes-model','prepare',{'action':'prepare'},gateway_request_handler=object())
            current_start_mock.assert_not_called()

    def test_hermes_model_preparation_unknown_is_blocked_without_receipt(self):
        from workflow.domains.hermes_agent.model_preparation_store import HermesModelPreparationStore
        current_trial_root = Path(self.hermes_temporary_root.name)
        current_store_value = HermesModelPreparationStore(current_trial_root / 'model-receipts-unknown')
        current_request_value = {'request_id':'request_model_unknown', 'service':'hermes-model'}
        current_status_path = current_trial_root / '.local/model-preparation/hermes-model/status.json'
        current_status_path.parent.mkdir(parents=True)
        current_status_path.write_text('{broken')
        with patch('workflow.domains.hermes_agent.service.WORKFLOW_ROOT_DIRECTORY', current_trial_root), patch('workflow.domains.hermes_agent.model_preparation_store.HermesModelPreparationStore', return_value=current_store_value), patch('workflow.common.management_gateway.execute_management_command') as current_gateway_mock:
            current_result_record = self.hermes_service_manager.execute_hermes_command('hermes-model-prepare', current_request_value)
            self.assertEqual(current_result_record, {**current_request_value,'state':'blocked','reason':'preparation_unknown'})
            current_gateway_mock.assert_not_called()
            self.assertEqual(current_store_value.read_model_preparation_receipt('request_model_unknown','hermes-model')['state'], 'not_found')

    def test_model_preparation_respects_existing_policy_and_keeps_receipt(self):
        from workflow.domains.hermes_agent.model_preparation_store import HermesModelPreparationStore
        current_store_value = HermesModelPreparationStore(Path(self.hermes_temporary_root.name) / 'receipts')
        current_request_value = {'request_id':'request_prepare_123', 'service':'flux-image'}
        with patch('workflow.domains.hermes_agent.model_preparation_store.HermesModelPreparationStore', return_value=current_store_value), patch('workflow.common.management_gateway.execute_management_command', return_value={'preparation_status':'running', 'path':'private'}) as current_gateway_mock:
            current_result_value = self.hermes_service_manager.execute_hermes_command('hermes-model-prepare', current_request_value)
            self.assertEqual(current_result_value['state'], 'accepted')
            self.assertNotIn('private', str(current_result_value))
            self.assertTrue(self.hermes_service_manager.execute_hermes_command('hermes-model-prepare', current_request_value)['duplicate'])
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-model-prepare-status', current_request_value)['state'], 'accepted')
            current_gateway_mock.assert_called_once()
            self.assertEqual(current_gateway_mock.call_args.args[:3], ('flux-image','prepare',{'action':'prepare'}))
            with self.assertRaises(ValueError):
                self.hermes_service_manager.execute_hermes_command('hermes-model-prepare', {'request_id':'request_blocked_123','service':'expression-lora'})
            with self.assertRaises(ValueError):
                self.hermes_service_manager.execute_hermes_command('hermes-model-prepare', {'request_id':'request_blocked_123','service':'flux-image', 'url':'private'})
            with self.assertRaises(ValueError):
                self.hermes_service_manager.execute_hermes_command('hermes-model-prepare', {'request_id':'request_blocked_123','service':[]})
        self.assertEqual(resolve_management_command('hermes-agent','hermes-model-prepare',current_request_value), ('POST','/hermes-agent/hermes-model-prepare'))

    def test_audio_model_preparation_uses_download_command(self):
        from workflow.domains.hermes_agent.model_preparation_store import HermesModelPreparationStore
        current_store_value = HermesModelPreparationStore(Path(self.hermes_temporary_root.name) / 'receipts')
        with patch('workflow.domains.hermes_agent.model_preparation_store.HermesModelPreparationStore', return_value=current_store_value), patch('workflow.common.management_gateway.execute_management_command', return_value={'ready':False,'preparation_status':'running'}) as current_gateway_mock:
            self.hermes_service_manager.execute_hermes_command('hermes-model-prepare', {'request_id':'request_audio_123','service':'music-heartmula'})
        self.assertEqual(current_gateway_mock.call_args.args[:3], ('music-heartmula','download-model',{}))

    def test_model_readiness_accepts_only_registered_service_and_filters_response(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_model_readiness
        with patch('workflow.common.management_gateway.execute_management_command', return_value={'ready':True,'generation_ready':True,'preparation_status':'completed','path':'private','secret':'private'}) as current_gateway_mock:
            current_status = read_hermes_model_readiness('flux-image')
            self.assertTrue(current_status['ready'])
            self.assertTrue(current_status['generation_ready'])
            self.assertIn('모델 파일 크기 기준',current_status['note'])
            self.assertIn('한국어 번역 준비',current_status['note'])
            self.assertNotIn('private',str(current_status))
            current_gateway_mock.assert_called_once()
            self.assertEqual(current_gateway_mock.call_args.args[:3],('flux-image','model-status',{}))
            with self.assertRaises(ValueError):
                read_hermes_model_readiness('unregistered-service')
            current_gateway_mock.assert_called_once()
        with patch('workflow.common.management_gateway.execute_management_command', side_effect=[{'ready':True,'preparation_status':'running','path':'private'},{'ready':False,'artifacts_ready':True}]):
            current_status = read_hermes_model_readiness('music-heartmula')
            self.assertFalse(current_status['ready'])
            self.assertTrue(current_status['artifacts_ready'])
            self.assertIsNone(current_status['generation_ready'])
            self.assertEqual(current_status['download'],{'ready':True,'preparation_status':'running'})
            self.assertNotIn('private',str(current_status))
        with patch('workflow.common.management_gateway.execute_management_command', side_effect=[OSError('private'),{'ready':False}]):
            current_status = read_hermes_model_readiness('music-heartmula')
            self.assertEqual(current_status['status'],'available')
            self.assertIsNone(current_status['download'])
        with patch('workflow.common.management_gateway.execute_management_command', side_effect=[{'ready':False,'preparation_status':'running'},OSError('private')]):
            current_status = read_hermes_model_readiness('music-heartmula')
            self.assertEqual(current_status['status'],'unavailable')
            self.assertEqual(current_status['download'],{'ready':False,'preparation_status':'running'})
            self.assertNotIn('private',str(current_status))
        with patch('workflow.common.management_gateway.execute_management_command', return_value={'ready':True}):
            current_status = read_hermes_model_readiness('flux-image')
            self.assertIsNone(current_status['generation_ready'])
            self.assertEqual(current_status['preparation_status'],'unknown')
        with patch('workflow.common.management_gateway.execute_management_command', side_effect=OSError('private path')):
            current_status = read_hermes_model_readiness('flux-image')
            self.assertEqual(current_status['status'],'unavailable')
            self.assertNotIn('private',str(current_status))
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-model-readiness', {'service':'flux-image','extra':'prepare'})

    def test_building_catalog_uses_generation_and_filters_paths(self):
        from workflow.domains.hermes_agent.asset_observer import read_hermes_building_catalog
        current_asset_record={'texture':'town-iseulon-guild-v1','image':'/private/image.png','width':512,'height':256,'properties':{'anchorX':0.5,'anchorY':1.0,'private':'secret'},'maps':[{'map':'iseulon','name':'길드','width':2,'height':3,'facing':'front','contentWidth':2}]}
        with patch('workflow.common.management_gateway.execute_management_command',return_value={'generation':7,'assets':[current_asset_record]}) as current_gateway_mock:
            current_result=read_hermes_building_catalog({'query':'길드','limit':1})
        self.assertEqual(current_result['generation'],7)
        self.assertEqual(current_result['items'][0]['uses'][0]['map'],'iseulon')
        self.assertEqual(current_result['items'][0]['image_pixels'],{'width':512,'height':256})
        self.assertNotIn('/private',str(current_result))
        self.assertNotIn('secret',str(current_result))
        current_gateway_mock.assert_called_once()
        self.assertEqual(current_gateway_mock.call_args.args[:3],('map-assets','building-list',{}))
        for current_invalid_record in ({'limit':31},{'offset':True},{'query':'a\nb'},{'command':'building-save'}):
            with self.subTest(request=current_invalid_record),self.assertRaises(ValueError):
                read_hermes_building_catalog(current_invalid_record)
        with patch('workflow.common.management_gateway.execute_management_command',side_effect=ValueError('/private')):
            with self.assertRaisesRegex(ValueError,'콘텐츠 서비스 연결') as current_error:
                read_hermes_building_catalog({})
            self.assertNotIn('/private',str(current_error.exception))

    def test_building_pages_reject_changed_generation_data_and_query(self):
        from workflow.domains.hermes_agent.asset_observer import read_hermes_building_catalog
        current_assets_list=[{'texture':'town-test-'+str(index)+'-v1','width':2,'height':2,'properties':{'anchorX':0.5,'anchorY':1},'maps':[]} for index in range(3)]
        current_catalog_value={'generation':5,'assets':current_assets_list}
        with patch('workflow.common.management_gateway.execute_management_command',return_value=current_catalog_value):
            current_first_page=read_hermes_building_catalog({'limit':1})
            current_second_page=read_hermes_building_catalog({'limit':1,'offset':1,'snapshot':current_first_page['snapshot']})
            self.assertNotEqual(current_first_page['items'][0]['id'],current_second_page['items'][0]['id'])
            with self.assertRaisesRegex(ValueError,'변경'):
                read_hermes_building_catalog({'query':'town','limit':1,'offset':1,'snapshot':current_first_page['snapshot']})
            current_catalog_value['generation']=6
            with self.assertRaisesRegex(ValueError,'변경'):
                read_hermes_building_catalog({'limit':1,'offset':1,'snapshot':current_first_page['snapshot']})
            current_catalog_value['generation']=5
            current_assets_list[1]['properties']['anchorX']=1
            with self.assertRaisesRegex(ValueError,'변경'):
                read_hermes_building_catalog({'limit':1,'offset':1,'snapshot':current_first_page['snapshot']})
            with self.assertRaises(ValueError):read_hermes_building_catalog({'snapshot':'bad'})

    def test_world_map_uses_validated_source_and_omits_private_paths(self):
        from workflow.domains.hermes_agent.asset_observer import read_hermes_world_map_catalog
        current_catalog = {'maps':[{'id':'town','name':'마을','safeTown':True,'column':0,'row':1,'connections':[{'id':'gate','target':'field','direction':'north','targetWaypointId':'return','path':'/private'}], 'thumbnail':{'url':'/private'}}], 'provenance':[{'managementId':'map.example','version':'v1','sha256':'a'*64,'source':'/private'}]}
        with patch('workflow.domains.world_map.catalog.load_world_review_catalog',return_value=current_catalog) as current_source_mock:
            current_result = read_hermes_world_map_catalog()
        current_source_mock.assert_called_once_with()
        self.assertEqual(current_result['maps'][0]['connections'][0]['target'],'field')
        self.assertEqual(current_result['provenance'][0]['sha256'],'a'*64)
        self.assertNotIn('/private',str(current_result))
        current_catalog['provenance'][0]['source'] = 'assets/maps/map_names/town.yaml'
        with patch('workflow.domains.world_map.catalog.load_world_review_catalog',return_value=current_catalog):
            current_selected = read_hermes_world_map_catalog('town')
        self.assertEqual(current_selected['provenance_scope'],'selected_map')
        self.assertEqual(current_selected['provenance'][0]['managementId'],'map.example')
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-world-map', {'map':None})
        with patch('workflow.domains.world_map.catalog.load_world_review_catalog',side_effect=ValueError('/private')):
            with self.assertRaisesRegex(ValueError,'원본을 검증') as current_error:
                read_hermes_world_map_catalog()
            self.assertNotIn('/private',str(current_error.exception))
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-world-map', {'command':'save'})

    def test_billboard_catalog_filters_paths_and_paginates(self):
        from workflow.domains.hermes_agent.asset_observer import read_hermes_billboard_catalog
        current_asset_record = {'texture':'tree-v1','name':'나무','category':'large-trees','image':'/private/image.png','properties':{'displayHeight':42,'anchorX':0.5,'private':'secret'},'maps':[{'path':'assets/maps/field_tiles/a.yaml','texture_key_occurrences':2},{'path':'/private/path','texture_key_occurrences':1}], 'modeling':{'purpose':'그늘','basis':'등록 이름 기준','visual_review':{'status':'확인 필요','source_sha256':'secret'}}, 'metadata':['private']}
        with patch('workflow.common.management_gateway.execute_management_command',return_value={'revision':'a'*64,'assets':[current_asset_record,{**current_asset_record,'texture':'tree-v2'}]}) as current_gateway_mock:
            current_result = read_hermes_billboard_catalog({'category':'large-trees','query':'나무','limit':1})
        self.assertEqual(current_result['total'],2)
        self.assertEqual(current_result['next_offset'],1)
        self.assertEqual(current_result['items'][0]['maps'],[{'map':'a','source_path':'assets/maps/field_tiles/a.yaml','occurrences':2}])
        self.assertEqual(current_result['items'][0]['display_properties']['displayHeight'],42)
        self.assertEqual(current_result['items'][0]['modeling']['visual_review_status'],'확인 필요')
        self.assertNotIn('private',str(current_result))
        self.assertNotIn('secret',str(current_result))
        self.assertEqual(current_gateway_mock.call_args.args[:3],('map-assets','asset-list',{'category':'large-trees'}))
        many_maps = [{'path':f'assets/maps/field_tiles/region-{i}.yaml'} for i in range(21)]
        with patch('workflow.common.management_gateway.execute_management_command',
                   return_value={'assets':[{**current_asset_record,'maps':many_maps}]}):
            match = read_hermes_billboard_catalog({'query':'region-20 나무'})
            self.assertEqual(match['total'],1)
            self.assertEqual(len(match['items'][0]['maps']),20)
            self.assertTrue(match['items'][0]['maps_truncated'])
        for current_bad_request in ({'limit':31},{'offset':True},{'query':'line\nbreak'},{'category':'../../x'},{'command':'asset-save'}):
            with self.subTest(request=current_bad_request), self.assertRaises(ValueError):
                read_hermes_billboard_catalog(current_bad_request)
        with patch('workflow.common.management_gateway.execute_management_command',side_effect=OSError('/private')):
            with self.assertRaisesRegex(ValueError,'확인할 수 없습니다') as current_error:
                read_hermes_billboard_catalog({})
            self.assertNotIn('/private',str(current_error.exception))

    def test_kimodo_recorded_active_observation_never_recovers_jobs(self):
        from workflow.domains.kimodo.generation import KimodoGenerationManager
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_manager_value=KimodoGenerationManager()
            current_manager_value.job_storage_root=Path(current_temp_root)/'jobs'
            self.assertEqual(current_manager_value.read_kimodo_recorded_active_status()['count'],0)
            current_running_path=current_manager_value.job_storage_root/'2026-11-17_10-00-00-12345678'
            current_running_path.mkdir(parents=True)
            current_status_path=current_running_path/'status.json'
            current_status_bytes=b'{"status":"running"}\n'
            current_status_path.write_bytes(current_status_bytes)
            current_result_value=current_manager_value.read_kimodo_recorded_active_status()
            self.assertTrue(current_result_value['running'])
            self.assertEqual(current_result_value['id'],current_running_path.name)
            self.assertIn('프로세스 생존',current_result_value['note'])
            self.assertEqual(current_status_path.read_bytes(),current_status_bytes)
            self.assertFalse((current_running_path/'resume.lock').exists())
            current_status_path.unlink()
            current_unknown_value=current_manager_value.read_kimodo_recorded_active_status()
            self.assertFalse(current_unknown_value['running'])
            self.assertEqual(current_unknown_value['unknown_count'],1)
            current_status_path.write_bytes(current_status_bytes)
            current_corrupt_path=current_manager_value.job_storage_root/'2026-11-17_11-00-00-87654321'
            current_corrupt_path.mkdir()
            (current_corrupt_path/'status.json').write_text('{broken')
            current_partial_value=current_manager_value.read_kimodo_recorded_active_status()
            self.assertEqual(current_partial_value['count'],1)
            self.assertEqual(current_partial_value['unknown_count'],1)
            self.assertEqual(current_status_path.read_bytes(),current_status_bytes)
        self.assertEqual(resolve_management_command('kimodo','active-observe',{}),('GET','/kimodo/active-observe'))

    def test_generator_observation_uses_only_fixed_read_commands(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_generator_snapshot
        current_job_id = '2026-11-17_10-00-00-12345678'
        with patch('workflow.common.management_gateway.execute_management_command', side_effect=[{'ready':True, 'preparation_status':'idle', 'private':'secret'}, {'running':True, 'id':current_job_id, 'count':2, 'unknown_count':1, 'private':'secret'}]) as current_gateway_mock:
            current_generator_value = read_hermes_generator_snapshot()['kimodo']
        self.assertEqual(current_generator_value['model'], {'status':'available', 'ready':True, 'preparation_status':'idle'})
        self.assertEqual(current_generator_value['active'], {'status':'available', 'running':True, 'id':current_job_id, 'count':2, 'unknown_count':1})
        self.assertEqual([current_call.args[:3] for current_call in current_gateway_mock.call_args_list], [('kimodo', 'model-status', {}), ('kimodo', 'active-observe', {})])
        with patch('workflow.common.management_gateway.execute_management_command', side_effect=[ValueError('offline'), {'running':True, 'id':'../../bad'}]):
            current_generator_value = read_hermes_generator_snapshot()['kimodo']
        self.assertEqual(current_generator_value['model']['status'], 'unavailable')
        self.assertEqual(current_generator_value['active']['status'], 'unavailable')
        for current_bad_record in ({'running':False,'id':None,'count':1,'unknown_count':0},{'running':True,'id':current_job_id,'count':True,'unknown_count':0},{'running':False,'id':current_job_id,'count':0,'unknown_count':0},{'running':False,'id':None,'count':0,'unknown_count':True}):
            with self.subTest(response=current_bad_record),patch('workflow.common.management_gateway.execute_management_command',side_effect=[{'ready':True},current_bad_record]):
                self.assertEqual(read_hermes_generator_snapshot()['kimodo']['active']['status'],'unavailable')

    def test_model_observation_reports_failure_without_ready_claim(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_management_snapshot
        with patch('workflow.domains.hermes_agent.management_observer.inspect_hermes_model_status', side_effect=OSError('unavailable')):
            current_observation_record = read_hermes_management_snapshot()
        self.assertEqual(current_observation_record['model'], {'status': 'unavailable'})

    def test_reservation_observation_is_filtered_and_conservative(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_gpu_reservation_snapshot
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_root_path = Path(current_temp_root)
            self.assertEqual(read_hermes_gpu_reservation_snapshot(current_root_path)['records'], [])
            current_active_path = current_root_path / 'active'
            current_active_path.mkdir()
            current_job_id = '2026-11-18_00-00-00-12345678'
            (current_active_path / 'one.json').write_text(json.dumps({'service':'hermes-agent','required_memory_mib':32768,'path':'/private/' + current_job_id,'worker_process_token':'secret','pid':123}))
            (current_active_path / 'two.json').write_text('bad json')
            current_result_value = read_hermes_gpu_reservation_snapshot(current_root_path)
            self.assertEqual(current_result_value['status'], 'available')
            self.assertEqual(current_result_value['records'][0], {'state':'cleanup_unverified','service':'hermes-agent','job_id':current_job_id,'required_memory_mib':32768})
            self.assertEqual(current_result_value['records'][1]['state'], 'unknown')
            self.assertNotIn('secret', str(current_result_value))
            self.assertNotIn('/private/', str(current_result_value))
            (current_active_path / 'two.json').unlink()
            (current_active_path / 'two.json').symlink_to(current_active_path / 'one.json')
            self.assertEqual(read_hermes_gpu_reservation_snapshot(current_root_path)['records'][1]['state'], 'unknown')
            with patch('os.scandir', side_effect=PermissionError('denied')):
                self.assertEqual(read_hermes_gpu_reservation_snapshot(current_root_path)['status'], 'unavailable')

    def test_service_lock_rejects_special_and_symbolic_files(self):
        import os
        current_job_root = self.hermes_service_manager.hermes_storage_root
        current_job_root.mkdir(parents=True, exist_ok=True)
        current_lock_path = current_job_root / '.service.lock'
        current_target_path = current_job_root / 'other-file'
        current_target_path.write_text('unchanged')
        current_lock_path.symlink_to(current_target_path)
        with self.assertRaises(OSError):
            with self.hermes_service_manager.hold_hermes_service_lock():
                self.fail('symbolic lock accepted')
        self.assertEqual(current_target_path.read_text(), 'unchanged')
        current_lock_path.unlink()
        os.mkfifo(current_lock_path)
        with self.assertRaises((OSError, ValueError)):
            with self.hermes_service_manager.hold_hermes_service_lock():
                self.fail('FIFO lock accepted')
        current_lock_path.unlink()
        with self.hermes_service_manager.hold_hermes_service_lock():
            self.assertTrue(current_lock_path.is_file())

    def test_recent_job_observation_filters_fields_and_handles_missing_status(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_recent_job_snapshot
        current_job_root = self.hermes_service_manager.hermes_storage_root
        current_job_root.mkdir(parents=True, exist_ok=True)
        for current_index in range(12):
            current_job_path = current_job_root / ('2026-11-18_00-00-' + f'{current_index:02d}' + '-12345678')
            current_job_path.mkdir()
            (current_job_path / 'request.json').write_text('{"prompt":"secret"}')
            if current_index != 11:
                (current_job_path / 'status.json').write_text('{"status":"completed","error":"private"}')
        current_result_value = read_hermes_recent_job_snapshot(self.hermes_service_manager)
        self.assertEqual(current_result_value['status'], 'available')
        self.assertEqual(len(current_result_value['jobs']), 10)
        self.assertTrue(current_result_value['truncated'])
        self.assertEqual(current_result_value['jobs'][0]['status'], 'unknown')
        self.assertNotIn('secret', str(current_result_value))
        self.assertNotIn('private', str(current_result_value))
        self.assertNotIn(str(current_job_root), str(current_result_value))
        with patch.object(self.hermes_service_manager, 'list_hermes_job_paths', side_effect=OSError('unavailable')):
            self.assertEqual(read_hermes_recent_job_snapshot(self.hermes_service_manager)['status'], 'unavailable')

    def test_recent_job_observation_limits_directory_entries_without_changing_history(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_recent_job_snapshot
        current_job_root = self.hermes_service_manager.hermes_storage_root
        current_job_root.mkdir(parents=True, exist_ok=True)
        for current_index in range(2):
            current_job_path = current_job_root / ('2026-11-18_00-00-0' + str(current_index) + '-12345678')
            current_job_path.mkdir()
            (current_job_path / 'status.json').write_text('{"status":"completed"}')
        with patch('workflow.domains.hermes_agent.service.HERMES_JOB_OBSERVATION_MAXIMUM_ENTRIES', 3):
            current_result_value = read_hermes_recent_job_snapshot(self.hermes_service_manager)
            self.assertEqual(current_result_value['status'], 'available')
            self.assertEqual([current_job_record['id'] for current_job_record in current_result_value['jobs']], [current_job_path.name for current_job_path in self.hermes_service_manager.list_hermes_job_paths()])
            (current_job_root / 'unrelated-entry').write_text('')
            self.assertEqual(read_hermes_recent_job_snapshot(self.hermes_service_manager), {'status': 'unavailable', 'jobs': [], 'truncated': False})
            self.assertEqual(len(self.hermes_service_manager.list_hermes_job_paths()), 2)

    def test_recent_job_observation_handles_oversized_and_fifo_status(self):
        import os
        from workflow.domains.hermes_agent.delegation_store import HERMES_DELEGATION_RECORD_MAXIMUM_BYTES
        from workflow.domains.hermes_agent.management_observer import read_hermes_recent_job_snapshot
        current_job_root=self.hermes_service_manager.hermes_storage_root
        current_job_root.mkdir(parents=True,exist_ok=True)
        for current_index,current_file_kind in enumerate(('oversized','fifo')):
            current_job_path=current_job_root/('2026-11-18_00-00-0'+str(current_index)+'-12345678')
            current_job_path.mkdir()
            current_status_path=current_job_path/'status.json'
            if current_file_kind=='oversized':current_status_path.write_bytes(b'x'*(HERMES_DELEGATION_RECORD_MAXIMUM_BYTES+1))
            else:os.mkfifo(current_status_path)
        current_result_value=read_hermes_recent_job_snapshot(self.hermes_service_manager)
        self.assertEqual(current_result_value['status'],'available')
        self.assertEqual([current_job_record['status'] for current_job_record in current_result_value['jobs']],['unknown','unknown'])

    def test_writer_reservation_preview_rejects_unverified_or_ambiguous_targets(self):
        import os
        from workflow.common import gpu_job_queue
        from workflow.domains.hermes_agent.writer_reservation import preview_writer_reservation_recovery
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_active_path=current_root_path/'active'
            current_active_path.mkdir()
            current_job_identifier='20261118-120000-12345678'
            current_reservation_value={'service':'writer-agent','path':'/private/jobs/'+current_job_identifier,'pid':os.getpid(),'pid_start_token':'different'}
            (current_active_path/'one.json').write_text(json.dumps(current_reservation_value))
            with patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_root_path),patch.object(gpu_job_queue,'open_verified_hermes_process_group',return_value=None):
                current_preview_value=preview_writer_reservation_recovery(current_job_identifier)
                self.assertFalse(current_preview_value['recoverable'])
                self.assertNotIn('/private',str(current_preview_value))
                (current_active_path/'two.json').write_text(json.dumps(current_reservation_value))
                with self.assertRaisesRegex(ValueError,'둘 이상'):preview_writer_reservation_recovery(current_job_identifier)
                with self.assertRaises(ValueError):preview_writer_reservation_recovery('../private')

    def test_writer_recovery_requires_absent_executor_and_unique_global_job(self):
        import os
        from workflow.common import gpu_job_queue
        from workflow.domains.hermes_agent.writer_reservation import preview_writer_reservation_recovery
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_queue_root=Path(current_directory_name)
            current_active_root=current_queue_root/'active'
            current_active_root.mkdir()
            current_job_identifier='20261118-120000-12345678'
            current_reservation_record={'service':'writer-agent','path':'/private/jobs/'+current_job_identifier,'pid':os.getpid(),'pid_start_token':'1'}
            (current_active_root/'writer.json').write_text(json.dumps(current_reservation_record))
            with patch.object(gpu_job_queue,'GPU_QUEUE_DIRECTORY',current_queue_root),patch.object(gpu_job_queue,'open_verified_hermes_process_group') as current_worker_open:
                # 시작 시각이 다른 재사용 PID도 확실한 부재가 아니다.
                self.assertFalse(preview_writer_reservation_recovery(current_job_identifier)['recoverable'])
                current_worker_open.assert_not_called()
                with patch('workflow.domains.hermes_agent.writer_reservation.os.kill',side_effect=PermissionError()):
                    self.assertFalse(preview_writer_reservation_recovery(current_job_identifier)['recoverable'])
                current_other_record={**current_reservation_record,'service':'kimodo'}
                (current_active_root/'other.json').write_text(json.dumps(current_other_record))
                with self.assertRaisesRegex(ValueError,'둘 이상'):
                    preview_writer_reservation_recovery(current_job_identifier)

    def test_generator_reservation_recovery_gateway_rejects_extra_inputs(self):
        from workflow.common.management_gateway import resolve_management_command
        current_request_record={'request_id':'recovery_123','service':'kimodo','job_id':'job-123','review_sha256':'a'*64,'outside_processes_checked':True}
        self.assertEqual(resolve_management_command('hermes-agent','hermes-generator-reservation-recover',current_request_record),('POST','/hermes-agent/hermes-generator-reservation-recover'))
        with patch('workflow.domains.hermes_agent.generator_reservation_recovery.recover_generator_reservation_once',return_value={'state':'unknown'}) as current_recover_mock:
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-generator-reservation-recover',current_request_record),{'state':'unknown'})
            current_recover_mock.assert_called_once_with('recovery_123','kimodo','job-123','a'*64,True)
            with self.assertRaises(ValueError):
                self.hermes_service_manager.execute_hermes_command('hermes-generator-reservation-recover',{**current_request_record,'extra':True})
            current_recover_mock.assert_called_once()
        with patch('workflow.domains.hermes_agent.generator_reservation_recovery.read_generator_recovery_receipt',return_value={'state':'not_found'}) as current_receipt_mock:
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-generator-reservation-receipt',{'request_id':'recovery_123'}),{'state':'not_found'})
            current_receipt_mock.assert_called_once_with('recovery_123')

    def test_translation_resume_commands_enforce_exact_fields(self):
        current_payload_value={'request_id':'request_123','job_id':'2026-11-18_00-00-00-12345678','expected_resume_fingerprint':'a'*64}
        with patch('workflow.domains.hermes_agent.translation_resume_operations.submit_hermes_translation_resume_once',return_value={'state':'accepted'}) as current_submit_mock:
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-translation-resume-submit',current_payload_value)['state'],'accepted')
            current_submit_mock.assert_called_once()
            with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-translation-resume-submit',{**current_payload_value,'extra':True})
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        self.assertTrue({'hermes-translation-resume-preview','hermes-translation-resume-submit','hermes-translation-resume-receipt'}<={item['command'] for item in current_catalog_value['records']})

    def test_audio_resume_commands_enforce_exact_fields(self):
        current_payload_value={'request_id':'request_123','service':'music-heartmula','job_id':'2026-11-18_00-00-00-12345678','expected_resume_fingerprint':'a'*64}
        with patch('workflow.domains.hermes_agent.audio_resume_operations.submit_hermes_audio_resume_once',return_value={'state':'accepted'}) as current_submit_mock:
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-audio-resume-submit',current_payload_value)['state'],'accepted')
            current_submit_mock.assert_called_once()
            with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-audio-resume-submit',{**current_payload_value,'extra':True})
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        self.assertTrue({'hermes-audio-resume-preview','hermes-audio-resume-submit','hermes-audio-resume-receipt'}<={item['command'] for item in current_catalog_value['records']})

    def test_unlinked_resume_and_history_deletion_are_discoverable(self):
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_services_by_name={item['service']:item for item in current_catalog_value['services']}
        for current_service_name,current_commands in (('kimodo',('history-delete','history-reset')),('writer-agent',('writer-delete',))):
            current_service_record=current_services_by_name[current_service_name]
            for current_command_name in current_commands:
                with self.subTest(current_service_name=current_service_name,current_command_name=current_command_name):
                    current_matching_notes=[item['note'] for item in current_service_record['conditional_limitations'] if item['command']==current_command_name]
                    self.assertTrue(any('Hermes에서는 이 명령을 직접 실행할 수 없습니다' in item for item in current_matching_notes))
        current_kimodo_notes=[item['note'] for item in current_services_by_name['wan22-vace']['conditional_limitations'] if item['command']=='resume']
        self.assertTrue(any('model_profile' in item for item in current_kimodo_notes))

    def test_registration_report_contains_current_services_and_links(self):
        from workflow.maintenance.report_hermes_service_registration import render_hermes_registration_report
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration
        current_report_text=render_hermes_registration_report('test-time')
        current_service_records=list_management_service_registration()['services']
        self.assertIn('생성 시각(UTC): test-time',current_report_text)
        self.assertEqual(current_report_text.count('\n## '),len(current_service_records))
        for current_service_record in current_service_records:
            current_service_section=current_report_text.split('\n## '+current_service_record['service']+'\n',1)[1].split('\n## ',1)[0]
            for current_command_name in current_service_record['commands']:
                self.assertIn('`'+current_command_name+'`',current_service_section)
            for current_link_name in current_service_record['hermes_links']:
                self.assertIn('`'+current_link_name+'`',current_service_section)
        self.assertIn('실행 권한·가용성·GPU 시험',current_report_text)

    def test_video_and_flux_resume_registration_explains_reviewed_alternative(self):
        from workflow.domains.hermes_agent.video_operations import HERMES_VIDEO_SERVICES
        from workflow.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
        current_catalog_record=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_services_by_name={current_record['service']:current_record for current_record in current_catalog_record['services']}
        for current_service_name in (*HERMES_VIDEO_SERVICES,*FLUX_IMAGE_PROFILE_RECORDS):
            with self.subTest(service=current_service_name):
                current_service_record=current_services_by_name[current_service_name]
                current_resume_notes=[current_item['note'] for current_item in current_service_record['conditional_limitations'] if current_item['command']=='resume']
                self.assertTrue(any('별도 재개 검토' in current_note and '확인 후 접수' in current_note for current_note in current_resume_notes))
                current_prefix_value='hermes-video-resume' if current_service_name in HERMES_VIDEO_SERVICES else 'hermes-flux-resume'
                self.assertTrue({current_prefix_value+'-preview',current_prefix_value+'-submit',current_prefix_value+'-receipt'} <= set(current_service_record['hermes_links']))

    def test_review_capture_limitations_are_discoverable_without_execution(self):
        current_catalog_record=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_services_by_name={current_record['service']:current_record for current_record in current_catalog_record['services']}
        for current_service_name in ('map-review','character-review'):
            current_service_record=current_services_by_name[current_service_name]
            self.assertEqual(current_service_record['hermes_links'],['hermes-capture-status','hermes-capture-proposal'])
            current_capture_note=next(current_item['note'] for current_item in current_service_record['conditional_limitations'] if current_item['command']=='capture')
            for current_required_text in ('실행하지 않는다','PNG','GPU','중복 방지'):
                self.assertIn(current_required_text,current_capture_note)
        current_capability_catalog=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_capture_status=next(current_record for current_record in current_capability_catalog['records'] if current_record['command']=='hermes-capture-status')
        self.assertEqual(current_capture_status['interfaces'],['gui','mcp','isolated_fixed_bridge'])
        self.assertIn('실행은 아직 지원하지 않는다',current_capture_status['note'])
        current_search_record=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{'query':'헤드리스'})
        self.assertTrue({'map-review','character-review'} <= {current_record['service'] for current_record in current_search_record['services']})

    def test_city_save_discloses_original_and_consumer_sync_limit(self):
        current_capability_catalog=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_city_load=next(current_record for current_record in current_capability_catalog['records'] if current_record['command']=='hermes-city-load')
        self.assertIn('isolated_fixed_bridge',current_city_load['interfaces'])
        self.assertIn('256 KiB',current_city_load['note'])
        self.assertIn('DB 편집 문서',current_city_load['label'])
        self.assertIn('hermes-city-source',current_city_load['note'])
        current_city_record=next(current_record for current_record in current_capability_catalog['records'] if current_record['command']=='hermes-city-save')
        for current_term_value in ('콘텐츠 DB','원본','등록부','잠금','동기화'):
            self.assertIn(current_term_value,current_city_record['note'])
        current_service_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_assets_record=next(current_record for current_record in current_service_catalog['services'] if current_record['service']=='map-assets')
        self.assertTrue(any(current_item['command']=='city-edit-save' and '원본' in current_item['note'] for current_item in current_assets_record['conditional_limitations']))

    def test_source_history_log_scope_is_discoverable(self):
        current_service_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_service_records={current_record['service']:current_record for current_record in current_service_catalog['services']}
        for current_service_name in ('music-heartmula','sfx-dasheng-audiogen','flux-image','flux-character','flux-expression'):
            with self.subTest(service=current_service_name):
                current_history_limit=next(current_item for current_item in current_service_records[current_service_name]['conditional_limitations'] if current_item['command']=='history')
                self.assertIn('로그',current_history_limit['note'])
                self.assertIn('Hermes 원본 이력 관측은 로그를 포함하지 않는다',current_history_limit['note'])

    def test_audio_and_flux_active_reports_recorded_status_limit(self):
        current_service_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_service_records={current_record['service']:current_record for current_record in current_service_catalog['services']}
        for current_service_name in ('music-heartmula','sfx-dasheng-audiogen','flux-image','flux-character','flux-expression'):
            with self.subTest(service=current_service_name):
                current_active_note=next(current_item['note'] for current_item in current_service_records[current_service_name]['conditional_limitations'] if current_item['command']=='active')
                self.assertIn('대기',current_active_note)
                self.assertIn('생존이나 종료를 확인하지 않는다',current_active_note)
                if current_service_name.startswith('music-') or current_service_name.startswith('sfx-'):
                    self.assertNotIn('FLUX',current_active_note)
                else:
                    self.assertIn('running도 대기를 포함',current_active_note)

    def test_image_model_status_does_not_claim_gpu_or_archived_generation(self):
        current_service_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_service_records={current_record['service']:current_record for current_record in current_service_catalog['services']}
        for current_service_name in ('flux-image','flux-character','flux-expression'):
            current_model_note=next(current_record['note'] for current_record in current_service_records[current_service_name]['conditional_limitations'] if current_record['command']=='model-status')
            self.assertIn('GPU 실행',current_model_note)
            self.assertIn('한국어 번역',current_model_note)
        current_legacy_note=next(current_record['note'] for current_record in current_service_records['qwen-21']['conditional_limitations'] if current_record['command']=='model-status')
        self.assertIn('신규 생성',current_legacy_note)
        self.assertIn('차단',current_legacy_note)

    def test_image_status_scope_is_discoverable_for_current_and_archived_services(self):
        current_service_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_service_records={current_record['service']:current_record for current_record in current_service_catalog['services']}
        for current_service_name in ('flux-image','flux-expression','qwen-21','floor-tile','building-generator'):
            with self.subTest(service=current_service_name):
                current_status_note=next(current_record['note'] for current_record in current_service_records[current_service_name]['conditional_limitations'] if current_record['command']=='status')
                self.assertIn('12,000바이트',current_status_note)
                self.assertIn('생존이나 종료는 확인하지 않는다',current_status_note)

    def test_source_log_read_bounds_are_discoverable(self):
        current_service_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_service_records={current_record['service']:current_record for current_record in current_service_catalog['services']}
        for current_service_name in ('music-heartmula','sfx-dasheng-audiogen','prompt-translation'):
            current_log_note=next(current_record['note'] for current_record in current_service_records[current_service_name]['conditional_limitations'] if current_record['command']=='logs')
            self.assertIn('16,000바이트',current_log_note)
        for current_service_name in ('flux-image','flux-expression','dwpose','wan22-vace','kimodo'):
            current_log_note=next(current_record['note'] for current_record in current_service_records[current_service_name]['conditional_limitations'] if current_record['command']=='logs')
            self.assertIn('로그 파일 전체',current_log_note)

    def test_archived_image_services_disclose_history_without_enabling_generation(self):
        current_service_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_service_records={current_record['service']:current_record for current_record in current_service_catalog['services']}
        for current_service_name in ('qwen-21','qwen-21-circular','seamless-tile','billboard-generator','building-generator','expression','floor-tile'):
            with self.subTest(service=current_service_name):
                current_service_record=current_service_records[current_service_name]
                self.assertIn('generate',{current_record['command'] for current_record in current_service_record['gateway_blocked']})
                current_limit_names={current_record['command'] for current_record in current_service_record['conditional_limitations']}
                self.assertTrue({'active','history','logs'}<=current_limit_names)

    def test_retired_resume_limitation_mentions_gateway_block(self):
        current_catalog_record=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_services_by_name={current_service_record['service']:current_service_record for current_service_record in current_catalog_record['services']}
        for current_service_name in ('floor-tile','seamless-tile'):
            with self.subTest(service=current_service_name):
                current_service_record=current_services_by_name[current_service_name]
                self.assertIn('resume',{current_block_record['command'] for current_block_record in current_service_record['gateway_blocked']})
                current_resume_note=next(current_limit_record['note'] for current_limit_record in current_service_record['conditional_limitations'] if current_limit_record['command']=='resume')
                self.assertIn('게이트웨이에서도 차단',current_resume_note)

    def test_legacy_cancellation_is_described_as_request_not_gpu_termination(self):
        current_service_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_service_records={current_record['service']:current_record for current_record in current_service_catalog['services']}
        for current_service_name in ('qwen-21','floor-tile','music-minimax','character-animation'):
            with self.subTest(service=current_service_name):
                current_cancel_note=next(current_record['note'] for current_record in current_service_records[current_service_name]['conditional_limitations'] if current_record['command']=='cancel')
                self.assertIn('중지 요청',current_cancel_note)
                self.assertIn('GPU 프로세스',current_cancel_note)
                self.assertIn('확인',current_cancel_note)

    def test_fun_resume_capability_exposes_preview_and_submission(self):
        current_catalog_record = self.hermes_service_manager.execute_hermes_command('hermes-capabilities', {})
        current_capability_records = {current_record['command']:current_record for current_record in current_catalog_record['records']}
        current_preview_record = current_capability_records['hermes-video-resume-preview']
        self.assertEqual(current_preview_record['effect'],'recovery_possible')
        self.assertEqual(current_preview_record['gpu'],'none')
        self.assertIn('복구할 수',current_preview_record['note'])
        current_preview_schema = current_preview_record['payload_schema']
        current_submit_schema = current_capability_records['hermes-video-resume-submit']['payload_schema']
        self.assertIn('wan22-fun-control', current_preview_schema['properties']['service']['enum'])
        self.assertIn('wan22-fun-control', current_submit_schema['properties']['service']['enum'])
        current_services = self.hermes_service_manager.execute_hermes_command('hermes-service-registration', {})['services']
        current_fun_record = next(current_record for current_record in current_services if current_record['service'] == 'wan22-fun-control')
        self.assertIn('hermes-video-resume-preview', current_fun_record['hermes_links'])
        self.assertIn('hermes-video-resume-submit', current_fun_record['hermes_links'])

    def test_cleanup_catalog_excludes_gateway_blocked_services(self):
        from workflow.domains.hermes_agent.cleanup_preview_observer import read_hermes_cleanup_preview
        current_catalog_record = self.hermes_service_manager.execute_hermes_command('hermes-service-registration', {})
        current_service_records = {current_record['service']:current_record for current_record in current_catalog_record['services']}
        self.assertNotIn('hermes-cleanup-preview', current_service_records['qwen-2511']['hermes_links'])
        self.assertIn('hermes-cleanup-preview', current_service_records['flux-image']['hermes_links'])
        with patch('workflow.common.management_client.execute_remote_management_command') as current_gateway_mock:
            with self.assertRaisesRegex(ValueError, '폐기'):
                read_hermes_cleanup_preview('qwen-2511')
            current_gateway_mock.assert_not_called()
        with patch('generators.music.service_constants.inspect_retired_audio_rejection', return_value='정리 조회 정책 제한'), patch('workflow.common.management_client.execute_remote_management_command') as current_gateway_mock:
            with self.assertRaisesRegex(ValueError, '정리 조회 정책 제한'):
                read_hermes_cleanup_preview('music-heartmula')
            current_gateway_mock.assert_not_called()

    def test_cleanup_preview_discloses_kimodo_exception(self):
        current_service_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_service_records={current_record['service']:current_record for current_record in current_service_catalog['services']}
        for current_service_name in ('music-heartmula','prompt-translation','flux-image','wan22-vace','kimodo','floor-tile'):
            with self.subTest(service=current_service_name):
                current_preview_note=next(current_record['note'] for current_record in current_service_records[current_service_name]['conditional_limitations'] if current_record['command']=='history-reset-preview')
                self.assertIn('삭제 없이',current_preview_note)
                self.assertIn('Hermes는 경로 없는 요약만 조회하며 실제 삭제는 지원하지 않는다',current_preview_note)
                if current_service_name=='kimodo':self.assertIn('확인 불가 항목은 제외',current_preview_note)
                else:self.assertIn('전체 정리 대상',current_preview_note)

    def test_video_source_active_and_history_disclose_recovery(self):
        current_service_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_service_records={current_record['service']:current_record for current_record in current_service_catalog['services']}
        for current_service_name in ('dwpose','wan22-animate2','wan22-fun-control','wan22-vace','kimodo'):
            with self.subTest(service=current_service_name):
                current_limit_records=current_service_records[current_service_name]['conditional_limitations']
                for current_command_name in ('active','history','status'):
                    current_matching_notes=[current_record['note'] for current_record in current_limit_records if current_record['command']==current_command_name]
                    self.assertTrue(any('복구' in current_note for current_note in current_matching_notes))

    def test_field_database_save_limit_is_discoverable(self):
        current_service_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_assets_record=next(current_record for current_record in current_service_catalog['services'] if current_record['service']=='map-assets')
        current_save_limit=next(current_item for current_item in current_assets_record['conditional_limitations'] if current_item['command']=='map-edit-save')
        self.assertIn('DB 모드',current_save_limit['note'])
        self.assertIn('차단',current_save_limit['note'])
        current_search_record=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{'query':'야외 맵 DB 모드'})
        self.assertIn('map-assets',{current_record['service'] for current_record in current_search_record['services']})

    def test_generator_reservation_recovery_is_discoverable_for_supported_services(self):
        current_service_records=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_service_mapping={current_record['service']:current_record for current_record in current_service_records['services']}
        for current_service_name in ('kimodo','flux-expression','prompt-translation','music-heartmula','wan22-fun-control'):
            self.assertTrue({'hermes-generator-reservation-inspect','hermes-generator-reservation-recover','hermes-generator-reservation-receipt'} <= set(current_service_mapping[current_service_name]['hermes_links']))

    def test_generator_reservation_inspection_uses_validated_gateway(self):
        from workflow.common.management_gateway import resolve_management_command
        current_request={'service':'kimodo','job_id':'2026-11-18_12-00-00-12345678'}
        self.assertEqual(resolve_management_command('hermes-agent','hermes-generator-reservation-inspect',current_request),('POST','/hermes-agent/hermes-generator-reservation-inspect'))
        with patch('workflow.domains.hermes_agent.reservation_observer.inspect_generator_reservation_identity',return_value={'executor':'unverified'}) as current_inspect_mock:
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-generator-reservation-inspect',current_request),{'executor':'unverified'})
            current_inspect_mock.assert_called_once_with(current_request['service'],current_request['job_id'])
        with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-generator-reservation-inspect',{**current_request,'extra':True})

    def test_other_service_dead_executor_reservation_is_visible_as_unverified(self):
        import os
        from workflow.domains.hermes_agent.management_observer import read_hermes_gpu_reservation_snapshot
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_active_path=Path(current_directory_name)/'active'
            current_active_path.mkdir()
            (current_active_path/'image.json').write_text(json.dumps({'service':'image','pid':os.getpid(),'pid_start_token':'0','required_memory_mib':1024}))
            current_result_value=read_hermes_gpu_reservation_snapshot(current_directory_name)
            self.assertEqual(current_result_value['records'][0]['state'],'cleanup_unverified')

    def test_wan_fun_prepare_reservation_rejects_other_source_and_duplicate(self):
        from workflow.common import gpu_job_queue
        from workflow.domains.hermes_agent.reservation_observer import find_generator_reservation_record
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_workflow_root=Path(current_temporary_directory)
            current_job_identifier='2026-11-20_20-02-00-prepare'
            current_job_directory=current_workflow_root/'.tmp'/'test'/'wan22-fun-control'/current_job_identifier
            current_job_directory.mkdir(parents=True)
            current_active_directory=current_workflow_root/'active'
            current_active_directory.mkdir()
            current_reservation_record={'service':'wan-fun-prepare','path':str(current_job_directory),'required_memory_mib':6144}
            (current_active_directory/'one.json').write_text(json.dumps(current_reservation_record))
            with patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_workflow_root):
                self.assertEqual(find_generator_reservation_record(current_active_directory,'wan22-fun-control',current_job_identifier)[2],6144)
                with self.assertRaises(ValueError):find_generator_reservation_record(current_active_directory,'kimodo',current_job_identifier)
                (current_active_directory/'two.json').write_text(json.dumps(current_reservation_record))
                with self.assertRaises(ValueError):find_generator_reservation_record(current_active_directory,'wan22-fun-control',current_job_identifier)
            self.assertEqual(len(list(current_active_directory.glob('*.json'))),2)

    def test_wan_fun_legacy_prepare_reservation_preserves_verified_identity(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_gpu_reservation_snapshot
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_workflow_root=Path(current_temporary_directory)
            current_job_identifier='2026-11-20_20-02-00-prepare'
            current_job_directory=current_workflow_root/'.tmp'/'test'/'wan22-fun-control'/current_job_identifier
            current_job_directory.mkdir(parents=True)
            current_queue_directory=current_workflow_root/'queue'
            (current_queue_directory/'active').mkdir(parents=True)
            current_reservation_path=current_queue_directory/'active'/'prepare.json'
            current_reservation_record={'service':'wan-fun-prepare','path':str(current_job_directory),'required_memory_mib':6144,'cleanup_unverified':True}
            current_reservation_path.write_text(json.dumps(current_reservation_record))
            with patch('workflow.common.gpu_job_queue.WORKFLOW_ROOT_DIRECTORY',current_workflow_root):
                current_snapshot_value=read_hermes_gpu_reservation_snapshot(current_queue_directory)
            current_record_value=current_snapshot_value['records'][0]
            self.assertEqual(current_record_value['job_id'],current_job_identifier)
            self.assertEqual(current_record_value['source_service'],'wan22-fun-control')
            self.assertNotIn(str(current_workflow_root),str(current_snapshot_value))
            current_reservation_record['service']='other-service'
            current_reservation_path.write_text(json.dumps(current_reservation_record))
            self.assertIsNone(read_hermes_gpu_reservation_snapshot(current_queue_directory)['records'][0]['job_id'])

    def test_oversized_reservation_is_unknown_and_blocks_identity(self):
        from workflow.domains.hermes_agent.delegation_store import HERMES_DELEGATION_RECORD_MAXIMUM_BYTES
        from workflow.domains.hermes_agent.management_observer import read_hermes_gpu_reservation_snapshot
        from workflow.domains.hermes_agent.reservation_observer import find_generator_reservation_record
        from workflow.domains.hermes_agent.writer_reservation import find_writer_reservation_record
        with tempfile.TemporaryDirectory() as current_root_name:
            current_root_path=Path(current_root_name)
            current_active_path=current_root_path/'active'
            current_active_path.mkdir()
            (current_active_path/'large.json').write_bytes(b'x'*(HERMES_DELEGATION_RECORD_MAXIMUM_BYTES+1))
            current_snapshot_record=read_hermes_gpu_reservation_snapshot(current_root_path)
            self.assertEqual(current_snapshot_record['records'][0]['state'],'unknown')
            with self.assertRaises(ValueError):find_generator_reservation_record(current_active_path,'kimodo','job-1')
            with self.assertRaises(ValueError):find_writer_reservation_record(current_active_path,'20261118-120000-12345678')

    def test_unverified_writer_cleanup_reservation_is_visible(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_gpu_reservation_snapshot
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_active_path=current_root_path/'active'
            current_active_path.mkdir()
            (current_active_path/'writer.json').write_text(json.dumps({'service':'writer-agent','path':'/private/jobs/20261118-120000-12345678','required_memory_mib':16384,'cleanup_unverified':True,'worker_pgid':123}))
            current_result_value=read_hermes_gpu_reservation_snapshot(current_root_path)
            self.assertEqual(current_result_value['records'][0]['state'],'cleanup_unverified')
            self.assertEqual(current_result_value['records'][0]['job_id'],'20261118-120000-12345678')
            self.assertNotIn('/private',str(current_result_value))
            (current_active_path/'writer.json').write_text(json.dumps({'service':'writer-agent','required_memory_mib':16384,'cleanup_unverified':'yes'}))
            self.assertEqual(read_hermes_gpu_reservation_snapshot(current_root_path)['records'][0]['state'],'unknown')

    def test_handoff_capability_schema_requires_confirmed_revision_and_real_interface(self):
        catalog=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        records={record['command']:record for record in catalog['records']}
        approve=records['hermes-gpu-handoff-approve']
        fields=approve['payload_schema']['properties']
        self.assertEqual(fields['confirmed'],{'const':True})
        self.assertEqual(fields['review_hash']['pattern'],'^[a-f0-9]{64}$')
        self.assertEqual(fields['resident_id']['pattern'],'^[A-Za-z0-9_-]{8,80}$')
        self.assertNotIn('mcp',approve['interfaces'])
        self.assertNotIn('Kimodo',fields['request'].get('validation',''))
        cancel=records['hermes-gpu-handoff-cancel']['payload_schema']['properties']
        self.assertEqual(cancel['expected_revision'],{'type':'integer','minimum':1})

    def test_capabilities_use_registered_gateway_and_strict_empty_input(self):
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, MANAGEMENT_COMMAND_ROUTES
        current_catalog_value = self.hermes_service_manager.execute_hermes_command('hermes-capabilities', {})
        self.assertEqual(current_catalog_value['version'], 1)
        self.assertTrue(current_catalog_value['records'])
        self.assertEqual(current_catalog_value['unlisted_commands'],[])
        current_self_service=next(current_record for current_record in self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})['services'] if current_record['service']=='hermes-agent')
        self.assertIn('hermes-capabilities',current_self_service['hermes_links'])
        self.assertIn('hermes-session-view',current_self_service['hermes_links'])
        current_capabilities_by_name={current_record['command']:current_record for current_record in current_catalog_value['records']}
        for current_command_name in ('hermes-video-proposal','hermes-kimodo-proposal','hermes-diff','hermes-delegation-status','hermes-flux-delegation-history'):
            self.assertEqual(current_capabilities_by_name[current_command_name]['effect'],'local_bookkeeping')
        self.assertEqual(current_capabilities_by_name['hermes-management-status']['effect'],'local_bookkeeping')
        self.assertEqual(current_capabilities_by_name['hermes-management-status']['gpu'],'inspection')
        self.assertIn('amd-smi',current_capabilities_by_name['hermes-management-status']['note'])
        self.assertEqual(current_capabilities_by_name['hermes-kimodo-build-status']['gpu'],'none')
        self.assertIn('캐시 유효성',current_capabilities_by_name['hermes-kimodo-build-status']['note'])
        current_command_list=MANAGEMENT_SERVICE_COMMANDS['hermes-agent']
        with patch.dict(MANAGEMENT_SERVICE_COMMANDS, {'hermes-agent':[*current_command_list,'hermes-new-command']}):
            current_drift_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities', {})
        self.assertEqual(current_drift_value['unlisted_commands'],['hermes-new-command'])
        for current_record_value in current_catalog_value['records']:
            self.assertIn(current_record_value['command'], MANAGEMENT_SERVICE_COMMANDS['hermes-agent'])
            self.assertEqual(current_record_value['method'], MANAGEMENT_COMMAND_ROUTES[current_record_value['command']][0])
            self.assertIn(current_record_value['effect'], ('read', 'write', 'enqueue', 'recovery_possible', 'cancel_request', 'local_bookkeeping'))
            self.assertEqual(current_record_value['payload_schema']['required'], current_record_value['required'])
            self.assertEqual(set(current_record_value['payload_schema']['properties']), set(current_record_value['required'] + current_record_value['optional']), current_record_value['command'])
            self.assertFalse(current_record_value['payload_schema']['additionalProperties'])
        for current_command_name in ('hermes-video-proposal','hermes-audio-proposal'):
            self.assertNotIn('service',current_capabilities_by_name[current_command_name]['payload_schema']['properties'])
        self.assertIn('service',current_capabilities_by_name['hermes-delegate-video']['payload_schema']['properties'])
        self.assertIn('service',current_capabilities_by_name['hermes-delegate-audio']['payload_schema']['properties'])
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-capabilities', {'extra':True})

    def test_service_receipt_discovery_matches_allowed_services_and_registration(self):
        from jsonschema import Draft202012Validator
        from workflow.domains.hermes_agent.delegation_store import list_hermes_service_receipt_names
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration
        current_names = list_hermes_service_receipt_names()
        self.assertEqual(len(current_names), len(set(current_names)))
        current_catalog = self.hermes_service_manager.execute_hermes_command('hermes-capabilities', {})
        current_schema = next(item['payload_schema'] for item in current_catalog['records'] if item['command']=='hermes-service-receipt')
        current_validator = Draft202012Validator(current_schema)
        self.assertEqual(set(current_schema['properties']['service']['enum']), set(current_names))
        current_registration = {item['service']:item for item in list_management_service_registration()['services']}
        with patch('workflow.domains.hermes_agent.delegation_store.HermesDelegationStore.read_service_delegation', return_value={'state':'not_found'}) as current_read:
            for current_service in current_names:
                with self.subTest(service=current_service):
                    current_input = {'service':current_service, 'request_id':'request_123'}
                    self.assertTrue(current_validator.is_valid(current_input))
                    self.assertIn('hermes-service-receipt', current_registration[current_service]['hermes_links'])
                    self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-service-receipt',current_input), {'state':'not_found','request_id':current_input['request_id']})
            self.assertEqual(current_read.call_count, len(current_names))
            self.assertFalse(current_validator.is_valid({'service':'kimodo','request_id':'request_123'}))
            with self.assertRaises(ValueError):
                self.hermes_service_manager.execute_hermes_command('hermes-service-receipt',{'service':'kimodo','request_id':'request_123'})

    def test_service_discovery_includes_kimodo_proposal(self):
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration,search_management_service_registration
        current_service_records=list_management_service_registration()['services']
        current_kimodo_record=next(current_record for current_record in current_service_records if current_record['service']=='kimodo')
        self.assertIn('hermes-kimodo-proposal',current_kimodo_record['hermes_links'])
        current_search_result=search_management_service_registration({'query':'Kimodo 제안 읽기'})
        self.assertIn('kimodo',[current_record['service'] for current_record in current_search_result['services']])

    def test_service_links_resolve_and_include_receipt_and_map_discovery(self):
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration,list_hermes_capability_catalog
        current_catalog_names={current_record['command'] for current_record in list_hermes_capability_catalog()['records']}
        current_service_records={current_record['service']:current_record for current_record in list_management_service_registration()['services']}
        for current_service_name,current_service_record in current_service_records.items():
            with self.subTest(service=current_service_name):
                current_link_names=current_service_record['hermes_links']
                self.assertEqual(len(current_link_names),len(set(current_link_names)))
                self.assertFalse(set(current_link_names)-current_catalog_names)
        self.assertIn('hermes-delegation-status',current_service_records['kimodo']['hermes_links'])
        self.assertIn('hermes-world-map',current_service_records['map-assets']['hermes_links'])
        self.assertIn('hermes-model-prepare-history',current_service_records['hermes-model']['hermes_links'])

    def test_archived_generator_reservation_limit_is_discoverable(self):
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration,search_management_service_registration
        current_service_records={current_record['service']:current_record for current_record in list_management_service_registration()['services']}
        for current_service_name in ('billboard-generator','building-generator'):
            with self.subTest(service=current_service_name):
                current_record_value=current_service_records[current_service_name]
                self.assertIn('hermes-generator-reservation-inspect',current_record_value['hermes_links'])
                self.assertTrue(any('건물 호환 요청인지 구분하지 못한다' in current_limit['note'] for current_limit in current_record_value['conditional_limitations']))
        current_search_result=search_management_service_registration({'query':'건물 호환 요청인지'})
        self.assertIn('billboard-generator',[current_record['service'] for current_record in current_search_result['services']])
        for current_service_name in ('qwen-21','qwen-21-circular','mannequin-generator','prop-generator','vegetation-generator','expression','seamless-tile','floor-tile'):
            self.assertIn('hermes-generator-reservation-inspect',current_service_records[current_service_name]['hermes_links'])

    def test_corrupt_session_does_not_hide_valid_history(self):
        import json
        current_root=self.hermes_service_manager.hermes_session_root
        current_root.mkdir(parents=True,exist_ok=True)
        current_valid_id='a'*32
        current_bad_id='b'*32
        current_valid_record={'version':1,'id':current_valid_id,'created_at':'2026-11-19','updated_at':'2026-11-19','messages':[{'text':'나무 작업'}]}
        (current_root/(current_valid_id+'.json')).write_text(json.dumps(current_valid_record))
        (current_root/(current_bad_id+'.json')).write_text('{invalid')
        current_page=self.hermes_service_manager.execute_hermes_command('hermes-session-list',{'offset':0,'query':'나무'})
        self.assertEqual([current_item['id'] for current_item in current_page['sessions']],[current_valid_id])
        self.assertEqual(current_page['unreadable_count'],1)
        current_old_snapshot=current_page['snapshot']
        (current_root/(current_bad_id+'.json')).unlink()
        with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-session-list',{'offset':0,'query':'나무','snapshot':current_old_snapshot})

    def test_session_pagination_reaches_old_sessions_and_detects_reordering(self):
        import json
        current_root=self.hermes_service_manager.hermes_session_root
        current_root.mkdir(parents=True,exist_ok=True)
        for current_index in range(105):
            current_identifier='%032x' % current_index
            current_time='2026-11-%02dT00:00:00Z' % (current_index//5+1)
            (current_root/(current_identifier+'.json')).write_text(json.dumps({'version':1,'id':current_identifier,'created_at':current_time,'updated_at':current_time,'messages':[]}))
        current_legacy=self.hermes_service_manager.execute_hermes_command('hermes-session-list',{})
        self.assertEqual(len(current_legacy['sessions']),100)
        self.assertTrue(current_legacy['truncated'])
        current_page=self.hermes_service_manager.execute_hermes_command('hermes-session-list',{'offset':0,'limit':30})
        current_snapshot=current_page['snapshot']
        for current_index in range(3):current_page=self.hermes_service_manager.execute_hermes_command('hermes-session-list',{'offset':current_page['next_offset'],'limit':30,'snapshot':current_snapshot})
        self.assertEqual(len(current_page['sessions']),15)
        self.assertNotIn(current_page['sessions'][-1]['id'],{item['id'] for item in current_legacy['sessions']})
        current_query=self.hermes_service_manager.execute_hermes_command('hermes-session-list',{'offset':0,'query':'00000000'})
        self.assertEqual(current_query['total'],105)
        current_path=current_root/(current_page['sessions'][-1]['id']+'.json')
        current_record=json.loads(current_path.read_text())
        current_record['updated_at']='2026-12-01T00:00:00Z'
        current_path.write_text(json.dumps(current_record))
        with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-session-list',{'offset':30,'snapshot':current_snapshot})
        with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-session-list',{'query':'bad\nquery'})
        with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-session-list',{'offset':30})

    def test_session_instruction_search_finds_old_sessions_without_returning_text(self):
        import json
        current_root=self.hermes_service_manager.hermes_session_root
        current_root.mkdir(parents=True,exist_ok=True)
        for current_index in range(105):
            current_identifier='%032x' % current_index
            current_time='2026-11-%02dT00:00:00Z' % (current_index//5+1)
            current_text='고유한 나무 빌보드' if current_index==0 else '일반 테스트'
            current_record={'version':1,'id':current_identifier,'created_at':current_time,'updated_at':current_time,'messages':[{'role':'user','text':current_text}]}
            (current_root/(current_identifier+'.json')).write_text(json.dumps(current_record,ensure_ascii=False))
        current_legacy=self.hermes_service_manager.execute_hermes_command('hermes-session-list',{})
        self.assertNotIn('0'*32,{item['id'] for item in current_legacy['sessions']})
        current_found=self.hermes_service_manager.execute_hermes_command('hermes-session-list',{'offset':0,'limit':30,'query':'나무 빌보드'})
        self.assertEqual(current_found['total'],1)
        self.assertEqual(current_found['sessions'][0]['id'],'0'*32)
        self.assertNotIn('고유한',str(current_found))
        current_first=self.hermes_service_manager.execute_hermes_command('hermes-session-list',{'offset':0,'limit':30,'query':'일반'})
        self.assertEqual(current_first['total'],104)
        current_path=current_root/(current_first['sessions'][0]['id']+'.json')
        current_record=json.loads(current_path.read_text())
        current_record['messages'][0]['text']='변경된 지시'
        current_path.write_text(json.dumps(current_record,ensure_ascii=False))
        with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-session-list',{'offset':30,'query':'일반','snapshot':current_first['snapshot']})
        with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-session-list',{'offset':30,'query':'다른 검색','snapshot':current_first['snapshot']})

    def test_history_pagination_preserves_legacy_and_detects_list_changes(self):
        from jsonschema import Draft202012Validator
        current_root=self.hermes_service_manager.hermes_storage_root
        current_root.mkdir(parents=True,exist_ok=True)
        for current_index in range(35):
            (current_root / ('2026-11-18_00-00-%02d-%08x' % (current_index,current_index))).mkdir()
        def current_read(current_path):
            return {'id':current_path.name,'request':{'prompt':'시험'},'status':{'status':'completed'},'result':None}
        with patch.object(self.hermes_service_manager,'read_hermes_job_record',side_effect=current_read):
            current_legacy=self.hermes_service_manager.execute_hermes_command('hermes-history',{})
            self.assertEqual(set(current_legacy),{'records'})
            self.assertEqual(len(current_legacy['records']),35)
            current_first=self.hermes_service_manager.execute_hermes_command('hermes-history',{'offset':0,'limit':30})
            self.assertEqual(current_first['total'],35)
            self.assertEqual(current_first['next_offset'],30)
            current_second=self.hermes_service_manager.execute_hermes_command('hermes-history',{'offset':30,'limit':30,'snapshot':current_first['snapshot']})
            self.assertEqual(len(current_second['records']),5)
            self.assertIsNone(current_second['next_offset'])
            self.assertFalse({item['id'] for item in current_first['records']} & {item['id'] for item in current_second['records']})
            with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-history',{'offset':30})
            with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-history',{'offset':0,'limit':True})
            (current_root/'2026-11-19_00-00-00-aaaaaaaa').mkdir()
            with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-history',{'offset':30,'snapshot':current_first['snapshot']})
        current_catalog=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_schema=next(item['payload_schema'] for item in current_catalog['records'] if item['command']=='hermes-history')
        current_validator=Draft202012Validator(current_schema)
        self.assertTrue(current_validator.is_valid({}))
        self.assertFalse(current_validator.is_valid({'offset':1}))
        self.assertTrue(current_validator.is_valid({'offset':1,'snapshot':'a'*64,'limit':30}))
        self.assertFalse(current_validator.is_valid({'limit':31}))

    def test_history_page_reaches_beyond_legacy_hundred_records(self):
        current_root=self.hermes_service_manager.hermes_storage_root
        current_root.mkdir(parents=True,exist_ok=True)
        for current_index in range(135):
            (current_root / ('2026-11-18_00-%02d-%02d-%08x' % (current_index//60,current_index%60,current_index))).mkdir()
        def current_read(current_path):
            return {'id':current_path.name,'request':{'prompt':'시험'},'status':{'status':'completed'},'result':None}
        with patch.object(self.hermes_service_manager,'read_hermes_job_record',side_effect=current_read):
            current_legacy=self.hermes_service_manager.execute_hermes_command('hermes-history',{})
            self.assertEqual(len(current_legacy['records']),100)
            current_page=self.hermes_service_manager.execute_hermes_command('hermes-history',{'offset':0,'limit':30})
            for current_index in range(4):
                current_page=self.hermes_service_manager.execute_hermes_command('hermes-history',{'offset':current_page['next_offset'],'limit':30,'snapshot':current_page['snapshot']})
            self.assertEqual(current_page['offset'],120)
            self.assertEqual(len(current_page['records']),15)
            self.assertIsNone(current_page['next_offset'])
            self.assertNotIn(current_page['records'][-1]['id'],{item['id'] for item in current_legacy['records']})

    def test_history_global_search_finds_older_jobs_and_detects_filter_changes(self):
        import json
        current_root=self.hermes_service_manager.hermes_storage_root
        current_root.mkdir(parents=True,exist_ok=True)
        for current_index in range(135):
            current_path=current_root/('2026-11-18_00-%02d-%02d-%08x' % (current_index//60,current_index%60,current_index))
            current_path.mkdir()
            (current_path/'request.json').write_text(json.dumps({'prompt':'특별한 오래된 지시' if current_index==0 else '일반 지시'},ensure_ascii=False))
            (current_path/'status.json').write_text(json.dumps({'status':'failed' if current_index<40 else 'completed'}))
        def current_read(current_path):
            return {'id':current_path.name,'request':json.loads((current_path/'request.json').read_text()),'status':json.loads((current_path/'status.json').read_text()),'result':None}
        with patch.object(self.hermes_service_manager,'read_hermes_job_record',side_effect=current_read):
            current_search=self.hermes_service_manager.execute_hermes_command('hermes-history',{'offset':0,'limit':30,'query':'특별한','status':'failed'})
            self.assertEqual(current_search['total'],1)
            self.assertEqual(current_search['records'][0]['id'],'2026-11-18_00-00-00-00000000')
            current_first=self.hermes_service_manager.execute_hermes_command('hermes-history',{'offset':0,'limit':30,'status':'failed'})
            self.assertEqual(current_first['total'],40)
            current_second=self.hermes_service_manager.execute_hermes_command('hermes-history',{'offset':30,'limit':30,'status':'failed','snapshot':current_first['snapshot']})
            self.assertEqual(len(current_second['records']),10)
            current_changed=current_root/current_first['records'][0]['id']/'status.json'
            current_changed.write_text(json.dumps({'status':'completed'}))
            with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-history',{'offset':30,'status':'failed','snapshot':current_first['snapshot']})
            with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-history',{'offset':30,'status':'completed','snapshot':current_first['snapshot']})
            with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-history',{'query':'bad\nquery'})

    def test_history_exact_job_id_precedes_prompt_mentions(self):
        current_root_path=self.hermes_service_manager.hermes_storage_root
        current_root_path.mkdir(parents=True,exist_ok=True)
        current_target_identifier='2026-11-18_00-00-00-00000000'
        for current_index_value in range(35):
            current_job_path=current_root_path/('2026-11-18_00-00-%02d-%08x' % (current_index_value,current_index_value))
            current_job_path.mkdir()
            (current_job_path/'request.json').write_text(json.dumps({'prompt':'조회 '+current_target_identifier}))
            (current_job_path/'status.json').write_text(json.dumps({'status':'completed'}))
        def read_current_history_record(current_job_path):
            return {'id':current_job_path.name,'request':json.loads((current_job_path/'request.json').read_text()),'status':{'status':'completed'},'result':None}
        with patch.object(self.hermes_service_manager,'read_hermes_job_record',side_effect=read_current_history_record):
            current_first_page=self.hermes_service_manager.execute_hermes_command('hermes-history',{'offset':0,'limit':30,'query':current_target_identifier})
            self.assertEqual(current_first_page['total'],35)
            self.assertEqual(current_first_page['records'][0]['id'],current_target_identifier)
            current_second_page=self.hermes_service_manager.execute_hermes_command('hermes-history',{'offset':30,'limit':30,'query':current_target_identifier,'snapshot':current_first_page['snapshot']})
            self.assertEqual(len(current_second_page['records']),5)
            self.assertNotIn(current_target_identifier,[current_record_value['id'] for current_record_value in current_second_page['records']])
            current_other_ids=[current_record_value['id'] for current_record_value in current_first_page['records'][1:]]+[current_record_value['id'] for current_record_value in current_second_page['records']]
            self.assertEqual(current_other_ids,sorted(current_other_ids,reverse=True))
            (current_root_path/'2026-11-18_00-00-34-00000022'/'request.json').write_text(json.dumps({'prompt':'다른 내용'}))
            with self.assertRaises(ValueError):
                self.hermes_service_manager.execute_hermes_command('hermes-history',{'offset':30,'limit':30,'query':current_target_identifier,'snapshot':current_first_page['snapshot']})

    def test_capability_catalog_fits_isolated_bridge_response(self):
        import json
        from workflow.domains.hermes_agent.capabilities import list_hermes_capability_catalog,search_hermes_capability_catalog
        from workflow.domains.hermes_agent.management_bridge import HERMES_OBSERVER_MAX_RESPONSE
        current_full_record=list_hermes_capability_catalog()
        self.assertLessEqual(len(json.dumps(current_full_record,ensure_ascii=False,allow_nan=False).encode('utf-8'))+1,HERMES_OBSERVER_MAX_RESPONSE)
        for current_offset_value in range(0,len(current_full_record['records']),20):
            current_page_record=search_hermes_capability_catalog({'offset':current_offset_value,'limit':20})
            self.assertLessEqual(len(json.dumps(current_page_record,ensure_ascii=False,allow_nan=False).encode('utf-8'))+1,HERMES_OBSERVER_MAX_RESPONSE)

    def test_capability_catalog_records_are_independent_across_reads(self):
        from workflow.domains.hermes_agent.capabilities import list_hermes_capability_catalog
        current_first_catalog=list_hermes_capability_catalog()
        current_first_record=next(current_record for current_record in current_first_catalog['records'] if current_record['command']=='hermes-video-resume-preview')
        current_first_record['required'].append('unexpected')
        current_first_record['interfaces'].append('unexpected')
        current_first_record['payload_schema']['properties']['job_id']['pattern']='changed'
        current_next_catalog=list_hermes_capability_catalog()
        current_next_record=next(current_record for current_record in current_next_catalog['records'] if current_record['command']=='hermes-video-resume-preview')
        self.assertNotIn('unexpected',current_next_record['required'])
        self.assertNotIn('unexpected',current_next_record['interfaces'])
        self.assertNotEqual(current_next_record['payload_schema']['properties']['job_id']['pattern'],'changed')

    def test_service_limitations_are_independent_across_catalog_reads(self):
        from workflow.domains.hermes_agent.capabilities import list_management_service_registration
        current_first_catalog=list_management_service_registration()
        current_first_service=next(current_record for current_record in current_first_catalog['services'] if current_record['service']=='character-animation')
        current_first_limit=next(current_record for current_record in current_first_service['conditional_limitations'] if current_record['command']=='anchor-load')
        current_original_note=current_first_limit['note']
        current_first_limit['note']='changed'
        current_next_catalog=list_management_service_registration()
        current_next_service=next(current_record for current_record in current_next_catalog['services'] if current_record['service']=='character-animation')
        current_next_limit=next(current_record for current_record in current_next_service['conditional_limitations'] if current_record['command']=='anchor-load')
        self.assertEqual(current_next_limit['note'],current_original_note)

    def test_mcp_only_input_lists_are_independent_across_catalog_reads(self):
        from workflow.domains.hermes_agent.capabilities import list_hermes_capability_catalog
        current_first_catalog=list_hermes_capability_catalog()
        current_first_catalog['mcp_only_tools'][0]['required'].append('unexpected')
        current_first_catalog['mcp_only_tools'][0]['optional'].append('unexpected')
        current_next_catalog=list_hermes_capability_catalog()
        self.assertEqual(current_next_catalog['mcp_only_tools'][0]['required'],[])
        self.assertEqual(current_next_catalog['mcp_only_tools'][0]['optional'],[])

    def test_isolated_capability_search_includes_required_and_optional_inputs(self):
        from workflow.domains.hermes_agent.capabilities import search_hermes_capability_catalog
        for current_query_value in ('animation_version', 'snapshot'):
            current_offset_value=0
            current_command_names=[]
            while True:
                current_page_record=search_hermes_capability_catalog({'query':current_query_value,'offset':current_offset_value,'limit':20})
                current_command_names.extend(current_record['command'] for current_record in current_page_record['records'])
                if current_page_record['next_offset'] is None:
                    break
                current_offset_value=current_page_record['next_offset']
            self.assertIn('hermes-anchor-history-observe',current_command_names)

    def test_verification_schema_uses_registered_modules(self):
        from jsonschema import Draft202012Validator
        from workflow.tests.run_management_audit import MANAGEMENT_AUDIT_MODULES
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_schemas_by_name={current_record['command']:current_record['payload_schema'] for current_record in current_catalog_value['records']}
        for current_command_name,current_session_fields in (('hermes-submit',{}),('hermes-session-submit',{'session_id':'a'*32})):
            current_schema_value=current_schemas_by_name[current_command_name]
            self.assertEqual(current_schema_value['properties']['verification_modules']['items']['enum'],list(MANAGEMENT_AUDIT_MODULES))
            current_validator_value=Draft202012Validator(current_schema_value)
            current_payload_value={'request_id':'request_123','prompt':'검토',**current_session_fields}
            self.assertTrue(current_validator_value.is_valid({**current_payload_value,'verification_modules':[MANAGEMENT_AUDIT_MODULES[0]]}))
            self.assertFalse(current_validator_value.is_valid({**current_payload_value,'verification_modules':['not.registered']}))

    def test_submission_schema_rejects_blank_prompt_and_duplicate_modules(self):
        from jsonschema import Draft202012Validator
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_schemas_by_name={current_record['command']:current_record['payload_schema'] for current_record in current_catalog_value['records']}
        for current_command_name,current_session_fields in (('hermes-submit',{}),('hermes-session-submit',{'session_id':'a'*32})):
            current_validator_value=Draft202012Validator(current_schemas_by_name[current_command_name])
            current_payload_value={'request_id':'request_123','prompt':'검토',**current_session_fields}
            self.assertTrue(current_validator_value.is_valid(current_payload_value))
            self.assertFalse(current_validator_value.is_valid({**current_payload_value,'prompt':'  \n '}))
            self.assertFalse(current_validator_value.is_valid({**current_payload_value,'verification_modules':['module','module']}))

    def test_priority_capability_uses_gateway_and_retirement_policy(self):
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS
        from workflow.domains.hermes_agent.priority_observer import validate_hermes_priority_target
        current_expected_services=set()
        for current_service_name in MANAGEMENT_SERVICE_COMMANDS:
            try:validate_hermes_priority_target(current_service_name,'2026-11-20_12-00-00-abcdef12')
            except ValueError:continue
            current_expected_services.add(current_service_name)
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        for current_record in current_catalog_value['records']:
            if current_record['command'] in ('hermes-priority-preview','hermes-priority-submit'):
                self.assertEqual(set(current_record['payload_schema']['properties']['service']['enum']),current_expected_services)
        self.assertIn('kimodo',current_expected_services)
        self.assertNotIn('qwen-21',current_expected_services)
        self.assertNotIn('music-minimax',current_expected_services)

    def test_capture_status_capability_lists_only_supported_services(self):
        from jsonschema import Draft202012Validator
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_schema_value=next(current_record['payload_schema'] for current_record in current_catalog_value['records'] if current_record['command']=='hermes-capture-status')
        current_validator_value=Draft202012Validator(current_schema_value)
        for current_service_name in ('map-review','character-review'):
            self.assertTrue(current_validator_value.is_valid({'request_id':'request_123','service':current_service_name}))
        self.assertFalse(current_validator_value.is_valid({'request_id':'request_123','service':'other'}))

    def test_model_capability_services_match_runtime_catalog(self):
        from workflow.common.model_management_catalog import MODEL_PREPARATION_SERVICES
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_schemas_by_name={current_record['command']:current_record['payload_schema'] for current_record in current_catalog_value['records']}
        current_expected_services={current_name for _,current_name in MODEL_PREPARATION_SERVICES}
        for current_command_name in ('hermes-model-readiness','hermes-model-prepare','hermes-model-prepare-status'):
            current_service_schema=current_schemas_by_name[current_command_name]['properties']['service']
            self.assertEqual(set(current_service_schema['enum']),current_expected_services)
            self.assertIn('허용 여부',current_service_schema['note'])

    def test_source_and_reservation_capability_services_match_runtime(self):
        from workflow.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES,SOURCE_HISTORY_AUDIO_SERVICES
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_schemas_by_name={current_record['command']:current_record['payload_schema'] for current_record in current_catalog_value['records']}
        self.assertEqual(set(current_schemas_by_name['hermes-generator-source-history']['properties']['service']['enum']),set(SOURCE_HISTORY_GENERATOR_SERVICES))
        current_expected_services=(set(SOURCE_HISTORY_GENERATOR_SERVICES)|set(SOURCE_HISTORY_AUDIO_SERVICES)) - {'writer-agent'}
        for current_command_name in ('hermes-generator-reservation-inspect','hermes-generator-reservation-recover'):
            self.assertEqual(set(current_schemas_by_name[current_command_name]['properties']['service']['enum']),current_expected_services)

    def test_reservation_capability_accepts_legacy_job_identifier(self):
        from jsonschema import Draft202012Validator
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_schemas_by_name={current_record['command']:current_record['payload_schema'] for current_record in current_catalog_value['records']}
        current_validator_value=Draft202012Validator(current_schemas_by_name['hermes-generator-reservation-inspect'])
        self.assertTrue(current_validator_value.is_valid({'service':'kimodo','job_id':'legacy-job_1'}))
        self.assertFalse(current_validator_value.is_valid({'service':'kimodo','job_id':'../other'}))
        current_recover_validator=Draft202012Validator(current_schemas_by_name['hermes-generator-reservation-recover'])
        self.assertTrue(current_recover_validator.is_valid({'request_id':'request_123','service':'kimodo','job_id':'legacy-job_1','review_sha256':'a'*64,'outside_processes_checked':True}))

    def test_writer_search_capability_uses_writer_job_identifier(self):
        from jsonschema import Draft202012Validator
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_schema_value=next(current_record['payload_schema'] for current_record in current_catalog_value['records'] if current_record['command']=='hermes-writer-job-search-paths')
        current_validator_value=Draft202012Validator(current_schema_value)
        self.assertTrue(current_validator_value.is_valid({'job_id':'20261120-120000-abcdef12'}))
        self.assertFalse(current_validator_value.is_valid({'job_id':'2026-11-20_12-00-00-abcdef12'}))

    def test_keyframe_capability_schema_matches_batch_contract(self):
        from jsonschema import Draft202012Validator
        from workflow.domains.kimodo.keyframe_storage import KIMODO_KEYFRAME_LIMIT
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_record_value=next(record for record in current_catalog_value['records'] if record['command']=='hermes-kimodo-keyframe-validate')
        current_schema_value=current_record_value['payload_schema']
        self.assertEqual(current_schema_value['properties']['keyframes']['maxItems'],KIMODO_KEYFRAME_LIMIT)
        current_validator_value=Draft202012Validator(current_schema_value)
        self.assertTrue(current_validator_value.is_valid({'frames':30,'keyframes':[{'id':'a'*32,'frame':1}]}))
        self.assertFalse(current_validator_value.is_valid({'frames':30,'keyframes':[{'id':'invalid','frame':1}]}))
        self.assertFalse(current_validator_value.is_valid({'frames':30,'keyframes':[{'id':'a'*32,'frame':1,'extra':True}]}))
        self.assertFalse(current_validator_value.is_valid({'frames':30,'keyframes':[{'id':'a'*32,'frame':1}]*(KIMODO_KEYFRAME_LIMIT+1)}))

    def test_capability_schema_describes_pagination_and_optional_filters(self):
        from jsonschema import Draft202012Validator
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities', {})
        current_schemas_by_command={record['command']:record['payload_schema'] for record in current_catalog_value['records']}
        current_keyframe_validator=Draft202012Validator(current_schemas_by_command['hermes-kimodo-keyframes'])
        self.assertTrue(current_keyframe_validator.is_valid({'snapshot':None}))
        self.assertTrue(current_keyframe_validator.is_valid({'snapshot':'a'*64}))
        self.assertFalse(current_keyframe_validator.is_valid({'snapshot':'invalid'}))
        current_sprite_validator=Draft202012Validator(current_schemas_by_command['hermes-sprite-detail'])
        self.assertTrue(current_sprite_validator.is_valid({'path':'assets/characters/default/animations/sheet.png','offset':0,'snapshot':None}))
        self.assertFalse(current_sprite_validator.is_valid({'path':'assets/characters/default/animations/sheet.png','offset':1}))
        self.assertFalse(current_sprite_validator.is_valid({'path':'assets/characters/default/animations/sheet.png','offset':1,'snapshot':None}))
        self.assertTrue(current_sprite_validator.is_valid({'path':'assets/characters/default/animations/sheet.png','offset':1,'snapshot':'a'*64}))
        current_world_validator=Draft202012Validator(current_schemas_by_command['hermes-world-map'])
        self.assertTrue(current_world_validator.is_valid({}))
        self.assertTrue(current_world_validator.is_valid({'map':'forest'}))
        self.assertFalse(current_world_validator.is_valid({'map':None}))
        self.assertTrue(Draft202012Validator(current_schemas_by_command['hermes-billboard-catalog']).is_valid({'category':None}))
        self.assertFalse(Draft202012Validator(current_schemas_by_command['hermes-sprite-catalog']).is_valid({'query':'first\nsecond'}))
        current_field_validator=Draft202012Validator(current_schemas_by_command['hermes-field-region'])
        self.assertTrue(current_field_validator.is_valid({'map':'forest','revision':None}))
        self.assertFalse(current_field_validator.is_valid({'map':'forest','revision':''}))
        self.assertFalse(current_field_validator.is_valid({'map':'forest','offset':1}))
        self.assertFalse(current_field_validator.is_valid({'map':'forest','offset':1,'revision':None}))
        self.assertTrue(current_field_validator.is_valid({'map':'forest','offset':1,'revision':'asset:abc'}))

    def test_writer_material_schema_matches_pagination_validation(self):
        from jsonschema import Draft202012Validator
        from generators.writer_agent.material_pages import validate_writer_material_request
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities', {})
        current_schema_value=next(current_record['payload_schema'] for current_record in current_catalog_value['records'] if current_record['command']=='hermes-writer-job-material')
        current_schema_validator=Draft202012Validator(current_schema_value)
        current_base_request={'job_id':'20261115-114927-8d274ccd','section':'search'}
        for current_fields_value,current_expected_validity in (({},True),({'snapshot':None},True),({'offset':1},False),({'offset':1,'snapshot':None},False),({'offset':1,'snapshot':'a'*64},True),({'snapshot':'bad'},False)):
            with self.subTest(fields=current_fields_value):
                current_request_value={**current_base_request,**current_fields_value}
                self.assertEqual(current_schema_validator.is_valid(current_request_value),current_expected_validity)
                try:
                    validate_writer_material_request(current_request_value)
                    current_runtime_validity=True
                except ValueError:
                    current_runtime_validity=False
                self.assertEqual(current_runtime_validity,current_expected_validity)

    def test_building_anchor_capability_describes_strict_draft(self):
        from jsonschema import Draft202012Validator
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_schema_value=next(item['payload_schema'] for item in current_catalog_value['records'] if item['command']=='hermes-building-preview')
        current_validator_value=Draft202012Validator(current_schema_value)
        current_draft_value={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1},'properties':{'anchorX':0.6,'anchorY':1}}
        self.assertTrue(current_validator_value.is_valid({'draft':current_draft_value}))
        for current_invalid_value in ({**current_draft_value,'generation':True},{**current_draft_value,'texture':'bad'}, {**current_draft_value,'unknown':1},{**current_draft_value,'properties':{'anchorX':17,'anchorY':1}},{**current_draft_value,'properties':{'anchorX':0.5,'anchorY':1,'displayWidthAdjustment':1}},{**current_draft_value,'properties':{'anchorX':0.5,'anchorY':1,'shadowShape':'circle'}}):
            with self.subTest(draft=current_invalid_value):self.assertFalse(current_validator_value.is_valid({'draft':current_invalid_value}))

    def test_building_catalog_schema_accepts_optional_null_snapshot(self):
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_schema_value=next(current_record['payload_schema'] for current_record in current_catalog_value['records'] if current_record['command']=='hermes-building-catalog')
        self.assertNotIn('snapshot',current_schema_value['required'])
        self.assertIn({'type':'null'},current_schema_value['properties']['snapshot']['anyOf'])
        self.assertEqual(current_schema_value['properties']['snapshot']['anyOf'][0]['pattern'],'^[a-f0-9]{64}$')
        self.assertIn('건물 목록',current_schema_value['properties']['snapshot']['anyOf'][0]['note'])

    def test_source_history_schema_requires_snapshot_for_later_page(self):
        from jsonschema import Draft202012Validator
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        for current_command_name,current_service_name in (('hermes-audio-source-history','music-heartmula'),('hermes-generator-source-history','wan22-fun-control')):
            current_schema_value=next(current_record['payload_schema'] for current_record in current_catalog_value['records'] if current_record['command']==current_command_name)
            current_validator_value=Draft202012Validator(current_schema_value)
            self.assertTrue(current_validator_value.is_valid({'service':current_service_name,'offset':0}))
            self.assertFalse(current_validator_value.is_valid({'service':current_service_name,'offset':1}))
            self.assertFalse(current_validator_value.is_valid({'service':current_service_name,'offset':1,'snapshot':None}))
            self.assertTrue(current_validator_value.is_valid({'service':current_service_name,'offset':1,'snapshot':'a'*64,'query':'job-1'}))
            self.assertFalse(current_validator_value.is_valid({'service':current_service_name,'query':'bad query'}))

    def test_source_history_catalog_matches_routes_and_capabilities(self):
        from workflow.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES,SOURCE_HISTORY_AUDIO_SERVICES
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS,resolve_management_command
        current_service_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_service_records={record['service']:record for record in current_service_catalog['services']}
        for current_service_name in (*SOURCE_HISTORY_GENERATOR_SERVICES,*SOURCE_HISTORY_AUDIO_SERVICES):
            with self.subTest(service=current_service_name):
                current_source_command='writer-history-observe' if current_service_name=='writer-agent' else 'history-observe'
                self.assertIn(current_source_command,MANAGEMENT_SERVICE_COMMANDS[current_service_name])
                self.assertEqual(resolve_management_command(current_service_name,current_source_command,{})[0],'POST')
                current_expected_link='hermes-audio-source-history' if current_service_name in SOURCE_HISTORY_AUDIO_SERVICES else 'hermes-generator-source-history'
                self.assertIn(current_expected_link,current_service_records[current_service_name]['hermes_links'])
        self.assertEqual(len(SOURCE_HISTORY_GENERATOR_SERVICES),len(set(SOURCE_HISTORY_GENERATOR_SERVICES)))
        self.assertFalse(set(SOURCE_HISTORY_GENERATOR_SERVICES)&set(SOURCE_HISTORY_AUDIO_SERVICES))

    def test_service_registration_links_to_existing_hermes_capabilities(self):
        current_service_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_capability_catalog=self.hermes_service_manager.execute_hermes_command('hermes-capabilities',{})
        current_capability_names={record['command'] for record in current_capability_catalog['records']}
        current_service_records={record['service']:record for record in current_service_catalog['services']}
        for current_service_name,current_expected_command in (('music-heartmula','hermes-delegate-audio'),('wan22-vace','hermes-delegate-video'),('flux-building','hermes-delegate-flux-profile'),('kimodo','hermes-delegate-kimodo'),('writer-agent','hermes-delegate-writer'),('prompt-translation','hermes-delegate-translation'),('map-assets','hermes-city-save'),('map-assets','hermes-effect-register'),('character-animation','hermes-sprite-save'),('character-animation','hermes-sprite-catalog'),('kimodo','hermes-kimodo-keyframes'),('model-downloads','hermes-model-inventory')):
            self.assertIn(current_expected_command,current_service_records[current_service_name]['hermes_links'])
        for current_service_name,current_expected_commands in {
            'flux-image':{'hermes-delegate-flux-image','hermes-flux-delegation-status','hermes-flux-delegation-history','hermes-flux-delegation-cancel','hermes-flux-proposal'},
            'map-assets':{'hermes-billboard-receipt','hermes-building-proposal','hermes-effect-receipt','hermes-effect-register-receipt','hermes-waypoint-receipt','hermes-field-receipt','hermes-field-history','hermes-city-proposal','hermes-city-receipt','hermes-city-history'},
            'character-animation':{'hermes-sprite-proposal','hermes-sprite-receipt'},
            'writer-agent':{'hermes-writer-proposal','hermes-writer-apply-status','hermes-writer-apply-history'},
            'music-heartmula':{'hermes-audio-proposal'},
            'wan22-vace':{'hermes-video-proposal'},
            'prompt-translation':{'hermes-translation-proposal'},
        }.items():
            self.assertTrue(current_expected_commands <= set(current_service_records[current_service_name]['hermes_links']))
        self.assertIn('hermes-priority-preview',current_service_records['kimodo']['hermes_links'])
        self.assertNotIn('hermes-priority-preview',current_service_records['qwen-21']['hermes_links'])
        current_search_record=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{'query':'작가 요청 제안'})
        self.assertIn('writer-agent',[item['service'] for item in current_search_record['services']])
        for current_service_record in current_service_catalog['services']:
            self.assertTrue(set(current_service_record['hermes_links']) <= current_capability_names)
            self.assertEqual(len(current_service_record['hermes_links']),len(set(current_service_record['hermes_links'])))
        from workflow.common.model_management_catalog import MODEL_PREPARATION_SERVICES
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, inspect_registered_model_operation
        for _,current_service_name in MODEL_PREPARATION_SERVICES:
            current_links_value=current_service_records[current_service_name]['hermes_links']
            self.assertIn('hermes-model-readiness',current_links_value)
            self.assertIn('hermes-model-prepare-status',current_links_value)
            current_prepare_allowed=inspect_registered_model_operation(current_service_name,MANAGEMENT_SERVICE_COMMANDS[current_service_name],'prepare') is not None
            self.assertEqual('hermes-model-prepare' in current_links_value,current_prepare_allowed)

    def test_wan21_registration_exposes_proposal_without_direct_delegation(self):
        current_catalog=self.hermes_service_manager.execute_hermes_command('hermes-service-registration',{})
        current_services={item['service']:item for item in current_catalog['services']}
        for current_name in ('wan21-t2v','wan21-i2v'):
            with self.subTest(service=current_name):
                current_record=current_services[current_name]
                self.assertIn('hermes-video-proposal',current_record['hermes_links'])
                self.assertIn('hermes-generator-source-history',current_record['hermes_links'])
                self.assertNotIn('hermes-delegate-video',current_record['hermes_links'])
                self.assertTrue(any(item['command']=='hermes-video-proposal' and '프롬프트만' in item['note'] for item in current_record['conditional_limitations']))

    def test_known_flux_seamless_limitations_match_service_validator(self):
        from workflow.domains.image.flux_image_generation import FluxImageGenerationManager
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-service-registration', {})
        current_service_value=next(record for record in current_catalog_value['services'] if record['service']=='flux-seamless')
        current_note_value=next(record['note'] for record in current_service_value['conditional_limitations'] if record['command']=='generate')
        for current_expected_text in ('512×512','참조 이미지 없음','global-periodic-v1','16스텝'):
            self.assertIn(current_expected_text,current_note_value)
        current_manager_value=FluxImageGenerationManager('flux-seamless')
        current_request_value={'action':'generate','prompt':'grass','images':[],'width':512,'height':512,'steps':16,'seed':42}
        self.assertEqual(current_manager_value.validate_generation_request(current_request_value)['seamless_method'],'global-periodic-v1')
        for current_change_value in ({'width':768},{'steps':20},{'seamless_method':'edge-blend'}):
            with self.subTest(change=current_change_value),self.assertRaises(ValueError):
                current_manager_value.validate_generation_request({**current_request_value,**current_change_value})

    def test_flux_profile_reference_limits_match_service_validators(self):
        from workflow.domains.image.flux_image_generation import FluxImageGenerationManager
        from workflow.domains.image.flux_expression_generation import FluxExpressionGenerationManager
        from workflow.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-service-registration', {})
        current_records_by_service={record['service']:record for record in current_catalog_value['services']}
        current_request_value={'action':'generate','prompt':'grass','images':[],'width':768,'height':768,'steps':16,'seed':42}
        for current_profile_name,current_profile_values in FLUX_IMAGE_PROFILE_RECORDS.items():
            if current_profile_name=='flux-seamless':
                continue
            current_note_value=next(record['note'] for record in current_records_by_service[current_profile_name]['conditional_limitations'] if record['command']=='generate')
            self.assertIn('최대 2장',current_note_value)
            self.assertIn('1~50스텝' if current_profile_name=='flux-character' else '16스텝',current_note_value)
            current_manager_value=FluxImageGenerationManager(current_profile_name)
            if current_profile_values[4]:
                self.assertIn('첫 참조 이미지가 필요',current_note_value)
                with self.subTest(profile=current_profile_name),self.assertRaises(ValueError):
                    current_manager_value.validate_generation_request(current_request_value)
        current_note_value=next(record['note'] for record in current_records_by_service['flux-expression']['conditional_limitations'] if record['command']=='generate')
        self.assertIn('얼굴 참조 이미지 1장',current_note_value)
        with self.assertRaises(ValueError):
            FluxExpressionGenerationManager().validate_generation_request(current_request_value)

    def test_known_video_limitations_match_service_validators(self):
        from generators.wan_fun.contracts import reject_retired_rgb_input, validate_fun_request
        from workflow.domains.wan_vace.generation import VaceVideoGenerationManager
        current_catalog_value=self.hermes_service_manager.execute_hermes_command('hermes-service-registration', {})
        current_records_by_service={record['service']:record for record in current_catalog_value['services']}
        current_fun_notes=' '.join(item['note'] for item in current_records_by_service['wan22-fun-control']['conditional_limitations'])
        for current_request_value in ({'start_image':'image'},{'end_image':'image'},{'input_mode':'reference-only'},{'input_mode':'rgb-video'}):
            with self.subTest(request=current_request_value),self.assertRaises(ValueError):
                reject_retired_rgb_input(current_request_value)
        self.assertIn('타일 VAE',current_fun_notes)
        current_tiled_request={'action':'generate','prompt':'walk','negative_prompt':'','images':[],'width':832,'height':480,'frames':5,'steps':20,'seed':42,'flow_shift':5,'guidance_scale':6,'switch_ratio':0.5,'control_type':'pose','pose_video':'video','use_regular_vae':False}
        with self.assertRaisesRegex(ValueError,'타일 VAE'):
            validate_fun_request(current_tiled_request)
        current_vace_notes=' '.join(item['note'] for item in current_records_by_service['wan22-vace']['conditional_limitations'])
        self.assertIn('official-bf16-resident-v1',current_vace_notes)
        with patch('workflow.domains.wan_vace.generation.validate_vace_assets') as current_asset_validator:
            current_manager_value=VaceVideoGenerationManager()
            with self.assertRaises(ValueError):
                current_manager_value.validate_generation_runtime({'model_profile':'retired-q4'})
            current_asset_validator.assert_not_called()
            current_manager_value.validate_generation_runtime({'model_profile':'official-bf16-resident-v1'})
            current_asset_validator.assert_called_once()

    def test_tool_activity_is_bounded_and_reports_command_exit(self):
        from workflow.domains.hermes_agent.service import read_hermes_tool_activity
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_job_path = Path(current_temp_root)
            current_events = [{'type':'tool_use','name':'terminal','tool_call_id':'call1','input':{'command':'echo test'},'timestamp':1794929185434}, {'type':'tool_result','name':'terminal','tool_call_id':'call1','output':json.dumps({'exit_code':2,'output':'private full text'}),'is_error':False}]
            (current_job_path / 'hermes-events.jsonl').write_text('\n'.join(json.dumps(current_event) for current_event in current_events))
            current_activity_record = read_hermes_tool_activity(current_job_path)
            self.assertEqual(current_activity_record['events'][0]['target'], 'echo test')
            self.assertEqual(current_activity_record['events'][1]['result'], 'error')
            self.assertEqual(current_activity_record['events'][1]['output'], 'private full text')
            current_events[1]['output'] = 'x' * 5000
            (current_job_path / 'hermes-events.jsonl').write_text('\n'.join(json.dumps(event) for event in current_events))
            bounded = read_hermes_tool_activity(current_job_path)['events'][1]
            self.assertEqual(len(bounded['output']), 4000)
            self.assertTrue(bounded['output_truncated'])
            (current_job_path / 'hermes-events.jsonl').write_text('\n'.join(json.dumps(current_events[0]) for _ in range(12)))
            current_activity_record = read_hermes_tool_activity(current_job_path)
            self.assertEqual(len(current_activity_record['events']), 8)
            self.assertTrue(current_activity_record['truncated'])

    def test_video_viewer_requires_matching_successful_tool_result(self):
        from workflow.domains.hermes_agent.service import read_hermes_tool_activity
        service, job = 'wan22-fun-control', '2026-11-21_10-21-48-00e8c029'
        base = f'/{service}/jobs/{job}/attempts/' + 'a' * 32 + '/'
        request = {'service':service, 'job_id':job}
        result = {'service':service, 'job_id':job, 'job':{'status':'completed', 'result_status':'available', 'video':base+'preview.mp4', 'image':base+'output-000.png', 'download':base+'frames.zip'}}
        events = [{'type':'tool_use','name':'terminal','tool_call_id':'a','input':{'command':"/runtime/.venv/bin/python /control/management-status.py video-source-status '"+json.dumps(request)+"'"}},
                  {'type':'tool_result','name':'terminal','tool_call_id':'a','output':json.dumps({'exit_code':0,'output':json.dumps(result)})}]
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'hermes-events.jsonl'
            def read():
                path.write_text('\n'.join(json.dumps(event) for event in events))
                return read_hermes_tool_activity(Path(root))
            self.assertEqual(read()['video_source'], request)
            result['job']['video'] = 'https://example.com/video.mp4'
            events[1]['output'] = json.dumps({'exit_code':0,'output':json.dumps(result)})
            self.assertNotIn('video_source', read())
            events[1]['tool_call_id'] = 'other'
            self.assertNotIn('video_source', read())

    def test_hermes_model_readiness_does_not_claim_ready_during_preparation(self):
        from workflow.domains.hermes_agent.management_observer import inspect_hermes_model_status
        with patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready'):
            current_ready_status = inspect_hermes_model_status(True, 'completed')
            current_preparing_status = inspect_hermes_model_status(True, 'running')
        self.assertTrue(current_ready_status['generation_ready'])
        self.assertFalse(current_preparing_status['generation_ready'])
        self.assertIn('준비 진행 중', current_preparing_status['message'])
        with patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready'):
            current_unknown_status = inspect_hermes_model_status(True, 'unknown')
        self.assertFalse(current_unknown_status['generation_ready'])
        self.assertIn('확인 불가', current_unknown_status['message'])

    def test_memory_capacity_rejects_inconsistent_gpu_measurements(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_memory_capacity
        current_device_value={'vram_total_mib':1000,'vram_free_mib':1001,'gtt_total_mib':500,'gtt_free_mib':100}
        current_gpu_values={'status':'idle','queue_device_memory':current_device_value}
        with patch('workflow.common.gpu_job_queue.read_host_available_memory') as current_host_mock:
            self.assertEqual(read_hermes_memory_capacity(current_gpu_values),{'status':'unavailable'})
            current_device_value.update(vram_total_mib=0,vram_free_mib=0,gtt_total_mib=0,gtt_free_mib=0)
            self.assertEqual(read_hermes_memory_capacity(current_gpu_values),{'status':'unavailable'})
            current_host_mock.assert_not_called()

    def test_memory_capacity_distinguishes_vram_from_host_gtt(self):
        from workflow.domains.hermes_agent.management_observer import read_hermes_memory_capacity
        current_device_value = {'vram_total_mib':98304, 'vram_free_mib':90000, 'gtt_total_mib':15000, 'gtt_free_mib':14000}
        current_gpu_value={'status':'idle','queue_device_memory':current_device_value}
        with patch('workflow.common.gpu_job_queue.read_host_available_memory', return_value=20000), patch('workflow.common.gpu_memory_history.estimate_required_memory', return_value={'required_memory_mib':32768}):
            current_capacity_value = read_hermes_memory_capacity(current_gpu_value)
            self.assertEqual(current_capacity_value['domain'], 'vram')
            self.assertTrue(current_capacity_value['capacity_sufficient'])
            self.assertEqual(current_capacity_value['pool_available_mib'], 90000)
            current_device_value.update(vram_total_mib=1000, gtt_total_mib=100000, gtt_free_mib=90000)
            current_capacity_value = read_hermes_memory_capacity(current_gpu_value)
            self.assertEqual(current_capacity_value['domain'], 'gtt')
            self.assertFalse(current_capacity_value['capacity_sufficient'])
            self.assertEqual(current_capacity_value['pool_available_mib'], 20000 - current_capacity_value['host_reserve_mib'])
        with patch('workflow.common.gpu_job_queue.read_host_available_memory', return_value=5000), patch('workflow.common.gpu_memory_history.estimate_required_memory', return_value={'required_memory_mib':32768}):
            current_device_value.update(vram_total_mib=98304, gtt_total_mib=15000)
            self.assertEqual(read_hermes_memory_capacity(current_gpu_value)['pool_available_mib'], 0)
        self.assertEqual(read_hermes_memory_capacity({'status':'unavailable'})['status'], 'unavailable')
        current_device_value.update(vram_total_mib=1000,gtt_total_mib=100000,gtt_free_mib=90000)
        from workflow.common.host_memory_guard import HOST_MEMORY_RESERVE_KIB
        current_host_reserve=HOST_MEMORY_RESERVE_KIB//1024
        with patch('workflow.common.gpu_job_queue.read_host_available_memory',side_effect=[current_host_reserve+32767,current_host_reserve+32768]),patch('workflow.common.gpu_memory_history.estimate_required_memory',return_value={'required_memory_mib':32768}):
            self.assertFalse(read_hermes_memory_capacity(current_gpu_value)['capacity_sufficient'])
            current_capacity_value=read_hermes_memory_capacity(current_gpu_value)
            self.assertTrue(current_capacity_value['capacity_sufficient'])
            self.assertEqual(current_capacity_value['pool_available_mib'],32768)
            self.assertIn('다른 예약과 작업 순서는 반영하지 않습니다',current_capacity_value['detail'])

    def test_session_requests_are_idempotent_and_survive_reopen(self):
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        hermes_store_path = Path(self.hermes_temporary_root.name) / 'sessions'
        hermes_session_store = HermesSessionStore(hermes_store_path)
        hermes_session_identifier = hermes_session_store.create_session_record()['id']
        with ThreadPoolExecutor(max_workers=4) as hermes_thread_pool:
            hermes_result_values = list(hermes_thread_pool.map(lambda _: HermesSessionStore(hermes_store_path).append_session_request(hermes_session_identifier, 'session-request-1234', '상태를 확인해 줘'), range(4)))
        self.assertEqual(sum(not hermes_result_record['duplicate'] for hermes_result_record in hermes_result_values), 1)
        with self.assertRaisesRegex(ValueError, '다른 메시지'):
            hermes_session_store.append_session_request(hermes_session_identifier, 'session-request-1234', '다른 지시')
        hermes_job_identifier = '2026-11-17_10-00-00-12345678'
        hermes_session_store.attach_session_job(hermes_session_identifier, 'session-request-1234', hermes_job_identifier)
        hermes_session_store.attach_session_job(hermes_session_identifier, 'session-request-1234', hermes_job_identifier)
        with self.assertRaisesRegex(ValueError, '다른 작업'):
            hermes_session_store.attach_session_job(hermes_session_identifier, 'session-request-1234', '2026-11-17_10-00-01-12345678')
        hermes_session_record = HermesSessionStore(hermes_store_path).read_session_record(hermes_session_identifier)
        self.assertEqual(len(hermes_session_record['messages']), 1)
        self.assertEqual(hermes_session_record['messages'][0]['job_id'], hermes_job_identifier)
        with self.assertRaises(ValueError):
            hermes_session_store.read_session_record('../outside')

    def test_expression_catalog_search_pagination_and_snapshot(self):
        current_first=self.hermes_service_manager.execute_hermes_command('hermes-expression-catalog',{'limit':3})
        self.assertEqual(len(current_first['records']),3)
        self.assertEqual(set(current_first['records'][0]),{'id','label'})
        self.assertEqual(current_first['next_offset'],3)
        current_second=self.hermes_service_manager.execute_hermes_command('hermes-expression-catalog',{'limit':3,'offset':3,'snapshot':current_first['snapshot']})
        self.assertNotEqual(current_first['records'],current_second['records'])
        current_query=self.hermes_service_manager.execute_hermes_command('hermes-expression-catalog',{'query':'기쁨'})
        self.assertIn({'id':'joy','label':'기쁨'},current_query['records'])
        for current_bad in ({'offset':3},{'query':'기쁨','offset':3,'snapshot':current_first['snapshot']},{'limit':True},{'path':'/tmp'}):
            with self.subTest(payload=current_bad),self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-expression-catalog',current_bad)

    def test_unreadable_session_record_is_not_replaced(self):
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        current_identifier='a'*32
        current_store_value=HermesSessionStore(self.hermes_service_manager.hermes_session_root)
        current_store_value.create_session_record(current_identifier)
        current_record_path=current_store_value.resolve_session_record_path(current_identifier)
        current_original_bytes=current_record_path.read_bytes()
        current_lstat_method=Path.lstat
        def reject_session_stat(current_path_value,*current_arguments,**current_keywords):
            if current_path_value==current_record_path:raise PermissionError('unreadable')
            return current_lstat_method(current_path_value,*current_arguments,**current_keywords)
        with patch.object(Path,'exists',return_value=False),patch.object(Path,'lstat',autospec=True,side_effect=reject_session_stat),patch('workflow.domains.hermes_agent.session_store.write_record_atomically') as current_write_mock:
            with self.assertRaises(PermissionError):current_store_value.create_session_record(current_identifier)
            current_write_mock.assert_not_called()
        self.assertEqual(current_record_path.read_bytes(),current_original_bytes)

    def test_session_view_detects_duplicate_jobs_across_pages(self):
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        current_session='a'*32
        current_store=HermesSessionStore(self.hermes_service_manager.hermes_session_root)
        current_store.create_session_record(current_session)
        for current_index in range(25):current_store.append_session_request(current_session,'request_%04d'%current_index,'지시')
        current_job='2026-10-09_21-13-20-1a356bbd'
        current_store.attach_session_job(current_session,'request_0000',current_job)
        current_store.attach_session_job(current_session,'request_0024',current_job)
        current_first=self.hermes_service_manager.execute_hermes_command('hermes-session-view',{'session_id':current_session})
        self.assertFalse(current_first['messages'][-1]['session_job_unique'])
        current_older=self.hermes_service_manager.execute_hermes_command('hermes-session-view',{'session_id':current_session,'offset':20,'snapshot':current_first['snapshot']})
        self.assertFalse(current_older['messages'][0]['session_job_unique'])
        self.assertIsNone(current_older['messages'][1]['session_job_unique'])

    def test_direct_service_receipt_looks_up_old_record_without_service_calls(self):
        from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
        current_store=HermesDelegationStore(Path(self.hermes_temporary_root.name)/'receipts')
        current_service='wan22-vace'
        current_job='2026-10-09_21-13-20-1a356bbd'
        with current_store.hold_delegation_storage_lock():
            for current_index in range(105):
                current_request='request_%04d'%current_index
                current_record={'version':2,'id':current_request,'service':current_service,'state':'accepted','job_id':current_job}
                current_store.resolve_delegation_record_path(current_request).write_text(json.dumps(current_record))
        self.assertNotIn('request_0000',[item['request_id'] for item in current_store.list_service_delegations(current_service)['records']])
        with patch('workflow.domains.hermes_agent.delegation_store.HermesDelegationStore',return_value=current_store),patch('workflow.common.management_gateway.execute_management_command') as current_service_mock:
            current_result=self.hermes_service_manager.execute_hermes_command('hermes-service-receipt',{'request_id':'request_0000','service':current_service})
            self.assertEqual(current_result,{'state':'accepted','service':current_service,'job_id':current_job,'request_id':'request_0000'})
            self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-service-receipt',{'request_id':'request_missing','service':current_service}),{'state':'not_found','request_id':'request_missing','service':current_service})
            with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-service-receipt',{'request_id':'request_0000','service':'dwpose'})
            with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-service-receipt',{'request_id':'request_0000','service':'unsupported'})
            current_service_mock.assert_not_called()

    def test_session_history_pages_and_change_detection(self):
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        current_session='a'*32
        current_store=HermesSessionStore(self.hermes_service_manager.hermes_session_root)
        current_store.create_session_record(current_session)
        for current_index in range(45):
            current_store.append_session_request(current_session,'request_%04d'%current_index,'지시 %d'%current_index)
        current_first=self.hermes_service_manager.execute_hermes_command('hermes-session-view',{'session_id':current_session})
        current_small=self.hermes_service_manager.execute_hermes_command('hermes-session-view',{'session_id':current_session,'limit':6})
        self.assertEqual([item['text'] for item in current_small['messages']],['지시 %d'%item for item in range(39,45)])
        self.assertEqual(current_small['next_offset'],6)
        current_small_older=self.hermes_service_manager.execute_hermes_command('hermes-session-view',{'session_id':current_session,'limit':6,'offset':6,'snapshot':current_small['snapshot']})
        self.assertEqual([item['text'] for item in current_small_older['messages']],['지시 %d'%item for item in range(33,39)])
        for invalid_limit in (0,21,True):
            with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-session-view',{'session_id':current_session,'limit':invalid_limit})
        self.assertEqual([item['text'] for item in current_first['messages']],['지시 %d'%item for item in range(25,45)])
        self.assertTrue(current_first['messages'][0]['created_at'])
        self.assertEqual(current_first['next_offset'],20)
        current_second=self.hermes_service_manager.execute_hermes_command('hermes-session-view',{'session_id':current_session,'offset':20,'snapshot':current_first['snapshot']})
        self.assertEqual([item['text'] for item in current_second['messages']],['지시 %d'%item for item in range(5,25)])
        current_last=self.hermes_service_manager.execute_hermes_command('hermes-session-view',{'session_id':current_session,'offset':40,'snapshot':current_first['snapshot']})
        self.assertEqual(len(current_last['messages']),5)
        self.assertIsNone(current_last['next_offset'])
        with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-session-view',{'session_id':current_session,'offset':20})
        with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-session-view',{'session_id':current_session,'offset':True,'snapshot':current_first['snapshot']})
        current_store.append_session_request(current_session,'request_new','새 지시')
        with self.assertRaises(ValueError):self.hermes_service_manager.execute_hermes_command('hermes-session-view',{'session_id':current_session,'offset':20,'snapshot':current_first['snapshot']})

    def test_session_creation_and_read_are_gateway_compatible_and_idempotent(self):
        hermes_session_identifier = 'a' * 32
        hermes_session_payload = {'session_id': hermes_session_identifier}
        for hermes_command_name in ('hermes-session-create', 'hermes-session-read'):
            hermes_method_value, hermes_route_value = resolve_management_command('hermes-agent', hermes_command_name, hermes_session_payload)
            self.assertEqual(identify_management_command(hermes_route_value, hermes_method_value, hermes_session_payload), ('hermes-agent', hermes_command_name, hermes_session_payload))
        hermes_first_record = self.hermes_service_manager.execute_hermes_command('hermes-session-create', hermes_session_payload)
        self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-session-create', hermes_session_payload), hermes_first_record)
        self.assertEqual(self.hermes_service_manager.execute_hermes_command('hermes-session-read', hermes_session_payload), hermes_first_record)
        hermes_session_list = self.hermes_service_manager.execute_hermes_command('hermes-session-list', {})
        self.assertEqual(hermes_session_list['sessions'][0]['id'], hermes_session_identifier)
        self.assertEqual(hermes_session_list['sessions'][0]['message_count'], 0)
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-session-list', {'extra': 1})
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': '../outside'})
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': None})
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-session-read', {'session_id': hermes_session_identifier, 'extra': 1})

    @patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('workflow.domains.hermes_agent.service.launch_gpu_process')
    @patch('workflow.domains.hermes_agent.resident_queue.find_session_resident', return_value=None)
    @patch('workflow.domains.hermes_agent.resident_queue.ensure_session_resident', return_value={'state':'accepted','id':'resident_123'})
    @patch('workflow.domains.hermes_agent.resident_queue.inspect_resident', return_value={'state':'ready'})
    def test_session_submit_retries_and_includes_completed_context(self, resident_status_mock, resident_start_mock, resident_find_mock, hermes_launch_mock, hermes_ready_mock):
        hermes_session_identifier = 'b' * 32
        self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': hermes_session_identifier})
        hermes_first_payload = {'session_id': hermes_session_identifier, 'request_id': 'first-request-1234', 'prompt': '첫 질문'}
        with ThreadPoolExecutor(max_workers=4) as hermes_thread_pool:
            hermes_first_results = list(hermes_thread_pool.map(lambda _: self.hermes_service_manager.execute_hermes_command('hermes-session-submit', hermes_first_payload), range(4)))
        self.assertEqual(hermes_launch_mock.call_count, 1)
        self.assertEqual(len({current_result['job_id'] for current_result in hermes_first_results}), 1)
        self.assertEqual(sum(not current_result['duplicate'] for current_result in hermes_first_results), 1)
        hermes_second_payload = {'session_id': hermes_session_identifier, 'request_id': 'second-request-1234', 'prompt': '그 답을 이어서'}
        queued = self.hermes_service_manager.execute_hermes_command('hermes-session-submit', hermes_second_payload)
        self.assertTrue(queued['queued'])
        self.assertEqual(hermes_launch_mock.call_count, 1)
        with self.assertRaisesRegex(ValueError, '종료된 후'):
            self.hermes_service_manager.dispatch_chat_queue(hermes_session_identifier)
        hermes_first_job_path = self.hermes_service_manager.hermes_storage_root / hermes_first_results[0]['job_id']
        (hermes_first_job_path / 'status.json').write_text('{"status":"completed"}')
        (hermes_first_job_path / 'hermes-events.jsonl').write_text(json.dumps({'type':'result', 'text':'첫 답변'}, ensure_ascii=False))
        hermes_second_result = self.hermes_service_manager.dispatch_chat_queue(hermes_session_identifier)
        hermes_second_request = json.loads((self.hermes_service_manager.hermes_storage_root / hermes_second_result['job_id'] / 'request.json').read_text())
        self.assertEqual(hermes_second_request['context']['messages'], [
            {'role':'user','content':'첫 질문'}, {'role':'assistant','content':'첫 답변'}])
        hermes_view_record = self.hermes_service_manager.execute_hermes_command('hermes-session-view', {'session_id': hermes_session_identifier})
        self.assertEqual(hermes_view_record['messages'][0]['job']['final_response'], '첫 답변')
        self.assertEqual(hermes_view_record['messages'][1]['job']['status']['status'], 'unknown')
        self.assertEqual(hermes_view_record['message_count'], 2)
        self.assertIn('그 답을 이어서', hermes_second_request['prompt'])
        self.assertEqual(hermes_launch_mock.call_count, 2)
        with self.assertRaisesRegex(ValueError, '다른 메시지'):
            self.hermes_service_manager.execute_hermes_command('hermes-session-submit', {**hermes_first_payload, 'prompt':'다른 질문'})

    @patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('workflow.domains.hermes_agent.service.launch_gpu_process')
    def test_session_retry_after_job_accepted_but_link_failed(self, hermes_launch_mock, hermes_ready_mock):
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        hermes_session_identifier = 'c' * 32
        self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': hermes_session_identifier})
        hermes_request_record = {'session_id': hermes_session_identifier, 'request_id': 'retry-request-1234', 'prompt': '테스트'}
        with patch.object(HermesSessionStore, 'attach_session_job', side_effect=OSError('저장 중단')):
            with self.assertRaises(OSError):
                self.hermes_service_manager.execute_hermes_command('hermes-session-submit', hermes_request_record)
        hermes_retry_record = self.hermes_service_manager.execute_hermes_command('hermes-session-submit', hermes_request_record)
        self.assertTrue(hermes_retry_record['duplicate'])
        hermes_launch_mock.assert_called_once()
        hermes_saved_record = self.hermes_service_manager.execute_hermes_command('hermes-session-read', {'session_id': hermes_session_identifier})
        self.assertEqual(hermes_saved_record['messages'][0]['job_id'], hermes_retry_record['job_id'])

    @patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('workflow.domains.hermes_agent.service.launch_gpu_process')
    @patch('workflow.domains.hermes_agent.resident_queue.find_session_resident', return_value=None)
    @patch('workflow.domains.hermes_agent.resident_queue.ensure_session_resident', return_value={'state':'accepted','id':'resident_123'})
    @patch('workflow.domains.hermes_agent.resident_queue.inspect_resident', return_value={'state':'ready'})
    def test_manual_context_job_is_idempotent_and_blocks_new_turn_until_terminal(self, resident_status_mock, resident_start_mock, resident_find_mock, launch, ready):
        session = 'd' * 32
        self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': session})
        first = self.hermes_service_manager.execute_hermes_command('hermes-session-submit',
                    {'session_id': session, 'request_id': 'request_first', 'prompt': '코드 수정 요청'})
        path = self.hermes_service_manager.hermes_storage_root / first['job_id']
        (path / 'status.json').write_text('{"status":"completed"}')
        (path / 'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':'답변'}, ensure_ascii=False))
        payload = {'session_id': session, 'request_id': 'compact_request'}
        result = self.hermes_service_manager.execute_hermes_command('hermes-session-context-compress', payload)
        retry = self.hermes_service_manager.execute_hermes_command('hermes-session-context-compress', payload)
        self.assertEqual(result['job_id'], retry['job_id'])
        self.assertTrue(retry['duplicate'])
        request = json.loads((self.hermes_service_manager.hermes_storage_root / result['job_id'] / 'request.json').read_text())
        self.assertTrue(request['context']['force'])
        self.assertTrue(request['context']['only'])
        self.assertEqual(request['model_profile'], 'qwen3.8-27b')
        snapshot = self.hermes_service_manager.execute_hermes_command('hermes-session-read', {'session_id': session})
        with self.assertRaisesRegex(ValueError, '정리'):
            self.hermes_service_manager.execute_hermes_command('hermes-session-archive',
                {'session_id': session, 'expected_update': snapshot['updated_at']})
        queued = self.hermes_service_manager.execute_hermes_command('hermes-session-submit',
                {'session_id': session, 'request_id': 'request_next', 'prompt': '다음 질문'})
        self.assertTrue(queued['queued'])
        with self.assertRaisesRegex(ValueError, '정리'):
            self.hermes_service_manager.dispatch_chat_queue(session)
        (self.hermes_service_manager.hermes_storage_root / result['job_id'] / 'status.json').write_text('{"status":"completed"}')
        self.hermes_service_manager.dispatch_chat_queue(session)
        self.assertEqual(launch.call_count, 3)

    @patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('workflow.domains.hermes_agent.service.launch_gpu_process')
    def test_long_prior_answer_is_preserved_in_context(self, launch, ready):
        session = 'e' * 32
        self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': session})
        first = self.hermes_service_manager.execute_hermes_command('hermes-session-submit',
                    {'session_id': session, 'request_id': 'request_first', 'prompt': '첫 질문'})
        path = self.hermes_service_manager.hermes_storage_root / first['job_id']
        answer = '과거 답변 ' * 20000
        (path / 'status.json').write_text('{"status":"completed"}')
        (path / 'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':answer}, ensure_ascii=False))
        second = self.hermes_service_manager.execute_hermes_command('hermes-session-submit',
                    {'session_id': session, 'request_id': 'request_second', 'prompt': '후속 질문'})
        request = json.loads((self.hermes_service_manager.hermes_storage_root / second['job_id'] / 'request.json').read_text())
        self.assertEqual(request['context']['messages'][-1]['content'], answer)
        self.assertEqual(request['prompt'], '후속 질문')

    def test_context_settings_round_trip_and_default(self):
        session = 'f' * 32
        self.hermes_service_manager.execute_hermes_command('hermes-session-create', {'session_id': session})
        view = self.hermes_service_manager.execute_hermes_command('hermes-session-view', {'session_id': session})
        self.assertTrue(view['context']['automatic'])
        for command, payload in (
            ('hermes-session-context-settings', {'session_id': session, 'enabled': False}),
            ('hermes-session-context-compress', {'session_id': session, 'request_id': 'compact_request'}),
        ):
            method, route = resolve_management_command('hermes-agent', command, payload)
            self.assertEqual(identify_management_command(route, method, payload), ('hermes-agent', command, payload))
        self.hermes_service_manager.execute_hermes_command('hermes-session-context-settings', {'session_id': session, 'enabled': False})
        view = self.hermes_service_manager.execute_hermes_command('hermes-session-view', {'session_id': session})
        self.assertFalse(view['context']['automatic'])
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-session-context-settings', {'session_id': session, 'enabled': 1})

    def test_gateway_command_round_trip(self):
        hermes_payload_record = {'request_id':'test-request-1234', 'prompt':'테스트'}
        hermes_method_value, hermes_route_value = resolve_management_command('hermes-agent', 'hermes-submit', hermes_payload_record)
        self.assertEqual(identify_management_command(hermes_route_value, hermes_method_value, hermes_payload_record), ('hermes-agent', 'hermes-submit', hermes_payload_record))

    @patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('workflow.domains.hermes_agent.service.launch_gpu_process')
    def test_detail_includes_agent_response_and_tool_result(self, hermes_launch_mock, hermes_ready_mock):
        hermes_job_result = self.hermes_service_manager.execute_hermes_command('hermes-submit', {'request_id':'trace-request-1234', 'prompt':'테스트'})
        hermes_job_path = self.hermes_service_manager.hermes_storage_root / hermes_job_result['id']
        hermes_event_values = [{'type':'tool_use','name':'terminal','input':{'command':'python -m unittest'}}, {'type':'tool_result','output':'OK'}, {'type':'result','text':'검사 완료'}]
        (hermes_job_path / 'hermes-events.jsonl').write_text(''.join(json.dumps(hermes_event_record, ensure_ascii=False) + '\n' for hermes_event_record in hermes_event_values))
        hermes_detail_record = self.hermes_service_manager.execute_hermes_command('hermes-detail', {'id':hermes_job_result['id']})
        self.assertIn('python -m unittest', hermes_detail_record['log'])
        self.assertIn('검사 완료', hermes_detail_record['log'])
        self.assertEqual(hermes_detail_record['final_response'], '검사 완료')
        self.assertFalse(hermes_detail_record['final_response_truncated'])
        (hermes_job_path / 'hermes-events.jsonl').write_text(json.dumps({'type':'result','text':'가' * 8001}, ensure_ascii=False))
        hermes_detail_record = self.hermes_service_manager.execute_hermes_command('hermes-detail', {'id':hermes_job_result['id']})
        self.assertEqual(len(hermes_detail_record['final_response']), 8000)
        self.assertTrue(hermes_detail_record['final_response_truncated'])

    @patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('workflow.domains.hermes_agent.service.launch_gpu_process')
    def test_diff_chunks_preserve_unicode_bytes_and_require_completion(self, hermes_launch_mock, hermes_ready_mock):
        hermes_job_result = self.hermes_service_manager.execute_hermes_command('hermes-submit', {'request_id':'diff-request-1234', 'prompt':'테스트'})
        hermes_job_path = self.hermes_service_manager.hermes_storage_root / hermes_job_result['id']
        hermes_diff_bytes = '가나다'.encode('utf-8')
        (hermes_job_path / 'change.diff').write_bytes(hermes_diff_bytes)
        hermes_chunk_request = {'id':hermes_job_result['id'], 'offset':0, 'limit':2}
        with self.assertRaisesRegex(ValueError, '종료된 뒤'):
            self.hermes_service_manager.execute_hermes_command('hermes-diff', hermes_chunk_request)
        (hermes_job_path / 'status.json').write_text('{"status":"completed"}')
        hermes_collected_bytes = bytearray()
        while hermes_chunk_request['offset'] is not None:
            hermes_chunk_record = self.hermes_service_manager.execute_hermes_command('hermes-diff', hermes_chunk_request)
            hermes_collected_bytes.extend(base64.b64decode(hermes_chunk_record['data_base64']))
            hermes_chunk_request['offset'] = hermes_chunk_record['next_offset']
        self.assertEqual(bytes(hermes_collected_bytes), hermes_diff_bytes)
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-diff', {'id':hermes_job_result['id'], 'offset':0, 'limit':999999})

    @patch('workflow.domains.hermes_agent.service.validate_hermes_runtime_ready')
    @patch('workflow.domains.hermes_agent.service.launch_gpu_process')
    def test_verification_modules_are_allowlisted_and_idempotent(self, hermes_launch_mock, hermes_ready_mock):
        hermes_request_record = {'request_id':'verify-request-1234', 'prompt':'테스트', 'verification_modules':['workflow.tests.test_hermes_service']}
        hermes_first_result = self.hermes_service_manager.execute_hermes_command('hermes-submit', hermes_request_record)
        self.assertFalse(hermes_first_result['duplicate'])
        self.assertTrue(self.hermes_service_manager.execute_hermes_command('hermes-submit', hermes_request_record)['duplicate'])
        with self.assertRaises(ValueError):
            self.hermes_service_manager.execute_hermes_command('hermes-submit', {'request_id':'verify-request-1234', 'prompt':'테스트'})
        with self.assertRaisesRegex(ValueError, '등록된 검증 모듈'):
            self.hermes_service_manager.execute_hermes_command('hermes-submit', {'request_id':'bad-module-1234', 'prompt':'테스트', 'verification_modules':['os.system']})
        hermes_launch_mock.assert_called_once()


if __name__ == '__main__':
    unittest.main()
