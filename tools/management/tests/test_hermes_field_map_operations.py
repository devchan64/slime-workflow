"""Hermes 야외 맵 초안 검증과 중복 방지 저장 검사."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.management.domains.hermes_agent import field_map_operations


class HermesFieldMapOperationsTests(unittest.TestCase):
    def test_database_preview_rejects_before_record_or_save(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore
        current_draft_record={'map':'sample','revision':'revision','cells':[],'objects':[]}
        current_token_value=field_map_operations.validate_field_map_draft(current_draft_record)
        current_preview_record={'token':current_token_value,'changed':True,'reachable':1,'objects':0,'cells':0,'save_available':False,'save_block_reason':'database'}
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            with patch.object(field_map_operations,'HermesDelegationStore',return_value=current_store_value),patch.object(field_map_operations,'call_field_map_editor',return_value=current_preview_record) as current_gateway_mock:
                with self.assertRaisesRegex(ValueError,'신규 저장은 중단'):
                    field_map_operations.save_hermes_field_map_once('field_test_123',current_draft_record,current_token_value)
                self.assertFalse(current_store_value.resolve_delegation_record_path('field_test_123').exists())
                self.assertEqual(current_gateway_mock.call_args_list[0].args[0],'map-edit-preview')
                self.assertNotIn('map-edit-save',[current_call.args[0] for current_call in current_gateway_mock.call_args_list])

    def test_field_change_summary_uses_observed_values_and_marks_missing(self):
        from tools.management.ui.gradio.hermes_agent_app import format_conversation_field_changes
        current_source_value={'tiles':{'rows':['ab']},'terrain':{'elevations':[[1,2]],'blocked':[[1,0]]}}
        current_cells_value=[{'column':1,'row':0,'tile':'c','height':3,'blocked':False},{'column':4,'row':9,'tile':'a'}]
        current_summary_value=format_conversation_field_changes(current_cells_value,current_source_value,'원본 동기화 확인')
        self.assertIn('변경할 셀 2건',current_summary_value)
        self.assertIn('타일 코드: "b" → "c"',current_summary_value)
        self.assertIn('높이: 2 → 3',current_summary_value)
        self.assertIn('통행 차단: true → false',current_summary_value)
        self.assertIn('타일 코드: 확인 불가 → "a"',current_summary_value)
        self.assertIn('주변 배치',current_summary_value)
        current_source_value['terrain']['blocked']=[['bad',0]]
        self.assertIn('통행 차단: 확인 불가 → false',format_conversation_field_changes(current_cells_value,current_source_value,'확인'))

    def test_database_alignment_reports_changed_revision_as_unavailable(current_test_case):
        current_draft={'map':'sample','revision':'revision-1','cells':[],'objects':[]}
        current_token=field_map_operations.validate_field_map_draft(current_draft)
        current_preview={'token':current_token,'changed':True,'reachable':1,'objects':0,'cells':0,'save_available':False,'save_block_reason':'database'}
        current_load={'map':'sample','revision':'revision-1','tiles':{},'terrain':{},'textures':[],'codes':{}}
        with patch.object(field_map_operations,'call_field_map_editor',return_value=current_preview),patch.object(field_map_operations,'load_hermes_field_map',side_effect=[current_load,{**current_load,'revision':'revision-2'}]),patch('tools.management.domains.map_assets.source_consistency.inspect_field_source_alignment',return_value={'status':'matched','note':'test'}):
            current_result=field_map_operations.preview_hermes_field_map(current_draft)
            current_test_case.assertFalse(current_result['save_available'])
            current_test_case.assertEqual(current_result['source_alignment']['status'],'unavailable')

    def test_conversation_field_review_shows_alignment_and_blocks_save(current_test_case):
        import json
        from tools.management.ui.gradio import hermes_agent_app
        current_draft={'map':'sample','revision':'revision-1','cells':[],'objects':[]}
        current_token=field_map_operations.validate_field_map_draft(current_draft)
        current_preview={'token':current_token,'changed':True,'reachable':1,'objects':0,'cells':0,'save_available':False,'save_block_reason':'database','source_alignment':{'status':'mismatch','note':'test'}}
        def respond_review_gateway(current_service,current_command,current_payload):
            if current_command=='hermes-field-receipt':return {'state':'not_found'}
            if current_command=='hermes-field-preview':return current_preview
            raise AssertionError('예상하지 못한 명령')
        with patch.object(hermes_agent_app,'find_conversation_session_job'),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=respond_review_gateway),patch.object(hermes_agent_app,'load_hermes_field_map_proposal',return_value=('sample',json.dumps(current_draft),{'tiles':{'rows':[]},'terrain':{}},None)):
            current_card,current_text,_,current_notice=hermes_agent_app.prepare_conversation_edit_review('session-123','job-123','field')
            current_test_case.assertFalse(current_card['ready'])
            current_test_case.assertIn('등록 원본 비교: 불일치',current_text)
            current_test_case.assertIn('저장',current_notice)

    def test_unknown_block_reason_does_not_assume_database(current_test_case):
        import json
        from tools.management.ui.gradio import hermes_agent_app
        current_draft={'map':'sample','revision':'revision','cells':[],'objects':[]}
        current_token=field_map_operations.validate_field_map_draft(current_draft)
        current_preview={'token':current_token,'changed':True,'reachable':1,'objects':0,'cells':0,'save_available':False}
        with patch.object(field_map_operations,'call_field_map_editor',return_value=current_preview),patch.object(field_map_operations,'load_hermes_field_map') as current_load:
            current_result=field_map_operations.preview_hermes_field_map(current_draft)
            current_test_case.assertNotIn('source_alignment',current_result)
            current_load.assert_not_called()
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_preview) as current_gateway:
            current_review,current_summary,_=hermes_agent_app.review_hermes_field_map_draft(json.dumps(current_draft),'field_test_123')
            current_test_case.assertIn('차단 사유를 확인할 수 없습니다',current_summary)
            current_test_case.assertNotIn('DB 모드',current_summary)
            current_test_case.assertIn('저장 요청을 보내지 않았습니다',hermes_agent_app.save_hermes_field_map_draft(current_review,json.dumps(current_draft),'field_test_123')[2])
            current_test_case.assertEqual(current_gateway.call_count,1)

    def test_unknown_block_reason_rejects_direct_save_without_receipt(current_test_case):
        current_draft={'map':'sample','revision':'revision','cells':[],'objects':[]}
        current_token=field_map_operations.validate_field_map_draft(current_draft)
        for current_available in (False,None):
            current_preview={'token':current_token,'changed':True,'reachable':1,'objects':0,'cells':0,'save_available':current_available}
            with current_test_case.subTest(save_available=current_available),TemporaryDirectory() as current_directory,patch.object(field_map_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_directory))),patch.object(field_map_operations,'call_field_map_editor',return_value=current_preview) as current_editor:
                with current_test_case.assertRaisesRegex(ValueError,'차단 사유를 확인할 수 없어'):
                    field_map_operations.save_hermes_field_map_once('field_test_123',current_draft,current_token)
                current_test_case.assertFalse((Path(current_directory)/'field_test_123.json').exists())
                current_test_case.assertEqual([current_call.args[0] for current_call in current_editor.call_args_list],['map-edit-preview'])

    def test_field_block_messages_distinguish_reasons(current_test_case):
        from tools.management.ui.gradio.hermes_agent_app import describe_field_map_save_block
        current_test_case.assertIn('이전 야외 맵 저장이 중단',describe_field_map_save_block({'save_block_reason':'interrupted'}))
        current_test_case.assertIn('DB 모드',describe_field_map_save_block({'save_block_reason':'database'}))
        current_test_case.assertNotIn('DB 모드',describe_field_map_save_block({}))

    def test_interrupted_save_is_blocked_before_receipt(current_test_case):
        current_draft={'map':'sample','revision':'revision','cells':[],'objects':[]}
        current_token=field_map_operations.validate_field_map_draft(current_draft)
        current_preview={'token':current_token,'changed':True,'reachable':1,'objects':0,'cells':0,'save_available':False,'save_block_reason':'interrupted'}
        with TemporaryDirectory() as current_directory,patch.object(field_map_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_directory))),patch.object(field_map_operations,'call_field_map_editor',return_value=current_preview) as current_editor:
            current_result=field_map_operations.preview_hermes_field_map(current_draft)
            current_test_case.assertEqual(current_result['save_block_reason'],'interrupted')
            current_test_case.assertNotIn('source_alignment',current_result)
            with current_test_case.assertRaises(ValueError):field_map_operations.save_hermes_field_map_once('field_test_123',current_draft,current_token)
            current_test_case.assertFalse((Path(current_directory)/'field_test_123.json').exists())
            current_test_case.assertTrue(all(current_call.args[0]=='map-edit-preview' for current_call in current_editor.call_args_list))

    def test_preview_and_concurrent_save_reuses_receipt(self):
        current_draft_value = {'map':'moss-clearing','revision':'old-revision','cells':[],'objects':[]}
        current_token_value = field_map_operations.validate_field_map_draft(current_draft_value)
        current_calls_list = []
        def execute_field_command(current_command_name,current_payload_value):
            current_calls_list.append(current_command_name)
            if current_command_name == 'map-edit-preview':
                return {'token':current_token_value,'changed':True,'reachable':12,'objects':0,'cells':0,'save_available':True,'render':{'secret':'private'}}
            return {'saved':True,'backup':'private'}
        with TemporaryDirectory() as current_root_name:
            current_store_value = HermesDelegationStore(Path(current_root_name))
            with patch.object(field_map_operations,'HermesDelegationStore',return_value=current_store_value), patch.object(field_map_operations,'call_field_map_editor',side_effect=execute_field_command):
                current_preview_value = field_map_operations.preview_hermes_field_map(current_draft_value)
                self.assertNotIn('private',str(current_preview_value))
                with ThreadPoolExecutor(max_workers=4) as current_executor_value:
                    current_results_list = list(current_executor_value.map(lambda unused_value:field_map_operations.save_hermes_field_map_once('field_request_123',current_draft_value,current_token_value),range(4)))
                self.assertEqual(current_calls_list.count('map-edit-save'),1)
                self.assertEqual(sum(not item['duplicate'] for item in current_results_list),1)
                self.assertTrue(all(item['request_id']=='field_request_123' for item in current_results_list))
                with self.assertRaises(ValueError):
                    field_map_operations.save_hermes_field_map_once('field_request_123',{**current_draft_value,'map':'another'},field_map_operations.validate_field_map_draft({**current_draft_value,'map':'another'}))
                self.assertEqual(current_store_value.list_delegation_receipts()['records'],[])

    def test_legacy_preview_cannot_start_new_save(self):
        current_draft_record={'map':'sample','revision':'revision','cells':[],'objects':[]}
        current_token_value=field_map_operations.validate_field_map_draft(current_draft_record)
        current_preview_record={'token':current_token_value,'changed':True,'reachable':1,'objects':0,'cells':0}
        with TemporaryDirectory() as current_root_name:
            current_store_value=HermesDelegationStore(Path(current_root_name))
            with patch.object(field_map_operations,'HermesDelegationStore',return_value=current_store_value),patch.object(field_map_operations,'call_field_map_editor',return_value=current_preview_record) as current_gateway_mock:
                with self.assertRaisesRegex(ValueError,'차단 사유를 확인할 수 없어'):
                    field_map_operations.save_hermes_field_map_once('field_test_123',current_draft_record,current_token_value)
                self.assertFalse(current_store_value.resolve_delegation_record_path('field_test_123').exists())
                self.assertEqual(current_gateway_mock.call_count,1)

    def test_field_ui_consumes_real_service_save_receipt(self):
        import json
        from tools.management.ui.gradio import hermes_agent_app
        current_draft={'map':'moss-clearing','revision':'revision','cells':[],'objects':[]}
        current_token=field_map_operations.validate_field_map_draft(current_draft)
        current_review={'request_id':'field_request_123','draft':current_draft,'token':current_token,'save_available':True}
        current_commands=[]
        def current_editor(current_command,current_payload):
            current_commands.append(current_command)
            if current_command=='map-edit-preview':return {'token':current_token,'changed':True,'reachable':1,'objects':0,'cells':0,'save_available':True}
            if current_command=='map-edit-save':return {'saved':True}
            raise ValueError('unexpected command')
        def current_gateway(current_service,current_command,current_payload):
            self.assertEqual((current_service,current_command),('hermes-agent','hermes-field-save'))
            return field_map_operations.save_hermes_field_map_once(current_payload['request_id'],current_payload['draft'],current_payload['token'])
        with TemporaryDirectory() as current_directory, patch.object(field_map_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_directory))), patch.object(field_map_operations,'call_field_map_editor',side_effect=current_editor), patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            for current_iteration in range(2):
                _,_,current_status=hermes_agent_app.save_hermes_field_map_draft(current_review,json.dumps(current_draft),current_review['request_id'])
                self.assertIn('맵 저장 완료',current_status)
            self.assertEqual(current_commands.count('map-edit-save'),1)

    def test_lost_save_response_is_not_retried(self):
        current_draft_value = {'map':'moss-clearing','revision':'old','cells':[],'objects':[]}
        current_token_value = field_map_operations.validate_field_map_draft(current_draft_value)
        def execute_field_command(current_command_name,current_payload_value):
            if current_command_name == 'map-edit-preview':
                return {'token':current_token_value,'changed':True,'reachable':12,'objects':0,'cells':0,'save_available':True}
            raise OSError('lost response')
        with TemporaryDirectory() as current_root_name, patch.object(field_map_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(field_map_operations,'call_field_map_editor',side_effect=execute_field_command) as current_gateway_mock:
            with self.assertRaises(OSError):
                field_map_operations.save_hermes_field_map_once('field_request_456',current_draft_value,current_token_value)
            self.assertEqual(field_map_operations.save_hermes_field_map_once('field_request_456',current_draft_value,current_token_value)['state'],'unknown')
            self.assertEqual(current_gateway_mock.call_count,2)

    def test_receipts_recover_unknown_and_filter_corruption(self):
        current_draft_value = {'map':'moss-clearing','revision':'r','cells':[],'objects':[]}
        current_token_value = field_map_operations.validate_field_map_draft(current_draft_value)
        def execute_field_command(current_command_name,current_payload_value):
            if current_command_name == 'map-edit-preview':
                return {'token':current_token_value,'changed':True,'reachable':12,'objects':0,'cells':0,'save_available':True}
            raise OSError('lost')
        with TemporaryDirectory() as current_root_name, patch.object(field_map_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_root_name))), patch.object(field_map_operations,'call_field_map_editor',side_effect=execute_field_command):
            with self.assertRaises(OSError):
                field_map_operations.save_hermes_field_map_once('field_unknown_123',current_draft_value,current_token_value)
            (Path(current_root_name)/'bad_record_123.json').write_text('{')
            current_receipt_value = field_map_operations.read_hermes_field_receipt('field_unknown_123')
            self.assertEqual(current_receipt_value['state'],'unknown')
            self.assertEqual(field_map_operations.list_hermes_field_receipts()['records'],[{**current_receipt_value,'updated_at':field_map_operations.list_hermes_field_receipts()['records'][0]['updated_at']}])
            self.assertEqual(field_map_operations.read_hermes_field_receipt('missing_123')['state'],'not_found')
            with self.assertRaises(ValueError):
                field_map_operations.read_hermes_field_receipt('../private')

    def test_region_limits_paging_and_revision(self):
        current_map_value = {'map':'sample','revision':'abc','tiles':{'rows':['ab','ba'],'objects':[{'id':'tower','kind':'ward-tower','position':{'column':0,'row':0}},{'id':'tree','kind':'decoration','position':{'column':1,'row':1},'textureKey':'tree-v1','tileAnchor':'center','private':'secret'}]},'terrain':{'columns':2,'rows':2,'elevations':[[0,1],[2,3]],'blocked':[[1,0]]},'codes':{'a':'grass','b':'road'},'textures':[]}
        with patch.object(field_map_operations,'load_hermes_field_region_source',return_value=current_map_value):
            current_page_value = field_map_operations.read_hermes_field_region({'map':'sample','width':2,'height':2,'limit':1})
            self.assertEqual(len(current_page_value['cells']),4)
            self.assertEqual(current_page_value['summary'],{'cell_count':4,'terrain_counts':{'grass':2,'road':2},'height_counts':{'0':1,'1':1,'2':1,'3':1},'source_blocked_count':1})
            self.assertTrue(current_page_value['cells'][1]['blocked'])
            self.assertEqual(current_page_value['object_next_offset'],1)
            with self.assertRaisesRegex(ValueError,'첫 조회의 revision'):
                field_map_operations.read_hermes_field_region({'map':'sample','offset':1,'limit':1})
            current_next_value = field_map_operations.read_hermes_field_region({'map':'sample','revision':'abc','offset':1,'limit':1})
            self.assertEqual(current_next_value['objects'][0]['id'],'tree')
            self.assertNotIn('secret',str(current_next_value))
            with self.assertRaises(ValueError):
                field_map_operations.read_hermes_field_region({'map':'sample','revision':'stale'})
            for current_invalid_value in ({'map':'sample','width':17},{'map':'sample','column':True},{'map':'sample','offset':-1},{'map':'sample','command':'save'}):
                with self.assertRaises(ValueError):
                    field_map_operations.read_hermes_field_region(current_invalid_value)

    def test_invalid_token_and_unverified_preview_do_not_save(self):
        current_draft_value = {'map':'moss-clearing','revision':'old','cells':[],'objects':[]}
        with patch.object(field_map_operations,'call_field_map_editor',return_value={'token':'bad'}) as current_gateway_mock:
            with self.assertRaises(ValueError):
                field_map_operations.save_hermes_field_map_once('field_request_789',current_draft_value,'a'*64)
            current_gateway_mock.assert_not_called()
            with self.assertRaises(ValueError):
                field_map_operations.preview_hermes_field_map(current_draft_value)
