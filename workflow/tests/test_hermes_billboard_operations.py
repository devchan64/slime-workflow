"""빌보드 위임의 검토 고정·중복 방지·응답 유실을 검사한다."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.domains.hermes_agent import billboard_operations
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesBillboardOperationTests(unittest.TestCase):
    def test_unconfigured_file_asset_previews_all_initial_properties(self):
        catalog={'revision':'abc','assets':[{'texture':'grass-v1','properties':None}]}
        with patch.object(billboard_operations,'call_field_map_editor',return_value=catalog):
            source=billboard_operations.load_hermes_billboard_edit('grass-v1')
        self.assertTrue(source['initial'])
        self.assertEqual(source['properties']['displayHeight'],128)
        self.assertEqual(set(source['properties']),billboard_operations.EDITOR_MUTABLE_FIELDS-{'billboardPlacementAnchor'})

    def test_change_summary_shows_values_maps_and_warnings(self):
        from gui.ui.gradio.hermes_agent_app import format_conversation_billboard_changes
        current_preview_value={'changes':[{'texture':'tree-v1','before':{'displayHeight':520,'anchorY':1},'after':{'displayHeight':500,'anchorY':1}}],'maps':['assets/maps/field_tiles/meadow.yaml'],'map_warnings':[{'map':'assets/maps/field_tiles/meadow.yaml','message':'접지 확인'}],'note':'맵은 다시 확인'}
        current_summary_value=format_conversation_billboard_changes({'displayHeight':520,'anchorY':1,'other':False},current_preview_value,'저장 시 원본 변경')
        self.assertIn('에셋: tree-v1',current_summary_value)
        self.assertIn('표시 높이: 520 → 500',current_summary_value)
        self.assertIn('other: false',current_summary_value)
        self.assertIn('assets/maps/field_tiles/meadow.yaml: 접지 확인',current_summary_value)
        self.assertIn('저장 시 원본 변경',current_summary_value)

    def setUp(self):
        self.current_temporary_root=tempfile.TemporaryDirectory()
        self.addCleanup(self.current_temporary_root.cleanup)
        self.current_store_value=HermesDelegationStore(Path(self.current_temporary_root.name))
        self.current_draft_record={'revision':'abc','changes':[{'texture':'grass-v1','values':{'displayHeight':130}}]}
        self.current_token_value=billboard_operations.validate_billboard_edit_draft(self.current_draft_record)
        self.current_preview_record={'token':self.current_token_value,'changes':[{'texture':'grass-v1','before':{'displayHeight':128},'after':{'displayHeight':130}}],'maps':[],'map_warnings':[],'note':'검수'}
        self.current_store_patch=patch.object(billboard_operations,'HermesDelegationStore',return_value=self.current_store_value)
        self.current_store_patch.start()
        self.addCleanup(self.current_store_patch.stop)

    def test_history_asset_target_matching_and_legacy(self):
        import hashlib
        from gui.ui.gradio import operations_history_app
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_page={'session_id':current_session,'offset':0,'snapshot':'b'*64}
        for current_kind,current_target_key,current_good_value,current_bad_value,current_proposal in (
            ('billboard','textures',['tree-a','tree-b'],['tree-a'],{'changes':[{'texture':'tree-b'},{'texture':'tree-a'}]}),
            ('sprite','path','assets/sprites/test.png','assets/sprites/other.png',{'path':'assets/sprites/test.png'})):
            with self.subTest(kind=current_kind):
                current_request='chat_'+hashlib.sha256((current_session+':'+current_job+':'+current_kind).encode()).hexdigest()
                current_receipt={'state':'completed','request_id':current_request,'saved':True}
                def current_gateway(service,command,payload):
                    if command=='hermes-session-view':return {'id':current_session,'offset':0,'snapshot':'b'*64,'messages':[{'job_id':current_job,'session_job_unique':True,'job':{'status':{'status':'completed'},'final_response':'HERMES_'+current_kind.upper()+'_PROPOSAL'}}]}
                    if command=='hermes-'+current_kind+'-proposal':return {'job_id':current_job,'proposal':current_proposal}
                    if command=='hermes-'+current_kind+'-receipt':return current_receipt
                    raise AssertionError(command)
                with patch.object(operations_history_app,'execute_remote_management_command',side_effect=current_gateway):
                    current_rows,_=operations_history_app.read_operations_current_page_receipts(current_session,current_page)
                    self.assertIn('대상 미확인',current_rows[0][3])
                    current_receipt[current_target_key]=current_bad_value
                    current_rows,_=operations_history_app.read_operations_current_page_receipts(current_session,current_page)
                    self.assertEqual(current_rows[0][3],'제안 또는 접수 조회 불가')
                    current_receipt['state']='unknown'
                    current_rows,_=operations_history_app.read_operations_current_page_receipts(current_session,current_page)
                    self.assertEqual(current_rows[0][3],'제안 또는 접수 조회 불가')
                    current_receipt[current_target_key]=current_good_value
                    current_rows,_=operations_history_app.read_operations_current_page_receipts(current_session,current_page)
                    self.assertEqual(current_rows[0][3],'접수 확인 필요')

    def test_confirmed_save_and_duplicate_are_single_dispatch(self):
        def execute_test_editor(current_command_name,current_payload_record):
            return {'saved':True} if current_command_name=='asset-save-reviewed' else self.current_preview_record
        with patch.object(billboard_operations,'call_field_map_editor',side_effect=execute_test_editor) as current_editor_mock:
            current_review_record=billboard_operations.preview_hermes_billboard_edit(self.current_draft_record)
            current_save_args=('request_123',self.current_draft_record,self.current_token_value,current_review_record['review_sha256'])
            self.assertTrue(billboard_operations.save_hermes_billboard_edit_once(*current_save_args)['saved'])
            self.assertEqual(billboard_operations.read_hermes_billboard_edit_receipt('request_123')['textures'],sorted(item['texture'] for item in self.current_draft_record['changes']))
            self.assertTrue(billboard_operations.save_hermes_billboard_edit_once(*current_save_args)['duplicate'])
            self.assertEqual(sum(current_call.args[0]=='asset-save-reviewed' for current_call in current_editor_mock.call_args_list),1)
            self.assertEqual(billboard_operations.read_hermes_billboard_edit_receipt('request_123')['state'],'completed')

    def test_database_ledger_status_survives_receipt_and_duplicate(self):
        from gui.ui.gradio.hermes_agent_app import format_billboard_saved_status
        def execute_test_editor(current_command_name,current_payload_record):
            return {'saved':True,'snapshot':'pending'} if current_command_name=='asset-save-reviewed' else self.current_preview_record
        with patch.object(billboard_operations,'call_field_map_editor',side_effect=execute_test_editor):
            current_review_record=billboard_operations.preview_hermes_billboard_edit(self.current_draft_record)
            current_save_args=('request_123',self.current_draft_record,self.current_token_value,current_review_record['review_sha256'])
            current_saved_record=billboard_operations.save_hermes_billboard_edit_once(*current_save_args)
            self.assertEqual(current_saved_record['ledger_status_at_save'],'pending')
            self.assertEqual(billboard_operations.read_hermes_billboard_edit_receipt('request_123')['ledger_status_at_save'],'pending')
            self.assertEqual(billboard_operations.save_hermes_billboard_edit_once(*current_save_args)['ledger_status_at_save'],'pending')
            self.assertIn('저장 당시 원장 반영 대기',format_billboard_saved_status(current_saved_record))
            self.assertNotIn('DB 저장',format_billboard_saved_status({'saved':True}))

    def test_changed_receipt_after_save_is_preserved_and_not_retried(self):
        import json
        current_record_path=self.current_store_value.resolve_delegation_record_path('request_123')
        def current_editor_response(current_command_name,current_payload_record):
            if current_command_name!='asset-save-reviewed':return self.current_preview_record
            current_changed_record=json.loads(current_record_path.read_text())
            current_changed_record['external_change']='preserve'
            current_record_path.write_text(json.dumps(current_changed_record))
            return {'saved':True}
        with patch.object(billboard_operations,'call_field_map_editor',side_effect=current_editor_response) as current_editor_mock:
            current_review_record=billboard_operations.preview_hermes_billboard_edit(self.current_draft_record)
            current_save_args=('request_123',self.current_draft_record,self.current_token_value,current_review_record['review_sha256'])
            with self.assertRaisesRegex(ValueError,'접수 기록이 변경'):billboard_operations.save_hermes_billboard_edit_once(*current_save_args)
            self.assertEqual(billboard_operations.save_hermes_billboard_edit_once(*current_save_args)['state'],'unknown')
            self.assertEqual(sum(current_call.args[0]=='asset-save-reviewed' for current_call in current_editor_mock.call_args_list),1)
            self.assertEqual(json.loads(current_record_path.read_text())['external_change'],'preserve')

    def test_changed_warning_requires_new_review(self):
        with patch.object(billboard_operations,'call_field_map_editor',return_value=self.current_preview_record) as current_editor_mock:
            current_review_record=billboard_operations.preview_hermes_billboard_edit(self.current_draft_record)
            self.current_preview_record['maps']=['assets/maps/field_tiles/meadow.yaml']
            self.current_preview_record['map_warnings']=[{'map':'assets/maps/field_tiles/meadow.yaml','message':'충돌'}]
            with self.assertRaisesRegex(ValueError,'다시 확인'):
                billboard_operations.save_hermes_billboard_edit_once('request_123',self.current_draft_record,self.current_token_value,current_review_record['review_sha256'])
            self.assertFalse(any(current_call.args[0]=='asset-save-reviewed' for current_call in current_editor_mock.call_args_list))

    def test_lost_save_response_is_not_retried(self):
        def execute_test_editor(current_command_name,current_payload_record):
            if current_command_name=='asset-save-reviewed':raise RuntimeError('응답 유실')
            return self.current_preview_record
        with patch.object(billboard_operations,'call_field_map_editor',side_effect=execute_test_editor) as current_editor_mock:
            current_review_record=billboard_operations.preview_hermes_billboard_edit(self.current_draft_record)
            current_save_args=('request_123',self.current_draft_record,self.current_token_value,current_review_record['review_sha256'])
            with self.assertRaises(RuntimeError):billboard_operations.save_hermes_billboard_edit_once(*current_save_args)
            self.assertEqual(billboard_operations.save_hermes_billboard_edit_once(*current_save_args)['state'],'unknown')
            self.assertEqual(sum(current_call.args[0]=='asset-save-reviewed' for current_call in current_editor_mock.call_args_list),1)

    def test_disallowed_fields_and_nonfinite_values_rejected(self):
        for current_change_values in ({'image':'x'},{'displayHeight':float('nan')}):
            with self.subTest(values=current_change_values),self.assertRaises(ValueError):
                billboard_operations.validate_billboard_edit_draft({'revision':'abc','changes':[{'texture':'grass-v1','values':current_change_values}]})

    def test_real_gateway_dispatches_reviewed_save_under_editor_lock(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import json
        import threading
        from workflow.common.management_gateway import ManagementCommandGateway, execute_management_command
        from workflow.domains.map_assets import editor, resize
        current_call_order=[]
        def execute_test_preview(current_payload_record):
            current_call_order.append('preview')
            return self.current_preview_record
        def execute_test_save(current_payload_record):
            current_call_order.append('save')
            return {'saved':True}
        current_gateway_value=ManagementCommandGateway({'map-assets':resize.handle_map_resize_request})
        class GatewayTestHandler(BaseHTTPRequestHandler):
            def do_POST(current_handler_value):
                current_gateway_value.handle(current_handler_value)
            def log_message(current_handler_value,current_log_format,*current_log_values):
                pass
        current_server_value=ThreadingHTTPServer(('127.0.0.1',0),GatewayTestHandler)
        current_server_thread=threading.Thread(target=current_server_value.serve_forever,daemon=True)
        current_server_thread.start()
        try:
            current_preview_digest=editor.hash_billboard_review_result(self.current_preview_record)
            current_save_payload={**self.current_draft_record,'token':self.current_token_value,'review_sha256':current_preview_digest}
            with patch.dict('os.environ',{'SLIME_CONTENT_STORAGE':'file'}), patch.object(resize,'RESIZE_STORAGE_DIRECTORY',Path(self.current_temporary_root.name)/'locks'), patch.object(editor,'preview_editor_changes',side_effect=execute_test_preview), patch.object(editor,'save_editor_changes',side_effect=execute_test_save):
                current_response_record=execute_management_command('map-assets','asset-save-reviewed',current_save_payload,'http://127.0.0.1:'+str(current_server_value.server_port))
            self.assertTrue(current_response_record['saved'])
            self.assertEqual(current_call_order,['preview','save'])
        finally:
            current_server_value.shutdown()
            current_server_value.server_close()
            current_server_thread.join(timeout=5)
