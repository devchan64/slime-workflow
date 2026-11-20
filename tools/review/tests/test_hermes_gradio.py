import unittest
import gradio as gr
import tempfile
from unittest.mock import patch

from tools.review.ui.gradio import hermes_agent_app
from tools.review.ui.gradio.management_menu_app import load_manager_page_records
from tools.review.common.management_asgi import build_management_blocks
from pathlib import Path


def build_async_test_interface(current_interface_builder, *current_interface_arguments, **current_interface_options):
    """운영 서버처럼 실행 중인 루프에서 화면 빌더를 호출한다."""
    import asyncio
    async def construct_async_test_interface():
        return current_interface_builder(*current_interface_arguments, **current_interface_options)
    return asyncio.run(construct_async_test_interface())


def build_hermes_test_interface(*current_interface_arguments, **current_interface_options):
    """ASGI와 같이 실행 중인 루프에서 Gradio 테스트 화면을 구성한다."""
    import asyncio
    async def construct_hermes_test_interface():
        return hermes_agent_app.build_hermes_agent_interface(*current_interface_arguments, **current_interface_options)
    return asyncio.run(construct_hermes_test_interface())


class HermesGradioTests(unittest.TestCase):
    def test_wan_fun_prepare_selection_requires_verified_source(self):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-20_20-02-00-abcdef12'
        current_queue_rows=[['1','wan-fun-prepare',current_job_identifier,'wan22-fun-control']]
        current_target_value,_,current_button_value=operations_history_app.select_operations_priority_target(current_queue_rows,SimpleNamespace(index=0))
        self.assertEqual(current_target_value,{'service':'wan22-fun-control','id':current_job_identifier})
        self.assertTrue(current_button_value['interactive'])
        current_queue_rows[0][3]='미확인'
        self.assertIsNone(operations_history_app.select_operations_priority_target(current_queue_rows,SimpleNamespace(index=0))[0])
        current_reservation_rows=[['정리 확인 필요','wan-fun-prepare','2026-11-20_20-02-00-prepare','6144','미제공','wan22-fun-control']]
        current_target_value,current_button_value,_=operations_history_app.select_operations_reservation_inspection(current_reservation_rows,SimpleNamespace(index=0))
        self.assertEqual(current_target_value,{'service':'wan22-fun-control','job_id':'2026-11-20_20-02-00-prepare'})
        self.assertTrue(current_button_value['interactive'])
        current_reservation_rows[0][5]='미확인'
        self.assertIsNone(operations_history_app.select_operations_reservation_inspection(current_reservation_rows,SimpleNamespace(index=0))[0])
        current_queue_rows[0][2]='2026-11-20_20-02-00-prepare'
        current_queue_rows[0][3]='wan22-fun-control'
        current_target_value,_,current_button_value=operations_history_app.select_operations_priority_target(current_queue_rows,SimpleNamespace(index=0))
        self.assertIsNone(current_target_value)
        self.assertFalse(current_button_value['interactive'])

    def test_wan_fun_prepare_source_history_connects_queue_and_reservation(self):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-20_20-02-00-prepare'
        current_source_record={'service':'wan22-fun-control','source_service':'wan22-fun-control','records':[{'id':current_job_identifier,'recorded_status':'queued','status_source':'job'}],'total':1,'offset':0,'next_offset':None,'snapshot':'a'*64,'unavailable_count':0}
        current_management_record={'queried_at':'time','queue':{'status':'available','jobs':[{'service':'wan-fun-prepare','id':current_job_identifier,'source_service':'wan22-fun-control'}]},'reservations':{'status':'available','records':[{'state':'recorded','service':'wan-fun-prepare','job_id':current_job_identifier,'source_service':'wan22-fun-control','required_memory_mib':6144}],'truncated':False}}
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-generator-source-history':return current_source_record
            if current_command_name=='hermes-management-status':return current_management_record
            raise AssertionError(current_command_name)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=current_gateway_response):
            current_rows_value,current_notice_text,_,_,_=operations_history_app.read_operations_source_history('wan22-fun-control')
        self.assertEqual(current_rows_value[0][0],current_job_identifier)
        self.assertIn('준비: 대기 기록 확인 · 원 서비스 확인',current_rows_value[0][3])
        self.assertIn('준비: 예약 기록 확인 · 원 서비스 확인',current_rows_value[0][4])
        self.assertIn('GPU 대기 관측',current_notice_text)

    def test_wan_fun_prepare_history_checks_source_and_shows_both_queues(self):
        from collections import Counter
        from tools.review.common.gpu_job_queue import identify_dedicated_gpu_reservation_source
        from tools.review.ui.gradio import operations_history_app
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_workflow_root=Path(current_temporary_directory)
            current_job_directory=current_workflow_root/'.tmp'/'test'/'wan22-fun-control'/'prepare-123'
            current_job_directory.mkdir(parents=True)
            self.assertEqual(identify_dedicated_gpu_reservation_source(str(current_job_directory),'wan-fun-prepare',current_workflow_root),'wan22-fun-control')
            self.assertIsNone(identify_dedicated_gpu_reservation_source(str(current_workflow_root/'other'/'prepare-123'),'wan-fun-prepare',current_workflow_root))
        self.assertEqual(operations_history_app.read_operations_verified_source('wan-fun-prepare','wan22-fun-control'),'wan22-fun-control')
        self.assertIsNone(operations_history_app.read_operations_verified_source('wan-fun-prepare','other'))
        current_queue_counts=Counter({('wan-fun-prepare','prepare-123'):1})
        current_source_counts=Counter({('wan-fun-prepare','wan22-fun-control','prepare-123'):1})
        current_queue_label=operations_history_app.label_operations_verified_dedicated_queue(current_queue_counts,current_source_counts,'wan-fun','wan22-fun-control','prepare-123')
        self.assertIn('준비: 대기 기록 확인 · 원 서비스 확인',current_queue_label)
        current_reservation_index={('wan-fun-prepare','prepare-123'):['recorded'],('source','wan-fun-prepare','wan22-fun-control','prepare-123'):['recorded']}
        current_reservation_label=operations_history_app.label_operations_verified_dedicated_reservation(current_reservation_index,False,'wan-fun','wan22-fun-control','prepare-123')
        self.assertIn('준비: 예약 기록 확인 · 원 서비스 확인',current_reservation_label)
        current_unverified_label=operations_history_app.label_operations_verified_dedicated_queue(current_queue_counts,Counter(),'wan-fun','wan22-fun-control','prepare-123')
        self.assertIn('소유 확인 필요',current_unverified_label)

    def test_operations_session_navigation_disables_all_page_buttons(self):
        from tools.review.ui.gradio import operations_history_app
        current_interface_value=build_async_test_interface(operations_history_app.build_operations_history_interface)
        current_config_value=current_interface_value.get_config_file()
        current_component_labels={current_component['id']:current_component.get('props',{}).get('value') for current_component in current_config_value['components']}
        for current_button_label in ('세션 지시 조회','이전 지시','최근 지시 쪽'):
            current_matching_events=[current_event for current_event in current_config_value['dependencies'] if any(current_component_labels.get(current_target[0])==current_button_label and current_target[1]=='click' for current_target in current_event['targets']) and len(current_event['outputs'])==6]
            self.assertEqual(len(current_matching_events),1)
            current_updates=current_interface_value.fns[current_matching_events[0]['id']].fn()
            self.assertEqual([current_update.get('interactive') for current_update in current_updates[2:5]],[False,False,False])

    def test_operations_instruction_collection_accepts_overlapping_selection(self):
        from tools.review.ui.gradio import operations_history_app
        current_interface_value=build_async_test_interface(operations_history_app.build_operations_history_interface)
        current_config_value=current_interface_value.get_config_file()
        current_matching_events=[current_event for current_event in current_config_value['dependencies'] if current_interface_value.fns[current_event['id']].fn is operations_history_app.collect_operations_instruction_selection]
        self.assertEqual(len(current_matching_events),1)
        self.assertEqual(current_matching_events[0]['trigger_mode'],'multiple')

    def test_operations_instruction_rejects_late_session_page_or_selection(self):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_page_state={'session_id':current_session_identifier,'offset':0,'snapshot':'a'*64}
        current_token_value,current_selection_record,_,_=operations_history_app.prepare_operations_instruction_selection(current_session_identifier,[['time','old','job','완료','']],current_page_state,SimpleNamespace(index=0))
        with patch.object(operations_history_app,'select_operations_session_instruction',return_value=('old-link','old-instruction')):
            current_result_record=operations_history_app.collect_operations_instruction_selection(current_selection_record)
        self.assertEqual(operations_history_app.render_operations_instruction_selection('b'*32,current_page_state,current_token_value,current_result_record),(gr.skip(),gr.skip()))
        self.assertEqual(operations_history_app.render_operations_instruction_selection(current_session_identifier,{**current_page_state,'offset':20},current_token_value,current_result_record),(gr.skip(),gr.skip()))
        self.assertEqual(operations_history_app.render_operations_instruction_selection(current_session_identifier,current_page_state,'new-token',current_result_record),(gr.skip(),gr.skip()))
        self.assertEqual(operations_history_app.render_operations_instruction_selection(current_session_identifier,current_page_state,current_token_value,current_result_record),('old-link','old-instruction'))

    def test_operations_session_page_rejects_late_session_or_request(self):
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_page_result={'session_id':current_session_identifier,'token':'old-token','result':([['old']], '확인', 'old-link', None, gr.update(interactive=False), gr.update(interactive=False))}
        current_skip_values=(gr.skip(),)*10
        self.assertEqual(operations_history_app.render_operations_session_page('b'*32,'old-token',current_page_result),current_skip_values)
        self.assertEqual(operations_history_app.render_operations_session_page(current_session_identifier,'new-token',current_page_result),current_skip_values)
        current_render_values=operations_history_app.render_operations_session_page(current_session_identifier,'old-token',current_page_result)
        self.assertEqual(current_render_values[0],[['old']])
        self.assertEqual(current_render_values[6],[])
        self.assertIn('접수 기록을 조회',current_render_values[7])
        self.assertTrue(current_render_values[9]['interactive'])

    def test_operations_receipt_result_rejects_late_session_or_page(self):
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_page_state={'session_id':current_session_identifier,'offset':0,'snapshot':'a'*64}
        current_result_record={'session_id':current_session_identifier,'page':current_page_state,'token':'old-token','rows':[['job']],'notice':'확인'}
        current_skip_values=(gr.skip(),gr.skip(),gr.skip(),gr.skip())
        self.assertEqual(operations_history_app.render_operations_page_receipts('b'*32,current_page_state,'old-token',current_result_record),current_skip_values)
        self.assertEqual(operations_history_app.render_operations_page_receipts(current_session_identifier,{**current_page_state,'offset':20},'old-token',current_result_record),current_skip_values)
        self.assertEqual(operations_history_app.render_operations_page_receipts(current_session_identifier,current_page_state,'new-token',current_result_record),current_skip_values)
        self.assertEqual(operations_history_app.render_operations_page_receipts(current_session_identifier,current_page_state,'old-token',current_result_record),([['job']],'확인','',gr.update(interactive=True)))
        with patch.object(operations_history_app,'read_operations_current_page_receipts',return_value=([],'조회 실패')):
            current_collected_record=operations_history_app.collect_operations_page_receipts(current_session_identifier,current_page_state,'new-token')
        self.assertEqual(operations_history_app.render_operations_page_receipts(current_session_identifier,current_page_state,'new-token',current_collected_record),([],'조회 실패','',gr.update(interactive=True)))

    def test_cleanup_preview_rejects_late_other_service_result(self):
        from tools.review.ui.gradio import operations_history_app
        current_preview_record={'service':'dwpose','token':'old-token','message':'이전 서비스 조회 결과'}
        self.assertEqual(operations_history_app.render_operations_cleanup_preview('wan22-vace','old-token',current_preview_record),gr.skip())
        self.assertEqual(operations_history_app.render_operations_cleanup_preview('dwpose','old-token',current_preview_record),'이전 서비스 조회 결과')
        self.assertEqual(operations_history_app.render_operations_cleanup_preview('dwpose','new-token',None),gr.skip())
        self.assertEqual(operations_history_app.render_operations_cleanup_preview('dwpose','new-token',current_preview_record),gr.skip())

    def test_media_conversation_shows_unclassified_failure_guidance(self):
        current_session_identifier='a'*32
        current_source_identifier='2026-11-20_00-00-00-12345678'
        current_job_identifier='2026-11-20_01-00-00-87654321'
        for current_kind_name,current_service_name,current_page_name in (('audio','music-heartmula','music-heartmula'),('video','dwpose','dwpose-generator'),('flux','flux-character','flux-character-generator'),('flux','flux-image','flux-image-generator')):
            with self.subTest(kind=current_kind_name,service=current_service_name):
                current_card_record={'session_id':current_session_identifier,'source_job_id':current_source_identifier,'kind':current_kind_name,'service':current_service_name,'review':{'request_id':'request_123'}}
                current_status_record={'receipt':{'state':'accepted','request_id':'request_123','service':current_service_name,'job_id':current_job_identifier},'job':{'status':'failed','failure_code':'unclassified_failure','failure_reason':'실패 원인을 확인하지 못했습니다. 원 서비스의 작업 상태와 상세 로그를 확인하세요.'}}
                with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_status_record):
                    current_state_value,current_result_text=hermes_agent_app.read_conversation_service_status(current_card_record,current_session_identifier,current_source_identifier,current_kind_name)
                self.assertEqual(current_state_value,'accepted')
                self.assertIn('실패 원인을 확인하지 못했습니다',current_result_text)
                self.assertIn('상세 로그',current_result_text)
                self.assertNotIn('GPU 메모리 부족',current_result_text)
                current_expected_link='/management/frame/'+current_page_name+'/?job='+current_job_identifier+'&session='+current_session_identifier
                self.assertIn(current_expected_link,current_result_text)
                self.assertIn('job='+current_job_identifier,current_expected_link)
                self.assertIn('session='+current_session_identifier,current_expected_link)

    def test_result_views_reject_unrecognized_receipt_state(self):
        current_result_readers=[
            (hermes_agent_app.read_hermes_writer_result,('request_123',),'writer-agent'),
            (hermes_agent_app.read_hermes_translation_result,('request_123',),'prompt-translation'),
            (hermes_agent_app.read_hermes_video_result,('request_123','wan22-vace'),'wan22-vace'),
            (hermes_agent_app.read_hermes_audio_result,('request_123','music-heartmula'),'music-heartmula'),
            (hermes_agent_app.read_hermes_flux_profile_result,('request_123','flux-building'),'flux-building'),
            (hermes_agent_app.read_hermes_flux_receipt,('request_123',),'flux-image'),
        ]
        for current_reader_value,current_reader_arguments,current_service_name in current_result_readers:
            current_receipt_record={'request_id':'request_123','service':current_service_name,'state':'unexpected','job_id':'2026-11-18_00-00-00-12345678'}
            with self.subTest(service=current_service_name), patch.object(hermes_agent_app,'execute_remote_management_command',return_value={'receipt':current_receipt_record,'job':{'status':'completed'}}):
                with self.assertRaises(gr.Error):current_reader_value(*current_reader_arguments)

    def test_flux_receipt_rejects_wrong_unknown_or_missing_identity(self):
        for current_receipt_record in ({'state':'unknown','request_id':'wrong','service':'flux-image'}, {'state':'not_found','request_id':'request_123','service':'other'}, {'state':'unexpected','request_id':'request_123','service':'flux-image'}, None):
            with self.subTest(receipt=current_receipt_record), patch.object(hermes_agent_app,'execute_remote_management_command',return_value={'receipt':current_receipt_record}):
                with self.assertRaises(gr.Error):hermes_agent_app.read_hermes_flux_receipt('request_123')
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value={'receipt':{'state':'unknown','request_id':'request_123','service':'flux-image'}}):
            self.assertIn('접수 여부 확인 필요',hermes_agent_app.read_hermes_flux_receipt('request_123')[1])

    def test_flux_receipt_displays_unclassified_failure(self):
        current_job_identifier='2026-11-20_01-00-00-87654321'
        current_response_record={'receipt':{'state':'accepted','request_id':'request_123','service':'flux-image','job_id':current_job_identifier},'job':{'status':'failed','failure_reason':'원 서비스의 작업 상태와 상세 로그를 확인하세요.'},'result':{'image':None,'status':'not_ready'}}
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_response_record):
            current_identifier_value,current_notice_text=hermes_agent_app.read_hermes_flux_receipt('request_123')
        self.assertEqual(current_identifier_value,current_job_identifier)
        self.assertIn('상세 로그를 확인하세요',current_notice_text)

    def test_kimodo_conversation_shows_unclassified_failure_guidance(self):
        current_session_identifier='a'*32
        current_source_identifier='2026-11-20_00-00-00-12345678'
        current_job_identifier='2026-11-20_01-00-00-87654321'
        current_card_record={'session_id':current_session_identifier,'source_job_id':current_source_identifier,'kind':'kimodo','service':'kimodo','review':{'request_id':'request_123'}}
        current_result_record={'receipt':{'state':'accepted','request_id':'request_123','service':'kimodo','job_id':current_job_identifier},'job':{'status':'failed','failure_reason':'원 서비스 상세 로그를 확인하세요.'}}
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_result_record):
            current_result_text=hermes_agent_app.read_conversation_kimodo_result(current_card_record,current_session_identifier,current_source_identifier)
            self.assertIn('원 서비스 상세 로그',current_result_text)

    def test_operations_cleanup_summary_is_read_only_and_validates_service(self):
        from tools.review.ui.gradio import operations_history_app
        current_summary_record={'service':'dwpose','job_count':2,'blocked_count':1,'status_counts':{'failed':1,'running':1},'can_reset':False,'excludes_blocked':False}
        with patch.object(operations_history_app,'execute_remote_management_command',return_value=current_summary_record) as current_gateway_mock:
            current_display_text=operations_history_app.read_operations_cleanup_preview('dwpose')
            self.assertIn('서비스: `dwpose`',current_display_text)
            self.assertIn('2건',current_display_text)
            self.assertIn('차단 1건',current_display_text)
            self.assertIn('삭제는 수행하지 않았',current_display_text)
            current_gateway_mock.assert_called_once_with('hermes-agent','hermes-cleanup-preview',{'service':'dwpose'})
            self.assertIn('확인하지 못했습니다',operations_history_app.read_operations_cleanup_preview('wan22-vace'))
        with patch.object(operations_history_app,'execute_remote_management_command',return_value={**current_summary_record,'status_counts':{'failed':3}}):
            self.assertIn('확인하지 못했습니다',operations_history_app.read_operations_cleanup_preview('dwpose'))

    def test_video_resume_rechecks_preparation_before_submit(self):
        current_session_identifier='a'*32
        current_source_job='2026-11-20_00-00-00-12345678'
        current_target_job='2026-11-20_01-00-00-87654321'
        current_proposal_record={'service':'wan22-vace','job_id':current_target_job,'expected_resume_fingerprint':'b'*64}
        current_preparation_state={'value':'available'}
        current_command_values=[]
        def simulate_video_gateway(current_service_name,current_command_name,current_payload_record):
            current_command_values.append(current_command_name)
            if current_command_name=='hermes-video-resume-proposal':return {'job_id':current_source_job,'proposal':current_proposal_record}
            if current_command_name=='hermes-video-resume-receipt':return {'request_id':current_payload_record['request_id'],'state':'not_found'}
            if current_command_name=='hermes-video-resume-preview':return {**current_proposal_record,'status':'failed','resume_availability':current_preparation_state['value']}
            raise AssertionError('접수되면 안 됩니다: '+current_command_name)
        with patch.object(hermes_agent_app,'find_conversation_session_job',return_value={}),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=simulate_video_gateway):
            current_card_record,_,_=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'video_resume')
            self.assertTrue(current_card_record['ready'])
            current_preparation_state['value']='download_running'
            current_fresh_record,current_status_text=hermes_agent_app.submit_conversation_service_review(current_card_record,current_session_identifier,current_source_job,'video_resume')
            self.assertFalse(current_fresh_record['ready'])
            self.assertIn('모델 준비가 진행 중',current_status_text)
            self.assertNotIn('hermes-video-resume-submit',current_command_values)

    def test_video_resume_unknown_receipt_is_consistent_across_views(self):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_source_job='2026-11-20_00-00-00-12345678'
        current_target_job='2026-11-20_01-00-00-87654321'
        current_fingerprint_value='b'*64
        current_request_identifier='video_resume_'+hashlib.sha256(('dwpose\0'+current_target_job+'\0'+current_fingerprint_value).encode()).hexdigest()
        current_proposal_record={'service':'dwpose','job_id':current_target_job,'expected_resume_fingerprint':current_fingerprint_value}
        current_receipt_record={'request_id':current_request_identifier,**current_proposal_record,'state':'unknown'}
        def simulate_video_gateway(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-video-resume-proposal':return {'job_id':current_source_job,'proposal':current_proposal_record}
            if current_command_name=='hermes-video-resume-receipt':return current_receipt_record
            raise AssertionError('조회 중 예상하지 않은 명령: '+current_command_name)
        with patch.object(hermes_agent_app,'find_conversation_session_job',return_value={}),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=simulate_video_gateway),patch.object(operations_history_app,'execute_remote_management_command',side_effect=simulate_video_gateway):
            current_card_record,current_preview_text,current_notice_text=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'video_resume')
            self.assertFalse(current_card_record['ready'])
            self.assertIn(current_request_identifier,current_preview_text)
            self.assertIn('자동 재접수하지 않습니다',current_notice_text)
            current_state_value,current_status_text=hermes_agent_app.read_conversation_service_status(current_card_record,current_session_identifier,current_source_job,'video_resume')
            self.assertEqual(current_state_value,'unknown')
            self.assertIn('자동 재접수하지 않습니다',current_status_text)
            current_history_text=operations_history_app.read_operations_audio_resume_receipt(current_request_identifier,'dwpose')
            self.assertIn(current_target_job,current_history_text)
            self.assertIn('자동 재요청하지 마세요',current_history_text)
            current_receipt_record['job_id']='2026-11-20_01-00-00-aaaaaaaa'
            with self.assertRaises(gr.Error):
                hermes_agent_app.read_conversation_service_status(current_card_record,current_session_identifier,current_source_job,'video_resume')
            self.assertIn('확인할 수 없습니다',operations_history_app.read_operations_audio_resume_receipt(current_request_identifier,'dwpose'))

    def test_conversation_video_resume_routes_reviews_and_checks_receipt(self):
        import json
        current_session_identifier='a'*32
        current_source_job='2026-11-20_00-00-00-12345678'
        current_target_job='2026-11-20_01-00-00-87654321'
        current_proposal_value={'service':'wan22-vace','job_id':current_target_job,'expected_resume_fingerprint':'b'*64}
        current_answer_text='HERMES_VIDEO_RESUME_PROPOSAL\n'+json.dumps(current_proposal_value)+'\nEND_HERMES_VIDEO_RESUME_PROPOSAL'
        current_job_record={'job':{'status':{'status':'completed'},'final_response':current_answer_text,'final_response_truncated':False}}
        current_receipt_value={}
        current_submit_values=[]
        def respond_video_gateway(current_service_name,current_command_name,current_payload_value):
            if current_command_name=='hermes-video-resume-proposal':return {'job_id':current_source_job,'proposal':current_proposal_value}
            if current_command_name=='hermes-video-resume-receipt':return {**current_receipt_value,'request_id':current_payload_value['request_id']} if current_receipt_value else {'request_id':current_payload_value['request_id'],'state':'not_found'}
            if current_command_name=='hermes-video-resume-preview':return {**current_proposal_value,'status':'failed','resume_availability':'available'}
            if current_command_name=='hermes-video-resume-submit':
                current_submit_values.append(current_payload_value)
                current_receipt_value.update({**current_payload_value,'state':'accepted'})
                return current_receipt_value
            if current_command_name=='hermes-generator-source-history':return {'service':'wan22-vace','records':[{'id':current_target_job,'recorded_status':'completed','status_source':'job'}]}
            raise AssertionError(current_command_name)
        with patch.object(hermes_agent_app,'find_conversation_session_job',return_value=current_job_record),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=respond_video_gateway):
            current_route_value=hermes_agent_app.route_conversation_proposal(current_session_identifier,current_source_job)
            self.assertEqual(current_route_value[4],'video_resume')
            self.assertIn('영상 재개 제안',hermes_agent_app.format_hermes_conversation_answer(current_answer_text))
            current_card_value,_,_=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'video_resume')
            self.assertTrue(current_card_value['ready'])
            current_finished_value,current_notice_text=hermes_agent_app.submit_conversation_service_review(current_card_value,current_session_identifier,current_source_job,'video_resume')
            self.assertFalse(current_finished_value['ready'])
            self.assertIn('대기열에 접수',current_notice_text)
            self.assertEqual(len(current_submit_values),1)
            current_reopened_value,_,_=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'video_resume')
            self.assertFalse(current_reopened_value['ready'])
            current_status_value,current_status_text=hermes_agent_app.read_conversation_service_status(current_reopened_value,current_session_identifier,current_source_job,'video_resume')
            self.assertEqual(current_status_value,'accepted')
            self.assertIn('완료 기록',current_status_text)

    def test_conversation_fun_resume_routes_reviews_and_checks_receipt(self):
        import json
        current_session_identifier='a'*32
        current_source_job='2026-11-20_00-00-00-12345678'
        current_target_job='2026-11-20_01-00-00-87654321'
        current_proposal_value={'service':'wan22-fun-control','job_id':current_target_job,'expected_resume_fingerprint':'b'*64}
        current_answer_text='HERMES_VIDEO_RESUME_PROPOSAL\n'+json.dumps(current_proposal_value)+'\nEND_HERMES_VIDEO_RESUME_PROPOSAL'
        current_job_record={'job':{'status':{'status':'completed'},'final_response':current_answer_text,'final_response_truncated':False}}
        current_receipt_value={}
        current_submit_values=[]
        def respond_video_gateway(current_service_name,current_command_name,current_payload_value):
            if current_command_name=='hermes-video-resume-proposal':return {'job_id':current_source_job,'proposal':current_proposal_value}
            if current_command_name=='hermes-video-resume-receipt':return {**current_receipt_value,'request_id':current_payload_value['request_id']} if current_receipt_value else {'request_id':current_payload_value['request_id'],'state':'not_found'}
            if current_command_name=='hermes-video-resume-preview':return {**current_proposal_value,'status':'failed','resume_availability':'available'}
            if current_command_name=='hermes-video-resume-submit':
                current_submit_values.append(current_payload_value)
                current_receipt_value.update({**current_payload_value,'state':'accepted'})
                return current_receipt_value
            if current_command_name=='hermes-generator-source-history':return {'service':'wan22-fun-control','records':[{'id':current_target_job,'recorded_status':'completed','status_source':'job'}]}
            raise AssertionError(current_command_name)
        with patch.object(hermes_agent_app,'find_conversation_session_job',return_value=current_job_record),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=respond_video_gateway):
            current_route_value=hermes_agent_app.route_conversation_proposal(current_session_identifier,current_source_job)
            self.assertEqual(current_route_value[4],'video_resume')
            self.assertIn('영상 재개 제안',hermes_agent_app.format_hermes_conversation_answer(current_answer_text))
            current_card_value,_,_=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'video_resume')
            self.assertTrue(current_card_value['ready'])
            current_finished_value,current_notice_text=hermes_agent_app.submit_conversation_service_review(current_card_value,current_session_identifier,current_source_job,'video_resume')
            self.assertFalse(current_finished_value['ready'])
            self.assertIn('대기열에 접수',current_notice_text)
            self.assertEqual(len(current_submit_values),1)
            current_reopened_value,_,_=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'video_resume')
            self.assertFalse(current_reopened_value['ready'])
            current_status_value,current_status_text=hermes_agent_app.read_conversation_service_status(current_reopened_value,current_session_identifier,current_source_job,'video_resume')
            self.assertEqual(current_status_value,'accepted')
            self.assertIn('완료 기록',current_status_text)

    def test_conversation_flux_resume_routes_reviews_and_checks_receipt(self):
        import json
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_source_job='2026-11-20_00-00-00-12345678'
        current_target_job='2026-11-20_01-00-00-87654321'
        current_fingerprint='b'*64
        current_proposal_value={'service':'flux-character','job_id':current_target_job,'expected_resume_fingerprint':current_fingerprint}
        current_answer_text='HERMES_FLUX_RESUME_PROPOSAL\n'+json.dumps(current_proposal_value)+'\nEND_HERMES_FLUX_RESUME_PROPOSAL'
        current_job_record={'job':{'status':{'status':'completed'},'final_response':current_answer_text,'final_response_truncated':False}}
        current_receipt_value={}
        current_submit_values=[]
        def respond_flux_gateway(current_service_name,current_command_name,current_payload_value):
            if current_command_name=='hermes-flux-resume-proposal':return {'job_id':current_source_job,'proposal':current_proposal_value}
            if current_command_name=='hermes-flux-resume-receipt':return {**current_receipt_value,'request_id':current_payload_value['request_id']} if current_receipt_value else {'request_id':current_payload_value['request_id'],'state':'not_found'}
            if current_command_name=='hermes-flux-resume-preview':return {**current_proposal_value,'status':'failed','resume_availability':'available'}
            if current_command_name=='hermes-flux-resume-submit':
                current_submit_values.append(current_payload_value)
                current_receipt_value.update({**current_payload_value,'state':'accepted'})
                return current_receipt_value
            if current_command_name=='hermes-generator-source-history':return {'service':'flux-character','records':[{'id':current_target_job,'recorded_status':'completed','status_source':'job'}]}
            raise AssertionError(current_command_name)
        with patch.object(hermes_agent_app,'find_conversation_session_job',return_value=current_job_record),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=respond_flux_gateway):
            current_route_value=hermes_agent_app.route_conversation_proposal(current_session_identifier,current_source_job)
            self.assertEqual(current_route_value[4],'flux_resume')
            self.assertIn('FLUX 재개 제안',hermes_agent_app.format_hermes_conversation_answer(current_answer_text))
            current_card_value,_,_=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'flux_resume')
            self.assertTrue(current_card_value['ready'])
            current_page_value={'service':'flux-character','snapshot':'a'*64}
            current_rows_value=[[current_target_job,'failed','job','','']]
            with patch.object(operations_history_app,'execute_remote_management_command',side_effect=lambda service,command,payload: {**current_proposal_value,'status':'failed','resume_availability':'available'} if command=='hermes-flux-resume-preview' else {'request_id':payload['request_id'],'state':'not_found'}):
                current_history_value,_,_=operations_history_app.prepare_operations_audio_resume('flux-character',current_target_job,current_page_value,current_rows_value)
            self.assertEqual(current_history_value['request_id'],current_card_value['review']['request_id'])
            current_finished_value,current_notice_text=hermes_agent_app.submit_conversation_service_review(current_card_value,current_session_identifier,current_source_job,'flux_resume')
            self.assertFalse(current_finished_value['ready'])
            self.assertIn('대기열에 접수',current_notice_text)
            self.assertEqual(len(current_submit_values),1)
            current_reopened_value,_,_=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'flux_resume')
            self.assertFalse(current_reopened_value['ready'])
            current_status_value,current_status_text=hermes_agent_app.read_conversation_service_status(current_reopened_value,current_session_identifier,current_source_job,'flux_resume')
            self.assertEqual(current_status_value,'accepted')
            self.assertIn('완료 기록',current_status_text)

    def test_flux_conversation_resume_rejects_changed_review_and_unknown_receipt(self):
        current_session_identifier='a'*32
        current_source_job='2026-11-20_00-00-00-12345678'
        current_target_job='2026-11-20_01-00-00-87654321'
        current_proposal_value={'service':'flux-character','job_id':current_target_job,'expected_resume_fingerprint':'b'*64}
        current_preview_value={**current_proposal_value,'status':'failed','resume_availability':'available'}
        current_receipt_value={}
        current_submit_values=[]
        def respond_flux_gateway(current_service_name,current_command_name,current_payload_value):
            if current_command_name=='hermes-flux-resume-proposal':return {'job_id':current_source_job,'proposal':current_proposal_value}
            if current_command_name=='hermes-flux-resume-receipt':return {**current_receipt_value,'request_id':current_payload_value['request_id']} if current_receipt_value else {'request_id':current_payload_value['request_id'],'state':'not_found'}
            if current_command_name=='hermes-flux-resume-preview':return current_preview_value
            if current_command_name=='hermes-flux-resume-submit':current_submit_values.append(current_payload_value);raise AssertionError('실제 접수 금지')
            raise AssertionError(current_command_name)
        with patch.object(hermes_agent_app,'find_conversation_session_job'),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=respond_flux_gateway):
            current_card_value,_,_=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'flux_resume')
            self.assertTrue(current_card_value['ready'])
            current_preview_value['expected_resume_fingerprint']='c'*64
            with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_service_review(current_card_value,current_session_identifier,current_source_job,'flux_resume')
            self.assertFalse(current_submit_values)
            current_preview_value['expected_resume_fingerprint']='b'*64
            current_preview_value['resume_availability']='download_running'
            current_card_busy,_,current_notice_text=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'flux_resume')
            self.assertFalse(current_card_busy['ready'])
            self.assertIn('모델 준비',current_notice_text)
            current_preview_value['resume_availability']='available'
            current_receipt_value.update({'state':'unknown','service':'flux-character','job_id':current_target_job,'expected_resume_fingerprint':'b'*64})
            current_card_unknown,_,current_notice_text=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'flux_resume')
            self.assertFalse(current_card_unknown['ready'])
            self.assertIn('자동 재접수하지 않습니다',current_notice_text)
            with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_service_review(current_card_unknown,current_session_identifier,current_source_job,'flux_resume')
            self.assertFalse(current_submit_values)

    def test_conversation_routes_kimodo_resume_proposal(self):
        import json
        current_session_identifier='a'*32
        current_source_job='2026-11-20_00-00-00-12345678'
        current_target_job='2026-11-20_01-00-00-87654321'
        current_answer_text='HERMES_KIMODO_RESUME_PROPOSAL\n'+json.dumps({'job_id':current_target_job,'expected_resume_fingerprint':'b'*64})+'\nEND_HERMES_KIMODO_RESUME_PROPOSAL'
        current_job_record={'job':{'status':{'status':'completed'},'final_response':current_answer_text,'final_response_truncated':False}}
        with patch.object(hermes_agent_app,'find_conversation_session_job',return_value=current_job_record):
            current_route_value=hermes_agent_app.route_conversation_proposal(current_session_identifier,current_source_job)
            self.assertEqual(current_route_value[4],'kimodo_resume')
            self.assertEqual(current_route_value[6]['area'],'service')
            self.assertIn('Kimodo 재개 제안',hermes_agent_app.format_hermes_conversation_answer(current_answer_text))

    def test_operations_session_kimodo_resume_links_shared_receipt(self):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_source_job='2026-11-20_00-00-00-12345678'
        current_target_job='2026-11-20_01-00-00-87654321'
        current_fingerprint='b'*64
        current_request_identifier='kimodo_resume_'+hashlib.sha256(('kimodo\0'+current_target_job+'\0'+current_fingerprint).encode()).hexdigest()
        current_receipt={'request_id':current_request_identifier,'service':'kimodo','job_id':current_target_job,'expected_resume_fingerprint':current_fingerprint,'state':'accepted'}
        def kimodo_history_gateway(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'messages':[{'job_id':current_source_job,'session_job_unique':True,'job':{'status':{'status':'completed'},'final_response':'HERMES_KIMODO_RESUME_PROPOSAL'}}],'truncated':False}
            if current_command_name=='hermes-kimodo-resume-proposal':return {'id':'a'*32,'job_id':current_source_job,'proposal':{'job_id':current_target_job,'expected_resume_fingerprint':current_fingerprint}}
            if current_command_name=='hermes-kimodo-resume-receipt':return current_receipt
            if current_command_name=='hermes-management-status':return {'queue':{'status':'available','jobs':[]},'reservations':{'status':'available','records':[],'truncated':False}}
            raise AssertionError(current_command_name)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=kimodo_history_gateway):
            current_rows_value,_=operations_history_app.read_operations_session_receipts(current_session_identifier)
            self.assertEqual(current_rows_value[0][:5],[current_source_job,'kimodo',current_request_identifier,'Kimodo 재개 · 접수 기록',current_target_job])
            current_receipt['job_id']='2026-11-20_01-00-00-aaaaaaaa'
            current_rows_value,_=operations_history_app.read_operations_session_receipts(current_session_identifier)
            self.assertEqual(current_rows_value[0][3],'제안 또는 접수 조회 불가')

    def test_operations_session_flux_resume_links_shared_receipt(self):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_source_job='2026-11-20_00-00-00-12345678'
        current_target_job='2026-11-20_01-00-00-87654321'
        current_fingerprint='b'*64
        current_request_identifier='flux_resume_'+hashlib.sha256(('flux-character\0'+current_target_job+'\0'+current_fingerprint).encode()).hexdigest()
        current_receipt={'request_id':current_request_identifier,'service':'flux-character','job_id':current_target_job,'expected_resume_fingerprint':current_fingerprint,'state':'accepted'}
        def flux_history_gateway(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'messages':[{'job_id':current_source_job,'session_job_unique':True,'job':{'status':{'status':'completed'},'final_response':'HERMES_FLUX_RESUME_PROPOSAL'}}],'truncated':False}
            if current_command_name=='hermes-flux-resume-proposal':return {'id':'a'*32,'job_id':current_source_job,'proposal':{'service':'flux-character','job_id':current_target_job,'expected_resume_fingerprint':current_fingerprint}}
            if current_command_name=='hermes-flux-resume-receipt':return current_receipt
            if current_command_name=='hermes-management-status':return {'queue':{'status':'available','jobs':[{'service':'flux-image','source_service':'flux-character','id':current_target_job}]},'reservations':{'status':'available','records':[],'truncated':False}}
            raise AssertionError(current_command_name)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=flux_history_gateway):
            current_rows_value,_=operations_history_app.read_operations_session_receipts(current_session_identifier)
            self.assertEqual(current_rows_value[0][:5],[current_source_job,'flux-character',current_request_identifier,'FLUX 재개 · 접수 기록',current_target_job])
            self.assertIn('대기 기록 확인',current_rows_value[0][5])
            current_receipt['job_id']='2026-11-20_01-00-00-aaaaaaaa'
            current_rows_value,_=operations_history_app.read_operations_session_receipts(current_session_identifier)
            self.assertEqual(current_rows_value[0][3],'제안 또는 접수 조회 불가')

    def test_operations_video_resume_links_session_and_queue(self):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_source_job='2026-11-20_00-00-00-12345678'
        current_target_job='2026-11-20_01-00-00-87654321'
        current_fingerprint='b'*64
        current_request_identifier='video_resume_'+hashlib.sha256(('wan22-vace\0'+current_target_job+'\0'+current_fingerprint).encode()).hexdigest()
        current_proposal_value={'service':'wan22-vace','job_id':current_target_job,'expected_resume_fingerprint':current_fingerprint}
        current_receipt_value={'request_id':current_request_identifier,**current_proposal_value,'state':'accepted'}
        def video_history_gateway(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'messages':[{'job_id':current_source_job,'session_job_unique':True,'job':{'status':{'status':'completed'},'final_response':'HERMES_VIDEO_RESUME_PROPOSAL'}}],'truncated':False}
            if current_command_name=='hermes-video-resume-proposal':return {'id':'a'*32,'job_id':current_source_job,'proposal':current_proposal_value}
            if current_command_name=='hermes-video-resume-receipt':return current_receipt_value
            if current_command_name=='hermes-management-status':return {'queue':{'status':'available','jobs':[{'service':'image','source_service':'wan22-vace','id':current_target_job}]},'reservations':{'status':'available','records':[],'truncated':False}}
            raise AssertionError(current_command_name)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=video_history_gateway):
            current_rows_value,_=operations_history_app.read_operations_session_receipts(current_session_identifier)
            self.assertEqual(current_rows_value[0][:5],[current_source_job,'wan22-vace',current_request_identifier,'영상 재개 · 접수 기록',current_target_job])
            self.assertIn('대기 기록 확인',current_rows_value[0][5])
        current_page_value={'service':'wan22-vace','snapshot':'a'*64}
        current_source_rows=[[current_target_job,'failed','job','','']]
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=lambda service,command,payload: {**current_proposal_value,'status':'failed','resume_availability':'available'} if command=='hermes-video-resume-preview' else {'request_id':payload['request_id'],'state':'not_found'}):
            current_review_value,_,current_history_identifier=operations_history_app.prepare_operations_audio_resume('wan22-vace',current_target_job,current_page_value,current_source_rows)
        self.assertEqual(current_history_identifier,current_request_identifier)
        self.assertEqual(current_review_value['request_id'],current_request_identifier)

    def test_unconfirmed_resume_message_accepts_only_valid_existing_identifier(self):
        from tools.review.ui.gradio.hermes_agent_app import describe_unconfirmed_resume_error
        current_error_value=ValueError('관리 API 오류 (400): 같은 작업에 결과가 확인되지 않은 기존 접수가 있습니다 (접수 ID: request_first). 해당 접수와 원 서비스 상태를 확인하세요. 자동 재접수하지 마세요.')
        self.assertIn('request_first',describe_unconfirmed_resume_error(current_error_value))
        self.assertIsNone(describe_unconfirmed_resume_error(ValueError(str(current_error_value).replace('request_first','../other'))))
        self.assertIsNone(describe_unconfirmed_resume_error(OSError(str(current_error_value))))

    def test_unconfirmed_resume_id_reaches_conversation_and_history(self):
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_source_identifier='2026-11-20_00-00-00-12345678'
        current_target_identifier='2026-11-20_01-00-00-87654321'
        current_page_snapshot='a'*64
        current_review_record={'request_id':'request_current','job_id':current_target_identifier,'expected_resume_fingerprint':'b'*64}
        current_card_record={'ready':True,'kind':'kimodo_resume','session_id':current_session_identifier,'source_job_id':current_source_identifier,'service':'kimodo','review':current_review_record}
        current_error_value=ValueError('관리 API 오류 (400): 같은 작업에 결과가 확인되지 않은 기존 접수가 있습니다 (접수 ID: request_first). 해당 접수와 원 서비스 상태를 확인하세요. 자동 재접수하지 마세요.')
        with patch.object(hermes_agent_app,'prepare_conversation_service_review',return_value=(current_card_record,'','')),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_error_value):
            current_result_value,current_notice_text=hermes_agent_app.submit_conversation_service_review(current_card_record,current_session_identifier,current_source_identifier,'kimodo_resume')
            self.assertFalse(current_result_value['ready'])
            self.assertIn('request_first',current_notice_text)
        current_page_value={'service':'kimodo','snapshot':current_page_snapshot}
        current_rows_value=[[current_target_identifier,'failed','job','','']]
        current_history_request={**current_review_record,'service':'kimodo','history_snapshot':current_page_snapshot}
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=current_error_value):
            current_result_value,current_notice_text=operations_history_app.submit_operations_audio_resume(current_history_request,'kimodo',current_target_identifier,current_page_value,current_rows_value)
            self.assertIsNone(current_result_value)
            self.assertIn('request_first',current_notice_text)

    def test_conversation_kimodo_resume_reviews_submits_and_reopens_receipt(self):
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_source_job='2026-11-20_00-00-00-12345678'
        current_target_job='2026-11-20_01-00-00-87654321'
        current_fingerprint='b'*64
        current_proposal={'job_id':current_target_job,'expected_resume_fingerprint':current_fingerprint}
        current_existing_receipt={}
        current_submit_calls=[]
        def kimodo_resume_gateway(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-kimodo-resume-proposal':return {'job_id':current_source_job,'proposal':current_proposal}
            if current_command_name=='hermes-kimodo-resume-receipt':return {**current_existing_receipt,'request_id':current_payload_record['request_id']} if current_existing_receipt else {'state':'not_found','request_id':current_payload_record['request_id']}
            if current_command_name=='hermes-kimodo-resume-preview':return {'service':'kimodo','job_id':current_target_job,'status':'failed','expected_resume_fingerprint':current_fingerprint,'resume_availability':'available'}
            if current_command_name=='hermes-generator-source-history':return {'service':'kimodo','records':[{'id':current_target_job,'recorded_status':'completed','status_source':'job'}]}
            if current_command_name=='hermes-kimodo-resume-submit':
                current_submit_calls.append(current_payload_record)
                current_existing_receipt.update({**current_payload_record,'service':'kimodo','state':'accepted'})
                return current_existing_receipt
            raise AssertionError(current_command_name)
        with patch.object(hermes_agent_app,'find_conversation_session_job'),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=kimodo_resume_gateway) as current_gateway_mock:
            current_card_value,current_preview_text,_=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'kimodo_resume')
            self.assertTrue(current_card_value['ready'])
            self.assertIn(current_target_job,current_preview_text)
            current_history_page={'service':'kimodo','snapshot':'a'*64}
            current_history_rows=[[current_target_job,'failed','job','','']]
            with patch.object(operations_history_app,'execute_remote_management_command',side_effect=lambda service,command,payload: {'service':'kimodo','job_id':current_target_job,'status':'failed','expected_resume_fingerprint':current_fingerprint,'resume_availability':'available'} if command=='hermes-kimodo-resume-preview' else {'request_id':payload['request_id'],'state':'not_found'}):
                current_history_record,_,_=operations_history_app.prepare_operations_audio_resume('kimodo',current_target_job,current_history_page,current_history_rows)
            self.assertEqual(current_history_record['request_id'],current_card_value['review']['request_id'])
            current_finished_card,current_notice_text=hermes_agent_app.submit_conversation_service_review(current_card_value,current_session_identifier,current_source_job,'kimodo_resume')
            self.assertFalse(current_finished_card['ready'])
            self.assertIn('대기열에 접수',current_notice_text)
            self.assertEqual(len(current_submit_calls),1)
            current_gateway_mock.reset_mock()
            current_reopened_card,_,current_reopened_notice=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'kimodo_resume')
            self.assertFalse(current_reopened_card['ready'])
            self.assertIn('기존 재개 접수',current_reopened_notice)
            self.assertNotIn('hermes-kimodo-resume-preview',[item.args[1] for item in current_gateway_mock.call_args_list])
            current_status_value,current_status_text=hermes_agent_app.read_conversation_service_status(current_reopened_card,current_session_identifier,current_source_job,'kimodo_resume')
            self.assertEqual(current_status_value,'accepted')
            self.assertIn('완료 기록',current_status_text)
            self.assertIn('작업 상태 파일',current_status_text)
            self.assertIn('Kimodo 작업 이력과 결과 열기',current_status_text)

    def test_conversation_kimodo_resume_blocks_changed_or_busy_target(self):
        current_session_identifier='a'*32
        current_source_job='2026-11-20_00-00-00-12345678'
        current_target_job='2026-11-20_01-00-00-87654321'
        current_proposal={'job_id':current_target_job,'expected_resume_fingerprint':'b'*64}
        current_preview={'service':'kimodo','job_id':current_target_job,'status':'failed','expected_resume_fingerprint':'b'*64,'resume_availability':'download_running'}
        def kimodo_resume_gateway(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-kimodo-resume-proposal':return {'job_id':current_source_job,'proposal':current_proposal}
            if current_command_name=='hermes-kimodo-resume-receipt':return {'request_id':current_payload_record['request_id'],'state':'not_found'}
            if current_command_name=='hermes-kimodo-resume-preview':return current_preview
            raise AssertionError(current_command_name)
        with patch.object(hermes_agent_app,'find_conversation_session_job'),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=kimodo_resume_gateway):
            current_card_value,_,current_notice_text=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'kimodo_resume')
            self.assertFalse(current_card_value['ready'])
            self.assertIn('모델 준비',current_notice_text)
            current_preview['expected_resume_fingerprint']='c'*64
            with self.assertRaises(gr.Error):hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'kimodo_resume')

    def test_flux_history_resume_reviews_submits_and_reads_receipt(self):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_page_value={'service':'flux-character','snapshot':'a'*64}
        current_rows_value=[[current_job_identifier,'실패 기록','job','','']]
        current_preview_value={'service':'flux-character','job_id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'b'*64,'resume_availability':'available'}
        current_submissions=[]
        def respond_flux_gateway(current_service_name,current_command_name,current_payload_value):
            if current_command_name=='hermes-flux-resume-preview':return current_preview_value
            if current_command_name=='hermes-flux-resume-receipt':
                return {**current_submissions[-1],'state':'accepted'} if current_submissions else {'request_id':current_payload_value['request_id'],'state':'not_found'}
            if current_command_name=='hermes-flux-resume-submit':
                current_submissions.append(current_payload_value)
                return {**current_payload_value,'state':'accepted'}
            raise AssertionError(current_command_name)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=respond_flux_gateway):
            current_request_value,current_notice_text,current_identifier=operations_history_app.prepare_operations_audio_resume('flux-character',current_job_identifier,current_page_value,current_rows_value)
            self.assertTrue(current_identifier.startswith('flux_resume_'))
            self.assertIn('재개 검토',current_notice_text)
            self.assertFalse(current_submissions)
            self.assertIn('바뀌었습니다',operations_history_app.submit_operations_audio_resume(current_request_value,'flux-character',current_job_identifier,{**current_page_value,'snapshot':'c'*64},current_rows_value)[1])
            self.assertFalse(current_submissions)
            self.assertIn('대기열에 접수',operations_history_app.submit_operations_audio_resume(current_request_value,'flux-character',current_job_identifier,current_page_value,current_rows_value)[1])
            self.assertEqual(len(current_submissions),1)
            self.assertEqual(current_submissions[0]['request_id'],current_identifier)
            self.assertIn('대기열 접수 기록',operations_history_app.read_operations_audio_resume_receipt(current_identifier,'flux-character'))
            self.assertIn('대기열 접수 기록',operations_history_app.read_operations_audio_resume_receipt(current_identifier))
        current_preview_value['resume_availability']='unknown'
        with patch.object(operations_history_app,'execute_remote_management_command',return_value=current_preview_value) as current_gateway_mock:
            current_request_value,current_notice_text,_=operations_history_app.prepare_operations_audio_resume('flux-character',current_job_identifier,current_page_value,current_rows_value)
            self.assertIsNone(current_request_value)
            self.assertIn('충돌 상태를 확인할 수 없습니다',current_notice_text)
            current_gateway_mock.assert_called_once()

    def test_operations_fun_resume_reviews_and_submits_matching_job(self):
        from tools.review.ui.gradio import operations_history_app
        current_service_name = 'wan22-fun-control'
        current_job_identifier = '2026-11-20_00-00-00-12345678'
        current_page_value = {'service':current_service_name,'snapshot':'a'*64}
        current_rows_value = [[current_job_identifier,'failed','job','','']]
        current_preview_value = {'service':current_service_name,'job_id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'b'*64,'resume_availability':'available'}
        current_commands_seen = []
        def mock_fun_gateway(current_target_name,current_command_name,current_payload_record):
            current_commands_seen.append(current_command_name)
            if current_command_name == 'hermes-video-resume-preview': return current_preview_value
            if current_command_name == 'hermes-video-resume-receipt': return {'request_id':current_payload_record['request_id'],'state':'not_found'}
            if current_command_name == 'hermes-video-resume-submit': return {**current_payload_record,'state':'accepted'}
            raise AssertionError(current_command_name)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=mock_fun_gateway):
            current_request_record,_,current_request_identifier = operations_history_app.prepare_operations_audio_resume(current_service_name,current_job_identifier,current_page_value,current_rows_value)
            self.assertTrue(current_request_identifier.startswith('video_resume_'))
            self.assertEqual(current_request_record['service'],current_service_name)
            _,current_notice_text = operations_history_app.submit_operations_audio_resume(current_request_record,current_service_name,current_job_identifier,current_page_value,current_rows_value)
            self.assertIn('대기열에 접수',current_notice_text)
        self.assertEqual(current_commands_seen,['hermes-video-resume-preview','hermes-video-resume-receipt','hermes-video-resume-submit'])

    def test_operations_kimodo_resume_uses_reviewed_receipt_and_selection(self):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_page_value={'service':'kimodo','snapshot':'a'*64}
        current_rows_value=[[current_job_identifier,'failed','job','','']]
        current_preview_value={'service':'kimodo','job_id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'b'*64,'resume_availability':'available'}
        current_submissions=[]
        def kimodo_resume_gateway(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-kimodo-resume-preview':return current_preview_value
            if current_command_name=='hermes-kimodo-resume-receipt':return {'request_id':current_payload_record['request_id'],'state':'not_found'}
            if current_command_name=='hermes-kimodo-resume-submit':
                current_submissions.append(current_payload_record)
                return {**current_payload_record,'service':'kimodo','state':'accepted'}
            raise AssertionError(current_command_name)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=kimodo_resume_gateway):
            current_request_value,current_notice_text,current_identifier=operations_history_app.prepare_operations_audio_resume('kimodo',current_job_identifier,current_page_value,current_rows_value)
            self.assertTrue(current_identifier.startswith('kimodo_resume_'))
            self.assertEqual(current_request_value['expected_resume_fingerprint'],'b'*64)
            self.assertFalse(current_submissions)
            self.assertIn('바뀌었습니다',operations_history_app.submit_operations_audio_resume(current_request_value,'kimodo',current_job_identifier,{**current_page_value,'snapshot':'c'*64},current_rows_value)[1])
            self.assertFalse(current_submissions)
            self.assertIn('대기열에 접수',operations_history_app.submit_operations_audio_resume(current_request_value,'kimodo',current_job_identifier,current_page_value,current_rows_value)[1])
            self.assertEqual(current_submissions,[{'request_id':current_identifier,'job_id':current_job_identifier,'expected_resume_fingerprint':'b'*64}])

    def test_operations_kimodo_resume_preview_blocks_unconfirmed_preparation(self):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_page_value={'service':'kimodo','snapshot':'a'*64}
        current_rows_value=[[current_job_identifier,'failed','job','','']]
        for current_availability_value in ('download_running','unknown'):
            current_preview_value={'service':'kimodo','job_id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'b'*64,'resume_availability':current_availability_value}
            with self.subTest(current_availability_value=current_availability_value),patch.object(operations_history_app,'execute_remote_management_command',return_value=current_preview_value) as current_gateway_mock:
                current_request_value,current_notice_text,current_identifier=operations_history_app.prepare_operations_audio_resume('kimodo',current_job_identifier,current_page_value,current_rows_value)
                self.assertIsNone(current_request_value)
                self.assertEqual(current_identifier,'')
                self.assertIn('확인' if current_availability_value=='unknown' else '다운로드',current_notice_text)
                current_gateway_mock.assert_called_once_with('hermes-agent','hermes-kimodo-resume-preview',{'job_id':current_job_identifier})

    def test_operations_kimodo_resume_receipt_requires_matching_identifier(self):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_fingerprint_value='b'*64
        current_request_identifier='kimodo_resume_'+hashlib.sha256(('kimodo\0'+current_job_identifier+'\0'+current_fingerprint_value).encode()).hexdigest()
        current_receipt_value={'request_id':current_request_identifier,'service':'kimodo','job_id':current_job_identifier,'expected_resume_fingerprint':current_fingerprint_value,'state':'accepted'}
        with patch.object(operations_history_app,'execute_remote_management_command',return_value=current_receipt_value) as current_gateway_mock:
            self.assertIn('대기열 접수 기록',operations_history_app.read_operations_audio_resume_receipt(current_request_identifier))
            current_gateway_mock.assert_called_once_with('hermes-agent','hermes-kimodo-resume-receipt',{'request_id':current_request_identifier})
            current_receipt_value['service']='music-heartmula'
            self.assertIn('확인할 수 없습니다',operations_history_app.read_operations_audio_resume_receipt(current_request_identifier))

    def test_operations_model_preparation_receipt_checks_identity_without_assuming_job(self):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_request_identifier='chat_'+hashlib.sha256((current_session_identifier+':'+current_job_identifier+':model_preparation').encode()).hexdigest()
        current_receipt_record={'service':'flux-image','request_id':current_request_identifier,'state':'accepted'}
        def model_history_gateway(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'messages':[{'job_id':current_job_identifier,'session_job_unique':True,'job':{'status':{'status':'completed'},'final_response':'HERMES_MODEL_PREPARATION_PROPOSAL'}}],'truncated':False}
            if current_command_name=='hermes-model-preparation-proposal':return {'id':'a'*32,'job_id':current_job_identifier,'proposal':{'service':'flux-image'}}
            if current_command_name=='hermes-model-prepare-status':return current_receipt_record
            raise AssertionError(current_command_name)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=model_history_gateway) as current_gateway_mock:
            current_rows_value,_=operations_history_app.read_operations_session_receipts(current_session_identifier)
            self.assertEqual(current_rows_value[0][:5],[current_job_identifier,'flux-image',current_request_identifier,'모델 준비 · 접수 기록','미확인'])
            self.assertEqual(current_rows_value[0][5:7],['작업 ID 미확인','작업 ID 미확인'])
            self.assertNotIn('hermes-management-status',[item.args[1] for item in current_gateway_mock.call_args_list])
            current_receipt_record['service']='kimodo'
            current_rows_value,_=operations_history_app.read_operations_session_receipts(current_session_identifier)
            self.assertEqual(current_rows_value[0][3],'제안 또는 접수 조회 불가')

    def test_operations_model_preparation_checks_real_queue_identity_when_job_is_present(self):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_source_job='2026-11-20_00-00-00-12345678'
        current_target_job='2026-11-20_01-00-00-87654321'
        current_request_identifier='chat_'+hashlib.sha256((current_session_identifier+':'+current_source_job+':model_preparation').encode()).hexdigest()
        def model_queue_gateway(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'messages':[{'job_id':current_source_job,'session_job_unique':True,'job':{'status':{'status':'completed'},'final_response':'HERMES_MODEL_PREPARATION_PROPOSAL'}}],'truncated':False}
            if current_command_name=='hermes-model-preparation-proposal':return {'id':'a'*32,'job_id':current_source_job,'proposal':{'service':'flux-image'}}
            if current_command_name=='hermes-model-prepare-status':return {'service':'flux-image','request_id':current_request_identifier,'state':'accepted','job_id':current_target_job}
            if current_command_name=='hermes-management-status':return {'queue':{'status':'available','jobs':[]},'reservations':{'status':'available','records':[],'truncated':False},'queried_at':'mock'}
            raise AssertionError(current_command_name)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=model_queue_gateway) as current_gateway_mock:
            current_rows_value,_=operations_history_app.read_operations_session_receipts(current_session_identifier)
            self.assertEqual(current_rows_value[0][3:5],['모델 준비 · 접수 기록',current_target_job])
            self.assertNotEqual(current_rows_value[0][5],'작업 ID 미확인')
            self.assertIn('hermes-management-status',[item.args[1] for item in current_gateway_mock.call_args_list])

    def test_conversation_routes_model_preparation_proposal(self):
        current_session_identifier='a'*32
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_answer_text='HERMES_MODEL_PREPARATION_PROPOSAL\n{"service":"flux-image"}\nEND_HERMES_MODEL_PREPARATION_PROPOSAL'
        current_job_record={'job':{'status':{'status':'completed'},'final_response':current_answer_text,'final_response_truncated':False}}
        with patch.object(hermes_agent_app,'find_conversation_session_job',return_value=current_job_record):
            current_routing_value=hermes_agent_app.route_conversation_proposal(current_session_identifier,current_job_identifier)
            self.assertEqual(current_routing_value[4],'model_preparation')
            self.assertEqual(current_routing_value[6]['kind'],'model_preparation')
            self.assertEqual(current_routing_value[6]['area'],'service')
            self.assertIn('모델 준비 제안',hermes_agent_app.format_hermes_conversation_answer(current_answer_text))

    def test_conversation_model_preparation_review_submit_and_identity(self):
        current_session_identifier='a'*32
        current_source_job_identifier='2026-11-20_00-00-00-12345678'
        current_readiness_record={'service':'flux-image','status':'available','ready':False,'prepare_allowed':True,'preparation_status':'idle'}
        current_receipt_state={'state':'not_found'}
        current_commands_seen=[]
        def model_preparation_gateway(current_service_name,current_command_name,current_payload_record):
            current_commands_seen.append(current_command_name)
            if current_command_name=='hermes-model-preparation-proposal':return {'job_id':current_source_job_identifier,'proposal':{'service':'flux-image'}}
            if current_command_name=='hermes-model-readiness':return current_readiness_record
            if current_command_name=='hermes-model-prepare-status':return {**current_payload_record,**current_receipt_state}
            if current_command_name=='hermes-model-prepare':return {**current_payload_record,'state':'accepted'}
            raise AssertionError(current_command_name)
        with patch.object(hermes_agent_app,'find_conversation_session_job'),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=model_preparation_gateway):
            current_card_value,current_preview_text,current_notice_text=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job_identifier,'model_preparation')
            self.assertTrue(current_card_value['ready'])
            self.assertIn('flux-image',current_preview_text)
            self.assertNotIn('hermes-model-prepare',current_commands_seen)
            current_finished_card,current_result_text=hermes_agent_app.submit_conversation_service_review(current_card_value,current_session_identifier,current_source_job_identifier,'model_preparation')
            self.assertFalse(current_finished_card['ready'])
            self.assertIn('요청 응답',current_result_text)
            current_receipt_state['state']='unknown'
            current_reopened_card,_,current_notice_text=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job_identifier,'model_preparation')
            self.assertFalse(current_reopened_card['ready'])
            self.assertIn('자동 재접수하지 않습니다',current_notice_text)
            with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_service_review(current_card_value,'b'*32,current_source_job_identifier,'model_preparation')

    def test_conversation_shows_model_use_conflict_failure(self):
        current_session_identifier = 'a' * 32
        current_error_text = 'Hermes 모델이 준비 또는 사용 중이어서 작업을 시작하지 못했습니다.'
        current_session_record = {'id':current_session_identifier, 'message_count':1, 'queried_at':'test', 'truncated':False, 'messages':[{'text':'작업 요청','job_id':'2026-11-20_00-00-00-12345678','job':{'status':{'status':'failed','error':current_error_text},'final_response':None}}]}
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_session_record):
            current_conversation,_,current_timer,_ = hermes_agent_app.read_hermes_session_conversation(current_session_identifier)
        self.assertIn(current_error_text,current_conversation[-1]['content'])
        self.assertFalse(current_timer['active'])

    def test_model_preparation_reports_verified_preflight_block(self):
        current_review_record = {'service':'hermes-model', 'request_id':'request_model_123'}
        current_response_record = {**current_review_record, 'state':'blocked', 'reason':'model_in_use'}
        with patch.object(hermes_agent_app, 'execute_remote_management_command', return_value=current_response_record):
            _, _, current_notice_text = hermes_agent_app.submit_hermes_model_preparation(current_review_record, 'hermes-model', 'request_model_123')
            self.assertIn('접수하지 않았습니다', current_notice_text)
            self.assertIn('다시 검토', current_notice_text)
        with patch.object(hermes_agent_app, 'execute_remote_management_command', return_value={**current_response_record, 'reason':'preparation_unknown'}):
            _, _, current_notice_text = hermes_agent_app.submit_hermes_model_preparation(current_review_record, 'hermes-model', 'request_model_123')
            self.assertIn('상태를 확인할 수 없어', current_notice_text)
        with patch.object(hermes_agent_app, 'execute_remote_management_command', return_value={**current_response_record, 'request_id':'wrong'}):
            _, _, current_notice_text = hermes_agent_app.submit_hermes_model_preparation(current_review_record, 'hermes-model', 'request_model_123')
            self.assertIn('확인할 수 없습니다', current_notice_text)

    def test_model_readiness_button_requires_current_session_and_ready_card(self):
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_card_value={'session_id':'a'*32,'source_job_id':current_job_identifier,'kind':'model_preparation','ready':True}
        self.assertTrue(hermes_agent_app.refresh_conversation_model_readiness(current_card_value,'a'*32,current_job_identifier,'model_preparation')['interactive'])
        for current_card_record,current_session_value,current_kind_value in ((current_card_value,'b'*32,'model_preparation'),({**current_card_value,'ready':False},'a'*32,'model_preparation'),(current_card_value,'a'*32,'writer')):
            self.assertFalse(hermes_agent_app.refresh_conversation_model_readiness(current_card_record,current_session_value,current_job_identifier,current_kind_value)['interactive'])

    def test_model_confirmation_rejects_changed_context_before_submission(self):
        current_card_value={'session_id':'a'*32,'source_job_id':'2026-11-20_00-00-00-12345678','kind':'model_preparation','ready':True,'service':'flux-image','review':{'service':'flux-image','request_id':'request_123'}}
        current_confirmed_value,current_group_value=hermes_agent_app.prepare_conversation_model_confirmation(current_card_value,'a'*32,current_card_value['source_job_id'],'model_preparation')
        self.assertTrue(current_group_value['visible'])
        with patch.object(hermes_agent_app,'submit_conversation_service_review') as current_submit_mock:
            with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_model_confirmation(current_confirmed_value,current_card_value,'b'*32,current_card_value['source_job_id'],'model_preparation')
            current_submit_mock.assert_not_called()

    def test_conversation_model_status_formats_single_consistent_receipt(self):
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_card_value={'session_id':'a'*32,'source_job_id':current_job_identifier,'kind':'model_preparation','service':'flux-image','review':{'service':'flux-image','request_id':'request_123'}}
        current_receipt_value={'state':'accepted','service':'flux-image','request_id':'request_123','message':'접수됨'}
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_receipt_value) as current_gateway_mock,patch.object(hermes_agent_app,'read_hermes_model_readiness_summary',return_value='현재 확인 불가'):
            current_state_value,current_status_text=hermes_agent_app.read_conversation_service_status(current_card_value,'a'*32,current_job_identifier,'model_preparation')
            self.assertEqual(current_state_value,'accepted')
            self.assertIn('접수됨',current_status_text)
            current_gateway_mock.assert_called_once_with('hermes-agent','hermes-model-prepare-status',{'service':'flux-image','request_id':'request_123'})

    def test_conversation_model_preparation_refuses_wrong_receipt_service(self):
        current_job_identifier='2026-11-20_00-00-00-12345678'
        def wrong_model_receipt(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-model-preparation-proposal':return {'job_id':current_job_identifier,'proposal':{'service':'flux-image'}}
            if current_command_name=='hermes-model-readiness':return {'service':'flux-image','status':'available','ready':False,'prepare_allowed':True,'preparation_status':'idle'}
            if current_command_name=='hermes-model-prepare-status':return {'service':'kimodo','request_id':current_payload_record['request_id'],'state':'not_found'}
            raise AssertionError(current_command_name)
        with patch.object(hermes_agent_app,'find_conversation_session_job'),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=wrong_model_receipt):
            current_card_value,_,current_notice_text=hermes_agent_app.prepare_conversation_service_review('a'*32,current_job_identifier,'model_preparation')
            self.assertFalse(current_card_value['ready'])
            self.assertIn('확인할 수 없습니다',current_notice_text)

    def test_city_source_view_rejects_wrong_document_and_clears_result(self):
        current_document_value={'managementId':'config.city-layouts.stonewarm','data':{'cityId':'stonewarm'}}
        current_response_value={'map':'stonewarm','document':current_document_value,'source_sha256':'a'*64}
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_response_value):
            current_document_result,current_status_text=hermes_agent_app.read_hermes_city_source_view('stonewarm')
            self.assertEqual(current_document_result,current_document_value)
            self.assertIn('DB 리비전',current_status_text)
        for current_bad_response in ({**current_response_value,'source_sha256':'invalid'}, {**current_response_value,'document':{'managementId':'config.city-layouts.other','data':{'cityId':'stonewarm'}}}, {**current_response_value,'document':{'managementId':'config.city-layouts.stonewarm','data':{'cityId':'other'}}}):
            with self.subTest(current_bad_response=current_bad_response), patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_bad_response):
                current_document_result,current_status_text=hermes_agent_app.read_hermes_city_source_view('stonewarm')
                self.assertEqual(current_document_result,{})
                self.assertIn('확인할 수 없습니다',current_status_text)

    def test_writer_index_status_review_displays_stale_and_no_gpu_assumption(self):
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value={'status':'stale'}) as current_gateway_mock:
            current_message_value=hermes_agent_app.read_hermes_writer_index_status_for_review()
            self.assertIn('갱신 필요',current_message_value)
            self.assertIn('GPU',current_message_value)
            current_gateway_mock.assert_called_once_with('hermes-agent','hermes-writer-index-status',{})

    def test_audio_resume_submit_reports_preflight_block_and_checks_identity(self):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_page_value={'service':'music-heartmula','snapshot':'a'*64}
        current_rows_value=[[current_job_identifier,'failed','job','','']]
        current_request_value={'request_id':'audio_resume_'+('c'*64),'service':'music-heartmula','job_id':current_job_identifier,'expected_resume_fingerprint':'b'*64,'history_snapshot':'a'*64}
        current_response_value={current_key_name:current_request_value[current_key_name] for current_key_name in ('request_id','service','job_id','expected_resume_fingerprint')}
        current_response_value.update(state='blocked',reason='download_running',duplicate=False)
        with patch.object(operations_history_app,'execute_remote_management_command',return_value=current_response_value):
            current_state_value,current_notice_value=operations_history_app.submit_operations_audio_resume(current_request_value,'music-heartmula',current_job_identifier,current_page_value,current_rows_value)
            self.assertIsNone(current_state_value)
            self.assertIn('접수 전 차단',current_notice_value)
            current_response_value['job_id']='2026-11-20_00-00-00-87654321'
            self.assertIn('접수 결과를 확인할 수 없습니다',operations_history_app.submit_operations_audio_resume(current_request_value,'music-heartmula',current_job_identifier,current_page_value,current_rows_value)[1])

    def test_audio_resume_review_blocks_current_download_without_creating_receipt(self):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_page_value={'service':'music-heartmula','snapshot':'a'*64}
        current_rows_value=[[current_job_identifier,'failed','job','','']]
        current_preview_value={'service':'music-heartmula','job_id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'b'*64,'resume_availability':'download_running'}
        with patch.object(operations_history_app,'execute_remote_management_command',return_value=current_preview_value) as current_gateway_mock:
            current_request_value,current_notice_value,current_identifier_value=operations_history_app.prepare_operations_audio_resume('music-heartmula',current_job_identifier,current_page_value,current_rows_value)
            self.assertIsNone(current_request_value)
            self.assertIn('다운로드가 진행 중',current_notice_value)
            self.assertEqual(current_identifier_value,'')
            self.assertEqual(current_gateway_mock.call_count,1)

    def test_audio_resume_review_blocks_unknown_legacy_conflict_status(self):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_page_value={'service':'music-heartmula','snapshot':'a'*64}
        current_rows_value=[[current_job_identifier,'failed','job','','']]
        current_preview_value={'service':'music-heartmula','job_id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'b'*64}
        with patch.object(operations_history_app,'execute_remote_management_command',return_value=current_preview_value) as current_gateway_mock:
            current_request_value,current_notice_value,current_identifier_value=operations_history_app.prepare_operations_audio_resume('music-heartmula',current_job_identifier,current_page_value,current_rows_value)
            self.assertIsNone(current_request_value)
            self.assertIn('충돌 상태를 확인할 수 없습니다',current_notice_value)
            self.assertEqual(current_identifier_value,'')
            self.assertEqual(current_gateway_mock.call_count,1)

    def test_sprite_save_reports_blocked_before_dispatch(self):
        import json
        current_draft_value={'path':'assets/example.png'}
        current_review_value={'request_id':'sprite_request_123','draft':current_draft_value}
        current_result_value={'request_id':'sprite_request_123','state':'blocked','saved':False,'reason':'pending','path':'assets/example.png'}
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_result_value):
            current_result_values=hermes_agent_app.save_hermes_sprite_anchor_draft(current_review_value,json.dumps(current_draft_value),'sprite_request_123')
            self.assertIn('저장 접수 전 차단',current_result_values[2])
            self.assertIn('중단된 저장',current_result_values[2])
            current_result_value['path']='assets/other.png'
            self.assertIn('저장 결과 확인 필요',hermes_agent_app.save_hermes_sprite_anchor_draft(current_review_value,json.dumps(current_draft_value),'sprite_request_123')[2])

    def test_sprite_pending_review_only_reads_gateway(self):
        current_pending_record={'state':'pending','files':[{'path':'assets/example.png','current':'before','backup':'valid'}]}
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_pending_record) as current_gateway_mock:
            self.assertEqual(hermes_agent_app.read_hermes_sprite_pending_status_for_review(),current_pending_record)
            current_gateway_mock.assert_called_once_with('hermes-agent','hermes-sprite-pending-status',{})

    def test_translation_evidence_review_reads_without_submitting(self):
        current_evidence_record={'candidates':[{'path':'lore/tree.md','heading':'나무','text':'근거','matched_terms':['나무']}],'note':'문서 근거'}
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_evidence_record) as current_gateway_mock:
            self.assertEqual(hermes_agent_app.search_hermes_translation_evidence_for_review('나무'),current_evidence_record)
            current_gateway_mock.assert_called_once_with('hermes-agent','hermes-translation-evidence',{'text':'나무'})

    def test_change_event_outputs_have_no_static_cycles(self):
        current_interface_value=build_hermes_test_interface()
        current_graph_value={}
        for current_dependency_value in current_interface_value.config['dependencies']:
            for current_target_value in current_dependency_value.get('targets',[]):
                if current_target_value[1]=='change':
                    current_graph_value.setdefault(current_target_value[0],set()).update(current_dependency_value.get('outputs',[]))
        current_seen_values=set()
        current_active_values=set()
        def visit_current_change_target(current_node_value):
            self.assertNotIn(current_node_value,current_active_values,'change 이벤트 출력에 순환이 있습니다')
            if current_node_value in current_seen_values:return
            current_active_values.add(current_node_value)
            for current_next_value in current_graph_value.get(current_node_value,()):visit_current_change_target(current_next_value)
            current_active_values.remove(current_node_value)
            current_seen_values.add(current_node_value)
        self.assertTrue(current_graph_value)
        for current_node_value in current_graph_value:visit_current_change_target(current_node_value)

    def test_operations_capture_selection_rechecks_receipt_and_job(self):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-20_00-00-00-12345678'
        current_rows_value=[['1','review-capture',current_job_identifier,'review-capture','맵 · request_123']]
        current_receipt_value={'state':'accepted','request_id':'request_123','service':'map-review','job_id':current_job_identifier}
        current_status_value={'receipt':current_receipt_value,'job':{'status':'queued','result_available':False}}
        with patch.object(operations_history_app,'execute_remote_management_command',return_value=current_status_value) as current_gateway_mock:
            current_message_value=operations_history_app.read_operations_selected_capture_status(current_rows_value,SimpleNamespace(index=(0,1)))
            self.assertIn('맵 캡처 · 대기',current_message_value)
            self.assertIn(current_job_identifier,current_message_value)
            self.assertIn('조회 시점 기준',current_message_value)
            current_gateway_mock.assert_called_once_with('hermes-agent','hermes-capture-status',{'request_id':'request_123','service':'map-review'})
            current_receipt_value['job_id']='2026-11-20_00-00-00-87654321'
            self.assertIn('일치하지 않습니다',operations_history_app.read_operations_selected_capture_status(current_rows_value,SimpleNamespace(index=0)))
            current_receipt_value['job_id']=current_job_identifier
            current_status_value['job']['result_available']='yes'
            self.assertIn('확인할 수 없습니다',operations_history_app.read_operations_selected_capture_status(current_rows_value,SimpleNamespace(index=0)))
            current_gateway_mock.reset_mock()
            self.assertIn('캡처 대기 기록을 선택',operations_history_app.read_operations_selected_capture_status([['1','kimodo',current_job_identifier,'미확인','—']],SimpleNamespace(index=0)))
            current_gateway_mock.assert_not_called()

    def test_operations_queue_capture_request_label_and_existing_priority_selection(self):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app
        current_capture_value={'service':'review-capture','source_service':'review-capture','request_id':'request_123','capture_service':'map-review'}
        self.assertEqual(operations_history_app.format_operations_capture_request_id(current_capture_value),'맵 · request_123')
        self.assertEqual(operations_history_app.format_operations_capture_request_id({**current_capture_value,'capture_service':'character-review'}),'캐릭터 · request_123')
        self.assertEqual(operations_history_app.format_operations_capture_request_id({**current_capture_value,'capture_service':'other'}),'미확인')
        self.assertEqual(operations_history_app.format_operations_capture_request_id({**current_capture_value,'source_service':'unknown'}),'미확인')
        self.assertEqual(operations_history_app.format_operations_capture_request_id({**current_capture_value,'request_id':'../invalid'}),'미확인')
        self.assertEqual(operations_history_app.format_operations_capture_request_id({'service':'kimodo'}),'—')
        current_rows_value=[['1','kimodo','2026-11-20_00-00-00-12345678','미확인','—']]
        current_target_value,current_notice_value,current_button_value=operations_history_app.select_operations_priority_target(current_rows_value,SimpleNamespace(index=0))
        self.assertEqual(current_target_value['service'],'kimodo')
        self.assertTrue(current_button_value['interactive'])

    def test_writer_request_events_and_history_clear_confirmation(self):
        current_blocks_value=build_hermes_test_interface(include_advanced_controls=True)
        current_config_value=current_blocks_value.get_config_file()
        current_components={current_component['id']:current_component.get('props',{}).get('label') or current_component.get('props',{}).get('value') for current_component in current_config_value['components']}
        current_request_ids={current_identifier for current_identifier,current_label in current_components.items() if current_label=='작가 AI 위임 접수 ID'}
        self.assertEqual(len(current_request_ids),1)
        current_request_id=next(iter(current_request_ids))
        current_triggers=[current_target[1] for current_event in current_config_value['dependencies'] for current_target in current_event['targets'] if current_target[0]==current_request_id]
        self.assertEqual(current_triggers.count('change'),0)
        self.assertEqual(current_triggers.count('input'),3)
        current_history_buttons={current_identifier for current_identifier,current_label in current_components.items() if current_label=='선택한 작가 AI 접수 확인'}
        current_history_events=[current_event for current_event in current_config_value['dependencies'] if any(current_target[0] in current_history_buttons and current_target[1]=='click' for current_target in current_event['targets']) and current_request_id in current_event['outputs']]
        self.assertEqual(len(current_history_events),1)
        current_result_values=current_blocks_value.fns[current_history_events[0]['id']].fn('request_123')
        self.assertEqual(current_result_values[0],'request_123')
        self.assertIsNone(current_result_values[1])
        self.assertFalse(current_result_values[3]['interactive'])
        self.assertIsNone(current_result_values[4])
        self.assertFalse(current_result_values[5]['visible'])
        self.assertIsNone(current_result_values[6])
        self.assertFalse(current_result_values[7]['visible'])

    def test_session_selection_clears_service_and_writer_review_together(self):
        current_blocks_value=build_hermes_test_interface(include_advanced_controls=False)
        current_config_value=current_blocks_value.get_config_file()
        current_component_labels={current_component['id']:current_component.get('props',{}).get('label') for current_component in current_config_value['components']}
        for current_label_value in ('세션','세션 작업 선택'):
            current_matching_events=[current_event for current_event in current_config_value['dependencies'] if any(current_component_labels.get(current_target[0])==current_label_value and current_target[1]=='change' for current_target in current_event['targets']) and current_blocks_value.fns[current_event['id']].fn is hermes_agent_app.reset_conversation_context_state]
            self.assertEqual(len(current_matching_events),1)
            current_result_values=current_blocks_value.fns[current_matching_events[0]['id']].fn()
            self.assertIsNone(current_result_values[0])
            self.assertFalse(current_result_values[3]['interactive'])
            self.assertIsNone(current_result_values[4])
            self.assertFalse(current_result_values[6])
            self.assertIsNone(current_result_values[7])
            self.assertFalse(current_result_values[8]['visible'])
            self.assertIsNone(current_result_values[10])
            self.assertFalse(current_result_values[14]['visible'])
            self.assertFalse(current_result_values[15]['interactive'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_video_results_link_actual_source_for_both_paths(self,current_gateway_mock):
        current_session_identifier='a'*32
        current_source_job='2026-11-18_11-00-00-12345678'
        current_video_job='2026-11-18_12-00-00-12345678'
        current_card_record={'session_id':current_session_identifier,'source_job_id':current_source_job,'kind':'video','service':'wan22-fun-control','review':{'request_id':'request_123'}}
        current_gateway_mock.return_value={'receipt':{'state':'accepted','request_id':'request_123','job_id':current_video_job,'service':'wan22-fun-control'},'job':{'status':'paused'}}
        current_state,current_text=hermes_agent_app.read_conversation_service_status(current_card_record,current_session_identifier,current_source_job,'video')
        self.assertEqual(current_state,'accepted')
        self.assertIn('일시정지',current_text)
        self.assertIn('/management/frame/wan22-fun-control-generator/?job='+current_video_job,current_text)
        self.assertNotIn('/management/frame/wan22-vace-generator/',current_text)
        current_source_record={'session_id':current_session_identifier,'source_job_id':current_source_job,'request_id':'request_123','proposal':{'service':'wan22-fun-control'}}
        self.assertIn('session='+current_session_identifier,hermes_agent_app.read_conversation_video_receipt(current_source_record,current_session_identifier,current_source_job))
        _,current_attached_text=hermes_agent_app.read_hermes_video_result('request_123','wan22-fun-control')
        self.assertIn('/management/frame/wan22-fun-control-generator/?job='+current_video_job,current_attached_text)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_attached_result_rejects_wrong_service_and_job_identifier(self,current_gateway_mock):
        current_gateway_mock.return_value={'receipt':{'state':'accepted','service':'wan22-vace','job_id':'2026-11-18_00-00-00-12345678'},'job':{'status':'completed'}}
        with self.assertRaises(gr.Error):hermes_agent_app.read_hermes_video_result('request_123','wan22-fun-control')
        current_gateway_mock.return_value['receipt']['service']='wan22-fun-control'
        current_gateway_mock.return_value['receipt']['job_id']='../invalid'
        with self.assertRaises(gr.Error):hermes_agent_app.read_hermes_video_result('request_123','wan22-fun-control')
        current_gateway_mock.return_value['receipt']['service']='music-heartmula'
        with self.assertRaises(gr.Error):hermes_agent_app.read_hermes_audio_result('request_123','music-heartmula')

    def test_attachment_proposal_open_failure_clears_review_and_disables_submission(self):
        for current_safe_function,current_target_name,current_review_index in ((hermes_agent_app.open_conversation_flux_reference_safely,'open_conversation_flux_reference',3),(hermes_agent_app.open_conversation_video_proposal_safely,'open_conversation_video_proposal',7)):
            with self.subTest(target=current_target_name),patch.object(hermes_agent_app,current_target_name,side_effect=gr.Error('unavailable')):
                current_result_values=current_safe_function('session','job')
                self.assertIsNone(current_result_values[0])
                self.assertIsNone(current_result_values[current_review_index])
                self.assertFalse(current_result_values[-1]['interactive'])
                self.assertIn('확인하지 못했습니다',current_result_values[-2])

    def test_attachment_open_events_clear_review_and_submission_control(self):
        current_blocks_value=build_hermes_test_interface(include_advanced_controls=False)
        current_open_events={getattr(current_event_value.fn,'__name__',''):current_event_value for current_event_value in current_blocks_value.fns.values()}
        for current_function_name,current_expected_count,current_button_label,current_review_index in (
            ('open_conversation_flux_reference_safely',7,'이미지 작업 대기열에 추가',3),
            ('open_conversation_video_proposal_safely',11,'영상 작업 대기열에 추가',7),
        ):
            with self.subTest(callback=current_function_name):
                current_event_value=current_open_events[current_function_name]
                self.assertEqual(len(current_event_value.outputs),current_expected_count)
                self.assertIsInstance(current_event_value.outputs[current_review_index],gr.State)
                self.assertEqual(current_event_value.outputs[-1].value,current_button_label)
                self.assertIsInstance(current_event_value.outputs[-1],gr.Button)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_attached_video_mismatched_receipt_disables_review_with_guidance(self,current_gateway_mock):
        current_session_identifier='a'*32
        current_source_job='2026-11-18_11-00-00-12345678'
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source_job,'job':{'status':{'status':'completed'}}}]}
            if current_command_name=='hermes-video-proposal':return {'id':'a'*32,'job_id':current_payload_record['id'],'proposal':{'service':'wan22-fun-control','mode':'pose','prompt':'walk'}}
            if current_command_name=='hermes-service-receipt':return {'state':'accepted','request_id':current_payload_record['request_id'],'service':'wan22-vace','job_id':'2026-11-18_12-00-00-12345678'}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_open_values=hermes_agent_app.open_conversation_video_proposal(current_session_identifier,current_source_job)
        self.assertIsNone(current_open_values[0])
        self.assertIn('자동 재접수하지 마세요',current_open_values[-1])

    def test_safe_result_callbacks_clear_previous_values_on_failure(self):
        current_cases=((hermes_agent_app.read_safe_hermes_video_result,('request_123','wan22-vace'),2),(hermes_agent_app.read_safe_hermes_audio_result,('request_123','music-heartmula'),2),(hermes_agent_app.read_safe_hermes_flux_result,('request_123','flux-building'),2),(hermes_agent_app.read_safe_hermes_translation_result,('request_123',),3),(hermes_agent_app.read_safe_hermes_writer_result,('request_123',),3))
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=OSError('offline')):
            for current_reader,current_arguments,current_count in current_cases:
                with self.subTest(reader=current_reader):
                    current_result=current_reader(*current_arguments)
                    self.assertEqual(len(current_result),current_count)
                    self.assertEqual(current_result[0],'')
                    self.assertIn('확인 불가',current_result[1])
                    if current_count==3:self.assertIsNone(current_result[2])

    def test_conversation_status_refresh_replaces_previous_result_on_failure(self):
        current_card={'session_id':'a'*32,'source_job_id':'job-a','kind':'flux','service':'flux-image','review':{'request_id':'request_123'}}
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=OSError('offline')):
            current_notice=hermes_agent_app.refresh_conversation_service_status(current_card,'a'*32,'job-a','flux')
        self.assertIn('확인 불가',current_notice)
        self.assertIn('자동 재접수하지 않습니다',current_notice)

    def test_result_readers_reject_explicit_other_request_identity(self):
        current_job='2026-11-18_12-00-00-12345678'
        current_cases=((hermes_agent_app.read_hermes_video_result,('request_123','wan22-vace'),'wan22-vace'),(hermes_agent_app.read_hermes_audio_result,('request_123','music-heartmula'),'music-heartmula'),(hermes_agent_app.read_hermes_flux_profile_result,('request_123','flux-building'),'flux-building'),(hermes_agent_app.read_hermes_translation_result,('request_123',),'prompt-translation'),(hermes_agent_app.read_hermes_writer_result,('request_123',),'writer-agent'))
        for current_reader,current_arguments,current_service in current_cases:
            for current_state in ('not_found','unknown','accepted'):
                with self.subTest(service=current_service,state=current_state):
                    current_response={'receipt':{'state':current_state,'request_id':'wrong','service':current_service,'job_id':current_job},'job':{}}
                    with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_response):
                        with self.assertRaises(gr.Error):current_reader(*current_arguments)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_result_rejects_other_service_or_invalid_job(self,current_gateway_mock):
        current_session_identifier='a'*32
        current_source_job='2026-11-18_11-00-00-12345678'
        for current_kind,current_service in (('video','wan22-fun-control'),('audio','music-heartmula'),('flux','flux-image'),('translation','prompt-translation'),('writer','writer-agent')):
            current_card_record={'session_id':current_session_identifier,'source_job_id':current_source_job,'kind':current_kind,'service':current_service,'review':{'request_id':'request_123'}}
            for current_receipt_value in ({'state':'accepted','service':'other','job_id':'2026-11-18_12-00-00-12345678'},{'state':'accepted','service':current_service,'job_id':'../invalid'}):
                with self.subTest(kind=current_kind,receipt=current_receipt_value):
                    current_gateway_mock.return_value={'receipt':current_receipt_value,'job':{'status':'completed'}}
                    with self.assertRaises(gr.Error):hermes_agent_app.read_conversation_service_status(current_card_record,current_session_identifier,current_source_job,current_kind)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_text_proposal_mismatched_receipt_disables_resubmission(self,current_gateway_mock):
        current_session_identifier='a'*32
        current_source_job='2026-11-18_11-00-00-12345678'
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source_job,'job':{'status':{'status':'completed'}}}]}
            if current_command_name=='hermes-flux-proposal':return {'id':'a'*32,'job_id':current_payload_record['id'],'proposal':{'service':'flux-image','prompt':'test','width':512,'height':512,'seed':42}}
            if current_command_name=='hermes-service-receipt':return {'state':'accepted','request_id':current_payload_record['request_id'],'service':'flux-building','job_id':'2026-11-18_12-00-00-12345678'}
            if current_command_name=='hermes-flux-delegation-status':return {'receipt':{'state':'accepted','service':'flux-building','job_id':'2026-11-18_12-00-00-12345678'},'job':{'status':'completed'}}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_card_record,_,current_notice_text=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job,'flux')
        self.assertFalse(current_card_record['ready'])
        self.assertIn('자동 재접수하지 마세요',current_notice_text)
        with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_service_review(current_card_record,current_session_identifier,current_source_job,'flux')
        self.assertFalse(any(current_call.args[1].startswith('hermes-delegate') for current_call in current_gateway_mock.call_args_list))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_media_links_require_matching_completed_attempt(self,current_gateway_mock):
        current_job_identifier='2026-11-18_12-00-00-12345678'
        current_prefix='/wan22-vace/jobs/'+current_job_identifier+'/attempts/'
        current_gateway_mock.return_value={'receipt':{'state':'accepted','service':'wan22-vace','job_id':current_job_identifier},'job':{'status':'completed','video':current_prefix+'a'*32+'/preview.mp4','image':current_prefix+'b'*32+'/output-000.png','download':None}}
        _,current_status_text=hermes_agent_app.read_hermes_video_result('request_123','wan22-vace')
        self.assertNotIn('[영상]',current_status_text)
        self.assertIn('결과 파일 확인 불가',current_status_text)
        current_gateway_mock.return_value['job']['image']=current_prefix+'a'*32+'/output-000.png'
        _,current_status_text=hermes_agent_app.read_hermes_video_result('request_123','wan22-vace')
        self.assertIn('[영상]',current_status_text)
        current_gateway_mock.return_value['job']['status']='running'
        self.assertNotIn('[영상]',hermes_agent_app.read_hermes_video_result('request_123','wan22-vace')[1])
        current_gateway_mock.return_value={'receipt':{'state':'accepted','service':'music-heartmula','job_id':current_job_identifier},'job':{'status':'completed','audio':'/other/jobs/'+current_job_identifier+'/attempts/'+'a'*32+'/music.wav'}}
        self.assertNotIn('[생성 음원 듣기]',hermes_agent_app.read_hermes_audio_result('request_123','music-heartmula')[1])

    def test_conversation_result_links_follow_actual_service_and_validated_job(self):
        current_job_identifier='2026-11-18_12-00-00-12345678'
        for current_service_name,current_page_name in (('kimodo','kimodo-generator'),('dwpose','dwpose-generator'),('wan22-animate2','wan22-animate2-generator'),('wan22-fun-control','wan22-fun-control-generator'),('wan22-vace','wan22-vace-generator'),('music-heartmula','music-heartmula'),('flux-expression','flux-expression-generator'),('prompt-translation','prompt-translation')):
            with self.subTest(service=current_service_name):
                self.assertEqual(hermes_agent_app.build_conversation_result_link(current_service_name,current_job_identifier),'/management/frame/'+current_page_name+'/?job='+current_job_identifier)
                self.assertEqual(hermes_agent_app.build_conversation_result_link(current_service_name,'../unsafe'),'/management/frame/'+current_page_name+'/')
        self.assertIsNone(hermes_agent_app.build_conversation_result_link('unknown',current_job_identifier))

    def test_flux_expression_operations_link_forwards_selected_job(self):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-18_12-00-00-12345678'
        current_link_text=operations_history_app.render_operations_source_link('flux-expression',current_job_identifier)
        self.assertIn('/management/frame/flux-expression-generator/?job='+current_job_identifier,current_link_text)
        self.assertNotIn('?job=',operations_history_app.render_operations_source_link('flux-expression','../unsafe'))

    def test_writer_history_link_requires_writer_identifier(self):
        from generators.writer_agent.page.interface import prepare_writer_history_link
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='20261118-120000-12345678'
        self.assertEqual(hermes_agent_app.build_conversation_result_link('writer-agent',current_job_identifier),'/management/frame/writer-agent/?job='+current_job_identifier)
        self.assertIn('?job='+current_job_identifier,operations_history_app.render_operations_source_link('writer-agent',current_job_identifier))
        self.assertEqual(prepare_writer_history_link(current_job_identifier)[0],current_job_identifier)
        self.assertEqual(prepare_writer_history_link('../bad')[0],'')

    def test_result_link_preserves_valid_origin_session(self):
        current_job_identifier='2026-11-18_12-00-00-12345678'
        current_session_identifier='a'*32
        current_link_text=hermes_agent_app.build_conversation_result_link('prompt-translation',current_job_identifier,current_session_identifier)
        self.assertEqual(current_link_text,'/management/frame/prompt-translation/?job='+current_job_identifier+'&session='+current_session_identifier)
        self.assertNotIn('session=',hermes_agent_app.build_conversation_result_link('prompt-translation',current_job_identifier,'../bad'))

    def test_direct_link_preserves_only_valid_session(self):
        current_session_identifier = 'a' * 32
        current_link_text = hermes_agent_app.build_conversation_direct_link(current_session_identifier)
        self.assertIn('/management/frame/hermes-direct/?session=' + current_session_identifier, current_link_text)
        for current_invalid_value in (None, '', 'A' * 32, 'a' * 31, 'a' * 32 + '&evil=1'):
            with self.subTest(current_invalid_value=current_invalid_value):
                self.assertIn('href="/management/frame/hermes-direct/"', hermes_agent_app.build_conversation_direct_link(current_invalid_value))

    def test_management_page_composes_with_menu(self):
        with tempfile.TemporaryDirectory() as hermes_temporary_root:
            hermes_source_path = Path(hermes_temporary_root) / 'manager.json'
            hermes_source_path.write_text('{"pages":[]}')
            hermes_page_records = load_manager_page_records(hermes_source_path)
            self.assertIn('hermes-agent', [hermes_page_record['id'] for hermes_page_record in hermes_page_records])
            self.assertEqual(next(current_page_record['label'] for current_page_record in hermes_page_records if current_page_record['id'] == 'hermes-agent'), '운영 대화')
            with patch.dict('os.environ', {'SLIME_MANAGEMENT_MENU_SOURCE': str(Path(hermes_temporary_root) / 'missing.json')}):
                hermes_interface_blocks, hermes_mount_options = build_async_test_interface(build_management_blocks, 'hermes-agent', 8770, hermes_source_path)
            hermes_component_labels = [getattr(hermes_component_value, 'label', None) for hermes_component_value in hermes_interface_blocks.blocks.values()]
            self.assertNotIn('작업 지시', hermes_component_labels)
            self.assertIn('요청 입력', hermes_component_labels)
            self.assertIn('대화', hermes_component_labels)
            self.assertNotIn('검토용 변경 diff', hermes_component_labels)
            with patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command'):
                current_direct_blocks,_=build_async_test_interface(build_management_blocks,'hermes-direct',8770,hermes_source_path)
            current_direct_labels=[getattr(current_component_value,'label',None) for current_component_value in current_direct_blocks.blocks.values()]
            self.assertIn('작업 지시',current_direct_labels)
            self.assertIn('검토용 변경 diff',current_direct_labels)
            current_direct_components=current_direct_blocks.get_config_file()['components']
            current_direct_accordion=next(current_record for current_record in current_direct_components if current_record.get('props',{}).get('elem_id')=='hermes-direct-controls')
            self.assertTrue(current_direct_accordion['props']['open'])
            current_direct_chatbots=[current_record for current_record in current_direct_components if current_record['type']=='chatbot']
            self.assertTrue(current_direct_chatbots)
            self.assertTrue(all(not current_record['props']['visible'] for current_record in current_direct_chatbots))
            self.assertNotIn('요청 입력',current_direct_labels)
            self.assertIn('세션 작업 선택',current_direct_labels)
            current_session_events=[current_event for current_event in current_direct_blocks.fns.values() if getattr(current_event.fn,'__name__','')=='read_hermes_session_conversation' and current_event.inputs and getattr(current_event.inputs[0],'label',None)=='세션']
            self.assertTrue(current_session_events)
            self.assertTrue(any(any(getattr(current_output,'label',None)=='세션 작업 선택' for current_output in current_event.outputs) for current_event in current_session_events))
            current_reset_events=[current_event for current_event in current_direct_blocks.fns.values() if getattr(current_event.fn,'__name__','')=='reset_direct_session_job_detail']
            self.assertEqual(len(current_reset_events),2)
            self.assertTrue(all(any(getattr(current_output,'label',None)=='작업 ID' for current_output in current_event.outputs) for current_event in current_reset_events))
            self.assertEqual(hermes_agent_app.reset_direct_session_job_detail()[0],'')
            self.assertIsNone(hermes_agent_app.reset_direct_session_job_detail()[7])
            self.assertTrue(any('#hermes-direct-controls' in str(current_record.get('props',{}).get('value','')) for current_record in current_direct_components))
            self.assertLess(len(hermes_interface_blocks.config['dependencies']),len(current_direct_blocks.config['dependencies']))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_kimodo_review_uses_same_receipt_after_reopening(self, current_gateway_mock):
        current_session_identifier = 'a' * 32
        current_source_job_identifier = '2026-11-18_00-24-38-0f938e1b'
        current_generated_job_identifier = '2026-11-18_12-00-19-05056f95'
        current_proposal_record = {'prompt':'천천히 걷기', 'frames':90, 'steps':100, 'seed':42}
        current_receipt_state = {'state':'not_found'}
        def current_gateway_result(current_service_name, current_command_name, current_payload_value):
            if current_command_name == 'hermes-session-view':
                return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source_job_identifier, 'job':{'status':{'status':'completed'}}}]}
            if current_command_name == 'hermes-kimodo-proposal':
                return {'job_id':current_source_job_identifier,'proposal':current_proposal_record}
            if current_command_name == 'hermes-delegation-status':
                return {'request_id':current_payload_value['request_id'],'service':'kimodo',**current_receipt_state}
            if current_command_name == 'hermes-delegation-job-status':
                return {'receipt':{'request_id':current_payload_value['request_id'],'service':'kimodo',**current_receipt_state}, 'job':{'status':'completed'}}
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
        self.assertIn('중단 작업 복구',current_status_text)
        current_reopened_card,_,current_reopened_status = hermes_agent_app.prepare_conversation_kimodo_review(current_session_identifier,current_source_job_identifier)
        self.assertEqual(current_card_record['review']['request_id'],current_reopened_card['review']['request_id'])
        self.assertFalse(current_reopened_card['ready'])
        self.assertIn('기존 Kimodo 접수',current_reopened_status)
        self.assertEqual(sum(current_call.args[1]=='hermes-delegation-job-status' for current_call in current_gateway_mock.call_args_list),1)
        self.assertEqual(sum(current_call.args[1] == 'hermes-delegate-kimodo' for current_call in current_gateway_mock.call_args_list),1)

    def test_kimodo_proposal_open_rejects_unverified_absence_without_status(self):
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_proposal={'prompt':'walk','frames':90,'steps':100,'seed':42}
        current_calls=[]
        def current_gateway(service,command,payload):
            current_calls.append(command)
            if command=='hermes-delegation-status':return {'state':'not_found'}
            raise AssertionError(command)
        with patch.object(hermes_agent_app,'find_conversation_session_job'),patch.object(hermes_agent_app,'read_matching_hermes_edit_proposal',return_value=current_proposal),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            current_card,_,current_notice=hermes_agent_app.prepare_conversation_kimodo_review(current_session,current_job)
        self.assertFalse(current_card['ready'])
        self.assertIn('확인할 수 없습니다',current_notice)
        self.assertEqual(current_calls,['hermes-delegation-status'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_kimodo_refuses_unknown_and_wrong_session(self,current_gateway_mock):
        current_session_identifier = 'a' * 32
        current_source_job_identifier = '2026-11-18_00-24-38-0f938e1b'
        current_proposal_record = {'prompt':'천천히 걷기', 'frames':90, 'steps':100, 'seed':42}
        def current_gateway_result(current_service_name,current_command_name,current_payload_value):
            if current_command_name == 'hermes-session-view':
                return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source_job_identifier,'job':{'status':{'status':'completed'}}}]}
            if current_command_name == 'hermes-kimodo-proposal':return {'job_id':current_source_job_identifier,'proposal':current_proposal_record}
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

    def test_uncertain_conversation_dispatch_disables_reuse_without_retry(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_card={'session_id':current_session,'source_job_id':current_job,'kind':'translation','service':'prompt-translation','review':{'request_id':'request_123','request':{}},'ready':True}
        for current_response in (OSError('lost'), None, {'state':'invalid'}, {'state':'unknown'}, {'state':'accepted'}, {'state':'accepted','job_id':'x','service':'wrong'}):
            with self.subTest(response=current_response):
                with patch.object(hermes_agent_app,'prepare_conversation_service_review',return_value=(current_card.copy(),'','')):
                    with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_response if isinstance(current_response,Exception) else None,return_value=current_response) as current_gateway:
                        current_after,current_notice=hermes_agent_app.submit_conversation_service_review(current_card,current_session,current_job,'translation')
                        self.assertFalse(current_after['ready'])
                        self.assertIn('자동 재접수하지 않습니다',current_notice)
                        with self.assertRaises(gr.Error):
                            hermes_agent_app.submit_conversation_service_review(current_after,current_session,current_job,'translation')
                        current_gateway.assert_called_once()

    def test_conversation_dispatch_rejects_mismatched_followup_job(self):
        current_session='a'*32
        current_source='2026-11-18_00-00-00-12345678'
        current_job='2026-11-18_01-00-00-12345678'
        current_other_job='2026-11-18_02-00-00-87654321'
        current_card={'session_id':current_session,'source_job_id':current_source,'kind':'translation','service':'prompt-translation','review':{'request_id':'request_123','request':{}},'ready':True}
        for current_receipt_job in (current_job,current_other_job):
            with self.subTest(receipt_job=current_receipt_job):
                current_receipt={'state':'accepted','request_id':'request_123','service':'prompt-translation','job_id':current_receipt_job}
                current_responses=[{'state':'accepted','job_id':current_job},{'receipt':current_receipt,'job':{'status':'completed','result':'확인된 결과'}}]
                with patch.object(hermes_agent_app,'prepare_conversation_service_review',return_value=(current_card.copy(),'','')),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_responses):
                    current_after,current_notice=hermes_agent_app.submit_conversation_service_review(current_card,current_session,current_source,'translation')
                self.assertFalse(current_after['ready'])
                if current_receipt_job==current_job:self.assertIn('확인된 결과',current_notice)
                else:
                    self.assertIn('확인 불가',current_notice)
                    self.assertNotIn('확인된 결과',current_notice)

    def test_kimodo_dispatch_rejects_mismatched_followup_job(self):
        current_session='a'*32
        current_source='2026-11-18_00-00-00-12345678'
        current_job='2026-11-18_01-00-00-12345678'
        current_other='2026-11-18_02-00-00-87654321'
        current_card={'session_id':current_session,'source_job_id':current_source,'review':{'request_id':'request_123','request':{}},'ready':True}
        for current_followup in (current_job,current_other):
            with self.subTest(followup=current_followup):
                current_response={'receipt':{'state':'accepted','request_id':'request_123','service':'kimodo','job_id':current_followup},'job':{'status':'completed'}}
                with patch.object(hermes_agent_app,'prepare_conversation_kimodo_review',return_value=(current_card.copy(),'','')),patch.object(hermes_agent_app,'submit_hermes_kimodo_request',return_value=(current_job,'접수')),patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_response):
                    current_after,current_notice=hermes_agent_app.submit_conversation_kimodo_review(current_card,current_session,current_source)
                self.assertFalse(current_after['ready'])
                if current_followup==current_job:self.assertIn('완료',current_notice)
                else:
                    self.assertIn('확인할 수 없습니다',current_notice)
                    self.assertNotIn(current_other,current_notice)

    def test_uncertain_kimodo_and_video_dispatch_disable_reuse(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_card={'session_id':current_session,'source_job_id':current_job,'review':{'request_id':'request_123','request':{}},'ready':True}
        with patch.object(hermes_agent_app,'prepare_conversation_kimodo_review',return_value=(current_card.copy(),'','')),patch.object(hermes_agent_app,'submit_hermes_kimodo_request',side_effect=gr.Error('lost')) as current_submit:
            current_after,current_notice=hermes_agent_app.submit_conversation_kimodo_review(current_card,current_session,current_job)
            self.assertFalse(current_after['ready'])
            self.assertIn('자동 재접수하지 않습니다',current_notice)
            with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_kimodo_review(current_after,current_session,current_job)
            current_submit.assert_called_once()
        current_source={'session_id':current_session,'source_job_id':current_job,'proposal':{'service':'wan22-vace'},'request_id':'request_123'}
        current_review={'source':current_source,'review':{'request_id':'request_123','service':'wan22-vace','request':{}}}
        for current_response in (OSError('lost'),None,{'state':'invalid'},{'state':'unknown'},{'state':'accepted'},{'state':'accepted','job_id':'x','service':'wrong'}):
            with self.subTest(response=current_response),patch.object(hermes_agent_app,'review_conversation_video_inputs',return_value=(current_review,'','')),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_response if isinstance(current_response,Exception) else None,return_value=current_response) as current_gateway:
                current_after,current_notice=hermes_agent_app.submit_conversation_video_inputs(current_review,current_source,current_session,current_job,'{}',None,None,None,None,None)
                self.assertIsNone(current_after)
                self.assertIn('자동 재접수하지 않습니다',current_notice)
                with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_video_inputs(current_after,current_source,current_session,current_job,'{}',None,None,None,None,None)
                current_gateway.assert_called_once()

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_translation_reopens_receipt_and_never_reexecutes(self,current_gateway_mock):
        current_session_identifier='a'*32
        current_source_job_identifier='2026-11-18_00-24-38-0f938e1b'
        current_generation_job_identifier='2026-11-18_12-00-19-05056f95'
        current_receipt_record={'state':'not_found'}
        current_proposal_record={'text':'안녕하세요','target_language':'English','glossary':[]}
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source_job_identifier,'job':{'status':{'status':'completed'}}}]}
            if current_command_name=='hermes-translation-proposal':return {'id':'a'*32,'job_id':current_payload_record['id'],'proposal':current_proposal_record}
            if current_command_name=='hermes-service-receipt':return {'request_id':current_payload_record['request_id'],'service':'prompt-translation',**current_receipt_record}
            if current_command_name=='hermes-translation-status':return {'receipt':{'request_id':current_payload_record['request_id'],'service':'prompt-translation',**current_receipt_record},'job':{'status':'completed','result':'Hello'}}
            if current_command_name=='hermes-delegate-translation':
                current_receipt_record.update(state='accepted',service='prompt-translation',job_id=current_generation_job_identifier)
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

    def test_service_proposal_open_reads_only_receipt(self):
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_calls=[]
        current_proposal={'service':'flux-image','prompt':'tree','width':512,'height':512,'seed':42}
        def current_gateway(service,command,payload):
            current_calls.append(command)
            if command=='hermes-service-receipt':return {'request_id':payload['request_id'],'service':'flux-image','state':'accepted','job_id':'2026-11-18_01-00-00-87654321'}
            raise AssertionError(command)
        with patch.object(hermes_agent_app,'find_conversation_session_job'),patch.object(hermes_agent_app,'read_matching_hermes_edit_proposal',return_value=current_proposal),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            current_card,_,current_notice=hermes_agent_app.prepare_conversation_service_review(current_session,current_job,'flux')
        self.assertFalse(current_card['ready'])
        self.assertIn('상태와 결과 확인',current_notice)
        self.assertEqual(current_calls,['hermes-service-receipt'])

    def test_conversation_service_rejects_wrong_or_unverified_receipt_identity(self):
        current_card={'session_id':'a'*32,'source_job_id':'job-a','kind':'flux','service':'flux-image','review':{'request_id':'request_123'}}
        current_receipt={'state':'not_found','request_id':'request_123','service':'flux-image'}
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value={'receipt':current_receipt}):
            self.assertEqual(hermes_agent_app.read_conversation_service_status(current_card,'a'*32,'job-a','flux')[0],'not_found')
            for current_changes in ({'request_id':'wrong'},{'service':'flux-prop'},{'request_id':None},{'service':None}):
                current_before=dict(current_receipt)
                current_receipt.update(current_changes)
                with self.assertRaises(gr.Error):hermes_agent_app.read_conversation_service_status(current_card,'a'*32,'job-a','flux')
                current_receipt.clear();current_receipt.update(current_before)
            current_receipt.update(state='unknown',request_id='wrong')
            with self.assertRaises(gr.Error):hermes_agent_app.read_conversation_service_status(current_card,'a'*32,'job-a','flux')
            current_receipt.update(state='accepted',request_id=None,service='flux-image',job_id='2026-11-18_00-00-00-12345678')
            with self.assertRaises(gr.Error):hermes_agent_app.read_conversation_service_status(current_card,'a'*32,'job-a','flux')

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_edit_confirmation_rejects_replaced_card(self,current_gateway_mock):
        current_card_record={'session_id':'a'*32,'source_job_id':'job-a','kind':'effect','ready':True,'review':{'draft':{'id':'old'}}}
        current_changed_card={**current_card_record,'review':{'draft':{'id':'new'}}}
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_confirmed_conversation_edit(current_card_record,current_changed_card,'a'*32,'job-a','effect')
        current_gateway_mock.assert_not_called()

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_completed_results_show_missing_paths(self,current_unused_mock):
        current_session_identifier='a'*32
        current_source_identifier='source-job'
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_request_identifier='request_123'
        for current_kind_name,current_service_name,current_job_record,current_expected_notice in (
            ('flux','flux-building',{'status':'completed','image':None},'이미지 경로를 확인할 수 없습니다'),
            ('video','wan22-vace',{'status':'completed','video':'/wan22-vace/jobs/'+current_job_identifier+'/attempts/'+('a'*32)+'/preview.mp4'},'결과 경로 일부만 확인')):
            with self.subTest(kind=current_kind_name):
                current_card_record={'session_id':current_session_identifier,'source_job_id':current_source_identifier,'kind':current_kind_name,'service':current_service_name,'review':{'request_id':current_request_identifier}}
                current_response_record={'receipt':{'state':'accepted','request_id':current_request_identifier,'service':current_service_name,'job_id':current_job_identifier},'job':current_job_record}
                with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_response_record):
                    _,current_notice_text=hermes_agent_app.read_conversation_service_status(current_card_record,current_session_identifier,current_source_identifier,current_kind_name)
                    self.assertIn(current_expected_notice,current_notice_text)
                    self.assertIn('품질 승인',current_notice_text)
                    self.assertIn('파일 존재와 재생 여부',current_notice_text)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_edit_rejects_other_completed_receipt(self,current_gateway_mock):
        current_card={'session_id':'a'*32,'source_job_id':'job-a','kind':'effect','request_id':'request_123','ready':False}
        current_gateway_mock.return_value={'state':'completed','saved':True,'request_id':'other_request'}
        with self.assertRaises(gr.Error):hermes_agent_app.read_conversation_edit_result(current_card,'a'*32,'job-a','effect')
        current_gateway_mock.return_value['request_id']='request_123'
        self.assertIn('저장 완료',hermes_agent_app.read_conversation_edit_result(current_card,'a'*32,'job-a','effect'))

    def test_conversation_edit_result_checks_receipt_target(self):
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        for current_kind,current_field,current_good,current_bad,current_proposal in (
            ('building','texture','town-a-v1','town-b-v1',{'texture':'town-a-v1'}),
            ('effect','effect_id','fire','water',{'id':'fire'}),
            ('billboard','textures',['tree-a','tree-b'],['tree-a'],{'changes':[{'texture':'tree-b'},{'texture':'tree-a'}]}),
            ('sprite','path','assets/sprites/a.png','assets/sprites/b.png',{'path':'assets/sprites/a.png'})):
            with self.subTest(kind=current_kind):
                current_card={'session_id':current_session,'source_job_id':current_job,'kind':current_kind,'request_id':'request_123','ready':False}
                current_receipt={'state':'completed','saved':True,'request_id':'request_123'}
                def current_gateway(service,command,payload):
                    if command.endswith('-receipt'):return current_receipt
                    if command.endswith('-proposal'):return {'job_id':current_job,'proposal':current_proposal}
                    raise AssertionError(command)
                with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
                    self.assertIn('대상 미확인',hermes_agent_app.read_conversation_edit_result(current_card,current_session,current_job,current_kind))
                    current_receipt[current_field]=current_bad
                    with self.assertRaises(gr.Error):hermes_agent_app.read_conversation_edit_result(current_card,current_session,current_job,current_kind)
                    current_receipt['state']='unknown'
                    with self.assertRaises(gr.Error):hermes_agent_app.read_conversation_edit_result(current_card,current_session,current_job,current_kind)
                    current_receipt[current_field]=current_good
                    self.assertIn('확인 불가',hermes_agent_app.read_conversation_edit_result(current_card,current_session,current_job,current_kind))
                    current_receipt['state']='completed'
                    self.assertNotIn('대상 미확인',hermes_agent_app.read_conversation_edit_result(current_card,current_session,current_job,current_kind))

    def test_conversation_receipts_show_saved_ledger_state(self):
        current_session_identifier='a'*32
        current_job_identifier='job-a'
        for current_edit_kind,current_target_field,current_target_value,current_proposal_value in (
            ('effect','effect_id','effect-a',{'id':'effect-a'}),
            ('billboard','textures',['tree-a'],{'changes':[{'texture':'tree-a'}]})):
            with self.subTest(kind=current_edit_kind):
                current_card_record={'session_id':current_session_identifier,'source_job_id':current_job_identifier,'kind':current_edit_kind,'request_id':'request_123'}
                current_receipt_record={'request_id':'request_123','state':'completed','saved':True,current_target_field:current_target_value,'ledger_status_at_save':'pending','generation':4}
                def current_gateway_response(current_service_name,current_command_name,current_payload_record):
                    if current_command_name.endswith('-receipt'):return current_receipt_record
                    if current_command_name.endswith('-proposal'):return {'job_id':current_job_identifier,'proposal':current_proposal_value}
                    raise AssertionError(current_command_name)
                with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway_response):
                    current_result_text=hermes_agent_app.read_conversation_edit_result(current_card_record,current_session_identifier,current_job_identifier,current_edit_kind)
                    self.assertIn('저장 당시 원장 반영 대기',current_result_text)
                    self.assertIn('현재 원장',current_result_text)
                    self.assertIn('?session='+current_session_identifier,current_result_text)
                    current_receipt_record['saved']=False
                    current_result_text=hermes_agent_app.read_conversation_edit_result(current_card_record,current_session_identifier,current_job_identifier,current_edit_kind)
                    self.assertIn('저장되지 않음',current_result_text)
                    self.assertNotIn('저장 완료',current_result_text)

    def test_building_conversation_receipt_does_not_claim_unsaved_result(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_session_identifier='a'*32
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_card_record={'session_id':current_session_identifier,'source_job_id':current_job_identifier,'kind':'building','request_id':'request_123','ready':False}
        current_receipt_record={'state':'completed','saved':False,'request_id':'request_123','texture':'town-a-v1'}
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-building-receipt':return current_receipt_record
            if current_command_name=='hermes-building-proposal':return {'job_id':current_job_identifier,'proposal':{'texture':'town-a-v1'}}
            raise AssertionError(current_command_name)
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway_response):
            current_result_text=hermes_agent_app.read_conversation_edit_result(current_card_record,current_session_identifier,current_job_identifier,'building')
            self.assertIn('저장되지 않음',current_result_text)
            self.assertNotIn('저장 완료',current_result_text)
            current_receipt_record['saved']=True
            self.assertIn('저장 완료',hermes_agent_app.read_conversation_edit_result(current_card_record,current_session_identifier,current_job_identifier,'building'))

    def test_unsaved_map_receipts_do_not_claim_no_changes(self):
        from tools.review.ui.gradio import hermes_agent_app
        for current_kind_name in ('city','field'):
            current_receipt_value={'request_id':'request_123','map':'map-a','state':'completed','saved':False}
            with self.subTest(current_kind_name=current_kind_name),patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_receipt_value):
                current_reader_function=hermes_agent_app.read_hermes_city_map_receipt if current_kind_name=='city' else hermes_agent_app.read_hermes_field_map_receipt
                current_result_text=current_reader_function('request_123')
                self.assertIn('저장되지 않음',current_result_text)
                self.assertIn('변경 여부 확인',current_result_text)
                self.assertNotIn('변경 없음',current_result_text)

    def test_uncertain_edit_save_disables_review_and_does_not_claim_not_saved(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_functions={'billboard':'save_hermes_billboard_edit_draft','effect':'save_hermes_effect_edit_draft','field':'save_hermes_field_map_draft','sprite':'save_hermes_sprite_anchor_draft'}
        for current_kind,current_function in current_functions.items():
            current_card={'session_id':current_session,'source_job_id':current_job,'kind':current_kind,'request_id':'request_123','ready':True,'review':{'draft':{'example':1}}}
            for current_failure in (OSError('lost'), gr.Error('invalid response'), None):
                with self.subTest(kind=current_kind,failure=current_failure):
                    current_return=(None,gr.update(visible=False),'저장 결과 확인 필요')
                    with patch.object(hermes_agent_app,'prepare_conversation_edit_review',return_value=(current_card.copy(),'',None,'')),patch.object(hermes_agent_app,current_function,side_effect=current_failure,return_value=current_return) as current_save,patch.object(hermes_agent_app,'execute_remote_management_command',return_value={'state':'not_found'}) as current_gateway:
                        current_after,current_notice=hermes_agent_app.submit_confirmed_conversation_edit(current_card,current_card,current_session,current_job,current_kind)
                        self.assertFalse(current_after['ready'])
                        self.assertIn('확인 불가',current_notice)
                        self.assertIn('자동 재저장하지 않습니다',current_notice)
                        with self.assertRaises(gr.Error):hermes_agent_app.submit_confirmed_conversation_edit(current_after,current_after,current_session,current_job,current_kind)
                        current_save.assert_called_once()
                        self.assertEqual(current_gateway.call_count,0 if current_failure else 1)
                        self.assertTrue(current_after['save_attempted'])
                        current_recheck=hermes_agent_app.read_conversation_edit_result(current_after,current_session,current_job,current_kind)
                        self.assertIn('확인 불가',current_recheck)
                        self.assertNotIn('아직 저장하지 않았습니다',current_recheck)
                        current_gateway.return_value={'state':'completed','saved':None}
                        with self.assertRaises(gr.Error):hermes_agent_app.read_conversation_edit_result(current_after,current_session,current_job,current_kind)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_edit_unknown_receipt_never_previews_or_saves(self,current_gateway_mock):
        current_session_identifier='a'*32
        current_source_job_identifier='2026-11-18_00-24-38-0f938e1b'
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source_job_identifier,'job':{'status':{'status':'completed'}}}]}
            if current_command_name=='hermes-effect-receipt':return {'id':'a'*32,'state':'unknown'}
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
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source_job_identifier,'job':{'status':{'status':'completed'}}}]}
            if current_command_name in ('hermes-flux-proposal','hermes-audio-proposal'):return {'id':'a'*32,'job_id':current_payload_record['id'],'proposal':current_proposals[current_command_name.split('-')[1]]}
            if current_command_name=='hermes-service-receipt':return {'state':'not_found','request_id':current_payload_record['request_id'],'service':current_payload_record['service']}
            if current_command_name in ('hermes-flux-delegation-status','hermes-audio-status'):return {'receipt':{'state':'not_found','request_id':current_payload_record['request_id'],'service':'flux-image' if current_command_name=='hermes-flux-delegation-status' else current_payload_record['service']}}
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
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source_job_identifier,'job':{'status':{'status':'completed'}}}]}
            if current_command_name=='hermes-effect-receipt':return {'id':'a'*32,**current_receipt_record,**({'request_id':current_payload_record['request_id']} if current_receipt_record['state']=='completed' else {})}
            if current_command_name=='hermes-effect-save':
                current_receipt_record.update(state='completed',saved=True)
                return {'state':'completed','saved':True}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        def current_load_response(current_job_identifier):return None,{},json.dumps(current_draft_record),None,None,None,None
        def current_preview_response(current_draft_text,current_request_identifier):
            return {'request_id':current_request_identifier,'draft':json.loads(current_draft_text),'token':'test-token'},{'id':'effect-a','before':{'alpha':0.5,'frames':[[0,0,4,4]]},'after':{'alpha':1,'frames':[[0,0,4,4]]},'token':'test-token'},{}
        with patch.object(hermes_agent_app,'load_hermes_effect_edit_proposal',side_effect=current_load_response),patch.object(hermes_agent_app,'review_hermes_effect_edit_draft',side_effect=current_preview_response):
            current_card_record,current_preview_text,_,_=hermes_agent_app.prepare_conversation_edit_review(current_session_identifier,current_source_job_identifier,'effect')
            self.assertIn('불투명도: 0.5 → 1',current_preview_text)
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
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source_job_identifier,'job':{'status':{'status':'completed'}}}]}
            if current_command_name=='hermes-video-proposal':return {'id':'a'*32,'job_id':current_payload_record['id'],'proposal':current_proposal_record.copy()}
            if current_command_name=='hermes-service-receipt':return {'state':'not_found','request_id':current_payload_record['request_id'],'service':current_payload_record['service']}
            if current_command_name=='hermes-video-status':return {'receipt':{'state':'not_found','request_id':current_payload_record['request_id'],'service':current_payload_record['service']}}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_card_record,current_preview_text,current_status_text=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job_identifier,'video')
        self.assertTrue(current_card_record['ready'])
        self.assertEqual(current_card_record['review']['request']['mode'],'text')
        self.assertIn('기본값 포함',current_preview_text)
        current_proposal_record['mode']='reference'
        with self.assertRaises(gr.Error):hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_source_job_identifier,'video')
        self.assertFalse(any(current_call.args[1]=='hermes-delegate-video' for current_call in current_gateway_mock.call_args_list))

    def test_attached_video_submit_requires_same_service_and_confirmed_job(self):
        current_source={'proposal':{'service':'dwpose'},'request_id':'video_request_123'}
        current_review={'source':current_source,'review':{'request_id':'video_request_123'}}
        current_job='2026-11-18_12-00-19-05056f95'
        with patch.object(hermes_agent_app,'review_conversation_video_inputs',return_value=(current_review,'','')), patch.object(hermes_agent_app,'execute_remote_management_command') as current_gateway, patch.object(hermes_agent_app,'read_hermes_video_result') as current_status:
            for current_response in ({'state':'accepted','job_id':current_job},{'state':'accepted','service':'dwpose','job_id':'invalid'}):
                current_gateway.return_value=current_response
                _,current_message=hermes_agent_app.submit_conversation_video_inputs(current_review,current_source,'session','job','{}',None,None,None,None,None)
                self.assertIn('확인 불가',current_message)
            current_status.assert_not_called()
            current_gateway.return_value={'state':'accepted','service':'dwpose','job_id':current_job}
            current_status.return_value=('','접수 기록이 없습니다.')
            _,current_message=hermes_agent_app.submit_conversation_video_inputs(current_review,current_source,'session','job','{}',None,None,None,None,None)
            self.assertIn('확인 불가',current_message)
            self.assertIn('자동 재접수하지 않습니다',current_message)

    def test_attached_video_open_and_review_do_not_read_recovery_status(self):
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_proposal={'service':'dwpose','mode':'image','prompt':''}
        current_calls=[]
        def current_gateway(service,command,payload):
            current_calls.append(command)
            if command=='hermes-service-receipt':return {'request_id':payload['request_id'],'service':'dwpose','state':'accepted','job_id':'2026-11-18_01-00-00-87654321'}
            raise AssertionError(command)
        with patch.object(hermes_agent_app,'find_conversation_session_job'),patch.object(hermes_agent_app,'read_matching_hermes_edit_proposal',return_value=current_proposal),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            current_source,current_settings,*_=hermes_agent_app.open_conversation_video_proposal(current_session,current_job)
            current_review,_,current_notice=hermes_agent_app.review_conversation_video_inputs(current_source,current_session,current_job,current_settings,None,None,None,None,None)
            self.assertIsNone(current_review)
            self.assertIn('상태와 결과 확인',current_notice)
            self.assertTrue(current_calls)
            self.assertEqual(set(current_calls),{'hermes-service-receipt'})

    def test_attached_video_requires_matching_absent_receipt_before_review(self):
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_proposal={'service':'dwpose','mode':'image','prompt':''}
        current_receipt={'state':'not_found'}
        def current_gateway(service,command,payload):
            if command=='hermes-service-receipt':return current_receipt
            raise AssertionError(command)
        with patch.object(hermes_agent_app,'find_conversation_session_job'),patch.object(hermes_agent_app,'read_matching_hermes_edit_proposal',return_value=current_proposal),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway),patch.object(hermes_agent_app,'review_hermes_video_request') as current_review_mock:
            self.assertIsNone(hermes_agent_app.open_conversation_video_proposal(current_session,current_job)[0])
            import hashlib
            current_request='chat_'+hashlib.sha256((current_session+':'+current_job+':video').encode()).hexdigest()
            current_receipt.update(request_id=current_request,service='dwpose')
            current_source,current_settings,*_=hermes_agent_app.open_conversation_video_proposal(current_session,current_job)
            current_responses=[dict(current_receipt),{'state':'not_found','request_id':'wrong','service':'dwpose'}]
            with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_responses):
                current_review,_,current_notice=hermes_agent_app.review_conversation_video_inputs(current_source,current_session,current_job,current_settings,None,None,None,None,None)
            self.assertIsNone(current_review)
            self.assertIn('확인할 수 없습니다',current_notice)
            current_review_mock.assert_not_called()

    def test_attached_flux_rejects_absent_receipt_wrong_service(self):
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_proposal={'service':'flux-billboard','prompt':'tree','width':512,'height':512,'seed':1}
        def current_gateway(service,command,payload):return {'state':'not_found','request_id':payload['request_id'],'service':'flux-building'}
        with patch.object(hermes_agent_app,'find_conversation_session_job'),patch.object(hermes_agent_app,'read_matching_hermes_edit_proposal',return_value=current_proposal),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            with self.assertRaises(gr.Error):hermes_agent_app.open_conversation_flux_reference(current_session,current_job)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_attached_video_revalidates_and_restores_receipt(self,current_gateway_mock):
        import io
        from PIL import Image
        current_session_identifier='a'*32
        current_source_job_identifier='2026-11-18_00-24-38-0f938e1b'
        current_video_job_identifier='2026-11-18_12-00-19-05056f95'
        current_proposal_record={'service':'dwpose','mode':'image','prompt':''}
        current_receipt_record={'state':'not_found'}
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source_job_identifier,'job':{'status':{'status':'completed'}}}]}
            if current_command_name=='hermes-video-proposal':return {'id':'a'*32,'job_id':current_payload_record['id'],'proposal':current_proposal_record.copy()}
            if current_command_name=='hermes-service-receipt':return {'request_id':current_payload_record['request_id'],'service':'dwpose',**current_receipt_record}
            if current_command_name=='hermes-video-status':return {'receipt':{'request_id':current_payload_record['request_id'],'service':'dwpose',**current_receipt_record},'job':{'status':'completed','result_status':'unavailable'}}
            if current_command_name=='hermes-delegate-video':
                current_receipt_record.update(state='accepted',service='dwpose',job_id=current_video_job_identifier)
                return {'state':'accepted','service':'dwpose','job_id':current_video_job_identifier}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_image_stream=io.BytesIO()
        Image.new('RGB',(832,480),'blue').save(current_image_stream,format='PNG')
        current_image_bytes=current_image_stream.getvalue()
        current_open_values=hermes_agent_app.open_conversation_video_proposal(current_session_identifier,current_source_job_identifier)
        current_source_record,current_settings_text=current_open_values[:2]
        current_inputs=[current_source_record,current_session_identifier,current_source_job_identifier,current_settings_text,[current_image_bytes],None,None,None,None]
        current_review_value,current_preview_text,_=hermes_agent_app.review_conversation_video_inputs(*current_inputs)
        self.assertIn('SHA-256',current_preview_text)
        with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_video_inputs(current_review_value,*[current_source_record,'b'*32,*current_inputs[2:]])
        with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_video_inputs(current_review_value,*[current_source_record,current_session_identifier,current_source_job_identifier,current_settings_text,[],None,None,None,None])
        current_cleared_review,current_status_text=hermes_agent_app.submit_conversation_video_inputs(current_review_value,*current_inputs)
        self.assertIsNone(current_cleared_review)
        self.assertIn('completed',current_status_text)
        current_reopened_values=hermes_agent_app.open_conversation_video_proposal(current_session_identifier,current_source_job_identifier)
        self.assertEqual(current_source_record['request_id'],current_reopened_values[0]['request_id'])
        current_rechecked,_,_=hermes_agent_app.review_conversation_video_inputs(*current_inputs)
        self.assertIsNone(current_rechecked)
        self.assertEqual(sum(current_call.args[1]=='hermes-delegate-video' for current_call in current_gateway_mock.call_args_list),1)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_attached_video_rejects_unknown_and_mismatched_mode(self,current_gateway_mock):
        current_session_identifier='a'*32
        current_source_job_identifier='2026-11-18_00-24-38-0f938e1b'
        current_proposal_record={'service':'wan22-fun-control','mode':'pose_video','prompt':'걷는 사람'}
        current_receipt_record={'state':'not_found'}
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source_job_identifier,'job':{'status':{'status':'completed'}}}]}
            if current_command_name=='hermes-video-proposal':return {'id':'a'*32,'job_id':current_payload_record['id'],'proposal':current_proposal_record.copy()}
            if current_command_name=='hermes-service-receipt':return {'request_id':current_payload_record['request_id'],'service':current_payload_record['service'],**current_receipt_record}
            if current_command_name=='hermes-video-status':return {'receipt':{'request_id':current_payload_record['request_id'],'service':current_payload_record['service'],**current_receipt_record}}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_source_record,current_settings_text,*_=hermes_agent_app.open_conversation_video_proposal(current_session_identifier,current_source_job_identifier)
        with self.assertRaises(gr.Error):hermes_agent_app.review_conversation_video_inputs(current_source_record,current_session_identifier,current_source_job_identifier,current_settings_text,[],b'wrong video',None,None,None)
        current_receipt_record['state']='unknown'
        current_review_value,_,current_status_text=hermes_agent_app.review_conversation_video_inputs(current_source_record,current_session_identifier,current_source_job_identifier,current_settings_text,[],None,None,None,None)
        self.assertIsNone(current_review_value)
        self.assertIn('확인 필요',current_status_text)
        self.assertFalse(any(current_call.args[1]=='hermes-delegate-video' for current_call in current_gateway_mock.call_args_list))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_writer_review_submit_and_unknown_are_idempotent(self,current_gateway_mock):
        from tools.review.ui.gradio import hermes_agent_app
        current_session_identifier='a'*32
        current_job_identifier='2026-11-18_00-24-38-0f938e1b'
        current_receipt={'state':'not_found'}
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_job_identifier,'job':{'status':{'status':'completed'}}}]}
            if current_command_name=='hermes-writer-proposal':return {'id':'a'*32,'job_id':current_payload_record['id'],'proposal':{'mode':'write','prompt':'마을 설명'}}
            if current_command_name=='hermes-service-receipt':return {'request_id':current_payload_record['request_id'],'service':'writer-agent',**current_receipt}
            if current_command_name=='hermes-writer-status':return {'receipt':{'request_id':current_payload_record['request_id'],'service':'writer-agent',**current_receipt},'job':{'stage':'review'}}
            if current_command_name=='hermes-delegate-writer':
                current_receipt.update(state='accepted',service='writer-agent',job_id='20261118-120000-12345678')
                return {'state':'accepted','job_id':'20261118-120000-12345678'}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_card,current_preview,current_status=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_job_identifier,'writer')
        self.assertTrue(current_card['ready'])
        self.assertIn('마을 설명',current_preview)
        current_new_card,current_result=hermes_agent_app.submit_conversation_service_review(current_card,current_session_identifier,current_job_identifier,'writer')
        self.assertFalse(current_new_card['ready'])
        self.assertIn('아직 적용되지 않았습니다',current_result)
        self.assertEqual(sum(item.args[1]=='hermes-delegate-writer' for item in current_gateway_mock.call_args_list),1)
        current_receipt.clear()
        current_receipt.update(state='unknown')
        current_unknown_card,_,current_unknown_status=hermes_agent_app.prepare_conversation_service_review(current_session_identifier,current_job_identifier,'writer')
        self.assertFalse(current_unknown_card['ready'])
        self.assertIn('다시 접수하지 않습니다',current_unknown_status)
        with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_service_review(current_unknown_card,current_session_identifier,current_job_identifier,'writer')

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_writer_details_and_apply_reject_mismatched_receipt(self,current_gateway_mock):
        current_card={'session_id':'a'*32,'source_job_id':'job-a','kind':'writer','review':{'request_id':'writer_request_123'}}
        current_gateway_mock.return_value={'receipt':{'state':'accepted','service':'other','job_id':'20261118-120000-12345678'},'job':{'stage':'review','truncated':False,'proposal_hash':'a'*64,'changes':[{'path':'town.md','diff':'-a\n+b'}]}}
        current_result,current_notice=hermes_agent_app.read_conversation_writer_details(current_card,'a'*32,'job-a','writer')
        self.assertIsNone(current_result)
        self.assertIn('자동 재접수하지 마세요',current_notice)
        current_gateway_mock.return_value['receipt'].update(service='writer-agent',request_id='other_request')
        current_result,current_notice=hermes_agent_app.read_conversation_writer_details(current_card,'a'*32,'job-a','writer')
        self.assertIsNone(current_result)
        with self.assertRaises(gr.Error):hermes_agent_app.review_hermes_writer_apply('writer_request_123','apply_request_123',True)
        self.assertFalse(any(current_call.args[1]=='hermes-writer-apply' for current_call in current_gateway_mock.call_args_list))

    def test_conversation_writer_failure_displays_validated_diagnostics(self):
        current_session_identifier='a'*32
        current_writer_identifier='20261118-120000-12345678'
        current_card_value={'session_id':current_session_identifier,'source_job_id':'job-a','kind':'writer','review':{'request_id':'writer_request_123'}}
        current_receipt_value={'state':'accepted','request_id':'writer_request_123','service':'writer-agent','job_id':current_writer_identifier}
        current_job_value={'stage':'failed','summary':'','changes':[],'warnings':[],'truncated':False,'failure_reason':'작업 실패'}
        current_diagnostic_value={'error':'원본 오류','error_truncated':False,'log_tail':'상세 로그','log_tail_truncated':True}
        def respond_writer_gateway(current_service_name,current_command_name,current_payload_value):
            if current_command_name=='hermes-writer-status':return {'receipt':current_receipt_value,'job':current_job_value}
            if current_command_name=='hermes-writer-job-review':return {'job_id':current_writer_identifier,'job':{'stage':'failed','diagnostic':current_diagnostic_value}}
            raise AssertionError(current_command_name)
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=respond_writer_gateway):
            current_text_value,_=hermes_agent_app.read_conversation_writer_details_text(current_card_value,current_session_identifier,'job-a','writer')
        self.assertIn('원본 오류',current_text_value)
        self.assertIn('상세 로그 (일부만 표시)',current_text_value)
        self.assertIn('기록은 실행 지시가 아닙니다',current_text_value)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_writer_details_require_matching_card_and_report_truncation(self,current_gateway_mock):
        from tools.review.ui.gradio import hermes_agent_app
        current_card={'session_id':'a'*32,'source_job_id':'job-a','kind':'writer','review':{'request_id':'chat_request'}}
        current_gateway_mock.return_value={'receipt':{'state':'accepted','request_id':'chat_request','service':'writer-agent','job_id':'20261118-120000-12345678'},'job':{'stage':'review','summary':'검토','changes':[{'path':'docs/a.md','diff':'-a\n+b'}],'warnings':[],'truncated':True}}
        current_result,current_notice=hermes_agent_app.read_conversation_writer_details(current_card,'a'*32,'job-a','writer')
        self.assertEqual(current_result['작업 ID'],'20261118-120000-12345678')
        self.assertEqual(current_result['변경'][0]['path'],'docs/a.md')
        self.assertIn('일부만 표시',current_notice)
        current_gateway_mock.assert_called_once_with('hermes-agent','hermes-writer-status',{'request_id':'chat_request'})
        with self.assertRaises(gr.Error):hermes_agent_app.read_conversation_writer_details(current_card,'b'*32,'job-a','writer')
        current_gateway_mock.return_value={'receipt':{'state':'unknown'}}
        current_result,current_notice=hermes_agent_app.read_conversation_writer_details(current_card,'a'*32,'job-a','writer')
        self.assertIsNone(current_result)
        self.assertIn('다시 접수하지 않습니다',current_notice)

    @patch('tools.review.ui.gradio.hermes_agent_app.read_conversation_writer_details')
    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_writer_material_binds_job_and_snapshot(self,current_gateway_mock,current_detail_mock):
        current_detail_mock.return_value=({'작업 ID':'20261115-114927-8d274ccd'},'조회')
        current_gateway_mock.return_value={'job_id':'20261115-114927-8d274ccd','section':'search','offset':0,'snapshot':'a'*64,'total_characters':6,'content':'abc','next_offset':3}
        current_text,current_state,current_next,current_notice=hermes_agent_app.read_conversation_writer_material_page({},'session','job','writer','search',None,False)
        self.assertEqual(current_text,'abc')
        self.assertTrue(current_next['interactive'])
        self.assertIn('다음 부분',current_notice)
        current_gateway_mock.return_value.update(offset=3,content='def',next_offset=None)
        current_text,current_state,current_next,_=hermes_agent_app.read_conversation_writer_material_page({},'session','job','writer','search',current_state,True)
        self.assertEqual(current_text,'def')
        self.assertFalse(current_next['interactive'])
        with self.assertRaises(gr.Error):
            hermes_agent_app.read_conversation_writer_material_page({},'other','job','writer','search',current_state,True)
        current_gateway_mock.return_value.update(offset=0,content='a',next_offset=True)
        with self.assertRaises(gr.Error):
            hermes_agent_app.read_conversation_writer_material_page({},'session','job','writer','search',None,False)

    def test_conversation_writer_results_show_readable_changes_and_limits(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_result={'작업 ID':'writer-job','상태':'review','요약':'변경 1개','변경 근거':'마을 설정 보완','근거 일부만 표시':False,'검토 범위':{'eligible_chunks':10,'compared_pairs':3,'candidate_pairs':2,'reviewed_pairs':1,'limited':True},'보존 사유':[{'path':'world/a.md','reason':'고유 설정'}],'보존 사유 일부만 표시':True,'변경':[{'path':'world/b.md','diff':'-이전\n+변경'}],'경고':['원문 확인'],'일부만 표시':True}
        current_text=hermes_agent_app.format_conversation_writer_details(current_result)
        for current_expected in ('변경 검토 대기','마을 설정 보완','검토 가능한 문단: 10개','후보 수 제한 적용','world/a.md · 고유 설정','원문 확인','world/b.md','-이전\n+변경','일부만 표시'):
            self.assertIn(current_expected,current_text)
        current_result['탐색 근거']=[{'path':'world/a.md','heading':'마을','text':'관련 원문','truncated':False}]
        current_result['탐색 근거 일부만 표시']=True
        current_evidence_text=hermes_agent_app.format_conversation_writer_details(current_result)
        self.assertIn('탐색 근거 · 원문 일부',current_evidence_text)
        self.assertIn('관련 원문',current_evidence_text)
        self.assertNotIn('eligible_chunks',current_text)
        self.assertEqual(hermes_agent_app.format_conversation_writer_details(None),'')

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_writer_apply_rechecks_target_and_requires_confirmation(self,current_gateway_mock):
        from tools.review.ui.gradio import hermes_agent_app
        current_card={'session_id':'a'*32,'source_job_id':'job-a','kind':'writer','review':{'request_id':'writer_request_123'}}
        current_apply_state={'state':'not_found'}
        current_job_state={'stage':'review','truncated':False,'proposal_hash':'a'*64,'changes':[{'path':'world/town.md','diff':'-a\n+b'}]}
        def current_gateway_response(current_service,current_command,current_payload):
            if current_command=='hermes-writer-apply-status':return current_apply_state.copy()
            if current_command=='hermes-writer-status':return {'receipt':{'state':'accepted','request_id':current_payload['request_id'],'service':'writer-agent','job_id':'20261118-120000-12345678'},'job':current_job_state.copy()}
            if current_command=='hermes-writer-apply':return {'state':'completed',**current_payload}
            raise AssertionError(current_command)
        current_gateway_mock.side_effect=current_gateway_response
        with self.assertRaises(gr.Error):hermes_agent_app.prepare_conversation_writer_apply(current_card,'a'*32,'job-a','writer',False)
        current_review,_,_=hermes_agent_app.prepare_conversation_writer_apply(current_card,'a'*32,'job-a','writer',True)
        current_job_state['proposal_hash']='b'*64
        with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_writer_apply(current_review,current_card,'a'*32,'job-a','writer',True)
        self.assertFalse(any(item.args[1]=='hermes-writer-apply' for item in current_gateway_mock.call_args_list))
        current_job_state['proposal_hash']='a'*64
        _,_,current_message=hermes_agent_app.submit_conversation_writer_apply(current_review,current_card,'a'*32,'job-a','writer',True)
        self.assertIn('적용했습니다',current_message)
        self.assertEqual(sum(item.args[1]=='hermes-writer-apply' for item in current_gateway_mock.call_args_list),1)
        current_apply_state['state']='unknown'
        with self.assertRaises(gr.Error):hermes_agent_app.prepare_conversation_writer_apply(current_card,'a'*32,'job-a','writer',True)

    def test_conversation_writer_proposal_has_review_instruction(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_answer='HERMES_WRITER_PROPOSAL\n{"mode":"write","prompt":"이야기"}\nEND_HERMES_WRITER_PROPOSAL'
        self.assertIn('작가 AI 요청 제안',hermes_agent_app.format_hermes_conversation_answer(current_answer))

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_history_matches_queue_by_service_and_job(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-18_00-24-38-0f938e1b'
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-list':return {'sessions':[{'id':'a'*32,'updated_at':'2026-11-18T00:00:00Z','message_count':1}],'truncated':False}
            if current_command_name=='hermes-management-status':return {'queried_at':'now','queue':{'status':'available','jobs':[{'service':'flux-image','id':current_job_identifier}]}}
            if current_command_name=='hermes-history':return {'records':[{'id':current_job_identifier,'status':{'status':'queued'},'request':{'prompt':'걷는 동작'}}]}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_result_value=operations_history_app.read_operations_history_overview('걷는','queued')
        self.assertEqual(current_result_value[2][0][2],'다른 GPU 서비스 동일 ID · 소유 확인 필요')
        self.assertEqual(current_result_value[4][0][1],'flux-image')
        def current_matched_response(current_service_name,current_command_name,current_payload_record):
            current_value=current_gateway_response(current_service_name,current_command_name,current_payload_record)
            if current_command_name=='hermes-management-status':current_value['queue']['jobs']=[{'service':'hermes-agent','id':current_job_identifier}]*2
            return current_value
        current_gateway_mock.side_effect=current_matched_response
        self.assertEqual(operations_history_app.read_operations_history_overview()[2][0][2],'연결 불확실 · 중복 대기')

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_history_refresh_keeps_only_unique_existing_selected_session(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_session='a'*32
        current_records=[{'id':current_session,'updated_at':'2026-11-18T00:00:00Z','message_count':1}]
        def current_gateway(service,command,payload):
            if command=='hermes-session-list':return {'sessions':current_records,'truncated':False}
            if command=='hermes-session-read':raise ValueError('missing')
            if command=='hermes-management-status':return {'queue':{'status':'available','jobs':[]},'reservations':{'status':'available','records':[],'truncated':False}}
            if command=='hermes-history':return {'records':[]}
            raise AssertionError(command)
        current_gateway_mock.side_effect=current_gateway
        current_value=operations_history_app.read_operations_history_overview('검색','queued',current_session)
        self.assertEqual(current_value[0]['value'],current_session)
        current_records.append(current_records[0].copy())
        current_value=operations_history_app.read_operations_history_overview('','전체',current_session)
        self.assertIsNone(current_value[0]['value'])
        self.assertIn('유일하게 확인할 수 없습니다',current_value[1])
        current_records.clear()
        self.assertIsNone(operations_history_app.read_operations_history_overview('','전체',current_session)[0]['value'])
        current_records[:]=[{'id':'not-a-session','updated_at':'2026-11-18T00:00:00Z','message_count':1}]
        self.assertIsNone(operations_history_app.read_operations_history_overview('','전체','not-a-session')[0]['value'])

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_history_filters_unknown_and_paused_records(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_records=[{'id':'job-a','status':{'status':'paused'},'request':{}},{'id':'job-b','status':{'status':'unknown'},'request':{}},{'id':'job-c','status':{'status':'unexpected'},'request':{}},{'id':'job-d','status':{'status':'completed'},'request':{}}]
        def current_gateway(service,command,payload):
            if command=='hermes-session-list':return {'sessions':[],'truncated':False}
            if command=='hermes-management-status':return {'queue':{'status':'available','jobs':[]},'reservations':{'status':'available','records':[],'truncated':False}}
            if command=='hermes-history':return {'records':current_records}
            raise AssertionError(command)
        current_gateway_mock.side_effect=current_gateway
        current_unknown=operations_history_app.read_operations_history_overview('','unknown')[2]
        self.assertEqual([(item[0],item[1]) for item in current_unknown],[('job-b','확인 불가'),('job-c','확인 불가')])
        current_paused=operations_history_app.read_operations_history_overview('','paused')[2]
        self.assertEqual([(item[0],item[1]) for item in current_paused],[('job-a','일시정지')])
        self.assertEqual(operations_history_app.read_operations_history_overview('job-d','completed')[2][0][1],'완료')

    def test_conversation_restores_verified_session_outside_recent_list(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_session='a'*32
        def current_gateway(service,command,payload):
            if command=='hermes-session-list':return {'sessions':[],'truncated':True}
            if command=='hermes-session-read':return {'id':current_session,'updated_at':'2026-11-01','messages':[{}]}
            raise AssertionError(command)
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            current_choices,current_notice=hermes_agent_app.list_hermes_session_choices(current_session)
            self.assertEqual(current_choices['value'],current_session)
            self.assertIn('이전 세션',current_notice)
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=lambda service,command,payload: {'sessions':[]} if command=='hermes-session-list' else {'id':'b'*32,'updated_at':'x','messages':[]}):
            current_choices,current_notice=hermes_agent_app.list_hermes_session_choices(current_session)
            self.assertIsNone(current_choices['value'])
            self.assertIn('확인 불가',current_notice)

    def test_older_session_page_selection_and_refresh_revalidate_origin(self):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app
        current_records=[{'id':'%032x' % item,'updated_at':'2026-11-01','message_count':item} for item in range(35)]
        current_snapshot='a'*64
        def current_gateway(service,command,payload):
            if command=='hermes-session-list':
                if not payload:return {'sessions':current_records[:2],'truncated':True}
                current_offset=payload.get('offset',0)
                return {'sessions':current_records[current_offset:current_offset+30],'offset':current_offset,'next_offset':30 if current_offset==0 else None,'total':35,'snapshot':current_snapshot}
            if command=='hermes-session-read':return {'id':payload['session_id'],'updated_at':'2026-11-01','messages':[{}]}
            if command=='hermes-history':return {'records':[]}
            if command=='hermes-management-status':return {'queue':{'status':'available','jobs':[]},'reservations':{'status':'available','records':[],'truncated':False}}
            raise AssertionError(command)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=current_gateway):
            current_first=operations_history_app.read_operations_session_page('')
            self.assertEqual(len(current_first[0]),30)
            current_second=operations_history_app.read_older_operations_session_page('',current_first[2])
            self.assertEqual(len(current_second[0]),5)
            current_selected,current_notice=operations_history_app.select_operations_older_session(current_second[0],SimpleNamespace(index=(0,1)))
            self.assertEqual(current_selected['value'],current_records[30]['id'])
            self.assertIn('선택',current_notice)
            current_overview=operations_history_app.read_operations_history_overview('','전체',current_records[30]['id'])
            self.assertEqual(current_overview[0]['value'],current_records[30]['id'])
            self.assertIn('이전 세션 포함',current_overview[1])
            self.assertIsNone(operations_history_app.read_older_operations_session_page('abc',current_first[2])[2])
            current_snapshot='b'*64
            self.assertIsNone(operations_history_app.read_older_operations_session_page('',current_first[2])[2])
            with self.assertRaises(gr.Error):operations_history_app.select_operations_older_session([['x','bad','0']],SimpleNamespace(index=0))

    def test_history_overview_refresh_clears_previous_work_detail(self):
        from tools.review.ui.gradio import operations_history_app
        current_result=operations_history_app.reset_operations_history_detail()
        self.assertEqual(current_result[0],'')
        self.assertIn('선택',current_result[1])
        self.assertEqual(current_result[2:6],('','','',''))
        self.assertIsNone(current_result[6])
        current_blocks=build_async_test_interface(operations_history_app.build_operations_history_interface)
        current_resets=[item for item in current_blocks.fns.values() if getattr(item.fn,'__name__',None)=='reset_operations_history_detail']
        self.assertEqual(len(current_resets),6)
        self.assertTrue(all(len(item.outputs)==7 for item in current_resets))

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_linked_job_search_uses_full_history(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-18_00-00-00-12345678'
        def read_linked_history_gateway(current_service_name,current_command_name,current_payload_value):
            if current_command_name=='hermes-history':
                self.assertEqual(current_payload_value,{'offset':0,'limit':30,'query':current_job_identifier})
                return {'records':[{'id':current_job_identifier,'status':{'status':'completed'},'request':{'prompt':'이전 작업'}}],'offset':0,'next_offset':None,'total':1,'snapshot':'a'*64}
            if current_command_name=='hermes-management-status':return {'queue':{'status':'available','jobs':[]},'reservations':{'status':'available','records':[],'truncated':False}}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=read_linked_history_gateway
        current_result_value=operations_history_app.read_linked_operations_history_page(current_job_identifier,'전체')
        self.assertEqual(current_result_value[0][0][0],current_job_identifier)
        self.assertTrue(current_result_value[5]['open'])
        current_gateway_mock.reset_mock()
        current_result_value=operations_history_app.read_linked_operations_history_page('../invalid','전체')
        self.assertFalse(current_result_value[5]['open'])
        current_gateway_mock.assert_not_called()

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_linked_job_search_warns_when_only_prompt_matches(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_other_identifier='2026-11-18_00-00-01-12345678'
        def read_prompt_match_gateway(current_service_name,current_command_name,current_payload_value):
            if current_command_name=='hermes-history':return {'records':[{'id':current_other_identifier,'status':{'status':'completed'},'request':{'prompt':'참조 '+current_job_identifier}}],'offset':0,'next_offset':None,'total':1,'snapshot':'a'*64}
            if current_command_name=='hermes-management-status':return {'queue':{'status':'available','jobs':[]},'reservations':{'status':'available','records':[],'truncated':False}}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=read_prompt_match_gateway
        current_result_value=operations_history_app.read_linked_operations_history_page(current_job_identifier,'전체')
        self.assertEqual(current_result_value[0][0][0],current_other_identifier)
        self.assertIn('링크한 작업 ID가 확인되지 않습니다',current_result_value[1])
        self.assertIn('다른 작업',current_result_value[1])

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_linked_job_search_does_not_report_empty_on_failure(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-18_00-00-00-12345678'
        for current_response_value in ({'records':[]},OSError('offline')):
            with self.subTest(response=type(current_response_value).__name__):
                current_gateway_mock.side_effect=current_response_value if isinstance(current_response_value,Exception) else None
                if isinstance(current_response_value,dict):current_gateway_mock.return_value=current_response_value
                current_result_value=operations_history_app.read_linked_operations_history_page(current_job_identifier,'전체')
                self.assertEqual(current_result_value[0],[])
                self.assertIn('확인할 수 없거나',current_result_value[1])
                self.assertIsNone(current_result_value[2])
                self.assertTrue(current_result_value[5]['open'])

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_old_job_pages_match_queue_and_reject_changed_list(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_ids=['2026-11-18_00-00-%02d-%08x' % (item,item) for item in range(35)]
        current_snapshot='a'*64
        def current_gateway(service,command,payload):
            if command=='hermes-history':
                current_offset=payload['offset']
                return {'records':[{'id':item,'status':{'status':'queued'},'request':{'prompt':'테스트'}} for item in current_ids[current_offset:current_offset+30]],'offset':current_offset,'next_offset':30 if current_offset==0 else None,'total':35,'snapshot':current_snapshot}
            if command=='hermes-management-status':return {'queue':{'status':'available','jobs':[{'service':'hermes-agent','id':current_ids[30]}]},'reservations':{'status':'available','records':[],'truncated':False}}
            raise AssertionError(command)
        current_gateway_mock.side_effect=current_gateway
        current_first=operations_history_app.read_operations_job_history_page('','전체')
        self.assertEqual(len(current_first[0]),30)
        self.assertTrue(current_first[3]['interactive'])
        self.assertFalse(current_first[4]['interactive'])
        current_second=operations_history_app.read_older_operations_job_history('','전체',current_first[2])
        self.assertEqual(len(current_second[0]),5)
        self.assertEqual(current_second[0][0][2],'대기 기록 확인')
        self.assertTrue(current_second[4]['interactive'])
        self.assertFalse(current_second[3]['interactive'])
        current_back=operations_history_app.read_newer_operations_job_history('','전체',current_second[2])
        self.assertEqual(current_back[0][0][0],current_ids[0])
        current_changed=operations_history_app.read_older_operations_job_history('다른 검색','전체',current_first[2])
        self.assertIsNone(current_changed[2])
        current_snapshot='b'*64
        self.assertIsNone(operations_history_app.read_older_operations_job_history('','전체',current_first[2])[2])
        current_gateway_mock.side_effect=lambda service,command,payload:{'records':[]}
        self.assertIn('다시 조회',operations_history_app.read_operations_job_history_page('','전체')[1])

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_job_page_identifies_other_service_queue_collision(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_jobs=[{'service':'flux-image','id':'same-job'}]
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-history':return {'records':[{'id':'same-job','status':{'status':'queued'},'request':{}}],'offset':0,'next_offset':None,'total':1,'snapshot':'a'*64}
            if current_command_name=='hermes-management-status':return {'queue':{'status':'available','jobs':current_jobs},'reservations':{'status':'available','records':[],'truncated':False}}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        self.assertEqual(operations_history_app.read_operations_job_history_page('','전체')[0][0][2],'다른 GPU 서비스 동일 ID · 소유 확인 필요')
        current_jobs.append({'service':'hermes-agent','id':'same-job'})
        self.assertEqual(operations_history_app.read_operations_job_history_page('','전체')[0][0][2],'대기 기록 확인 · 다른 서비스 동일 ID · 우선 실행 확인 불가')

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_old_job_page_search_sends_filters_to_full_history(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_requests=[]
        def current_gateway(service,command,payload):
            if command=='hermes-history':
                current_requests.append(payload)
                return {'records':[{'id':'old-job','status':{'status':'failed'},'request':{'prompt':'오래된 시험'}}],'offset':0,'next_offset':None,'total':1,'snapshot':'a'*64}
            if command=='hermes-management-status':return {'queue':{'status':'available','jobs':[]},'reservations':{'status':'available','records':[],'truncated':False}}
            raise AssertionError(command)
        current_gateway_mock.side_effect=current_gateway
        current_result=operations_history_app.read_operations_job_history_page('오래된','failed')
        self.assertEqual(current_requests,[{'offset':0,'limit':30,'query':'오래된','status':'failed'}])
        self.assertEqual(current_result[0][0][0],'old-job')
        self.assertIn('1건',current_result[1])

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_history_handles_queue_failure_without_claiming_empty(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-list':return {'sessions':[]}
            if current_command_name=='hermes-management-status':raise OSError('unavailable')
            if current_command_name=='hermes-history':return {'records':[{'id':'job-a','status':{'status':'running'},'request':{'prompt':'시험'}}]}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_result_value=operations_history_app.read_operations_history_overview()
        self.assertEqual(current_result_value[2][0][2],'조회 불가')
        self.assertIn('대기열이 비었다는 뜻이 아닙니다',current_result_value[5])
        self.assertIn('일부 조회 불가',current_result_value[6])

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_session_links_only_valid_session(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_gateway_mock.return_value={'id':'a'*32,'messages':[{'text':'기존 지시','job_id':None,'job':None}],'truncated':False}
        current_rows,current_notice,current_link=operations_history_app.read_operations_session_history('a'*32)
        self.assertIn('접수 확인 필요',current_rows[0])
        self.assertIn('session='+'a'*32,current_link)
        self.assertIn('target="_blank"',current_link)
        with self.assertRaises(gr.Error):operations_history_app.read_operations_session_history('bad&session=evil')

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_session_receipt_links_only_exact_id_and_never_recovers_video(self,current_gateway_mock):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_job_identifier='job-video'
        current_request_identifier='chat_'+hashlib.sha256((current_session_identifier+':'+current_job_identifier+':video').encode()).hexdigest()
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'messages':[{'job_id':current_job_identifier,'session_job_unique':True,'job':{'status':{'status':'completed'},'final_response':'HERMES_VIDEO_PROPOSAL'}}], 'truncated':True}
            if current_command_name=='hermes-video-proposal':return {'id':'a'*32,'job_id':current_job_identifier,'proposal':{'service':'wan22-vace'}}
            if current_command_name=='hermes-video-history':return {'records':[{'request_id':current_request_identifier,'service':'wan22-vace','state':'accepted','job_id':'video-job'}],'truncated':False}
            if current_command_name=='hermes-management-status':return {'queue':{'status':'available','jobs':[{'service':'wan22-vace','id':'video-job'}]},'reservations':{'status':'available','records':[],'truncated':False},'queried_at':'mock'}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_rows,current_notice=operations_history_app.read_operations_session_receipts(current_session_identifier)
        self.assertEqual(current_rows[0],[current_job_identifier,'wan22-vace',current_request_identifier,'접수 기록','video-job','다른 GPU 서비스 동일 ID · 소유 확인 필요','일치 예약 기록 없음 · 상태 별도 확인','해당 없음'])
        self.assertIn('이전 메시지',current_notice)
        self.assertNotIn('hermes-video-status',[item.args[1] for item in current_gateway_mock.call_args_list])
        def current_wrong_service_response(current_service_name,current_command_name,current_payload_record):
            current_result=current_gateway_response(current_service_name,current_command_name,current_payload_record)
            if current_command_name=='hermes-video-history':current_result['records'][0]['service']='dwpose'
            return current_result
        current_gateway_mock.side_effect=current_wrong_service_response
        self.assertIn('확인 필요',operations_history_app.read_operations_session_receipts(current_session_identifier)[0][0][3])

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_receipt_does_not_link_unverified_duplicate_job(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_message={'job_id':'job-a','job':{'status':{'status':'completed'},'final_response':'HERMES_KIMODO_PROPOSAL'}}
        for current_unique,current_truncated in ((False,False),(None,True)):
            with self.subTest(unique=current_unique,truncated=current_truncated):
                current_message['session_job_unique']=current_unique
                current_gateway_mock.return_value={'id':'a'*32,'messages':[current_message],'truncated':current_truncated}
                current_rows,current_notice=operations_history_app.read_operations_session_receipts('a'*32)
                self.assertEqual(current_rows,[])
                self.assertIn('확인하지 못한 메시지',current_notice)
                current_gateway_mock.assert_called_once_with('hermes-agent','hermes-session-view',{'session_id':'a'*32})
                current_gateway_mock.reset_mock()

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_session_finds_flux_profile_receipt_in_legacy_view(self,current_gateway_mock):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_session='a'*32
        current_job='job-flux'
        current_request='chat_'+hashlib.sha256((current_session+':'+current_job+':flux').encode()).hexdigest()
        def respond_history_gateway(current_service,current_command,current_payload):
            if current_command=='hermes-session-view':return {'id':'a'*32,'messages':[{'job_id':current_job,'job':{'status':{'status':'completed'},'final_response':'HERMES_FLUX_PROPOSAL'}}],'truncated':False}
            if current_command=='hermes-flux-proposal':return {'id':'a'*32,'job_id':current_job,'proposal':{'service':'flux-prop'}}
            if current_command=='hermes-flux-profile-history':
                self.assertEqual(current_payload,{'service':'flux-prop'})
                return {'records':[{'request_id':current_request,'service':'flux-prop','state':'accepted','job_id':'2026-11-18_00-00-00-12345678'}],'truncated':False}
            if current_command=='hermes-management-status':return {'queue':{'status':'available','jobs':[]},'reservations':{'status':'available','records':[],'truncated':False}}
            raise AssertionError(current_command)
        current_gateway_mock.side_effect=respond_history_gateway
        current_rows,_=operations_history_app.read_operations_session_receipts(current_session)
        self.assertEqual(current_rows[0][1:5],['flux-prop',current_request,'접수 기록','2026-11-18_00-00-00-12345678'])
        self.assertNotIn('hermes-flux-delegation-history',[current_call.args[1] for current_call in current_gateway_mock.call_args_list])

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_session_receipt_gpu_observations_are_independent(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'messages':[{'job_id':'job-a','job':{'status':{'status':'completed'},'final_response':'HERMES_KIMODO_PROPOSAL'}}]}
            if current_command_name=='hermes-kimodo-proposal':return {'id':'a'*32,'job_id':'job-a','proposal':{}}
            if current_command_name=='hermes-delegation-status':return {'state':'accepted','request_id':current_payload_record['request_id'],'service':'kimodo','job_id':'target-a'}
            if current_command_name=='hermes-management-status':return {'queue':{'status':'unavailable'},'reservations':{'status':'available','records':[{'state':'recorded','service':'kimodo','job_id':'target-a','required_memory_mib':50}],'truncated':False},'queried_at':'mock'}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_rows,current_notice=operations_history_app.read_operations_session_receipts('a'*32)
        self.assertEqual(current_rows[0][5:7],['조회 불가','다른 GPU 서비스 동일 ID · 소유 확인 필요'])
        self.assertIn('완료나 생존을 뜻하지 않습니다',current_notice)
        def current_mismatch_response(current_service_name,current_command_name,current_payload_record):
            current_result=current_gateway_response(current_service_name,current_command_name,current_payload_record)
            if current_command_name=='hermes-management-status':current_result['queue']={'status':'available','jobs':[{'service':'other','id':'target-a'}]}
            return current_result
        current_gateway_mock.side_effect=current_mismatch_response
        self.assertEqual(operations_history_app.read_operations_session_receipts('a'*32)[0][0][5],'다른 GPU 서비스 동일 ID · 소유 확인 필요')

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_receipts_clear_rows_on_session_validation_failure(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_page_state={'session_id':'a'*32,'offset':0,'snapshot':'a'*64}
        for current_session_value,current_response_value in (('bad',{}),('a'*32,{'id':'a'*32,'offset':0,'snapshot':'a'*64,'messages':None})):
            current_gateway_mock.return_value=current_response_value
            current_rows_value,current_notice_text=operations_history_app.read_operations_current_page_receipts(current_session_value,current_page_state)
            self.assertEqual(current_rows_value,[])
            self.assertIn('다시 조회',current_notice_text)

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_receipts_reject_missing_or_wrong_session_identity(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        for current_session_value in (None,'b'*32):
            current_session_record={'messages':[{'job_id':'job-1','job':{'status':{'status':'completed'},'final_response':'HERMES_VIDEO_PROPOSAL'}}]}
            if current_session_value is not None:current_session_record['id']=current_session_value
            current_gateway_mock.reset_mock()
            current_gateway_mock.return_value=current_session_record
            with self.assertRaises(ValueError):operations_history_app.read_operations_session_receipts('a'*32)
            current_gateway_mock.assert_called_once_with('hermes-agent','hermes-session-view',{'session_id':'a'*32})

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_wan_fun_uses_verified_queue_service(self,current_gateway_mock):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_session='a'*32
        current_job='job-video'
        current_request='chat_'+hashlib.sha256((current_session+':'+current_job+':video').encode()).hexdigest()
        def current_gateway_response(current_service,current_command,current_payload):
            if current_command=='hermes-session-view':return {'id':'a'*32,'messages':[{'job_id':current_job,'job':{'status':{'status':'completed'},'final_response':'HERMES_VIDEO_PROPOSAL'}}]}
            if current_command=='hermes-video-proposal':return {'id':'a'*32,'job_id':current_job,'proposal':{'service':'wan22-fun-control'}}
            if current_command=='hermes-video-history':return {'records':[{'request_id':current_request,'service':'wan22-fun-control','state':'accepted','job_id':'video-job'}],'truncated':False}
            if current_command=='hermes-management-status':return {'queue':{'status':'available','jobs':[{'service':'wan-fun','id':'video-job'}]},'reservations':{'status':'available','records':[{'state':'recorded','service':'wan-fun','job_id':'video-job','required_memory_mib':10}],'truncated':False}}
            raise AssertionError(current_command)
        current_gateway_mock.side_effect=current_gateway_response
        current_row=operations_history_app.read_operations_session_receipts(current_session)[0][0]
        self.assertIn('생성: 공용 wan-fun 대기열 · 소유 확인 필요',current_row[5])
        self.assertIn('생성: 공용 wan-fun 예약 · 소유 확인 필요',current_row[6])
        self.assertIn('준비:',current_row[5])
        self.assertIn('준비:',current_row[6])
        def current_verified_response(current_service,current_command,current_payload):
            current_result=current_gateway_response(current_service,current_command,current_payload)
            if current_command=='hermes-management-status':
                current_result['queue']['jobs'][0]['source_service']='wan22-fun-control'
                current_result['reservations']['records'][0]['source_service']='wan22-fun-control'
            return current_result
        current_gateway_mock.side_effect=current_verified_response
        current_row=operations_history_app.read_operations_session_receipts(current_session)[0][0]
        self.assertIn('생성: 대기 기록 확인 · 원 서비스 확인',current_row[5])
        self.assertIn('생성: 예약 기록 확인 · 원 서비스 확인',current_row[6])
        self.assertIn('준비:',current_row[5])
        self.assertIn('준비:',current_row[6])
        self.assertIsNone(operations_history_app.resolve_operations_queue_identity('kimodo'))
        self.assertIsNone(operations_history_app.resolve_operations_queue_identity('flux-image'))
        self.assertIsNone(operations_history_app.resolve_operations_queue_identity('flux-building'))
        self.assertEqual(operations_history_app.resolve_operations_queue_identity('flux-expression'),'flux-expression')

    def test_shared_reservation_reports_unobserved_records_for_every_match(self):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='target-a'
        current_reservation_cases=[
            ({('image',current_job_identifier):['recorded','recorded']},'중복 예약'),
            ({('other',current_job_identifier):['recorded']},'다른 GPU 서비스'),
            ({('image',current_job_identifier):['recorded']},'소유 확인 필요'),
            ({('image',current_job_identifier):['recorded'],('source','image','kimodo',current_job_identifier):['recorded']},'원 서비스 확인'),
        ]
        for current_reservation_index,current_expected_label in current_reservation_cases:
            with self.subTest(current_expected_label=current_expected_label):
                current_result_label=operations_history_app.label_operations_shared_reservation_record(current_reservation_index,True,'image','kimodo',current_job_identifier)
                self.assertIn(current_expected_label,current_result_label)
                self.assertIn('미확인 기록 포함',current_result_label)
                current_complete_label=operations_history_app.label_operations_shared_reservation_record(current_reservation_index,False,'image','kimodo',current_job_identifier)
                self.assertNotIn('미확인 기록 포함',current_complete_label)

    def test_gpu_source_display_accepts_only_expected_pool_and_service(self):
        from tools.review.ui.gradio import operations_history_app
        self.assertEqual(operations_history_app.read_operations_verified_source('image','kimodo'),'kimodo')
        self.assertEqual(operations_history_app.read_operations_verified_source('flux-image','flux-character'),'flux-character')
        self.assertIsNone(operations_history_app.read_operations_verified_source('image','flux-character'))
        self.assertIsNone(operations_history_app.read_operations_verified_source('image',[]))
        current_record={'reservations':{'status':'available','truncated':False,'records':[{'state':'recorded','service':'image','source_service':'kimodo','job_id':'job-a','required_memory_mib':1}]}}
        _,_,current_rows,_=operations_history_app.summarize_operations_reservation_snapshot(current_record)
        self.assertEqual(current_rows[0][5],'kimodo')
        current_record['reservations']['records'][0]['source_service']='flux-character'
        _,_,current_rows,_=operations_history_app.summarize_operations_reservation_snapshot(current_record)
        self.assertEqual(current_rows[0][5],'미확인')

    def test_dedicated_history_labels_distinguish_unverified_source(self):
        from collections import Counter
        from tools.review.ui.gradio import operations_history_app
        current_queue_counts=Counter({('music-heartmula','job-1'):1})
        current_source_counts=Counter()
        current_reservation_index={('music-heartmula','job-1'):['recorded']}
        self.assertIn('원 서비스 확인 필요',operations_history_app.label_operations_verified_dedicated_queue(current_queue_counts,current_source_counts,'music-heartmula','music-heartmula','job-1'))
        self.assertIn('원 서비스 확인 필요',operations_history_app.label_operations_verified_dedicated_reservation(current_reservation_index,False,'music-heartmula','music-heartmula','job-1'))
        current_source_counts[('music-heartmula','music-heartmula','job-1')]=1
        current_reservation_index[('source','music-heartmula','music-heartmula','job-1')]=['recorded']
        self.assertIn('원 서비스 확인',operations_history_app.label_operations_verified_dedicated_queue(current_queue_counts,current_source_counts,'music-heartmula','music-heartmula','job-1'))
        self.assertIn('원 서비스 확인',operations_history_app.label_operations_verified_dedicated_reservation(current_reservation_index,False,'music-heartmula','music-heartmula','job-1'))

    def test_dedicated_queue_source_requires_verified_path_for_selection(self):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-18_12-00-00-12345678'
        current_rows=[['1','music-heartmula',current_job_identifier,'미확인']]
        current_target,current_notice,current_button=operations_history_app.select_operations_priority_target(current_rows,SimpleNamespace(index=0))
        self.assertIsNone(current_target)
        self.assertFalse(current_button['interactive'])
        current_rows[0][3]='music-heartmula'
        current_target,current_notice,current_button=operations_history_app.select_operations_priority_target(current_rows,SimpleNamespace(index=0))
        self.assertEqual(current_target,{'service':'music-heartmula','id':current_job_identifier})
        self.assertTrue(current_button['interactive'])
        self.assertEqual(operations_history_app.read_operations_verified_source('wan-fun','wan22-fun-control'),'wan22-fun-control')
        self.assertIsNone(operations_history_app.read_operations_verified_source('music-heartmula','music-magenta'))
        current_reservation_rows=[['정리 확인 필요','music-heartmula',current_job_identifier,'100','미제공','미확인']]
        self.assertIsNone(operations_history_app.select_operations_reservation_inspection(current_reservation_rows,SimpleNamespace(index=0))[0])
        self.assertNotIn('<a ',operations_history_app.select_operations_reservation_target(current_reservation_rows,SimpleNamespace(index=0)))
        current_reservation_rows[0][5]='music-heartmula'
        self.assertEqual(operations_history_app.select_operations_reservation_inspection(current_reservation_rows,SimpleNamespace(index=0))[0],{'service':'music-heartmula','job_id':current_job_identifier})

    def test_reservation_source_is_checked_independently_and_no_path_leaks(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from tools.review.common import gpu_job_queue
        from tools.review.domains.hermes_agent.management_observer import read_hermes_gpu_reservation_snapshot
        from tools.review.ui.gradio import operations_history_app
        with TemporaryDirectory() as current_temp:
            current_root=Path(current_temp)
            current_job=current_root/'.tmp/test/kimodo/2026-11-18_12-00-00-12345678'
            current_job.mkdir(parents=True)
            current_active=current_root/'.tmp/gpu-queue/active'
            current_active.mkdir(parents=True)
            import os
            current_start=Path(f'/proc/{os.getpid()}/stat').read_text().rpartition(') ')[2].split()[19]
            current_record={'path':str(current_job),'service':'image','required_memory_mib':500,'pid':os.getpid(),'pid_start_token':current_start}
            (current_active/'one.json').write_text(json.dumps(current_record))
            with patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root):
                current_snapshot=read_hermes_gpu_reservation_snapshot(current_active.parent)
            self.assertEqual(current_snapshot['records'][0]['source_service'],'kimodo')
            self.assertNotIn(str(current_root),str(current_snapshot))
            current_index,current_unmatched,_,_=operations_history_app.summarize_operations_reservation_snapshot({'reservations':current_snapshot})
            current_label=operations_history_app.label_operations_shared_reservation_record(current_index,current_unmatched,'image','kimodo',current_job.name)
            self.assertEqual(current_label,'예약 기록 확인 · 원 서비스 확인')
            self.assertEqual(operations_history_app.label_operations_shared_reservation_record(current_index,current_unmatched,'image','dwpose',current_job.name),'공용 image 예약 · 소유 확인 필요')
            current_snapshot['records'].append(current_snapshot['records'][0].copy())
            current_index,current_unmatched,_,_=operations_history_app.summarize_operations_reservation_snapshot({'reservations':current_snapshot})
            self.assertEqual(operations_history_app.label_operations_shared_reservation_record(current_index,current_unmatched,'image','kimodo',current_job.name),'연결 불확실 · 중복 예약')
            current_snapshot['records'][0].pop('source_service')
            current_snapshot['records'].pop()
            current_index,current_unmatched,_,_=operations_history_app.summarize_operations_reservation_snapshot({'reservations':current_snapshot})
            self.assertEqual(operations_history_app.label_operations_shared_reservation_record(current_index,current_unmatched,'image','kimodo',current_job.name),'공용 image 예약 · 소유 확인 필요')

    def test_shared_gpu_observation_distinguishes_absence_duplicate_and_other_pool(self):
        from collections import Counter
        from tools.review.ui.gradio import operations_history_app
        current_counts=Counter()
        current_sources=Counter()
        current_job='job-a'
        current_queue=operations_history_app.label_operations_shared_queue_record
        self.assertEqual(current_queue(current_counts,current_sources,'image','kimodo',current_job),'일치 대기 기록 없음 · 상태 별도 확인')
        current_counts[('other',current_job)]=1
        self.assertEqual(current_queue(current_counts,current_sources,'image','kimodo',current_job),'다른 GPU 서비스 동일 ID · 소유 확인 필요')
        current_counts[('image',current_job)]=2
        self.assertEqual(current_queue(current_counts,current_sources,'image','kimodo',current_job),'연결 불확실 · 중복 대기')
        current_counts[('image',current_job)]=1
        self.assertEqual(current_queue(current_counts,current_sources,'image','kimodo',current_job),'공용 image 대기열 · 소유 확인 필요')
        current_sources[('image','kimodo',current_job)]=1
        self.assertEqual(current_queue(current_counts,current_sources,'image','kimodo',current_job),'대기 기록 확인 · 다른 서비스 동일 ID · 우선 실행 확인 불가')
        current_reservation=operations_history_app.label_operations_shared_reservation_record
        self.assertEqual(current_reservation({},False,'image','kimodo',current_job),'일치 예약 기록 없음 · 상태 별도 확인')
        self.assertEqual(current_reservation({},True,'image','kimodo',current_job),'미확인 예약 포함')
        self.assertEqual(current_reservation({('other',current_job):['recorded']},False,'image','kimodo',current_job),'다른 GPU 서비스 동일 ID · 소유 확인 필요')
        self.assertEqual(current_reservation({('image',current_job):['recorded','recorded']},False,'image','kimodo',current_job),'연결 불확실 · 중복 예약')

    def test_gpu_source_identity_checks_storage_and_symlinks(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from tools.review.common.gpu_job_queue import identify_gpu_queue_source
        with TemporaryDirectory() as current_temp:
            current_root=Path(current_temp)
            current_job=current_root/'.tmp/test/kimodo/job-1'
            current_job.mkdir(parents=True)
            self.assertEqual(identify_gpu_queue_source(current_job,'image',current_root),'kimodo')
            self.assertIsNone(identify_gpu_queue_source(current_job,'flux-image',current_root))
            current_other=current_root/'.tmp/test/flux-image-generator/job-1'
            current_other.mkdir(parents=True)
            self.assertEqual(identify_gpu_queue_source(current_other,'flux-image',current_root),'flux-image')
            current_link=current_root/'.tmp/test/dwpose'
            current_link.symlink_to(current_job.parent,target_is_directory=True)
            self.assertIsNone(identify_gpu_queue_source(current_link/'job-1','image',current_root))
            self.assertIsNone(identify_gpu_queue_source(current_root/'.tmp/test/kimodo/../kimodo/job-1','image',current_root))
            for current_service_name,current_directory_name in (('qwen-21','qwen-image-21'),('qwen-21-circular','qwen-image-21-circular'),('mannequin-generator','mannequin-generator'),('prop-generator','prop-generator'),('vegetation-generator','vegetation-generator'),('expression','expression-generator'),('seamless-tile','seamless-tile-generator'),('floor-tile','qwen-image-2512/floor-tile'),('billboard-generator','billboard-generator'),('building-generator','building-generator')):
                current_qwen_job=current_root/'.tmp/test'/current_directory_name/'job-2'
                current_qwen_job.mkdir(parents=True)
                self.assertEqual(identify_gpu_queue_source(current_qwen_job,'image',current_root),current_service_name)
                self.assertIsNone(identify_gpu_queue_source(current_qwen_job,'flux-image',current_root))
                from tools.review.ui.gradio.operations_history_app import read_operations_verified_source
                self.assertEqual(read_operations_verified_source('image',current_service_name),current_service_name)
            current_nested_root=current_root/'.tmp/test/qwen-image-2512'
            current_nested_root.rename(current_root/'.tmp/test/actual-nested')
            current_nested_root.symlink_to(current_root/'.tmp/test/actual-nested',target_is_directory=True)
            self.assertIsNone(identify_gpu_queue_source(current_nested_root/'floor-tile/job-2','image',current_root))

    def test_operations_links_isolated_receipt_to_verified_queue_ticket(self):
        import hashlib
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from tools.review.common import gpu_job_queue
        from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
        from tools.review.ui.gradio import operations_history_app
        current_session='a'*32
        current_source_job='2026-11-18_00-24-38-0f938e1b'
        current_target_job='2026-11-18_12-00-00-12345678'
        current_request='chat_'+hashlib.sha256((current_session+':'+current_source_job).encode()).hexdigest()
        with TemporaryDirectory() as current_directory:
            current_root=Path(current_directory)
            current_job_path=current_root/'.tmp/test/kimodo'/current_target_job
            current_job_path.mkdir(parents=True)
            (current_job_path/'status.json').write_text('{"status":"queued"}')
            (current_job_path/'gpu-command.json').write_text('{"service":"image"}')
            current_ticket=current_root/'ticket.json'
            current_ticket.write_text(json.dumps({'pid':123,'path':str(current_job_path)}))
            current_store=HermesDelegationStore(current_root/'receipts')
            current_store.execute_delegation_once(current_request,{},lambda current_request_value:{'id':current_target_job})
            def respond_isolated_gateway(current_service,current_command,current_payload):
                if current_command=='hermes-session-view':return {'id':current_session,'truncated':False,'messages':[{'job_id':current_source_job,'session_job_unique':True,'job':{'status':{'status':'completed'},'final_response':'HERMES_KIMODO_PROPOSAL'}}]}
                if current_command=='hermes-kimodo-proposal':return {'id':'a'*32,'job_id':current_source_job,'proposal':{}}
                if current_command=='hermes-delegation-status':return {**current_store.read_delegation_status(current_payload['request_id']),'request_id':current_payload['request_id'],'service':'kimodo'}
                if current_command=='hermes-management-status':return {'queue':{'status':'available',**gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)},'reservations':{'status':'available','records':[],'truncated':False}}
                raise AssertionError(current_command)
            with patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root),patch.object(gpu_job_queue,'read_priority_tickets',return_value=[current_ticket]),patch.object(gpu_job_queue.os,'kill'),patch.object(operations_history_app,'execute_remote_management_command',side_effect=respond_isolated_gateway):
                current_rows,_=operations_history_app.read_operations_session_receipts(current_session)
            self.assertEqual(current_rows[0][1:6],['kimodo',current_request,'접수 기록',current_target_job,'대기 기록 확인 · 원 서비스 확인'])
            self.assertNotIn(str(current_root),str(current_rows))

    def test_gpu_ticket_source_is_optional_and_does_not_expose_paths(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from tools.review.common import gpu_job_queue
        with TemporaryDirectory() as current_temp:
            current_root=Path(current_temp)
            current_job=current_root/'.tmp/test/kimodo/job-1'
            current_job.mkdir(parents=True)
            (current_job/'status.json').write_text('{"status":"queued"}')
            (current_job/'gpu-command.json').write_text('{"service":"image"}')
            current_ticket=current_root/'ticket.json'
            current_ticket.write_text(json.dumps({'pid':123,'path':str(current_job)}))
            with patch.object(gpu_job_queue,'WORKFLOW_ROOT_DIRECTORY',current_root),patch.object(gpu_job_queue,'read_priority_tickets',return_value=[current_ticket]),patch.object(gpu_job_queue.os,'kill'):
                current_legacy=gpu_job_queue.list_waiting_gpu_jobs()
                current_extended=gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True)
            self.assertEqual(current_legacy,{'jobs':[{'id':'job-1','service':'image'}]})
            self.assertEqual(current_extended['jobs'][0]['source_service'],'kimodo')
            self.assertEqual(len(current_extended['jobs'][0]['ticket_revision']),64)
            self.assertNotIn(str(current_root),str(current_extended))

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_shared_queue_requires_verified_unique_source(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_tickets=[{'service':'image','id':'target-a','source_service':'kimodo'}]
        def current_gateway_response(current_service,current_command,current_payload):
            if current_command=='hermes-session-view':return {'id':'a'*32,'messages':[{'job_id':'job-a','job':{'status':{'status':'completed'},'final_response':'HERMES_KIMODO_PROPOSAL'}}]}
            if current_command=='hermes-kimodo-proposal':return {'id':'a'*32,'job_id':'job-a','proposal':{}}
            if current_command=='hermes-delegation-status':return {'state':'accepted','request_id':current_payload['request_id'],'service':'kimodo','job_id':'target-a'}
            if current_command=='hermes-management-status':return {'queue':{'status':'available','jobs':current_tickets},'reservations':{'status':'available','records':[],'truncated':False}}
            raise AssertionError(current_command)
        current_gateway_mock.side_effect=current_gateway_response
        self.assertEqual(operations_history_app.read_operations_session_receipts('a'*32)[0][0][5],'대기 기록 확인 · 원 서비스 확인')
        current_tickets.append({'service':'image','id':'target-a'})
        self.assertEqual(operations_history_app.read_operations_session_receipts('a'*32)[0][0][5],'연결 불확실 · 중복 대기')
        current_tickets[:]=[{'service':'image','id':'target-a'},{'service':'other','id':'target-a','source_service':'kimodo'}]
        self.assertEqual(operations_history_app.read_operations_session_receipts('a'*32)[0][0][5],'공용 image 대기열 · 소유 확인 필요')
        current_tickets[:]=[{'service':'image','id':'target-a'}]
        self.assertEqual(operations_history_app.read_operations_session_receipts('a'*32)[0][0][5],'공용 image 대기열 · 소유 확인 필요')

    def test_history_job_link_validates_identifiers_and_restores_through_session_lookup(self):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app,hermes_agent_app
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_rows=[['시각','이전 지시',current_job,'completed','']]
        current_link=operations_history_app.select_operations_session_job_link(current_session,current_rows,SimpleNamespace(index=(0,1)))
        self.assertIn('?session='+current_session+'&amp;job='+current_job,current_link)
        current_rows[0][2]='bad&job=<script>'
        current_link=operations_history_app.select_operations_session_job_link(current_session,current_rows,SimpleNamespace(index=0))
        self.assertNotIn('<script>',current_link)
        self.assertIn('작업 ID를 확인할 수 없습니다',current_link)
        with self.assertRaises(gr.Error):operations_history_app.select_operations_session_job_link('bad',current_rows,SimpleNamespace(index=0))
        with patch.object(hermes_agent_app,'select_older_conversation_job',return_value=(gr.update(value=current_job),'selected')) as current_lookup:
            self.assertEqual(hermes_agent_app.restore_linked_conversation_job(current_session,current_job)[0]['value'],current_job)
            current_lookup.assert_called_once_with(current_session,current_job)
        with patch.object(hermes_agent_app,'select_older_conversation_job',side_effect=gr.Error('wrong session')):
            self.assertIn('확인할 수 없습니다',hermes_agent_app.restore_linked_conversation_job(current_session,current_job)[1])

    def test_flux_reference_composed_confirmation_rejects_changed_image_and_cancels(self):
        from PIL import Image
        from tools.review.ui.gradio import hermes_agent_app
        current_blocks=build_hermes_test_interface(include_advanced_controls=False)
        def current_callback_name(current_function):
            current_closure=dict(zip(current_function.__code__.co_freevars,(item.cell_contents for item in current_function.__closure__ or ())))
            return getattr(current_closure.get('generation_callback_value'),'__name__',None)
        current_confirmation_record=next(item for item in current_blocks.fns.values() if item.fn and item.fn.__name__=='execute_confirmed_generation' and current_callback_name(item.fn)=='submit_conversation_flux_reference')
        current_prepare_record=next(item for item in current_blocks.fns.values() if item.fn and item.fn.__name__=='prepare_generation_confirmation' and list(item.inputs)==list(current_confirmation_record.inputs[1:]))
        current_cancel_record=next(item for item in current_blocks.fns.values() if item.fn and item.fn.__name__=='cancel_generation_confirmation' and item.inputs and item.inputs[0] is current_confirmation_record.inputs[0])
        current_session='a'*32
        current_source='2026-11-18_00-00-00-12345678'
        current_source_record={'session_id':current_session,'source_job_id':current_source,'proposal':{'service':'flux-building'},'request_id':'request_123'}
        current_review_record={'source':current_source_record,'review':{'request_id':'request_123'}}
        current_image=Image.new('RGB',(16,16),'red')
        current_changed=Image.new('RGB',(16,16),'blue')
        current_inputs=(current_review_record,current_source_record,current_session,current_source,current_image,None)
        current_pending=current_prepare_record.fn(*current_inputs)[0]
        with patch.object(hermes_agent_app,'review_conversation_flux_reference') as current_review_mock:
            with self.assertRaises(gr.Error):list(current_confirmation_record.fn(current_pending,*current_inputs[:-2],current_changed,None))
            current_review_mock.assert_not_called()
            with self.assertRaises(gr.Error):list(current_confirmation_record.fn(current_pending,*current_inputs))
        current_pending=current_prepare_record.fn(*current_inputs)[0]
        self.assertIsNone(current_cancel_record.fn(current_pending,current_review_record)[0])
        with self.assertRaises(gr.Error):list(current_confirmation_record.fn(current_pending,*current_inputs))
        current_pending=current_prepare_record.fn(*current_inputs)[0]
        current_accepted={'state':'accepted','service':'flux-building','job_id':'2026-11-18_01-00-00-87654321'}
        with patch.object(hermes_agent_app,'review_conversation_flux_reference',return_value=(current_review_record,'','')),patch.object(hermes_agent_app,'read_hermes_flux_profile_result',return_value=(current_accepted['job_id'],'대기')),patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_accepted) as current_gateway:
            current_result=list(current_confirmation_record.fn(current_pending,*current_inputs))
            self.assertIn('접수 기록',current_result[0][1])
            current_gateway.assert_called_once()
            with self.assertRaises(gr.Error):list(current_confirmation_record.fn(current_pending,*current_inputs))

    def test_uncertain_conversation_confirmation_leaves_queue_button_disabled(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_blocks=build_hermes_test_interface(include_advanced_controls=False)
        def current_callback_name(current_function):
            current_closure=dict(zip(current_function.__code__.co_freevars,(item.cell_contents for item in current_function.__closure__ or ())))
            return getattr(current_closure.get('generation_callback_value'),'__name__',None)
        current_confirm=next(item for item in current_blocks.fns.values() if item.fn and item.fn.__name__=='execute_confirmed_generation' and current_callback_name(item.fn)=='submit_conversation_service_review')
        current_prepare=next(item for item in current_blocks.fns.values() if item.fn and item.fn.__name__=='prepare_generation_confirmation' and list(item.inputs)==list(current_confirm.inputs[1:]))
        current_cancel=next(item for item in current_blocks.fns.values() if item.fn and item.fn.__name__=='cancel_generation_confirmation' and item.inputs and item.inputs[0] is current_confirm.inputs[0])
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_card={'session_id':current_session,'source_job_id':current_job,'kind':'translation','service':'prompt-translation','review':{'request_id':'request_123','request':{}},'ready':True}
        current_inputs=(current_card,current_session,current_job,'translation')
        current_pending=current_prepare.fn(*current_inputs)[0]
        with patch.object(hermes_agent_app,'prepare_conversation_service_review',return_value=(current_card.copy(),'','')),patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=OSError('response lost')) as current_gateway:
            current_result=list(current_confirm.fn(current_pending,*current_inputs))[0]
            self.assertFalse(current_result[0]['ready'])
            self.assertIn('확인 불가',current_result[1])
            self.assertFalse(current_cancel.fn(current_pending,current_result[0])[2]['interactive'])
            with self.assertRaises(gr.Error):list(current_confirm.fn(current_pending,*current_inputs))
            current_gateway.assert_called_once()

    def test_conversation_route_guides_only_one_valid_proposal_without_execution(self):
        import json
        from tools.review.ui.gradio import hermes_agent_app
        current_session='a'*32
        current_source='2026-11-18_00-00-00-12345678'
        def current_answer(kind,payload):return 'HERMES_'+kind+'_PROPOSAL\n'+json.dumps(payload,ensure_ascii=False)+'\nEND_HERMES_'+kind+'_PROPOSAL'
        current_cases=[
            ('FLUX',{'service':'flux-prop','prompt':'crate','width':512,'height':512,'seed':42},0,'flux'),
            ('FLUX',{'service':'flux-expression','prompt':'joy','width':512,'height':512,'seed':42},2,None),
            ('VIDEO',{'service':'wan22-vace','mode':'text','prompt':'a scene'},3,None),
            ('WRITER',{'mode':'write','prompt':'마을 소개'},0,'writer'),
            ('FIELD',{'map':'moss-clearing','revision':'a'*64,'cells':[{'column':1,'row':2,'tile':'m','height':0,'blocked':False}]},1,'field'),
        ]
        for current_kind,current_payload,current_area,current_selection in current_cases:
            with self.subTest(kind=current_kind,area=current_area):
                current_match={'job':{'final_response':current_answer(current_kind,current_payload),'final_response_truncated':False}}
                with patch.object(hermes_agent_app,'find_conversation_session_job',return_value=current_match),patch.object(hermes_agent_app,'execute_remote_management_command') as current_gateway:
                    current_result=hermes_agent_app.route_conversation_proposal(current_session,current_source)
                    self.assertTrue(current_result[current_area]['open'])
                    self.assertEqual(sum(bool(item.get('open')) for item in current_result[:4]),1)
                    if current_area==0:self.assertEqual(current_result[4],current_selection)
                    if current_area==1:self.assertEqual(current_result[5],current_selection)
                    current_gateway.assert_not_called()
        current_bad=current_answer('WRITER',{'mode':'write','prompt':'마을'})+'\n'+current_answer('FLUX',{'prompt':'x','width':512,'height':512,'seed':42})
        with patch.object(hermes_agent_app,'find_conversation_session_job',return_value={'job':{'final_response':current_bad,'final_response_truncated':False}}):
            self.assertIn('단일 제안',hermes_agent_app.route_conversation_proposal(current_session,current_source)[-1])
        with patch.object(hermes_agent_app,'find_conversation_session_job',return_value={'job':{'final_response':current_bad,'final_response_truncated':True}}):
            self.assertIn('전체',hermes_agent_app.route_conversation_proposal(current_session,current_source)[-1])

    def test_reopening_proposal_clears_writer_attestation_and_pending_apply(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_detail, current_notice, current_checked, current_pending, current_confirm, current_status, current_card, current_preview, current_card_status, current_button = hermes_agent_app.reset_conversation_writer_review()
        self.assertIsNone(current_detail)
        self.assertFalse(current_checked)
        self.assertIsNone(current_pending)
        self.assertFalse(current_confirm['visible'])
        self.assertIn('확인', current_notice)
        self.assertIn('검토', current_status)
        self.assertIsNone(current_card)
        self.assertEqual(current_preview, '')
        self.assertFalse(current_button['interactive'])

    def test_reopening_edit_clears_previous_preview_and_pending_save(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_card, current_preview, current_image, current_notice, current_pending, current_confirm, current_button, current_route_notice = hermes_agent_app.reset_conversation_edit_review()
        self.assertIsNone(current_card)
        self.assertEqual(current_preview, '')
        self.assertIsNone(current_image)
        self.assertIn('다시 확인', current_notice)
        self.assertIsNone(current_pending)
        self.assertFalse(current_confirm['visible'])
        self.assertFalse(current_button['interactive'])

    def test_edit_reopen_failure_reports_error_without_restoring_review(self):
        from tools.review.ui.gradio import hermes_agent_app
        with patch.object(hermes_agent_app, 'prepare_conversation_edit_review', side_effect=gr.Error('세부 오류')):
            current_card, current_preview, current_image, current_notice = hermes_agent_app.open_conversation_edit_review('session', 'job', 'field')
        self.assertIsNone(current_card)
        self.assertEqual(current_preview, '')
        self.assertIsNone(current_image)
        self.assertIn('확인하지 못했습니다', current_notice)
        self.assertNotIn('세부 오류', current_notice)

    def test_edit_review_and_automatic_routing_reset_before_reloading(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_blocks = build_hermes_test_interface(include_advanced_controls=False)
        current_by_name = {}
        for current_identifier, current_event in current_blocks.fns.items():
            current_name = getattr(current_event.fn, '__name__', '')
            current_by_name.setdefault(current_name, []).append((current_identifier, current_event))
        current_resets = dict(current_by_name['reset_conversation_edit_review'])
        current_direct = current_by_name['open_conversation_edit_review'][0][1]
        current_route = current_by_name['route_conversation_proposal'][0][1]
        current_direct_reset = current_resets[current_direct.get_config()['trigger_after']]
        current_route_reset = current_resets[current_route.get_config()['trigger_after']]
        self.assertEqual(list(current_direct_reset.outputs), list(current_route_reset.outputs))
        self.assertEqual(list(current_direct_reset.outputs[:4]), list(current_direct.outputs))
        self.assertEqual(len(current_direct_reset.outputs), 8)

    def test_routed_proposal_opens_only_matching_review_and_rejects_changed_selection(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_session = 'a' * 32
        current_job = '2026-11-18_00-00-00-12345678'
        current_cases = [
            ('service', 'writer', 'prepare_conversation_service_review', 0, 3),
            ('edit', 'field', 'prepare_conversation_edit_review', 3, 4),
            ('image', 'flux', 'open_conversation_flux_reference', 7, 6),
            ('video', 'video', 'open_conversation_video_proposal', 13, 10),
        ]
        for current_area, current_kind, current_callback, current_offset, current_length in current_cases:
            with self.subTest(area=current_area):
                current_route = {'session_id': current_session, 'job_id': current_job, 'area': current_area, 'kind': current_kind}
                current_values = tuple('value-' + str(current_index) for current_index in range(current_length))
                with patch.object(hermes_agent_app, current_callback, return_value=current_values) as current_open, patch.object(hermes_agent_app, 'execute_remote_management_command') as current_gateway:
                    current_result = hermes_agent_app.open_routed_conversation_proposal(current_route, current_session, current_job)
                    self.assertEqual(current_result[current_offset:current_offset + current_length], current_values)
                    current_open.assert_called_once()
                    current_gateway.assert_not_called()
                    current_open.reset_mock()
                    self.assertIn('바뀌었습니다', hermes_agent_app.open_routed_conversation_proposal(current_route, current_session, 'another-job')[-1])
                    current_open.assert_not_called()

    def test_conversation_expression_catalog_rechecks_page_and_query(self):
        from tools.review.ui.gradio import hermes_agent_app
        def current_gateway(service,command,payload):
            self.assertEqual(command,'hermes-expression-catalog')
            current_offset=payload.get('offset',0)
            return {'records':[{'id':'joy','label':'기쁨'}],'total':2,'offset':current_offset,'next_offset':1 if current_offset==0 else None,'snapshot':'a'*64}
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            current_rows,current_notice,current_state,current_button=hermes_agent_app.read_conversation_expression_catalog('기')
            self.assertEqual(current_rows,[['기쁨','joy']])
            self.assertTrue(current_button['interactive'])
            current_rows,current_notice,current_next,current_button=hermes_agent_app.read_next_conversation_expression_catalog('기',current_state)
            self.assertIsNone(current_next)
            self.assertFalse(current_button['interactive'])
            self.assertIn('검색 조건',hermes_agent_app.read_next_conversation_expression_catalog('다른',current_state)[1])

    def test_conversation_expression_validates_face_and_preset_before_submit(self):
        from PIL import Image
        from tools.review.ui.gradio import hermes_agent_app
        current_session='a'*32
        current_source='2026-11-18_00-00-00-12345678'
        current_job='2026-11-18_01-00-00-87654321'
        current_face=Image.new('RGB',(16,16),'red')
        current_other=Image.new('RGB',(16,16),'blue')
        current_receipt={'state':'not_found'}
        current_proposal={'service':'flux-expression','prompt':'joy','width':512,'height':512,'seed':42}
        current_calls=[]
        def current_gateway(service,command,payload):
            current_calls.append(command)
            if command=='hermes-session-view':return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source,'session_job_unique':True,'job':{'status':{'status':'completed'}}}]}
            if command=='hermes-flux-proposal':return {'id':'a'*32,'job_id':payload['id'],'proposal':current_proposal.copy()}
            if command=='hermes-service-receipt':return {'service':payload['service'],**current_receipt,'request_id':payload['request_id']}
            if command=='hermes-flux-profile-status':return {'receipt':current_receipt.copy(),'job':{'status':'queued'}}
            if command=='hermes-delegate-flux-profile':
                self.assertEqual(payload['service'],'flux-expression')
                self.assertEqual(payload['request']['prompt'],'joy')
                self.assertEqual(len(payload['request']['images']),1)
                current_receipt.update(state='accepted',service='flux-expression',job_id=current_job)
                return current_receipt.copy()
            raise AssertionError(command)
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            current_source_record,_,_,_,_,current_open_notice=hermes_agent_app.open_conversation_flux_reference(current_session,current_source)
            self.assertIn('기쁨 (joy)',current_open_notice)
            with self.assertRaises(gr.Error):hermes_agent_app.review_conversation_flux_reference(current_source_record,current_session,current_source,None,None)
            with self.assertRaises(gr.Error):hermes_agent_app.review_conversation_flux_reference(current_source_record,current_session,current_source,current_face,current_other)
            current_review,current_preview,_=hermes_agent_app.review_conversation_flux_reference(current_source_record,current_session,current_source,current_face,None)
            self.assertIn('joy',current_preview)
            self.assertIn('SHA-256',current_preview)
            with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_flux_reference(current_review,current_source_record,current_session,current_source,current_other,None)
            self.assertNotIn('hermes-delegate-flux-profile',current_calls)
            current_after,current_status=hermes_agent_app.submit_conversation_flux_reference(current_review,current_source_record,current_session,current_source,current_face,None)
            self.assertIsNone(current_after)
            self.assertIn('접수 기록',current_status)
            self.assertEqual(current_calls.count('hermes-delegate-flux-profile'),1)
            self.assertIsNone(hermes_agent_app.review_conversation_flux_reference(current_source_record,current_session,current_source,current_face,None)[0])

    def test_conversation_reference_rejects_mismatched_receipt_identifier(self):
        from PIL import Image
        from tools.review.ui.gradio import hermes_agent_app
        current_session='a'*32
        current_source='2026-11-18_00-00-00-12345678'
        current_receipt_calls=[]
        def current_gateway(service,command,payload):
            if command=='hermes-session-view':return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source,'session_job_unique':True,'job':{'status':{'status':'completed'}}}]}
            if command=='hermes-flux-proposal':return {'id':'a'*32,'job_id':payload['id'],'proposal':{'service':'flux-expression','prompt':'joy','width':512,'height':512,'seed':42}}
            if command=='hermes-service-receipt':
                current_receipt_calls.append(payload['request_id'])
                return {'state':'not_found','service':payload['service'],'request_id':payload['request_id'] if len(current_receipt_calls)==2 else 'another_request'}
            raise AssertionError(command)
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            with self.assertRaises(gr.Error):hermes_agent_app.open_conversation_flux_reference(current_session,current_source)
            current_source_record,*_=hermes_agent_app.open_conversation_flux_reference(current_session,current_source)
            with self.assertRaises(gr.Error):hermes_agent_app.review_conversation_flux_reference(current_source_record,current_session,current_source,Image.new('RGB',(16,16),'red'),None)

    def test_flux_reference_submit_rejects_unmatched_receipt(self):
        current_source={'request_id':'request_123','proposal':{'service':'flux-building'}}
        current_review={'source':current_source,'review':{'request_id':'request_123'}}
        current_response={'state':'accepted','service':'flux-building','job_id':'2026-11-18_01-00-00-87654321'}
        with patch.object(hermes_agent_app,'review_conversation_flux_reference',return_value=(current_review,'','')), patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_response), patch.object(hermes_agent_app,'read_hermes_flux_profile_result',return_value=('', '접수 기록이 없습니다.')):
            current_after,current_status=hermes_agent_app.submit_conversation_flux_reference(current_review,current_source,'session','job',None,None)
            self.assertIsNone(current_after)
            self.assertIn('확인 필요',current_status)
            self.assertIn('자동 재접수하지 않습니다',current_status)

    def test_conversation_flux_reference_recovers_lost_response_without_resubmission(self):
        from PIL import Image
        from tools.review.ui.gradio import hermes_agent_app
        current_session='a'*32
        current_source='2026-11-18_00-00-00-12345678'
        current_job='2026-11-18_01-00-00-87654321'
        current_image=Image.new('RGB',(16,16),'red')
        current_receipt={'state':'not_found'}
        current_calls=[]
        def current_gateway(service,command,payload):
            current_calls.append(command)
            if command=='hermes-session-view':return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source,'session_job_unique':True,'job':{'status':{'status':'completed'}}}]}
            if command=='hermes-flux-proposal':return {'id':'a'*32,'job_id':payload['id'],'proposal':{'service':'flux-building','prompt':'house','width':512,'height':512,'seed':42}}
            if command=='hermes-service-receipt':return {'service':payload['service'],**current_receipt,'request_id':payload['request_id']}
            if command=='hermes-delegate-flux-profile':
                current_receipt.update(state='accepted',service='flux-building',job_id=current_job)
                raise OSError('response lost')
            if command=='hermes-flux-profile-status':return {'receipt':current_receipt.copy(),'job':{'status':'completed','image':None,'result_status':'unavailable'}}
            raise AssertionError(command)
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            current_source_record,*_=hermes_agent_app.open_conversation_flux_reference(current_session,current_source)
            current_review,_,_=hermes_agent_app.review_conversation_flux_reference(current_source_record,current_session,current_source,current_image,None)
            current_after,current_notice=hermes_agent_app.submit_conversation_flux_reference(current_review,current_source_record,current_session,current_source,current_image,None)
            self.assertIsNone(current_after)
            self.assertIn('자동 재접수하지 않습니다',current_notice)
            self.assertIn('이미지 링크 확인 불가',hermes_agent_app.read_conversation_flux_reference(current_source_record,current_session,current_source))
            self.assertIn('품질 승인',hermes_agent_app.read_conversation_flux_reference(current_source_record,current_session,current_source))
            self.assertIn('session='+current_session,hermes_agent_app.read_conversation_flux_reference(current_source_record,current_session,current_source))
            current_review,_,_=hermes_agent_app.review_conversation_flux_reference(current_source_record,current_session,current_source,current_image,None)
            self.assertIsNone(current_review)
            self.assertEqual(current_calls.count('hermes-delegate-flux-profile'),1)

    def test_conversation_reference_result_explains_wrong_receipt(self):
        current_source={'session_id':'a'*32,'source_job_id':'job-a','request_id':'request_123','proposal':{'service':'flux-building'}}
        current_response={'receipt':{'state':'accepted','request_id':'wrong','service':'flux-building','job_id':'2026-11-18_01-00-00-87654321'},'job':{'status':'completed'}}
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_response):
            current_message=hermes_agent_app.read_conversation_flux_reference(current_source,'a'*32,'job-a')
        self.assertIn('접수 ID',current_message)
        self.assertIn('자동 재접수하지 마세요',current_message)

    def test_flux_profile_result_rejects_wrong_service_or_job(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_response={'receipt':{'state':'accepted','service':'flux-building','job_id':'2026-11-18_00-00-00-12345678'},'job':{'status':'completed','image':None}}
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_response):
            self.assertIn('이미지 링크 확인 불가',hermes_agent_app.read_hermes_flux_profile_result('request_123','flux-building')[1])
            current_response['receipt']['service']='flux-prop'
            with self.assertRaises(gr.Error):hermes_agent_app.read_hermes_flux_profile_result('request_123','flux-building')
            current_response['receipt'].update(service='flux-building',job_id='../bad')
            with self.assertRaises(gr.Error):hermes_agent_app.read_hermes_flux_profile_result('request_123','flux-building')

    def test_conversation_flux_reference_rechecks_images_and_never_repeats(self):
        from PIL import Image
        from tools.review.ui.gradio import hermes_agent_app
        current_session='a'*32
        current_source='2026-11-18_00-00-00-12345678'
        current_job='2026-11-18_01-00-00-87654321'
        current_first=Image.new('RGB',(16,16),'red')
        current_changed=Image.new('RGB',(16,16),'blue')
        current_receipt={'state':'not_found'}
        current_proposal={'service':'flux-building','prompt':'stone house','width':512,'height':512,'seed':42}
        current_calls=[]
        def current_gateway(service,command,payload):
            current_calls.append(command)
            if command=='hermes-session-view':return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source,'session_job_unique':True,'job':{'status':{'status':'completed'}}}]}
            if command=='hermes-flux-proposal':return {'id':'a'*32,'job_id':payload['id'],'proposal':current_proposal.copy()}
            if command=='hermes-service-receipt':return {'service':payload['service'],**current_receipt,'request_id':payload['request_id']}
            if command=='hermes-flux-profile-status':return {'receipt':current_receipt.copy(),'job':{'status':'queued'}}
            if command=='hermes-delegate-flux-profile':
                self.assertEqual(payload['service'],'flux-building')
                self.assertEqual(len(payload['request']['images']),1)
                current_receipt.update(state='accepted',service='flux-building',job_id=current_job)
                return current_receipt.copy()
            raise AssertionError(command)
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            current_source_record,*_=hermes_agent_app.open_conversation_flux_reference(current_session,current_source)
            with self.assertRaises(gr.Error):hermes_agent_app.review_conversation_flux_reference(current_source_record,current_session,current_source,None,None)
            current_review,current_preview,current_status=hermes_agent_app.review_conversation_flux_reference(current_source_record,current_session,current_source,current_first,None)
            self.assertIn('SHA-256',current_preview)
            with self.assertRaises(gr.Error):hermes_agent_app.submit_conversation_flux_reference(current_review,current_source_record,current_session,current_source,current_changed,None)
            self.assertNotIn('hermes-delegate-flux-profile',current_calls)
            current_after,current_status=hermes_agent_app.submit_conversation_flux_reference(current_review,current_source_record,current_session,current_source,current_first,None)
            self.assertIsNone(current_after)
            self.assertIn('접수 기록',current_status)
            current_after,current_preview,current_status=hermes_agent_app.review_conversation_flux_reference(current_source_record,current_session,current_source,current_first,None)
            self.assertIsNone(current_after)
            self.assertEqual(current_calls.count('hermes-delegate-flux-profile'),1)
            current_proposal['service']='flux-prop'
            with self.assertRaises(gr.Error):hermes_agent_app.review_conversation_flux_reference(current_source_record,current_session,current_source,current_first,None)

    def test_conversation_flux_profile_review_submit_and_restore(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_session='a'*32
        current_source='2026-11-18_00-00-00-12345678'
        current_job='2026-11-18_01-00-00-87654321'
        current_receipt={'state':'not_found'}
        current_proposal={'service':'flux-prop','prompt':'wooden crate','width':512,'height':512,'seed':42}
        current_calls=[]
        def current_gateway(service,command,payload):
            current_calls.append(command)
            if command=='hermes-session-view':return {'id':'a'*32,'truncated':False,'messages':[{'job_id':current_source,'session_job_unique':True,'job':{'status':{'status':'completed'}}}]}
            if command=='hermes-flux-proposal':return {'id':'a'*32,'job_id':payload['id'],'proposal':current_proposal.copy()}
            if command=='hermes-service-receipt':return {'request_id':payload['request_id'],'service':'flux-prop',**current_receipt}
            if command=='hermes-flux-profile-status':return {'receipt':{'request_id':payload['request_id'],'service':'flux-prop',**current_receipt},'job':{'status':'completed','image':'/flux-prop-generator/jobs/'+current_job+'/result.png'}}
            if command=='hermes-delegate-flux-profile':
                self.assertEqual(payload['service'],'flux-prop')
                self.assertEqual(payload['request']['images'],[])
                current_receipt.update(state='accepted',service='flux-prop',job_id=current_job)
                return current_receipt.copy()
            raise AssertionError(command)
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            current_card,current_preview,current_notice=hermes_agent_app.prepare_conversation_service_review(current_session,current_source,'flux')
            self.assertTrue(current_card['ready'])
            self.assertIn('flux-prop',current_preview)
            current_result,current_notice=hermes_agent_app.submit_conversation_service_review(current_card,current_session,current_source,'flux')
            self.assertFalse(current_result['ready'])
            self.assertIn('/flux-prop-generator/jobs/'+current_job+'/result.png',current_notice)
            self.assertIn('중단 작업 복구',current_notice)
            self.assertIn('/management/frame/flux-prop-generator/',current_notice)
            current_again,_,_=hermes_agent_app.prepare_conversation_service_review(current_session,current_source,'flux')
            self.assertFalse(current_again['ready'])
            self.assertEqual(current_calls.count('hermes-delegate-flux-profile'),1)
            self.assertNotIn('hermes-delegate-flux-image',current_calls)

    def test_conversation_finds_old_session_job_and_refuses_changed_snapshot(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_snapshot='b'*64
        current_calls=[]
        def current_gateway(service,command,payload):
            current_calls.append(payload.copy())
            if payload.get('offset')==20:return {'id':current_session,'offset':20,'snapshot':current_snapshot,'messages':[{'job_id':current_job,'session_job_unique':True,'job':{'status':{'status':'completed'}}}],'next_offset':None,'truncated':False}
            return {'id':current_session,'offset':0,'snapshot':current_snapshot,'messages':[],'next_offset':20,'truncated':True}
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_gateway):
            current_choice,current_notice=hermes_agent_app.select_older_conversation_job(current_session,current_job)
            self.assertEqual(current_choice['value'],current_job)
            self.assertIn('이전 작업',current_notice)
            self.assertEqual(current_calls[-1],{'session_id':current_session,'offset':20,'snapshot':current_snapshot})
        def current_changed(service,command,payload):
            current_response=current_gateway(service,command,payload)
            if payload.get('offset')==20:current_response['snapshot']='c'*64
            return current_response
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_changed):
            with self.assertRaises(gr.Error):hermes_agent_app.select_older_conversation_job(current_session,current_job)
        def current_duplicate(service,command,payload):
            current_response=current_gateway(service,command,payload)
            if payload.get('offset')==20:current_response['messages'][0]['session_job_unique']=False
            return current_response
        with patch.object(hermes_agent_app,'execute_remote_management_command',side_effect=current_duplicate):
            with self.assertRaises(gr.Error):hermes_agent_app.select_older_conversation_job(current_session,current_job)

    def test_older_conversation_selection_requires_first_page_session_identity(self):
        current_session_identifier='a'*32
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_message_record={'job_id':current_job_identifier,'job':{'status':{'status':'completed'}}}
        for current_session_value in (None,'b'*32):
            current_response_record={'messages':[current_message_record],'truncated':False}
            if current_session_value is not None:current_response_record['id']=current_session_value
            with self.subTest(session=current_session_value),patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_response_record):
                with self.assertRaises(gr.Error):hermes_agent_app.find_conversation_session_job(current_session_identifier,current_job_identifier)

    def test_conversation_proposals_refuse_cross_page_duplicate_or_unknown(self):
        from tools.review.ui.gradio import hermes_agent_app
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_message={'job_id':current_job,'session_job_unique':False,'job':{'status':{'status':'completed'}}}
        current_view={'messages':[current_message],'truncated':True}
        current_actions=[lambda:hermes_agent_app.prepare_conversation_kimodo_review(current_session,current_job),lambda:hermes_agent_app.prepare_conversation_service_review(current_session,current_job,'flux'),lambda:hermes_agent_app.prepare_conversation_edit_review(current_session,current_job,'field'),lambda:hermes_agent_app.open_conversation_video_proposal(current_session,current_job)]
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_view) as current_gateway:
            for current_action in current_actions:
                with self.assertRaises(gr.Error):current_action()
            self.assertTrue(all(item.args[1]=='hermes-session-view' for item in current_gateway.call_args_list))
            current_message.pop('session_job_unique')
            with self.assertRaises(gr.Error):current_actions[0]()
            current_view['truncated']=False
            hermes_agent_app.validate_conversation_session_match(current_view,[current_message])
            current_message['session_job_unique']=True
            current_view['truncated']=True
            hermes_agent_app.validate_conversation_session_match(current_view,[current_message])

    def test_history_detail_selection_clears_invalid_rows(self):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with patch.object(operations_history_app,'refresh_hermes_work_status',return_value=('완료','답변','diff','로그',{},'지시')) as current_detail_mock:
            current_result_value=operations_history_app.select_operations_history_job([[current_job_identifier,'완료','','','']],SimpleNamespace(index=0))
            self.assertEqual(current_result_value[0],current_job_identifier)
            current_detail_mock.assert_called_once_with(current_job_identifier)
            current_detail_mock.reset_mock()
            for current_rows_value,current_index_value in (([[]],0),([['../bad','','','','']],0),([[current_job_identifier]],0),([],0),([[current_job_identifier,'','','','']],True)):
                with self.subTest(rows=current_rows_value,index=current_index_value):
                    self.assertEqual(operations_history_app.select_operations_history_job(current_rows_value,SimpleNamespace(index=current_index_value)),operations_history_app.reset_operations_history_detail())
            current_detail_mock.assert_not_called()

    def test_history_link_parameters_require_job_and_session_shapes(self):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_session_identifier='a'*32
        self.assertEqual(operations_history_app.validate_operations_history_link(current_job_identifier,current_session_identifier),(current_job_identifier,current_session_identifier))
        for current_bad_value in ('../unsafe','x'*500,None):
            with self.subTest(value=current_bad_value):
                self.assertEqual(operations_history_app.validate_operations_history_link(current_bad_value,current_bad_value),('',''))

    def test_conversation_history_link_validates_selected_identifiers(self):
        current_session_identifier='a'*32
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_link_value=hermes_agent_app.build_conversation_history_link(current_session_identifier,current_job_identifier)
        self.assertIn('/management/frame/operations-history/?job='+current_job_identifier+'&amp;session='+current_session_identifier,current_link_value)
        for current_session_value,current_job_value in (('bad',current_job_identifier),(current_session_identifier,'../unsafe'),(None,current_job_identifier)):
            with self.subTest(session=current_session_value,job=current_job_value):
                self.assertNotIn('<a ',hermes_agent_app.build_conversation_history_link(current_session_value,current_job_value))

    def test_history_to_conversation_rechecks_session_membership(self):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_snapshot_value='b'*64
        current_message_value={'created_at':'2026-11-19','text':'지시','job_id':current_job_identifier,'job':{'status':{'status':'completed'}}}
        current_page_value={'id':current_session_identifier,'offset':0,'snapshot':current_snapshot_value,'messages':[current_message_value],'truncated':False}
        current_page_state={'session_id':current_session_identifier,'offset':0,'snapshot':current_snapshot_value}
        current_row_values=[['2026-11-19','지시',current_job_identifier,'completed','']]
        with patch.object(operations_history_app,'execute_remote_management_command',return_value=current_page_value),patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_page_value):
            current_link_value,current_text_value=operations_history_app.select_operations_session_instruction(current_session_identifier,current_row_values,current_page_state,SimpleNamespace(index=0))
            self.assertIn('session='+current_session_identifier,current_link_value)
            self.assertIn('job='+current_job_identifier,current_link_value)
            self.assertEqual(current_text_value,'지시')
            self.assertEqual(hermes_agent_app.restore_linked_conversation_job(current_session_identifier,current_job_identifier)[0]['value'],current_job_identifier)
            current_page_value['id']='c'*32
            self.assertIn('확인할 수 없습니다',hermes_agent_app.restore_linked_conversation_job(current_session_identifier,current_job_identifier)[1])
            self.assertEqual(operations_history_app.select_operations_session_instruction(current_session_identifier,current_row_values,current_page_state,SimpleNamespace(index=0))[0],'')

    def test_operations_instruction_detail_verifies_snapshot_and_row(self):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app
        current_session='a'*32
        current_snapshot='b'*64
        current_job='2026-11-18_00-00-00-12345678'
        current_message={'created_at':'2026-11-19','text':'긴 지시 '+('내용 '*100),'job_id':current_job}
        current_response={'id':current_session,'offset':0,'snapshot':current_snapshot,'messages':[current_message]}
        current_state={'session_id':current_session,'offset':0,'snapshot':current_snapshot}
        current_rows=[['2026-11-19',current_message['text'][:200],current_job,'completed','']]
        with patch.object(operations_history_app,'execute_remote_management_command',return_value=current_response):
            current_link,current_detail=operations_history_app.select_operations_session_instruction(current_session,current_rows,current_state,SimpleNamespace(index=(0,1)))
            self.assertEqual(current_detail,current_message['text'])
            self.assertIn(current_job,current_link)
            current_link,current_detail=operations_history_app.select_operations_session_instruction(current_session,[['다른 시각',*current_rows[0][1:]]],current_state,SimpleNamespace(index=0))
            self.assertEqual(current_link,'')
            self.assertIn('다시 조회',current_detail)
            current_response['snapshot']='c'*64
            current_link,current_detail=operations_history_app.select_operations_session_instruction(current_session,current_rows,current_state,SimpleNamespace(index=0))
            self.assertEqual(current_link,'')
            self.assertIn('다시 조회',current_detail)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_direct_asset_save_clears_review_on_lost_or_mismatched_response(self,current_gateway_mock):
        import json
        current_review={'request_id':'request_123','draft':{'id':'example'}}
        current_readers=(hermes_agent_app.save_hermes_building_anchor_draft,hermes_agent_app.save_hermes_sprite_anchor_draft,hermes_agent_app.save_hermes_effect_edit_draft,hermes_agent_app.save_hermes_billboard_edit_draft)
        for current_reader in current_readers:
            with self.subTest(reader=current_reader.__name__):
                for current_response in (OSError('response lost'),{'request_id':'other','state':'completed','saved':True}):
                    current_gateway_mock.side_effect=current_response if isinstance(current_response,Exception) else None
                    if isinstance(current_response,dict):current_gateway_mock.return_value=current_response
                    current_state,current_hidden,current_status=current_reader(current_review,json.dumps(current_review['draft']),'request_123')
                    self.assertIsNone(current_state)
                    self.assertFalse(current_hidden['visible'])
                    self.assertIn('확인 필요',current_status)

    def test_direct_cancel_checks_receipt_before_reporting_success(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with patch.object(hermes_agent_app,'execute_remote_management_command') as current_gateway_mock:
            for current_response_value in (None,{}, {'cancel_requested':False,'status':'running'}, {'cancel_requested':True,'status':'unknown'}, {'cancel_requested':1,'status':'queued'}, {'id':'wrong','cancel_requested':True,'status':'running'}, {'cancel_requested':True,'status':'running'}):
                current_gateway_mock.return_value=current_response_value
                current_review_record,_,_=hermes_agent_app.review_direct_job_cancel(current_job_identifier)
                _,_,current_status_text=hermes_agent_app.submit_direct_job_cancel(current_review_record,current_job_identifier)
                with self.subTest(current_response_value=current_response_value):
                    self.assertIn('결과 확인 필요',current_status_text)
                    self.assertIn(current_job_identifier,current_status_text)
            for current_status_name in ('queued','running','cancelled'):
                current_gateway_mock.return_value={'id':current_job_identifier,'cancel_requested':True,'status':current_status_name}
                current_review_record,_,_=hermes_agent_app.review_direct_job_cancel(current_job_identifier)
                _,_,current_status_text=hermes_agent_app.submit_direct_job_cancel(current_review_record,current_job_identifier)
                with self.subTest(current_status_name=current_status_name):
                    self.assertIn('중지를 요청했습니다',current_status_text)
                    self.assertIn('실제 종료',current_status_text)

    def test_direct_cancel_confirms_same_job_and_handles_uncertainty(self):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_other_identifier='2026-11-18_00-00-00-87654321'
        current_review_record,current_summary_text,current_visible_update=hermes_agent_app.review_direct_job_cancel(current_job_identifier)
        self.assertIn(current_job_identifier,current_summary_text)
        self.assertTrue(current_visible_update['visible'])
        with patch.object(hermes_agent_app,'cancel_hermes_work_request') as current_cancel_mock:
            current_state,current_group,current_status=hermes_agent_app.submit_direct_job_cancel(current_review_record,current_other_identifier)
            self.assertIsNone(current_state)
            self.assertFalse(current_group['visible'])
            self.assertIn('변경',current_status)
            current_cancel_mock.assert_not_called()
            current_cancel_mock.side_effect=OSError('offline')
            current_review_record,_,_=hermes_agent_app.review_direct_job_cancel(current_job_identifier)
            current_state,current_group,current_status=hermes_agent_app.submit_direct_job_cancel(current_review_record,current_job_identifier)
            self.assertIsNone(current_state)
            self.assertFalse(current_group['visible'])
            self.assertIn('실제 상태',current_status)
            self.assertIn(current_job_identifier,current_status)
            current_cancel_mock.assert_called_once_with(current_job_identifier)
            _,_,current_repeat_status=hermes_agent_app.submit_direct_job_cancel(current_review_record,current_job_identifier)
            self.assertEqual(current_repeat_status.get('__type__'),'update')
            current_cancel_mock.assert_called_once_with(current_job_identifier)
            current_discarded_record,_,_=hermes_agent_app.review_direct_job_cancel(current_job_identifier)
            hermes_agent_app.discard_direct_job_cancel(current_discarded_record)
            _,_,current_discarded_status=hermes_agent_app.submit_direct_job_cancel(current_discarded_record,current_job_identifier)
            self.assertEqual(current_discarded_status.get('__type__'),'update')
            current_cancel_mock.assert_called_once_with(current_job_identifier)

    def test_direct_cancel_requires_valid_job_identifier(self):
        for current_job_identifier in (None,'','bad','2026-11-18_00-00-00-12345678/extra'):
            with self.subTest(current_job_identifier=current_job_identifier):
                self.assertFalse(hermes_agent_app.update_direct_job_cancel_availability(current_job_identifier)['interactive'])
        self.assertTrue(hermes_agent_app.update_direct_job_cancel_availability('2026-11-18_00-00-00-12345678')['interactive'])

    def test_direct_session_change_rejects_previous_session_job(self):
        current_old_job='2026-11-18_00-00-00-12345678'
        current_new_job='2026-11-18_00-00-00-87654321'
        current_session_identifier='b'*32
        current_session_record={'id':current_session_identifier,'message_count':1,'queried_at':'now','messages':[{'text':'새 요청','job_id':current_new_job,'job':{'status':{'status':'completed'}}}]}
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_session_record), patch.object(hermes_agent_app,'find_conversation_session_job',side_effect=gr.Error('세션 불일치')) as current_old_lookup:
            _,_,current_timer_update,current_jobs_update=hermes_agent_app.read_hermes_session_conversation(current_session_identifier,current_old_job)
        current_old_lookup.assert_called_once_with(current_session_identifier,current_old_job)
        self.assertEqual(current_jobs_update['value'],current_new_job)
        self.assertNotIn(current_old_job,[current_choice[1] for current_choice in current_jobs_update['choices']])
        self.assertFalse(current_timer_update['active'])
        _,_,current_empty_timer,current_empty_jobs=hermes_agent_app.read_hermes_session_conversation(None,current_old_job)
        self.assertIsNone(current_empty_jobs['value'])
        self.assertFalse(current_empty_timer['active'])

    def test_conversation_context_reset_clears_selection_bound_reviews(self):
        current_reset_values = hermes_agent_app.reset_conversation_context_state()
        self.assertEqual(len(current_reset_values), 25)
        self.assertEqual(current_reset_values[:17], hermes_agent_app.reset_conversation_selection_state())
        self.assertEqual(current_reset_values[17], '')
        self.assertIsNone(current_reset_values[18])
        self.assertFalse(current_reset_values[19]['visible'])
        self.assertFalse(current_reset_values[20]['interactive'])
        self.assertEqual(current_reset_values[21:23], ('', None))
        self.assertFalse(current_reset_values[23]['interactive'])
        self.assertIn('처음부터', current_reset_values[24])

    def test_conversation_context_reset_is_bound_to_session_and_job(self):
        current_interface_value = build_hermes_test_interface(False)
        current_reset_events = [current_event for current_event in current_interface_value.fns.values() if getattr(current_event.fn, '__name__', '') == 'reset_conversation_context_state']
        self.assertEqual(len(current_reset_events), 2)
        current_target_labels = set()
        for current_event in current_reset_events:
            self.assertEqual(len(current_event.outputs), len(hermes_agent_app.reset_conversation_context_state()))
            current_dependency_record = next(current_record for current_record in current_interface_value.config['dependencies'] if current_record['id'] == current_event._id)
            self.assertEqual(len(current_dependency_record['targets']), 1)
            current_target_identifier, current_target_event = current_dependency_record['targets'][0]
            self.assertEqual(current_target_event, 'change')
            current_target_labels.add(current_interface_value.blocks[current_target_identifier].label)
        self.assertEqual(current_target_labels, {'세션', '세션 작업 선택'})

    def test_conversation_timer_starts_disabled_with_ten_second_interval(self):
        current_interface_value = build_hermes_test_interface(False)
        current_timer_values = [current_component for current_component in current_interface_value.blocks.values() if current_component.__class__.__name__ == 'Timer']
        self.assertEqual(len(current_timer_values), 1)
        current_timer_value = current_timer_values[0]
        self.assertEqual(current_timer_value.value, 10)
        self.assertFalse(current_timer_value.active)
        current_tick_events = [current_event for current_event in current_interface_value.config['dependencies'] if (current_timer_value._id, 'tick') in [tuple(current_target) for current_target in current_event['targets']]]
        self.assertEqual(len(current_tick_events), 1)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_session_timer_tracks_any_active_job_without_restarting_idle(self,current_gateway_mock):
        current_session_identifier='a'*32
        current_job_values=[{'text':'요청','job_id':f'2026-11-18_00-00-0{current_index}-12345678','job':{'status':{'status':current_status_name}}} for current_index,current_status_name in enumerate(('completed','queued','failed'))]
        current_gateway_mock.return_value={'id':current_session_identifier,'message_count':3,'queried_at':'now','messages':current_job_values}
        current_conversation,_,current_timer,_=hermes_agent_app.read_hermes_session_conversation(current_session_identifier)
        self.assertEqual(len(current_conversation),6)
        self.assertTrue(current_timer['active'])
        current_job_values[1]['job']['status']['status']='completed'
        _,_,current_timer,_=hermes_agent_app.read_hermes_session_conversation(current_session_identifier)
        self.assertFalse(current_timer['active'])
        current_job_values[1]['job']['status']['status']='unknown'
        _,_,current_timer,_=hermes_agent_app.read_hermes_session_conversation(current_session_identifier)
        self.assertFalse(current_timer['active'])
        current_gateway_mock.side_effect=OSError('offline')
        _,current_notice,current_timer,_=hermes_agent_app.read_hermes_session_conversation(current_session_identifier)
        self.assertFalse(current_timer['active'])
        self.assertIn('세션 조회 실패',current_notice)
        self.assertEqual(current_gateway_mock.call_count,4)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_session_poll_stops_after_work_finishes(self,current_gateway_mock):
        current_session_identifier='a'*32
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_message_value={'text':'요청','job_id':current_job_identifier,'job':{'status':{'status':'queued'}}}
        current_gateway_mock.return_value={'id':current_session_identifier,'message_count':1,'queried_at':'now','messages':[current_message_value]}
        for current_status_name,current_expected_active in (('queued',True),('running',True),('completed',False),('failed',False),('cancelled',False)):
            with self.subTest(status=current_status_name):
                current_message_value['job']['status']['status']=current_status_name
                current_timer_value=hermes_agent_app.read_hermes_session_conversation(current_session_identifier)[2]
                self.assertEqual(current_timer_value['active'],current_expected_active)
        current_gateway_mock.side_effect=OSError('offline')
        self.assertFalse(hermes_agent_app.read_hermes_session_conversation(current_session_identifier)[2]['active'])
        self.assertFalse(hermes_agent_app.read_hermes_session_conversation(None)[2]['active'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_conversation_rejects_missing_or_wrong_session_identity(self,current_gateway_mock):
        for current_identifier in (None,'b'*32):
            current_gateway_mock.return_value={'id':current_identifier,'message_count':1,'queried_at':'now','messages':[{'text':'다른 대화'}]}
            current_messages,current_notice,current_timer,current_jobs=hermes_agent_app.read_hermes_session_conversation('a'*32)
            self.assertEqual(current_messages,[])
            self.assertIn('세션 조회 실패',current_notice)
            self.assertIsNone(current_jobs['value'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command',side_effect=OSError('private error'))
    def test_failed_session_refresh_clears_stale_conversation_and_jobs(self,current_gateway_mock):
        current_messages,current_notice,current_timer,current_jobs=hermes_agent_app.read_hermes_session_conversation('a'*32,'2026-11-18_00-00-00-12345678')
        self.assertEqual(current_messages,[])
        self.assertIn('세션 조회 실패',current_notice)
        self.assertIn('삭제된 것은 아닙니다',current_notice)
        self.assertNotIn('private error',current_notice)
        self.assertFalse(current_timer['active'])
        self.assertEqual(current_jobs['choices'],[])
        self.assertIsNone(current_jobs['value'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_registration_receipt_rejects_wrong_identity_and_result(self,current_gateway_mock):
        for current_reader in (hermes_agent_app.read_hermes_effect_registration_status,hermes_agent_app.read_hermes_waypoint_replacement_status):
            current_gateway_mock.return_value={'request_id':'request_123','state':'completed','id':'effect-1','generation':1}
            self.assertIn('completed',current_reader('request_123'))
            for current_invalid in ({'request_id':'other','state':'completed','id':'effect-1'},{'request_id':'request_123','state':'completed','id':'../invalid'},{'request_id':'request_123','state':'invalid'}):
                current_gateway_mock.return_value=current_invalid
                self.assertIn('확인 필요',current_reader('request_123'))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_asset_edit_receipts_require_matching_identity_and_completed_save(self,current_gateway_mock):
        current_readers=(hermes_agent_app.read_hermes_building_anchor_status,hermes_agent_app.read_hermes_sprite_anchor_status,hermes_agent_app.read_hermes_effect_edit_status,hermes_agent_app.read_hermes_billboard_edit_status)
        for current_reader in current_readers:
            with self.subTest(reader=current_reader.__name__):
                current_gateway_mock.return_value={'request_id':'request_123','state':'completed','saved':True}
                self.assertIn('저장 완료',current_reader('request_123'))
                for current_invalid in ({'request_id':'other','state':'completed','saved':True},{'request_id':'request_123','state':'unknown','saved':True},{'request_id':'request_123','state':'completed','saved':False}):
                    current_gateway_mock.return_value=current_invalid
                    self.assertIn('확인 필요',current_reader('request_123'))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_field_receipt_rejects_mismatched_and_invalid_results(self,current_gateway_mock):
        current_request='field_request_123'
        current_receipt={'request_id':current_request,'map':'moss-clearing','state':'completed','saved':True}
        current_gateway_mock.return_value=current_receipt
        self.assertIn('소비자 동기화',hermes_agent_app.read_hermes_field_map_receipt(current_request))
        for current_change in ({'request_id':'other'},{'saved':'yes'},{'state':'invalid'}):
            current_gateway_mock.return_value={**current_receipt,**current_change}
            self.assertIn('확인 필요',hermes_agent_app.read_hermes_field_map_receipt(current_request))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_city_receipt_identifies_db_scope_and_rejects_wrong_receipts(self,current_gateway_mock):
        current_request='city_request_123'
        current_receipt={'request_id':current_request,'map':'stonewarm','state':'completed','saved':True}
        current_gateway_mock.return_value=current_receipt
        current_result=hermes_agent_app.read_hermes_city_map_receipt(current_request)
        self.assertIn('콘텐츠 DB 저장 완료',current_result)
        self.assertIn('동기화',current_result)
        for current_change in ({'request_id':'different'},{'saved':'yes'},{'state':'invalid'}):
            current_gateway_mock.return_value={**current_receipt,**current_change}
            self.assertIn('확인 필요',hermes_agent_app.read_hermes_city_map_receipt(current_request))
        current_gateway_mock.return_value={'state':'not_found'}
        self.assertIn('시도했다면',hermes_agent_app.read_hermes_city_map_receipt(current_request))

    def test_operations_session_history_older_page_and_session_change(self):
        from tools.review.ui.gradio import operations_history_app
        current_session='a'*32
        current_snapshot='b'*64
        def current_gateway(service,command,payload):
            current_offset=payload.get('offset',0)
            return {'id':current_session,'offset':current_offset,'messages':[{'text':'지시','created_at':'2026-11-19T00:00:00Z','job_id':None}],'next_offset':1 if current_offset==0 else None,'snapshot':current_snapshot}
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=current_gateway):
            current_rows,current_notice,current_link,current_state,current_button,current_newer=operations_history_app.read_operations_session_history_page(current_session)
            self.assertEqual(current_rows[0][0],'2026-11-19T00:00:00Z')
            self.assertTrue(current_button['interactive'])
            current_rows,current_notice,current_link,current_next,current_button,current_newer=operations_history_app.read_next_operations_session_history(current_session,current_state)
            self.assertEqual(current_next['offset'],1)
            self.assertIsNone(current_next['next_offset'])
            self.assertFalse(current_button['interactive'])
            self.assertTrue(current_newer['interactive'])
            current_again=operations_history_app.read_newer_operations_session_history(current_session,current_next)
            self.assertEqual(current_again[3]['offset'],0)
            self.assertFalse(current_again[5]['interactive'])
            current_rows,current_notice,current_link,current_next,current_button,current_newer=operations_history_app.read_next_operations_session_history('c'*32,current_state)
            self.assertEqual(current_rows,[])
            self.assertIn('세션이 바뀌었습니다',current_notice)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=ValueError('changed')):
            self.assertIn('변경됐습니다',operations_history_app.read_next_operations_session_history(current_session,current_state)[1])

    def test_session_history_rejects_wrong_initial_session_or_offset(self):
        from tools.review.ui.gradio import operations_history_app
        current_session='a'*32
        current_responses=({'id':current_session,'offset':20,'messages':[],'next_offset':None,'snapshot':'b'*64},{'id':'c'*32,'offset':0,'messages':[]})
        for current_response in current_responses:
            with self.subTest(response=current_response),patch.object(operations_history_app,'execute_remote_management_command',return_value=current_response) as current_gateway_mock:
                self.assertIsNone(operations_history_app.read_operations_session_history_page(current_session)[3])
                with self.assertRaises(ValueError):operations_history_app.read_operations_session_receipts(current_session)
                self.assertTrue(all(current_call.args[1]=='hermes-session-view' for current_call in current_gateway_mock.call_args_list))

    def test_operations_page_uses_direct_service_receipt_without_recovery(self):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_session='a'*32
        current_job='2026-11-18_00-00-00-12345678'
        current_request='chat_'+hashlib.sha256((current_session+':'+current_job+':video').encode()).hexdigest()
        current_page={'session_id':current_session,'offset':20,'next_offset':None,'snapshot':'b'*64}
        current_commands=[]
        def current_gateway(service,command,payload):
            current_commands.append(command)
            if command=='hermes-session-view':return {'id':current_session,'offset':20,'snapshot':'b'*64,'messages':[{'session_job_unique':True,'job_id':current_job,'job':{'status':{'status':'completed'},'final_response':'HERMES_VIDEO_PROPOSAL'}}]}
            if command=='hermes-video-proposal':return {'id':'a'*32,'job_id':current_job,'proposal':{'service':'wan22-vace'}}
            if command=='hermes-service-receipt':
                self.assertEqual(payload,{'request_id':current_request,'service':'wan22-vace'})
                return {'request_id':current_request,'state':'accepted','service':'wan22-vace','job_id':'target-old'}
            if command=='hermes-management-status':return {'queue':{'status':'available','jobs':[]},'reservations':{'status':'available','records':[],'truncated':False}}
            raise AssertionError(command)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=current_gateway):
            current_rows,current_notice=operations_history_app.read_operations_current_page_receipts(current_session,current_page)
            self.assertEqual(current_rows[0][3:5],['접수 기록','target-old'])
            self.assertNotIn('hermes-video-status',current_commands)
            self.assertNotIn('hermes-video-history',current_commands)
        def current_wrong_receipt(service,command,payload):
            current_result=current_gateway(service,command,payload)
            if command=='hermes-service-receipt':current_result['request_id']='another_request'
            return current_result
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=current_wrong_receipt):
            current_rows,_=operations_history_app.read_operations_current_page_receipts(current_session,current_page)
            self.assertEqual(current_rows[0][3:5],['제안 또는 접수 조회 불가','미확인'])

    def test_operations_receipts_follow_displayed_history_page(self):
        from tools.review.ui.gradio import operations_history_app
        current_session='a'*32
        current_page={'session_id':current_session,'offset':20,'next_offset':None,'snapshot':'b'*64}
        current_job='2026-11-18_00-00-00-12345678'
        current_calls=[]
        def current_gateway(service,command,payload):
            current_calls.append((command,payload))
            if command=='hermes-session-view':return {'id':current_session,'offset':20,'snapshot':'b'*64,'messages':[{'session_job_unique':True,'job_id':current_job,'job':{'status':{'status':'completed'},'final_response':'HERMES_KIMODO_PROPOSAL'}}]}
            if command=='hermes-kimodo-proposal':return {'id':'a'*32,'job_id':current_job,'proposal':{}}
            if command=='hermes-delegation-status':return {'state':'not_found'}
            raise AssertionError(command)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=current_gateway):
            current_rows,current_notice=operations_history_app.read_operations_current_page_receipts(current_session,current_page)
            self.assertEqual(current_rows[0][0],current_job)
            self.assertIn('페이지',current_notice)
            self.assertEqual(current_calls[0][1],{'session_id':current_session,'offset':20,'snapshot':'b'*64})
            self.assertEqual(operations_history_app.read_operations_current_page_receipts('c'*32,current_page)[0],[])
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=ValueError('changed')):
            self.assertIn('변경됐습니다',operations_history_app.read_operations_current_page_receipts(current_session,current_page)[1])

    def test_operations_receipts_refuse_duplicate_or_unverified_session_job(self):
        from tools.review.ui.gradio import operations_history_app
        current_session='a'*32
        current_page={'session_id':current_session,'offset':20,'snapshot':'b'*64}
        current_job='2026-11-18_00-00-00-12345678'
        current_message={'job_id':current_job,'session_job_unique':False,'job':{'status':{'status':'completed'},'final_response':'HERMES_VIDEO_PROPOSAL'}}
        current_view={'id':current_session,'offset':20,'snapshot':'b'*64,'messages':[current_message]}
        with patch.object(operations_history_app,'execute_remote_management_command',return_value=current_view) as current_mock:
            current_rows,current_notice=operations_history_app.read_operations_current_page_receipts(current_session,current_page)
            self.assertEqual(current_rows,[])
            self.assertIn('확인하지 못한 메시지 1건',current_notice)
            current_mock.assert_called_once()
            del current_message['session_job_unique']
            self.assertEqual(operations_history_app.read_operations_current_page_receipts(current_session,current_page)[0],[])

    def test_queue_refresh_invalidates_priority_review(self):
        from tools.review.ui.gradio import operations_history_app
        current_interface_value=build_async_test_interface(operations_history_app.build_operations_history_interface)
        current_config_value=current_interface_value.get_config_file()
        current_component_labels={current_component['id']:current_component.get('props',{}).get('label') for current_component in current_config_value['components']}
        current_events=[current_event for current_event in current_config_value['dependencies'] if len(current_event['outputs'])==6 and any(current_component_labels.get(current_target[0])=='현재 대기 기록' and current_target[1]=='change' for current_target in current_event['targets'])]
        self.assertEqual(len(current_events),1)
        current_values=current_interface_value.fns[current_events[0]['id']].fn()
        self.assertIsNone(current_values[1])
        self.assertIsNone(current_values[2])
        self.assertFalse(current_values[4]['interactive'])
        self.assertFalse(current_values[5]['visible'])

    def test_new_gpu_review_clears_previous_confirmation(self):
        from tools.review.ui.gradio import operations_history_app
        current_priority_values=operations_history_app.start_operations_priority_review()
        current_reservation_values=operations_history_app.start_operations_reservation_review()
        for current_review_values in (current_priority_values,current_reservation_values):
            self.assertEqual(len(current_review_values[0]),32)
            self.assertFalse(current_review_values[1]['interactive'])
            self.assertIsNone(current_review_values[2])
            self.assertFalse(current_review_values[3]['visible'])
        self.assertFalse(current_reservation_values[4])
        current_interface_value=build_async_test_interface(operations_history_app.build_operations_history_interface)
        current_config_value=current_interface_value.get_config_file()
        for current_start_function,current_expected_count in ((operations_history_app.start_operations_priority_review,4),(operations_history_app.start_operations_reservation_review,5)):
            current_events=[current_event for current_event in current_config_value['dependencies'] if current_interface_value.fns[current_event['id']].fn is current_start_function]
            self.assertEqual(len(current_events),1)
            self.assertEqual(len(current_events[0]['outputs']),current_expected_count)

    def test_priority_review_rejects_late_target_or_token(self):
        from tools.review.ui.gradio import operations_history_app
        current_target_record={'service':'kimodo','id':'2026-11-18_00-00-00-12345678'}
        current_result_values=({'request_id':'priority_test'},'검토','priority_test',gr.update(visible=True))
        with patch.object(operations_history_app,'prepare_operations_priority_request',return_value=current_result_values):
            current_review_record=operations_history_app.collect_operations_priority_review(current_target_record,'old-token')
        self.assertEqual(operations_history_app.render_operations_priority_review({'service':'kimodo','id':'other'},'old-token',current_review_record),(gr.skip(),)*5)
        self.assertEqual(operations_history_app.render_operations_priority_review(current_target_record,'new-token',current_review_record),(gr.skip(),)*5)
        current_render_values=operations_history_app.render_operations_priority_review(current_target_record,'old-token',current_review_record)
        self.assertTrue(current_render_values[3]['visible'])
        self.assertTrue(current_render_values[4]['interactive'])

    def test_operations_priority_confirmation_and_receipt_recovery(self):
        from tools.review.ui.gradio import operations_history_app
        current_target={'service':'wan22-vace','id':'2026-11-18_12-00-00-12345678'}
        current_preview={'service':current_target['service'],'job_id':current_target['id'],'queue_position':2,'queue_count':3,'ticket_revision':'a'*64,'observed_at':'mock'}
        current_calls=[]
        def current_gateway(service,command,payload):
            current_calls.append((command,payload))
            if command=='hermes-priority-preview':return current_preview
            if command=='hermes-priority-receipt':return {'state':'not_found'}
            if command=='hermes-priority-submit':return {'request_id':payload['request_id'],'service':payload['service'],'job_id':payload['id'],'ticket_revision':payload['ticket_revision'],'state':'completed'}
            raise RuntimeError('unexpected')
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=current_gateway):
            current_request,current_notice,current_identifier,current_group=operations_history_app.prepare_operations_priority_request(current_target)
            self.assertEqual(current_request['request_id'],current_identifier)
            from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
            self.assertIsNotNone(HERMES_DELEGATION_ID_PATTERN.fullmatch(current_identifier))
            self.assertIn('순번 2 / 3',current_notice)
            self.assertTrue(current_group['visible'])
            self.assertNotIn('hermes-priority-submit',[current_item[0] for current_item in current_calls])
            current_request_after,current_notice,current_group=operations_history_app.submit_operations_priority_request(current_request,{'service':'kimodo','id':current_target['id']})
            self.assertIsNone(current_request_after)
            self.assertIn('바뀌었습니다',current_notice)
            self.assertNotIn('hermes-priority-submit',[current_item[0] for current_item in current_calls])
            current_request_after,current_notice,current_group=operations_history_app.submit_operations_priority_request(current_request,current_target)
            self.assertIsNone(current_request_after)
            self.assertIn('접수되었습니다',current_notice)
            self.assertFalse(current_group['visible'])
        current_receipt={'request_id':current_identifier,'service':current_target['service'],'job_id':current_target['id'],'ticket_revision':'a'*64,'state':'unknown'}
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=lambda service,command,payload: current_preview if command=='hermes-priority-preview' else current_receipt):
            current_request,current_notice,current_identifier_again,current_group=operations_history_app.prepare_operations_priority_request(current_target)
            self.assertIsNone(current_request)
            self.assertEqual(current_identifier_again,current_identifier)
            self.assertIn('결과를 확인할 수 없습니다',current_notice)
            self.assertFalse(current_group['visible'])
            self.assertIn('결과 확인 필요',operations_history_app.read_operations_priority_request(current_identifier))
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=OSError('offline')):
            current_request_after,current_notice,current_group=operations_history_app.submit_operations_priority_request({'request_id':current_identifier,**current_target,'ticket_revision':'a'*64},current_target)
            self.assertIsNone(current_request_after)
            self.assertIn('자동으로 다시 요청하지 않습니다',current_notice)

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_priority_preview_rechecks_verified_queue_target(self,current_gateway_mock):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app
        current_job='2026-11-18_12-00-00-12345678'
        current_rows=[['1','image',current_job,'kimodo']]
        current_target,current_message,current_button=operations_history_app.select_operations_priority_target(current_rows,SimpleNamespace(index=(0,1)))
        self.assertEqual(current_target,{'service':'kimodo','id':current_job})
        self.assertTrue(current_button['interactive'])
        current_gateway_mock.return_value={'service':'kimodo','job_id':current_job,'queue_position':2,'queue_count':3,'observed_at':'mock'}
        self.assertIn('관측 순번 2 / 3',operations_history_app.preview_operations_priority_target(current_target))
        self.assertIn('식별값이 빠진 티켓은 실행기 신원을 확인할 수 없습니다',operations_history_app.preview_operations_priority_target(current_target))
        self.assertEqual(current_gateway_mock.call_count,2)
        current_gateway_mock.assert_called_with('hermes-agent','hermes-priority-preview',current_target)
        current_gateway_mock.return_value['job_id']='different'
        self.assertIn('확인할 수 없습니다',operations_history_app.preview_operations_priority_target(current_target))
        current_rows[0][3]='미확인'
        current_target,current_message,current_button=operations_history_app.select_operations_priority_target(current_rows,SimpleNamespace(index=0))
        self.assertIsNone(current_target)
        self.assertFalse(current_button['interactive'])
        self.assertIn('확인되지 않았습니다',current_message)
        with self.assertRaises(gr.Error):operations_history_app.select_operations_priority_target(current_rows,SimpleNamespace(index=3))

    def test_building_billboard_reservation_selection_keeps_canonical_source(self):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app
        current_management_record={'queried_at':'now','reservations':{'status':'available','truncated':False,'records':[{'service':'image','job_id':'job-1','required_memory_mib':1,'state':'recorded','source_service':'billboard-generator'},{'service':'image','job_id':'job-2','required_memory_mib':2,'state':'recorded','source_service':'building-generator'}]}}
        _,_,current_rows,_=operations_history_app.summarize_operations_reservation_snapshot(current_management_record)
        for current_index_value,current_service_name in enumerate(('billboard-generator','building-generator')):
            with self.subTest(service=current_service_name):
                current_target,current_button,_=operations_history_app.select_operations_reservation_inspection(current_rows,SimpleNamespace(index=current_index_value))
                self.assertEqual(current_target,{'service':current_service_name,'job_id':'job-'+str(current_index_value+1)})
                self.assertTrue(current_button['interactive'])
        current_rows[0][-1]='미확인'
        self.assertIsNone(operations_history_app.select_operations_reservation_inspection(current_rows,SimpleNamespace(index=0))[0])
        current_rows.append(current_rows[1].copy())
        self.assertIsNone(operations_history_app.select_operations_reservation_inspection(current_rows,SimpleNamespace(index=1))[0])

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_generator_reservation_inspection_only_reads_matching_target(self,current_gateway_mock):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app
        current_rows=[['정리 확인 필요','image','job-12','1024','미제공','kimodo']]
        current_target,current_button,current_notice=operations_history_app.select_operations_reservation_inspection(current_rows,SimpleNamespace(index=0))
        self.assertTrue(current_button['interactive'])
        current_gateway_mock.return_value={'service':'kimodo','job_id':'job-12','executor':'not_observed','worker_leader':'verified_running','required_memory_mib':1024}
        current_message=operations_history_app.inspect_operations_reservation_target(current_target)
        self.assertIn('일치 실행기 미관측',current_message)
        self.assertIn('그룹 전체·별도 그룹의 종료를 보증하지 않습니다',current_message)
        current_gateway_mock.assert_called_once_with('hermes-agent','hermes-generator-reservation-inspect',current_target)
        current_gateway_mock.return_value['service']='dwpose'
        self.assertIn('확인할 수 없습니다',operations_history_app.inspect_operations_reservation_target(current_target))
        current_rows[0][5]='미확인'
        self.assertIsNone(operations_history_app.select_operations_reservation_inspection(current_rows,SimpleNamespace(index=0))[0])

    def test_reservation_review_rejects_late_target_or_token(self):
        from tools.review.ui.gradio import operations_history_app
        current_target_record={'service':'kimodo','job_id':'job-1'}
        current_result_values=({'service':'kimodo','job_id':'job-1'},'검토','recovery_id',gr.update(visible=True),False)
        with patch.object(operations_history_app,'prepare_operations_reservation_recovery',return_value=current_result_values):
            current_review_record=operations_history_app.collect_operations_reservation_recovery(current_target_record,'old-token')
        self.assertEqual(operations_history_app.render_operations_reservation_recovery({'service':'kimodo','job_id':'job-2'},'old-token',current_review_record),(gr.skip(),)*6)
        self.assertEqual(operations_history_app.render_operations_reservation_recovery(current_target_record,'new-token',current_review_record),(gr.skip(),)*6)
        current_render_values=operations_history_app.render_operations_reservation_recovery(current_target_record,'old-token',current_review_record)
        self.assertTrue(current_render_values[3]['visible'])
        self.assertFalse(current_render_values[4])
        self.assertTrue(current_render_values[5]['interactive'])

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_reservation_recovery_requires_confirmation_and_no_automatic_retry(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_target_record={'service':'kimodo','job_id':'job-12'}
        current_gateway_mock.side_effect=[{'service':'kimodo','job_id':'job-12','review_ready':True,'review_sha256':'a'*64},{'state':'not_found'}]
        current_request_record,current_notice,current_receipt_id,current_group,current_checked=operations_history_app.prepare_operations_reservation_recovery(current_target_record)
        self.assertTrue(current_group['visible'])
        self.assertFalse(current_checked)
        self.assertEqual(current_request_record['request_id'],current_receipt_id)
        from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
        self.assertIsNotNone(HERMES_DELEGATION_ID_PATTERN.fullmatch(current_receipt_id))
        current_gateway_mock.reset_mock(side_effect=True)
        current_result_record,current_notice,current_group=operations_history_app.submit_operations_reservation_recovery(current_request_record,current_target_record,False)
        self.assertIsNotNone(current_result_record)
        current_gateway_mock.assert_not_called()
        current_result_record,current_notice,current_group=operations_history_app.submit_operations_reservation_recovery(current_request_record,{'service':'dwpose','job_id':'job-12'},True)
        self.assertIsNone(current_result_record)
        current_gateway_mock.assert_not_called()
        current_gateway_mock.side_effect=OSError('response lost')
        current_result_record,current_notice,current_group=operations_history_app.submit_operations_reservation_recovery(current_request_record,current_target_record,True)
        self.assertIsNone(current_result_record)
        self.assertIn('다시 실행하지 마세요',current_notice)
        self.assertEqual(current_gateway_mock.call_count,1)
        self.assertFalse(current_group['visible'])

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_reservation_recovery_receipt_identifies_valid_target(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_request_id='recovery_'+'a'*64
        current_gateway_mock.return_value={'request_id':current_request_id,'state':'completed','service':'kimodo','job_id':'job-12'}
        current_message=operations_history_app.read_operations_reservation_recovery_receipt(current_request_id)
        self.assertIn('kimodo · job-12',current_message)
        self.assertIn('정리 완료',current_message)
        for current_bad_value in ({'service':'unknown'},{'job_id':'../bad'},{'request_id':'wrong'}):
            current_gateway_mock.return_value={'request_id':current_request_id,'state':'completed','service':'kimodo','job_id':'job-12',**current_bad_value}
            self.assertIn('확인할 수 없습니다',operations_history_app.read_operations_reservation_recovery_receipt(current_request_id))

    def test_reservation_selection_requires_verified_owner_and_unique_id(self):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app
        current_rows=[['정리 확인 필요','image','job-12','1024','미제공','kimodo']]
        current_result=operations_history_app.select_operations_reservation_target(current_rows,SimpleNamespace(index=(0,1)))
        self.assertIn('/management/frame/kimodo-generator/?job=job-12',current_result)
        self.assertIn('자동 정리하지 않으며',current_result)
        self.assertIn('상태 조회가 중단 기록을 복구',current_result)
        current_rows[0][5]='미확인'
        self.assertNotIn('<a ',operations_history_app.select_operations_reservation_target(current_rows,SimpleNamespace(index=0)))
        current_rows[0][5]='kimodo'
        current_rows.append(list(current_rows[0]))
        self.assertIn('중복',operations_history_app.select_operations_reservation_target(current_rows,SimpleNamespace(index=0)))
        current_rows.pop()
        current_rows[0][2]='<script>'
        self.assertNotIn('<script>',operations_history_app.select_operations_reservation_target(current_rows,SimpleNamespace(index=0)))

    def test_dedicated_queue_and_reservation_do_not_merge_different_services(self):
        from tools.review.ui.gradio import operations_history_app
        current_queue={('other-service','job-1'):1}
        self.assertIn('다른 GPU 서비스',operations_history_app.label_operations_dedicated_queue(current_queue,'writer-agent','job-1'))
        self.assertIn('대기 기록 없음',operations_history_app.label_operations_dedicated_queue(current_queue,'writer-agent','job-2'))
        current_queue[('writer-agent','job-1')]=1
        self.assertEqual(operations_history_app.label_operations_dedicated_queue(current_queue,'writer-agent','job-1'),'대기 기록 확인 · 다른 서비스 동일 ID · 우선 실행 확인 불가')
        current_queue.pop(('writer-agent','job-1'))
        current_queue[('image','job-1')]=1
        self.assertEqual(operations_history_app.label_operations_shared_queue_record(current_queue,{('image','kimodo','job-1'):1},'image','kimodo','job-1'),'대기 기록 확인 · 다른 서비스 동일 ID · 우선 실행 확인 불가')
        self.assertIn('다른 GPU 서비스',operations_history_app.label_operations_reservation_record({('other-service','job-1'):['recorded']},False,'writer-agent','job-1'))
        self.assertIn('미확인 기록 포함',operations_history_app.label_operations_reservation_record({('other-service','job-1'):['recorded']},True,'writer-agent','job-1'))

    def test_operations_receipt_links_require_confirmed_unique_jobs(self):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app
        current_rows=[['hermes-job','wan22-vace','request','접수 기록','job-a','대기','예약','해당 없음']]
        current_link=operations_history_app.select_operations_receipt_service(current_rows,SimpleNamespace(index=(0,1)))
        self.assertIn('/management/frame/wan22-vace-generator/',current_link)
        self.assertIn('?job=job-a',current_link)
        self.assertIn('입력이나 출처의 일치를 보증하지 않습니다',current_link)
        current_rows[0][3]='모델 준비 · 접수 기록'
        self.assertIn('?job=job-a',operations_history_app.select_operations_receipt_service(current_rows,SimpleNamespace(index=0)))
        current_rows.append([*current_rows[0][:3],'접수 기록',*current_rows[0][4:]])
        self.assertNotIn('?job=',operations_history_app.select_operations_receipt_service(current_rows,SimpleNamespace(index=0)))
        current_rows.pop()
        current_rows[0][3]='접수 기록'
        current_rows.append(list(current_rows[0]))
        self.assertNotIn('?job=',operations_history_app.select_operations_receipt_service(current_rows,SimpleNamespace(index=0)))
        current_rows.pop()
        current_rows[0][3]='접수 확인 필요'
        self.assertNotIn('?job=',operations_history_app.select_operations_receipt_service(current_rows,SimpleNamespace(index=0)))
        current_rows[0][3]='접수 기록'
        current_rows[0][4]='../bad'
        self.assertNotIn('?job=',operations_history_app.select_operations_receipt_service(current_rows,SimpleNamespace(index=0)))
        current_rows[0][1]='<script>bad</script>'
        self.assertNotIn('<script>',operations_history_app.select_operations_receipt_service(current_rows,SimpleNamespace(index=0)))
        with self.assertRaises(gr.Error):operations_history_app.select_operations_receipt_service(current_rows,SimpleNamespace(index=2))

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_writer_apply_receipt_requires_matching_ids(self,current_gateway_mock):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_session='a'*32
        current_job='source-job'
        current_seed=current_session+':'+current_job+':writer'
        current_request='chat_'+hashlib.sha256(current_seed.encode()).hexdigest()
        current_apply='chat_apply_'+hashlib.sha256(current_seed.encode()).hexdigest()
        current_apply_receipt={'state':'completed','request_id':current_apply,'writer_request_id':current_request,'job_id':'writer-job'}
        def current_gateway_response(current_service,current_command,current_payload):
            if current_command=='hermes-session-view':return {'id':'a'*32,'messages':[{'job_id':current_job,'job':{'status':{'status':'completed'},'final_response':'HERMES_WRITER_PROPOSAL'}}]}
            if current_command=='hermes-writer-proposal':return {'id':'a'*32,'job_id':current_job,'proposal':{'mode':'write','prompt':'test'}}
            if current_command=='hermes-writer-history':return {'records':[{'request_id':current_request,'service':'writer-agent','state':'accepted','job_id':'writer-job'}],'truncated':False}
            if current_command=='hermes-management-status':return {'queue':{'status':'available','jobs':[{'service':'writer-agent','id':'writer-job'}]},'reservations':{'status':'available','records':[],'truncated':False},'queried_at':'mock'}
            if current_command=='hermes-writer-apply-status':return current_apply_receipt.copy()
            raise AssertionError(current_command)
        current_gateway_mock.side_effect=current_gateway_response
        current_rows,_=operations_history_app.read_operations_session_receipts(current_session)
        self.assertEqual(current_rows[0][5],'대기 기록 확인')
        self.assertEqual(current_rows[0][7],'적용 완료 기록')
        current_apply_receipt['job_id']='different-job'
        self.assertEqual(operations_history_app.read_operations_session_receipts(current_session)[0][0][7],'적용 연결 확인 불가')
        current_apply_receipt['job_id']='writer-job'
        current_apply_receipt['state']='unknown'
        self.assertEqual(operations_history_app.read_operations_session_receipts(current_session)[0][0][7],'적용 확인 필요')
        self.assertNotIn('hermes-writer-apply',[item.args[1] for item in current_gateway_mock.call_args_list])

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_session_receipt_reports_unsaved_edit(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-view':return {'id':'a'*32,'messages':[{'job_id':'job-field','job':{'status':{'status':'completed'},'final_response':'HERMES_FIELD_PROPOSAL'}}]}
            if current_command_name=='hermes-field-proposal':return {'id':'a'*32,'job_id':'job-field','proposal':{'map':'moss-clearing'}}
            if current_command_name=='hermes-field-receipt':return {'state':'completed','saved':False,'request_id':current_payload_record['request_id'],'map':'moss-clearing'}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        self.assertEqual(operations_history_app.read_operations_session_receipts('a'*32)[0][0][3],'저장되지 않음')
        def current_wrong_map_response(current_service_name,current_command_name,current_payload_record):
            current_result=current_gateway_response(current_service_name,current_command_name,current_payload_record)
            if current_command_name=='hermes-field-receipt':current_result['map']='grove'
            return current_result
        current_gateway_mock.side_effect=current_wrong_map_response
        self.assertEqual(operations_history_app.read_operations_session_receipts('a'*32)[0][0][3],'제안 또는 접수 조회 불가')

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_session_receipt_rejects_duplicate_or_truncated_proposals(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_message={'job_id':'job-a','job':{'status':{'status':'completed'},'final_response':'HERMES_KIMODO_PROPOSAL','final_response_truncated':True}}
        current_gateway_mock.return_value={'id':'a'*32,'messages':[current_message]}
        current_rows,current_notice=operations_history_app.read_operations_session_receipts('a'*32)
        self.assertEqual(current_rows,[])
        self.assertIn('확인하지 못한 메시지',current_notice)
        current_message['job']['final_response_truncated']=False
        current_gateway_mock.return_value={'id':'a'*32,'messages':[current_message,current_message]}
        self.assertEqual(operations_history_app.read_operations_session_receipts('a'*32)[0],[])
        self.assertTrue(all(item.args[1]=='hermes-session-view' for item in current_gateway_mock.call_args_list))

    def test_audio_resume_review_requires_selected_row_and_tracks_receipt(self):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_page_value={'service':'music-heartmula','snapshot':'a'*64}
        current_rows_value=[[current_job_identifier,'실패 기록','작업 상태 파일','조회 불가','조회 불가']]
        def current_gateway_response(current_service_name,current_command_name,current_payload_value):
            if current_command_name=='hermes-audio-resume-preview':return {'service':'music-heartmula','job_id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'b'*64,'resume_availability':'available'}
            if current_command_name=='hermes-audio-resume-receipt':return {'state':'not_found','request_id':current_payload_value['request_id']}
            if current_command_name=='hermes-audio-resume-submit':return {**current_payload_value,'state':'accepted'}
            raise AssertionError(current_command_name)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=current_gateway_response) as current_gateway_mock:
            current_request_value,current_notice_value,current_identifier_value=operations_history_app.prepare_operations_audio_resume('music-heartmula',current_job_identifier,current_page_value,current_rows_value)
            self.assertIn('재개 검토',current_notice_value)
            self.assertEqual(current_request_value['request_id'],current_identifier_value)
            self.assertNotIn('hermes-audio-resume-submit',[item.args[1] for item in current_gateway_mock.call_args_list])
            self.assertIn('바뀌었습니다',operations_history_app.submit_operations_audio_resume(current_request_value,'music-heartmula','other',current_page_value,current_rows_value)[1])
            self.assertIn('바뀌었습니다',operations_history_app.submit_operations_audio_resume(current_request_value,'music-heartmula',current_job_identifier,{**current_page_value,'snapshot':'c'*64},current_rows_value)[1])
            self.assertNotIn('hermes-audio-resume-submit',[item.args[1] for item in current_gateway_mock.call_args_list])
            self.assertIn('대기열에 접수',operations_history_app.submit_operations_audio_resume(current_request_value,'music-heartmula',current_job_identifier,current_page_value,current_rows_value)[1])
            self.assertIn('바뀌었습니다',operations_history_app.submit_operations_audio_resume(current_request_value,'music-heartmula',current_job_identifier,current_page_value,[])[1])
            self.assertIsNone(operations_history_app.prepare_operations_audio_resume('music-heartmula',current_job_identifier,current_page_value,[])[0])

    def test_trans_resume_review_uses_shared_history_and_fixed_commands(self):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_page_value={'service':'prompt-translation','snapshot':'a'*64}
        current_rows_value=[[current_job_identifier,'실패 기록','작업 상태 파일','조회 불가','조회 불가']]
        def current_gateway_response(current_service_name,current_command_name,current_payload_value):
            if current_command_name=='hermes-translation-resume-preview':return {'service':'prompt-translation','job_id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'b'*64}
            if current_command_name=='hermes-translation-resume-receipt':return {'state':'not_found','request_id':current_payload_value['request_id']}
            if current_command_name=='hermes-translation-resume-submit':return {**current_payload_value,'service':'prompt-translation','state':'accepted'}
            raise AssertionError(current_command_name)
        with patch.object(operations_history_app,'execute_remote_management_command',side_effect=current_gateway_response) as current_gateway_mock:
            current_request_value,current_notice_value,current_identifier_value=operations_history_app.prepare_operations_audio_resume('prompt-translation',current_job_identifier,current_page_value,current_rows_value)
            self.assertTrue(current_identifier_value.startswith('trans_resume_'))
            from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
            self.assertIsNotNone(HERMES_DELEGATION_ID_PATTERN.fullmatch(current_identifier_value))
            self.assertIn('재개 검토',current_notice_value)
            self.assertIn('바뀌었습니다',operations_history_app.submit_operations_audio_resume(current_request_value,'prompt-translation',current_job_identifier,{**current_page_value,'snapshot':'c'*64},current_rows_value)[1])
            self.assertNotIn('hermes-translation-resume-submit',[item.args[1] for item in current_gateway_mock.call_args_list])
            self.assertIn('대기열에 접수',operations_history_app.submit_operations_audio_resume(current_request_value,'prompt-translation',current_job_identifier,current_page_value,current_rows_value)[1])
            current_submit_payload=next(item.args[2] for item in current_gateway_mock.call_args_list if item.args[1]=='hermes-translation-resume-submit')
            self.assertNotIn('service',current_submit_payload)
            self.assertEqual(set(current_submit_payload),{'request_id','job_id','expected_resume_fingerprint'})

    def test_history_resume_generated_ids_reach_receipt_store(self):
        from tempfile import TemporaryDirectory
        from tools.review.domains.hermes_agent import audio_resume_operations,translation_resume_operations
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-18_00-00-00-12345678'
        with TemporaryDirectory() as current_directory_name,patch.object(audio_resume_operations,'AUDIO_RESUME_RECEIPT_ROOT',Path(current_directory_name)/'audio'),patch.object(translation_resume_operations,'TRANSLATION_RESUME_RECEIPT_ROOT',Path(current_directory_name)/'translation'):
            for current_service_name in ('music-heartmula','sfx-dasheng-audiogen','prompt-translation'):
                with self.subTest(service=current_service_name):
                    current_page_value={'service':current_service_name,'snapshot':'a'*64}
                    current_rows_value=[[current_job_identifier,'실패 기록','작업 상태 파일','조회 불가','조회 불가']]
                    def read_current_resume_gateway(current_target_service,current_command_name,current_payload_value):
                        if current_command_name.endswith('-preview'):
                            return {'service':current_service_name,'job_id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'b'*64,'resume_availability':'available'}
                        if current_command_name=='hermes-translation-resume-receipt':
                            return translation_resume_operations.read_hermes_translation_resume_receipt(current_payload_value['request_id'])
                        if current_command_name=='hermes-audio-resume-receipt':
                            return audio_resume_operations.read_hermes_audio_resume_receipt(current_payload_value['request_id'])
                        raise AssertionError(current_command_name)
                    with patch.object(operations_history_app,'execute_remote_management_command',side_effect=read_current_resume_gateway):
                        current_request_value,current_notice_value,current_identifier_value=operations_history_app.prepare_operations_audio_resume(current_service_name,current_job_identifier,current_page_value,current_rows_value)
                    self.assertIsNotNone(current_request_value)
                    self.assertEqual(current_request_value['request_id'],current_identifier_value)
                    self.assertIn('재개 검토',current_notice_value)

    def test_trans_resume_confirmation_rejects_changed_history_page(self):
        from tools.review.ui.gradio import operations_history_app
        current_blocks_value=build_async_test_interface(operations_history_app.build_operations_history_interface)
        current_prepare_values=[item.fn for item in current_blocks_value.fns.values() if item.fn and item.fn.__name__=='prepare_generation_confirmation']
        current_confirm_values=[item.fn for item in current_blocks_value.fns.values() if item.fn and item.fn.__name__=='execute_confirmed_generation']
        self.assertEqual(len(current_prepare_values),1)
        self.assertEqual(len(current_confirm_values),1)
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_request_value={'request_id':'trans_resume_'+'a'*64,'service':'prompt-translation','job_id':current_job_identifier,'expected_resume_fingerprint':'b'*64}
        current_page_value={'service':'prompt-translation','snapshot':'c'*64}
        current_rows_value=[[current_job_identifier,'실패 기록','작업 상태 파일','조회 불가','조회 불가']]
        current_input_values=(current_request_value,'prompt-translation',current_job_identifier,current_page_value,current_rows_value)
        current_pending_value=current_prepare_values[0](*current_input_values)[0]
        with patch.object(operations_history_app,'execute_remote_management_command') as current_gateway_mock:
            with self.assertRaises(gr.Error):
                list(current_confirm_values[0](current_pending_value,current_request_value,'prompt-translation',current_job_identifier,{**current_page_value,'snapshot':'d'*64},current_rows_value))
            current_gateway_mock.assert_not_called()
            current_pending_value=current_prepare_values[0](*current_input_values)[0]
            with self.assertRaises(gr.Error):
                list(current_confirm_values[0](current_pending_value,current_request_value,'prompt-translation',current_job_identifier,current_page_value,[]))
            current_gateway_mock.assert_not_called()

    def test_audio_resume_receipt_display_rejects_mismatched_target(self):
        import hashlib
        from tools.review.ui.gradio import operations_history_app
        current_service_name='music-heartmula'
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_fingerprint_value='b'*64
        current_request_identifier='audio_resume_'+hashlib.sha256((current_service_name+'\0'+current_job_identifier+'\0'+current_fingerprint_value).encode()).hexdigest()
        current_receipt_value={'state':'accepted','request_id':current_request_identifier,'service':current_service_name,'job_id':current_job_identifier,'expected_resume_fingerprint':current_fingerprint_value}
        with patch.object(operations_history_app,'execute_remote_management_command',return_value=current_receipt_value):
            self.assertIn('대기열 접수 기록',operations_history_app.read_operations_audio_resume_receipt(current_request_identifier))
            for current_field_name,current_bad_value in (('service','sfx-dasheng-audiogen'),('job_id','2026-11-18_00-00-00-ffffffff'),('expected_resume_fingerprint','c'*64)):
                current_original_value=current_receipt_value[current_field_name]
                current_receipt_value[current_field_name]=current_bad_value
                with self.subTest(current_field_name=current_field_name):
                    self.assertIn('확인할 수 없습니다',operations_history_app.read_operations_audio_resume_receipt(current_request_identifier))
                current_receipt_value[current_field_name]=current_original_value

    def test_resume_receipt_supports_mcp_identifier_with_selected_service(self):
        from tools.review.ui.gradio import operations_history_app
        current_receipt_value={'state':'unknown','request_id':'mcp_request_123','service':'kimodo','job_id':'2026-11-18_00-00-00-12345678','expected_resume_fingerprint':'b'*64}
        with patch.object(operations_history_app,'execute_remote_management_command',return_value=current_receipt_value) as current_gateway_mock:
            self.assertIn('접수 결과 확인 필요',operations_history_app.read_operations_audio_resume_receipt('mcp_request_123','kimodo'))
            current_gateway_mock.assert_called_once_with('hermes-agent','hermes-kimodo-resume-receipt',{'request_id':'mcp_request_123'})
            self.assertIn('확인할 수 없습니다',operations_history_app.read_operations_audio_resume_receipt('mcp_request_123','music-heartmula'))
            self.assertIn('확인할 수 없습니다',operations_history_app.read_operations_audio_resume_receipt('mcp_request_123'))
            self.assertIn('확인할 수 없습니다',operations_history_app.read_operations_audio_resume_receipt('../invalid','kimodo'))

    def test_source_history_selection_uses_validated_page_and_original_owner(self):
        from types import SimpleNamespace
        from tools.review.ui.gradio import operations_history_app
        current_page={'service':'building-generator','snapshot':'a'*64,'next_offset':None}
        current_rows=[['old_job-123','완료','작업 상태 파일','조회 불가','조회 불가']]
        with patch.object(operations_history_app,'execute_remote_management_command') as current_gateway:
            current_identifier,current_link=operations_history_app.select_operations_source_job('building-generator',current_page,current_rows,SimpleNamespace(index=(0,0)))
            self.assertEqual(current_identifier,'old_job-123')
            self.assertIn('원본 서비스: billboard-generator',current_link)
            self.assertIn('자동 선택하지 않습니다',current_link)
            self.assertIn('도구 이동 링크는 제공되지 않습니다',current_link)
            self.assertNotIn('<a ',current_link)
            current_gateway.assert_not_called()
            with self.assertRaises(gr.Error):operations_history_app.select_operations_source_job('kimodo',current_page,current_rows,SimpleNamespace(index=0))
            with self.assertRaises(gr.Error):operations_history_app.select_operations_source_job('building-generator',current_page,[['<script>','x','x','x','x']],SimpleNamespace(index=0))
            with self.assertRaises(gr.Error):operations_history_app.select_operations_source_job('building-generator',current_page,current_rows,SimpleNamespace(index=1))

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_source_history_paginates_and_matches_verified_source(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_snapshot_value='a'*64
        current_first_items=[{'id':'job-'+str(index),'recorded_status':'queued','status_source':'job'} for index in range(30)]
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-generator-source-history':
                current_offset_value=current_payload_record.get('offset',0)
                current_records_value=current_first_items if current_offset_value==0 else [{'id':'job-last','recorded_status':'completed','status_source':'index'}]
                return {'service':'building-generator','source_service':'billboard-generator','records':current_records_value,'total':31,'offset':current_offset_value,'next_offset':30 if current_offset_value==0 else None,'snapshot':current_snapshot_value,'unavailable_count':0}
            if current_command_name=='hermes-management-status':return {'queried_at':'time','queue':{'status':'available','jobs':[{'service':'building-generator','id':'job-0'},{'service':'billboard-generator','id':'job-1'}]}}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_search_result=operations_history_app.read_operations_source_history('building-generator',current_search_text='job-0')
        self.assertEqual(current_search_result[0],[])
        self.assertIn('조회 불가',current_search_result[1])
        self.assertEqual(current_gateway_mock.call_args.args[2]['query'],'job-0')
        current_rows,current_notice,current_state,current_next_update,_=operations_history_app.read_operations_source_history('building-generator')
        self.assertEqual(current_rows[0][1],'대기')
        self.assertEqual(operations_history_app.describe_operations_source_status('completed'),'완료 기록')
        self.assertEqual(operations_history_app.describe_operations_source_status('not-a-known-status'),'확인 불가')
        self.assertEqual(current_rows[0][3],'다른 GPU 서비스 동일 ID · 소유 확인 필요')
        self.assertEqual(current_rows[1][3],'다른 GPU 서비스 동일 ID · 소유 확인 필요')
        self.assertIn('원본 billboard-generator',current_notice)
        self.assertTrue(current_next_update['interactive'])
        current_next_rows,_,current_second_state,current_next_update,_=operations_history_app.read_next_operations_source_history('building-generator',current_state)
        self.assertEqual(current_next_rows[0][0],'job-last')
        self.assertFalse(current_next_update['interactive'])
        current_previous_rows,_,current_previous_state,_,_=operations_history_app.read_previous_operations_source_history('building-generator',current_second_state)
        self.assertEqual(current_previous_rows[0][0],'job-0')
        self.assertEqual(current_previous_state['offset'],0)
        self.assertEqual(current_gateway_mock.call_args_list[-2].args[2]['snapshot'],current_snapshot_value)
        self.assertFalse(operations_history_app.render_operations_source_history_page('building-generator',current_second_state,'previous')[-1]['interactive'])
        current_call_count=current_gateway_mock.call_count
        current_wrong_rows,current_wrong_notice,_,_,_=operations_history_app.read_next_operations_source_history('kimodo',current_state)
        self.assertEqual(current_wrong_rows,[])
        self.assertIn('처음부터',current_wrong_notice)
        self.assertEqual(current_gateway_mock.call_count,current_call_count)

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_source_history_queue_failure_and_snapshot_mismatch(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-generator-source-history':return {'service':'kimodo','source_service':'kimodo','records':[{'id':'job-a','recorded_status':'running','status_source':'job'}],'total':1,'offset':current_payload_record.get('offset',0),'next_offset':None,'snapshot':'b'*64,'unavailable_count':0}
            if current_command_name=='hermes-management-status':raise OSError('queue unavailable')
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_rows,current_notice,_,_,_=operations_history_app.read_operations_source_history('kimodo')
        self.assertEqual(current_rows[0][3],'조회 불가')
        self.assertIn('GPU 대기 관측 조회 불가',current_notice)
        current_rows,current_notice,_,current_next_update,_=operations_history_app.read_next_operations_source_history('kimodo',{'service':'kimodo','next_offset':0,'snapshot':'a'*64})
        self.assertEqual(current_rows,[])
        self.assertIn('처음부터',current_notice)
        self.assertFalse(current_next_update['interactive'])
        current_rows,current_notice,_,_,_=operations_history_app.read_previous_operations_source_history('kimodo',{'service':'kimodo','offset':30,'snapshot':'a'*64})
        self.assertEqual(current_rows,[])
        self.assertIn('처음부터',current_notice)

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_reservations_distinguish_matching_unknown_and_duplicates(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-18_00-24-38-0f938e1b'
        current_reservation_values=[{'state':'cleanup_unverified','service':'writer-agent','job_id':current_job_identifier,'required_memory_mib':4096,'worker_leader':'verified_running'}, {'state':'recorded','service':'hermes-agent','job_id':current_job_identifier,'required_memory_mib':32768}, {'state':'unknown','service':None,'job_id':None,'required_memory_mib':None}]
        current_snapshot_record={'queried_at':'now','reservations':{'status':'available','records':current_reservation_values,'truncated':False}}
        current_index_value,current_unmatched_value,current_rows_value,current_notice_text=operations_history_app.summarize_operations_reservation_snapshot(current_snapshot_record)
        self.assertTrue(current_unmatched_value)
        self.assertEqual(operations_history_app.label_operations_reservation_record(current_index_value,current_unmatched_value,'writer-agent',current_job_identifier),'정리 확인 필요 · 미확인 기록 포함')
        self.assertIn('그룹 전체는 미확인',current_rows_value[0][4])
        self.assertEqual(operations_history_app.label_operations_reservation_record(current_index_value,current_unmatched_value,'flux-image',current_job_identifier),'다른 GPU 서비스 동일 ID · 소유 확인 필요 · 미확인 기록 포함')
        self.assertIn('생존이나 예약 해제를 보장하지 않습니다',current_notice_text)
        current_reservation_values.append(current_reservation_values[1].copy())
        current_index_value,current_unmatched_value,_,_=operations_history_app.summarize_operations_reservation_snapshot(current_snapshot_record)
        self.assertEqual(operations_history_app.label_operations_reservation_record(current_index_value,current_unmatched_value,'hermes-agent',current_job_identifier),'연결 불확실 · 중복 예약')
        current_gateway_mock.assert_not_called()

    @patch('tools.review.ui.gradio.operations_history_app.execute_remote_management_command')
    def test_operations_reservation_failure_is_independent_of_queue(self,current_gateway_mock):
        from tools.review.ui.gradio import operations_history_app
        current_job_identifier='2026-11-18_00-24-38-0f938e1b'
        def current_gateway_response(current_service_name,current_command_name,current_payload_record):
            if current_command_name=='hermes-session-list':return {'sessions':[]}
            if current_command_name=='hermes-management-status':return {'queried_at':'now','queue':{'status':'available','jobs':[{'service':'hermes-agent','id':current_job_identifier}]},'reservations':{'status':'unavailable','records':[],'truncated':False}}
            if current_command_name=='hermes-history':return {'records':[{'id':current_job_identifier,'status':{'status':'queued'},'request':{'prompt':'test'}}]}
            raise AssertionError(current_command_name)
        current_gateway_mock.side_effect=current_gateway_response
        current_result_value=operations_history_app.read_operations_history_overview()
        self.assertEqual(current_result_value[2][0][2],'대기 기록 확인')
        self.assertEqual(current_result_value[2][0][4],'조회 불가')
        self.assertIn('예약이 없다는 뜻이 아닙니다',current_result_value[8])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_sprite_proposal_rejects_stale_snapshot(self,current_gateway_mock):
        import json
        current_proposal_record={'path':'assets/characters/default/animations/test/sheet.png','snapshot':'a'*64,'columns':4,'anchors':[{'frame_id':'idle.0','x':1,'y':2}]}
        current_detail_record={'path':current_proposal_record['path'],'snapshot':'a'*64,'metadata_sha256':'b'*64}
        current_gateway_mock.side_effect=[{'job_id':'job-1','proposal':current_proposal_record},current_detail_record]
        current_result_value=hermes_agent_app.load_hermes_sprite_anchor_proposal('job-1')
        self.assertEqual(json.loads(current_result_value[1]),current_proposal_record)
        self.assertIsNone(current_result_value[3])
        current_gateway_mock.side_effect=[{'job_id':'job-1','proposal':current_proposal_record},{**current_detail_record,'snapshot':'c'*64}]
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
        current_gateway_mock.side_effect=[{'job_id':'job-1','proposal':current_proposal_record},current_detail_record]
        current_result_value=hermes_agent_app.load_hermes_effect_edit_proposal('job-1')
        self.assertEqual(json.loads(current_result_value[2]),current_proposal_record)
        self.assertIsNone(current_result_value[4])
        current_gateway_mock.side_effect=[{'job_id':'job-1','proposal':current_proposal_record},{**current_detail_record,'revision':'b'*64}]
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
        current_gateway_mock.side_effect=[{'job_id':'job-1','proposal':current_proposal_record},{'texture':'tree-v1','revision':'new','properties':{'displayHeight':520}}]
        current_result_value=hermes_agent_app.load_hermes_billboard_edit_proposal('job-1')
        self.assertEqual(json.loads(current_result_value[2]),{'revision':'new','changes':[{'texture':'tree-v1','values':{'displayHeight':500}}]})
        self.assertIsNone(current_result_value[4])
        current_gateway_mock.side_effect=[{'job_id':'job-1','proposal':current_proposal_record},{'texture':'tree-v1','revision':'new','properties':{'displayHeight':521}}]
        with self.assertRaises(gr.Error):
            hermes_agent_app.load_hermes_billboard_edit_proposal('job-1')
        self.assertEqual([current_call.args[1] for current_call in current_gateway_mock.call_args_list],['hermes-billboard-proposal','hermes-billboard-load']*2)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_edit_proposals_reject_other_job_before_loading_source(self,current_gateway_mock):
        for current_loader_function in (hermes_agent_app.load_hermes_sprite_anchor_proposal,hermes_agent_app.load_hermes_effect_edit_proposal,hermes_agent_app.load_hermes_billboard_edit_proposal):
            with self.subTest(loader=current_loader_function.__name__):
                current_gateway_mock.reset_mock()
                current_gateway_mock.return_value={'job_id':'other-job','proposal':{}}
                with self.assertRaises(gr.Error):current_loader_function('job-1')
                self.assertEqual(current_gateway_mock.call_count,1)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_edit_proposals_reject_different_source(self,current_gateway_mock):
        current_cases_values=(
            (hermes_agent_app.load_hermes_sprite_anchor_proposal,{'path':'a','snapshot':'hash'},{'path':'b','snapshot':'hash','metadata_sha256':'hash'}),
            (hermes_agent_app.load_hermes_effect_edit_proposal,{'id':'a','revision':'hash'},{'id':'b','revision':'hash'}),
            (hermes_agent_app.load_hermes_billboard_edit_proposal,{'texture':'a'},{'texture':'b'}),
        )
        for current_loader_function,current_proposal_record,current_source_record in current_cases_values:
            with self.subTest(loader=current_loader_function.__name__):
                current_gateway_mock.side_effect=[{'job_id':'job-1','proposal':current_proposal_record},current_source_record]
                with self.assertRaises(gr.Error):current_loader_function('job-1')

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
        current_gateway_mock.return_value={'job_id':'job-1','proposal':{'service':'wan22-vace','mode':'video_edit','prompt':'change the background'}}
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
        current_gateway_mock.return_value={'job_id':'job-1','proposal':{'service':'music-heartmula','request':{'action':'generate','prompt':'piano','lyrics':'[Verse]\nHello','duration_seconds':30,'seed':7,'loop_request':False}}}
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
    def test_writer_apply_receipt_requires_matching_completed_record(self,current_gateway_mock):
        current_request='apply_request_123'
        current_job='20261118-120000-12345678'
        for current_reply in ({'state':'unknown'}, {'state':'invalid','request_id':current_request,'job_id':current_job}, {'state':'completed','request_id':'different','job_id':current_job}, {'state':'completed','request_id':current_request,'job_id':'../bad'}):
            with self.subTest(reply=current_reply):
                current_gateway_mock.return_value=current_reply
                current_result=hermes_agent_app.read_hermes_writer_apply_receipt(current_request)
                self.assertIn('확인 필요',current_result)
                self.assertNotIn('적용 완료',current_result)
        current_gateway_mock.return_value={'state':'completed','request_id':current_request,'job_id':current_job}
        self.assertIn('적용 완료',hermes_agent_app.read_hermes_writer_apply_receipt(current_request))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_writer_apply_requires_full_review_and_unchanged_confirmation(self,current_gateway_mock):
        current_gateway_mock.return_value={'receipt':{'state':'accepted','request_id':'writer_request_123','service':'writer-agent','job_id':'20261118-120000-12345678'},'job':{'stage':'review','proposal_hash':'a'*64,'truncated':False,'changes':[{'path':'town.md','diff':'-a\n+b'}]}}
        with self.assertRaises(gr.Error):
            hermes_agent_app.review_hermes_writer_apply('writer_request_123','apply_request_123',False)
        current_gateway_mock.assert_not_called()
        current_review_value,current_diff_value,current_group_value,current_summary_value=hermes_agent_app.review_hermes_writer_apply('writer_request_123','apply_request_123',True)
        self.assertTrue(current_group_value['visible'])
        for current_bad_value in ('bad',None,12):
            current_gateway_mock.return_value['job']['proposal_hash']=current_bad_value
            with self.assertRaises(gr.Error):hermes_agent_app.review_hermes_writer_apply('writer_request_123','apply_request_123',True)
        current_gateway_mock.return_value['job']['proposal_hash']='a'*64
        current_gateway_mock.reset_mock()
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_writer_apply(current_review_value,'writer_request_123','different_123',True)
        current_gateway_mock.assert_not_called()
        current_gateway_mock.return_value={'state':'completed',**current_review_value}
        self.assertIn('원본에 적용',hermes_agent_app.submit_hermes_writer_apply(current_review_value,'writer_request_123','apply_request_123',True)[2])
        current_gateway_mock.return_value={'state':'completed',**current_review_value,'job_id':'20261118-120000-87654321'}
        self.assertIn('적용 결과 확인 필요',hermes_agent_app.submit_hermes_writer_apply(current_review_value,'writer_request_123','apply_request_123',True)[2])
        current_gateway_mock.side_effect=OSError('lost')
        current_after,current_group,current_notice=hermes_agent_app.submit_hermes_writer_apply(current_review_value,'writer_request_123','apply_request_123',True)
        self.assertIsNone(current_after)
        self.assertFalse(current_group['visible'])
        self.assertIn('자동 재적용하지 마세요',current_notice)

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
        current_gateway_mock.return_value={'job_id':'job-1','proposal':{'text':'푸른 나무','target_language':'en','glossary':[{'source':'나무','target':'tree'}]}}
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

    def test_field_save_button_follows_confirmed_availability(self):
        for current_review_record,current_expected_value in ((None,False),({},False),({'save_available':False},False),({'save_available':None},False),({'save_available':1},False),({'save_available':True},True)):
            with self.subTest(review=current_review_record):
                self.assertEqual(hermes_agent_app.update_field_save_button(current_review_record)['interactive'],current_expected_value)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_field_database_preview_does_not_submit_save(self,current_gateway_mock):
        current_draft_text='{"map":"sample","revision":"revision","cells":[],"objects":[]}'
        current_gateway_mock.return_value={'token':'a'*64,'changed':True,'cells':0,'objects':0,'reachable':1,'save_available':False,'save_block_reason':'database'}
        current_review_value,current_summary_value,_=hermes_agent_app.review_hermes_field_map_draft(current_draft_text,'field_request_123')
        self.assertIn('DB 모드 신규 저장 중단',current_summary_value)
        self.assertIn('요청을 보내지 않았습니다',hermes_agent_app.save_hermes_field_map_draft(current_review_value,current_draft_text,'field_request_123')[2])
        self.assertEqual(current_gateway_mock.call_count,1)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_flux_readiness_summary_explains_file_and_gpu_scope(self,current_gateway_mock):
        current_gateway_mock.return_value={'service':'flux-image','status':'available','ready':True,'artifacts_ready':None,'generation_ready':True,'preparation_status':'idle','prepare_allowed':True,'queried_at':'now'}
        current_summary_text=hermes_agent_app.read_hermes_model_readiness_summary('flux-image')
        self.assertIn('모델 파일 크기 기준',current_summary_text)
        self.assertIn('한국어 번역 준비와 GPU 생성 검증은 별도',current_summary_text)

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
        current_gateway_mock.return_value={'state':'completed','saved':False,'request_id':'city_request_123','map':'stonewarm'}
        self.assertIn('DB에 저장되지 않음',hermes_agent_app.save_hermes_city_map_draft(current_review_value,current_draft_text,'city_request_123')[2])
        current_gateway_mock.return_value={'state':'completed','saved':True,'request_id':'city_request_123','map':'stonewarm'}
        self.assertIn('콘텐츠 DB 저장 완료',hermes_agent_app.save_hermes_city_map_draft(current_review_value,current_draft_text,'city_request_123')[2])
        current_gateway_mock.return_value['map']='other'
        current_state,current_group,current_notice=hermes_agent_app.save_hermes_city_map_draft(current_review_value,current_draft_text,'city_request_123')
        self.assertIsNone(current_state)
        self.assertFalse(current_group['visible'])
        self.assertIn('자동 재접수하지 마세요',current_notice)
        current_gateway_mock.side_effect=OSError('lost')
        self.assertIn('저장 결과 확인 필요',hermes_agent_app.save_hermes_city_map_draft(current_review_value,current_draft_text,'city_request_123')[2])

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
        current_gateway_mock.side_effect=[{'job_id':'job-1','proposal':current_proposal_value},current_map_value]
        current_result_value=hermes_agent_app.load_hermes_field_map_proposal('job-1')
        current_draft_value=json.loads(current_result_value[1])
        self.assertEqual(current_draft_value['cells'],[current_cell_value])
        self.assertEqual(current_draft_value['objects'],[current_object_value])
        self.assertIsNone(current_result_value[4])
        self.assertFalse(current_result_value[5]['visible'])
        self.assertEqual([item.args[1] for item in current_gateway_mock.call_args_list],['hermes-field-proposal','hermes-field-load'])
        current_gateway_mock.side_effect=[{'job_id':'job-1','proposal':current_proposal_value},{**current_map_value,'revision':'r2'}]
        with self.assertRaises(gr.Error):
            hermes_agent_app.load_hermes_field_map_proposal('job-1')
        current_gateway_mock.side_effect=[{'job_id':'different','proposal':current_proposal_value}]
        with self.assertRaises(gr.Error):hermes_agent_app.load_hermes_field_map_proposal('job-1')
        current_gateway_mock.side_effect=[{'job_id':'job-1','proposal':current_proposal_value},{**current_map_value,'map':'other'}]
        with self.assertRaises(gr.Error):hermes_agent_app.load_hermes_field_map_proposal('job-1')

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
        current_gateway_mock.return_value = {'token':'a'*64,'changed':True,'cells':0,'objects':0,'reachable':1,'save_available':True}
        current_review_value, current_summary_value, current_group_value = hermes_agent_app.review_hermes_field_map_draft(current_draft_text,'field_request_123')
        self.assertTrue(current_group_value['visible'])
        with self.assertRaises(gr.Error):
            hermes_agent_app.save_hermes_field_map_draft(current_review_value,current_draft_text.replace('moss-clearing','grove'),'field_request_123')
        self.assertEqual(current_gateway_mock.call_count,1)
        current_gateway_mock.return_value = {'state':'completed','saved':True,'request_id':'field_request_123','map':'moss-clearing'}
        self.assertIn('저장 완료',hermes_agent_app.save_hermes_field_map_draft(current_review_value,current_draft_text,'field_request_123')[2])
        for current_wrong in ({'request_id':'other'}, {'map':'grove'}, {'saved':'true'}, {'state':'unknown'}):
            current_gateway_mock.return_value={'state':'completed','saved':True,'request_id':'field_request_123','map':'moss-clearing',**current_wrong}
            current_result_value=hermes_agent_app.save_hermes_field_map_draft(current_review_value,current_draft_text,'field_request_123')
            self.assertIn('자동 재접수하지 마세요',current_result_value[2])
            self.assertFalse(current_result_value[1]['visible'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_content_database_summary_distinguishes_pending_and_unavailable(self, current_gateway_mock):
        current_gateway_mock.return_value = {'status':'available','generation':9,'ledger_generation':7,'pending':True,'latest':{'state':'failed','lease_expired':True},'queried_at':'now'}
        current_summary_value = hermes_agent_app.read_hermes_content_database_summary()
        self.assertIn('반영 대기: 예', current_summary_value)
        self.assertIn('임대 만료', current_summary_value)
        current_gateway_mock.return_value = {'status':'unavailable','failure_reason':'service_origin'}
        self.assertIn('콘텐츠 서비스 주소 설정',hermes_agent_app.read_hermes_content_database_summary())
        current_gateway_mock.return_value = {'status':'unavailable'}
        self.assertIn('확인 불가', hermes_agent_app.read_hermes_content_database_summary())

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_content_summary_labels_local_mode_without_assuming_backend(self,current_gateway_mock):
        for current_mode_value,current_expected_text in (('database','DB 설정'),('files','파일 설정'),('unexpected','확인 불가')):
            with self.subTest(mode=current_mode_value):
                current_gateway_mock.return_value={'status':'unavailable','local_map_mode':current_mode_value}
                current_summary_value=hermes_agent_app.read_hermes_content_database_summary()
                self.assertIn('이 Hermes 서비스의 맵 모드: '+current_expected_text,current_summary_value)
                self.assertIn('백엔드의 실제 모드는 별도 확인',current_summary_value)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_content_summary_requires_consistent_map_counts(self,current_gateway_mock):
        for current_map_record in ({'status':'matched'}, {'status':'matched','checked_files':2,'mismatched_files':1}, {'status':'matched','checked_files':True,'mismatched_files':0}, {'status':'mismatch','checked_files':2,'mismatched_files':0}):
            with self.subTest(current_map_record=current_map_record):
                current_gateway_mock.return_value={'status':'unavailable','map_sources':current_map_record}
                current_summary_value=hermes_agent_app.read_hermes_content_database_summary()
                self.assertIn('원본·등록부·백엔드 잠금 확인 불가',current_summary_value)
                self.assertIn('콘텐츠 DB 상태 확인 불가',current_summary_value)
        current_gateway_mock.return_value={'status':'unavailable','map_sources':{'status':'matched','checked_files':2,'mismatched_files':0}}
        current_summary_value=hermes_agent_app.read_hermes_content_database_summary()
        self.assertIn('원본·등록부·백엔드 잠금 일치',current_summary_value)
        self.assertIn('DB 일치·실행 중 백엔드 반영은 별도 확인',current_summary_value)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_model_readiness_distinguishes_service_and_artifact_status(self, current_gateway_mock):
        current_gateway_mock.return_value={'service':'music-heartmula','status':'available','ready':False,'artifacts_ready':True,'generation_ready':None,'preparation_status':'unknown','prepare_allowed':True,'queried_at':'now'}
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

    def test_model_preparation_receipt_requires_matching_identity(self):
        current_valid={'state':'accepted','request_id':'request_123','service':'flux-image','message':'접수 기록'}
        with patch.object(hermes_agent_app,'execute_remote_management_command') as current_gateway_mock:
            for current_changes in ({'request_id':'other'},{'request_id':None},{'service':'kimodo'},{'service':None},{'state':'other'}):
                current_gateway_mock.return_value={**current_valid,**current_changes}
                self.assertIn('확인할 수 없습니다',hermes_agent_app.read_hermes_model_preparation_receipt('flux-image','request_123'))
            current_gateway_mock.return_value=current_valid
            self.assertEqual(hermes_agent_app.read_hermes_model_preparation_receipt('flux-image','request_123'),'접수 기록')
            current_gateway_mock.return_value={'state':'not_found','request_id':'request_123','service':'flux-image'}
            self.assertIn('접수 기록이 없습니다',hermes_agent_app.read_hermes_model_preparation_receipt('flux-image','request_123'))
            current_gateway_mock.return_value={'state':'accepted','request_id':'other','service':'flux-image'}
            current_review={'service':'flux-image','request_id':'request_123'}
            self.assertIn('접수 결과를 확인할 수 없습니다',hermes_agent_app.submit_hermes_model_preparation(current_review,'flux-image','request_123')[2])

    def test_failed_model_review_clears_confirmation_state(self):
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value={'service':'wrong','status':'available','ready':True,'prepare_allowed':True,'preparation_status':'idle'}) as current_gateway_mock:
            current_state,current_summary,current_group,current_notice=hermes_agent_app.safely_review_hermes_model_preparation('flux-image','request_123')
        self.assertIsNone(current_state)
        self.assertEqual(current_summary,'')
        self.assertFalse(current_group['visible'])
        self.assertIn('준비 요청은 실행하지 않았습니다',current_notice)
        self.assertTrue(all(item.args[1]!='hermes-model-prepare' for item in current_gateway_mock.call_args_list))

    def test_model_preparation_rejects_wrong_service_and_invalid_state(self):
        current_valid_record={'service':'flux-image','status':'available','ready':False,'preparation_status':'idle','prepare_allowed':True,'queried_at':'now'}
        for current_changes in ({'service':'kimodo'},{'service':None},{'ready':'yes'},{'prepare_allowed':'yes'},{'preparation_status':'unexpected'}):
            with self.subTest(changes=current_changes),patch.object(hermes_agent_app,'execute_remote_management_command',return_value={**current_valid_record,**current_changes}) as current_gateway_mock:
                with self.assertRaises(gr.Error):hermes_agent_app.review_hermes_model_preparation('flux-image','request_123')
                self.assertEqual(current_gateway_mock.call_args.args[1],'hermes-model-readiness')
                self.assertFalse(any(item.args[1]=='hermes-model-prepare' for item in current_gateway_mock.call_args_list))
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value={**current_valid_record,'service':'kimodo'}):
            self.assertIn('조회 실패',hermes_agent_app.read_hermes_model_readiness_summary('flux-image'))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_model_preparation_history_restores_service_and_identifier(self, current_gateway_mock):
        current_gateway_mock.return_value = {'records':[{'request_id':'request_123','service':'flux-image','state':'unknown'}]}
        current_choices_value, current_message_value = hermes_agent_app.list_hermes_model_preparation_choices()
        self.assertEqual(current_choices_value['choices'][0][1], 'flux-image:request_123')
        self.assertEqual(hermes_agent_app.select_hermes_model_preparation_receipt('flux-image:request_123'), ('flux-image','request_123'))
        current_gateway_mock.assert_called_once_with('hermes-agent','hermes-model-prepare-history',{})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_model_preparation_requires_review_and_unchanged_target(self, current_gateway_mock):
        current_gateway_mock.return_value = {'service':'flux-image', 'status':'available', 'ready':False, 'preparation_status':'idle', 'prepare_allowed':True}
        current_review_value, current_summary_value, current_group_value = hermes_agent_app.review_hermes_model_preparation('flux-image', 'request_123')
        self.assertTrue(current_group_value['visible'])
        self.assertIn('다운로드', current_summary_value)
        with self.assertRaises(gr.Error):
            hermes_agent_app.submit_hermes_model_preparation(current_review_value, 'kimodo', 'request_123')
        self.assertEqual(current_gateway_mock.call_count, 1)
        current_gateway_mock.return_value = {'state':'accepted','request_id':'request_123','service':'flux-image'}
        current_result_value = hermes_agent_app.submit_hermes_model_preparation(current_review_value, 'flux-image', 'request_123')
        self.assertIn('완료 여부', current_result_value[2])
        current_gateway_mock.assert_called_with('hermes-agent','hermes-model-prepare',current_review_value)
        current_gateway_mock.return_value={'state':'accepted','request_id':'request_123','service':'flux-image','preparation_status':'failed'}
        self.assertIn('접수 응답 당시 상태: 실패',hermes_agent_app.submit_hermes_model_preparation(current_review_value,'flux-image','request_123')[2])
        for current_uncertain_value in (OSError('lost'),None,{'state':'accepted','service':'kimodo'},{'state':'accepted','job_id':'bad'}):
            current_gateway_mock.side_effect=current_uncertain_value if isinstance(current_uncertain_value,Exception) else None
            current_gateway_mock.return_value=current_uncertain_value
            current_state,current_group,current_message=hermes_agent_app.submit_hermes_model_preparation(current_review_value,'flux-image','request_123')
            self.assertIsNone(current_state)
            self.assertFalse(current_group['visible'])
            self.assertIn('접수 결과를 확인할 수 없습니다',current_message)
            self.assertIn('같은 접수 ID',current_message)
        current_gateway_mock.side_effect=None
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
        current_gateway_mock.return_value={'receipt':{'state':'accepted','service':'flux-building','job_id':'2026-11-18_00-00-00-12345678'},'job':{'status':'completed','result_status':'unavailable','audio':None,'image':None}}
        current_gateway_mock.return_value['receipt']['service']='music-heartmula'
        self.assertIn('음원 링크 확인 불가',hermes_agent_app.read_hermes_audio_result('request_123','music-heartmula')[1])
        current_gateway_mock.return_value['receipt']['service']='flux-building'
        self.assertIn('이미지 링크 확인 불가',hermes_agent_app.read_hermes_flux_profile_result('request_123','flux-building')[1])
        current_gateway_mock.return_value['receipt']['service']='music-heartmula'
        current_gateway_mock.return_value['job']['result_status']='not_ready'
        current_gateway_mock.return_value['job']['status']='running'
        self.assertNotIn('링크 확인 불가',hermes_agent_app.read_hermes_audio_result('request_123','music-heartmula')[1])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_video_result_distinguishes_completed_from_unavailable_files(self,current_gateway_mock):
        current_gateway_mock.return_value={'receipt':{'state':'accepted','service':'wan22-vace','job_id':'2026-11-18_00-00-00-12345678'},'job':{'status':'completed','result_status':'unavailable'}}
        self.assertIn('결과 파일 확인 불가',hermes_agent_app.read_hermes_video_result('request_123','wan22-vace')[1])
        current_gateway_mock.return_value['job']['result_status']='partial'
        current_gateway_mock.return_value['job']['video']='/wan22-vace/jobs/2026-11-18_00-00-00-12345678/attempts/'+('a'*32)+'/preview.mp4'
        self.assertIn('결과 일부만 확인됨',hermes_agent_app.read_hermes_video_result('request_123','wan22-vace')[1])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_flux_profile_result_links_only_matching_completed_image(self,current_gateway_mock):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_image_path='/flux-building-generator/jobs/'+current_job_identifier+'/result.png'
        current_gateway_mock.return_value={'receipt':{'state':'accepted','service':'flux-building','job_id':current_job_identifier},'job':{'status':'completed','image':current_image_path}}
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
    def test_kimodo_result_rejects_invalid_job_identifier(self,current_gateway_mock):
        current_gateway_mock.return_value={'receipt':{'state':'accepted','request_id':'request_123','service':'kimodo','job_id':'../invalid'},'job':{'status':'completed'}}
        current_card_record={'session_id':'session','source_job_id':'source','review':{'request_id':'request_123'}}
        with self.assertRaises(gr.Error):hermes_agent_app.read_conversation_kimodo_result(current_card_record,'session','source')

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_general_flux_result_link_requires_matching_completed_job(self,current_gateway_mock):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_image_path='/flux-image-generator/jobs/'+current_job_identifier+'/result.png'
        current_gateway_mock.return_value={'receipt':{'state':'accepted','request_id':'request_123','service':'flux-image','job_id':current_job_identifier},'job':{'status':'completed'},'result':{'status':'available','image':current_image_path}}
        self.assertIn('[생성 이미지 보기]('+current_image_path+')',hermes_agent_app.read_hermes_flux_receipt('request_123')[1])
        self.assertIn('파일 존재와 재생',hermes_agent_app.read_hermes_flux_receipt('request_123')[1])
        current_gateway_mock.return_value['result']={'status':'unavailable','image':None}
        self.assertIn('이미지 링크 확인 불가',hermes_agent_app.read_hermes_flux_receipt('request_123')[1])
        self.assertNotIn('경로 형식만 확인',hermes_agent_app.read_hermes_flux_receipt('request_123')[1])
        current_gateway_mock.return_value['result']={'status':'available','image':'https://example.com/result.png'}
        self.assertNotIn('생성 이미지 보기',hermes_agent_app.read_hermes_flux_receipt('request_123')[1])
        current_gateway_mock.return_value['receipt']['request_id']='different'
        with self.assertRaises(gr.Error):hermes_agent_app.read_hermes_flux_receipt('request_123')
        current_gateway_mock.return_value['receipt']['request_id']='request_123'
        current_gateway_mock.return_value['receipt']['service']='flux-building'
        with self.assertRaises(gr.Error):hermes_agent_app.read_hermes_flux_receipt('request_123')
        current_gateway_mock.return_value['receipt'].update(service='flux-image',job_id='../invalid')
        with self.assertRaises(gr.Error):hermes_agent_app.read_hermes_flux_receipt('request_123')

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
        current_gateway_mock.return_value = {'job_id':'job-1','proposal':{'prompt':'blue sky','width':512,'height':512,'seed':42}}
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
        current_gateway_mock.return_value={'state':'completed','request_id':'other','job_id':current_job_identifier}
        self.assertIn('결과 확인 필요',hermes_agent_app.submit_hermes_writer_reservation_recovery(current_review_value,'recovery_123',current_job_identifier,True)[2])
        current_gateway_mock.return_value={'state':'completed','request_id':'recovery_123','job_id':current_job_identifier}
        self.assertIn('예약을 해제',hermes_agent_app.submit_hermes_writer_reservation_recovery(current_review_value,'recovery_123',current_job_identifier,True)[2])
        self.assertTrue(current_gateway_mock.call_args.args[2]['outside_processes_checked'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_writer_recovery_review_and_receipt_require_matching_identity(self,current_gateway_mock):
        current_job_identifier='20261118-120000-12345678'
        for current_response_value in ({'job_id':'20261118-120000-ffffffff','recoverable':True,'preview_sha256':'a'*64,'reason':'test'},{'job_id':current_job_identifier,'recoverable':True,'preview_sha256':'bad','reason':'test'}):
            current_gateway_mock.return_value=current_response_value
            with self.assertRaises(gr.Error):hermes_agent_app.review_hermes_writer_reservation_recovery(current_job_identifier,'recovery_123')
        for current_response_value in ({'request_id':'other','job_id':current_job_identifier,'state':'completed'},{'request_id':'recovery_123','job_id':'../invalid','state':'completed'}):
            current_gateway_mock.return_value=current_response_value
            self.assertIn('확인 필요',hermes_agent_app.read_hermes_writer_reservation_recovery_receipt('recovery_123'))
        current_gateway_mock.return_value={'request_id':'recovery_123','job_id':current_job_identifier,'state':'completed'}
        self.assertIn('기록됐습니다',hermes_agent_app.read_hermes_writer_reservation_recovery_receipt('recovery_123'))

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_cancel_review_rejects_other_service_or_unaccepted_receipt(self,current_gateway_mock):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_cases=((hermes_agent_app.review_hermes_translation_cancellation,('request_123',current_job_identifier),'prompt-translation'),(hermes_agent_app.review_hermes_video_cancellation,('request_123','wan22-vace',current_job_identifier),'wan22-vace'),(hermes_agent_app.review_hermes_audio_cancellation,('request_123','music-heartmula',current_job_identifier),'music-heartmula'),(hermes_agent_app.review_hermes_flux_profile_cancellation,('request_123','flux-prop',current_job_identifier),'flux-prop'),(hermes_agent_app.review_hermes_flux_cancellation,('request_123',current_job_identifier),'flux-image'))
        for current_function_value,current_arguments,current_service_name in current_cases:
            for current_receipt_value in ({'state':'accepted','service':'other','job_id':current_job_identifier},{'state':'unknown','service':current_service_name,'job_id':current_job_identifier}):
                with self.subTest(function=current_function_value.__name__,receipt=current_receipt_value):
                    current_gateway_mock.return_value={'receipt':current_receipt_value}
                    with self.assertRaises(gr.Error):current_function_value(*current_arguments)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_cancel_review_requires_matching_request_identifier(self,current_gateway_mock):
        current_job_identifier='2026-11-18_00-00-00-12345678'
        current_cases=((hermes_agent_app.review_hermes_translation_cancellation,('request_123',current_job_identifier),'prompt-translation'),(hermes_agent_app.review_hermes_video_cancellation,('request_123','wan22-vace',current_job_identifier),'wan22-vace'),(hermes_agent_app.review_hermes_audio_cancellation,('request_123','music-heartmula',current_job_identifier),'music-heartmula'),(hermes_agent_app.review_hermes_flux_profile_cancellation,('request_123','flux-prop',current_job_identifier),'flux-prop'),(hermes_agent_app.review_hermes_flux_cancellation,('request_123',current_job_identifier),'flux-image'))
        for current_function,current_arguments,current_service in current_cases:
            with self.subTest(service=current_service):
                current_gateway_mock.return_value={'receipt':{'state':'accepted','request_id':'other_request','service':current_service,'job_id':current_job_identifier},'job':{'stage':'reasoning'}}
                with self.assertRaises(gr.Error):current_function(*current_arguments)
                current_gateway_mock.return_value['receipt']['request_id']='request_123'
                self.assertTrue(current_function(*current_arguments)[1]['visible'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_writer_cancel_confirmation_checks_identity_and_status(self,current_gateway_mock):
        current_job_identifier='20261118-120000-12345678'
        current_gateway_mock.return_value={'receipt':{'state':'accepted','request_id':'request_123','service':'writer-agent','job_id':current_job_identifier},'job':{'stage':'reasoning'}}
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
        current_gateway_mock.return_value={'state':'completed','saved':True,'request_id':current_request_identifier}
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
        current_gateway_mock.return_value = {'job_id':'2026-11-18_00-00-00-12345678','proposal': {'prompt':'walk', 'frames':90, 'steps':100, 'seed':42}}
        current_input_values = hermes_agent_app.load_hermes_kimodo_proposal('2026-11-18_00-00-00-12345678')
        self.assertEqual(current_input_values[:4], ('walk', 90, 100, 42))
        self.assertIsNone(current_input_values[5])
        self.assertFalse(current_input_values[8]['interactive'])
        current_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-kimodo-proposal', {'id':'2026-11-18_00-00-00-12345678'})

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_kimodo_proposal_rejects_other_job(self,current_gateway_mock):
        current_gateway_mock.return_value={'job_id':'other-job','proposal':{'prompt':'walk','frames':90,'steps':100,'seed':42}}
        with self.assertRaises(gr.Error):hermes_agent_app.load_hermes_kimodo_proposal('selected-job')
        current_gateway_mock.assert_called_once()

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_generation_proposals_reject_other_job_before_review(self,current_gateway_mock):
        current_gateway_mock.return_value={'job_id':'other-job','proposal':{}}
        current_loaders=(hermes_agent_app.load_hermes_flux_proposal,hermes_agent_app.load_hermes_video_proposal,hermes_agent_app.load_hermes_audio_proposal,hermes_agent_app.load_hermes_translation_proposal)
        for current_loader_function in current_loaders:
            with self.subTest(loader=current_loader_function.__name__):
                current_gateway_mock.reset_mock()
                with self.assertRaises(gr.Error):current_loader_function('selected-job')
                current_gateway_mock.assert_called_once()

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_receipt_lookup_does_not_resubmit(self, current_gateway_mock):
        current_gateway_mock.return_value = {'state':'accepted', 'request_id':'request_123456', 'service':'kimodo', 'job_id':'2026-11-18_00-00-00-12345678'}
        self.assertEqual(hermes_agent_app.read_hermes_delegation_receipt('request_123456')[0], '2026-11-18_00-00-00-12345678')
        current_gateway_mock.assert_called_once_with('hermes-agent', 'hermes-delegation-status', {'request_id':'request_123456'})
        current_gateway_mock.return_value['request_id']='other_request'
        with self.assertRaises(gr.Error):hermes_agent_app.read_hermes_delegation_receipt('request_123456')
        current_gateway_mock.return_value = {'state':'unknown','request_id':'request_123456','service':'kimodo'}
        self.assertIn('확인 필요', hermes_agent_app.read_hermes_delegation_receipt('request_123456')[1])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_cancel_review_pins_receipt_before_request(self, current_gateway_mock):
        current_job_id = '2026-11-18_00-00-00-12345678'
        current_gateway_mock.return_value = {'state':'accepted', 'request_id':'request_123456','service':'kimodo', 'job_id':current_job_id}
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
        current_gateway_mock.side_effect = [{'records':[{'request_id':'request_123456', 'state':'accepted', 'job_id':'2026-11-18_00-00-00-12345678'}], 'truncated':False}, {'state':'accepted','request_id':'request_123456','service':'kimodo','job_id':'2026-11-18_00-00-00-12345678'}]
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

    def test_management_summary_does_not_treat_incomplete_capacity_as_ready(self):
        current_snapshot_value={'model':{'status':'unavailable'},'gpu':{'status':'idle'},'queue':{'status':'available','jobs':[]},'queried_at':'now','memory_capacity':{'status':'available','domain':'vram','pool_available_mib':40000,'required_mib':32000,'host_available_mib':50000,'capacity_sufficient':True}}
        with patch.object(hermes_agent_app,'execute_remote_management_command',return_value=current_snapshot_value):
            current_summary_text=hermes_agent_app.read_hermes_management_summary()
            self.assertIn('관측치상 메모리 기준 충족',current_summary_text)
            self.assertIn('실제 실행 가능 여부 별도',current_summary_text)
            self.assertIn('다른 예약·순서 제외',current_summary_text)
            current_snapshot_value['memory_capacity']['capacity_sufficient']='false'
            current_summary_text=hermes_agent_app.read_hermes_management_summary()
            self.assertIn('메모리: 조회 불가',current_summary_text)
            self.assertNotIn('관측치상 메모리 기준 충족',current_summary_text)

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
        current_gateway_mock.return_value={'request_id':'register_request_1','state':'completed','id':'fog-v1','generation':4}
        _,current_hidden_value,current_status_value=hermes_agent_app.save_hermes_effect_registration_draft(current_review_value,current_draft_text,'register_request_1')
        self.assertFalse(current_hidden_value['visible'])
        self.assertIn('세대 4',current_status_value)
        current_gateway_mock.assert_called_with('hermes-agent','hermes-effect-register',current_review_value)
        current_gateway_mock.return_value={'request_id':'other','state':'completed','id':'fog-v1','generation':4}
        current_state,current_hidden,current_status=hermes_agent_app.save_hermes_effect_registration_draft(current_review_value,current_draft_text,'register_request_1')
        self.assertIsNone(current_state)
        self.assertFalse(current_hidden['visible'])
        self.assertIn('확인 필요',current_status)
        current_gateway_mock.side_effect=OSError('response lost')
        current_state,current_hidden,current_status=hermes_agent_app.save_hermes_effect_registration_draft(current_review_value,current_draft_text,'register_request_1')
        self.assertIsNone(current_state)
        self.assertFalse(current_hidden['visible'])
        self.assertIn('확인 필요',current_status)

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
        current_gateway_mock.return_value={'request_id':'waypoint_request_1','state':'completed','id':'waypoint-v2'}
        _,current_hidden_value,current_status_value=hermes_agent_app.save_hermes_waypoint_replacement_draft(current_review_value,current_draft_text,'waypoint_request_1','waypoint-v1')
        self.assertFalse(current_hidden_value['visible'])
        self.assertIn('DB 교체 완료',current_status_value)
        current_gateway_mock.assert_called_with('hermes-agent','hermes-waypoint-replace',current_review_value)
        current_gateway_mock.return_value={'request_id':'other','state':'completed','id':'waypoint-v2'}
        current_state,current_hidden,current_status=hermes_agent_app.save_hermes_waypoint_replacement_draft(current_review_value,current_draft_text,'waypoint_request_1','waypoint-v1')
        self.assertIsNone(current_state)
        self.assertFalse(current_hidden['visible'])
        self.assertIn('확인 필요',current_status)
        current_gateway_mock.side_effect=OSError('response lost')
        current_state,current_hidden,current_status=hermes_agent_app.save_hermes_waypoint_replacement_draft(current_review_value,current_draft_text,'waypoint_request_1','waypoint-v1')
        self.assertIsNone(current_state)
        self.assertFalse(current_hidden['visible'])
        self.assertIn('확인 필요',current_status)

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_source_history_accepts_canonical_owner_and_audio_service(self,current_gateway_mock):
        current_base_record={'records':[{'id':'job-1','recorded_status':'queued','status_source':'job'}],'total':1,'offset':0,'next_offset':None,'snapshot':'a'*64,'unavailable_count':0}
        for current_service_name,current_command_name,current_source_service in (('building-generator','hermes-generator-source-history','billboard-generator'),('music-heartmula','hermes-audio-source-history','music-heartmula')):
            with self.subTest(service=current_service_name):
                current_gateway_mock.return_value={**current_base_record,'service':current_service_name,'source_service':current_source_service}
                current_rows_value,current_notice_text,current_page_state,_=hermes_agent_app.read_hermes_source_history_page(current_service_name,current_command_name)
                self.assertEqual(current_rows_value[0][0],'job-1')
                self.assertEqual(current_page_state['service'],current_service_name)
                if current_service_name=='building-generator':self.assertIn('billboard-generator',current_notice_text)
                current_gateway_mock.return_value['source_service']='unexpected'
                self.assertEqual(hermes_agent_app.read_hermes_source_history_page(current_service_name,current_command_name)[0],[])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_source_history_pages_keep_service_and_snapshot(self,current_gateway_mock):
        current_gateway_mock.return_value={'service':'flux-image','records':[{'id':f'2026-11-18_00-00-{current_index:02d}-12345678','recorded_status':'running','status_source':'job'} for current_index in range(30)],'total':31,'offset':0,'next_offset':30,'snapshot':'a'*64,'unavailable_count':2}
        current_rows_value,current_status_value,current_page_state,current_next_update=hermes_agent_app.read_hermes_generator_source_rows('flux-image')
        self.assertEqual(current_rows_value[0][1],'running')
        self.assertTrue(current_next_update['interactive'])
        self.assertIn('1–30',current_status_value)
        self.assertIn('확인 불가 이력 2건',current_status_value)
        current_gateway_mock.return_value={'service':'flux-image','records':[{'id':'2026-11-18_00-00-30-12345678','recorded_status':'completed','status_source':'job'}],'total':31,'offset':30,'next_offset':None,'snapshot':'a'*64,'unavailable_count':0}
        _,current_status_value,_,current_next_update=hermes_agent_app.read_next_hermes_generator_source_rows('flux-image',current_page_state)
        current_gateway_mock.assert_called_with('hermes-agent','hermes-generator-source-history',{'service':'flux-image','limit':30,'offset':30,'snapshot':'a'*64})
        self.assertIn('31–31',current_status_value)
        self.assertFalse(current_next_update['interactive'])
        for current_changed_fields in ({'service':'kimodo'},{'snapshot':'b'*64},{'offset':29},{'source_service':'kimodo'}):
            current_original_record=current_gateway_mock.return_value.copy()
            current_gateway_mock.return_value.update(current_changed_fields)
            current_rows_value,current_error_value,current_cleared_state,current_next_update=hermes_agent_app.read_next_hermes_generator_source_rows('flux-image',current_page_state)
            self.assertEqual(current_rows_value,[])
            self.assertIsNone(current_cleared_state)
            self.assertFalse(current_next_update['interactive'])
            current_gateway_mock.return_value=current_original_record
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
        current_gateway_mock.return_value = {'id':'a'*32, 'message_count':1, 'queried_at':'now', 'messages':[{'text':'질문','job_id':'job-1','job':{'status':{'status':'completed'},'final_response':'최종 답변','tool_activity':{'events':[{'type':'tool_use','name':'terminal','target':'상태 조회','timestamp':'now'},{'type':'tool_result','name':'terminal','result':'success'}],'truncated':False}}}]}
        current_conversation_values = hermes_agent_app.read_hermes_session_conversation('a' * 32)[0]
        self.assertIn('호출 terminal · 상태 조회', current_conversation_values[1]['content'])
        self.assertIn('결과 terminal · 성공', current_conversation_values[1]['content'])
        self.assertIn('최종 답변', current_conversation_values[2]['content'])

    @patch('tools.review.ui.gradio.hermes_agent_app.execute_remote_management_command')
    def test_session_conversation_reads_existing_job_and_reports_truncation(self, hermes_gateway_mock):
        hermes_gateway_mock.return_value = {'id':'a'*32, 'message_count': 1, 'queried_at':'2026-11-17T14:00:00+00:00', 'messages': [{'text': '첫 질문', 'job_id': 'job-1', 'context_truncated': True, 'job': {'status': {'status':'completed'}, 'final_response':'첫 답변', 'final_response_truncated':False}}]}
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


class OperationsSourceDeepLinkTests(unittest.TestCase):
    def test_gradio_selection_injects_event_before_session(self):
        import gradio as gr
        from gradio.helpers import special_args
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_event_value=gr.EventData(None,{'index':[0,0],'value':'job-12'})
        current_page_value={'service':'prompt-translation','snapshot':'b'*64}
        current_source_rows=[['job-12','완료','작업 상태 파일','조회 불가','조회 불가']]
        current_inputs,_,current_event_index,_=special_args(operations_history_app.select_operations_source_job,['prompt-translation',current_page_value,current_source_rows,current_session_identifier],event_data=current_event_value)
        self.assertEqual(current_event_index,3)
        self.assertIn('session='+current_session_identifier,operations_history_app.select_operations_source_job(*current_inputs)[1])
        current_receipt_rows=[['request','prompt-translation','', '접수 기록','job-12','','','']]
        current_inputs,_,current_event_index,_=special_args(operations_history_app.select_operations_receipt_service,[current_receipt_rows,current_session_identifier],event_data=current_event_value)
        self.assertEqual(current_event_index,1)
        self.assertIn('session='+current_session_identifier,operations_history_app.select_operations_receipt_service(*current_inputs))

    def test_operations_session_change_updates_return_link(self):
        import subprocess
        from tools.review.ui.gradio import operations_history_app
        current_interface_value=build_async_test_interface(operations_history_app.build_operations_history_interface)
        current_scripts=[str(current_dependency.get('js','')) for current_dependency in current_interface_value.get_config_file()['dependencies']]
        current_script_text=next(current_script for current_script in current_scripts if "management-return-conversation a" in current_script and 'sessionId' in current_script)
        current_runner_text="""
const vm=require('vm'), fn=process.argv[1], a='a'.repeat(32); let href='';
const ctx={document:{querySelector:()=>({setAttribute:(_,v)=>{href=v;}})}};
const apply=vm.runInNewContext('('+fn+')',ctx);
apply(a); if(href!='/management/frame/hermes-agent/?session='+a)throw Error(href);
apply('bad'); if(href!='/management/frame/hermes-agent/')throw Error(href);
"""
        current_result_value=subprocess.run(['node','-e',current_runner_text,current_script_text],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_result_value.returncode,0,current_result_value.stderr)

    def test_session_change_clears_source_link(self):
        from tools.review.ui.gradio import operations_history_app
        current_interface_value=build_async_test_interface(operations_history_app.build_operations_history_interface)
        current_config_value=current_interface_value.get_config_file()
        current_source_bindings=[current_binding for current_binding in current_interface_value.fns.values() if getattr(current_binding.fn,'__name__','')=='select_operations_source_job']
        self.assertEqual(len(current_source_bindings),1)
        current_source_link=current_source_bindings[0].outputs[1]
        current_session_control=current_source_bindings[0].inputs[-1]
        current_clear_bindings=[current_binding for current_binding in current_interface_value.fns.values() if current_binding.inputs==[] and current_binding.outputs==[current_source_link] and current_binding.fn and current_binding.fn()=='']
        self.assertTrue(current_clear_bindings)
        current_clear_identifiers={current_binding._id for current_binding in current_clear_bindings}
        self.assertTrue(any(current_dependency['id'] in current_clear_identifiers and any(tuple(current_target)==(current_session_control._id,'change') for current_target in current_dependency.get('targets',[])) for current_dependency in current_config_value['dependencies']))

    def test_operations_source_link_preserves_selected_session(self):
        from tools.review.ui.gradio import operations_history_app
        current_session_identifier='a'*32
        current_link_text=operations_history_app.render_operations_source_link('prompt-translation','job-12',current_session_identifier)
        self.assertIn('?job=job-12&amp;session='+current_session_identifier,current_link_text)
        self.assertNotIn('session=',operations_history_app.render_operations_source_link('prompt-translation','job-12','../bad'))

    def test_supported_links_only_include_valid_identifiers(self):
        from tools.review.ui.gradio import operations_history_app
        for current_service in ('kimodo','dwpose','flux-image','flux-building','music-heartmula','sfx-dasheng-audiogen'):
            self.assertIn('?job=job-12',operations_history_app.render_operations_source_link(current_service,'job-12'))
        self.assertIn('?job=job-12',operations_history_app.render_operations_source_link('flux-expression','job-12'))
        self.assertIn('?job=job-12',operations_history_app.render_operations_source_link('prompt-translation','job-12'))
        self.assertNotIn('?job=',operations_history_app.render_operations_source_link('kimodo','../bad'))
