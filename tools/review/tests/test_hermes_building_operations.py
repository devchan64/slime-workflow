"""건물 앵커 위임의 검토·충돌·응답 유실을 검사한다."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.review.domains.hermes_agent import building_operations
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesBuildingOperationsTests(unittest.TestCase):
    def test_conversation_receipt_history_identifies_database_and_no_gpu(self):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_request='chat_'+hashlib.sha256((current_session+':'+current_job+':building').encode()).hexdigest()
        current_page={'session_id':current_session,'offset':0,'snapshot':'b'*64}
        def current_gateway(service,command,payload):
            if command=='hermes-session-view':return {'id':current_session,'offset':0,'snapshot':'b'*64,'messages':[{'job_id':current_job,'session_job_unique':True,'job':{'status':{'status':'completed'},'final_response':'HERMES_BUILDING_PROPOSAL'}}]}
            if command=='hermes-building-proposal':return {'job_id':current_job,'proposal':{'texture':'town-test-v1'}}
            if command=='hermes-building-receipt':return {'state':'completed','request_id':current_request,'saved':True,'texture':'town-test-v1'}
            raise AssertionError(command)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=current_gateway):
            current_rows,_=operations_history_app.read_operations_current_page_receipts(current_session,current_page)
            self.assertEqual(current_rows[0][3:7],['건물 앵커 DB 저장 기록','해당 없음','GPU 작업 아님','GPU 예약 대상 아님'])

    def test_history_distinguishes_legacy_and_mismatched_building_target(self):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_request='chat_'+hashlib.sha256((current_session+':'+current_job+':building').encode()).hexdigest()
        current_page={'session_id':current_session,'offset':0,'snapshot':'b'*64}
        current_receipt={'state':'completed','request_id':current_request,'saved':True}
        def current_gateway(service,command,payload):
            if command=='hermes-session-view':return {'id':current_session,'offset':0,'snapshot':'b'*64,'messages':[{'job_id':current_job,'session_job_unique':True,'job':{'status':{'status':'completed'},'final_response':'HERMES_BUILDING_PROPOSAL'}}]}
            if command=='hermes-building-proposal':return {'job_id':current_job,'proposal':{'texture':'town-test-v1'}}
            if command=='hermes-building-receipt':return current_receipt
            raise AssertionError(command)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=current_gateway):
            current_rows,_=operations_history_app.read_operations_current_page_receipts(current_session,current_page)
            self.assertIn('대상 미확인',current_rows[0][3])
            current_receipt['texture']='town-other-v1'
            current_rows,_=operations_history_app.read_operations_current_page_receipts(current_session,current_page)
            self.assertEqual(current_rows[0][3],'제안 또는 접수 조회 불가')
            current_receipt['state']='unknown'
            current_rows,_=operations_history_app.read_operations_current_page_receipts(current_session,current_page)
            self.assertEqual(current_rows[0][3],'제안 또는 접수 조회 불가')

    def test_conversation_proposal_rechecks_current_building_before_save(self):
        import json
        from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_building_proposal
        from tools.review.ui.gradio import hermes_agent_app
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_draft={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1},'properties':{'anchorX':0.6,'anchorY':1}}
        current_answer='HERMES_BUILDING_PROPOSAL\n'+json.dumps(current_draft)+'\nEND_HERMES_BUILDING_PROPOSAL'
        self.assertEqual(parse_hermes_building_proposal(current_answer),current_draft)
        current_catalog={'generation':3,'assets':[{'texture':'town-test-v1','properties':current_draft['expected'],'maps':[{'map':'test-city'}]}]}
        def current_gateway(service,command,payload):
            if command=='hermes-building-receipt':return {'state':'not_found'}
            if command=='hermes-building-proposal':return {'job_id':current_job,'proposal':current_draft}
            if command=='hermes-building-preview':
                with patch.object(building_operations,'call_field_map_editor',return_value=current_catalog):return building_operations.preview_hermes_building_anchor(payload['draft'])
            raise AssertionError(command)
        with patch.object(hermes_agent_app,'find_conversation_session_job'),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            current_card,current_preview,_,_=hermes_agent_app.prepare_conversation_edit_review(current_session,current_job,'building')
            self.assertTrue(current_card['ready'])
            self.assertIn('test-city',current_preview)
            self.assertIn('앵커 X: 0.5 → 0.6',current_preview)
            self.assertIn('건물: town-test-v1',current_preview)
            current_catalog['generation']=4
            with self.assertRaises(ValueError):hermes_agent_app.prepare_conversation_edit_review(current_session,current_job,'building')
        current_draft['properties']['anchorY']=float('nan')
        with self.assertRaises(ValueError):parse_hermes_building_proposal('HERMES_BUILDING_PROPOSAL\n'+json.dumps(current_draft)+'\nEND_HERMES_BUILDING_PROPOSAL')

    def test_saved_building_status_describes_historical_ledger_state(current_test_case):
        from tools.review.ui.gradio.hermes_agent_app import format_building_anchor_saved_status
        current_message=format_building_anchor_saved_status({'generation':4,'ledger_status_at_save':'pending'})
        current_test_case.assertIn('저장 당시 원장 반영 대기',current_message)
        current_test_case.assertIn('DB 세대 4',current_message)
        current_test_case.assertIn('현재 원장 동기화',current_message)
        current_test_case.assertNotIn('반영 대기',format_building_anchor_saved_status({}))

    def test_review_save_duplicate_and_response_loss(self):
        current_draft_value={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1},'properties':{'anchorX':0.6,'anchorY':1}}
        current_catalog_value={'generation':3,'assets':[{'texture':'town-test-v1','properties':current_draft_value['expected'],'maps':[{'map':'test-city'}],'image':'/private'}]}
        with TemporaryDirectory() as current_directory_name, patch.object(building_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_directory_name))), patch.object(building_operations,'call_field_map_editor') as current_gateway_mock:
            current_gateway_mock.side_effect=lambda current_command_name,current_payload_value: current_catalog_value if current_command_name=='building-list' else {'saved':True,'generation':4,'snapshot':'pending'}
            current_preview_value=building_operations.preview_hermes_building_anchor(current_draft_value)
            self.assertEqual(current_preview_value['maps'],['test-city'])
            self.assertNotIn('/private',str(current_preview_value))
            current_saved_value=building_operations.save_hermes_building_anchor('building_123',current_draft_value,current_preview_value['review_sha256'])
            self.assertEqual(current_saved_value['state'],'completed')
            self.assertEqual(current_saved_value['texture'],'town-test-v1')
            self.assertEqual((current_saved_value['generation'],current_saved_value['ledger_status_at_save']),(4,'pending'))
            self.assertEqual(building_operations.read_hermes_building_receipt('building_123')['generation'],4)
            self.assertEqual(building_operations.read_hermes_building_receipt('building_123')['texture'],'town-test-v1')
            self.assertTrue(building_operations.save_hermes_building_anchor('building_123',current_draft_value,current_preview_value['review_sha256'])['duplicate'])
            self.assertEqual(sum(current_call.args[0]=='building-save' for current_call in current_gateway_mock.call_args_list),1)
            current_gateway_mock.side_effect=lambda current_command_name,current_payload_value: current_catalog_value if current_command_name=='building-list' else (_ for _ in ()).throw(OSError('lost'))
            with self.assertRaises(OSError):building_operations.save_hermes_building_anchor('building_456',current_draft_value,current_preview_value['review_sha256'])
            self.assertEqual(building_operations.read_hermes_building_receipt('building_456')['state'],'unknown')
            self.assertEqual(building_operations.save_hermes_building_anchor('building_456',current_draft_value,current_preview_value['review_sha256'])['state'],'unknown')

    def test_mismatched_building_response_remains_unknown(current_test_case):
        current_draft={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1},'properties':{'anchorX':0.6,'anchorY':1}}
        current_catalog={'generation':3,'assets':[{'texture':'town-test-v1','properties':current_draft['expected'],'maps':[]}]}
        with TemporaryDirectory() as current_directory,patch.object(building_operations,'HermesDelegationStore',return_value=HermesDelegationStore(Path(current_directory))),patch.object(building_operations,'call_field_map_editor') as current_editor:
            current_editor.side_effect=lambda current_command,current_payload:current_catalog if current_command=='building-list' else {'saved':True,'asset':'town-other-v1','generation':4,'snapshot':'pending'}
            current_review=building_operations.preview_hermes_building_anchor(current_draft)
            with current_test_case.assertRaisesRegex(ValueError,'결과 확인 필요'):
                building_operations.save_hermes_building_anchor('building_wrong_123',current_draft,current_review['review_sha256'])
            current_test_case.assertEqual(building_operations.read_hermes_building_receipt('building_wrong_123')['state'],'unknown')
            current_test_case.assertEqual(building_operations.save_hermes_building_anchor('building_wrong_123',current_draft,current_review['review_sha256'])['state'],'unknown')
            current_test_case.assertEqual(sum(item.args[0]=='building-save' for item in current_editor.call_args_list),1)

    def test_changed_receipt_after_building_save_is_not_overwritten(self):
        import json
        current_draft_value={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1},'properties':{'anchorX':0.6,'anchorY':1}}
        current_catalog_value={'generation':3,'assets':[{'texture':'town-test-v1','properties':current_draft_value['expected'],'maps':[]}]}
        with TemporaryDirectory() as current_directory_name:
            current_store_value=HermesDelegationStore(Path(current_directory_name))
            current_record_path=current_store_value.resolve_delegation_record_path('building_123')
            def current_editor_response(current_command_name,current_payload_value):
                if current_command_name=='building-list':return current_catalog_value
                current_receipt_value=json.loads(current_record_path.read_text())
                current_receipt_value['external_change']='preserve'
                current_record_path.write_text(json.dumps(current_receipt_value))
                return {'saved':True}
            with patch.object(building_operations,'HermesDelegationStore',return_value=current_store_value),patch.object(building_operations,'call_field_map_editor',side_effect=current_editor_response) as current_editor_mock:
                current_preview_value=building_operations.preview_hermes_building_anchor(current_draft_value)
                current_save_args=('building_123',current_draft_value,current_preview_value['review_sha256'])
                with self.assertRaisesRegex(ValueError,'접수 기록이 변경'):building_operations.save_hermes_building_anchor(*current_save_args)
                self.assertEqual(building_operations.save_hermes_building_anchor(*current_save_args)['state'],'unknown')
                self.assertEqual(sum(item.args[0]=='building-save' for item in current_editor_mock.call_args_list),1)
                self.assertEqual(json.loads(current_record_path.read_text())['external_change'],'preserve')

    def test_changed_state_or_non_anchor_change_is_rejected(self):
        current_draft_value={'texture':'town-test-v1','generation':3,'expected':{'anchorX':0.5,'anchorY':1,'displayWidthAdjustment':0,'displayHeightAdjustment':0},'properties':{'anchorX':0.6,'anchorY':1,'displayWidthAdjustment':0,'displayHeightAdjustment':0}}
        with patch.object(building_operations,'call_field_map_editor',return_value={'generation':4,'assets':[]}):
            with self.assertRaisesRegex(ValueError,'세대'):building_operations.preview_hermes_building_anchor(current_draft_value)
        current_draft_value['properties']['displayWidthAdjustment']=1
        with self.assertRaisesRegex(ValueError,'앵커'):building_operations.inspect_hermes_building_draft(current_draft_value)
