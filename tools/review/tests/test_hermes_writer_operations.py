"""작가 AI 위임 기록과 제안 조회 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.review.domains.hermes_agent import writer_operations
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesWriterOperationsTests(unittest.TestCase):
    def test_cancellation_requires_matching_receipt_and_job(self):
        current_job_identifier='20261118-120000-12345678'
        with patch.object(writer_operations,'HermesDelegationStore') as current_store_mock, patch.object(writer_operations,'call_hermes_writer_service',return_value={'id':current_job_identifier,'status':'running','cancel_requested':True}) as current_gateway_mock:
            current_store_mock.return_value.read_service_delegation.return_value={'state':'accepted','job_id':current_job_identifier}
            with self.assertRaises(ValueError):writer_operations.cancel_hermes_writer_request('request_123','20261118-120000-ffffffff')
            current_gateway_mock.assert_not_called()
            self.assertTrue(writer_operations.cancel_hermes_writer_request('request_123',current_job_identifier)['cancel_requested'])
            current_gateway_mock.assert_called_once_with('writer-cancel',{'id':current_job_identifier})
            current_gateway_mock.return_value={'id':'wrong','cancel_requested':True}
            with self.assertRaises(ValueError):writer_operations.cancel_hermes_writer_request('request_123',current_job_identifier)

    def test_writer_job_id_duplicate_and_sanitized_status(self):
        current_request_value={'mode':'write','prompt':'마을 설명'}
        current_job_identifier='20261118-120000-12345678'
        current_detail_value={'id':current_job_identifier,'job_path':'/private/secret','status':{'stage':'review','proposal_hash':'a'*64,'summary':'변경 1개','error':'private'},'proposal':{'changes':[{'path':'world/town.md','diff':'-이전\n+변경','after':'secret'}],'warnings':['검토']},'log':'private'}
        def execute_writer_command(current_command_name,current_payload_value):
            if current_command_name=='writer-submit':return {'id':current_job_identifier,'job_path':'/private'}
            if current_command_name=='writer-detail':return current_detail_value
            raise AssertionError(current_command_name)
        with TemporaryDirectory() as current_root_name, patch.object(writer_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(writer_operations,'validate_hermes_writer_request') as current_validate_mock, patch.object(writer_operations,'call_hermes_writer_service',side_effect=execute_writer_command) as current_gateway_mock:
            self.assertFalse(writer_operations.submit_hermes_writer_request('writer_request_123',current_request_value)['duplicate'])
            self.assertTrue(writer_operations.submit_hermes_writer_request('writer_request_123',current_request_value)['duplicate'])
            current_validate_mock.assert_called_once()
            current_status_value=writer_operations.read_hermes_writer_status('writer_request_123')
            self.assertEqual(current_status_value['job']['changes'][0]['path'],'world/town.md')
            self.assertEqual(current_status_value['job']['proposal_hash'],'a'*64)
            self.assertNotIn('private',str(current_status_value))
            self.assertNotIn('secret',str(current_status_value))
            self.assertEqual(current_gateway_mock.call_count,2)
            self.assertEqual(HermesDelegationStore(Path(current_root_name)).list_service_delegations('writer-agent')['records'][0]['job_id'],current_job_identifier)

    def test_writer_warnings_cannot_be_silently_truncated(self):
        current_job_identifier='20261118-120000-12345678'
        current_detail_value={'id':current_job_identifier,'status':{'stage':'review','proposal_hash':'a'*64},'proposal':{'changes':[{'path':'world/town.md','diff':'-a\n+b'}],'warnings':[]}}
        with patch.object(writer_operations,'HermesDelegationStore') as current_store_mock, patch.object(writer_operations,'call_hermes_writer_service',return_value=current_detail_value) as current_gateway_mock:
            current_store_mock.return_value.read_service_delegation.return_value={'state':'accepted','job_id':current_job_identifier}
            current_detail_value['proposal']['warnings']=['경고']*31
            current_result=writer_operations.read_hermes_writer_status('writer_request_123')
            self.assertTrue(current_result['job']['truncated'])
            self.assertEqual(len(current_result['job']['warnings']),30)
            current_detail_value['proposal']['warnings']=['x'*1001]
            current_result=writer_operations.read_hermes_writer_status('writer_request_123')
            self.assertTrue(current_result['job']['truncated'])
            self.assertEqual(len(current_result['job']['warnings'][0]),1000)
            current_detail_value['proposal']['warnings']=['경고',None]
            with self.assertRaises(ValueError):writer_operations.read_hermes_writer_status('writer_request_123')
            self.assertTrue(all(item.args[0]=='writer-detail' for item in current_gateway_mock.call_args_list))

    def test_writer_reason_exposes_bounded_text_without_absolute_paths(self):
        current_job_identifier='20261118-120000-12345678'
        current_detail_value={'id':current_job_identifier,'status':{'stage':'review'},'proposal':{'reason':'관련 문서를 보완합니다.','changes':[],'warnings':[]}}
        with patch.object(writer_operations,'HermesDelegationStore') as current_store_mock, patch.object(writer_operations,'call_hermes_writer_service',return_value=current_detail_value):
            current_store_mock.return_value.read_service_delegation.return_value={'state':'accepted','job_id':current_job_identifier}
            current_result=writer_operations.read_hermes_writer_status('writer_request_123')['job']
            self.assertEqual(current_result['reason'],'관련 문서를 보완합니다.')
            self.assertFalse(current_result['reason_truncated'])
            current_detail_value['proposal']['reason']='x'*2001
            current_result=writer_operations.read_hermes_writer_status('writer_request_123')['job']
            self.assertTrue(current_result['reason_truncated'])
            self.assertEqual(len(current_result['reason']),2000)
            current_detail_value['proposal']['reason']='확인: /home/private/file'
            current_result=writer_operations.read_hermes_writer_status('writer_request_123')['job']
            self.assertIsNone(current_result['reason'])
            self.assertNotIn('/home/private',str(current_result))

    def test_writer_coverage_and_retained_are_bounded_and_paths_checked(self):
        current_job_identifier='20261118-120000-12345678'
        current_coverage_value={'eligible_chunks':10,'compared_pairs':3,'candidate_pairs':2,'reviewed_pairs':2,'limited':False}
        current_proposal_value={'changes':[],'warnings':[],'coverage':current_coverage_value,'retained':[{'path':'world/town.md','reason':'고유 정보 보존'}]}
        current_detail_value={'id':current_job_identifier,'status':{'stage':'review'},'proposal':current_proposal_value}
        with patch.object(writer_operations,'HermesDelegationStore') as current_store_mock, patch.object(writer_operations,'call_hermes_writer_service',return_value=current_detail_value):
            current_store_mock.return_value.read_service_delegation.return_value={'state':'accepted','job_id':current_job_identifier}
            current_result=writer_operations.read_hermes_writer_status('writer_request_123')['job']
            self.assertEqual(current_result['coverage'],current_coverage_value)
            self.assertEqual(current_result['retained'][0]['reason'],'고유 정보 보존')
            self.assertFalse(current_result['retained_truncated'])
            current_proposal_value['retained']=[{'path':'/private/secret','reason':'no'},{'path':'C:\\secret','reason':'no'}]
            current_result=writer_operations.read_hermes_writer_status('writer_request_123')['job']
            self.assertTrue(current_result['retained_truncated'])
            self.assertEqual(current_result['retained'],[])
            self.assertNotIn('/private/secret',str(current_result))
            current_proposal_value['coverage']={**current_coverage_value,'eligible_chunks':True}
            with self.assertRaises(ValueError):writer_operations.read_hermes_writer_status('writer_request_123')

    def test_writer_evidence_limits_content_and_blocks_unsafe_paths(self):
        current_chunk={'path':'world/town.md','heading':'마을','text':'기존 설정','id':'chunk-1'}
        current_values,current_truncated=writer_operations.summarize_hermes_writer_evidence([current_chunk])
        self.assertFalse(current_truncated)
        self.assertEqual(current_values[0]['text'],'기존 설정')
        current_values,current_truncated=writer_operations.summarize_hermes_writer_evidence([{'keep':current_chunk,'remove':current_chunk,'reason':'중복'}])
        self.assertFalse(current_truncated)
        self.assertEqual(current_values[0]['reason'],'중복')
        current_values,current_truncated=writer_operations.summarize_hermes_writer_evidence([{**current_chunk,'path':'/private/secret'},{**current_chunk,'text':'x'*4001}])
        self.assertTrue(current_truncated)
        self.assertEqual(len(current_values[0]['text']),4000)
        self.assertNotIn('/private/secret',str(current_values))
        with self.assertRaises(ValueError):writer_operations.summarize_hermes_writer_evidence([{'path':'x'}])

    def test_warning_truncation_blocks_writer_apply(self):
        current_job_identifier='20261118-120000-12345678'
        current_hash_value='a'*64
        current_detail_value={'id':current_job_identifier,'status':{'stage':'review','proposal_hash':current_hash_value},'proposal':{'changes':[{'path':'world/town.md','diff':'-a\n+b'}],'warnings':['경고']*31}}
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('writer_request_123','writer-agent',{},lambda current_request:{'id':current_job_identifier},lambda current_request:None)
            with patch.object(writer_operations,'HermesDelegationStore',return_value=current_store_value), patch.object(writer_operations,'call_hermes_writer_service',return_value=current_detail_value) as current_gateway_mock:
                with self.assertRaises(ValueError):
                    writer_operations.apply_hermes_writer_proposal_once('writer_apply_123','writer_request_123',current_job_identifier,current_hash_value)
                self.assertTrue(all(item.args[0]!='writer-apply' for item in current_gateway_mock.call_args_list))

    def test_lost_writer_response_not_retried(self):
        with TemporaryDirectory() as current_root_name, patch.object(writer_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(writer_operations,'validate_hermes_writer_request'), patch.object(writer_operations,'call_hermes_writer_service',side_effect=OSError('lost')) as current_gateway_mock:
            with self.assertRaises(OSError):
                writer_operations.submit_hermes_writer_request('writer_request_456',{'mode':'write','prompt':'제안'})
            self.assertEqual(writer_operations.read_hermes_writer_status('writer_request_456')['receipt']['state'],'unknown')
            self.assertTrue(writer_operations.submit_hermes_writer_request('writer_request_456',{'mode':'write','prompt':'제안'})['duplicate'])
            current_gateway_mock.assert_called_once()

    def test_writer_checks_fresh_index_before_submission(self):
        current_request_value={'mode':'write','prompt':'제안'}
        with patch('generators.writer_agent.jobs.validate_job_request'), patch.object(writer_operations,'call_hermes_writer_service',side_effect=[{'configured':True,'ready':True,'trained':True,'active_job':None},{'status':'stale'}]) as current_gateway_mock:
            with self.assertRaisesRegex(ValueError,'색인이 오래'):
                writer_operations.validate_hermes_writer_request(current_request_value)
            self.assertEqual([item.args[0] for item in current_gateway_mock.call_args_list],['writer-state','writer-index-status'])
        with patch('generators.writer_agent.jobs.validate_job_request'), patch.object(writer_operations,'call_hermes_writer_service',return_value={'configured':True,'ready':True,'trained':False,'active_job':None}) as current_gateway_mock:
            writer_operations.validate_hermes_writer_request({'mode':'learn','prompt':''})
            self.assertEqual(current_gateway_mock.call_count,1)

    def test_writer_reports_concurrent_document_change_without_paths(self):
        current_job_identifier='20261118-120000-12345678'
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('writer_request_998','writer-agent',{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
            current_reply_value={'id':current_job_identifier,'status':{'stage':'failed','error':'검토 중 원문이 변경되어 /private 오류'}}
            with patch.object(writer_operations,'HermesDelegationStore',return_value=current_store_value), patch.object(writer_operations,'call_hermes_writer_service',return_value=current_reply_value):
                current_result_value=writer_operations.read_hermes_writer_status('writer_request_998')
            self.assertIn('원문이 변경',current_result_value['job']['failure_reason'])
            self.assertNotIn('/private',str(current_result_value))

    def test_apply_approved_proposal_once_and_recover(self):
        from concurrent.futures import ThreadPoolExecutor
        current_job_identifier='20261118-120000-12345678'
        current_hash_value='a'*64
        current_status_value={'receipt':{'state':'accepted','service':'writer-agent','job_id':current_job_identifier},'job':{'stage':'review','proposal_hash':current_hash_value,'truncated':False,'changes':[{'path':'world/town.md','diff':'-old\n+new'}]}}
        with TemporaryDirectory() as current_root_name, patch.object(writer_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(writer_operations,'read_hermes_writer_status',return_value=current_status_value), patch.object(writer_operations,'call_hermes_writer_service',return_value={'status':'applied','paths':['private']}) as current_apply_mock:
            def submit_current_apply(unused_index_value):
                return writer_operations.apply_hermes_writer_proposal_once('apply_request_123','writer_request_123',current_job_identifier,current_hash_value)
            with ThreadPoolExecutor(max_workers=4) as current_pool_value:
                current_results_list=list(current_pool_value.map(submit_current_apply,range(4)))
            self.assertEqual(sum(not item['duplicate'] for item in current_results_list),1)
            current_apply_mock.assert_called_once_with('writer-apply',{'id':current_job_identifier,'proposal_hash':current_hash_value})
            self.assertNotIn('private',str(current_results_list))
            self.assertEqual(writer_operations.read_writer_apply_receipt('apply_request_123')['state'],'completed')
            self.assertEqual(writer_operations.list_writer_apply_receipts()['records'][0]['job_id'],current_job_identifier)
            with self.assertRaises(ValueError):
                writer_operations.apply_hermes_writer_proposal_once('apply_request_123','writer_request_123',current_job_identifier,'b'*64)
            self.assertEqual(HermesDelegationStore(Path(current_root_name)).list_delegation_receipts()['records'],[])

    def test_apply_rejects_mismatched_receipt_and_preserves_changed_record(self):
        import json
        current_job_identifier='20261118-120000-12345678'
        current_hash_value='a'*64
        current_status_value={'receipt':{'state':'accepted','service':'other','job_id':current_job_identifier},'job':{'stage':'review','proposal_hash':current_hash_value,'truncated':False,'changes':[{'path':'world/town.md','diff':'x'}]}}
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_record_path=current_store_value.resolve_delegation_record_path('apply_request_123')
            def current_apply_response(current_command_name,current_payload_value):
                current_record_value=json.loads(current_record_path.read_text())
                current_record_value['external_change']='preserve'
                current_record_path.write_text(json.dumps(current_record_value))
                return {'status':'applied'}
            with patch.object(writer_operations,'HermesDelegationStore',return_value=current_store_value),patch.object(writer_operations,'read_hermes_writer_status',return_value=current_status_value),patch.object(writer_operations,'call_hermes_writer_service',side_effect=current_apply_response) as current_apply_mock:
                current_arguments=('apply_request_123','writer_request_123',current_job_identifier,current_hash_value)
                with self.assertRaises(ValueError):writer_operations.apply_hermes_writer_proposal_once(*current_arguments)
                current_apply_mock.assert_not_called()
                current_status_value['receipt']['service']='writer-agent'
                with self.assertRaisesRegex(ValueError,'접수 기록이 변경'):writer_operations.apply_hermes_writer_proposal_once(*current_arguments)
                self.assertEqual(writer_operations.apply_hermes_writer_proposal_once(*current_arguments)['state'],'unknown')
                current_apply_mock.assert_called_once()
                self.assertEqual(json.loads(current_record_path.read_text())['external_change'],'preserve')

    def test_apply_rejects_truncated_or_changed_and_preserves_unknown(self):
        current_job_identifier='20261118-120000-12345678'
        current_hash_value='a'*64
        current_status_value={'receipt':{'state':'accepted','service':'writer-agent','job_id':current_job_identifier},'job':{'stage':'review','proposal_hash':current_hash_value,'truncated':True,'changes':[{'path':'world/town.md','diff':'...'}]}}
        with TemporaryDirectory() as current_root_name, patch.object(writer_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(writer_operations,'read_hermes_writer_status',return_value=current_status_value), patch.object(writer_operations,'call_hermes_writer_service',side_effect=OSError('lost')) as current_apply_mock:
            with self.assertRaises(ValueError):
                writer_operations.apply_hermes_writer_proposal_once('apply_request_456','writer_request_123',current_job_identifier,current_hash_value)
            current_apply_mock.assert_not_called()
            current_status_value['job']['truncated']=False
            with self.assertRaises(OSError):
                writer_operations.apply_hermes_writer_proposal_once('apply_request_456','writer_request_123',current_job_identifier,current_hash_value)
            self.assertEqual(writer_operations.read_writer_apply_receipt('apply_request_456')['state'],'unknown')
            self.assertTrue(writer_operations.apply_hermes_writer_proposal_once('apply_request_456','writer_request_123',current_job_identifier,current_hash_value)['duplicate'])
            current_apply_mock.assert_called_once()

    def test_apply_different_ids_race_with_existing_delegation(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        current_job_identifier='20261118-120000-12345678'
        current_hash_value='a'*64
        current_status_value={'receipt':{'state':'accepted','service':'writer-agent','job_id':current_job_identifier},'job':{'stage':'review','proposal_hash':current_hash_value,'truncated':False,'changes':[{'path':'example.md','diff':'x'}]}}
        current_start_barrier=threading.Barrier(3)
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('writer_request_123','writer-agent',{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
            with patch.object(writer_operations,'HermesDelegationStore',return_value=current_store_value),patch.object(writer_operations,'read_hermes_writer_status',return_value=current_status_value),patch.object(writer_operations,'call_hermes_writer_service',return_value={'status':'applied'}) as current_apply_mock:
                def submit_racing_writer_apply(current_index_value):
                    current_start_barrier.wait(timeout=5)
                    try:
                        return writer_operations.apply_hermes_writer_proposal_once(f'apply_racing_{current_index_value:03d}','writer_request_123',current_job_identifier,current_hash_value)['state']
                    except ValueError as current_error_value:
                        return str(current_error_value)
                with ThreadPoolExecutor(max_workers=3) as current_pool_value:
                    current_result_values=list(current_pool_value.map(submit_racing_writer_apply,range(3)))
                self.assertEqual(current_result_values.count('completed'),1)
                self.assertEqual(sum('기존 적용 접수' in current_result_value for current_result_value in current_result_values),2)
                current_apply_mock.assert_called_once()

    def test_apply_rejects_different_id_for_unknown_proposal(self):
        current_job_identifier='20261118-120000-12345678'
        current_hash_value='a'*64
        current_status_value={'receipt':{'state':'accepted','service':'writer-agent','job_id':current_job_identifier},'job':{'stage':'review','proposal_hash':current_hash_value,'truncated':False,'changes':[{'path':'example.md','diff':'x'}]}}
        with TemporaryDirectory() as current_root_name,patch.object(writer_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))),patch.object(writer_operations,'read_hermes_writer_status',return_value=current_status_value),patch.object(writer_operations,'call_hermes_writer_service',side_effect=OSError('response lost')) as current_apply_mock:
            with self.assertRaises(OSError):writer_operations.apply_hermes_writer_proposal_once('apply_original_123','writer_request_123',current_job_identifier,current_hash_value)
            with self.assertRaisesRegex(ValueError,'기존 적용 접수'):
                writer_operations.apply_hermes_writer_proposal_once('apply_different_123','writer_request_123',current_job_identifier,current_hash_value)
            self.assertEqual(writer_operations.read_writer_apply_receipt('apply_original_123')['state'],'unknown')
            current_apply_mock.assert_called_once()

    def test_writer_rejects_unsafe_diff_path(self):
        current_job_identifier='20261118-120000-12345678'
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('writer_request_789','writer-agent',{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
            for current_unsafe_path in ('../private','C:\\private\\secret.md','world/../secret.md','world//town.md','world/secret\nfile.md',''):
                current_reply_value={'id':current_job_identifier,'status':{'stage':'review'},'proposal':{'changes':[{'path':current_unsafe_path,'diff':'x'}]}}
                with self.subTest(path=current_unsafe_path),patch.object(writer_operations,'HermesDelegationStore',return_value=current_store_value),patch.object(writer_operations,'call_hermes_writer_service',return_value=current_reply_value),self.assertRaises(ValueError):
                    writer_operations.read_hermes_writer_status('writer_request_789')
