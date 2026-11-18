"""빌보드 위임의 검토 고정·중복 방지·응답 유실을 검사한다."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.review.domains.hermes_agent import billboard_operations
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesBillboardOperationTests(unittest.TestCase):
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

    def test_confirmed_save_and_duplicate_are_single_dispatch(self):
        def execute_test_editor(current_command_name,current_payload_record):
            return {'saved':True} if current_command_name=='asset-save-reviewed' else self.current_preview_record
        with patch.object(billboard_operations,'call_field_map_editor',side_effect=execute_test_editor) as current_editor_mock:
            current_review_record=billboard_operations.preview_hermes_billboard_edit(self.current_draft_record)
            current_save_args=('request_123',self.current_draft_record,self.current_token_value,current_review_record['review_sha256'])
            self.assertTrue(billboard_operations.save_hermes_billboard_edit_once(*current_save_args)['saved'])
            self.assertTrue(billboard_operations.save_hermes_billboard_edit_once(*current_save_args)['duplicate'])
            self.assertEqual(sum(current_call.args[0]=='asset-save-reviewed' for current_call in current_editor_mock.call_args_list),1)
            self.assertEqual(billboard_operations.read_hermes_billboard_edit_receipt('request_123')['state'],'completed')

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
        from tools.review.common.management_gateway import ManagementCommandGateway, execute_management_command
        from tools.review.domains.map_assets import editor, resize
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
