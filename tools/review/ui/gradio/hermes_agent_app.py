"""공용 게이트웨이를 사용하는 격리 Hermes 코딩 작업 화면."""
import base64
import binascii
import uuid

import gradio as gr
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_generator_changelog import build_generator_changelog
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES, SOURCE_HISTORY_AUDIO_SERVICES


def match_hermes_confirmation_inputs(confirmed_input_values, current_input_values):
    """확인창을 연 뒤 지시나 대상을 바꾸면 새 확인이 필요하다."""
    return confirmed_input_values == current_input_values


def submit_hermes_work_request(hermes_prompt_text, hermes_request_identifier, hermes_verification_text=''):
    try:
        hermes_request_record = {'prompt':hermes_prompt_text, 'request_id':hermes_request_identifier}
        hermes_verification_modules = [hermes_module_name.strip() for hermes_module_name in (hermes_verification_text or '').splitlines() if hermes_module_name.strip()]
        if hermes_verification_modules:
            hermes_request_record['verification_modules'] = hermes_verification_modules
        hermes_response_record = execute_remote_management_command('hermes-agent', 'hermes-submit', hermes_request_record)
        return hermes_response_record['id'], '기존 접수 확인' if hermes_response_record.get('duplicate') else 'GPU 대기열에 등록했습니다.'
    except Exception as hermes_request_error:
        raise gr.Error('접수 확인 실패: ' + str(hermes_request_error) + ' · 같은 접수 식별자로 다시 확인하세요.') from hermes_request_error


def refresh_hermes_work_status(hermes_job_identifier):
    try:
        hermes_job_record = execute_remote_management_command('hermes-agent', 'hermes-detail', {'id':hermes_job_identifier})
        hermes_status_record = hermes_job_record['status']
        hermes_status_text = hermes_status_record.get('status', 'unknown')
        if hermes_status_record.get('queue_position'):
            hermes_status_text += ' · 대기 순서 ' + str(hermes_status_record['queue_position'])
        if hermes_status_record.get('error'):
            hermes_status_text += ' · ' + str(hermes_status_record['error'])
        if hermes_status_record.get('message'):
            hermes_status_text += ' · ' + str(hermes_status_record['message'])
        if hermes_job_record['diff_truncated']:
            hermes_status_text += ' · diff 일부만 표시'
        hermes_result_record = hermes_job_record.get('result')
        hermes_verification_record = hermes_result_record.get('verification') if isinstance(hermes_result_record, dict) else None
        if isinstance(hermes_verification_record, dict):
            hermes_verification_status = hermes_verification_record.get('status', 'unknown')
            hermes_status_text += ' · 독립 검증 ' + {'passed':'통과', 'failed':'실패', 'not_requested':'미요청', 'not_run':'미실행'}.get(hermes_verification_status, '확인 불가')
        hermes_answer_text = hermes_job_record.get('final_response')
        if not isinstance(hermes_answer_text, str) or not hermes_answer_text:
            hermes_answer_text = '최종 응답이 아직 없거나 기록에서 확인할 수 없습니다.'
        elif hermes_job_record.get('final_response_truncated'):
            hermes_answer_text += '\n\n[응답 일부만 표시]'
        hermes_request_record = hermes_job_record.get('request')
        hermes_original_prompt = hermes_request_record.get('prompt') if isinstance(hermes_request_record, dict) else None
        if not isinstance(hermes_original_prompt, str):
            hermes_original_prompt = '기록에서 작업 지시를 확인할 수 없습니다.'
        return hermes_status_text, hermes_answer_text, hermes_job_record['diff'], hermes_job_record['log'], hermes_result_record, hermes_original_prompt
    except Exception as hermes_request_error:
        raise gr.Error('조회 실패: ' + str(hermes_request_error)) from hermes_request_error


def read_hermes_diff_page(current_job_identifier, current_cursor_record=None):
    """완료된 작업의 diff를 바이트 경계에서 이어 읽는다."""
    if not isinstance(current_job_identifier, str) or not current_job_identifier:
        raise gr.Error('먼저 작업을 선택하세요.')
    if current_cursor_record is None:
        current_offset_value = 0
        current_expected_size = None
    elif not isinstance(current_cursor_record, dict) or current_cursor_record.get('job_id') != current_job_identifier:
        raise gr.Error('작업이 변경됐습니다. 처음 부분부터 다시 보세요.')
    else:
        current_offset_value = current_cursor_record.get('next_offset')
        current_expected_size = current_cursor_record.get('size_bytes')
        if current_offset_value is None:
            raise gr.Error('마지막 부분까지 표시했습니다.')
        if type(current_offset_value) is not int or current_offset_value < 0 or type(current_expected_size) is not int:
            raise gr.Error('diff 위치를 확인할 수 없습니다. 처음부터 다시 보세요.')
    try:
        current_chunk_record = execute_remote_management_command('hermes-agent', 'hermes-diff', {'id': current_job_identifier, 'offset': current_offset_value, 'limit': 65536})
        current_total_bytes = current_chunk_record['size_bytes']
        if current_chunk_record.get('id') != current_job_identifier or current_chunk_record.get('offset') != current_offset_value or type(current_total_bytes) is not int or current_total_bytes < current_offset_value or (current_expected_size is not None and current_total_bytes != current_expected_size):
            raise ValueError('diff 크기 또는 응답 위치가 변경됐습니다. 처음부터 다시 보세요.')
        current_chunk_bytes = base64.b64decode(current_chunk_record['data_base64'], validate=True)
        if len(current_chunk_bytes) > 65536 or current_offset_value + len(current_chunk_bytes) > current_total_bytes or (not current_chunk_bytes and current_offset_value < current_total_bytes):
            raise ValueError('diff 응답 크기 오류')
        current_expected_next = current_offset_value + len(current_chunk_bytes)
        if current_chunk_record.get('next_offset') != (current_expected_next if current_expected_next < current_total_bytes else None):
            raise ValueError('diff 응답 이어보기 위치 오류')
        current_decode_warning = ''
        try:
            current_page_text = current_chunk_bytes.decode('utf-8')
        except UnicodeDecodeError as current_decode_error:
            if current_decode_error.reason == 'unexpected end of data' and current_decode_error.start > 0 and current_expected_next < current_total_bytes:
                current_chunk_bytes = current_chunk_bytes[:current_decode_error.start]
                current_page_text = current_chunk_bytes.decode('utf-8')
            else:
                current_page_text = current_chunk_bytes.decode('utf-8', errors='backslashreplace')
                current_decode_warning = ' · UTF-8이 아닌 바이트는 이스케이프 표시; 원본 바이트는 MCP에서 확인'
        current_end_offset = current_offset_value + len(current_chunk_bytes)
        current_next_offset = current_end_offset if current_end_offset < current_total_bytes else None
        current_cursor_value = {'job_id': current_job_identifier, 'next_offset': current_next_offset, 'size_bytes': current_total_bytes}
        current_page_message = f'바이트 {current_offset_value}~{current_end_offset} / {current_total_bytes}' + (' · 마지막 부분' if current_next_offset is None else ' · 다음 부분이 있습니다') + current_decode_warning
        return current_page_text, current_page_message, current_cursor_value
    except (KeyError, ValueError, TypeError, binascii.Error) as current_diff_error:
        raise gr.Error('전체 diff 조회 실패: ' + str(current_diff_error)) from current_diff_error


def start_hermes_diff_pages(current_job_identifier):
    return read_hermes_diff_page(current_job_identifier)


def cancel_hermes_work_request(hermes_job_identifier):
    try:
        execute_remote_management_command('hermes-agent', 'hermes-cancel', {'id':hermes_job_identifier})
        return '중지를 요청했습니다. 실제 종료 여부는 상태를 새로고침해 확인하세요.'
    except Exception as hermes_request_error:
        raise gr.Error('중지 실패: ' + str(hermes_request_error)) from hermes_request_error


def refresh_hermes_work_history():
    try:
        hermes_history_record = execute_remote_management_command('hermes-agent', 'hermes-history', {})
        hermes_history_rows = [[hermes_job_record['id'], hermes_job_record['status'].get('status', 'unknown'), hermes_job_record['request']['prompt'][:120]] for hermes_job_record in hermes_history_record['records']]
        return hermes_history_rows, f'작업 이력 {len(hermes_history_rows)}개'
    except Exception as hermes_request_error:
        return [], '이력 조회 실패: ' + str(hermes_request_error) + ' · 관리 게이트웨이 실행 상태와 버전을 확인하세요.'


def select_hermes_history_record(hermes_history_rows, hermes_select_event: gr.SelectData):
    """선택한 행의 작업을 기존 상세 게이트웨이에서 다시 읽는다."""
    hermes_selected_index = hermes_select_event.index
    if isinstance(hermes_selected_index, (list, tuple)):
        hermes_selected_index = hermes_selected_index[0] if hermes_selected_index else None
    if type(hermes_selected_index) is not int or not isinstance(hermes_history_rows, list) or not 0 <= hermes_selected_index < len(hermes_history_rows):
        raise gr.Error('선택한 작업을 확인할 수 없습니다. 이력을 새로고침하세요.')
    hermes_selected_row = hermes_history_rows[hermes_selected_index]
    if not isinstance(hermes_selected_row, (list, tuple)) or not hermes_selected_row or not isinstance(hermes_selected_row[0], str):
        raise gr.Error('선택한 작업 ID를 확인할 수 없습니다. 이력을 새로고침하세요.')
    hermes_selected_identifier = hermes_selected_row[0]
    hermes_status_text, hermes_answer_text, hermes_diff_text, hermes_log_text, hermes_result_record, hermes_original_prompt = refresh_hermes_work_status(hermes_selected_identifier)
    return hermes_selected_identifier, hermes_status_text, hermes_answer_text, hermes_diff_text, hermes_log_text, hermes_result_record, hermes_original_prompt


def list_hermes_session_choices(hermes_selected_identifier=None):
    """저장된 세션의 선택 목록을 읽는다."""
    try:
        hermes_list_record = execute_remote_management_command('hermes-agent', 'hermes-session-list', {})
        hermes_session_records = hermes_list_record['sessions']
        hermes_session_choices = [(current_session_record['updated_at'] + ' · ' + current_session_record['id'][:8] + ' · ' + str(current_session_record['message_count']) + '개 메시지', current_session_record['id']) for current_session_record in hermes_session_records]
        hermes_valid_identifiers = {current_session_record['id'] for current_session_record in hermes_session_records}
        hermes_list_message = '세션 ' + str(len(hermes_session_choices)) + '개' + (' · 최근 100개만 표시' if hermes_list_record.get('truncated') else '')
        return gr.update(choices=hermes_session_choices, value=hermes_selected_identifier if hermes_selected_identifier in hermes_valid_identifiers else None), hermes_list_message
    except Exception as hermes_request_error:
        raise gr.Error('세션 목록 조회 실패: ' + str(hermes_request_error)) from hermes_request_error


def create_hermes_session_from_draft(hermes_draft_identifier):
    """응답 유실 시 같은 초안 ID로 세션 생성을 다시 확인한다."""
    try:
        hermes_session_record = execute_remote_management_command('hermes-agent', 'hermes-session-create', {'session_id': hermes_draft_identifier})
        hermes_choices_update, hermes_list_message = list_hermes_session_choices(hermes_session_record['id'])
        return hermes_choices_update, uuid.uuid4().hex, hermes_list_message
    except Exception as hermes_request_error:
        raise gr.Error('세션 생성 확인 실패: ' + str(hermes_request_error) + ' · 같은 요청으로 다시 확인하세요.') from hermes_request_error


def format_hermes_conversation_answer(current_answer_text, current_answer_truncated=False):
    """검증된 제안 마커를 사용자가 취할 수 있는 다음 단계로 표시한다."""
    if not isinstance(current_answer_text, str) or not current_answer_text:
        return '아직 확인된 최종 답변이 없습니다.'
    if current_answer_truncated:
        return current_answer_text
    from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_kimodo_proposal, HERMES_PROPOSAL_START, parse_hermes_flux_proposal, HERMES_FLUX_PROPOSAL_START, parse_hermes_field_proposal, HERMES_FIELD_PROPOSAL_START, parse_hermes_translation_proposal, HERMES_TRANSLATION_PROPOSAL_START, parse_hermes_audio_proposal, HERMES_AUDIO_PROPOSAL_START, parse_hermes_video_proposal, HERMES_VIDEO_PROPOSAL_START, parse_hermes_billboard_proposal, HERMES_BILLBOARD_PROPOSAL_START, parse_hermes_effect_proposal, HERMES_EFFECT_PROPOSAL_START, parse_hermes_sprite_proposal, HERMES_SPRITE_PROPOSAL_START
    for current_parser, current_marker, current_instruction_text in ((parse_hermes_sprite_proposal,HERMES_SPRITE_PROPOSAL_START,'스프라이트 앵커 제안이 있습니다. 세션 작업을 선택한 뒤 스프라이트 조회에서 제안을 불러와 검토하세요.'), (parse_hermes_effect_proposal,HERMES_EFFECT_PROPOSAL_START,'이펙트 좌표 제안이 있습니다. 세션 작업을 선택한 뒤 이펙트 조회에서 제안을 불러와 검토하세요.'), (parse_hermes_billboard_proposal,HERMES_BILLBOARD_PROPOSAL_START,'빌보드 속성 제안이 있습니다. 이 작업을 선택한 뒤 빌보드 편집에서 제안을 불러와 검토하세요.'), (parse_hermes_kimodo_proposal, HERMES_PROPOSAL_START, 'Kimodo 작업 제안이 있습니다. 이 작업을 선택한 뒤 Kimodo 작업 위임에서 제안을 불러와 검토하세요.'), (parse_hermes_flux_proposal, HERMES_FLUX_PROPOSAL_START, 'FLUX 작업 제안이 있습니다. 이 작업을 선택한 뒤 FLUX 이미지 작업 위임에서 제안을 불러와 검토하세요.'), (parse_hermes_field_proposal,HERMES_FIELD_PROPOSAL_START,'야외 맵 셀 제안이 있습니다. 이 작업을 선택한 뒤 야외 맵 초안에서 제안을 불러와 검토하세요.'), (parse_hermes_translation_proposal,HERMES_TRANSLATION_PROPOSAL_START,'번역 위임 제안이 있습니다. 이 작업을 선택한 뒤 번역 위임에서 제안을 불러와 검토하세요.'), (parse_hermes_audio_proposal,HERMES_AUDIO_PROPOSAL_START,'음악·효과음 제안이 있습니다. 이 작업을 선택한 뒤 오디오 위임에서 제안을 불러와 검토하세요.'), (parse_hermes_video_proposal,HERMES_VIDEO_PROPOSAL_START,'동작·영상 제안이 있습니다. 이 작업을 선택한 뒤 동작·영상 위임에서 제안을 불러와 검토하세요.')):
        try:
            current_parser(current_answer_text)
        except (ValueError, TypeError, KeyError):
            continue
        current_marker_position = current_answer_text.rfind('\n' + current_marker + '\n')
        if current_marker_position < 0:
            if not current_answer_text.startswith(current_marker + '\n'):
                continue
            current_narrative_text = ''
        else:
            current_narrative_text = current_answer_text[:current_marker_position].rstrip()
        current_suffix_text = ''
        if current_marker in (HERMES_SPRITE_PROPOSAL_START,HERMES_EFFECT_PROPOSAL_START,HERMES_BILLBOARD_PROPOSAL_START,HERMES_FIELD_PROPOSAL_START,HERMES_TRANSLATION_PROPOSAL_START,HERMES_AUDIO_PROPOSAL_START,HERMES_VIDEO_PROPOSAL_START):
            current_end_marker = 'END_' + current_marker
            current_suffix_text = current_answer_text.split('\n' + current_end_marker,1)[1].strip()
        return (current_narrative_text + '\n\n' if current_narrative_text else '') + current_instruction_text + ('\n\n' + current_suffix_text if current_suffix_text else '')
    return current_answer_text


def read_hermes_session_conversation(hermes_session_identifier, hermes_selected_job=None):
    """메시지와 참조된 기존 작업의 현재 결과를 함께 표시한다."""
    if not hermes_session_identifier:
        return [], '세션을 선택하거나 새로 만드세요.', gr.update(active=False), gr.update(choices=[], value=None)
    try:
        hermes_session_record = execute_remote_management_command('hermes-agent', 'hermes-session-view', {'session_id': hermes_session_identifier})
        hermes_message_records = hermes_session_record['messages']
        hermes_conversation_values = []
        hermes_active_jobs = False
        hermes_job_choices = []
        for current_message_record in hermes_message_records[-20:]:
            hermes_conversation_values.append({'role': 'user', 'content': current_message_record['text']})
            current_job_identifier = current_message_record.get('job_id')
            if not current_job_identifier:
                current_answer_text = '접수 상태를 확인할 수 없습니다. 같은 메시지를 같은 식별자로 재시도하세요.'
            else:
                current_job_record = current_message_record.get('job') or {}
                current_status_record = current_job_record.get('status') or {}
                current_status_name = current_status_record.get('status', 'unknown')
                hermes_job_choices.append((current_job_identifier + ' · ' + str(current_status_name), current_job_identifier))
                hermes_active_jobs = hermes_active_jobs or current_status_name in ('queued', 'running')
                current_activity_record = current_job_record.get('tool_activity') or {}
                current_activity_events = current_activity_record.get('events', [])
                if isinstance(current_activity_events, list) and current_activity_events:
                    current_activity_lines = ['도구 사용 내역']
                    if current_activity_record.get('truncated'):
                        current_activity_lines.append('최근 일부만 표시 · 전체 내용은 작업 로그에서 확인')
                    for current_tool_event in current_activity_events:
                        if not isinstance(current_tool_event, dict):
                            continue
                        current_tool_label = str(current_tool_event.get('name', 'unknown'))
                        current_tool_time = str(current_tool_event.get('timestamp', '시간 확인 불가'))
                        if current_tool_event.get('type') == 'tool_use':
                            current_tool_line = current_tool_time + ' · 호출 ' + current_tool_label
                            if current_tool_event.get('target'):
                                current_tool_line += ' · ' + str(current_tool_event['target'])
                        else:
                            current_tool_line = current_tool_time + ' · 결과 ' + current_tool_label + ' · ' + {'success':'성공', 'error':'오류', 'recorded':'기록됨'}.get(current_tool_event.get('result'), '확인 불가')
                        current_activity_lines.append(current_tool_line)
                    hermes_conversation_values.append({'role': 'assistant', 'content': '\n'.join(current_activity_lines)})
                current_final_answer = current_job_record.get('final_response')
                current_answer_text = format_hermes_conversation_answer(current_final_answer, current_job_record.get('final_response_truncated', False))
                if current_job_record.get('final_response_truncated'):
                    current_answer_text += '\n[응답 일부만 표시]'
                current_answer_text += '\n\n작업 ' + current_job_identifier + ' · 상태 ' + current_status_name
                if current_status_record.get('message'):
                    current_answer_text += ' · ' + str(current_status_record['message'])
                if current_status_record.get('error'):
                    current_answer_text += ' · 오류: ' + str(current_status_record['error'])
            if current_message_record.get('context_truncated'):
                current_answer_text += '\n[이 요청에는 이전 문맥 일부만 전달됨]'
            hermes_conversation_values.append({'role': 'assistant', 'content': current_answer_text})
        hermes_session_message = '세션 ' + hermes_session_identifier + ' · 메시지 ' + str(hermes_session_record['message_count']) + '개 · 확인 ' + hermes_session_record['queried_at']
        if hermes_session_record.get('truncated'):
            hermes_session_message += ' · 최근 20개만 표시'
        hermes_job_identifiers = [current_job_choice[1] for current_job_choice in hermes_job_choices]
        hermes_selected_value = hermes_selected_job if hermes_selected_job in hermes_job_identifiers else (hermes_job_identifiers[-1] if hermes_job_identifiers else None)
        return hermes_conversation_values, hermes_session_message, gr.update(active=hermes_active_jobs), gr.update(choices=hermes_job_choices, value=hermes_selected_value)
    except Exception as hermes_request_error:
        raise gr.Error('세션 조회 실패: ' + str(hermes_request_error)) from hermes_request_error


def read_hermes_building_catalog_rows(current_search_text, current_offset_value, current_page_state=None):
    """콘텐츠 서비스 건물 목록을 화면에 표시한다."""
    try:
        current_request_record={'query':current_search_text or '', 'offset':current_offset_value, 'limit':20}
        if current_page_state is not None:
            if not isinstance(current_page_state,dict) or current_page_state.get('query')!=(current_search_text or '') or current_page_state.get('next_offset')!=current_offset_value or not isinstance(current_page_state.get('snapshot'),str):
                raise ValueError('검색 조건 또는 페이지가 바뀌었습니다. 처음부터 다시 조회하세요.')
            current_request_record['snapshot']=current_page_state['snapshot']
        current_catalog_record=execute_remote_management_command('hermes-agent','hermes-building-catalog',current_request_record)
        current_building_rows=[]
        for current_building_record in current_catalog_record['items']:
            current_pixels=current_building_record['image_pixels']
            current_properties=current_building_record.get('display_properties') or {}
            current_building_rows.append([current_building_record['id'],str(current_pixels['width'])+'×'+str(current_pixels['height']),str(current_properties.get('anchorX','설정 필요')),str(current_properties.get('anchorY','설정 필요')),', '.join(item['map'] for item in current_building_record['uses'])])
        current_next_offset=current_catalog_record.get('next_offset')
        current_next_value={'query':current_search_text or '', 'next_offset':current_next_offset, 'snapshot':current_catalog_record.get('snapshot')} if current_next_offset is not None else None
        current_status_text=f"총 {current_catalog_record['total']}개 · 시작 {current_catalog_record['offset']} · 콘텐츠 세대 {current_catalog_record['generation']} · 이미지 픽셀은 게임 표시 크기가 아닙니다."
        return current_building_rows,current_status_text,current_next_value,gr.update(interactive=current_next_value is not None),[{**current_item_value,'generation':current_catalog_record['generation']} for current_item_value in current_catalog_record['items']],None
    except Exception as current_catalog_error:
        return [],'건물 목록 조회 실패: '+str(current_catalog_error),None,gr.update(interactive=False),[],None


def select_hermes_building_catalog_item(current_catalog_items, current_selection_event: gr.SelectData):
    current_row_index=current_selection_event.index[0] if isinstance(current_selection_event.index,(tuple,list)) else current_selection_event.index
    if not isinstance(current_catalog_items,list) or type(current_row_index) is not int or not 0<=current_row_index<len(current_catalog_items):
        raise gr.Error('건물을 다시 검색하고 행을 선택하세요.')
    return current_catalog_items[current_row_index]


def prepare_hermes_building_anchor_draft(current_catalog_items,current_selection_event: gr.SelectData):
    import json
    current_item_record=select_hermes_building_catalog_item(current_catalog_items,current_selection_event)
    current_property_values=current_item_record.get('display_properties')
    if not isinstance(current_property_values,dict) or not {'anchorX','anchorY'} <= current_property_values.keys():
        raise gr.Error('현재 건물의 공용 앵커를 확인할 수 없습니다.')
    current_draft_record={'texture':current_item_record['id'],'generation':current_item_record['generation'],'expected':current_property_values,'properties':dict(current_property_values)}
    return current_item_record,json.dumps(current_draft_record,ensure_ascii=False,indent=2),uuid.uuid4().hex,None,gr.update(visible=False),'properties의 앵커 X·Y만 수정하고 검토하세요.'


def review_hermes_building_anchor_draft(current_draft_text,current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):raise gr.Error('접수 ID 형식 오류')
    current_draft_record=parse_management_request_json(current_draft_text)
    current_preview_record=execute_remote_management_command('hermes-agent','hermes-building-preview',{'draft':current_draft_record})
    current_review_record={'request_id':current_request_identifier,'draft':current_draft_record,'review_sha256':current_preview_record['review_sha256']}
    return current_review_record,current_preview_record,gr.update(visible=True),'변경 전후와 사용 맵을 확인하세요. 저장 후 게임 화면의 외형을 별도로 확인하세요.'


