"""공용 게이트웨이를 사용하는 격리 Hermes 코딩 작업 화면."""
import base64
import binascii
import json
import re
import threading
import uuid

import gradio as gr
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_generator_changelog import build_generator_changelog
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES, SOURCE_HISTORY_AUDIO_SERVICES


def describe_unconfirmed_resume_error(current_error_value):
    """검증된 기존 접수 ID만 사용자에게 표시한다."""
    if not isinstance(current_error_value,ValueError):return None
    current_match_value=re.search(r'같은 작업에 결과가 확인되지 않은 기존 접수가 있습니다 \(접수 ID: ([A-Za-z0-9_-]{8,80})\)\. 해당 접수와 원 서비스 상태를 확인하세요\. 자동 재접수하지 마세요\.',str(current_error_value))
    if current_match_value is None:return None
    return f'기존 재개 접수 {current_match_value.group(1)}의 결과가 확인되지 않았습니다. 해당 접수와 원 서비스 상태를 확인하세요. 자동 재접수하지 않습니다.'


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
        current_cancel_response=execute_remote_management_command('hermes-agent', 'hermes-cancel', {'id':hermes_job_identifier})
        if not isinstance(current_cancel_response,dict) or current_cancel_response.get('id')!=hermes_job_identifier or current_cancel_response.get('cancel_requested') is not True or current_cancel_response.get('status') not in ('queued','running','cancelled'):
            raise ValueError('중지 요청 접수 응답을 확인할 수 없습니다.')
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
        current_unreadable_count=hermes_list_record.get('unreadable_count',0)
        if type(current_unreadable_count) is not int or current_unreadable_count<0:raise ValueError('세션 누락 수 오류')
        if current_unreadable_count:hermes_list_message+=' · 읽을 수 없는 세션 '+str(current_unreadable_count)+'개 제외'
        if isinstance(hermes_selected_identifier,str) and re.fullmatch(r'[a-f0-9]{32}',hermes_selected_identifier) and hermes_selected_identifier not in hermes_valid_identifiers:
            try:
                current_selected_record=execute_remote_management_command('hermes-agent','hermes-session-read',{'session_id':hermes_selected_identifier})
                if not isinstance(current_selected_record,dict) or current_selected_record.get('id')!=hermes_selected_identifier or not isinstance(current_selected_record.get('updated_at'),str) or not isinstance(current_selected_record.get('messages'),list):raise ValueError('세션 기록 오류')
                hermes_session_choices.append((current_selected_record['updated_at']+' · '+hermes_selected_identifier[:8]+' · '+str(len(current_selected_record['messages']))+'개 메시지 · 이전 세션',hermes_selected_identifier))
                hermes_valid_identifiers.add(hermes_selected_identifier)
                hermes_list_message+=' · 선택한 이전 세션 포함'
            except (OSError,ValueError,KeyError,TypeError,RuntimeError):
                hermes_list_message+=' · 선택한 이전 세션 확인 불가'
        return gr.update(choices=hermes_session_choices, value=hermes_selected_identifier if hermes_selected_identifier in hermes_valid_identifiers else None), hermes_list_message
    except Exception as hermes_request_error:
        raise gr.Error('세션 목록 조회 실패: ' + str(hermes_request_error)) from hermes_request_error


def review_conversation_workflow_definition(current_session_identifier, workflow_definition_text):
    from tools.review.common.management_gateway import parse_management_request_json
    from tools.review.domains.hermes_agent.workflow_catalog import create_workflow_step_draft, read_workflow_generator_catalog
    from tools.review.domains.hermes_agent.workflow_definition import compile_workflow_dependencies
    if not re.fullmatch(r"[a-f0-9]{32}", current_session_identifier or ""):
        raise gr.Error("대화 세션을 선택하세요.")
    current_proposal_record = parse_management_request_json(workflow_definition_text)
    if not isinstance(current_proposal_record, dict) or set(current_proposal_record) != {"steps"} or not isinstance(current_proposal_record["steps"], list):
        raise gr.Error("steps 목록을 확인하세요.")
    normalized_step_records = []
    for current_step_record in current_proposal_record["steps"]:
        if not isinstance(current_step_record, dict) or set(current_step_record) - {"id", "generator", "inputs", "bindings"}:
            raise gr.Error("단계 정의를 확인하세요.")
        fixed_input_record = current_step_record.get("inputs", {})
        bound_input_record = current_step_record.get("bindings", {})
        if not isinstance(fixed_input_record, dict) or not isinstance(bound_input_record, dict) or fixed_input_record.keys() & bound_input_record.keys():
            raise gr.Error("단계 입력과 연결을 확인하세요.")
        normalized_step_record = create_workflow_step_draft(current_step_record.get("id"), current_step_record.get("generator"), fixed_input_record)
        for current_field_name in bound_input_record:
            normalized_step_record["inputs"].pop(current_field_name, None)
        normalized_step_record["bindings"] = bound_input_record
        normalized_step_records.append(normalized_step_record)
    compile_workflow_dependencies(normalized_step_records, read_workflow_generator_catalog())
    return {"session_id": current_session_identifier, "run_id": uuid.uuid4().hex, "steps": normalized_step_records}


def load_conversation_workflow_definition(current_session_identifier, current_source_job_identifier):
    current_session_match = find_conversation_session_job(current_session_identifier, current_source_job_identifier)
    current_job_record = current_session_match["job"]
    current_answer_text = current_job_record.get("final_response")
    if current_job_record.get("final_response_truncated") is not False or not isinstance(current_answer_text, str):
        raise gr.Error("완료된 대화 답변 전체가 필요합니다.")
    proposal_block_values = re.findall(r"(?ms)^HERMES_WORKFLOW_PROPOSAL[ \t]*\n(.*?)\nEND_HERMES_WORKFLOW_PROPOSAL[ \t]*$", current_answer_text)
    if len(proposal_block_values) != 1:
        raise gr.Error("선택한 답변에서 워크플로우 제안 한 개를 확인하세요.")
    return proposal_block_values[0]


def submit_conversation_workflow_definition(current_review_record, current_session_identifier, workflow_definition_text):
    expected_review_record = review_conversation_workflow_definition(current_session_identifier, workflow_definition_text)
    if not current_review_record or any(current_review_record[key] != expected_review_record[key] for key in ("session_id", "steps")):
        raise gr.Error("편집한 단계를 다시 검토하세요.")
    return execute_remote_management_command("hermes-agent", "hermes-workflow-register", current_review_record)


def import_workflow_translation_proposal(current_session_identifier, current_source_job_identifier):
    find_conversation_session_job(current_session_identifier, current_source_job_identifier)
    proposal_input_record = read_matching_hermes_edit_proposal(current_source_job_identifier, "hermes-translation-proposal")
    translation_glossary_text = "\n".join(item["source"] + " => " + item["target"] for item in proposal_input_record["glossary"])
    return proposal_input_record["text"], proposal_input_record["target_language"], translation_glossary_text


def review_translation_image_workflow(current_session_identifier, current_source_text, current_image_width, current_image_height, image_revision_prompt="", translation_target_language="en", translation_glossary_text=""):
    from tools.review.domains.hermes_agent.workflow_catalog import create_workflow_step_draft
    if not re.fullmatch(r"[a-f0-9]{32}", current_session_identifier or ""):
        raise gr.Error("먼저 대화 세션을 선택하세요.")
    if not current_source_text or not current_source_text.strip() or len(current_source_text) > 6000:
        raise gr.Error("번역할 원문을 1~6000자로 입력하세요.")
    for current_size_value in (current_image_width, current_image_height):
        if current_size_value not in range(256, 1665, 16):
            raise gr.Error("이미지 크기는 256~1664 범위에서 16의 배수로 입력하세요.")
    from tools.review.ui.gradio.prompt_translation_app import parse_translation_glossary
    from tools.review.domains.translation.service import validate_translation_submission
    translation_input_record = {"text": current_source_text, "target_language": translation_target_language,
                                "glossary": parse_translation_glossary(translation_glossary_text)}
    validate_translation_submission(translation_input_record)
    translation_step_record = create_workflow_step_draft("translate", "prompt-translation", translation_input_record)
    image_step_record = create_workflow_step_draft("image", "flux-image",
        {"width": int(current_image_width), "height": int(current_image_height)})
    image_step_record["bindings"]["prompt"] = {"from_step": "translate", "output": "text"}
    workflow_request_record = {"session_id": current_session_identifier, "run_id": uuid.uuid4().hex,
                               "steps": [translation_step_record, image_step_record]}
    if image_revision_prompt and image_revision_prompt.strip():
        if len(image_revision_prompt) > 8000:
            raise gr.Error("이미지 수정 요청은 8000자 이하로 입력하세요.")
        revision_step_record = create_workflow_step_draft("revise", "flux-image",
            {"prompt": image_revision_prompt.strip(), "width": int(current_image_width), "height": int(current_image_height)})
        del revision_step_record["inputs"]["images"]
        revision_step_record["bindings"]["images"] = {"from_step": "image", "output": "images"}
        workflow_request_record["steps"].append(revision_step_record)
    return workflow_request_record, workflow_request_record["steps"], workflow_request_record["run_id"]


def submit_translation_image_workflow(current_review_record, current_session_identifier, current_source_text,
                                      current_image_width, current_image_height, image_revision_prompt="", translation_target_language="en", translation_glossary_text=""):
    current_expected_record, _, _ = review_translation_image_workflow(
        current_session_identifier, current_source_text, current_image_width, current_image_height, image_revision_prompt,
        translation_target_language, translation_glossary_text)
    if (not current_review_record or current_review_record["session_id"] != current_session_identifier
            or current_review_record["steps"] != current_expected_record["steps"]):
        raise gr.Error("현재 입력으로 워크플로우를 다시 검토하세요.")
    return execute_remote_management_command("hermes-agent", "hermes-workflow-register", current_review_record)


def resolve_workflow_priority_target(current_session_identifier, workflow_run_identifier, workflow_step_identifier):
    current_run_view = read_conversation_workflow_result(current_session_identifier, workflow_run_identifier)
    for current_step_record in current_run_view["steps"]:
        if current_step_record["step_id"] == workflow_step_identifier and current_step_record["state"] == "submitting":
            current_service_name = {"translation": "prompt-translation", "image": "flux-image"}[current_step_record["category"]]
            current_receipt_request = {"request_id": current_step_record["request_id"], "service": current_service_name}
            current_receipt_record = execute_remote_management_command("hermes-agent", "hermes-service-receipt", current_receipt_request)
            if (all(current_receipt_record.get(key) == value for key, value in current_receipt_request.items())
                    and current_receipt_record.get("state") == "accepted" and current_receipt_record.get("job_id")):
                return {"service": current_service_name, "id": current_receipt_record["job_id"]}
    raise gr.Error("접수된 단계의 서비스 작업 ID를 확인할 수 없습니다.")


def review_workflow_step_priority(current_session_identifier, workflow_run_identifier, workflow_step_identifier):
    from .operations_history_app import prepare_operations_priority_request
    current_target_record = resolve_workflow_priority_target(current_session_identifier, workflow_run_identifier, workflow_step_identifier)
    current_request_record, current_notice_text, _, current_button_update = prepare_operations_priority_request(current_target_record)
    return current_request_record, current_notice_text, current_button_update


def submit_workflow_step_priority(current_request_record, current_session_identifier, workflow_run_identifier, workflow_step_identifier):
    from .operations_history_app import submit_operations_priority_request
    current_target_record = resolve_workflow_priority_target(current_session_identifier, workflow_run_identifier, workflow_step_identifier)
    return submit_operations_priority_request(current_request_record, current_target_record)


def list_conversation_workflow_steps(current_session_identifier, current_category_name, current_state_name):
    return execute_remote_management_command("hermes-agent", "hermes-workflow-list",
        {"session_id": current_session_identifier, "category": current_category_name, "state": current_state_name})


def display_conversation_workflow_results(current_session_identifier, workflow_run_identifier):
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    current_run_view = read_conversation_workflow_result(current_session_identifier, workflow_run_identifier)
    translated_result_values = []
    image_result_links = []
    for current_result_record in current_run_view["results"]:
        current_output_record = current_result_record["outputs"]
        if "text" in current_output_record:
            translated_result_values.append(current_output_record["text"])
        if "preview" in current_output_record:
            current_job_identifier = current_result_record["job_id"]
            if not validate_service_job_identifier("flux-image", current_job_identifier):
                raise gr.Error("이미지 작업 ID를 확인할 수 없습니다.")
            expected_result_path = f"/flux-image-generator/jobs/{current_job_identifier}/result.png"
            if current_output_record["preview"] != expected_result_path:
                raise gr.Error("이미지 결과 경로가 작업과 일치하지 않습니다.")
            image_result_links.append(f"[생성 이미지 {len(image_result_links) + 1} 열기]({expected_result_path})")
    return current_run_view, "\n\n".join(translated_result_values), "\n\n".join(image_result_links)


def read_conversation_workflow_result(current_session_identifier, workflow_run_identifier):
    return execute_remote_management_command("hermes-agent", "hermes-workflow-view",
        {"session_id": current_session_identifier, "run_id": workflow_run_identifier})


def create_hermes_session_from_draft(hermes_draft_identifier):
    """응답 유실 시 같은 초안 ID로 세션 생성을 다시 확인한다."""
    try:
        hermes_session_record = execute_remote_management_command('hermes-agent', 'hermes-session-create', {'session_id': hermes_draft_identifier})
        hermes_choices_update, hermes_list_message = list_hermes_session_choices(hermes_session_record['id'])
        return hermes_choices_update, uuid.uuid4().hex, hermes_list_message
    except Exception as hermes_request_error:
        raise gr.Error('세션 생성 확인 실패: ' + str(hermes_request_error) + ' · 같은 요청으로 다시 확인하세요.') from hermes_request_error


def format_capture_settings_for_conversation(current_capture_settings):
    """검증된 캡처 설정을 대화에서 읽기 쉬운 항목으로 표시한다."""
    current_setting_labels={'map':'맵 ID','show_character':'캐릭터 표시','show_safe_boundary':'안전 구역 표시','edges':'경계 표시','tile_edges':'타일 경계 표시','ground':'바닥','zoom':'확대 배율','column':'가로 위치','row':'세로 위치','rotation':'회전 단계','outline':'외곽선','outline_width':'외곽선 두께','rim':'테두리 조명','shadow':'그림자','shadow_profile':'그림자 유형','contrast':'명암','saturation_reduced':'채도 감소','brightness_reduced':'밝기 감소','width':'너비','height':'높이'}
    current_option_labels={'paving':'포장 바닥','grass':'풀','meadow-road':'초원 길','baseline':'기본','contrast':'강조','broad':'넓게','original':'원본','soft':'부드럽게'}
    current_setting_lines=[]
    for current_setting_name,current_setting_value in current_capture_settings.items():
        if type(current_setting_value) is bool:
            current_display_value='켜짐' if current_setting_value else '꺼짐'
        elif isinstance(current_setting_value,str):
            current_display_value=current_option_labels.get(current_setting_value,current_setting_value) if current_setting_name in ('ground','shadow_profile','contrast') else current_setting_value
        else:
            current_display_value=str(current_setting_value)
        current_setting_lines.append('- '+current_setting_labels.get(current_setting_name,current_setting_name)+': '+current_display_value)
    return '\n'.join(current_setting_lines)


def format_hermes_conversation_answer(current_answer_text, current_answer_truncated=False):
    """검증된 제안 마커를 사용자가 취할 수 있는 다음 단계로 표시한다."""
    if not isinstance(current_answer_text, str) or not current_answer_text:
        return '아직 확인된 최종 답변이 없습니다.'
    if current_answer_truncated:
        return current_answer_text
    from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_capture_proposal, parse_hermes_model_preparation_proposal, parse_hermes_kimodo_resume_proposal, parse_hermes_flux_resume_proposal, parse_hermes_video_resume_proposal
    try:
        parse_hermes_video_resume_proposal(current_answer_text)
        current_prefix_text=current_answer_text.split('HERMES_VIDEO_RESUME_PROPOSAL',1)[0].rstrip()
        current_suffix_text=current_answer_text.split('END_HERMES_VIDEO_RESUME_PROPOSAL',1)[1].strip()
        return (current_prefix_text+'\n\n' if current_prefix_text else '')+'영상 재개 제안이 있습니다. 선택한 작업의 대상과 검토 상태를 확인하세요.'+('\n\n'+current_suffix_text if current_suffix_text else '')
    except (ValueError,TypeError,KeyError):
        pass
    try:
        parse_hermes_flux_resume_proposal(current_answer_text)
        current_prefix_text=current_answer_text.split('HERMES_FLUX_RESUME_PROPOSAL',1)[0].rstrip()
        current_suffix_text=current_answer_text.split('END_HERMES_FLUX_RESUME_PROPOSAL',1)[1].strip()
        return (current_prefix_text+'\n\n' if current_prefix_text else '')+'FLUX 재개 제안이 있습니다. 선택한 작업의 대상과 검토 상태를 확인하세요.'+('\n\n'+current_suffix_text if current_suffix_text else '')
    except (ValueError,TypeError,KeyError):
        pass
    try:
        parse_hermes_kimodo_resume_proposal(current_answer_text)
        current_prefix_text=current_answer_text.split('HERMES_KIMODO_RESUME_PROPOSAL',1)[0].rstrip()
        current_suffix_text=current_answer_text.split('END_HERMES_KIMODO_RESUME_PROPOSAL',1)[1].strip()
        return (current_prefix_text+'\n\n' if current_prefix_text else '')+'Kimodo 재개 제안이 있습니다. 선택한 작업의 대상과 검토 상태를 확인하세요.'+('\n\n'+current_suffix_text if current_suffix_text else '')
    except (ValueError,TypeError,KeyError):
        pass
    try:
        parse_hermes_model_preparation_proposal(current_answer_text)
        current_prefix_text=current_answer_text.split('HERMES_MODEL_PREPARATION_PROPOSAL',1)[0].rstrip()
        return (current_prefix_text+'\n\n' if current_prefix_text else '')+'모델 준비 제안이 있습니다. 작업을 선택해 대상과 영향을 검토하세요.'
    except (ValueError,TypeError,KeyError):
        pass
    try:
        current_capture_proposal=parse_hermes_capture_proposal(current_answer_text)
        current_prefix=current_answer_text.split('HERMES_CAPTURE_PROPOSAL',1)[0].rstrip()
        current_capture_label='맵 검수 캡처' if current_capture_proposal['service']=='map-review' else '캐릭터 검수 캡처'
        current_capture_settings=format_capture_settings_for_conversation(current_capture_proposal['settings'])
        current_capture_notice=(' 맵 등록 여부는 별도 확인이 필요합니다. 도구 탐색에서 맵 검수 화면을 열어 설정을 직접 확인할 수 있습니다. 원 도구의 캡처는 GPU를 사용할 수 있습니다.' if current_capture_proposal['service']=='map-review' else ' 캐릭터 표현 검수 화면은 폐기되어 직접 이동할 수 없습니다. 운영 이력의 현재 대기 항목에서 확인된 캡처 접수만 상태를 조회할 수 있습니다. 그 밖의 기록과 결과는 기존 원 서비스에서 확인하세요.')
        return (current_prefix+'\n\n' if current_prefix else '')+current_capture_label+' 제안 설정입니다. 현재 캡처 실행은 지원하지 않습니다.'+current_capture_notice+'\n\n'+current_capture_settings
    except (ValueError,TypeError,KeyError):
        pass
    from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_city_proposal, parse_hermes_building_proposal
    try:
        parse_hermes_building_proposal(current_answer_text)
        current_prefix=current_answer_text.split('HERMES_BUILDING_PROPOSAL',1)[0].rstrip()
        return (current_prefix+'\n\n' if current_prefix else '')+'건물 앵커 변경 제안이 있습니다. 작업을 선택해 변경 내용과 사용 맵을 검토하세요.'
    except (ValueError,TypeError,KeyError):
        pass
    try:
        parse_hermes_city_proposal(current_answer_text)
        current_prefix=current_answer_text.split('HERMES_CITY_PROPOSAL',1)[0].rstrip()
        return (current_prefix+'\n\n' if current_prefix else '')+'도시 맵 변경 제안이 있습니다. 작업을 선택해 변경 내용과 원본을 검토하세요.'
    except (ValueError,TypeError,KeyError):
        pass
    from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_kimodo_proposal, HERMES_PROPOSAL_START, parse_hermes_flux_proposal, HERMES_FLUX_PROPOSAL_START, parse_hermes_field_proposal, HERMES_FIELD_PROPOSAL_START, parse_hermes_translation_proposal, HERMES_TRANSLATION_PROPOSAL_START, parse_hermes_audio_proposal, HERMES_AUDIO_PROPOSAL_START, parse_hermes_video_proposal, HERMES_VIDEO_PROPOSAL_START, parse_hermes_billboard_proposal, HERMES_BILLBOARD_PROPOSAL_START, parse_hermes_effect_proposal, HERMES_EFFECT_PROPOSAL_START, parse_hermes_sprite_proposal, HERMES_SPRITE_PROPOSAL_START, parse_hermes_writer_proposal, HERMES_WRITER_PROPOSAL_START
    for current_parser, current_marker, current_instruction_text in ((parse_hermes_writer_proposal,HERMES_WRITER_PROPOSAL_START,'작가 AI 요청 제안이 있습니다. 세션 작업을 선택한 뒤 대화 아래 작업 제안에서 검토하세요.'), (parse_hermes_sprite_proposal,HERMES_SPRITE_PROPOSAL_START,'스프라이트 앵커 제안이 있습니다. 세션 작업을 선택한 뒤 대화 아래 맵·에셋 변경 제안에서 검토하세요.'), (parse_hermes_effect_proposal,HERMES_EFFECT_PROPOSAL_START,'이펙트 좌표 제안이 있습니다. 세션 작업을 선택한 뒤 대화 아래 맵·에셋 변경 제안에서 검토하세요.'), (parse_hermes_billboard_proposal,HERMES_BILLBOARD_PROPOSAL_START,'빌보드 속성 제안이 있습니다. 이 작업을 선택한 뒤 대화 아래 맵·에셋 변경 제안에서 검토하세요.'), (parse_hermes_kimodo_proposal, HERMES_PROPOSAL_START, 'Kimodo 작업 제안이 있습니다. 이 작업을 선택한 뒤 대화 아래 작업 제안에서 Kimodo 모션을 검토하세요.'), (parse_hermes_flux_proposal, HERMES_FLUX_PROPOSAL_START, 'FLUX 작업 제안이 있습니다. 이 작업을 선택한 뒤 대화 아래 작업 제안에서 FLUX 이미지를 검토하세요.'), (parse_hermes_field_proposal,HERMES_FIELD_PROPOSAL_START,'야외 맵 셀 제안이 있습니다. 이 작업을 선택한 뒤 대화 아래 맵·에셋 변경 제안에서 검토하세요.'), (parse_hermes_translation_proposal,HERMES_TRANSLATION_PROPOSAL_START,'번역 위임 제안이 있습니다. 이 작업을 선택한 뒤 대화 아래 작업 제안에서 번역을 검토하세요.'), (parse_hermes_audio_proposal,HERMES_AUDIO_PROPOSAL_START,'음악·효과음 제안이 있습니다. 이 작업을 선택한 뒤 대화 아래 작업 제안에서 음악·효과음을 검토하세요.'), (parse_hermes_video_proposal,HERMES_VIDEO_PROPOSAL_START,'동작·영상 제안이 있습니다. 이 작업을 선택한 뒤 대화 아래 첨부 영상 제안에서 설정과 첨부를 검토하세요.')):
        try:
            current_parsed_proposal=current_parser(current_answer_text)
        except (ValueError, TypeError, KeyError):
            continue
        if current_marker==HERMES_FLUX_PROPOSAL_START and current_parsed_proposal.get('service') in ('flux-mannequin','flux-billboard','flux-building','flux-expression'):
            current_instruction_text='FLUX 참조 이미지 제안이 있습니다. 이 작업을 선택한 뒤 대화 아래 첨부 이미지 제안에서 검토하세요.'
        current_marker_position = current_answer_text.rfind('\n' + current_marker + '\n')
        if current_marker_position < 0:
            if not current_answer_text.startswith(current_marker + '\n'):
                continue
            current_narrative_text = ''
        else:
            current_narrative_text = current_answer_text[:current_marker_position].rstrip()
        current_suffix_text = ''
        if current_marker in (HERMES_SPRITE_PROPOSAL_START,HERMES_EFFECT_PROPOSAL_START,HERMES_BILLBOARD_PROPOSAL_START,HERMES_FIELD_PROPOSAL_START,HERMES_TRANSLATION_PROPOSAL_START,HERMES_AUDIO_PROPOSAL_START,HERMES_VIDEO_PROPOSAL_START,HERMES_WRITER_PROPOSAL_START):
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
        if not isinstance(hermes_session_record,dict) or hermes_session_record.get('id')!=hermes_session_identifier or not isinstance(hermes_session_record.get('messages'),list):
            raise ValueError('세션 응답 식별 오류')
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
        if hermes_selected_job and hermes_selected_job not in hermes_job_identifiers:
            try:
                current_older_job=find_conversation_session_job(hermes_session_identifier,hermes_selected_job)
                current_older_status=(current_older_job.get('job') or {}).get('status') or {}
                hermes_job_choices.append((hermes_selected_job+' · '+str(current_older_status.get('status','unknown'))+' · 이전 작업',hermes_selected_job))
                hermes_job_identifiers.append(hermes_selected_job)
            except (gr.Error,OSError,ValueError,KeyError,TypeError,RuntimeError):
                pass
        hermes_selected_value = hermes_selected_job if hermes_selected_job in hermes_job_identifiers else (hermes_job_identifiers[-1] if hermes_job_identifiers else None)
        return hermes_conversation_values, hermes_session_message, gr.update(active=hermes_active_jobs), gr.update(choices=hermes_job_choices, value=hermes_selected_value)
    except Exception:
        return [], '세션 조회 실패 · 대화와 작업을 확인할 수 없습니다. 연결을 확인하고 대화 상태 새로고침을 누르세요. 저장된 이력이 삭제된 것은 아닙니다.', gr.update(active=False), gr.update(choices=[], value=None)



def validate_conversation_session_match(current_session_record,current_job_matches):
    """세션 전체에서 중복되거나 확인할 수 없는 제안 작업은 사용하지 않는다."""
    if not isinstance(current_session_record,dict) or not isinstance(current_job_matches,list) or len(current_job_matches)!=1:
        raise gr.Error('선택한 세션에 속한 완료 작업만 확인할 수 있습니다.')
    current_match_record=current_job_matches[0]
    if not isinstance(current_match_record,dict):raise gr.Error('세션 작업 연결을 확인할 수 없습니다.')
    current_unique_value=current_match_record.get('session_job_unique')
    if current_unique_value is not True and (current_unique_value is not None or current_session_record.get('truncated') is not False):
        raise gr.Error('세션 전체에서 작업 연결이 중복되었거나 확인되지 않았습니다. 이력을 확인하세요.')
    current_job_record=current_match_record.get('job') or {}
    current_status_record=current_job_record.get('status') or {} if isinstance(current_job_record,dict) else {}
    if not isinstance(current_status_record,dict) or current_status_record.get('status')!='completed':
        raise gr.Error('선택한 세션에 속한 완료 작업만 확인할 수 있습니다.')


def find_conversation_session_job(current_session_identifier,current_job_identifier):
    """고정된 세션 기록에서 완료 작업을 최근 페이지부터 찾는다."""
    if not isinstance(current_session_identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',current_session_identifier) or not isinstance(current_job_identifier,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_job_identifier):
        raise gr.Error('세션과 작업 ID를 확인하세요.')
    current_payload_record={'session_id':current_session_identifier}
    current_snapshot_value=None
    for current_page_number in range(10):
        current_session_record=execute_remote_management_command('hermes-agent','hermes-session-view',current_payload_record)
        if not isinstance(current_session_record,dict) or not isinstance(current_session_record.get('messages'),list):raise gr.Error('세션 이력을 확인할 수 없습니다.')
        if current_session_record.get('id')!=current_session_identifier:raise gr.Error('세션이 일치하지 않거나 확인되지 않습니다.')
        if current_page_number and (current_session_record.get('id')!=current_session_identifier or current_session_record.get('offset')!=current_payload_record['offset'] or current_session_record.get('snapshot')!=current_snapshot_value):
            raise gr.Error('세션 이력이 변경됐습니다. 다시 조회하세요.')
        current_matches=[item for item in current_session_record['messages'] if isinstance(item,dict) and item.get('job_id')==current_job_identifier]
        if current_matches:
            if current_page_number and current_matches[0].get('session_job_unique') is not True:
                raise gr.Error('세션 전체에서 작업 연결이 중복되었거나 확인되지 않았습니다.')
            validate_conversation_session_match(current_session_record,current_matches)
            return current_matches[0]
        current_next_offset=current_session_record.get('next_offset')
        if current_next_offset is None:break
        current_current_offset=current_payload_record.get('offset',0)
        current_first_snapshot=current_session_record.get('snapshot')
        if type(current_next_offset) is not int or current_next_offset<=current_current_offset or not isinstance(current_first_snapshot,str) or not re.fullmatch(r'[a-f0-9]{64}',current_first_snapshot) or (current_snapshot_value is not None and current_first_snapshot!=current_snapshot_value):
            raise gr.Error('세션 페이지를 확인할 수 없습니다. 다시 조회하세요.')
        current_snapshot_value=current_first_snapshot
        current_payload_record={'session_id':current_session_identifier,'offset':current_next_offset,'snapshot':current_snapshot_value}
    raise gr.Error('이 세션에서 완료된 작업을 찾지 못했습니다. 운영 이력의 작업 ID와 세션을 확인하세요.')


def select_older_conversation_job(current_session_identifier,current_job_identifier):
    """운영 이력에서 찾은 작업을 같은 대화의 제안 선택에 연결한다."""
    current_match_record=find_conversation_session_job(current_session_identifier,current_job_identifier)
    current_status_record=(current_match_record.get('job') or {}).get('status') or {}
    current_label_value=current_job_identifier+' · '+str(current_status_record.get('status','unknown'))
    return gr.update(choices=[(current_label_value,current_job_identifier)],value=current_job_identifier),'이전 작업을 선택했습니다. 아래 제안 종류를 선택해 확인하세요.'


def build_conversation_direct_link(current_session_identifier):
    """직접 작업 화면으로 현재 세션을 명시적으로 전달한다."""
    current_session_query = '?session=' + current_session_identifier if isinstance(current_session_identifier,str) and re.fullmatch(r'[a-f0-9]{32}',current_session_identifier) else ''
    return '<a href="/management/frame/hermes-direct/' + current_session_query + '" target="_blank" rel="noopener">직접 조회와 작업 열기</a>'


def build_conversation_history_link(current_session_identifier,current_job_identifier):
    """선택한 세션과 작업의 이력 검색 링크를 생성한다."""
    if not isinstance(current_session_identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',current_session_identifier) or not isinstance(current_job_identifier,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_job_identifier):
        return '<p>세션과 작업을 선택하세요.</p>'
    return '<a href="/management/frame/operations-history/?job='+current_job_identifier+'&amp;session='+current_session_identifier+'" target="_blank" rel="noopener">선택 작업을 운영 이력에서 찾기</a><p>이력에서 작업 행을 선택해 상세를 확인하세요.</p>'


def restore_linked_conversation_job(current_session_identifier,current_job_identifier):
    """이력에서 전달된 작업은 세션 조회 후 검증해 선택한다."""
    if not current_job_identifier:return gr.update(),''
    try:
        return select_older_conversation_job(current_session_identifier,current_job_identifier)
    except (gr.Error,OSError,ValueError,KeyError,TypeError,RuntimeError):
        return gr.update(),'이력에서 지정한 작업을 이 세션에서 확인할 수 없습니다. 운영 이력을 다시 확인하세요.'


def prepare_conversation_kimodo_review(current_session_identifier, current_source_job_identifier, current_keyframe_attachment=None):
    """세션에 속한 완료 작업의 Kimodo 제안을 기존 검증기로 고정한다."""
    import hashlib
    if not current_session_identifier or not current_source_job_identifier:
        raise gr.Error('세션과 제안을 만든 작업을 선택하세요.')
    find_conversation_session_job(current_session_identifier,current_source_job_identifier)
    current_proposal_record = read_matching_hermes_edit_proposal(current_source_job_identifier,'hermes-kimodo-proposal')
    current_identifier_bytes = (current_session_identifier + ':' + current_source_job_identifier).encode('utf-8')
    current_keyframes_text=''
    current_keyframe_validation=None
    if current_keyframe_attachment is not None:
        import json
        if not isinstance(current_keyframe_attachment,dict) or set(current_keyframe_attachment)!={'session_id','receipt_id','keyframe_id','output_frame'} or current_keyframe_attachment['session_id']!=current_session_identifier or not isinstance(current_keyframe_attachment['receipt_id'],str) or not re.fullmatch(r'keyframe_[a-f0-9]{64}',current_keyframe_attachment['receipt_id']) or not isinstance(current_keyframe_attachment['keyframe_id'],str) or not re.fullmatch(r'[a-f0-9]{32}',current_keyframe_attachment['keyframe_id']) or type(current_keyframe_attachment['output_frame']) is not int or not 1<=current_keyframe_attachment['output_frame']<=current_proposal_record['frames']:raise gr.Error('키프레임 선택 또는 출력 프레임 오류')
        current_saved_receipt=execute_remote_management_command('hermes-agent','hermes-kimodo-keyframe-receipt',{'request_id':current_keyframe_attachment['receipt_id']})
        if not isinstance(current_saved_receipt,dict) or (current_saved_receipt.get('request_id'),current_saved_receipt.get('state'),current_saved_receipt.get('keyframe_id'))!=(current_keyframe_attachment['receipt_id'],'completed',current_keyframe_attachment['keyframe_id']):raise gr.Error('저장된 키프레임 접수를 확인할 수 없습니다.')
        current_placements_value=[{'id':current_keyframe_attachment['keyframe_id'],'frame':current_keyframe_attachment['output_frame']}]
        current_verified_value=execute_remote_management_command('hermes-agent','hermes-kimodo-keyframe-validate',{'keyframes':current_placements_value,'frames':current_proposal_record['frames']})
        if not isinstance(current_verified_value,dict) or current_verified_value.get('placements')!=current_placements_value or not isinstance(current_verified_value.get('sources'),list) or len(current_verified_value['sources'])!=1 or not isinstance(current_verified_value['sources'][0],dict) or current_verified_value['sources'][0].get('id')!=current_keyframe_attachment['keyframe_id'] or not isinstance(current_verified_value['sources'][0].get('preview_sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_verified_value['sources'][0]['preview_sha256']):raise gr.Error('키프레임 원본 검증을 확인할 수 없습니다.')
        current_source_hash=current_verified_value['sources'][0].get('source_sha256')
        if not isinstance(current_source_hash,str) or not re.fullmatch(r'[a-f0-9]{64}',current_source_hash):raise gr.Error('키프레임 원본 검증을 확인할 수 없습니다.')
        current_skeleton_hash=current_verified_value.get('skeleton_signature_sha256')
        if not isinstance(current_skeleton_hash,str) or not re.fullmatch(r'[a-f0-9]{64}',current_skeleton_hash):raise gr.Error('키프레임 골격 검증을 확인할 수 없습니다.')
        current_keyframe_validation={'preview_sha256':current_verified_value['sources'][0]['preview_sha256'],'skeleton_signature_sha256':current_skeleton_hash,'source_sha256':current_source_hash}
        current_keyframes_text=json.dumps(current_placements_value,ensure_ascii=False)
        current_identifier_bytes+=b':keyframe:'+json.dumps(current_keyframe_attachment,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    current_request_identifier = 'chat_' + hashlib.sha256(current_identifier_bytes).hexdigest()
    current_review_record, current_preview_text, current_review_message = review_hermes_kimodo_request(current_proposal_record['prompt'], current_proposal_record['frames'], current_proposal_record['steps'], current_proposal_record['seed'], current_request_identifier,current_keyframes_text)
    if not current_review_record:
        raise gr.Error(current_review_message)
    if current_keyframe_attachment is not None:current_review_record['request']['keyframe_source_hashes']={current_keyframe_attachment['keyframe_id']:current_keyframe_validation['source_sha256']}
    current_receipt_record = execute_remote_management_command('hermes-agent', 'hermes-delegation-status', {'request_id': current_request_identifier})
    current_receipt_state = current_receipt_record.get('state') if isinstance(current_receipt_record,dict) else None
    current_card_record = {'session_id': current_session_identifier, 'source_job_id': current_source_job_identifier, 'review': current_review_record, 'ready': False}
    if current_keyframe_attachment is not None:
        current_card_record['keyframe_attachment']=dict(current_keyframe_attachment)
        current_card_record['keyframe_validation']=current_keyframe_validation
        current_preview_text+='\n저장 사본 미리보기 SHA-256: '+current_keyframe_validation['preview_sha256']+'\n원본 확인값: '+current_keyframe_validation['source_sha256']+'\n골격 확인값: '+current_keyframe_validation['skeleton_signature_sha256']
    if current_receipt_state not in ('not_found', 'accepted', 'unknown') or current_receipt_record.get('request_id') not in (None,current_request_identifier) or current_receipt_record.get('service') not in (None,'kimodo'):
        return current_card_record,current_preview_text,'접수 ID 또는 서비스를 확인할 수 없습니다. Kimodo 이력을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_state in ('not_found','accepted') and (current_receipt_record.get('request_id')!=current_request_identifier or current_receipt_record.get('service')!='kimodo'):
        return current_card_record,current_preview_text,'접수 ID와 서비스를 확인할 수 없습니다. 게이트웨이와 Kimodo 이력을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_state=='accepted':
        from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
        if not validate_service_job_identifier('kimodo',current_receipt_record.get('job_id')):raise gr.Error('Kimodo 접수 작업을 확인할 수 없습니다.')
    current_card_record['ready']=current_receipt_state=='not_found'
    current_result_text={'not_found':'아직 접수하지 않았습니다. 내용을 확인한 뒤 대기열에 추가할 수 있습니다.','accepted':'기존 Kimodo 접수가 있습니다. 작업 상태와 결과 확인 버튼으로 조회하세요.','unknown':'접수 결과 확인 불가 · Kimodo 작업 이력을 확인하세요. 자동으로 다시 접수하지 않습니다.'}[current_receipt_state]
    return current_card_record, current_preview_text, current_result_text



def build_conversation_result_link(current_service_name,current_job_identifier,current_session_identifier=None):
    """지원되는 원 서비스와 검증된 ID로만 이력 링크를 만든다."""
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    from tools.review.domains.hermes_agent.video_operations import HERMES_VIDEO_SERVICES
    from tools.review.domains.hermes_agent.audio_operations import HERMES_AUDIO_SERVICES
    from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
    current_page_mapping={'kimodo':'kimodo-generator',**{current_name:current_name+'-generator' for current_name in HERMES_VIDEO_SERVICES},**{current_name:current_name for current_name in HERMES_AUDIO_SERVICES},**{current_name:current_name+'-generator' for current_name in FLUX_IMAGE_PROFILE_RECORDS},'flux-expression':'flux-expression-generator','prompt-translation':'prompt-translation','writer-agent':'writer-agent'}
    current_page_name=current_page_mapping.get(current_service_name)
    if current_page_name is None:return None
    current_page_path='/management/frame/'+current_page_name+'/'
    current_query_parts=[]
    if validate_service_job_identifier(current_service_name,current_job_identifier):current_query_parts.append('job='+current_job_identifier)
    if isinstance(current_session_identifier,str) and re.fullmatch(r'[a-f0-9]{32}',current_session_identifier):current_query_parts.append('session='+current_session_identifier)
    if current_query_parts:current_page_path+='?'+'&'.join(current_query_parts)
    return current_page_path


def read_conversation_kimodo_result(current_card_record, current_session_identifier, current_source_job_identifier, current_expected_job_identifier=None):
    """선택한 세션·제안의 접수와 실제 작업 상태를 구분한다."""
    if not isinstance(current_card_record, dict) or (current_card_record.get('session_id'), current_card_record.get('source_job_id')) != (current_session_identifier, current_source_job_identifier):
        raise gr.Error('세션과 제안 작업이 바뀌었습니다. 다시 제안을 확인하세요.')
    current_request_identifier = current_card_record['review']['request_id']
    current_result_record = execute_remote_management_command('hermes-agent', 'hermes-delegation-job-status', {'request_id': current_request_identifier})
    current_receipt_record = current_result_record.get('receipt') or {}
    current_receipt_state = current_receipt_record.get('state')
    if current_receipt_state in ('not_found','accepted') and (current_receipt_record.get('request_id')!=current_request_identifier or current_receipt_record.get('service')!='kimodo'):
        raise gr.Error('Kimodo 접수 ID와 서비스를 확인할 수 없습니다. 게이트웨이와 원 서비스 이력을 확인하세요.')
    if current_expected_job_identifier is not None and (current_receipt_state != 'accepted' or current_receipt_record.get('job_id') != current_expected_job_identifier):
        raise gr.Error('Kimodo 접수 응답과 작업 이력이 일치하지 않습니다. 같은 접수 ID를 확인하세요.')
    if current_receipt_state == 'not_found':
        return '아직 접수하지 않았습니다. 내용을 확인한 뒤 대기열에 추가할 수 있습니다.'
    if current_receipt_state == 'unknown':
        return '접수 결과 확인 불가 · Kimodo 작업 이력을 확인하세요. 자동으로 다시 접수하지 않습니다.'
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    if current_receipt_state != 'accepted' or not validate_service_job_identifier('kimodo',current_receipt_record.get('job_id')):
        raise gr.Error('접수 상태를 확인할 수 없습니다.')
    current_job_identifier = current_receipt_record['job_id']
    current_job_record = current_result_record.get('job') or {}
    current_job_state = current_job_record.get('status', 'unknown')
    current_status_labels = {'queued':'대기 중', 'running':'실행 중', 'completed':'완료', 'failed':'실패', 'cancelled':'취소됨', 'canceled':'취소됨', 'paused':'일시정지', 'unknown':'확인 불가'}
    current_result_lines = ['Kimodo 작업 ' + current_job_identifier + ' · ' + current_status_labels.get(current_job_state, '확인 불가'), '이전에 접수된 작업입니다. 현재 제안과 기존 접수 입력의 일치 여부는 별도로 확인해야 합니다.', '상태 조회 시 기존 중단 작업 복구가 따를 수 있습니다.']
    current_progress_record = current_job_record.get('progress')
    if isinstance(current_progress_record, dict) and type(current_progress_record.get('percent')) in (int, float):
        current_result_lines.append('진행률: ' + str(current_progress_record['percent']) + '%')
    for current_field_name, current_field_label in (('message', '안내'), ('error', '오류')):
        if isinstance(current_job_record.get(current_field_name), str) and current_job_record[current_field_name]:
            current_result_lines.append(current_field_label + ': ' + current_job_record[current_field_name])
    if current_job_state == 'failed' and isinstance(current_job_record.get('failure_reason'),str):
        current_result_lines.append('실패 안내: '+current_job_record['failure_reason'])
    if current_job_state == 'completed':
        current_source_observation=read_conversation_video_source_observation('kimodo',current_job_identifier)
        if current_source_observation is None:
            current_result_lines.append('원본 결과 확인 불가 · Kimodo 도구에서 확인하세요.')
        elif current_source_observation['status']!='completed':
            current_result_lines.append('원본 작업 상태가 변경되어 결과를 다시 확인해야 합니다.')
        elif current_source_observation['result_status']=='available':
            current_result_lines.append('결과 파일 존재는 조회 시점 기준이며 생성 품질이나 재생은 별도 확인하세요.')
            for current_field_name,current_label_text in (('video','생성 영상'),('image','첫 프레임'),('download','프레임 ZIP')):
                current_result_lines.append('['+current_label_text+']('+current_source_observation[current_field_name]+')')
        else:
            current_result_lines.append('완료 기록은 있으나 영상·프레임·ZIP 파일을 모두 확인할 수 없습니다. 참조 분석 전용 결과는 Kimodo 도구에서 확인하세요.')
        current_result_lines.append('생성 완료는 품질 승인을 뜻하지 않습니다.')
    return '  \n'.join(current_result_lines) + '  \n[Kimodo 작업과 결과 열기]('+build_conversation_result_link('kimodo',current_job_identifier,current_session_identifier)+')'


def submit_conversation_kimodo_review(current_card_record, current_session_identifier, current_source_job_identifier):
    """확인 시 제안과 세션을 다시 검증하고 기존 중복 방지 접수를 사용한다."""
    if not isinstance(current_card_record, dict) or current_card_record.get('ready') is not True:
        raise gr.Error('먼저 실행 가능한 제안을 검토하세요.')
    if (current_card_record.get('session_id'), current_card_record.get('source_job_id')) != (current_session_identifier, current_source_job_identifier):
        raise gr.Error('세션이나 제안 작업이 바뀌었습니다. 다시 검토하세요.')
    current_attachment_value=current_card_record.get('keyframe_attachment')
    if current_attachment_value is None:current_fresh_record, _, current_current_result = prepare_conversation_kimodo_review(current_session_identifier, current_source_job_identifier)
    else:current_fresh_record, _, current_current_result = prepare_conversation_kimodo_review(current_session_identifier, current_source_job_identifier,current_attachment_value)
    if current_attachment_value is not None and current_fresh_record.get('keyframe_validation')!=current_card_record.get('keyframe_validation'):
        raise gr.Error('키프레임 원본이 변경됐습니다. 다시 검토하세요.')
    if current_fresh_record['review'] != current_card_record['review']:
        raise gr.Error('제안이 변경됐습니다. 다시 검토하세요.')
    if not current_fresh_record['ready']:
        return current_fresh_record, current_current_result
    try:
        current_submitted_job,_ = submit_hermes_kimodo_request(current_fresh_record['review'])
    except (gr.Error,OSError,ValueError,TypeError,RuntimeError):
        return {**current_fresh_record,'ready':False}, '접수 결과 확인 불가 · Kimodo 이력과 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'
    current_fresh_record['ready'] = False
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    if not validate_service_job_identifier('kimodo',current_submitted_job):
        return current_fresh_record, '접수 결과 확인 불가 · Kimodo 이력과 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'
    try:
        current_current_result = read_conversation_kimodo_result(current_fresh_record, current_session_identifier, current_source_job_identifier, current_submitted_job)
    except Exception:
        current_current_result = '접수 결과를 확인할 수 없습니다. 같은 제안을 다시 열어 상태를 확인하세요. 자동 재접수하지 않습니다.'
    return current_fresh_record, current_current_result



def prepare_conversation_service_review(current_session_identifier, current_source_job_identifier, current_service_kind):
    """세션의 완료 제안을 서비스별 검증기에 전달하고 같은 접수를 복원한다."""
    import hashlib
    import json
    if current_service_kind == 'kimodo':
        current_card_record, current_preview_text, current_result_text = prepare_conversation_kimodo_review(current_session_identifier, current_source_job_identifier)
        return {**current_card_record, 'kind':'kimodo'}, current_preview_text, current_result_text
    if current_service_kind not in ('flux','translation','audio','video','writer','model_preparation','kimodo_resume','flux_resume','video_resume'):
        raise gr.Error('지원하는 제안 종류를 선택하세요.')
    if not current_session_identifier or not current_source_job_identifier:
        raise gr.Error('세션과 제안을 만든 작업을 선택하세요.')
    find_conversation_session_job(current_session_identifier,current_source_job_identifier)
    current_proposal_command={'model_preparation':'hermes-model-preparation-proposal','kimodo_resume':'hermes-kimodo-resume-proposal','flux_resume':'hermes-flux-resume-proposal','video_resume':'hermes-video-resume-proposal'}.get(current_service_kind,'hermes-'+current_service_kind+'-proposal')
    current_proposal_record = read_matching_hermes_edit_proposal(current_source_job_identifier,current_proposal_command)
    current_request_identifier = 'chat_' + hashlib.sha256((current_session_identifier+':'+current_source_job_identifier+':'+current_service_kind).encode()).hexdigest()
    if current_service_kind == 'kimodo_resume':
        current_target_job=current_proposal_record['job_id']
        current_expected_fingerprint=current_proposal_record['expected_resume_fingerprint']
        current_request_identifier='kimodo_resume_'+hashlib.sha256(('kimodo\0'+current_target_job+'\0'+current_expected_fingerprint).encode()).hexdigest()
        current_review_record={'request_id':current_request_identifier,'job_id':current_target_job,'expected_resume_fingerprint':current_expected_fingerprint}
        current_card_record={'session_id':current_session_identifier,'source_job_id':current_source_job_identifier,'kind':current_service_kind,'service':'kimodo','review':current_review_record,'ready':False}
        current_preview_text='Kimodo 기존 작업: '+current_target_job+'\n접수 ID: '+current_request_identifier+'\n확인하면 기존 작업을 GPU 대기열에 다시 추가합니다. 실행과 메모리 여유는 별도 확인합니다.'
        current_receipt_record=execute_remote_management_command('hermes-agent','hermes-kimodo-resume-receipt',{'request_id':current_request_identifier})
        if not isinstance(current_receipt_record,dict) or current_receipt_record.get('request_id')!=current_request_identifier or current_receipt_record.get('state') not in ('not_found','accepted','unknown'):
            raise gr.Error('재개 접수 기록을 확인할 수 없습니다. 원 서비스 이력을 확인하세요.')
        if current_receipt_record['state']!='not_found':
            if any(current_receipt_record.get(current_key_name)!=current_value for current_key_name,current_value in (('service','kimodo'),('job_id',current_target_job),('expected_resume_fingerprint',current_expected_fingerprint))):
                raise gr.Error('재개 접수 대상이 일치하지 않습니다. 원 서비스 이력을 확인하세요.')
            current_status_text='기존 재개 접수가 있습니다. 상태와 결과를 확인하세요.' if current_receipt_record['state']=='accepted' else '재개 접수 결과 확인 필요 · 원 서비스와 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'
            return current_card_record,current_preview_text,current_status_text
        current_preview_record=execute_remote_management_command('hermes-agent','hermes-kimodo-resume-preview',{'job_id':current_target_job})
        if not isinstance(current_preview_record,dict) or (current_preview_record.get('service'),current_preview_record.get('job_id'),current_preview_record.get('expected_resume_fingerprint'))!=('kimodo',current_target_job,current_expected_fingerprint) or current_preview_record.get('status') not in ('failed','cancelled','paused'):
            raise gr.Error('검토한 작업이나 확인값이 바뀌었습니다. 현재 상태를 다시 조회하세요.')
        current_preview_text+='\n기록 상태: '+current_preview_record['status']
        current_availability=current_preview_record.get('resume_availability','unknown')
        if current_availability!='available':
            return current_card_record,current_preview_text,('모델 준비가 진행 중입니다. 완료 후 다시 검토하세요.' if current_availability=='download_running' else '모델 준비 상태를 확인할 수 없습니다. 원 서비스를 확인하세요.')
        current_card_record['ready']=True
        current_source_link=build_conversation_result_link('kimodo',current_target_job,current_session_identifier)
        current_status_text='재개 대상과 입력을 확인하세요. 기존 생성 입력과 결과는 Kimodo 이력에서 확인해야 합니다.'
        if current_source_link:current_status_text+='  \n[기존 Kimodo 작업 열기]('+current_source_link+')'
        return current_card_record,current_preview_text,current_status_text
    if current_service_kind in ('flux_resume','video_resume'):
        current_target_service=current_proposal_record['service']
        current_target_job=current_proposal_record['job_id']
        current_expected_fingerprint=current_proposal_record['expected_resume_fingerprint']
        current_request_identifier=current_service_kind+'_'+hashlib.sha256((current_target_service+'\0'+current_target_job+'\0'+current_expected_fingerprint).encode()).hexdigest()
        current_review_record={'request_id':current_request_identifier,'service':current_target_service,'job_id':current_target_job,'expected_resume_fingerprint':current_expected_fingerprint}
        current_card_record={'session_id':current_session_identifier,'source_job_id':current_source_job_identifier,'kind':current_service_kind,'service':current_target_service,'review':current_review_record,'ready':False}
        current_preview_text=('FLUX 서비스: ' if current_service_kind=='flux_resume' else '영상 서비스: ')+current_target_service+'\n기존 작업: '+current_target_job+'\n접수 ID: '+current_request_identifier+'\n확인하면 기존 작업을 GPU 대기열에 다시 추가합니다. 실행과 메모리 여유는 별도 확인합니다.'
        if current_service_kind=='video_resume':
            current_preview_text+='\n재개 검토는 중단된 실행 기록을 복구할 수 있습니다.'
        current_receipt_record=execute_remote_management_command('hermes-agent','hermes-'+('flux' if current_service_kind=='flux_resume' else 'video')+'-resume-receipt',{'request_id':current_request_identifier})
        if not isinstance(current_receipt_record,dict) or current_receipt_record.get('request_id')!=current_request_identifier or current_receipt_record.get('state') not in ('not_found','accepted','unknown'):
            raise gr.Error('재개 접수 기록을 확인할 수 없습니다. 원 서비스 이력을 확인하세요.')
        if current_receipt_record['state']!='not_found':
            if any(current_receipt_record.get(current_key_name)!=current_value for current_key_name,current_value in (('service',current_target_service),('job_id',current_target_job),('expected_resume_fingerprint',current_expected_fingerprint))):
                raise gr.Error('재개 접수 대상이 일치하지 않습니다. 원 서비스 이력을 확인하세요.')
            current_status_text='기존 재개 접수가 있습니다. 상태와 결과를 확인하세요.' if current_receipt_record['state']=='accepted' else '재개 접수 결과 확인 필요 · 원 서비스와 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'
            return current_card_record,current_preview_text,current_status_text
        current_preview_record=execute_remote_management_command('hermes-agent','hermes-'+('flux' if current_service_kind=='flux_resume' else 'video')+'-resume-preview',{'service':current_target_service,'job_id':current_target_job})
        if not isinstance(current_preview_record,dict) or (current_preview_record.get('service'),current_preview_record.get('job_id'),current_preview_record.get('expected_resume_fingerprint'))!=(current_target_service,current_target_job,current_expected_fingerprint) or current_preview_record.get('status') not in ('failed','cancelled','paused'):
            raise gr.Error('검토한 작업이나 확인값이 바뀌었습니다. 현재 상태를 다시 조회하세요.')
        current_preview_text+='\n기록 상태: '+current_preview_record['status']
        current_availability=current_preview_record.get('resume_availability','unknown')
        if current_availability!='available':
            return current_card_record,current_preview_text,('모델 준비가 진행 중입니다. 완료 후 다시 검토하세요.' if current_availability=='download_running' else '모델 준비 상태를 확인할 수 없습니다. 원 서비스를 확인하세요.')
        current_card_record['ready']=True
        current_source_link=build_conversation_result_link(current_target_service,current_target_job,current_session_identifier)
        current_status_text='재개 대상과 입력을 확인하세요. 기존 생성 입력과 결과는 원 서비스 이력에서 확인해야 합니다.'
        if current_source_link:current_status_text+='  \n[기존 작업 열기]('+current_source_link+')'
        return current_card_record,current_preview_text,current_status_text
    if current_service_kind == 'model_preparation':
        current_service_name=current_proposal_record['service']
        current_review_record,current_preview_text,_=review_hermes_model_preparation(current_service_name,current_request_identifier)
        current_card_record={'session_id':current_session_identifier,'source_job_id':current_source_job_identifier,'kind':current_service_kind,'service':current_service_name,'review':current_review_record,'ready':False}
        try:
            current_receipt_record=execute_remote_management_command('hermes-agent','hermes-model-prepare-status',current_review_record)
            if not isinstance(current_receipt_record,dict) or current_receipt_record.get('request_id')!=current_request_identifier or current_receipt_record.get('service')!=current_service_name or current_receipt_record.get('state') not in ('not_found','accepted','unknown'):
                raise ValueError('모델 준비 접수 식별 오류')
            current_receipt_state=current_receipt_record['state']
            current_card_record['ready']=current_receipt_state=='not_found'
            current_status_text={'not_found':'아직 접수하지 않았습니다. 대상과 영향을 검토하고 확인하세요.','accepted':'기존 접수가 있습니다. 모델 상태와 접수 기록을 확인하세요.','unknown':'접수 결과 확인 불가 · 원 서비스와 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'}[current_receipt_state]
            return current_card_record,current_preview_text,current_status_text
        except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError):
            return current_card_record,current_preview_text,'접수 ID 또는 서비스를 확인할 수 없습니다. 원 서비스 이력을 확인하고 자동 재접수하지 마세요.'
    if current_service_kind == 'flux':
        current_service_name=current_proposal_record.get('service','flux-image')
        if current_service_name in ('flux-mannequin','flux-billboard','flux-building','flux-expression'):
            raise gr.Error('첫 참조 이미지가 필요합니다. 대화의 첨부 이미지 제안에서 검토하세요.')
        if current_service_name=='flux-image':
            current_review_record,current_preview_text,current_message_text,_=review_hermes_flux_request(current_proposal_record['prompt'],current_proposal_record['width'],current_proposal_record['height'],current_proposal_record['seed'],current_request_identifier)
        else:
            current_review_record,current_preview_text,current_message_text,_=review_hermes_flux_profile_request(current_service_name,current_proposal_record['prompt'],current_proposal_record['width'],current_proposal_record['height'],current_proposal_record['seed'],None,None,current_request_identifier)
    elif current_service_kind == 'translation':
        current_glossary_text = '\n'.join(item['source']+' => '+item['target'] for item in current_proposal_record['glossary'])
        current_review_record,current_preview_text,current_message_text,_ = review_hermes_translation_request(current_proposal_record['text'],current_proposal_record['target_language'],current_glossary_text,current_request_identifier)
        current_preview_text += '\n원문: '+current_proposal_record['text']+'\n용어: '+(current_glossary_text or '없음')
        current_service_name = 'prompt-translation'
    elif current_service_kind == 'writer':
        current_service_name = 'writer-agent'
        current_review_record,current_preview_text,current_message_text,_ = review_hermes_writer_request(current_proposal_record['mode'],current_proposal_record['prompt'],current_request_identifier)
    elif current_service_kind == 'audio':
        current_request_record = current_proposal_record['request']
        current_service_name = current_proposal_record['service']
        current_review_record,current_preview_text,current_message_text,_ = review_hermes_audio_request(current_service_name,current_request_record['prompt'],current_request_record.get('lyrics',''),current_request_record.get('duration_seconds',30),current_request_record['loop_request'],current_request_record['seed'],current_request_identifier)
        if current_request_record.get('lyrics'):
            current_preview_text += '\n가사: '+current_request_record['lyrics']
    else:
        current_service_name=current_proposal_record['service']
        if (current_service_name,current_proposal_record['mode'])!=('wan22-vace','text'):
            raise gr.Error('이미지·영상 첨부가 필요한 제안입니다. 기존 동작·영상 생성 기능에서 첨부를 검토하세요.')
        current_settings_record=json.loads(default_hermes_video_settings(current_service_name))
        current_settings_record.update(mode='text',prompt=current_proposal_record['prompt'])
        current_settings_text=json.dumps(current_settings_record,ensure_ascii=False)
        current_review_record,current_preview_text,current_message_text,_=review_hermes_video_request(current_service_name,current_settings_text,None,None,None,None,None,current_request_identifier)
        current_preview_text+='\n영상 설정(기본값 포함): '+current_settings_text
        current_preview_text+='\n영상 생성은 GPU 메모리와 실행 시간을 많이 사용할 수 있습니다.'
    if not current_review_record:
        raise gr.Error(current_message_text)
    current_card_record={'session_id':current_session_identifier,'source_job_id':current_source_job_identifier,'kind':current_service_kind,'service':current_service_name,'review':current_review_record,'ready':False}
    try:
        current_receipt_record=execute_remote_management_command('hermes-agent','hermes-service-receipt',{'request_id':current_request_identifier,'service':current_service_name})
        if not isinstance(current_receipt_record,dict) or current_receipt_record.get('request_id')!=current_request_identifier or current_receipt_record.get('service')!=current_service_name or current_receipt_record.get('state') not in ('not_found','accepted','unknown'):
            raise ValueError('접수 ID 또는 서비스 오류')
        if current_receipt_record['state']=='accepted':
            from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
            if not validate_service_job_identifier(current_service_name,current_receipt_record.get('job_id')):raise ValueError('접수 작업 ID 오류')
    except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError):
        return current_card_record,current_preview_text,'접수 서비스 또는 작업을 확인할 수 없습니다. 원 서비스와 접수 이력을 확인하고 자동 재접수하지 마세요.'
    current_receipt_state=current_receipt_record['state']
    current_card_record['ready']=current_receipt_state=='not_found'
    current_status_text={'not_found':'아직 접수하지 않았습니다. 내용을 검토한 뒤 대기열에 추가하세요.','unknown':'접수 결과 확인 불가 · 원래 도구의 이력을 확인하세요. 자동으로 다시 접수하지 않습니다.','accepted':'기존 접수가 있습니다. 작업 상태와 결과 확인 버튼으로 조회하세요.'}[current_receipt_state]
    return current_card_record,current_preview_text,current_status_text


def read_conversation_flux_source_observation(current_service_name,current_job_identifier):
    """기존 접수의 이미지 원본을 복구 없이 재확인한다."""
    from tools.review.domains.hermes_agent.flux_profile_operations import validate_hermes_flux_source_response
    try:
        current_response_value=execute_remote_management_command('hermes-agent','hermes-flux-source-status',{'service':current_service_name,'job_id':current_job_identifier})
    except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError,AttributeError):
        return None
    try:
        return validate_hermes_flux_source_response(current_service_name,current_job_identifier,current_response_value)
    except (ValueError,TypeError,KeyError,AttributeError) as current_response_error:
        raise gr.Error('이미지 원본 응답이 일치하지 않아 결과 링크를 표시하지 않습니다.') from current_response_error


def read_conversation_video_source_observation(current_service_name,current_job_identifier):
    """접수된 영상 원본의 결과 파일을 복구 없이 재확인한다."""
    from tools.review.domains.hermes_agent.video_operations import validate_hermes_video_source_response
    try:
        current_response_value=execute_remote_management_command('hermes-agent','hermes-video-source-status',{'service':current_service_name,'job_id':current_job_identifier})
    except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError,AttributeError):
        return None
    try:
        return validate_hermes_video_source_response(current_service_name,current_job_identifier,current_response_value)
    except (ValueError,TypeError,KeyError,AttributeError) as current_response_error:
        raise gr.Error('영상 원본 응답이 일치하지 않아 결과 링크를 표시하지 않습니다.') from current_response_error


def format_conversation_translation_result(current_result_record):
    """번역문과 검토 항목을 구분해 제한된 일반 텍스트로 표시한다."""
    import json
    if not isinstance(current_result_record,dict) or not isinstance(current_result_record.get('text'),str) or len(current_result_record['text'])>12000:raise ValueError('번역 결과 형식 오류')
    current_lines_value=['번역 결과','',*['    '+current_line for current_line in (current_result_record['text'].splitlines() or [''])]]
    for current_field_name,current_label_text in (('term_checks','용어 검사'),('quality_checks','조건 검사')):
        current_check_records=current_result_record.get(current_field_name,[])
        if not isinstance(current_check_records,list) or len(current_check_records)>200 or any(not isinstance(current_check_record,dict) for current_check_record in current_check_records):raise ValueError('번역 검토 항목 형식 오류')
        current_lines_value.extend(['',current_label_text+' '+str(len(current_check_records))+'건'])
        for current_check_record in current_check_records[:5]:
            current_display_record={current_key_name:(current_field_value[:200] if isinstance(current_field_value,str) else current_field_value) for current_key_name in ('source','target','status','source_count','target_count') if type(current_field_value:=current_check_record.get(current_key_name)) in (str,int)}
            current_lines_value.extend(['','    '+json.dumps(current_display_record,ensure_ascii=False,allow_nan=False)])
        if len(current_check_records)>5:current_lines_value.append('나머지 '+str(len(current_check_records)-5)+'건은 번역 도구에서 확인하세요.')
    current_lines_value.extend(['','검사 결과는 번역 품질 승인이 아닙니다.'])
    return '\n'.join(current_lines_value)


def read_conversation_service_status(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_expected_job_identifier=None):
    """접수·실행·결과 상태를 구분하고 조회 실패는 실행 가능으로 간주하지 않는다."""
    if not isinstance(current_card_record,dict) or (current_card_record.get('session_id'),current_card_record.get('source_job_id'),current_card_record.get('kind')) != (current_session_identifier,current_source_job_identifier,current_service_kind):
        raise gr.Error('세션, 작업 또는 제안 종류가 바뀌었습니다. 다시 확인하세요.')
    if current_service_kind == 'kimodo_resume':
        current_review_record=current_card_record['review']
        current_receipt_record=execute_remote_management_command('hermes-agent','hermes-kimodo-resume-receipt',{'request_id':current_review_record['request_id']})
        if not isinstance(current_receipt_record,dict) or current_receipt_record.get('request_id')!=current_review_record['request_id'] or current_receipt_record.get('state') not in ('not_found','accepted','unknown'):
            raise gr.Error('재개 접수 기록을 확인할 수 없습니다.')
        if current_receipt_record['state']!='not_found' and any(current_receipt_record.get(current_key_name)!=current_value for current_key_name,current_value in (('service','kimodo'),('job_id',current_review_record['job_id']),('expected_resume_fingerprint',current_review_record['expected_resume_fingerprint']))):
            raise gr.Error('재개 접수 대상이 일치하지 않습니다.')
        current_receipt_state=current_receipt_record['state']
        if current_receipt_state=='accepted':
            current_status_text='재개 접수 기록이 있습니다. 원본 작업 상태: 확인 불가'
            try:
                current_history_record=execute_remote_management_command('hermes-agent','hermes-generator-source-history',{'service':'kimodo','query':current_review_record['job_id'],'limit':5})
                if not isinstance(current_history_record,dict) or current_history_record.get('service')!='kimodo' or not isinstance(current_history_record.get('records'),list):raise ValueError('Kimodo 원본 이력 오류')
                current_matching_records=[current_record for current_record in current_history_record['records'] if isinstance(current_record,dict) and current_record.get('id')==current_review_record['job_id']]
                if len(current_matching_records)!=1:raise ValueError('Kimodo 원본 작업 확인 불가')
                current_status_label={'queued':'대기 기록','running':'실행 기록','completed':'완료 기록','failed':'실패 기록','cancelled':'취소 기록','canceled':'취소 기록','paused':'일시정지 기록','unknown':'확인 불가'}.get(current_matching_records[0].get('recorded_status'),'확인 불가')
                current_source_label={'job':'작업 상태 파일','index':'이전 색인','unavailable':'확인 불가'}.get(current_matching_records[0].get('status_source'),'확인 불가')
                current_status_text='재개 접수 기록이 있습니다. 원본 작업 상태: '+current_status_label+' · 출처: '+current_source_label
            except (OSError,ValueError,TypeError,KeyError,RuntimeError):
                pass
            current_source_link=build_conversation_result_link('kimodo',current_review_record['job_id'],current_session_identifier)
            if current_source_link:current_status_text+='  \n[Kimodo 작업 이력과 결과 열기]('+current_source_link+')'
            return current_receipt_state,current_status_text+'  \n기록 상태는 실제 프로세스 생존과 결과 품질을 보증하지 않습니다.'
        return current_receipt_state,{'not_found':'재개 접수 기록이 없습니다. 원 서비스 상태를 확인하세요.','unknown':'재개 접수 결과 확인 필요 · 원 서비스와 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'}[current_receipt_state]
    if current_service_kind in ('flux_resume','video_resume'):
        current_review_record=current_card_record['review']
        current_target_service=current_card_record['service']
        current_receipt_record=execute_remote_management_command('hermes-agent','hermes-'+('flux' if current_service_kind=='flux_resume' else 'video')+'-resume-receipt',{'request_id':current_review_record['request_id']})
        if not isinstance(current_receipt_record,dict) or current_receipt_record.get('request_id')!=current_review_record['request_id'] or current_receipt_record.get('state') not in ('not_found','accepted','unknown'):
            raise gr.Error('재개 접수 기록을 확인할 수 없습니다.')
        if current_receipt_record['state']!='not_found' and any(current_receipt_record.get(current_key_name)!=current_value for current_key_name,current_value in (('service',current_target_service),('job_id',current_review_record['job_id']),('expected_resume_fingerprint',current_review_record['expected_resume_fingerprint']))):
            raise gr.Error('재개 접수 대상이 일치하지 않습니다.')
        current_receipt_state=current_receipt_record['state']
        if current_receipt_state=='accepted':
            current_status_text='재개 접수 기록이 있습니다. 원본 작업 상태: 확인 불가'
            try:
                current_history_record=execute_remote_management_command('hermes-agent','hermes-generator-source-history',{'service':current_target_service,'query':current_review_record['job_id'],'limit':5})
                if not isinstance(current_history_record,dict) or current_history_record.get('service')!=current_target_service or not isinstance(current_history_record.get('records'),list):raise ValueError('Kimodo 원본 이력 오류')
                current_matching_records=[current_record for current_record in current_history_record['records'] if isinstance(current_record,dict) and current_record.get('id')==current_review_record['job_id']]
                if len(current_matching_records)!=1:raise ValueError('Kimodo 원본 작업 확인 불가')
                current_status_label={'queued':'대기 기록','running':'실행 기록','completed':'완료 기록','failed':'실패 기록','cancelled':'취소 기록','canceled':'취소 기록','paused':'일시정지 기록','unknown':'확인 불가'}.get(current_matching_records[0].get('recorded_status'),'확인 불가')
                current_source_label={'job':'작업 상태 파일','index':'이전 색인','unavailable':'확인 불가'}.get(current_matching_records[0].get('status_source'),'확인 불가')
                current_status_text='재개 접수 기록이 있습니다. 원본 작업 상태: '+current_status_label+' · 출처: '+current_source_label
            except (OSError,ValueError,TypeError,KeyError,RuntimeError):
                pass
            current_source_link=build_conversation_result_link(current_target_service,current_review_record['job_id'],current_session_identifier)
            if current_source_link:current_status_text+='  \n[작업 이력과 결과 열기]('+current_source_link+')'
            return current_receipt_state,current_status_text+'  \n기록 상태는 실제 프로세스 생존과 결과 품질을 보증하지 않습니다.'
        return current_receipt_state,{'not_found':'재개 접수 기록이 없습니다. 원 서비스 상태를 확인하세요.','unknown':'재개 접수 결과 확인 필요 · 원 서비스와 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'}[current_receipt_state]
    if current_service_kind == 'model_preparation':
        current_request_identifier=current_card_record['review']['request_id']
        current_service_name=current_card_record['service']
        current_receipt_value=execute_remote_management_command('hermes-agent','hermes-model-prepare-status',{'service':current_service_name,'request_id':current_request_identifier})
        if not isinstance(current_receipt_value,dict) or current_receipt_value.get('request_id')!=current_request_identifier or current_receipt_value.get('service')!=current_service_name or current_receipt_value.get('state') not in ('not_found','accepted','unknown'):
            raise gr.Error('모델 준비 접수 ID 또는 서비스를 확인할 수 없습니다.')
        current_receipt_state=current_receipt_value['state']
        current_receipt_text=format_hermes_model_preparation_receipt(current_receipt_value,current_service_name,current_request_identifier)
        current_readiness_text=read_hermes_model_readiness_summary(current_service_name)
        return current_receipt_state,current_receipt_text+'  \n현재 모델 상태: '+current_readiness_text
    if current_service_kind == 'kimodo':
        return 'checked',read_conversation_kimodo_result(current_card_record,current_session_identifier,current_source_job_identifier)
    current_request_identifier=current_card_record['review']['request_id']
    current_status_commands={'flux':'hermes-flux-delegation-status','translation':'hermes-translation-status','audio':'hermes-audio-status','video':'hermes-video-status','writer':'hermes-writer-status'}
    current_payload_record={'request_id':current_request_identifier}
    if current_service_kind in ('audio','video'):current_payload_record['service']=current_card_record['service']
    if current_service_kind=='flux' and current_card_record['service']!='flux-image':
        current_status_commands['flux']='hermes-flux-profile-status'
        current_payload_record['service']=current_card_record['service']
    current_status_record=execute_remote_management_command('hermes-agent',current_status_commands[current_service_kind],current_payload_record)
    current_receipt_record=current_status_record.get('receipt') or {}
    current_receipt_state=current_receipt_record.get('state')
    if current_expected_job_identifier is not None and (current_receipt_state!='accepted' or current_receipt_record.get('request_id')!=current_request_identifier or current_receipt_record.get('job_id')!=current_expected_job_identifier):
        raise gr.Error('접수 응답과 작업 이력이 일치하지 않습니다. 원 서비스와 같은 접수 ID를 확인하세요.')
    current_expected_service={'translation':'prompt-translation','writer':'writer-agent'}.get(current_service_kind,current_card_record.get('service'))
    if current_card_record.get('service')!=current_expected_service:
        raise gr.Error('제안 서비스가 일치하지 않습니다. 원 서비스와 접수 이력을 확인하세요.')
    current_returned_identifier=current_receipt_record.get('request_id')
    current_returned_service=current_receipt_record.get('service')
    if current_returned_identifier is not None and current_returned_identifier!=current_request_identifier or current_returned_service is not None and current_returned_service!=current_expected_service:
        raise gr.Error('접수 ID 또는 서비스가 일치하지 않습니다. 원 서비스와 접수 이력을 확인하세요.')
    if current_receipt_state in ('not_found','accepted') and (current_returned_identifier!=current_request_identifier or current_returned_service!=current_expected_service):
        raise gr.Error('접수 ID와 서비스를 확인할 수 없습니다. 게이트웨이를 갱신하고 원 서비스 이력을 확인하세요.')
    if current_receipt_state == 'not_found':return current_receipt_state,'아직 접수하지 않았습니다. 내용을 검토한 뒤 대기열에 추가하세요.'
    if current_receipt_state == 'unknown':return current_receipt_state,'접수 결과 확인 불가 · 원래 도구의 이력을 확인하세요. 자동으로 다시 접수하지 않습니다.'
    if current_receipt_state != 'accepted' or not isinstance(current_receipt_record.get('job_id'),str):raise gr.Error('접수 상태를 확인할 수 없습니다.')
    if current_service_kind in ('flux','audio','video','translation','writer'):
        from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
        current_expected_service={'translation':'prompt-translation','writer':'writer-agent'}.get(current_service_kind,current_card_record.get('service'))
        if current_card_record.get('service')!=current_expected_service or current_receipt_record.get('service')!=current_expected_service or not validate_service_job_identifier(current_expected_service,current_receipt_record['job_id']):
            raise gr.Error('접수 서비스 또는 작업 ID를 확인할 수 없습니다. 원 서비스의 이력을 확인하세요.')
    current_job_record=current_status_record.get('job') or {}
    current_job_identifier=current_receipt_record['job_id']
    if current_service_kind == 'writer':
        current_stage_value = current_job_record.get('stage', 'unknown')
        current_status_text = '작가 작업 ' + current_job_identifier + ' · 기록 상태: ' + str(current_stage_value)
        current_status_text += '  \n기존 접수 입력과 현재 제안의 일치 여부는 별도로 확인하세요.'
        if current_job_record.get('failure_reason'):
            current_status_text += '  \n오류: ' + str(current_job_record['failure_reason'])
        if current_stage_value == 'review':
            current_status_text += '  \n제안은 아직 적용되지 않았습니다. 작가 AI 화면에서 전체 변경과 근거를 검토하세요.'
        current_status_text += '  \n[작가 AI 이력과 결과 열기]('+build_conversation_result_link('writer-agent',current_job_identifier,current_session_identifier)+')'
        return current_receipt_state,current_status_text
    current_status_label={'queued':'대기 중','running':'실행 중','completed':'완료','failed':'실패','cancelled':'취소됨','canceled':'취소됨','paused':'일시정지','unknown':'확인 불가'}.get(current_job_record.get('status'),'확인 불가')
    current_status_text='작업 '+current_job_identifier+' · '+current_status_label+'  \n기존 접수 입력과 현재 제안의 일치 여부는 별도로 확인하세요.'
    if current_job_record.get('failure_reason'):current_status_text+='  \n오류: '+str(current_job_record['failure_reason'])
    if current_service_kind == 'flux':
        current_result_record=current_status_record.get('result') or {}
        current_expected_path='/'+current_card_record['service']+'-generator/jobs/'+current_job_identifier+'/result.png'
        current_image_path=current_result_record.get('image') if current_card_record['service']=='flux-image' else current_job_record.get('image')
        current_source_observation=read_conversation_flux_source_observation(current_card_record['service'],current_job_identifier) if current_job_record.get('status')=='completed' else None
        if current_source_observation is not None:
            if current_source_observation['status']=='completed' and current_source_observation['result_status']=='available':
                current_status_text+='  \n[생성 이미지 보기]('+current_source_observation['image']+') · 파일 존재는 조회 시점 기준'
            elif current_source_observation['status']=='completed':current_status_text+='  \n완료 기록은 있으나 이미지 파일을 확인할 수 없습니다.'
            else:current_status_text+='  \n원본 작업 상태가 변경되어 이미지 결과를 다시 확인해야 합니다.'
        elif current_job_record.get('status') == 'completed' and current_image_path == current_expected_path:current_status_text+='  \n[생성 이미지 보기]('+current_expected_path+')'
        elif current_job_record.get('status') == 'completed':current_status_text+='  \n완료 기록은 있으나 이미지 경로를 확인할 수 없습니다.'
        if current_job_record.get('status')=='completed' and current_source_observation is None:
            current_status_text+='  \n원본 이미지 상태 조회 불가 · 원 도구에서 다시 확인하세요.'
        current_status_text+='  \n[이미지 생성기 열기]('+build_conversation_result_link(current_card_record['service'],current_job_identifier,current_session_identifier)+')'
        current_status_text+='  \n상태 조회 시 기존 중단 작업 복구가 따를 수 있습니다.'
    elif current_service_kind == 'translation':
        if current_job_record.get('status') == 'completed' and current_job_record.get('result') is not None:
            current_status_text+='  \n\n'+format_conversation_translation_result(current_job_record['result'])
        current_status_text+='  \n[번역 도구 열기]('+build_conversation_result_link('prompt-translation',current_job_identifier,current_session_identifier)+')'
    elif current_service_kind == 'video':
        from tools.review.domains.hermes_agent.media_result_paths import validate_hermes_video_result_paths
        current_media_paths=validate_hermes_video_result_paths(current_card_record['service'],current_job_identifier,current_job_record)
        current_video_observation=read_conversation_video_source_observation(current_card_record['service'],current_job_identifier) if current_job_record.get('status')=='completed' else None
        if current_video_observation is not None:
            current_media_paths={current_field_name:current_video_observation[current_field_name] for current_field_name in ('video','image','download')}
            if current_video_observation['status']!='completed':current_status_text+='  \n원본 작업 상태가 변경되어 영상 결과를 다시 확인해야 합니다.'
            elif current_video_observation['result_status']=='available':current_status_text+='  \n결과 파일 존재는 조회 시점 기준입니다.'
        if current_job_record.get('status')=='completed' and current_video_observation is None:
            current_status_text+='  \n원본 영상 상태 조회 불가 · 원 도구에서 다시 확인하세요.'
        for current_field_name,current_label_text in (('video','생성 영상'),('image','첫 프레임'),('download','프레임 ZIP')):
            current_result_path=current_media_paths[current_field_name]
            if current_result_path:current_status_text+='  \n['+current_label_text+']('+current_result_path+')'
        if current_job_record.get('status')=='completed' and not any(current_media_paths.values()):current_status_text+='  \n완료 기록은 있으나 결과 파일 경로를 확인할 수 없습니다.'
        elif current_job_record.get('status')=='completed' and not all(current_media_paths.values()):current_status_text+='  \n결과 경로 일부만 확인됐습니다. 원 서비스에서 나머지 결과를 확인하세요.'
        current_video_link=build_conversation_result_link(current_card_record['service'],current_job_identifier,current_session_identifier)
        if current_video_link is None:raise gr.Error('영상 원 서비스를 확인할 수 없습니다.')
        current_status_text+='  \n[영상 도구 열기]('+current_video_link+') · 상태 조회 시 중단 작업 복구가 따를 수 있습니다.'
    else:
        from tools.review.domains.hermes_agent.media_result_paths import validate_hermes_audio_result_path
        current_audio_path=validate_hermes_audio_result_path(current_card_record['service'],current_job_identifier,current_job_record)
        current_audio_file_observation=current_job_record.get('file_observation','unknown')
        if current_audio_file_observation not in ('present','unavailable','unknown','not_ready') or (current_audio_file_observation in ('present','unavailable') and not current_audio_path) or (current_audio_file_observation=='not_ready' and current_audio_path):raise gr.Error('음원 파일 관측을 확인할 수 없습니다.')
        if current_audio_file_observation=='unavailable':
            current_audio_path=None
            current_status_text+='  \n음원 파일을 확인할 수 없어 링크를 표시하지 않습니다.'
        elif current_audio_file_observation=='present':current_status_text+='  \n음원 파일 존재는 조회 시점 기준입니다.'
        if current_audio_path:current_status_text+='  \n[생성 음원 듣기]('+current_audio_path+')'
        elif current_job_record.get('status')=='completed' and current_audio_file_observation!='unavailable':current_status_text+='  \n완료 기록은 있으나 음원 경로를 확인할 수 없습니다.'
        current_audio_link=build_conversation_result_link(current_card_record['service'],current_job_identifier,current_session_identifier)
        if current_audio_link is None:raise gr.Error('오디오 원 서비스를 확인할 수 없습니다.')
        current_status_text+='  \n[음악·효과음 도구 열기]('+current_audio_link+')'
    if current_job_record.get('status')=='completed':
        current_status_text+='  \n완료는 결과 품질 승인을 뜻하지 않습니다.'
        if current_service_kind=='flux' and current_source_observation is not None:
            current_status_text+=' 이미지 내용과 품질은 별도로 확인하세요.'
        elif current_service_kind=='video' and current_video_observation is not None:
            current_status_text+=' 영상 내용과 재생은 별도로 확인하세요.'
        elif current_service_kind=='audio' and current_audio_file_observation=='present':
            current_status_text+=' 음원 내용과 재생은 별도로 확인하세요.'
        elif current_service_kind in ('flux','audio','video'):
            current_status_text+=' 결과 링크는 경로 형식만 확인했으며 파일 존재와 재생 여부는 원 도구에서 확인하세요.'
    return current_receipt_state,current_status_text


def refresh_conversation_service_status(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_expected_job_identifier=None):
    try:
        return read_conversation_service_status(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_expected_job_identifier)[1]
    except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError,AttributeError):
        return '접수 또는 작업 상태 확인 불가 · 원 서비스와 같은 접수 ID의 이력을 확인하세요. 자동 재접수하지 않습니다.'




def create_conversation_status_token():
    import uuid
    return uuid.uuid4().hex


def collect_conversation_status_result(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_request_token):
    """선택과 조회 식별자를 함께 보관해 이전 응답을 구분한다."""
    from copy import deepcopy
    current_identity_value=deepcopy([current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind])
    current_status_text=refresh_conversation_service_status(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind)
    return {'identity':current_identity_value,'token':current_request_token,'notice':current_status_text}


def render_conversation_status_result(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_request_token,current_result_record):
    if not isinstance(current_result_record,dict) or current_result_record.get('token')!=current_request_token or current_result_record.get('identity')!=[current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind]:return gr.skip()
    return current_result_record['notice']


def update_conversation_kimodo_frame_button(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind):
    current_ready_value=(current_service_kind=='kimodo' and isinstance(current_card_record,dict) and (current_card_record.get('session_id'),current_card_record.get('source_job_id'),current_card_record.get('kind'))==(current_session_identifier,current_source_job_identifier,'kimodo') and current_card_record.get('service') in (None,'kimodo') and isinstance(current_card_record.get('review'),dict) and isinstance(current_card_record['review'].get('request_id'),str))
    return gr.update(interactive=current_ready_value)


def collect_conversation_kimodo_frame(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_request_token):
    """대화 접수의 Kimodo 현재 시도를 확인하고 지정 프레임을 읽는다."""
    from copy import deepcopy
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    from tools.review.domains.hermes_agent.video_operations import validate_hermes_video_source_response
    from tools.review.domains.hermes_agent.kimodo_frame_observer import validate_kimodo_source_frame_response
    current_identity_value=deepcopy([current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number])
    current_frame_record=None
    try:
        if update_conversation_kimodo_frame_button(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind).get('interactive') is not True or type(current_frame_number) is not int or not 1<=current_frame_number<=1000:raise ValueError('대화 또는 프레임 선택 오류')
        current_request_identifier=current_card_record['review']['request_id']
        current_receipt_record=execute_remote_management_command('hermes-agent','hermes-delegation-status',{'request_id':current_request_identifier})
        if not isinstance(current_receipt_record,dict) or current_receipt_record.get('state')!='accepted' or current_receipt_record.get('service')!='kimodo' or current_receipt_record.get('request_id')!=current_request_identifier or not validate_service_job_identifier('kimodo',current_receipt_record.get('job_id')):raise ValueError('Kimodo 접수 신원 오류')
        current_job_identifier=current_receipt_record['job_id']
        current_source_response=execute_remote_management_command('hermes-agent','hermes-video-source-status',{'service':'kimodo','job_id':current_job_identifier})
        current_source_record=validate_hermes_video_source_response('kimodo',current_job_identifier,current_source_response)
        if current_source_record['status']!='completed' or current_source_record['result_status']!='available':raise ValueError('Kimodo 결과 확인 불가')
        current_video_match=re.fullmatch('/kimodo/jobs/'+re.escape(current_job_identifier)+r'/attempts/([a-f0-9]{32})/preview\.mp4',current_source_record['video'])
        if not current_video_match:raise ValueError('Kimodo 시도 오류')
        current_attempt_identifier=current_video_match[1]
        current_frame_response=execute_remote_management_command('hermes-agent','hermes-kimodo-source-frame',{'job_id':current_job_identifier,'attempt_id':current_attempt_identifier,'frame':current_frame_number})
        current_frame_record=validate_kimodo_source_frame_response(current_job_identifier,current_attempt_identifier,current_frame_number,current_frame_response)
        current_notice_text='프레임 '+str(current_frame_number)+' / '+str(current_frame_record['frame_count'])+' · SHA-256 `'+current_frame_record['image_sha256']+'`  \n[원본 프레임 열기]('+current_frame_record['image']+')  \nPNG 시그니처와 해시만 확인했습니다. 이미지 내용·모션·골격과 저장 가능성은 별도입니다.'
    except (gr.Error,OSError,ValueError,KeyError,TypeError,RuntimeError,AttributeError):
        current_notice_text='프레임을 확인할 수 없습니다. 같은 접수 ID의 완료된 Kimodo 작업과 프레임 번호를 확인하세요.'
    return {'identity':current_identity_value,'token':current_request_token,'notice':current_notice_text,'frame_record':current_frame_record}


def render_conversation_kimodo_frame(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_request_token,current_result_record):
    if not isinstance(current_result_record,dict) or current_result_record.get('token')!=current_request_token or current_result_record.get('identity')!=[current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number]:return gr.skip()
    return current_result_record['notice']


def review_conversation_kimodo_keyframe(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_frame_result):
    """현재 대화에서 확인한 프레임과 태그로 저장 내용을 검토한다."""
    import hashlib
    import json
    current_identity_value=[current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number]
    if not isinstance(current_frame_result,dict) or current_frame_result.get('identity')!=current_identity_value or current_frame_result.get('token')!=current_frame_token or not isinstance(current_frame_result.get('frame_record'),dict):raise gr.Error('현재 대화의 원본 프레임을 먼저 확인하세요.')
    current_frame_record=current_frame_result['frame_record']
    current_request_record={'job_id':current_frame_record['job_id'],'attempt_id':current_frame_record['attempt_id'],'frame':current_frame_number,'tag':current_tag_text}
    current_review_record=execute_remote_management_command('hermes-agent','hermes-kimodo-keyframe-source-review',current_request_record)
    if not isinstance(current_review_record,dict) or any(current_review_record.get(current_key_name)!=current_expected_value for current_key_name,current_expected_value in {'job_id':current_request_record['job_id'],'attempt_id':current_request_record['attempt_id'],'frame':current_frame_number,'tag':current_tag_text.strip(),'image':current_frame_record['image'],'image_sha256':current_frame_record['image_sha256']}.items()) or not isinstance(current_review_record.get('review_sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_review_record['review_sha256']):raise gr.Error('키프레임 검토 결과가 현재 원본과 다릅니다.')
    if current_review_record.get('chat_save_readiness') not in ('ready','check_required'):raise gr.Error('기존 키프레임 접수 확인 상태 오류')
    current_request_record['tag']=current_tag_text.strip()
    current_request_record['review_sha256']=current_review_record['review_sha256']
    current_request_identity={current_key_name:current_request_record[current_key_name] for current_key_name in ('job_id','attempt_id','frame','tag')}
    current_request_bytes=json.dumps([current_session_identifier,current_source_job_identifier,current_request_identity],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    current_request_identifier='keyframe_'+hashlib.sha256(current_request_bytes).hexdigest()
    current_legacy_bytes=json.dumps([current_session_identifier,current_source_job_identifier,current_request_record],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    current_legacy_identifier='keyframe_'+hashlib.sha256(current_legacy_bytes).hexdigest()
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-kimodo-keyframe-receipt',{'request_id':current_request_identifier})
    if not isinstance(current_receipt_record,dict) or current_receipt_record.get('request_id')!=current_request_identifier or current_receipt_record.get('state') not in ('not_found','completed','unknown'):raise gr.Error('키프레임 저장 접수 상태를 확인할 수 없습니다.')
    if current_receipt_record['state']=='not_found':
        current_legacy_receipt=execute_remote_management_command('hermes-agent','hermes-kimodo-keyframe-receipt',{'request_id':current_legacy_identifier})
        if not isinstance(current_legacy_receipt,dict) or current_legacy_receipt.get('request_id')!=current_legacy_identifier or current_legacy_receipt.get('state') not in ('not_found','completed','unknown'):raise gr.Error('기존 키프레임 저장 접수 상태를 확인할 수 없습니다.')
        if current_legacy_receipt['state']!='not_found':current_request_identifier,current_receipt_record=current_legacy_identifier,current_legacy_receipt
    current_review_state={'identity':current_identity_value,'frame_token':current_frame_token,'request':current_request_record,'request_id':current_request_identifier,'receipt':current_receipt_record,'chat_save_readiness':current_review_record['chat_save_readiness']}
    current_notice_text='작업 `'+current_request_record['job_id']+'` · 시도 `'+current_request_record['attempt_id']+'` · 프레임 '+str(current_frame_number)+' · 태그 '+current_request_record['tag']+'  \n[확인한 원본 프레임]('+current_frame_record['image']+') · SHA-256 `'+current_frame_record['image_sha256']+'`  \n원본 모션과 골격을 재검증해 독립 키프레임을 저장합니다. 생성이나 GPU 작업은 하지 않습니다. 접수 상태: '+current_receipt_record['state']
    if current_review_record['chat_save_readiness']=='check_required':
        current_notice_text+='  \n기존 키프레임 접수를 확인할 수 없어 새 대화 저장을 보류합니다. [Kimodo 도구](/management/frame/kimodo-generator/)와 기존 접수를 확인하세요.'
        current_blocker_value=current_review_record.get('legacy_receipts')
        if current_blocker_value is not None:
            if not isinstance(current_blocker_value,dict) or set(current_blocker_value)!={'records','truncated'} or not isinstance(current_blocker_value['records'],list) or len(current_blocker_value['records'])>20 or type(current_blocker_value['truncated']) is not bool:raise gr.Error('기존 키프레임 접수 목록 형식 오류')
            for current_blocker_record in current_blocker_value['records']:
                if not isinstance(current_blocker_record,dict) or set(current_blocker_record)!={'request_id','state'} or not isinstance(current_blocker_record['request_id'],str) or not re.fullmatch(r'keyframe_[a-f0-9]{64}',current_blocker_record['request_id']) or current_blocker_record['state'] not in ('unknown','completed','unavailable'):raise gr.Error('기존 키프레임 접수 항목 오류')
                current_notice_text+='  \n접수 ID `'+current_blocker_record['request_id']+'` · 상태 '+{'unknown':'확인 필요','completed':'완료 기록','unavailable':'읽기 불가'}[current_blocker_record['state']]
            if current_blocker_value['truncated']:current_notice_text+='  \n확인 대상이 20개를 넘어 일부만 표시했습니다.'
    if current_receipt_record['state']=='unknown':current_notice_text+=' · 원 서비스 목록에서 확인하고 자동 재저장하지 마세요.'
    if current_receipt_record['state']=='completed':current_notice_text+=' · 키프레임 ID `'+str(current_receipt_record.get('keyframe_id'))+'`'
    return current_review_state,current_notice_text,False,gr.update(interactive=current_receipt_record['state']=='not_found' and current_review_record['chat_save_readiness']=='ready')


def begin_conversation_kimodo_keyframe_review():
    """새 검토가 시작되면 이전 승인과 저장 버튼을 즉시 해제한다."""
    return create_conversation_status_token(),None,False,gr.update(interactive=False),'키프레임 원본과 기존 접수를 확인하고 있습니다.'


def collect_conversation_kimodo_keyframe_review(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_request_token,current_frame_result):
    from copy import deepcopy
    current_identity_value=deepcopy([current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_request_token])
    try:
        current_review_outputs=review_conversation_kimodo_keyframe(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_frame_result)
        return {'identity':current_identity_value,'outputs':current_review_outputs}
    except (gr.Error,OSError,ValueError,KeyError,TypeError,RuntimeError,AttributeError):
        return {'identity':current_identity_value,'outputs':(None,'원본 저장 검토를 확인할 수 없습니다. 프레임과 태그를 다시 확인하세요.',False,gr.update(interactive=False))}


def render_conversation_kimodo_keyframe_review(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_request_token,current_review_result):
    if not isinstance(current_review_result,dict) or current_review_result.get('identity')!=[current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_request_token]:return (gr.skip(),gr.skip(),gr.skip(),gr.skip())
    return current_review_result['outputs']


def submit_conversation_kimodo_keyframe(current_review_state,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_confirm_value):
    """검토한 선택과 명시적 확인이 유지된 경우에만 저장한다."""
    current_identity_value=[current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number]
    if current_confirm_value is not True or not isinstance(current_review_state,dict) or current_review_state.get('identity')!=current_identity_value or current_review_state.get('frame_token')!=current_frame_token or not isinstance(current_tag_text,str) or current_review_state.get('request',{}).get('tag')!=current_tag_text.strip() or current_review_state.get('receipt',{}).get('state')!='not_found' or current_review_state.get('chat_save_readiness')!='ready':raise gr.Error('현재 원본과 기존 접수를 다시 검토하고 저장을 확인하세요.')
    try:
        current_result_record=execute_remote_management_command('hermes-agent','hermes-kimodo-keyframe-save',{'request_id':current_review_state['request_id'],**current_review_state['request']})
        if not isinstance(current_result_record,dict) or current_result_record.get('request_id')!=current_review_state['request_id'] or current_result_record.get('state') not in ('completed','unknown'):raise ValueError('접수 결과 오류')
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,AttributeError,gr.Error):
        return '저장 응답을 확인할 수 없습니다. 아래 접수와 원 서비스 및 기존 접수 기록을 확인하고 자동 재저장하지 마세요. 접수 ID `'+current_review_state['request_id']+'`',gr.update(interactive=False)
    return format_conversation_kimodo_keyframe_receipt(current_review_state,current_result_record),gr.update(interactive=False)


def collect_conversation_kimodo_keyframe_submit(current_review_state,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_confirm_value):
    """저장 결과에 제출 시 선택과 접수 신원을 함께 보관한다."""
    from copy import deepcopy
    current_identity_value=deepcopy([current_review_state,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token])
    current_submit_outputs=submit_conversation_kimodo_keyframe(current_review_state,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_confirm_value)
    return {'identity':current_identity_value,'outputs':current_submit_outputs}


def render_conversation_kimodo_keyframe_submit(current_review_state,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_submit_result):
    """지연된 저장 응답은 다른 대화·선택을 덮어쓰지 않는다."""
    if not isinstance(current_submit_result,dict) or current_submit_result.get('identity')!=[current_review_state,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token]:return (gr.skip(),gr.skip())
    return current_submit_result['outputs']


def format_conversation_kimodo_keyframe_receipt(current_review_state,current_receipt_record):
    if not isinstance(current_receipt_record,dict) or current_receipt_record.get('request_id')!=current_review_state['request_id'] or current_receipt_record.get('state') not in ('not_found','completed','unknown'):return '접수 상태를 확인할 수 없습니다. 자동 재저장하지 마세요.'
    if current_receipt_record['state']=='completed':
        current_saved_identifier=current_receipt_record.get('keyframe_id')
        if not isinstance(current_saved_identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',current_saved_identifier):return '저장 결과 ID를 확인할 수 없습니다. 원 서비스를 확인하세요.'
        return '키프레임 저장 완료 · ID `'+current_saved_identifier+'` · 원 서비스에서 목록과 결과를 확인하세요.'
    if current_receipt_record['state']=='unknown':return '저장 결과 불확실 · 접수 ID `'+current_review_state['request_id']+'` · [Kimodo 키프레임 목록 열기](/management/frame/kimodo-generator/)에서 확인하고 자동 재저장하지 마세요.'
    return '저장 접수가 없습니다. 원 서비스의 목록과 접수 ID를 확인하세요.'


def refresh_conversation_kimodo_keyframe_receipt(current_review_state):
    if not isinstance(current_review_state,dict) or not isinstance(current_review_state.get('request_id'),str):return '먼저 저장할 원본을 검토하세요.'
    try:
        current_receipt_record=execute_remote_management_command('hermes-agent','hermes-kimodo-keyframe-receipt',{'request_id':current_review_state['request_id']})
        return format_conversation_kimodo_keyframe_receipt(current_review_state,current_receipt_record)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,AttributeError,gr.Error):
        return '접수 상태를 확인할 수 없습니다. 자동 재저장하지 마세요.'


def collect_conversation_kimodo_keyframe_receipt(current_review_state,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_request_token):
    from copy import deepcopy
    current_identity_value=deepcopy([current_review_state,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_request_token])
    return {'identity':current_identity_value,'notice':refresh_conversation_kimodo_keyframe_receipt(current_review_state)}


def render_conversation_kimodo_keyframe_receipt(current_review_state,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_request_token,current_receipt_result):
    if not isinstance(current_receipt_result,dict) or current_receipt_result.get('identity')!=[current_review_state,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_request_token]:return gr.skip()
    return current_receipt_result['notice']


def collect_conversation_saved_keyframe_preview(current_review_state,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_request_token):
    """현재 대화의 완료 접수와 저장된 키프레임 원본을 다시 확인한다."""
    from copy import deepcopy
    current_identity_value=deepcopy([current_review_state,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_request_token])
    try:
        current_expected_identity=[current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number]
        if not isinstance(current_review_state,dict) or current_review_state.get('identity')!=current_expected_identity or current_review_state.get('frame_token')!=current_frame_token or not isinstance(current_tag_text,str) or current_review_state.get('request',{}).get('tag')!=current_tag_text.strip():raise ValueError('대화 선택 오류')
        current_receipt_record=execute_remote_management_command('hermes-agent','hermes-kimodo-keyframe-receipt',{'request_id':current_review_state['request_id']})
        current_keyframe_identifier=current_receipt_record.get('keyframe_id') if isinstance(current_receipt_record,dict) else None
        if not isinstance(current_receipt_record,dict) or current_receipt_record.get('request_id')!=current_review_state['request_id'] or current_receipt_record.get('state')!='completed' or not isinstance(current_keyframe_identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',current_keyframe_identifier):raise ValueError('완료된 저장 접수 없음')
        current_image_value,current_image_notice=read_hermes_kimodo_keyframe_preview_image(current_keyframe_identifier)
        current_notice_text='저장된 키프레임 ID `'+current_keyframe_identifier+'` · '+current_image_notice
    except (gr.Error,OSError,ValueError,KeyError,TypeError,RuntimeError,AttributeError):
        current_image_value=None
        current_notice_text='저장된 키프레임을 확인할 수 없습니다. 같은 접수와 원 서비스의 목록을 확인하세요.'
    return {'identity':current_identity_value,'image':current_image_value,'notice':current_notice_text}


def render_conversation_saved_keyframe_preview(current_review_state,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_request_token,current_preview_result):
    if not isinstance(current_preview_result,dict) or current_preview_result.get('identity')!=[current_review_state,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_frame_number,current_tag_text,current_frame_token,current_request_token]:return (gr.skip(),gr.skip())
    return current_preview_result['image'],current_preview_result['notice']


def select_conversation_saved_keyframe(current_review_state,current_session_identifier):
    """저장 완료 접수를 확인하여 같은 세션에서 다음 제안에 사용할 사본을 선택한다."""
    if not isinstance(current_review_state,dict) or not isinstance(current_review_state.get('identity'),list) or len(current_review_state['identity'])!=5 or current_review_state['identity'][1]!=current_session_identifier:raise gr.Error('현재 세션의 저장 검토를 선택하세요.')
    current_request_identifier=current_review_state.get('request_id')
    if not isinstance(current_request_identifier,str) or not re.fullmatch(r'keyframe_[a-f0-9]{64}',current_request_identifier):raise gr.Error('키프레임 접수 ID 오류')
    current_receipt_value=execute_remote_management_command('hermes-agent','hermes-kimodo-keyframe-receipt',{'request_id':current_request_identifier})
    current_keyframe_identifier=current_receipt_value.get('keyframe_id') if isinstance(current_receipt_value,dict) else None
    if not isinstance(current_receipt_value,dict) or (current_receipt_value.get('request_id'),current_receipt_value.get('state'))!=(current_request_identifier,'completed') or not isinstance(current_keyframe_identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',current_keyframe_identifier):raise gr.Error('완료된 키프레임 접수를 확인할 수 없습니다.')
    return {'session_id':current_session_identifier,'receipt_id':current_request_identifier,'keyframe_id':current_keyframe_identifier},'다음 Kimodo 제안에 사용할 키프레임 `'+current_keyframe_identifier+'`을 선택했습니다.'


def collect_conversation_saved_keyframe_selection(current_review_state,current_session_identifier,current_request_token):
    from copy import deepcopy
    current_identity_value=deepcopy([current_review_state,current_session_identifier,current_request_token])
    try:current_selection_outputs=select_conversation_saved_keyframe(current_review_state,current_session_identifier)
    except (gr.Error,OSError,ValueError,KeyError,TypeError,RuntimeError,AttributeError):current_selection_outputs=(None,'완료된 키프레임 접수를 확인할 수 없습니다.')
    return {'identity':current_identity_value,'outputs':current_selection_outputs}


def render_conversation_saved_keyframe_selection(current_review_state,current_session_identifier,current_request_token,current_selection_result):
    if not isinstance(current_selection_result,dict) or current_selection_result.get('identity')!=[current_review_state,current_session_identifier,current_request_token]:return (gr.skip(),gr.skip())
    return current_selection_result['outputs']


def review_conversation_kimodo_with_saved_keyframe(current_saved_selection,current_session_identifier,current_source_job_identifier,current_service_kind,current_output_frame):
    """선택한 사본을 출력 프레임에 배치한 제안을 별도 검토한다."""
    if current_service_kind!='kimodo' or not isinstance(current_saved_selection,dict) or set(current_saved_selection)!={'session_id','receipt_id','keyframe_id'} or current_saved_selection['session_id']!=current_session_identifier or type(current_output_frame) is not int:raise gr.Error('현재 세션의 키프레임과 Kimodo 제안을 선택하세요.')
    current_attachment_value={**current_saved_selection,'output_frame':current_output_frame}
    current_card_value,current_preview_text,current_status_text=prepare_conversation_kimodo_review(current_session_identifier,current_source_job_identifier,current_attachment_value)
    return {**current_card_value,'kind':'kimodo'},current_preview_text,current_status_text


def begin_conversation_keyframe_attachment_review():
    """새 첨부 검토를 시작하며 기존 제안 승인을 해제한다."""
    return create_conversation_status_token(),None,'','키프레임과 제안을 확인하고 있습니다.',gr.update(interactive=False)


def collect_conversation_keyframe_attachment_review(current_saved_selection,current_session_identifier,current_source_job_identifier,current_service_kind,current_output_frame,current_request_token):
    from copy import deepcopy
    current_identity_value=deepcopy([current_saved_selection,current_session_identifier,current_source_job_identifier,current_service_kind,current_output_frame,current_request_token])
    try:current_review_outputs=review_conversation_kimodo_with_saved_keyframe(current_saved_selection,current_session_identifier,current_source_job_identifier,current_service_kind,current_output_frame)
    except (gr.Error,OSError,ValueError,KeyError,TypeError,RuntimeError,AttributeError):current_review_outputs=(None,'','키프레임이나 제안을 확인할 수 없습니다. 선택과 원 서비스를 다시 확인하세요.')
    return {'identity':current_identity_value,'outputs':current_review_outputs}


def render_conversation_keyframe_attachment_review(current_saved_selection,current_session_identifier,current_source_job_identifier,current_service_kind,current_output_frame,current_request_token,current_review_result):
    if not isinstance(current_review_result,dict) or current_review_result.get('identity')!=[current_saved_selection,current_session_identifier,current_source_job_identifier,current_service_kind,current_output_frame,current_request_token]:return (gr.skip(),gr.skip(),gr.skip())
    return current_review_result['outputs']


def invalidate_conversation_keyframe_attachment(current_card_record):
    if not isinstance(current_card_record,dict) or 'keyframe_attachment' not in current_card_record:return gr.skip(),gr.skip()
    return None,gr.update(interactive=False)


def collect_attachment_status_result(current_source_record,current_session_identifier,current_source_job_identifier,current_attachment_kind,current_request_token):
    """첨부 제안 결과와 해당 선택·요청을 함께 보관한다."""
    from copy import deepcopy
    current_identity_value=deepcopy([current_source_record,current_session_identifier,current_source_job_identifier,current_attachment_kind])
    try:
        if current_attachment_kind=='image':current_status_text=read_conversation_flux_reference(current_source_record,current_session_identifier,current_source_job_identifier)
        elif current_attachment_kind=='video':current_status_text=read_conversation_video_receipt(current_source_record,current_session_identifier,current_source_job_identifier)
        else:raise ValueError('첨부 종류 오류')
    except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError,AttributeError):
        current_status_text='접수 또는 작업 상태 확인 불가 · 원 서비스와 같은 접수 ID의 이력을 확인하세요. 자동 재접수하지 않습니다.'
    return {'identity':current_identity_value,'token':current_request_token,'notice':current_status_text}


def render_attachment_status_result(current_source_record,current_session_identifier,current_source_job_identifier,current_attachment_kind,current_request_token,current_result_record):
    if not isinstance(current_result_record,dict) or current_result_record.get('token')!=current_request_token or current_result_record.get('identity')!=[current_source_record,current_session_identifier,current_source_job_identifier,current_attachment_kind]:return gr.skip()
    return current_result_record['notice']


def is_valid_writer_receipt(current_receipt_record,current_request_identifier):
    """작가 접수의 서비스와 기존 작업 ID 계약을 확인한다."""
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    return isinstance(current_receipt_record,dict) and current_receipt_record.get('state')=='accepted' and current_receipt_record.get('request_id')==current_request_identifier and current_receipt_record.get('service')=='writer-agent' and validate_service_job_identifier('writer-agent',current_receipt_record.get('job_id'))


def read_conversation_writer_details(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind):
    """선택한 작가 접수의 제한된 변경 결과를 읽으며 문서에 적용하지 않는다."""
    if not isinstance(current_card_record,dict) or (current_card_record.get('session_id'),current_card_record.get('source_job_id'),current_card_record.get('kind'),current_service_kind)!=(current_session_identifier,current_source_job_identifier,'writer','writer'):
        raise gr.Error('작가 제안이 선택된 세션과 일치하지 않습니다. 다시 확인하세요.')
    current_review_record=current_card_record.get('review')
    if not isinstance(current_review_record,dict) or not isinstance(current_review_record.get('request_id'),str):
        raise gr.Error('작가 접수 ID를 확인할 수 없습니다.')
    current_status_record=execute_remote_management_command('hermes-agent','hermes-writer-status',{'request_id':current_review_record['request_id']})
    if not isinstance(current_status_record,dict) or not isinstance(current_status_record.get('receipt'),dict):
        raise gr.Error('작가 접수 상태를 확인할 수 없습니다.')
    current_receipt_record=current_status_record['receipt']
    if current_receipt_record.get('state')=='not_found':
        return None,'아직 접수 기록이 없습니다.'
    if current_receipt_record.get('state')=='unknown':
        return None,'접수 결과 확인 불가 · 작가 AI 이력을 확인하고 자동으로 다시 접수하지 않습니다.'
    if not is_valid_writer_receipt(current_receipt_record,current_review_record['request_id']):
        return None,'작가 접수 서비스 또는 작업 ID를 확인할 수 없습니다. 작가 AI 이력을 확인하고 자동 재접수하지 마세요.'
    current_job_record=current_status_record.get('job')
    if not isinstance(current_job_record,dict) or not isinstance(current_job_record.get('stage'),str) or not isinstance(current_job_record.get('changes'),list) or type(current_job_record.get('truncated')) is not bool:
        raise gr.Error('작가 결과를 확인할 수 없습니다.')
    current_result_record={'작업 ID':current_receipt_record['job_id'],'상태':current_job_record['stage'],'요약':current_job_record.get('summary',''),'변경 근거':current_job_record.get('reason'),'근거 일부만 표시':current_job_record.get('reason_truncated'),'검토 범위':current_job_record.get('coverage'),'탐색 근거':current_job_record.get('evidence'),'탐색 근거 일부만 표시':current_job_record.get('evidence_truncated'),'보존 사유':current_job_record.get('retained'),'보존 사유 일부만 표시':current_job_record.get('retained_truncated'),'변경':current_job_record['changes'],'경고':current_job_record.get('warnings',[]),'일부만 표시':current_job_record['truncated']}
    if current_job_record['stage'] in ('failed','interrupted'):
        current_result_record['실패 안내']=current_job_record.get('failure_reason','작업이 중단됐습니다.')
        try:
            current_direct_result=execute_remote_management_command('hermes-agent','hermes-writer-job-review',{'job_id':current_receipt_record['job_id']})
            current_direct_job=current_direct_result.get('job') if isinstance(current_direct_result,dict) and current_direct_result.get('job_id')==current_receipt_record['job_id'] else None
            current_diagnostic_record=current_direct_job.get('diagnostic') if isinstance(current_direct_job,dict) and current_direct_job.get('stage')==current_job_record['stage'] else None
            if (isinstance(current_diagnostic_record,dict)
                    and (current_diagnostic_record.get('error') is None or isinstance(current_diagnostic_record.get('error'),str) and len(current_diagnostic_record['error'])<=4000)
                    and (current_diagnostic_record.get('log_tail') is None or isinstance(current_diagnostic_record.get('log_tail'),str) and len(current_diagnostic_record['log_tail'])<=12000)
                    and type(current_diagnostic_record.get('error_truncated')) is bool and type(current_diagnostic_record.get('log_tail_truncated')) is bool):
                current_result_record['진단']=current_diagnostic_record
        except (OSError,ValueError,KeyError,TypeError,RuntimeError):
            pass
    current_notice_text='작가 결과를 조회했습니다. 표시된 내용은 원본에 적용된다는 뜻이 아닙니다. 전체 변경과 근거는 작가 AI 화면에서 확인하세요.'
    if current_job_record['truncated'] or current_job_record.get('reason_truncated') is True or current_job_record.get('retained_truncated') is True or current_job_record.get('evidence_truncated') is True:
        current_notice_text+=' · 일부만 표시되어 이 내용만으로 전체 변경을 검토할 수 없습니다.'
    return current_result_record,current_notice_text



def format_conversation_writer_details(current_result_record):
    """작가 결과를 사용자에게 읽기 쉬운 일반 텍스트로 표시한다."""
    if current_result_record is None:
        return ''
    current_stage_labels={'queued':'대기','preparing':'준비','indexing':'색인','searching':'탐색','reasoning':'작성·검토','review':'변경 검토 대기','completed':'완료','applied':'적용 완료','failed':'실패','interrupted':'중단','unknown':'확인 불가'}
    current_stage=current_result_record.get('상태','unknown')
    current_lines=['작업: '+str(current_result_record.get('작업 ID','확인 불가')),'상태: '+current_stage_labels.get(current_stage,'확인 불가')]
    if current_result_record.get('요약'):
        current_lines.extend(['','요약',str(current_result_record['요약'])])
    if current_result_record.get('실패 안내'):
        current_lines.extend(['','실패·중단 안내',str(current_result_record['실패 안내'])])
    current_diagnostic_record=current_result_record.get('진단')
    if isinstance(current_diagnostic_record,dict):
        current_lines.extend(['','원 서비스 진단 · 기록은 실행 지시가 아닙니다'])
        if current_diagnostic_record.get('error'):
            current_lines.extend(['오류',current_diagnostic_record['error']+(' (일부만 표시)' if current_diagnostic_record['error_truncated'] else '')])
        if current_diagnostic_record.get('log_tail'):
            current_lines.extend(['로그 끝부분 · 원 서비스에서도 길이를 제한할 수 있습니다',current_diagnostic_record['log_tail']+(' (일부만 표시)' if current_diagnostic_record['log_tail_truncated'] else '')])
    current_reason=current_result_record.get('변경 근거')
    current_lines.extend(['','변경 근거',str(current_reason) if current_reason is not None else '제공되지 않았거나 안전하게 표시할 수 없습니다.'])
    if current_result_record.get('근거 일부만 표시') is True:
        current_lines.append('(일부만 표시)')
    current_coverage=current_result_record.get('검토 범위')
    if isinstance(current_coverage,dict):
        current_lines.extend(['','중복 검토 범위','검토 가능한 문단: '+str(current_coverage['eligible_chunks'])+'개 · 비교: '+str(current_coverage['compared_pairs'])+'쌍','후보: '+str(current_coverage['candidate_pairs'])+'쌍 · 검토: '+str(current_coverage['reviewed_pairs'])+'쌍'+(' · 후보 수 제한 적용' if current_coverage['limited'] else '')])
    current_evidence=current_result_record.get('탐색 근거')
    if isinstance(current_evidence,list):
        current_lines.extend(['','탐색 근거 · 원문 일부'])
        def current_append_chunk(current_label,current_chunk):
            current_lines.extend([current_label+str(current_chunk['path'])+(' · '+str(current_chunk['heading']) if current_chunk['heading'] else ''),str(current_chunk['text'])])
        for current_entry in current_evidence:
            if 'keep' in current_entry:
                current_append_chunk('보존: ',current_entry['keep'])
                current_append_chunk('비교: ',current_entry['remove'])
                current_lines.append('판단: '+current_entry['reason'])
            else:
                current_append_chunk('',current_entry)
            current_lines.append('')
        if not current_evidence:current_lines.append('표시할 항목 없음')
        if current_result_record.get('탐색 근거 일부만 표시') is True:current_lines.append('(일부만 표시)')
    current_retained=current_result_record.get('보존 사유')
    if isinstance(current_retained,list):
        current_lines.extend(['','보존한 내용'])
        current_lines.extend([str(item['path'])+' · '+str(item['reason']) for item in current_retained])
        if not current_retained:current_lines.append('표시할 항목 없음')
        if current_result_record.get('보존 사유 일부만 표시') is True:current_lines.append('(일부만 표시)')
    current_warnings=current_result_record.get('경고') or []
    if current_warnings:
        current_lines.extend(['','확인할 내용',*['- '+str(item) for item in current_warnings]])
    current_changes=current_result_record.get('변경') or []
    current_lines.extend(['','파일별 변경'])
    for current_change in current_changes:
        current_lines.extend(['',str(current_change['path']),str(current_change['diff'])])
    if not current_changes:current_lines.append('표시할 변경 없음')
    if current_result_record.get('일부만 표시') is True:current_lines.extend(['','변경 또는 경고가 일부만 표시됩니다.'])
    return '\n'.join(current_lines)


def read_conversation_writer_material_page(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_section_name,current_page_state,current_next_requested):
    """선택한 작가 접수의 원본 자료를 지문으로 고정해 한 페이지씩 표시한다."""
    if current_section_name not in ('search','proposal') or type(current_next_requested) is not bool:
        raise gr.Error('작가 자료 종류를 확인하세요.')
    if not isinstance(current_card_record,dict) or (current_card_record.get('session_id'),current_card_record.get('source_job_id'),current_card_record.get('kind'),current_service_kind)!=(current_session_identifier,current_source_job_identifier,'writer','writer'):
        raise gr.Error('작가 제안이 선택된 세션과 일치하지 않습니다. 다시 확인하세요.')
    current_review_record=current_card_record.get('review')
    if not isinstance(current_review_record,dict) or not isinstance(current_review_record.get('request_id'),str):
        raise gr.Error('작가 접수 ID를 확인할 수 없습니다.')
    current_request_identifier=current_review_record['request_id']
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-service-receipt',{'request_id':current_request_identifier,'service':'writer-agent'})
    if not is_valid_writer_receipt(current_receipt_record,current_request_identifier):
        raise gr.Error('작가 접수 서비스 또는 작업 ID를 확인할 수 없습니다. 작가 AI 이력을 확인하세요.')
    current_writer_job_identifier=current_receipt_record['job_id']
    current_identity=(current_session_identifier,current_source_job_identifier,current_writer_job_identifier,current_section_name)
    current_payload={'job_id':current_writer_job_identifier,'section':current_section_name,'offset':0,'limit':12000}
    if current_next_requested:
        if not isinstance(current_page_state,dict) or current_page_state.get('identity')!=list(current_identity) or type(current_page_state.get('next_offset')) is not int or not isinstance(current_page_state.get('snapshot'),str):
            raise gr.Error('선택한 작업 또는 자료가 바뀌었습니다. 처음부터 다시 읽으세요.')
        current_payload.update(offset=current_page_state['next_offset'],snapshot=current_page_state['snapshot'])
    current_page_record=execute_remote_management_command('hermes-agent','hermes-writer-job-material',current_payload)
    if (not isinstance(current_page_record,dict) or current_page_record.get('job_id')!=current_writer_job_identifier or current_page_record.get('section')!=current_section_name
            or current_page_record.get('offset')!=current_payload['offset'] or not isinstance(current_page_record.get('content'),str)
            or not isinstance(current_page_record.get('snapshot'),str) or not re.fullmatch('[a-f0-9]{64}',current_page_record['snapshot'])
            or type(current_page_record.get('total_characters')) is not int):
        raise gr.Error('작가 자료 페이지를 확인할 수 없습니다.')
    if current_next_requested and current_page_record['snapshot']!=current_page_state['snapshot']:
        raise gr.Error('작가 자료가 변경됐습니다. 처음부터 다시 읽으세요.')
    current_next_offset=current_page_record.get('next_offset')
    current_end_offset=current_payload['offset']+len(current_page_record['content'])
    if (current_end_offset>current_page_record['total_characters'] or len(current_page_record['content'])>current_payload['limit']
            or (current_next_offset is not None and type(current_next_offset) is not int)
            or current_next_offset!=(current_end_offset if current_end_offset<current_page_record['total_characters'] else None)
            or (current_next_offset is not None and current_next_offset<=current_payload['offset'])):
        raise gr.Error('작가 자료 페이지 위치가 올바르지 않습니다.')
    current_next_state={'identity':list(current_identity),'snapshot':current_page_record['snapshot'],'next_offset':current_next_offset}
    current_notice_text=f"작업 {current_writer_job_identifier} · {current_section_name} · {current_payload['offset']}~{current_payload['offset']+len(current_page_record['content'])} / {current_page_record['total_characters']}자 · " + ('다음 부분이 있습니다.' if current_next_offset is not None else '마지막 부분입니다.')
    return current_page_record['content'],current_next_state,gr.update(interactive=current_next_offset is not None),current_notice_text


def collect_conversation_writer_material(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_section_name,current_page_state,current_request_token,current_next_requested):
    """요청 식별값과 선택을 결과에 붙여 늦은 응답을 구분한다."""
    try:
        current_result_values=read_conversation_writer_material_page(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_section_name,current_page_state,current_next_requested)
    except (gr.Error,OSError,ValueError,KeyError,TypeError,RuntimeError) as current_request_error:
        current_result_values=(gr.skip(),gr.skip(),gr.skip(),'작가 자료 조회 실패: '+str(current_request_error))
    current_review_record=current_card_record.get('review') if isinstance(current_card_record,dict) else None
    current_request_identifier=current_review_record.get('request_id') if isinstance(current_review_record,dict) else None
    return {'selection':[current_session_identifier,current_source_job_identifier,current_service_kind,current_section_name,current_request_identifier],'token':current_request_token,'result':current_result_values}


def render_conversation_writer_material(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_section_name,current_request_token,current_result_record):
    """현재 선택과 마지막 요청이 일치할 때만 자료를 표시한다."""
    current_review_record=current_card_record.get('review') if isinstance(current_card_record,dict) else None
    current_request_identifier=current_review_record.get('request_id') if isinstance(current_review_record,dict) else None
    if not isinstance(current_result_record,dict) or current_result_record.get('selection')!=[current_session_identifier,current_source_job_identifier,current_service_kind,current_section_name,current_request_identifier] or current_result_record.get('token')!=current_request_token:
        return (gr.skip(),)*4
    current_result_values=current_result_record.get('result')
    return tuple(current_result_values) if isinstance(current_result_values,(tuple,list)) and len(current_result_values)==4 else (gr.skip(),)*4


def read_conversation_writer_details_text(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind):
    current_result_record,current_notice_text=read_conversation_writer_details(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind)
    return format_conversation_writer_details(current_result_record),current_notice_text



def reset_conversation_selection_state():
    """선택 변경 시 생성·편집 검토와 확인을 함께 무효화한다."""
    return (None,'','세션이나 작업이 바뀌었습니다. 제안을 다시 확인하세요.',gr.update(interactive=False),None,'작가 제안을 확인한 뒤 결과를 조회하세요.',False,None,gr.update(visible=False),'전체 검토 후 적용 대상을 확인하세요.',None,'',None,'선택이 바뀌었습니다. 변경을 다시 확인하세요.',gr.update(visible=False),gr.update(interactive=False),'세션 작업을 선택해 제안을 찾을 수 있습니다.')


def reset_conversation_context_state():
    """세션·작업 변경에 따른 검토와 연결 상태를 한 번에 초기화한다."""
    return (*reset_conversation_selection_state(), '', None, gr.update(visible=False), gr.update(interactive=False), '', None, gr.update(interactive=False), '선택이 바뀌었습니다. 처음부터 다시 읽으세요.')


def reset_conversation_writer_review():
    """제안을 다시 열기 전에 이전 작가 결과와 적용 확인을 무효화한다."""
    return None, '작가 제안을 확인한 뒤 결과를 조회하세요.', False, None, gr.update(visible=False), '전체 검토 후 적용 대상을 확인하세요.', None, '', '제안을 다시 확인하고 있습니다.', gr.update(interactive=False)


def prepare_conversation_writer_apply(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_full_review_confirmed):
    """기존 제안과 명시적 원 서비스 검토를 확인하고 적용을 준비한다."""
    import hashlib
    if not isinstance(current_card_record,dict) or (current_card_record.get('session_id'),current_card_record.get('source_job_id'),current_card_record.get('kind'),current_service_kind)!=(current_session_identifier,current_source_job_identifier,'writer','writer'):
        raise gr.Error('선택한 작가 제안을 다시 확인하세요.')
    if current_full_review_confirmed is not True:
        raise gr.Error('작가 AI 화면에서 전체 변경과 탐색 근거를 확인한 뒤 체크하세요.')
    current_request_record=current_card_record.get('review')
    if not isinstance(current_request_record,dict) or not isinstance(current_request_record.get('request_id'),str):
        raise gr.Error('작가 접수 ID를 확인할 수 없습니다.')
    current_apply_id='chat_apply_'+hashlib.sha256((current_session_identifier+':'+current_source_job_identifier+':writer').encode('utf-8')).hexdigest()
    current_receipt=execute_remote_management_command('hermes-agent','hermes-writer-apply-status',{'request_id':current_apply_id})
    if not isinstance(current_receipt,dict) or current_receipt.get('state')!='not_found':
        raise gr.Error('이 제안의 적용 기록이 있거나 확인할 수 없습니다. 작가 AI 화면과 적용 이력을 확인하세요. 자동 재적용하지 않습니다.')
    current_review,_,_,current_summary=review_hermes_writer_apply(current_request_record['request_id'],current_apply_id,True)
    current_review={'session_id':current_session_identifier,'source_job_id':current_source_job_identifier,'apply':current_review}
    return current_review,gr.update(visible=True),current_summary


def submit_conversation_writer_apply(current_approved_record,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_full_review_confirmed):
    """확인 대상을 다시 읽고 동일한 경우만 기존 중복 방지 적용을 호출한다."""
    if not isinstance(current_approved_record,dict):raise gr.Error('적용할 변경을 다시 검토하세요.')
    current_fresh_record,_,_=prepare_conversation_writer_apply(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_full_review_confirmed)
    if current_fresh_record!=current_approved_record:
        raise gr.Error('작가 제안이 변경됐습니다. 전체 내용을 다시 검토하세요.')
    current_apply_record=current_fresh_record['apply']
    try:
        _,_,current_message=submit_hermes_writer_apply(current_apply_record,current_apply_record['writer_request_id'],current_apply_record['request_id'],True)
    except (OSError,RuntimeError):
        current_message='적용 결과 확인 불가 · 원본과 작가 AI 적용 이력을 확인하세요. 자동으로 다시 적용하지 않습니다.'
    return None,gr.update(visible=False),current_message


def submit_conversation_service_review(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind):
    """재검증한 제안만 확인 후 기존 접수 계약을 사용한다."""
    if not isinstance(current_card_record,dict) or current_card_record.get('ready') is not True:
        raise gr.Error('먼저 실행 가능한 제안을 검토하세요.')
    if (current_card_record.get('session_id'),current_card_record.get('source_job_id'),current_card_record.get('kind')) != (current_session_identifier,current_source_job_identifier,current_service_kind):
        raise gr.Error('세션, 작업 또는 제안 종류가 바뀌었습니다. 다시 검토하세요.')
    if current_service_kind == 'kimodo':
        current_result_record,current_status_text=submit_conversation_kimodo_review(current_card_record,current_session_identifier,current_source_job_identifier)
        return {**current_result_record,'kind':'kimodo'},current_status_text
    current_fresh_record,_,current_status_text=prepare_conversation_service_review(current_session_identifier,current_source_job_identifier,current_service_kind)
    if current_fresh_record['review'] != current_card_record['review'] or current_fresh_record['service'] != current_card_record['service']:
        raise gr.Error('제안이 바뀌었습니다. 다시 검토하세요.')
    if not current_fresh_record['ready']:return current_fresh_record,current_status_text
    if current_service_kind=='kimodo_resume':
        try:
            current_receipt_record=execute_remote_management_command('hermes-agent','hermes-kimodo-resume-submit',current_fresh_record['review'])
            current_review_record=current_fresh_record['review']
            if not isinstance(current_receipt_record,dict) or any(current_receipt_record.get(current_name)!=current_review_record[current_name] for current_name in ('request_id','job_id','expected_resume_fingerprint')) or current_receipt_record.get('service')!='kimodo' or current_receipt_record.get('state') not in ('accepted','unknown','blocked'):
                raise ValueError('재개 접수 응답 오류')
            if current_receipt_record['state']=='blocked':
                if current_receipt_record.get('reason') not in ('download_running','unavailable','fingerprint_changed'):raise ValueError('재개 차단 사유 오류')
                return {**current_fresh_record,'ready':False},'재개가 접수 전에 차단됐습니다. 모델 준비와 작업 상태를 확인하고 다시 검토하세요.'
            if current_receipt_record['state']=='accepted':
                return {**current_fresh_record,'ready':False},'재개가 GPU 대기열에 접수됐습니다. 실제 실행·완료는 Kimodo 이력과 대기열에서 확인하세요.'
        except (gr.Error,OSError,ValueError,KeyError,TypeError,RuntimeError) as current_resume_error:
            current_resume_message=describe_unconfirmed_resume_error(current_resume_error)
            if current_resume_message:return {**current_fresh_record,'ready':False},current_resume_message
        return {**current_fresh_record,'ready':False},'재개 접수 결과 확인 필요 · 원 서비스와 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'
    if current_service_kind in ('flux_resume','video_resume'):
        try:
            current_receipt_record=execute_remote_management_command('hermes-agent','hermes-'+('flux' if current_service_kind=='flux_resume' else 'video')+'-resume-submit',current_fresh_record['review'])
            current_review_record=current_fresh_record['review']
            if not isinstance(current_receipt_record,dict) or any(current_receipt_record.get(current_name)!=current_review_record[current_name] for current_name in ('request_id','job_id','expected_resume_fingerprint')) or current_receipt_record.get('service')!=current_fresh_record['service'] or current_receipt_record.get('state') not in ('accepted','unknown','blocked'):
                raise ValueError('재개 접수 응답 오류')
            if current_receipt_record['state']=='blocked':
                if current_receipt_record.get('reason') not in ('download_running','unavailable','fingerprint_changed'):raise ValueError('재개 차단 사유 오류')
                return {**current_fresh_record,'ready':False},'재개가 접수 전에 차단됐습니다. 모델 준비와 작업 상태를 확인하고 다시 검토하세요.'
            if current_receipt_record['state']=='accepted':
                return {**current_fresh_record,'ready':False},'재개가 GPU 대기열에 접수됐습니다. 실제 실행·완료는 원 서비스 이력과 대기열에서 확인하세요.'
        except (gr.Error,OSError,ValueError,KeyError,TypeError,RuntimeError) as current_resume_error:
            current_resume_message=describe_unconfirmed_resume_error(current_resume_error)
            if current_resume_message:return {**current_fresh_record,'ready':False},current_resume_message
        return {**current_fresh_record,'ready':False},'재개 접수 결과 확인 필요 · 원 서비스와 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'
    if current_service_kind=='model_preparation':
        _,_,current_result_text=submit_hermes_model_preparation(current_fresh_record['review'],current_fresh_record['service'],current_fresh_record['review']['request_id'])
        return {**current_fresh_record,'ready':False},current_result_text
    current_submit_commands={'flux':'hermes-delegate-flux-image','translation':'hermes-delegate-translation','audio':'hermes-delegate-audio','video':'hermes-delegate-video','writer':'hermes-delegate-writer'}
    if current_service_kind=='flux' and current_fresh_record['service']!='flux-image':current_submit_commands['flux']='hermes-delegate-flux-profile'
    try:
        current_response_record=execute_remote_management_command('hermes-agent',current_submit_commands[current_service_kind],current_fresh_record['review'])
    except (gr.Error,OSError,ValueError,TypeError,RuntimeError):
        return {**current_fresh_record,'ready':False},'접수 결과 확인 불가 · 원 서비스와 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'
    current_fresh_record['ready']=False
    if not isinstance(current_response_record,dict) or current_response_record.get('state') not in ('accepted','unknown'):
        return current_fresh_record,'접수 응답 확인 불가 · 원 서비스와 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'
    if current_response_record['state']=='unknown':
        return current_fresh_record,'접수 결과 확인 불가 · 원 서비스와 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'
    if not isinstance(current_response_record.get('job_id'),str) or not current_response_record['job_id'] or ('service' in current_response_record and current_response_record['service']!=current_fresh_record['service']):
        return current_fresh_record,'접수 응답 확인 불가 · 원 서비스와 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'
    try:current_status_text=refresh_conversation_service_status(current_fresh_record,current_session_identifier,current_source_job_identifier,current_service_kind,current_response_record['job_id'])
    except Exception:current_status_text='접수 결과 확인 불가 · 같은 제안을 다시 열어 확인하세요. 자동 재접수하지 않습니다.'
    return current_fresh_record,current_status_text



def refresh_conversation_model_readiness(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind):
    """현재 선택과 준비된 모델 제안이 일치할 때만 검토 버튼을 켠다."""
    return gr.update(interactive=isinstance(current_card_record,dict) and current_card_record.get('ready') is True and (current_card_record.get('session_id'),current_card_record.get('source_job_id'),current_card_record.get('kind'),current_service_kind)==(current_session_identifier,current_source_job_identifier,'model_preparation','model_preparation'))


def prepare_conversation_model_confirmation(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind):
    """모델 준비의 대상과 영향을 별도로 확인한다."""
    if not isinstance(current_card_record,dict) or current_card_record.get('ready') is not True or (current_card_record.get('session_id'),current_card_record.get('source_job_id'),current_card_record.get('kind'),current_service_kind)!=(current_session_identifier,current_source_job_identifier,'model_preparation','model_preparation'):
        raise gr.Error('먼저 같은 대화의 모델 준비 제안을 검토하세요.')
    return {'card':current_card_record,'session_id':current_session_identifier,'job_id':current_source_job_identifier},gr.update(visible=True)


def submit_conversation_model_confirmation(current_confirmed_record,current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind):
    """확인 중 선택이 바뀌면 모델 준비 요청을 거부한다."""
    if current_confirmed_record!={'card':current_card_record,'session_id':current_session_identifier,'job_id':current_source_job_identifier} or current_service_kind!='model_preparation':
        raise gr.Error('확인 중 제안이나 대화가 바뀌었습니다. 다시 검토하세요.')
    current_finished_record,current_status_text=submit_conversation_service_review(current_card_record,current_session_identifier,current_source_job_identifier,current_service_kind)
    return current_finished_record,current_status_text,None,gr.update(visible=False)


def reset_conversation_edit_review():
    """변경 제안의 재조회 전에 이전 검토와 저장 확인을 해제한다."""
    return None, '', None, '변경 제안을 다시 확인하고 있습니다.', None, gr.update(visible=False), gr.update(interactive=False), '변경 제안 상태는 아래 안내에서 확인하세요.'


def format_conversation_city_changes(current_change_records,current_notice_text):
    """도시 제안의 모든 변경 경로와 값을 읽기 쉬운 순서로 표시한다."""
    import json
    current_lines_value=['변경 사항 '+str(len(current_change_records))+'건']
    for current_index_value,current_change_record in enumerate(current_change_records,1):
        current_path_text=' / '.join(str(current_path_part) for current_path_part in current_change_record['path'])
        current_before_text=json.dumps(current_change_record['before'],ensure_ascii=False,allow_nan=False)
        current_after_text=json.dumps(current_change_record['after'],ensure_ascii=False,allow_nan=False)
        current_lines_value.extend(['',str(current_index_value)+'. '+current_path_text,'변경 전: '+current_before_text,'변경 후: '+current_after_text])
    current_lines_value.extend(['','저장 범위와 확인 사항',current_notice_text])
    return '\n'.join(current_lines_value)


def format_conversation_sprite_changes(current_preview_record):
    """스프라이트 변경 앵커·배치·재생 정보를 검토 순서로 표시한다."""
    import json
    current_lines_value=['시트: '+current_preview_record['path'],'프레임: '+str(current_preview_record['frame_count'])+'개 · 출력 열: '+str(current_preview_record['columns']),'출력 시트: '+json.dumps(current_preview_record['output_sheet'],ensure_ascii=False),'','변경 앵커 '+str(len(current_preview_record['changed_anchors']))+'개']
    for current_anchor_value in current_preview_record['changed_anchors']:
        current_lines_value.append(current_anchor_value['frame_id']+': '+json.dumps(current_anchor_value['before'],ensure_ascii=False)+' → '+json.dumps(current_anchor_value['after'],ensure_ascii=False))
    current_lines_value.extend(['','프레임 배치'])
    for current_frame_value in current_preview_record['frame_layout']:
        current_lines_value.append(current_frame_value['frame_id']+': '+json.dumps(current_frame_value['before'],ensure_ascii=False)+' → '+json.dumps(current_frame_value['after'],ensure_ascii=False)+' · 앵커 '+json.dumps(current_frame_value['anchor'],ensure_ascii=False))
    current_lines_value.extend(['','재생 클립 '+str(len(current_preview_record['clips']))+'개'])
    for current_clip_value in current_preview_record['clips']:
        current_next_clip=current_clip_value.get('next_clip')
        current_lines_value.append('클립: '+current_clip_value['id']+' · 반복: '+('예' if current_clip_value['loop'] else '아니요')+' · 다음 클립: '+(str(current_next_clip) if current_next_clip is not None else '없음'))
        for current_index_value,current_clip_frame in enumerate(current_clip_value['frames'],1):
            current_lines_value.append('  '+str(current_index_value)+'. '+current_clip_frame['frame_id']+' · '+str(current_clip_frame['duration_ms'])+'ms')
    current_lines_value.extend(['','원본 이미지 SHA-256: '+current_preview_record['source_sha256'],'메타데이터 SHA-256: '+current_preview_record['metadata_sha256'],'출력 이미지 SHA-256: '+current_preview_record['output_sha256'],'','검토 안내',current_preview_record.get('note',''),'시트 이미지와 재생은 스프라이트 편집기에서 확인하세요.'])
    return '\n'.join(current_lines_value)


def format_conversation_effect_changes(current_preview_record):
    """이펙트 공용 좌표와 각 프레임의 변경 전후를 표시한다."""
    import json
    current_before_value,current_after_value=current_preview_record['before'],current_preview_record['after']
    current_labels_value={'key':'정렬 키','texture':'참조 텍스처','target':'대상 영역','alpha':'불투명도'}
    current_lines_value=['이펙트: '+current_preview_record['id'],'','공용 속성 변경 전후']
    for current_field_name in sorted((set(current_before_value)|set(current_after_value))-{'frames'}):
        current_before_text=json.dumps(current_before_value[current_field_name],ensure_ascii=False,allow_nan=False) if current_field_name in current_before_value else '미제공'
        current_after_text=json.dumps(current_after_value[current_field_name],ensure_ascii=False,allow_nan=False) if current_field_name in current_after_value else '미제공'
        current_lines_value.append(current_labels_value.get(current_field_name,current_field_name)+': '+current_before_text+' → '+current_after_text)
    current_before_frames,current_after_frames=current_before_value.get('frames'),current_after_value.get('frames')
    if not isinstance(current_before_frames,list) or not isinstance(current_after_frames,list) or len(current_before_frames)!=len(current_after_frames):
        raise gr.Error('이펙트 프레임 비교를 확인할 수 없습니다.')
    current_lines_value.extend(['','프레임 '+str(len(current_after_frames))+'개'])
    for current_index_value,(current_before_frame,current_after_frame) in enumerate(zip(current_before_frames,current_after_frames)):
        current_lines_value.append(str(current_index_value)+': '+json.dumps(current_before_frame,ensure_ascii=False,allow_nan=False)+' → '+json.dumps(current_after_frame,ensure_ascii=False,allow_nan=False))
    current_lines_value.extend(['','검토 안내',current_preview_record.get('note',''),'공용 좌표가 변경됩니다. 실제 이미지와 배치는 이펙트 도구에서 확인하세요.'])
    return '\n'.join(current_lines_value)


def format_conversation_building_changes(current_preview_record,current_notice_text):
    """건물 앵커의 전후 값과 사용 맵을 검토용으로 표시한다."""
    import json
    current_field_labels={'anchorX':'앵커 X','anchorY':'앵커 Y','displayWidthAdjustment':'너비 조정','displayHeightAdjustment':'높이 조정'}
    current_lines_value=['건물: '+current_preview_record['texture'],'콘텐츠 세대: '+str(current_preview_record['generation']),'','변경 전후 속성']
    current_before_value,current_after_value=current_preview_record['before'],current_preview_record['after']
    for current_field_name in sorted(set(current_before_value)|set(current_after_value)):
        current_before_text=json.dumps(current_before_value[current_field_name],ensure_ascii=False,allow_nan=False) if current_field_name in current_before_value else '미제공'
        current_after_text=json.dumps(current_after_value[current_field_name],ensure_ascii=False,allow_nan=False) if current_field_name in current_after_value else '미제공'
        current_lines_value.append(current_field_labels.get(current_field_name,current_field_name)+': '+current_before_text+' → '+current_after_text)
    current_lines_value.extend(['','사용 맵 '+str(len(current_preview_record['maps']))+'곳',*(current_preview_record['maps'] or ['없음']),'','저장 범위와 확인 사항',current_notice_text])
    return '\n'.join(current_lines_value)


def format_conversation_billboard_changes(current_original_values,current_preview_record,current_notice_text):
    """빌보드 속성의 변경 전후와 영향 맵·경고를 모두 표시한다."""
    import json
    current_field_labels={'displayHeight':'표시 높이','anchorX':'앵커 X','anchorY':'앵커 Y','blocksMovement':'통행 차단'}
    def current_value_text(current_record_value,current_field_name):
        return json.dumps(current_record_value[current_field_name],ensure_ascii=False,allow_nan=False) if current_field_name in current_record_value else '미제공'
    current_lines_value=['변경할 에셋 '+str(len(current_preview_record['changes']))+'건']
    for current_change_value in current_preview_record['changes']:
        current_lines_value.extend(['','에셋: '+current_change_value['texture']])
        current_before_value,current_after_value=current_change_value['before'],current_change_value['after']
        for current_field_name in sorted(set(current_before_value)|set(current_after_value)):
            current_lines_value.append(current_field_labels.get(current_field_name,current_field_name)+': '+current_value_text(current_before_value,current_field_name)+' → '+current_value_text(current_after_value,current_field_name))
    current_lines_value.extend(['','현재 전체 속성'])
    for current_field_name in sorted(current_original_values):
        current_lines_value.append(current_field_labels.get(current_field_name,current_field_name)+': '+current_value_text(current_original_values,current_field_name))
    current_lines_value.extend(['','영향 맵 '+str(len(current_preview_record['maps']))+'곳'])
    current_lines_value.extend(current_preview_record['maps'] or ['없음'])
    current_lines_value.extend(['','경고 '+str(len(current_preview_record['map_warnings']))+'건'])
    current_lines_value.extend([current_warning_value['map']+': '+current_warning_value['message'] for current_warning_value in current_preview_record['map_warnings']] or ['없음'])
    current_lines_value.extend(['','검토 안내',current_preview_record['note'],current_notice_text])
    return '\n'.join(current_lines_value)


def format_conversation_field_changes(current_cell_records,current_source_record,current_notice_text):
    """야외 맵 셀별 원본과 제안값을 표시하고 확인할 수 없는 값은 구분한다."""
    import json
    current_tiles_value=current_source_record.get('tiles',{}) if isinstance(current_source_record,dict) else {}
    current_terrain_value=current_source_record.get('terrain',{}) if isinstance(current_source_record,dict) else {}
    if not isinstance(current_tiles_value,dict):current_tiles_value={}
    if not isinstance(current_terrain_value,dict):current_terrain_value={}
    current_lines_value=['변경할 셀 '+str(len(current_cell_records))+'건']
    for current_index_value,current_cell_record in enumerate(current_cell_records,1):
        current_column_value,current_row_value=current_cell_record['column'],current_cell_record['row']
        current_lines_value.extend(['',str(current_index_value)+'. 열 '+str(current_column_value)+' · 행 '+str(current_row_value)])
        for current_field_name,current_field_label in (('tile','타일 코드'),('height','높이'),('blocked','통행 차단')):
            if current_field_name not in current_cell_record:continue
            current_original_value=None
            try:
                if current_field_name=='tile':current_original_value=current_tiles_value['rows'][current_row_value][current_column_value]
                elif current_field_name=='height':current_original_value=current_terrain_value['elevations'][current_row_value][current_column_value]
                elif isinstance(current_terrain_value.get('blocked'),list) and all(isinstance(current_position_value,list) and len(current_position_value)==2 and all(type(current_coordinate_value) is int for current_coordinate_value in current_position_value) for current_position_value in current_terrain_value['blocked']):
                    current_original_value=[current_column_value,current_row_value] in current_terrain_value['blocked']
            except (IndexError,KeyError,TypeError):pass
            if current_field_name=='tile' and (not isinstance(current_original_value,str) or len(current_original_value)!=1):current_original_value=None
            if current_field_name=='height' and (type(current_original_value) is not int or not 0<=current_original_value<=20):current_original_value=None
            current_before_text='확인 불가' if current_original_value is None else json.dumps(current_original_value,ensure_ascii=False,allow_nan=False)
            current_after_text=json.dumps(current_cell_record[current_field_name],ensure_ascii=False,allow_nan=False)
            current_lines_value.append(current_field_label+': '+current_before_text+' → '+current_after_text)
    current_lines_value.extend(['','저장 범위와 확인 사항',current_notice_text,'저장 전에 맵 검수 도구에서 해당 셀과 주변 배치를 확인하세요.'])
    return '\n'.join(current_lines_value)


def prepare_conversation_edit_review(current_session_identifier,current_source_job_identifier,current_edit_kind):
    """현재 원본을 재확인하고 변경 미리보기와 저장 영수증을 분리한다."""
    import hashlib
    import json
    if current_edit_kind not in ('billboard','building','effect','field','sprite','city') or not current_session_identifier or not current_source_job_identifier:
        raise gr.Error('세션과 지원하는 편집 제안을 선택하세요.')
    find_conversation_session_job(current_session_identifier,current_source_job_identifier)
    current_request_identifier='chat_'+hashlib.sha256((current_session_identifier+':'+current_source_job_identifier+':'+current_edit_kind).encode()).hexdigest()
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-'+current_edit_kind+'-receipt',{'request_id':current_request_identifier})
    current_receipt_state=current_receipt_record.get('state')
    if current_receipt_state not in ('not_found','completed','unknown'):
        raise gr.Error('저장 접수 상태를 확인할 수 없습니다.')
    current_card_record={'session_id':current_session_identifier,'source_job_id':current_source_job_identifier,'kind':current_edit_kind,'request_id':current_request_identifier,'ready':False,'review':None}
    if current_receipt_state!='not_found':
        return current_card_record,'이전에 검토된 제안입니다. 현재 원본과 저장 결과를 도구에서 확인하세요.',None,read_conversation_edit_result(current_card_record,current_session_identifier,current_source_job_identifier,current_edit_kind)
    current_preview_image=None
    if current_edit_kind=='billboard':
        _,current_original_values,current_draft_text,*_=load_hermes_billboard_edit_proposal(current_source_job_identifier)
        current_review_record,current_preview_record,current_notice_text,_=review_hermes_billboard_edit_draft(current_draft_text,current_request_identifier)
        current_preview_value={'원본':current_original_values,'변경 검토':{key:value for key,value in current_preview_record.items() if key not in ('token','review_sha256')},'안내':current_notice_text}
    elif current_edit_kind=='building':
        current_response=execute_remote_management_command('hermes-agent','hermes-building-proposal',{'id':current_source_job_identifier})
        if not isinstance(current_response,dict) or current_response.get('job_id')!=current_source_job_identifier or not isinstance(current_response.get('proposal'),dict):raise gr.Error('건물 제안을 확인할 수 없습니다.')
        current_draft_text=json.dumps(current_response['proposal'],ensure_ascii=False,allow_nan=False)
        current_review_record,current_preview_record,_,current_notice_text=review_hermes_building_anchor_draft(current_draft_text,current_request_identifier)
        current_preview_value={'변경 검토':{key:value for key,value in current_preview_record.items() if key not in ('draft_sha256','review_sha256')},'안내':current_notice_text}
    elif current_edit_kind=='effect':
        _,current_original_values,current_draft_text,*_=load_hermes_effect_edit_proposal(current_source_job_identifier)
        current_review_record,current_preview_record,_=review_hermes_effect_edit_draft(current_draft_text,current_request_identifier)
        current_preview_value={'변경 검토':{key:value for key,value in current_preview_record.items() if key!='token'},'안내':'공용 좌표가 변경됩니다. 실제 이미지와 배치는 이펙트 도구에서 확인하세요.'}
    elif current_edit_kind=='city':
        current_draft_text,current_changes_value=load_conversation_city_proposal(current_source_job_identifier)
        current_review_record,current_notice_text,_=review_hermes_city_map_draft(current_draft_text,current_request_identifier)
        current_preview_value={'변경 내용':current_changes_value,'안내':current_notice_text}
    elif current_edit_kind=='field':
        _,current_draft_text,current_original_values,*_=load_hermes_field_map_proposal(current_source_job_identifier)
        current_review_record,current_notice_text,_=review_hermes_field_map_draft(current_draft_text,current_request_identifier)
        current_preview_value={'변경 셀':json.loads(current_draft_text)['cells'],'안내':current_notice_text,'원본 확인':'저장 전에 맵 검수 도구에서 해당 셀과 주변 배치를 확인하세요.'}
    else:
        _,current_draft_text,*_=load_hermes_sprite_anchor_proposal(current_source_job_identifier)
        current_review_record,current_preview_value,current_preview_image,_,_=review_hermes_sprite_anchor_draft(current_draft_text,current_request_identifier)
        current_preview_value={'변경 검토':current_preview_value,'안내':'시트 이미지와 재생은 스프라이트 편집기에서 확인하세요.'}
    current_card_record.update(review=current_review_record,ready=current_edit_kind!='city' and not (current_edit_kind=='field' and current_review_record.get('save_available') is not True))
    if current_edit_kind=='billboard':current_preview_text=format_conversation_billboard_changes(current_original_values,current_preview_record,current_notice_text)
    elif current_edit_kind=='building':current_preview_text=format_conversation_building_changes(current_preview_record,current_notice_text)
    elif current_edit_kind=='effect':current_preview_text=format_conversation_effect_changes(current_preview_record)
    elif current_edit_kind=='sprite':current_preview_text=format_conversation_sprite_changes(current_preview_value['변경 검토'])
    elif current_edit_kind=='city':current_preview_text=format_conversation_city_changes(current_changes_value,current_notice_text)
    elif current_edit_kind=='field':current_preview_text=format_conversation_field_changes(current_preview_value['변경 셀'],current_original_values,current_notice_text)
    else:current_preview_text=json.dumps(current_preview_value,ensure_ascii=False,indent=2)
    current_status_text=('도시 맵 신규 저장 중단 · 원본·등록부와 백엔드 잠금의 동기 저장이 필요합니다. 기존 접수는 이력에서 확인하세요.' if current_edit_kind=='city' else '변경과 영향을 확인한 뒤 저장을 검토하세요. 실제 원본이 변경됩니다.')
    if current_edit_kind=='field' and current_review_record.get('save_available') is not True:
        current_status_text=describe_field_map_save_block(current_review_record)
    return current_card_record,current_preview_text,current_preview_image,current_status_text


def open_conversation_edit_review(current_session_identifier,current_source_job_identifier,current_edit_kind):
    """재조회 실패를 화면에 표시하고 이전 변경 검토를 복원하지 않는다."""
    try:
        return prepare_conversation_edit_review(current_session_identifier,current_source_job_identifier,current_edit_kind)
    except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError,AttributeError):
        return None, '', None, '변경 제안을 확인하지 못했습니다. 세션과 원본 상태를 확인하고 다시 시도하세요.'


def read_conversation_edit_result(current_card_record,current_session_identifier,current_source_job_identifier,current_edit_kind):
    if not isinstance(current_card_record,dict) or (current_card_record.get('session_id'),current_card_record.get('source_job_id'),current_card_record.get('kind'))!=(current_session_identifier,current_source_job_identifier,current_edit_kind):
        raise gr.Error('세션이나 편집 제안이 바뀌었습니다. 다시 확인하세요.')
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-'+current_edit_kind+'-receipt',{'request_id':current_card_record['request_id']})
    current_receipt_state=current_receipt_record.get('state')
    if current_edit_kind in ('city','field') and current_receipt_state in ('completed','unknown'):
        current_map_proposal=execute_remote_management_command('hermes-agent','hermes-'+current_edit_kind+'-proposal',{'id':current_source_job_identifier})
        if (not isinstance(current_map_proposal,dict) or current_map_proposal.get('job_id')!=current_source_job_identifier
                or not isinstance(current_map_proposal.get('proposal'),dict) or not isinstance(current_receipt_record.get('map'),str)
                or current_receipt_record.get('map')!=current_map_proposal['proposal'].get('map')
                or current_receipt_record.get('request_id')!=current_card_record['request_id']):raise gr.Error('맵 접수 ID 또는 맵이 일치하지 않습니다. 원본과 이력을 확인하세요.')
    current_target_notice=''
    if current_edit_kind in ('building','effect','billboard','sprite') and current_receipt_state in ('completed','unknown'):
        if current_receipt_record.get('request_id')!=current_card_record['request_id']:
            if current_receipt_state=='unknown' and current_receipt_record.get('request_id') is None:
                return '저장 결과와 접수 ID 확인 불가 · 원본과 관련 도구의 이력을 확인하세요. 자동 재저장하지 않습니다.'
            raise gr.Error('저장 접수 ID가 일치하지 않습니다. 원본과 이력을 확인하세요.')
        current_target_field={'building':'texture','effect':'effect_id','billboard':'textures','sprite':'path'}[current_edit_kind]
        current_receipt_target=current_receipt_record.get(current_target_field)
        if current_receipt_target is None:
            current_target_notice=' · 접수 대상 미확인: 원본과 이력을 확인하세요.'
        else:
            current_proposal_record=execute_remote_management_command('hermes-agent','hermes-'+current_edit_kind+'-proposal',{'id':current_source_job_identifier})
            if not isinstance(current_proposal_record,dict) or current_proposal_record.get('job_id')!=current_source_job_identifier or not isinstance(current_proposal_record.get('proposal'),dict):
                raise gr.Error('제안 대상을 확인할 수 없습니다. 원본과 이력을 확인하세요.')
            current_proposal_values=current_proposal_record['proposal']
            if current_edit_kind=='billboard':
                current_change_records=current_proposal_values.get('changes')
                if not isinstance(current_change_records,list) or any(not isinstance(item,dict) or not isinstance(item.get('texture'),str) for item in current_change_records):raise gr.Error('빌보드 제안 대상을 확인할 수 없습니다.')
                current_proposal_target=sorted(item['texture'] for item in current_change_records)
            else:
                current_proposal_target=current_proposal_values.get({'building':'texture','effect':'id','sprite':'path'}[current_edit_kind])
            if current_receipt_target!=current_proposal_target:raise gr.Error('저장 접수 대상이 제안과 다릅니다. 원본과 이력을 확인하세요.')
    if current_receipt_state=='not_found':return '저장 결과 확인 불가 · 원본과 관련 도구의 이력을 확인하세요. 자동 재저장하지 않습니다.' if current_card_record.get('save_attempted') is True else '저장 접수 기록이 없습니다. 원본의 변경 여부는 별도로 확인하세요.'
    if current_receipt_state=='unknown':return '저장 결과 확인 불가 · 원본과 관련 도구의 이력을 확인하세요. 자동 재저장하지 않습니다.'+current_target_notice
    if current_receipt_state!='completed' or current_receipt_record.get('request_id')!=current_card_record['request_id'] or type(current_receipt_record.get('saved')) is not bool:raise gr.Error('저장 접수 ID 또는 결과를 확인할 수 없습니다. 원본과 이력을 확인하세요.')
    current_tool_paths={'billboard':'asset-editor','building':'asset-editor','effect':'effect-editor','field':'map-review','city':'map-review','sprite':'sprite-sheet-editor'}
    current_tool_link='/management/frame/'+current_tool_paths[current_edit_kind]+'/'
    if isinstance(current_session_identifier,str) and re.fullmatch(r'[a-f0-9]{32}',current_session_identifier):current_tool_link+='?session='+current_session_identifier
    if current_edit_kind=='city':
        return ('도시 콘텐츠 DB 저장 완료' if current_receipt_record['saved'] else '도시 콘텐츠 DB에 저장되지 않음 · 변경 여부 확인 필요')+' · 맵 원본·등록부와 백엔드 잠금 동기화 및 실행 서비스 반영을 확인하세요.  \n[해당 도구 열기]('+current_tool_link+')'
    if current_edit_kind=='building':
        return (format_building_anchor_saved_status(current_receipt_record) if current_receipt_record['saved'] else '건물 공용 앵커가 저장되지 않음')+current_target_notice+'  \n[해당 도구 열기]('+current_tool_link+')'
    if current_edit_kind=='billboard':
        return (format_billboard_saved_status(current_receipt_record) if current_receipt_record['saved'] else '공용 속성이 저장되지 않음')+current_target_notice+'  \n[해당 도구 열기]('+current_tool_link+')'
    if current_edit_kind=='effect':
        return (format_effect_saved_status(current_receipt_record) if current_receipt_record['saved'] else '이펙트가 저장되지 않음')+current_target_notice+'  \n[해당 도구 열기]('+current_tool_link+')'
    return ('저장 완료' if current_receipt_record.get('saved') else '저장되지 않음 · 변경 여부 확인 필요')+' · 원본과 소비자 상태를 확인하세요.'+current_target_notice+'  \n[해당 도구 열기]('+current_tool_link+')'


def submit_conversation_edit_review(current_card_record,current_session_identifier,current_source_job_identifier,current_edit_kind):
    import json
    if not isinstance(current_card_record,dict) or current_card_record.get('ready') is not True or (current_card_record.get('session_id'),current_card_record.get('source_job_id'),current_card_record.get('kind'))!=(current_session_identifier,current_source_job_identifier,current_edit_kind):
        raise gr.Error('세션이나 제안이 바뀌었습니다. 다시 검토하세요.')
    current_fresh_card,_,_,current_fresh_status=prepare_conversation_edit_review(current_session_identifier,current_source_job_identifier,current_edit_kind)
    if not current_fresh_card['ready']:return current_fresh_card,current_fresh_status
    if current_fresh_card['review']['draft']!=current_card_record['review']['draft']:
        raise gr.Error('제안이나 원본이 변경됐습니다. 다시 검토하세요.')
    current_save_functions={'billboard':save_hermes_billboard_edit_draft,'building':save_hermes_building_anchor_draft,'effect':save_hermes_effect_edit_draft,'field':save_hermes_field_map_draft,'city':save_hermes_city_map_draft,'sprite':save_hermes_sprite_anchor_draft}
    current_draft_text=json.dumps(current_card_record['review']['draft'],ensure_ascii=False)
    try:
        current_save_functions[current_edit_kind](current_card_record['review'],current_draft_text,current_card_record['request_id'])
    except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError,AttributeError):
        return {**current_card_record,'ready':False,'save_attempted':True},'저장 결과 확인 불가 · 원본과 같은 접수 ID의 이력을 확인하세요. 자동 재저장하지 않습니다.'
    current_card_record={**current_card_record,'ready':False,'save_attempted':True}
    try:current_result_text=read_conversation_edit_result(current_card_record,current_session_identifier,current_source_job_identifier,current_edit_kind)
    except Exception:current_result_text='저장 결과 확인 불가 · 같은 제안을 다시 열어 확인하세요. 자동 재저장하지 않습니다.'
    return current_card_record,current_result_text



def submit_confirmed_conversation_edit(current_confirmed_card,current_current_card,current_session_identifier,current_source_job_identifier,current_edit_kind):
    if not isinstance(current_confirmed_card,dict) or current_confirmed_card!=current_current_card:
        raise gr.Error('확인 중 변경 대상이나 검토 내용이 바뀌었습니다. 다시 검토하세요.')
    return submit_conversation_edit_review(current_current_card,current_session_identifier,current_source_job_identifier,current_edit_kind)



def read_conversation_capture_review(current_session_identifier,current_source_job_identifier):
    """선택한 완료 작업의 캡처 설정과 맵 등록 상태만 조회한다."""
    from tools.review.domains.hermes_agent.capture_delegation import normalize_capture_delegation_request
    find_conversation_session_job(current_session_identifier,current_source_job_identifier)
    current_response_record=execute_remote_management_command('hermes-agent','hermes-capture-proposal',{'id':current_source_job_identifier})
    if not isinstance(current_response_record,dict) or current_response_record.get('job_id')!=current_source_job_identifier or not isinstance(current_response_record.get('proposal'),dict):
        raise ValueError('캡처 제안 응답 오류')
    current_proposal_record=current_response_record['proposal']
    if set(current_proposal_record)!={'service','settings'} or normalize_capture_delegation_request(current_proposal_record['service'],current_proposal_record['settings'])!=current_proposal_record['settings']:
        raise ValueError('캡처 제안 설정 오류')
    current_registration_record=current_response_record.get('map_registration')
    if not isinstance(current_registration_record,dict):raise ValueError('맵 등록 상태 오류')
    if current_proposal_record['service']=='map-review':
        if set(current_registration_record)!={'status','map'} or current_registration_record['map']!=current_proposal_record['settings']['map'] or current_registration_record['status'] not in ('registered','not_registered','unavailable'):
            raise ValueError('맵 등록 상태 불일치')
        current_registration_text={'registered':'등록된 맵','not_registered':'등록 맵 목록에 없음','unavailable':'등록 여부 확인 불가'}[current_registration_record['status']]
    elif current_registration_record=={'status':'not_applicable'}:
        current_registration_text='캐릭터 표현 검수 화면은 폐기됐습니다.'
    else:
        raise ValueError('캡처 서비스 상태 불일치')
    current_navigation_text=''
    if current_proposal_record['service']=='map-review' and current_registration_record['status']=='registered':
        from urllib.parse import urlencode
        current_link_parameters={'map':current_registration_record['map'],'townPage':'1'}
        if isinstance(current_session_identifier,str) and re.fullmatch(r'[a-f0-9]{32}',current_session_identifier):
            current_link_parameters['session']=current_session_identifier
        current_navigation_text='\n\n[이 맵의 검수 화면 열기](/management/frame/map-review/?'+urlencode(current_link_parameters)+')'
    return '캡처 제안 검토 · '+current_registration_text+'\n\n'+format_capture_settings_for_conversation(current_proposal_record['settings'])+current_navigation_text+'\n\n캡처 실행은 지원하지 않으며 GPU 여유나 결과 품질도 확인하지 않았습니다.'


def route_conversation_proposal(current_session_identifier,current_source_job_identifier):
    """완료 답변의 단일 검증 제안에 맞는 검토 영역만 연다. 실행하지 않는다."""
    current_unchanged=(gr.update(),gr.update(),gr.update(),gr.update(),gr.update(),gr.update())
    try:
        from tools.review.domains.hermes_agent import delegation_proposal
        current_match_record=find_conversation_session_job(current_session_identifier,current_source_job_identifier)
        current_job_record=current_match_record.get('job') or {}
        current_answer_text=current_job_record.get('final_response')
        if not isinstance(current_answer_text,str) or current_job_record.get('final_response_truncated') is not False:
            return (*current_unchanged,None,'완료 답변 전체를 확인할 수 없습니다. 작업 상세를 확인하세요.')
        current_markers=re.findall(r'(?m)^HERMES_(KIMODO|FLUX|TRANSLATION|AUDIO|VIDEO|WRITER|FIELD|CITY|EFFECT|BILLBOARD|BUILDING|SPRITE|MODEL_PREPARATION|KIMODO_RESUME|FLUX_RESUME|VIDEO_RESUME|CAPTURE)_PROPOSAL[ \t]*$',current_answer_text)
        if len(current_markers)!=1:
            return (*current_unchanged,None,'실행 가능한 단일 제안을 확인하지 못했습니다. 대화 응답과 작업 상세를 확인하세요.')
        current_kind_value=current_markers[0].lower()
        current_parser_value=getattr(delegation_proposal,'parse_hermes_'+current_kind_value+'_proposal')
        current_proposal_value=current_parser_value(current_answer_text)
        if not isinstance(current_proposal_value,dict):raise ValueError('제안 형식 오류')
        current_area_value='service'
        current_service_kind=current_kind_value
        current_edit_kind=gr.update()
        if current_kind_value in ('field','city','effect','billboard','building','sprite'):
            current_area_value='edit'
            current_service_kind=gr.update()
            current_edit_kind=current_kind_value
        elif current_kind_value=='capture':
            current_area_value='capture'
            current_service_kind=gr.update()
        elif current_kind_value=='video':
            current_area_value='video'
            current_service_kind=gr.update()
        elif current_kind_value=='flux' and current_proposal_value.get('service') in ('flux-mannequin','flux-billboard','flux-building','flux-expression'):
            current_area_value='image'
            current_service_kind=gr.update()
        current_route_record={'session_id':current_session_identifier,'job_id':current_source_job_identifier,'area':current_area_value,'kind':current_kind_value,'nonce':uuid.uuid4().hex}
        return (gr.update(open=current_area_value=='service'),gr.update(open=current_area_value=='edit'),gr.update(open=current_area_value=='image'),gr.update(open=current_area_value=='video'),current_service_kind,current_edit_kind,current_route_record,'제안을 확인하고 있습니다.')
    except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError,AttributeError):
        return (*current_unchanged,None,'선택한 작업의 제안을 확인할 수 없습니다. 세션과 작업 상태를 확인하세요.')


def open_routed_conversation_proposal(current_route_record,current_session_identifier,current_source_job_identifier):
    """선택과 제안을 다시 확인해 해당 검토 내용을 불러온다. 접수·저장은 하지 않는다."""
    current_outputs=[gr.skip() for _ in range(24)]
    if current_route_record is None:return tuple(current_outputs)
    if not isinstance(current_route_record,dict) or (current_route_record.get('session_id'),current_route_record.get('job_id'))!=(current_session_identifier,current_source_job_identifier):
        current_outputs[-1]='세션이나 작업이 바뀌었습니다. 제안을 다시 찾으세요.'
        return tuple(current_outputs)
    current_area_value=current_route_record.get('area')
    current_kind_value=current_route_record.get('kind')
    try:
        if current_area_value=='capture' and current_kind_value=='capture':
            current_outputs[-1]='캡처 제안과 맵 등록 상태를 확인하고 있습니다.'
            return tuple(current_outputs)
        if current_area_value=='service' and current_kind_value in ('kimodo','flux','translation','audio','writer','model_preparation','kimodo_resume','flux_resume','video_resume'):
            current_outputs[0:3]=prepare_conversation_service_review(current_session_identifier,current_source_job_identifier,current_kind_value)
        elif current_area_value=='edit' and current_kind_value in ('billboard','building','effect','field','sprite','city'):
            current_outputs[3:7]=prepare_conversation_edit_review(current_session_identifier,current_source_job_identifier,current_kind_value)
        elif current_area_value=='image' and current_kind_value=='flux':
            current_outputs[7:13]=open_conversation_flux_reference(current_session_identifier,current_source_job_identifier)
        elif current_area_value=='video' and current_kind_value=='video':
            current_outputs[13:23]=open_conversation_video_proposal(current_session_identifier,current_source_job_identifier)
        else:
            raise ValueError('제안 연결 오류')
        current_outputs[-1]='아래에 불러온 제안과 필요한 입력을 확인하세요.'
    except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError,AttributeError):
        if current_area_value=='service':current_outputs[0:3]=[None,'','제안을 확인하지 못했습니다. 작업과 접수 상태를 확인하세요.']
        elif current_area_value=='edit':current_outputs[3:7]=[None,'',None,'변경 제안을 확인하지 못했습니다. 원본과 작업 상태를 확인하세요.']
        elif current_area_value=='image':current_outputs[7:13]=[None,None,None,None,'','첨부 제안을 확인하지 못했습니다. 작업과 접수 상태를 확인하세요.']
        elif current_area_value=='video':current_outputs[13:23]=[None,'{}',None,None,None,None,None,None,'','영상 제안을 확인하지 못했습니다. 작업과 접수 상태를 확인하세요.']
        current_outputs[-1]='제안을 불러오지 못했습니다. 아래 안내와 작업 상태를 확인하세요.'
    return tuple(current_outputs)


def collect_routed_capture_review(current_route_record,current_session_identifier,current_source_job_identifier):
    """캡처 조회 결과를 요청 신원과 묶어 늦은 응답을 구분한다."""
    if not isinstance(current_route_record,dict) or (current_route_record.get('session_id'),current_route_record.get('job_id'),current_route_record.get('area'))!=(current_session_identifier,current_source_job_identifier,'capture'):
        return None
    try:
        current_notice_text=read_conversation_capture_review(current_session_identifier,current_source_job_identifier)
    except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError,AttributeError):
        current_notice_text='캡처 제안을 확인하지 못했습니다. 선택한 작업과 맵 등록 상태를 확인하세요.'
    return {'route':current_route_record,'notice':current_notice_text}


def render_routed_capture_review(current_route_record,current_session_identifier,current_source_job_identifier,current_result_record):
    """현재 작업과 같은 조회만 대화에 표시한다."""
    if not isinstance(current_result_record,dict) or current_result_record.get('route')!=current_route_record or not isinstance(current_route_record,dict) or (current_route_record.get('session_id'),current_route_record.get('job_id'),current_route_record.get('area'))!=(current_session_identifier,current_source_job_identifier,'capture') or not isinstance(current_result_record.get('notice'),str):
        return gr.skip()
    return current_result_record['notice']


def open_conversation_flux_reference_safely(current_session_identifier,current_source_job_identifier):
    """제안 열기에 실패해도 이전 첨부와 검토를 지운다."""
    try:
        current_result_values=open_conversation_flux_reference(current_session_identifier,current_source_job_identifier)
    except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError,AttributeError):
        current_result_values=(None,None,None,None,'','첨부 제안을 확인하지 못했습니다. 작업과 접수 상태를 확인하세요.')
    return (*current_result_values,gr.update(interactive=False))


def open_conversation_video_proposal_safely(current_session_identifier,current_source_job_identifier):
    """제안 열기에 실패해도 이전 영상 입력과 검토를 지운다."""
    try:
        current_result_values=open_conversation_video_proposal(current_session_identifier,current_source_job_identifier)
    except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError,AttributeError):
        current_result_values=(None,'{}',None,None,None,None,None,None,'','영상 제안을 확인하지 못했습니다. 작업과 접수 상태를 확인하세요.')
    return (*current_result_values,gr.update(interactive=False))


def read_hermes_legacy_anchor_page(current_animation_identifier,current_animation_version,current_page_state=None,current_next_page=False):
    """과거 좌표 검수의 경로 없는 이력만 페이지별로 표시한다."""
    current_payload_record={'animation_id':current_animation_identifier,'animation_version':current_animation_version,'limit':20}
    if current_next_page:
        if not isinstance(current_page_state,dict) or (current_page_state.get('animation_id'),current_page_state.get('animation_version'))!=(current_animation_identifier,current_animation_version) or type(current_page_state.get('offset')) is not int or not isinstance(current_page_state.get('snapshot'),str):
            return [],'검색 조건이 바뀌었습니다. 처음부터 조회하세요.',None,gr.update(interactive=False)
        current_payload_record.update(offset=current_page_state['offset'],snapshot=current_page_state['snapshot'])
    try:
        current_result_record=execute_remote_management_command('hermes-agent','hermes-anchor-history-observe',current_payload_record)
        if not isinstance(current_result_record,dict) or not isinstance(current_result_record.get('records'),list) or type(current_result_record.get('total')) is not int:raise ValueError('이력 형식 오류')
        current_rows_value=[]
        for current_entry_value in current_result_record['records']:
            if not isinstance(current_entry_value,dict) or not isinstance(current_entry_value.get('id'),str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_entry_value['id']) or not isinstance(current_entry_value.get('created_at'),str) or type(current_entry_value.get('frames')) is not int:raise ValueError('이력 항목 오류')
            current_rows_value.append([current_entry_value['id'],current_entry_value['created_at'],current_entry_value['frames']])
        current_snapshot_value=current_result_record.get('snapshot')
        current_offset_value=current_payload_record.get('offset',0)
        current_next_offset=current_result_record.get('next_offset')
        if current_result_record.get('offset')!=current_offset_value or not isinstance(current_snapshot_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_snapshot_value) or (current_next_page and current_snapshot_value!=current_page_state['snapshot']):raise ValueError('이력 버전 오류')
        if current_next_offset is not None and (type(current_next_offset) is not int or current_next_offset!=current_offset_value+len(current_rows_value) or current_next_offset<=current_offset_value):raise ValueError('이력 페이지 오류')
        current_next_state={'animation_id':current_animation_identifier,'animation_version':current_animation_version,'offset':current_next_offset,'snapshot':current_snapshot_value} if current_next_offset is not None else None
        return current_rows_value,'과거 좌표 검수 '+str(current_result_record['total'])+'건 · 대상 '+current_animation_identifier+' / '+current_animation_version+' · 현재 등록 앵커와 별도입니다.',current_next_state,gr.update(interactive=current_next_state is not None)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError):
        return [],'과거 앵커 이력을 확인할 수 없거나 변경됐습니다. 처음부터 조회하세요.',None,gr.update(interactive=False)


def read_next_hermes_legacy_anchor_page(current_animation_identifier,current_animation_version,current_page_state):
    return read_hermes_legacy_anchor_page(current_animation_identifier,current_animation_version,current_page_state,True)


def collect_hermes_legacy_anchor_page(current_animation_identifier,current_animation_version,current_page_state,current_request_token,current_next_page):
    return {'animation_id':current_animation_identifier,'animation_version':current_animation_version,'token':current_request_token,'values':read_hermes_legacy_anchor_page(current_animation_identifier,current_animation_version,current_page_state,current_next_page)}


def render_hermes_legacy_anchor_page(current_animation_identifier,current_animation_version,current_request_token,current_result_record):
    if not isinstance(current_result_record,dict) or (current_result_record.get('animation_id'),current_result_record.get('animation_version'),current_result_record.get('token'))!=(current_animation_identifier,current_animation_version,current_request_token):
        return gr.skip(),gr.skip(),gr.skip(),gr.skip()
    return current_result_record['values']


def read_conversation_expression_catalog(current_query_text,current_page_state=None,current_next_page=False):
    """대화에 등록 표정의 ID와 한국어 이름을 페이지별로 표시한다."""
    current_query_value=current_query_text or ''
    current_payload_record={'query':current_query_value,'limit':20}
    if current_next_page:
        if not isinstance(current_page_state,dict) or current_page_state.get('query')!=current_query_value or type(current_page_state.get('offset')) is not int or not isinstance(current_page_state.get('snapshot'),str):
            return [],'검색 조건이 바뀌었습니다. 처음부터 조회하세요.',None,gr.update(interactive=False)
        current_payload_record.update(offset=current_page_state['offset'],snapshot=current_page_state['snapshot'])
    try:
        current_result_record=execute_remote_management_command('hermes-agent','hermes-expression-catalog',current_payload_record)
        if not isinstance(current_result_record,dict) or not isinstance(current_result_record.get('records'),list) or type(current_result_record.get('total')) is not int:raise ValueError('목록 오류')
        current_rows_value=[]
        for current_entry_value in current_result_record['records']:
            if not isinstance(current_entry_value,dict) or set(current_entry_value)!={'id','label'} or not isinstance(current_entry_value['id'],str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}',current_entry_value['id']) or not isinstance(current_entry_value['label'],str):raise ValueError('표정 항목 오류')
            current_rows_value.append([current_entry_value['label'],current_entry_value['id']])
        current_snapshot_value=current_result_record.get('snapshot')
        current_next_offset=current_result_record.get('next_offset')
        current_expected_offset=current_payload_record.get('offset',0)
        if current_result_record.get('offset')!=current_expected_offset or not isinstance(current_snapshot_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_snapshot_value) or (current_next_page and current_snapshot_value!=current_page_state['snapshot']):raise ValueError('목록 버전 오류')
        if current_next_offset is not None and (type(current_next_offset) is not int or current_next_offset!=current_expected_offset+len(current_rows_value) or current_next_offset<=current_expected_offset):raise ValueError('페이지 오류')
        current_next_state={'query':current_query_value,'offset':current_next_offset,'snapshot':current_snapshot_value} if current_next_offset is not None else None
        return current_rows_value,'등록 표정 '+str(current_result_record['total'])+'개 · 목록의 이름과 ID만 표시합니다.',current_next_state,gr.update(interactive=current_next_state is not None)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError):
        return [],'표정 목록을 확인할 수 없거나 변경됐습니다. 처음부터 다시 조회하세요.',None,gr.update(interactive=False)


def read_next_conversation_expression_catalog(current_query_text,current_page_state):
    return read_conversation_expression_catalog(current_query_text,current_page_state,True)


def open_conversation_flux_reference(current_session_identifier,current_source_job_identifier):
    """검증된 참조 필수 프로필 제안과 기존 접수만 확인한다."""
    import hashlib
    find_conversation_session_job(current_session_identifier,current_source_job_identifier)
    current_proposal_record=read_matching_hermes_edit_proposal(current_source_job_identifier,'hermes-flux-proposal')
    if not isinstance(current_proposal_record,dict) or current_proposal_record.get('service') not in ('flux-mannequin','flux-billboard','flux-building','flux-expression'):
        raise gr.Error('첫 참조가 필요한 FLUX 프로필 제안을 선택하세요.')
    current_service_name=current_proposal_record['service']
    current_request_identifier='chat_'+hashlib.sha256((current_session_identifier+':'+current_source_job_identifier+':flux').encode()).hexdigest()
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-service-receipt',{'request_id':current_request_identifier,'service':current_service_name})
    if not isinstance(current_receipt_record,dict) or current_receipt_record.get('request_id')!=current_request_identifier or current_receipt_record.get('state') not in ('not_found','unknown','accepted'):
        raise gr.Error('기존 접수 상태를 확인할 수 없습니다.')
    if current_receipt_record.get('service')!=current_service_name:
        raise gr.Error('접수 서비스가 일치하지 않습니다.')
    current_source_record={'session_id':current_session_identifier,'source_job_id':current_source_job_identifier,'proposal':current_proposal_record,'request_id':current_request_identifier}
    current_state_label={'not_found':'아직 접수하지 않았습니다. 첫 참조 이미지를 첨부하고 검토하세요.','unknown':'접수 결과 확인 필요 · 자동 재접수하지 않습니다.','accepted':'기존 접수가 있습니다. 상태와 결과를 확인하세요.'}[current_receipt_record['state']]
    current_proposal_label=current_service_name+' · '+current_state_label
    if current_service_name=='flux-expression':
        from tools.review.domains.image.expression_generation import load_expression_configuration
        current_expression_value=next((item for item in load_expression_configuration()['expressions'] if item['id']==current_proposal_record.get('prompt')),None)
        if not current_expression_value:raise gr.Error('등록된 표정을 확인할 수 없습니다.')
        current_proposal_label+=' · 표정: '+current_expression_value['label_ko']+' ('+current_expression_value['id']+')'
    return current_source_record,None,None,None,'',current_proposal_label


def review_conversation_flux_reference(current_source_record,current_session_identifier,current_source_job_identifier,current_first_image,current_second_image):
    if not isinstance(current_source_record,dict) or (current_source_record.get('session_id'),current_source_record.get('source_job_id'))!=(current_session_identifier,current_source_job_identifier):raise gr.Error('세션이나 작업이 바뀌었습니다. 제안을 다시 여세요.')
    current_fresh_source,_,_,_,_,_=open_conversation_flux_reference(current_session_identifier,current_source_job_identifier)
    if current_fresh_source!=current_source_record:raise gr.Error('제안이 바뀌었습니다. 다시 확인하세요.')
    current_proposal_record=current_source_record['proposal']
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-service-receipt',{'request_id':current_source_record['request_id'],'service':current_proposal_record['service']})
    if not isinstance(current_receipt_record,dict) or current_receipt_record.get('request_id')!=current_source_record['request_id'] or current_receipt_record.get('service')!=current_proposal_record['service'] or current_receipt_record.get('state')!='not_found':return None,'','기존 접수 또는 확인이 필요한 기록이 있습니다. 상태를 확인하세요.'
    if current_proposal_record['service']=='flux-expression':
        if current_second_image is not None:raise gr.Error('표정 생성은 얼굴 참조 이미지 한 장만 사용합니다.')
        current_review_record,current_preview_text,current_status_text,_=review_hermes_flux_expression_request(current_first_image,current_proposal_record['prompt'],'',current_proposal_record['width'],current_proposal_record['height'],current_proposal_record['seed'],current_source_record['request_id'])
    else:
        current_review_record,current_preview_text,current_status_text,_=review_hermes_flux_profile_request(current_proposal_record['service'],current_proposal_record['prompt'],current_proposal_record['width'],current_proposal_record['height'],current_proposal_record['seed'],current_first_image,current_second_image,current_source_record['request_id'])
    if not current_review_record:raise gr.Error(current_status_text)
    return {'source':current_source_record,'review':current_review_record},current_preview_text,current_status_text


def submit_conversation_flux_reference(current_review_record,current_source_record,current_session_identifier,current_source_job_identifier,current_first_image,current_second_image):
    if not isinstance(current_review_record,dict) or current_review_record.get('source')!=current_source_record:raise gr.Error('제안이나 첨부가 바뀌었습니다. 다시 검토하세요.')
    current_rechecked_record,_,current_status_text=review_conversation_flux_reference(current_source_record,current_session_identifier,current_source_job_identifier,current_first_image,current_second_image)
    if current_rechecked_record is None:return None,current_status_text
    if current_rechecked_record!=current_review_record:raise gr.Error('참조 이미지나 제안이 바뀌었습니다. 다시 검토하세요.')
    try:
        current_result_record=execute_remote_management_command('hermes-agent','hermes-delegate-flux-profile',current_review_record['review'])
    except (OSError,ValueError,TypeError,RuntimeError):
        return None,'접수 결과 확인 필요 · 원 서비스와 이력을 확인하세요. 자동 재접수하지 않습니다.'
    if not isinstance(current_result_record,dict) or current_result_record.get('state') not in ('accepted','unknown') or current_result_record.get('service')!=current_source_record['proposal']['service']:
        return None,'접수 응답을 확인할 수 없습니다. 원 서비스와 이력을 확인하세요. 자동 재접수하지 않습니다.'
    if current_result_record['state']=='unknown':return None,'접수 결과 확인 필요 · 원 서비스와 이력을 확인하세요. 자동 재접수하지 않습니다.'
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    if not validate_service_job_identifier(current_source_record['proposal']['service'],current_result_record.get('job_id')):return None,'접수 작업 ID 확인 필요 · 원 서비스와 이력을 확인하세요. 자동 재접수하지 않습니다.'
    try:
        current_confirmed_job,current_status_text=read_hermes_flux_profile_result(current_source_record['request_id'],current_source_record['proposal']['service'],current_session_identifier)
        if current_confirmed_job!=current_result_record['job_id']:raise ValueError('접수 작업 불일치')
    except Exception:
        return None,'접수 결과 확인 필요 · 같은 접수 ID와 원 서비스 이력을 확인하세요. 자동 재접수하지 않습니다.'
    return None,'생성 접수 기록 확인 · '+current_status_text+' · 생성은 에셋 채택이나 품질 승인을 뜻하지 않습니다.'


def read_conversation_flux_reference(current_source_record,current_session_identifier,current_source_job_identifier):
    if not isinstance(current_source_record,dict) or (current_source_record.get('session_id'),current_source_record.get('source_job_id'))!=(current_session_identifier,current_source_job_identifier):raise gr.Error('세션이나 작업이 바뀌었습니다. 제안을 다시 여세요.')
    try:
        _,current_status_text=read_hermes_flux_profile_result(current_source_record['request_id'],current_source_record['proposal']['service'],current_session_identifier)
    except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError):
        return '접수 ID·서비스 또는 결과를 확인할 수 없습니다. 원 서비스와 접수 이력을 확인하고 자동 재접수하지 마세요.'
    return current_status_text


def open_conversation_video_proposal(current_session_identifier,current_source_job_identifier):
    """선택된 세션의 영상 제안을 첨부 없이 열고 기존 접수를 먼저 확인한다."""
    import hashlib
    import json
    if not current_session_identifier or not current_source_job_identifier:
        raise gr.Error('세션과 제안을 만든 작업을 선택하세요.')
    find_conversation_session_job(current_session_identifier,current_source_job_identifier)
    current_proposal_record=read_matching_hermes_edit_proposal(current_source_job_identifier,'hermes-video-proposal')
    current_service_name=current_proposal_record['service']
    current_mode_name=current_proposal_record['mode']
    current_settings_record=json.loads(default_hermes_video_settings(current_service_name))
    if current_service_name!='dwpose':current_settings_record['prompt']=current_proposal_record['prompt']
    if current_service_name=='wan22-vace':current_settings_record['mode']=current_mode_name
    if current_service_name=='wan22-fun-control':
        current_settings_record['control_type']='pose'
    current_request_identifier='chat_'+hashlib.sha256((current_session_identifier+':'+current_source_job_identifier+':video').encode()).hexdigest()
    current_source_record={'session_id':current_session_identifier,'source_job_id':current_source_job_identifier,'proposal':current_proposal_record,'request_id':current_request_identifier}
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-service-receipt',{'request_id':current_request_identifier,'service':current_service_name})
    if not isinstance(current_receipt_record,dict) or current_receipt_record.get('state') not in ('not_found','accepted','unknown'):raise gr.Error('영상 접수 상태를 확인할 수 없습니다.')
    current_receipt_state=current_receipt_record['state']
    if current_receipt_record.get('request_id')!=current_request_identifier or current_receipt_record.get('service')!=current_service_name:
        return None,'{}',None,None,None,None,None,None,'','접수 ID 또는 서비스를 확인할 수 없습니다. 원 서비스 이력을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_state=='accepted':
        from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
        if not validate_service_job_identifier(current_service_name,current_receipt_record.get('job_id')):raise gr.Error('영상 접수 작업을 확인할 수 없습니다.')
    current_status_text={'not_found':'아직 접수하지 않았습니다. 제안 모드에 필요한 첨부와 설정을 확인하세요.','unknown':'접수 결과 확인 필요 · 자동 재접수하지 않습니다.','accepted':'기존 접수가 있습니다. 영상 상태와 결과 확인 버튼으로 조회하세요.'}[current_receipt_state]
    current_notice_text='서비스: '+current_service_name+' · 제안 모드: '+current_mode_name+' · 프레임·단계 등은 기본값입니다. 필요한 첨부를 선택하고 검토하세요.'
    return current_source_record,json.dumps(current_settings_record,ensure_ascii=False,indent=2),None,None,None,None,None,None,'',current_notice_text+'  \n'+current_status_text


def read_conversation_video_receipt(current_source_record,current_session_identifier,current_source_job_identifier):
    if not isinstance(current_source_record,dict) or (current_source_record.get('session_id'),current_source_record.get('source_job_id'))!=(current_session_identifier,current_source_job_identifier):
        raise gr.Error('세션이나 작업이 바뀌었습니다. 제안을 다시 여세요.')
    _,current_status_text=read_hermes_video_result(current_source_record['request_id'],current_source_record['proposal']['service'],current_session_identifier)
    return current_status_text


def review_conversation_video_inputs(current_source_record,current_session_identifier,current_source_job_identifier,current_settings_text,current_image_files,current_driving_video,current_pose_video,current_edit_video,current_edit_mask):
    import json
    if not isinstance(current_source_record,dict) or (current_source_record.get('session_id'),current_source_record.get('source_job_id'))!=(current_session_identifier,current_source_job_identifier):
        raise gr.Error('세션이나 작업이 바뀌었습니다. 제안을 다시 여세요.')
    current_fresh_source,_,_,_,_,_,_,_,_,_=open_conversation_video_proposal(current_session_identifier,current_source_job_identifier)
    if current_fresh_source!=current_source_record:raise gr.Error('영상 제안이 바뀌었습니다. 다시 여세요.')
    current_service_name=current_source_record['proposal']['service']
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-service-receipt',{'request_id':current_source_record['request_id'],'service':current_service_name})
    if not isinstance(current_receipt_record,dict) or current_receipt_record.get('request_id')!=current_source_record['request_id'] or current_receipt_record.get('service')!=current_service_name:
        return None,'','영상 접수 ID와 서비스를 확인할 수 없습니다. 원 서비스 이력을 확인하세요.'
    if current_receipt_record.get('state')!='not_found':
        return None,'','기존 접수 또는 접수 확인 필요 기록이 있습니다. 영상 상태와 결과 확인 버튼으로 조회하세요.'
    current_settings_record=json.loads(current_settings_text)
    if current_service_name=='wan22-vace' and current_settings_record.get('mode')!=current_source_record['proposal']['mode']:
        raise gr.Error('제안된 영상 모드가 바뀌었습니다. 새 제안을 요청하세요.')
    if current_service_name=='wan22-fun-control':
        current_expected_control='pose'
        if current_settings_record.get('control_type')!=current_expected_control:raise gr.Error('제안된 제어 모드가 바뀌었습니다. 새 제안을 요청하세요.')
        current_proposed_mode=current_source_record['proposal']['mode']
        if (current_proposed_mode=='frames' and (current_pose_video is not None or current_driving_video is not None)) or (current_proposed_mode=='pose_video' and (current_pose_video is None or current_driving_video is not None)) or (current_proposed_mode=='driving_video' and (current_driving_video is None or current_pose_video is not None)):
            raise gr.Error('영상 첨부가 제안된 제어 모드와 일치하지 않습니다.')
    current_review_record,current_preview_text,current_status_text,_=review_hermes_video_request(current_service_name,current_settings_text,current_image_files,current_driving_video,current_pose_video,current_edit_video,current_edit_mask,current_source_record['request_id'])
    if not current_review_record:raise gr.Error(current_status_text)
    current_review_value={'source':current_source_record,'review':current_review_record}
    return current_review_value,current_preview_text+'  \n영상 설정: '+json.dumps(current_settings_record,ensure_ascii=False),current_status_text


def submit_conversation_video_inputs(current_review_value,current_source_record,current_session_identifier,current_source_job_identifier,current_settings_text,current_image_files,current_driving_video,current_pose_video,current_edit_video,current_edit_mask):
    if not isinstance(current_review_value,dict) or current_review_value.get('source')!=current_source_record:
        raise gr.Error('제안 또는 입력이 변경됐습니다. 다시 검토하세요.')
    current_rebuilt_review,_,current_status_text=review_conversation_video_inputs(current_source_record,current_session_identifier,current_source_job_identifier,current_settings_text,current_image_files,current_driving_video,current_pose_video,current_edit_video,current_edit_mask)
    if current_rebuilt_review is None:return None,current_status_text
    if current_rebuilt_review!=current_review_value:raise gr.Error('첨부나 설정이 바뀌었습니다. 다시 검토하세요.')
    try:
        current_result_record=execute_remote_management_command('hermes-agent','hermes-delegate-video',current_review_value['review'])
    except (gr.Error,OSError,ValueError,TypeError,RuntimeError):
        return None,'접수 결과 확인 불가 · 영상 도구와 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'
    if not isinstance(current_result_record,dict) or current_result_record.get('state') not in ('accepted','unknown'):
        return None,'접수 응답 확인 불가 · 영상 도구와 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'
    if current_result_record['state']=='unknown':
        return None,'접수 결과 확인 불가 · 영상 도구와 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    current_service_name=current_source_record['proposal']['service']
    if current_result_record.get('service')!=current_service_name or not validate_service_job_identifier(current_service_name,current_result_record.get('job_id')):
        return None,'접수 응답 확인 불가 · 영상 도구와 같은 접수 ID를 확인하세요. 자동 재접수하지 않습니다.'
    try:
        current_confirmed_job,current_status_text=read_hermes_video_result(current_source_record['request_id'],current_service_name,current_session_identifier)
        if current_confirmed_job!=current_result_record['job_id']:
            raise ValueError('접수 작업 불일치')
    except Exception:current_status_text='접수 결과 확인 불가 · 같은 제안의 상태를 확인하세요. 자동 재접수하지 않습니다.'
    return None,current_status_text


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
    try:current_result_record=execute_remote_management_command('hermes-agent','hermes-building-save',current_review_record)
    except (OSError,ValueError,TypeError,RuntimeError):
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    if not isinstance(current_result_record,dict) or current_result_record.get('request_id')!=current_request_identifier:
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    if current_result_record.get('state')=='unknown':return None,gr.update(visible=False),'저장 결과 확인 필요 · 원본과 접수를 확인하세요. 자동 재접수하지 않습니다.'
    if current_result_record.get('state')!='completed' or current_result_record.get('saved') is not True:
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    return None,gr.update(visible=False),format_building_anchor_saved_status(current_result_record)


def invalidate_hermes_building_review():
    """화면의 입력이 바뀌면 이전 확인을 즉시 해제한다."""
    return None,None,gr.update(visible=False),'입력 또는 검색 조건이 변경됐습니다. 다시 검토하세요.'


def matches_hermes_edit_receipt(current_receipt_record,current_request_identifier):
    """저장 이력의 접수 식별과 완료 결과를 함께 확인한다."""
    if not isinstance(current_receipt_record,dict):return False
    current_state_value=current_receipt_record.get('state')
    if current_state_value=='not_found':return True
    if current_receipt_record.get('request_id')!=current_request_identifier:return False
    if current_state_value=='unknown':return current_receipt_record.get('saved') is None
    return current_state_value=='completed' and current_receipt_record.get('saved') is True


def format_building_anchor_saved_status(current_receipt_record):
    """저장 응답 당시 원장 상태와 현재 확인할 항목을 구분한다."""
    current_status_text='건물 공용 앵커 DB 저장 완료'
    current_generation_value=current_receipt_record.get('generation')
    if current_receipt_record.get('ledger_status_at_save')=='pending' and type(current_generation_value) is int and current_generation_value>=1:
        current_status_text+=' · 저장 당시 원장 반영 대기 · DB 세대 '+str(current_generation_value)
    return current_status_text+' · 현재 원장 동기화와 사용 맵·게임 외형을 확인하세요.'


def read_hermes_building_anchor_status(current_request_identifier):
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-building-receipt',{'request_id':current_request_identifier})
    if not matches_hermes_edit_receipt(current_receipt_record,current_request_identifier):return '저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_record.get('state')=='completed':return format_building_anchor_saved_status(current_receipt_record)
    return {'not_found':'접수 기록이 없습니다. 저장을 시도했다면 원본을 확인하고 자동 재접수하지 마세요.','unknown':'저장 결과 확인 필요 · 원본과 접수를 확인하세요.'}.get(current_receipt_record.get('state'),'저장 상태를 확인할 수 없습니다.')


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



def read_matching_hermes_edit_proposal(current_job_identifier,current_command_name):
    if not current_job_identifier:
        raise gr.Error('먼저 세션 작업을 선택하세요.')
    current_response_record=execute_remote_management_command('hermes-agent',current_command_name,{'id':current_job_identifier})
    if not isinstance(current_response_record,dict) or current_response_record.get('job_id')!=current_job_identifier or not isinstance(current_response_record.get('proposal'),dict):
        raise gr.Error('선택한 작업의 제안을 확인하지 못했습니다. 다시 조회하세요.')
    return current_response_record['proposal']


def load_hermes_sprite_anchor_proposal(current_job_identifier):
    """완료된 제안의 기준 해시가 현재 시트와 일치할 때 초안으로 불러온다."""
    import json
    current_proposal_record=read_matching_hermes_edit_proposal(current_job_identifier,'hermes-sprite-proposal')
    current_detail_record=execute_remote_management_command('hermes-agent','hermes-sprite-detail',{'path':current_proposal_record['path'],'offset':0,'limit':20})
    if current_detail_record.get('path')!=current_proposal_record['path'] or current_detail_record.get('snapshot')!=current_proposal_record['snapshot'] or not current_detail_record.get('metadata_sha256'):
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
    try:current_result_record=execute_remote_management_command('hermes-agent','hermes-sprite-save',current_review_record)
    except (OSError,ValueError,TypeError,RuntimeError):
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    if not isinstance(current_result_record,dict) or current_result_record.get('request_id')!=current_request_identifier:
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    if current_result_record.get('state')=='unknown':return None,gr.update(visible=False),'저장 결과 확인 필요 · 에셋과 잠금 목록을 확인하고 자동 재접수하지 마세요.'
    if current_result_record.get('state')=='blocked':
        current_block_messages={'pending':'이전에 중단된 저장이 있습니다. 스프라이트 저장 중단 상태와 백업을 확인하세요.','busy':'다른 스프라이트 저장이 진행 중입니다. 완료 후 다시 검토하세요.','unavailable':'스프라이트 저장 상태를 확인할 수 없습니다. 원본과 잠금을 확인하세요.'}
        if current_result_record.get('saved') is not False or current_result_record.get('path')!=current_draft_record.get('path') or current_result_record.get('reason') not in current_block_messages:
            return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
        return None,gr.update(visible=False),'저장 접수 전 차단 · '+current_block_messages[current_result_record['reason']]
    if current_result_record.get('state')!='completed' or current_result_record.get('saved') is not True:
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    return None,gr.update(visible=False),'시트·메타데이터·등록부·프런트 잠금 저장 완료 · 원본과 재생을 다시 확인하세요.'


def read_hermes_sprite_pending_status_for_review():
    return execute_remote_management_command('hermes-agent','hermes-sprite-pending-status',{})


def read_hermes_sprite_anchor_status(current_request_identifier):
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-sprite-receipt',{'request_id':current_request_identifier})
    if not matches_hermes_edit_receipt(current_receipt_record,current_request_identifier):return '저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_record.get('state')=='not_found':return '스프라이트 저장 접수 기록이 없습니다. 저장을 시도했다면 원본을 확인하고 자동 재접수하지 마세요.'
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
    current_proposal_record=read_matching_hermes_edit_proposal(current_job_identifier,'hermes-effect-proposal')
    current_detail_record=execute_remote_management_command('hermes-agent','hermes-effect-detail',{'id':current_proposal_record['id']})
    if current_detail_record.get('id')!=current_proposal_record['id'] or current_detail_record['revision']!=current_proposal_record['revision']:
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
    try:current_result_record=execute_remote_management_command('hermes-agent','hermes-effect-save',current_review_record)
    except (OSError,ValueError,TypeError,RuntimeError):
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    if not isinstance(current_result_record,dict) or current_result_record.get('request_id')!=current_request_identifier:
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    if current_result_record.get('state')=='unknown':
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 원장을 확인하고 자동 재접수하지 마세요.'
    if current_result_record.get('state')!='completed' or current_result_record.get('saved') is not True:
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    return None,gr.update(visible=False),format_effect_saved_status(current_result_record)


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
    try:current_result_record=execute_remote_management_command('hermes-agent','hermes-effect-register',current_review_record)
    except (OSError,ValueError,TypeError,RuntimeError):
        return None,gr.update(visible=False),'등록 결과 확인 필요 · 같은 접수 ID와 원장을 확인하고 자동 재접수하지 마세요.'
    if not isinstance(current_result_record,dict):
        return None,gr.update(visible=False),'등록 결과 확인 필요 · 같은 접수 ID와 원장을 확인하고 자동 재접수하지 마세요.'
    if current_result_record.get('state')=='unknown':
        return None,gr.update(visible=False),'등록 결과 확인 필요 · 원장과 접수 기록을 확인하고 자동 재등록하지 마세요.'
    if current_result_record.get('state')!='completed' or current_result_record.get('request_id')!=current_request_identifier or current_result_record.get('id')!=current_draft_record.get('id') or type(current_result_record.get('generation')) is not int or current_result_record['generation']<1:
        return None,gr.update(visible=False),'등록 결과 확인 필요 · 같은 접수 ID와 원장을 확인하고 자동 재등록하지 마세요.'
    return None,gr.update(visible=False),'DB 등록 완료 · 세대 '+str(current_result_record.get('generation','확인 필요'))+' · 현재 원장 반영 상태와 게임 참조를 확인하세요.'


def matches_hermes_registration_receipt(current_receipt_record,current_request_identifier):
    """등록·교체 이력의 접수 ID와 결과를 검증한다."""
    from tools.review.domains.hermes_agent.effect_operations import EFFECT_IDENTIFIER_PATTERN
    if not isinstance(current_receipt_record,dict):return False
    current_state_value=current_receipt_record.get('state')
    if current_state_value=='not_found':return True
    if current_receipt_record.get('request_id')!=current_request_identifier:return False
    if current_state_value=='unknown':return True
    current_effect_value=current_receipt_record.get('id')
    return current_state_value=='completed' and isinstance(current_effect_value,str) and bool(EFFECT_IDENTIFIER_PATTERN.fullmatch(current_effect_value))


def read_hermes_effect_registration_status(current_request_identifier):
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-effect-register-receipt',{'request_id':current_request_identifier})
    if not matches_hermes_registration_receipt(current_receipt_record,current_request_identifier):return '접수 결과 확인 필요 · 같은 접수 ID와 원장을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_record.get('state')=='not_found':return '접수 기록이 없습니다. 실행을 시도했다면 원장을 확인하고 자동 재접수하지 마세요.'
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
    try:current_result_record=execute_remote_management_command('hermes-agent','hermes-waypoint-replace',current_review_record)
    except (OSError,ValueError,TypeError,RuntimeError):
        return None,gr.update(visible=False),'교체 결과 확인 필요 · 같은 접수 ID와 원장을 확인하고 자동 재접수하지 마세요.'
    if not isinstance(current_result_record,dict):
        return None,gr.update(visible=False),'교체 결과 확인 필요 · 같은 접수 ID와 원장을 확인하고 자동 재접수하지 마세요.'
    if current_result_record.get('state')=='unknown':
        return None,gr.update(visible=False),'교체 결과 확인 필요 · 원장과 접수 기록을 확인하고 자동 재접수하지 마세요.'
    if current_result_record.get('state')!='completed' or current_result_record.get('request_id')!=current_request_identifier or current_result_record.get('id')!=current_draft_record['effect']['id']:
        return None,gr.update(visible=False),'교체 결과 확인 필요 · 같은 접수 ID와 원장을 확인하고 자동 재접수하지 마세요.'
    return None,gr.update(visible=False),'DB 교체 완료 · 세대 '+str(current_result_record.get('generation','확인 필요'))+' · 저장 시 원장 반영 대기 · 현재 원장 반영 상태와 사용 맵을 확인하세요.'


def read_hermes_waypoint_replacement_status(current_request_identifier):
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-waypoint-receipt',{'request_id':current_request_identifier})
    if not matches_hermes_registration_receipt(current_receipt_record,current_request_identifier):return '접수 결과 확인 필요 · 같은 접수 ID와 원장을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_record.get('state')=='not_found':return '접수 기록이 없습니다. 실행을 시도했다면 원장을 확인하고 자동 재접수하지 마세요.'
    return '교체 접수 상태: '+str(current_receipt_record.get('state','unknown'))+' · DB 세대: '+str(current_receipt_record.get('generation','확인 필요'))+' · 저장 시 원장 상태: '+str(current_receipt_record.get('ledger_status_at_save','확인 필요'))+' · 현재 원장 상태는 별도로 확인하세요. 응답이 불확실하면 재접수하지 마세요.'


def format_effect_saved_status(current_receipt_record):
    current_status_text='이펙트 좌표 DB 저장 완료'
    current_generation_value=current_receipt_record.get('generation')
    if current_receipt_record.get('ledger_status_at_save')=='pending' and type(current_generation_value) is int and current_generation_value>=1:
        current_status_text+=' · 저장 당시 원장 반영 대기 · DB 세대 '+str(current_generation_value)
    return current_status_text+' · 현재 원장과 사용 맵을 확인하세요.'


def read_hermes_effect_edit_status(current_request_identifier):
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-effect-receipt',{'request_id':current_request_identifier})
    if not matches_hermes_edit_receipt(current_receipt_record,current_request_identifier):return '저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_record.get('state')=='not_found':return '이펙트 저장 접수 기록이 없습니다. 저장을 시도했다면 원본을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_record.get('state')=='unknown':return '저장 결과 확인 필요 · 원장을 확인하고 자동 재접수하지 마세요.'
    return format_effect_saved_status(current_receipt_record) if current_receipt_record.get('saved') is True else '이펙트 저장 상태를 확인할 수 없습니다.'


def load_hermes_billboard_edit_draft(current_asset_identifier):
    """현재 공용 속성과 수정할 필드만 포함한 빈 초안을 불러온다."""
    import json
    current_source_record=execute_remote_management_command('hermes-agent','hermes-billboard-load',{'texture':current_asset_identifier})
    current_draft_record={'revision':current_source_record['revision'],'changes':[{'texture':current_source_record['texture'],'values':{}}]}
    return current_source_record['properties'],json.dumps(current_draft_record,ensure_ascii=False,indent=2),None,gr.update(visible=False),'수정할 공용 속성만 values에 입력하고 검증하세요.'



def load_hermes_billboard_edit_proposal(current_job_identifier):
    """현재 에셋의 선택된 속성이 제안의 관측값과 같을 때만 초안을 만든다."""
    import json
    current_proposal_record=read_matching_hermes_edit_proposal(current_job_identifier,'hermes-billboard-proposal')
    current_source_record=execute_remote_management_command('hermes-agent','hermes-billboard-load',{'texture':current_proposal_record['texture']})
    if current_source_record.get('texture')!=current_proposal_record['texture']:
        raise gr.Error('선택한 빌보드 원본을 확인하지 못했습니다. 다시 조회하세요.')
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
    try:current_result_record=execute_remote_management_command('hermes-agent','hermes-billboard-save',current_review_record)
    except (OSError,ValueError,TypeError,RuntimeError):
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    if not isinstance(current_result_record,dict) or current_result_record.get('request_id')!=current_request_identifier:
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    if current_result_record.get('state')=='unknown':
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 공용 속성과 원장을 확인하고 자동 재접수하지 마세요.'
    if current_result_record.get('state')!='completed' or current_result_record.get('saved') is not True:
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    return None,gr.update(visible=False),format_billboard_saved_status(current_result_record)


def format_billboard_saved_status(current_receipt_record):
    if current_receipt_record.get('ledger_status_at_save')=='pending':
        return '공용 속성 DB 저장 완료 · 저장 당시 원장 반영 대기 · 현재 원장과 사용 맵을 확인하세요.'
    return '공용 속성 저장 완료 · 원본과 사용 맵을 확인하세요.'


def read_hermes_billboard_edit_status(current_request_identifier):
    current_receipt_record=execute_remote_management_command('hermes-agent','hermes-billboard-receipt',{'request_id':current_request_identifier})
    if not matches_hermes_edit_receipt(current_receipt_record,current_request_identifier):return '저장 결과 확인 필요 · 같은 접수 ID와 원본을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_record.get('state')=='not_found':
        return '빌보드 저장 접수 기록이 없습니다. 저장을 시도했다면 원본을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_record.get('state')=='unknown':
        return '저장 결과 확인 필요 · 공용 속성과 원장을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_record.get('state')=='completed' and current_receipt_record.get('saved') is True:
        return format_billboard_saved_status(current_receipt_record)
    return '빌보드 저장 상태를 확인할 수 없습니다.'


def read_hermes_city_source_view(current_map_identifier):
    """편집 초안과 분리해 검증된 도시 에셋 원본을 표시한다."""
    try:
        current_source_record=execute_remote_management_command('hermes-agent','hermes-city-source',{'map':current_map_identifier})
        if (not isinstance(current_source_record,dict) or current_source_record.get('map')!=current_map_identifier
                or not isinstance(current_source_record.get('document'),dict)
                or current_source_record['document'].get('managementId')!='config.city-layouts.'+current_map_identifier
                or not isinstance(current_source_record['document'].get('data'),dict)
                or current_source_record['document']['data'].get('cityId')!=current_map_identifier
                or not isinstance(current_source_record.get('source_sha256'),str)
                or not re.fullmatch(r'[a-f0-9]{64}',current_source_record['source_sha256'])):
            raise ValueError('도시 원본 응답 오류')
        return current_source_record['document'],'에셋 원본 SHA-256: '+current_source_record['source_sha256']+' · DB 리비전과 실행 서비스 반영은 확인하지 않습니다.'
    except (OSError,ValueError,RuntimeError,KeyError,TypeError):
        return {},'도시 에셋 원본을 확인할 수 없습니다. 맵 ID·등록부·백엔드 잠금을 확인하세요.'


def load_hermes_city_map_draft(current_map_identifier):
    import json
    try:
        current_draft_value = execute_remote_management_command('hermes-agent','hermes-city-load',{'map':current_map_identifier})
        return json.dumps(current_draft_value,ensure_ascii=False,indent=2), None, gr.update(visible=False), '콘텐츠 DB 원장을 불러왔습니다. 수정하고 검증하세요.'
    except (OSError,ValueError,RuntimeError,KeyError,TypeError):
        return '', None, gr.update(visible=False), '도시 원장을 불러올 수 없습니다. 콘텐츠 DB 연결·인증과 도시 맵 ID를 확인하세요.'


def load_conversation_city_proposal(current_job_identifier):
    """현재 도시 원장의 정확한 기존 값에만 변경 제안을 적용한다."""
    import copy
    import json
    current_response=execute_remote_management_command('hermes-agent','hermes-city-proposal',{'id':current_job_identifier})
    if not isinstance(current_response,dict) or current_response.get('job_id')!=current_job_identifier or not isinstance(current_response.get('proposal'),dict):raise gr.Error('도시 제안을 확인할 수 없습니다.')
    from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_city_proposal
    current_proposal=parse_hermes_city_proposal('HERMES_CITY_PROPOSAL\n'+json.dumps(current_response['proposal'],ensure_ascii=False,allow_nan=False)+'\nEND_HERMES_CITY_PROPOSAL')
    current_draft=execute_remote_management_command('hermes-agent','hermes-city-load',{'map':current_proposal['map']})
    if not isinstance(current_draft,dict) or any(current_draft.get(current_name)!=current_proposal[current_name] for current_name in ('map','generation','revision')):raise gr.Error('도시 원장이 변경됐습니다. 다시 조회하고 제안하세요.')
    current_draft=copy.deepcopy(current_draft)
    for current_change in current_proposal['changes']:
        current_container=current_draft['document']
        for current_part in current_change['path'][:-1]:
            if isinstance(current_container,dict) and isinstance(current_part,str) and current_part in current_container:current_container=current_container[current_part]
            elif isinstance(current_container,list) and type(current_part) is int and 0<=current_part<len(current_container):current_container=current_container[current_part]
            else:raise gr.Error('도시 변경 경로가 현재 원장에 없습니다.')
        current_key=current_change['path'][-1]
        if isinstance(current_container,dict) and isinstance(current_key,str) and current_key in current_container:current_original=current_container[current_key]
        elif isinstance(current_container,list) and type(current_key) is int and 0<=current_key<len(current_container):current_original=current_container[current_key]
        else:raise gr.Error('도시 변경 항목이 현재 원장에 없습니다.')
        if json.dumps(current_original,sort_keys=True,ensure_ascii=False,allow_nan=False)!=json.dumps(current_change['before'],sort_keys=True,ensure_ascii=False,allow_nan=False):raise gr.Error('도시 원본 값이 제안과 다릅니다.')
        current_container[current_key]=copy.deepcopy(current_change['after'])
    return json.dumps(current_draft,ensure_ascii=False,indent=2),current_proposal['changes']


def format_city_source_plan_notice(current_source_plan):
    """검증 가능한 원본 전후 해시만 표시하고 저장 준비와 구분한다."""
    if isinstance(current_source_plan,dict) and current_source_plan.get('status')=='available' and all(isinstance(current_source_plan.get(current_hash_name),str) and re.fullmatch(r'[a-f0-9]{64}',current_source_plan[current_hash_name]) for current_hash_name in ('before_sha256','after_sha256')):
        return '원본 변경 계획: 해시 계산됨\n변경 전 SHA-256: '+current_source_plan['before_sha256']+'\n변경 후 SHA-256: '+current_source_plan['after_sha256']+'\n저장 또는 복구 준비 완료를 뜻하지 않습니다.'
    return '원본 변경 계획: 확인 불가 · 저장 또는 복구 준비 완료를 뜻하지 않습니다.'


def review_hermes_city_map_draft(current_draft_text,current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
        raise gr.Error('접수 ID 형식 오류')
    current_draft_value = parse_management_request_json(current_draft_text)
    current_preview_value = execute_remote_management_command('hermes-agent','hermes-city-preview',{'draft':current_draft_value})
    current_review_value = {'request_id':current_request_identifier,'draft':current_draft_value,'token':current_preview_value['token']}
    current_summary_value = (f"도시: {current_draft_value['map']} · 접수 ID: {current_request_identifier} · DB 세대: {current_draft_value['generation']} · 리비전: {current_draft_value['revision']} · 변경: {'있음' if current_preview_value['changed'] else '없음'} · 건물: {current_preview_value['buildings']} · 장식: {current_preview_value['objects']}  \
도시 원장 초안과 실제 변경을 확인하세요. 맵 원본·등록부와 백엔드 잠금의 동기 저장이 구현될 때까지 신규 저장은 사용할 수 없습니다. 기존 접수는 이력에서 확인할 수 있습니다.")
    current_alignment_status=current_preview_value.get('source_alignment',{}).get('status') if isinstance(current_preview_value.get('source_alignment'),dict) else None
    current_summary_value+='  \
DB와 등록 원본 비교: '+{'matched':'일치','mismatch':'불일치','unavailable':'확인 불가'}.get(current_alignment_status,'확인 불가')+' · 실행 중인 서비스 반영 여부는 별도입니다.'
    current_summary_value+='\n'+format_city_source_plan_notice(current_preview_value.get('source_plan'))
    return current_review_value,current_summary_value,gr.update(visible=True)


def save_hermes_city_map_draft(current_review_value,current_draft_text,current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    current_draft_value = parse_management_request_json(current_draft_text)
    if not isinstance(current_review_value,dict) or current_review_value.get('request_id') != current_request_identifier or current_review_value.get('draft') != current_draft_value:
        raise gr.Error('초안이나 접수 ID가 변경됐습니다. 다시 검증하세요.')
    try:current_result_value=execute_remote_management_command('hermes-agent','hermes-city-save',current_review_value)
    except (OSError,ValueError,TypeError,RuntimeError):
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID로 도시 DB와 이력을 확인하고 자동 재접수하지 마세요.'
    if not isinstance(current_result_value,dict) or current_result_value.get('state')!='completed' or current_result_value.get('request_id')!=current_request_identifier or current_result_value.get('map')!=current_draft_value['map'] or type(current_result_value.get('saved')) is not bool:
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID로 도시 DB와 이력을 확인하고 자동 재접수하지 마세요.'
    return None,gr.update(visible=False),('도시 콘텐츠 DB 저장 완료 · 에셋 원본·등록부와 백엔드 잠금 동기화는 별도로 확인하세요.' if current_result_value['saved'] else 'DB에 저장되지 않음 · 변경 여부와 에셋 원본·소비자 상태를 확인하세요.')


def list_hermes_city_map_choices():
    current_history_value = execute_remote_management_command('hermes-agent','hermes-city-history',{})
    current_choice_values = [(item['map']+' · '+item['request_id']+' · '+item['state'],item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values,value=None),'최근 도시 맵 저장 접수 '+str(len(current_choice_values))+'건 · 손상된 기록은 제외됩니다.'


def read_hermes_city_map_receipt(current_request_identifier):
    current_receipt_value = execute_remote_management_command('hermes-agent','hermes-city-receipt',{'request_id':current_request_identifier})
    if isinstance(current_receipt_value,dict) and current_receipt_value.get('state') == 'not_found':
        return '도시 맵 저장 접수 기록이 없습니다. 저장을 시도했다면 결과를 별도로 확인하세요.'
    if not isinstance(current_receipt_value,dict) or current_receipt_value.get('request_id')!=current_request_identifier or not isinstance(current_receipt_value.get('map'),str):
        return '도시 맵 저장 결과 확인 필요 · 같은 접수 ID로 DB와 이력을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_value.get('state') == 'unknown':
        return '도시: '+current_receipt_value['map']+' · 저장 결과 확인 필요. DB와 이력을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_value.get('state')!='completed' or type(current_receipt_value.get('saved')) is not bool:
        return '도시 맵 저장 결과 확인 필요 · 같은 접수 ID로 DB와 이력을 확인하고 자동 재접수하지 마세요.'
    return '도시: '+current_receipt_value['map']+' · '+('콘텐츠 DB 저장 완료' if current_receipt_value['saved'] else 'DB에 저장되지 않음 · 변경 여부 확인 필요')+' · 맵 원본·등록부와 백엔드 잠금 동기화 및 실행 서비스 반영은 별도 확인하세요.'


def load_hermes_field_map_draft(current_map_identifier):
    """현재 장식 오브젝트를 보존하는 변경 없는 초안을 만든다."""
    import json
    current_map_value = execute_remote_management_command('hermes-agent','hermes-field-load',{'map':current_map_identifier})
    if not isinstance(current_map_value,dict) or current_map_value.get('map')!=current_map_identifier:
        raise gr.Error('요청한 야외 맵 원본을 확인할 수 없습니다.')
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
    current_proposal_response = execute_remote_management_command('hermes-agent','hermes-field-proposal',{'id':current_job_identifier})
    if not isinstance(current_proposal_response,dict) or current_proposal_response.get('job_id')!=current_job_identifier or not isinstance(current_proposal_response.get('proposal'),dict):
        raise gr.Error('선택한 작업의 야외 맵 제안을 확인할 수 없습니다.')
    current_proposal_value = current_proposal_response['proposal']
    current_draft_text,current_source_value,current_review_value,current_confirm_value,current_status_value = load_hermes_field_map_draft(current_proposal_value['map'])
    current_draft_value = json.loads(current_draft_text)
    if current_draft_value['revision'] != current_proposal_value['revision']:
        raise gr.Error('맵 원본이 제안 이후 변경됐습니다. 다시 조회하고 새 제안을 받으세요.')
    current_draft_value['cells'] = current_proposal_value['cells']
    return current_proposal_value['map'],json.dumps(current_draft_value,ensure_ascii=False,indent=2),current_source_value,uuid.uuid4().hex,None,gr.update(visible=False),'제안을 불러왔습니다. 기존 장식을 유지했으며 실제 변경을 살펴보고 초안을 검증하세요.'


def describe_field_map_save_block(current_review_record):
    current_block_reason=current_review_record.get('save_block_reason')
    if current_block_reason=='interrupted':
        return '이전 야외 맵 저장이 중단되었습니다. 콘텐츠 상태에서 백업과 원본·등록부·잠금을 확인하세요.'
    if current_block_reason=='database':
        return 'DB 모드 신규 저장 중단 · 원본·등록부와 백엔드 잠금의 동기화가 필요합니다.'
    return '야외 맵 저장 가능 상태 또는 차단 사유를 확인할 수 없습니다. 원 서비스의 상태를 확인하세요.'


def review_hermes_field_map_draft(current_draft_text, current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
        raise gr.Error('접수 ID 형식 오류')
    current_draft_value = parse_management_request_json(current_draft_text)
    current_preview_value = execute_remote_management_command('hermes-agent','hermes-field-preview',{'draft':current_draft_value})
    current_review_value = {'request_id':current_request_identifier,'draft':current_draft_value,'token':current_preview_value['token'],'save_available':current_preview_value.get('save_available'),'save_block_reason':current_preview_value.get('save_block_reason')}
    current_summary_value = (f"맵: {current_draft_value['map']} · 접수 ID: {current_request_identifier} · 변경: {'있음' if current_preview_value['changed'] else '없음'} · 셀: {current_preview_value['cells']} · 장식: {current_preview_value['objects']} · 도달 셀: {current_preview_value['reachable']}  \
저장 시 맵 원본과 등록부·소비자 잠금·카탈로그가 변경될 수 있습니다. 초안과 원본의 실제 차이를 확인하세요.")
    if current_review_value['save_available'] is not True:
        current_summary_value+=' · '+describe_field_map_save_block(current_review_value)
    if current_review_value['save_available'] is False and current_review_value.get('save_block_reason')=='database':
        current_alignment_status=current_preview_value.get('source_alignment',{}).get('status') if isinstance(current_preview_value.get('source_alignment'),dict) else None
        current_summary_value+=' · DB 타일·지형과 등록 원본 비교: '+{'matched':'일치','mismatch':'불일치','unavailable':'확인 불가'}.get(current_alignment_status,'확인 불가')+' · 실행 중인 서비스 반영은 별도입니다.'
    return current_review_value,current_summary_value,gr.update(visible=True)


def update_field_save_button(current_review_value):
    return gr.update(interactive=isinstance(current_review_value,dict) and current_review_value.get('save_available') is True)


def save_hermes_field_map_draft(current_review_value, current_draft_text, current_request_identifier):
    from tools.review.common.management_gateway import parse_management_request_json
    current_draft_value = parse_management_request_json(current_draft_text)
    if not isinstance(current_review_value,dict) or current_review_value.get('request_id') != current_request_identifier or current_review_value.get('draft') != current_draft_value:
        raise gr.Error('초안이나 접수 ID가 변경됐습니다. 다시 검증하세요.')
    if current_review_value.get('save_available') is not True:
        return None,gr.update(visible=False),describe_field_map_save_block(current_review_value)+' 저장 요청을 보내지 않았습니다.'
    current_save_payload={key:current_review_value[key] for key in ('request_id','draft','token')}
    try:
        current_result_value = execute_remote_management_command('hermes-agent','hermes-field-save',current_save_payload)
    except (OSError,ValueError,TypeError,RuntimeError):
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID로 맵 원본과 이력을 확인하고 자동 재접수하지 마세요.'
    if (not isinstance(current_result_value,dict) or current_result_value.get('state')!='completed'
            or current_result_value.get('request_id')!=current_request_identifier or current_result_value.get('map')!=current_draft_value['map']
            or type(current_result_value.get('saved')) is not bool):
        return None,gr.update(visible=False),'저장 결과 확인 필요 · 같은 접수 ID로 맵 원본과 이력을 확인하고 자동 재접수하지 마세요.'
    return None,gr.update(visible=False),('맵 저장 완료' if current_result_value.get('saved') else '저장되지 않음 · 변경 여부 확인 필요') + ' · 원본과 소비자 상태를 확인하세요.'


def list_hermes_field_map_choices():
    current_history_value = execute_remote_management_command('hermes-agent','hermes-field-history',{})
    current_choice_values = [(item['map']+' · '+item['request_id']+' · '+item['state'],item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values,value=None), '최근 맵 저장 접수 ' + str(len(current_choice_values)) + '건 · 손상된 기록은 제외됩니다.'


def read_hermes_field_map_receipt(current_request_identifier):
    current_receipt_value = execute_remote_management_command('hermes-agent','hermes-field-receipt',{'request_id':current_request_identifier})
    if isinstance(current_receipt_value,dict) and current_receipt_value.get('state') == 'not_found':
        return '맵 저장 접수 기록이 없습니다. 저장을 시도했다면 결과를 별도로 확인하세요.'
    if not isinstance(current_receipt_value,dict) or current_receipt_value.get('request_id')!=current_request_identifier or not isinstance(current_receipt_value.get('map'),str):
        return '맵 저장 결과 확인 필요 · 같은 접수 ID로 원본과 이력을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_value.get('state') == 'unknown':
        return '맵: '+current_receipt_value['map']+' · 저장 결과 확인 필요. 원본을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_value.get('state')!='completed' or type(current_receipt_value.get('saved')) is not bool:
        return '맵 저장 결과 확인 필요 · 같은 접수 ID로 원본과 이력을 확인하고 자동 재접수하지 마세요.'
    return '맵: '+current_receipt_value['map']+' · '+('저장 완료' if current_receipt_value['saved'] else '저장되지 않음 · 변경 여부 확인 필요')+' · 원본·등록부와 소비자 동기화 및 실행 서비스 반영은 별도 확인하세요.'


def read_hermes_content_database_summary():
    """DB 저장과 원장 반영 상태를 분리하여 표시한다."""
    current_status_record = execute_remote_management_command('hermes-agent', 'hermes-content-database-status', {})
    current_map_record = current_status_record.get('map_sources')
    current_map_state = current_map_record.get('status') if isinstance(current_map_record,dict) else None
    if current_map_state in ('matched','mismatch'):
        current_checked_count=current_map_record.get('checked_files')
        current_mismatch_count=current_map_record.get('mismatched_files')
        if type(current_checked_count) is not int or current_checked_count<1 or type(current_mismatch_count) is not int or not 0<=current_mismatch_count<=current_checked_count or (current_map_state=='matched' and current_mismatch_count!=0) or (current_map_state=='mismatch' and current_mismatch_count==0):
            current_map_state='unavailable'
    current_map_text = {'matched':'원본·등록부·백엔드 잠금 일치','mismatch':'원본·등록부·백엔드 잠금 불일치','unavailable':'원본·등록부·백엔드 잠금 확인 불가'}.get(current_map_state,'원본·등록부·백엔드 잠금 확인 불가')
    if current_map_state=='mismatch' and isinstance(current_map_record,dict) and type(current_map_record.get('mismatched_files')) is int and current_map_record['mismatched_files']>=0:
        current_map_text += ' '+str(current_map_record['mismatched_files'])+'개'
    current_map_text += ' · 로컬 인접 저장소 기준이며 DB 일치·실행 중 백엔드 반영은 별도 확인'
    current_map_mode=current_status_record.get('local_map_mode')
    current_map_text+=' · 이 Hermes 서비스의 맵 모드: '+{'database':'DB 설정','files':'파일 설정'}.get(current_map_mode,'확인 불가')+' · 원 서비스와 백엔드의 실제 모드는 별도 확인'
    current_save_record=current_status_record.get('map_save')
    current_save_state=current_save_record.get('state') if isinstance(current_save_record,dict) else None
    current_map_text+=' · 야외 맵 저장: '+{'clear':'중단 기록 없음','busy':'저장 진행 중','pending':'중단 기록 확인 필요','unavailable':'중단 상태 확인 불가'}.get(current_save_state,'중단 상태 확인 불가')
    if current_save_state=='pending':
        current_count_fields=('files','backup_valid','backup_invalid','backup_unavailable','changed_since_backup','current_unavailable')
        if all(type(current_save_record.get(current_field_name)) is int and current_save_record[current_field_name]>=0 for current_field_name in current_count_fields) and sum(current_save_record[current_field_name] for current_field_name in ('backup_valid','backup_invalid','backup_unavailable'))==current_save_record['files'] and current_save_record['changed_since_backup']+current_save_record['current_unavailable']<=current_save_record['files']:
            current_map_text+=f" · 백업 유효 {current_save_record['backup_valid']} · 손상 {current_save_record['backup_invalid']} · 확인 불가 {current_save_record['backup_unavailable']} · 변경된 파일 {current_save_record['changed_since_backup']} · 현재 확인 불가 {current_save_record['current_unavailable']}"
        else:current_map_text+=' · 백업 수량 확인 불가'
        current_map_text+=' · 원본과 백업을 확인하세요'
        current_file_details=current_save_record.get('file_details')
        if isinstance(current_file_details,list) and len(current_file_details)<=128:
            current_visible_details=[]
            for current_file_record in current_file_details:
                if not isinstance(current_file_record,dict) or set(current_file_record)!={'path','current','backup'} or not isinstance(current_file_record['path'],str) or not re.fullmatch(r'(?:assets/(?:maps|billboards)/[A-Za-z0-9_./-]+|asset-registry\.yaml|backend/map-data\.lock\.yaml)',current_file_record['path']) or '..' in current_file_record['path'].split('/') or current_file_record['current'] not in ('before','after','changed','unavailable') or current_file_record['backup'] not in ('valid','invalid','unavailable'):
                    current_visible_details=[]
                    break
                if current_file_record['current']!='before' or current_file_record['backup']!='valid':
                    current_visible_details.append(current_file_record['path']+' (현재 '+{'before':'이전과 같음','after':'저장 예정 내용과 같음','changed':'다른 내용','unavailable':'확인 불가'}[current_file_record['current']]+', 백업 '+{'valid':'유효','invalid':'손상','unavailable':'확인 불가'}[current_file_record['backup']]+')')
            if current_visible_details:
                current_map_text+=' · 확인 대상: '+', '.join(current_visible_details[:10])
                if len(current_visible_details)>10:current_map_text+=' 외 '+str(len(current_visible_details)-10)+'개'
    if current_status_record.get('status') != 'available':
        current_status_guidance = ('게이트웨이의 콘텐츠 서비스 주소 설정을 확인하세요.' if current_status_record.get('failure_reason') == 'service_origin' else '서비스 연결과 인증을 확인하세요.')
        return '콘텐츠 DB 상태 확인 불가 · '+current_status_guidance+' · '+current_map_text
    current_latest_record = current_status_record.get('latest')
    current_latest_text = '기록 없음' if current_latest_record is None else current_latest_record['state'] + (' · 임대 만료' if current_latest_record['lease_expired'] else '')
    return (f"DB 저장 세대: {current_status_record['generation']} · 원장 반영 세대: {current_status_record['ledger_generation']} · "
            f"반영 대기: {'예' if current_status_record['pending'] else '아니요'} · 최근 반영: {current_latest_text} · 조회: {current_status_record['queried_at']} · {current_map_text}")


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
        if not isinstance(current_status_record,dict) or current_status_record.get('service')!=current_service_name:raise ValueError('모델 서비스가 일치하지 않습니다.')
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
        current_flux_scope_text = ' · FLUX 생성 준비 판정은 모델 파일 크기 기준이며 한국어 번역 준비와 GPU 생성 검증은 별도' if current_service_name=='flux-image' else ''
        return (str(current_service_name) + ' · 서비스 준비 판정: ' + ('예' if current_status_record['ready'] else '아니요') + ' · 파일 준비 별도 판정: ' + ('예' if current_artifacts_value is True else '아니요' if current_artifacts_value is False else '확인 불가') + ' · 생성 준비: ' + ('예' if current_generation_value is True else '아니요' if current_generation_value is False else '확인 불가') + ' · 준비 상태: ' + current_status_record['preparation_status'] + current_download_text + ' · 다운로드 정책: ' + ('허용' if current_status_record['prepare_allowed'] else '제한') + ' · 조회: ' + current_status_record['queried_at'] + ' · 서비스 응답이며 실행 권한·GPU 실행·전체 해시는 별도 확인' + current_flux_scope_text)
    except Exception as current_status_error:
        return '모델 상태 조회 실패: '+str(current_status_error)


def review_hermes_model_preparation(current_service_name, current_request_identifier):
    """준비 대상과 영향을 확인하고 제한된 서비스는 접수를 허용하지 않는다."""
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if not isinstance(current_request_identifier, str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):
        raise gr.Error('접수 ID 형식을 확인하세요.')
    current_status_record = execute_remote_management_command('hermes-agent', 'hermes-model-readiness', {'service':current_service_name})
    if not isinstance(current_status_record,dict) or current_status_record.get('service')!=current_service_name or current_status_record.get('status') != 'available' or type(current_status_record.get('ready')) is not bool or type(current_status_record.get('prepare_allowed')) is not bool or current_status_record.get('preparation_status') not in ('idle','running','completed','failed','unknown'):
        raise gr.Error('선택한 모델 서비스의 준비 상태를 확인할 수 없습니다.')
    if not current_status_record['prepare_allowed']:
        raise gr.Error('기존 관리 정책에서 이 모델의 준비를 제한합니다.')
    current_review_record = {'service':current_service_name, 'request_id':current_request_identifier}
    current_summary_text = (f"대상: {current_service_name} · 접수 ID: {current_request_identifier}  \
현재 파일 준비: {'예' if current_status_record['ready'] else '아니요'} · 준비 상태: {current_status_record['preparation_status']}  \
네트워크 다운로드와 디스크 사용이 발생할 수 있고 서비스에 따라 GPU 작업이 접수될 수 있습니다. 기존 서비스 정책을 적용합니다.")
    return current_review_record, current_summary_text, gr.update(visible=True)


def safely_review_hermes_model_preparation(current_service_name,current_request_identifier):
    """검토 실패 시 이전 확인 상태를 지우고 사용자에게 원인을 요약한다."""
    try:
        current_review_record,current_summary_text,current_group_update=review_hermes_model_preparation(current_service_name,current_request_identifier)
        return current_review_record,current_summary_text,current_group_update,'확인할 모델 준비 요청을 검토했습니다.'
    except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError,AttributeError):
        return None,'',gr.update(visible=False),'모델 준비 검토 실패 · 선택한 서비스와 접수 ID, 모델 상태를 다시 확인하세요. 준비 요청은 실행하지 않았습니다.'


def submit_hermes_model_preparation(current_review_record, current_service_name, current_request_identifier):
    """확인 당시의 대상과 ID가 그대로일 때만 모델 준비를 요청한다."""
    if current_review_record != {'service':current_service_name, 'request_id':current_request_identifier}:
        raise gr.Error('대상이나 접수 ID가 변경됐습니다. 다시 검토하세요.')
    try:
        current_result_value = execute_remote_management_command('hermes-agent', 'hermes-model-prepare', current_review_record)
        if not isinstance(current_result_value,dict):
            raise ValueError('접수 응답 형식 오류')
        current_state_value = current_result_value.get('state')
        if current_state_value == 'blocked' and current_result_value.get('request_id') == current_request_identifier and current_result_value.get('service') == 'hermes-model' and current_service_name == 'hermes-model' and current_result_value.get('reason') == 'model_in_use':
            return None, gr.update(visible=False), '모델 사용 중이어서 준비 요청을 접수하지 않았습니다. 실행이 끝난 뒤 같은 요청을 다시 검토하세요.'
        if current_state_value == 'blocked' and current_result_value.get('request_id') == current_request_identifier and current_result_value.get('service') == 'hermes-model' and current_service_name == 'hermes-model' and current_result_value.get('reason') == 'preparation_unknown':
            return None, gr.update(visible=False), '모델 준비 상태를 확인할 수 없어 요청을 접수하지 않았습니다. 원 서비스 상태 기록을 확인하세요.'
        if current_state_value not in ('accepted', 'unknown') or current_result_value.get('request_id')!=current_request_identifier or current_result_value.get('service')!=current_service_name:
            raise ValueError('접수 응답 형식 또는 서비스 오류')
        current_job_value = current_result_value.get('job_id')
        if current_job_value is not None:
            from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_JOB_PATTERN
            if not isinstance(current_job_value,str) or not HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_job_value):
                raise ValueError('모델 준비 작업 ID 오류')
        current_message_text = ('접수 결과 확인 필요. 자동 재접수하지 마세요.' if current_state_value == 'unknown' else '준비 요청 응답을 받았습니다. 실제 완료 여부는 모델 상태에서 확인하세요.')
        current_preparation_status=current_result_value.get('preparation_status')
        current_status_labels={'running':'진행 중','completed':'완료','idle':'대기','failed':'실패','queued':'대기열'}
        if current_state_value=='accepted' and current_preparation_status in current_status_labels:
            current_message_text+=' 접수 응답 당시 상태: '+current_status_labels[current_preparation_status]+'. 현재 상태는 별도로 확인하세요.'
        if current_job_value:
            current_message_text += ' 작업 ID: ' + current_job_value
        return None, gr.update(visible=False), current_message_text
    except Exception:
        return None,gr.update(visible=False),'준비 요청의 접수 결과를 확인할 수 없습니다. 자동으로 다시 요청하지 마세요. 같은 접수 ID의 기록과 원 서비스 모델 상태를 확인하세요.'


def format_hermes_model_preparation_receipt(current_receipt_value,current_service_name,current_request_identifier):
    """한 번 조회한 접수 응답의 식별자와 작업 ID를 검증해 표시한다."""
    if not isinstance(current_receipt_value,dict) or current_receipt_value.get('request_id')!=current_request_identifier or current_receipt_value.get('service')!=current_service_name or current_receipt_value.get('state') not in ('not_found','unknown','accepted'):
        raise ValueError('모델 준비 접수 식별 또는 상태 오류')
    if current_receipt_value['state']=='not_found':return '접수 기록이 없습니다. 준비 요청을 시도했다면 원 서비스 상태를 확인하세요.'
    current_message_text=current_receipt_value.get('message')
    if not isinstance(current_message_text,str):raise ValueError('모델 준비 접수 안내 오류')
    current_job_identifier=current_receipt_value.get('job_id')
    if current_job_identifier is not None:
        from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_JOB_PATTERN
        if not isinstance(current_job_identifier,str) or not HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_job_identifier):raise ValueError('모델 준비 작업 ID 오류')
    return current_message_text+(' 작업 ID: '+current_job_identifier if current_job_identifier else '')


def read_hermes_model_preparation_receipt(current_service_name, current_request_identifier):
    try:
        current_receipt_value=execute_remote_management_command('hermes-agent','hermes-model-prepare-status',{'service':current_service_name,'request_id':current_request_identifier})
        return format_hermes_model_preparation_receipt(current_receipt_value,current_service_name,current_request_identifier)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,AttributeError,gr.Error):
        return '접수 기록을 확인할 수 없습니다. 같은 접수 ID와 원 서비스 상태를 확인하고 자동 재요청하지 마세요.'


def list_hermes_model_preparation_choices():
    current_history_value = execute_remote_management_command('hermes-agent', 'hermes-model-prepare-history', {})
    current_choice_values = [(item['service'] + ' · ' + item['request_id'] + ' · ' + item['state'], item['service'] + ':' + item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values, value=None), '최근 접수 ' + str(len(current_choice_values)) + '건 · 손상된 기록은 제외됩니다.'


def select_hermes_model_preparation_receipt(current_selection_value):
    if not isinstance(current_selection_value, str) or ':' not in current_selection_value:
        raise gr.Error('접수 이력을 선택하세요.')
    current_service_name, current_request_identifier = current_selection_value.split(':', 1)
    return current_service_name, current_request_identifier


def read_hermes_model_download_status_for_review():
    return execute_remote_management_command('hermes-agent','hermes-model-download-status',{})


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


def update_direct_job_cancel_availability(current_job_identifier):
    """형식이 확인된 작업 ID가 있을 때만 중지 요청을 활성화한다."""
    current_valid_identifier = isinstance(current_job_identifier,str) and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_job_identifier))
    return gr.update(interactive=current_valid_identifier)


DIRECT_CANCEL_CONFIRMATION_LOCK = threading.Lock()


def review_direct_job_cancel(current_job_identifier):
    """중지 요청 전에 대상 ID를 고정한다."""
    if not update_direct_job_cancel_availability(current_job_identifier)['interactive']:
        raise gr.Error('유효한 작업 ID를 확인하세요.')
    return {'job_id':current_job_identifier,'consumed':False}, '중지 대상: '+current_job_identifier+' · 요청 후 실제 종료를 확인하세요.', gr.update(visible=True)


def discard_direct_job_cancel(current_review_record):
    """취소된 확인은 뒤늦은 중지 요청에도 사용할 수 없게 한다."""
    with DIRECT_CANCEL_CONFIRMATION_LOCK:
        if isinstance(current_review_record,dict):current_review_record['consumed']=True
    return None,gr.update(visible=False)


def submit_direct_job_cancel(current_review_record,current_job_identifier):
    """확인 이후 바뀌지 않은 대상에만 중지를 요청한다."""
    with DIRECT_CANCEL_CONFIRMATION_LOCK:
        if not isinstance(current_review_record,dict) or current_review_record.get('consumed') is not False:
            return None,gr.update(visible=False),gr.skip()
        current_review_record['consumed']=True
        if current_review_record.get('job_id') != current_job_identifier or not update_direct_job_cancel_availability(current_job_identifier)['interactive']:
            return None,gr.update(visible=False),'중지 대상이 변경되었습니다. 작업을 다시 확인하세요.'
    try:
        current_result_text=cancel_hermes_work_request(current_job_identifier)
    except Exception:
        return None,gr.update(visible=False),'중지 요청 결과 확인 필요 · 작업 '+current_job_identifier+'의 실제 상태를 확인하고 다시 요청하기 전에 종료 여부를 확인하세요.'
    return None,gr.update(visible=False),'중지 요청 대상: '+current_job_identifier+' · '+current_result_text


def reset_direct_session_job_detail():
    """세션이나 작업 선택이 바뀌면 이전 상세와 중지 대상을 지운다."""
    return '', '선택이 바뀌었습니다. 작업 상세를 다시 여세요.', '', '', '', None, '', None, '전체 diff를 보려면 완료된 작업을 선택하세요.'


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
        if not isinstance(current_snapshot_record, dict):
            raise ValueError('관리 상태 응답 형식 오류')
        def read_status_record(current_parent_record, current_field_name):
            current_field_value = current_parent_record.get(current_field_name)
            return current_field_value if isinstance(current_field_value, dict) else {}
        current_model_record = read_status_record(current_snapshot_record, 'model')
        current_gpu_record = read_status_record(current_snapshot_record, 'gpu')
        current_queue_record = read_status_record(current_snapshot_record, 'queue')
        current_capacity_record = read_status_record(current_snapshot_record, 'memory_capacity')
        current_reservation_record = read_status_record(current_snapshot_record, 'reservations')
        current_recent_jobs = read_status_record(current_snapshot_record, 'recent_hermes_jobs')
        current_generator_record = read_status_record(read_status_record(current_snapshot_record, 'generators'), 'kimodo')
        current_generator_model = read_status_record(current_generator_record, 'model')
        current_generator_active = read_status_record(current_generator_record, 'active')
        if not isinstance(current_queue_record.get('jobs'), list): current_queue_record = {}
        if not isinstance(current_reservation_record.get('records'), list) or any(not isinstance(current_record, dict) for current_record in current_reservation_record.get('records', [])): current_reservation_record = {}
        if not isinstance(current_recent_jobs.get('jobs'), list): current_recent_jobs = {}
        current_model_text = current_model_record['message'] if current_model_record.get('status') == 'available' and isinstance(current_model_record.get('message'), str) else '조회 불가'
        current_queue_text = str(len(current_queue_record['jobs'])) + '건' if current_queue_record.get('status') == 'available' else '조회 불가'
        current_generator_text = ('준비됨' if current_generator_model['ready'] else '준비 필요') if current_generator_model.get('status') == 'available' and type(current_generator_model.get('ready')) is bool else '조회 불가'
        if current_generator_active.get('status')=='available' and type(current_generator_active.get('running')) is bool and type(current_generator_active.get('count')) is int and type(current_generator_active.get('unknown_count')) is int and current_generator_active['count'] >= 0 and current_generator_active['unknown_count'] >= 0 and current_generator_active['running'] == (current_generator_active['count'] > 0):
            current_active_text=('기록상 대기·실행 '+str(current_generator_active.get('count'))+'건 · 최근 '+str(current_generator_active.get('id'))) if current_generator_active.get('running') else '확인된 대기·실행 기록 없음'
            if current_generator_active.get('unknown_count',0):
                current_active_text+=' · 상태 확인 불가 '+str(current_generator_active['unknown_count'])+'건'
        else:
            current_active_text='조회 불가'
        current_capacity_text='조회 불가'
        if (current_capacity_record.get('status')=='available' and current_capacity_record.get('domain') in ('vram','gtt')
                and current_gpu_record.get('status') in ('idle','busy')
                and type(current_capacity_record.get('capacity_sufficient')) is bool
                and all(type(current_capacity_record.get(current_field_name)) is int and current_capacity_record[current_field_name]>=0 for current_field_name in ('pool_available_mib','required_mib','host_available_mib'))
                and current_capacity_record['required_mib']>0
                and current_capacity_record['capacity_sufficient']==(current_capacity_record['pool_available_mib']>=current_capacity_record['required_mib'])):
            current_capacity_text=(current_capacity_record['domain'].upper()+' 여유 '+str(current_capacity_record['pool_available_mib'])+' / 필요 '+str(current_capacity_record['required_mib'])+' MiB · 호스트 여유 '+str(current_capacity_record['host_available_mib'])+' MiB · '+('관측치상 메모리 기준 충족' if current_capacity_record['capacity_sufficient'] else '관측치상 메모리 부족')+' · 실제 실행 가능 여부 별도')
        current_reservation_text = (str(len(current_reservation_record.get('records', []))) + '건' + (' 이상' if current_reservation_record.get('truncated') else '') + (' · 확인 불가 기록 포함' if any(current_record.get('state') == 'unknown' for current_record in current_reservation_record.get('records', [])) else '') + (' · 종료 확인이 필요한 예약 포함' if any(current_record.get('state') == 'cleanup_unverified' for current_record in current_reservation_record.get('records', [])) else '') + (' · 작가 작업자 리더 생존 확인' if any(current_record.get('state') == 'cleanup_unverified' and current_record.get('worker_leader') == 'verified_running' for current_record in current_reservation_record.get('records', [])) else '')) if current_reservation_record.get('status') == 'available' else '조회 불가'
        current_jobs_text = (str(len(current_recent_jobs.get('jobs', []))) + '건' + (' (최근 10건)' if current_recent_jobs.get('truncated') else '')) if current_recent_jobs.get('status') == 'available' else '조회 불가'
        return 'GPU 예약 기록: ' + current_reservation_text + ' · 최근 Hermes 작업: ' + current_jobs_text + ' · 메모리: ' + current_capacity_text + ' (다른 예약·순서 제외) · Kimodo: ' + current_generator_text + ' · ' + current_active_text + ' · Hermes 모델: ' + current_model_text + ' · GPU: ' + str(current_gpu_record.get('status', 'unavailable')) + ' · 대기: ' + current_queue_text + ' · 확인: ' + str(current_snapshot_record.get('queried_at') or '조회 시각 확인 불가') + ' (GPU 측정은 짧게 캐시될 수 있음)'
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


def validate_hermes_result_identity(current_receipt_record,current_request_identifier,current_service_identifier):
    """결과 조회 응답의 명시적인 접수·서비스 불일치를 거절한다."""
    if not isinstance(current_receipt_record,dict) or current_receipt_record.get('state') not in ('accepted','unknown','not_found'):
        raise gr.Error('접수 상태를 확인할 수 없습니다. 원 서비스 이력을 확인하세요.')
    if current_receipt_record.get('request_id') not in (None,current_request_identifier) or current_receipt_record.get('service') not in (None,current_service_identifier):
        raise gr.Error('접수 ID 또는 서비스가 일치하지 않습니다. 원 서비스 이력을 확인하세요.')
    if current_receipt_record.get('state')=='accepted':
        from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
        if current_receipt_record.get('service')!=current_service_identifier or not validate_service_job_identifier(current_service_identifier,current_receipt_record.get('job_id')):
            raise gr.Error('접수 서비스 또는 작업 ID를 확인할 수 없습니다.')


def read_hermes_writer_result(current_request_identifier,current_session_identifier=None):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-writer-status',{'request_id':current_request_identifier})
    current_receipt_value=current_status_value['receipt']
    validate_hermes_result_identity(current_receipt_value,current_request_identifier,'writer-agent')
    if current_receipt_value.get('state')=='not_found':
        return '', '작가 접수 기록이 없습니다.',None
    if current_receipt_value.get('state')=='unknown':
        return '', '작가 접수 결과 확인 필요 · 작가 AI 이력을 확인하세요.',None
    current_job_value=current_status_value.get('job',{})
    return current_receipt_value['job_id'],'작가 작업 상태: '+str(current_job_value.get('stage','unknown'))+(' · '+current_job_value['failure_reason'] if current_job_value.get('failure_reason') else '')+' · [작가 AI 이력 열기]('+build_conversation_result_link('writer-agent',current_receipt_value['job_id'],current_session_identifier)+')',current_job_value


def list_hermes_writer_choices():
    current_history_value=execute_remote_management_command('hermes-agent','hermes-writer-history',{})
    current_choice_values=[(item['request_id']+' · '+item['state'],item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values,value=None),'최근 작가 위임 '+str(len(current_choice_values))+'건 · 손상된 기록은 제외됩니다.'


def review_hermes_writer_apply(current_writer_identifier,current_apply_identifier,current_confirmation_value):
    import re
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if current_confirmation_value is not True:
        raise gr.Error('작가 AI 화면에서 전체 변경과 근거를 확인한 뒤 체크하세요.')
    if not isinstance(current_apply_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_apply_identifier):
        raise gr.Error('적용 접수 ID 형식 오류')
    current_status_value=execute_remote_management_command('hermes-agent','hermes-writer-status',{'request_id':current_writer_identifier})
    current_receipt_value=current_status_value.get('receipt',{})
    current_job_value=current_status_value.get('job',{})
    if not is_valid_writer_receipt(current_receipt_value,current_writer_identifier):
        raise gr.Error('작가 접수 서비스 또는 작업 ID를 확인할 수 없습니다. 작가 AI 이력을 확인하세요.')
    if (not isinstance(current_job_value,dict) or current_job_value.get('stage')!='review' or current_job_value.get('truncated') is not False
            or not isinstance(current_job_value.get('proposal_hash'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_job_value['proposal_hash'])
            or not isinstance(current_job_value.get('changes'),list) or not current_job_value['changes']):
        raise gr.Error('전체 변경이 확인되는 미적용 작가 제안이 필요합니다.')
    current_review_value={'request_id':current_apply_identifier,'writer_request_id':current_writer_identifier,'job_id':current_receipt_value['job_id'],'proposal_hash':current_job_value['proposal_hash']}
    current_summary_value='작가 작업 '+current_receipt_value['job_id']+' · 변경 문서 '+str(len(current_job_value['changes']))+'개 · 제안 해시 '+current_job_value['proposal_hash']+' · 확인 후 원본이 변경됩니다.'
    return current_review_value,current_job_value,gr.update(visible=True),current_summary_value


def submit_hermes_writer_apply(current_review_value,current_writer_identifier,current_apply_identifier,current_confirmation_value):
    if not isinstance(current_review_value,dict) or current_confirmation_value is not True or current_review_value.get('request_id')!=current_apply_identifier or current_review_value.get('writer_request_id')!=current_writer_identifier:
        raise gr.Error('확인 또는 적용 대상이 바뀌었습니다. 다시 검토하세요.')
    try:current_result_value=execute_remote_management_command('hermes-agent','hermes-writer-apply',current_review_value)
    except (OSError,ValueError,TypeError,RuntimeError):
        return None,gr.update(visible=False),'적용 결과 확인 필요 · 같은 접수 ID로 이력과 원본을 확인하고 자동 재적용하지 마세요.'
    if not isinstance(current_result_value,dict) or current_result_value.get('state')!='completed' or any(current_result_value.get(current_field_name)!=current_review_value.get(current_field_name) for current_field_name in ('request_id','writer_request_id','job_id','proposal_hash')):
        return None,gr.update(visible=False),'적용 결과 확인 필요 · 같은 접수 ID로 이력과 원본을 확인하고 자동 재적용하지 마세요.'
    return None,gr.update(visible=False),'작가 제안을 원본에 적용했습니다. 다음 작업 전 문서 색인을 갱신하세요.'


def list_hermes_writer_apply_choices():
    current_history_value=execute_remote_management_command('hermes-agent','hermes-writer-apply-history',{})
    current_choice_values=[(item['request_id']+' · '+item['job_id']+' · '+item['state'],item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values,value=None),'최근 작가 적용 '+str(len(current_choice_values))+'건 · 손상된 기록은 제외됩니다.'


def read_hermes_writer_apply_receipt(current_apply_identifier):
    current_receipt_value=execute_remote_management_command('hermes-agent','hermes-writer-apply-status',{'request_id':current_apply_identifier})
    if current_receipt_value.get('state')=='not_found':
        return '적용 접수 기록이 없습니다.'
    if (current_receipt_value.get('state')!='completed' or current_receipt_value.get('request_id')!=current_apply_identifier
            or not isinstance(current_receipt_value.get('job_id'),str)):
        return '적용 결과 확인 필요 · 원본과 작가 AI 상태를 확인하고 자동 재적용하지 마세요.'
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    if not validate_service_job_identifier('writer-agent',current_receipt_value['job_id']):
        return '적용 결과 확인 필요 · 원본과 작가 AI 상태를 확인하고 자동 재적용하지 마세요.'
    return '작가 작업 '+current_receipt_value['job_id']+' · 적용 완료 · 다음 작업 전 색인을 갱신하세요.'


def load_hermes_translation_proposal(current_job_identifier):
    """완료된 번역 제안을 검토 입력으로 불러오되 접수하지 않는다."""
    if not current_job_identifier:
        raise gr.Error('먼저 세션 작업을 선택하세요.')
    current_proposal_value=read_matching_hermes_edit_proposal(current_job_identifier,'hermes-translation-proposal')
    current_glossary_text='\n'.join(item['source']+' => '+item['target'] for item in current_proposal_value['glossary'])
    return current_proposal_value['text'],current_proposal_value['target_language'],current_glossary_text,uuid.uuid4().hex,None,'','제안을 불러왔습니다. 원문과 목표 언어·용어를 확인하고 다시 검토하세요.',gr.update(interactive=False)


def read_hermes_writer_index_status_for_review():
    current_status_record=execute_remote_management_command('hermes-agent','hermes-writer-index-status',{})
    current_status_labels={'fresh':'최신','stale':'갱신 필요','unavailable':'확인 불가'}
    return '작가 색인: '+current_status_labels.get(current_status_record.get('status'),'확인 불가')+' · 조회 시점 기준. 갱신의 GPU 사용 여부와 실행 가능성은 별도 확인합니다.'


def search_hermes_translation_evidence_for_review(current_source_text):
    """번역 원문에 대한 작가 색인 근거를 번역 접수 없이 조회한다."""
    return execute_remote_management_command('hermes-agent','hermes-translation-evidence',{'text':current_source_text})


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


def read_hermes_translation_result(current_request_identifier,current_session_identifier=None):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-translation-status',{'request_id':current_request_identifier})
    current_receipt_value=current_status_value['receipt']
    validate_hermes_result_identity(current_receipt_value,current_request_identifier,'prompt-translation')
    if current_receipt_value.get('state')=='not_found':
        return '', '번역 접수 기록이 없습니다.', None
    if current_receipt_value.get('state')=='unknown':
        return '', '번역 접수 결과 확인 필요 · 번역기 이력을 확인하세요.', None
    current_job_value=current_status_value.get('job',{})
    return current_receipt_value['job_id'],'번역 작업 상태: '+str(current_job_value.get('status','unknown'))+(' · '+current_job_value['failure_reason'] if current_job_value.get('failure_reason') else '')+' · [번역 이력 열기]('+build_conversation_result_link('prompt-translation',current_receipt_value['job_id'],current_session_identifier)+')',current_job_value.get('result')


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
    import re
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN
    if not isinstance(current_request_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_request_identifier):raise gr.Error('정리 접수 ID 형식 오류')
    current_result_value=execute_remote_management_command('hermes-agent','hermes-writer-reservation-preview',{'job_id':current_job_identifier})
    if not isinstance(current_result_value,dict) or current_result_value.get('job_id')!=current_job_identifier or type(current_result_value.get('recoverable')) is not bool:
        raise gr.Error('선택한 작가 예약을 확인할 수 없습니다. 다시 조회하세요.')
    if current_result_value.get('recoverable') is not True:
        return None,current_result_value,gr.update(visible=False),current_result_value.get('reason','예약을 확인할 수 없습니다.')
    if not isinstance(current_result_value.get('preview_sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_result_value['preview_sha256']) or not isinstance(current_result_value.get('reason'),str):
        raise gr.Error('작가 예약 검토 정보를 확인할 수 없습니다. 다시 조회하세요.')
    current_review_value={'request_id':current_request_identifier,'job_id':current_job_identifier,'review_sha256':current_result_value['preview_sha256']}
    return current_review_value,current_result_value,gr.update(visible=True),current_result_value['reason']


def submit_hermes_writer_reservation_recovery(current_review_value,current_request_identifier,current_job_identifier,current_outside_checked):
    if not isinstance(current_review_value,dict) or current_review_value.get('request_id')!=current_request_identifier or current_review_value.get('job_id')!=current_job_identifier or current_outside_checked is not True:
        raise gr.Error('대상과 별도 그룹 GPU 프로세스 확인을 다시 확인하세요.')
    try:
        current_result_value=execute_remote_management_command('hermes-agent','hermes-writer-reservation-recover',{**current_review_value,'outside_processes_checked':True})
    except Exception:
        return None,gr.update(visible=False),'정리 결과 확인 필요 · 접수를 확인하고 자동 재실행하지 마세요.'
    if isinstance(current_result_value,dict) and current_result_value.get('state')=='completed' and current_result_value.get('request_id')==current_request_identifier and current_result_value.get('job_id')==current_job_identifier:
        return None,gr.update(visible=False),'검증된 그룹을 종료하고 예약을 해제했습니다. 작업 상태와 GPU 사용량을 확인하세요.'
    return None,gr.update(visible=False),'정리 결과 확인 필요 · 접수를 확인하고 자동 재실행하지 마세요.'


def read_hermes_writer_reservation_recovery_receipt(current_request_identifier):
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    current_result_value=execute_remote_management_command('hermes-agent','hermes-writer-reservation-receipt',{'request_id':current_request_identifier})
    if not isinstance(current_result_value,dict):return '정리 접수를 확인할 수 없습니다.'
    if current_result_value.get('state') in ('unknown','completed') and (current_result_value.get('request_id')!=current_request_identifier or not validate_service_job_identifier('writer-agent',current_result_value.get('job_id'))):
        return '정리 결과 확인 필요 · 접수 ID와 작업 상태를 확인하세요.'
    return {'not_found':'정리 접수 기록이 없습니다.','unknown':'정리 결과 확인 필요 · 예약과 작업 상태를 확인하세요.','completed':'검증된 그룹 정리와 예약 해제가 기록됐습니다.'}.get(current_result_value.get('state'),'정리 접수를 확인할 수 없습니다.')


def matches_hermes_cancellation_receipt(current_receipt_record,current_service_name,current_job_identifier,current_request_identifier):
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    return (isinstance(current_receipt_record,dict) and current_receipt_record.get('state')=='accepted'
            and current_receipt_record.get('request_id')==current_request_identifier and current_receipt_record.get('service')==current_service_name and current_receipt_record.get('job_id')==current_job_identifier
            and validate_service_job_identifier(current_service_name,current_job_identifier))


def review_hermes_writer_cancellation(current_request_identifier,current_job_identifier):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-writer-status',{'request_id':current_request_identifier})
    if not matches_hermes_cancellation_receipt(current_status_value.get('receipt'), 'writer-agent',current_job_identifier,current_request_identifier):
        raise gr.Error('접수 기록과 작가 작업 ID가 일치하지 않습니다.')
    if current_status_value.get('job',{}).get('stage') not in ('queued','preparing','indexing','searching','reasoning'):
        raise gr.Error('대기 또는 실행 중인 작가 작업만 중지할 수 있습니다.')
    return {'request_id':current_request_identifier,'job_id':current_job_identifier},gr.update(visible=True),'작가 작업 '+current_job_identifier+'에 중지를 요청합니다. 실제 종료는 상태에서 확인하세요.'


def submit_hermes_writer_cancellation(current_review_value,current_request_identifier,current_job_identifier):
    if current_review_value!={'request_id':current_request_identifier,'job_id':current_job_identifier}:raise gr.Error('중지 대상이 바뀌었습니다. 다시 확인하세요.')
    return submit_hermes_checked_cancellation('hermes-writer-cancel',current_review_value,current_job_identifier)


def review_hermes_translation_cancellation(current_request_identifier,current_job_identifier):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-translation-status',{'request_id':current_request_identifier})
    if not matches_hermes_cancellation_receipt(current_status_value.get('receipt'),'prompt-translation',current_job_identifier,current_request_identifier):
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
    current_proposal_value=read_matching_hermes_edit_proposal(current_job_identifier,'hermes-video-proposal')
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



def read_safe_hermes_result(current_read_function,current_result_count,*current_request_values):
    """조회 실패 시 이전 작업 ID와 결과를 지우고 확인 필요를 표시한다."""
    try:
        return current_read_function(*current_request_values)
    except (gr.Error,OSError,ValueError,TypeError,KeyError,RuntimeError,AttributeError):
        current_notice_text='접수 또는 결과 확인 불가 · 원 서비스와 같은 접수 ID의 이력을 확인하세요. 자동 재접수하지 않습니다.'
        return ('',current_notice_text,None) if current_result_count==3 else ('',current_notice_text)


def read_safe_hermes_writer_result(current_request_identifier,current_session_identifier=None):
    return read_safe_hermes_result(read_hermes_writer_result,3,current_request_identifier,current_session_identifier)


def read_safe_hermes_translation_result(current_request_identifier,current_session_identifier=None):
    return read_safe_hermes_result(read_hermes_translation_result,3,current_request_identifier,current_session_identifier)


def read_safe_hermes_video_result(current_request_identifier,current_service_name,current_session_identifier=None):
    return read_safe_hermes_result(read_hermes_video_result,2,current_request_identifier,current_service_name,current_session_identifier)


def read_safe_hermes_audio_result(current_request_identifier,current_service_name,current_session_identifier=None):
    return read_safe_hermes_result(read_hermes_audio_result,2,current_request_identifier,current_service_name,current_session_identifier)


def read_safe_hermes_flux_result(current_request_identifier,current_service_name,current_session_identifier=None):
    return read_safe_hermes_result(read_hermes_flux_profile_result,2,current_request_identifier,current_service_name,current_session_identifier)


def validate_conversation_result_receipt(current_receipt_value,current_service_name,current_session_identifier=None):
    """원 서비스와 작업 ID가 확인된 접수만 결과 링크에 사용한다."""
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    if not isinstance(current_receipt_value,dict) or current_receipt_value.get('state')!='accepted' or current_receipt_value.get('service')!=current_service_name or not validate_service_job_identifier(current_service_name,current_receipt_value.get('job_id')):
        raise gr.Error('접수 서비스 또는 작업 ID를 확인할 수 없습니다.')
    current_result_link=build_conversation_result_link(current_service_name,current_receipt_value['job_id'],current_session_identifier)
    if current_result_link is None:raise gr.Error('지원하는 원 서비스를 확인할 수 없습니다.')
    return current_result_link


def format_media_link_verification_notice(current_has_links):
    return ' · 결과 경로 형식만 확인했으며 파일 존재와 재생은 원 도구에서 확인하세요.' if current_has_links else ''


def read_hermes_video_result(current_request_identifier,current_service_name,current_session_identifier=None):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-video-status',{'request_id':current_request_identifier,'service':current_service_name})
    current_receipt_value=current_status_value['receipt']
    validate_hermes_result_identity(current_receipt_value,current_request_identifier,current_service_name)
    if current_receipt_value.get('state')=='not_found':
        return '', '해당 서비스의 접수 기록이 없습니다.'
    if current_receipt_value.get('state')=='unknown':
        return '', '접수 결과 확인 필요 · 해당 생성기 이력을 확인하세요.'
    current_history_link=validate_conversation_result_receipt(current_receipt_value,current_service_name,current_session_identifier)
    current_job_value=current_status_value.get('job',{})
    from tools.review.domains.hermes_agent.media_result_paths import validate_hermes_video_result_paths
    current_media_paths=validate_hermes_video_result_paths(current_service_name,current_receipt_value['job_id'],current_job_value)
    current_video_observation=read_conversation_video_source_observation(current_service_name,current_receipt_value['job_id']) if current_job_value.get('status')=='completed' else None
    if current_video_observation is not None:
        current_media_paths={current_field_name:current_video_observation[current_field_name] for current_field_name in ('video','image','download')}
    current_links_text=''.join(' · ['+label+']('+current_media_paths[field]+')' for field,label in (('video','영상'),('image','첫 프레임'),('download','프레임 ZIP')) if current_media_paths[field])
    current_result_count=sum(current_value is not None for current_value in current_media_paths.values())
    current_result_state=('available' if current_result_count==3 else 'partial' if current_result_count else 'unavailable') if current_job_value.get('status')=='completed' else 'not_ready'
    current_result_notice={'partial':' · 결과 일부만 확인됨','unavailable':' · 완료 기록은 있으나 결과 파일 확인 불가'}.get(current_result_state,'')
    if current_video_observation is not None:
        if current_video_observation['status']!='completed':current_result_notice=' · 원본 작업 상태가 변경되어 결과를 다시 확인하세요.'
        elif current_video_observation['result_status']=='available':current_result_notice=' · 파일 존재는 조회 시점 기준'
    if current_job_value.get('status')=='completed' and current_video_observation is None:
        current_result_notice+=' · 원본 영상 상태 조회 불가 · 원 도구에서 다시 확인하세요.'
    current_verification_notice=(' · 영상 내용과 재생은 별도로 확인하세요.' if current_video_observation is not None and current_links_text else format_media_link_verification_notice(bool(current_links_text)))
    return current_receipt_value['job_id'],'작업 상태: '+str(current_job_value.get('status','unknown'))+current_result_notice+(' · '+current_job_value['failure_reason'] if current_job_value.get('failure_reason') else '')+current_links_text+' · [생성기 이력]('+current_history_link+') · 상태 조회 시 기존 복구가 따를 수 있습니다.'+current_verification_notice


def list_hermes_video_choices(current_service_name):
    current_history_value=execute_remote_management_command('hermes-agent','hermes-video-history',{'service':current_service_name})
    current_choice_values=[(item['request_id']+' · '+item['state'],item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values,value=None),'이 서비스의 최근 접수 '+str(len(current_choice_values))+'건 · 손상된 기록은 제외됩니다.'


def review_hermes_video_cancellation(current_request_identifier,current_service_name,current_job_identifier):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-video-status',{'request_id':current_request_identifier,'service':current_service_name})
    if not matches_hermes_cancellation_receipt(current_status_value.get('receipt'),current_service_name,current_job_identifier,current_request_identifier):
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
    current_proposal_value=read_matching_hermes_edit_proposal(current_job_identifier,'hermes-audio-proposal')
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


def read_hermes_audio_result(current_request_identifier,current_service_name,current_session_identifier=None):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-audio-status',{'request_id':current_request_identifier,'service':current_service_name})
    current_receipt_value=current_status_value['receipt']
    validate_hermes_result_identity(current_receipt_value,current_request_identifier,current_service_name)
    if current_receipt_value.get('state')=='not_found':
        return '', '해당 오디오 서비스의 접수 기록이 없습니다.'
    if current_receipt_value.get('state')=='unknown':
        return '', '오디오 접수 결과 확인 필요 · 해당 생성기 이력을 확인하세요.'
    current_history_link=validate_conversation_result_receipt(current_receipt_value,current_service_name,current_session_identifier)
    current_job_value=current_status_value.get('job',{})
    from tools.review.domains.hermes_agent.media_result_paths import validate_hermes_audio_result_path
    current_audio_path=validate_hermes_audio_result_path(current_service_name,current_receipt_value['job_id'],current_job_value)
    current_file_observation=current_job_value.get('file_observation','unknown')
    if current_file_observation not in ('present','unavailable','unknown','not_ready') or (current_file_observation in ('present','unavailable') and not current_audio_path) or (current_file_observation=='not_ready' and current_audio_path):raise gr.Error('음원 파일 관측을 확인할 수 없습니다.')
    if current_file_observation=='unavailable':current_audio_path=None
    current_result_notice=' · 완료 기록은 있으나 음원 링크 확인 불가' if current_job_value.get('status')=='completed' and not current_audio_path else ''
    current_verification_notice=' · 음원 파일 존재는 조회 시점 기준이며 재생은 별도 확인하세요.' if current_file_observation=='present' else format_media_link_verification_notice(bool(current_audio_path))
    return current_receipt_value['job_id'],'작업 상태: '+str(current_job_value.get('status','unknown'))+current_result_notice+(' · '+current_job_value['failure_reason'] if current_job_value.get('failure_reason') else '')+(' · [생성 음원 듣기]('+current_audio_path+')' if current_audio_path else '')+' · [생성기 이력]('+current_history_link+')'+current_verification_notice


def read_hermes_source_history_page(current_service_name,current_command_name,current_page_state=None,current_next_page=False):
    """서비스와 스냅샷을 고정하여 원본 이력을 페이지별로 표시한다."""
    try:
        current_request_value={'service':current_service_name,'limit':30}
        if current_next_page:
            if not isinstance(current_page_state,dict) or current_page_state.get('service')!=current_service_name or current_page_state.get('command')!=current_command_name or type(current_page_state.get('next_offset')) is not int or not isinstance(current_page_state.get('snapshot'),str):
                raise ValueError('서비스가 바뀌었거나 다음 페이지가 없습니다. 처음부터 조회하세요.')
            current_request_value.update(offset=current_page_state['next_offset'],snapshot=current_page_state['snapshot'])
        current_result_value=execute_remote_management_command('hermes-agent',current_command_name,current_request_value)
        from tools.review.domains.hermes_agent.audio_operations import sanitize_hermes_source_history
        from tools.review.common.source_history_catalog import SOURCE_HISTORY_SERVICE_ALIASES
        if not isinstance(current_result_value,dict) or current_result_value.get('service')!=current_service_name:
            raise ValueError('원본 이력 서비스 불일치')
        current_source_service=SOURCE_HISTORY_SERVICE_ALIASES.get(current_service_name,current_service_name)
        if current_result_value.get('source_service',current_source_service)!=current_source_service:
            raise ValueError('원본 이력 소유 서비스 불일치')
        current_safe_result=sanitize_hermes_source_history(current_service_name,{current_key:current_value for current_key,current_value in current_request_value.items() if current_key!='service'},current_result_value)
        current_safe_result['source_service']=current_source_service
        current_result_value=current_safe_result
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
            current_status_text+=' · 확인 불가 이력 '+str(current_result_value['unavailable_count'])+'건은 원 생성기에서 확인하세요.'
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
    if not matches_hermes_cancellation_receipt(current_status_value.get('receipt'),current_service_name,current_job_identifier,current_request_identifier):
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


def read_hermes_flux_profile_result(current_request_identifier,current_profile_name,current_session_identifier=None):
    from tools.review.domains.hermes_agent.flux_profile_operations import validate_hermes_flux_profile
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    validate_hermes_flux_profile(current_profile_name)
    current_status_value=execute_remote_management_command('hermes-agent','hermes-flux-profile-status',{'request_id':current_request_identifier,'service':current_profile_name})
    if not isinstance(current_status_value,dict) or not isinstance(current_status_value.get('receipt'),dict):raise gr.Error('접수 상태를 확인할 수 없습니다.')
    current_receipt_value=current_status_value['receipt']
    validate_hermes_result_identity(current_receipt_value,current_request_identifier,current_profile_name)
    if current_receipt_value.get('state')=='not_found':
        return '', '해당 프로필의 접수 기록이 없습니다.'
    if current_receipt_value.get('state')=='unknown':
        if current_receipt_value.get('service')!=current_profile_name:raise gr.Error('접수 서비스가 일치하지 않습니다.')
        return '', '접수 결과 확인 필요 · 해당 생성기 이력을 확인하고 자동 재접수하지 마세요.'
    if current_receipt_value.get('state')!='accepted' or current_receipt_value.get('service')!=current_profile_name or not validate_service_job_identifier(current_profile_name,current_receipt_value.get('job_id')):
        raise gr.Error('접수 서비스 또는 작업 ID를 확인할 수 없습니다.')
    current_job_value=current_status_value.get('job')
    if not isinstance(current_job_value,dict):raise gr.Error('생성 상태를 확인할 수 없습니다.')
    current_job_status=current_job_value.get('status')
    if current_job_status not in ('queued','running','completed','failed','cancelled','canceled','paused','unknown'):current_job_status='unknown'
    current_expected_path='/'+current_profile_name+'-generator/jobs/'+current_receipt_value['job_id']+'/result.png'
    current_image_link=' · [생성 이미지 보기]('+current_expected_path+')' if current_job_status=='completed' and current_job_value.get('image')==current_expected_path else ''
    current_result_notice=' · 완료 기록은 있으나 이미지 링크 확인 불가' if current_job_status=='completed' and not current_image_link else ''
    current_source_observation=read_conversation_flux_source_observation(current_profile_name,current_receipt_value['job_id']) if current_job_status=='completed' else None
    if current_source_observation is not None:
        current_image_link=' · [생성 이미지 보기]('+current_source_observation['image']+')' if current_source_observation['status']=='completed' and current_source_observation['result_status']=='available' else ''
        current_result_notice=' · 파일 존재는 조회 시점 기준' if current_image_link else ' · 원본 상태 또는 이미지 파일을 다시 확인하세요.'
    if current_job_status=='completed' and current_source_observation is None:
        current_result_notice+=' · 원본 이미지 상태 조회 불가 · 원 도구에서 다시 확인하세요.'
    current_quality_notice=' · 완료는 결과 품질 승인이나 에셋 등록을 뜻하지 않습니다.' if current_job_status=='completed' else ''
    return current_receipt_value['job_id'],'작업 상태: '+str(current_job_status)+current_result_notice+(' · '+current_job_value['failure_reason'] if isinstance(current_job_value.get('failure_reason'),str) else '')+current_image_link+' · [해당 생성기 결과 확인]('+str(build_conversation_result_link(current_profile_name,current_receipt_value['job_id'],current_session_identifier))+')'+current_quality_notice+(' · 이미지 내용은 별도로 확인하세요.' if current_source_observation is not None and current_image_link else format_media_link_verification_notice(bool(current_image_link)))


def list_hermes_flux_profile_choices(current_profile_name):
    current_history_value=execute_remote_management_command('hermes-agent','hermes-flux-profile-history',{'service':current_profile_name})
    current_choice_values=[(item['request_id']+' · '+item['state'],item['request_id']) for item in current_history_value['records']]
    return gr.update(choices=current_choice_values,value=None),'이 프로필의 최근 접수 '+str(len(current_choice_values))+'건 · 손상된 기록은 제외됩니다.'


def review_hermes_flux_profile_cancellation(current_request_identifier,current_profile_name,current_job_identifier):
    current_status_value=execute_remote_management_command('hermes-agent','hermes-flux-profile-status',{'request_id':current_request_identifier,'service':current_profile_name})
    if not matches_hermes_cancellation_receipt(current_status_value.get('receipt'),current_profile_name,current_job_identifier,current_request_identifier):
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
        current_proposal_record = read_matching_hermes_edit_proposal(current_job_identifier,'hermes-flux-proposal')
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


def read_hermes_flux_receipt(current_request_identifier,current_session_identifier=None):
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    current_result_record = execute_remote_management_command('hermes-agent','hermes-flux-delegation-status',{'request_id':current_request_identifier})
    current_receipt_record = current_result_record['receipt']
    validate_hermes_result_identity(current_receipt_record,current_request_identifier,'flux-image')
    if current_receipt_record.get('state') == 'accepted':
        if current_receipt_record.get('request_id')!=current_request_identifier or current_receipt_record.get('service')!='flux-image' or not validate_service_job_identifier('flux-image',current_receipt_record.get('job_id')):
            raise gr.Error('접수 서비스 또는 작업 ID를 확인할 수 없습니다. 원 서비스의 이력을 확인하세요.')
        current_job_identifier=current_receipt_record['job_id']
        current_job_value=current_result_record.get('job',{})
        current_result_value=current_result_record.get('result',{})
        current_expected_path='/flux-image-generator/jobs/'+current_job_identifier+'/result.png'
        current_image_link=' · [생성 이미지 보기]('+current_expected_path+')' if current_job_value.get('status')=='completed' and current_result_value.get('image')==current_expected_path else ''
        current_result_notice=' · 완료 기록은 있으나 이미지 링크 확인 불가' if current_result_value.get('status')=='unavailable' else ''
        current_failure_notice=' · '+current_job_value['failure_reason'] if current_job_value.get('status')=='failed' and isinstance(current_job_value.get('failure_reason'),str) else ''
        current_source_observation=read_conversation_flux_source_observation('flux-image',current_job_identifier) if current_job_value.get('status')=='completed' else None
        if current_source_observation is not None:
            current_image_link=' · [생성 이미지 보기]('+current_source_observation['image']+')' if current_source_observation['status']=='completed' and current_source_observation['result_status']=='available' else ''
            current_result_notice=' · 파일 존재는 조회 시점 기준' if current_image_link else ' · 원본 상태 또는 이미지 파일을 다시 확인하세요.'
        if current_job_value.get('status')=='completed' and current_source_observation is None:
            current_result_notice+=' · 원본 이미지 상태 조회 불가 · 원 도구에서 다시 확인하세요.'
        current_verification_notice=' · 이미지 내용은 별도로 확인하세요.' if current_source_observation is not None and current_image_link else format_media_link_verification_notice(bool(current_image_link))
        return current_job_identifier,'작업 상태: '+str(current_job_value.get('status','확인 불가'))+current_failure_notice+current_result_notice+current_image_link+' · [일반 이미지 생성기]('+str(build_conversation_result_link('flux-image',current_job_identifier,current_session_identifier))+')'+current_verification_notice
    if current_receipt_record.get('state') == 'unknown':
        return '', '접수 여부 확인 필요 · FLUX 이력을 확인하세요.'
    return '', '접수 기록이 없습니다.'


def read_safe_hermes_flux_receipt(current_request_identifier,current_session_identifier=None):
    return read_safe_hermes_result(read_hermes_flux_receipt,2,current_request_identifier,current_session_identifier)


def review_hermes_flux_cancellation(current_request_identifier, current_job_identifier):
    current_result_record = execute_remote_management_command('hermes-agent','hermes-flux-delegation-status',{'request_id':current_request_identifier})
    current_receipt_record = current_result_record['receipt']
    if not matches_hermes_cancellation_receipt(current_receipt_record,'flux-image',current_job_identifier,current_request_identifier):
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
        current_proposal_record = read_matching_hermes_edit_proposal(current_job_identifier,'hermes-kimodo-proposal')
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
        if current_result_record.get('request_id')!=current_request_identifier or current_result_record.get('service')!='kimodo':
            raise ValueError('접수 ID 또는 서비스가 일치하지 않습니다.')
        from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
        if current_state_value == 'accepted' and validate_service_job_identifier('kimodo',current_result_record.get('job_id')):
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
        if current_receipt_record.get('request_id') != current_request_identifier or current_receipt_record.get('service') != 'kimodo' or current_receipt_record.get('state') != 'accepted' or current_receipt_record.get('job_id') != current_job_identifier:
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


def clear_hermes_service_registration_search():
    """검색어가 바뀌면 이전 페이지와 결과를 제거한다."""
    return 0, [], '검색 조건이 변경됐습니다. 목록을 다시 조회하세요.', None


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


def collect_hermes_service_registration_search(current_search_text,current_offset_value,current_request_token):
    return {'query':current_search_text,'offset':current_offset_value,'token':current_request_token,'values':read_hermes_service_registration_rows(current_search_text,current_offset_value)}


def render_hermes_service_registration_search(current_search_text,current_offset_value,current_request_token,current_result_record):
    if not isinstance(current_result_record,dict) or not isinstance(current_request_token,str) or (current_result_record.get('query'),current_result_record.get('offset'),current_result_record.get('token'))!=(current_search_text,current_offset_value,current_request_token):
        return gr.skip(),gr.skip()
    return current_result_record['values']


def read_hermes_capability_rows(current_search_text=""):
    """공용 기능 목록을 사람이 비교하기 쉬운 행으로 보여 준다."""
    try:
        current_catalog_record = execute_remote_management_command('hermes-agent', 'hermes-capabilities', {})
        current_effect_labels = {'read':'조회', 'write':'원본 저장', 'enqueue':'대기열 접수', 'recovery_possible':'상태 복구 가능', 'cancel_request':'중지 요청', 'local_bookkeeping':'상태 조회·로컬 잠금'}
        current_gpu_labels = {'none':'사용 안 함', 'exclusive':'배타 사용', 'queued':'대기열 사용', 'inspection':'GPU 상태 조회 · 대기열 밖'}
        current_interface_labels={'gui':'화면','mcp':'Codex MCP','isolated_fixed_bridge':'격리 조회'}
        current_retry_labels={'safe':'같은 요청 재시도 가능','request_id':'같은 접수 ID','request_id_or_unknown':'같은 ID · 불확실 시 확인','check_status':'상태 확인'}
        current_all_rows=[[current_record['label'],current_record['command'],', '.join(current_interface_labels.get(current_interface,current_interface) for current_interface in current_record['interfaces']),'필수: '+(', '.join(current_record['required']) or '없음')+' · 선택: '+(', '.join(current_record.get('optional', [])) or '없음'),current_effect_labels.get(current_record['effect'],current_record['effect']),current_gpu_labels.get(current_record['gpu'],current_record['gpu']),current_retry_labels.get(current_record['retry'],current_record['retry']),current_record['note']] for current_record in current_catalog_record['records']]
        for current_tool_record in current_catalog_record.get('mcp_only_tools',[]):
            current_all_rows.append([current_tool_record['label'],current_tool_record['name'],'Codex MCP','필수: '+(', '.join(current_tool_record['required']) or '없음')+' · 선택: '+(', '.join(current_tool_record['optional']) or '없음'),current_effect_labels.get(current_tool_record['effect'],current_tool_record['effect']),current_gpu_labels.get(current_tool_record['gpu'],current_tool_record['gpu']),current_retry_labels.get(current_tool_record['retry'],current_tool_record['retry']),current_tool_record['note']])
        if not isinstance(current_search_text,str) or len(current_search_text)>100:
            raise ValueError('검색어는 100자 이하여야 합니다.')
        current_search_value=current_search_text.strip().casefold()
        current_rows_value=[current_row_value for current_row_value in current_all_rows if not current_search_value or current_search_value in ' '.join(current_row_value).casefold()]
        current_unlisted_commands=current_catalog_record.get('unlisted_commands',[])
        current_status_text='기능 '+str(len(current_rows_value))+'개 / 전체 '+str(len(current_all_rows))+'개 · 작업 변경은 각 확인 절차와 서비스 검증을 따릅니다. MCP 표시는 서버 구현 기준입니다. 현재 Codex 연결의 도구 목록에 없으면 MCP를 다시 연결하세요.'
        if current_unlisted_commands:
            current_status_text+=' 목록에 없는 등록 명령: '+', '.join(current_unlisted_commands)+' · 지원 여부 확인 필요'
        return current_rows_value,current_status_text
    except Exception as current_catalog_error:
        return [], '기능 목록 조회 실패: ' + str(current_catalog_error)


def build_hermes_agent_interface(include_advanced_controls=True):
    with gr.Blocks(title='직접 조회와 작업' if include_advanced_controls else '운영 대화') as hermes_interface_blocks:
        build_generator_changelog(hermes_interface_blocks, 'hermes-agent')
        if include_advanced_controls:
            gr.HTML('<h2>직접 조회와 작업</h2><p>관리 기능을 직접 확인하거나 실행할 수 있습니다. 아래에서 세션과 작업을 선택하면 관련 제안을 불러올 수 있습니다.</p><p><a href="#hermes-direct-controls">직접 기능으로 이동</a></p>')
        if not include_advanced_controls:
            gr.Markdown('## 운영 대화\nHermes에게 관리 상태 확인과 작업을 요청하세요. 실행된 작업과 세부 입력은 해당 도구에서 확인하거나 직접 조작할 수 있습니다.\n\n대화 요청은 GPU를 사용할 수 있습니다. 대기열의 배타 예약은 관리도구 작업에 적용되며 외부 GPU 작업과의 성능 간섭을 막지는 못합니다. 다른 작업 중에는 GPU 상태를 확인하세요.')
        gr.Markdown('화면을 열거나 관리 상태를 새로고침하면 amd-smi로 GPU 프로세스와 메모리를 조회합니다. GPU 생성이나 추론은 시작하지 않으며 조회 결과는 잠시 캐시될 수 있습니다.')
        hermes_management_summary = gr.Markdown('관리 상태를 확인하고 있습니다.')
        hermes_management_refresh = gr.Button('관리 상태 새로고침')
        hermes_management_refresh.click(read_hermes_management_summary, outputs=hermes_management_summary, queue=False)
        hermes_interface_blocks.load(read_hermes_management_summary, outputs=hermes_management_summary, queue=False)
        if include_advanced_controls:
            gr.Markdown('### 연결할 대화 작업\n기존 제안을 불러올 때만 세션과 작업을 선택하세요.')
            with gr.Row():
                hermes_session_control = gr.Dropdown(label='세션', choices=[], interactive=True)
                hermes_session_list_button = gr.Button('세션 목록 새로고침')
                hermes_session_job_selection = gr.Dropdown(label='세션 작업 선택', choices=[], interactive=True)
                hermes_session_job_open = gr.Button('선택 작업 상세 열기')
            hermes_session_list_status = gr.Markdown('세션 목록을 확인하고 있습니다.')
            hermes_session_status = gr.Markdown('세션을 선택하세요.')
            hermes_session_conversation = gr.Chatbot(visible=False, render_markdown=False, allow_file_downloads=False)
            hermes_session_timer = gr.Timer(value=10, active=False)
            with gr.Accordion('이전 세션 작업 찾기',open=False):
                hermes_older_job_input = gr.Textbox(label='이전 작업 ID')
                hermes_older_job_button = gr.Button('이전 작업 선택')
                hermes_older_job_status = gr.Markdown()
            hermes_older_job_button.click(select_older_conversation_job,[hermes_session_control,hermes_older_job_input],[hermes_session_job_selection,hermes_older_job_status],queue=False)
            hermes_session_list_button.click(list_hermes_session_choices,[hermes_session_control],[hermes_session_control,hermes_session_list_status],queue=False)
            hermes_session_control.change(read_hermes_session_conversation,[hermes_session_control,hermes_session_job_selection],[hermes_session_conversation,hermes_session_status,hermes_session_timer,hermes_session_job_selection],queue=False)
            hermes_session_timer.tick(read_hermes_session_conversation,[hermes_session_control,hermes_session_job_selection],[hermes_session_conversation,hermes_session_status,hermes_session_timer,hermes_session_job_selection],queue=False)
            hermes_session_control.change(fn=None, inputs=[hermes_session_control], js="(sessionId)=>{if(/^[a-f0-9]{32}$/.test(sessionId || '')){const returnLink=document.querySelector('#management-return-conversation a');if(/^[a-f0-9]{32}$/.test(sessionId)){if(returnLink)returnLink.setAttribute('href','/management/frame/hermes-agent/?session='+sessionId);const historyLink=document.querySelector('#management-open-history a');if(historyLink)historyLink.setAttribute('href','/management/frame/operations-history/?session='+sessionId);}try{sessionStorage.setItem('slime-management-session',sessionId);}catch(e){}try{localStorage.setItem('slime-management-session',sessionId);}catch(e){}const currentUrl=new URL(window.location.href);if(currentUrl.searchParams.has('session')){if(currentUrl.searchParams.get('session')!==sessionId)currentUrl.searchParams.delete('job');currentUrl.searchParams.set('session',sessionId);window.history.replaceState(window.history.state,'',currentUrl.href);}} return sessionId;}", queue=False)
            hermes_interface_blocks.load(list_hermes_session_choices, inputs=[hermes_session_control], outputs=[hermes_session_control, hermes_session_list_status], js="(sessionId)=>{const linkedSession=new URL(window.location.href).searchParams.get('session');let tabSession=null;let recentSession=null;try{tabSession=sessionStorage.getItem('slime-management-session');}catch(e){}try{recentSession=localStorage.getItem('slime-management-session');}catch(e){}return [[linkedSession,tabSession,recentSession,sessionId].find(value=>typeof value==='string'&&/^[a-f0-9]{32}$/.test(value)) || null];}", preprocess=False, queue=False).then(restore_linked_conversation_job,inputs=[hermes_session_control,hermes_older_job_input],outputs=[hermes_session_job_selection,hermes_older_job_status],js="(sessionId,jobId)=>[sessionId,new URL(window.location.href).searchParams.get('job') || '']",preprocess=False,queue=False)
        else:
            with gr.Group():
                gr.Markdown('### 대화\n관리 상태를 묻거나 필요한 작업을 요청하세요. 예: GPU 대기 상태를 알려줘 · 사용할 빌보드를 찾아줘 · 걷기 동작을 제안해줘. 이전 작업이 끝나면 후속 메시지를 보낼 수 있습니다.')
                gr.Markdown('Kimodo 생성·재개, 모델 준비, 이미지·번역·오디오·영상·작가 AI 제안은 대화 아래에서 검토하고 실행 상태를 확인할 수 있습니다. 맵·에셋 변경 제안은 별도 검토 영역에서 확인합니다. 첨부가 필요한 이미지와 영상은 각각의 첨부 검토 영역을 사용합니다. 작가 변경은 작가 AI 화면에서 전체 근거를 검토한 뒤 대화에서 적용할 수 있습니다. 코딩 변경은 격리 사본에서 검토합니다.')
                with gr.Row():
                    hermes_session_control = gr.Dropdown(label='세션', choices=[], interactive=True)
                    hermes_new_session_button = gr.Button('새 세션')
                    hermes_session_list_button = gr.Button('세션 목록 새로고침')
                hermes_session_draft = gr.State(value=lambda: uuid.uuid4().hex)
                hermes_session_request = gr.State(value=lambda: uuid.uuid4().hex)
                hermes_session_list_status = gr.Markdown('세션 목록을 확인하고 있습니다.')
                hermes_session_conversation = gr.Chatbot(label='대화', value=[], height=420, placeholder='새 세션을 만들거나 기존 세션을 선택한 뒤 요청을 입력하세요.', render_markdown=False, allow_file_downloads=False)
                hermes_session_status = gr.Markdown('세션을 선택하거나 새로 만드세요.')
                with gr.Row():
                    hermes_session_job_selection = gr.Dropdown(label='세션 작업 선택', choices=[], interactive=True)
                    if include_advanced_controls:
                        hermes_session_job_open = gr.Button('선택 작업 상세 열기')
                    hermes_history_link_button = gr.Button('운영 이력에서 찾기')
                    hermes_proposal_route_button=gr.Button('이 작업의 제안 확인',variant='primary')
                hermes_history_link_display=gr.HTML()
                hermes_history_link_button.click(build_conversation_history_link,[hermes_session_control,hermes_session_job_selection],[hermes_history_link_display],queue=False)
                hermes_proposal_route_state=gr.State(None)
                hermes_proposal_route_status=gr.Markdown('세션 작업을 선택해 제안을 찾을 수 있습니다.')
                with gr.Accordion('이전 세션 작업 찾기',open=False):
                    gr.Markdown('운영 이력에서 확인한 작업 ID를 입력하면 이 세션의 완료 작업인지 확인합니다.')
                    hermes_older_job_input=gr.Textbox(label='이전 작업 ID')
                    hermes_older_job_button=gr.Button('이전 작업 선택')
                    hermes_older_job_status=gr.Markdown()
                    hermes_older_job_button.click(select_older_conversation_job,[hermes_session_control,hermes_older_job_input],[hermes_session_job_selection,hermes_older_job_status],queue=False)
                    hermes_session_control.change(lambda:('', ''),outputs=[hermes_older_job_input,hermes_older_job_status],queue=False)
                with gr.Accordion('선택한 대화의 작업 제안', open=False) as hermes_service_proposal_area:
                    gr.Markdown('위에서 제안을 만든 완료 작업을 선택하고 내용을 확인하세요. 값 변경은 대화에서 새 제안을 요청하세요. 이 화면에서 같은 제안을 다시 열면 기존 접수를 확인합니다. 기존 도구에서 별도로 접수한 작업은 자동 연결되지 않습니다. Kimodo·FLUX·영상의 작업 상태 조회와 영상 재개 검토에는 기존 중단 작업 복구가 따를 수 있습니다.')
                    hermes_conversation_service_kind = gr.Dropdown(label='제안 종류', choices=[('Kimodo 모션','kimodo'),('FLUX 이미지','flux'),('번역','translation'),('음악·효과음','audio'),('텍스트 영상','video'),('작가 AI','writer'),('모델 준비','model_preparation'),('Kimodo 재개','kimodo_resume'),('FLUX 재개','flux_resume'),('영상 재개','video_resume')],value='kimodo',interactive=True)
                    hermes_conversation_kimodo_card = gr.State(None)
                    hermes_conversation_kimodo_open = gr.Button('선택한 제안 확인')
                    hermes_conversation_kimodo_preview = gr.Textbox(label='검토할 작업 내용', lines=7, interactive=False)
                    hermes_conversation_kimodo_status = gr.Markdown('아직 제안을 확인하지 않았습니다.')
                    with gr.Row():
                        hermes_conversation_kimodo_submit = gr.Button('확인한 작업을 대기열에 추가', variant='primary', interactive=False)
                        hermes_conversation_kimodo_refresh = gr.Button('작업 상태와 결과 확인')
                    hermes_conversation_status_token=gr.State(None)
                    hermes_conversation_status_result=gr.State(None)
                    hermes_conversation_status_inputs=[hermes_conversation_kimodo_card,hermes_session_control,hermes_session_job_selection,hermes_conversation_service_kind]
                    hermes_conversation_kimodo_refresh.click(create_conversation_status_token,outputs=hermes_conversation_status_token,queue=False).then(collect_conversation_status_result,[*hermes_conversation_status_inputs,hermes_conversation_status_token],hermes_conversation_status_result,queue=False,trigger_mode='multiple').then(render_conversation_status_result,[*hermes_conversation_status_inputs,hermes_conversation_status_token,hermes_conversation_status_result],hermes_conversation_kimodo_status,queue=False)
                    for current_status_selection in hermes_conversation_status_inputs:
                        current_status_selection.change(create_conversation_status_token,outputs=hermes_conversation_status_token,queue=False)
                    with gr.Group(visible=True) as current_chat_kimodo_frame_group:
                        gr.Markdown('### Kimodo 원본 프레임과 키프레임 저장\n이 대화에서 접수한 완료 작업의 현재 시도를 확인합니다. 프레임을 보고 태그를 입력한 뒤 저장 내용을 검토하세요.')
                        current_chat_kimodo_frame_number=gr.Number(label='원본 프레임 번호 · 1부터',value=1,minimum=1,maximum=1000,precision=0)
                        current_chat_kimodo_frame_button=gr.Button('대화 작업의 원본 프레임 확인',interactive=False)
                        current_chat_kimodo_frame_notice=gr.Markdown('Kimodo 제안을 연 뒤 확인하세요.')
                        current_chat_kimodo_frame_token=gr.State(None)
                        current_chat_kimodo_frame_result=gr.State(None)
                        current_chat_kimodo_frame_inputs=[hermes_conversation_kimodo_card,hermes_session_control,hermes_session_job_selection,hermes_conversation_service_kind,current_chat_kimodo_frame_number]
                        current_chat_kimodo_frame_button.click(create_conversation_status_token,outputs=current_chat_kimodo_frame_token,queue=False).then(collect_conversation_kimodo_frame,[*current_chat_kimodo_frame_inputs,current_chat_kimodo_frame_token],current_chat_kimodo_frame_result,queue=False,trigger_mode='multiple').then(render_conversation_kimodo_frame,[*current_chat_kimodo_frame_inputs,current_chat_kimodo_frame_token,current_chat_kimodo_frame_result],current_chat_kimodo_frame_notice,queue=False)
                        for current_frame_selection in current_chat_kimodo_frame_inputs:
                            current_frame_selection.change(lambda:(create_conversation_status_token(),'선택 또는 프레임이 바뀌었습니다. 다시 확인하세요.'),outputs=[current_chat_kimodo_frame_token,current_chat_kimodo_frame_notice],queue=False).then(update_conversation_kimodo_frame_button,hermes_conversation_status_inputs,current_chat_kimodo_frame_button,queue=False)
                        current_chat_kimodo_frame_number.input(lambda:(create_conversation_status_token(),'프레임 번호가 바뀌었습니다. 다시 확인하세요.'),outputs=[current_chat_kimodo_frame_token,current_chat_kimodo_frame_notice],queue=False)
                        current_chat_keyframe_tag=gr.Textbox(label='저장할 키프레임 태그',max_lines=1)
                        current_chat_keyframe_review=gr.Button('키프레임 저장 검토')
                        current_chat_keyframe_review_state=gr.State(None)
                        current_chat_keyframe_review_result=gr.State(None)
                        current_chat_keyframe_review_token=gr.State(None)
                        current_chat_keyframe_receipt_token=gr.State(None)
                        current_chat_keyframe_saved_preview_token=gr.State(None)
                        current_chat_keyframe_saved_preview_result=gr.State(None)
                        current_chat_keyframe_submit_result=gr.State(None)
                        current_chat_keyframe_receipt_result=gr.State(None)
                        current_chat_keyframe_review_notice=gr.Markdown('원본 프레임을 확인하고 태그를 입력하세요.')
                        current_chat_keyframe_confirm=gr.Checkbox(label='위 원본과 태그를 확인했으며 독립 키프레임 저장에 동의합니다.',value=False)
                        with gr.Row():
                            current_chat_keyframe_save=gr.Button('확인한 키프레임 저장',variant='primary',interactive=False)
                            current_chat_keyframe_receipt=gr.Button('키프레임 저장 접수 확인')
                        current_chat_keyframe_status=gr.Markdown('저장 후 결과를 확인할 수 있습니다.')
                        current_chat_keyframe_saved_preview=gr.Button('저장된 키프레임 검증·보기')
                        current_chat_keyframe_saved_image=gr.Image(label='저장된 키프레임',interactive=False,type='pil')
                        current_chat_keyframe_saved_notice=gr.Markdown('저장 완료 후 사본을 다시 검증할 수 있습니다.')
                        current_chat_keyframe_selected=gr.State(None)
                        current_chat_keyframe_selection_token=gr.State(None)
                        current_chat_keyframe_selection_result=gr.State(None)
                        current_chat_keyframe_attachment_token=gr.State(None)
                        current_chat_keyframe_attachment_result=gr.State(None)
                        current_chat_keyframe_selected_notice=gr.Markdown('다음 제안에 사용할 키프레임을 선택할 수 있습니다.')
                        current_chat_keyframe_select=gr.Button('저장된 키프레임을 다음 제안에 사용')
                        current_chat_keyframe_output_frame=gr.Number(label='다음 생성의 출력 프레임 · 1부터',value=1,minimum=1,maximum=1000,precision=0)
                        current_chat_keyframe_attach_review=gr.Button('선택 키프레임으로 현재 제안 검토')
                        current_chat_keyframe_select.click(create_conversation_status_token,outputs=current_chat_keyframe_selection_token,queue=False).then(collect_conversation_saved_keyframe_selection,[current_chat_keyframe_review_state,hermes_session_control,current_chat_keyframe_selection_token],current_chat_keyframe_selection_result,queue=False,trigger_mode='multiple').then(render_conversation_saved_keyframe_selection,[current_chat_keyframe_review_state,hermes_session_control,current_chat_keyframe_selection_token,current_chat_keyframe_selection_result],[current_chat_keyframe_selected,current_chat_keyframe_selected_notice],queue=False)
                        for current_selection_input in (current_chat_keyframe_review_state,hermes_session_control):
                            current_selection_input.change(create_conversation_status_token,outputs=current_chat_keyframe_selection_token,queue=False)
                        hermes_session_control.change(lambda:(None,'다음 제안에 사용할 키프레임을 선택할 수 있습니다.'),outputs=[current_chat_keyframe_selected,current_chat_keyframe_selected_notice],queue=False)
                        current_chat_keyframe_attachment_inputs=[current_chat_keyframe_selected,hermes_session_control,hermes_session_job_selection,hermes_conversation_service_kind,current_chat_keyframe_output_frame]
                        current_chat_keyframe_attach_review_event=current_chat_keyframe_attach_review.click(begin_conversation_keyframe_attachment_review,outputs=[current_chat_keyframe_attachment_token,hermes_conversation_kimodo_card,hermes_conversation_kimodo_preview,hermes_conversation_kimodo_status,hermes_conversation_kimodo_submit],queue=False).then(collect_conversation_keyframe_attachment_review,[*current_chat_keyframe_attachment_inputs,current_chat_keyframe_attachment_token],current_chat_keyframe_attachment_result,queue=False,trigger_mode='multiple').then(render_conversation_keyframe_attachment_review,[*current_chat_keyframe_attachment_inputs,current_chat_keyframe_attachment_token,current_chat_keyframe_attachment_result],[hermes_conversation_kimodo_card,hermes_conversation_kimodo_preview,hermes_conversation_kimodo_status],queue=False)
                        for current_attachment_selection in current_chat_keyframe_attachment_inputs:
                            current_attachment_selection.change(create_conversation_status_token,outputs=current_chat_keyframe_attachment_token,queue=False)
                        current_chat_keyframe_output_frame.input(create_conversation_status_token,outputs=current_chat_keyframe_attachment_token,queue=False)
                        for current_attachment_input in (current_chat_keyframe_selected,current_chat_keyframe_output_frame):
                            current_attachment_input.change(invalidate_conversation_keyframe_attachment,hermes_conversation_kimodo_card,[hermes_conversation_kimodo_card,hermes_conversation_kimodo_submit],queue=False)
                        current_chat_keyframe_output_frame.input(invalidate_conversation_keyframe_attachment,hermes_conversation_kimodo_card,[hermes_conversation_kimodo_card,hermes_conversation_kimodo_submit],queue=False)
                        current_chat_keyframe_review_inputs=[*current_chat_kimodo_frame_inputs,current_chat_keyframe_tag,current_chat_kimodo_frame_token]
                        current_chat_keyframe_review.click(begin_conversation_kimodo_keyframe_review,outputs=[current_chat_keyframe_review_token,current_chat_keyframe_review_state,current_chat_keyframe_confirm,current_chat_keyframe_save,current_chat_keyframe_review_notice],queue=False).then(collect_conversation_kimodo_keyframe_review,[*current_chat_keyframe_review_inputs,current_chat_keyframe_review_token,current_chat_kimodo_frame_result],current_chat_keyframe_review_result,queue=False,trigger_mode='multiple').then(render_conversation_kimodo_keyframe_review,[*current_chat_keyframe_review_inputs,current_chat_keyframe_review_token,current_chat_keyframe_review_result],[current_chat_keyframe_review_state,current_chat_keyframe_review_notice,current_chat_keyframe_confirm,current_chat_keyframe_save],queue=False)
                        current_chat_keyframe_submit_inputs=[current_chat_keyframe_review_state,*current_chat_kimodo_frame_inputs,current_chat_keyframe_tag,current_chat_kimodo_frame_token]
                        current_chat_keyframe_save.click(collect_conversation_kimodo_keyframe_submit,[*current_chat_keyframe_submit_inputs,current_chat_keyframe_confirm],current_chat_keyframe_submit_result,queue=False,trigger_mode='multiple').then(render_conversation_kimodo_keyframe_submit,[*current_chat_keyframe_submit_inputs,current_chat_keyframe_submit_result],[current_chat_keyframe_status,current_chat_keyframe_save],queue=False)
                        current_chat_keyframe_receipt.click(create_conversation_status_token,outputs=current_chat_keyframe_receipt_token,queue=False).then(collect_conversation_kimodo_keyframe_receipt,[*current_chat_keyframe_submit_inputs,current_chat_keyframe_receipt_token],current_chat_keyframe_receipt_result,queue=False,trigger_mode='multiple').then(render_conversation_kimodo_keyframe_receipt,[*current_chat_keyframe_submit_inputs,current_chat_keyframe_receipt_token,current_chat_keyframe_receipt_result],current_chat_keyframe_status,queue=False)
                        current_chat_keyframe_saved_preview.click(create_conversation_status_token,outputs=current_chat_keyframe_saved_preview_token,queue=False).then(collect_conversation_saved_keyframe_preview,[*current_chat_keyframe_submit_inputs,current_chat_keyframe_saved_preview_token],current_chat_keyframe_saved_preview_result,queue=False,trigger_mode='multiple').then(render_conversation_saved_keyframe_preview,[*current_chat_keyframe_submit_inputs,current_chat_keyframe_saved_preview_token,current_chat_keyframe_saved_preview_result],[current_chat_keyframe_saved_image,current_chat_keyframe_saved_notice],queue=False)
                        for current_keyframe_input in [*current_chat_kimodo_frame_inputs,current_chat_keyframe_tag,current_chat_kimodo_frame_token]:
                            current_keyframe_input.change(lambda:(None,False,gr.update(interactive=False),'입력이 바뀌었습니다. 다시 검토하세요.','선택한 원본의 접수 결과가 여기에 표시됩니다.',None,'저장 완료 후 사본을 다시 검증할 수 있습니다.'),outputs=[current_chat_keyframe_review_state,current_chat_keyframe_confirm,current_chat_keyframe_save,current_chat_keyframe_review_notice,current_chat_keyframe_status,current_chat_keyframe_saved_image,current_chat_keyframe_saved_notice],queue=False)
                        current_chat_keyframe_tag.input(lambda:(None,False,gr.update(interactive=False),'태그가 바뀌었습니다. 다시 검토하세요.','선택한 원본의 접수 결과가 여기에 표시됩니다.',None,'저장 완료 후 사본을 다시 검증할 수 있습니다.'),outputs=[current_chat_keyframe_review_state,current_chat_keyframe_confirm,current_chat_keyframe_save,current_chat_keyframe_review_notice,current_chat_keyframe_status,current_chat_keyframe_saved_image,current_chat_keyframe_saved_notice],queue=False)
                        hermes_conversation_service_kind.change(lambda current_kind_value:gr.update(visible=current_kind_value=='kimodo'),inputs=hermes_conversation_service_kind,outputs=current_chat_kimodo_frame_group,queue=False)
                    hermes_conversation_model_prepare=gr.Button('모델 준비 요청 검토',visible=False,interactive=False)
                    hermes_conversation_model_confirmation=gr.State(None)
                    with gr.Group(visible=False) as hermes_conversation_model_confirm_group:
                        gr.Markdown('### 모델 준비를 요청할까요?\n서비스에 따라 다운로드와 디스크 사용이 발생하며 GPU 작업이 시작되거나 대기열에 등록될 수 있습니다. 위에서 확인한 서비스와 접수 ID로 요청합니다.')
                        with gr.Row():
                            hermes_conversation_model_cancel=gr.Button('요청하지 않기')
                            hermes_conversation_model_confirm=gr.Button('확인 후 모델 준비 요청',variant='primary')
                    hermes_conversation_service_kind.change(lambda current_kind_value:(gr.update(visible=current_kind_value!='model_preparation'),gr.update(visible=current_kind_value=='model_preparation'),None,gr.update(visible=False)),[hermes_conversation_service_kind],[hermes_conversation_kimodo_submit,hermes_conversation_model_prepare,hermes_conversation_model_confirmation,hermes_conversation_model_confirm_group],queue=False)
                    hermes_conversation_model_prepare.click(prepare_conversation_model_confirmation,[hermes_conversation_kimodo_card,hermes_session_control,hermes_session_job_selection,hermes_conversation_service_kind],[hermes_conversation_model_confirmation,hermes_conversation_model_confirm_group],queue=False)
                    hermes_conversation_model_cancel.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_conversation_model_confirmation,hermes_conversation_model_confirm_group],queue=False)
                    hermes_conversation_model_confirm.click(submit_conversation_model_confirmation,[hermes_conversation_model_confirmation,hermes_conversation_kimodo_card,hermes_session_control,hermes_session_job_selection,hermes_conversation_service_kind],[hermes_conversation_kimodo_card,hermes_conversation_kimodo_status,hermes_conversation_model_confirmation,hermes_conversation_model_confirm_group],trigger_mode='once',concurrency_limit=1).success(lambda:gr.update(interactive=False),outputs=[hermes_conversation_model_prepare],queue=False)
                    with gr.Group(visible=False) as hermes_conversation_writer_section:
                        hermes_conversation_writer_detail_button=gr.Button('작가 결과와 변경 조회')
                        hermes_conversation_writer_detail=gr.Textbox(label='작가 결과와 제한된 변경',lines=14,max_lines=28,interactive=False)
                        hermes_conversation_writer_detail_status=gr.Markdown('작가 제안을 확인한 뒤 결과를 조회하세요.')
                        with gr.Accordion('검색·제안 원본 읽기',open=False):
                            gr.Markdown('선택한 작가 작업의 자료를 부분별로 읽습니다. 원본 자료는 적용되지 않습니다.')
                            hermes_writer_material_section=gr.Radio(label='자료',choices=[('검색 결과','search'),('제안','proposal')],value='proposal')
                            with gr.Row():
                                hermes_writer_material_first=gr.Button('처음부터 읽기')
                                hermes_writer_material_next=gr.Button('다음 부분',interactive=False)
                            hermes_writer_material_text=gr.Textbox(label='작가 자료 JSON',lines=12,max_lines=24,interactive=False)
                            hermes_writer_material_status=gr.Markdown('자료를 선택하고 처음부터 읽으세요.')
                            hermes_writer_material_state=gr.State(None)
                        hermes_conversation_writer_checked=gr.Checkbox(label='작가 AI 화면에서 전체 변경과 탐색 근거를 확인했습니다.',value=False)
                        hermes_conversation_writer_apply_review=gr.Button('작가 변경 적용 검토')
                        hermes_conversation_writer_apply_record=gr.State(None)
                        hermes_conversation_writer_apply_status=gr.Markdown('전체 검토 후 적용 대상을 확인하세요.')
                        with gr.Group(visible=False) as hermes_conversation_writer_apply_confirm:
                            gr.Markdown('확인하면 작가 제안이 실제 문서 원본에 적용됩니다.')
                            with gr.Row():
                                hermes_conversation_writer_apply_cancel=gr.Button('적용하지 않기')
                                hermes_conversation_writer_apply_send=gr.Button('확인 후 원본 적용',variant='primary')
                    hermes_conversation_writer_apply_inputs=[hermes_conversation_kimodo_card,hermes_session_control,hermes_session_job_selection,hermes_conversation_service_kind,hermes_conversation_writer_checked]
                    hermes_conversation_writer_apply_review.click(prepare_conversation_writer_apply,hermes_conversation_writer_apply_inputs,[hermes_conversation_writer_apply_record,hermes_conversation_writer_apply_confirm,hermes_conversation_writer_apply_status],queue=False)
                    hermes_conversation_writer_apply_cancel.click(lambda:(None,gr.update(visible=False),'적용하지 않았습니다.'),outputs=[hermes_conversation_writer_apply_record,hermes_conversation_writer_apply_confirm,hermes_conversation_writer_apply_status],queue=False)
                    hermes_conversation_writer_apply_send.click(submit_conversation_writer_apply,[hermes_conversation_writer_apply_record,*hermes_conversation_writer_apply_inputs],[hermes_conversation_writer_apply_record,hermes_conversation_writer_apply_confirm,hermes_conversation_writer_apply_status],queue=False)
                    hermes_conversation_writer_checked.change(lambda:(None,gr.update(visible=False)),outputs=[hermes_conversation_writer_apply_record,hermes_conversation_writer_apply_confirm],queue=False)
                    hermes_conversation_writer_detail_button.click(read_conversation_writer_details_text,[hermes_conversation_kimodo_card,hermes_session_control,hermes_session_job_selection,hermes_conversation_service_kind],[hermes_conversation_writer_detail,hermes_conversation_writer_detail_status],queue=False)
                    hermes_writer_material_inputs=[hermes_conversation_kimodo_card,hermes_session_control,hermes_session_job_selection,hermes_conversation_service_kind,hermes_writer_material_section,hermes_writer_material_state]
                    hermes_writer_material_outputs=[hermes_writer_material_text,hermes_writer_material_state,hermes_writer_material_next,hermes_writer_material_status]
                    hermes_writer_material_token=gr.State(None)
                    hermes_writer_material_result=gr.State(None)
                    for current_material_button,current_next_requested in ((hermes_writer_material_first,False),(hermes_writer_material_next,True)):
                        current_material_button.click(lambda:uuid.uuid4().hex,outputs=hermes_writer_material_token,queue=False).then(lambda *current_values,_next=current_next_requested:collect_conversation_writer_material(*current_values,_next),[*hermes_writer_material_inputs,hermes_writer_material_token],hermes_writer_material_result,queue=False,trigger_mode='multiple').then(render_conversation_writer_material,[hermes_conversation_kimodo_card,hermes_session_control,hermes_session_job_selection,hermes_conversation_service_kind,hermes_writer_material_section,hermes_writer_material_token,hermes_writer_material_result],hermes_writer_material_outputs,queue=False)
                    for current_material_selection in (hermes_conversation_kimodo_card,hermes_session_control,hermes_session_job_selection,hermes_conversation_service_kind,hermes_writer_material_section):
                        current_material_selection.change(lambda:uuid.uuid4().hex,outputs=hermes_writer_material_token,queue=False)
                    for current_material_selection in (hermes_conversation_kimodo_card,hermes_conversation_service_kind,hermes_writer_material_section):
                        current_material_selection.change(lambda:('',None,gr.update(interactive=False),'선택이 바뀌었습니다. 처음부터 다시 읽으세요.'),outputs=hermes_writer_material_outputs,queue=False)
                    hermes_conversation_writer_reset_outputs=[hermes_conversation_writer_detail,hermes_conversation_writer_detail_status,hermes_conversation_writer_checked,hermes_conversation_writer_apply_record,hermes_conversation_writer_apply_confirm,hermes_conversation_writer_apply_status,hermes_conversation_kimodo_card,hermes_conversation_kimodo_preview,hermes_conversation_kimodo_status,hermes_conversation_kimodo_submit]
                    hermes_conversation_kimodo_open_event=hermes_conversation_kimodo_open.click(reset_conversation_writer_review,outputs=hermes_conversation_writer_reset_outputs,queue=False).then(prepare_conversation_service_review,[hermes_session_control,hermes_session_job_selection,hermes_conversation_service_kind],[hermes_conversation_kimodo_card,hermes_conversation_kimodo_preview,hermes_conversation_kimodo_status],queue=False)
                    hermes_conversation_kimodo_open_event.success(refresh_conversation_model_readiness,[hermes_conversation_kimodo_card,hermes_session_control,hermes_session_job_selection,hermes_conversation_service_kind],[hermes_conversation_model_prepare],queue=False)
                    hermes_conversation_kimodo_open_event.success(update_conversation_kimodo_frame_button,hermes_conversation_status_inputs,current_chat_kimodo_frame_button,queue=False)
                    hermes_conversation_service_kind.input(lambda: (None, '', '종류가 바뀌었습니다. 제안을 다시 확인하세요.', gr.update(interactive=False), None, '작가 제안을 확인한 뒤 결과를 조회하세요.'), outputs=[hermes_conversation_kimodo_card, hermes_conversation_kimodo_preview, hermes_conversation_kimodo_status, hermes_conversation_kimodo_submit, hermes_conversation_writer_detail, hermes_conversation_writer_detail_status], queue=False)
                    hermes_conversation_service_kind.change(lambda current_kind:gr.update(visible=current_kind=='writer'),inputs=[hermes_conversation_service_kind],outputs=[hermes_conversation_writer_section],queue=False)
                    hermes_conversation_service_kind.change(lambda:(False,None,gr.update(visible=False),'전체 검토 후 적용 대상을 확인하세요.'),outputs=[hermes_conversation_writer_checked,hermes_conversation_writer_apply_record,hermes_conversation_writer_apply_confirm,hermes_conversation_writer_apply_status],queue=False)
                    bind_gpu_generation_confirmation(hermes_conversation_kimodo_submit, submit_conversation_service_review, [hermes_conversation_kimodo_card, hermes_session_control, hermes_session_job_selection, hermes_conversation_service_kind], [hermes_conversation_kimodo_card, hermes_conversation_kimodo_status], generation_readiness_callback=lambda current_card_value: isinstance(current_card_value, dict) and current_card_value.get('ready') is True, generation_readiness_inputs=[hermes_conversation_kimodo_card], generation_readiness_events=[hermes_conversation_kimodo_open_event,current_chat_keyframe_attach_review_event], generation_confirmation_validator=match_hermes_confirmation_inputs, generation_confirmation_inputs=[hermes_conversation_kimodo_card, hermes_session_control, hermes_session_job_selection, hermes_conversation_service_kind])
                with gr.Accordion('선택한 대화의 맵·에셋 변경 제안', open=False) as hermes_edit_proposal_area:
                    gr.Markdown('제안을 만든 완료 작업을 선택하고 변경 전후와 영향을 확인하세요. 저장하면 실제 원본과 연결된 데이터가 바뀝니다. 상세 이미지와 배치는 해당 도구에서 검수하세요.')
                    hermes_conversation_edit_kind=gr.Dropdown(label='변경 종류',choices=[('빌보드 공용 속성','billboard'),('건물 앵커','building'),('이펙트 좌표','effect'),('야외 맵 셀','field'),('도시 맵','city'),('스프라이트 앵커','sprite')],value='billboard')
                    hermes_conversation_edit_card=gr.State(None)
                    hermes_conversation_edit_confirmed=gr.State(None)
                    hermes_conversation_edit_open=gr.Button('선택한 변경 제안 확인')
                    hermes_conversation_edit_preview=gr.Textbox(label='원본과 변경 검토',lines=9,interactive=False)
                    hermes_conversation_edit_image=gr.Image(label='스프라이트 미리보기',interactive=False,visible=True)
                    hermes_conversation_edit_status=gr.Markdown('아직 변경을 확인하지 않았습니다.')
                    with gr.Row():
                        hermes_conversation_edit_review=gr.Button('변경 저장 검토',interactive=False)
                        hermes_conversation_edit_refresh=gr.Button('저장 결과 확인')
                    with gr.Group(visible=False) as hermes_conversation_edit_confirm:
                        gr.Markdown('실제 원본과 관련 데이터가 변경됩니다. 검토한 변경을 저장할까요?')
                        with gr.Row():
                            hermes_conversation_edit_cancel=gr.Button('저장하지 않기')
                            hermes_conversation_edit_save=gr.Button('확인 후 변경 저장',variant='primary')
                    hermes_conversation_edit_reset_outputs=[hermes_conversation_edit_card,hermes_conversation_edit_preview,hermes_conversation_edit_image,hermes_conversation_edit_status,hermes_conversation_edit_confirmed,hermes_conversation_edit_confirm,hermes_conversation_edit_review,hermes_proposal_route_status]
                    hermes_conversation_edit_open.click(reset_conversation_edit_review,outputs=hermes_conversation_edit_reset_outputs,queue=False).then(open_conversation_edit_review,[hermes_session_control,hermes_session_job_selection,hermes_conversation_edit_kind],[hermes_conversation_edit_card,hermes_conversation_edit_preview,hermes_conversation_edit_image,hermes_conversation_edit_status],queue=False)
                    hermes_conversation_edit_card.change(lambda current_card:gr.update(interactive=isinstance(current_card,dict) and current_card.get('ready') is True),[hermes_conversation_edit_card],hermes_conversation_edit_review,queue=False)
                    hermes_conversation_edit_refresh.click(read_conversation_edit_result,[hermes_conversation_edit_card,hermes_session_control,hermes_session_job_selection,hermes_conversation_edit_kind],hermes_conversation_edit_status,queue=False)
                    hermes_conversation_edit_review.click(lambda current_card:(current_card,gr.update(visible=True)),inputs=hermes_conversation_edit_card,outputs=[hermes_conversation_edit_confirmed,hermes_conversation_edit_confirm],queue=False)
                    hermes_conversation_edit_cancel.click(lambda:(None,gr.update(visible=False)),outputs=[hermes_conversation_edit_confirmed,hermes_conversation_edit_confirm],queue=False)
                    hermes_conversation_edit_save.click(submit_confirmed_conversation_edit,[hermes_conversation_edit_confirmed,hermes_conversation_edit_card,hermes_session_control,hermes_session_job_selection,hermes_conversation_edit_kind],[hermes_conversation_edit_card,hermes_conversation_edit_status],queue=False).success(lambda:(None,gr.update(visible=False)),outputs=[hermes_conversation_edit_confirmed,hermes_conversation_edit_confirm],queue=False)
                    hermes_conversation_edit_kind.input(lambda:(None,'',None,'선택이 바뀌었습니다. 변경을 다시 확인하세요.',gr.update(visible=False),gr.update(interactive=False)),outputs=[hermes_conversation_edit_card,hermes_conversation_edit_preview,hermes_conversation_edit_image,hermes_conversation_edit_status,hermes_conversation_edit_confirm,hermes_conversation_edit_review],queue=False)
                with gr.Accordion('선택한 대화의 첨부 이미지 제안',open=False) as hermes_image_proposal_area:
                    gr.Markdown('마네킨·빌보드·건물 제안은 첫 참조가 필수입니다. 표정 제안은 얼굴 참조 한 장을 첨부합니다. 검토에는 PNG 크기와 SHA-256이 표시됩니다. 상태 조회 시 기존 중단 작업 복구가 따를 수 있습니다.')
                    with gr.Accordion('등록된 표정 찾기',open=False):
                        current_expression_catalog_query=gr.Textbox(label='표정 이름 또는 ID 검색')
                        current_expression_catalog_page=gr.State(None)
                        with gr.Row():
                            current_expression_catalog_search=gr.Button('표정 검색')
                            current_expression_catalog_next=gr.Button('다음 표정',interactive=False)
                        current_expression_catalog_table=gr.Dataframe(headers=['표정','ID'],datatype=['str','str'],interactive=False,type='array',label='등록 표정')
                        current_expression_catalog_notice=gr.Markdown('표정을 검색하세요.')
                        current_expression_catalog_outputs=[current_expression_catalog_table,current_expression_catalog_notice,current_expression_catalog_page,current_expression_catalog_next]
                        current_expression_catalog_search.click(read_conversation_expression_catalog,[current_expression_catalog_query],current_expression_catalog_outputs,queue=False)
                        current_expression_catalog_query.submit(read_conversation_expression_catalog,[current_expression_catalog_query],current_expression_catalog_outputs,queue=False)
                        current_expression_catalog_next.click(read_next_conversation_expression_catalog,[current_expression_catalog_query,current_expression_catalog_page],current_expression_catalog_outputs,queue=False)
                        current_expression_catalog_query.change(lambda:([],'검색 조건이 바뀌었습니다. 다시 검색하세요.',None,gr.update(interactive=False)),outputs=current_expression_catalog_outputs,queue=False)
                    current_flux_reference_source=gr.State(None)
                    current_flux_reference_review=gr.State(None)
                    current_flux_reference_open=gr.Button('첨부 이미지 제안 열기')
                    with gr.Row():
                        current_flux_reference_first=gr.Image(label='첫 참조 이미지 · 필수',type='pil')
                        current_flux_reference_second=gr.Image(label='두 번째 참조 이미지 · 표정은 사용 안 함',type='pil')
                    current_flux_reference_preview=gr.Markdown()
                    current_flux_reference_status=gr.Markdown('세션 작업에서 FLUX 제안을 선택하세요.')
                    with gr.Row():
                        current_flux_reference_check=gr.Button('이미지 입력과 첨부 검토')
                        current_flux_reference_send=gr.Button('이미지 작업 대기열에 추가',interactive=False)
                        current_flux_reference_read=gr.Button('이미지 상태와 결과 확인')
                    current_flux_reference_inputs=[current_flux_reference_source,hermes_session_control,hermes_session_job_selection,current_flux_reference_first,current_flux_reference_second]
                    current_flux_reference_open.click(open_conversation_flux_reference_safely,[hermes_session_control,hermes_session_job_selection],[current_flux_reference_source,current_flux_reference_first,current_flux_reference_second,current_flux_reference_review,current_flux_reference_preview,current_flux_reference_status,current_flux_reference_send],queue=False)
                    current_flux_reference_review_event=current_flux_reference_check.click(review_conversation_flux_reference,current_flux_reference_inputs,[current_flux_reference_review,current_flux_reference_preview,current_flux_reference_status],queue=False)
                    current_flux_status_token=gr.State(None)
                    current_flux_status_result=gr.State(None)
                    current_flux_status_kind=gr.State('image')
                    current_flux_status_inputs=[current_flux_reference_source,hermes_session_control,hermes_session_job_selection,current_flux_status_kind]
                    current_flux_reference_read.click(create_conversation_status_token,outputs=current_flux_status_token,queue=False).then(collect_attachment_status_result,[*current_flux_status_inputs,current_flux_status_token],current_flux_status_result,queue=False,trigger_mode='multiple').then(render_attachment_status_result,[*current_flux_status_inputs,current_flux_status_token,current_flux_status_result],current_flux_reference_status,queue=False)
                    for current_status_selection in (current_flux_reference_source,hermes_session_control,hermes_session_job_selection):
                        current_status_selection.change(create_conversation_status_token,outputs=current_flux_status_token,queue=False)
                    for current_status_selection in (hermes_session_control,hermes_session_job_selection):
                        current_status_selection.change(lambda:'세션이나 작업이 바뀌었습니다. 이미지 제안을 다시 여세요.',outputs=current_flux_reference_status,queue=False)
                    for current_flux_reference_input in current_flux_reference_inputs:
                        current_flux_reference_input.change(lambda:(None,'',gr.update(interactive=False)),outputs=[current_flux_reference_review,current_flux_reference_preview,current_flux_reference_send],queue=False)
                    bind_gpu_generation_confirmation(current_flux_reference_send,submit_conversation_flux_reference,[current_flux_reference_review,*current_flux_reference_inputs],[current_flux_reference_review,current_flux_reference_status],generation_readiness_callback=lambda current_review:bool(current_review),generation_readiness_inputs=[current_flux_reference_review],generation_readiness_events=[current_flux_reference_review_event],generation_confirmation_validator=match_hermes_confirmation_inputs,generation_confirmation_inputs=[current_flux_reference_review,*current_flux_reference_inputs])
                with gr.Accordion('선택한 대화의 첨부 영상 제안', open=False) as hermes_video_proposal_area:
                    gr.Markdown('제안의 서비스와 모드에 필요한 PNG·MP4를 첨부하고 기본 설정을 검토합니다. 첨부 합계는 24 MiB 이하입니다. 실제 생성은 확인 후 공용 GPU 대기열에서 실행됩니다. 상태 조회 시 기존 중단 작업 복구가 따를 수 있습니다.')
                    hermes_conversation_video_source=gr.State(None)
                    hermes_conversation_video_review=gr.State(None)
                    hermes_conversation_video_open=gr.Button('선택한 영상 제안 열기')
                    hermes_conversation_video_settings=gr.Code(label='영상 설정 · 기본값 확인',language='json',value='{}',lines=8,interactive=True)
                    hermes_conversation_video_images=gr.File(label='참조·제어 PNG · 순서대로',file_types=['.png'],file_count='multiple',type='binary')
                    with gr.Row():
                        hermes_conversation_video_driving=gr.File(label='동작 RGB MP4',file_types=['.mp4'],type='binary')
                        hermes_conversation_video_pose=gr.File(label='포즈 MP4',file_types=['.mp4'],type='binary')
                    with gr.Row():
                        hermes_conversation_video_edit=gr.File(label='편집·조건 MP4',file_types=['.mp4'],type='binary')
                        hermes_conversation_video_mask=gr.File(label='편집 마스크 MP4',file_types=['.mp4'],type='binary')
                    hermes_conversation_video_preview=gr.Markdown()
                    hermes_conversation_video_status=gr.Markdown('세션 작업에서 영상 제안을 선택하세요.')
                    with gr.Row():
                        hermes_conversation_video_check=gr.Button('영상 입력과 첨부 검토')
                        hermes_conversation_video_send=gr.Button('영상 작업 대기열에 추가',interactive=False)
                        hermes_conversation_video_read=gr.Button('영상 상태와 결과 확인')
                    hermes_conversation_video_inputs=[hermes_conversation_video_source,hermes_session_control,hermes_session_job_selection,hermes_conversation_video_settings,hermes_conversation_video_images,hermes_conversation_video_driving,hermes_conversation_video_pose,hermes_conversation_video_edit,hermes_conversation_video_mask]
                    hermes_conversation_video_open.click(open_conversation_video_proposal_safely,[hermes_session_control,hermes_session_job_selection],[hermes_conversation_video_source,hermes_conversation_video_settings,hermes_conversation_video_images,hermes_conversation_video_driving,hermes_conversation_video_pose,hermes_conversation_video_edit,hermes_conversation_video_mask,hermes_conversation_video_review,hermes_conversation_video_preview,hermes_conversation_video_status,hermes_conversation_video_send],queue=False)
                    hermes_conversation_video_review_event=hermes_conversation_video_check.click(review_conversation_video_inputs,hermes_conversation_video_inputs,[hermes_conversation_video_review,hermes_conversation_video_preview,hermes_conversation_video_status],queue=False)
                    current_video_status_token=gr.State(None)
                    current_video_status_result=gr.State(None)
                    current_video_status_kind=gr.State('video')
                    current_video_status_inputs=[hermes_conversation_video_source,hermes_session_control,hermes_session_job_selection,current_video_status_kind]
                    hermes_conversation_video_read.click(create_conversation_status_token,outputs=current_video_status_token,queue=False).then(collect_attachment_status_result,[*current_video_status_inputs,current_video_status_token],current_video_status_result,queue=False,trigger_mode='multiple').then(render_attachment_status_result,[*current_video_status_inputs,current_video_status_token,current_video_status_result],hermes_conversation_video_status,queue=False)
                    for current_status_selection in (hermes_conversation_video_source,hermes_session_control,hermes_session_job_selection):
                        current_status_selection.change(create_conversation_status_token,outputs=current_video_status_token,queue=False)
                    for current_status_selection in (hermes_session_control,hermes_session_job_selection):
                        current_status_selection.change(lambda:'세션이나 작업이 바뀌었습니다. 영상 제안을 다시 여세요.',outputs=hermes_conversation_video_status,queue=False)
                    for current_video_input in hermes_conversation_video_inputs:
                        current_video_input.change(lambda:(None,'',gr.update(interactive=False)),outputs=[hermes_conversation_video_review,hermes_conversation_video_preview,hermes_conversation_video_send],queue=False)
                    bind_gpu_generation_confirmation(hermes_conversation_video_send,submit_conversation_video_inputs,[hermes_conversation_video_review,*hermes_conversation_video_inputs],[hermes_conversation_video_review,hermes_conversation_video_status],generation_readiness_callback=lambda current_review:bool(current_review),generation_readiness_inputs=[hermes_conversation_video_review],generation_readiness_events=[hermes_conversation_video_review_event],generation_confirmation_validator=match_hermes_confirmation_inputs,generation_confirmation_inputs=[hermes_conversation_video_review,*hermes_conversation_video_inputs])
                hermes_proposal_route_event=hermes_proposal_route_button.click(reset_conversation_writer_review,outputs=hermes_conversation_writer_reset_outputs,queue=False).then(reset_conversation_edit_review,outputs=hermes_conversation_edit_reset_outputs,queue=False).then(route_conversation_proposal,[hermes_session_control,hermes_session_job_selection],[hermes_service_proposal_area,hermes_edit_proposal_area,hermes_image_proposal_area,hermes_video_proposal_area,hermes_conversation_service_kind,hermes_conversation_edit_kind,hermes_proposal_route_state,hermes_proposal_route_status],queue=False)
                hermes_auto_route_open_event=hermes_proposal_route_event.then(open_routed_conversation_proposal,[hermes_proposal_route_state,hermes_session_control,hermes_session_job_selection],[hermes_conversation_kimodo_card,hermes_conversation_kimodo_preview,hermes_conversation_kimodo_status,hermes_conversation_edit_card,hermes_conversation_edit_preview,hermes_conversation_edit_image,hermes_conversation_edit_status,current_flux_reference_source,current_flux_reference_first,current_flux_reference_second,current_flux_reference_review,current_flux_reference_preview,current_flux_reference_status,hermes_conversation_video_source,hermes_conversation_video_settings,hermes_conversation_video_images,hermes_conversation_video_driving,hermes_conversation_video_pose,hermes_conversation_video_edit,hermes_conversation_video_mask,hermes_conversation_video_review,hermes_conversation_video_preview,hermes_conversation_video_status,hermes_proposal_route_status],queue=False)
                hermes_capture_review_result=gr.State(None)
                hermes_auto_route_open_event.then(collect_routed_capture_review,[hermes_proposal_route_state,hermes_session_control,hermes_session_job_selection],hermes_capture_review_result,queue=False,trigger_mode='multiple').then(render_routed_capture_review,[hermes_proposal_route_state,hermes_session_control,hermes_session_job_selection,hermes_capture_review_result],hermes_proposal_route_status,queue=False)
                hermes_auto_route_open_event.success(refresh_conversation_model_readiness,[hermes_conversation_kimodo_card,hermes_session_control,hermes_session_job_selection,hermes_conversation_service_kind],[hermes_conversation_model_prepare],queue=False)
                hermes_auto_route_open_event.success(update_conversation_kimodo_frame_button,hermes_conversation_status_inputs,current_chat_kimodo_frame_button,queue=False)
                hermes_auto_route_open_event.then(lambda current_route,current_session,current_job,current_service_card,current_edit_card:(gr.update(interactive=isinstance(current_route,dict) and (current_route.get('session_id'),current_route.get('job_id'))==(current_session,current_job) and current_route.get('area')=='service' and isinstance(current_service_card,dict) and current_service_card.get('ready') is True),gr.update(interactive=isinstance(current_route,dict) and (current_route.get('session_id'),current_route.get('job_id'))==(current_session,current_job) and current_route.get('area')=='edit' and isinstance(current_edit_card,dict) and current_edit_card.get('ready') is True),None,gr.update(visible=False)),[hermes_proposal_route_state,hermes_session_control,hermes_session_job_selection,hermes_conversation_kimodo_card,hermes_conversation_edit_card],[hermes_conversation_kimodo_submit,hermes_conversation_edit_review,hermes_conversation_edit_confirmed,hermes_conversation_edit_confirm],queue=False)
                for current_route_selection in (hermes_session_control,hermes_session_job_selection):
                    current_route_selection.change(lambda:None,outputs=hermes_proposal_route_state,queue=False)
                    current_route_selection.change(reset_conversation_context_state,outputs=[hermes_conversation_kimodo_card,hermes_conversation_kimodo_preview,hermes_conversation_kimodo_status,hermes_conversation_kimodo_submit,hermes_conversation_writer_detail,hermes_conversation_writer_detail_status,hermes_conversation_writer_checked,hermes_conversation_writer_apply_record,hermes_conversation_writer_apply_confirm,hermes_conversation_writer_apply_status,hermes_conversation_edit_card,hermes_conversation_edit_preview,hermes_conversation_edit_image,hermes_conversation_edit_status,hermes_conversation_edit_confirm,hermes_conversation_edit_review,hermes_proposal_route_status,hermes_history_link_display,hermes_conversation_model_confirmation,hermes_conversation_model_confirm_group,hermes_conversation_model_prepare,*hermes_writer_material_outputs],queue=False)
                hermes_session_timer = gr.Timer(value=10, active=False)
                with gr.Row():
                    hermes_session_prompt = gr.Textbox(label='요청 입력', lines=3, max_lines=10, placeholder='무엇을 확인하거나 처리할까요?')
                    hermes_session_send = gr.Button('요청 검토', variant='primary', interactive=False)
                    hermes_session_refresh = gr.Button('대화 상태 새로고침')
                    hermes_session_recover = gr.Button('미확인 요청 복원')
                with gr.Accordion("번역 후 이미지 생성", open=False):
                    workflow_review_state = gr.State(None)
                    workflow_image_width = gr.Number(label="이미지 너비", value=512, precision=0)
                    workflow_image_height = gr.Number(label="이미지 높이", value=512, precision=0)
                    workflow_revision_prompt = gr.Textbox(label="첫 이미지를 참조한 수정 요청 (선택)", lines=2)
                    workflow_target_language = gr.Dropdown([("영어", "en"), ("중국어 간체", "zh-CN")], value="en", label="번역 언어")
                    workflow_glossary_text = gr.Textbox(label="번역 용어 (원문 => 번역어, 한 줄에 하나)", lines=2)
                    workflow_import_button = gr.Button("선택한 대화의 번역 제안 가져오기")
                    workflow_import_button.click(import_workflow_translation_proposal, [hermes_session_control, hermes_session_job_selection],
                        [hermes_session_prompt, workflow_target_language, workflow_glossary_text], queue=False)
                    workflow_input_components = [hermes_session_control, hermes_session_prompt,
                                                 workflow_image_width, workflow_image_height, workflow_revision_prompt, workflow_target_language, workflow_glossary_text]
                    workflow_review_button = gr.Button("요청 입력으로 단계 검토")
                    workflow_definition_preview = gr.JSON(label="단계별 입력과 결과 연결")
                    workflow_run_identifier = gr.Textbox(label="실행 ID")
                    workflow_submit_button = gr.Button("검토한 단계 대기열에 등록")
                    workflow_result_button = gr.Button("실행 상태와 결과 조회")
                    workflow_run_display = gr.JSON(label="워크플로우 실행 결과")
                    workflow_review_event = workflow_review_button.click(review_translation_image_workflow,
                        workflow_input_components, [workflow_review_state, workflow_definition_preview, workflow_run_identifier], queue=False)
                    workflow_submission_inputs = [workflow_review_state, *workflow_input_components]
                    bind_gpu_generation_confirmation(workflow_submit_button, submit_translation_image_workflow,
                        workflow_submission_inputs, [workflow_run_display],
                        generation_readiness_callback=lambda current_review_value: bool(current_review_value),
                        generation_readiness_inputs=[workflow_review_state], generation_readiness_events=[workflow_review_event],
                        generation_confirmation_validator=match_hermes_confirmation_inputs,
                        generation_confirmation_inputs=workflow_submission_inputs)
                    workflow_translation_output = gr.Textbox(label="완료된 번역문", interactive=False)
                    workflow_image_links = gr.Markdown()
                    workflow_display_outputs = [workflow_run_display, workflow_translation_output, workflow_image_links]
                    workflow_result_button.click(display_conversation_workflow_results,
                        [hermes_session_control, workflow_run_identifier], workflow_display_outputs, queue=False)
                    for workflow_context_input in (hermes_session_control, workflow_run_identifier):
                        workflow_context_input.change(lambda: (None, "", ""), outputs=workflow_display_outputs, queue=False)
                with gr.Accordion("대화에서 설계한 워크플로우", open=False):
                    workflow_load_proposal = gr.Button("선택한 답변에서 단계 가져오기")
                    workflow_definition_text = gr.Textbox(label="생성기 입력과 단계 연결 (JSON)", lines=8)
                    workflow_load_proposal.click(load_conversation_workflow_definition, [hermes_session_control, hermes_session_job_selection], workflow_definition_text, queue=False)
                    workflow_graph_review = gr.Button("입력과 연결 검토")
                    workflow_graph_state = gr.State(None)
                    workflow_graph_preview = gr.JSON(label="기본값을 포함한 실행 계획")
                    workflow_graph_event = workflow_graph_review.click(review_conversation_workflow_definition, [hermes_session_control, workflow_definition_text], workflow_graph_state, queue=False)
                    workflow_graph_event.success(lambda record: (record["steps"], record["run_id"]), workflow_graph_state, [workflow_graph_preview, workflow_run_identifier], queue=False)
                    workflow_graph_submit = gr.Button("검토한 워크플로우 등록")
                    workflow_graph_inputs = [workflow_graph_state, hermes_session_control, workflow_definition_text]
                    bind_gpu_generation_confirmation(workflow_graph_submit, submit_conversation_workflow_definition, workflow_graph_inputs, [workflow_run_display],
                        generation_readiness_callback=lambda record: bool(record), generation_readiness_inputs=[workflow_graph_state],
                        generation_readiness_events=[workflow_graph_event], generation_confirmation_validator=match_hermes_confirmation_inputs,
                        generation_confirmation_inputs=workflow_graph_inputs)
                with gr.Accordion("이 대화의 워크플로우 작업 찾기", open=False):
                    workflow_category_filter = gr.Dropdown([("전체", ""), ("번역", "translation"), ("이미지", "image")], value="", label="카테고리")
                    workflow_state_filter = gr.Dropdown([("전체", ""), ("선행 작업 대기", "waiting"), ("접수 준비", "ready"),
                        ("접수·결과 확인 중", "submitting"), ("생성기 대기", "queued"), ("생성기 실행 중", "running"),
                        ("생성기 일시정지", "paused"), ("생성기 상태 확인 불가", "unknown"), ("완료", "completed"), ("실패", "failed"),
                        ("취소", "cancelled"), ("차단", "blocked")], value="", label="단계 상태")
                    workflow_search_button = gr.Button("작업 찾기")
                    workflow_search_results = gr.JSON(label="최근 일치 작업과 실행 ID")
                    workflow_search_button.click(list_conversation_workflow_steps,
                        [hermes_session_control, workflow_category_filter, workflow_state_filter], workflow_search_results, queue=False)
                    hermes_session_control.change(lambda: None, outputs=workflow_search_results, queue=False)
                    workflow_step_identifier = gr.Textbox(label="우선 실행할 단계 ID")
                    workflow_priority_review = gr.Button("대기 순번과 대상 검토")
                    workflow_priority_record = gr.State(None)
                    workflow_priority_notice = gr.Markdown()
                    workflow_priority_submit = gr.Button("검토한 작업 우선 실행", visible=False)
                    workflow_target_inputs = [hermes_session_control, workflow_run_identifier, workflow_step_identifier]
                    workflow_priority_outputs = [workflow_priority_record, workflow_priority_notice, workflow_priority_submit]
                    workflow_priority_review.click(review_workflow_step_priority, workflow_target_inputs, workflow_priority_outputs, queue=False)
                    workflow_priority_submit.click(submit_workflow_step_priority, [workflow_priority_record, *workflow_target_inputs], workflow_priority_outputs, queue=False)
                    for workflow_target_input in workflow_target_inputs:
                        workflow_target_input.change(lambda: (None, "", gr.update(visible=False)), outputs=workflow_priority_outputs, queue=False)
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
                hermes_session_control.change(fn=None, inputs=[hermes_session_control], js="(sessionId)=>{if(/^[a-f0-9]{32}$/.test(sessionId || '')){const returnLink=document.querySelector('#management-return-conversation a');if(/^[a-f0-9]{32}$/.test(sessionId)){if(returnLink)returnLink.setAttribute('href','/management/frame/hermes-agent/?session='+sessionId);const historyLink=document.querySelector('#management-open-history a');if(historyLink)historyLink.setAttribute('href','/management/frame/operations-history/?session='+sessionId);}try{sessionStorage.setItem('slime-management-session',sessionId);}catch(e){}try{localStorage.setItem('slime-management-session',sessionId);}catch(e){}const currentUrl=new URL(window.location.href);if(currentUrl.searchParams.has('session')){if(currentUrl.searchParams.get('session')!==sessionId)currentUrl.searchParams.delete('job');currentUrl.searchParams.set('session',sessionId);window.history.replaceState(window.history.state,'',currentUrl.href);}} return sessionId;}", queue=False)
                hermes_interface_blocks.load(fn=None,js="()=>{const sessionId=new URL(window.location.href).searchParams.get('session');const returnLink=document.querySelector('#management-return-conversation a');if(/^[a-f0-9]{32}$/.test(sessionId || '')){if(returnLink)returnLink.setAttribute('href','/management/frame/hermes-agent/?session='+sessionId);const historyLink=document.querySelector('#management-open-history a');if(historyLink)historyLink.setAttribute('href','/management/frame/operations-history/?session='+sessionId);}}")
                hermes_interface_blocks.load(list_hermes_session_choices, inputs=[hermes_session_control], outputs=[hermes_session_control, hermes_session_list_status], js="(sessionId)=>{const linkedSession=new URL(window.location.href).searchParams.get('session');let tabSession=null;let recentSession=null;try{tabSession=sessionStorage.getItem('slime-management-session');}catch(e){}try{recentSession=localStorage.getItem('slime-management-session');}catch(e){}return [[linkedSession,tabSession,recentSession,sessionId].find(value=>typeof value==='string'&&/^[a-f0-9]{32}$/.test(value)) || null];}", preprocess=False, queue=False).then(restore_linked_conversation_job,inputs=[hermes_session_control,hermes_older_job_input],outputs=[hermes_session_job_selection,hermes_older_job_status],js="(sessionId,jobId)=>[sessionId,new URL(window.location.href).searchParams.get('job') || '']",preprocess=False,queue=False)
        if include_advanced_controls:
            with gr.Accordion('직접 조회와 작업', open=True, elem_id='hermes-direct-controls') as hermes_advanced_accordion:
                gr.Markdown('대화에서 나온 제안을 검토하거나 기존 기능을 직접 실행합니다. 이 영역은 대화 중심 작업 흐름으로 전환 중입니다. 전문 설정과 실행 결과는 각 도구 페이지에서도 확인할 수 있습니다.')
                with gr.Accordion('사용 가능한 관리 기능', open=False):
                    gr.Markdown('조회와 작업 변경의 영향을 확인합니다. 작업 실행 권한을 별도로 부여하는 화면은 아닙니다.')
                    hermes_capability_search = gr.Textbox(label='관리 기능 검색',placeholder='기능명, 명령, 연결 경로 또는 입력',max_lines=1)
                    hermes_capability_refresh = gr.Button('관리 기능 목록 새로고침')
                    hermes_capability_status = gr.Markdown('목록 새로고침으로 기능을 확인하세요.')
                    hermes_capability_table = gr.Dataframe(headers=['기능','명령','연결','필수·선택 입력','영향','GPU','재시도','확인 사항'], datatype=['str']*8, interactive=False, type='array', label='관리 기능 목록')
                    hermes_capability_refresh.click(read_hermes_capability_rows, inputs=[hermes_capability_search], outputs=[hermes_capability_table, hermes_capability_status], queue=False)
                    hermes_capability_search.submit(read_hermes_capability_rows, inputs=[hermes_capability_search], outputs=[hermes_capability_table, hermes_capability_status], queue=False)
                with gr.Accordion('과거 앵커 검수 이력',open=False):
                    gr.Markdown('과거 좌표 검수 기록 요약입니다. 현재 등록된 앵커와 문서 적용 여부는 별도로 확인하세요.')
                    with gr.Row():
                        current_anchor_animation=gr.Textbox(label='애니메이션 ID')
                        current_anchor_version=gr.Textbox(label='애니메이션 버전')
                        current_anchor_search=gr.Button('이력 조회')
                        current_anchor_next=gr.Button('다음 이력',interactive=False)
                    current_anchor_notice=gr.Markdown('애니메이션 ID와 버전을 입력하세요.')
                    current_anchor_rows=gr.Dataframe(headers=['이력 ID','저장 시각','프레임 수'],datatype=['str','str','number'],type='array',interactive=False)
                    current_anchor_page=gr.State(None)
                    current_anchor_token=gr.State(None)
                    current_anchor_result=gr.State(None)
                    for current_anchor_button,current_anchor_direction in ((current_anchor_search,False),(current_anchor_next,True)):
                        current_anchor_button.click(create_conversation_status_token,outputs=current_anchor_token,queue=False).then(lambda current_animation,current_version,current_page,current_token,current_direction=current_anchor_direction:collect_hermes_legacy_anchor_page(current_animation,current_version,current_page,current_token,current_direction),[current_anchor_animation,current_anchor_version,current_anchor_page,current_anchor_token],current_anchor_result,queue=False,trigger_mode='multiple').then(render_hermes_legacy_anchor_page,[current_anchor_animation,current_anchor_version,current_anchor_token,current_anchor_result],[current_anchor_rows,current_anchor_notice,current_anchor_page,current_anchor_next],queue=False)
                    for current_anchor_input in (current_anchor_animation,current_anchor_version):
                        current_anchor_input.input(lambda:([],None,gr.update(interactive=False),'조건이 변경됐습니다. 다시 조회하세요.',None),outputs=[current_anchor_rows,current_anchor_page,current_anchor_next,current_anchor_notice,current_anchor_token],queue=False)
                with gr.Accordion('전체 관리 서비스 등록 목록', open=False):
                    gr.Markdown('게이트웨이 등록만 표시합니다. 폐기·제한·미연결 명령을 포함하며 Hermes에서 실행할 수 있다는 뜻은 아닙니다.')
                    with gr.Row():
                        hermes_service_registration_query = gr.Textbox(label='서비스·기능 검색',placeholder='서비스명, 명령 또는 한국어 기능명')
                        hermes_service_registration_offset = gr.Number(label='조회 시작 위치',value=0,precision=0,minimum=0)
                    hermes_service_registration_button = gr.Button('서비스 등록 목록 조회')
                    hermes_service_registration_status = gr.Markdown('조회하면 게이트웨이에 등록된 서비스를 표시합니다.')
                    hermes_service_registration_table = gr.Dataframe(headers=['서비스','등록된 명령','게이트웨이 명시 차단','확인된 서비스 차단','확인된 조건부 제한','Hermes 연결 기능'], datatype=['str','str','str','str','str','str'], interactive=False, type='array', label='전체 관리 서비스 등록')
                    hermes_service_registration_token=gr.State(None)
                    hermes_service_registration_result=gr.State(None)
                    hermes_service_registration_query.input(clear_hermes_service_registration_search, outputs=[hermes_service_registration_offset,hermes_service_registration_table,hermes_service_registration_status,hermes_service_registration_token], queue=False)
                    hermes_service_registration_offset.input(lambda:([], '조회 위치가 변경됐습니다. 목록을 다시 조회하세요.', None), outputs=[hermes_service_registration_table,hermes_service_registration_status,hermes_service_registration_token], queue=False)
                    for current_search_event in (hermes_service_registration_button.click,hermes_service_registration_query.submit):
                        current_search_event(create_conversation_status_token,outputs=hermes_service_registration_token,queue=False).then(collect_hermes_service_registration_search,[hermes_service_registration_query,hermes_service_registration_offset,hermes_service_registration_token],hermes_service_registration_result,queue=False,trigger_mode='multiple').then(render_hermes_service_registration_search,[hermes_service_registration_query,hermes_service_registration_offset,hermes_service_registration_token,hermes_service_registration_result],[hermes_service_registration_table,hermes_service_registration_status],queue=False)
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
                    gr.Markdown('저장 중단 여부는 원본·등록부·잠금과 백업 해시의 조회 시점 비교입니다. 자동 복구하지 않습니다.')
                    hermes_sprite_pending_button=gr.Button('스프라이트 저장 중단 상태 확인')
                    hermes_sprite_pending_result=gr.JSON(label='중단 저장 상태와 백업 확인')
                    hermes_sprite_pending_button.click(read_hermes_sprite_pending_status_for_review,outputs=[hermes_sprite_pending_result],queue=False)
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
                    gr.Markdown('에셋 원본은 DB 없이 조회합니다. DB 편집 초안 검증에는 콘텐츠 DB가 필요하며, 원본·등록부·백엔드 잠금의 동기 저장이 구현될 때까지 신규 저장은 중단됩니다. 기존 저장 접수는 아래 이력에서 확인하세요.')
                    hermes_city_map_id = gr.Textbox(label='도시 맵 ID',value='iseulon')
                    hermes_city_source_button = gr.Button('도시 에셋 원본 조회')
                    hermes_city_source_document = gr.JSON(label='검증된 도시 에셋 원본')
                    hermes_city_source_status = gr.Markdown('원본 조회는 DB 편집 리비전을 제공하지 않습니다.')
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
                            hermes_city_save_button = gr.Button('도시 맵 신규 저장 중단',variant='primary',interactive=False)
                    hermes_city_source_button.click(read_hermes_city_source_view,[hermes_city_map_id],[hermes_city_source_document,hermes_city_source_status],queue=False)
                    hermes_city_map_id.change(lambda:({},'도시 ID가 변경되었습니다. 원본을 다시 조회하세요.'),outputs=[hermes_city_source_document,hermes_city_source_status],queue=False)
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
                            hermes_field_save_button = gr.Button('확인 후 야외 맵 저장', variant='primary', interactive=False)
                    hermes_field_load_button.click(load_hermes_field_map_draft, [hermes_field_map_id], [hermes_field_draft_text,hermes_field_source_data,hermes_field_review_state,hermes_field_confirm_group,hermes_field_status_text], queue=False)
                    hermes_field_review_button.click(review_hermes_field_map_draft, [hermes_field_draft_text,hermes_field_request_id], [hermes_field_review_state,hermes_field_review_summary,hermes_field_confirm_group], queue=False).then(update_field_save_button,[hermes_field_review_state],[hermes_field_save_button],queue=False)
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
                    hermes_model_preparation_review_button.click(safely_review_hermes_model_preparation, [hermes_model_readiness_selection, hermes_model_preparation_request], [hermes_model_preparation_state, hermes_model_preparation_summary, hermes_model_preparation_confirm_group, hermes_model_preparation_result], queue=False)
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
                with gr.Accordion('모델 다운로드 상태', open=False):
                    gr.Markdown('관리도구에 기록된 다운로드를 조회합니다. 외부 작업과 모델 실행 준비 여부는 별도 확인합니다.')
                    hermes_download_status_button=gr.Button('다운로드 상태 확인')
                    hermes_download_status_result=gr.JSON(label='다운로드 기록')
                    hermes_download_status_button.click(read_hermes_model_download_status_for_review,outputs=[hermes_download_status_result],queue=False)
                with gr.Accordion('모델 파일 보유량', open=False):
                    hermes_model_inventory_button = gr.Button('모델 파일 보유량 조회')
                    hermes_model_inventory_status = gr.Markdown('조회하면 모델별 파일 수와 용량을 표시합니다.')
                    hermes_model_inventory_table = gr.Dataframe(headers=['서비스', '파일 수', '바이트', '조사 상태'], datatype=['str','str','str','str'], interactive=False, type='array', label='모델 파일 보유량')
                    hermes_model_inventory_button.click(read_hermes_model_inventory_rows, outputs=[hermes_model_inventory_table, hermes_model_inventory_status], queue=False)
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
                        (current_writer_input.input if current_writer_input is hermes_writer_request_id else current_writer_input.change)(lambda:(None,'','입력이 변경되어 다시 검토해야 합니다.',gr.update(interactive=False)),outputs=[hermes_writer_review_state,hermes_writer_preview,hermes_writer_status,hermes_writer_submit],queue=False)
                    bind_gpu_generation_confirmation(hermes_writer_submit,submit_hermes_writer_reviewed,[hermes_writer_review_state,*hermes_writer_inputs],[hermes_writer_job_id,hermes_writer_status],generation_readiness_callback=lambda current_review_value:bool(current_review_value),generation_readiness_inputs=[hermes_writer_review_state],generation_readiness_events=[hermes_writer_review_event],generation_confirmation_validator=match_hermes_confirmation_inputs,generation_confirmation_inputs=[hermes_writer_review_state,*hermes_writer_inputs])
                    hermes_writer_read_button = gr.Button('작가 AI 상태·제안 조회')
                    hermes_writer_result = gr.JSON(label='작가 AI 제안과 제한된 diff')
                    hermes_writer_read_button.click(read_safe_hermes_writer_result,[hermes_writer_request_id,hermes_session_control],[hermes_writer_job_id,hermes_writer_status,hermes_writer_result],queue=False)
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
                        (current_writer_cancel_input.input if current_writer_cancel_input is hermes_writer_request_id else current_writer_cancel_input.change)(lambda:(None,gr.update(visible=False)),outputs=[hermes_writer_cancel_state,hermes_writer_cancel_group],queue=False)
                    hermes_writer_history = gr.Dropdown(label='작가 AI 위임 접수 이력',choices=[],interactive=True)
                    with gr.Row():
                        hermes_writer_history_refresh = gr.Button('작가 AI 위임 이력 조회')
                        hermes_writer_history_open = gr.Button('선택한 작가 AI 접수 확인')
                    hermes_writer_history_status = gr.Markdown('Hermes를 통해 접수한 작가 작업만 표시합니다.')
                    hermes_writer_history_refresh.click(list_hermes_writer_choices,outputs=[hermes_writer_history,hermes_writer_history_status],queue=False)
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
                            (current_writer_apply_input.input if current_writer_apply_input is hermes_writer_request_id else current_writer_apply_input.change)(lambda:(None,gr.update(visible=False)),outputs=[hermes_writer_apply_state,hermes_writer_apply_group],queue=False)
                        hermes_writer_history_open.click(lambda current_request_value:(current_request_value,None,'',gr.update(interactive=False),None,gr.update(visible=False),None,gr.update(visible=False)),[hermes_writer_history],[hermes_writer_request_id,hermes_writer_review_state,hermes_writer_preview,hermes_writer_submit,hermes_writer_cancel_state,hermes_writer_cancel_group,hermes_writer_apply_state,hermes_writer_apply_group],queue=False).then(read_safe_hermes_writer_result,[hermes_writer_request_id,hermes_session_control],[hermes_writer_job_id,hermes_writer_status,hermes_writer_result],queue=False)
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
                    hermes_translation_index_button = gr.Button('작가 색인 상태 확인')
                    hermes_translation_index_status = gr.Markdown('문서 변경 후에는 색인 상태를 확인하세요.')
                    hermes_translation_index_button.click(read_hermes_writer_index_status_for_review,outputs=[hermes_translation_index_status],queue=False)
                    hermes_translation_evidence_button = gr.Button('작가 문서에서 번역 근거 검색')
                    hermes_translation_evidence_result = gr.JSON(label='문서 근거 · 승인 용어 아님')
                    hermes_translation_evidence_button.click(search_hermes_translation_evidence_for_review,[hermes_translation_source],[hermes_translation_evidence_result],queue=False)
                    hermes_translation_source.change(lambda:None,outputs=[hermes_translation_evidence_result],queue=False)
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
                    hermes_translation_read_button.click(read_safe_hermes_translation_result,[hermes_translation_request_id,hermes_session_control],[hermes_translation_job_id,hermes_translation_status,hermes_translation_result],queue=False)
                    hermes_translation_history = gr.Dropdown(label='번역 위임 접수 이력',choices=[],interactive=True)
                    with gr.Row():
                        hermes_translation_history_refresh = gr.Button('번역 위임 이력 조회')
                        hermes_translation_history_open = gr.Button('선택한 번역 접수 확인')
                    hermes_translation_history_status = gr.Markdown('Hermes를 통해 접수한 번역만 표시합니다.')
                    hermes_translation_history_refresh.click(list_hermes_translation_choices,outputs=[hermes_translation_history,hermes_translation_history_status],queue=False)
                    hermes_translation_history_open.click(lambda current_request_value:current_request_value,[hermes_translation_history],[hermes_translation_request_id],queue=False).then(read_safe_hermes_translation_result,[hermes_translation_request_id,hermes_session_control],[hermes_translation_job_id,hermes_translation_status,hermes_translation_result],queue=False)
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
                    hermes_video_read_button.click(read_safe_hermes_video_result,[hermes_video_request_id,hermes_video_service,hermes_session_control],[hermes_video_job_id,hermes_video_status],queue=False)
                    hermes_video_history=gr.Dropdown(label='동작·영상 접수 이력',choices=[],interactive=True)
                    with gr.Row():
                        hermes_video_history_refresh=gr.Button('동작·영상 이력 조회')
                        hermes_video_history_open=gr.Button('선택한 동작·영상 접수 확인')
                    hermes_video_history_status=gr.Markdown('선택한 서비스의 Hermes 접수만 표시합니다.')
                    hermes_video_history_refresh.click(list_hermes_video_choices,[hermes_video_service],[hermes_video_history,hermes_video_history_status],queue=False)
                    hermes_video_history_open.click(lambda current_request_value:current_request_value,[hermes_video_history],[hermes_video_request_id],queue=False).then(read_safe_hermes_video_result,[hermes_video_request_id,hermes_video_service,hermes_session_control],[hermes_video_job_id,hermes_video_status],queue=False)
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
                    hermes_audio_read_button.click(read_safe_hermes_audio_result,[hermes_audio_request_id,hermes_audio_service,hermes_session_control],[hermes_audio_job_id,hermes_audio_status],queue=False)
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
                    hermes_audio_history_open.click(lambda current_request_value:current_request_value,[hermes_audio_history],[hermes_audio_request_id],queue=False).then(read_safe_hermes_audio_result,[hermes_audio_request_id,hermes_audio_service,hermes_session_control],[hermes_audio_job_id,hermes_audio_status],queue=False)
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
                    hermes_expression_read_button.click(lambda current_request_value,current_session_identifier:read_safe_hermes_flux_result(current_request_value,'flux-expression',current_session_identifier),[hermes_expression_request_id,hermes_session_control],[hermes_expression_job_id,hermes_expression_status],queue=False)
                    hermes_expression_history = gr.Dropdown(label='표정 생성 접수 이력',choices=[],interactive=True)
                    with gr.Row():
                        hermes_expression_history_refresh = gr.Button('표정 생성 이력 조회')
                        hermes_expression_history_open = gr.Button('선택한 표정 생성 접수 확인')
                    hermes_expression_history_status = gr.Markdown('Hermes를 통해 접수한 표정 작업만 표시합니다.')
                    hermes_expression_history_refresh.click(lambda:list_hermes_flux_profile_choices('flux-expression'),outputs=[hermes_expression_history,hermes_expression_history_status],queue=False)
                    hermes_expression_history_open.click(lambda current_request_value:current_request_value,[hermes_expression_history],[hermes_expression_request_id],queue=False).then(lambda current_request_value,current_session_identifier:read_safe_hermes_flux_result(current_request_value,'flux-expression',current_session_identifier),[hermes_expression_request_id,hermes_session_control],[hermes_expression_job_id,hermes_expression_status],queue=False)
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
                    hermes_profile_read_button.click(read_safe_hermes_flux_result,[hermes_profile_request_id,hermes_profile_selection,hermes_session_control],[hermes_profile_job_id,hermes_profile_status],queue=False)
                    hermes_profile_history = gr.Dropdown(label='FLUX 프로필 접수 이력',choices=[],interactive=True)
                    with gr.Row():
                        hermes_profile_history_refresh = gr.Button('FLUX 프로필 이력 조회')
                        hermes_profile_history_open = gr.Button('선택한 FLUX 프로필 접수 확인')
                    hermes_profile_history_status = gr.Markdown('선택한 프로필의 접수 이력만 표시합니다.')
                    hermes_profile_history_refresh.click(list_hermes_flux_profile_choices,[hermes_profile_selection],[hermes_profile_history,hermes_profile_history_status],queue=False)
                    hermes_profile_history_open.click(lambda current_request_value:current_request_value,[hermes_profile_history],[hermes_profile_request_id],queue=False).then(read_safe_hermes_flux_result,[hermes_profile_request_id,hermes_profile_selection,hermes_session_control],[hermes_profile_job_id,hermes_profile_status],queue=False)
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
                    hermes_flux_history_open.click(lambda current_id:(current_id, None, '', gr.update(interactive=False)), [hermes_flux_history], [hermes_flux_request_id, hermes_flux_review_state, hermes_flux_preview, hermes_flux_submit], queue=False).then(read_safe_hermes_flux_receipt, [hermes_flux_request_id, hermes_session_control], [hermes_flux_job, hermes_flux_status], queue=False)
                    hermes_flux_status_button = gr.Button('FLUX 접수와 작업 상태 조회')
                    hermes_flux_status_button.click(read_safe_hermes_flux_receipt, [hermes_flux_request_id, hermes_session_control], [hermes_flux_job, hermes_flux_status], queue=False)
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
                        hermes_cancel_button = gr.Button('작업 중지 요청', interactive=False)
                    gr.Markdown('중지할 작업의 ID를 확인하면 중지 요청을 사용할 수 있습니다. 요청 후 실제 종료는 상태를 다시 확인하세요.')
                    hermes_job_control.change(update_direct_job_cancel_availability,inputs=hermes_job_control,outputs=hermes_cancel_button,queue=False)
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
                    hermes_cancel_review_state = gr.State(None)
                    with gr.Group(visible=False) as hermes_cancel_confirmation_group:
                        hermes_cancel_review_summary = gr.Markdown()
                        with gr.Row():
                            hermes_cancel_decline_button = gr.Button('중지하지 않기')
                            hermes_cancel_confirm_button = gr.Button('확인 후 중지 요청', variant='stop')
                    hermes_cancel_button.click(review_direct_job_cancel,inputs=hermes_job_control,outputs=[hermes_cancel_review_state,hermes_cancel_review_summary,hermes_cancel_confirmation_group],queue=False)
                    hermes_cancel_decline_button.click(discard_direct_job_cancel,inputs=hermes_cancel_review_state,outputs=[hermes_cancel_review_state,hermes_cancel_confirmation_group],queue=False)
                    hermes_cancel_confirm_button.click(submit_direct_job_cancel,inputs=[hermes_cancel_review_state,hermes_job_control],outputs=[hermes_cancel_review_state,hermes_cancel_confirmation_group,hermes_status_control],trigger_mode='once',concurrency_limit=1)
                    hermes_job_control.change(discard_direct_job_cancel,inputs=hermes_cancel_review_state,outputs=[hermes_cancel_review_state,hermes_cancel_confirmation_group],queue=False)
                    hermes_session_job_open.click(open_hermes_session_job, [hermes_session_job_selection], [hermes_job_control, hermes_status_control, hermes_answer_control, hermes_diff_control, hermes_log_control, hermes_result_control, hermes_original_prompt_control, hermes_legacy_accordion], queue=False).then(lambda: gr.update(open=True), outputs=hermes_advanced_accordion, queue=False)
                    for current_session_selection in (hermes_session_control,hermes_session_job_selection):
                        current_session_selection.change(reset_direct_session_job_detail,outputs=[hermes_job_control,hermes_status_control,hermes_answer_control,hermes_diff_control,hermes_log_control,hermes_result_control,hermes_original_prompt_control,hermes_diff_cursor,hermes_diff_page_status],queue=False)
                    with gr.Accordion('작업 이력', open=True):
                        hermes_history_button = gr.Button('이력 새로고침')
                        hermes_history_status = gr.Markdown('이력을 확인하고 있습니다.')
                        gr.Markdown('이력의 행을 선택하면 해당 작업의 상태와 결과를 불러옵니다.')
                        hermes_history_table = gr.Dataframe(headers=['작업 ID', '상태', '지시'], datatype=['str', 'str', 'str'], type='array', interactive=False)
                        hermes_history_table.select(select_hermes_history_record, inputs=[hermes_history_table], outputs=[hermes_job_control, hermes_status_control, hermes_answer_control, hermes_diff_control, hermes_log_control, hermes_result_control, hermes_original_prompt_control], queue=False)
                        hermes_history_button.click(refresh_hermes_work_history, outputs=[hermes_history_table, hermes_history_status], queue=False)
                    hermes_interface_blocks.load(refresh_hermes_work_history, outputs=[hermes_history_table, hermes_history_status], queue=False)
                hermes_billboard_edit_proposal.click(load_hermes_billboard_edit_proposal,[hermes_session_job_selection],[hermes_billboard_edit_id,hermes_billboard_edit_original,hermes_billboard_edit_draft,hermes_billboard_edit_request,hermes_billboard_edit_state,hermes_billboard_edit_confirm,hermes_billboard_edit_status],queue=False)
                hermes_effect_edit_proposal.click(load_hermes_effect_edit_proposal,[hermes_session_job_selection],[hermes_effect_choices,hermes_effect_detail,hermes_effect_edit_draft,hermes_effect_edit_request,hermes_effect_edit_state,hermes_effect_edit_confirm,hermes_effect_edit_status],queue=False)
                hermes_sprite_edit_proposal.click(load_hermes_sprite_anchor_proposal,[hermes_session_job_selection],[hermes_sprite_choices,hermes_sprite_edit_draft,hermes_sprite_edit_request,hermes_sprite_edit_state,hermes_sprite_edit_confirm,hermes_sprite_edit_status],queue=False)
                hermes_field_proposal_button.click(load_hermes_field_map_proposal,[hermes_session_job_selection],[hermes_field_map_id,hermes_field_draft_text,hermes_field_source_data,hermes_field_request_id,hermes_field_review_state,hermes_field_confirm_group,hermes_field_status_text],queue=False)
        else:
            current_direct_link_display=gr.HTML(build_conversation_direct_link(None))
            hermes_session_control.change(build_conversation_direct_link,inputs=hermes_session_control,outputs=current_direct_link_display,queue=False)
    return hermes_interface_blocks


def build_hermes_direct_interface():
    """기존 직접 기능을 별도 화면에서 유지한다."""
    return build_hermes_agent_interface(include_advanced_controls=True)
