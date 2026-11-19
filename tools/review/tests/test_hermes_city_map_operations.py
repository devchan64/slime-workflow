"""도시 맵 접수의 중복과 응답 유실 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.review.domains.hermes_agent import city_map_operations


class HermesCityMapOperationsTests(unittest.TestCase):
    def test_city_change_summary_keeps_all_before_and_after_values(self):
        from tools.review.ui.gradio.hermes_agent_app import format_conversation_city_changes
        current_changes_value=[{'path':['data','buildings',0,'name'],'before':'기존','after':'새 이름'},{'path':['data','objects',2,'visible'],'before':True,'after':False}]
        current_summary_value=format_conversation_city_changes(current_changes_value,'DB 저장 후 원본 동기화 필요')
        self.assertIn('변경 사항 2건',current_summary_value)
        self.assertIn('data / buildings / 0 / name',current_summary_value)
        self.assertIn('변경 전: "기존"',current_summary_value)
        self.assertIn('변경 후: "새 이름"',current_summary_value)
        self.assertIn('변경 전: true',current_summary_value)
        self.assertIn('변경 후: false',current_summary_value)
        self.assertIn('DB 저장 후 원본 동기화 필요',current_summary_value)

    def test_city_history_receipt_is_not_a_gpu_job(self):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_request='chat_'+hashlib.sha256((current_session+':'+current_job+':city').encode()).hexdigest()
        current_page={'session_id':current_session,'offset':0,'snapshot':'b'*64}
        def current_gateway(service,command,payload):
            if command=='hermes-session-view':return {'id':current_session,'offset':0,'snapshot':'b'*64,'messages':[{'job_id':current_job,'session_job_unique':True,'job':{'status':{'status':'completed'},'final_response':'HERMES_CITY_PROPOSAL'}}]}
            if command=='hermes-city-proposal':return {'job_id':current_job,'proposal':{'map':'stonewarm'}}
            if command=='hermes-city-receipt':return {'state':'completed','request_id':current_request,'map':'stonewarm','saved':True}
            raise AssertionError(command)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=current_gateway):
            current_rows,_=operations_history_app.read_operations_current_page_receipts(current_session,current_page)
            self.assertEqual(current_rows[0][3:5],['도시 DB 저장 기록','해당 없음'])
            self.assertEqual(current_rows[0][5:7],['GPU 작업 아님','GPU 예약 대상 아님'])
        def wrong_map_gateway(service,command,payload):
            current_response=current_gateway(service,command,payload)
            if command=='hermes-city-receipt':current_response['map']='other-town'
            return current_response
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=wrong_map_gateway):
            current_rows,_=operations_history_app.read_operations_current_page_receipts(current_session,current_page)
            self.assertEqual(current_rows[0][3],'제안 또는 접수 조회 불가')

    def test_city_conversation_receipt_describes_database_scope(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_card={'session_id':'a'*32,'source_job_id':'job-1','kind':'city','request_id':'request-1'}
        def current_gateway(service,command,payload):
            if command=='hermes-city-receipt':return {'state':'completed','request_id':'request-1','map':'stonewarm','saved':True}
            if command=='hermes-city-proposal':return {'job_id':'job-1','proposal':{'map':'stonewarm'}}
            raise AssertionError(command)
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            current_message=hermes_agent_app.read_conversation_edit_result(current_card,'a'*32,'job-1','city')
            self.assertIn('DB 저장 완료',current_message)
            self.assertIn('동기화',current_message)
        def wrong_map_gateway(service,command,payload):
            current_response=current_gateway(service,command,payload)
            if command=='hermes-city-receipt':current_response['map']='other-town'
            return current_response
        import gradio as gr
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=wrong_map_gateway):
            with self.assertRaises(gr.Error):hermes_agent_app.read_conversation_edit_result(current_card,'a'*32,'job-1','city')

    def test_city_conversation_proposal_checks_original_and_revision(self):
        import json
        import gradio as gr
        from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_city_proposal
        from tools.review.ui.gradio import hermes_agent_app
        current_proposal={'map':'stonewarm','generation':5,'revision':2,'changes':[{'path':['data','buildings',0,'name'],'before':'기존','after':'변경'}]}
        current_answer='HERMES_CITY_PROPOSAL\n'+json.dumps(current_proposal,ensure_ascii=False)+'\nEND_HERMES_CITY_PROPOSAL'
        self.assertEqual(parse_hermes_city_proposal(current_answer),current_proposal)
        current_draft={'map':'stonewarm','generation':5,'revision':2,'document':{'data':{'buildings':[{'name':'기존'}]}}}
        def current_gateway(service,command,payload):
            if command=='hermes-city-proposal':return {'job_id':'job-1','proposal':current_proposal}
            if command=='hermes-city-load':return current_draft
            raise AssertionError(command)
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            current_draft_text,current_changes=hermes_agent_app.load_conversation_city_proposal('job-1')
            self.assertEqual(json.loads(current_draft_text)['document']['data']['buildings'][0]['name'],'변경')
            self.assertEqual(current_draft['document']['data']['buildings'][0]['name'],'기존')
            self.assertEqual(current_changes,current_proposal['changes'])
            current_draft['revision']=3
            with self.assertRaises(gr.Error):hermes_agent_app.load_conversation_city_proposal('job-1')
            current_draft['revision']=2
            current_draft['document']['data']['buildings'][0]['name']='다른 값'
            with self.assertRaises(gr.Error):hermes_agent_app.load_conversation_city_proposal('job-1')
        current_proposal['changes'].append({'path':['data','buildings'],'before':[],'after':[]})
        with self.assertRaises(ValueError):parse_hermes_city_proposal('HERMES_CITY_PROPOSAL\n'+json.dumps(current_proposal)+'\nEND_HERMES_CITY_PROPOSAL')

    def test_unknown_response_is_not_retried_and_can_be_recovered(self):
        current_draft_value = {'map':'stonewarm','generation':5,'revision':2,'document':{'name':'한글'}}
        current_token_value = city_map_operations.validate_hermes_city_draft(current_draft_value)
        def execute_city_command(current_command_name,current_payload_value):
            if current_command_name == 'city-edit-preview':
                return {'token':current_token_value,'changed':True,'cityId':'stonewarm','columns':5,'rows':5,'buildings':1,'objects':0}
            raise OSError('lost response')
        with TemporaryDirectory() as current_root_name, patch.object(city_map_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(city_map_operations,'call_field_map_editor',side_effect=execute_city_command) as current_gateway_mock:
            with self.assertRaises(OSError):
                city_map_operations.save_hermes_city_map_once('city_unknown_123',current_draft_value,current_token_value)
            self.assertEqual(city_map_operations.read_hermes_city_receipt('city_unknown_123')['state'],'unknown')
            self.assertEqual(city_map_operations.list_hermes_city_receipts()['records'][0]['state'],'unknown')
            self.assertTrue(city_map_operations.save_hermes_city_map_once('city_unknown_123',current_draft_value,current_token_value)['duplicate'])
            self.assertEqual(current_gateway_mock.call_count,2)
            current_other_draft = {**current_draft_value,'revision':3}
            with self.assertRaises(ValueError):
                city_map_operations.save_hermes_city_map_once('city_unknown_123',current_other_draft,city_map_operations.validate_hermes_city_draft(current_other_draft))
            self.assertEqual(HermesDelegationStore(Path(current_root_name)).list_delegation_receipts()['records'],[])

    def test_map_save_does_not_overwrite_changed_receipt_or_retry(self):
        import json
        from tools.review.domains.hermes_agent import field_map_operations
        current_city_draft={'map':'stonewarm','generation':5,'revision':2,'document':{'name':'한글'}}
        current_field_draft={'map':'moss-clearing','revision':'old','cells':[],'objects':[]}
        current_cases=((city_map_operations,'city',current_city_draft,city_map_operations.validate_hermes_city_draft(current_city_draft)),(field_map_operations,'field',current_field_draft,field_map_operations.validate_field_map_draft(current_field_draft)))
        for current_module_value,current_kind_name,current_draft_value,current_token_value in current_cases:
            with self.subTest(kind=current_kind_name),TemporaryDirectory() as current_root_name:
                current_store_value=HermesDelegationStore(Path(current_root_name))
                current_request_value=current_kind_name+'_changed_123'
                current_record_path=current_store_value.resolve_delegation_record_path(current_request_value)
                current_calls=[]
                def current_editor_response(current_command_name,current_payload_value):
                    current_calls.append(current_command_name)
                    if current_command_name=='city-edit-preview':return {'token':current_token_value,'changed':True,'cityId':'stonewarm','columns':5,'rows':5,'buildings':1,'objects':0}
                    if current_command_name=='map-edit-preview':return {'token':current_token_value,'changed':True,'reachable':12,'objects':0,'cells':0}
                    current_changed_record=json.loads(current_record_path.read_text())
                    current_changed_record['external_change']='preserve'
                    current_record_path.write_text(json.dumps(current_changed_record))
                    return {'saved':True}
                current_save_function=city_map_operations.save_hermes_city_map_once if current_kind_name=='city' else field_map_operations.save_hermes_field_map_once
                with patch.object(current_module_value,'HermesDelegationStore',return_value=current_store_value),patch.object(current_module_value,'call_field_map_editor',side_effect=current_editor_response):
                    with self.assertRaisesRegex(ValueError,'접수 기록이 변경'):current_save_function(current_request_value,current_draft_value,current_token_value)
                    self.assertEqual(current_save_function(current_request_value,current_draft_value,current_token_value)['state'],'unknown')
                self.assertEqual(len(current_calls),2)
                self.assertEqual(json.loads(current_record_path.read_text())['external_change'],'preserve')

    def test_stale_or_invalid_draft_never_saves(self):
        current_draft_value = {'map':'stonewarm','generation':5,'revision':2,'document':{}}
        with patch.object(city_map_operations,'call_field_map_editor',side_effect=ValueError('도시 원장이 변경되었습니다.')) as current_gateway_mock:
            with self.assertRaises(ValueError):
                city_map_operations.preview_hermes_city_map(current_draft_value)
            self.assertEqual(current_gateway_mock.call_args.args[0],'city-edit-preview')
        with self.assertRaises(ValueError):
            city_map_operations.validate_hermes_city_draft({**current_draft_value,'generation':True})
