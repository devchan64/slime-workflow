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
        current_status_value={'receipt':{'state':'accepted','job_id':current_job_identifier},'job':{'stage':'review','proposal_hash':current_hash_value,'truncated':False,'changes':[{'path':'world/town.md','diff':'-old\n+new'}]}}
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

    def test_apply_rejects_truncated_or_changed_and_preserves_unknown(self):
        current_job_identifier='20261118-120000-12345678'
        current_hash_value='a'*64
        current_status_value={'receipt':{'state':'accepted','job_id':current_job_identifier},'job':{'stage':'review','proposal_hash':current_hash_value,'truncated':True,'changes':[{'path':'world/town.md','diff':'...'}]}}
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

    def test_writer_rejects_unsafe_diff_path(self):
        current_job_identifier='20261118-120000-12345678'
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            current_store_value.execute_service_delegation_once('writer_request_789','writer-agent',{},lambda current_request_value:{'id':current_job_identifier},lambda current_request_value:None)
            current_reply_value={'id':current_job_identifier,'status':{'stage':'review'},'proposal':{'changes':[{'path':'../private','diff':'x'}]}}
            with patch.object(writer_operations,'HermesDelegationStore',return_value=current_store_value), patch.object(writer_operations,'call_hermes_writer_service',return_value=current_reply_value), self.assertRaises(ValueError):
                writer_operations.read_hermes_writer_status('writer_request_789')