def save_hermes_building_anchor_draft(current_review_record,current_draft_text,current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    if not isinstance(current_review_record,dict) or current_review_record.get('request_id')!=current_request_identifier or current_review_record.get('draft')!=parse_management_request_json(current_draft_text):raise gr.Error('초안이나 접수 ID가 변경됐습니다. 다시 검토하세요.')
    current_result_record=execute_remote_management_command('hermes-agent','hermes-building-save',current_review_record)
    if current_result_record.get('state')=='unknown':return None,gr.update(visible=False),'저장 결과 확인 필요 · 원본과 접수를 확인하세요. 자동 재접수하지 않습니다.'
    if current_result_record.get('state')!='completed' or current_result_record.get('saved') is not True:raise gr.Error('저장 결과를 확인할 수 없습니다.')
    return None,gr.update(visible=False),'건물 공용 앵커 저장 완료 · 사용 맵과 게임 외형을 확인하세요.'


def invalidate_hermes_building_review():
    """화면의 입력이 바뀌면 이전 확인을 즉시 해제한다."""
    return None,None,gr.update(visible=False),'입력 또는 검색 조건이 변경됐습니다. 다시 검토하세요.'


def read_hermes_building_anchor_status(current_request_identifier):
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-building-receipt',{'request_id':current_request_identifier})
    return {'not_found':'접수 기록이 없습니다.','unknown':'저장 결과 확인 필요 · 원본과 접수를 확인하세요.','completed':'건물 앵커 저장 완료 · 사용 맵과 게임 외형을 확인하세요.'}.get(current_receipt_record.get('state'),'저장 상태를 확인할 수 없습니다.')


def read_hermes_world_map_rows():
    """등록 원본과 연결 정보를 표로 표시한다."""
    try:
        current_catalog_record = execute_remote_management_command('hermes-agent','hermes-world-map',{})
        current_world_rows = [[item['id'],item['name'],'도시' if item['safe_town'] else '필드',str(item['column']),str(item['row']),', '.join(link['target']+' ('+link['direction']+')' for link in item['connections'])] for item in current_catalog_record['maps']]
        return current_world_rows, '맵 '+str(len(current_world_rows))+'개 · 등록 원본 '+str(len(current_catalog_record['provenance']))+'건 · 조회 '+current_catalog_record['queried_at']+' · 좌표는 월드맵 표시 위치입니다.', current_catalog_record['maps'], None
    except Exception as current_world_error:
        return [], '월드맵 조회 실패: '+str(current_world_error), [], None


def select_hermes_world_map_item(current_catalog_items, current_selection_event: gr.SelectData):
    current_row_index = current_selection_event.index[0] if isinstance(current_selection_event.index,(tuple,list)) else current_selection_event.index
    if not isinstance(current_catalog_items,list) or type(current_row_index) is not int or not 0 <= current_row_index < len(current_catalog_items):
        raise gr.Error('월드맵을 다시 조회하고 행을 선택하세요.')
    return current_catalog_items[current_row_index]


def read_hermes_billboard_catalog_rows(current_category_value, current_search_text, current_offset_value):
    """공용 카탈로그 결과를 한 화면의 범위로 표시한다."""
    try:
        current_request_record = {'query':current_search_text or '', 'offset':current_offset_value, 'limit':20}
        if current_category_value:
            current_request_record['category'] = current_category_value
        current_catalog_record = execute_remote_management_command('hermes-agent','hermes-billboard-catalog',current_request_record)
        current_asset_rows = []
        for current_asset_record in current_catalog_record['items']:
            current_display_record = current_asset_record.get('display_properties') or {}
            current_modeling_record = current_asset_record.get('modeling') or {}
            current_asset_rows.append([current_asset_record['id'], current_asset_record['name'], current_asset_record['category'], str(current_display_record.get('displayHeight','설정 필요')), current_modeling_record.get('purpose',''), current_modeling_record.get('visual_review_status','확인 필요'), ', '.join(item['map'] for item in current_asset_record['maps'])])
        current_next_value = current_catalog_record.get('next_offset')
        current_revision_value = current_catalog_record.get('revision') or '확인 불가'
        current_status_text = f"총 {current_catalog_record['total']}개 · 시작 {current_catalog_record['offset']} · 원본 리비전 {current_revision_value} · 이미지는 PNG 해상도가 아닌 공용 표시 높이를 사용합니다. 원본이 바뀌면 다시 검색하세요."
        return current_asset_rows, current_status_text, current_next_value, gr.update(interactive=current_next_value is not None), current_catalog_record['items'], None
    except Exception as current_catalog_error:
        return [], '빌보드 조회 실패: '+str(current_catalog_error), None, gr.update(interactive=False), [], None


def select_hermes_billboard_catalog_item(current_catalog_items, current_selection_event: gr.SelectData):
    """선택한 항목의 공용 속성과 배치 근거를 읽는다."""
    current_row_index = current_selection_event.index[0] if isinstance(current_selection_event.index, (tuple,list)) else current_selection_event.index
    if not isinstance(current_catalog_items,list) or type(current_row_index) is not int or not 0 <= current_row_index < len(current_catalog_items):
        raise gr.Error('빌보드를 다시 검색하고 행을 선택하세요.')
    return current_catalog_items[current_row_index]





def read_hermes_sprite_catalog_choices(current_query_text,current_offset_value):
    if type(current_offset_value) not in (int,float) or int(current_offset_value)!=current_offset_value or current_offset_value<0:
        raise gr.Error('조회 시작 위치는 0 이상의 정수여야 합니다.')
    current_catalog_record=execute_remote_management_command('hermes-agent','hermes-sprite-catalog',{'query':current_query_text or '', 'offset':int(current_offset_value),'limit':20})
    current_choice_values=[(current_item_record['label']+' · '+current_item_record['path'],current_item_record['path']) for current_item_record in current_catalog_record['items']]
    current_status_text=f"총 {current_catalog_record['total']}개 · 시작 {current_catalog_record['offset']} · 원본을 선택하세요."
    return gr.update(choices=current_choice_values,value=None),None,current_status_text,current_catalog_record['next_offset'],gr.update(interactive=current_catalog_record['next_offset'] is not None)


def read_hermes_sprite_sheet_summary(current_asset_path,current_frame_offset,current_snapshot_record):
    if not current_asset_path:raise gr.Error('등록된 스프라이트를 선택하세요.')
    if type(current_frame_offset) not in (int,float) or int(current_frame_offset)!=current_frame_offset or current_frame_offset<0:raise gr.Error('프레임 위치는 0 이상의 정수여야 합니다.')
    current_request_record={'path':current_asset_path,'offset':int(current_frame_offset),'limit':20}
    if current_frame_offset>0:
        if not isinstance(current_snapshot_record,dict) or current_snapshot_record.get('path')!=current_asset_path:
            raise gr.Error('먼저 첫 프레임부터 조회하세요.')
        current_request_record['snapshot']=current_snapshot_record['snapshot']
    current_detail_record=execute_remote_management_command('hermes-agent','hermes-sprite-detail',current_request_record)
    current_snapshot_record={'path':current_asset_path,'snapshot':current_detail_record['snapshot']}
    return current_detail_record,('이미지와 등록된 메타데이터 해시를 검증했습니다.' if current_detail_record.get('metadata_sha256') else '이미지 해시를 검증했습니다. 연결된 애니메이션 메타데이터가 없습니다.')+' 외형과 재생은 스프라이트 시트 편집기에서 확인하세요.',current_snapshot_record



def make_hermes_sprite_anchor_draft(current_detail_record):
    import json
    if not isinstance(current_detail_record,dict) or not current_detail_record.get('metadata_sha256') or not current_detail_record.get('animation'):
        raise gr.Error('애니메이션 좌표가 있는 등록 시트를 먼저 조회하세요.')
    current_draft_record={'path':current_detail_record['path'],'snapshot':current_detail_record['snapshot'],'columns':4,'anchors':[]}
    return json.dumps(current_draft_record,ensure_ascii=False,indent=2),None,gr.update(visible=False),'출력 열 수와 변경할 frame_id·x·y를 지정하고 검증하세요. 이미지 재패킹이 발생합니다.'



def load_hermes_sprite_anchor_proposal(current_job_identifier):
    """완료된 제안의 기준 해시가 현재 시트와 일치할 때 초안으로 불러온다."""
    import json
    if not current_job_identifier:raise gr.Error('먼저 세션 작업을 선택하세요.')
    current_proposal_record=execute_remote_management_command('hermes-agent','hermes-sprite-proposal',{'id':current_job_identifier})['proposal']
    current_detail_record=execute_remote_management_command('hermes-agent','hermes-sprite-detail',{'path':current_proposal_record['path'],'offset':0,'limit':20})
    if current_detail_record.get('snapshot')!=current_proposal_record['snapshot'] or not current_detail_record.get('metadata_sha256'):
        raise gr.Error('스프라이트 원본이 변경됐거나 메타데이터가 없습니다. 다시 조회하세요.')
    current_choice_update=gr.update(choices=[(current_detail_record['path'],current_detail_record['path'])],value=current_detail_record['path'])
    return current_choice_update,json.dumps(current_proposal_record,ensure_ascii=False,indent=2),uuid.uuid4().hex,None,gr.update(visible=False),'현재 원본과 일치하는 제안을 불러왔습니다. 앵커·시트·재생을 검수하세요.'


def review_hermes_sprite_anchor_draft(current_draft_text,current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):raise gr.Error('접수 ID 형식 오류')
    current_draft_record=parse_management_request_json(current_draft_text)
    current_preview_record=execute_remote_management_command('hermes-agent','hermes-sprite-preview',{'draft':current_draft_record})
    import base64
    from io import BytesIO
    from PIL import Image
    current_preview_image=Image.open(BytesIO(base64.b64decode(current_preview_record['preview_image'],validate=True)))
    current_preview_image.load()
    current_review_record={'request_id':current_request_identifier,'draft':current_draft_record,'token':current_preview_record['token'],'review_sha256':current_preview_record['review_sha256']}
    current_summary_record={current_field_name:current_field_value for current_field_name,current_field_value in current_preview_record.items() if current_field_name!='preview_image'}
    current_clip_choices=[(current_clip_record['id'],current_clip_record['id']) for current_clip_record in current_preview_record.get('clips',[])]
    return current_review_record,current_summary_record,current_preview_image,gr.update(choices=current_clip_choices,value=None),gr.update(visible=True)



def render_hermes_sprite_anchor_playback(current_review_record,current_draft_text,current_request_identifier,current_fps_value):
    import base64
    from tools.review.common.management_gateway import parse_management_request_json
    current_draft_record=parse_management_request_json(current_draft_text)
    if not isinstance(current_review_record,dict) or current_review_record.get('request_id')!=current_request_identifier or current_review_record.get('draft')!=current_draft_record:
        raise gr.Error('초안이나 접수 ID가 변경됐습니다. 다시 검증하세요.')
    if type(current_fps_value) not in (int,float) or int(current_fps_value)!=current_fps_value:
        raise gr.Error('재생 FPS를 선택하세요.')
    current_request_record={current_field_name:current_review_record[current_field_name] for current_field_name in ('draft','token','review_sha256')}
    current_result_record=execute_remote_management_command('hermes-agent','hermes-sprite-playback',{**current_request_record,'fps':int(current_fps_value)})
    try:current_gif_bytes=base64.b64decode(current_result_record['gif'],validate=True)
    except (KeyError,ValueError,TypeError) as current_gif_error:raise gr.Error('재생 미리보기 형식 오류') from current_gif_error
    import hashlib
    if not current_gif_bytes.startswith((b'GIF87a',b'GIF89a')) or len(current_gif_bytes)>9_000_000 or hashlib.sha256(current_gif_bytes).hexdigest()!=current_result_record.get('sha256'):
        raise gr.Error('재생 미리보기 해시 또는 형식 오류')
    current_gif_text=base64.b64encode(current_gif_bytes).decode('ascii')
    current_playback_html='<img alt="스프라이트 앵커 정렬 재생" style="max-width:100%;image-rendering:pixelated" src="data:image/gif;base64,'+current_gif_text+'">'
    current_status_text=f"전체 {current_result_record['frame_count']}프레임 · 균일 {current_result_record['fps']} FPS · {current_result_record['note']}"
    return current_playback_html,current_status_text



def render_hermes_sprite_registered_clip(current_review_record,current_draft_text,current_request_identifier,current_clip_identifier):
    import base64
    import hashlib
    from tools.review.common.management_gateway import parse_management_request_json
    current_draft_record=parse_management_request_json(current_draft_text)
    if not isinstance(current_review_record,dict) or current_review_record.get('request_id')!=current_request_identifier or current_review_record.get('draft')!=current_draft_record:
        raise gr.Error('초안이나 접수 ID가 변경됐습니다. 다시 검증하세요.')
    if not current_clip_identifier:raise gr.Error('등록된 클립을 선택하세요.')
    current_request_record={current_field_name:current_review_record[current_field_name] for current_field_name in ('draft','token','review_sha256')}
    current_result_record=execute_remote_management_command('hermes-agent','hermes-sprite-clip-playback',{**current_request_record,'clip':current_clip_identifier})
    try:current_gif_bytes=base64.b64decode(current_result_record['gif'],validate=True)
    except (KeyError,ValueError,TypeError) as current_gif_error:raise gr.Error('클립 미리보기 형식 오류') from current_gif_error
    if not current_gif_bytes.startswith((b'GIF87a',b'GIF89a')) or len(current_gif_bytes)>9_000_000 or hashlib.sha256(current_gif_bytes).hexdigest()!=current_result_record.get('sha256'):
        raise gr.Error('클립 미리보기 해시 또는 형식 오류')
    current_gif_text=base64.b64encode(current_gif_bytes).decode('ascii')
    current_playback_html='<img alt="등록 클립 앵커 정렬 재생" style="max-width:100%;image-rendering:pixelated" src="data:image/gif;base64,'+current_gif_text+'">'
    current_status_text=f"클립 {current_clip_identifier} · {current_result_record['frame_count']}프레임 · 반복 {'예' if current_result_record['loop'] else '아니요'} · {current_result_record['note']}"
    return current_playback_html,current_status_text


def save_hermes_sprite_anchor_draft(current_review_record,current_draft_text,current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    current_draft_record=parse_management_request_json(current_draft_text)
    if not isinstance(current_review_record,dict) or current_review_record.get('request_id')!=current_request_identifier or current_review_record.get('draft')!=current_draft_record:raise gr.Error('초안이나 접수 ID가 변경됐습니다. 다시 검증하세요.')
    current_result_record=execute_remote_management_command('hermes-agent','hermes-sprite-save',current_review_record)
    if current_result_record.get('state')=='unknown':return None,gr.update(visible=False),'저장 결과 확인 필요 · 에셋과 잠금 목록을 확인하고 자동 재접수하지 마세요.'
    if current_result_record.get('state')!='completed' or current_result_record.get('saved') is not True:raise gr.Error('저장 결과 확인 필요 · 같은 접수 ID를 유지하세요.')
    return None,gr.update(visible=False),'시트·메타데이터·등록부·프런트 잠금 저장 완료 · 원본과 재생을 다시 확인하세요.'


def read_hermes_sprite_anchor_status(current_request_identifier):
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-sprite-receipt',{'request_id':current_request_identifier})
    if current_receipt_record.get('state')=='not_found':return '스프라이트 저장 접수 기록이 없습니다.'
    if current_receipt_record.get('state')=='unknown':return '저장 결과 확인 필요 · 에셋과 잠금 목록을 확인하고 자동 재접수하지 마세요.'
    return '스프라이트 저장 완료 · 원본과 재생을 다시 확인하세요.' if current_receipt_record.get('saved') is True else '저장 상태를 확인할 수 없습니다.'


def read_hermes_kimodo_keyframe_rows(current_query_text,current_offset_value,current_snapshot_value=None):
    if type(current_offset_value) not in (int,float) or int(current_offset_value)!=current_offset_value or current_offset_value<0:
        raise gr.Error('조회 시작 위치는 0 이상의 정수여야 합니다.')
    current_request_value={'query':current_query_text or '', 'offset':int(current_offset_value),'limit':20}
    if current_snapshot_value is not None:current_request_value['snapshot']=current_snapshot_value
    current_result_value=execute_remote_management_command('hermes-agent','hermes-kimodo-keyframes',current_request_value)
    current_rows_value=[[item['id'],item['tag'],item['source_frame']] for item in current_result_value['items']]
    current_next_value=current_result_value.get('next_offset')
    current_next_record={'query':current_query_text or '', 'offset':current_next_value,'snapshot':current_result_value['snapshot']} if current_next_value is not None else None
    return current_rows_value,'전체 '+str(current_result_value['total'])+'개 · 시작 '+str(int(current_offset_value))+' · 원본 해시와 실제 동작은 Kimodo에서 확인하세요.',current_next_record,gr.update(interactive=current_next_record is not None)


def read_next_hermes_kimodo_keyframe_rows(current_query_text,current_next_record):
    if not isinstance(current_next_record,dict) or current_next_record.get('query')!=(current_query_text or '') or type(current_next_record.get('offset')) is not int:
        raise gr.Error('검색어가 변경됐습니다. 다시 검색하세요.')
    current_offset_value=current_next_record['offset']
    current_rows_value,current_status_value,current_next_value,current_button_value=read_hermes_kimodo_keyframe_rows(current_query_text,current_offset_value,current_next_record.get('snapshot'))
    return current_offset_value,current_rows_value,current_status_value,current_next_value,current_button_value


def select_hermes_kimodo_keyframe_row(current_rows_value,current_selection_event: gr.SelectData):
    import re
    current_row_index=current_selection_event.index[0] if isinstance(current_selection_event.index,(tuple,list)) else current_selection_event.index
    if not isinstance(current_rows_value,list) or type(current_row_index) is not int or not 0<=current_row_index<len(current_rows_value):
        raise gr.Error('현재 키프레임 목록을 다시 검색하세요.')
    current_row_value=current_rows_value[current_row_index]
    if not isinstance(current_row_value,(list,tuple)) or not current_row_value or not isinstance(current_row_value[0],str) or not re.fullmatch(r'[a-f0-9]{32}',current_row_value[0]):
        raise gr.Error('키프레임 행 형식 오류')
    return current_row_value[0]


def append_hermes_kimodo_keyframe_placement(current_keyframes_text,current_keyframe_identifier,current_output_frame,current_frame_count):
    import json
    from tools.review.domains.kimodo.keyframe_storage import validate_kimodo_keyframe_placements
    try:
        current_placements_value=json.loads(current_keyframes_text or '[]')
        if not isinstance(current_placements_value,list) or type(current_output_frame) not in (int,float) or int(current_output_frame)!=current_output_frame:
            raise ValueError('키프레임 배열과 정수 출력 프레임을 입력하세요.')
        current_placements_value=validate_kimodo_keyframe_placements([*current_placements_value,{'id':current_keyframe_identifier,'frame':int(current_output_frame)}],current_frame_count)
        return json.dumps(current_placements_value,ensure_ascii=False,indent=2)
    except (ValueError,TypeError,OverflowError) as current_input_error:
        raise gr.Error('키프레임 배치 오류: '+str(current_input_error)) from current_input_error


def verify_hermes_kimodo_keyframe_placements(current_keyframes_text,current_frame_count):
    import json
    try:
        if type(current_frame_count) not in (int,float) or int(current_frame_count)!=current_frame_count:
            raise ValueError('출력 프레임 수는 정수여야 합니다.')
        current_placements_value=json.loads(current_keyframes_text or '[]')
        current_result_value=execute_remote_management_command('hermes-agent','hermes-kimodo-keyframe-validate',{'keyframes':current_placements_value,'frames':int(current_frame_count)})
        current_source_values=current_result_value['sources']
        return '검증 완료 · '+str(len(current_result_value['placements']))+'개 배치, '+str(len(current_source_values))+'개 원본 · 골격 구조 일치\n'+'\n'.join(item['id']+' · PNG SHA-256: '+item['preview_sha256'] for item in current_source_values)+'\n접수 시 원본을 다시 검증하며, 지금 검증한 뒤 원본이 바뀔 수 있습니다.'
    except (ValueError,TypeError,KeyError,OSError,RuntimeError,OverflowError) as current_error_value:
        return '키프레임 검증 실패: '+str(current_error_value)


def read_hermes_kimodo_keyframe_preview_image(current_keyframe_identifier):
    import base64
    import io
    from PIL import Image
    current_result_value=execute_remote_management_command('hermes-agent','hermes-kimodo-keyframe-preview',{'keyframe_id':current_keyframe_identifier})
    current_image_bytes=base64.b64decode(current_result_value['image_base64'],validate=True)
    with Image.open(io.BytesIO(current_image_bytes)) as current_image_value:
        current_display_image=current_image_value.convert('RGB')
    return current_display_image,'검증된 미리보기 PNG SHA-256: '+current_result_value['sha256']+' · 생성 동작의 품질은 별도 확인하세요.'


def load_hermes_effect_choices():
    try:
        current_catalog_record=execute_remote_management_command('hermes-agent','hermes-effect-catalog',{'limit':30})
        current_choice_values=[(current_effect_record['name']+' · '+current_effect_record['id'],current_effect_record['id']) for current_effect_record in current_catalog_record['items']]
        current_status_text=f"검수 가능한 이펙트 {current_catalog_record['total']}개 중 {len(current_choice_values)}개 표시"
        if current_catalog_record.get('next_offset') is not None:
            current_status_text+=' · 나머지는 MCP의 페이지 조회를 이용하세요.'
        return gr.update(choices=current_choice_values,value=None),None,current_status_text
    except (OSError,ValueError,RuntimeError,KeyError,TypeError):
        return gr.update(choices=[],value=None),None,'이펙트 조회 실패 · 콘텐츠 DB 연결을 확인하세요.'


def load_hermes_effect_summary(current_effect_identifier):
    if not current_effect_identifier:
        raise gr.Error('이펙트를 선택하세요.')
    current_detail_record=execute_remote_management_command('hermes-agent','hermes-effect-detail',{'id':current_effect_identifier})
    return current_detail_record,'좌표를 불러왔습니다. 이미지와 실제 배치는 이펙트 검수 화면에서 확인하세요.'



def load_hermes_effect_edit_draft(current_effect_identifier):
    import json
    current_detail_record=execute_remote_management_command('hermes-agent','hermes-effect-detail',{'id':current_effect_identifier})
    current_alignment_record=current_detail_record.get('alignment')
    if not isinstance(current_alignment_record,dict):
        raise gr.Error('이 이펙트는 공용 좌표 편집을 지원하지 않습니다.')
    current_draft_record={'id':current_detail_record['id'],'revision':current_detail_record['revision'],**{current_field_name:current_alignment_record[current_field_name] for current_field_name in ('target','alpha','frames')}}
    return json.dumps(current_draft_record,ensure_ascii=False,indent=2),None,gr.update(visible=False),'변경할 좌표를 입력하고 검증하세요.'



def load_hermes_effect_edit_proposal(current_job_identifier):
    """선택한 작업의 제안을 현재 원본 리비전과 비교해 초안으로 불러온다."""
    import json
    if not current_job_identifier:
        raise gr.Error('먼저 세션 작업을 선택하세요.')
    current_proposal_record=execute_remote_management_command('hermes-agent','hermes-effect-proposal',{'id':current_job_identifier})['proposal']
    current_detail_record=execute_remote_management_command('hermes-agent','hermes-effect-detail',{'id':current_proposal_record['id']})
    if current_detail_record['revision']!=current_proposal_record['revision']:
        raise gr.Error('이펙트 원본이 변경됐습니다. 다시 조회하고 제안하세요.')
    if not isinstance(current_detail_record.get('alignment'),dict) or current_detail_record['frames']!=len(current_proposal_record['frames']):
        raise gr.Error('좌표 편집 대상이나 프레임 수를 확인하세요.')
    current_choice_update=gr.update(choices=[(current_detail_record['name']+' · '+current_detail_record['id'],current_detail_record['id'])],value=current_detail_record['id'])
    return current_choice_update,current_detail_record,json.dumps(current_proposal_record,ensure_ascii=False,indent=2),uuid.uuid4().hex,None,gr.update(visible=False),'제안을 불러왔습니다. 실제 이미지와 변경 전후를 검수한 뒤 저장하세요.'


def review_hermes_effect_edit_draft(current_draft_text,current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
        raise gr.Error('접수 ID 형식 오류')
    current_draft_record=parse_management_request_json(current_draft_text)
    current_preview_record=execute_remote_management_command('hermes-agent','hermes-effect-preview',{'draft':current_draft_record})
    current_review_record={'request_id':current_request_identifier,'draft':current_draft_record,'token':current_preview_record['token']}
    return current_review_record,current_preview_record,gr.update(visible=True)


def save_hermes_effect_edit_draft(current_review_record,current_draft_text,current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    current_draft_record=parse_management_request_json(current_draft_text)
    if not isinstance(current_review_record,dict) or current_review_record.get('request_id')!=current_request_identifier or current_review_record.get('draft')!=current_draft_record:
        raise gr.Error('초안이나 접수 ID가 변경됐습니다. 다시 검증하세요.')
    current_result_record=execute_remote_management_command('hermes-agent','hermes-effect-save',current_review_record)
    if current_result_record.get('state')=='unknown':
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 원장을 확인하고 자동 재접수하지 마세요.'
    if current_result_record.get('state')!='completed' or current_result_record.get('saved') is not True:
        raise gr.Error('저장 결과 확인 필요 · 같은 접수 ID를 유지하세요.')
    return None,gr.update(visible=False),'이펙트 좌표 저장 완료 · 사용 맵과 원장 반영을 확인하세요.'


def review_hermes_effect_registration_draft(current_draft_text,current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
        raise gr.Error('접수 ID 형식 오류')
    current_draft_record=parse_management_request_json(current_draft_text)
    current_preview_record=execute_remote_management_command('hermes-agent','hermes-effect-register-preview',{'draft':current_draft_record})
    current_review_record={'request_id':current_request_identifier,'draft':current_draft_record,'review_sha256':current_preview_record['review_sha256']}
    return current_review_record,current_preview_record,gr.update(visible=True)


def save_hermes_effect_registration_draft(current_review_record,current_draft_text,current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    current_draft_record=parse_management_request_json(current_draft_text)
    if not isinstance(current_review_record,dict) or current_review_record.get('request_id')!=current_request_identifier or current_review_record.get('draft')!=current_draft_record:
        raise gr.Error('초안이나 접수 ID가 변경됐습니다. 다시 검토하세요.')
    current_result_record=execute_remote_management_command('hermes-agent','hermes-effect-register',current_review_record)
    if current_result_record.get('state')=='unknown':
        return None,gr.update(visible=False),'등록 결과 확인 필요 · 원장과 접수 기록을 확인하고 자동 재등록하지 마세요.'
    if current_result_record.get('state')!='completed' or current_result_record.get('id')!=current_draft_record.get('id'):
        raise gr.Error('등록 결과 확인 필요 · 같은 접수 ID를 유지하세요.')
    return None,gr.update(visible=False),'DB 등록 완료 · 세대 '+str(current_result_record.get('generation','확인 필요'))+' · 현재 원장 반영 상태와 게임 참조를 확인하세요.'


def read_hermes_effect_registration_status(current_request_identifier):
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-effect-register-receipt',{'request_id':current_request_identifier})
    return '등록 접수 상태: '+str(current_receipt_record.get('state','unknown'))+' · DB 세대: '+str(current_receipt_record.get('generation','확인 필요'))+' · 현재 원장 상태는 별도로 확인하세요. 미확인 상태는 재등록하지 마세요.'


def load_hermes_waypoint_replacement_draft(current_effect_identifier):
    import json
    if not current_effect_identifier:
        raise gr.Error('기존 웨이포인트를 선택하세요.')
    current_detail_record=execute_remote_management_command('hermes-agent','hermes-effect-detail',{'id':current_effect_identifier})
    if current_detail_record.get('id')!=current_effect_identifier or current_detail_record.get('renderer')!='waypoint-animation':
        raise gr.Error('웨이포인트 이펙트를 선택하세요.')
    current_draft_record={'id':current_detail_record['id'],'revision':current_detail_record['revision'],'effect':{'id':'','name':'','image':'','animation':'','renderer':'waypoint-animation','columns':4,'rows':2,'frames':8}}
    return json.dumps(current_draft_record,ensure_ascii=False,indent=2),None,gr.update(visible=False),'새 이펙트 ID·이름과 등록된 이미지·애니메이션 경로를 입력하세요.'


def review_hermes_waypoint_replacement_draft(current_draft_text,current_request_identifier,current_selected_effect):
    from tools.review.common.management_gateway import parse_management_request_json
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
        raise gr.Error('접수 ID 형식 오류')
    current_draft_record=parse_management_request_json(current_draft_text)
    if not isinstance(current_draft_record,dict) or current_draft_record.get('id')!=current_selected_effect:
        raise gr.Error('선택한 이펙트와 교체 대상 ID가 일치해야 합니다.')
    current_preview_record=execute_remote_management_command('hermes-agent','hermes-waypoint-preview',{'draft':current_draft_record})
    current_review_record={'request_id':current_request_identifier,'draft':current_draft_record,'review_sha256':current_preview_record['review_sha256']}
    return current_review_record,current_preview_record,gr.update(visible=True)


def save_hermes_waypoint_replacement_draft(current_review_record,current_draft_text,current_request_identifier,current_selected_effect):
    from tools.review.common.management_gateway import parse_management_request_json
    current_draft_record=parse_management_request_json(current_draft_text)
    if not isinstance(current_review_record,dict) or current_review_record.get('request_id')!=current_request_identifier or current_review_record.get('draft')!=current_draft_record or current_draft_record.get('id')!=current_selected_effect:
        raise gr.Error('선택·초안·접수 ID가 변경됐습니다. 다시 검토하세요.')
    current_result_record=execute_remote_management_command('hermes-agent','hermes-waypoint-replace',current_review_record)
    if current_result_record.get('state')=='unknown':
        return None,gr.update(visible=False),'교체 결과 확인 필요 · 원장과 접수 기록을 확인하고 자동 재접수하지 마세요.'
    if current_result_record.get('state')!='completed' or current_result_record.get('id')!=current_draft_record['effect']['id']:
        raise gr.Error('교체 결과 확인 필요 · 같은 접수 ID를 유지하세요.')
    return None,gr.update(visible=False),'DB 교체 완료 · 세대 '+str(current_result_record.get('generation','확인 필요'))+' · 저장 시 원장 반영 대기 · 현재 원장 반영 상태와 사용 맵을 확인하세요.'


def read_hermes_waypoint_replacement_status(current_request_identifier):
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-waypoint-receipt',{'request_id':current_request_identifier})
    return '교체 접수 상태: '+str(current_receipt_record.get('state','unknown'))+' · DB 세대: '+str(current_receipt_record.get('generation','확인 필요'))+' · 저장 시 원장 상태: '+str(current_receipt_record.get('ledger_status_at_save','확인 필요'))+' · 현재 원장 상태는 별도로 확인하세요. 응답이 불확실하면 재접수하지 마세요.'


def read_hermes_effect_edit_status(current_request_identifier):
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-effect-receipt',{'request_id':current_request_identifier})
    if current_receipt_record.get('state')=='not_found':return '이펙트 저장 접수 기록이 없습니다.'
    if current_receipt_record.get('state')=='unknown':return '저장 결과 확인 필요 · 원장을 확인하고 자동 재접수하지 마세요.'
    return '이펙트 저장 완료 · 사용 맵과 원장 반영을 확인하세요.' if current_receipt_record.get('saved') is True else '이펙트 저장 상태를 확인할 수 없습니다.'


def load_hermes_billboard_edit_draft(current_asset_identifier):
    """현재 공용 속성과 수정할 필드만 포함한 빈 초안을 불러온다."""
    import json
    current_source_record=execute_remote_management_command('hermes-agent','hermes-billboard-load',{'texture':current_asset_identifier})
    current_draft_record={'revision':current_source_record['revision'],'changes':[{'texture':current_source_record['texture'],'values':{}}]}
    return current_source_record['properties'],json.dumps(current_draft_record,ensure_ascii=False,indent=2),None,gr.update(visible=False),'수정할 공용 속성만 values에 입력하고 검증하세요.'



def load_hermes_billboard_edit_proposal(current_job_identifier):
    """현재 에셋의 선택된 속성이 제안의 관측값과 같을 때만 초안을 만든다."""
    import json
    if not current_job_identifier:
        raise gr.Error('먼저 세션 작업을 선택하세요.')
    current_proposal_record=execute_remote_management_command('hermes-agent','hermes-billboard-proposal',{'id':current_job_identifier})['proposal']
    current_source_record=execute_remote_management_command('hermes-agent','hermes-billboard-load',{'texture':current_proposal_record['texture']})
    current_original_values=current_source_record['properties']
    for current_field_name,current_expected_value in current_proposal_record['expected'].items():
        current_actual_value=current_original_values.get(current_field_name)
        if (type(current_expected_value) is bool and type(current_actual_value) is not bool) or current_actual_value!=current_expected_value:
            raise gr.Error('빌보드 현재값이 제안과 다릅니다. 원본을 다시 확인하세요.')
    current_draft_record={'revision':current_source_record['revision'],'changes':[{'texture':current_source_record['texture'],'values':current_proposal_record['values']}]}
    return current_source_record['texture'],current_original_values,json.dumps(current_draft_record,ensure_ascii=False,indent=2),uuid.uuid4().hex,None,gr.update(visible=False),'현재 속성과 일치하는 제안을 불러왔습니다. 변경과 맵 경고를 검증하세요.'


def review_hermes_billboard_edit_draft(current_draft_text,current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
        raise gr.Error('접수 ID 형식 오류')
    current_draft_record=parse_management_request_json(current_draft_text)
    current_preview_record=execute_remote_management_command('hermes-agent','hermes-billboard-preview',{'draft':current_draft_record})
    current_review_record={'request_id':current_request_identifier,'draft':current_draft_record,'token':current_preview_record['token'],'review_sha256':current_preview_record['review_sha256']}
    current_summary_text='변경 전후·영향 맵·경고를 검토하세요. 저장하면 공용 에셋 속성과 관련 원장이 변경됩니다. 이후 맵 변경과 전체 게임 통행은 별도 확인이 필요합니다.'
    return current_review_record,current_preview_record,current_summary_text,gr.update(visible=True)


def save_hermes_billboard_edit_draft(current_review_record,current_draft_text,current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    current_draft_record=parse_management_request_json(current_draft_text)
    if not isinstance(current_review_record,dict) or current_review_record.get('request_id')!=current_request_identifier or current_review_record.get('draft')!=current_draft_record:
        raise gr.Error('초안이나 접수 ID가 변경됐습니다. 다시 검증하세요.')
    current_result_record=execute_remote_management_command('hermes-agent','hermes-billboard-save',current_review_record)
    if current_result_record.get('state')=='unknown':
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 공용 속성과 원장을 확인하고 자동 재접수하지 마세요.'
    if current_result_record.get('state')!='completed' or current_result_record.get('saved') is not True:
        raise gr.Error('빌보드 저장 결과 확인 필요 · 같은 접수 ID를 유지하세요.')
    return None,gr.update(visible=False),'공용 속성 저장 완료 · 사용 맵을 확인하세요.'


def read_hermes_billboard_edit_status(current_request_identifier):
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-billboard-receipt',{'request_id':current_request_identifier})
    if current_receipt_record.get('state')=='not_found':
        return '빌보드 저장 접수 기록이 없습니다.'
    if current_receipt_record.get('state')=='unknown':
        return '저장 결과 확인 필요 · 공용 속성과 원장을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_record.get('state')=='completed' and current_receipt_record.get('saved') is True:
        return '공용 속성 저장 완료 · 사용 맵을 확인하세요.'
    return '빌보드 저장 상태를 확인할 수 없습니다.'


def load_hermes_city_map_draft(current_map_identifier):
    import json
    try:
        current_draft_value = execute_remote_management_command('hermes-agent','hermes-city-load',{'map':current_map_identifier})
        return json.dumps(current_draft_value,ensure_ascii=False,indent=2), None, gr.update(visible=False), '콘텐츠 DB 원장을 불러왔습니다. 수정하고 검증하세요.'
    except (OSError,ValueError,RuntimeError,KeyError,TypeError):
        return '', None, gr.update(visible=False), '도시 원장을 불러올 수 없습니다. 콘텐츠 DB 연결·인증과 도시 맵 ID를 확인하세요.'


def review_hermes_city_map_draft(current_draft_text,current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
        raise gr.Error('접수 ID 형식 오류')
    current_draft_value = parse_management_request_json(current_draft_text)
    current_preview_value = execute_remote_management_command('hermes-agent','hermes-city-preview',{'draft':current_draft_value})
    current_review_value = {'request_id':current_request_identifier,'draft':current_draft_value,'token':current_preview_value['token']}
    current_summary_value = (f"도시: {current_draft_value['map']} · 접수 ID: {current_request_identifier} · DB 세대: {current_draft_value['generation']} · 리비전: {current_draft_value['revision']} · 변경: {'있음' if current_preview_value['changed'] else '없음'} · 건물: {current_preview_value['buildings']} · 장식: {current_preview_value['objects']}  \
도시 원장 초안과 실제 변경을 확인하세요. 저장하면 콘텐츠 DB가 변경됩니다.")
    return current_review_value,current_summary_value,gr.update(visible=True)


def save_hermes_city_map_draft(current_review_value,current_draft_text,current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    current_draft_value = parse_management_request_json(current_draft_text)
    if not isinstance(current_review_value,dict) or current_review_value.get('request_id') != current_request_identifier or current_review_value.get('draft') != current_draft_value:
        raise gr.Error('초안이나 접수 ID가 변경됐습니다. 다시 검증하세요.')
    current_result_value = execute_remote_management_command('hermes-agent','hermes-city-save',current_review_value)
    if current_result_value.get('state') == 'unknown':
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 도시 원장과 이력을 확인하고 자동 재접수하지 마세요.'
    if current_result_value.get('state') != 'completed':
        raise gr.Error('도시 맵 저장 결과 확인 실패 · 같은 접수 ID를 유지하세요.')
    return None,gr.update(visible=False),('도시 맵 저장 완료 · 원장 반영 상태를 확인하세요.' if current_result_value.get('saved') else '변경 없음 · DB 쓰기를 생략했습니다.')


def list_hermes_city_map_choices():
    current_history_value = execute_remote_management_command('hermes-agent','hermes-city-history',{})
    current_choice_values = [(item['map']+' · '+item['request_id']+' · '+item['state'],item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values,value=None),'최근 도시 맵 저장 접수 '+str(len(current_choice_values))+'건 · 손상된 기록은 제외됩니다.'


def read_hermes_city_map_receipt(current_request_identifier):
    current_receipt_value = execute_remote_management_command('hermes-agent','hermes-city-receipt',{'request_id':current_request_identifier})
    if current_receipt_value.get('state') == 'not_found':
        return '도시 맵 저장 접수 기록이 없습니다.'
    if current_receipt_value.get('state') == 'unknown':
        return '도시: '+current_receipt_value['map']+' · 저장 결과 확인 필요. 원장을 확인하고 자동 재접수하지 마세요.'
    return '도시: '+current_receipt_value['map']+' · '+('저장 완료' if current_receipt_value.get('saved') else '변경 없음')


def load_hermes_field_map_draft(current_map_identifier):
    """현재 장식 오브젝트를 보존하는 변경 없는 초안을 만든다."""
    import json
    current_map_value = execute_remote_management_command('hermes-agent','hermes-field-load',{'map':current_map_identifier})
    current_objects_list = []
    for current_object_value in current_map_value['tiles'].get('objects',[]):
        if current_object_value.get('kind') == 'decoration':
            current_objects_list.append({key:current_object_value[key] for key in ('id','kind','position','textureKey','tileAnchor')})
    current_draft_value = {'map':current_map_value['map'],'revision':current_map_value['revision'],'cells':[],'objects':current_objects_list}
    return json.dumps(current_draft_value,ensure_ascii=False,indent=2), current_map_value, None, gr.update(visible=False), '원본을 불러왔습니다. 초안을 편집한 뒤 검증하세요.'


def load_hermes_field_map_proposal(current_job_identifier):
    """현재 원본과 리비전이 같은 제안만 초안으로 가져온다."""
    import json
    if not current_job_identifier:
        raise gr.Error('먼저 세션 작업을 선택하세요.')
    current_proposal_value = execute_remote_management_command('hermes-agent','hermes-field-proposal',{'id':current_job_identifier})['proposal']
    current_draft_text,current_source_value,current_review_value,current_confirm_value,current_status_value = load_hermes_field_map_draft(current_proposal_value['map'])
    current_draft_value = json.loads(current_draft_text)
    if current_draft_value['revision'] != current_proposal_value['revision']:
        raise gr.Error('맵 원본이 제안 이후 변경됐습니다. 다시 조회하고 새 제안을 받으세요.')
    current_draft_value['cells'] = current_proposal_value['cells']
    return current_proposal_value['map'],json.dumps(current_draft_value,ensure_ascii=False,indent=2),current_source_value,uuid.uuid4().hex,None,gr.update(visible=False),'제안을 불러왔습니다. 기존 장식을 유지했으며 실제 변경을 살펴보고 초안을 검증하세요.'


def review_hermes_field_map_draft(current_draft_text, current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
        raise gr.Error('접수 ID 형식 오류')
    current_draft_value = parse_management_request_json(current_draft_text)
    current_preview_value = execute_remote_management_command('hermes-agent','hermes-field-preview',{'draft':current_draft_value})
    current_review_value = {'request_id':current_request_identifier,'draft':current_draft_value,'token':current_preview_value['token']}
    current_summary_value = (f"맵: {current_draft_value['map']} · 접수 ID: {current_request_identifier} · 변경: {'있음' if current_preview_value['changed'] else '없음'} · 셀: {current_preview_value['cells']} · 장식: {current_preview_value['objects']} · 도달 셀: {current_preview_value['reachable']}  \
저장 시 맵 원본과 등록부·소비자 잠금·카탈로그 또는 콘텐츠 DB가 변경될 수 있습니다. 초안과 원본의 실제 차이를 확인하세요.")
    return current_review_value,current_summary_value,gr.update(visible=True)


def save_hermes_field_map_draft(current_review_value, current_draft_text, current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    current_draft_value = parse_management_request_json(current_draft_text)
    if not isinstance(current_review_value,dict) or current_review_value.get('request_id') != current_request_identifier or current_review_value.get('draft') != current_draft_value:
        raise gr.Error('초안이나 접수 ID가 변경됐습니다. 다시 검증하세요.')
    current_result_value = execute_remote_management_command('hermes-agent','hermes-field-save',current_review_value)
    if current_result_value.get('state') == 'unknown':
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 맵 원본과 관리도구 이력을 확인하고 자동 재접수하지 마세요.'
    if current_result_value.get('state') != 'completed':
        raise gr.Error('저장 결과 확인 실패 · 같은 접수 ID를 유지하세요.')
    return None,gr.update(visible=False),('맵 저장 완료' if current_result_value.get('saved') else '변경 없음') + ' · 원본과 소비자 상태를 확인하세요.'


def list_hermes_field_map_choices():
    current_history_value = execute_remote_management_command('hermes-agent','hermes-field-history',{})
    current_choice_values = [(item['map']+' · '+item['request_id']+' · '+item['state'],item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values,value=None), '최근 맵 저장 접수 ' + str(len(current_choice_values)) + '건 · 손상된 기록은 제외됩니다.'


def read_hermes_field_map_receipt(current_request_identifier):
    current_receipt_value = execute_remote_management_command('hermes-agent','hermes-field-receipt',{'request_id':current_request_identifier})
    if current_receipt_value.get('state') == 'not_found':
        return '맵 저장 접수 기록이 없습니다.'
    if current_receipt_value.get('state') == 'unknown':
        return '맵: '+current_receipt_value['map']+' · 저장 결과 확인 필요. 원본을 확인하고 자동 재접수하지 마세요.'
    return '맵: '+current_receipt_value['map']+' · '+('저장 완료' if current_receipt_value.get('saved') else '변경 없음')


def read_hermes_content_database_summary():
    """DB 저장과 원장 반영 상태를 분리하여 표시한다."""
    current_status_record = execute_remote_management_command('hermes-agent', 'hermes-content-database-status', {})
    if current_status_record.get('status') != 'available':
        return '콘텐츠 DB 상태 확인 불가 · 서비스 연결과 인증을 확인하세요.'
    current_latest_record = current_status_record.get('latest')
    current_latest_text = '기록 없음' if current_latest_record is None else current_latest_record['state'] + (' · 임대 만료' if current_latest_record['lease_expired'] else '')
    return (f"DB 저장 세대: {current_status_record['generation']} · 원장 반영 세대: {current_status_record['ledger_generation']} · "
            f"반영 대기: {'예' if current_status_record['pending'] else '아니요'} · 최근 반영: {current_latest_text} · 조회: {current_status_record['queried_at']}")


def read_hermes_kimodo_build_summary():
    """기존 모델 관리의 빌드 상태를 확인한다."""
    try:
        current_status_record=execute_remote_management_command('hermes-agent','hermes-kimodo-build-status',{})
        from tools.review.ui.gradio.model_management_app import format_migraphx_build_status
        return format_migraphx_build_status({'status':current_status_record['status'],'id':current_status_record.get('job_id')}) + (' · '+current_status_record['failure_reason'] if current_status_record.get('failure_reason') else '') + ' · 캐시 유효성과 실제 작업 생존 여부는 확인되지 않았습니다.'
    except Exception as current_status_error:
        return '빌드 상태 조회 실패: '+str(current_status_error)


def read_hermes_model_readiness_summary(current_service_name):
    """모델 상태와 파일 보유량을 혼동하지 않도록 분리한다."""
    try:
        current_status_record = execute_remote_management_command('hermes-agent','hermes-model-readiness',{'service':current_service_name})
        if current_status_record.get('status') != 'available':
            current_download_record = current_status_record.get('download')
            if current_service_name in ('music-heartmula','sfx-dasheng-audiogen') and isinstance(current_download_record,dict) and type(current_download_record.get('ready')) is bool and current_download_record.get('preparation_status') in ('idle','running','completed','failed','unknown'):
                current_download_state={'idle':'대기','running':'진행 중','completed':'완료','failed':'실패','unknown':'확인 불가'}[current_download_record['preparation_status']]
                return '모델 상태 조회 불가 · ' + str(current_service_name) + ' · 다운로드 파일 준비: ' + ('예' if current_download_record['ready'] else '아니요') + ' · 다운로드 상태: ' + current_download_state
            return '모델 상태 조회 불가 · ' + str(current_service_name)
        current_generation_value = current_status_record.get('generation_ready')
        current_artifacts_value = current_status_record.get('artifacts_ready')
        current_download_text = ''
        if current_service_name in ('music-heartmula','sfx-dasheng-audiogen'):
            current_download_record = current_status_record.get('download')
            if isinstance(current_download_record,dict) and type(current_download_record.get('ready')) is bool and current_download_record.get('preparation_status') in ('idle','running','completed','failed','unknown'):
                current_download_text = ' · 다운로드 파일 준비: ' + ('예' if current_download_record['ready'] else '아니요') + ' · 다운로드 상태: ' + {'idle':'대기','running':'진행 중','completed':'완료','failed':'실패','unknown':'확인 불가'}[current_download_record['preparation_status']]
            else:
                current_download_text = ' · 다운로드 상태: 확인 불가'
        return (str(current_service_name) + ' · 서비스 준비 판정: ' + ('예' if current_status_record['ready'] else '아니요') + ' · 파일 준비 별도 판정: ' + ('예' if current_artifacts_value is True else '아니요' if current_artifacts_value is False else '확인 불가') + ' · 생성 준비: ' + ('예' if current_generation_value is True else '아니요' if current_generation_value is False else '확인 불가') + ' · 준비 상태: ' + current_status_record['preparation_status'] + current_download_text + ' · 다운로드 정책: ' + ('허용' if current_status_record['prepare_allowed'] else '제한') + ' · 조회: ' + current_status_record['queried_at'] + ' · 서비스 응답이며 실행 권한·GPU 실행·전체 해시는 별도 확인')
    except Exception as current_status_error:
        return '모델 상태 조회 실패: '+str(current_status_error)


def review_hermes_model_preparation(current_service_name, current_request_identifier):
    """준비 대상과 영향을 확인하고 제한된 서비스는 접수를 허용하지 않는다."""
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if not isinstance(current_request_identifier, str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
        raise gr.Error('접수 ID 형식을 확인하세요.')
    current_status_record = execute_remote_management_command('hermes-agent', 'hermes-model-readiness', {'service':current_service_name})
    if current_status_record.get('status') != 'available':
        raise gr.Error('모델 서비스 상태를 확인할 수 없습니다.')
    if not current_status_record.get('prepare_allowed'):
        raise gr.Error('기존 관리 정책에서 이 모델의 준비를 제한합니다.')
    current_review_record = {'service':current_service_name, 'request_id':current_request_identifier}
    current_summary_text = (f"대상: {current_service_name} · 접수 ID: {current_request_identifier}  \
현재 파일 준비: {'예' if current_status_record['ready'] else '아니요'} · 준비 상태: {current_status_record['preparation_status']}  \
네트워크 다운로드와 디스크 사용이 발생할 수 있고 서비스에 따라 GPU 작업이 접수될 수 있습니다. 기존 서비스 정책을 적용합니다.")
    return current_review_record, current_summary_text, gr.update(visible=True)


def submit_hermes_model_preparation(current_review_record, current_service_name, current_request_identifier):
    """확인 당시의 대상과 ID가 그대로일 때만 모델 준비를 요청한다."""
    if current_review_record != {'service':current_service_name, 'request_id':current_request_identifier}:
        raise gr.Error('대상이나 접수 ID가 변경됐습니다. 다시 검토하세요.')
    try:
        current_result_value = execute_remote_management_command('hermes-agent', 'hermes-model-prepare', current_review_record)
        current_state_value = current_result_value.get('state')
        if current_state_value not in ('accepted', 'unknown'):
            raise ValueError('접수 응답 형식 오류')
        current_job_value = current_result_value.get('job_id')
        current_message_text = ('접수 결과 확인 필요. 자동 재접수하지 마세요.' if current_state_value == 'unknown' else '준비 요청 응답을 받았습니다. 실제 완료 여부는 모델 상태에서 확인하세요.')
        if current_job_value:
            current_message_text += ' 작업 ID: ' + current_job_value
        return None, gr.update(visible=False), current_message_text
    except Exception as current_submit_error:
        raise gr.Error('준비 요청 확인 실패: ' + str(current_submit_error) + ' · 같은 접수 ID로 확인하세요.') from current_submit_error


def read_hermes_model_preparation_receipt(current_service_name, current_request_identifier):
    current_receipt_value = execute_remote_management_command('hermes-agent', 'hermes-model-prepare-status', {'service':current_service_name, 'request_id':current_request_identifier})
    current_state_value = current_receipt_value.get('state')
    if current_state_value == 'not_found':
        return '접수 기록이 없습니다.'
    return str(current_receipt_value.get('message', '접수 상태를 확인할 수 없습니다.')) + (' 작업 ID: ' + current_receipt_value['job_id'] if current_receipt_value.get('job_id') else '')


def list_hermes_model_preparation_choices():
    current_history_value = execute_remote_management_command('hermes-agent', 'hermes-model-prepare-history', {})
    current_choice_values = [(item['service'] + ' · ' + item['request_id'] + ' · ' + item['state'], item['service'] + ':' + item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values, value=None), '최근 접수 ' + str(len(current_choice_values)) + '건 · 손상된 기록은 제외됩니다.'


def select_hermes_model_preparation_receipt(current_selection_value):
    if not isinstance(current_selection_value, str) or ':' not in current_selection_value:
        raise gr.Error('접수 이력을 선택하세요.')
    current_service_name, current_request_identifier = current_selection_value.split(':', 1)
    return current_service_name, current_request_identifier


def read_hermes_model_inventory_rows():
    """모델 보유량을 기존 공용 계약에서 조회한다."""
    try:
        current_inventory_record = execute_remote_management_command('hermes-agent', 'hermes-model-inventory', {})
        if current_inventory_record.get('status') != 'available':
            return [], '모델 파일 보유량 조회 실패'
        current_model_rows = [[item['service'], str(item['file_count']), str(item['total_bytes']), '일부 누락' if item['incomplete'] else '목록 조회됨'] for item in current_inventory_record['models']]
        return current_model_rows, '조회 ' + current_inventory_record['queried_at'] + ' · 파일 존재는 준비 완료나 해시 검증을 뜻하지 않습니다.'
    except (OSError, ValueError, TypeError, KeyError) as current_inventory_error:
        return [], '모델 파일 보유량 조회 실패: ' + str(current_inventory_error)


def open_hermes_session_job(hermes_job_identifier):
    """세션에서 선택한 작업을 기존 작업 상세에 연결한다."""
    if not hermes_job_identifier:
        raise gr.Error('먼저 세션 작업을 선택하세요.')
    hermes_status_text, hermes_answer_text, hermes_diff_text, hermes_log_text, hermes_result_record, hermes_original_prompt = refresh_hermes_work_status(hermes_job_identifier)
    return hermes_job_identifier, hermes_status_text, hermes_answer_text, hermes_diff_text, hermes_log_text, hermes_result_record, hermes_original_prompt, gr.update(open=True)


def recover_hermes_session_request(hermes_session_identifier):
    """작업 연결이 확인되지 않은 마지막 요청의 원래 입력을 복원한다."""
    if not hermes_session_identifier:
        raise gr.Error('먼저 세션을 선택하세요.')
    try:
        hermes_session_record = execute_remote_management_command('hermes-agent', 'hermes-session-read', {'session_id': hermes_session_identifier})
        hermes_pending_record = next((current_message_record for current_message_record in reversed(hermes_session_record['messages']) if not current_message_record.get('job_id')), None)
        if hermes_pending_record is None:
            raise ValueError('연결 확인이 필요한 메시지가 없습니다. 대화 상태를 확인하세요.')
        return hermes_pending_record['request_id'], hermes_pending_record['text'], '\n'.join(hermes_pending_record.get('verification_modules', [])), '저장된 원래 입력을 복원했습니다. 확인 후 같은 요청을 다시 접수하세요.'
    except Exception as hermes_request_error:
        raise gr.Error('요청 복원 실패: ' + str(hermes_request_error)) from hermes_request_error


def submit_hermes_session_request(hermes_session_identifier, hermes_request_identifier, hermes_prompt_text, hermes_verification_text=''):
    """기존 GPU 확인 뒤 세션 메시지를 중복 방지 식별자로 접수한다."""
    try:
        hermes_request_record = {'session_id': hermes_session_identifier, 'request_id': hermes_request_identifier, 'prompt': hermes_prompt_text}
        hermes_verification_modules = [current_module_name.strip() for current_module_name in (hermes_verification_text or '').splitlines() if current_module_name.strip()]
        if hermes_verification_modules:
            hermes_request_record['verification_modules'] = hermes_verification_modules
        hermes_submit_record = execute_remote_management_command('hermes-agent', 'hermes-session-submit', hermes_request_record)
        hermes_submit_message = ('기존 접수 확인' if hermes_submit_record.get('duplicate') else 'GPU 대기열에 등록했습니다.')
        if hermes_submit_record.get('context_truncated'):
            hermes_submit_message += ' · 이전 문맥 일부만 전달'
        return hermes_submit_record['job_id'], hermes_submit_message, uuid.uuid4().hex, gr.update(active=True)
    except Exception as hermes_request_error:
        raise gr.Error('메시지 접수 확인 실패: ' + str(hermes_request_error) + ' · 입력과 식별자를 유지한 채 다시 확인하세요.') from hermes_request_error


def read_hermes_management_summary():
    """공용 관측을 표시하며 조회 실패를 준비 또는 유휴로 오인하지 않는다."""
    try:
        current_snapshot_record = execute_remote_management_command('hermes-agent', 'hermes-management-status', {})
        current_model_record = current_snapshot_record['model']
        current_gpu_record = current_snapshot_record['gpu']
        current_queue_record = current_snapshot_record['queue']
        current_capacity_record = current_snapshot_record.get('memory_capacity', {})
        current_reservation_record = current_snapshot_record.get('reservations', {})
        current_recent_jobs = current_snapshot_record.get('recent_hermes_jobs', {})
        current_generator_record = current_snapshot_record.get('generators', {}).get('kimodo', {})
        current_generator_model = current_generator_record.get('model', {})
        current_generator_active = current_generator_record.get('active', {})
        current_model_text = current_model_record.get('message', '조회 불가') if current_model_record.get('status') == 'available' else '조회 불가'
        current_queue_text = str(len(current_queue_record['jobs'])) + '건' if current_queue_record.get('status') == 'available' else '조회 불가'
        current_generator_text = ('준비됨' if current_generator_model.get('ready') else '준비 필요') if current_generator_model.get('status') == 'available' else '조회 불가'
        if current_generator_active.get('status')=='available':
            current_active_text=('기록상 대기·실행 '+str(current_generator_active.get('count'))+'건 · 최근 '+str(current_generator_active.get('id'))) if current_generator_active.get('running') else '확인된 대기·실행 기록 없음'
            if current_generator_active.get('unknown_count',0):
                current_active_text+=' · 상태 확인 불가 '+str(current_generator_active['unknown_count'])+'건'
        else:
            current_active_text='조회 불가'
        current_capacity_text = (str(current_capacity_record['domain']).upper() + ' 여유 ' + str(current_capacity_record['pool_available_mib']) + ' / 필요 ' + str(current_capacity_record['required_mib']) + ' MiB · 호스트 여유 ' + str(current_capacity_record['host_available_mib']) + ' MiB · ' + ('메모리 기준 충족' if current_capacity_record.get('capacity_sufficient') else '메모리 대기')) if current_capacity_record.get('status') == 'available' else '조회 불가'
        current_reservation_text = (str(len(current_reservation_record.get('records', []))) + '건' + (' 이상' if current_reservation_record.get('truncated') else '') + (' · 확인 불가 기록 포함' if any(current_record.get('state') == 'unknown' for current_record in current_reservation_record.get('records', [])) else '') + (' · 종료 확인이 필요한 예약 포함' if any(current_record.get('state') == 'cleanup_unverified' for current_record in current_reservation_record.get('records', [])) else '') + (' · 작가 작업자 리더 생존 확인' if any(current_record.get('state') == 'cleanup_unverified' and current_record.get('worker_leader') == 'verified_running' for current_record in current_reservation_record.get('records', [])) else '')) if current_reservation_record.get('status') == 'available' else '조회 불가'
        current_jobs_text = (str(len(current_recent_jobs.get('jobs', []))) + '건' + (' (최근 10건)' if current_recent_jobs.get('truncated') else '')) if current_recent_jobs.get('status') == 'available' else '조회 불가'
        return 'GPU 예약 기록: ' + current_reservation_text + ' · 최근 Hermes 작업: ' + current_jobs_text + ' · 메모리: ' + current_capacity_text + ' (다른 예약·순서 제외) · Kimodo: ' + current_generator_text + ' · ' + current_active_text + ' · Hermes 모델: ' + current_model_text + ' · GPU: ' + str(current_gpu_record.get('status', 'unavailable')) + ' · 대기: ' + current_queue_text + ' · 확인: ' + current_snapshot_record['queried_at'] + ' (GPU 측정은 짧게 캐시될 수 있음)'
    except Exception as current_status_error:
        return '관리 상태 조회 실패 · ' + str(current_status_error)


def review_hermes_writer_request(current_mode_value,current_prompt_text,current_request_identifier):
    from generators.writer_agent.jobs import validate_job_request
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    try:
        if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
            raise ValueError('접수 ID 형식 오류')
        current_request_value={'mode':current_mode_value,'prompt':current_prompt_text or ''}
        validate_job_request(current_request_value)
        current_review_value={'request_id':current_request_identifier,'request':current_request_value}
        return current_review_value,f'접수 ID: {current_request_identifier} · 작업: {current_mode_value} · 지시: {current_prompt_text or "없음"}', '작업 내용을 검토한 뒤 GPU 대기열 접수를 확인하세요.',gr.update(interactive=True)
    except (ValueError,TypeError) as current_review_error:
        return None,'','작가 입력 확인 실패: '+str(current_review_error),gr.update(interactive=False)


def submit_hermes_writer_reviewed(current_review_value,current_mode_value,current_prompt_text,current_request_identifier):
    current_expected_value={'request_id':current_request_identifier,'request':{'mode':current_mode_value,'prompt':current_prompt_text or ''}}
    if current_review_value!=current_expected_value:
        raise gr.Error('작가 입력이 바뀌었습니다. 다시 검토하세요.')
    current_result_value=execute_remote_management_command('hermes-agent','hermes-delegate-writer',current_review_value)
    if current_result_value.get('state')=='unknown':
        return '', '작가 접수 결과 확인 필요 · 작가 AI 이력을 확인하고 자동 재접수하지 마세요.'
    if current_result_value.get('state')!='accepted' or not isinstance(current_result_value.get('job_id'),str):
        raise gr.Error('작가 접수 응답 오류 · 같은 ID를 유지하세요.')
    return current_result_value['job_id'],'작가 작업 접수 · 완료와 제안 검토는 별도로 확인하세요.'


def read_hermes_writer_result(current_request_identifier):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-writer-status',{'request_id':current_request_identifier})
    current_receipt_value=current_status_value['receipt']
    if current_receipt_value.get('state')=='not_found':
        return '', '작가 접수 기록이 없습니다.',None
    if current_receipt_value.get('state')=='unknown':
        return '', '작가 접수 결과 확인 필요 · 작가 AI 이력을 확인하세요.',None
    current_job_value=current_status_value.get('job',{})
    return current_receipt_value['job_id'],'작가 작업 상태: '+str(current_job_value.get('stage','unknown'))+(' · '+current_job_value['failure_reason'] if current_job_value.get('failure_reason') else ''),current_job_value


def list_hermes_writer_choices():
    current_history_value=execute_remote_management_command('hermes-agent','hermes-writer-history',{})
    current_choice_values=[(item['request_id']+' · '+item['state'],item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values,value=None),'최근 작가 위임 '+str(len(current_choice_values))+'건 · 손상된 기록은 제외됩니다.'


def review_hermes_writer_apply(current_writer_identifier,current_apply_identifier,current_confirmation_value):
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if current_confirmation_value is not True:
        raise gr.Error('작가 AI 화면에서 전체 변경과 근거를 확인한 뒤 체크하세요.')
    if not isinstance(current_apply_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_apply_identifier):
        raise gr.Error('적용 접수 ID 형식 오류')
    current_status_value=execute_remote_management_command('hermes-agent','hermes-writer-status',{'request_id':current_writer_identifier})
    current_receipt_value=current_status_value.get('receipt',{})
    current_job_value=current_status_value.get('job',{})
    if (current_receipt_value.get('state')!='accepted' or current_job_value.get('stage')!='review' or current_job_value.get('truncated') is not False
            or not current_job_value.get('proposal_hash') or not current_job_value.get('changes')):
        raise gr.Error('전체 변경이 확인되는 미적용 작가 제안이 필요합니다.')
    current_review_value={'request_id':current_apply_identifier,'writer_request_id':current_writer_identifier,'job_id':current_receipt_value['job_id'],'proposal_hash':current_job_value['proposal_hash']}
    current_summary_value='작가 작업 '+current_receipt_value['job_id']+' · 변경 문서 '+str(len(current_job_value['changes']))+'개 · 제안 해시 '+current_job_value['proposal_hash']+' · 확인 후 원본이 변경됩니다.'
    return current_review_value,current_job_value,gr.update(visible=True),current_summary_value


def submit_hermes_writer_apply(current_review_value,current_writer_identifier,current_apply_identifier,current_confirmation_value):
    if not isinstance(current_review_value,dict) or current_confirmation_value is not True or current_review_value.get('request_id')!=current_apply_identifier or current_review_value.get('writer_request_id')!=current_writer_identifier:
        raise gr.Error('확인 또는 적용 대상이 바뀌었습니다. 다시 검토하세요.')
    current_result_value=execute_remote_management_command('hermes-agent','hermes-writer-apply',current_review_value)
    if current_result_value.get('state')=='unknown':
        return None,gr.update(visible=False),'적용 결과 확인 필요 · 원본과 작가 AI 상태를 확인하고 자동 재적용하지 마세요.'
    if current_result_value.get('state')!='completed':
        raise gr.Error('작가 적용 응답 확인 실패 · 같은 적용 접수 ID를 유지하세요.')
    return None,gr.update(visible=False),'작가 제안을 원본에 적용했습니다. 다음 작업 전 문서 색인을 갱신하세요.'


def list_hermes_writer_apply_choices():
    current_history_value=execute_remote_management_command('hermes-agent','hermes-writer-apply-history',{})
    current_choice_values=[(item['request_id']+' · '+item['job_id']+' · '+item['state'],item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values,value=None),'최근 작가 적용 '+str(len(current_choice_values))+'건 · 손상된 기록은 제외됩니다.'


def read_hermes_writer_apply_receipt(current_apply_identifier):
    current_receipt_value=execute_remote_management_command('hermes-agent','hermes-writer-apply-status',{'request_id':current_apply_identifier})
    if current_receipt_value.get('state')=='not_found':
        return '적용 접수 기록이 없습니다.'
    if current_receipt_value.get('state')=='unknown':
        return '적용 결과 확인 필요 · 원본과 작가 AI 상태를 확인하고 자동 재적용하지 마세요.'
    return '작가 작업 '+current_receipt_value['job_id']+' · 적용 완료 · 다음 작업 전 색인을 갱신하세요.'


def load_hermes_translation_proposal(current_job_identifier):
    """완료된 번역 제안을 검토 입력으로 불러오되 접수하지 않는다."""
    if not current_job_identifier:
        raise gr.Error('먼저 세션 작업을 선택하세요.')
    current_proposal_value=execute_remote_management_command('hermes-agent','hermes-translation-proposal',{'id':current_job_identifier})['proposal']
    current_glossary_text='\n'.join(item['source']+' => '+item['target'] for item in current_proposal_value['glossary'])
    return current_proposal_value['text'],current_proposal_value['target_language'],current_glossary_text,uuid.uuid4().hex,None,'','제안을 불러왔습니다. 원문과 목표 언어·용어를 확인하고 다시 검토하세요.',gr.update(interactive=False)


def review_hermes_translation_request(current_source_text,current_target_language,current_glossary_text,current_request_identifier):
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    from tools.review.domains.translation.service import validate_translation_submission
    from tools.review.ui.gradio.prompt_translation_app import parse_translation_glossary
    try:
        if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
            raise ValueError('접수 ID 형식 오류')
        current_request_value={'text':current_source_text,'target_language':current_target_language,'glossary':parse_translation_glossary(current_glossary_text)}
        validate_translation_submission(current_request_value)
        current_review_value={'request_id':current_request_identifier,'request':current_request_value}
        return current_review_value, f'접수 ID: {current_request_identifier} · 목표 언어: {current_target_language} · 원문 {len(current_source_text)}자 · 확인 용어 {len(current_request_value["glossary"])}개', '번역 내용과 용어를 확인한 뒤 GPU 대기열 접수를 진행하세요.', gr.update(interactive=True)
    except (ValueError,TypeError) as current_review_error:
        return None,'','번역 입력 확인 실패: '+str(current_review_error),gr.update(interactive=False)


def submit_hermes_translation_reviewed(current_review_value,current_source_text,current_target_language,current_glossary_text,current_request_identifier):
    from tools.review.ui.gradio.prompt_translation_app import parse_translation_glossary
    current_expected_value={'request_id':current_request_identifier,'request':{'text':current_source_text,'target_language':current_target_language,'glossary':parse_translation_glossary(current_glossary_text)}}
    if current_review_value!=current_expected_value:
        raise gr.Error('번역 입력이 바뀌었습니다. 다시 검토하세요.')
    current_result_value=execute_remote_management_command('hermes-agent','hermes-delegate-translation',current_review_value)
    if current_result_value.get('state')=='unknown':
        return '', '번역 접수 결과 확인 필요 · 이력을 확인하고 자동 재접수하지 마세요.'
    if current_result_value.get('state')!='accepted' or not isinstance(current_result_value.get('job_id'),str):
        raise gr.Error('번역 접수 응답 오류 · 같은 ID를 유지하세요.')
    return current_result_value['job_id'],'번역 접수 완료 · 실제 작업 완료와 결과 검토는 별도로 확인하세요.'


def read_hermes_translation_result(current_request_identifier):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-translation-status',{'request_id':current_request_identifier})
    current_receipt_value=current_status_value['receipt']
    if current_receipt_value.get('state')=='not_found':
        return '', '번역 접수 기록이 없습니다.', None
    if current_receipt_value.get('state')=='unknown':
        return '', '번역 접수 결과 확인 필요 · 번역기 이력을 확인하세요.', None
    current_job_value=current_status_value.get('job',{})
    return current_receipt_value['job_id'],'번역 작업 상태: '+str(current_job_value.get('status','unknown'))+(' · '+current_job_value['failure_reason'] if current_job_value.get('failure_reason') else ''),current_job_value.get('result')


def list_hermes_translation_choices():
    current_history_value=execute_remote_management_command('hermes-agent','hermes-translation-history',{})
    current_choice_values=[(item['request_id']+' · '+item['state'],item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values,value=None),'최근 번역 위임 '+str(len(current_choice_values))+'건 · 손상된 기록은 제외됩니다.'


def preview_hermes_writer_reservation_recovery(current_job_identifier):
    try:
        current_result_value=execute_remote_management_command('hermes-agent','hermes-writer-reservation-preview',{'job_id':current_job_identifier})
        return current_result_value, current_result_value['reason']
    except Exception as current_preview_error:
        return None,'작가 예약 확인 실패: '+str(current_preview_error)


def review_hermes_writer_reservation_recovery(current_job_identifier,current_request_identifier):
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):raise gr.Error('정리 접수 ID 형식 오류')
    current_result_value=execute_remote_management_command('hermes-agent','hermes-writer-reservation-preview',{'job_id':current_job_identifier})
    if current_result_value.get('recoverable') is not True:
        return None,current_result_value,gr.update(visible=False),current_result_value.get('reason','예약을 확인할 수 없습니다.')
    current_review_value={'request_id':current_request_identifier,'job_id':current_job_identifier,'review_sha256':current_result_value['preview_sha256']}
    return current_review_value,current_result_value,gr.update(visible=True),current_result_value['reason']


def submit_hermes_writer_reservation_recovery(current_review_value,current_request_identifier,current_job_identifier,current_outside_checked):
    if not isinstance(current_review_value,dict) or current_review_value.get('request_id')!=current_request_identifier or current_review_value.get('job_id')!=current_job_identifier or current_outside_checked is not True:
        raise gr.Error('대상과 별도 그룹 GPU 프로세스 확인을 다시 확인하세요.')
    try:
        current_result_value=execute_remote_management_command('hermes-agent','hermes-writer-reservation-recover',{**current_review_value,'outside_processes_checked':True})
    except Exception:
        return None,gr.update(visible=False),'정리 결과 확인 필요 · 접수를 확인하고 자동 재실행하지 마세요.'
    if current_result_value.get('state')=='completed':return None,gr.update(visible=False),'검증된 그룹을 종료하고 예약을 해제했습니다. 작업 상태와 GPU 사용량을 확인하세요.'
    return None,gr.update(visible=False),'정리 결과 확인 필요 · 접수를 확인하고 자동 재실행하지 마세요.'


def read_hermes_writer_reservation_recovery_receipt(current_request_identifier):
    current_result_value=execute_remote_management_command('hermes-agent','hermes-writer-reservation-receipt',{'request_id':current_request_identifier})
    return {'not_found':'정리 접수 기록이 없습니다.','unknown':'정리 결과 확인 필요 · 예약과 작업 상태를 확인하세요.','completed':'검증된 그룹 정리와 예약 해제가 기록됐습니다.'}.get(current_result_value.get('state'),'정리 접수를 확인할 수 없습니다.')


def review_hermes_writer_cancellation(current_request_identifier,current_job_identifier):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-writer-status',{'request_id':current_request_identifier})
    if current_status_value.get('receipt',{}).get('job_id')!=current_job_identifier or not current_job_identifier:
        raise gr.Error('접수 기록과 작가 작업 ID가 일치하지 않습니다.')
    if current_status_value.get('job',{}).get('stage') not in ('queued','preparing','indexing','searching','reasoning'):
        raise gr.Error('대기 또는 실행 중인 작가 작업만 중지할 수 있습니다.')
    return {'request_id':current_request_identifier,'job_id':current_job_identifier},gr.update(visible=True),'작가 작업 '+current_job_identifier+'에 중지를 요청합니다. 실제 종료는 상태에서 확인하세요.'


def submit_hermes_writer_cancellation(current_review_value,current_request_identifier,current_job_identifier):
    if current_review_value!={'request_id':current_request_identifier,'job_id':current_job_identifier}:raise gr.Error('중지 대상이 바뀌었습니다. 다시 확인하세요.')
    return submit_hermes_checked_cancellation('hermes-writer-cancel',current_review_value,current_job_identifier)


def review_hermes_translation_cancellation(current_request_identifier,current_job_identifier):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-translation-status',{'request_id':current_request_identifier})
    if current_status_value.get('receipt',{}).get('job_id')!=current_job_identifier or not current_job_identifier:
        raise gr.Error('접수 기록과 번역 작업 ID가 일치하지 않습니다.')
    return {'request_id':current_request_identifier,'job_id':current_job_identifier},gr.update(visible=True),'번역 작업 '+current_job_identifier+'에 중지를 요청합니다. 실제 종료는 상태에서 확인하세요.'


def submit_hermes_checked_cancellation(current_command_name,current_review_value,current_job_identifier):
    """전송 뒤 응답이 불확실하면 확인창을 닫고 실제 상태 확인을 안내한다."""
    try:
        current_response_value=execute_remote_management_command('hermes-agent',current_command_name,current_review_value)
        if not isinstance(current_response_value,dict) or current_response_value.get('cancel_requested') is not True or current_response_value.get('job_id')!=current_job_identifier:
            raise ValueError('중지 접수 응답 확인 불가')
    except Exception:
        return None,gr.update(visible=False),'중지 요청 결과 확인 필요 · 같은 접수 ID와 작업 ID로 상태를 확인하고 다시 요청하기 전에 실제 종료 여부를 확인하세요.'
    return None,gr.update(visible=False),'중지를 요청했습니다. 실제 종료는 상태에서 확인하세요.'


def submit_hermes_translation_cancellation(current_review_value,current_request_identifier,current_job_identifier):
    if current_review_value!={'request_id':current_request_identifier,'job_id':current_job_identifier}:
        raise gr.Error('중지 대상이 바뀌었습니다. 다시 확인하세요.')
    return submit_hermes_checked_cancellation('hermes-translation-cancel',current_review_value,current_job_identifier)


def load_hermes_video_proposal(current_job_identifier):
    """제안을 기본 설정으로 옮기고 이전 첨부를 비워 사용자가 직접 선택하게 한다."""
    import json
    if not current_job_identifier:
        raise gr.Error('먼저 세션 작업을 선택하세요.')
    current_proposal_value=execute_remote_management_command('hermes-agent','hermes-video-proposal',{'id':current_job_identifier})['proposal']
    current_service_name=current_proposal_value['service']
    current_mode_value=current_proposal_value['mode']
    current_settings_value=json.loads(default_hermes_video_settings(current_service_name))
    if current_service_name!='dwpose':
        current_settings_value['prompt']=current_proposal_value['prompt']
    if current_service_name=='wan22-vace':
        current_settings_value['mode']=current_mode_value
    current_attachment_hints={('dwpose','image'):'832×480 PNG 한 장',('wan22-animate2','motion'):'832×480 참조 PNG 한 장과 동작 RGB MP4',
        ('wan22-fun-control','frames'):'외형 참조 PNG와 출력 프레임 수만큼의 제어 PNG',('wan22-fun-control','pose_video'):'외형 참조 PNG와 포즈 MP4',('wan22-fun-control','driving_video'):'외형 참조 PNG와 동작 RGB MP4',
        ('wan22-vace','text'):'첨부 없음',('wan22-vace','reference'):'참조 PNG 한 장',('wan22-vace','first_frame'):'첫 프레임 PNG 한 장',
        ('wan22-vace','video_edit'):'참조 PNG와 편집 MP4·마스크 MP4',('wan22-vace','video_condition'):'참조 PNG와 조건 MP4',('wan22-vace','pose'):'참조 PNG와 포즈 MP4'}
    current_status_text='제안을 불러왔습니다. 이전 첨부는 비웠습니다. 필요 첨부: '+current_attachment_hints[(current_service_name,current_mode_value)]+'. 프레임·스텝 등은 기본값이므로 검토하고 입력을 검증하세요.'
    return (current_service_name,json.dumps(current_settings_value,ensure_ascii=False,indent=2),None,None,None,None,None,uuid.uuid4().hex,None,'',current_status_text,gr.update(interactive=False))


def default_hermes_video_settings(current_service_name):
    import json
    from generators.wan_fun.contracts import FUN_DEFAULT_SETTINGS
    from generators.wan_vace.contracts import VACE_DEFAULT_SETTINGS
    if current_service_name=='dwpose':
        current_settings_value={'action':'generate','images':[],'pose_include_hands':False,'pose_include_face':False}
    elif current_service_name=='wan22-animate2':
        current_settings_value={'action':'generate','images':[],'prompt':'','frames':21,'steps':40,'seed':42,'width':832,'height':480}
    elif current_service_name=='wan22-fun-control':
        current_settings_value={'action':'generate','prompt':'','negative_prompt':'','images':[],'width':832,'height':480,'control_type':'pose',**FUN_DEFAULT_SETTINGS}
    elif current_service_name=='wan22-vace':
        current_settings_value={'action':'generate','mode':VACE_DEFAULT_SETTINGS['mode'],'prompt':'','negative_prompt':'','images':[],'width':832,'height':480,**{key:value for key,value in VACE_DEFAULT_SETTINGS.items() if key!='mode'}}
    else:
        raise gr.Error('지원하지 않는 동작·영상 서비스')
    return json.dumps(current_settings_value,ensure_ascii=False,indent=2)


def build_hermes_video_request(current_service_name,current_settings_text,current_image_files,current_driving_video,current_pose_video,current_edit_video,current_edit_mask,current_request_identifier):
    import base64
    from tools.review.common.management_gateway import parse_management_request_json
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    from tools.review.domains.hermes_agent.video_operations import validate_hermes_video_request
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
        raise ValueError('접수 ID 형식 오류')
    current_settings_value=parse_management_request_json(current_settings_text)
    if not isinstance(current_settings_value,dict):
        raise ValueError('영상 설정은 JSON 객체여야 합니다.')
    current_request_value=dict(current_settings_value)
    if current_request_value.get('images') not in (None,[]):
        raise ValueError('참조 이미지는 설정 JSON이 아닌 파일 첨부로 입력하세요.')
    if any(current_field_name in current_request_value for current_field_name in ('driving_video','pose_video','edit_video','edit_mask')):
        raise ValueError('영상과 마스크는 설정 JSON이 아닌 파일 첨부로 입력하세요.')
    current_file_values=list(current_image_files or [])
    current_attachment_values=[('driving_video',current_driving_video),('pose_video',current_pose_video),('edit_video',current_edit_video),('edit_mask',current_edit_mask)]
    current_all_files=current_file_values+[current_file_value for _,current_file_value in current_attachment_values if current_file_value is not None]
    if any(not isinstance(current_file_value,bytes) for current_file_value in current_all_files):
        raise ValueError('첨부는 업로드한 파일이어야 합니다.')
    if sum(len(current_file_value) for current_file_value in current_all_files)>24*1024*1024:
        raise ValueError('화면 첨부 파일 합계는 24MiB 이하여야 합니다.')
    if current_file_values:
        current_request_value['images']=[base64.b64encode(current_file_value).decode('ascii') for current_file_value in current_file_values]
    for current_field_name,current_file_value in current_attachment_values:
        if current_file_value is not None:
            current_request_value[current_field_name]=base64.b64encode(current_file_value).decode('ascii')
    validate_hermes_video_request(current_service_name,current_request_value)
    return {'request_id':current_request_identifier,'service':current_service_name,'request':current_request_value}


def review_hermes_video_request(current_service_name,current_settings_text,current_image_files,current_driving_video,current_pose_video,current_edit_video,current_edit_mask,current_request_identifier):
    import hashlib
    try:
        current_review_value=build_hermes_video_request(current_service_name,current_settings_text,current_image_files,current_driving_video,current_pose_video,current_edit_video,current_edit_mask,current_request_identifier)
        current_attachment_values=[('참조 이미지 '+str(current_image_index),current_image_value) for current_image_index,current_image_value in enumerate(current_image_files or [],1)]
        current_attachment_values.extend((current_label_value,current_file_value) for current_label_value,current_file_value in (('동작 RGB 영상',current_driving_video),('포즈 영상',current_pose_video),('편집·조건 영상',current_edit_video),('편집 마스크',current_edit_mask)) if current_file_value is not None)
        current_attachment_lines=[current_label_value+' · '+str(len(current_file_value))+'바이트 · SHA-256 '+hashlib.sha256(current_file_value).hexdigest() for current_label_value,current_file_value in current_attachment_values]
        current_settings_value=current_review_value['request']
        current_summary_value=f'서비스: {current_service_name} · 접수 ID: {current_request_identifier} · 첨부 {len(current_attachment_values)}개 · 프레임: {current_settings_value.get("frames",1)} · 스텝: {current_settings_value.get("steps",1)}'
        current_summary_value+='  \n'+('  \n'.join(current_attachment_lines) if current_attachment_lines else '첨부 없음')
        current_summary_value+='  \n설정 JSON과 첨부를 확인하세요. 영상 작업은 GPU 메모리와 실행 시간이 클 수 있습니다.'
        return current_review_value,current_summary_value,'입력 검증 후 GPU 대기열 접수를 확인하세요.',gr.update(interactive=True)
    except (ValueError,TypeError,OSError,KeyError) as current_review_error:
        return None,'','동작·영상 입력 확인 실패: '+str(current_review_error),gr.update(interactive=False)


def submit_hermes_video_reviewed(current_review_value,current_service_name,current_settings_text,current_image_files,current_driving_video,current_pose_video,current_edit_video,current_edit_mask,current_request_identifier):
    current_expected_value=build_hermes_video_request(current_service_name,current_settings_text,current_image_files,current_driving_video,current_pose_video,current_edit_video,current_edit_mask,current_request_identifier)
    if current_review_value!=current_expected_value:
        raise gr.Error('설정이나 첨부가 바뀌었습니다. 다시 검토하세요.')
    current_result_value=execute_remote_management_command('hermes-agent','hermes-delegate-video',current_review_value)
    if current_result_value.get('state')=='unknown':
        return '', '접수 결과 확인 필요 · 해당 생성기 이력을 확인하고 자동 재접수하지 마세요.'
    if current_result_value.get('state')!='accepted' or not isinstance(current_result_value.get('job_id'),str):
        raise gr.Error('동작·영상 접수 응답 오류 · 같은 ID를 유지하세요.')
    return current_result_value['job_id'],'작업 접수 완료 · 완료와 결과는 별도로 확인하세요.'


def read_hermes_video_result(current_request_identifier,current_service_name):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-video-status',{'request_id':current_request_identifier,'service':current_service_name})
    current_receipt_value=current_status_value['receipt']
    if current_receipt_value.get('state')=='not_found':
        return '', '해당 서비스의 접수 기록이 없습니다.'
    if current_receipt_value.get('state')=='unknown':
        return '', '접수 결과 확인 필요 · 해당 생성기 이력을 확인하세요.'
    current_job_value=current_status_value.get('job',{})
    current_links_text=''.join(' · ['+label+']('+current_job_value[field]+')' for field,label in (('video','영상'),('image','첫 프레임'),('download','프레임 ZIP')) if current_job_value.get(field))
    current_result_state=current_job_value.get('result_status')
    current_result_notice={'partial':' · 결과 일부만 확인됨','unavailable':' · 완료 기록은 있으나 결과 파일 확인 불가'}.get(current_result_state,'')
    return current_receipt_value['job_id'],'작업 상태: '+str(current_job_value.get('status','unknown'))+current_result_notice+(' · '+current_job_value['failure_reason'] if current_job_value.get('failure_reason') else '')+current_links_text+' · [생성기 이력](/management/frame/'+current_service_name+'-generator/) · 상태 조회 시 기존 복구가 따를 수 있습니다.'


def list_hermes_video_choices(current_service_name):
    current_history_value=execute_remote_management_command('hermes-agent','hermes-video-history',{'service':current_service_name})
    current_choice_values=[(item['request_id']+' · '+item['state'],item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values,value=None),'이 서비스의 최근 접수 '+str(len(current_choice_values))+'건 · 손상된 기록은 제외됩니다.'


def review_hermes_video_cancellation(current_request_identifier,current_service_name,current_job_identifier):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-video-status',{'request_id':current_request_identifier,'service':current_service_name})
    if current_status_value.get('receipt',{}).get('job_id')!=current_job_identifier or not current_job_identifier:
        raise gr.Error('접수 기록과 동작·영상 작업 ID가 일치하지 않습니다.')
    return {'request_id':current_request_identifier,'service':current_service_name,'job_id':current_job_identifier},gr.update(visible=True),current_service_name+' 작업 '+current_job_identifier+'에 중지를 요청합니다. 실제 종료는 상태에서 확인하세요.'


def submit_hermes_video_cancellation(current_review_value,current_request_identifier,current_service_name,current_job_identifier):
    if current_review_value!={'request_id':current_request_identifier,'service':current_service_name,'job_id':current_job_identifier}:
        raise gr.Error('중지 대상이 바뀌었습니다. 다시 확인하세요.')
    return submit_hermes_checked_cancellation('hermes-video-cancel',current_review_value,current_job_identifier)


def load_hermes_audio_proposal(current_job_identifier):
    """완료된 오디오 제안을 검토 입력으로 불러오되 접수하지 않는다."""
    if not current_job_identifier:
        raise gr.Error('먼저 세션 작업을 선택하세요.')
    current_proposal_value=execute_remote_management_command('hermes-agent','hermes-audio-proposal',{'id':current_job_identifier})['proposal']
    current_request_value=current_proposal_value['request']
    return (current_proposal_value['service'],current_request_value['prompt'],current_request_value.get('lyrics',''),
            current_request_value.get('duration_seconds',30),current_request_value['loop_request'],current_request_value['seed'],uuid.uuid4().hex,
            None,'','제안을 불러왔습니다. 서비스·가사·길이와 가정을 확인하고 다시 검토하세요.',gr.update(interactive=False))


def build_hermes_audio_request(current_service_name,current_prompt_text,current_lyrics_text,current_duration_value,current_loop_value,current_seed_value,current_request_identifier):
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    from tools.review.domains.hermes_agent.audio_operations import validate_hermes_audio_request
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
        raise ValueError('접수 ID 형식 오류')
    current_request_value={'action':'generate','prompt':current_prompt_text,'seed':current_seed_value,'loop_request':current_loop_value}
    if current_service_name=='music-heartmula':
        current_request_value.update(lyrics=current_lyrics_text or '',duration_seconds=current_duration_value)
    elif current_service_name=='sfx-dasheng-audiogen' and current_lyrics_text:
        raise ValueError('효과음에는 가사를 사용할 수 없습니다.')
    validate_hermes_audio_request(current_service_name,current_request_value)
    return {'request_id':current_request_identifier,'service':current_service_name,'request':current_request_value}


def review_hermes_audio_request(current_service_name,current_prompt_text,current_lyrics_text,current_duration_value,current_loop_value,current_seed_value,current_request_identifier):
    try:
        current_review_value=build_hermes_audio_request(current_service_name,current_prompt_text,current_lyrics_text,current_duration_value,current_loop_value,current_seed_value,current_request_identifier)
        current_length_text=(str(current_duration_value)+'초 최대 출력 상한 · 가사 '+str(len(current_lyrics_text or ''))+'자' if current_service_name=='music-heartmula' else '효과음 길이는 모델이 결정')
        return current_review_value,f'서비스: {current_service_name} · 접수 ID: {current_request_identifier} · {current_length_text} · 시드: {current_seed_value} · 반복 요청: {current_loop_value}  \
지시: {current_prompt_text}', '입력을 확인한 뒤 GPU 대기열 접수를 검토하세요.',gr.update(interactive=True)
    except (ValueError,TypeError,OSError) as current_review_error:
        return None,'','오디오 입력 확인 실패: '+str(current_review_error),gr.update(interactive=False)


def submit_hermes_audio_reviewed(current_review_value,current_service_name,current_prompt_text,current_lyrics_text,current_duration_value,current_loop_value,current_seed_value,current_request_identifier):
    current_expected_value=build_hermes_audio_request(current_service_name,current_prompt_text,current_lyrics_text,current_duration_value,current_loop_value,current_seed_value,current_request_identifier)
    if current_review_value!=current_expected_value:
        raise gr.Error('오디오 입력이 바뀌었습니다. 다시 검토하세요.')
    current_result_value=execute_remote_management_command('hermes-agent','hermes-delegate-audio',current_review_value)
    if current_result_value.get('state')=='unknown':
        return '', '오디오 접수 결과 확인 필요 · 해당 생성기 이력을 확인하고 자동 재접수하지 마세요.'
    if current_result_value.get('state')!='accepted' or not isinstance(current_result_value.get('job_id'),str):
        raise gr.Error('오디오 접수 응답 오류 · 같은 ID를 유지하세요.')
    return current_result_value['job_id'],'오디오 작업 접수 완료 · 완료와 결과는 별도로 확인하세요.'


def read_hermes_audio_result(current_request_identifier,current_service_name):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-audio-status',{'request_id':current_request_identifier,'service':current_service_name})
    current_receipt_value=current_status_value['receipt']
    if current_receipt_value.get('state')=='not_found':
        return '', '해당 오디오 서비스의 접수 기록이 없습니다.'
    if current_receipt_value.get('state')=='unknown':
        return '', '오디오 접수 결과 확인 필요 · 해당 생성기 이력을 확인하세요.'
    current_job_value=current_status_value.get('job',{})
    current_audio_path=current_job_value.get('audio')
    current_result_notice=' · 완료 기록은 있으나 음원 링크 확인 불가' if current_job_value.get('result_status')=='unavailable' else ''
    return current_receipt_value['job_id'],'작업 상태: '+str(current_job_value.get('status','unknown'))+current_result_notice+(' · '+current_job_value['failure_reason'] if current_job_value.get('failure_reason') else '')+(' · [생성 음원 듣기]('+current_audio_path+')' if current_audio_path else '')+' · [생성기 이력](/management/frame/'+current_service_name+'/)'


def read_hermes_source_history_page(current_service_name,current_command_name,current_page_state=None,current_next_page=False):
    """서비스와 스냅샷을 고정하여 원본 이력을 페이지별로 표시한다."""
    try:
        current_request_value={'service':current_service_name,'limit':30}
        if current_next_page:
            if not isinstance(current_page_state,dict) or current_page_state.get('service')!=current_service_name or current_page_state.get('command')!=current_command_name or type(current_page_state.get('next_offset')) is not int or not isinstance(current_page_state.get('snapshot'),str):
                raise ValueError('서비스가 바뀌었거나 다음 페이지가 없습니다. 처음부터 조회하세요.')
            current_request_value.update(offset=current_page_state['next_offset'],snapshot=current_page_state['snapshot'])
        current_result_value=execute_remote_management_command('hermes-agent',current_command_name,current_request_value)
        current_source_labels={'job':'작업 상태 파일','index':'이전 색인','unavailable':'확인 불가'}
        current_rows_value=[[current_record['id'],current_record['recorded_status'],current_source_labels[current_record['status_source']]] for current_record in current_result_value['records']]
        current_next_offset=current_result_value['next_offset']
        current_next_state={'service':current_service_name,'command':current_command_name,'next_offset':current_next_offset,'snapshot':current_result_value['snapshot']}
        current_first_index=current_result_value['offset']+1 if current_rows_value else 0
        current_last_index=current_result_value['offset']+len(current_rows_value) if current_rows_value else 0
        current_status_text='전체 '+str(current_result_value['total'])+'건 중 '+str(current_first_index)+'–'+str(current_last_index)+'건 · 기록 상태입니다. 실제 결과와 작업 생존은 원 생성기에서 확인하세요.'
        if current_result_value.get('source_service') and current_result_value['source_service']!=current_service_name:
            current_status_text+=' · 실제 이력 서비스: '+current_result_value['source_service']+' (호환 경로)'
        if current_result_value['unavailable_count']:
            current_status_text+=' · 확인 불가 색인 '+str(current_result_value['unavailable_count'])+'건은 원 생성기에서 확인하세요.'
        return current_rows_value,current_status_text,current_next_state,gr.update(interactive=current_next_offset is not None)
    except Exception as current_history_error:
        return [],'원본 이력 조회 실패: '+str(current_history_error)+' · 처음부터 다시 조회하세요.',None,gr.update(interactive=False)


def read_hermes_generator_source_rows(current_service_name):
    return read_hermes_source_history_page(current_service_name,'hermes-generator-source-history')


def read_next_hermes_generator_source_rows(current_service_name,current_page_state):
    return read_hermes_source_history_page(current_service_name,'hermes-generator-source-history',current_page_state,True)


def read_hermes_audio_source_rows(current_service_name):
    return read_hermes_source_history_page(current_service_name,'hermes-audio-source-history')


def read_next_hermes_audio_source_rows(current_service_name,current_page_state):
    return read_hermes_source_history_page(current_service_name,'hermes-audio-source-history',current_page_state,True)


def clear_hermes_source_history():
    return [],'서비스가 바뀌었습니다. 원본 이력을 다시 조회하세요.',None,gr.update(interactive=False)


def list_hermes_audio_choices(current_service_name):
    current_history_value=execute_remote_management_command('hermes-agent','hermes-audio-history',{'service':current_service_name})
    current_choice_values=[(item['request_id']+' · '+item['state'],item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values,value=None),'이 서비스의 최근 접수 '+str(len(current_choice_values))+'건 · 손상된 기록은 제외됩니다.'


def review_hermes_audio_cancellation(current_request_identifier,current_service_name,current_job_identifier):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-audio-status',{'request_id':current_request_identifier,'service':current_service_name})
    if current_status_value.get('receipt',{}).get('job_id')!=current_job_identifier or not current_job_identifier:
        raise gr.Error('접수 기록과 오디오 작업 ID가 일치하지 않습니다.')
    return {'request_id':current_request_identifier,'service':current_service_name,'job_id':current_job_identifier},gr.update(visible=True),current_service_name+' 작업 '+current_job_identifier+'에 중지를 요청합니다. 실제 종료는 상태에서 확인하세요.'


def submit_hermes_audio_cancellation(current_review_value,current_request_identifier,current_service_name,current_job_identifier):
    if current_review_value!={'request_id':current_request_identifier,'service':current_service_name,'job_id':current_job_identifier}:
        raise gr.Error('중지 대상이 바뀌었습니다. 다시 확인하세요.')
    return submit_hermes_checked_cancellation('hermes-audio-cancel',current_review_value,current_job_identifier)


def load_hermes_default_face_reference():
    from importlib import import_module
    return import_module('generators.flux-expression.page.interface').load_default_face_reference()


def build_hermes_flux_expression_request(current_face_image,current_expression_name,current_additional_text,current_width_value,current_height_value,current_seed_value,current_request_identifier):
    import base64
    import io
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    from tools.review.domains.image.flux_expression_generation import FluxExpressionGenerationManager
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
        raise ValueError('접수 ID 형식 오류')
    if current_face_image is None:
        raise ValueError('얼굴 참조 이미지 1장이 필요합니다.')
    current_image_buffer=io.BytesIO()
    current_face_image.convert('RGB').save(current_image_buffer,format='PNG')
    current_request_value={'action':'generate','prompt':current_expression_name,'images':[base64.b64encode(current_image_buffer.getvalue()).decode('ascii')],'width':current_width_value,'height':current_height_value,'steps':16,'seed':current_seed_value,'tag':''}
    if current_additional_text and current_additional_text.strip():
        current_request_value['translation_source_ko']=current_additional_text.strip()
    FluxExpressionGenerationManager().validate_generation_request(current_request_value)
    return {'request_id':current_request_identifier,'service':'flux-expression','request':current_request_value}


def format_hermes_flux_reference_details(current_image_values):
    """실제로 접수할 PNG 바이트의 크기와 해시를 표시한다."""
    import base64
    import hashlib
    current_detail_values=[]
    for current_image_index,current_image_text in enumerate(current_image_values,1):
        current_image_bytes=base64.b64decode(current_image_text,validate=True)
        current_image_digest=hashlib.sha256(current_image_bytes).hexdigest()
        current_detail_values.append(f'참조 {current_image_index} · {len(current_image_bytes)}바이트 · PNG SHA-256: {current_image_digest}')
    return current_detail_values


def review_hermes_flux_expression_request(current_face_image,current_expression_name,current_additional_text,current_width_value,current_height_value,current_seed_value,current_request_identifier):
    try:
        current_review_value=build_hermes_flux_expression_request(current_face_image,current_expression_name,current_additional_text,current_width_value,current_height_value,current_seed_value,current_request_identifier)
        current_summary_lines=[f'접수 ID: {current_request_identifier} · 표정: {current_expression_name} · 크기: {current_width_value}×{current_height_value} · 시드: {current_seed_value} · 얼굴 참조: 1장', f'추가 지시: {current_additional_text or "없음"}']
        current_summary_lines.extend(format_hermes_flux_reference_details(current_review_value['request']['images']))
        return current_review_value,'  \n'.join(current_summary_lines),'얼굴 참조와 표정을 검토한 뒤 GPU 대기열 접수를 확인하세요.',gr.update(interactive=True)
    except (ValueError,TypeError,OSError) as current_review_error:
        return None,'','표정 입력 확인 실패: '+str(current_review_error),gr.update(interactive=False)


def match_hermes_flux_expression_confirmation(confirmed_input_values,current_input_values):
    try:
        if len(confirmed_input_values)!=8 or len(current_input_values)!=8:
            return False
        current_review_value=current_input_values[0]
        return current_review_value==confirmed_input_values[0] and current_review_value==build_hermes_flux_expression_request(*current_input_values[1:])
    except (ValueError,TypeError,OSError):
        return False


def submit_hermes_flux_expression_reviewed(current_review_value,current_face_image,current_expression_name,current_additional_text,current_width_value,current_height_value,current_seed_value,current_request_identifier):
    current_expected_value=build_hermes_flux_expression_request(current_face_image,current_expression_name,current_additional_text,current_width_value,current_height_value,current_seed_value,current_request_identifier)
    if current_review_value!=current_expected_value:
        raise gr.Error('표정 입력이나 얼굴 참조가 바뀌었습니다. 다시 검토하세요.')
    current_result_value=execute_remote_management_command('hermes-agent','hermes-delegate-flux-profile',current_review_value)
    if current_result_value.get('state')=='unknown':
        return '', '표정 접수 결과 확인 필요 · 표정 생성기 이력을 확인하고 자동 재접수하지 마세요.'
    if current_result_value.get('state')!='accepted' or not isinstance(current_result_value.get('job_id'),str):
        raise gr.Error('표정 생성 접수 응답 오류 · 같은 ID를 유지하세요.')
    return current_result_value['job_id'],'표정 생성 접수 완료 · 결과와 번역 검토는 표정 생성기에서 확인하세요.'


def build_hermes_flux_profile_request(current_profile_name,current_prompt_text,current_width_value,current_height_value,current_seed_value,current_first_image,current_second_image,current_request_identifier):
    import base64
    import io
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    from tools.review.domains.image.flux_image_generation import FluxImageGenerationManager
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
        raise ValueError('접수 ID 형식 오류')
    if current_first_image is None and current_second_image is not None:
        raise ValueError('두 번째 참조를 사용하려면 첫 번째 참조도 지정하세요.')
    current_image_values=[]
    for current_image_value in (current_first_image,current_second_image):
        if current_image_value is None:
            continue
        current_image_buffer=io.BytesIO()
        current_image_value.save(current_image_buffer,format='PNG')
        current_image_values.append(base64.b64encode(current_image_buffer.getvalue()).decode('ascii'))
    current_request_value={'action':'generate','prompt':current_prompt_text,'images':current_image_values,'width':current_width_value,'height':current_height_value,'steps':16,'seed':current_seed_value}
    FluxImageGenerationManager(current_profile_name).validate_generation_request(current_request_value)
    return {'request_id':current_request_identifier,'service':current_profile_name,'request':current_request_value}


def update_hermes_flux_profile_defaults(current_profile_name):
    from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
    if current_profile_name not in FLUX_IMAGE_PROFILE_RECORDS:
        raise gr.Error('등록된 FLUX 프로필이 아닙니다.')
    current_profile_value=FLUX_IMAGE_PROFILE_RECORDS[current_profile_name]
    return current_profile_value[2],current_profile_value[3]


def review_hermes_flux_profile_request(current_profile_name,current_prompt_text,current_width_value,current_height_value,current_seed_value,current_first_image,current_second_image,current_request_identifier):
    try:
        current_review_value=build_hermes_flux_profile_request(current_profile_name,current_prompt_text,current_width_value,current_height_value,current_seed_value,current_first_image,current_second_image,current_request_identifier)
        current_summary_lines=[f'프로필: {current_profile_name} · 접수 ID: {current_request_identifier} · 크기: {current_width_value}×{current_height_value} · 시드: {current_seed_value} · 참조: {len(current_review_value["request"]["images"])}장', f'지시: {current_prompt_text}']
        current_summary_lines.extend(format_hermes_flux_reference_details(current_review_value['request']['images']))
        current_summary_value='  \n'.join(current_summary_lines)
        return current_review_value,current_summary_value,'검토 후 GPU 대기열 접수를 확인하세요.',gr.update(interactive=True)
    except (ValueError,TypeError,OSError) as current_review_error:
        return None,'','입력 확인 실패: '+str(current_review_error),gr.update(interactive=False)


def match_hermes_flux_profile_confirmation(confirmed_input_values,current_input_values):
    try:
        if len(confirmed_input_values)!=9 or len(current_input_values)!=9:
            return False
        current_review_value=current_input_values[0]
        return current_review_value==confirmed_input_values[0] and current_review_value==build_hermes_flux_profile_request(*current_input_values[1:])
    except (ValueError,TypeError,OSError):
        return False


def submit_hermes_flux_profile_reviewed(current_review_value,current_profile_name,current_prompt_text,current_width_value,current_height_value,current_seed_value,current_first_image,current_second_image,current_request_identifier):
    current_expected_value=build_hermes_flux_profile_request(current_profile_name,current_prompt_text,current_width_value,current_height_value,current_seed_value,current_first_image,current_second_image,current_request_identifier)
    if current_review_value!=current_expected_value:
        raise gr.Error('생성기 입력이 바뀌었습니다. 다시 검토하세요.')
    current_result_value=execute_remote_management_command('hermes-agent','hermes-delegate-flux-profile',current_review_value)
    if current_result_value.get('state')=='unknown':
        return '', '접수 결과 확인 필요 · 해당 생성기 이력을 확인하고 자동 재접수하지 마세요.'
    if current_result_value.get('state')!='accepted' or not isinstance(current_result_value.get('job_id'),str):
        raise gr.Error('생성 접수 응답 오류 · 같은 ID를 유지하세요.')
    return current_result_value['job_id'],'생성 접수 완료 · 결과와 상세 로그는 해당 생성기 화면에서 확인하세요.'


def read_hermes_flux_profile_result(current_request_identifier,current_profile_name):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-flux-profile-status',{'request_id':current_request_identifier,'service':current_profile_name})
    current_receipt_value=current_status_value['receipt']
    if current_receipt_value.get('state')=='not_found':
        return '', '해당 프로필의 접수 기록이 없습니다.'
    if current_receipt_value.get('state')=='unknown':
        return '', '접수 결과 확인 필요 · 해당 생성기 이력을 확인하세요.'
    current_job_value=current_status_value.get('job',{})
    current_expected_path='/'+current_profile_name+'-generator/jobs/'+current_receipt_value['job_id']+'/result.png'
    current_image_link=' · [생성 이미지 보기]('+current_expected_path+')' if current_job_value.get('status')=='completed' and current_job_value.get('image')==current_expected_path else ''
    current_result_notice=' · 완료 기록은 있으나 이미지 링크 확인 불가' if current_job_value.get('result_status')=='unavailable' else ''
    return current_receipt_value['job_id'],'작업 상태: '+str(current_job_value.get('status','unknown'))+current_result_notice+(' · '+current_job_value['failure_reason'] if current_job_value.get('failure_reason') else '')+current_image_link+' · [해당 생성기 결과 확인](/management/frame/'+current_profile_name+'-generator/)'


def list_hermes_flux_profile_choices(current_profile_name):
    current_history_value=execute_remote_management_command('hermes-agent','hermes-flux-profile-history',{'service':current_profile_name})
    current_choice_values=[(item['request_id']+' · '+item['state'],item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values,value=None),'이 프로필의 최근 접수 '+str(len(current_choice_values))+'건 · 손상된 기록은 제외됩니다.'


def review_hermes_flux_profile_cancellation(current_request_identifier,current_profile_name,current_job_identifier):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-flux-profile-status',{'request_id':current_request_identifier,'service':current_profile_name})
    if current_status_value.get('receipt',{}).get('job_id')!=current_job_identifier or not current_job_identifier:
        raise gr.Error('접수 기록과 생성기 작업 ID가 일치하지 않습니다.')
    return {'request_id':current_request_identifier,'service':current_profile_name,'job_id':current_job_identifier},gr.update(visible=True),current_profile_name+' 작업 '+current_job_identifier+'에 중지를 요청합니다. 실제 종료는 상태에서 확인하세요.'


def submit_hermes_flux_profile_cancellation(current_review_value,current_request_identifier,current_profile_name,current_job_identifier):
    if current_review_value!={'request_id':current_request_identifier,'service':current_profile_name,'job_id':current_job_identifier}:
        raise gr.Error('중지 대상이 바뀌었습니다. 다시 확인하세요.')
    return submit_hermes_checked_cancellation('hermes-flux-profile-cancel',current_review_value,current_job_identifier)


def load_hermes_flux_proposal(current_job_identifier):
    """완료된 제안의 입력을 가져오되 검토와 접수는 하지 않는다."""
    if not current_job_identifier:
        raise gr.Error('먼저 세션 작업을 선택하세요.')
    try:
        current_proposal_record = execute_remote_management_command('hermes-agent','hermes-flux-proposal',{'id':current_job_identifier})['proposal']
        return current_proposal_record['prompt'], current_proposal_record['width'], current_proposal_record['height'], current_proposal_record['seed'], uuid.uuid4().hex, None, None, None, '', '제안을 불러왔습니다. 내용을 확인하고 다시 검토하세요.', gr.update(interactive=False)
    except Exception as current_proposal_error:
        raise gr.Error('FLUX 제안 불러오기 실패: '+str(current_proposal_error)) from current_proposal_error


def build_hermes_flux_image_request(current_prompt_text,current_width_value,current_height_value,current_seed_value,current_request_identifier,current_first_image=None,current_second_image=None):
    current_profile_record=build_hermes_flux_profile_request('flux-image',current_prompt_text,current_width_value,current_height_value,current_seed_value,current_first_image,current_second_image,current_request_identifier)
    return {'request_id':current_profile_record['request_id'],'request':current_profile_record['request']}


def review_hermes_flux_request(current_prompt_text,current_width_value,current_height_value,current_seed_value,current_request_identifier,current_first_image=None,current_second_image=None):
    """참조 이미지까지 포함한 확정 입력을 기존 생성기로 검증한다."""
    try:
        current_review_record=build_hermes_flux_image_request(current_prompt_text,current_width_value,current_height_value,current_seed_value,current_request_identifier,current_first_image,current_second_image)
        import base64
        import hashlib
        current_image_values=current_review_record['request']['images']
        current_image_count=len(current_image_values)
        current_preview_text=f'접수 ID: {current_request_identifier}\n지시: {current_prompt_text}\n크기: {current_width_value} × {current_height_value} · 단계: 16 · 시드: {current_seed_value} · 참조 이미지: {current_image_count}장'
        for current_image_index,current_image_text in enumerate(current_image_values,1):
            current_image_digest=hashlib.sha256(base64.b64decode(current_image_text,validate=True)).hexdigest()
            current_preview_text+=f'\n참조 {current_image_index} PNG SHA-256: {current_image_digest}'
        return current_review_record,current_preview_text,'참조 이미지와 입력을 검토한 뒤 GPU 대기열 접수를 확인하세요.',gr.update(interactive=True)
    except (ValueError,TypeError,OSError) as current_review_error:
        return None,'','입력 확인 실패: '+str(current_review_error),gr.update(interactive=False)


def match_hermes_flux_image_confirmation(confirmed_input_values,current_input_values):
    try:
        if len(confirmed_input_values)!=8 or len(current_input_values)!=8:
            return False
        current_review_record=current_input_values[0]
        return current_review_record==confirmed_input_values[0] and current_review_record==build_hermes_flux_image_request(*current_input_values[1:])
    except (ValueError,TypeError,OSError):
        return False


def submit_hermes_flux_reviewed_request(current_review_record,current_prompt_text,current_width_value,current_height_value,current_seed_value,current_request_identifier,current_first_image=None,current_second_image=None):
    """참조 이미지를 포함한 현재 입력이 검토본과 일치할 때만 접수한다."""
    if not isinstance(current_review_record,dict) or not isinstance(current_review_record.get('request'),dict):
        raise gr.Error('먼저 FLUX 입력을 검토하세요.')
    try:
        current_expected_record=build_hermes_flux_image_request(current_prompt_text,current_width_value,current_height_value,current_seed_value,current_request_identifier,current_first_image,current_second_image)
    except (ValueError,TypeError,OSError) as current_input_error:
        raise gr.Error('입력이 변경됐습니다. 다시 검토하세요.') from current_input_error
    if current_review_record!=current_expected_record:
        raise gr.Error('입력이 변경됐습니다. 다시 검토하세요.')
    try:
        current_result_record=execute_remote_management_command('hermes-agent','hermes-delegate-flux-image',current_review_record)
        if current_result_record.get('state')=='unknown':
            return '', '접수 여부 확인 필요 · FLUX 이력에서 확인하고 자동 재접수하지 마세요.'
        if current_result_record.get('state')!='accepted' or not isinstance(current_result_record.get('job_id'),str):
            raise ValueError('접수 응답 형식 오류')
        return current_result_record['job_id'],('기존 접수 확인' if current_result_record.get('duplicate') else 'FLUX 작업 접수')+' · 실제 완료는 상태를 확인하세요.'
    except Exception as current_submit_error:
        raise gr.Error('접수 확인 실패: '+str(current_submit_error)+' · 같은 접수 ID와 입력을 유지하세요.') from current_submit_error


def list_hermes_flux_delegation_choices(current_selected_identifier):
    current_history_record = execute_remote_management_command('hermes-agent','hermes-flux-delegation-history',{})
    current_choice_values = [(item['request_id']+' · '+item['state']+(' · '+item['job_id'] if item.get('job_id') else ''), item['request_id']) for item in current_history_record['records']]
    current_selected_value = current_selected_identifier if current_selected_identifier in [item[1] for item in current_choice_values] else None
    return gr.update(choices=current_choice_values, value=current_selected_value), 'FLUX 접수 이력 '+str(len(current_choice_values))+'개 · 확인 불가능한 기록은 제외됩니다.'


def read_hermes_flux_receipt(current_request_identifier):
    current_result_record = execute_remote_management_command('hermes-agent','hermes-flux-delegation-status',{'request_id':current_request_identifier})
    current_receipt_record = current_result_record['receipt']
    if current_receipt_record.get('state') == 'accepted':
        current_job_identifier=current_receipt_record['job_id']
        current_job_value=current_result_record.get('job',{})
        current_result_value=current_result_record.get('result',{})
        current_expected_path='/flux-image-generator/jobs/'+current_job_identifier+'/result.png'
        current_image_link=' · [생성 이미지 보기]('+current_expected_path+')' if current_job_value.get('status')=='completed' and current_result_value.get('image')==current_expected_path else ''
        current_result_notice=' · 완료 기록은 있으나 이미지 링크 확인 불가' if current_result_value.get('status')=='unavailable' else ''
        return current_job_identifier,'작업 상태: '+str(current_job_value.get('status','확인 불가'))+current_result_notice+current_image_link+' · [일반 이미지 생성기](/management/frame/flux-image-generator/)'
    if current_receipt_record.get('state') == 'unknown':
        return '', '접수 여부 확인 필요 · FLUX 이력을 확인하세요.'
    return '', '접수 기록이 없습니다.'


def review_hermes_flux_cancellation(current_request_identifier, current_job_identifier):
    current_result_record = execute_remote_management_command('hermes-agent','hermes-flux-delegation-status',{'request_id':current_request_identifier})
    current_receipt_record = current_result_record['receipt']
    if current_receipt_record.get('state') != 'accepted' or current_receipt_record.get('job_id') != current_job_identifier:
        raise gr.Error('접수 ID와 FLUX 작업 ID가 일치하지 않습니다.')
    return {'request_id':current_request_identifier,'job_id':current_job_identifier}, gr.update(visible=True), 'FLUX 작업 '+current_job_identifier+'의 중지를 요청할까요? 실제 종료를 확인해야 합니다.'


def submit_hermes_flux_cancellation(current_cancel_record, current_request_identifier, current_job_identifier):
    if not isinstance(current_cancel_record,dict) or set(current_cancel_record) != {'request_id','job_id'}:
        raise gr.Error('중지 대상을 다시 확인하세요.')
    if (current_cancel_record['request_id'], current_cancel_record['job_id']) != (current_request_identifier, current_job_identifier):
        raise gr.Error('중지 대상이 변경됐습니다. 다시 검토하세요.')
    return submit_hermes_checked_cancellation('hermes-flux-delegation-cancel',current_cancel_record,current_job_identifier)


def load_hermes_kimodo_proposal(current_job_identifier):
    """완료된 작업의 제안을 입력란으로 가져오되 접수하지 않는다."""
    if not current_job_identifier:
        raise gr.Error('먼저 세션 작업을 선택하세요.')
    try:
        current_result_record = execute_remote_management_command('hermes-agent', 'hermes-kimodo-proposal', {'id': current_job_identifier})
        current_proposal_record = current_result_record['proposal']
        return (current_proposal_record['prompt'], current_proposal_record['frames'], current_proposal_record['steps'], current_proposal_record['seed'], uuid.uuid4().hex, None, '', 'Hermes 제안을 불러왔습니다. 내용을 확인하고 위임 입력 검토를 눌러 주세요.', gr.update(interactive=False))
    except Exception as current_proposal_error:
        raise gr.Error('제안 불러오기 실패: ' + str(current_proposal_error)) from current_proposal_error


def review_hermes_kimodo_request(current_prompt_text, current_frames_value, current_steps_value, current_seed_value, current_request_identifier, current_keyframes_text=""):
    """기존 Kimodo 기본 설정과 사용자 입력으로 검토할 불변 입력을 만든다."""
    from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS, validate_kimodo_request
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    try:
        if not isinstance(current_request_identifier, str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
            raise ValueError('접수 ID는 영문·숫자·밑줄·하이픈 8~80자여야 합니다.')
        current_generation_record = {current_key_name: current_value for current_key_name, current_value in KIMODO_DEFAULT_SETTINGS.items() if current_key_name != 'schema_version'}
        current_generation_record.update(action='generate', prompt=current_prompt_text, frames=current_frames_value, steps=current_steps_value, seed=current_seed_value)
        if current_keyframes_text and current_keyframes_text.strip():
            import json
            current_keyframe_values=json.loads(current_keyframes_text)
            if not isinstance(current_keyframe_values,list):
                raise ValueError('키프레임은 ID·프레임 객체의 배열이어야 합니다.')
            if current_keyframe_values:
                current_generation_record.update(keyframes=current_keyframe_values,post_processing=True,remove_horizontal_motion=False)
        current_validated_record=validate_kimodo_request(current_generation_record)
        if current_generation_record.get('keyframes'):
            current_generation_record['keyframes']=current_validated_record['keyframes']
        current_review_record = {'request_id': current_request_identifier, 'request': current_generation_record}
        current_preview_text = ('접수 ID: ' + current_request_identifier + '\n동작: ' + current_generation_record['prompt'] + '\n프레임: ' + str(current_frames_value) + ' · 단계: ' + str(current_steps_value) + ' · 시드: ' + str(current_seed_value) + '\n방향: ' + ', '.join(current_generation_record['directions']) + ' · 가이던스: ' + str(current_generation_record['guidance_scale']) + ' · 시작 각도: ' + str(current_generation_record['heading_degrees']) + '\n후처리: ' + str(current_generation_record['post_processing']) + ' · 수평 이동 제거: ' + str(current_generation_record['remove_horizontal_motion']) + '\nOpenPose 배율: ' + str(current_generation_record['openpose_scale_percent']) + '% · 손: ' + str(current_generation_record['pose_include_hands']) + ' · 얼굴: ' + str(current_generation_record['pose_include_face']))
        if current_generation_record.get('keyframes'):
            current_preview_text+='\n키프레임: '+str(current_generation_record['keyframes'])+' · 공식 후처리 사용 · 수평 이동 유지\n원본은 접수 시 다시 검증하여 작업에 고정됩니다. 검토 후 원본이 바뀔 수 있으므로 미리보기를 다시 확인하세요.'
        return current_review_record, current_preview_text, '아래 확정 입력을 확인하세요. 접수하면 Kimodo 생성 작업이 공용 GPU 대기열에 추가됩니다. 입력 변경은 다시 검토해야 반영됩니다.'
    except (ValueError, TypeError) as current_review_error:
        return None, None, '위임 입력 확인 실패: ' + str(current_review_error)


def invalidate_hermes_kimodo_review(current_review_record, current_prompt_text, current_frames_value, current_steps_value, current_seed_value, current_request_identifier, current_keyframes_text=""):
    """검토 뒤 입력이 바뀌면 이전 확정본을 사용할 수 없게 한다."""
    if not isinstance(current_review_record, dict) or not isinstance(current_review_record.get('request'), dict):
        return gr.skip(), gr.skip(), gr.skip(), gr.skip()
    current_review_request = current_review_record['request']
    current_rebuilt_record,_,_=review_hermes_kimodo_request(current_prompt_text,current_frames_value,current_steps_value,current_seed_value,current_request_identifier,current_keyframes_text)
    if current_review_record==current_rebuilt_record:
        return gr.skip(), gr.skip(), gr.skip(), gr.skip()
    return None, '', '입력이 변경되어 이전 검토를 해제했습니다. 위임 입력을 다시 검토하세요.', gr.update(interactive=False)


def submit_hermes_kimodo_request(current_review_record):
    """사용자가 검토한 입력을 그대로 접수한다."""
    if not isinstance(current_review_record, dict) or set(current_review_record) != {'request_id', 'request'}:
        raise gr.Error('먼저 위임 입력을 검토하세요.')
    try:
        current_result_record = execute_remote_management_command('hermes-agent', 'hermes-delegate-kimodo', current_review_record)
        if current_result_record.get('state') == 'unknown':
            return '', '접수 여부 확인 필요: Kimodo 이력과 실제 작업을 확인하세요. 자동 재접수하지 않습니다.'
        if current_result_record.get('state') != 'accepted' or not isinstance(current_result_record.get('job_id'), str):
            raise ValueError('위임 접수 응답 형식 오류')
        current_message_text = '기존 접수 확인' if current_result_record.get('duplicate') else 'Kimodo 작업 접수'
        return current_result_record['job_id'], current_message_text + ' · 완료 여부는 작업 상태에서 확인하세요.'
    except Exception as current_submit_error:
        raise gr.Error('위임 접수 확인 실패: ' + str(current_submit_error) + ' · 같은 접수 ID와 입력으로 다시 확인하세요.') from current_submit_error


def submit_hermes_kimodo_reviewed_request(current_review_record, current_prompt_text, current_frames_value, current_steps_value, current_seed_value, current_request_identifier, current_keyframes_text=""):
    """확인 시점에 검토본과 버튼 입력이 같을 때만 접수한다."""
    if not isinstance(current_review_record, dict) or not isinstance(current_review_record.get('request'), dict):
        raise gr.Error('먼저 위임 입력을 검토하세요.')
    current_rebuilt_record,_,_=review_hermes_kimodo_request(current_prompt_text,current_frames_value,current_steps_value,current_seed_value,current_request_identifier,current_keyframes_text)
    if current_review_record!=current_rebuilt_record:
        raise gr.Error('입력이 변경됐습니다. 위임 입력을 다시 검토하세요.')
    return submit_hermes_kimodo_request(current_review_record)


def list_hermes_delegation_choices(current_selected_identifier=None):
    """새로고침 뒤에도 기존 접수를 선택할 수 있다."""
    try:
        current_history_record = execute_remote_management_command('hermes-agent', 'hermes-delegation-history', {})
        current_receipt_values = current_history_record['records']
        current_choices_list = [(current_receipt_value['request_id'] + ' · ' + current_receipt_value['state'] + (' · ' + current_receipt_value['job_id'] if current_receipt_value.get('job_id') else ''), current_receipt_value['request_id']) for current_receipt_value in current_receipt_values]
        current_choice_ids = [current_choice_value[1] for current_choice_value in current_choices_list]
        current_selected_value = current_selected_identifier if current_selected_identifier in current_choice_ids else None
        return gr.update(choices=current_choices_list, value=current_selected_value), '접수 이력 ' + str(len(current_choices_list)) + '개' + (' · 최근 100개만 표시' if current_history_record.get('truncated') else '')
    except Exception as current_history_error:
        raise gr.Error('위임 이력 조회 실패: ' + str(current_history_error)) from current_history_error


def select_hermes_delegation_receipt(current_request_identifier):
    """이력 선택은 기존 검토·중지 확인을 폐기하고 기록만 확인한다."""
    if not current_request_identifier:
        raise gr.Error('먼저 위임 접수 이력을 선택하세요.')
    current_job_identifier, current_receipt_message = read_hermes_delegation_receipt(current_request_identifier)
    return current_request_identifier, current_job_identifier, current_receipt_message, None, '', None, gr.update(visible=False), gr.update(interactive=False)


def read_hermes_delegation_receipt(current_request_identifier):
    """접수 ID로 기존 접수 결과만 확인한다."""
    try:
        current_result_record = execute_remote_management_command('hermes-agent', 'hermes-delegation-status', {'request_id': current_request_identifier})
        current_state_value = current_result_record.get('state')
        if current_state_value == 'accepted' and isinstance(current_result_record.get('job_id'), str):
            return current_result_record['job_id'], '기존 접수 확인 · 작업 상태 조회로 완료 여부를 확인하세요.'
        if current_state_value == 'unknown':
            return '', '접수 여부 확인 필요: Kimodo 이력과 실제 작업을 확인하세요. 자동 재접수하지 않습니다.'
        if current_state_value == 'not_found':
            return '', '이 접수 ID의 기록이 없습니다. 입력과 ID를 확인하세요.'
        raise ValueError('접수 조회 응답 형식 오류')
    except Exception as current_receipt_error:
        raise gr.Error('위임 접수 조회 실패: ' + str(current_receipt_error)) from current_receipt_error


def review_hermes_kimodo_cancellation(current_request_identifier, current_job_identifier):
    """접수 기록과 화면의 작업 ID가 일치할 때 확인 대상을 고정한다."""
    try:
        current_receipt_record = execute_remote_management_command('hermes-agent', 'hermes-delegation-status', {'request_id': current_request_identifier})
        if current_receipt_record.get('state') != 'accepted' or current_receipt_record.get('job_id') != current_job_identifier:
            raise ValueError('접수 ID와 작업 ID가 일치하지 않습니다. 접수 ID로 먼저 확인하세요.')
        return {'request_id': current_request_identifier, 'job_id': current_job_identifier}, gr.update(visible=True), 'Kimodo 작업 ' + current_job_identifier + '의 중지를 요청할까요? 실제 종료까지 GPU 예약이 유지됩니다.'
    except Exception as current_review_error:
        raise gr.Error('중지 대상 확인 실패: ' + str(current_review_error)) from current_review_error


def submit_hermes_kimodo_cancellation(current_cancel_record):
    if not isinstance(current_cancel_record, dict) or set(current_cancel_record) != {'request_id', 'job_id'}:
        raise gr.Error('중지할 위임 작업을 다시 확인하세요.')
    return submit_hermes_checked_cancellation('hermes-delegation-cancel',current_cancel_record,current_cancel_record['job_id'])


def read_hermes_kimodo_job(current_job_identifier):
    """기존 Kimodo 작업 서비스의 상태를 읽는다."""
    if not isinstance(current_job_identifier, str) or not current_job_identifier:
        raise gr.Error('먼저 접수된 Kimodo 작업 ID를 입력하세요.')
    try:
        current_job_record = execute_remote_management_command('kimodo', 'status', {'id': current_job_identifier})
        if not isinstance(current_job_record, dict):
            raise ValueError('작업 상태 형식 오류')
        current_status_value = current_job_record.get('status', 'unknown')
        current_status_label = {'queued':'대기 중', 'running':'실행 중', 'completed':'완료', 'failed':'실패', 'cancelled':'취소됨', 'paused':'일시정지', 'unknown':'확인 불가'}.get(current_status_value, str(current_status_value))
        current_status_lines = ['작업 ' + current_job_identifier + ' · ' + current_status_label]
        current_progress_record = current_job_record.get('progress')
        if isinstance(current_progress_record, dict) and type(current_progress_record.get('percent')) in (int, float):
            current_status_lines.append('진행률: ' + str(current_progress_record['percent']) + '%')
        for current_field_name, current_field_label in (('message','안내'), ('error','오류')):
            if isinstance(current_job_record.get(current_field_name), str) and current_job_record[current_field_name]:
                current_status_lines.append(current_field_label + ': ' + current_job_record[current_field_name])
        current_warning_values = current_job_record.get('quality_warnings')
        if isinstance(current_warning_values, list) and current_warning_values:
            current_status_lines.append('품질 경고: ' + '; '.join(str(current_warning_value) for current_warning_value in current_warning_values))
        current_log_text = current_job_record.get('log')
        if isinstance(current_log_text, str) and 'VerifyOutputSizes' in current_log_text and ('simcc_x' in current_log_text or 'simcc_y' in current_log_text):
            current_status_lines.append('DWPose 출력 형상 경고: 축 순서 자동 검사를 거쳤으나 포즈 결과의 품질을 확인하세요.')
        if current_job_record.get('video'):
            current_status_lines.append('미리보기와 상세 로그는 Kimodo 작업과 이력 보기에서 확인하세요.')
        return '\n'.join(current_status_lines)
    except Exception as current_status_error:
        raise gr.Error('Kimodo 작업 조회 실패: ' + str(current_status_error)) from current_status_error


def read_hermes_service_registration_rows(current_search_text=None,current_offset_value=0):
    """등록 목록과 실제 연결 범위를 구분한다."""
    try:
        current_request_value={} if current_search_text is None else {'query':current_search_text,'offset':current_offset_value,'limit':10}
        current_catalog_record = execute_remote_management_command('hermes-agent', 'hermes-service-registration', current_request_value)
        current_service_rows = [[current_service_record['service'], ', '.join(current_service_record['commands']), '; '.join(current_blocked_record['command']+': '+current_blocked_record['reason'] for current_blocked_record in current_service_record.get('gateway_blocked',[])) or '게이트웨이 명시 차단 없음', '; '.join(current_blocked_record['command']+': '+current_blocked_record['reason'] for current_blocked_record in current_service_record.get('known_service_blocked',[])) or '확인된 차단 없음 · 그 외 정책 미확인', '; '.join(current_limit_record['command']+': '+current_limit_record['note'] for current_limit_record in current_service_record.get('conditional_limitations',[])) or '확인된 조건부 제한 없음 · 전수 확인 아님', (', '.join(current_service_record['hermes_links']) or '기재된 Hermes 연결 없음') if isinstance(current_service_record.get('hermes_links'),list) else '연결 정보 미제공'] for current_service_record in current_catalog_record['services']]
        current_page_text = ''
        if 'total' in current_catalog_record:
            current_page_text=' / 검색 결과 '+str(current_catalog_record['total'])+'개 · 다음 시작 위치: '+str(current_catalog_record['next_offset'] if current_catalog_record['next_offset'] is not None else '없음')
        return current_service_rows, '등록 서비스 ' + str(len(current_service_rows)) + '개' + current_page_text + ' · 명시 차단이 없어도 실행 가능 여부는 미확인입니다. 사용 가능한 기능은 위 기능 목록을 확인하세요.'
    except Exception as current_catalog_error:
        return [], '서비스 등록 목록 조회 실패: ' + str(current_catalog_error)


def read_hermes_capability_rows(current_search_text=""):
    """공용 기능 목록을 사람이 비교하기 쉬운 행으로 보여 준다."""
    try:
        current_catalog_record = execute_remote_management_command('hermes-agent', 'hermes-capabilities', {})
        current_effect_labels = {'read':'조회', 'write':'원본 저장', 'enqueue':'대기열 접수', 'recovery_possible':'상태 복구 가능', 'cancel_request':'중지 요청', 'local_bookkeeping':'상태 조회·로컬 잠금'}
        current_gpu_labels = {'none':'사용 안 함', 'exclusive':'배타 사용', 'queued':'대기열 사용', 'inspection':'장치 초기화 가능 · 대기열 밖'}
        current_interface_labels={'gui':'화면','mcp':'Codex MCP','isolated_fixed_bridge':'격리 조회'}
        current_retry_labels={'safe':'같은 요청 재시도 가능','request_id':'같은 접수 ID','request_id_or_unknown':'같은 ID · 불확실 시 확인','check_status':'상태 확인'}
        current_all_rows=[[current_record['label'],current_record['command'],', '.join(current_interface_labels.get(current_interface,current_interface) for current_interface in current_record['interfaces']),', '.join(current_record['required']) or '없음',current_effect_labels.get(current_record['effect'],current_record['effect']),current_gpu_labels.get(current_record['gpu'],current_record['gpu']),current_retry_labels.get(current_record['retry'],current_record['retry']),current_record['note']] for current_record in current_catalog_record['records']]
        if not isinstance(current_search_text,str) or len(current_search_text)>100:
            raise ValueError('검색어는 100자 이하여야 합니다.')
        current_search_value=current_search_text.strip().casefold()
        current_rows_value=[current_row_value for current_row_value in current_all_rows if not current_search_value or current_search_value in ' '.join(current_row_value).casefold()]
        current_unlisted_commands=current_catalog_record.get('unlisted_commands',[])
        current_status_text='기능 '+str(len(current_rows_value))+'개 / 전체 '+str(len(current_all_rows))+'개 · 작업 변경은 각 확인 절차와 서비스 검증을 따릅니다.'
        if current_unlisted_commands:
            current_status_text+=' 목록에 없는 등록 명령: '+', '.join(current_unlisted_commands)+' · 지원 여부 확인 필요'
        return current_rows_value,current_status_text
    except Exception as current_catalog_error:
        return [], '기능 목록 조회 실패: ' + str(current_catalog_error)


def build_hermes_agent_interface():
    with gr.Blocks(title='Hermes 관리 에이전트') as hermes_interface_blocks:
        build_generator_changelog(hermes_interface_blocks, 'hermes-agent')
        gr.Markdown('## Hermes 관리 에이전트\n관리 상태 조회는 로컬 잠금 파일을 만들 수 있습니다. Kimodo 활성 상태는 기록 기준입니다. 관리 기능과 서비스 상태를 탐색하고 음악·영상·이미지·번역·작가 작업을 위임할 수 있습니다. 맵과 에셋은 지원되는 변경을 검토하고 저장하며, 대화에서 관리 정보를 확인하거나 격리 코딩 작업을 요청할 수 있습니다. 서비스별 지원 범위와 제한은 기능 목록에서 확인하세요. 생성 위임은 사용자가 입력을 검토하고 확인한 뒤 공용 GPU 대기열에 접수합니다. 코딩 작업의 변경은 격리 사본의 검토용 diff로 제공하며 원본에 자동 적용하지 않습니다. 모델 추론은 공용 GPU를 배타적으로 사용합니다. 실행 시간은 관측 이력이 부족해 계산 중입니다. 모델 준비는 [모델 관리](/management/frame/model-management/)에서 확인하세요.')
        hermes_management_summary = gr.Markdown('관리 상태를 확인하고 있습니다.')
        hermes_management_refresh = gr.Button('관리 상태 새로고침')
        hermes_management_refresh.click(read_hermes_management_summary, outputs=hermes_management_summary, queue=False)
        hermes_interface_blocks.load(read_hermes_management_summary, outputs=hermes_management_summary, queue=False)
        with gr.Accordion('사용 가능한 관리 기능', open=False):
            gr.Markdown('조회와 작업 변경의 영향을 확인합니다. 작업 실행 권한을 별도로 부여하는 화면은 아닙니다.')
            hermes_capability_search = gr.Textbox(label='관리 기능 검색',placeholder='기능명, 명령, 연결 경로 또는 입력',max_lines=1)
            hermes_capability_refresh = gr.Button('관리 기능 목록 새로고침')
            hermes_capability_status = gr.Markdown('목록 새로고침으로 기능을 확인하세요.')
            hermes_capability_table = gr.Dataframe(headers=['기능','명령','연결','필수 입력','영향','GPU','재시도','확인 사항'], datatype=['str']*8, interactive=False, type='array', label='관리 기능 목록')
            hermes_capability_refresh.click(read_hermes_capability_rows, inputs=[hermes_capability_search], outputs=[hermes_capability_table, hermes_capability_status], queue=False)
            hermes_capability_search.submit(read_hermes_capability_rows, inputs=[hermes_capability_search], outputs=[hermes_capability_table, hermes_capability_status], queue=False)
        with gr.Accordion('전체 관리 서비스 등록 목록', open=False):
            gr.Markdown('게이트웨이 등록만 표시합니다. 폐기·제한·미연결 명령을 포함하며 Hermes에서 실행할 수 있다는 뜻은 아닙니다.')
            with gr.Row():
                hermes_service_registration_query = gr.Textbox(label='서비스·기능 검색',placeholder='서비스명, 명령 또는 한국어 기능명')
                hermes_service_registration_offset = gr.Number(label='조회 시작 위치',value=0,precision=0,minimum=0)
            hermes_service_registration_button = gr.Button('서비스 등록 목록 조회')
            hermes_service_registration_status = gr.Markdown('조회하면 게이트웨이에 등록된 서비스를 표시합니다.')
            hermes_service_registration_table = gr.Dataframe(headers=['서비스','등록된 명령','게이트웨이 명시 차단','확인된 서비스 차단','확인된 조건부 제한','Hermes 연결 기능'], datatype=['str','str','str','str','str','str'], interactive=False, type='array', label='전체 관리 서비스 등록')
            hermes_service_registration_button.click(read_hermes_service_registration_rows, inputs=[hermes_service_registration_query,hermes_service_registration_offset], outputs=[hermes_service_registration_table, hermes_service_registration_status], queue=False)
            hermes_service_registration_query.submit(read_hermes_service_registration_rows, inputs=[hermes_service_registration_query,hermes_service_registration_offset], outputs=[hermes_service_registration_table, hermes_service_registration_status], queue=False)
        with gr.Accordion('건물 에셋 조회', open=False):
            gr.Markdown('콘텐츠 서비스의 세대와 등록 건물 원본을 확인합니다. 이미지 픽셀 크기는 게임 표시 크기가 아닙니다. [건물 관리](/management/frame/building-editor/)에서 이미지를 확인하세요.')
            with gr.Row():
                hermes_building_query = gr.Textbox(label='건물 ID·맵·이름 검색')
                hermes_building_offset = gr.Number(label='건물 조회 시작 위치',value=0,precision=0,minimum=0)
            hermes_building_search = gr.Button('건물 검색')
            hermes_building_next = gr.Button('건물 다음 결과',interactive=False)
            hermes_building_next_offset = gr.State(None)
            hermes_building_catalog_items = gr.State([])
            hermes_building_status = gr.Markdown('콘텐츠 서비스에 연결되어야 건물을 조회할 수 있습니다.')
            hermes_building_table = gr.Dataframe(headers=['ID','원본 픽셀','앵커 X','앵커 Y','사용 맵'],datatype=['str']*5,interactive=False,type='array',label='건물 에셋 목록')
            hermes_building_detail = gr.JSON(label='선택한 건물 상세')
            hermes_building_draft=gr.Textbox(label='건물 앵커 변경 초안 JSON',lines=8)
            hermes_building_request=gr.Textbox(label='건물 앵커 접수 ID')
            hermes_building_review_state=gr.State(None)
            hermes_building_review=gr.JSON(label='변경 전후와 사용 맵')
            hermes_building_edit_status=gr.Markdown('건물을 선택해 앵커 초안을 준비하세요.')
            hermes_building_review_button=gr.Button('앵커 변경 검토')
            hermes_building_receipt_button=gr.Button('앵커 저장 접수 조회')
            with gr.Group(visible=False) as hermes_building_confirm_group:
                gr.Markdown('변경 전후와 사용 맵을 확인한 뒤 저장하세요.')
                hermes_building_save_button=gr.Button('앵커 저장 확인',variant='primary')
            hermes_building_table.select(prepare_hermes_building_anchor_draft,[hermes_building_catalog_items],[hermes_building_detail,hermes_building_draft,hermes_building_request,hermes_building_review_state,hermes_building_confirm_group,hermes_building_edit_status],queue=False)
            hermes_building_review_button.click(review_hermes_building_anchor_draft,[hermes_building_draft,hermes_building_request],[hermes_building_review_state,hermes_building_review,hermes_building_confirm_group,hermes_building_edit_status],queue=False)
            hermes_building_save_button.click(save_hermes_building_anchor_draft,[hermes_building_review_state,hermes_building_draft,hermes_building_request],[hermes_building_review_state,hermes_building_confirm_group,hermes_building_edit_status],queue=False)
            hermes_building_receipt_button.click(read_hermes_building_anchor_status,[hermes_building_request],[hermes_building_edit_status],queue=False)
            hermes_building_invalidate_outputs=[hermes_building_review_state,hermes_building_review,hermes_building_confirm_group,hermes_building_edit_status]
            for current_input_component in (hermes_building_draft,hermes_building_request,hermes_building_query,hermes_building_offset):
                current_input_component.input(invalidate_hermes_building_review,outputs=hermes_building_invalidate_outputs,queue=False)
            hermes_building_search.click(invalidate_hermes_building_review,outputs=hermes_building_invalidate_outputs,queue=False)
            hermes_building_next.click(invalidate_hermes_building_review,outputs=hermes_building_invalidate_outputs,queue=False)
            hermes_building_inputs = [hermes_building_query,hermes_building_offset]
            hermes_building_outputs = [hermes_building_table,hermes_building_status,hermes_building_next_offset,hermes_building_next,hermes_building_catalog_items,hermes_building_detail]
            hermes_building_query.change(lambda:(0,None,gr.update(interactive=False),[],'검색 조건이 변경됐습니다. 다시 검색하세요.',[],None),outputs=[hermes_building_offset,hermes_building_next_offset,hermes_building_next,hermes_building_table,hermes_building_status,hermes_building_catalog_items,hermes_building_detail],queue=False)
            hermes_building_search.click(read_hermes_building_catalog_rows,hermes_building_inputs,hermes_building_outputs,queue=False)
            hermes_building_next.click(lambda current_page_state:current_page_state['next_offset'],[hermes_building_next_offset],[hermes_building_offset],queue=False).then(read_hermes_building_catalog_rows,[*hermes_building_inputs,hermes_building_next_offset],hermes_building_outputs,queue=False)
        with gr.Accordion('월드맵 연결 조회', open=False):
            gr.Markdown('등록된 맵과 이동 연결을 월드맵 검수와 같은 원본에서 읽습니다. [월드맵 검수 화면](/management/frame/world-map/)에서 시각적으로 확인할 수 있습니다.')
            hermes_world_button = gr.Button('월드맵 연결 조회')
            hermes_world_status = gr.Markdown('조회하면 맵과 연결을 표시합니다.')
            hermes_world_items = gr.State([])
            hermes_world_table = gr.Dataframe(headers=['ID','이름','구분','표시 열','표시 행','연결 맵'], datatype=['str']*6, interactive=False, type='array', label='월드맵 연결')
            hermes_world_detail = gr.JSON(label='선택한 맵의 연결 상세')
            hermes_world_button.click(read_hermes_world_map_rows, outputs=[hermes_world_table,hermes_world_status,hermes_world_items,hermes_world_detail], queue=False)
            hermes_world_table.select(select_hermes_world_map_item, [hermes_world_items], [hermes_world_detail], queue=False)
        with gr.Accordion('등록 스프라이트 시트 조회', open=False):
            gr.Markdown('에셋 저장소의 등록 스프라이트를 검색하고 프레임·앵커와 원본 해시를 읽습니다. 이미지 외형과 재생은 [스프라이트 시트 편집기](/management/frame/sprite-sheet-editor/)에서 확인하세요.')
            with gr.Row():
                hermes_sprite_query = gr.Textbox(label='스프라이트 검색어')
                hermes_sprite_offset = gr.Number(label='스프라이트 검색 시작 위치',value=0,precision=0,minimum=0)
            hermes_sprite_search = gr.Button('등록 스프라이트 검색')
            hermes_sprite_next = gr.Button('스프라이트 다음 결과',interactive=False)
            hermes_sprite_next_offset = gr.State(None)
            hermes_sprite_choices = gr.Dropdown(label='등록 스프라이트 선택',choices=[],interactive=True)
            hermes_sprite_status = gr.Markdown('검색어를 입력하고 등록 원본을 검색하세요.')
            hermes_sprite_snapshot = gr.State(None)
            hermes_sprite_frame_offset = gr.Number(label='프레임 조회 시작 위치',value=0,precision=0,minimum=0)
            hermes_sprite_read = gr.Button('스프라이트 프레임·앵커 조회')
            hermes_sprite_detail = gr.JSON(label='스프라이트 원본과 프레임')
            hermes_sprite_search.click(read_hermes_sprite_catalog_choices,[hermes_sprite_query,hermes_sprite_offset],[hermes_sprite_choices,hermes_sprite_detail,hermes_sprite_status,hermes_sprite_next_offset,hermes_sprite_next],queue=False)
            hermes_sprite_next.click(lambda current_next_value:current_next_value,[hermes_sprite_next_offset],[hermes_sprite_offset],queue=False).then(read_hermes_sprite_catalog_choices,[hermes_sprite_query,hermes_sprite_offset],[hermes_sprite_choices,hermes_sprite_detail,hermes_sprite_status,hermes_sprite_next_offset,hermes_sprite_next],queue=False)
            hermes_sprite_read.click(read_hermes_sprite_sheet_summary,[hermes_sprite_choices,hermes_sprite_frame_offset,hermes_sprite_snapshot],[hermes_sprite_detail,hermes_sprite_status,hermes_sprite_snapshot],queue=False)
            hermes_sprite_choices.change(lambda:(None,0,None),outputs=[hermes_sprite_detail,hermes_sprite_frame_offset,hermes_sprite_snapshot],queue=False)
            hermes_sprite_query.change(lambda:(0,None,gr.update(interactive=False)),outputs=[hermes_sprite_offset,hermes_sprite_next_offset,hermes_sprite_next],queue=False)
            gr.Markdown('### 앵커 변경 · 시트 재패킹\n변경할 프레임을 지정하고 출력 시트 크기와 모든 프레임의 재배치, 앵커 변경을 확인하세요. 저장 전에 기존 편집기에서 이미지와 재생을 검수하세요.')
            hermes_sprite_edit_load = gr.Button('조회한 시트로 앵커 초안 만들기')
            hermes_sprite_edit_proposal = gr.Button('선택한 세션 작업의 앵커 제안 불러오기 · 기존 초안 교체')
            hermes_sprite_edit_draft = gr.Code(label='스프라이트 앵커 변경 초안 JSON',language='json',interactive=True,lines=8)
            hermes_sprite_edit_request = gr.Textbox(label='스프라이트 저장 접수 ID',value=lambda:uuid.uuid4().hex,interactive=True)
            hermes_sprite_edit_state = gr.State(None)
            hermes_sprite_edit_status = gr.Markdown('원본 시트를 조회한 뒤 초안을 만드세요.')
            hermes_sprite_edit_preview = gr.Button('스프라이트 앵커 변경 검증')
            with gr.Group(visible=False) as hermes_sprite_edit_confirm:
                gr.Markdown('시트 이미지가 다시 패킹됩니다. 모든 프레임 위치와 앵커 변경을 확인하세요.')
                hermes_sprite_edit_image = gr.Image(label='재패킹된 출력 시트 미리보기',type='pil',format='png',interactive=False)
                hermes_sprite_edit_comparison = gr.JSON(label='스프라이트 변경 및 출력 시트')
                hermes_sprite_clip_choice = gr.Dropdown(label='등록 재생 클립',choices=[],interactive=True)
                hermes_sprite_clip_button = gr.Button('등록 클립 시간으로 재생 검수')
                hermes_sprite_playback_fps = gr.Dropdown(label='검수 재생 FPS',choices=[4,6,8,12,16,24,30],value=8)
                hermes_sprite_playback_button = gr.Button('변경안 재생 검수 생성')
                hermes_sprite_playback_status = gr.Markdown('재생은 전체 프레임을 균일한 속도로 보여줍니다.')
                hermes_sprite_playback_html = gr.HTML()
                with gr.Row():
                    hermes_sprite_edit_cancel = gr.Button('스프라이트 저장하지 않기')
                    hermes_sprite_edit_save = gr.Button('확인 후 스프라이트 저장',variant='primary')
            hermes_sprite_edit_receipt = gr.Button('스프라이트 저장 접수 확인')
            hermes_sprite_edit_load.click(make_hermes_sprite_anchor_draft,[hermes_sprite_detail],[hermes_sprite_edit_draft,hermes_sprite_edit_state,hermes_sprite_edit_confirm,hermes_sprite_edit_status],queue=False)
            hermes_sprite_edit_preview.click(lambda:('', '재생은 전체 프레임을 균일한 속도로 보여줍니다.'),outputs=[hermes_sprite_playback_html,hermes_sprite_playback_status],queue=False).then(review_hermes_sprite_anchor_draft,[hermes_sprite_edit_draft,hermes_sprite_edit_request],[hermes_sprite_edit_state,hermes_sprite_edit_comparison,hermes_sprite_edit_image,hermes_sprite_clip_choice,hermes_sprite_edit_confirm],queue=False)
            hermes_sprite_clip_button.click(render_hermes_sprite_registered_clip,[hermes_sprite_edit_state,hermes_sprite_edit_draft,hermes_sprite_edit_request,hermes_sprite_clip_choice],[hermes_sprite_playback_html,hermes_sprite_playback_status],trigger_mode='once',concurrency_limit=1)
            hermes_sprite_playback_button.click(render_hermes_sprite_anchor_playback,[hermes_sprite_edit_state,hermes_sprite_edit_draft,hermes_sprite_edit_request,hermes_sprite_playback_fps],[hermes_sprite_playback_html,hermes_sprite_playback_status],trigger_mode='once',concurrency_limit=1)
            hermes_sprite_edit_save.click(save_hermes_sprite_anchor_draft,[hermes_sprite_edit_state,hermes_sprite_edit_draft,hermes_sprite_edit_request],[hermes_sprite_edit_state,hermes_sprite_edit_confirm,hermes_sprite_edit_status],trigger_mode='once',concurrency_limit=1)
            hermes_sprite_edit_cancel.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_sprite_edit_state,hermes_sprite_edit_confirm],queue=False)
            hermes_sprite_edit_receipt.click(read_hermes_sprite_anchor_status,[hermes_sprite_edit_request],[hermes_sprite_edit_status],queue=False)
            for current_sprite_input in (hermes_sprite_choices,hermes_sprite_edit_draft,hermes_sprite_edit_request):
                current_sprite_input.change(lambda:(None,gr.update(visible=False)),outputs=[hermes_sprite_edit_state,hermes_sprite_edit_confirm],queue=False)
        with gr.Accordion('맵 이펙트 조회', open=False):
            gr.Markdown('콘텐츠 DB의 이펙트와 좌표를 조회합니다. 이미지와 실제 배치는 [이펙트 검수 화면](/management/frame/effect-editor/)에서 확인하세요.')
            hermes_effect_choices = gr.Dropdown(label='맵 이펙트 선택',choices=[],interactive=True)
            with gr.Row():
                hermes_effect_refresh = gr.Button('맵 이펙트 목록 새로고침')
                hermes_effect_read = gr.Button('선택 이펙트 좌표 조회')
            hermes_effect_status = gr.Markdown('콘텐츠 DB 연결이 필요합니다.')
            hermes_effect_detail = gr.JSON(label='맵 이펙트 정보와 좌표')
            hermes_effect_refresh.click(load_hermes_effect_choices,outputs=[hermes_effect_choices,hermes_effect_detail,hermes_effect_status],queue=False)
            hermes_effect_read.click(load_hermes_effect_summary,[hermes_effect_choices],[hermes_effect_detail,hermes_effect_status],queue=False)
            hermes_effect_choices.change(lambda:None,outputs=[hermes_effect_detail],queue=False)
            gr.Markdown('좌표는 같은 이펙트를 사용하는 모든 맵에 적용됩니다. 실제 이미지 정렬은 검수 화면에서 먼저 확인하세요.')
            hermes_effect_edit_load = gr.Button('선택 이펙트 좌표 초안 불러오기')
            hermes_effect_edit_proposal = gr.Button('선택한 세션 작업의 이펙트 제안 불러오기 · 기존 초안 교체')
            hermes_effect_edit_draft = gr.Code(label='이펙트 좌표 변경 초안 JSON',language='json',interactive=True,lines=8)
            hermes_effect_edit_request = gr.Textbox(label='이펙트 저장 접수 ID',value=lambda:uuid.uuid4().hex,interactive=True)
            hermes_effect_edit_state = gr.State(None)
            hermes_effect_edit_status = gr.Markdown('좌표 편집을 지원하는 이펙트를 선택하세요.')
            hermes_effect_edit_preview = gr.Button('이펙트 좌표 변경 검증')
            with gr.Group(visible=False) as hermes_effect_edit_confirm:
                gr.Markdown('변경 전후와 적용 범위를 확인하세요. 저장하면 콘텐츠 DB가 변경됩니다.')
                hermes_effect_edit_comparison = gr.JSON(label='이펙트 좌표 변경 전후')
                with gr.Row():
                    hermes_effect_edit_cancel = gr.Button('이펙트 저장하지 않기')
                    hermes_effect_edit_save = gr.Button('확인 후 이펙트 저장',variant='primary')
            hermes_effect_edit_receipt = gr.Button('이펙트 저장 접수 확인')
            hermes_effect_edit_load.click(load_hermes_effect_edit_draft,[hermes_effect_choices],[hermes_effect_edit_draft,hermes_effect_edit_state,hermes_effect_edit_confirm,hermes_effect_edit_status],queue=False)
            hermes_effect_edit_preview.click(review_hermes_effect_edit_draft,[hermes_effect_edit_draft,hermes_effect_edit_request],[hermes_effect_edit_state,hermes_effect_edit_comparison,hermes_effect_edit_confirm],queue=False)
            hermes_effect_edit_save.click(save_hermes_effect_edit_draft,[hermes_effect_edit_state,hermes_effect_edit_draft,hermes_effect_edit_request],[hermes_effect_edit_state,hermes_effect_edit_confirm,hermes_effect_edit_status],trigger_mode='once',concurrency_limit=1)
            hermes_effect_edit_cancel.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_effect_edit_state,hermes_effect_edit_confirm],queue=False)
            hermes_effect_edit_receipt.click(read_hermes_effect_edit_status,[hermes_effect_edit_request],[hermes_effect_edit_status],queue=False)
            for current_effect_input in (hermes_effect_choices,hermes_effect_edit_draft,hermes_effect_edit_request):
                current_effect_input.change(lambda:(None,gr.update(visible=False)),outputs=[hermes_effect_edit_state,hermes_effect_edit_confirm],queue=False)
            with gr.Accordion('이펙트 신규 등록',open=False):
                gr.Markdown('에셋 저장소에 등록된 원본을 사용합니다. 웨이포인트는 4×2 8프레임 이미지와 애니메이션 메타데이터가 필요합니다. 안개·군집·빌보드 발광은 alignment가 필요합니다. 안전지대 오라는 이펙트 좌표 검수기에 표시되지 않습니다. 게임 원본 참조와 실제 외형은 별도 확인하세요.')
                hermes_effect_register_draft=gr.Code(label='신규 이펙트 JSON',language='json',interactive=True,lines=8,value='{"id":"","name":"","image":"","renderer":"safe-barrier-aura","columns":4,"rows":2,"frames":8}')
                hermes_effect_register_request=gr.Textbox(label='신규 등록 접수 ID',value=lambda:uuid.uuid4().hex,interactive=True)
                hermes_effect_register_state=gr.State(None)
                hermes_effect_register_status=gr.Markdown('신규 이펙트와 등록된 원본 경로를 입력하세요.')
                hermes_effect_register_preview=gr.Button('신규 이펙트 검토')
                with gr.Group(visible=False) as hermes_effect_register_confirm:
                    gr.Markdown('등록 정보와 원본 해시를 확인하세요. DB 저장 후 원장 반영과 게임 참조 갱신은 별도로 확인합니다.')
                    hermes_effect_register_comparison=gr.JSON(label='신규 이펙트와 원본 해시')
                    hermes_effect_register_save=gr.Button('확인 후 신규 등록',variant='primary')
                    hermes_effect_register_cancel=gr.Button('등록하지 않기')
                hermes_effect_register_receipt=gr.Button('신규 등록 접수 확인')
                hermes_effect_register_preview.click(review_hermes_effect_registration_draft,[hermes_effect_register_draft,hermes_effect_register_request],[hermes_effect_register_state,hermes_effect_register_comparison,hermes_effect_register_confirm],queue=False)
                hermes_effect_register_save.click(save_hermes_effect_registration_draft,[hermes_effect_register_state,hermes_effect_register_draft,hermes_effect_register_request],[hermes_effect_register_state,hermes_effect_register_confirm,hermes_effect_register_status],trigger_mode='once',concurrency_limit=1)
                hermes_effect_register_cancel.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_effect_register_state,hermes_effect_register_confirm],queue=False)
                hermes_effect_register_receipt.click(read_hermes_effect_registration_status,[hermes_effect_register_request],[hermes_effect_register_status],queue=False)
                for current_register_input in (hermes_effect_register_draft,hermes_effect_register_request):
                    current_register_input.change(lambda:(None,gr.update(visible=False)),outputs=[hermes_effect_register_state,hermes_effect_register_confirm],queue=False)
            with gr.Accordion('웨이포인트 이펙트 교체',open=False):
                gr.Markdown('콘텐츠 DB의 기존 이펙트 ID가 제거됩니다. 게임은 에셋 원본을 직접 참조하므로 이 교체만으로 게임이 바뀌지 않습니다. [이펙트 검수 화면](/management/frame/effect-editor/)에서 외형과 사용 맵을 확인한 뒤 등록된 새 원본을 지정하세요.')
                hermes_waypoint_draft=gr.Code(label='교체 초안 JSON · id, revision, effect',language='json',interactive=True,lines=8)
                hermes_waypoint_request=gr.Textbox(label='교체 접수 ID',value=lambda:uuid.uuid4().hex,interactive=True)
                hermes_waypoint_state=gr.State(None)
                hermes_waypoint_status=gr.Markdown('기존 웨이포인트를 선택하고 교체 초안을 입력하세요.')
                hermes_waypoint_load=gr.Button('선택한 웨이포인트에서 교체 초안 만들기')
                hermes_waypoint_preview=gr.Button('교체 내용 검토')
                with gr.Group(visible=False) as hermes_waypoint_confirm:
                    gr.Markdown('변경 전후, 등록 원본의 해시와 실제 사용 맵을 확인하세요. 교체하면 기존 ID가 제거됩니다.')
                    hermes_waypoint_comparison=gr.JSON(label='교체 검토와 원본 해시')
                    hermes_waypoint_save=gr.Button('확인 후 웨이포인트 교체',variant='primary')
                    hermes_waypoint_cancel=gr.Button('교체하지 않기')
                hermes_waypoint_receipt=gr.Button('교체 접수 확인')
                hermes_waypoint_ledger_button=gr.Button('현재 콘텐츠 DB·원장 상태 조회')
                hermes_waypoint_ledger_status=gr.Markdown('접수에 기록된 저장 시점과 현재 원장 세대는 별도로 확인합니다.')
                hermes_waypoint_load.click(load_hermes_waypoint_replacement_draft,[hermes_effect_choices],[hermes_waypoint_draft,hermes_waypoint_state,hermes_waypoint_confirm,hermes_waypoint_status],queue=False)
                hermes_waypoint_preview.click(review_hermes_waypoint_replacement_draft,[hermes_waypoint_draft,hermes_waypoint_request,hermes_effect_choices],[hermes_waypoint_state,hermes_waypoint_comparison,hermes_waypoint_confirm],queue=False)
                hermes_waypoint_save.click(save_hermes_waypoint_replacement_draft,[hermes_waypoint_state,hermes_waypoint_draft,hermes_waypoint_request,hermes_effect_choices],[hermes_waypoint_state,hermes_waypoint_confirm,hermes_waypoint_status],trigger_mode='once',concurrency_limit=1)
                hermes_waypoint_cancel.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_waypoint_state,hermes_waypoint_confirm],queue=False)
                hermes_waypoint_receipt.click(read_hermes_waypoint_replacement_status,[hermes_waypoint_request],[hermes_waypoint_status],queue=False)
                hermes_waypoint_ledger_button.click(read_hermes_content_database_summary,outputs=[hermes_waypoint_ledger_status],queue=False)
                for current_waypoint_input in (hermes_waypoint_draft,hermes_waypoint_request,hermes_effect_choices):
                    current_waypoint_input.change(lambda:(None,gr.update(visible=False)),outputs=[hermes_waypoint_state,hermes_waypoint_confirm],queue=False)
        with gr.Accordion('빌보드 카탈로그 조회', open=False):
            gr.Markdown('에셋 저장소에 등록된 빌보드의 용도와 표시 속성·사용 맵을 검색합니다. 원본을 수정하지 않습니다.')
            with gr.Row():
                hermes_billboard_category = gr.Dropdown(label='빌보드 분류', choices=[('전체',None),('식생','vegetation'),('초본','herbaceous'),('큰 나무','large-trees'),('바위·광물','rocks-minerals'),('소품','props')], value=None)
                hermes_billboard_query = gr.Textbox(label='빌보드 검색어')
                hermes_billboard_offset = gr.Number(label='조회 시작 위치', value=0, precision=0, minimum=0)
            hermes_billboard_search = gr.Button('빌보드 검색')
            hermes_billboard_next = gr.Button('빌보드 다음 결과', interactive=False)
            hermes_billboard_next_offset = gr.State(None)
            hermes_billboard_catalog_items = gr.State([])
            hermes_billboard_status = gr.Markdown('검색하면 최대 20개를 표시합니다.')
            hermes_billboard_table = gr.Dataframe(headers=['ID','이름','분류','표시 높이','용도','외형 검수','사용 맵'], datatype=['str']*7, interactive=False, type='array', label='빌보드 카탈로그')
            hermes_billboard_detail = gr.JSON(label='선택한 빌보드 상세')
            gr.Markdown('[빌보드 원본과 이미지 검수 화면](/management/frame/asset-editor/)에서 에셋을 확인할 수 있습니다.')
            hermes_billboard_inputs = [hermes_billboard_category, hermes_billboard_query, hermes_billboard_offset]
            hermes_billboard_outputs = [hermes_billboard_table, hermes_billboard_status, hermes_billboard_next_offset, hermes_billboard_next, hermes_billboard_catalog_items, hermes_billboard_detail]
            for hermes_billboard_filter in (hermes_billboard_category, hermes_billboard_query):
                hermes_billboard_filter.change(lambda: (0, None, gr.update(interactive=False), [], '검색 조건이 변경됐습니다. 다시 검색하세요.', [], None), outputs=[hermes_billboard_offset, hermes_billboard_next_offset, hermes_billboard_next, hermes_billboard_table, hermes_billboard_status, hermes_billboard_catalog_items, hermes_billboard_detail], queue=False)
            hermes_billboard_search.click(read_hermes_billboard_catalog_rows, hermes_billboard_inputs, hermes_billboard_outputs, queue=False)
            hermes_billboard_next.click(lambda current_next_value:current_next_value, [hermes_billboard_next_offset], [hermes_billboard_offset], queue=False).then(read_hermes_billboard_catalog_rows, hermes_billboard_inputs, hermes_billboard_outputs, queue=False)
        with gr.Accordion('빌보드 공용 속성 검증과 저장', open=False):
            gr.Markdown('카탈로그의 빌보드 ID를 입력합니다. 변경 전후·사용 맵 경고를 확인한 뒤 저장하세요. 이미지 원본은 수정하지 않습니다.')
            hermes_billboard_edit_id = gr.Textbox(label='편집할 빌보드 ID')
            hermes_billboard_edit_load = gr.Button('빌보드 공용 속성 불러오기')
            hermes_billboard_edit_proposal = gr.Button('선택한 세션 작업의 빌보드 제안 불러오기 · 기존 초안 교체')
            hermes_billboard_edit_original = gr.JSON(label='현재 공용 속성')
            hermes_billboard_edit_draft = gr.Code(label='빌보드 변경 초안 JSON',language='json',interactive=True,lines=8)
            hermes_billboard_edit_request = gr.Textbox(label='빌보드 저장 접수 ID',value=lambda:uuid.uuid4().hex,interactive=True)
            hermes_billboard_edit_state = gr.State(None)
            hermes_billboard_edit_status = gr.Markdown('원본을 불러와 수정할 필드만 입력하세요.')
            hermes_billboard_edit_preview = gr.Button('빌보드 변경 검증')
            with gr.Group(visible=False) as hermes_billboard_edit_confirm:
                hermes_billboard_edit_summary = gr.Markdown()
                hermes_billboard_edit_comparison = gr.JSON(label='변경 전후와 영향 맵·경고')
                with gr.Row():
                    hermes_billboard_edit_cancel = gr.Button('빌보드 저장하지 않기')
                    hermes_billboard_edit_save = gr.Button('확인 후 빌보드 저장',variant='primary')
            hermes_billboard_edit_receipt = gr.Button('빌보드 저장 접수 확인')
            hermes_billboard_table.select(select_hermes_billboard_catalog_item,[hermes_billboard_catalog_items],[hermes_billboard_detail],queue=False).then(lambda current_detail_record:current_detail_record['id'],[hermes_billboard_detail],[hermes_billboard_edit_id],queue=False)
            hermes_billboard_edit_load.click(load_hermes_billboard_edit_draft,[hermes_billboard_edit_id],[hermes_billboard_edit_original,hermes_billboard_edit_draft,hermes_billboard_edit_state,hermes_billboard_edit_confirm,hermes_billboard_edit_status],queue=False)
            hermes_billboard_edit_preview.click(review_hermes_billboard_edit_draft,[hermes_billboard_edit_draft,hermes_billboard_edit_request],[hermes_billboard_edit_state,hermes_billboard_edit_comparison,hermes_billboard_edit_summary,hermes_billboard_edit_confirm],queue=False)
            hermes_billboard_edit_save.click(save_hermes_billboard_edit_draft,[hermes_billboard_edit_state,hermes_billboard_edit_draft,hermes_billboard_edit_request],[hermes_billboard_edit_state,hermes_billboard_edit_confirm,hermes_billboard_edit_status],trigger_mode='once',concurrency_limit=1)
            hermes_billboard_edit_cancel.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_billboard_edit_state,hermes_billboard_edit_confirm],queue=False)
            hermes_billboard_edit_receipt.click(read_hermes_billboard_edit_status,[hermes_billboard_edit_request],[hermes_billboard_edit_status],queue=False)
            for current_billboard_input in (hermes_billboard_edit_id,hermes_billboard_edit_draft,hermes_billboard_edit_request):
                current_billboard_input.change(lambda:(None,gr.update(visible=False)),outputs=[hermes_billboard_edit_state,hermes_billboard_edit_confirm],queue=False)
        with gr.Accordion('도시 맵 초안 검증과 저장', open=False):
            gr.Markdown('콘텐츠 DB가 필요합니다. 도시 원장과 초안의 건물·통행·출구를 확인한 뒤 저장하세요.')
            hermes_city_map_id = gr.Textbox(label='도시 맵 ID',value='iseulon')
            hermes_city_load_button = gr.Button('도시 맵 원장 불러오기')
            hermes_city_draft_text = gr.Code(label='도시 맵 초안 JSON',language='json',interactive=True,lines=12)
            hermes_city_request_id = gr.Textbox(label='도시 맵 저장 접수 ID',value=lambda:uuid.uuid4().hex,interactive=True)
            hermes_city_review_state = gr.State(None)
            hermes_city_status_text = gr.Markdown('도시 원장을 불러와 초안을 검증하세요.')
            hermes_city_review_button = gr.Button('도시 맵 초안 검증')
            with gr.Group(visible=False) as hermes_city_confirm_group:
                hermes_city_review_summary = gr.Markdown()
                with gr.Row():
                    hermes_city_cancel_button = gr.Button('도시 맵 저장하지 않기')
                    hermes_city_save_button = gr.Button('확인 후 도시 맵 저장',variant='primary')
            hermes_city_load_button.click(load_hermes_city_map_draft,[hermes_city_map_id],[hermes_city_draft_text,hermes_city_review_state,hermes_city_confirm_group,hermes_city_status_text],queue=False)
            hermes_city_review_button.click(review_hermes_city_map_draft,[hermes_city_draft_text,hermes_city_request_id],[hermes_city_review_state,hermes_city_review_summary,hermes_city_confirm_group],queue=False)
            hermes_city_save_button.click(save_hermes_city_map_draft,[hermes_city_review_state,hermes_city_draft_text,hermes_city_request_id],[hermes_city_review_state,hermes_city_confirm_group,hermes_city_status_text],trigger_mode='once',concurrency_limit=1)
            hermes_city_cancel_button.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_city_review_state,hermes_city_confirm_group],queue=False)
            hermes_city_history = gr.Dropdown(label='도시 맵 저장 접수 이력',choices=[],interactive=True)
            with gr.Row():
                hermes_city_history_refresh = gr.Button('도시 맵 저장 이력 조회')
                hermes_city_history_open = gr.Button('선택한 도시 맵 접수 확인')
            hermes_city_history_status = gr.Markdown('최근 도시 맵 저장 접수 ID를 복구할 수 있습니다.')
            hermes_city_history_refresh.click(list_hermes_city_map_choices,outputs=[hermes_city_history,hermes_city_history_status],queue=False)
            hermes_city_history_open.click(lambda current_receipt_identifier:current_receipt_identifier,[hermes_city_history],[hermes_city_request_id],queue=False).then(read_hermes_city_map_receipt,[hermes_city_request_id],[hermes_city_status_text],queue=False)
            for current_city_input_value in (hermes_city_draft_text,hermes_city_request_id):
                current_city_input_value.change(lambda:(None,gr.update(visible=False)),outputs=[hermes_city_review_state,hermes_city_confirm_group],queue=False)
        with gr.Accordion('야외 맵 초안 검증과 저장', open=False):
            gr.Markdown('기존 야외 맵 편집기의 초안을 검증합니다. 변경할 셀과 전체 장식 목록을 검토하고 저장하세요. 도시 맵은 지원하지 않습니다.')
            hermes_field_map_id = gr.Textbox(label='야외 맵 ID', value='moss-clearing')
            hermes_field_load_button = gr.Button('야외 맵 원본 불러오기')
            hermes_field_proposal_button = gr.Button('선택한 세션 작업의 맵 제안 불러오기 · 기존 초안 교체')
            hermes_field_source_data = gr.JSON(label='야외 맵 원본과 선택 가능한 항목')
            hermes_field_draft_text = gr.Code(label='야외 맵 초안 JSON', language='json', interactive=True, lines=12)
            hermes_field_request_id = gr.Textbox(label='야외 맵 저장 접수 ID', value=lambda:uuid.uuid4().hex, interactive=True)
            hermes_field_review_state = gr.State(None)
            hermes_field_status_text = gr.Markdown('맵을 불러와 초안을 검증하세요.')
            hermes_field_review_button = gr.Button('야외 맵 초안 검증')
            with gr.Group(visible=False) as hermes_field_confirm_group:
                hermes_field_review_summary = gr.Markdown()
                with gr.Row():
                    hermes_field_cancel_button = gr.Button('저장하지 않기')
                    hermes_field_save_button = gr.Button('확인 후 야외 맵 저장', variant='primary')
            hermes_field_load_button.click(load_hermes_field_map_draft, [hermes_field_map_id], [hermes_field_draft_text,hermes_field_source_data,hermes_field_review_state,hermes_field_confirm_group,hermes_field_status_text], queue=False)
            hermes_field_review_button.click(review_hermes_field_map_draft, [hermes_field_draft_text,hermes_field_request_id], [hermes_field_review_state,hermes_field_review_summary,hermes_field_confirm_group], queue=False)
            hermes_field_save_button.click(save_hermes_field_map_draft, [hermes_field_review_state,hermes_field_draft_text,hermes_field_request_id], [hermes_field_review_state,hermes_field_confirm_group,hermes_field_status_text], trigger_mode='once', concurrency_limit=1)
            hermes_field_cancel_button.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_field_review_state,hermes_field_confirm_group],queue=False)
            hermes_field_history = gr.Dropdown(label='야외 맵 저장 접수 이력',choices=[],interactive=True)
            with gr.Row():
                hermes_field_history_refresh = gr.Button('야외 맵 저장 이력 조회')
                hermes_field_history_open = gr.Button('선택한 맵 저장 접수 확인')
            hermes_field_history_status = gr.Markdown('최근 맵 저장 접수 ID를 복구할 수 있습니다.')
            hermes_field_history_refresh.click(list_hermes_field_map_choices,outputs=[hermes_field_history,hermes_field_history_status],queue=False)
            hermes_field_history_open.click(lambda current_receipt_identifier:current_receipt_identifier,[hermes_field_history],[hermes_field_request_id],queue=False).then(read_hermes_field_map_receipt,[hermes_field_request_id],[hermes_field_status_text],queue=False)
            for current_field_input_value in (hermes_field_draft_text,hermes_field_request_id):
                current_field_input_value.change(lambda:(None,gr.update(visible=False)),outputs=[hermes_field_review_state,hermes_field_confirm_group],queue=False)
        with gr.Accordion('콘텐츠 DB 상태', open=False):
            gr.Markdown('콘텐츠 DB 저장과 원장 반영의 세대를 조회합니다. 연결 실패는 정상 상태로 취급하지 않습니다.')
            hermes_content_status_button = gr.Button('콘텐츠 DB 상태 조회')
            hermes_content_status_text = gr.Markdown('조회하면 저장·원장 반영 상태를 표시합니다.')
            hermes_content_status_button.click(read_hermes_content_database_summary, outputs=[hermes_content_status_text], queue=False)
        with gr.Accordion('이미지·영상·번역·작가 원본 이력', open=False):
            gr.Markdown('Hermes 외 작업도 포함합니다. 중단 작업을 복구하지 않으며 기록 상태와 실제 생존 여부는 다를 수 있습니다.')
            hermes_source_generator = gr.Dropdown(label='생성기',choices=list(SOURCE_HISTORY_GENERATOR_SERVICES),value='flux-image')
            hermes_source_button = gr.Button('원본 이력 조회')
            hermes_source_status = gr.Markdown('최근 30건의 기록을 조회합니다.')
            hermes_source_table = gr.Dataframe(headers=['작업 ID','기록 상태','상태 출처'],datatype=['str','str','str'],interactive=False,type='array',label='생성기 원본 이력')
            hermes_source_state = gr.State(None)
            hermes_source_next = gr.Button('다음 원본 이력',interactive=False)
            hermes_source_outputs=[hermes_source_table,hermes_source_status,hermes_source_state,hermes_source_next]
            hermes_source_button.click(read_hermes_generator_source_rows,[hermes_source_generator],hermes_source_outputs,queue=False)
            hermes_source_next.click(read_next_hermes_generator_source_rows,[hermes_source_generator,hermes_source_state],hermes_source_outputs,queue=False)
            hermes_source_generator.change(clear_hermes_source_history,outputs=hermes_source_outputs,queue=False)
        with gr.Accordion('모델 준비 상태', open=False):
            from tools.review.common.model_management_catalog import MODEL_PREPARATION_SERVICES
            hermes_kimodo_build_button = gr.Button('Kimodo MIGraphX 빌드 상태 확인')
            hermes_kimodo_build_status = gr.Markdown('최근 빌드 기록만 조회합니다. 캐시 유효성 검사와 빌드 요청은 모델 관리에서 수행합니다.')
            hermes_kimodo_build_button.click(read_hermes_kimodo_build_summary, outputs=[hermes_kimodo_build_status], queue=False)
            hermes_model_readiness_selection = gr.Dropdown(label='모델 서비스', choices=[(label,name) for label,name in MODEL_PREPARATION_SERVICES], value='flux-image')
            hermes_model_readiness_button = gr.Button('모델 준비 상태 조회')
            hermes_model_readiness_status = gr.Markdown('상태 조회는 로컬 잠금 파일을 만들 수 있습니다. 모델 실행 또는 다운로드는 하지 않습니다.')
            hermes_model_readiness_button.click(read_hermes_model_readiness_summary, [hermes_model_readiness_selection], [hermes_model_readiness_status], queue=False)
            hermes_model_preparation_request = gr.Textbox(label='모델 준비 접수 ID', value=lambda:uuid.uuid4().hex, interactive=True)
            with gr.Row():
                hermes_model_preparation_review_button = gr.Button('모델 준비 검토')
                hermes_model_preparation_receipt_button = gr.Button('접수 기록 확인')
                hermes_model_preparation_new_button = gr.Button('새 접수 ID')
            hermes_model_preparation_state = gr.State(None)
            hermes_model_preparation_result = gr.Markdown('모델 준비는 검토와 확인 후 요청합니다. 완료 여부는 모델 준비 상태에서 별도로 확인하세요.')
            with gr.Group(visible=False) as hermes_model_preparation_confirm_group:
                hermes_model_preparation_summary = gr.Markdown()
                with gr.Row():
                    hermes_model_preparation_cancel = gr.Button('준비하지 않기')
                    hermes_model_preparation_submit = gr.Button('확인 후 모델 준비 요청', variant='primary')
            hermes_model_preparation_review_button.click(review_hermes_model_preparation, [hermes_model_readiness_selection, hermes_model_preparation_request], [hermes_model_preparation_state, hermes_model_preparation_summary, hermes_model_preparation_confirm_group], queue=False)
            hermes_model_preparation_submit.click(submit_hermes_model_preparation, [hermes_model_preparation_state, hermes_model_readiness_selection, hermes_model_preparation_request], [hermes_model_preparation_state, hermes_model_preparation_confirm_group, hermes_model_preparation_result], trigger_mode='once', concurrency_limit=1)
            hermes_model_preparation_cancel.click(lambda:(None,gr.update(visible=False)), outputs=[hermes_model_preparation_state,hermes_model_preparation_confirm_group], queue=False)
            hermes_model_preparation_receipt_button.click(read_hermes_model_preparation_receipt, [hermes_model_readiness_selection,hermes_model_preparation_request], [hermes_model_preparation_result], queue=False)
            hermes_model_preparation_new_button.click(lambda:uuid.uuid4().hex, outputs=[hermes_model_preparation_request], queue=False)
            hermes_model_preparation_history = gr.Dropdown(label='모델 준비 접수 이력', choices=[], interactive=True)
            with gr.Row():
                hermes_model_preparation_history_refresh = gr.Button('모델 준비 이력 조회')
                hermes_model_preparation_history_select = gr.Button('선택한 접수 열기')
            hermes_model_preparation_history_status = gr.Markdown('최근 접수 ID를 확인할 수 있습니다.')
            hermes_model_preparation_history_refresh.click(list_hermes_model_preparation_choices, outputs=[hermes_model_preparation_history,hermes_model_preparation_history_status], queue=False)
            hermes_model_preparation_history_select.click(select_hermes_model_preparation_receipt, [hermes_model_preparation_history], [hermes_model_readiness_selection,hermes_model_preparation_request], queue=False).then(read_hermes_model_preparation_receipt, [hermes_model_readiness_selection,hermes_model_preparation_request], [hermes_model_preparation_result], queue=False)
            for current_model_preparation_input in (hermes_model_readiness_selection, hermes_model_preparation_request):
                current_model_preparation_input.change(lambda:(None,gr.update(visible=False)), outputs=[hermes_model_preparation_state,hermes_model_preparation_confirm_group], queue=False)
        with gr.Accordion('모델 파일 보유량', open=False):
            hermes_model_inventory_button = gr.Button('모델 파일 보유량 조회')
            hermes_model_inventory_status = gr.Markdown('조회하면 모델별 파일 수와 용량을 표시합니다.')
            hermes_model_inventory_table = gr.Dataframe(headers=['서비스', '파일 수', '바이트', '조사 상태'], datatype=['str','str','str','str'], interactive=False, type='array', label='모델 파일 보유량')
            hermes_model_inventory_button.click(read_hermes_model_inventory_rows, outputs=[hermes_model_inventory_table, hermes_model_inventory_status], queue=False)
        with gr.Group():
            gr.Markdown('### 대화 세션\n이전 작업이 끝난 뒤 후속 메시지를 보낼 수 있습니다. 각 메시지는 새 격리 사본에서 실행됩니다.')
            with gr.Row():
                hermes_session_control = gr.Dropdown(label='세션', choices=[], interactive=True)
                hermes_new_session_button = gr.Button('새 세션')
                hermes_session_list_button = gr.Button('세션 목록 새로고침')
            hermes_session_draft = gr.State(value=lambda: uuid.uuid4().hex)
            hermes_session_request = gr.State(value=lambda: uuid.uuid4().hex)
            hermes_session_list_status = gr.Markdown('세션 목록을 확인하고 있습니다.')
            hermes_session_conversation = gr.Chatbot(label='대화', value=[], height=260, placeholder='세션을 만들거나 선택하면 대화가 표시됩니다.', render_markdown=False, allow_file_downloads=False)
            hermes_session_status = gr.Markdown('세션을 선택하거나 새로 만드세요.')
            with gr.Row():
                hermes_session_job_selection = gr.Dropdown(label='세션 작업 선택', choices=[], interactive=True)
                hermes_session_job_open = gr.Button('선택 작업 상세 열기')
            hermes_billboard_edit_proposal.click(load_hermes_billboard_edit_proposal,[hermes_session_job_selection],[hermes_billboard_edit_id,hermes_billboard_edit_original,hermes_billboard_edit_draft,hermes_billboard_edit_request,hermes_billboard_edit_state,hermes_billboard_edit_confirm,hermes_billboard_edit_status],queue=False)
            hermes_effect_edit_proposal.click(load_hermes_effect_edit_proposal,[hermes_session_job_selection],[hermes_effect_choices,hermes_effect_detail,hermes_effect_edit_draft,hermes_effect_edit_request,hermes_effect_edit_state,hermes_effect_edit_confirm,hermes_effect_edit_status],queue=False)
            hermes_sprite_edit_proposal.click(load_hermes_sprite_anchor_proposal,[hermes_session_job_selection],[hermes_sprite_choices,hermes_sprite_edit_draft,hermes_sprite_edit_request,hermes_sprite_edit_state,hermes_sprite_edit_confirm,hermes_sprite_edit_status],queue=False)
            hermes_field_proposal_button.click(load_hermes_field_map_proposal,[hermes_session_job_selection],[hermes_field_map_id,hermes_field_draft_text,hermes_field_source_data,hermes_field_request_id,hermes_field_review_state,hermes_field_confirm_group,hermes_field_status_text],queue=False)
            hermes_session_timer = gr.Timer(value=10, active=False)
            with gr.Row():
                hermes_session_prompt = gr.Textbox(label='세션 메시지', lines=3, max_lines=10)
                hermes_session_send = gr.Button('메시지 대기열 접수', interactive=False)
                hermes_session_refresh = gr.Button('대화 상태 새로고침')
                hermes_session_recover = gr.Button('미확인 요청 복원')
            hermes_session_verification = gr.Textbox(label='세션 작업 검증 모듈 · 선택', lines=2, placeholder='tools.review.tests.test_hermes_service')
            hermes_session_job = gr.Textbox(label='세션 작업 ID', interactive=False)
            hermes_session_submit_status = gr.Markdown('세션과 메시지를 선택하세요.')
            hermes_new_session_button.click(create_hermes_session_from_draft, [hermes_session_draft], [hermes_session_control, hermes_session_draft, hermes_session_list_status], queue=False)
            hermes_session_list_button.click(list_hermes_session_choices, [hermes_session_control], [hermes_session_control, hermes_session_list_status], queue=False)
            hermes_session_control.change(read_hermes_session_conversation, [hermes_session_control, hermes_session_job_selection], [hermes_session_conversation, hermes_session_status, hermes_session_timer, hermes_session_job_selection], queue=False)
            hermes_session_refresh.click(read_hermes_session_conversation, [hermes_session_control, hermes_session_job_selection], [hermes_session_conversation, hermes_session_status, hermes_session_timer, hermes_session_job_selection], queue=False)
            hermes_session_timer.tick(read_hermes_session_conversation, [hermes_session_control, hermes_session_job_selection], [hermes_session_conversation, hermes_session_status, hermes_session_timer, hermes_session_job_selection], queue=False)
            hermes_session_recover.click(recover_hermes_session_request, [hermes_session_control], [hermes_session_request, hermes_session_prompt, hermes_session_verification, hermes_session_submit_status], queue=False)
            bind_gpu_generation_confirmation(hermes_session_send, submit_hermes_session_request, [hermes_session_control, hermes_session_request, hermes_session_prompt, hermes_session_verification], [hermes_session_job, hermes_session_submit_status, hermes_session_request, hermes_session_timer], generation_readiness_callback=lambda current_session_id, current_message_text: bool(current_session_id and (current_message_text or '').strip()), generation_readiness_inputs=[hermes_session_control, hermes_session_prompt], generation_confirmation_validator=match_hermes_confirmation_inputs, generation_confirmation_inputs=[hermes_session_control, hermes_session_request, hermes_session_prompt, hermes_session_verification])
            hermes_interface_blocks.load(list_hermes_session_choices, inputs=[hermes_session_control], outputs=[hermes_session_control, hermes_session_list_status], queue=False)
        with gr.Accordion('Kimodo 키프레임 찾기',open=False):
            gr.Markdown('기존 키프레임 기록을 검색하고 원본을 검증할 수 있습니다. 전체 동작의 품질은 별도 확인하세요.')
            with gr.Row():
                hermes_keyframe_query=gr.Textbox(label='ID 또는 태그')
                hermes_keyframe_offset=gr.Number(label='조회 시작 위치',value=0,precision=0,minimum=0)
                hermes_keyframe_search=gr.Button('키프레임 검색')
            hermes_keyframe_next=gr.Button('다음 키프레임',interactive=False)
            hermes_keyframe_next_state=gr.State(None)
            hermes_keyframe_rows=gr.Dataframe(headers=['ID','태그','원본 프레임'],datatype=['str','str','number'],interactive=False,type='array')
            hermes_keyframe_status=gr.Markdown('검색하면 최대 20개를 표시합니다.')
            hermes_keyframe_search.click(read_hermes_kimodo_keyframe_rows,[hermes_keyframe_query,hermes_keyframe_offset],[hermes_keyframe_rows,hermes_keyframe_status,hermes_keyframe_next_state,hermes_keyframe_next],queue=False)
            hermes_keyframe_next.click(read_next_hermes_kimodo_keyframe_rows,[hermes_keyframe_query,hermes_keyframe_next_state],[hermes_keyframe_offset,hermes_keyframe_rows,hermes_keyframe_status,hermes_keyframe_next_state,hermes_keyframe_next],queue=False)
            hermes_keyframe_query.change(lambda:(None,gr.update(interactive=False)),outputs=[hermes_keyframe_next_state,hermes_keyframe_next],queue=False)
            hermes_keyframe_preview_id=gr.Textbox(label='미리볼 키프레임 ID')
            hermes_keyframe_rows.select(select_hermes_kimodo_keyframe_row,[hermes_keyframe_rows],[hermes_keyframe_preview_id],queue=False)
            hermes_keyframe_preview_button=gr.Button('키프레임 원본 검증·미리보기')
            hermes_keyframe_preview_image=gr.Image(label='키프레임 미리보기',interactive=False,type='pil')
            hermes_keyframe_preview_status=gr.Markdown('목록에서 ID를 입력하세요.')
            hermes_keyframe_search.click(lambda:('',None,'목록에서 키프레임을 선택하세요.'),outputs=[hermes_keyframe_preview_id,hermes_keyframe_preview_image,hermes_keyframe_preview_status],queue=False)
            hermes_keyframe_next.click(lambda:('',None,'목록에서 키프레임을 선택하세요.'),outputs=[hermes_keyframe_preview_id,hermes_keyframe_preview_image,hermes_keyframe_preview_status],queue=False)
            hermes_keyframe_preview_button.click(read_hermes_kimodo_keyframe_preview_image,[hermes_keyframe_preview_id],[hermes_keyframe_preview_image,hermes_keyframe_preview_status],queue=False)
            hermes_keyframe_preview_id.change(lambda:(None,'선택한 키프레임을 다시 검증하세요.'),outputs=[hermes_keyframe_preview_image,hermes_keyframe_preview_status],queue=False)
        with gr.Accordion('Kimodo 작업 위임', open=False):
            gr.Markdown('모션 생성 입력을 검토하고 공용 GPU 대기열에 접수합니다. 접수와 완료는 별도이며, 응답 유실 시 같은 접수 ID와 입력을 유지하세요. [Kimodo 작업과 이력 보기](/management/frame/kimodo-generator/)')
            hermes_delegate_prompt = gr.Textbox(label='Kimodo 동작 지시', lines=3)
            with gr.Row():
                hermes_delegate_frames = gr.Number(label='프레임 수', value=90, precision=0)
                hermes_delegate_steps = gr.Number(label='생성 단계', value=100, precision=0)
                hermes_delegate_seed = gr.Number(label='시드', value=42, precision=0)
            hermes_delegate_keyframes = gr.Code(label='키프레임 배치 JSON · id와 출력 frame · 선택 사항',language='json',value='[]',lines=3)
            with gr.Row():
                hermes_keyframe_output_frame=gr.Number(label='선택한 키프레임의 출력 프레임',value=1,precision=0,minimum=1)
                hermes_keyframe_append=gr.Button('선택 키프레임을 배치에 추가')
                hermes_keyframe_verify=gr.Button('배치된 원본 모두 검증')
            hermes_keyframe_append.click(append_hermes_kimodo_keyframe_placement,[hermes_delegate_keyframes,hermes_keyframe_preview_id,hermes_keyframe_output_frame,hermes_delegate_frames],[hermes_delegate_keyframes],queue=False)
            hermes_keyframe_verify_status=gr.Textbox(label='키프레임 검증 결과',interactive=False,lines=3)
            hermes_keyframe_verify.click(verify_hermes_kimodo_keyframe_placements,[hermes_delegate_keyframes,hermes_delegate_frames],[hermes_keyframe_verify_status],queue=False)
            hermes_delegate_keyframes.change(lambda:'배치가 변경됐습니다. 다시 검증하세요.',outputs=[hermes_keyframe_verify_status],queue=False)
            hermes_delegate_frames.change(lambda:'출력 프레임 수가 변경됐습니다. 배치를 다시 검증하세요.',outputs=[hermes_keyframe_verify_status],queue=False)
            hermes_delegate_request_id = gr.Textbox(label='위임 접수 ID', value=lambda: uuid.uuid4().hex, interactive=True, info='응답 유실 시 같은 ID와 입력을 사용하세요. 새 작업에는 새 ID를 입력하세요.')
            hermes_delegate_review_state = gr.State(None)
            hermes_delegate_proposal = gr.Button('선택한 세션 작업의 Hermes 제안 불러오기')
            hermes_delegate_review = gr.Button('위임 입력 검토')
            hermes_delegate_review_status = gr.Markdown('동작 지시를 입력하고 위임 입력을 검토하세요.')
            hermes_delegate_review_json = gr.Textbox(label='확정할 위임 입력', lines=6, interactive=False)
            hermes_delegate_review_event = hermes_delegate_review.click(review_hermes_kimodo_request, [hermes_delegate_prompt, hermes_delegate_frames, hermes_delegate_steps, hermes_delegate_seed, hermes_delegate_request_id, hermes_delegate_keyframes], [hermes_delegate_review_state, hermes_delegate_review_json, hermes_delegate_review_status], queue=False)
            hermes_delegate_submit = gr.Button('검토한 위임 대기열에 추가', interactive=False)
            hermes_delegate_proposal.click(load_hermes_kimodo_proposal, [hermes_session_job_selection], [hermes_delegate_prompt, hermes_delegate_frames, hermes_delegate_steps, hermes_delegate_seed, hermes_delegate_request_id, hermes_delegate_review_state, hermes_delegate_review_json, hermes_delegate_review_status, hermes_delegate_submit], queue=False).then(lambda:'[]',outputs=[hermes_delegate_keyframes],queue=False)
            hermes_delegate_review_inputs = [hermes_delegate_prompt, hermes_delegate_frames, hermes_delegate_steps, hermes_delegate_seed, hermes_delegate_request_id, hermes_delegate_keyframes]
            for current_delegate_input in hermes_delegate_review_inputs:
                current_delegate_input.change(invalidate_hermes_kimodo_review, [hermes_delegate_review_state, *hermes_delegate_review_inputs], [hermes_delegate_review_state, hermes_delegate_review_json, hermes_delegate_review_status, hermes_delegate_submit], queue=False)
            hermes_delegate_job = gr.Textbox(label='Kimodo 작업 ID', interactive=True)
            hermes_delegate_receipt = gr.Button('위임 접수 ID로 확인')
            hermes_delegate_history = gr.Dropdown(label='위임 접수 이력', choices=[], interactive=True)
            hermes_delegate_history_refresh = gr.Button('위임 접수 이력 새로고침')
            hermes_delegate_history_open = gr.Button('선택한 위임 접수 확인')
            hermes_delegate_history_status = gr.Markdown('이력 새로고침으로 이전 접수를 확인하세요.')
            hermes_delegate_status = gr.Markdown('접수된 작업이 없습니다.')
            hermes_delegate_job_refresh = gr.Button('Kimodo 작업 상태 조회')
            hermes_delegate_job_details = gr.Textbox(label='Kimodo 작업 상태', lines=4, interactive=False)
            hermes_cancel_review_button = gr.Button('위임 작업 중지 요청 검토')
            hermes_cancel_state = gr.State(None)
            with gr.Group(visible=False) as hermes_cancel_confirmation:
                hermes_cancel_summary = gr.Markdown()
                with gr.Row():
                    hermes_cancel_dismiss = gr.Button('중지하지 않기')
                    hermes_cancel_confirm = gr.Button('확인 후 중지 요청')
            hermes_cancel_review_button.click(review_hermes_kimodo_cancellation, [hermes_delegate_request_id, hermes_delegate_job], [hermes_cancel_state, hermes_cancel_confirmation, hermes_cancel_summary], queue=False)
            hermes_cancel_dismiss.click(lambda: (None, gr.update(visible=False)), outputs=[hermes_cancel_state, hermes_cancel_confirmation], queue=False)
            hermes_cancel_confirm.click(submit_hermes_kimodo_cancellation, [hermes_cancel_state], [hermes_cancel_state, hermes_cancel_confirmation, hermes_delegate_status], queue=False)

            hermes_delegate_history_refresh.click(list_hermes_delegation_choices, [hermes_delegate_history], [hermes_delegate_history, hermes_delegate_history_status], queue=False)
            hermes_delegate_history_open.click(select_hermes_delegation_receipt, [hermes_delegate_history], [hermes_delegate_request_id, hermes_delegate_job, hermes_delegate_status, hermes_delegate_review_state, hermes_delegate_review_json, hermes_cancel_state, hermes_cancel_confirmation, hermes_delegate_submit], queue=False)
            hermes_delegate_receipt.click(read_hermes_delegation_receipt, [hermes_delegate_request_id], [hermes_delegate_job, hermes_delegate_status], queue=False)
            hermes_delegate_job_refresh.click(read_hermes_kimodo_job, [hermes_delegate_job], [hermes_delegate_job_details], queue=False)
            bind_gpu_generation_confirmation(hermes_delegate_submit, submit_hermes_kimodo_reviewed_request, [hermes_delegate_review_state, *hermes_delegate_review_inputs], [hermes_delegate_job, hermes_delegate_status], generation_readiness_callback=lambda current_review_value: bool(current_review_value), generation_readiness_inputs=[hermes_delegate_review_state], generation_readiness_events=[hermes_delegate_review_event], generation_confirmation_validator=match_hermes_confirmation_inputs, generation_confirmation_inputs=[hermes_delegate_review_state, *hermes_delegate_review_inputs])
        with gr.Accordion('작가 AI 작업 위임', open=False):
            gr.Markdown('문서 색인 갱신, 작성 제안 또는 중복 검토를 공용 GPU 대기열에 접수합니다. 전체 변경과 근거는 [작가 AI 화면](/management/frame/writer-agent/)에서 확인하고, 적용은 아래 확인 절차를 사용합니다.')
            hermes_writer_mode = gr.Dropdown(label='작가 AI 작업 종류',choices=[('문서 색인 갱신','learn'),('작성 제안','write'),('중복 검토','deduplicate')],value='write')
            hermes_writer_prompt = gr.Textbox(label='작가 AI 작업 지시',lines=4)
            hermes_writer_request_id = gr.Textbox(label='작가 AI 위임 접수 ID',value=lambda:uuid.uuid4().hex,interactive=True)
            hermes_writer_review_state = gr.State(None)
            hermes_writer_review_button = gr.Button('작가 AI 입력 검토')
            hermes_writer_preview = gr.Markdown()
            hermes_writer_status = gr.Markdown('작업 종류와 지시를 검토하세요.')
            hermes_writer_submit = gr.Button('작가 AI GPU 대기열에 추가',interactive=False)
            hermes_writer_job_id = gr.Textbox(label='작가 AI 작업 ID',interactive=False)
            hermes_writer_inputs = [hermes_writer_mode,hermes_writer_prompt,hermes_writer_request_id]
            hermes_writer_review_event = hermes_writer_review_button.click(review_hermes_writer_request,hermes_writer_inputs,[hermes_writer_review_state,hermes_writer_preview,hermes_writer_status,hermes_writer_submit],queue=False)
            for current_writer_input in hermes_writer_inputs:
                current_writer_input.change(lambda:(None,'','입력이 변경되어 다시 검토해야 합니다.',gr.update(interactive=False)),outputs=[hermes_writer_review_state,hermes_writer_preview,hermes_writer_status,hermes_writer_submit],queue=False)
            bind_gpu_generation_confirmation(hermes_writer_submit,submit_hermes_writer_reviewed,[hermes_writer_review_state,*hermes_writer_inputs],[hermes_writer_job_id,hermes_writer_status],generation_readiness_callback=lambda current_review_value:bool(current_review_value),generation_readiness_inputs=[hermes_writer_review_state],generation_readiness_events=[hermes_writer_review_event],generation_confirmation_validator=match_hermes_confirmation_inputs,generation_confirmation_inputs=[hermes_writer_review_state,*hermes_writer_inputs])
            hermes_writer_read_button = gr.Button('작가 AI 상태·제안 조회')
            hermes_writer_result = gr.JSON(label='작가 AI 제안과 제한된 diff')
            hermes_writer_read_button.click(read_hermes_writer_result,[hermes_writer_request_id],[hermes_writer_job_id,hermes_writer_status,hermes_writer_result],queue=False)
            hermes_writer_reservation_job=gr.Textbox(label='예약을 확인할 작가 작업 ID',interactive=True)
            hermes_writer_reservation_request=gr.Textbox(label='작가 GPU 예약 정리 접수 ID',value=lambda:uuid.uuid4().hex,interactive=True)
            hermes_writer_reservation_button=gr.Button('작가 GPU 예약 신원 확인')
            hermes_writer_reservation_result=gr.JSON(label='작가 예약 확인 결과')
            hermes_writer_reservation_status=gr.Markdown('실행기와 작업자 그룹 신원을 확인합니다.')
            hermes_writer_reservation_state=gr.State(None)
            with gr.Group(visible=False) as hermes_writer_reservation_confirm_group:
                gr.Markdown('확인된 작업자 그룹을 강제 종료합니다. 별도 그룹 프로세스는 자동으로 확인하지 못합니다.')
                hermes_writer_outside_checked=gr.Checkbox(label='별도 그룹의 GPU 프로세스를 확인했습니다',value=False)
                hermes_writer_reservation_confirm=gr.Button('작가 그룹 종료와 예약 해제',variant='stop')
            hermes_writer_reservation_receipt=gr.Button('작가 예약 정리 접수 확인')
            hermes_writer_job_id.change(lambda current_job_identifier:current_job_identifier,[hermes_writer_job_id],[hermes_writer_reservation_job],queue=False)
            hermes_writer_reservation_button.click(review_hermes_writer_reservation_recovery,[hermes_writer_reservation_job,hermes_writer_reservation_request],[hermes_writer_reservation_state,hermes_writer_reservation_result,hermes_writer_reservation_confirm_group,hermes_writer_reservation_status],queue=False)
            hermes_writer_reservation_confirm.click(submit_hermes_writer_reservation_recovery,[hermes_writer_reservation_state,hermes_writer_reservation_request,hermes_writer_reservation_job,hermes_writer_outside_checked],[hermes_writer_reservation_state,hermes_writer_reservation_confirm_group,hermes_writer_reservation_status],queue=False)
            hermes_writer_reservation_receipt.click(read_hermes_writer_reservation_recovery_receipt,[hermes_writer_reservation_request],[hermes_writer_reservation_status],queue=False)
            for current_reservation_input in (hermes_writer_reservation_job,hermes_writer_reservation_request):
                current_reservation_input.change(lambda:(None,gr.update(visible=False),False),outputs=[hermes_writer_reservation_state,hermes_writer_reservation_confirm_group,hermes_writer_outside_checked],queue=False)
            hermes_writer_cancel_review=gr.Button('작가 작업 중지 검토')
            hermes_writer_cancel_state=gr.State(None)
            with gr.Group(visible=False) as hermes_writer_cancel_group:
                hermes_writer_cancel_summary=gr.Markdown()
                with gr.Row():
                    hermes_writer_cancel_back=gr.Button('중지하지 않기')
                    hermes_writer_cancel_confirm=gr.Button('작가 작업 중지 요청',variant='stop')
            hermes_writer_cancel_review.click(review_hermes_writer_cancellation,[hermes_writer_request_id,hermes_writer_job_id],[hermes_writer_cancel_state,hermes_writer_cancel_group,hermes_writer_cancel_summary],queue=False)
            hermes_writer_cancel_confirm.click(submit_hermes_writer_cancellation,[hermes_writer_cancel_state,hermes_writer_request_id,hermes_writer_job_id],[hermes_writer_cancel_state,hermes_writer_cancel_group,hermes_writer_status],queue=False)
            hermes_writer_cancel_back.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_writer_cancel_state,hermes_writer_cancel_group],queue=False)
            for current_writer_cancel_input in (hermes_writer_request_id,hermes_writer_job_id):
                current_writer_cancel_input.change(lambda:(None,gr.update(visible=False)),outputs=[hermes_writer_cancel_state,hermes_writer_cancel_group],queue=False)
            hermes_writer_history = gr.Dropdown(label='작가 AI 위임 접수 이력',choices=[],interactive=True)
            with gr.Row():
                hermes_writer_history_refresh = gr.Button('작가 AI 위임 이력 조회')
                hermes_writer_history_open = gr.Button('선택한 작가 AI 접수 확인')
            hermes_writer_history_status = gr.Markdown('Hermes를 통해 접수한 작가 작업만 표시합니다.')
            hermes_writer_history_refresh.click(list_hermes_writer_choices,outputs=[hermes_writer_history,hermes_writer_history_status],queue=False)
            hermes_writer_history_open.click(lambda current_request_value:current_request_value,[hermes_writer_history],[hermes_writer_request_id],queue=False).then(read_hermes_writer_result,[hermes_writer_request_id],[hermes_writer_job_id,hermes_writer_status,hermes_writer_result],queue=False)
            with gr.Accordion('작가 AI 제안 원본 적용',open=False):
                gr.Markdown('작가 AI 화면에서 전체 변경과 근거를 검토하세요. 적용하면 원본 문서가 변경되며 이후 색인 갱신이 필요합니다.')
                hermes_writer_apply_id = gr.Textbox(label='작가 제안 적용 접수 ID',value=lambda:uuid.uuid4().hex,interactive=True)
                hermes_writer_apply_checked = gr.Checkbox(label='작가 AI 화면의 전체 변경과 근거를 확인했습니다',value=False)
                hermes_writer_apply_review = gr.Button('작가 제안 적용 검토')
                hermes_writer_apply_state = gr.State(None)
                hermes_writer_apply_diff = gr.JSON(label='적용할 작가 제안과 전체 diff')
                with gr.Group(visible=False) as hermes_writer_apply_group:
                    hermes_writer_apply_summary = gr.Markdown()
                    with gr.Row():
                        hermes_writer_apply_cancel = gr.Button('작가 제안 적용하지 않기')
                        hermes_writer_apply_confirm = gr.Button('확인 후 작가 제안 적용',variant='primary')
                hermes_writer_apply_status = gr.Markdown('전체 변경과 근거를 확인한 뒤 적용을 검토하세요.')
                hermes_writer_apply_review.click(review_hermes_writer_apply,[hermes_writer_request_id,hermes_writer_apply_id,hermes_writer_apply_checked],[hermes_writer_apply_state,hermes_writer_apply_diff,hermes_writer_apply_group,hermes_writer_apply_summary],queue=False)
                hermes_writer_apply_confirm.click(submit_hermes_writer_apply,[hermes_writer_apply_state,hermes_writer_request_id,hermes_writer_apply_id,hermes_writer_apply_checked],[hermes_writer_apply_state,hermes_writer_apply_group,hermes_writer_apply_status],trigger_mode='once',concurrency_limit=1)
                hermes_writer_apply_cancel.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_writer_apply_state,hermes_writer_apply_group],queue=False)
                for current_writer_apply_input in (hermes_writer_request_id,hermes_writer_apply_id,hermes_writer_apply_checked):
                    current_writer_apply_input.change(lambda:(None,gr.update(visible=False)),outputs=[hermes_writer_apply_state,hermes_writer_apply_group],queue=False)
                hermes_writer_apply_history = gr.Dropdown(label='작가 제안 적용 이력',choices=[],interactive=True)
                with gr.Row():
                    hermes_writer_apply_history_refresh = gr.Button('작가 제안 적용 이력 조회')
                    hermes_writer_apply_history_open = gr.Button('선택한 작가 적용 접수 확인')
                hermes_writer_apply_history_status = gr.Markdown('Hermes를 통한 적용 접수를 확인합니다.')
                hermes_writer_apply_history_refresh.click(list_hermes_writer_apply_choices,outputs=[hermes_writer_apply_history,hermes_writer_apply_history_status],queue=False)
                hermes_writer_apply_history_open.click(lambda current_request_value:current_request_value,[hermes_writer_apply_history],[hermes_writer_apply_id],queue=False).then(read_hermes_writer_apply_receipt,[hermes_writer_apply_id],[hermes_writer_apply_status],queue=False)
        with gr.Accordion('프롬프트 번역 위임', open=False):
            gr.Markdown('한국어 원문을 영어 또는 중국어 간체로 번역합니다. 승인 용어 검증과 공용 GPU 대기열을 사용하며 결과의 용어·조건 검토 항목을 확인하세요.')
            hermes_translation_source = gr.Textbox(label='번역할 한국어 원문',lines=4)
            hermes_translation_target = gr.Dropdown(label='번역 목표 언어',choices=[('영어','en'),('중국어 간체','zh-CN')],value='en')
            hermes_translation_glossary = gr.Textbox(label='번역 확인 용어 · 원문 => 번역어',lines=2)
            hermes_translation_request_id = gr.Textbox(label='번역 위임 접수 ID',value=lambda:uuid.uuid4().hex,interactive=True)
            hermes_translation_review_state = gr.State(None)
            hermes_translation_proposal_button = gr.Button('선택한 세션 작업의 번역 제안 불러오기 · 기존 입력 교체')
            hermes_translation_review_button = gr.Button('번역 입력 검토')
            hermes_translation_preview = gr.Markdown()
            hermes_translation_status = gr.Markdown('번역 입력을 검토하세요.')
            hermes_translation_submit = gr.Button('번역 GPU 대기열에 추가',interactive=False)
            hermes_translation_job_id = gr.Textbox(label='번역 작업 ID',interactive=True)
            hermes_translation_inputs = [hermes_translation_source,hermes_translation_target,hermes_translation_glossary,hermes_translation_request_id]
            hermes_translation_review_event = hermes_translation_review_button.click(review_hermes_translation_request,hermes_translation_inputs,[hermes_translation_review_state,hermes_translation_preview,hermes_translation_status,hermes_translation_submit],queue=False)
            hermes_translation_proposal_button.click(load_hermes_translation_proposal,[hermes_session_job_selection],[hermes_translation_source,hermes_translation_target,hermes_translation_glossary,hermes_translation_request_id,hermes_translation_review_state,hermes_translation_preview,hermes_translation_status,hermes_translation_submit],queue=False)
            for current_translation_input in hermes_translation_inputs:
                current_translation_input.change(lambda:(None,'','입력이 변경되어 다시 검토해야 합니다.',gr.update(interactive=False)),outputs=[hermes_translation_review_state,hermes_translation_preview,hermes_translation_status,hermes_translation_submit],queue=False)
            bind_gpu_generation_confirmation(hermes_translation_submit,submit_hermes_translation_reviewed,[hermes_translation_review_state,*hermes_translation_inputs],[hermes_translation_job_id,hermes_translation_status],generation_readiness_callback=lambda current_review_value:bool(current_review_value),generation_readiness_inputs=[hermes_translation_review_state],generation_readiness_events=[hermes_translation_review_event],generation_confirmation_validator=match_hermes_confirmation_inputs,generation_confirmation_inputs=[hermes_translation_review_state,*hermes_translation_inputs])
            hermes_translation_read_button = gr.Button('번역 상태·결과 조회')
            hermes_translation_result = gr.JSON(label='번역 결과와 검토 항목')
            hermes_translation_read_button.click(read_hermes_translation_result,[hermes_translation_request_id],[hermes_translation_job_id,hermes_translation_status,hermes_translation_result],queue=False)
            hermes_translation_history = gr.Dropdown(label='번역 위임 접수 이력',choices=[],interactive=True)
            with gr.Row():
                hermes_translation_history_refresh = gr.Button('번역 위임 이력 조회')
                hermes_translation_history_open = gr.Button('선택한 번역 접수 확인')
            hermes_translation_history_status = gr.Markdown('Hermes를 통해 접수한 번역만 표시합니다.')
            hermes_translation_history_refresh.click(list_hermes_translation_choices,outputs=[hermes_translation_history,hermes_translation_history_status],queue=False)
            hermes_translation_history_open.click(lambda current_request_value:current_request_value,[hermes_translation_history],[hermes_translation_request_id],queue=False).then(read_hermes_translation_result,[hermes_translation_request_id],[hermes_translation_job_id,hermes_translation_status,hermes_translation_result],queue=False)
            hermes_translation_cancel_review = gr.Button('번역 작업 중지 검토')
            hermes_translation_cancel_state = gr.State(None)
            with gr.Group(visible=False) as hermes_translation_cancel_group:
                hermes_translation_cancel_summary = gr.Markdown()
                with gr.Row():
                    hermes_translation_cancel_back = gr.Button('번역 중지하지 않기')
                    hermes_translation_cancel_confirm = gr.Button('확인 후 번역 중지 요청')
            hermes_translation_cancel_review.click(review_hermes_translation_cancellation,[hermes_translation_request_id,hermes_translation_job_id],[hermes_translation_cancel_state,hermes_translation_cancel_group,hermes_translation_cancel_summary],queue=False)
            hermes_translation_cancel_back.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_translation_cancel_state,hermes_translation_cancel_group],queue=False)
            hermes_translation_cancel_confirm.click(submit_hermes_translation_cancellation,[hermes_translation_cancel_state,hermes_translation_request_id,hermes_translation_job_id],[hermes_translation_cancel_state,hermes_translation_cancel_group,hermes_translation_status],queue=False)
            for current_translation_cancel_input in (hermes_translation_request_id,hermes_translation_job_id):
                current_translation_cancel_input.change(lambda:(None,gr.update(visible=False)),outputs=[hermes_translation_cancel_state,hermes_translation_cancel_group],queue=False)
        with gr.Accordion('동작·영상 생성 위임',open=False):
            gr.Markdown('DWPose 및 Wan 생성기의 기존 입력 검증과 공용 GPU 대기열을 사용합니다. 설정 예제는 서비스 전환 시 교체됩니다. PNG 이미지는 순서대로 첨부하며 영상·마스크 MP4는 해당 입력에 첨부하세요. 바이너리는 설정 JSON에 넣지 않습니다. 화면 첨부 합계는 24MiB 이하입니다. 큰 작업은 GPU 메모리와 시간이 많이 필요합니다.')
            hermes_video_service=gr.Dropdown(label='동작·영상 서비스',choices=[('DWPose','dwpose'),('Wan Animate-2','wan22-animate2'),('Wan Fun Control','wan22-fun-control'),('Wan VACE','wan22-vace')],value='dwpose')
            hermes_video_settings=gr.Code(label='동작·영상 설정 JSON',language='json',value=default_hermes_video_settings('dwpose'),interactive=True,lines=10)
            hermes_video_service.input(default_hermes_video_settings,[hermes_video_service],[hermes_video_settings],queue=False)
            hermes_video_images=gr.File(label='참조·제어 PNG 이미지 · 순서대로',file_types=['.png'],file_count='multiple',type='binary')
            with gr.Row():
                hermes_video_driving=gr.File(label='동작 RGB MP4 · driving_video',file_types=['.mp4'],type='binary')
                hermes_video_pose=gr.File(label='포즈 MP4 · pose_video',file_types=['.mp4'],type='binary')
            with gr.Row():
                hermes_video_edit=gr.File(label='편집·조건 MP4 · edit_video',file_types=['.mp4'],type='binary')
                hermes_video_mask=gr.File(label='편집 마스크 MP4 · edit_mask',file_types=['.mp4'],type='binary')
            hermes_video_request_id=gr.Textbox(label='동작·영상 접수 ID',value=lambda:uuid.uuid4().hex,interactive=True)
            hermes_video_review_state=gr.State(None)
            hermes_video_proposal_button=gr.Button('선택한 세션 작업의 동작·영상 제안 불러오기 · 기존 설정·첨부 교체')
            hermes_video_review_button=gr.Button('동작·영상 입력 검토')
            hermes_video_preview=gr.Markdown()
            hermes_video_status=gr.Markdown('서비스와 설정·첨부를 검토하세요.')
            hermes_video_submit=gr.Button('동작·영상 GPU 대기열에 추가',interactive=False)
            hermes_video_job_id=gr.Textbox(label='동작·영상 작업 ID',interactive=True)
            hermes_video_inputs=[hermes_video_service,hermes_video_settings,hermes_video_images,hermes_video_driving,hermes_video_pose,hermes_video_edit,hermes_video_mask,hermes_video_request_id]
            hermes_video_review_event=hermes_video_review_button.click(review_hermes_video_request,hermes_video_inputs,[hermes_video_review_state,hermes_video_preview,hermes_video_status,hermes_video_submit],queue=False)
            hermes_video_proposal_button.click(load_hermes_video_proposal,[hermes_session_job_selection],[hermes_video_service,hermes_video_settings,hermes_video_images,hermes_video_driving,hermes_video_pose,hermes_video_edit,hermes_video_mask,hermes_video_request_id,hermes_video_review_state,hermes_video_preview,hermes_video_status,hermes_video_submit],queue=False)
            for current_video_input in hermes_video_inputs:
                current_video_input.change(lambda:(None,'','입력이 변경되어 다시 검토해야 합니다.',gr.update(interactive=False)),outputs=[hermes_video_review_state,hermes_video_preview,hermes_video_status,hermes_video_submit],queue=False)
            bind_gpu_generation_confirmation(hermes_video_submit,submit_hermes_video_reviewed,[hermes_video_review_state,*hermes_video_inputs],[hermes_video_job_id,hermes_video_status],generation_readiness_callback=lambda current_review_value:bool(current_review_value),generation_readiness_inputs=[hermes_video_review_state],generation_readiness_events=[hermes_video_review_event],generation_confirmation_validator=match_hermes_confirmation_inputs,generation_confirmation_inputs=[hermes_video_review_state,*hermes_video_inputs])
            hermes_video_read_button=gr.Button('동작·영상 상태·결과 조회')
            hermes_video_read_button.click(read_hermes_video_result,[hermes_video_request_id,hermes_video_service],[hermes_video_job_id,hermes_video_status],queue=False)
            hermes_video_history=gr.Dropdown(label='동작·영상 접수 이력',choices=[],interactive=True)
            with gr.Row():
                hermes_video_history_refresh=gr.Button('동작·영상 이력 조회')
                hermes_video_history_open=gr.Button('선택한 동작·영상 접수 확인')
            hermes_video_history_status=gr.Markdown('선택한 서비스의 Hermes 접수만 표시합니다.')
            hermes_video_history_refresh.click(list_hermes_video_choices,[hermes_video_service],[hermes_video_history,hermes_video_history_status],queue=False)
            hermes_video_history_open.click(lambda current_request_value:current_request_value,[hermes_video_history],[hermes_video_request_id],queue=False).then(read_hermes_video_result,[hermes_video_request_id,hermes_video_service],[hermes_video_job_id,hermes_video_status],queue=False)
            hermes_video_cancel_review=gr.Button('동작·영상 작업 중지 검토')
            hermes_video_cancel_state=gr.State(None)
            with gr.Group(visible=False) as hermes_video_cancel_group:
                hermes_video_cancel_summary=gr.Markdown()
                with gr.Row():
                    hermes_video_cancel_back=gr.Button('동작·영상 중지하지 않기')
                    hermes_video_cancel_confirm=gr.Button('확인 후 동작·영상 중지 요청')
            hermes_video_cancel_review.click(review_hermes_video_cancellation,[hermes_video_request_id,hermes_video_service,hermes_video_job_id],[hermes_video_cancel_state,hermes_video_cancel_group,hermes_video_cancel_summary],queue=False)
            hermes_video_cancel_back.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_video_cancel_state,hermes_video_cancel_group],queue=False)
            hermes_video_cancel_confirm.click(submit_hermes_video_cancellation,[hermes_video_cancel_state,hermes_video_request_id,hermes_video_service,hermes_video_job_id],[hermes_video_cancel_state,hermes_video_cancel_group,hermes_video_status],queue=False)
            for current_video_cancel_input in (hermes_video_request_id,hermes_video_service,hermes_video_job_id):
                current_video_cancel_input.change(lambda:(None,gr.update(visible=False)),outputs=[hermes_video_cancel_state,hermes_video_cancel_group],queue=False)
        with gr.Accordion('음악·효과음 생성 위임',open=False):
            gr.Markdown('HeartMuLa는 가사를 직접 지정하며 최대 출력 시간은 완결 길이를 보장하지 않습니다. 빈 가사도 무보컬을 보장하지 않습니다. Dasheng 효과음은 길이를 모델이 결정합니다. 결과는 자동 에셋 등록되지 않습니다.')
            hermes_audio_service = gr.Dropdown(label='오디오 생성 서비스',choices=[('HeartMuLa 음악','music-heartmula'),('Dasheng 효과음','sfx-dasheng-audiogen')],value='music-heartmula')
            hermes_audio_prompt = gr.Textbox(label='오디오 생성 지시',lines=3)
            hermes_audio_lyrics = gr.Textbox(label='음악 가사·구간 태그 · 효과음은 비움',lines=4)
            with gr.Row():
                hermes_audio_duration = gr.Number(label='음악 최대 출력 시간(초) · 효과음에는 적용 안 함',value=30,precision=0)
                hermes_audio_loop = gr.Checkbox(label='반복 구조 요청 · 효과음만 지원',value=False)
                hermes_audio_seed = gr.Number(label='오디오 시드',value=42,precision=0)
            hermes_audio_request_id = gr.Textbox(label='오디오 생성 접수 ID',value=lambda:uuid.uuid4().hex,interactive=True)
            hermes_audio_review_state = gr.State(None)
            hermes_audio_proposal_button = gr.Button('선택한 세션 작업의 오디오 제안 불러오기 · 기존 입력 교체')
            hermes_audio_review_button = gr.Button('오디오 생성 입력 검토')
            hermes_audio_preview = gr.Markdown()
            hermes_audio_status = gr.Markdown('서비스와 입력을 검토하세요.')
            hermes_audio_submit = gr.Button('오디오 GPU 대기열에 추가',interactive=False)
            hermes_audio_job_id = gr.Textbox(label='오디오 생성 작업 ID',interactive=True)
            hermes_audio_inputs = [hermes_audio_service,hermes_audio_prompt,hermes_audio_lyrics,hermes_audio_duration,hermes_audio_loop,hermes_audio_seed,hermes_audio_request_id]
            hermes_audio_review_event=hermes_audio_review_button.click(review_hermes_audio_request,hermes_audio_inputs,[hermes_audio_review_state,hermes_audio_preview,hermes_audio_status,hermes_audio_submit],queue=False)
            hermes_audio_proposal_button.click(load_hermes_audio_proposal,[hermes_session_job_selection],[hermes_audio_service,hermes_audio_prompt,hermes_audio_lyrics,hermes_audio_duration,hermes_audio_loop,hermes_audio_seed,hermes_audio_request_id,hermes_audio_review_state,hermes_audio_preview,hermes_audio_status,hermes_audio_submit],queue=False)
            for current_audio_input in hermes_audio_inputs:
                current_audio_input.change(lambda:(None,'','입력이 변경되어 다시 검토해야 합니다.',gr.update(interactive=False)),outputs=[hermes_audio_review_state,hermes_audio_preview,hermes_audio_status,hermes_audio_submit],queue=False)
            bind_gpu_generation_confirmation(hermes_audio_submit,submit_hermes_audio_reviewed,[hermes_audio_review_state,*hermes_audio_inputs],[hermes_audio_job_id,hermes_audio_status],generation_readiness_callback=lambda current_review_value:bool(current_review_value),generation_readiness_inputs=[hermes_audio_review_state],generation_readiness_events=[hermes_audio_review_event],generation_confirmation_validator=match_hermes_confirmation_inputs,generation_confirmation_inputs=[hermes_audio_review_state,*hermes_audio_inputs])
            hermes_audio_read_button = gr.Button('오디오 생성 상태·결과 조회')
            hermes_audio_read_button.click(read_hermes_audio_result,[hermes_audio_request_id,hermes_audio_service],[hermes_audio_job_id,hermes_audio_status],queue=False)
            hermes_audio_source_service = gr.Dropdown(label='오디오 이력 서비스',choices=[({'music-heartmula':'HeartMuLa 음악','sfx-dasheng-audiogen':'Dasheng 효과음','music-magenta':'보관된 Magenta 음악','music-minimax':'보관된 MiniMax 음악'}.get(current_service_name,current_service_name),current_service_name) for current_service_name in SOURCE_HISTORY_AUDIO_SERVICES],value='music-heartmula')
            hermes_audio_source_button = gr.Button('생성기 원본 이력 조회')
            hermes_audio_source_status = gr.Markdown('Hermes 외 작업도 포함한 기록 상태를 조회합니다.')
            hermes_audio_source_table = gr.Dataframe(headers=['작업 ID','기록 상태','상태 출처'],datatype=['str','str','str'],interactive=False,type='array',label='오디오 원본 이력')
            hermes_audio_source_state = gr.State(None)
            hermes_audio_source_next = gr.Button('다음 오디오 원본 이력',interactive=False)
            hermes_audio_source_outputs=[hermes_audio_source_table,hermes_audio_source_status,hermes_audio_source_state,hermes_audio_source_next]
            hermes_audio_source_button.click(read_hermes_audio_source_rows,[hermes_audio_source_service],hermes_audio_source_outputs,queue=False)
            hermes_audio_source_next.click(read_next_hermes_audio_source_rows,[hermes_audio_source_service,hermes_audio_source_state],hermes_audio_source_outputs,queue=False)
            hermes_audio_source_service.change(clear_hermes_source_history,outputs=hermes_audio_source_outputs,queue=False)
            hermes_audio_history = gr.Dropdown(label='오디오 생성 접수 이력',choices=[],interactive=True)
            with gr.Row():
                hermes_audio_history_refresh = gr.Button('오디오 생성 이력 조회')
                hermes_audio_history_open = gr.Button('선택한 오디오 접수 확인')
            hermes_audio_history_status = gr.Markdown('선택한 서비스의 Hermes 접수만 표시합니다.')
            hermes_audio_history_refresh.click(list_hermes_audio_choices,[hermes_audio_service],[hermes_audio_history,hermes_audio_history_status],queue=False)
            hermes_audio_history_open.click(lambda current_request_value:current_request_value,[hermes_audio_history],[hermes_audio_request_id],queue=False).then(read_hermes_audio_result,[hermes_audio_request_id,hermes_audio_service],[hermes_audio_job_id,hermes_audio_status],queue=False)
            hermes_audio_cancel_review = gr.Button('오디오 생성 중지 검토')
            hermes_audio_cancel_state = gr.State(None)
            with gr.Group(visible=False) as hermes_audio_cancel_group:
                hermes_audio_cancel_summary = gr.Markdown()
                with gr.Row():
                    hermes_audio_cancel_back = gr.Button('오디오 생성 중지하지 않기')
                    hermes_audio_cancel_confirm = gr.Button('확인 후 오디오 생성 중지 요청')
            hermes_audio_cancel_review.click(review_hermes_audio_cancellation,[hermes_audio_request_id,hermes_audio_service,hermes_audio_job_id],[hermes_audio_cancel_state,hermes_audio_cancel_group,hermes_audio_cancel_summary],queue=False)
            hermes_audio_cancel_back.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_audio_cancel_state,hermes_audio_cancel_group],queue=False)
            hermes_audio_cancel_confirm.click(submit_hermes_audio_cancellation,[hermes_audio_cancel_state,hermes_audio_request_id,hermes_audio_service,hermes_audio_job_id],[hermes_audio_cancel_state,hermes_audio_cancel_group,hermes_audio_status],queue=False)
            for current_audio_cancel_input in (hermes_audio_request_id,hermes_audio_service,hermes_audio_job_id):
                current_audio_cancel_input.change(lambda:(None,gr.update(visible=False)),outputs=[hermes_audio_cancel_state,hermes_audio_cancel_group],queue=False)
        with gr.Accordion('FLUX 표정 생성 위임',open=False):
            from tools.review.domains.image.expression_generation import load_expression_configuration
            current_expression_choices=[(item['label_ko'],item['id']) for item in load_expression_configuration()['expressions']]
            gr.Markdown('얼굴 참조 한 장과 표정 프리셋을 사용합니다. 한국어 추가 지시는 기존 번역 대기열을 거칩니다. [표정 생성기 결과](/management/frame/flux-expression-generator/)에서 얼굴 특징과 색상을 비교하세요.')
            hermes_expression_face = gr.Image(label='표정 생성 얼굴 참조',type='pil',image_mode='RGB')
            hermes_expression_default = gr.Button('기본 캐릭터 얼굴 참조 불러오기')
            hermes_expression_default.click(load_hermes_default_face_reference,outputs=[hermes_expression_face],queue=False)
            hermes_expression_selection = gr.Dropdown(label='표정 프리셋',choices=current_expression_choices,value=current_expression_choices[0][1])
            hermes_expression_extra = gr.Textbox(label='표정 한국어 추가 지시 · 선택',lines=2)
            with gr.Row():
                hermes_expression_width = gr.Number(label='표정 너비',value=768,precision=0)
                hermes_expression_height = gr.Number(label='표정 높이',value=512,precision=0)
                hermes_expression_seed = gr.Number(label='표정 시드',value=42,precision=0)
            hermes_expression_request_id = gr.Textbox(label='표정 생성 접수 ID',value=lambda:uuid.uuid4().hex,interactive=True)
            hermes_expression_review_state = gr.State(None)
            hermes_expression_review_button = gr.Button('표정 생성 입력 검토')
            hermes_expression_preview = gr.Markdown()
            hermes_expression_status = gr.Markdown('얼굴 참조와 표정 입력을 검토하세요.')
            hermes_expression_submit = gr.Button('표정 생성 GPU 대기열에 추가',interactive=False)
            hermes_expression_job_id = gr.Textbox(label='표정 생성 작업 ID',interactive=True)
            hermes_expression_inputs = [hermes_expression_face,hermes_expression_selection,hermes_expression_extra,hermes_expression_width,hermes_expression_height,hermes_expression_seed,hermes_expression_request_id]
            hermes_expression_review_event = hermes_expression_review_button.click(review_hermes_flux_expression_request,hermes_expression_inputs,[hermes_expression_review_state,hermes_expression_preview,hermes_expression_status,hermes_expression_submit],queue=False)
            for current_expression_input in hermes_expression_inputs:
                current_expression_input.change(lambda:(None,'','입력이 변경되어 다시 검토해야 합니다.',gr.update(interactive=False)),outputs=[hermes_expression_review_state,hermes_expression_preview,hermes_expression_status,hermes_expression_submit],queue=False)
            bind_gpu_generation_confirmation(hermes_expression_submit,submit_hermes_flux_expression_reviewed,[hermes_expression_review_state,*hermes_expression_inputs],[hermes_expression_job_id,hermes_expression_status],generation_readiness_callback=lambda current_review_value:bool(current_review_value),generation_readiness_inputs=[hermes_expression_review_state],generation_readiness_events=[hermes_expression_review_event],generation_confirmation_validator=match_hermes_flux_expression_confirmation,generation_confirmation_inputs=[hermes_expression_review_state,*hermes_expression_inputs])
            hermes_expression_read_button = gr.Button('표정 생성 상태 조회')
            hermes_expression_read_button.click(lambda current_request_value:read_hermes_flux_profile_result(current_request_value,'flux-expression'),[hermes_expression_request_id],[hermes_expression_job_id,hermes_expression_status],queue=False)
            hermes_expression_history = gr.Dropdown(label='표정 생성 접수 이력',choices=[],interactive=True)
            with gr.Row():
                hermes_expression_history_refresh = gr.Button('표정 생성 이력 조회')
                hermes_expression_history_open = gr.Button('선택한 표정 생성 접수 확인')
            hermes_expression_history_status = gr.Markdown('Hermes를 통해 접수한 표정 작업만 표시합니다.')
            hermes_expression_history_refresh.click(lambda:list_hermes_flux_profile_choices('flux-expression'),outputs=[hermes_expression_history,hermes_expression_history_status],queue=False)
            hermes_expression_history_open.click(lambda current_request_value:current_request_value,[hermes_expression_history],[hermes_expression_request_id],queue=False).then(lambda current_request_value:read_hermes_flux_profile_result(current_request_value,'flux-expression'),[hermes_expression_request_id],[hermes_expression_job_id,hermes_expression_status],queue=False)
            hermes_expression_cancel_review = gr.Button('표정 생성 중지 검토')
            hermes_expression_cancel_state = gr.State(None)
            with gr.Group(visible=False) as hermes_expression_cancel_group:
                hermes_expression_cancel_summary = gr.Markdown()
                with gr.Row():
                    hermes_expression_cancel_back = gr.Button('표정 생성 중지하지 않기')
                    hermes_expression_cancel_confirm = gr.Button('확인 후 표정 생성 중지 요청')
            hermes_expression_cancel_review.click(lambda current_request_value,current_job_value:review_hermes_flux_profile_cancellation(current_request_value,'flux-expression',current_job_value),[hermes_expression_request_id,hermes_expression_job_id],[hermes_expression_cancel_state,hermes_expression_cancel_group,hermes_expression_cancel_summary],queue=False)
            hermes_expression_cancel_back.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_expression_cancel_state,hermes_expression_cancel_group],queue=False)
            hermes_expression_cancel_confirm.click(lambda current_review_value,current_request_value,current_job_value:submit_hermes_flux_profile_cancellation(current_review_value,current_request_value,'flux-expression',current_job_value),[hermes_expression_cancel_state,hermes_expression_request_id,hermes_expression_job_id],[hermes_expression_cancel_state,hermes_expression_cancel_group,hermes_expression_status],queue=False)
            for current_expression_cancel_input in (hermes_expression_request_id,hermes_expression_job_id):
                current_expression_cancel_input.change(lambda:(None,gr.update(visible=False)),outputs=[hermes_expression_cancel_state,hermes_expression_cancel_group],queue=False)
        with gr.Accordion('FLUX 프로필 생성 위임',open=False):
            from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
            gr.Markdown('프로필별 생성기 검증과 공용 GPU 대기열을 사용합니다. 마네킨·빌보드·건물은 첫 참조가 필요하며 심리스는 512×512 무참조입니다. 결과는 해당 생성기 화면에서 확인합니다.')
            hermes_profile_selection = gr.Dropdown(label='FLUX 생성 프로필',choices=[(value[0],name) for name,value in FLUX_IMAGE_PROFILE_RECORDS.items()],value='flux-prop')
            hermes_profile_prompt = gr.Textbox(label='FLUX 프로필 생성 지시',lines=3)
            with gr.Row():
                hermes_profile_width = gr.Number(label='프로필 너비',value=768,precision=0)
                hermes_profile_height = gr.Number(label='프로필 높이',value=768,precision=0)
                hermes_profile_seed = gr.Number(label='프로필 시드',value=42,precision=0)
            with gr.Row():
                hermes_profile_image_first = gr.Image(label='첫 번째 참조 이미지',type='pil',image_mode='RGB')
                hermes_profile_image_second = gr.Image(label='두 번째 참조 이미지',type='pil',image_mode='RGB')
            hermes_profile_request_id = gr.Textbox(label='FLUX 프로필 접수 ID',value=lambda:uuid.uuid4().hex,interactive=True)
            hermes_profile_review_state = gr.State(None)
            hermes_profile_review_button = gr.Button('FLUX 프로필 입력 검토')
            hermes_profile_preview = gr.Markdown()
            hermes_profile_status = gr.Markdown('프로필과 입력을 검토하세요.')
            hermes_profile_submit = gr.Button('FLUX 프로필 GPU 대기열에 추가',interactive=False)
            hermes_profile_job_id = gr.Textbox(label='FLUX 프로필 작업 ID',interactive=True)
            hermes_profile_inputs = [hermes_profile_selection,hermes_profile_prompt,hermes_profile_width,hermes_profile_height,hermes_profile_seed,hermes_profile_image_first,hermes_profile_image_second,hermes_profile_request_id]
            hermes_profile_review_event = hermes_profile_review_button.click(review_hermes_flux_profile_request,hermes_profile_inputs,[hermes_profile_review_state,hermes_profile_preview,hermes_profile_status,hermes_profile_submit],queue=False)
            hermes_profile_selection.change(update_hermes_flux_profile_defaults,[hermes_profile_selection],[hermes_profile_width,hermes_profile_height],queue=False)
            for current_profile_input in hermes_profile_inputs:
                current_profile_input.change(lambda:(None,'','입력이 변경되어 다시 검토해야 합니다.',gr.update(interactive=False)),outputs=[hermes_profile_review_state,hermes_profile_preview,hermes_profile_status,hermes_profile_submit],queue=False)
            bind_gpu_generation_confirmation(hermes_profile_submit,submit_hermes_flux_profile_reviewed,[hermes_profile_review_state,*hermes_profile_inputs],[hermes_profile_job_id,hermes_profile_status],generation_readiness_callback=lambda current_review_value:bool(current_review_value),generation_readiness_inputs=[hermes_profile_review_state],generation_readiness_events=[hermes_profile_review_event],generation_confirmation_validator=match_hermes_flux_profile_confirmation,generation_confirmation_inputs=[hermes_profile_review_state,*hermes_profile_inputs])
            hermes_profile_read_button = gr.Button('FLUX 프로필 작업 상태 조회')
            hermes_profile_read_button.click(read_hermes_flux_profile_result,[hermes_profile_request_id,hermes_profile_selection],[hermes_profile_job_id,hermes_profile_status],queue=False)
            hermes_profile_history = gr.Dropdown(label='FLUX 프로필 접수 이력',choices=[],interactive=True)
            with gr.Row():
                hermes_profile_history_refresh = gr.Button('FLUX 프로필 이력 조회')
                hermes_profile_history_open = gr.Button('선택한 FLUX 프로필 접수 확인')
            hermes_profile_history_status = gr.Markdown('선택한 프로필의 접수 이력만 표시합니다.')
            hermes_profile_history_refresh.click(list_hermes_flux_profile_choices,[hermes_profile_selection],[hermes_profile_history,hermes_profile_history_status],queue=False)
            hermes_profile_history_open.click(lambda current_request_value:current_request_value,[hermes_profile_history],[hermes_profile_request_id],queue=False).then(read_hermes_flux_profile_result,[hermes_profile_request_id,hermes_profile_selection],[hermes_profile_job_id,hermes_profile_status],queue=False)
            hermes_profile_cancel_review = gr.Button('FLUX 프로필 작업 중지 검토')
            hermes_profile_cancel_state = gr.State(None)
            with gr.Group(visible=False) as hermes_profile_cancel_group:
                hermes_profile_cancel_summary = gr.Markdown()
                with gr.Row():
                    hermes_profile_cancel_back = gr.Button('FLUX 프로필 중지하지 않기')
                    hermes_profile_cancel_confirm = gr.Button('확인 후 FLUX 프로필 중지 요청')
            hermes_profile_cancel_review.click(review_hermes_flux_profile_cancellation,[hermes_profile_request_id,hermes_profile_selection,hermes_profile_job_id],[hermes_profile_cancel_state,hermes_profile_cancel_group,hermes_profile_cancel_summary],queue=False)
            hermes_profile_cancel_back.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_profile_cancel_state,hermes_profile_cancel_group],queue=False)
            hermes_profile_cancel_confirm.click(submit_hermes_flux_profile_cancellation,[hermes_profile_cancel_state,hermes_profile_request_id,hermes_profile_selection,hermes_profile_job_id],[hermes_profile_cancel_state,hermes_profile_cancel_group,hermes_profile_status],queue=False)
            for current_profile_cancel_input in (hermes_profile_request_id,hermes_profile_selection,hermes_profile_job_id):
                current_profile_cancel_input.change(lambda:(None,gr.update(visible=False)),outputs=[hermes_profile_cancel_state,hermes_profile_cancel_group],queue=False)
        with gr.Accordion('FLUX 이미지 작업 위임', open=False):
            gr.Markdown('텍스트와 선택한 참조 이미지로 일반 이미지를 생성합니다. 입력을 검토한 뒤 공용 GPU 확인을 거칩니다.')
            hermes_flux_prompt = gr.Textbox(label='이미지 지시', lines=3)
            with gr.Row():
                hermes_flux_width = gr.Number(label='가로', value=512, precision=0, minimum=256, maximum=1664)
                hermes_flux_height = gr.Number(label='세로', value=512, precision=0, minimum=256, maximum=1664)
                hermes_flux_seed = build_generation_seed(42)
            with gr.Row():
                hermes_flux_image_first = gr.Image(label='일반 이미지 첫 번째 참조',type='pil',image_mode='RGB')
                hermes_flux_image_second = gr.Image(label='일반 이미지 두 번째 참조',type='pil',image_mode='RGB')
            hermes_flux_request_id = gr.Textbox(label='FLUX 위임 접수 ID', value=lambda:uuid.uuid4().hex, interactive=True, info='같은 ID와 입력으로 재시도하며 새 작업에는 새 ID를 사용하세요.')
            hermes_flux_review_state = gr.State(None)
            hermes_flux_proposal_button = gr.Button('선택한 세션 작업의 FLUX 제안 불러오기')
            hermes_flux_review_button = gr.Button('FLUX 입력 검토')
            hermes_flux_preview = gr.Textbox(label='확인할 FLUX 입력', lines=6, interactive=False)
            hermes_flux_status = gr.Markdown('입력을 검토하세요.')
            hermes_flux_submit = gr.Button('FLUX 작업 대기열에 추가', interactive=False)
            hermes_flux_job = gr.Textbox(label='FLUX 작업 ID', interactive=False)
            hermes_flux_review_inputs = [hermes_flux_prompt, hermes_flux_width, hermes_flux_height, hermes_flux_seed, hermes_flux_request_id, hermes_flux_image_first, hermes_flux_image_second]
            hermes_flux_proposal_button.click(load_hermes_flux_proposal, [hermes_session_job_selection], [hermes_flux_prompt, hermes_flux_width, hermes_flux_height, hermes_flux_seed, hermes_flux_request_id, hermes_flux_image_first, hermes_flux_image_second, hermes_flux_review_state, hermes_flux_preview, hermes_flux_status, hermes_flux_submit], queue=False)
            hermes_flux_review_event = hermes_flux_review_button.click(review_hermes_flux_request, hermes_flux_review_inputs, [hermes_flux_review_state, hermes_flux_preview, hermes_flux_status, hermes_flux_submit], queue=False)
            for hermes_flux_input in hermes_flux_review_inputs:
                hermes_flux_input.change(lambda: (None, '', '입력이 변경되어 다시 검토해야 합니다.', gr.update(interactive=False)), outputs=[hermes_flux_review_state, hermes_flux_preview, hermes_flux_status, hermes_flux_submit], queue=False)
            bind_gpu_generation_confirmation(hermes_flux_submit, submit_hermes_flux_reviewed_request, [hermes_flux_review_state, *hermes_flux_review_inputs], [hermes_flux_job, hermes_flux_status], generation_readiness_callback=lambda current_review_value:bool(current_review_value), generation_readiness_inputs=[hermes_flux_review_state], generation_readiness_events=[hermes_flux_review_event], generation_confirmation_validator=match_hermes_flux_image_confirmation, generation_confirmation_inputs=[hermes_flux_review_state, *hermes_flux_review_inputs])
            hermes_flux_history = gr.Dropdown(label='FLUX 위임 접수 이력', choices=[], interactive=True)
            hermes_flux_history_refresh = gr.Button('FLUX 위임 이력 새로고침')
            hermes_flux_history_open = gr.Button('선택한 FLUX 접수 열기')
            hermes_flux_history_status = gr.Markdown('이력을 새로고침하세요.')
            hermes_flux_history_refresh.click(list_hermes_flux_delegation_choices, [hermes_flux_history], [hermes_flux_history, hermes_flux_history_status], queue=False)
            hermes_flux_history_open.click(lambda current_id:(current_id, None, '', gr.update(interactive=False)), [hermes_flux_history], [hermes_flux_request_id, hermes_flux_review_state, hermes_flux_preview, hermes_flux_submit], queue=False).then(read_hermes_flux_receipt, [hermes_flux_request_id], [hermes_flux_job, hermes_flux_status], queue=False)
            hermes_flux_status_button = gr.Button('FLUX 접수와 작업 상태 조회')
            hermes_flux_status_button.click(read_hermes_flux_receipt, [hermes_flux_request_id], [hermes_flux_job, hermes_flux_status], queue=False)
            hermes_flux_cancel_review = gr.Button('FLUX 중지 요청 검토')
            hermes_flux_cancel_state = gr.State(None)
            with gr.Group(visible=False) as hermes_flux_cancel_group:
                hermes_flux_cancel_summary = gr.Markdown()
                with gr.Row():
                    hermes_flux_cancel_no = gr.Button('FLUX 중지하지 않기')
                    hermes_flux_cancel_yes = gr.Button('확인 후 FLUX 중지 요청')
            hermes_flux_cancel_review.click(review_hermes_flux_cancellation, [hermes_flux_request_id, hermes_flux_job], [hermes_flux_cancel_state, hermes_flux_cancel_group, hermes_flux_cancel_summary], queue=False)
            hermes_flux_cancel_no.click(lambda:(None, gr.update(visible=False)), outputs=[hermes_flux_cancel_state, hermes_flux_cancel_group], queue=False)
            hermes_flux_cancel_yes.click(submit_hermes_flux_cancellation, [hermes_flux_cancel_state, hermes_flux_request_id, hermes_flux_job], [hermes_flux_cancel_state, hermes_flux_cancel_group, hermes_flux_status], queue=False)
        with gr.Accordion('격리 코딩 작업과 이력', open=False) as hermes_legacy_accordion:
            hermes_prompt_control = gr.Textbox(label='작업 지시', lines=6, max_lines=20)
            hermes_verification_control = gr.Textbox(label='완료 후 검증 모듈 · 선택', lines=2, placeholder='tools.review.tests.test_hermes_service', info='공용 회귀 실행기에 등록된 모듈을 한 줄에 하나씩 최대 5개 입력합니다. Hermes 종료 후 격리 환경에서 별도로 검사합니다.')
            hermes_prompt_count = gr.Markdown('원문 0단어 · 최종 입력 0단어')
            hermes_prompt_control.change(lambda hermes_text_value: f'원문 {len((hermes_text_value or "").split())}단어 · 최종 입력 {len((hermes_text_value or "").split())}단어', hermes_prompt_control, hermes_prompt_count, queue=False)
            hermes_request_control = gr.Textbox(label='접수 식별자', value=lambda: uuid.uuid4().hex, interactive=False, info='요청 실패나 응답 유실 시 같은 식별자로 다시 접수하면 중복 실행하지 않습니다.')
            with gr.Row():
                hermes_submit_control = gr.Button('작업 대기열에 추가', variant='primary', interactive=False)
                hermes_new_request_button = gr.Button('새 접수 식별자')
            hermes_job_control = gr.Textbox(label='작업 ID', interactive=True)
            hermes_status_control = gr.Markdown('작업 지시를 입력하세요.')
            hermes_new_request_button.click(lambda: (uuid.uuid4().hex, '', '새 접수 식별자를 만들었습니다.'), outputs=[hermes_request_control, hermes_job_control, hermes_status_control], queue=False)
            bind_gpu_generation_confirmation(hermes_submit_control, submit_hermes_work_request, [hermes_prompt_control, hermes_request_control, hermes_verification_control], [hermes_job_control, hermes_status_control], generation_readiness_callback=lambda hermes_prompt_value: bool((hermes_prompt_value or '').strip()), generation_readiness_inputs=[hermes_prompt_control], generation_confirmation_validator=match_hermes_confirmation_inputs, generation_confirmation_inputs=[hermes_prompt_control, hermes_request_control, hermes_verification_control])
            with gr.Row():
                hermes_refresh_button = gr.Button('상태·결과 새로고침')
                hermes_cancel_button = gr.Button('작업 중지 요청')
            hermes_original_prompt_control = gr.Textbox(label='선택 작업에 전달된 지시', lines=4, interactive=False, info='세션 후속 작업은 이전 대화 문맥을 포함할 수 있습니다.')
            hermes_answer_control = gr.Textbox(label='Hermes 최종 응답', lines=5, interactive=False)
            hermes_diff_control = gr.Code(label='검토용 변경 diff', language=None, interactive=False, buttons=['copy', 'download'])
            gr.Markdown('긴 diff는 아래에서 처음부터 부분별로 확인할 수 있습니다. 복사·다운로드는 현재 표시 부분에 적용됩니다. 원본 바이트는 MCP의 diff 조회로 받을 수 있습니다.')
            hermes_diff_cursor = gr.State(None)
            hermes_diff_page_status = gr.Markdown('전체 diff를 보려면 완료된 작업을 선택하세요.')
            with gr.Row():
                hermes_diff_first_button = gr.Button('diff 처음 부분 보기')
                hermes_diff_next_button = gr.Button('diff 다음 부분 보기')
            hermes_diff_first_button.click(start_hermes_diff_pages, [hermes_job_control], [hermes_diff_control, hermes_diff_page_status, hermes_diff_cursor], queue=False)
            hermes_diff_next_button.click(read_hermes_diff_page, [hermes_job_control, hermes_diff_cursor], [hermes_diff_control, hermes_diff_page_status, hermes_diff_cursor], queue=False)

            hermes_result_control = gr.JSON(label='실행 결과')
            hermes_log_control = gr.Textbox(label='작업 로그', lines=8, interactive=False)
            hermes_refresh_button.click(refresh_hermes_work_status, hermes_job_control, [hermes_status_control, hermes_answer_control, hermes_diff_control, hermes_log_control, hermes_result_control, hermes_original_prompt_control], queue=False)
            hermes_cancel_button.click(cancel_hermes_work_request, hermes_job_control, hermes_status_control, queue=False)
            hermes_session_job_open.click(open_hermes_session_job, [hermes_session_job_selection], [hermes_job_control, hermes_status_control, hermes_answer_control, hermes_diff_control, hermes_log_control, hermes_result_control, hermes_original_prompt_control, hermes_legacy_accordion], queue=False)
            with gr.Accordion('작업 이력', open=True):
                hermes_history_button = gr.Button('이력 새로고침')
                hermes_history_status = gr.Markdown('이력을 확인하고 있습니다.')
                gr.Markdown('이력의 행을 선택하면 해당 작업의 상태와 결과를 불러옵니다.')
                hermes_history_table = gr.Dataframe(headers=['작업 ID', '상태', '지시'], datatype=['str', 'str', 'str'], type='array', interactive=False)
                hermes_history_table.select(select_hermes_history_record, inputs=[hermes_history_table], outputs=[hermes_job_control, hermes_status_control, hermes_answer_control, hermes_diff_control, hermes_log_control, hermes_result_control, hermes_original_prompt_control], queue=False)
                hermes_history_button.click(refresh_hermes_work_history, outputs=[hermes_history_table, hermes_history_status], queue=False)
            hermes_interface_blocks.load(refresh_hermes_work_history, outputs=[hermes_history_table, hermes_history_status], queue=False)
    return hermes_interface_blocks
