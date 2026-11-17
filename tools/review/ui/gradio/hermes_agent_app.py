"""공용 게이트웨이를 사용하는 격리 Hermes 코딩 작업 화면."""
import base64
import binascii
import uuid

import gradio as gr
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_generator_changelog import build_generator_changelog
from tools.review.common.management_client import execute_remote_management_command


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
    from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_kimodo_proposal, HERMES_PROPOSAL_START
    try:
        parse_hermes_kimodo_proposal(current_answer_text)
    except (ValueError, TypeError, KeyError):
        return current_answer_text
    current_marker_position = current_answer_text.rfind('\n' + HERMES_PROPOSAL_START + '\n')
    if current_marker_position < 0:
        if not current_answer_text.startswith(HERMES_PROPOSAL_START + '\n'):
            return current_answer_text
        current_narrative_text = ''
    else:
        current_narrative_text = current_answer_text[:current_marker_position].rstrip()
    current_instruction_text = 'Kimodo 작업 제안이 있습니다. 이 작업을 선택한 뒤 Kimodo 작업 위임에서 제안을 불러와 검토하세요.'
    return (current_narrative_text + '\n\n' if current_narrative_text else '') + current_instruction_text


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
        current_active_text = ('실행 ' + str(current_generator_active.get('id')) if current_generator_active.get('running') else '활성 작업 없음') if current_generator_active.get('status') == 'available' else '조회 불가'
        current_capacity_text = (str(current_capacity_record['domain']).upper() + ' 여유 ' + str(current_capacity_record['pool_available_mib']) + ' / 필요 ' + str(current_capacity_record['required_mib']) + ' MiB · 호스트 여유 ' + str(current_capacity_record['host_available_mib']) + ' MiB · ' + ('메모리 기준 충족' if current_capacity_record.get('capacity_sufficient') else '메모리 대기')) if current_capacity_record.get('status') == 'available' else '조회 불가'
        current_reservation_text = (str(len(current_reservation_record.get('records', []))) + '건' + (' 이상' if current_reservation_record.get('truncated') else '') + (' · 확인 불가 기록 포함' if any(current_record.get('state') == 'unknown' for current_record in current_reservation_record.get('records', [])) else '')) if current_reservation_record.get('status') == 'available' else '조회 불가'
        current_jobs_text = (str(len(current_recent_jobs.get('jobs', []))) + '건' + (' (최근 10건)' if current_recent_jobs.get('truncated') else '')) if current_recent_jobs.get('status') == 'available' else '조회 불가'
        return 'GPU 예약 기록: ' + current_reservation_text + ' · 최근 Hermes 작업: ' + current_jobs_text + ' · 메모리: ' + current_capacity_text + ' (다른 예약·순서 제외) · Kimodo: ' + current_generator_text + ' · ' + current_active_text + ' · Hermes 모델: ' + current_model_text + ' · GPU: ' + str(current_gpu_record.get('status', 'unavailable')) + ' · 대기: ' + current_queue_text + ' · 확인: ' + current_snapshot_record['queried_at'] + ' (GPU 측정은 짧게 캐시될 수 있음)'
    except Exception as current_status_error:
        return '관리 상태 조회 실패 · ' + str(current_status_error)


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


