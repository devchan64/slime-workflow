import unittest
import gradio as gr
import tempfile
from unittest.mock import patch

from tools.review.ui.gradio import hermes_agent_app
from tools.review.ui.gradio.management_menu_app import load_manager_page_records
from tools.review.common.management_asgi import build_management_blocks
from pathlib import Path


class HermesGradioTests(unittest.TestCase):
    def test_management_page_composes_with_menu(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_source_path = Path(hermes_temporary_root) / 'manager.json'
            hermes_source_path.write_text('{"pages":[]}')
            hermes_page_records = load_manager_page_records(hermes_source_path)
            self.assertIn('hermes-agent', [hermes_page_record['id'] for hermes_page_record in hermes_page_records])
            self.assertEqual(next(current_page_record['label'] for current_page_record in hermes_page_records if current_page_record['id'] == 'hermes-agent'), '운영 대화')
            with patch.dict('os.environ', {'SLIME_MANAGEMENT_MENU_SOURCE': str(Path(hermes_temporary_root) / 'missing.json')}):
                hermes_interface_blocks, hermes_mount_options = build_management_blocks('hermes-agent', 8770, hermes_source_path)
            hermes_component_labels = [getattr(hermes_component_value, 'label', None) for hermes_component_value in hermes_interface_blocks.blocks.values()]
            self.assertIn('작업 지시', hermes_component_labels)
            self.assertIn('요청 입력', hermes_component_labels)
            self.assertIn('대화', hermes_component_labels)
            self.assertIn('검토용 변경 diff', hermes_component_labels)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_kimodo_review_uses_same_receipt_after_reopening(self, current_gateway_mock):
        current_session_identifier = 'a' * 32
        current_source_job_identifier = '2026-11-18_00-24-38-0f938e1b'
        current_generated_job_identifier = '2026-11-18_12-00-19-05056f95'
        current_proposal_record = {'prompt':'천천히 걷기', 'frames':90, 'steps':100, 'seed':42}
        current_receipt_state = {'state':'not_found'}
        def current_gateway_result(current_service_name, current_command_name, current_payload_value):
            if current_command_name == 'hermes-session-view':
                return {'messages':[{'job_id':current_source_job_identifier, 'job':{'status':{'status':'completed'}}}]}
            if current_command_name == 'hermes-kimodo-proposal':
                return {'proposal':current_proposal_record}
            if current_command_name == 'hermes-delegation-status':
                return current_receipt_state.copy()
            if current_command_name == 'hermes-delegation-job-status':
                return {'receipt':current_receipt_state.copy(), 'job':{'status':'completed'}}
            if current_command_name == 'hermes-delegate-kimodo':
                current_receipt_state.update(state='accepted',job_id=current_generated_job_identifier)
                return {'state':'accepted','job_id':current_generated_job_identifier}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect = current_gateway_result
        current_card_record,current_preview_text,current_status_text = hermes_agent_app.prepare_conversation_kimodo_review(current_session_identifier,current_source_job_identifier)
        self.assertTrue(current_card_record['ready'])
        self.assertIn('천천히 걷기',current_preview_text)
        current_completed_card,current_status_text = hermes_agent_app.submit_conversation_kimodo_review(current_card_record,current_session_identifier,current_source_job_identifier)
        self.assertFalse(current_completed_card['ready'])
        self.assertIn('완료',current_status_text)
        self.assertIn('품질 승인',current_status_text)
        current_reopened_card,_,current_reopened_status = hermes_agent_app.prepare_conversation_kimodo_review(current_session_identifier,current_source_job_identifier)
        self.assertEqual(current_card_record['review']['request_id'],current_reopened_card['review']['request_id'])
        self.assertFalse(current_reopened_card['ready'])
        self.assertIn(current_generated_job_identifier,current_reopened_status)
        self.assertEqual(sum(current_call.args[1] == 'hermes-delegate-kimodo' for current_call in current_gateway_mock.call_args_list),1)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_kimodo_refuses_unknown_and_wrong_session(self,current_gateway_mock):
        current_session_identifier = 'a' * 32
        current_source_job_identifier = '2026-11-18_00-24-38-0f938e1b'
        current_proposal_record = {'prompt':'천천히 걷기', 'frames':90, 'steps':100, 'seed':42}
        def current_gateway_result(current_service_name,current_command_name,current_payload_value):
            if current_command_name == 'hermes-session-view':
                return {'messages':[{'job_id':current_source_job_identifier,'job':{'status':{'status':'completed'}}}]}
            if current_command_name == 'hermes-kimodo-proposal':return {'proposal':current_proposal_record}
            if current_command_name == 'hermes-delegation-status':return {'state':'unknown'}
            if current_command_name == 'hermes-delegation-job-status':return {'receipt':{'state':'unknown'}}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect = current_gateway_result
        current_card_record,_,current_status_text = hermes_agent_app.prepare_conversation_kimodo_review(current_session_identifier,current_source_job_identifier)
        self.assertFalse(current_card_record['ready'])
        self.assertIn('확인 불가',current_status_text)
        with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_kimodo_review(current_card_record,current_session_identifier,current_source_job_identifier)
        with self.assertRaises(gr.Error):hermes_agent_app.read_conversation_kimodo_result(current_card_record,'b'*32,current_source_job_identifier)
        self.assertFalse(any(current_call.args[1]=='hermes-delegate-kimodo' for current_call in current_gateway_mock.call_args_list))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_translation_reopens_receipt_and_never_reexecutes(self,current_gateway_mock):
        current_session_identifier='a'*32
        current_source_job_identifier='2026-11-18_00-24-38-0f938e1b'
        current_generation_job_identifier='2026-11-18_12-00-19-05056f95'
        current_receipt_record={'state':'not_found'}
        current_proposal_record={'text':'안녕하세요','target_language':'English','glossary':[]}
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'messages':[{'job_id':current_source_job_identifier,'job':{'status':{'status':'completed'}}}]}
            if current_command_name=='hermes-translation-proposal':return {'proposal':current_proposal_record}
            if current_command_name=='hermes-translation-status':return {'receipt':current_receipt_record.copy(),'job':{'status':'completed','result':'Hello'}}
            if current_command_name=='hermes-delegate-translation':
                current_receipt_record.update(state='accepted',job_id=current_generation_job_identifier)
                return {'state':'accepted','job_id':current_generation_job_identifier}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_review_record={'request_id':'unused','request':{'text':'안녕하세요','target_language':'English','glossary':[]}}
        def current_review_response(current_text,current_language,current_glossary,current_request_identifier):
            return {**current_review_record,'request_id':current_request_identifier},'번역 검토','입력 검토',{}
        with patch.object(hermes_agent_app,'review_hermes_translation_request',side_effect=current_review_response):
            current_card_record,current_preview_text,_=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job_identifier,'translation')
            self.assertIn('안녕하세요',current_preview_text)
            self.assertTrue(current_card_record['ready'])
            current_result_card,current_status_text=hermes_agent_app.submit_conversation_service_review(current_card_record,current_session_identifier,current_source_job_identifier,'translation')
            self.assertFalse(current_result_card['ready'])
            self.assertIn('Hello',current_status_text)
            current_reopened_card,_,_=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job_identifier,'translation')
            self.assertFalse(current_reopened_card['ready'])
            self.assertEqual(current_card_record['review']['request_id'],current_reopened_card['review']['request_id'])
        self.assertEqual(sum(current_call.args[1]=='hermes-delegate-translation' for current_call in current_gateway_mock.call_args_list),1)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_service_unknown_receipt_and_changed_target_never_submit(self,current_gateway_mock):
        current_session_identifier='a'*32
        current_source_job_identifier='2026-11-18_00-24-38-0f938e1b'
        current_card_record={'session_id':current_session_identifier,'source_job_id':current_source_job_identifier,'kind':'flux','service':'flux-image','review':{'request_id':'chat_12345678','request':{}},'ready':True}
        with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_service_review(current_card_record,'b'*32,current_source_job_identifier,'flux')
        current_gateway_mock.return_value={'receipt':{'state':'unknown'}}
        current_state_value,current_status_text=hermes_agent_app.read_conversation_service_status(current_card_record,current_session_identifier,current_source_job_identifier,'flux')
        self.assertEqual(current_state_value,'unknown')
        self.assertIn('자동으로 다시 접수하지',current_status_text)
        self.assertFalse(any(current_call.args[1].startswith('hermes-delegate') for current_call in current_gateway_mock.call_args_list))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_edit_confirmation_rejects_replaced_card(self,current_gateway_mock):
        current_card_record={'session_id':'a'*32,'source_job_id':'job-a','kind':'effect','ready':True,'review':{'draft':{'id':'old'}}}
        current_changed_card={**current_card_record,'review':{'draft':{'id':'new'}}}
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_confirmed_conversation_edit(current_card_record,current_changed_card,'a'*32,'job-a','effect')
        current_gateway_mock.assert_not_called()

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_edit_unknown_receipt_never_previews_or_saves(self,current_gateway_mock):
        current_session_identifier='a'*32
        current_source_job_identifier='2026-11-18_00-24-38-0f938e1b'
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'messages':[{'job_id':current_source_job_identifier,'job':{'status':{'status':'completed'}}}]}
            if current_command_name=='hermes-effect-receipt':return {'state':'unknown'}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_card_record,_,_,current_status_text=hermes_agent_app.prepare_conversation_edit_review(current_session_identifier,current_source_job_identifier,'effect')
        self.assertFalse(current_card_record['ready'])
        self.assertIn('자동 재저장하지',current_status_text)
        with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_edit_review(current_card_record,current_session_identifier,current_source_job_identifier,'effect')
        self.assertFalse(any(current_call.args[1].endswith(('-save','-preview')) for current_call in current_gateway_mock.call_args_list))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_image_and_audio_reuse_service_contracts(self,current_gateway_mock):
        current_session_identifier='a'*32
        current_source_job_identifier='2026-11-18_00-24-38-0f938e1b'
        current_proposals={'flux':{'prompt':'작은 마을','width':512,'height':512,'seed':42},'audio':{'service':'sfx-dasheng-audiogen','request':{'action':'generate','prompt':'바람 소리','seed':42,'loop_request':False}}}
        current_calls=[]
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            current_calls.append(current_command_name)
            if current_command_name=='hermes-session-view':return {'messages':[{'job_id':current_source_job_identifier,'job':{'status':{'status':'completed'}}}]}
            if current_command_name in ('hermes-flux-proposal','hermes-audio-proposal'):return {'proposal':current_proposals[current_command_name.split('-')[1]]}
            if current_command_name in ('hermes-flux-delegation-status','hermes-audio-status'):return {'receipt':{'state':'not_found'}}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        for current_kind_value in ('flux','audio'):
            with self.subTest(kind=current_kind_value):
                current_card_record,current_preview_text,current_status_text=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job_identifier,current_kind_value)
                self.assertTrue(current_card_record['ready'])
                self.assertIn('아직 접수하지',current_status_text)
                self.assertEqual(current_card_record['review']['request']['seed'],42)
        self.assertFalse(any(current_command.startswith('hermes-delegate') for current_command in current_calls))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_effect_save_rechecks_draft_and_restores_receipt(self,current_gateway_mock):
        import json
        current_session_identifier='a'*32
        current_source_job_identifier='2026-11-18_00-24-38-0f938e1b'
        current_draft_record={'id':'effect-a','revision':'a'*64,'target':[0,0,4,4],'alpha':1,'frames':[[0,0,4,4]]}
        current_receipt_record={'state':'not_found'}
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'messages':[{'job_id':current_source_job_identifier,'job':{'status':{'status':'completed'}}}]}
            if current_command_name=='hermes-effect-receipt':return current_receipt_record.copy()
            if current_command_name=='hermes-effect-save':
                current_receipt_record.update(state='completed',saved=True)
                return {'state':'completed','saved':True}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        def current_load_response(current_job_identifier):return None,{},json.dumps(current_draft_record),None,None,None,None
        def current_preview_response(current_draft_text,current_request_identifier):
            return {'request_id':current_request_identifier,'draft':json.loads(current_draft_text),'token':'test-token'},{'before':{'alpha':0.5},'after':{'alpha':1},'token':'test-token'},{}
        with patch.object(hermes_agent_app,'load_hermes_effect_edit_proposal',side_effect=current_load_response),patch.object(hermes_agent_app,'review_hermes_effect_edit_draft',side_effect=current_preview_response):
            current_card_record,current_preview_text,_,_=hermes_agent_app.prepare_conversation_edit_review(current_session_identifier,current_source_job_identifier,'effect')
            self.assertIn('before',current_preview_text)
            current_changed_card={**current_card_record,'review':{**current_card_record['review'],'draft':{**current_draft_record,'alpha':0.9}}}
            with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_edit_review(current_changed_card,current_session_identifier,current_source_job_identifier,'effect')
            current_completed_card,current_status_text=hermes_agent_app.submit_confirmed_conversation_edit(current_card_record,current_card_record,current_session_identifier,current_source_job_identifier,'effect')
            self.assertFalse(current_completed_card['ready'])
            self.assertIn('저장 완료',current_status_text)
            current_reopened_card,_,_,_=hermes_agent_app.prepare_conversation_edit_review(current_session_identifier,current_source_job_identifier,'effect')
            self.assertFalse(current_reopened_card['ready'])
        self.assertEqual(sum(current_call.args[1]=='hermes-effect-save' for current_call in current_gateway_mock.call_args_list),1)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_video_requires_attachments_for_reference_modes(self,current_gateway_mock):
        current_session_identifier='a'*32
        current_source_job_identifier='2026-11-18_00-24-38-0f938e1b'
        current_proposal_record={'service':'wan22-vace','mode':'text','prompt':'햇살이 비치는 마을'}
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'messages':[{'job_id':current_source_job_identifier,'job':{'status':{'status':'completed'}}}]}
            if current_command_name=='hermes-video-proposal':return {'proposal':current_proposal_record.copy()}
            if current_command_name=='hermes-video-status':return {'receipt':{'state':'not_found'}}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_card_record,current_preview_text,current_status_text=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job_identifier,'video')
        self.assertTrue(current_card_record['ready'])
        self.assertEqual(current_card_record['review']['request']['mode'],'text')
        self.assertIn('기본값 포함',current_preview_text)
        current_proposal_record['mode']='reference'
        with self.assertRaises(gr.Error):hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job_identifier,'video')
        self.assertFalse(any(current_call.args[1]=='hermes-delegate-video' for current_call in current_gateway_mock.call_args_list))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_sprite_proposal_rejects_stale_snapshot(self,current_gateway_mock):
        import json
        current_proposal_record={'path':'assets/characters/default/animations/test/sheet.png','snapshot':'a'*64,'columns':4,'anchors':[{'frame_id':'idle.0','x':1,'y':2}]}
        current_detail_record={'path':current_proposal_record['path'],'snapshot':'a'*64,'metadata_sha256':'b'*64}
        current_gateway_mock.side_effect=[{'proposal':current_proposal_record},current_detail_record]
        current_result_value=hermes_agent_app.load_hermes_sprite_anchor_proposal('job-1')
        self.assertEqual(json.loads(current_result_value[1]),current_proposal_record)
        self.assertIsNone(current_result_value[3])
        current_gateway_mock.side_effect=[{'proposal':current_proposal_record},{**current_detail_record,'snapshot':'c'*64}]
        with self.assertRaises(gr.Error):hermes_agent_app.load_hermes_sprite_anchor_proposal('job-1')
        self.assertEqual([current_call.args[1] for current_call in current_gateway_mock.call_args_list],['hermes-sprite-proposal','hermes-sprite-detail']*2)

    def test_sprite_proposal_display_preserves_suffix(self):
        import json
        current_proposal_record={'path':'assets/characters/default/animations/test/sheet.png','snapshot':'a'*64,'columns':4,'anchors':[{'frame_id':'idle.0','x':1,'y':2}]}
        current_answer_text='설명\nHERMES_SPRITE_PROPOSAL\n'+json.dumps(current_proposal_record)+'\nEND_HERMES_SPRITE_PROPOSAL\n재생을 검토하세요.'
        current_display_text=hermes_agent_app.format_hermes_conversation_answer(current_answer_text)
        self.assertIn('스프라이트 앵커 제안',current_display_text)
        self.assertIn('재생을 검토하세요.',current_display_text)
        self.assertNotIn('HERMES_SPRITE_PROPOSAL',current_display_text)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_sprite_playback_rejects_changed_draft_and_invalid_gif(self,current_gateway_mock):
        import base64,hashlib,json
        current_draft_record={'path':'assets/characters/default/animations/test/a.png','snapshot':'a'*64,'columns':4,'anchors':[{'frame_id':'idle.0','x':1,'y':2}]}
        current_review_record={'request_id':'sprite_request_123','draft':current_draft_record,'token':'b'*64,'review_sha256':'c'*64}
        current_draft_text=json.dumps(current_draft_record)
        with self.assertRaises(gr.Error):hermes_agent_app.render_hermes_sprite_anchor_playback(current_review_record,json.dumps({**current_draft_record,'columns':2}),'sprite_request_123',8)
        current_gateway_mock.assert_not_called()
        current_bytes_value=b'GIF89a-test'
        current_gateway_mock.return_value={'gif':base64.b64encode(current_bytes_value).decode(),'sha256':hashlib.sha256(current_bytes_value).hexdigest(),'frame_count':1,'fps':8,'note':'균일 FPS'}
        current_html_value,current_status_text=hermes_agent_app.render_hermes_sprite_anchor_playback(current_review_record,current_draft_text,'sprite_request_123',8)
        self.assertIn('data:image/gif;base64,',current_html_value)
        self.assertIn('균일',current_status_text)
        current_gateway_mock.return_value['sha256']='0'*64
        with self.assertRaises(gr.Error):hermes_agent_app.render_hermes_sprite_anchor_playback(current_review_record,current_draft_text,'sprite_request_123',8)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_sprite_review_checks_draft_and_lost_response(self,current_gateway_mock):
        import json
        current_draft_record={'path':'assets/characters/default/animations/test/a.png','snapshot':'a'*64,'columns':4,'anchors':[{'frame_id':'idle.0','x':1,'y':2}]}
        current_draft_text=json.dumps(current_draft_record)
        import base64,io
        from PIL import Image
        current_image_buffer=io.BytesIO();Image.new('RGBA',(2,2)).save(current_image_buffer,format='PNG')
        current_gateway_mock.return_value={'token':'b'*64,'review_sha256':'c'*64,'frame_layout':[],'changed_anchors':[],'preview_image':base64.b64encode(current_image_buffer.getvalue()).decode()}
        current_review_record,current_preview_record,current_preview_image,current_clip_update,current_visible_update=hermes_agent_app.review_hermes_sprite_anchor_draft(current_draft_text,'sprite_request_123')
        self.assertTrue(current_visible_update['visible'])
        self.assertEqual(current_preview_image.size,(2,2))
        self.assertNotIn('preview_image',current_preview_record)
        current_gateway_mock.reset_mock()
        with self.assertRaises(gr.Error):hermes_agent_app.save_hermes_sprite_anchor_draft(current_review_record,json.dumps({**current_draft_record,'columns':2}),'sprite_request_123')
        with self.assertRaises(gr.Error):hermes_agent_app.save_hermes_sprite_anchor_draft(current_review_record,current_draft_text,'sprite_request_456')
        current_gateway_mock.assert_not_called()
        current_gateway_mock.return_value={'state':'unknown'}
        self.assertIn('자동 재접수하지',hermes_agent_app.save_hermes_sprite_anchor_draft(current_review_record,current_draft_text,'sprite_request_123')[2])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_effect_proposal_uses_fresh_revision_and_rejects_stale(self,current_gateway_mock):
        import json
        current_proposal_record={'id':'firefly-v1','revision':'a'*64,'target':[0,0,1,1],'alpha':0.7,'frames':[[0,0,1,1]]}
        current_detail_record={'id':'firefly-v1','name':'반딧불','revision':'a'*64,'alignment':{'alpha':0.5},'frames':1}
        current_gateway_mock.side_effect=[{'proposal':current_proposal_record},current_detail_record]
        current_result_value=hermes_agent_app.load_hermes_effect_edit_proposal('job-1')
        self.assertEqual(json.loads(current_result_value[2]),current_proposal_record)
        self.assertIsNone(current_result_value[4])
        current_gateway_mock.side_effect=[{'proposal':current_proposal_record},{**current_detail_record,'revision':'b'*64}]
        with self.assertRaises(gr.Error):hermes_agent_app.load_hermes_effect_edit_proposal('job-1')
        self.assertEqual([current_call.args[1] for current_call in current_gateway_mock.call_args_list],['hermes-effect-proposal','hermes-effect-detail']*2)

    def test_effect_proposal_display_preserves_suffix(self):
        import json
        current_proposal_record={'id':'firefly-v1','revision':'a'*64,'target':[0,0,1,1],'alpha':0.7,'frames':[[0,0,1,1]]}
        current_answer_text='설명\nHERMES_EFFECT_PROPOSAL\n'+json.dumps(current_proposal_record)+'\nEND_HERMES_EFFECT_PROPOSAL\n이미지 검수하세요.'
        current_display_text=hermes_agent_app.format_hermes_conversation_answer(current_answer_text)
        self.assertIn('이펙트 좌표 제안',current_display_text)
        self.assertIn('이미지 검수하세요.',current_display_text)
        self.assertNotIn('HERMES_EFFECT_PROPOSAL',current_display_text)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_effect_review_requires_unchanged_draft_and_id(self,current_gateway_mock):
        import json
        current_draft_record={'id':'firefly-v1','revision':'a'*64,'target':[0,0,1,1],'alpha':0.7,'frames':[[0,0,1,1]]}
        current_draft_text=json.dumps(current_draft_record)
        current_gateway_mock.return_value={'token':'b'*64,'before':{},'after':{},'note':'공용'}
        current_review_record,current_comparison_value,current_visible_update=hermes_agent_app.review_hermes_effect_edit_draft(current_draft_text,'effect_request_123')
        self.assertTrue(current_visible_update['visible'])
        current_gateway_mock.reset_mock()
        with self.assertRaises(gr.Error):hermes_agent_app.save_hermes_effect_edit_draft(current_review_record,json.dumps({**current_draft_record,'alpha':0.9}),'effect_request_123')
        with self.assertRaises(gr.Error):hermes_agent_app.save_hermes_effect_edit_draft(current_review_record,current_draft_text,'effect_request_456')
        current_gateway_mock.assert_not_called()
        current_gateway_mock.return_value={'state':'unknown'}
        self.assertIn('자동 재접수하지',hermes_agent_app.save_hermes_effect_edit_draft(current_review_record,current_draft_text,'effect_request_123')[2])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_billboard_proposal_reload_rejects_changed_original(self,current_gateway_mock):
        import json
        current_proposal_record={'texture':'tree-v1','expected':{'displayHeight':520},'values':{'displayHeight':500}}
        current_gateway_mock.side_effect=[{'proposal':current_proposal_record},{'texture':'tree-v1','revision':'new','properties':{'displayHeight':520}}]
        current_result_value=hermes_agent_app.load_hermes_billboard_edit_proposal('job-1')
        self.assertEqual(json.loads(current_result_value[2]),{'revision':'new','changes':[{'texture':'tree-v1','values':{'displayHeight':500}}]})
        self.assertIsNone(current_result_value[4])
        current_gateway_mock.side_effect=[{'proposal':current_proposal_record},{'texture':'tree-v1','revision':'new','properties':{'displayHeight':521}}]
        with self.assertRaises(gr.Error):
            hermes_agent_app.load_hermes_billboard_edit_proposal('job-1')
        self.assertEqual([current_call.args[1] for current_call in current_gateway_mock.call_args_list],['hermes-billboard-proposal','hermes-billboard-load']*2)

    def test_billboard_proposal_display_preserves_suffix(self):
        import json
        current_proposal_record={'texture':'tree-v1','expected':{'displayHeight':520},'values':{'displayHeight':500}}
        current_answer_text='설명\nHERMES_BILLBOARD_PROPOSAL\n'+json.dumps(current_proposal_record)+'\nEND_HERMES_BILLBOARD_PROPOSAL\n검토하세요.'
        current_display_text=hermes_agent_app.format_hermes_conversation_answer(current_answer_text)
        self.assertIn('빌보드 속성 제안',current_display_text)
        self.assertIn('검토하세요.',current_display_text)
        self.assertNotIn('HERMES_BILLBOARD_PROPOSAL',current_display_text)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_billboard_review_requires_unchanged_draft_and_request(self,current_gateway_mock):
        import json
        current_draft_record={'revision':'abc','changes':[{'texture':'grass-v1','values':{'displayHeight':130}}]}
        current_draft_text=json.dumps(current_draft_record)
        current_gateway_mock.return_value={'token':'a'*64,'review_sha256':'b'*64,'changes':[{'texture':'grass-v1','before':{},'after':{}}],'maps':[],'map_warnings':[],'note':'검수'}
        current_review_record,current_preview_record,current_summary_text,current_visible_update=hermes_agent_app.review_hermes_billboard_edit_draft(current_draft_text,'request_123')
        self.assertTrue(current_visible_update['visible'])
        self.assertIn('경고',current_summary_text)
        self.assertEqual(current_preview_record['review_sha256'],'b'*64)
        current_gateway_mock.reset_mock()
        for current_changed_text,current_changed_id in ((json.dumps({**current_draft_record,'revision':'other'}),'request_123'),(current_draft_text,'request_456')):
            with self.subTest(request=current_changed_id),self.assertRaises(gr.Error):
                hermes_agent_app.save_hermes_billboard_edit_draft(current_review_record,current_changed_text,current_changed_id)
        current_gateway_mock.assert_not_called()
        current_gateway_mock.return_value={'state':'unknown'}
        current_result_value=hermes_agent_app.save_hermes_billboard_edit_draft(current_review_record,current_draft_text,'request_123')
        self.assertIn('자동 재접수하지',current_result_value[2])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_billboard_load_makes_empty_edit_values(self,current_gateway_mock):
        import json
        current_gateway_mock.return_value={'texture':'grass-v1','revision':'abc','properties':{'displayHeight':128}}
        current_original_record,current_draft_text,current_review_state,current_visible_update,current_status_text=hermes_agent_app.load_hermes_billboard_edit_draft('grass-v1')
        self.assertEqual(current_original_record,{'displayHeight':128})
        self.assertEqual(json.loads(current_draft_text)['changes'][0]['values'],{})
        self.assertIsNone(current_review_state)
        self.assertFalse(current_visible_update['visible'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_video_proposal_clears_attachments_and_preserves_mode(self,current_gateway_mock):
        import json
        current_gateway_mock.return_value={'proposal':{'service':'wan22-vace','mode':'video_edit','prompt':'change the background'}}
        current_result_value=hermes_agent_app.load_hermes_video_proposal('job-1')
        self.assertEqual(current_result_value[0],'wan22-vace')
        current_settings_value=json.loads(current_result_value[1])
        self.assertEqual(current_settings_value['mode'],'video_edit')
        self.assertEqual(current_settings_value['prompt'],'change the background')
        self.assertEqual(current_result_value[2:7],(None,None,None,None,None))
        self.assertIsNone(current_result_value[8])
        self.assertFalse(current_result_value[11]['interactive'])
        self.assertIn('편집 MP4·마스크 MP4',current_result_value[10])
        current_gateway_mock.assert_called_once_with('hermes-agent','hermes-video-proposal',{'id':'job-1'})

    def test_video_proposal_display_preserves_suffix(self):
        import json
        current_proposal_value={'service':'wan22-vace','mode':'text','prompt':'a landscape'}
        current_answer_value='설명\nHERMES_VIDEO_PROPOSAL\n'+json.dumps(current_proposal_value)+'\nEND_HERMES_VIDEO_PROPOSAL\n\n첨부를 확인하세요.'
        current_display_value=hermes_agent_app.format_hermes_conversation_answer(current_answer_value)
        self.assertIn('동작·영상 제안',current_display_value)
        self.assertIn('첨부를 확인하세요.',current_display_value)
        self.assertNotIn('HERMES_VIDEO_PROPOSAL',current_display_value)

    def test_video_vace_text_template_and_attachment_conflict(self):
        import json
        current_settings_value=json.loads(hermes_agent_app.default_hermes_video_settings('wan22-vace'))
        current_settings_value.update(mode='text',prompt='a calm landscape')
        current_settings_text=json.dumps(current_settings_value)
        current_result_value=hermes_agent_app.review_hermes_video_request('wan22-vace',current_settings_text,[],None,None,None,None,'video_request_123')
        self.assertTrue(current_result_value[3]['interactive'])
        self.assertEqual(current_result_value[0]['request']['mode'],'text')
        with self.assertRaises(ValueError):
            hermes_agent_app.build_hermes_video_request('wan22-vace',json.dumps({**current_settings_value,'edit_video':'inline'}),[],None,None,b'file',None,'video_request_123')

    def test_video_review_rejects_inline_binary_in_settings(self):
        import json
        current_settings_value=json.loads(hermes_agent_app.default_hermes_video_settings('wan22-vace'))
        current_settings_value.update(mode='text',prompt='landscape')
        for current_field_name,current_field_value in (('images',['aW1hZ2U=']),('driving_video','dmlkZW8='),('pose_video','dmlkZW8='),('edit_video','dmlkZW8='),('edit_mask','bWFzaw==')):
            with self.subTest(field=current_field_name):
                current_invalid_settings=json.dumps({**current_settings_value,current_field_name:current_field_value})
                current_review_value,current_summary_value,current_status_value,current_button_value=hermes_agent_app.review_hermes_video_request('wan22-vace',current_invalid_settings,[],None,None,None,None,'video_request_123')
                self.assertIsNone(current_review_value)
                self.assertFalse(current_button_value['interactive'])
                self.assertIn('파일 첨부',current_status_value)

    @patch('tools.review.domains.hermes_agent.video_operations.validate_hermes_video_request')
    def test_video_review_identifies_attachment_roles_sizes_and_full_hashes(self,current_validator_mock):
        import hashlib
        current_file_values=([b'first',b'second'],b'driving',b'pose',b'edit',b'mask')
        current_review_value,current_summary_value,_,current_button_value=hermes_agent_app.review_hermes_video_request('wan22-vace','{"action":"generate","images":[]}',*current_file_values,'video_request_123')
        self.assertTrue(current_button_value['interactive'])
        for current_label_value,current_file_value in (('참조 이미지 1',b'first'),('참조 이미지 2',b'second'),('동작 RGB 영상',b'driving'),('포즈 영상',b'pose'),('편집·조건 영상',b'edit'),('편집 마스크',b'mask')):
            self.assertIn(current_label_value+' · '+str(len(current_file_value))+'바이트 · SHA-256 '+hashlib.sha256(current_file_value).hexdigest(),current_summary_value)
        self.assertEqual(current_summary_value.count('\n'),7)
        self.assertEqual(len(current_review_value['request']['images']),2)
        current_validator_mock.assert_called_once()

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_video_review_validates_dwpose_and_detects_changed_attachment(self,current_gateway_mock):
        import io
        from PIL import Image
        current_image_buffer=io.BytesIO()
        Image.new('RGB',(832,480),'white').save(current_image_buffer,format='PNG')
        current_image_bytes=current_image_buffer.getvalue()
        current_settings_value=hermes_agent_app.default_hermes_video_settings('dwpose')
        current_review_value,current_summary_value,current_status_value,current_button_value=hermes_agent_app.review_hermes_video_request('dwpose',current_settings_value,[current_image_bytes],None,None,None,None,'video_request_123')
        self.assertTrue(current_button_value['interactive'])
        self.assertIn('첨부 1개',current_summary_value)
        self.assertFalse(hermes_agent_app.review_hermes_video_request('dwpose',current_settings_value,[],None,None,None,None,'video_request_123')[3]['interactive'])
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_video_reviewed(current_review_value,'dwpose',current_settings_value,[current_image_bytes],None,None,None,None,'video_request_456')
        current_gateway_mock.assert_not_called()
        with self.assertRaises(ValueError):
            hermes_agent_app.build_hermes_video_request('dwpose',current_settings_value,[b'x'*(24*1024*1024+1)],None,None,None,None,'video_request_123')

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_audio_proposal_load_preserves_request_and_does_not_submit(self,current_gateway_mock):
        current_gateway_mock.return_value={'proposal':{'service':'music-heartmula','request':{'action':'generate','prompt':'piano','lyrics':'[Verse]\nHello','duration_seconds':30,'seed':7,'loop_request':False}}}
        current_result_value=hermes_agent_app.load_hermes_audio_proposal('job-1')
        self.assertEqual(current_result_value[:6],('music-heartmula','piano','[Verse]\nHello',30,False,7))
        self.assertIsNone(current_result_value[7])
        self.assertFalse(current_result_value[10]['interactive'])
        current_gateway_mock.assert_called_once_with('hermes-agent','hermes-audio-proposal',{'id':'job-1'})

    def test_audio_proposal_display_preserves_suffix(self):
        import json
        current_proposal_value={'service':'sfx-dasheng-audiogen','request':{'action':'generate','prompt':'water splash','seed':42,'loop_request':False}}
        current_answer_value='설명\nHERMES_AUDIO_PROPOSAL\n'+json.dumps(current_proposal_value)+'\nEND_HERMES_AUDIO_PROPOSAL\n\n사용자가 확인하세요.'
        current_display_value=hermes_agent_app.format_hermes_conversation_answer(current_answer_value)
        self.assertIn('음악·효과음 제안',current_display_value)
        self.assertIn('사용자가 확인하세요.',current_display_value)
        self.assertNotIn('HERMES_AUDIO_PROPOSAL',current_display_value)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_audio_review_respects_service_constraints_and_changed_input(self,current_gateway_mock):
        current_review_value,current_summary_value,current_status_value,current_button_value=hermes_agent_app.review_hermes_audio_request('music-heartmula','piano','[Verse]\nHello',30,False,7,'audio_request_123')
        self.assertTrue(current_button_value['interactive'])
        self.assertIn('최대 출력 상한',current_summary_value)
        self.assertFalse(hermes_agent_app.review_hermes_audio_request('music-heartmula','piano','[Verse]\nHello',30,True,7,'audio_request_123')[3]['interactive'])
        self.assertFalse(hermes_agent_app.review_hermes_audio_request('sfx-dasheng-audiogen','splash','가사',30,False,7,'audio_request_123')[3]['interactive'])
        current_effect_value=hermes_agent_app.review_hermes_audio_request('sfx-dasheng-audiogen','splash','',30,False,7,'audio_request_456')
        self.assertTrue(current_effect_value[3]['interactive'])
        self.assertNotIn('duration_seconds',current_effect_value[0]['request'])
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_audio_reviewed(current_review_value,'music-heartmula','other','[Verse]\nHello',30,False,7,'audio_request_123')
        current_gateway_mock.assert_not_called()

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_expression_review_requires_face_and_detects_changes(self,current_gateway_mock):
        from PIL import Image
        current_face_value=Image.new('RGB',(64,64),'white')
        self.assertFalse(hermes_agent_app.review_hermes_flux_expression_request(None,'joy','',768,512,42,'expression_request_123')[3]['interactive'])
        current_review_value,current_summary_value,current_status_value,current_button_value=hermes_agent_app.review_hermes_flux_expression_request(current_face_value,'joy','눈썹을 올린다',768,512,42,'expression_request_123')
        self.assertTrue(current_button_value['interactive'])
        self.assertIn('얼굴 참조: 1장',current_summary_value)
        import base64, hashlib
        current_reference_bytes=base64.b64decode(current_review_value['request']['images'][0])
        self.assertIn(f'{len(current_reference_bytes)}바이트 · PNG SHA-256: {hashlib.sha256(current_reference_bytes).hexdigest()}',current_summary_value)
        self.assertEqual(current_review_value['request']['translation_source_ko'],'눈썹을 올린다')
        current_inputs_value=(current_review_value,current_face_value,'joy','눈썹을 올린다',768,512,42,'expression_request_123')
        self.assertTrue(hermes_agent_app.match_hermes_flux_expression_confirmation(current_inputs_value,current_inputs_value))
        current_changed_face=Image.new('RGB',(64,64),'black')
        self.assertFalse(hermes_agent_app.match_hermes_flux_expression_confirmation(current_inputs_value,(current_review_value,current_changed_face,'joy','눈썹을 올린다',768,512,42,'expression_request_123')))
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_flux_expression_reviewed(current_review_value,current_face_value,'joy','다른 지시',768,512,42,'expression_request_123')
        current_gateway_mock.assert_not_called()

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_flux_profile_reference_constraints_and_changed_confirmation(self,current_gateway_mock):
        from PIL import Image
        current_image_value=Image.new('RGB',(64,64),'white')
        current_bad_value=hermes_agent_app.review_hermes_flux_profile_request('flux-building','small house',768,768,42,None,None,'profile_request_123')
        self.assertFalse(current_bad_value[3]['interactive'])
        self.assertFalse(hermes_agent_app.review_hermes_flux_profile_request('flux-building','small house',768,768,42,None,current_image_value,'profile_request_123')[3]['interactive'])
        self.assertEqual(hermes_agent_app.update_hermes_flux_profile_defaults('flux-seamless'),(512,512))
        current_review_value,current_summary_value,current_status_value,current_button_value=hermes_agent_app.review_hermes_flux_profile_request('flux-building','small house',768,768,42,current_image_value,None,'profile_request_123')
        self.assertTrue(current_button_value['interactive'])
        self.assertIn('참조: 1장',current_summary_value)
        import base64, hashlib
        current_reference_bytes=base64.b64decode(current_review_value['request']['images'][0])
        self.assertIn(f'{len(current_reference_bytes)}바이트 · PNG SHA-256: {hashlib.sha256(current_reference_bytes).hexdigest()}',current_summary_value)
        current_original_inputs=(current_review_value,'flux-building','small house',768,768,42,current_image_value,None,'profile_request_123')
        self.assertTrue(hermes_agent_app.match_hermes_flux_profile_confirmation(current_original_inputs,current_original_inputs))
        current_changed_image=Image.new('RGB',(64,64),'black')
        self.assertFalse(hermes_agent_app.match_hermes_flux_profile_confirmation(current_original_inputs,(current_review_value,'flux-building','small house',768,768,42,current_changed_image,None,'profile_request_123')))
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_flux_profile_reviewed(current_review_value,'flux-building','different',768,768,42,current_image_value,None,'profile_request_123')
        current_gateway_mock.assert_not_called()
        self.assertFalse(hermes_agent_app.review_hermes_flux_profile_request('flux-seamless','grass',768,768,42,None,None,'profile_request_456')[3]['interactive'])
        self.assertTrue(hermes_agent_app.review_hermes_flux_profile_request('flux-seamless','grass',512,512,42,None,None,'profile_request_456')[3]['interactive'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_writer_apply_requires_full_review_and_unchanged_confirmation(self,current_gateway_mock):
        current_gateway_mock.return_value={'receipt':{'state':'accepted','job_id':'20261118-120000-12345678'},'job':{'stage':'review','proposal_hash':'a'*64,'truncated':False,'changes':[{'path':'town.md','diff':'-a\n+b'}]}}
        with self.assertRaises(gr.Error):
            hermes_agent_app.review_hermes_writer_apply('writer_request_123','apply_request_123',False)
        current_gateway_mock.assert_not_called()
        current_review_value,current_diff_value,current_group_value,current_summary_value=hermes_agent_app.review_hermes_writer_apply('writer_request_123','apply_request_123',True)
        self.assertTrue(current_group_value['visible'])
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_writer_apply(current_review_value,'writer_request_123','different_123',True)
        self.assertEqual(current_gateway_mock.call_count,1)
        current_gateway_mock.return_value={'state':'completed'}
        self.assertIn('원본에 적용',hermes_agent_app.submit_hermes_writer_apply(current_review_value,'writer_request_123','apply_request_123',True)[2])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_writer_review_rejects_changed_input(self,current_gateway_mock):
        current_review_value,current_summary_value,current_status_value,current_button_value=hermes_agent_app.review_hermes_writer_request('write','마을 설명','writer_request_123')
        self.assertTrue(current_button_value['interactive'])
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_writer_reviewed(current_review_value,'write','다른 지시','writer_request_123')
        current_gateway_mock.assert_not_called()
        current_gateway_mock.return_value={'state':'accepted','job_id':'20261118-120000-12345678'}
        self.assertEqual(hermes_agent_app.submit_hermes_writer_reviewed(current_review_value,'write','마을 설명','writer_request_123')[0],'20261118-120000-12345678')

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_translation_proposal_load_does_not_submit(self,current_gateway_mock):
        current_gateway_mock.return_value={'proposal':{'text':'푸른 나무','target_language':'en','glossary':[{'source':'나무','target':'tree'}]}}
        current_result_value=hermes_agent_app.load_hermes_translation_proposal('job-1')
        self.assertEqual(current_result_value[:3],('푸른 나무','en','나무 => tree'))
        self.assertIsNone(current_result_value[4])
        self.assertFalse(current_result_value[7]['interactive'])
        current_gateway_mock.assert_called_once_with('hermes-agent','hermes-translation-proposal',{'id':'job-1'})

    @patch('tools.review.domains.translation.service.load_approved_translation_terms',return_value=[])
    def test_translation_proposal_display_preserves_suffix(self,current_terms_mock):
        import json
        current_proposal_value={'text':'나무','target_language':'en','glossary':[]}
        current_answer_value='설명\nHERMES_TRANSLATION_PROPOSAL\n'+json.dumps(current_proposal_value)+'\nEND_HERMES_TRANSLATION_PROPOSAL\n\n사용자가 확인하세요.'
        current_display_value=hermes_agent_app.format_hermes_conversation_answer(current_answer_value)
        self.assertIn('번역 위임 제안',current_display_value)
        self.assertIn('사용자가 확인하세요.',current_display_value)
        self.assertNotIn('HERMES_TRANSLATION_PROPOSAL',current_display_value)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    @patch('tools.review.domains.translation.service.validate_translation_submission')
    def test_translation_review_rejects_changed_request_and_cancel_target(self,current_validate_mock,current_gateway_mock):
        current_review_value,current_summary_value,current_status_value,current_button_value=hermes_agent_app.review_hermes_translation_request('나무','en','','translation_123')
        self.assertTrue(current_button_value['interactive'])
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_translation_reviewed(current_review_value,'다른 원문','en','','translation_123')
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_translation_cancellation({'request_id':'translation_123','job_id':'old'},'translation_123','new')
        current_gateway_mock.assert_not_called()
        current_gateway_mock.return_value={'state':'accepted','job_id':'job-1'}
        self.assertEqual(hermes_agent_app.submit_hermes_translation_reviewed(current_review_value,'나무','en','','translation_123')[0],'job-1')

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_city_load_failure_clears_draft_and_explains_connection(self,current_gateway_mock):
        current_gateway_mock.side_effect = ValueError('private details')
        current_draft_value,current_review_value,current_group_value,current_status_value = hermes_agent_app.load_hermes_city_map_draft('iseulon')
        self.assertEqual(current_draft_value,'')
        self.assertIsNone(current_review_value)
        self.assertFalse(current_group_value['visible'])
        self.assertIn('콘텐츠 DB 연결',current_status_value)
        self.assertNotIn('private',current_status_value)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_city_review_rejects_changed_draft(self,current_gateway_mock):
        current_draft_text = '{"map":"stonewarm","generation":5,"revision":2,"document":{}}'
        current_gateway_mock.return_value = {'token':'a'*64,'changed':True,'buildings':1,'objects':0}
        current_review_value, current_summary_value, current_group_value = hermes_agent_app.review_hermes_city_map_draft(current_draft_text,'city_request_123')
        self.assertTrue(current_group_value['visible'])
        self.assertIn('DB 세대: 5',current_summary_value)
        with self.assertRaises(gr.Error):
            hermes_agent_app.save_hermes_city_map_draft(current_review_value,current_draft_text.replace('stonewarm','iseulon'),'city_request_123')
        self.assertEqual(current_gateway_mock.call_count,1)
        current_gateway_mock.return_value = {'state':'completed','saved':False}
        self.assertIn('DB 쓰기를 생략',hermes_agent_app.save_hermes_city_map_draft(current_review_value,current_draft_text,'city_request_123')[2])

    def test_field_proposal_display_preserves_following_explanation(self):
        import json
        current_proposal_value={'map':'sample','revision':'r1','cells':[{'column':1,'row':2,'tile':'m','height':0,'blocked':False}]}
        current_answer_value='설명\nHERMES_FIELD_PROPOSAL\n'+json.dumps(current_proposal_value)+'\nEND_HERMES_FIELD_PROPOSAL\n\n저장 전 검토하세요.'
        current_display_value=hermes_agent_app.format_hermes_conversation_answer(current_answer_value)
        self.assertIn('셀 제안',current_display_value)
        self.assertIn('저장 전 검토하세요.',current_display_value)
        self.assertNotIn('HERMES_FIELD_PROPOSAL',current_display_value)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_field_proposal_preserves_objects_and_rejects_stale_revision(self,current_gateway_mock):
        import json
        current_cell_value={'column':1,'row':2,'tile':'m','height':0,'blocked':False}
        current_object_value={'id':'tree','kind':'decoration','position':{'column':1,'row':1},'textureKey':'tree-v1','tileAnchor':'center'}
        current_proposal_value={'map':'sample','revision':'r1','cells':[current_cell_value]}
        current_map_value={'map':'sample','revision':'r1','tiles':{'objects':[current_object_value]}}
        current_gateway_mock.side_effect=[{'proposal':current_proposal_value},current_map_value]
        current_result_value=hermes_agent_app.load_hermes_field_map_proposal('job-1')
        current_draft_value=json.loads(current_result_value[1])
        self.assertEqual(current_draft_value['cells'],[current_cell_value])
        self.assertEqual(current_draft_value['objects'],[current_object_value])
        self.assertIsNone(current_result_value[4])
        self.assertFalse(current_result_value[5]['visible'])
        self.assertEqual([item.args[1] for item in current_gateway_mock.call_args_list],['hermes-field-proposal','hermes-field-load'])
        current_gateway_mock.side_effect=[{'proposal':current_proposal_value},{**current_map_value,'revision':'r2'}]
        with self.assertRaises(gr.Error):
            hermes_agent_app.load_hermes_field_map_proposal('job-1')

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_field_history_reports_unknown_without_saving(self,current_gateway_mock):
        current_gateway_mock.return_value = {'records':[{'request_id':'field_unknown_123','map':'sample','state':'unknown'}]}
        current_choices_value, current_message_value = hermes_agent_app.list_hermes_field_map_choices()
        self.assertEqual(current_choices_value['choices'][0][1],'field_unknown_123')
        current_gateway_mock.return_value = {'request_id':'field_unknown_123','map':'sample','state':'unknown'}
        self.assertIn('확인 필요',hermes_agent_app.read_hermes_field_map_receipt('field_unknown_123'))
        self.assertEqual([item.args[1] for item in current_gateway_mock.call_args_list],['hermes-field-history','hermes-field-receipt'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_field_map_review_rejects_changed_draft(self, current_gateway_mock):
        current_draft_text = '{"map":"moss-clearing","revision":"r","cells":[],"objects":[]}'
        current_gateway_mock.return_value = {'token':'a'*64,'changed':True,'cells':0,'objects':0,'reachable':1}
        current_review_value, current_summary_value, current_group_value = hermes_agent_app.review_hermes_field_map_draft(current_draft_text,'field_request_123')
        self.assertTrue(current_group_value['visible'])
        with self.assertRaises(gr.Error):
            hermes_agent_app.save_hermes_field_map_draft(current_review_value,current_draft_text.replace('moss-clearing','grove'),'field_request_123')
        self.assertEqual(current_gateway_mock.call_count,1)
        current_gateway_mock.return_value = {'state':'completed','saved':True}
        self.assertIn('저장 완료',hermes_agent_app.save_hermes_field_map_draft(current_review_value,current_draft_text,'field_request_123')[2])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_content_database_summary_distinguishes_pending_and_unavailable(self, current_gateway_mock):
        current_gateway_mock.return_value = {'status':'available','generation':9,'ledger_generation':7,'pending':True,'latest':{'state':'failed','lease_expired':True},'queried_at':'now'}
        current_summary_value = hermes_agent_app.read_hermes_content_database_summary()
        self.assertIn('반영 대기: 예', current_summary_value)
        self.assertIn('임대 만료', current_summary_value)
        current_gateway_mock.return_value = {'status':'unavailable'}
        self.assertIn('확인 불가', hermes_agent_app.read_hermes_content_database_summary())

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_model_readiness_distinguishes_service_and_artifact_status(self, current_gateway_mock):
        current_gateway_mock.return_value={'status':'available','ready':False,'artifacts_ready':True,'generation_ready':None,'preparation_status':'unknown','prepare_allowed':True,'queried_at':'now'}
        current_summary_value=hermes_agent_app.read_hermes_model_readiness_summary('music-heartmula')
        self.assertIn('서비스 준비 판정: 아니요',current_summary_value)
        self.assertIn('파일 준비 별도 판정: 예',current_summary_value)
        self.assertIn('생성 준비: 확인 불가',current_summary_value)
        self.assertIn('다운로드 상태: 확인 불가',current_summary_value)
        current_gateway_mock.return_value['download']={'ready':False,'preparation_status':'running'}
        current_summary_value=hermes_agent_app.read_hermes_model_readiness_summary('music-heartmula')
        self.assertIn('다운로드 파일 준비: 아니요',current_summary_value)
        self.assertIn('다운로드 상태: 진행 중',current_summary_value)
        current_gateway_mock.return_value['status']='unavailable'
        current_summary_value=hermes_agent_app.read_hermes_model_readiness_summary('music-heartmula')
        self.assertIn('모델 상태 조회 불가',current_summary_value)
        self.assertIn('다운로드 상태: 진행 중',current_summary_value)
        current_gateway_mock.return_value['status']='available'
        current_gateway_mock.return_value.pop('artifacts_ready')
        self.assertIn('파일 준비 별도 판정: 확인 불가',hermes_agent_app.read_hermes_model_readiness_summary('music-heartmula'))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_model_preparation_history_restores_service_and_identifier(self, current_gateway_mock):
        current_gateway_mock.return_value = {'records':[{'request_id':'request_123','service':'flux-image','state':'unknown'}]}
        current_choices_value, current_message_value = hermes_agent_app.list_hermes_model_preparation_choices()
        self.assertEqual(current_choices_value['choices'][0][1], 'flux-image:request_123')
        self.assertEqual(hermes_agent_app.select_hermes_model_preparation_receipt('flux-image:request_123'), ('flux-image','request_123'))
        current_gateway_mock.assert_called_once_with('hermes-agent','hermes-model-prepare-history',{})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_model_preparation_requires_review_and_unchanged_target(self, current_gateway_mock):
        current_gateway_mock.return_value = {'status':'available', 'ready':False, 'preparation_status':'idle', 'prepare_allowed':True}
        current_review_value, current_summary_value, current_group_value = hermes_agent_app.review_hermes_model_preparation('flux-image', 'request_123')
        self.assertTrue(current_group_value['visible'])
        self.assertIn('다운로드', current_summary_value)
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_model_preparation(current_review_value, 'kimodo', 'request_123')
        self.assertEqual(current_gateway_mock.call_count, 1)
        current_gateway_mock.return_value = {'state':'accepted'}
        current_result_value = hermes_agent_app.submit_hermes_model_preparation(current_review_value, 'flux-image', 'request_123')
        self.assertIn('완료 여부', current_result_value[2])
        current_gateway_mock.assert_called_with('hermes-agent','hermes-model-prepare',current_review_value)
        current_gateway_mock.return_value = {'status':'available','prepare_allowed':False}
        with self.assertRaises(gr.Error):
            hermes_agent_app.review_hermes_model_preparation('expression-lora','request_456')

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_cancellation_uncertainty_closes_confirmation_and_requires_status(self,current_gateway_mock):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_cases=[(hermes_agent_app.submit_hermes_flux_cancellation,{'request_id':'request_12345','job_id':current_job_identifier},('request_12345',current_job_identifier)),(hermes_agent_app.submit_hermes_translation_cancellation,{'request_id':'request_12345','job_id':current_job_identifier},('request_12345',current_job_identifier)),(hermes_agent_app.submit_hermes_video_cancellation,{'request_id':'request_12345','service':'wan22-vace','job_id':current_job_identifier},('request_12345','wan22-vace',current_job_identifier)),(hermes_agent_app.submit_hermes_audio_cancellation,{'request_id':'request_12345','service':'music-heartmula','job_id':current_job_identifier},('request_12345','music-heartmula',current_job_identifier)),(hermes_agent_app.submit_hermes_flux_profile_cancellation,{'request_id':'request_12345','service':'flux-building','job_id':current_job_identifier},('request_12345','flux-building',current_job_identifier))]
        for current_function_value,current_review_value,current_arguments in current_cases:
            with self.subTest(function=current_function_value.__name__):
                for current_response_value in (OSError('lost'),{'cancel_requested':False,'job_id':current_job_identifier},{'cancel_requested':True,'job_id':'different'}):
                    current_gateway_mock.side_effect=current_response_value if isinstance(current_response_value,Exception) else None
                    current_gateway_mock.return_value=current_response_value
                    current_state_value,current_group_value,current_status_text=current_function_value(current_review_value,*current_arguments)
                    self.assertIsNone(current_state_value)
                    self.assertFalse(current_group_value['visible'])
                    self.assertIn('결과 확인 필요',current_status_text)
                    self.assertIn('상태를 확인',current_status_text)
                current_gateway_mock.side_effect=None
                current_gateway_mock.return_value={'cancel_requested':True,'job_id':current_job_identifier}
                self.assertIn('실제 종료',current_function_value(current_review_value,*current_arguments)[2])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_kimodo_cancellation_uncertainty_requires_status(self,current_gateway_mock):
        current_review_value={'request_id':'request_12345','job_id':'2026-11-18_00-00-00-12345678'}
        current_gateway_mock.side_effect=OSError('lost')
        current_state_value,current_group_value,current_status_text=hermes_agent_app.submit_hermes_kimodo_cancellation(current_review_value)
        self.assertIsNone(current_state_value)
        self.assertFalse(current_group_value['visible'])
        self.assertIn('상태를 확인',current_status_text)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_audio_and_flux_completion_report_unavailable_links(self,current_gateway_mock):
        current_gateway_mock.return_value={'receipt':{'state':'accepted','job_id':'job-1'},'job':{'status':'completed','result_status':'unavailable','audio':None,'image':None}}
        self.assertIn('음원 링크 확인 불가',hermes_agent_app.read_hermes_audio_result('request_123','music-heartmula')[1])
        self.assertIn('이미지 링크 확인 불가',hermes_agent_app.read_hermes_flux_profile_result('request_123','flux-building')[1])
        current_gateway_mock.return_value['job']['result_status']='not_ready'
        self.assertNotIn('링크 확인 불가',hermes_agent_app.read_hermes_audio_result('request_123','music-heartmula')[1])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_video_result_distinguishes_completed_from_unavailable_files(self,current_gateway_mock):
        current_gateway_mock.return_value={'receipt':{'state':'accepted','job_id':'job-1'},'job':{'status':'completed','result_status':'unavailable'}}
        self.assertIn('결과 파일 확인 불가',hermes_agent_app.read_hermes_video_result('request_123','wan22-vace')[1])
        current_gateway_mock.return_value['job']['result_status']='partial'
        self.assertIn('결과 일부만 확인됨',hermes_agent_app.read_hermes_video_result('request_123','wan22-vace')[1])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_flux_profile_result_links_only_matching_completed_image(self,current_gateway_mock):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_image_path='/flux-building-generator/jobs/'+current_job_identifier+'/result.png'
        current_gateway_mock.return_value={'receipt':{'state':'accepted','job_id':current_job_identifier},'job':{'status':'completed','image':current_image_path}}
        current_job_value,current_status_text=hermes_agent_app.read_hermes_flux_profile_result('profile_request_123','flux-building')
        self.assertEqual(current_job_value,current_job_identifier)
        self.assertIn('[생성 이미지 보기]('+current_image_path+')',current_status_text)
        current_gateway_mock.return_value['job']['image']='https://example.com/result.png'
        self.assertNotIn('생성 이미지 보기',hermes_agent_app.read_hermes_flux_profile_result('profile_request_123','flux-building')[1])
        current_gateway_mock.return_value['job']={'status':'running','image':current_image_path}
        self.assertNotIn('생성 이미지 보기',hermes_agent_app.read_hermes_flux_profile_result('profile_request_123','flux-building')[1])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_flux_review_blocks_changed_input_and_cancel_target(self, current_gateway_mock):
        current_review, current_preview, current_status, current_button = hermes_agent_app.review_hermes_flux_request('blue sky', 512, 512, 42, 'request_12345')
        self.assertTrue(current_button['interactive'])
        self.assertIn('blue sky', current_preview)
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_flux_reviewed_request(current_review, 'different', 512, 512, 42, 'request_12345')
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_flux_cancellation({'request_id':'request_12345', 'job_id':'old-job'}, 'request_12345', 'new-job')
        current_gateway_mock.assert_not_called()
        current_gateway_mock.return_value = {'state':'accepted','job_id':'job-1','duplicate':False}
        self.assertEqual(hermes_agent_app.submit_hermes_flux_reviewed_request(current_review, 'blue sky', 512, 512, 42, 'request_12345')[0], 'job-1')
        current_gateway_mock.assert_called_once_with('hermes-agent','hermes-delegate-flux-image',current_review)
        current_invalid_review = hermes_agent_app.review_hermes_flux_request('blue sky', 513, 512, 42, 'request_12345')
        self.assertIsNone(current_invalid_review[0])
        self.assertFalse(current_invalid_review[3]['interactive'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_flux_reference_images_are_reviewed_and_rechecked(self,current_gateway_mock):
        from PIL import Image
        current_first_image=Image.new('RGB',(8,8),'red')
        current_second_image=Image.new('RGB',(8,8),'blue')
        current_input_values=['blue sky',512,512,42,'request_12345',current_first_image,current_second_image]
        current_review_record,current_preview_text,_,current_button=hermes_agent_app.review_hermes_flux_request(*current_input_values)
        self.assertTrue(current_button['interactive'])
        self.assertIn('참조 이미지: 2장',current_preview_text)
        self.assertEqual(len(current_review_record['request']['images']),2)
        import base64,hashlib
        for current_image_index,current_image_text in enumerate(current_review_record['request']['images'],1):
            current_image_digest=hashlib.sha256(base64.b64decode(current_image_text)).hexdigest()
            self.assertIn(f'참조 {current_image_index} PNG SHA-256: {current_image_digest}',current_preview_text)
        current_confirm_values=[current_review_record,*current_input_values]
        self.assertTrue(hermes_agent_app.match_hermes_flux_image_confirmation(current_confirm_values,current_confirm_values))
        current_changed_values=[*current_input_values[:-1],Image.new('RGB',(8,8),'green')]
        self.assertFalse(hermes_agent_app.match_hermes_flux_image_confirmation(current_confirm_values,[current_review_record,*current_changed_values]))
        with self.assertRaises(gr.Error):hermes_agent_app.submit_hermes_flux_reviewed_request(current_review_record,*current_changed_values)
        current_gateway_mock.assert_not_called()
        current_gateway_mock.return_value={'state':'accepted','job_id':'job-1'}
        self.assertEqual(hermes_agent_app.submit_hermes_flux_reviewed_request(current_review_record,*current_input_values)[0],'job-1')
        self.assertIsNone(hermes_agent_app.review_hermes_flux_request(*current_input_values[:5],None,current_second_image)[0])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_general_flux_result_link_requires_matching_completed_job(self,current_gateway_mock):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_image_path='/flux-image-generator/jobs/'+current_job_identifier+'/result.png'
        current_gateway_mock.return_value={'receipt':{'state':'accepted','job_id':current_job_identifier},'job':{'status':'completed'},'result':{'status':'available','image':current_image_path}}
        self.assertIn('[생성 이미지 보기]('+current_image_path+')',hermes_agent_app.read_hermes_flux_receipt('request_123')[1])
        current_gateway_mock.return_value['result']={'status':'unavailable','image':None}
        self.assertIn('이미지 링크 확인 불가',hermes_agent_app.read_hermes_flux_receipt('request_123')[1])
        current_gateway_mock.return_value['result']={'status':'available','image':'https://example.com/result.png'}
        self.assertNotIn('생성 이미지 보기',hermes_agent_app.read_hermes_flux_receipt('request_123')[1])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_flux_history_and_status_do_not_submit(self, current_gateway_mock):
        current_gateway_mock.return_value = {'records':[{'request_id':'request_12345','state':'unknown','job_id':None}], 'truncated':False}
        current_choices, current_message = hermes_agent_app.list_hermes_flux_delegation_choices(None)
        self.assertEqual(current_choices['choices'][0][1], 'request_12345')
        current_gateway_mock.return_value = {'receipt':{'state':'unknown'}}
        self.assertIn('확인 필요', hermes_agent_app.read_hermes_flux_receipt('request_12345')[1])
        self.assertEqual([call.args[1] for call in current_gateway_mock.call_args_list], ['hermes-flux-delegation-history','hermes-flux-delegation-status'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_flux_proposal_load_clears_review_and_does_not_submit(self, current_gateway_mock):
        current_gateway_mock.return_value = {'proposal':{'prompt':'blue sky','width':512,'height':512,'seed':42}}
        current_values = hermes_agent_app.load_hermes_flux_proposal('job-1')
        self.assertEqual(current_values[:4], ('blue sky',512,512,42))
        self.assertIsNone(current_values[5])
        self.assertIsNone(current_values[6])
        self.assertIsNone(current_values[7])
        self.assertFalse(current_values[10]['interactive'])
        current_gateway_mock.assert_called_once_with('hermes-agent','hermes-flux-proposal',{'id':'job-1'})
        current_answer = '제안입니다.\nHERMES_FLUX_PROPOSAL\n{"prompt":"blue sky","width":512,"height":512,"seed":42}\nEND_HERMES_FLUX_PROPOSAL'
        self.assertIn('FLUX 작업 제안', hermes_agent_app.format_hermes_conversation_answer(current_answer))
        self.assertEqual(hermes_agent_app.format_hermes_conversation_answer(current_answer, True),current_answer)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_building_next_page_keeps_snapshot_and_search(self,current_gateway_mock):
        current_gateway_mock.return_value={'total':2,'offset':0,'generation':7,'next_offset':1,'snapshot':'a'*64,'items':[]}
        current_page_result=hermes_agent_app.read_hermes_building_catalog_rows('길드',0)
        current_page_state=current_page_result[2]
        self.assertEqual(current_page_state,{'query':'길드','next_offset':1,'snapshot':'a'*64})
        current_gateway_mock.return_value.update(offset=1,next_offset=None)
        hermes_agent_app.read_hermes_building_catalog_rows('길드',1,current_page_state)
        current_gateway_mock.assert_called_with('hermes-agent','hermes-building-catalog',{'query':'길드','offset':1,'limit':20,'snapshot':'a'*64})
        current_gateway_mock.reset_mock()
        current_result_value=hermes_agent_app.read_hermes_building_catalog_rows('다른 검색',1,current_page_state)
        self.assertIn('다시 조회',current_result_value[1])
        current_gateway_mock.assert_not_called()

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_kimodo_build_memory_failure_is_visible(self,current_gateway_mock):
        current_gateway_mock.return_value={'status':'failed','job_id':'2026-11-18_00-00-00-12345678','failure_reason':'시스템 메모리 보호로 빌드가 중단됐습니다.'}
        self.assertIn('메모리 보호',hermes_agent_app.read_hermes_kimodo_build_summary())

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_writer_reservation_recovery_needs_checked_current_target(self,current_gateway_mock):
        current_job_identifier='20261118-120000-12345678'
        current_gateway_mock.return_value={'job_id':current_job_identifier,'recoverable':True,'preview_sha256':'a'*64,'reason':'시험'}
        current_review_value,_,_,_=hermes_agent_app.review_hermes_writer_reservation_recovery(current_job_identifier,'recovery_123')
        with self.assertRaises(Exception):hermes_agent_app.submit_hermes_writer_reservation_recovery(current_review_value,'recovery_123',current_job_identifier,False)
        with self.assertRaises(Exception):hermes_agent_app.submit_hermes_writer_reservation_recovery(current_review_value,'recovery_456',current_job_identifier,True)
        current_gateway_mock.return_value={'state':'completed'}
        self.assertIn('예약을 해제',hermes_agent_app.submit_hermes_writer_reservation_recovery(current_review_value,'recovery_123',current_job_identifier,True)[2])
        self.assertTrue(current_gateway_mock.call_args.args[2]['outside_processes_checked'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_writer_cancel_confirmation_checks_identity_and_status(self,current_gateway_mock):
        current_job_identifier='20261118-120000-12345678'
        current_gateway_mock.return_value={'receipt':{'job_id':current_job_identifier},'job':{'stage':'reasoning'}}
        current_review_value,_,_=hermes_agent_app.review_hermes_writer_cancellation('request_123',current_job_identifier)
        with self.assertRaises(Exception):hermes_agent_app.submit_hermes_writer_cancellation(current_review_value,'request_456',current_job_identifier)
        current_gateway_mock.return_value={'job_id':current_job_identifier,'cancel_requested':True}
        self.assertIn('중지를 요청',hermes_agent_app.submit_hermes_writer_cancellation(current_review_value,'request_123',current_job_identifier)[2])
        current_gateway_mock.return_value={'receipt':{'job_id':current_job_identifier},'job':{'stage':'review'}}
        with self.assertRaises(Exception):hermes_agent_app.review_hermes_writer_cancellation('request_123',current_job_identifier)

    def test_building_edit_invalidation_hides_confirmation_and_review(self):
        current_state_value,current_review_value,current_group_update,current_status_text=hermes_agent_app.invalidate_hermes_building_review()
        self.assertIsNone(current_state_value)
        self.assertIsNone(current_review_value)
        self.assertFalse(current_group_update['visible'])
        self.assertIn('다시 검토',current_status_text)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_building_anchor_review_requires_unchanged_draft(self,current_gateway_mock):
        import json
        from types import SimpleNamespace
        current_catalog_items=[{'id':'town-test-v1','generation':3,'display_properties':{'anchorX':0.5,'anchorY':1}}]
        current_selected,current_draft_text,current_request_identifier,_,_,_=hermes_agent_app.prepare_hermes_building_anchor_draft(current_catalog_items,SimpleNamespace(index=0))
        current_draft_record=json.loads(current_draft_text)
        current_draft_record['properties']['anchorX']=0.6
        current_draft_text=json.dumps(current_draft_record)
        current_gateway_mock.return_value={'review_sha256':'a'*64}
        current_review_record,_,_,_=hermes_agent_app.review_hermes_building_anchor_draft(current_draft_text,current_request_identifier)
        with self.assertRaises(Exception):hermes_agent_app.save_hermes_building_anchor_draft(current_review_record,current_draft_text+' ',current_request_identifier+'changed')
        current_gateway_mock.return_value={'state':'completed','saved':True}
        current_result_value=hermes_agent_app.save_hermes_building_anchor_draft(current_review_record,current_draft_text,current_request_identifier)
        self.assertIn('저장 완료',current_result_value[2])
        current_gateway_mock.assert_called_with('hermes-agent','hermes-building-save',current_review_record)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_building_catalog_display_distinguishes_pixels_from_game_size(self,current_gateway_mock):
        current_gateway_mock.return_value={'total':1,'offset':0,'generation':7,'next_offset':None,'items':[{'id':'town-iseulon-guild-v1','image_pixels':{'width':512,'height':256},'display_properties':{'anchorX':0.5,'anchorY':1.0},'uses':[{'map':'iseulon'}]}]}
        current_rows,current_status,current_next,current_button,current_items,current_detail=hermes_agent_app.read_hermes_building_catalog_rows('길드',0)
        self.assertEqual(current_rows,[['town-iseulon-guild-v1','512×256','0.5','1.0','iseulon']])
        self.assertIn('게임 표시 크기가 아닙니다',current_status)
        self.assertEqual(current_items[0]['id'],'town-iseulon-guild-v1')
        self.assertFalse(current_button['interactive'])
        current_gateway_mock.assert_called_once_with('hermes-agent','hermes-building-catalog',{'query':'길드','offset':0,'limit':20})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_world_map_page_shows_links_without_assuming_tile_coordinates(self,current_gateway_mock):
        current_gateway_mock.return_value={'maps':[{'id':'town','name':'마을','safe_town':True,'column':0,'row':1,'connections':[{'target':'field','direction':'north'}]}],'provenance':[{}],'queried_at':'now'}
        current_rows,current_status,current_items,current_detail=hermes_agent_app.read_hermes_world_map_rows()
        self.assertEqual(current_rows,[['town','마을','도시','0','1','field (north)']])
        self.assertIn('표시 위치',current_status)
        self.assertEqual(current_items[0]['id'],'town')
        self.assertIsNone(current_detail)
        current_gateway_mock.assert_called_once_with('hermes-agent','hermes-world-map',{})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_billboard_page_displays_semantics_and_next_cursor(self,current_gateway_mock):
        current_gateway_mock.return_value={'total':2,'offset':0,'revision':'a'*64,'next_offset':1,'items':[{'id':'tree-v1','name':'나무','category':'vegetation','display_properties':{'displayHeight':42},'modeling':{'purpose':'그늘','visual_review_status':'확인 필요'},'maps':[{'map':'field'}]}]}
        current_rows,current_status,current_next,current_button,current_items,current_detail=hermes_agent_app.read_hermes_billboard_catalog_rows(None,'나무',0)
        self.assertEqual(current_rows[0],['tree-v1','나무','vegetation','42','그늘','확인 필요','field'])
        self.assertEqual(current_next,1)
        self.assertTrue(current_button['interactive'])
        current_gateway_mock.assert_called_once_with('hermes-agent','hermes-billboard-catalog',{'query':'나무','offset':0,'limit':20})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_proposal_loading_clears_previous_review_without_submitting(self, current_gateway_mock):
        current_gateway_mock.return_value = {'proposal': {'prompt':'walk', 'frames':90, 'steps':100, 'seed':42}}
        current_input_values = hermes_agent_app.load_hermes_kimodo_proposal('2026-11-18_00-00-00-12345678')
        self.assertEqual(current_input_values[:4], ('walk', 90, 100, 42))
        self.assertIsNone(current_input_values[5])
        self.assertFalse(current_input_values[8]['interactive'])
        current_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-kimodo-proposal', {'id':'2026-11-18_00-00-00-12345678'})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_receipt_lookup_does_not_resubmit(self, current_gateway_mock):
        current_gateway_mock.return_value = {'state':'accepted', 'job_id':'2026-11-18_00-00-00-12345678'}
        self.assertEqual(hermes_agent_app.read_hermes_delegation_receipt('request_123456')[0], '2026-11-18_00-00-00-12345678')
        current_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-delegation-status', {'request_id':'request_123456'})
        current_gateway_mock.return_value = {'state':'unknown'}
        self.assertIn('확인 필요', hermes_agent_app.read_hermes_delegation_receipt('request_123456')[1])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_cancel_review_pins_receipt_before_request(self, current_gateway_mock):
        current_job_id = '2026-11-18_00-00-00-12345678'
        current_gateway_mock.return_value = {'state':'accepted', 'job_id':current_job_id}
        current_cancel_record, current_group_update, current_summary_text = hermes_agent_app.review_hermes_kimodo_cancellation('request_123456', current_job_id)
        self.assertTrue(current_group_update['visible'])
        self.assertIn(current_job_id, current_summary_text)
        self.assertEqual(current_gateway_mock.call_count, 1)
        with self.assertRaises(gr.Error):
            hermes_agent_app.review_hermes_kimodo_cancellation('request_123456', 'other')
        current_gateway_mock.return_value = {'job_id':current_job_id, 'cancel_requested':True, 'status':'running'}
        self.assertIn('실제 종료', hermes_agent_app.submit_hermes_kimodo_cancellation(current_cancel_record)[2])
        current_gateway_mock.assert_called_with('hermes-agent', 'hermes-delegation-cancel', current_cancel_record)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_delegation_history_selection_clears_stale_confirmation(self, current_gateway_mock):
        current_gateway_mock.side_effect = [{'records':[{'request_id':'request_123456', 'state':'accepted', 'job_id':'2026-11-18_00-00-00-12345678'}], 'truncated':False}, {'state':'accepted','job_id':'2026-11-18_00-00-00-12345678'}]
        current_choices_value, current_message_text = hermes_agent_app.list_hermes_delegation_choices()
        self.assertEqual(current_choices_value['choices'][0][1], 'request_123456')
        self.assertIn('1개', current_message_text)
        current_selection_value = hermes_agent_app.select_hermes_delegation_receipt('request_123456')
        self.assertEqual(current_selection_value[:2], ('request_123456','2026-11-18_00-00-00-12345678'))
        self.assertIsNone(current_selection_value[3])
        self.assertIsNone(current_selection_value[5])
        self.assertFalse(current_selection_value[6]['visible'])
        self.assertFalse(current_selection_value[7]['interactive'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_kimodo_status_is_concise_and_reports_failure(self, current_gateway_mock):
        current_gateway_mock.return_value = {'status':'failed','error':'메모리 보호','progress':{'percent':20},'quality_warnings':['확인 필요'],'log':'private large log'}
        current_status_text = hermes_agent_app.read_hermes_kimodo_job('2026-11-18_00-00-00-12345678')
        self.assertIn('실패', current_status_text)
        self.assertIn('메모리 보호', current_status_text)
        self.assertIn('20%', current_status_text)
        self.assertIn('확인 필요', current_status_text)
        self.assertNotIn('private large log', current_status_text)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_kimodo_status_surfaces_pose_shape_warning_without_dumping_logs(self, current_gateway_mock):
        current_gateway_mock.return_value = {'status':'completed', 'log':'onnxruntime VerifyOutputSizes output simcc_x', 'video':'/kimodo/job/video'}
        current_status_text = hermes_agent_app.read_hermes_kimodo_job('2026-11-18_00-00-00-12345678')
        self.assertIn('DWPose 출력 형상 경고', current_status_text)
        self.assertIn('품질을 확인', current_status_text)
        self.assertNotIn('onnxruntime VerifyOutputSizes', current_status_text)

    def test_kimodo_input_change_invalidates_review(self):
        current_review_value, _, _ = hermes_agent_app.review_hermes_kimodo_request('walk forward', 90, 100, 42, 'request_123456')
        for current_inputs_value in [('walk backward',90,100,42,'request_123456'), ('walk forward',91,100,42,'request_123456'), ('walk forward',90,100,42,'different_123456')]:
            with self.subTest(inputs=current_inputs_value):
                current_invalidated_value = hermes_agent_app.invalidate_hermes_kimodo_review(current_review_value, *current_inputs_value)
                self.assertIsNone(current_invalidated_value[0])
                self.assertIn('다시 검토', current_invalidated_value[2])
                self.assertFalse(current_invalidated_value[3]['interactive'])
        current_same_value = hermes_agent_app.invalidate_hermes_kimodo_review(current_review_value, 'walk forward',90,100,42,'request_123456')
        self.assertEqual(current_same_value, (gr.skip(),gr.skip(),gr.skip(),gr.skip()))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_kimodo_submit_rejects_stale_review_even_if_change_event_is_delayed(self, current_gateway_mock):
        current_review_value, _, _ = hermes_agent_app.review_hermes_kimodo_request('walk forward', 90, 100, 42, 'request_123456')
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_kimodo_reviewed_request(current_review_value, 'walk backward', 90, 100, 42, 'request_123456')
        current_gateway_mock.assert_not_called()
        current_gateway_mock.return_value = {'state':'accepted','duplicate':False,'job_id':'2026-11-18_00-00-00-12345678'}
        self.assertEqual(hermes_agent_app.submit_hermes_kimodo_reviewed_request(current_review_value, 'walk forward', 90, 100, 42, 'request_123456')[0], '2026-11-18_00-00-00-12345678')
        current_gateway_mock.assert_called_once()

    def test_kimodo_review_freezes_request_and_rejects_invalid_input(self):
        current_snapshot_value, current_preview_value, current_message_text = hermes_agent_app.review_hermes_kimodo_request('walk forward', 90, 100, 42, 'request_123456')
        self.assertIn('walk forward', current_preview_value)
        self.assertIn('request_123456', current_preview_value)
        self.assertEqual(current_snapshot_value['request']['prompt'], 'walk forward')
        self.assertIn('공용 GPU 대기열', current_message_text)
        current_invalid_snapshot, _, current_invalid_message = hermes_agent_app.review_hermes_kimodo_request('walk forward', 1, 100, 42, 'request_123456')
        self.assertIsNone(current_invalid_snapshot)
        self.assertIn('실패', current_invalid_message)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_kimodo_confirmation_preserves_unknown_and_existing_id(self, current_gateway_mock):
        current_snapshot_value, _, _ = hermes_agent_app.review_hermes_kimodo_request('walk forward', 90, 100, 42, 'request_123456')
        current_gateway_mock.return_value = {'state':'unknown'}
        self.assertIn('확인 필요', hermes_agent_app.submit_hermes_kimodo_request(current_snapshot_value)[1])
        current_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-delegate-kimodo', current_snapshot_value)
        current_gateway_mock.return_value = {'state':'accepted', 'duplicate':True, 'job_id':'2026-11-18_00-00-00-12345678'}
        self.assertIn('기존 접수', hermes_agent_app.submit_hermes_kimodo_request(current_snapshot_value)[1])
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_kimodo_request(None)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_management_summary_distinguishes_unavailable(self, current_gateway_mock):
        from tools.review.ui.gradio.hermes_agent_app import read_hermes_management_summary
        current_gateway_mock.return_value = {'model': {'status':'unavailable'}, 'gpu': {'status':'unavailable'}, 'queue': {'status':'unavailable'}, 'queried_at':'now'}
        current_summary_text = read_hermes_management_summary()
        self.assertIn('Hermes 모델: 조회 불가', current_summary_text)
        self.assertIn('Kimodo: 조회 불가 · 조회 불가', current_summary_text)
        self.assertIn('메모리: 조회 불가', current_summary_text)
        self.assertIn('최근 Hermes 작업: 조회 불가', current_summary_text)
        self.assertIn('GPU 예약 기록: 조회 불가', current_summary_text)
        self.assertIn('GPU: unavailable', current_summary_text)
        self.assertIn('대기: 조회 불가', current_summary_text)
        current_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-management-status', {})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_management_summary_shows_recorded_active_count(self,current_gateway_mock):
        current_gateway_mock.return_value={'model':{'status':'unavailable'},'gpu':{'status':'unavailable'},'queue':{'status':'unavailable'},'queried_at':'now','generators':{'kimodo':{'model':{'status':'available','ready':True},'active':{'status':'available','running':True,'id':'job-1','count':2,'unknown_count':1}}}}
        current_summary_text=hermes_agent_app.read_hermes_management_summary()
        self.assertIn('기록상 대기·실행 2건 · 최근 job-1',current_summary_text)
        self.assertIn('상태 확인 불가 1건',current_summary_text)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_diff_pages_preserve_utf8_at_chunk_boundary(self, current_gateway_mock):
        import base64
        current_diff_bytes = b'a' * 65535 + '가나다'.encode('utf-8')
        def current_chunk_response(current_service_name, current_command_name, current_payload_value):
            self.assertEqual((current_service_name, current_command_name), ('hermes-agent', 'hermes-diff'))
            current_offset_value = current_payload_value['offset']
            current_chunk_value = current_diff_bytes[current_offset_value:current_offset_value + current_payload_value['limit']]
            current_next_value = current_offset_value + len(current_chunk_value)
            return {'id':current_payload_value['id'],'offset':current_offset_value,'size_bytes':len(current_diff_bytes),'data_base64':base64.b64encode(current_chunk_value).decode(),'next_offset':current_next_value if current_next_value < len(current_diff_bytes) else None}
        current_gateway_mock.side_effect = current_chunk_response
        current_first_text, current_first_message, current_cursor_value = hermes_agent_app.start_hermes_diff_pages('job-1')
        self.assertEqual(current_cursor_value['next_offset'], 65535)
        current_second_text, current_second_message, current_cursor_value = hermes_agent_app.read_hermes_diff_page('job-1', current_cursor_value)
        self.assertEqual(current_first_text + current_second_text, current_diff_bytes.decode('utf-8'))
        self.assertIn('마지막 부분', current_second_message)
        with self.assertRaises(gr.Error):
            hermes_agent_app.read_hermes_diff_page('job-1', current_cursor_value)
        with self.assertRaises(gr.Error):
            hermes_agent_app.read_hermes_diff_page('other-job', current_cursor_value)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_diff_pages_reject_changed_size_and_invalid_offsets(self, current_gateway_mock):
        current_gateway_mock.return_value = {'id':'job-1','offset':0,'size_bytes':4,'data_base64':'YQ==','next_offset':3}
        with self.assertRaises(gr.Error):
            hermes_agent_app.start_hermes_diff_pages('job-1')
        current_gateway_mock.return_value = {'id':'job-1','offset':2,'size_bytes':5,'data_base64':'YQ==','next_offset':3}
        with self.assertRaises(gr.Error):
            hermes_agent_app.read_hermes_diff_page('job-1', {'job_id':'job-1','next_offset':2,'size_bytes':4})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_batch_keyframe_verification_reports_failures(self,current_gateway_mock):
        import json
        current_placements_value=[{'id':'a'*32,'frame':1},{'id':'a'*32,'frame':20}]
        current_gateway_mock.return_value={'placements':current_placements_value,'sources':[{'id':'a'*32,'preview_sha256':'b'*64}]}
        current_status_value=hermes_agent_app.verify_hermes_kimodo_keyframe_placements(json.dumps(current_placements_value),30)
        self.assertIn('2개 배치, 1개 원본',current_status_value)
        self.assertIn('b'*64,current_status_value)
        current_gateway_mock.assert_called_once_with('hermes-agent','hermes-kimodo-keyframe-validate',{'keyframes':current_placements_value,'frames':30})
        current_gateway_mock.side_effect=OSError('unavailable')
        self.assertIn('검증 실패',hermes_agent_app.verify_hermes_kimodo_keyframe_placements(json.dumps(current_placements_value),30))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_keyframe_next_page_keeps_search_query(self,current_gateway_mock):
        current_gateway_mock.return_value={'items':[{'id':'a'*32,'tag':'걷기','source_frame':2}],'total':21,'snapshot':'c'*64,'next_offset':20}
        current_rows_value,current_status_value,current_next_value,current_button_value=hermes_agent_app.read_hermes_kimodo_keyframe_rows('걷기',0)
        self.assertTrue(current_button_value['interactive'])
        self.assertEqual(current_next_value,{'query':'걷기','offset':20,'snapshot':'c'*64})
        with self.assertRaises(gr.Error):
            hermes_agent_app.read_next_hermes_kimodo_keyframe_rows('달리기',current_next_value)
        current_gateway_mock.return_value={'items':[],'total':21,'snapshot':'c'*64,'next_offset':None}
        current_offset_value,_,_,_,current_button_value=hermes_agent_app.read_next_hermes_kimodo_keyframe_rows('걷기',current_next_value)
        self.assertEqual(current_offset_value,20)
        self.assertFalse(current_button_value['interactive'])

    def test_keyframe_selection_and_placement_validation(self):
        import json
        from types import SimpleNamespace
        current_rows_value=[['a'*32,'자세',12]]
        self.assertEqual(hermes_agent_app.select_hermes_kimodo_keyframe_row(current_rows_value,SimpleNamespace(index=(0,1))),'a'*32)
        current_json_value=hermes_agent_app.append_hermes_kimodo_keyframe_placement('[]','a'*32,5,30)
        self.assertEqual(json.loads(current_json_value),[{'id':'a'*32,'frame':5}])
        with self.assertRaises(gr.Error):
            hermes_agent_app.append_hermes_kimodo_keyframe_placement(current_json_value,'b'*32,5,30)
        with self.assertRaises(gr.Error):
            hermes_agent_app.select_hermes_kimodo_keyframe_row(current_rows_value,SimpleNamespace(index=(5,0)))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_kimodo_review_supports_keyframe_placements(self,current_gateway_mock):
        import json
        current_keyframes_text=json.dumps([{'id':'b'*32,'frame':20},{'id':'a'*32,'frame':1}])
        current_review_value,current_summary_value,current_status_value=hermes_agent_app.review_hermes_kimodo_request('걷기',30,2,42,'kimodo_request_1',current_keyframes_text)
        self.assertIsNotNone(current_review_value,current_status_value)
        self.assertEqual(current_review_value['request']['keyframes'][1]['frame'],20)
        self.assertTrue(current_review_value['request']['post_processing'])
        self.assertFalse(current_review_value['request']['remove_horizontal_motion'])
        self.assertIn('키프레임',current_summary_value)
        self.assertIn('접수 시 다시 검증',current_summary_value)
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_kimodo_reviewed_request(current_review_value,'걷기',30,2,42,'kimodo_request_1','[]')
        current_gateway_mock.assert_not_called()
        self.assertIsNone(hermes_agent_app.review_hermes_kimodo_request('걷기',30,2,42,'kimodo_request_1',json.dumps([{'id':'a'*32,'frame':31}]))[0])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_effect_registration_review_blocks_changed_inputs(self,current_gateway_mock):
        import json
        current_draft_text=json.dumps({'id':'fog-v1'})
        current_gateway_mock.return_value={'review_sha256':'a'*64}
        current_review_value,_,current_visible_value=hermes_agent_app.review_hermes_effect_registration_draft(current_draft_text,'register_request_1')
        self.assertTrue(current_visible_value['visible'])
        with self.assertRaises(gr.Error):
            hermes_agent_app.save_hermes_effect_registration_draft(current_review_value,json.dumps({'id':'other'}),'register_request_1')
        with self.assertRaises(gr.Error):
            hermes_agent_app.save_hermes_effect_registration_draft(current_review_value,current_draft_text,'register_request_2')
        current_gateway_mock.return_value={'state':'completed','id':'fog-v1','generation':4}
        _,current_hidden_value,current_status_value=hermes_agent_app.save_hermes_effect_registration_draft(current_review_value,current_draft_text,'register_request_1')
        self.assertFalse(current_hidden_value['visible'])
        self.assertIn('세대 4',current_status_value)
        current_gateway_mock.assert_called_with('hermes-agent','hermes-effect-register',current_review_value)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_waypoint_draft_uses_selected_revision(self,current_gateway_mock):
        import json
        current_gateway_mock.return_value={'id':'waypoint-v1','revision':'a'*64,'renderer':'waypoint-animation'}
        current_draft_text,current_review_value,current_visibility_value,current_status_value=hermes_agent_app.load_hermes_waypoint_replacement_draft('waypoint-v1')
        current_draft_value=json.loads(current_draft_text)
        self.assertEqual((current_draft_value['id'],current_draft_value['revision']),('waypoint-v1','a'*64))
        self.assertEqual(current_draft_value['effect']['image'],'')
        self.assertFalse(current_visibility_value['visible'])
        current_gateway_mock.return_value={'id':'waypoint-v1','revision':'a'*64,'renderer':'fog'}
        with self.assertRaises(gr.Error):
            hermes_agent_app.load_hermes_waypoint_replacement_draft('waypoint-v1')

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_waypoint_review_requires_unchanged_draft_and_selection(self,current_gateway_mock):
        import json
        current_draft_value={'id':'waypoint-v1','revision':'a'*64,'effect':{'id':'waypoint-v2'}}
        current_draft_text=json.dumps(current_draft_value)
        current_gateway_mock.return_value={'review_sha256':'b'*64}
        current_review_value,current_preview_value,current_visible_value=hermes_agent_app.review_hermes_waypoint_replacement_draft(current_draft_text,'waypoint_request_1','waypoint-v1')
        self.assertTrue(current_visible_value['visible'])
        with self.assertRaises(gr.Error):
            hermes_agent_app.save_hermes_waypoint_replacement_draft(current_review_value,current_draft_text,'waypoint_request_1','other')
        with self.assertRaises(gr.Error):
            hermes_agent_app.save_hermes_waypoint_replacement_draft(current_review_value,json.dumps({**current_draft_value,'id':'other'}),'waypoint_request_1','waypoint-v1')
        current_gateway_mock.return_value={'state':'completed','id':'waypoint-v2'}
        _,current_hidden_value,current_status_value=hermes_agent_app.save_hermes_waypoint_replacement_draft(current_review_value,current_draft_text,'waypoint_request_1','waypoint-v1')
        self.assertFalse(current_hidden_value['visible'])
        self.assertIn('DB 교체 완료',current_status_value)
        current_gateway_mock.assert_called_with('hermes-agent','hermes-waypoint-replace',current_review_value)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_source_history_pages_keep_service_and_snapshot(self,current_gateway_mock):
        current_gateway_mock.return_value={'records':[{'id':'2026-11-18_00-00-00-12345678','recorded_status':'running','status_source':'job'}],'total':2,'offset':0,'next_offset':1,'snapshot':'a'*64,'unavailable_count':2}
        current_rows_value,current_status_value,current_page_state,current_next_update=hermes_agent_app.read_hermes_generator_source_rows('flux-image')
        self.assertEqual(current_rows_value[0][1],'running')
        self.assertTrue(current_next_update['interactive'])
        self.assertIn('1–1',current_status_value)
        self.assertIn('확인 불가 색인 2건',current_status_value)
        current_gateway_mock.return_value={'records':[{'id':'2026-11-18_00-00-01-12345678','recorded_status':'completed','status_source':'job'}],'total':2,'offset':1,'next_offset':None,'snapshot':'a'*64,'unavailable_count':0}
        _,current_status_value,_,current_next_update=hermes_agent_app.read_next_hermes_generator_source_rows('flux-image',current_page_state)
        current_gateway_mock.assert_called_with('hermes-agent','hermes-generator-source-history',{'service':'flux-image','limit':30,'offset':1,'snapshot':'a'*64})
        self.assertIn('2–2',current_status_value)
        self.assertFalse(current_next_update['interactive'])
        current_gateway_mock.reset_mock()
        _,current_error_value,current_cleared_state,current_next_update=hermes_agent_app.read_next_hermes_generator_source_rows('kimodo',current_page_state)
        self.assertIn('처음부터',current_error_value)
        self.assertIsNone(current_cleared_state)
        self.assertFalse(current_next_update['interactive'])
        current_gateway_mock.assert_not_called()
        self.assertEqual(hermes_agent_app.clear_hermes_source_history()[0],[])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_service_registration_displays_only_explicit_gateway_rejections(self,current_gateway_mock):
        current_gateway_mock.return_value={'services':[{'service':'old','commands':['generate','history'],'gateway_blocked':[{'command':'generate','reason':'생성 차단'}],'conditional_limitations':[{'command':'resume','note':'이전 입력 제한'}],'hermes_links':['hermes-delegate-audio']},{'service':'future','commands':['run'],'gateway_blocked':[]}]}
        current_rows_value,current_status_value=hermes_agent_app.read_hermes_service_registration_rows()
        self.assertIn('generate: 생성 차단',current_rows_value[0][2])
        self.assertIn('resume: 이전 입력 제한',current_rows_value[0][4])
        self.assertIn('그 외 정책 미확인',current_rows_value[1][3])
        self.assertEqual(current_rows_value[0][5],'hermes-delegate-audio')
        self.assertEqual(current_rows_value[1][5],'연결 정보 미제공')
        self.assertIn('실행',current_status_value)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_service_registration_search_shows_pagination(self,current_gateway_mock):
        current_gateway_mock.return_value={'services':[],'total':15,'next_offset':10}
        current_rows_value,current_status_value=hermes_agent_app.read_hermes_service_registration_rows('음악',0)
        self.assertEqual(current_rows_value,[])
        self.assertIn('검색 결과 15개',current_status_value)
        self.assertIn('다음 시작 위치: 10',current_status_value)
        current_gateway_mock.assert_called_once_with('hermes-agent','hermes-service-registration',{'query':'음악','offset':0,'limit':10})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_capability_rows_explain_side_effects(self, current_gateway_mock):
        current_gateway_mock.return_value = {'records':[{'label':'Kimodo 작업 상태','command':'hermes-delegation-job-status','interfaces':['gui','mcp'],'required':['request_id'],'effect':'recovery_possible','gpu':'none','retry':'safe','note':'중단 작업 복구 가능'}],'unlisted_commands':['hermes-new-command']}
        current_rows_value, current_status_value = hermes_agent_app.read_hermes_capability_rows()
        self.assertEqual(current_rows_value[0][1:7],['hermes-delegation-job-status','화면, Codex MCP','request_id','상태 복구 가능','사용 안 함','같은 요청 재시도 가능'])
        self.assertIn('1개', current_status_value)
        self.assertIn('hermes-new-command',current_status_value)
        self.assertIn('지원 여부 확인 필요',current_status_value)
        current_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-capabilities', {})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_capability_search_filters_and_retains_unlisted_warning(self,current_gateway_mock):
        current_common_value={'interfaces':['gui','mcp'],'required':[],'effect':'read','gpu':'none','retry':'safe','note':'조회'}
        current_gateway_mock.return_value={'records':[{'label':'모델 상태','command':'hermes-model-readiness',**current_common_value},{'label':'FLUX 위임','command':'hermes-delegate-flux-image',**current_common_value}],'unlisted_commands':['hermes-new-command']}
        current_rows_value,current_status_value=hermes_agent_app.read_hermes_capability_rows('flux')
        self.assertEqual(len(current_rows_value),1)
        self.assertEqual(current_rows_value[0][1],'hermes-delegate-flux-image')
        self.assertIn('1개 / 전체 2개',current_status_value)
        self.assertIn('hermes-new-command',current_status_value)
        self.assertEqual(len(hermes_agent_app.read_hermes_capability_rows('CODEX MCP')[0]),2)
        self.assertEqual(hermes_agent_app.read_hermes_capability_rows('없는 기능')[0],[])

    def test_valid_proposal_is_presented_without_exposing_format(self):
        current_answer_value = '사람이 걷는 모션입니다.\nHERMES_KIMODO_PROPOSAL\n{"prompt":"walk forward","frames":90,"steps":100,"seed":42}\nEND_HERMES_KIMODO_PROPOSAL'
        current_display_value = hermes_agent_app.format_hermes_conversation_answer(current_answer_value)
        self.assertIn('사람이 걷는 모션입니다.', current_display_value)
        self.assertIn('대화 아래 작업 제안', current_display_value)
        self.assertNotIn('HERMES_KIMODO_PROPOSAL', current_display_value)
        self.assertEqual(hermes_agent_app.format_hermes_conversation_answer(current_answer_value, True), current_answer_value)
        current_invalid_value = current_answer_value.replace('"seed":42', '"seed":42,"url":"bad"')
        self.assertEqual(hermes_agent_app.format_hermes_conversation_answer(current_invalid_value), current_invalid_value)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_session_displays_tool_activity_before_final_answer(self, current_gateway_mock):
        current_gateway_mock.return_value = {'message_count':1, 'queried_at':'now', 'messages':[{'text':'질문','job_id':'job-1','job':{'status':{'status':'completed'},'final_response':'최종 답변','tool_activity':{'events':[{'type':'tool_use','name':'terminal','target':'상태 조회','timestamp':'now'},{'type':'tool_result','name':'terminal','result':'success'}],'truncated':False}}}]}
        current_conversation_values = hermes_agent_app.read_hermes_session_conversation('a' * 32)[0]
        self.assertIn('호출 terminal · 상태 조회', current_conversation_values[1]['content'])
        self.assertIn('결과 terminal · 성공', current_conversation_values[1]['content'])
        self.assertIn('최종 답변', current_conversation_values[2]['content'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_session_conversation_reads_existing_job_and_reports_truncation(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'message_count': 1, 'queried_at':'2026-11-17T14:00:00+00:00', 'messages': [{'text': '첫 질문', 'job_id': 'job-1', 'context_truncated': True, 'job': {'status': {'status':'completed'}, 'final_response':'첫 답변', 'final_response_truncated':False}}]}
        hermes_conversation_values, hermes_session_message, hermes_timer_update, hermes_job_update = hermes_agent_app.read_hermes_session_conversation('a' * 32)
        self.assertEqual(hermes_conversation_values[0], {'role': 'user', 'content': '첫 질문'})
        self.assertIn('첫 답변', hermes_conversation_values[1]['content'])
        self.assertIn('이전 문맥 일부', hermes_conversation_values[1]['content'])
        self.assertIn('메시지 1개', hermes_session_message)
        self.assertFalse(hermes_timer_update['active'])
        self.assertEqual(hermes_job_update['value'], 'job-1')
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-session-view', {'session_id':'a' * 32})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_session_job_opens_existing_details(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'status': {'status': 'completed'}, 'diff': 'diff', 'diff_truncated': False, 'log': 'log', 'result': None, 'final_response':'답변'}
        hermes_detail_values = hermes_agent_app.open_hermes_session_job('job-1')
        self.assertEqual(hermes_detail_values[:4], ('job-1', 'completed', '답변', 'diff'))
        self.assertIn('확인할 수 없습니다', hermes_detail_values[-2])
        self.assertTrue(hermes_detail_values[-1]['open'])
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-detail', {'id':'job-1'})
        with self.assertRaises(gr.Error):
            hermes_agent_app.open_hermes_session_job(None)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_pending_session_request_restores_original_id_and_inputs(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'messages': [{'request_id':'original-request-1234', 'text':'원래 질문', 'verification_modules':['tools.review.tests.test_hermes_service'], 'job_id':None}]}
        hermes_restored_values = hermes_agent_app.recover_hermes_session_request('a' * 32)
        self.assertEqual(hermes_restored_values[:3], ('original-request-1234', '원래 질문', 'tools.review.tests.test_hermes_service'))
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-session-read', {'session_id':'a' * 32})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_session_submission_uses_request_identifier_and_rotates_after_acknowledgement(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'job_id': 'job-1', 'duplicate': False, 'context_truncated': True}
        hermes_job_identifier, hermes_status_message, hermes_next_request, hermes_timer_update = hermes_agent_app.submit_hermes_session_request('a' * 32, 'same-request-1234', '질문')
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-session-submit', {'session_id':'a' * 32, 'request_id':'same-request-1234', 'prompt':'질문'})
        self.assertEqual(hermes_job_identifier, 'job-1')
        self.assertIn('일부만', hermes_status_message)
        self.assertNotEqual(hermes_next_request, 'same-request-1234')
        self.assertTrue(hermes_timer_update['active'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_selecting_history_loads_selected_job_details(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'status': {'status': 'completed'}, 'diff': '변경', 'diff_truncated': False, 'log': '기록', 'result': {'verification': {'status': 'passed'}}, 'final_response': '완료했습니다.', 'request': {'prompt':'전체 지시문'}}
        hermes_history_rows = [['first-job', 'failed', '첫 작업'], ['second-job', 'completed', '둘째 작업']]
        hermes_selected_event = gr.SelectData(None, {'index': (1, 2), 'value': '둘째 작업'})
        hermes_selected_values = hermes_agent_app.select_hermes_history_record(hermes_history_rows, hermes_selected_event)
        self.assertEqual(hermes_selected_values, ('second-job', 'completed · 독립 검증 통과', '완료했습니다.', '변경', '기록', {'verification': {'status': 'passed'}}, '전체 지시문'))
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-detail', {'id': 'second-job'})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_selecting_stale_history_does_not_request_another_job(self, hermes_gateway_mock):
        for hermes_selected_index in ((5, 0), (-1, 0), (True, 0), ()):
            with self.subTest(index=hermes_selected_index), self.assertRaises(gr.Error):
                hermes_agent_app.select_hermes_history_record([['first-job', 'completed', '작업']], gr.SelectData(None, {'index': hermes_selected_index, 'value': None}))
        hermes_gateway_mock.assert_not_called()

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_submission_passes_stable_request_identifier(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'id':'2026-11-17_10-00-00-12345678', 'duplicate':False}
        hermes_job_identifier, hermes_status_text = hermes_agent_app.submit_hermes_work_request('작업', 'same-request-1234')
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-submit', {'prompt':'작업', 'request_id':'same-request-1234'})
        self.assertEqual(hermes_job_identifier, '2026-11-17_10-00-00-12345678')

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command', side_effect=ValueError('지원하지 않는 관리 명령'))
    def test_history_explains_gateway_version_error(self, hermes_gateway_mock):
        hermes_history_rows, hermes_history_message = hermes_agent_app.refresh_hermes_work_history()
        self.assertEqual(hermes_history_rows, [])
        self.assertIn('게이트웨이 실행 상태와 버전', hermes_history_message)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_submission_includes_selected_verification_modules(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'id':'2026-11-17_10-00-00-12345678', 'duplicate':False}
        hermes_agent_app.submit_hermes_work_request('작업', 'request-1234', 'tools.review.tests.test_hermes_service\n')
        hermes_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-submit', {'prompt':'작업', 'request_id':'request-1234', 'verification_modules':['tools.review.tests.test_hermes_service']})


if __name__ == '__main__':
    unittest.main()