def review_hermes_kimodo_request(current_prompt_text, current_frames_value, current_steps_value, current_seed_value, current_request_identifier):
    """기존 Kimodo 기본 설정과 사용자 입력으로 검토할 불변 입력을 만든다."""
    from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS, validate_kimodo_request
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    try:
        if not isinstance(current_request_identifier, str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
            raise ValueError('접수 ID는 영문·숫자·밑줄·하이픈 8~80자여야 합니다.')
        current_generation_record = {current_key_name: current_value for current_key_name, current_value in KIMODO_DEFAULT_SETTINGS.items() if current_key_name != 'schema_version'}
        current_generation_record.update(action='generate', prompt=current_prompt_text, frames=current_frames_value, steps=current_steps_value, seed=current_seed_value)
        validate_kimodo_request(current_generation_record)
        current_review_record = {'request_id': current_request_identifier, 'request': current_generation_record}
        current_preview_text = ('접수 ID: ' + current_request_identifier + '\n동작: ' + current_generation_record['prompt'] + '\n프레임: ' + str(current_frames_value) + ' · 단계: ' + str(current_steps_value) + ' · 시드: ' + str(current_seed_value) + '\n방향: ' + ', '.join(current_generation_record['directions']) + ' · 가이던스: ' + str(current_generation_record['guidance_scale']) + ' · 시작 각도: ' + str(current_generation_record['heading_degrees']) + '\n후처리: ' + str(current_generation_record['post_processing']) + ' · 수평 이동 제거: ' + str(current_generation_record['remove_horizontal_motion']) + '\nOpenPose 배율: ' + str(current_generation_record['openpose_scale_percent']) + '% · 손: ' + str(current_generation_record['pose_include_hands']) + ' · 얼굴: ' + str(current_generation_record['pose_include_face']))
        return current_review_record, current_preview_text, '아래 확정 입력을 확인하세요. 접수하면 Kimodo 생성 작업이 공용 GPU 대기열에 추가됩니다. 입력 변경은 다시 검토해야 반영됩니다.'
    except (ValueError, TypeError) as current_review_error:
        return None, None, '위임 입력 확인 실패: ' + str(current_review_error)


def invalidate_hermes_kimodo_review(current_review_record, current_prompt_text, current_frames_value, current_steps_value, current_seed_value, current_request_identifier):
    """검토 뒤 입력이 바뀌면 이전 확정본을 사용할 수 없게 한다."""
    if not isinstance(current_review_record, dict) or not isinstance(current_review_record.get('request'), dict):
        return gr.skip(), gr.skip(), gr.skip(), gr.skip()
    current_review_request = current_review_record['request']
    if (current_review_record.get('request_id'), current_review_request.get('prompt'), current_review_request.get('frames'), current_review_request.get('steps'), current_review_request.get('seed')) == (current_request_identifier, current_prompt_text, current_frames_value, current_steps_value, current_seed_value):
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


def submit_hermes_kimodo_reviewed_request(current_review_record, current_prompt_text, current_frames_value, current_steps_value, current_seed_value, current_request_identifier):
    """확인 시점에 검토본과 버튼 입력이 같을 때만 접수한다."""
    if not isinstance(current_review_record, dict) or not isinstance(current_review_record.get('request'), dict):
        raise gr.Error('먼저 위임 입력을 검토하세요.')
    current_review_request = current_review_record['request']
    current_review_values = (current_review_record.get('request_id'), current_review_request.get('prompt'), current_review_request.get('frames'), current_review_request.get('steps'), current_review_request.get('seed'))
    if current_review_values != (current_request_identifier, current_prompt_text, current_frames_value, current_steps_value, current_seed_value):
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
    try:
        current_result_record = execute_remote_management_command('hermes-agent', 'hermes-delegation-cancel', current_cancel_record)
        if current_result_record.get('cancel_requested') is not True or current_result_record.get('job_id') != current_cancel_record['job_id']:
            raise ValueError('중지 접수 응답 확인 실패')
        return None, gr.update(visible=False), '중지를 요청했습니다. 실제 종료 여부는 Kimodo 작업 상태에서 확인하세요.'
    except Exception as current_cancel_error:
        raise gr.Error('중지 요청 확인 실패: ' + str(current_cancel_error) + ' · 작업 상태를 확인하세요.') from current_cancel_error


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


def read_hermes_capability_rows():
    """공용 기능 목록을 사람이 비교하기 쉬운 행으로 보여 준다."""
    try:
        current_catalog_record = execute_remote_management_command('hermes-agent', 'hermes-capabilities', {})
        current_effect_labels = {'read':'조회', 'enqueue':'대기열 접수', 'recovery_possible':'상태 복구 가능', 'cancel_request':'중지 요청'}
        current_gpu_labels = {'none':'사용 안 함', 'exclusive':'배타 사용', 'queued':'대기열 사용'}
        current_rows_value = [[current_record['label'], current_effect_labels.get(current_record['effect'], current_record['effect']), current_gpu_labels.get(current_record['gpu'], current_record['gpu']), current_record['note']] for current_record in current_catalog_record['records']]
        return current_rows_value, '기능 ' + str(len(current_rows_value)) + '개 · 작업 변경은 각 확인 절차와 서비스 검증을 따릅니다.'
    except Exception as current_catalog_error:
        return [], '기능 목록 조회 실패: ' + str(current_catalog_error)


def build_hermes_agent_interface():
    with gr.Blocks(title='Hermes 관리 에이전트') as hermes_interface_blocks:
        build_generator_changelog(hermes_interface_blocks, 'hermes-agent')
        gr.Markdown('## Hermes 관리 에이전트\n대화로 관리 상태를 확인하고 Kimodo 작업을 제안·위임하거나 격리 코딩을 요청할 수 있습니다. 생성 위임은 사용자가 입력을 검토하고 확인한 뒤 공용 GPU 대기열에 접수합니다. 코딩 작업의 변경은 격리 사본의 검토용 diff로 제공하며 원본에 자동 적용하지 않습니다. 모델 추론은 공용 GPU를 배타적으로 사용합니다. 실행 시간은 관측 이력이 부족해 계산 중입니다. 모델 준비는 [모델 관리](/management/frame/model-management/)에서 확인하세요.')
        hermes_management_summary = gr.Markdown('관리 상태를 확인하고 있습니다.')
        hermes_management_refresh = gr.Button('관리 상태 새로고침')
        hermes_management_refresh.click(read_hermes_management_summary, outputs=hermes_management_summary, queue=False)
        hermes_interface_blocks.load(read_hermes_management_summary, outputs=hermes_management_summary, queue=False)
        with gr.Accordion('사용 가능한 관리 기능', open=False):
            gr.Markdown('조회와 작업 변경의 영향을 확인합니다. 작업 실행 권한을 별도로 부여하는 화면은 아닙니다.')
            hermes_capability_refresh = gr.Button('관리 기능 목록 새로고침')
            hermes_capability_status = gr.Markdown('목록 새로고침으로 기능을 확인하세요.')
            hermes_capability_table = gr.Dataframe(headers=['기능', '영향', 'GPU', '확인 사항'], datatype=['str','str','str','str'], interactive=False, type='array', label='관리 기능 목록')
            hermes_capability_refresh.click(read_hermes_capability_rows, outputs=[hermes_capability_table, hermes_capability_status], queue=False)
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
        with gr.Accordion('Kimodo 작업 위임', open=False):
            gr.Markdown('모션 생성 입력을 검토하고 공용 GPU 대기열에 접수합니다. 접수와 완료는 별도이며, 응답 유실 시 같은 접수 ID와 입력을 유지하세요. [Kimodo 작업과 이력 보기](/management/frame/kimodo-generator/)')
            hermes_delegate_prompt = gr.Textbox(label='Kimodo 동작 지시', lines=3)
            with gr.Row():
                hermes_delegate_frames = gr.Number(label='프레임 수', value=90, precision=0)
                hermes_delegate_steps = gr.Number(label='생성 단계', value=100, precision=0)
                hermes_delegate_seed = gr.Number(label='시드', value=42, precision=0)
            hermes_delegate_request_id = gr.Textbox(label='위임 접수 ID', value=lambda: uuid.uuid4().hex, interactive=True, info='응답 유실 시 같은 ID와 입력을 사용하세요. 새 작업에는 새 ID를 입력하세요.')
            hermes_delegate_review_state = gr.State(None)
            hermes_delegate_proposal = gr.Button('선택한 세션 작업의 Hermes 제안 불러오기')
            hermes_delegate_review = gr.Button('위임 입력 검토')
            hermes_delegate_review_status = gr.Markdown('동작 지시를 입력하고 위임 입력을 검토하세요.')
            hermes_delegate_review_json = gr.Textbox(label='확정할 위임 입력', lines=6, interactive=False)
            hermes_delegate_review_event = hermes_delegate_review.click(review_hermes_kimodo_request, [hermes_delegate_prompt, hermes_delegate_frames, hermes_delegate_steps, hermes_delegate_seed, hermes_delegate_request_id], [hermes_delegate_review_state, hermes_delegate_review_json, hermes_delegate_review_status], queue=False)
            hermes_delegate_submit = gr.Button('검토한 위임 대기열에 추가', interactive=False)
            hermes_delegate_proposal.click(load_hermes_kimodo_proposal, [hermes_session_job_selection], [hermes_delegate_prompt, hermes_delegate_frames, hermes_delegate_steps, hermes_delegate_seed, hermes_delegate_request_id, hermes_delegate_review_state, hermes_delegate_review_json, hermes_delegate_review_status, hermes_delegate_submit], queue=False)
            hermes_delegate_review_inputs = [hermes_delegate_prompt, hermes_delegate_frames, hermes_delegate_steps, hermes_delegate_seed, hermes_delegate_request_id]
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
