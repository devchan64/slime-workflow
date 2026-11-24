"""Hermes 작업 접수·취소·결과를 공용 관리 명령과 GPU 대기열에 연결한다."""
from contextlib import contextmanager
import base64
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import threading
import time
import uuid
from zoneinfo import ZoneInfo

from workflow.common.generation_records import write_record_atomically
from workflow.common.gpu_job_queue import launch_gpu_process, cancel_gpu_generation
from workflow.common.management_transport import validate_management_http_request, send_management_json_response
from workflow.common.hermes_model_download import inspect_hermes_model_files
from workflow.domains.hermes_agent.runtime_integrity import verify_hermes_runtime_integrity
from workflow.domains.hermes_agent.verification import validate_hermes_verification_modules

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[3]
HERMES_JOB_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.tmp/test/hermes-agent/jobs'
HERMES_JOB_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}')
HERMES_JOB_OBSERVATION_MAXIMUM_ENTRIES = 5000
HERMES_REQUEST_PATTERN = re.compile(r'[A-Za-z0-9_-]{8,80}')


from workflow.common.hermes_model_routing import COMPLEX_MODEL, route_hermes_request


def validate_hermes_runtime_ready(model_profile=COMPLEX_MODEL):
    if model_profile != COMPLEX_MODEL:
        raise ValueError('폐기된 대화 모델입니다. Qwen 3.8을 사용하세요.')
    elif not inspect_hermes_model_files():
        raise ValueError('모델 관리에서 Hermes 모델을 먼저 준비하고 무결성을 확인하세요.')
    from generators.writer_agent.prepare import RUNTIME_SERVER_PATH
    hermes_project_environment = WORKFLOW_ROOT_DIRECTORY / '.venv'
    if hermes_project_environment.is_symlink() or not (hermes_project_environment / 'bin/python').is_file() or not (WORKFLOW_ROOT_DIRECTORY / '.local/writer-agent/prepared.json').is_file() or not RUNTIME_SERVER_PATH.is_file() or not shutil.which('bwrap'):
        raise ValueError('Hermes 실행환경·ROCm 추론 서버 또는 bubblewrap이 준비되지 않았습니다.')
    verify_hermes_runtime_integrity(WORKFLOW_ROOT_DIRECTORY / '.local/hermes-agent-runtime')


def read_hermes_agent_trace(hermes_job_path):
    """저장된 도구 사용·결과를 제한된 길이로 표시한다."""
    hermes_event_path = hermes_job_path / 'hermes-events.jsonl'
    if not hermes_event_path.is_file() or hermes_event_path.is_symlink():
        return ''
    with hermes_event_path.open('rb') as hermes_event_stream:
        hermes_event_stream.seek(max(0, hermes_event_path.stat().st_size - 128000))
        hermes_event_lines = hermes_event_stream.read().decode(errors='replace').splitlines()
    hermes_trace_lines = []
    for hermes_event_line in hermes_event_lines:
        try:
            hermes_event_record = json.loads(hermes_event_line)
        except ValueError:
            continue
        hermes_event_type = hermes_event_record.get('type')
        if hermes_event_type == 'tool_use':
            hermes_trace_lines.append('[도구 호출] ' + str(hermes_event_record.get('name', '')) + ' ' + json.dumps(hermes_event_record.get('input', {}), ensure_ascii=False)[:3000])
        elif hermes_event_type == 'tool_result':
            hermes_trace_lines.append('[도구 결과] ' + str(hermes_event_record.get('output', ''))[:5000])
        elif hermes_event_type == 'result':
            hermes_trace_lines.append('[최종 응답] ' + str(hermes_event_record.get('text', ''))[:8000])
    return '\n'.join(hermes_trace_lines)[-32000:]


def read_hermes_final_response(hermes_job_path):
    """최근 이벤트에서 최종 응답을 제한된 길이로 읽는다."""
    hermes_event_path = hermes_job_path / 'hermes-events.jsonl'
    if not hermes_event_path.is_file() or hermes_event_path.is_symlink():
        return None, False
    with hermes_event_path.open('rb') as hermes_event_stream:
        hermes_event_stream.seek(max(0, hermes_event_path.stat().st_size - 128000))
        hermes_event_lines = hermes_event_stream.read().decode(errors='replace').splitlines()
    for hermes_event_line in reversed(hermes_event_lines):
        try:
            hermes_event_record = json.loads(hermes_event_line)
        except (ValueError, TypeError):
            continue
        if isinstance(hermes_event_record, dict) and hermes_event_record.get('type') == 'result' and isinstance(hermes_event_record.get('text'), str):
            hermes_answer_text = hermes_event_record['text']
            return hermes_answer_text[:8000], len(hermes_answer_text) > 8000
    return None, False


def read_hermes_context_response(hermes_job_path):
    """표시용 8,000자 제한과 별도로 대화 문맥의 전체 최종 답변을 읽는다."""
    path = hermes_job_path / 'hermes-events.jsonl'
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16000000:
        raise ValueError('이전 답변 원문을 안전하게 읽을 수 없습니다.')
    with path.open(encoding='utf-8') as stream:
        answer = None
        for line in stream:
            try:
                event = json.loads(line)
            except (ValueError, TypeError):
                continue
            if isinstance(event, dict) and event.get('type') == 'result' and isinstance(event.get('text'), str):
                answer = event['text']
    if answer is None:
        raise ValueError('이전 답변 원문을 확인할 수 없습니다.')
    return answer

def parse_source_history_page(output):
    try:
        page = json.loads(output)
    except (TypeError, ValueError):
        return None
    if not isinstance(page, dict) or not isinstance(page.get('records'), list) or type(page.get('total')) is not int:
        return None
    service = page.get('source_service')
    if not isinstance(service, str) or not re.fullmatch(r'[a-z0-9-]{1,80}', service):
        return None
    rows = []
    labels = {'completed':'완료', 'running':'실행 중', 'queued':'대기 중', 'failed':'실패', 'cancelled':'취소'}
    for row in page['records']:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', row['id']):
            return None
        state = row.get('recorded_status')
        rows.append({"id": row["id"], "status": labels.get(state, "기타") if isinstance(state, str) else "미확인"})
    return {"service": service, "total": page["total"], "rows": rows}


def source_history_summary(page):
    lines = [f'{page["service"]} 생성 이력 · 총 {page["total"]}건 · 조회된 {len(page["rows"])}건']
    return "\n".join([*lines, *(f"- `{row['id']}` · {row['status']}" for row in page["rows"])])


def summarize_source_history(output):
    page = parse_source_history_page(output)
    return source_history_summary(page) if page else None


def read_hermes_tool_activity(hermes_job_path):
    """최근 도구 호출과 결과를 크기 제한하여 시간순으로 제공한다."""
    current_event_path = hermes_job_path / 'hermes-events.jsonl'
    if not current_event_path.is_file() or current_event_path.is_symlink():
        return {'events': [], 'truncated': False}
    with current_event_path.open('rb') as current_event_stream:
        current_file_size = current_event_path.stat().st_size
        current_event_stream.seek(max(0, current_file_size - 128000))
        current_event_lines = current_event_stream.read().decode(errors='replace').splitlines()
    current_tool_events = []
    history_calls = set()
    history_page = None
    video_calls = {}
    video_source = None
    for current_event_line in current_event_lines:
        try:
            current_event_record = json.loads(current_event_line)
        except ValueError:
            continue
        if not isinstance(current_event_record, dict) or current_event_record.get('type') not in ('tool_use', 'tool_result'):
            continue
        current_event_type = current_event_record['type']
        current_tool_name = current_event_record.get('name')
        current_call_identifier = current_event_record.get('tool_call_id')
        current_event_value = {'type': current_event_type, 'name': current_tool_name[:80] if isinstance(current_tool_name, str) else 'unknown', 'call_id': current_call_identifier[:80] if isinstance(current_call_identifier, str) else None}
        current_timestamp_value = current_event_record.get('timestamp')
        if type(current_timestamp_value) is int and 0 <= current_timestamp_value <= 253402300798999:
            current_event_value['timestamp'] = datetime.fromtimestamp(current_timestamp_value / 1000, timezone.utc).isoformat()
        if current_event_type == 'tool_use':
            current_input_record = current_event_record.get('input')
            if isinstance(current_input_record, dict):
                current_target_value = current_input_record.get('command') or current_input_record.get('path') or current_input_record.get('file_path')
                if isinstance(current_target_value, str):
                    current_event_value['target'] = current_target_value[:200]
                    if current_call_identifier and isinstance(current_call_identifier, str) and current_target_value.startswith('/runtime/.venv/bin/python /control/management-status.py source-history '):
                        history_calls.add(current_call_identifier)
                    if isinstance(current_call_identifier, str) and current_call_identifier and current_tool_name == 'terminal':
                        try:
                            parts = shlex.split(current_target_value)
                            if len(parts) == 4 and parts[:3] == ['/runtime/.venv/bin/python', '/control/management-status.py', 'video-source-status']:
                                request = json.loads(parts[3])
                                if isinstance(request, dict) and set(request) == {'service', 'job_id'}:
                                    video_calls[current_call_identifier] = request
                        except (ValueError, TypeError):
                            pass
        else:
            current_error_flag = current_event_record.get('is_error')
            current_output_value = current_event_record.get('output')
            try:
                current_parsed_output = json.loads(current_output_value) if isinstance(current_output_value, str) else None
            except ValueError:
                current_parsed_output = None
            # Only the bounded, already recorded tool output is exposed to the session UI.
            if isinstance(current_output_value, str):
                display_output = current_parsed_output.get('output') if isinstance(current_parsed_output, dict) and isinstance(current_parsed_output.get('output'), str) else current_output_value
                current_event_value['output'] = display_output[:4000]
                current_event_value['output_truncated'] = len(display_output) > 4000
            current_duration = current_event_record.get('duration_ms')
            if type(current_duration) is int and 0 <= current_duration <= 86400000:
                current_event_value['duration_ms'] = current_duration
            current_exit_value = current_parsed_output.get('exit_code') if isinstance(current_parsed_output, dict) else None
            if type(current_exit_value) is int:
                current_event_value['result'] = 'success' if current_exit_value == 0 and current_error_flag is not True else 'error'
            elif current_error_flag is True:
                current_event_value['result'] = 'error'
            else:
                current_event_value['result'] = 'recorded'
            if isinstance(current_call_identifier, str) and current_call_identifier in history_calls and current_event_value['result'] == 'success':
                page = parse_source_history_page(current_parsed_output.get('output'))
                if page is not None:
                    history_page = page
            if isinstance(current_call_identifier, str) and current_call_identifier in video_calls and current_event_value['result'] == 'success':
                try:
                    from workflow.domains.hermes_agent.video_operations import validate_hermes_video_source_response
                    request = video_calls[current_call_identifier]
                    response = json.loads(current_parsed_output['output'])
                    validate_hermes_video_source_response(request['service'], request['job_id'], response)
                    video_source = {'service': request['service'], 'job_id': request['job_id']}
                except (ValueError, TypeError, KeyError):
                    pass
        current_tool_events.append(current_event_value)
    return {**({'source_history_summary': source_history_summary(history_page), 'source_history_page': history_page} if history_page else {}), **({'video_source': video_source} if video_source else {}), 'events': current_tool_events[-8:], 'truncated': current_file_size > 128000 or len(current_tool_events) > 8}



def seed_form_proposal(text, prior_sources):
    """시드 변경 요청을 사용자 지정 또는 확인된 원본에만 연결한다."""
    if not isinstance(text, str) or not re.search(r'(시드|seed)', text, re.I) or not re.search(r'(다른|대른|새|변경|바꿔|바꾸|다시|재생성|생성|different|new|change)', text, re.I):
        return None
    ids = set(re.findall(r'(?<![0-9A-Za-z_-])\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}(?![0-9A-Za-z_-])', text))
    if len(ids) > 1:
        return {'reason':'원본 작업이 여러 개입니다. 사용할 작업 ID를 하나 지정하세요.'}
    if ids: source = next(iter(ids))
    elif len(prior_sources) == 1: source = next(iter(prior_sources))
    else: return {'reason':'원본 작업을 확실히 선택할 수 없습니다. Wan Fun Control 작업 ID를 지정하세요.'}
    matches = re.findall(r'(?:시드|seed)\s*(?:값\s*)?(?:를|는|을|은)?\s*(?:=|:|로)?\s*([-+]?\d+(?:\.\d+)?)', text, re.I)
    if len(matches) > 1 or (matches and (not matches[0].isdigit() or int(matches[0]) > 2147483647)):
        return {'reason':'시드는 0부터 2147483647 사이의 값 하나를 지정하세요.'}
    return {'job_id':source, 'seed':int(matches[0]) if matches else None}


def ordered_pending_chat_sessions(root):
    """각 세션의 첫 대기 요청을 접수 시각 순으로 정렬한다."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        return []
    candidates = []
    for path in root.glob('[0-9a-f]' * 32 + '.json'):
        try:
            if path.is_symlink():
                continue
            session = json.loads(path.read_text(encoding='utf-8'))
            queue = session.get('chat_queue', [])
            if not isinstance(queue, list) or any(not isinstance(row, dict) for row in queue):
                continue
            row = next((row for row in queue if row.get('state') in ('queued', 'dispatching')), None)
            if row is None:
                continue
            created = datetime.fromisoformat(row['created_at'])
            if created.tzinfo is None or created.utcoffset() is None:
                continue
            created = created.astimezone(timezone.utc)
            delta = created - datetime(1970, 1, 1, tzinfo=timezone.utc)
            fallback_order = (delta.days * 86400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1000
            order = row.get('queue_order_ns', fallback_order)
            if type(order) is not int or order <= 0:
                continue
            candidates.append((order, path.stem))
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            continue
    return [session_id for _, session_id in sorted(candidates)]


class HermesServiceManager:
    def __init__(self, hermes_storage_root=HERMES_JOB_DIRECTORY, hermes_session_root=None):
        self.hermes_storage_root = Path(hermes_storage_root)
        self.hermes_session_root = hermes_session_root
        self.hermes_thread_lock = threading.RLock()
        self.chat_queue_wakeup = threading.Event()
        self.chat_intent_cleanup_offset = 0

    def retire_terminal_chat_queue_intents(self):
        """종료 처리 직후 중단돼 남은 색인만 순차적으로 정리한다."""
        from workflow.common import gpu_job_queue
        from workflow.common.gpu_chat_admission import hold_gpu_queue_lock, list_chat_queue_intents_locked, retire_chat_queue_intent
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        queue_root_directory = Path(gpu_job_queue.GPU_QUEUE_DIRECTORY)
        if not queue_root_directory.exists():
            return
        with hold_gpu_queue_lock(queue_root_directory):
            queue_intent_records = sorted(list_chat_queue_intents_locked(queue_root_directory), key=lambda queue_intent_record:queue_intent_record['resident_id'])
        if not queue_intent_records:
            self.chat_intent_cleanup_offset = 0
            return
        cleanup_start_index = self.chat_intent_cleanup_offset % len(queue_intent_records)
        cleanup_batch_size = min(64, len(queue_intent_records))
        cleanup_batch_records = [queue_intent_records[(cleanup_start_index + cleanup_batch_index) % len(queue_intent_records)] for cleanup_batch_index in range(cleanup_batch_size)]
        self.chat_intent_cleanup_offset = cleanup_start_index + cleanup_batch_size
        session_store_instance = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
        for queue_intent_record in cleanup_batch_records:
            try:
                session_queue_record = session_store_instance.read_session_record(queue_intent_record['session_id'])
                session_queue_rows = session_queue_record.get('chat_queue', [])
                if not isinstance(session_queue_rows, list):
                    continue
                matching_request_records = [chat_request_record for chat_request_record in session_queue_rows if isinstance(chat_request_record, dict) and chat_request_record.get('request_id') == queue_intent_record['request_id']]
                if (len(matching_request_records) == 1 and matching_request_records[0].get('state') in ('cancelled', 'dispatched')
                        and type(matching_request_records[0].get('queue_order_ns')) is int
                        and matching_request_records[0].get('queue_order_ns') == queue_intent_record['order_ns']):
                    retire_chat_queue_intent(queue_root_directory, queue_intent_record['session_id'], queue_intent_record['request_id'], queue_intent_record['order_ns'])
            except (OSError, ValueError, TypeError, KeyError):
                # 확인할 수 없는 기록은 보존하고 다른 세션의 복구는 계속한다.
                continue

    def dispatch_chat_queue(self, session_id, *, dispatcher_stop_event=None):
        """Advance at most one durable request; the service lock serializes all dispatchers."""
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        from workflow.domains.hermes_agent.chat_queue_store import transition, prepare_legacy_chat_request
        from workflow.domains.hermes_agent.context_checkpoint import build_context_messages
        store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
        with self.hold_hermes_service_lock():
            if dispatcher_stop_event is not None and dispatcher_stop_event.is_set():
                return None
            pending_request_record = prepare_legacy_chat_request(store, session_id)
            if not pending_request_record or pending_request_record.get('edit_token'):
                return None
            if pending_request_record.get('require_resident') is True:
                from workflow.common import gpu_job_queue
                from workflow.common.gpu_chat_admission import register_chat_queue_intent
                pending_order_nanoseconds = pending_request_record.get('queue_order_ns')
                if pending_order_nanoseconds is not None:
                    if type(pending_order_nanoseconds) is not int or pending_order_nanoseconds <= 0:
                        raise ValueError('대화 요청의 대기 순서를 확인할 수 없습니다.')
                    register_chat_queue_intent(gpu_job_queue.GPU_QUEUE_DIRECTORY, session_id, pending_request_record['request_id'], pending_order_nanoseconds)
        runtime_prevalidated = False
        if pending_request_record.get('require_resident') is True:
            from workflow.domains.hermes_agent.resident_queue import find_session_resident, recover_clean_failed_residents
            try:
                resident_id = find_session_resident(session_id)
            except ValueError:
                recover_clean_failed_residents(session_id)
                resident_id = find_session_resident(session_id)
            if resident_id is None:
                validate_hermes_runtime_ready(COMPLEX_MODEL)
                runtime_prevalidated = True
        with self.hold_hermes_service_lock():
            if dispatcher_stop_event is not None and dispatcher_stop_event.is_set():
                return None
            session = store.read_session_record(session_id)
            row = next((item for item in session.get('chat_queue', []) if item.get('state') in ('queued', 'dispatching')), None)
            if not row or row.get('request_id') != pending_request_record.get('request_id') or row.get('edit_token'):
                return None
            if row.get('require_resident') is True:
                from workflow.domains.hermes_agent.resident_queue import ensure_session_resident, inspect_resident
                order = row.get('queue_order_ns')
                if order is not None and (type(order) is not int or order <= 0):
                    raise ValueError('대화 요청의 대기 순서를 확인할 수 없습니다.')
                resident = ensure_session_resident(session_id, row['request_id'], queue_order_ns=order, runtime_prevalidated=runtime_prevalidated, defer_runtime_validation=True)
                if resident.get('state') == 'retry':
                    return None
                if resident.get('state') != 'accepted' or not resident.get('id'):
                    raise ValueError('상주 모델 접수를 확인할 수 없습니다.')
                resident_state = inspect_resident(resident['id'], session_id).get('state')
                if resident_state in ('queued', 'running'):
                    return None
                if resident_state != 'ready':
                    raise ValueError('상주 모델 준비 또는 GPU 예약을 확인할 수 없습니다.')
            self.ensure_context_operation_finished(session)
            existing = next((item for item in session['messages'] if item.get('request_id') == row['request_id']), None)
            if existing is None:
                # Refuse dispatch until every earlier response is terminal and readable.
                build_context_messages(session, self.read_context_job)
            if dispatcher_stop_event is not None and dispatcher_stop_event.is_set():
                return None
            if row['state'] == 'queued':
                row = transition(store, session_id, row['request_id'], 'queued', 'dispatching')
            result = self.submit_hermes_session_message_locked({'session_id':session_id, 'request_id':row['request_id'], 'prompt':row['prompt'], **({'model_profile':row['model_profile']} if row.get('model_profile') is not None else {})})
            transition(store, session_id, row['request_id'], 'dispatching', 'dispatched', result['job_id'])
            if row.get('require_resident') is True and row.get('queue_order_ns') is not None:
                from workflow.common import gpu_job_queue
                from workflow.common.gpu_chat_admission import retire_chat_queue_intent
                retire_chat_queue_intent(gpu_job_queue.GPU_QUEUE_DIRECTORY, session_id, row['request_id'], row['queue_order_ns'])
            return result

    def start_chat_queue_dispatcher(self):
        """Recover pending requests on startup and retry while the service is running."""
        from workflow.domains.hermes_agent.session_store import HERMES_SESSION_ROOT
        root = Path(self.hermes_session_root) if self.hermes_session_root is not None else HERMES_SESSION_ROOT
        stop = threading.Event()
        dispatcher_state_lock = threading.Lock()
        active_session_identifiers = set()
        def dispatch_pending_session(chat_session_identifier):
            try:
                self.dispatch_chat_queue(chat_session_identifier, dispatcher_stop_event=stop)
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                # 요청 원본은 유지하고 다음 순회에서 다시 확인한다.
                pass
            finally:
                with dispatcher_state_lock:
                    active_session_identifiers.discard(chat_session_identifier)
        def run():
            next_intent_cleanup_time = 0
            next_session_dispatch_offset = 0
            while not stop.is_set():
                self.chat_queue_wakeup.wait(3)
                self.chat_queue_wakeup.clear()
                if stop.is_set():
                    return
                if time.monotonic() >= next_intent_cleanup_time:
                    next_intent_cleanup_time = time.monotonic() + 30
                    try:
                        self.retire_terminal_chat_queue_intents()
                    except (OSError, ValueError, TypeError, KeyError):
                        # 색인 관측 오류가 새로운 대화의 실행까지 멈추지는 않는다.
                        pass
                try:
                    sessions = ordered_pending_chat_sessions(root)
                except OSError:
                    continue
                if not sessions:
                    continue
                current_dispatch_start_index = next_session_dispatch_offset
                for session_offset_value in range(len(sessions)):
                    session_index_value = (current_dispatch_start_index + session_offset_value) % len(sessions)
                    chat_session_identifier = sessions[session_index_value]
                    with dispatcher_state_lock:
                        if len(active_session_identifiers) >= 2:
                            break
                        if chat_session_identifier in active_session_identifiers:
                            continue
                        active_session_identifiers.add(chat_session_identifier)
                    try:
                        threading.Thread(target=dispatch_pending_session, args=(chat_session_identifier,), daemon=True, name='hermes-chat-dispatch').start()
                    except RuntimeError:
                        with dispatcher_state_lock:
                            active_session_identifiers.discard(chat_session_identifier)
                        break
                    next_session_dispatch_offset = (session_index_value + 1) % len(sessions)
        threading.Thread(target=run, daemon=True, name='hermes-chat-queue').start()
        return stop

    @contextmanager
    def hold_hermes_service_lock(self):
        self.hermes_storage_root.mkdir(parents=True, exist_ok=True)
        with self.hermes_thread_lock:
            hermes_lock_descriptor = os.open(self.hermes_storage_root / '.service.lock', os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK, 0o666)
            with os.fdopen(hermes_lock_descriptor, 'a') as hermes_lock_stream:
                if not stat.S_ISREG(os.fstat(hermes_lock_stream.fileno()).st_mode):
                    raise ValueError('Hermes 서비스 잠금 파일 형식 오류')
                fcntl.flock(hermes_lock_stream, fcntl.LOCK_EX)
                yield

    def resolve_hermes_job_path(self, hermes_job_identifier):
        if not isinstance(hermes_job_identifier, str) or not HERMES_JOB_PATTERN.fullmatch(hermes_job_identifier):
            raise ValueError('Hermes 작업 ID 형식 오류')
        hermes_job_path = self.hermes_storage_root / hermes_job_identifier
        if hermes_job_path.is_symlink() or not hermes_job_path.is_dir():
            raise ValueError('Hermes 작업을 찾을 수 없습니다.')
        return hermes_job_path

    def list_hermes_job_paths(self, observation_limits=False):
        if observation_limits:
            hermes_observation_paths = []
            with os.scandir(self.hermes_storage_root) as hermes_directory_entries:
                for hermes_entry_count, hermes_directory_entry in enumerate(hermes_directory_entries, 1):
                    if hermes_entry_count > HERMES_JOB_OBSERVATION_MAXIMUM_ENTRIES:
                        raise ValueError('Hermes 작업 목록 관측 한도 초과')
                    if HERMES_JOB_PATTERN.fullmatch(hermes_directory_entry.name) and hermes_directory_entry.is_dir(follow_symlinks=False):
                        hermes_observation_paths.append(self.hermes_storage_root / hermes_directory_entry.name)
            return sorted(hermes_observation_paths, reverse=True)
        return [hermes_job_path for hermes_job_path in sorted(self.hermes_storage_root.iterdir(), reverse=True) if HERMES_JOB_PATTERN.fullmatch(hermes_job_path.name) and hermes_job_path.is_dir() and not hermes_job_path.is_symlink()]

    def read_hermes_job_record(self, hermes_job_path):
        hermes_request_record = json.loads((hermes_job_path / 'request.json').read_text())
        hermes_status_path = hermes_job_path / 'status.json'
        hermes_status_record = json.loads(hermes_status_path.read_text()) if hermes_status_path.is_file() else {'status':'unknown', 'message':'접수 중 프로세스가 종료됐는지 확인이 필요합니다. 자동으로 재접수하지 않습니다.'}
        if hermes_request_record.get('resident_id'):
            from workflow.domains.hermes_agent.resident_chat_executor import observe_resident_chat_status
            hermes_status_record = observe_resident_chat_status(hermes_job_path, hermes_status_record)
        hermes_result_path = hermes_job_path / 'result.json'
        hermes_result_record = json.loads(hermes_result_path.read_text()) if hermes_result_path.is_file() else None
        hermes_diff_path = hermes_job_path / 'change.diff'
        if hermes_diff_path.is_file():
            with hermes_diff_path.open('rb') as hermes_diff_stream:
                hermes_diff_text = hermes_diff_stream.read(500001).decode(errors='replace')
            hermes_diff_truncated = hermes_diff_path.stat().st_size > 500000
        else:
            hermes_diff_text = ''
            hermes_diff_truncated = False
        hermes_log_path = hermes_job_path / 'worker.log'
        if hermes_log_path.is_file():
            with hermes_log_path.open('rb') as hermes_log_stream:
                hermes_log_stream.seek(max(0, hermes_log_path.stat().st_size - 16000))
                hermes_log_text = hermes_log_stream.read().decode(errors='replace')
        else:
            hermes_log_text = ''
        hermes_agent_trace = read_hermes_agent_trace(hermes_job_path)
        if hermes_agent_trace:
            hermes_log_text += '\n--- Hermes 도구와 응답 ---\n' + hermes_agent_trace
        hermes_verification_path = hermes_job_path / 'verification.log'
        if hermes_verification_path.is_file() and not hermes_verification_path.is_symlink():
            with hermes_verification_path.open('rb') as hermes_verification_stream:
                hermes_verification_stream.seek(max(0, hermes_verification_path.stat().st_size - 16000))
                hermes_log_text += '\n--- 최종 독립 검증 ---\n' + hermes_verification_stream.read().decode(errors='replace')
        hermes_final_answer, hermes_answer_truncated = read_hermes_final_response(hermes_job_path)
        return {'id':hermes_job_path.name, 'request':hermes_request_record, 'status':hermes_status_record, 'result':hermes_result_record, 'diff':hermes_diff_text[:500000], 'diff_truncated':hermes_diff_truncated, 'log':hermes_log_text, 'final_response':hermes_final_answer, 'final_response_truncated':hermes_answer_truncated}

    def read_hermes_proposal_record(self, job_id):
        """세션 목록에는 상태와 제한된 최종 응답만 읽고 로그·diff는 읽지 않는다."""
        from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record
        path = self.resolve_hermes_job_path(job_id)
        status = read_bounded_delegation_record(path / 'status.json')
        if not isinstance(status, dict):
            raise ValueError('작업 상태 형식 오류')
        answer, truncated = read_hermes_final_response(path) if status.get('status') == 'completed' else (None, False)
        return {'status':status, 'final_response':answer, 'final_response_truncated':truncated}

    def submit_hermes_job_locked(self, hermes_payload_record, *, context=None, model_profile=None):
        if not {'request_id', 'prompt'} <= set(hermes_payload_record) or set(hermes_payload_record) - {'request_id', 'prompt', 'verification_modules'}:
            raise ValueError('request_id·prompt와 선택 검증 모듈만 전달하세요.')
        hermes_request_identifier = hermes_payload_record['request_id']
        hermes_prompt_text = hermes_payload_record['prompt']
        if not isinstance(hermes_request_identifier, str) or not HERMES_REQUEST_PATTERN.fullmatch(hermes_request_identifier):
            raise ValueError('접수 식별자는 영문·숫자·밑줄·하이픈 8~80자여야 합니다.')
        if not isinstance(hermes_prompt_text, str) or not hermes_prompt_text.strip() or len(hermes_prompt_text) > 12000:
            raise ValueError('작업 지시는 1~12000자여야 합니다.')
        hermes_verification_modules = validate_hermes_verification_modules(hermes_payload_record.get('verification_modules', []))
        for hermes_previous_path in self.list_hermes_job_paths():
            try:
                hermes_previous_request = json.loads((hermes_previous_path / 'request.json').read_text())
            except FileNotFoundError:
                continue
            if hermes_previous_request.get('request_id') == hermes_request_identifier:
                if hermes_previous_request.get('prompt') != hermes_prompt_text or hermes_previous_request.get('verification_modules', []) != hermes_verification_modules:
                    raise ValueError('같은 접수 식별자를 다른 지시에 사용할 수 없습니다.')
                if hermes_previous_request.get('context') != context:
                    raise ValueError('같은 접수 식별자의 대화 문맥이 변경되었습니다.')
                if model_profile is not None and hermes_previous_request.get('model_profile') != model_profile:
                    raise ValueError('같은 접수 식별자의 모델이 변경되었습니다.')
                return {'id':hermes_previous_path.name, 'duplicate':True}
        if model_profile is None:
            model_profile = route_hermes_request(hermes_payload_record)
        from workflow.common.hermes_model_routing import MODEL_FLOORS_MIB
        if model_profile not in MODEL_FLOORS_MIB:
            raise ValueError('지원하지 않는 Hermes 모델입니다.')
        validate_hermes_runtime_ready(model_profile)
        resident_id = None
        if isinstance(context, dict) and context.get('session_id'):
            from workflow.domains.hermes_agent.resident_queue import find_session_resident
            resident_id = find_session_resident(context['session_id'])
            if resident_id is not None and model_profile != 'qwen3.8-27b':
                raise ValueError('이 세션에 Qwen 3.8 상주 모델이 있습니다. 3.8을 사용하거나 상주 모델을 해제한 뒤 다시 요청하세요.')
        hermes_job_identifier = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S') + '-' + uuid.uuid4().hex[:8]
        hermes_job_path = self.hermes_storage_root / hermes_job_identifier
        hermes_job_path.mkdir()
        request_record = {**hermes_payload_record, 'model_profile': model_profile}
        policy = os.environ.get('SLIME_HERMES_MINIMAX_PREFERRED')
        if policy in ('0', '1'):
            request_record['minimax_preferred'] = policy == '1'
            request_record['image_selection_version'] = 1
        if context is not None:
            request_record['context'] = context
        if resident_id is not None:
            request_record['resident_id'] = resident_id
        write_record_atomically(hermes_job_path / 'request.json', request_record)
        if isinstance(context, dict) and context.get('session_id') and policy in ('0', '1'):
            write_record_atomically(hermes_job_path / 'minimax-form-pending.json', {'session_id':context['session_id'], 'job_id':hermes_job_identifier})
        with (hermes_job_path / 'worker.log').open('a') as hermes_log_stream:
            if resident_id is not None:
                from workflow.domains.hermes_agent.resident_chat_executor import launch_resident_chat
                launch_resident_chat(hermes_job_path, resident_id, context['session_id'], log=hermes_log_stream)
            else:
                launch_gpu_process([sys.executable, str(WORKFLOW_ROOT_DIRECTORY / 'workflow/domains/hermes_agent/worker.py'), str(hermes_job_path)], hermes_job_path, 'hermes-agent', stdout=hermes_log_stream, stderr=subprocess.STDOUT, start_new_session=True, cwd=WORKFLOW_ROOT_DIRECTORY)
        return {'id':hermes_job_identifier, 'status':'queued', 'duplicate':False}

    def read_context_job(self, job_id):
        path = self.resolve_hermes_job_path(job_id)
        job = self.read_hermes_job_record(path)
        if job.get('final_response_truncated') or (job['status'].get('status') == 'completed' and not job.get('final_response') and (path / 'hermes-events.jsonl').is_file()):
            job['final_response'] = read_hermes_context_response(path)
            job['final_response_truncated'] = False
        return job

    def ensure_context_operation_finished(self, session):
        operation = session.get('context_operation')
        if not operation:
            return
        job_id = operation.get('job_id')
        if not job_id:
            raise ValueError('대화 정리의 접수 상태를 먼저 확인하세요.')
        status = self.read_hermes_job_record(self.resolve_hermes_job_path(job_id))['status'].get('status')
        if status not in ('completed', 'failed', 'cancelled'):
            raise ValueError('대화 정리가 종료된 후 다시 시도하세요.')

    def submit_hermes_session_context_locked(self, payload):
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        from workflow.domains.hermes_agent.context_checkpoint import build_context_messages, context_prefix_digest
        if set(payload) != {'session_id', 'request_id'}:
            raise ValueError('세션 ID와 대화 정리 접수 ID를 전달하세요.')
        session_id, request_id = payload['session_id'], payload['request_id']
        if not isinstance(request_id, str) or not HERMES_REQUEST_PATTERN.fullmatch(request_id):
            raise ValueError('대화 정리 접수 식별자 형식 오류')
        store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
        session = store.read_session_record(session_id)
        operation = session.get('context_operation')
        read_job = self.read_context_job
        if not operation or operation.get('request_id') != request_id:
            self.ensure_context_operation_finished(session)
            messages = build_context_messages(session, read_job)
            if not messages:
                raise ValueError('정리할 대화가 없습니다.')
            count = len(session['messages'])
            execution_context = {'session_id': session_id, 'count': count,
                                 'digest': context_prefix_digest(session['messages'], count),
                                 'messages_digest': hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                                 'expected_checkpoint': session.get('context_checkpoint'),
                                 'automatic': session.get('context_automatic', True)}
            last_job = next((record.get('job_id') for record in reversed(session['messages']) if record.get('job_id')), None)
            if session.get('context_threshold') is not None: execution_context['threshold_tokens'] = session['context_threshold']
            execution_context['model_profile'] = read_job(last_job)['request'].get('model_profile', COMPLEX_MODEL) if last_job else COMPLEX_MODEL
            operation = store.begin_context_operation(session_id, request_id, execution_context)
        execution_context = operation['execution_context']
        prefix = session['messages'][:execution_context['count']]
        if context_prefix_digest(prefix, len(prefix)) != execution_context['digest']:
            raise ValueError('대화가 변경되어 정리 접수를 복원할 수 없습니다.')
        messages = build_context_messages({'messages': prefix, 'context_checkpoint': execution_context['expected_checkpoint']}, read_job)
        digest = hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if digest != execution_context['messages_digest']:
            raise ValueError('이전 작업 응답이 변경되어 정리 접수를 복원할 수 없습니다.')
        job_request_id = 'c_' + hashlib.sha256((session_id + ':' + request_id).encode()).hexdigest()
        context = {key: value for key, value in execution_context.items() if key != 'model_profile'}
        context.update(messages=messages, force=True, only=True)
        job = self.submit_hermes_job_locked({'request_id': job_request_id, 'prompt': '대화 문맥 정리'}, context=context, model_profile=execution_context['model_profile'])
        store.attach_context_job(session_id, request_id, job['id'])
        return {'session_id': session_id, 'job_id': job['id'], 'duplicate': job['duplicate']}

    def submit_hermes_session_message_locked(self, hermes_payload_record):
        from workflow.domains.hermes_agent.session_store import HermesSessionStore, HERMES_SESSION_ID_PATTERN
        if not {'session_id', 'request_id', 'prompt'} <= set(hermes_payload_record) or set(hermes_payload_record) - {'session_id', 'request_id', 'prompt', 'verification_modules', 'model_profile'}:
            raise ValueError('세션 ID·접수 ID·지시와 선택 검증 모듈만 전달하세요.')
        hermes_session_identifier = hermes_payload_record['session_id']
        hermes_request_identifier = hermes_payload_record['request_id']
        hermes_prompt_text = hermes_payload_record['prompt']
        model_profile = hermes_payload_record.get('model_profile')
        from workflow.common.hermes_model_routing import MODEL_FLOORS_MIB
        if 'model_profile' in hermes_payload_record and (not isinstance(model_profile, str) or model_profile not in MODEL_FLOORS_MIB):
            raise ValueError('지원하지 않는 Hermes 모델입니다.')
        if not isinstance(hermes_session_identifier, str) or not HERMES_SESSION_ID_PATTERN.fullmatch(hermes_session_identifier):
            raise ValueError('세션 ID 형식 오류')
        if not isinstance(hermes_request_identifier, str) or not HERMES_REQUEST_PATTERN.fullmatch(hermes_request_identifier):
            raise ValueError('접수 식별자 형식 오류')
        if not isinstance(hermes_prompt_text, str) or not hermes_prompt_text.strip() or len(hermes_prompt_text) > 8000:
            raise ValueError('세션 메시지는 1~8000자여야 합니다.')
        hermes_verification_modules = validate_hermes_verification_modules(hermes_payload_record.get('verification_modules', []))
        hermes_session_store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
        hermes_session_record = hermes_session_store.read_session_record(hermes_session_identifier)
        hermes_previous_message = next((current_message_record for current_message_record in hermes_session_record['messages'] if current_message_record.get('request_id') == hermes_request_identifier), None)
        if hermes_previous_message is None:
            self.ensure_context_operation_finished(hermes_session_record)
        from workflow.domains.hermes_agent.context_checkpoint import build_context_messages, build_coding_context_messages, context_prefix_digest
        read_previous_job = self.read_context_job
        hermes_context_truncated = False
        execution_context = None
        if hermes_previous_message is None:
            from workflow.common.hermes_model_routing import COMPLEX_TASK
            coding_context = bool(hermes_session_record.get('context_automatic', True) and COMPLEX_TASK.search(hermes_prompt_text))
            if coding_context:
                context_messages, omitted = build_coding_context_messages(hermes_session_record, read_previous_job)
                hermes_context_truncated = omitted > 0
            else:
                context_messages = build_context_messages(hermes_session_record, read_previous_job)
            count = len(hermes_session_record['messages'])
            context_digest = hashlib.sha256(json.dumps(context_messages, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            execution_context = {'session_id': hermes_session_identifier, 'count': count,
                                 'digest': context_prefix_digest(hermes_session_record['messages'], count),
                                 'messages_digest': context_digest,
                                 'expected_checkpoint': hermes_session_record.get('context_checkpoint'),
                                 'automatic': hermes_session_record.get('context_automatic', True)}
            if hermes_session_record.get('context_threshold') is not None: execution_context['threshold_tokens'] = hermes_session_record['context_threshold']
            if coding_context:
                execution_context['context_mode'] = 'coding'
            hermes_execution_prompt = hermes_prompt_text
        else:
            hermes_execution_prompt = hermes_previous_message['execution_prompt']
            hermes_context_truncated = hermes_previous_message.get('context_truncated', False)
            execution_context = hermes_previous_message.get('execution_context')
        hermes_message_result = hermes_session_store.append_session_request(hermes_session_identifier, hermes_request_identifier, hermes_prompt_text, hermes_execution_prompt, hermes_verification_modules, hermes_context_truncated, execution_context, model_profile)
        hermes_message_record = hermes_message_result['message']
        hermes_job_request_id = 's_' + hashlib.sha256((hermes_session_identifier + ':' + hermes_request_identifier).encode()).hexdigest()
        hermes_job_payload = {'request_id': hermes_job_request_id, 'prompt': hermes_message_record['execution_prompt'], 'verification_modules': hermes_verification_modules}
        context_payload = None
        if execution_context is not None:
            prefix = hermes_session_record['messages'][:execution_context['count']]
            if context_prefix_digest(prefix, len(prefix)) != execution_context['digest']:
                raise ValueError('대화 문맥이 변경됐습니다. 기존 작업의 접수 상태를 확인하세요.')
            if execution_context.get('context_mode') == 'coding':
                context_messages, _ = build_coding_context_messages({'messages': prefix}, read_previous_job)
            else:
                context_messages = build_context_messages({'messages': prefix, 'context_checkpoint': execution_context['expected_checkpoint']}, read_previous_job)
            digest = hashlib.sha256(json.dumps(context_messages, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            if digest != execution_context['messages_digest']:
                raise ValueError('이전 작업 응답이 변경되어 문맥을 복원할 수 없습니다.')
            context_payload = {**execution_context, 'messages': context_messages, 'force': False, 'only': False}
        hermes_job_record = self.submit_hermes_job_locked(hermes_job_payload, context=context_payload, model_profile=model_profile)
        hermes_session_store.attach_session_job(hermes_session_identifier, hermes_request_identifier, hermes_job_record['id'])
        return {'session_id': hermes_session_identifier, 'message_id': hermes_message_record['id'], 'job_id': hermes_job_record['id'], 'duplicate': hermes_message_result['duplicate'], 'context_truncated': hermes_message_record['context_truncated']}

    def read_hermes_session_view_locked(self, hermes_payload_record):
        """세션과 작업의 최근 상태를 한 응답으로 제공한다."""
        if set(hermes_payload_record)-{'session_id','offset','limit','snapshot'} or 'session_id' not in hermes_payload_record:
            raise ValueError('세션 ID와 이력 페이지 정보만 전달하세요.')
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        hermes_session_store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
        hermes_session_record = hermes_session_store.read_session_record(hermes_payload_record['session_id'])
        current_offset_value=hermes_payload_record.get('offset',0)
        current_limit_value=hermes_payload_record.get('limit',20)
        if type(current_limit_value) is not int or not 1 <= current_limit_value <= 20:
            raise ValueError('세션 이력 페이지 크기는 1~20이어야 합니다.')
        current_snapshot_value=hashlib.sha256(json.dumps(hermes_session_record['messages'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()
        if type(current_offset_value) is not int or current_offset_value<0 or current_offset_value>len(hermes_session_record['messages']):
            raise ValueError('세션 이력 위치 오류')
        if current_offset_value and hermes_payload_record.get('snapshot')!=current_snapshot_value:
            raise ValueError('세션 이력이 변경됐습니다. 처음부터 다시 조회하세요.')
        if 'snapshot' in hermes_payload_record and hermes_payload_record['snapshot']!=current_snapshot_value:
            raise ValueError('세션 이력이 변경됐습니다. 처음부터 다시 조회하세요.')
        from collections import Counter
        if any(not isinstance(item,dict) or (item.get('job_id') is not None and not isinstance(item.get('job_id'),str)) for item in hermes_session_record['messages']):
            raise ValueError('세션 작업 연결 형식 오류')
        current_session_job_counts=Counter(item['job_id'] for item in hermes_session_record['messages'] if isinstance(item.get('job_id'),str))
        current_end_index=len(hermes_session_record['messages'])-current_offset_value
        current_start_index=max(0,current_end_index-current_limit_value)
        hermes_view_messages = []
        prior_sources = set()
        def collect_source(message):
            if message.get('job_id'):
                try:
                    source = read_hermes_tool_activity(self.resolve_hermes_job_path(message['job_id'])).get('video_source')
                    if source and source.get('service') == 'wan22-fun-control': prior_sources.add(source['job_id'])
                except (OSError, ValueError, TypeError, KeyError): pass
            form_id = message.get('form_id')
            if isinstance(form_id, str) and re.fullmatch(r'[a-f0-9]{32}', form_id):
                try:
                    from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
                    receipt_id = 'vf_' + hashlib.sha256((hermes_session_record['id'] + ':' + form_id).encode()).hexdigest()
                    receipt = HermesDelegationStore().read_service_delegation(receipt_id, 'wan22-fun-control')
                    if receipt.get('state') == 'accepted': prior_sources.add(receipt['job_id'])
                except (OSError, ValueError, TypeError, KeyError): pass
        for earlier in hermes_session_record['messages'][:current_start_index]:
            collect_source(earlier)
        for current_message_record in hermes_session_record['messages'][current_start_index:current_end_index]:
            current_view_record = {'text': current_message_record['text'], 'created_at':current_message_record.get('created_at'), 'job_id': current_message_record.get('job_id'), 'session_job_unique':current_session_job_counts[current_message_record['job_id']]==1 if isinstance(current_message_record.get('job_id'),str) else None, 'context_truncated': current_message_record.get('context_truncated', False), 'job': None}
            if current_message_record.get('report_job_id') and current_message_record['report_job_id'] == current_view_record['job_id']:
                current_view_record['report_job_id'] = current_message_record['report_job_id']
            proposal = seed_form_proposal(current_message_record.get('text'), prior_sources)
            if proposal: current_view_record['seed_form_proposal'] = proposal
            if current_message_record.get('form_id'):
                current_view_record['form_id'] = current_message_record['form_id']
            if current_view_record['job_id']:
                try:
                    current_job_path = self.resolve_hermes_job_path(current_view_record['job_id'])
                    current_status_path = current_job_path / 'status.json'
                    current_status_record = json.loads(current_status_path.read_text()) if current_status_path.is_file() and not current_status_path.is_symlink() else {'status':'unknown'}
                    if not isinstance(current_status_record, dict):
                        raise ValueError('작업 상태 형식 오류')
                    current_final_answer, current_answer_truncated = read_hermes_final_response(current_job_path)
                    from .conversation_results import generation_history_table
                    activity = read_hermes_tool_activity(current_job_path)
                    if current_status_record.get('status') in ('queued','running','unknown'):
                        from .conversation_observation import conversation_observation
                        activity['observation'] = conversation_observation(current_job_path, current_status_record, hermes_session_record['id'])
                    table = generation_history_table(activity)
                    if table is None and current_final_answer:
                        table = generation_history_table({"source_history_summary": current_final_answer})
                        if table is not None:
                            activity["history_table_is_answer"] = True
                    if table is not None:
                        activity["history_table"] = table
                    current_view_record['job'] = {'status': current_status_record, 'final_response': current_final_answer, 'final_response_truncated': current_answer_truncated, 'tool_activity': activity}
                    if current_final_answer and not current_answer_truncated and (
                            "HERMES_WORKFLOW_PROPOSAL" in current_final_answer or "```json" in current_final_answer):
                        from .workflow_review import extract_conversation_workflow_proposal
                        try:
                            proposal = extract_conversation_workflow_proposal(current_final_answer)
                        except ValueError:
                            pass
                        else:
                            current_view_record["job"]["workflow_proposal"] = proposal
                except (OSError, ValueError, TypeError, KeyError):
                    current_view_record['job'] = {'status': {'status':'unavailable', 'message':'작업 상태를 읽을 수 없습니다.'}, 'final_response': None, 'final_response_truncated': False}
            hermes_view_messages.append(current_view_record)
            collect_source(current_message_record)
        context_view = {'automatic': hermes_session_record.get('context_automatic', True), 'threshold': hermes_session_record.get('context_threshold'), 'checkpoint': None, 'operation': None, 'usage': None}
        checkpoint = hermes_session_record.get('context_checkpoint')
        if checkpoint:
            from workflow.domains.hermes_agent.context_checkpoint import validate_context_checkpoint
            validate_context_checkpoint(checkpoint, hermes_session_record['messages'])
            context_view['checkpoint'] = {'count': checkpoint['count'], 'created_at': checkpoint.get('created_at'),
                                          'summary': '\n\n'.join(message['content'] for message in checkpoint['messages'] if message.get('_compressed_summary'))}
        operation = hermes_session_record.get('context_operation')
        if operation:
            job_id = operation.get('job_id')
            context_view['operation'] = {'request_id': operation.get('request_id'), 'job_id': job_id, 'status': 'pending'}
            if job_id:
                try:
                    job = self.read_hermes_job_record(self.resolve_hermes_job_path(job_id))
                    context_view['operation']['status'] = job['status'].get('status', 'unknown')
                    if context_view['operation']['status'] in ('queued', 'running', 'unknown'):
                        from workflow.domains.hermes_agent.conversation_observation import conversation_observation
                        context_view['operation']['observation'] = conversation_observation(
                            self.resolve_hermes_job_path(job_id), job['status'], hermes_session_record['id'])
                except (OSError, ValueError, KeyError, TypeError):
                    context_view['operation']['status'] = 'unknown'
        latest_job = next((item.get('job_id') for item in reversed(hermes_session_record['messages']) if item.get('job_id')), None)
        if operation and operation.get('job_id') and operation.get('execution_context', {}).get('count') == len(hermes_session_record['messages']):
            latest_job = operation['job_id']
        if latest_job:
            try:
                path = self.resolve_hermes_job_path(latest_job) / 'context-status.json'
                if not path.exists():
                    job = self.read_hermes_job_record(self.resolve_hermes_job_path(latest_job))
                    if job['status'].get('status') == 'running':
                        path = self.resolve_hermes_job_path(latest_job) / 'context-exchange' / 'progress.json'
                if path.is_file() and not path.is_symlink() and path.stat().st_size <= 4096:
                    usage = json.loads(path.read_text(encoding='utf-8'))
                    if isinstance(usage, dict) and type(usage.get('tokens')) is int and usage['tokens'] >= 0 and all(usage.get(key) is None or (type(usage[key]) is int and usage[key] >= 0) for key in ('tokens_after', 'threshold')):
                        context_view['usage'] = usage
            except (OSError, ValueError, TypeError):
                pass
        return {'id': hermes_session_record['id'], 'title': hermes_session_record.get('title', '새 대화'), 'message_count': len(hermes_session_record['messages']), 'messages': hermes_view_messages, 'truncated': current_start_index > 0, 'offset':current_offset_value, 'next_offset':current_offset_value+len(hermes_view_messages) if current_start_index>0 else None, 'snapshot':current_snapshot_value, 'queried_at': datetime.now(timezone.utc).isoformat(), 'context': context_view}

    def execute_hermes_command(self, hermes_command_name, hermes_payload_record):
        if hermes_command_name in ('hermes-resident-start', 'hermes-resident-status', 'hermes-resident-release', 'hermes-gpu-handoff-preview', 'hermes-gpu-handoff-approve', 'hermes-gpu-handoff-status', 'hermes-gpu-handoff-list', 'hermes-gpu-handoff-withdraw', 'hermes-gpu-handoff-writer-context', 'hermes-gpu-handoff-recover-release', 'hermes-gpu-handoff-recover-submission', 'hermes-gpu-handoff-recover-reload', 'hermes-gpu-handoff-retry-reload', 'hermes-gpu-handoff-cancel'):
            if not isinstance(hermes_payload_record, dict):
                raise ValueError('GPU 양도 입력은 객체여야 합니다.')
            from workflow.domains.hermes_agent.session_store import HermesSessionStore
            sessions = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
            if hermes_command_name == 'hermes-gpu-handoff-writer-context':
                if set(hermes_payload_record) != {'session_id'}: raise ValueError('세션이 필요합니다.')
                sessions.read_session_record(hermes_payload_record['session_id'])
                from workflow.domains.hermes_agent.gpu_handoff_writer import inspect_writer_workspace
                workspace = inspect_writer_workspace()
                return {'session_id':hermes_payload_record['session_id'], 'fingerprint':workspace['fingerprint'], 'document_root':workspace['document_root'], 'state_root':workspace['state_root']}
            if hermes_command_name == 'hermes-resident-start':
                if set(hermes_payload_record) != {'session_id','request_id'}: raise ValueError('대화 세션과 요청 ID가 필요합니다.')
                session_id = hermes_payload_record['session_id']
                sessions.read_session_record(session_id)
                validate_hermes_runtime_ready('qwen3.8-27b')
                from workflow.domains.hermes_agent.resident_queue import ensure_session_resident
                from workflow.domains.hermes_agent.resident_preload import locked_policy, save_policy
                with locked_policy() as policy_root:
                    result = ensure_session_resident(session_id, hermes_payload_record['request_id'])
                    if result.get('state') == 'accepted':
                        save_policy(policy_root, session_id, True)
                    return result
            if hermes_command_name == 'hermes-resident-release':
                if set(hermes_payload_record) != {'session_id','resident_id','confirmed'} or hermes_payload_record['confirmed'] is not True:
                    raise ValueError('상주 모델 해제에 대한 명시적 확인이 필요합니다.')
                session_id = hermes_payload_record['session_id']
                sessions.read_session_record(session_id)
                from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
                from workflow.domains.hermes_agent.resident_queue import request_resident_release
                from workflow.domains.hermes_agent.resident_preload import locked_policy, read_policy, save_policy
                with locked_policy() as policy_root:
                    policy = read_policy(policy_root)
                    if policy and policy['session_id'] == session_id:
                        save_policy(policy_root, session_id, False)
                    return GpuHandoffStore().run_without_open_session_handoff(session_id, lambda: request_resident_release(hermes_payload_record['resident_id'], session_id))
            if hermes_command_name == 'hermes-resident-status':
                if set(hermes_payload_record) != {'session_id'}: raise ValueError('대화 세션이 필요합니다.')
                session_id = hermes_payload_record['session_id']
                sessions.read_session_record(session_id)
                from workflow.domains.hermes_agent.resident_queue import find_session_resident, inspect_resident
                resident_id = find_session_resident(session_id)
                return {'session_id':session_id, 'resident_id':resident_id, 'resident':inspect_resident(resident_id, session_id) if resident_id else {'state':'not_found'}}
            if hermes_command_name == 'hermes-gpu-handoff-status':
                if set(hermes_payload_record) != {'session_id','request_id'}: raise ValueError('세션과 GPU 양도 요청 ID가 필요합니다.')
                sessions.read_session_record(hermes_payload_record['session_id'])
                from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore, summarize_handoff_request
                store = GpuHandoffStore()
                record = store.read(hermes_payload_record['request_id'])
                if record is None:
                    withdrawn = store.read_withdrawal(hermes_payload_record['request_id'], hermes_payload_record['session_id'])
                    return withdrawn if withdrawn is not None else {'state':'not_found','request_id':hermes_payload_record['request_id']}
                if record['session_id'] != hermes_payload_record['session_id']: raise ValueError('GPU 양도 요청의 세션이 일치하지 않습니다.')
                summary = summarize_handoff_request(record)
                return {**{key:value for key,value in record.items() if key != 'target_request'}, 'target_summary':summary}
            if hermes_command_name == 'hermes-gpu-handoff-list':
                if set(hermes_payload_record) != {'session_id'}: raise ValueError('세션이 필요합니다.')
                session_id = hermes_payload_record['session_id']
                sessions.read_session_record(session_id)
                from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
                return {'session_id':session_id, 'handoffs':GpuHandoffStore().list_session_records(session_id)}
            if hermes_command_name == 'hermes-gpu-handoff-withdraw':
                if set(hermes_payload_record) != {'session_id','request_id','service','confirmed'} or hermes_payload_record['confirmed'] is not True:
                    raise ValueError('미접수 GPU 양도 철회 확인 입력 오류')
                session_id = hermes_payload_record['session_id']
                sessions.read_session_record(session_id)
                from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
                return GpuHandoffStore().withdraw_if_unaccepted(hermes_payload_record['request_id'], session_id, hermes_payload_record['service'])
            if hermes_command_name == 'hermes-gpu-handoff-recover-release':
                if set(hermes_payload_record) != {'session_id','request_id','expected_revision','confirmed'}:
                    raise ValueError('GPU 양도 복구 확인 입력 오류')
                sessions.read_session_record(hermes_payload_record['session_id'])
                from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
                from workflow.domains.hermes_agent.gpu_handoff_controller import recover_release_observation
                from workflow.domains.hermes_agent.gpu_handoff_scheduler import HandoffServiceAdapter
                record = recover_release_observation(GpuHandoffStore(), hermes_payload_record['request_id'], hermes_payload_record['session_id'], hermes_payload_record['expected_revision'], HandoffServiceAdapter(), confirmed=hermes_payload_record['confirmed'])
                return {key:value for key,value in record.items() if key != 'target_request'}
            if hermes_command_name == 'hermes-gpu-handoff-retry-reload':
                if set(hermes_payload_record) != {'session_id','request_id','expected_revision','confirmed'}:
                    raise ValueError('GPU 재적재 재시도 확인 입력 오류')
                sessions.read_session_record(hermes_payload_record['session_id'])
                from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
                from workflow.domains.hermes_agent.gpu_handoff_controller import retry_failed_reload
                from workflow.domains.hermes_agent.gpu_handoff_scheduler import HandoffServiceAdapter
                record = retry_failed_reload(GpuHandoffStore(), hermes_payload_record['request_id'], hermes_payload_record['session_id'], hermes_payload_record['expected_revision'], HandoffServiceAdapter(), confirmed=hermes_payload_record['confirmed'])
                return {key:value for key,value in record.items() if key != 'target_request'}
            if hermes_command_name == 'hermes-gpu-handoff-recover-reload':
                if set(hermes_payload_record) != {'session_id','request_id','expected_revision','confirmed'}:
                    raise ValueError('GPU 재적재 복구 확인 입력 오류')
                sessions.read_session_record(hermes_payload_record['session_id'])
                from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
                from workflow.domains.hermes_agent.gpu_handoff_controller import recover_verified_reload
                from workflow.domains.hermes_agent.gpu_handoff_scheduler import HandoffServiceAdapter
                record = recover_verified_reload(GpuHandoffStore(), hermes_payload_record['request_id'], hermes_payload_record['session_id'], hermes_payload_record['expected_revision'], HandoffServiceAdapter(), confirmed=hermes_payload_record['confirmed'])
                return {key:value for key,value in record.items() if key != 'target_request'}
            if hermes_command_name == 'hermes-gpu-handoff-recover-submission':
                if set(hermes_payload_record) != {'session_id','request_id','expected_revision','confirmed'}:
                    raise ValueError('GPU 양도 접수 복구 확인 입력 오류')
                sessions.read_session_record(hermes_payload_record['session_id'])
                from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
                from workflow.domains.hermes_agent.gpu_handoff_controller import recover_accepted_submission
                from workflow.domains.hermes_agent.gpu_handoff_scheduler import HandoffServiceAdapter
                record = recover_accepted_submission(GpuHandoffStore(), hermes_payload_record['request_id'], hermes_payload_record['session_id'], hermes_payload_record['expected_revision'], HandoffServiceAdapter(), confirmed=hermes_payload_record['confirmed'])
                return {key:value for key,value in record.items() if key != 'target_request'}
            if hermes_command_name == 'hermes-gpu-handoff-cancel':
                if set(hermes_payload_record) != {'session_id','request_id','expected_revision','confirmed'}:
                    raise ValueError('GPU 양도 중지 확인 입력 오류')
                sessions.read_session_record(hermes_payload_record['session_id'])
                from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
                from workflow.domains.hermes_agent.gpu_handoff_controller import cancel_handoff
                from workflow.domains.hermes_agent.gpu_handoff_scheduler import HandoffServiceAdapter
                record = cancel_handoff(GpuHandoffStore(), hermes_payload_record['request_id'], hermes_payload_record['session_id'], hermes_payload_record['expected_revision'], HandoffServiceAdapter(), confirmed=hermes_payload_record['confirmed'])
                return {key:value for key,value in record.items() if key != 'target_request'}
            from workflow.domains.hermes_agent.gpu_handoff_operations import preview_kimodo_handoff, approve_kimodo_handoff, preview_handoff, approve_handoff
            if hermes_command_name == 'hermes-gpu-handoff-preview':
                if set(hermes_payload_record) not in ({'session_id','resident_id','request'}, {'session_id','resident_id','request','service'}): raise ValueError('GPU 양도 검토 입력 오류')
                if 'service' in hermes_payload_record:
                    return preview_handoff(hermes_payload_record['session_id'], hermes_payload_record['resident_id'], hermes_payload_record['service'], hermes_payload_record['request'], session_store=sessions)
                return preview_kimodo_handoff(hermes_payload_record['session_id'], hermes_payload_record['resident_id'], hermes_payload_record['request'], session_store=sessions)
            required = {'request_id','session_id','resident_id','request','review_hash','confirmed'}
            if set(hermes_payload_record) not in (required, required | {'service'}):
                raise ValueError('GPU 양도 확인 입력 오류')
            if 'service' in hermes_payload_record:
                record = approve_handoff(hermes_payload_record['request_id'], hermes_payload_record['session_id'], hermes_payload_record['resident_id'], hermes_payload_record['service'], hermes_payload_record['request'], hermes_payload_record['review_hash'], confirmed=hermes_payload_record['confirmed'], session_store=sessions)
            else:
                record = approve_kimodo_handoff(hermes_payload_record['request_id'], hermes_payload_record['session_id'], hermes_payload_record['resident_id'], hermes_payload_record['request'], hermes_payload_record['review_hash'], confirmed=hermes_payload_record['confirmed'], session_store=sessions)
            return {key:value for key,value in record.items() if key != 'target_request'}
        if hermes_command_name in ('hermes-video-form-save', 'hermes-video-form-read', 'hermes-video-form-submit', 'hermes-video-form-status'):
            from workflow.domains.hermes_agent.session_store import HermesSessionStore
            store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
            expected = {'session_id', 'form_id', 'request', 'video_info'} if hermes_command_name == 'hermes-video-form-save' else {'session_id', 'form_id'}
            if set(hermes_payload_record) != expected: raise ValueError('폼 요청 필드 오류')
            session_id, form_id = hermes_payload_record['session_id'], hermes_payload_record['form_id']
            if hermes_command_name == 'hermes-video-form-save':
                return store.save_video_form(session_id, form_id, hermes_payload_record['request'], hermes_payload_record['video_info'])
            snapshot = store.read_video_form(session_id, form_id)
            request_id = 'vf_' + hashlib.sha256((session_id + ':' + form_id).encode()).hexdigest()
            if hermes_command_name == 'hermes-video-form-read': return {'form_id':form_id, **snapshot}
            if hermes_command_name == 'hermes-video-form-submit':
                from workflow.domains.hermes_agent.video_operations import submit_hermes_video_request
                return submit_hermes_video_request(request_id, 'wan22-fun-control', snapshot['request'])
            from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
            return HermesDelegationStore().read_service_delegation(request_id, 'wan22-fun-control')
        if not isinstance(hermes_payload_record, dict):
            raise ValueError('입력은 객체여야 합니다.')
        if hermes_command_name == 'hermes-workflow-list':
            from .workflow_commands import execute_workflow_command
            from .session_queue import append_session_video_jobs, append_session_flux_proposals, append_session_writer_proposals
            result = execute_workflow_command(WORKFLOW_ROOT_DIRECTORY, hermes_command_name, hermes_payload_record)
            result = append_session_video_jobs(result, hermes_payload_record, self.hermes_session_root)
            result = append_session_flux_proposals(result, hermes_payload_record, self.read_hermes_proposal_record, self.hermes_session_root)
            return append_session_writer_proposals(result, hermes_payload_record, self.read_hermes_proposal_record, self.hermes_session_root)
        if hermes_command_name in ("hermes-workflow-list", "hermes-workflow-catalog", "hermes-workflow-review", "hermes-workflow-register", "hermes-workflow-view", 'hermes-workflow-cancel', 'hermes-workflow-select', 'hermes-workflow-retry', 'hermes-workflow-draft-read', 'hermes-workflow-draft-save', 'hermes-form-list', 'hermes-form-read', 'hermes-form-save', 'hermes-workflow-image-preview', 'hermes-workflow-audio-preview'):
            from .workflow_commands import execute_workflow_command
            return execute_workflow_command(WORKFLOW_ROOT_DIRECTORY, hermes_command_name, hermes_payload_record)
        if hermes_command_name=='hermes-anchor-history-observe':
            from workflow.domains.hermes_agent.anchor_history_observer import read_hermes_anchor_history
            return read_hermes_anchor_history(hermes_payload_record)
        if hermes_command_name=='hermes-expression-catalog':
            from workflow.domains.hermes_agent.expression_observer import read_hermes_expression_catalog
            return read_hermes_expression_catalog(hermes_payload_record)
        if hermes_command_name == 'hermes-capture-proposal':
            if set(hermes_payload_record) != {'id'}:
                raise ValueError('Hermes 작업 ID만 전달하세요.')
            current_job_path = self.resolve_hermes_job_path(hermes_payload_record['id'])
            current_job_record = self.read_hermes_job_record(current_job_path)
            if current_job_record['status'].get('status') != 'completed' or current_job_record.get('final_response_truncated'):
                raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
            from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_capture_proposal
            from workflow.domains.hermes_agent.capture_delegation import inspect_capture_map_registration
            current_capture_proposal=parse_hermes_capture_proposal(current_job_record.get('final_response'))
            return {'job_id':hermes_payload_record['id'],'proposal':current_capture_proposal,'map_registration':inspect_capture_map_registration(current_capture_proposal)}
        if hermes_command_name == 'hermes-capture-status':
            if set(hermes_payload_record) != {'request_id','service'}:
                raise ValueError('캡처 접수 ID와 서비스가 필요합니다.')
            from workflow.domains.hermes_agent.capture_status import read_capture_delegation_status
            from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
            return read_capture_delegation_status(HermesDelegationStore(),hermes_payload_record['request_id'],hermes_payload_record['service'],WORKFLOW_ROOT_DIRECTORY)
        if hermes_command_name=='hermes-service-receipt':
            if set(hermes_payload_record)!={'request_id','service'}:
                raise ValueError('접수 ID와 서비스가 필요합니다.')
            from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore, list_hermes_service_receipt_names
            if hermes_payload_record['service'] not in list_hermes_service_receipt_names():
                raise ValueError('지원하는 접수 서비스가 아닙니다.')
            current_receipt_record=HermesDelegationStore().read_service_delegation(hermes_payload_record['request_id'],hermes_payload_record['service'])
            return {**current_receipt_record,'request_id':hermes_payload_record['request_id']}
        if hermes_command_name == 'hermes-kimodo-build-status':
            if hermes_payload_record:
                raise ValueError('빌드 상태 조회에는 입력을 전달할 수 없습니다.')
            from workflow.domains.hermes_agent.management_observer import read_hermes_kimodo_build_status
            return read_hermes_kimodo_build_status()
        if hermes_command_name == 'hermes-service-registration':
            from workflow.domains.hermes_agent.capabilities import list_management_service_registration, search_management_service_registration
            return search_management_service_registration(hermes_payload_record) if hermes_payload_record else list_management_service_registration()
        if hermes_command_name=='hermes-sprite-clip-playback':
            if set(hermes_payload_record)!={'draft','token','review_sha256','clip'}:
                raise ValueError('검토한 초안·토큰·검수 해시·클립 ID가 필요합니다.')
            from workflow.domains.hermes_agent.sprite_operations import render_hermes_sprite_clip_playback
            return render_hermes_sprite_clip_playback(hermes_payload_record['draft'],hermes_payload_record['token'],hermes_payload_record['review_sha256'],hermes_payload_record['clip'])
        if hermes_command_name=='hermes-sprite-playback':
            if set(hermes_payload_record)!={'draft','token','review_sha256','fps'}:
                raise ValueError('검토한 초안·토큰·검수 해시·FPS가 필요합니다.')
            from workflow.domains.hermes_agent.sprite_operations import render_hermes_sprite_anchor_playback
            return render_hermes_sprite_anchor_playback(hermes_payload_record['draft'],hermes_payload_record['token'],hermes_payload_record['review_sha256'],hermes_payload_record['fps'])
        if hermes_command_name == 'hermes-sprite-pending-status':
            if hermes_payload_record:raise ValueError('스프라이트 저장 상태 조회에는 입력을 전달할 수 없습니다.')
            from workflow.domains.hermes_agent.sprite_pending_observer import inspect_hermes_sprite_pending_status
            return inspect_hermes_sprite_pending_status()
        if hermes_command_name in ('hermes-sprite-preview','hermes-sprite-save','hermes-sprite-receipt'):
            from workflow.domains.hermes_agent.sprite_operations import preview_hermes_sprite_anchor_edit, save_hermes_sprite_anchor_once, read_hermes_sprite_anchor_receipt
            if hermes_command_name=='hermes-sprite-preview' and set(hermes_payload_record)=={'draft'}:
                return preview_hermes_sprite_anchor_edit(hermes_payload_record['draft'])
            if hermes_command_name=='hermes-sprite-save' and set(hermes_payload_record)=={'request_id','draft','token','review_sha256'}:
                return save_hermes_sprite_anchor_once(hermes_payload_record['request_id'],hermes_payload_record['draft'],hermes_payload_record['token'],hermes_payload_record['review_sha256'])
            if hermes_command_name=='hermes-sprite-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_sprite_anchor_receipt(hermes_payload_record['request_id'])
            raise ValueError('스프라이트 편집 요청 필드 오류')
        if hermes_command_name in ('hermes-sprite-catalog','hermes-sprite-detail'):
            from workflow.domains.hermes_agent.sprite_observer import read_hermes_sprite_catalog, read_hermes_sprite_sheet
            return (read_hermes_sprite_catalog if hermes_command_name=='hermes-sprite-catalog' else read_hermes_sprite_sheet)(hermes_payload_record)
        if hermes_command_name=='hermes-kimodo-keyframe-validate':
            from workflow.domains.hermes_agent.keyframe_observer import validate_hermes_kimodo_keyframe_batch
            return validate_hermes_kimodo_keyframe_batch(hermes_payload_record)
        if hermes_command_name=='hermes-kimodo-source-frame':
            if set(hermes_payload_record)!={'job_id','attempt_id','frame'}:raise ValueError('Kimodo 작업·시도·프레임이 필요합니다.')
            from workflow.domains.hermes_agent.kimodo_frame_observer import inspect_kimodo_source_frame
            return inspect_kimodo_source_frame(hermes_payload_record['job_id'],hermes_payload_record['attempt_id'],hermes_payload_record['frame'])
        if hermes_command_name=='hermes-kimodo-keyframe-preview':
            from workflow.domains.hermes_agent.keyframe_observer import read_hermes_kimodo_keyframe_preview
            if set(hermes_payload_record)!={'keyframe_id'}:
                raise ValueError('키프레임 ID만 전달하세요.')
            return read_hermes_kimodo_keyframe_preview(hermes_payload_record['keyframe_id'])
        if hermes_command_name=='hermes-kimodo-keyframes':
            from workflow.domains.hermes_agent.keyframe_observer import read_hermes_kimodo_keyframe_catalog
            return read_hermes_kimodo_keyframe_catalog(hermes_payload_record)
        if hermes_command_name in ('hermes-effect-register-preview','hermes-effect-register','hermes-effect-register-receipt'):
            from workflow.domains.hermes_agent.effect_operations import preview_hermes_effect_registration, register_hermes_effect_once, read_hermes_effect_registration_receipt
            if hermes_command_name=='hermes-effect-register-preview' and set(hermes_payload_record)=={'draft'}:
                return preview_hermes_effect_registration(hermes_payload_record['draft'])
            if hermes_command_name=='hermes-effect-register' and set(hermes_payload_record)=={'request_id','draft','review_sha256'}:
                return register_hermes_effect_once(hermes_payload_record['request_id'],hermes_payload_record['draft'],hermes_payload_record['review_sha256'])
            if hermes_command_name=='hermes-effect-register-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_effect_registration_receipt(hermes_payload_record['request_id'])
            raise ValueError('이펙트 등록 입력 필드 오류')
        if hermes_command_name in ('hermes-waypoint-preview','hermes-waypoint-replace','hermes-waypoint-receipt'):
            from workflow.domains.hermes_agent.effect_operations import preview_hermes_waypoint_replacement, replace_hermes_waypoint_once, read_hermes_waypoint_replacement_receipt
            if hermes_command_name=='hermes-waypoint-preview' and set(hermes_payload_record)=={'draft'}:
                return preview_hermes_waypoint_replacement(hermes_payload_record['draft'])
            if hermes_command_name=='hermes-waypoint-replace' and set(hermes_payload_record)=={'request_id','draft','review_sha256'}:
                return replace_hermes_waypoint_once(hermes_payload_record['request_id'],hermes_payload_record['draft'],hermes_payload_record['review_sha256'])
            if hermes_command_name=='hermes-waypoint-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_waypoint_replacement_receipt(hermes_payload_record['request_id'])
            raise ValueError('웨이포인트 교체 입력 필드 오류')
        if hermes_command_name in ('hermes-effect-preview','hermes-effect-save','hermes-effect-receipt'):
            from workflow.domains.hermes_agent.effect_operations import preview_hermes_effect_edit, save_hermes_effect_edit_once, read_hermes_effect_edit_receipt
            if hermes_command_name=='hermes-effect-preview' and set(hermes_payload_record)=={'draft'}:
                return preview_hermes_effect_edit(hermes_payload_record['draft'])
            if hermes_command_name=='hermes-effect-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_effect_edit_receipt(hermes_payload_record['request_id'])
            if hermes_command_name=='hermes-effect-save' and set(hermes_payload_record)=={'request_id','draft','token'}:
                return save_hermes_effect_edit_once(hermes_payload_record['request_id'],hermes_payload_record['draft'],hermes_payload_record['token'])
            raise ValueError('이펙트 편집 입력 필드 오류')
        if hermes_command_name in ('hermes-effect-catalog','hermes-effect-detail'):
            from workflow.domains.hermes_agent.effect_observer import list_hermes_effect_catalog, read_hermes_effect_detail
            if hermes_command_name=='hermes-effect-catalog':
                return list_hermes_effect_catalog(hermes_payload_record)
            if set(hermes_payload_record)!={'id'}:
                raise ValueError('이펙트 ID만 전달하세요.')
            return read_hermes_effect_detail(hermes_payload_record['id'])
        if hermes_command_name in ('hermes-kimodo-keyframe-source-review','hermes-kimodo-keyframe-save','hermes-kimodo-keyframe-receipt'):
            from workflow.domains.hermes_agent.kimodo_keyframe_operations import preview_hermes_keyframe_source, save_hermes_keyframe_once, read_hermes_keyframe_receipt
            if hermes_command_name=='hermes-kimodo-keyframe-source-review' and set(hermes_payload_record)=={'job_id','attempt_id','frame','tag'}:
                return preview_hermes_keyframe_source(hermes_payload_record['job_id'],hermes_payload_record['attempt_id'],hermes_payload_record['frame'],hermes_payload_record['tag'])
            if hermes_command_name=='hermes-kimodo-keyframe-save' and set(hermes_payload_record)=={'request_id','job_id','attempt_id','frame','tag','review_sha256'}:
                return save_hermes_keyframe_once(hermes_payload_record['request_id'],{current_key_name:hermes_payload_record[current_key_name] for current_key_name in ('job_id','attempt_id','frame','tag','review_sha256')})
            if hermes_command_name=='hermes-kimodo-keyframe-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_keyframe_receipt(hermes_payload_record['request_id'])
            raise ValueError('Kimodo 키프레임 요청 필드 오류')
        if hermes_command_name in ('hermes-billboard-load','hermes-billboard-preview','hermes-billboard-save','hermes-billboard-receipt'):
            from workflow.domains.hermes_agent.billboard_operations import load_hermes_billboard_edit, preview_hermes_billboard_edit, save_hermes_billboard_edit_once, read_hermes_billboard_edit_receipt
            if hermes_command_name == 'hermes-billboard-load' and set(hermes_payload_record)=={'texture'}:
                return load_hermes_billboard_edit(hermes_payload_record['texture'])
            if hermes_command_name == 'hermes-billboard-preview' and set(hermes_payload_record)=={'draft'}:
                return preview_hermes_billboard_edit(hermes_payload_record['draft'])
            if hermes_command_name == 'hermes-billboard-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_billboard_edit_receipt(hermes_payload_record['request_id'])
            if hermes_command_name == 'hermes-billboard-save' and set(hermes_payload_record)=={'request_id','draft','token','review_sha256'}:
                return save_hermes_billboard_edit_once(hermes_payload_record['request_id'],hermes_payload_record['draft'],hermes_payload_record['token'],hermes_payload_record['review_sha256'])
            raise ValueError('빌보드 편집 요청 필드 오류')
        if hermes_command_name == 'hermes-city-source':
            if set(hermes_payload_record)!={'map'}:raise ValueError('도시 맵 ID만 전달하세요.')
            from workflow.domains.hermes_agent.city_map_operations import read_hermes_city_source
            return read_hermes_city_source(hermes_payload_record['map'])
        if hermes_command_name in ('hermes-city-load','hermes-city-preview','hermes-city-save','hermes-city-receipt','hermes-city-history'):
            from workflow.domains.hermes_agent.city_map_operations import load_hermes_city_map, preview_hermes_city_map, save_hermes_city_map_once, read_hermes_city_receipt, list_hermes_city_receipts
            if hermes_command_name == 'hermes-city-history':
                if hermes_payload_record:
                    raise ValueError('도시 맵 이력에는 입력을 전달할 수 없습니다.')
                return list_hermes_city_receipts()
            if hermes_command_name == 'hermes-city-receipt':
                if set(hermes_payload_record) != {'request_id'}:
                    raise ValueError('접수 ID만 전달하세요.')
                return read_hermes_city_receipt(hermes_payload_record['request_id'])
            if hermes_command_name == 'hermes-city-load':
                if set(hermes_payload_record) != {'map'}:
                    raise ValueError('도시 맵 ID만 전달하세요.')
                return load_hermes_city_map(hermes_payload_record['map'])
            if hermes_command_name == 'hermes-city-preview':
                if set(hermes_payload_record) != {'draft'}:
                    raise ValueError('도시 맵 초안만 전달하세요.')
                return preview_hermes_city_map(hermes_payload_record['draft'])
            if set(hermes_payload_record) != {'request_id','draft','token'}:
                raise ValueError('접수 ID와 검토한 도시 맵 초안·토큰이 필요합니다.')
            return save_hermes_city_map_once(hermes_payload_record['request_id'],hermes_payload_record['draft'],hermes_payload_record['token'])
        if hermes_command_name == 'hermes-field-region':
            from workflow.domains.hermes_agent.field_map_operations import read_hermes_field_region
            return read_hermes_field_region(hermes_payload_record)
        if hermes_command_name in ('hermes-field-receipt','hermes-field-history'):
            from workflow.domains.hermes_agent.field_map_operations import read_hermes_field_receipt, list_hermes_field_receipts
            if hermes_command_name == 'hermes-field-history':
                if hermes_payload_record:
                    raise ValueError('맵 저장 이력에는 입력을 전달할 수 없습니다.')
                return list_hermes_field_receipts()
            if set(hermes_payload_record) != {'request_id'}:
                raise ValueError('접수 ID만 전달하세요.')
            return read_hermes_field_receipt(hermes_payload_record['request_id'])
        if hermes_command_name in ('hermes-field-load','hermes-field-preview','hermes-field-save'):
            from workflow.domains.hermes_agent.field_map_operations import load_hermes_field_map, preview_hermes_field_map, save_hermes_field_map_once
            if hermes_command_name == 'hermes-field-load':
                if set(hermes_payload_record) != {'map'}:
                    raise ValueError('맵 ID만 전달하세요.')
                return load_hermes_field_map(hermes_payload_record['map'])
            if hermes_command_name == 'hermes-field-preview':
                if set(hermes_payload_record) != {'draft'}:
                    raise ValueError('맵 초안만 전달하세요.')
                return preview_hermes_field_map(hermes_payload_record['draft'])
            if set(hermes_payload_record) != {'request_id','draft','token'}:
                raise ValueError('접수 ID와 검토한 맵 초안·토큰이 필요합니다.')
            return save_hermes_field_map_once(hermes_payload_record['request_id'],hermes_payload_record['draft'],hermes_payload_record['token'])
        if hermes_command_name == 'hermes-world-map':
            if set(hermes_payload_record)-{'map'} or ('map' in hermes_payload_record and not isinstance(hermes_payload_record['map'],str)):
                raise ValueError('월드맵 조회에는 맵 ID만 전달할 수 있습니다.')
            from workflow.domains.hermes_agent.asset_observer import read_hermes_world_map_catalog
            return read_hermes_world_map_catalog(hermes_payload_record.get('map'))
        if hermes_command_name in ('hermes-building-preview','hermes-building-save','hermes-building-receipt'):
            from workflow.domains.hermes_agent.building_operations import preview_hermes_building_anchor, save_hermes_building_anchor, read_hermes_building_receipt
            if hermes_command_name=='hermes-building-preview' and set(hermes_payload_record)=={'draft'}:
                return preview_hermes_building_anchor(hermes_payload_record['draft'])
            if hermes_command_name=='hermes-building-save' and set(hermes_payload_record)=={'request_id','draft','review_sha256'}:
                return save_hermes_building_anchor(hermes_payload_record['request_id'],hermes_payload_record['draft'],hermes_payload_record['review_sha256'])
            if hermes_command_name=='hermes-building-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_building_receipt(hermes_payload_record['request_id'])
            raise ValueError('건물 앵커 위임 입력 오류')
        if hermes_command_name == 'hermes-building-catalog':
            from workflow.domains.hermes_agent.asset_observer import read_hermes_building_catalog
            return read_hermes_building_catalog(hermes_payload_record)
        if hermes_command_name == 'hermes-billboard-catalog':
            from workflow.domains.hermes_agent.asset_observer import read_hermes_billboard_catalog
            return read_hermes_billboard_catalog(hermes_payload_record)
        if hermes_command_name == 'hermes-model-prepare-history':
            if hermes_payload_record:
                raise ValueError('모델 준비 이력에는 입력을 전달할 수 없습니다.')
            from workflow.domains.hermes_agent.model_preparation_store import HermesModelPreparationStore
            return HermesModelPreparationStore().list_model_preparation_receipts()
        if hermes_command_name in ('hermes-model-prepare', 'hermes-model-prepare-status'):
            if set(hermes_payload_record) != {'request_id', 'service'}:
                raise ValueError('모델 서비스와 접수 ID만 전달하세요.')
            from workflow.domains.hermes_agent.model_preparation_store import HermesModelPreparationStore
            current_model_store = HermesModelPreparationStore()
            current_service_name = hermes_payload_record['service']
            current_request_identifier = hermes_payload_record['request_id']
            if hermes_command_name == 'hermes-model-prepare-status':
                return current_model_store.read_model_preparation_receipt(current_request_identifier, current_service_name)
            import os
            from workflow.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
            from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, inspect_registered_model_operation, execute_management_command
            current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
            class ModelPreparationPreflightBlocked(ValueError):
                pass
            def validate_current_model_service(model_service_name):
                current_operation_name = inspect_registered_model_operation(model_service_name, MANAGEMENT_SERVICE_COMMANDS.get(model_service_name, ()), 'prepare')
                if current_operation_name is None:
                    raise ValueError('이 모델의 준비는 기존 관리 정책에서 제한됩니다.')
                if model_service_name == 'hermes-model':
                    from workflow.common.hermes_model_download import inspect_hermes_model_files
                    from workflow.common.model_prepare_process import inspect_registered_preparation_strict, hold_hermes_model_usage_guard, HermesModelUsageBusy
                    try:
                        current_preparation_state = inspect_registered_preparation_strict(WORKFLOW_ROOT_DIRECTORY, 'hermes-model')
                    except (OSError, ValueError, TypeError, UnicodeError) as current_preparation_error:
                        raise ModelPreparationPreflightBlocked('preparation_unknown') from current_preparation_error
                    if not inspect_hermes_model_files() and current_preparation_state != 'running':
                        try:
                            with hold_hermes_model_usage_guard(WORKFLOW_ROOT_DIRECTORY):
                                pass
                        except HermesModelUsageBusy as current_usage_error:
                            raise ModelPreparationPreflightBlocked('model_in_use') from current_usage_error
            def submit_current_model_service(model_service_name):
                current_operation_name = inspect_registered_model_operation(model_service_name, MANAGEMENT_SERVICE_COMMANDS.get(model_service_name, ()), 'prepare')
                if current_operation_name is None:
                    raise ValueError('이 모델의 준비는 기존 관리 정책에서 제한됩니다.')
                current_payload_value = {'action':'prepare'} if current_operation_name == 'prepare' else {}
                return execute_management_command(model_service_name, current_operation_name, current_payload_value, current_gateway_address)
            try:
                return current_model_store.execute_model_preparation_once(current_request_identifier, current_service_name, validate_current_model_service, submit_current_model_service)
            except ModelPreparationPreflightBlocked as current_blocked_error:
                return {'request_id':current_request_identifier, 'service':current_service_name, 'state':'blocked', 'reason':str(current_blocked_error)}
        if hermes_command_name == 'hermes-model-readiness':
            if set(hermes_payload_record) != {'service'} or not isinstance(hermes_payload_record['service'], str):
                raise ValueError('모델 서비스 식별자만 전달하세요.')
            from workflow.domains.hermes_agent.management_observer import read_hermes_model_readiness
            return read_hermes_model_readiness(hermes_payload_record['service'])
        if hermes_command_name == 'hermes-map-database-receipt':
            if set(hermes_payload_record)!={'database_request_id','request_sha256'}:
                raise ValueError('DB 맵 변경 요청 ID와 원본 요청 해시가 필요합니다.')
            from workflow.domains.map_assets.database_client import read_content_map_receipt_by_hash
            return read_content_map_receipt_by_hash(hermes_payload_record['database_request_id'],hermes_payload_record['request_sha256'])
        if hermes_command_name == 'hermes-content-database-status':
            if hermes_payload_record:
                raise ValueError('콘텐츠 DB 상태 조회에는 입력을 전달할 수 없습니다.')
            from workflow.domains.hermes_agent.management_observer import read_hermes_content_database_status
            return read_hermes_content_database_status()
        if hermes_command_name == 'hermes-model-download-status':
            if hermes_payload_record:raise ValueError('모델 다운로드 상태 조회에는 입력을 전달할 수 없습니다.')
            from workflow.domains.hermes_agent.management_observer import read_hermes_model_download_status
            return read_hermes_model_download_status()
        if hermes_command_name == 'hermes-model-inventory':
            if hermes_payload_record:
                raise ValueError('모델 보유량 조회에는 입력을 전달할 수 없습니다.')
            from workflow.domains.hermes_agent.management_observer import read_hermes_model_inventory
            return read_hermes_model_inventory()
        if hermes_command_name == 'hermes-capabilities':
            if hermes_payload_record:
                raise ValueError('관리 기능 목록에는 입력을 전달할 수 없습니다.')
            from workflow.domains.hermes_agent.capabilities import list_hermes_capability_catalog
            return list_hermes_capability_catalog()
        if hermes_command_name == 'hermes-delegation-history':
            if hermes_payload_record:
                raise ValueError('위임 접수 이력에는 입력을 전달할 수 없습니다.')
            from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
            return HermesDelegationStore().list_delegation_receipts()
        if hermes_command_name == 'hermes-delegation-job-status':
            if set(hermes_payload_record) != {'request_id'}:
                raise ValueError('위임 접수 ID만 전달하세요.')
            from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
            from workflow.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
            from workflow.common.management_gateway import execute_management_command
            import os
            current_receipt_record = {**HermesDelegationStore().read_delegation_status(hermes_payload_record['request_id']),'request_id':hermes_payload_record['request_id'],'service':'kimodo'}
            if current_receipt_record.get('state') != 'accepted':
                return {'receipt': current_receipt_record}
            current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
            current_job_status = execute_management_command('kimodo', 'status', {'id': current_receipt_record['job_id']}, current_gateway_address)
            if not isinstance(current_job_status, dict) or ('id' in current_job_status and current_job_status['id'] != current_receipt_record['job_id']):
                raise ValueError('Kimodo 작업 상태 응답 또는 작업 ID 오류')
            from workflow.domains.hermes_agent.failure_observer import observe_hermes_generator_failure
            current_failure_record=observe_hermes_generator_failure(current_job_status.get('status'),current_job_status.get('error'))
            return {'receipt': current_receipt_record, 'job': {**current_job_status,**current_failure_record}}
        if hermes_command_name == 'hermes-delegation-cancel':
            if set(hermes_payload_record) != {'request_id', 'job_id'}:
                raise ValueError('위임 접수 ID와 확인한 작업 ID가 필요합니다.')
            from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
            from workflow.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
            from workflow.common.management_gateway import execute_management_command
            import os
            current_receipt_record = HermesDelegationStore().read_delegation_status(hermes_payload_record['request_id'])
            if current_receipt_record.get('state') != 'accepted' or current_receipt_record.get('job_id') != hermes_payload_record['job_id']:
                raise ValueError('접수 기록과 확인한 Kimodo 작업 ID가 일치하지 않습니다.')
            current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
            current_cancel_result = execute_management_command('kimodo', 'cancel', {'id': current_receipt_record['job_id']}, current_gateway_address)
            if (not isinstance(current_cancel_result, dict) or current_cancel_result.get('cancel_requested') is not True
                    or ('id' in current_cancel_result and current_cancel_result['id'] != current_receipt_record['job_id'])):
                raise ValueError('중지 요청 접수 여부를 확인할 수 없습니다. Kimodo 상태를 조회하세요.')
            return {'job_id': current_receipt_record['job_id'], 'cancel_requested': True, 'status': current_cancel_result.get('status', 'unknown')}
        if hermes_command_name == 'hermes-delegation-status':
            if set(hermes_payload_record) != {'request_id'}:
                raise ValueError('위임 접수 ID만 전달하세요.')
            from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
            return {**HermesDelegationStore().read_delegation_status(hermes_payload_record['request_id']),'request_id':hermes_payload_record['request_id'],'service':'kimodo'}
        if hermes_command_name in ('hermes-writer-apply','hermes-writer-apply-status','hermes-writer-apply-history'):
            from workflow.domains.hermes_agent.writer_operations import apply_hermes_writer_proposal_once, read_writer_apply_receipt, list_writer_apply_receipts
            if hermes_command_name=='hermes-writer-apply-history':
                if hermes_payload_record:
                    raise ValueError('작가 적용 이력에는 입력을 전달할 수 없습니다.')
                return list_writer_apply_receipts()
            if hermes_command_name=='hermes-writer-apply-status':
                if set(hermes_payload_record)!={'request_id'}:
                    raise ValueError('적용 접수 ID만 전달하세요.')
                return read_writer_apply_receipt(hermes_payload_record['request_id'])
            if set(hermes_payload_record)!={'request_id','writer_request_id','job_id','proposal_hash'}:
                raise ValueError('적용 접수 ID·작가 위임 ID·작업 ID·제안 해시가 필요합니다.')
            return apply_hermes_writer_proposal_once(hermes_payload_record['request_id'],hermes_payload_record['writer_request_id'],hermes_payload_record['job_id'],hermes_payload_record['proposal_hash'])
        if hermes_command_name in ('hermes-writer-reservation-recover','hermes-writer-reservation-receipt'):
            from workflow.domains.hermes_agent.writer_reservation import recover_writer_reservation_once, read_writer_recovery_receipt
            if hermes_command_name=='hermes-writer-reservation-recover' and set(hermes_payload_record)=={'request_id','job_id','review_sha256','outside_processes_checked'}:
                return recover_writer_reservation_once(hermes_payload_record['request_id'],hermes_payload_record['job_id'],hermes_payload_record['review_sha256'],hermes_payload_record['outside_processes_checked'])
            if hermes_command_name=='hermes-writer-reservation-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_writer_recovery_receipt(hermes_payload_record['request_id'])
            raise ValueError('작가 예약 정리 입력 필드 오류')
        if hermes_command_name in ('hermes-generator-reservation-recover','hermes-generator-reservation-receipt'):
            from workflow.domains.hermes_agent.generator_reservation_recovery import recover_generator_reservation_once, read_generator_recovery_receipt
            if hermes_command_name=='hermes-generator-reservation-recover' and set(hermes_payload_record)=={'request_id','service','job_id','review_sha256','outside_processes_checked'}:
                return recover_generator_reservation_once(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['job_id'],hermes_payload_record['review_sha256'],hermes_payload_record['outside_processes_checked'])
            if hermes_command_name=='hermes-generator-reservation-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_generator_recovery_receipt(hermes_payload_record['request_id'])
            raise ValueError('생성기 예약 정리 입력 필드 오류')
        if hermes_command_name=='hermes-generator-reservation-inspect':
            if set(hermes_payload_record)!={'service','job_id'}:raise ValueError('서비스와 작업 ID가 필요합니다.')
            from workflow.domains.hermes_agent.reservation_observer import inspect_generator_reservation_identity
            return inspect_generator_reservation_identity(hermes_payload_record['service'],hermes_payload_record['job_id'])
        if hermes_command_name=='hermes-writer-reservation-preview':
            if set(hermes_payload_record)!={'job_id'}:raise ValueError('작가 작업 ID가 필요합니다.')
            from workflow.domains.hermes_agent.writer_reservation import preview_writer_reservation_recovery
            return preview_writer_reservation_recovery(hermes_payload_record['job_id'])
        if hermes_command_name=='hermes-writer-cancel':
            if set(hermes_payload_record)!={'request_id','job_id'}:raise ValueError('작가 접수 ID와 확인한 작업 ID가 필요합니다.')
            from workflow.domains.hermes_agent.writer_operations import cancel_hermes_writer_request
            return cancel_hermes_writer_request(hermes_payload_record['request_id'],hermes_payload_record['job_id'])
        if hermes_command_name == 'hermes-writer-search-paths':
            if set(hermes_payload_record) != {'request_id'}:raise ValueError('작가 위임 접수 ID만 전달하세요.')
            from workflow.domains.hermes_agent.writer_operations import read_hermes_writer_search_paths
            return read_hermes_writer_search_paths(hermes_payload_record['request_id'])
        if hermes_command_name == 'hermes-writer-job-material':
            from workflow.domains.hermes_agent.writer_operations import read_writer_job_material_page
            return read_writer_job_material_page(hermes_payload_record)
        if hermes_command_name == 'hermes-writer-job-review':
            if set(hermes_payload_record) != {'job_id'}:raise ValueError('작가 작업 ID만 전달하세요.')
            from workflow.domains.hermes_agent.writer_operations import read_writer_job_review
            return {'job_id':hermes_payload_record['job_id'],'job':read_writer_job_review(hermes_payload_record['job_id'])}
        if hermes_command_name == 'hermes-writer-job-search-paths':
            if set(hermes_payload_record) != {'job_id'}:raise ValueError('작가 작업 ID만 전달하세요.')
            from workflow.domains.hermes_agent.writer_operations import read_writer_job_search_paths
            return read_writer_job_search_paths(hermes_payload_record['job_id'])
        if hermes_command_name == 'hermes-writer-index-status':
            from workflow.domains.hermes_agent.writer_operations import read_hermes_writer_index_status
            if hermes_payload_record:
                raise ValueError('작가 색인 상태 조회에는 입력을 전달할 수 없습니다.')
            return read_hermes_writer_index_status()
        if hermes_command_name in ('hermes-writer-proposal-submit','hermes-writer-proposal-receipt'):
            from workflow.domains.hermes_agent.session_store import HermesSessionStore
            from workflow.domains.hermes_agent.gpu_handoff_kimodo import _derived_id
            from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
            expected={'session_id','request_id','job_id'} | ({'request','confirmed','snapshot','offset'} if hermes_command_name.endswith('submit') else set())
            if set(hermes_payload_record)!=expected:raise ValueError('작가 제안 접수 입력 오류')
            session_id=hermes_payload_record['session_id'];request_id=hermes_payload_record['request_id'];job_id=hermes_payload_record['job_id']
            sessions=HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
            session_record=sessions.read_session_record(session_id)
            from workflow.domains.hermes_agent.delegation_store import validate_service_job_identifier
            if not validate_service_job_identifier('flux-image',job_id):raise ValueError('작가 제안 작업 ID 오류')
            expected_id='writer_'+hashlib.sha256(json.dumps([session_id,job_id],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
            if request_id!=expected_id or sum(message.get('job_id')==job_id for message in session_record['messages'] if isinstance(message,dict))!=1:raise ValueError('작가 제안과 접수 ID가 일치하지 않습니다.')
            if hermes_command_name.endswith('receipt'):
                return {**HermesDelegationStore().read_service_delegation(_derived_id('handoff_',request_id),'writer-agent'),'request_id':request_id}
            if hermes_payload_record['confirmed'] is not True:raise ValueError('작가 작업 확인이 필요합니다.')
            page=self.read_hermes_session_view_locked({'session_id':session_id,'offset':hermes_payload_record['offset'],'limit':6,'snapshot':hermes_payload_record['snapshot']})
            candidates=[message for message in page['messages'] if message.get('job_id')==job_id and message.get('session_job_unique') is True]
            if len(candidates)!=1 or not candidates[0].get('job') or candidates[0]['job']['status'].get('status')!='completed' or candidates[0]['job'].get('final_response_truncated'):
                raise ValueError('완료된 대화 제안을 다시 확인하세요.')
            from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_writer_proposal
            proposal=parse_hermes_writer_proposal(candidates[0]['job'].get('final_response'))
            bound=hermes_payload_record['request']
            if not isinstance(bound,dict) or not isinstance(bound.get('request'),dict) or bound['request'].get('mode')!=proposal['mode']:
                raise ValueError('작가 제안의 작업 종류가 변경되었습니다.')
            from workflow.domains.hermes_agent.gpu_handoff_writer import submit_bound_writer_once
            from workflow.domains.hermes_agent.resident_queue import find_session_resident
            def ensure_no_resident():
                if find_session_resident(session_id):raise ValueError('상주 모델 상태가 변경되었습니다. GPU 양도를 다시 검토하세요.')
            return submit_bound_writer_once(request_id,session_id,hermes_payload_record['request'],preflight=ensure_no_resident)
        if hermes_command_name in ('hermes-delegate-writer','hermes-writer-status','hermes-writer-history'):
            from workflow.domains.hermes_agent.writer_operations import submit_hermes_writer_request, read_hermes_writer_status
            from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
            if hermes_command_name == 'hermes-writer-history':
                if hermes_payload_record:
                    raise ValueError('작가 위임 이력에는 입력을 전달할 수 없습니다.')
                return HermesDelegationStore().list_service_delegations('writer-agent')
            if hermes_command_name == 'hermes-delegate-writer':
                if set(hermes_payload_record) != {'request_id','request'}:
                    raise ValueError('작가 위임 접수 ID와 요청이 필요합니다.')
                return submit_hermes_writer_request(hermes_payload_record['request_id'],hermes_payload_record['request'])
            if set(hermes_payload_record) != {'request_id'}:
                raise ValueError('작가 위임 접수 ID만 전달하세요.')
            return read_hermes_writer_status(hermes_payload_record['request_id'])
        if hermes_command_name == 'hermes-translation-evidence':
            from workflow.domains.hermes_agent.translation_operations import search_hermes_translation_evidence
            if set(hermes_payload_record)!={'text'}:
                raise ValueError('번역 근거 검색에는 원문이 필요합니다.')
            return search_hermes_translation_evidence(hermes_payload_record['text'])
        if hermes_command_name in ('hermes-delegate-translation','hermes-translation-status','hermes-translation-history','hermes-translation-cancel'):
            from workflow.domains.hermes_agent.translation_operations import submit_hermes_translation_request, read_hermes_translation_status, cancel_hermes_translation_request
            from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
            if hermes_command_name == 'hermes-translation-history':
                if hermes_payload_record:
                    raise ValueError('번역 이력에는 입력을 전달할 수 없습니다.')
                return HermesDelegationStore().list_service_delegations('prompt-translation')
            if hermes_command_name == 'hermes-delegate-translation':
                if set(hermes_payload_record) != {'request_id','request'}:
                    raise ValueError('번역 접수 ID와 요청이 필요합니다.')
                return submit_hermes_translation_request(hermes_payload_record['request_id'],hermes_payload_record['request'])
            if hermes_command_name == 'hermes-translation-status':
                if set(hermes_payload_record) != {'request_id'}:
                    raise ValueError('번역 접수 ID만 전달하세요.')
                return read_hermes_translation_status(hermes_payload_record['request_id'])
            if set(hermes_payload_record) != {'request_id','job_id'}:
                raise ValueError('번역 접수 ID와 확인한 작업 ID가 필요합니다.')
            return cancel_hermes_translation_request(hermes_payload_record['request_id'],hermes_payload_record['job_id'])
        if hermes_command_name=='hermes-character-source-status':
            if set(hermes_payload_record)!={'job_id'}:raise ValueError('캐릭터 원본 작업 ID가 필요합니다.')
            from workflow.domains.hermes_agent.character_source_operations import read_character_source_job
            return {'service':'character-animation','job_id':hermes_payload_record['job_id'],'job':read_character_source_job(hermes_payload_record['job_id'])}
        if hermes_command_name=='hermes-image-source-status':
            if set(hermes_payload_record)!={'service','job_id'}:raise ValueError('이미지 서비스와 원본 작업 ID가 필요합니다.')
            from workflow.domains.hermes_agent.image_source_operations import read_hermes_image_source_job
            return {'service':hermes_payload_record['service'],'job_id':hermes_payload_record['job_id'],'job':read_hermes_image_source_job(hermes_payload_record['service'],hermes_payload_record['job_id'])}
        if hermes_command_name=='hermes-flux-source-status':
            if set(hermes_payload_record)!={'service','job_id'}:raise ValueError('FLUX 서비스와 원본 작업 ID가 필요합니다.')
            from workflow.domains.hermes_agent.flux_profile_operations import read_hermes_flux_source_job
            return {'service':hermes_payload_record['service'],'job_id':hermes_payload_record['job_id'],'job':read_hermes_flux_source_job(hermes_payload_record['service'],hermes_payload_record['job_id'])}
        if hermes_command_name=='hermes-video-source-status':
            if set(hermes_payload_record)!={'service','job_id'}:raise ValueError('영상 서비스와 원본 작업 ID가 필요합니다.')
            from workflow.domains.hermes_agent.video_operations import read_hermes_video_source_job
            return {'service':hermes_payload_record['service'],'job_id':hermes_payload_record['job_id'],'job':read_hermes_video_source_job(hermes_payload_record['service'],hermes_payload_record['job_id'])}
        if hermes_command_name in ('hermes-minimax-form-prepare', 'hermes-minimax-form-create', 'hermes-minimax-form-list', 'hermes-minimax-form-read', 'hermes-minimax-form-save', 'hermes-minimax-form-update', 'hermes-minimax-form-submit'):
            from workflow.domains.hermes_agent.minimax_form_commands import execute_minimax_form_command
            from workflow.domains.hermes_agent.session_store import HermesSessionStore
            from workflow.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
            from workflow.common.management_gateway import execute_management_command
            import os
            sessions = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
            address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
            return execute_minimax_form_command(hermes_command_name, hermes_payload_record, sessions=sessions,
                read_job=self.read_context_job, dispatch=lambda service, command, request: execute_management_command(service, command, request, address))
        if hermes_command_name == 'hermes-minimax-report-retry':
            from workflow.domains.hermes_agent.minimax_submission import retry_report
            from workflow.domains.hermes_agent.session_store import HermesSessionStore
            sessions = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
            return retry_report(hermes_payload_record, sessions=sessions)
        if hermes_command_name == 'hermes-minimax-report-status':
            from workflow.domains.hermes_agent.minimax_submission import read_report_status
            from workflow.domains.hermes_agent.session_store import HermesSessionStore
            sessions = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
            return read_report_status(hermes_payload_record, sessions=sessions)
        if hermes_command_name == 'hermes-minimax-submit':
            import os as minimax_os
            from workflow.domains.hermes_agent.minimax_submission import submit_from_proposal
            from workflow.domains.hermes_agent.session_store import HermesSessionStore
            from workflow.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
            from workflow.common.management_gateway import execute_management_command
            sessions = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
            address = validate_gateway_address(minimax_os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
            return submit_from_proposal(hermes_payload_record, sessions=sessions, read_job=self.read_context_job,
                                        dispatch=lambda service, command, request: execute_management_command(service, command, request, address))
        if hermes_command_name in ('hermes-delegate-video','hermes-video-status','hermes-video-history','hermes-video-cancel'):
            from workflow.domains.hermes_agent.video_operations import submit_hermes_video_request, read_hermes_video_status, list_hermes_video_receipts, cancel_hermes_video_request
            if hermes_command_name=='hermes-video-history':
                if set(hermes_payload_record)!={'service'}:
                    raise ValueError('동작·영상 서비스만 전달하세요.')
                return list_hermes_video_receipts(hermes_payload_record['service'])
            if hermes_command_name=='hermes-delegate-video':
                if set(hermes_payload_record)!={'request_id','service','request'}:
                    raise ValueError('접수 ID·동작 서비스·요청이 필요합니다.')
                return submit_hermes_video_request(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['request'])
            if hermes_command_name=='hermes-video-status':
                if set(hermes_payload_record)!={'request_id','service'}:
                    raise ValueError('접수 ID와 동작 서비스가 필요합니다.')
                return read_hermes_video_status(hermes_payload_record['request_id'],hermes_payload_record['service'])
            if set(hermes_payload_record)!={'request_id','service','job_id'}:
                raise ValueError('접수 ID·동작 서비스·작업 ID가 필요합니다.')
            return cancel_hermes_video_request(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['job_id'])
        if hermes_command_name=='hermes-cleanup-preview':
            if set(hermes_payload_record)!={'service'}:raise ValueError('정리 미리보기 서비스만 전달하세요.')
            from workflow.domains.hermes_agent.cleanup_preview_observer import read_hermes_cleanup_preview
            return read_hermes_cleanup_preview(hermes_payload_record['service'])
        if hermes_command_name=='hermes-generator-source-history':
            if 'service' not in hermes_payload_record or set(hermes_payload_record)-{'service','offset','limit','snapshot','query'}:
                raise ValueError('생성기 서비스와 이력 페이지 입력을 확인하세요.')
            from workflow.domains.hermes_agent.audio_operations import read_hermes_generator_source_history
            return read_hermes_generator_source_history(hermes_payload_record['service'],{key:value for key,value in hermes_payload_record.items() if key!='service'})
        if hermes_command_name=='hermes-audio-source-status':
            if set(hermes_payload_record)!={'service','job_id'}:
                raise ValueError('오디오 서비스와 원본 작업 ID가 필요합니다.')
            from workflow.domains.hermes_agent.audio_operations import read_hermes_audio_source_job
            return {'service':hermes_payload_record['service'],'job_id':hermes_payload_record['job_id'],'job':read_hermes_audio_source_job(hermes_payload_record['service'],hermes_payload_record['job_id'])}
        if hermes_command_name=='hermes-audio-source-history':
            if 'service' not in hermes_payload_record or set(hermes_payload_record)-{'service','offset','limit','snapshot','query'}:
                raise ValueError('오디오 서비스와 이력 페이지 입력을 확인하세요.')
            from workflow.domains.hermes_agent.audio_operations import read_hermes_audio_source_history
            return read_hermes_audio_source_history(hermes_payload_record['service'],{key:value for key,value in hermes_payload_record.items() if key!='service'})
        if hermes_command_name in ('hermes-delegate-audio','hermes-audio-status','hermes-audio-history','hermes-audio-cancel'):
            from workflow.domains.hermes_agent.audio_operations import submit_hermes_audio_request, read_hermes_audio_status, list_hermes_audio_receipts, cancel_hermes_audio_request
            if hermes_command_name=='hermes-audio-history':
                if set(hermes_payload_record)!={'service'}:
                    raise ValueError('오디오 서비스만 전달하세요.')
                return list_hermes_audio_receipts(hermes_payload_record['service'])
            if hermes_command_name=='hermes-delegate-audio':
                if set(hermes_payload_record)!={'request_id','service','request'}:
                    raise ValueError('접수 ID·오디오 서비스·요청이 필요합니다.')
                return submit_hermes_audio_request(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['request'])
            if hermes_command_name=='hermes-audio-status':
                if set(hermes_payload_record)!={'request_id','service'}:
                    raise ValueError('접수 ID와 오디오 서비스가 필요합니다.')
                return read_hermes_audio_status(hermes_payload_record['request_id'],hermes_payload_record['service'])
            if set(hermes_payload_record)!={'request_id','service','job_id'}:
                raise ValueError('접수 ID·오디오 서비스·작업 ID가 필요합니다.')
            return cancel_hermes_audio_request(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['job_id'])
        if hermes_command_name in ('hermes-delegate-flux-profile','hermes-flux-profile-status','hermes-flux-profile-history','hermes-flux-profile-cancel'):
            from workflow.domains.hermes_agent.flux_profile_operations import submit_hermes_flux_profile, read_hermes_flux_profile_status, list_hermes_flux_profile_receipts, cancel_hermes_flux_profile
            if hermes_command_name=='hermes-flux-profile-history':
                if set(hermes_payload_record)!={'service'}:
                    raise ValueError('생성기 서비스만 전달하세요.')
                return list_hermes_flux_profile_receipts(hermes_payload_record['service'])
            if hermes_command_name=='hermes-delegate-flux-profile':
                base_fields = {'request_id', 'service', 'request'}
                if set(hermes_payload_record) in (base_fields | {'session_id','proposal_job_id'}, base_fields | {'session_id','handoff_id'}):
                    from .flux_reports import validate_origin
                    origin = {k:v for k,v in hermes_payload_record.items() if k not in ('service','request')}
                    validate_origin(origin, hermes_payload_record['service'])
                    if 'proposal_job_id' in origin:
                        from .session_store import HermesSessionStore
                        from .delegation_proposal import parse_hermes_flux_proposal
                        sessions = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
                        session = sessions.read_session_record(origin['session_id'])
                        if sum(m.get('job_id') == origin['proposal_job_id'] for m in session['messages']) != 1:
                            raise ValueError('대화의 FLUX 제안 작업을 확인할 수 없습니다.')
                        proposal_job = self.read_context_job(origin['proposal_job_id'])
                        if (proposal_job['status']['status'] != 'completed' or proposal_job.get('final_response_truncated')
                                or parse_hermes_flux_proposal(proposal_job['final_response']).get('service','flux-image') != hermes_payload_record['service']):
                            raise ValueError('완료된 FLUX 제안과 서비스가 일치하지 않습니다.')
                    return submit_hermes_flux_profile(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['request'],origin=origin)
                if set(hermes_payload_record)!=base_fields:
                    raise ValueError('접수 ID·생성기 서비스·요청이 필요합니다.')
                return submit_hermes_flux_profile(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['request'])
            if hermes_command_name=='hermes-flux-profile-status':
                if set(hermes_payload_record)!={'request_id','service'}:
                    raise ValueError('접수 ID와 생성기 서비스가 필요합니다.')
                return read_hermes_flux_profile_status(hermes_payload_record['request_id'],hermes_payload_record['service'])
            if set(hermes_payload_record)!={'request_id','service','job_id'}:
                raise ValueError('접수 ID·생성기 서비스·작업 ID가 필요합니다.')
            return cancel_hermes_flux_profile(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['job_id'])
        if hermes_command_name in ('hermes-delegate-flux-image', 'hermes-flux-delegation-history', 'hermes-flux-delegation-status', 'hermes-flux-delegation-cancel'):
            from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
            from workflow.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
            from workflow.common.management_gateway import execute_management_command
            import os
            current_delegation_store = HermesDelegationStore()
            if hermes_command_name == 'hermes-flux-delegation-history':
                if hermes_payload_record:
                    raise ValueError('FLUX 위임 이력에는 입력을 전달할 수 없습니다.')
                return current_delegation_store.list_service_delegations('flux-image')
            if hermes_command_name == 'hermes-delegate-flux-image':
                if set(hermes_payload_record) != {'request_id', 'request'} or not isinstance(hermes_payload_record['request'], dict):
                    raise ValueError('위임 접수 ID와 FLUX 요청 객체가 필요합니다.')
                from workflow.domains.image.flux_image_generation import FluxImageGenerationManager
                current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
                from .flux_reports import workflow_origin
                origin = workflow_origin(hermes_payload_record['request_id'])
                return current_delegation_store.execute_service_delegation_once(
                    hermes_payload_record['request_id'], 'flux-image', hermes_payload_record['request'],
                    lambda current_request_record: execute_management_command('flux-image', 'generate', {**current_request_record, '_report_origin':origin} if origin else current_request_record, current_gateway_address),
                    lambda current_request_record: FluxImageGenerationManager('flux-image').validate_generation_request(current_request_record))
            if hermes_command_name == 'hermes-flux-delegation-status':
                if set(hermes_payload_record) != {'request_id'}:
                    raise ValueError('위임 접수 ID만 전달하세요.')
                current_receipt_record = current_delegation_store.read_service_delegation(hermes_payload_record['request_id'], 'flux-image')
                if current_receipt_record.get('state') != 'accepted':
                    return {'receipt': current_receipt_record}
                current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
                current_job_record = execute_management_command('flux-image', 'status', {'id':current_receipt_record['job_id']}, current_gateway_address)
                if not isinstance(current_job_record, dict):
                    raise ValueError('FLUX 작업 상태 응답 형식 오류')
                from workflow.domains.hermes_agent.flux_profile_operations import inspect_hermes_flux_result
                current_result_record=inspect_hermes_flux_result('flux-image',current_receipt_record['job_id'],current_job_record)
                from workflow.domains.hermes_agent.failure_observer import observe_hermes_generator_failure
                current_failure_record=observe_hermes_generator_failure(current_job_record.get('status'),current_job_record.get('error'))
                return {'receipt': current_receipt_record, 'job':{**current_job_record,**current_failure_record}, 'result':current_result_record}
            if set(hermes_payload_record) != {'request_id', 'job_id'}:
                raise ValueError('위임 접수 ID와 확인한 FLUX 작업 ID가 필요합니다.')
            current_receipt_record = current_delegation_store.read_service_delegation(hermes_payload_record['request_id'], 'flux-image')
            if current_receipt_record.get('state') != 'accepted' or current_receipt_record.get('job_id') != hermes_payload_record['job_id']:
                raise ValueError('접수 기록과 확인한 FLUX 작업 ID가 일치하지 않습니다.')
            current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
            current_cancel_record = execute_management_command('flux-image', 'cancel', {'id':current_receipt_record['job_id']}, current_gateway_address)
            if (not isinstance(current_cancel_record, dict) or current_cancel_record.get('cancel_requested') is not True
                    or ('id' in current_cancel_record and current_cancel_record['id'] != current_receipt_record['job_id'])):
                raise ValueError('중지 요청 접수 여부를 확인할 수 없습니다. FLUX 상태를 조회하세요.')
            return {'job_id': current_receipt_record['job_id'], 'cancel_requested':True, 'status':current_cancel_record.get('status', 'unknown')}
        if hermes_command_name == 'hermes-delegate-kimodo':
            if set(hermes_payload_record) != {'request_id', 'request'} or not isinstance(hermes_payload_record['request'], dict):
                raise ValueError('위임 접수 식별자와 Kimodo 요청 객체가 필요합니다.')
            from generators.kimodo.contracts import validate_kimodo_request
            from workflow.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
            from workflow.common.management_gateway import execute_management_command
            from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
            import os
            current_request_value = hermes_payload_record['request']
            current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
            current_delegation_store = HermesDelegationStore()
            return current_delegation_store.execute_delegation_once(
                hermes_payload_record['request_id'], {'service': 'kimodo', 'request': current_request_value},
                lambda current_delegation_record: execute_management_command('kimodo', 'generate', current_delegation_record['request'], current_gateway_address),
                lambda current_delegation_record: validate_kimodo_request(current_delegation_record['request']))
        if hermes_command_name in ('hermes-kimodo-resume-submit','hermes-kimodo-resume-receipt'):
            from workflow.domains.hermes_agent.kimodo_resume_operations import submit_hermes_kimodo_resume_once,read_hermes_kimodo_resume_receipt
            if hermes_command_name=='hermes-kimodo-resume-receipt' and set(hermes_payload_record)=={'request_id'}:return read_hermes_kimodo_resume_receipt(hermes_payload_record['request_id'])
            if hermes_command_name=='hermes-kimodo-resume-submit' and set(hermes_payload_record)=={'request_id','job_id','expected_resume_fingerprint'}:return submit_hermes_kimodo_resume_once(hermes_payload_record['request_id'],hermes_payload_record['job_id'],hermes_payload_record['expected_resume_fingerprint'])
            raise ValueError('Kimodo 재개 입력 필드 오류')
        if hermes_command_name in ('hermes-video-resume-preview','hermes-video-resume-submit','hermes-video-resume-receipt'):
            from workflow.domains.hermes_agent.video_resume_operations import preview_hermes_video_resume, submit_hermes_video_resume_once, read_hermes_video_resume_receipt
            if hermes_command_name=='hermes-video-resume-preview' and set(hermes_payload_record)=={'service','job_id'}:return preview_hermes_video_resume(hermes_payload_record['service'],hermes_payload_record['job_id'])
            if hermes_command_name=='hermes-video-resume-receipt' and set(hermes_payload_record)=={'request_id'}:return read_hermes_video_resume_receipt(hermes_payload_record['request_id'])
            if hermes_command_name=='hermes-video-resume-submit' and set(hermes_payload_record)=={'request_id','service','job_id','expected_resume_fingerprint'}:return submit_hermes_video_resume_once(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['job_id'],hermes_payload_record['expected_resume_fingerprint'])
            raise ValueError('영상 재개 입력 필드 오류')
        if hermes_command_name in ('hermes-flux-resume-submit','hermes-flux-resume-receipt'):
            from workflow.domains.hermes_agent.flux_resume_operations import submit_hermes_flux_resume_once,read_hermes_flux_resume_receipt
            if hermes_command_name=='hermes-flux-resume-receipt' and set(hermes_payload_record)=={'request_id'}:return read_hermes_flux_resume_receipt(hermes_payload_record['request_id'])
            if hermes_command_name=='hermes-flux-resume-submit' and set(hermes_payload_record)=={'request_id','service','job_id','expected_resume_fingerprint'}:return submit_hermes_flux_resume_once(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['job_id'],hermes_payload_record['expected_resume_fingerprint'])
            raise ValueError('FLUX 재개 입력 필드 오류')
        if hermes_command_name=='hermes-flux-resume-preview':
            if set(hermes_payload_record)!={'service','job_id'}:raise ValueError('FLUX 서비스와 작업 ID가 필요합니다.')
            from workflow.domains.hermes_agent.flux_resume_operations import preview_hermes_flux_resume
            return preview_hermes_flux_resume(hermes_payload_record['service'],hermes_payload_record['job_id'])
        if hermes_command_name=='hermes-kimodo-resume-preview':
            if set(hermes_payload_record)!={'job_id'}:raise ValueError('Kimodo 작업 ID만 전달하세요.')
            from workflow.domains.hermes_agent.kimodo_resume_operations import preview_hermes_kimodo_resume
            return preview_hermes_kimodo_resume(hermes_payload_record['job_id'])
        if hermes_command_name in ('hermes-translation-resume-preview','hermes-translation-resume-submit','hermes-translation-resume-receipt'):
            from workflow.domains.hermes_agent.translation_resume_operations import preview_hermes_translation_resume,submit_hermes_translation_resume_once,read_hermes_translation_resume_receipt
            if hermes_command_name=='hermes-translation-resume-preview' and set(hermes_payload_record)=={'job_id'}:
                return preview_hermes_translation_resume(hermes_payload_record['job_id'])
            if hermes_command_name=='hermes-translation-resume-submit' and set(hermes_payload_record)=={'request_id','job_id','expected_resume_fingerprint'}:
                return submit_hermes_translation_resume_once(hermes_payload_record['request_id'],hermes_payload_record['job_id'],hermes_payload_record['expected_resume_fingerprint'])
            if hermes_command_name=='hermes-translation-resume-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_translation_resume_receipt(hermes_payload_record['request_id'])
            raise ValueError('번역 재개 요청 필드 오류')
        if hermes_command_name in ('hermes-audio-resume-preview','hermes-audio-resume-submit','hermes-audio-resume-receipt'):
            from workflow.domains.hermes_agent.audio_resume_operations import preview_hermes_audio_resume, submit_hermes_audio_resume_once, read_hermes_audio_resume_receipt
            if hermes_command_name=='hermes-audio-resume-preview' and set(hermes_payload_record)=={'service','job_id'}:
                return preview_hermes_audio_resume(hermes_payload_record['service'],hermes_payload_record['job_id'])
            if hermes_command_name=='hermes-audio-resume-submit' and set(hermes_payload_record)=={'request_id','service','job_id','expected_resume_fingerprint'}:
                return submit_hermes_audio_resume_once(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['job_id'],hermes_payload_record['expected_resume_fingerprint'])
            if hermes_command_name=='hermes-audio-resume-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_audio_resume_receipt(hermes_payload_record['request_id'])
            raise ValueError('음악 재개 요청 필드 오류')
        if hermes_command_name == 'hermes-priority-receipt':
            if set(hermes_payload_record) != {'request_id'}:raise ValueError('접수 ID만 전달하세요.')
            from workflow.domains.hermes_agent.priority_operations import read_hermes_priority_receipt
            return read_hermes_priority_receipt(hermes_payload_record['request_id'])
        if hermes_command_name == 'hermes-priority-submit':
            if set(hermes_payload_record) != {'request_id','service','id','ticket_revision'}:raise ValueError('접수 ID·서비스·작업 ID·티켓 확인값이 필요합니다.')
            from workflow.domains.hermes_agent.priority_operations import submit_hermes_priority_once
            return submit_hermes_priority_once(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['id'],hermes_payload_record['ticket_revision'])
        if hermes_command_name == 'hermes-priority-preview':
            if set(hermes_payload_record) != {'service','id'}:
                raise ValueError('서비스와 대기 작업 ID가 필요합니다.')
            from workflow.domains.hermes_agent.priority_observer import preview_hermes_queue_priority
            return preview_hermes_queue_priority(hermes_payload_record['service'],hermes_payload_record['id'])
        if hermes_command_name == 'hermes-management-status':
            if hermes_payload_record:
                raise ValueError('관리 상태 조회에는 입력을 전달할 수 없습니다.')
            from workflow.domains.hermes_agent.management_observer import read_hermes_management_snapshot
            return read_hermes_management_snapshot()
        if hermes_command_name in ('hermes-session-archived', 'hermes-session-archive', 'hermes-session-restore', 'hermes-session-delete', 'hermes-session-create', 'hermes-session-read', 'hermes-session-list'):
            from workflow.domains.hermes_agent.session_store import HermesSessionStore, HERMES_SESSION_ID_PATTERN
            hermes_session_store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
            if hermes_command_name == 'hermes-session-archived':
                return hermes_session_store.list_session_records(hermes_payload_record, archived=True)
            if hermes_command_name in ('hermes-session-archive', 'hermes-session-restore', 'hermes-session-delete'):
                if set(hermes_payload_record) != {'session_id', 'expected_update'}:
                    raise ValueError('세션 ID와 조회 시각을 확인하세요.')
                with self.hold_hermes_service_lock():
                    if hermes_command_name == 'hermes-session-archive':
                        self.ensure_context_operation_finished(hermes_session_store.read_session_record(hermes_payload_record['session_id']))
                    return hermes_session_store.change_session_lifecycle(hermes_payload_record['session_id'],
                        hermes_command_name.removeprefix('hermes-session-'), hermes_payload_record['expected_update'])
            if hermes_command_name == 'hermes-session-list':
                return hermes_session_store.list_session_records(hermes_payload_record)
            if set(hermes_payload_record) != {'session_id'}:
                raise ValueError('세션 ID만 전달하세요.')
            if not isinstance(hermes_payload_record['session_id'], str) or not HERMES_SESSION_ID_PATTERN.fullmatch(hermes_payload_record['session_id']):
                raise ValueError('세션 ID 형식 오류')
            if hermes_command_name == 'hermes-session-create':
                return hermes_session_store.create_session_record(hermes_payload_record['session_id'])
            return hermes_session_store.read_session_record(hermes_payload_record['session_id'])
        with self.hold_hermes_service_lock():
            if hermes_command_name=='hermes-video-resume-proposal':
                if set(hermes_payload_record)!={'id'}:raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated') is not False:raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_video_resume_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_video_resume_proposal(current_job_record.get('final_response'))}
            if hermes_command_name=='hermes-flux-resume-proposal':
                if set(hermes_payload_record)!={'id'}:raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated') is not False:raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_flux_resume_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_flux_resume_proposal(current_job_record.get('final_response'))}
            if hermes_command_name=='hermes-kimodo-resume-proposal':
                if set(hermes_payload_record)!={'id'}:raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated') is not False:raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_kimodo_resume_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_kimodo_resume_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-model-preparation-proposal':
                if set(hermes_payload_record)!={'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated') is not False:
                    raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_model_preparation_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_model_preparation_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-writer-proposal':
                if set(hermes_payload_record) != {'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path = self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record = self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status') != 'completed' or current_job_record.get('final_response_truncated'):
                    raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_writer_proposal
                return {'job_id': hermes_payload_record['id'], 'proposal': parse_hermes_writer_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-video-proposal':
                if set(hermes_payload_record) != {'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path = self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record = self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status') != 'completed':
                    raise ValueError('완료된 Hermes 작업에서만 제안을 확인할 수 있습니다.')
                if current_job_record.get('final_response_truncated'):
                    raise ValueError('최종 답변이 잘려 제안을 확인할 수 없습니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_video_proposal
                from workflow.domains.hermes_agent.video_selection import select_video_proposal
                proposal = parse_hermes_video_proposal(current_job_record.get('final_response'))
                proposal = select_video_proposal(proposal, current_job_record['request'])
                return {'job_id':hermes_payload_record['id'],'proposal':proposal}
            if hermes_command_name == 'hermes-audio-proposal':
                if set(hermes_payload_record) != {'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path = self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record = self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status') != 'completed':
                    raise ValueError('완료된 Hermes 작업에서만 제안을 확인할 수 있습니다.')
                if current_job_record.get('final_response_truncated'):
                    raise ValueError('최종 답변이 잘려 제안을 확인할 수 없습니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_audio_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_audio_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-translation-proposal':
                if set(hermes_payload_record) != {'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path = self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record = self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status') != 'completed':
                    raise ValueError('완료된 Hermes 작업에서만 제안을 확인할 수 있습니다.')
                if current_job_record.get('final_response_truncated'):
                    raise ValueError('최종 답변이 잘려 제안을 확인할 수 없습니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_translation_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_translation_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-sprite-proposal':
                if set(hermes_payload_record)!={'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated'):
                    raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_sprite_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_sprite_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-effect-proposal':
                if set(hermes_payload_record)!={'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated'):
                    raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_effect_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_effect_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-billboard-proposal':
                if set(hermes_payload_record) != {'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated'):
                    raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_billboard_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_billboard_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-building-proposal':
                if set(hermes_payload_record)!={'id'}:raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated'):
                    raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_building_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_building_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-city-proposal':
                if set(hermes_payload_record)!={'id'}:raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated'):
                    raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_city_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_city_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-field-proposal':
                if set(hermes_payload_record) != {'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path = self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record = self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status') != 'completed':
                    raise ValueError('완료된 Hermes 작업에서만 제안을 확인할 수 있습니다.')
                if current_job_record.get('final_response_truncated'):
                    raise ValueError('최종 답변이 잘려 제안을 확인할 수 없습니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_field_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_field_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-flux-proposal':
                if set(hermes_payload_record) != {'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path = self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record = self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status') != 'completed':
                    raise ValueError('완료된 Hermes 작업에서만 제안을 확인할 수 있습니다.')
                if current_job_record.get('final_response_truncated'):
                    raise ValueError('최종 답변이 잘려 제안을 확인할 수 없습니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_flux_proposal
                from workflow.domains.hermes_agent.image_selection import select_image_proposal
                proposal = parse_hermes_flux_proposal(current_job_record.get('final_response'))
                return {'job_id':hermes_payload_record['id'], 'proposal':select_image_proposal(proposal, current_job_record['request'])}
            if hermes_command_name == 'hermes-kimodo-proposal':
                if set(hermes_payload_record) != {'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path = self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record = self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status') != 'completed':
                    raise ValueError('완료된 Hermes 작업에서만 제안을 확인할 수 있습니다.')
                if current_job_record.get('final_response_truncated'):
                    raise ValueError('최종 답변이 잘려 제안을 확인할 수 없습니다.')
                from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_kimodo_proposal
                return {'job_id': hermes_payload_record['id'], 'proposal': parse_hermes_kimodo_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-live-instruction-recover':
                from workflow.domains.hermes_agent.session_store import HermesSessionStore
                from workflow.domains.hermes_agent.chat_queue_store import enqueue
                from workflow.domains.hermes_agent.live_instruction_operations import recovery_id
                if set(hermes_payload_record) != {'session_id', 'request_id'}:
                    raise ValueError('복구 요청 형식 오류')
                store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
                record = store.read_session_record(hermes_payload_record['session_id'])
                row = next((item for item in record.get('live_instructions', []) if item.get('request_id') == hermes_payload_record['request_id']), None)
                if not row or row.get('state') != 'undelivered':
                    raise ValueError('미전달이 확인된 지시만 복구할 수 있습니다.')
                return enqueue(store, hermes_payload_record['session_id'], recovery_id(row['request_id']), row['text'])
            if hermes_command_name == 'hermes-live-instruction':
                from workflow.domains.hermes_agent.session_store import HermesSessionStore
                from workflow.domains.hermes_agent.live_instruction_operations import deliver
                store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
                return deliver(self, store, hermes_payload_record)
            if hermes_command_name == 'hermes-session-view':
                result = self.read_hermes_session_view_locked(hermes_payload_record)
                from workflow.domains.hermes_agent.session_store import HermesSessionStore
                store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
                session_record = store.read_session_record(hermes_payload_record['session_id'])
                result['chat_queue'] = [dict(row) for row in session_record.get('chat_queue', []) if row.get('state') in ('queued','dispatching')]
                from workflow.domains.hermes_agent.live_instruction_operations import annotate_recoveries, settle
                result['live_instructions'] = annotate_recoveries(settle(self, store, hermes_payload_record['session_id'], [dict(row) for row in session_record.get('live_instructions', [])][-50:]), session_record)
                result['chat_active'] = None
                for message in reversed(session_record.get('messages', [])):
                    job_id = message.get('job_id')
                    if not job_id:
                        continue
                    try:
                        path = self.resolve_hermes_job_path(job_id) / 'status.json'
                        status = json.loads(path.read_text()) if path.is_file() and not path.is_symlink() else {}
                        state = status.get('status', 'unknown') if isinstance(status, dict) else 'unknown'
                    except (OSError, ValueError, TypeError):
                        state = 'unknown'
                    if state in ('running', 'queued', 'unknown'):
                        control_ready = False
                        try:
                            control_dir = self.resolve_hermes_job_path(job_id) / 'live-control'
                            endpoint = control_dir / 'agent.sock'
                            control_ready = not control_dir.is_symlink() and stat.S_ISSOCK(endpoint.lstat().st_mode)
                        except (OSError, ValueError):
                            pass
                        result['chat_active'] = {'job_id': job_id, 'prompt': message.get('text', ''), 'status': state, 'control_ready': control_ready}
                    break
                return result
            if hermes_command_name == 'hermes-chat-queue-edit':
                from workflow.domains.hermes_agent.session_store import HermesSessionStore
                from workflow.domains.hermes_agent.chat_queue_store import edit
                if set(hermes_payload_record) not in ({'session_id','request_id','revision','action','token'}, {'session_id','request_id','revision','action','token','prompt'}):
                    raise ValueError('대기 요청 편집 형식 오류')
                store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
                result = edit(store, **hermes_payload_record)
                if result.get('edit_token') is None: self.chat_queue_wakeup.set()
                return result
            if hermes_command_name == 'hermes-chat-queue-update':
                from workflow.domains.hermes_agent.session_store import HermesSessionStore
                from workflow.domains.hermes_agent.chat_queue_store import update
                if set(hermes_payload_record) not in ({'session_id','request_id','revision','prompt'}, {'session_id','request_id','revision','cancel'}):
                    raise ValueError('대기 요청 수정 형식 오류')
                store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
                updated_queue_record = update(store, **hermes_payload_record)
                if updated_queue_record.get('state') == 'cancelled' and updated_queue_record.get('require_resident') is True and updated_queue_record.get('queue_order_ns') is not None:
                    from workflow.common import gpu_job_queue
                    from workflow.common.gpu_chat_admission import retire_chat_queue_intent
                    from workflow.domains.hermes_agent.resident_queue import cancel_unused_queued_resident
                    current_session_record = store.read_session_record(hermes_payload_record['session_id'])
                    current_queue_records = current_session_record.get('chat_queue', [])
                    if isinstance(current_queue_records, list) and all(isinstance(chat_queue_record, dict) for chat_queue_record in current_queue_records) and not any(chat_queue_record.get('state') in ('queued', 'dispatching') for chat_queue_record in current_queue_records):
                        for cancelled_queue_record in reversed(current_queue_records[-1000:]):
                            if cancelled_queue_record.get('state') != 'cancelled' or cancelled_queue_record.get('require_resident') is not True or cancelled_queue_record.get('queue_order_ns') is None:
                                continue
                            try:
                                if cancel_unused_queued_resident(hermes_payload_record['session_id'], cancelled_queue_record['request_id'], cancelled_queue_record['queue_order_ns']):
                                    break
                            except (OSError, ValueError, TypeError, KeyError, RuntimeError):
                                # 확인되지 않은 모델은 건드리지 않고 대화 취소만 보존한다.
                                continue
                    retire_chat_queue_intent(gpu_job_queue.GPU_QUEUE_DIRECTORY, hermes_payload_record['session_id'], updated_queue_record['request_id'], updated_queue_record['queue_order_ns'])
                return updated_queue_record
            if hermes_command_name == 'hermes-session-context-settings':
                from workflow.domains.hermes_agent.session_store import HermesSessionStore
                store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
                if set(hermes_payload_record) == {'session_id','enabled'}:
                    return store.set_context_automatic(hermes_payload_record['session_id'], hermes_payload_record['enabled'])
                if set(hermes_payload_record) == {'session_id','threshold'}:
                    return store.set_context_threshold(hermes_payload_record['session_id'], hermes_payload_record['threshold'])
                raise ValueError('세션 ID와 설정 하나만 전달하세요.')
            if hermes_command_name == 'hermes-session-context-compress':
                return self.submit_hermes_session_context_locked(hermes_payload_record)
            if hermes_command_name == 'hermes-submit':
                return self.submit_hermes_job_locked(hermes_payload_record)
            if hermes_command_name == 'hermes-session-withdraw-unsubmitted':
                from workflow.domains.hermes_agent.session_store import HermesSessionStore
                if set(hermes_payload_record) != {'session_id', 'request_id'}:
                    raise ValueError('철회할 세션 ID와 요청 ID가 필요합니다.')
                store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
                return store.withdraw_unsubmitted_request(**hermes_payload_record)
            if hermes_command_name == 'hermes-unified-queue-observe':
                from workflow.domains.hermes_agent.session_store import HermesSessionStore
                from workflow.domains.hermes_agent.unified_queue import observe_unified_queue
                if set(hermes_payload_record) != {'session_id'}:
                    raise ValueError('대화 세션 ID만 전달하세요.')
                store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
                return observe_unified_queue(store, hermes_payload_record['session_id'])
            if hermes_command_name == 'hermes-session-queue-submit':
                from workflow.domains.hermes_agent.session_store import HermesSessionStore
                from workflow.domains.hermes_agent.chat_queue_store import enqueue
                if set(hermes_payload_record) != {'session_id', 'request_id', 'prompt', 'model_profile'} or hermes_payload_record['model_profile'] != COMPLEX_MODEL:
                    raise ValueError('대화 대기 요청 형식 오류')
                store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
                session = store.read_session_record(hermes_payload_record['session_id'])
                existing = next((row for row in session['messages'] if row.get('request_id') == hermes_payload_record['request_id']), None)
                queued_request_exists = any(isinstance(chat_request_record, dict) and chat_request_record.get('request_id') == hermes_payload_record['request_id'] for chat_request_record in session.get('chat_queue', []))
                if existing is not None and not queued_request_exists:
                    if existing.get('text') != hermes_payload_record['prompt'] or existing.get('model_profile') != hermes_payload_record['model_profile']:
                        raise ValueError('같은 접수 식별자를 다른 메시지에 사용할 수 없습니다.')
                    return {'session_id':hermes_payload_record['session_id'], 'request_id':hermes_payload_record['request_id'], 'queued':False, 'duplicate':True}
                receipt = enqueue(store, **hermes_payload_record, require_resident=True)
                queued_request_record = receipt['request']
                if queued_request_record.get('state') == 'cancelled':
                    raise ValueError('취소된 대화 요청입니다. 새 요청으로 접수하세요.')
                if queued_request_record.get('state') == 'dispatched':
                    return {'session_id':hermes_payload_record['session_id'], 'request_id':hermes_payload_record['request_id'], 'queued':False, 'duplicate':True}
                if queued_request_record.get('require_resident') is True and queued_request_record.get('queue_order_ns') is not None:
                    from workflow.common import gpu_job_queue
                    from workflow.common.gpu_chat_admission import register_chat_queue_intent
                    register_chat_queue_intent(gpu_job_queue.GPU_QUEUE_DIRECTORY, hermes_payload_record['session_id'], queued_request_record['request_id'], queued_request_record['queue_order_ns'])
                self.chat_queue_wakeup.set()
                return {'session_id':hermes_payload_record['session_id'], 'request_id':hermes_payload_record['request_id'], 'queued':True, **receipt}
            if hermes_command_name == 'hermes-session-submit':
                from workflow.domains.hermes_agent.session_store import HermesSessionStore
                from workflow.domains.hermes_agent.chat_queue_store import enqueue
                from workflow.domains.hermes_agent.context_checkpoint import build_context_messages
                if 'model_profile' in hermes_payload_record:
                    if hermes_payload_record['model_profile'] != COMPLEX_MODEL:
                        raise ValueError('폐기된 대화 모델입니다. Qwen 3.8을 사용하세요.')
                if {'session_id','request_id','prompt'} <= set(hermes_payload_record) and not set(hermes_payload_record) - {'session_id','request_id','prompt','model_profile'}:
                    store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
                    session = store.read_session_record(hermes_payload_record['session_id'])
                    duplicate = any(row.get('request_id') == hermes_payload_record['request_id'] for row in session.get('chat_queue', []))
                    if duplicate:
                        return {'session_id':hermes_payload_record['session_id'], 'queued':True, **enqueue(store, hermes_payload_record['session_id'], hermes_payload_record['request_id'], hermes_payload_record['prompt'], hermes_payload_record.get('model_profile'))}
                    existing = next ( (row for row in session['messages'] if row.get('request_id') == hermes_payload_record['request_id']), None)
                    if existing is not None:
                        return self.submit_hermes_session_message_locked(hermes_payload_record)
                    queued = any(row.get('state') in ('queued','dispatching') for row in session.get('chat_queue', []))
                    # 상주 모델이 없거나 상태가 불명확해도 요청은 안전한 대기열에 보존한다.
                    # 실제 모델 적재는 대기열 실행기가 별도로 상태와 GPU 예약을 검증한다.
                    from workflow.domains.hermes_agent.resident_queue import find_session_resident
                    try:
                        resident_id = find_session_resident(hermes_payload_record['session_id'])
                    except (OSError, ValueError):
                        resident_id = None
                    if resident_id is None:
                        receipt = enqueue(store, hermes_payload_record['session_id'], hermes_payload_record['request_id'], hermes_payload_record['prompt'], hermes_payload_record.get('model_profile'), require_resident=True)
                        row = receipt['request']
                        if row.get('state') in ('queued', 'dispatching') and row.get('queue_order_ns') is not None:
                            from workflow.common import gpu_job_queue
                            from workflow.common.gpu_chat_admission import register_chat_queue_intent
                            register_chat_queue_intent(gpu_job_queue.GPU_QUEUE_DIRECTORY, hermes_payload_record['session_id'], row['request_id'], row['queue_order_ns'])
                        self.chat_queue_wakeup.set()
                        return {'session_id':hermes_payload_record['session_id'], 'queued':True, **receipt}
                    try:
                        self.ensure_context_operation_finished(session)
                        build_context_messages(session, self.read_context_job)
                    except ValueError as error:
                        if str(error) not in ('이전 작업이 종료된 후 다시 시도하세요.','대화 정리가 종료된 후 다시 시도하세요.','대화 정리의 접수 상태를 먼저 확인하세요.'):
                            raise
                        queued = True
                    if queued:
                        return {'session_id':hermes_payload_record['session_id'], 'queued':True, **enqueue(store, hermes_payload_record['session_id'], hermes_payload_record['request_id'], hermes_payload_record['prompt'], hermes_payload_record.get('model_profile'))}
                return self.submit_hermes_session_message_locked(hermes_payload_record)
            if hermes_command_name == 'hermes-history':
                if set(hermes_payload_record)-{'offset','limit','snapshot','query','status'}:
                    raise ValueError('이력 조회 필드 오류')
                current_history_paths = self.list_hermes_job_paths()
                if not hermes_payload_record:
                    current_selected_paths = current_history_paths[:100]
                else:
                    current_history_offset = hermes_payload_record.get('offset',0)
                    current_history_limit = hermes_payload_record.get('limit',30)
                    current_history_snapshot = hermes_payload_record.get('snapshot')
                    if type(current_history_offset) is not int or current_history_offset<0 or type(current_history_limit) is not int or not 1<=current_history_limit<=30:
                        raise ValueError('이력 페이지 범위 오류')
                    from workflow.domains.hermes_agent.history_catalog import HERMES_HISTORY_STATUS_LABELS, normalize_hermes_history_status
                    current_history_query=hermes_payload_record.get('query','')
                    current_history_status=hermes_payload_record.get('status','전체')
                    if not isinstance(current_history_query,str) or len(current_history_query)>100 or any(ord(char)<32 for char in current_history_query) or current_history_status not in ('전체',*HERMES_HISTORY_STATUS_LABELS):
                        raise ValueError('이력 검색 조건 오류')
                    current_history_query=current_history_query.strip().casefold()
                    if current_history_query or current_history_status!='전체':
                        current_matching_paths=[]
                        for current_job_path in current_history_paths:
                            if current_history_status!='전체':
                                current_status_path=current_job_path/'status.json'
                                if current_status_path.is_symlink():raise ValueError('상태 경로 오류')
                                if current_status_path.exists():
                                    if not current_status_path.is_file() or current_status_path.stat().st_size>1048576:raise ValueError('상태 기록 오류')
                                    current_status_record=json.loads(current_status_path.read_text(encoding='utf-8'))
                                    if not isinstance(current_status_record,dict):raise ValueError('상태 기록 오류')
                                    current_status_value=normalize_hermes_history_status(current_status_record.get('status'))
                                else:current_status_value='unknown'
                                if current_status_value!=current_history_status:continue
                            if current_history_query:
                                current_request_path=current_job_path/'request.json'
                                if current_request_path.is_symlink() or not current_request_path.is_file() or current_request_path.stat().st_size>1048576:raise ValueError('지시 기록 오류')
                                current_request_record=json.loads(current_request_path.read_text(encoding='utf-8'))
                                if not isinstance(current_request_record,dict) or not isinstance(current_request_record.get('prompt'),str):raise ValueError('지시 기록 오류')
                                if current_history_query not in (current_job_path.name+' '+current_request_record['prompt']).casefold():continue
                            current_matching_paths.append(current_job_path)
                        if HERMES_JOB_PATTERN.fullmatch(current_history_query):
                            current_matching_paths.sort(key=lambda current_job_path:current_job_path.name!=current_history_query)
                        current_history_paths=current_matching_paths
                    current_history_digest = hashlib.sha256(json.dumps({'ids':[item.name for item in current_history_paths],'query':current_history_query,'status':current_history_status},ensure_ascii=True,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
                    if (current_history_offset>0 and current_history_snapshot!=current_history_digest) or ('snapshot' in hermes_payload_record and current_history_snapshot!=current_history_digest):
                        raise ValueError('작업 이력 목록이 변경됐습니다. 처음부터 다시 조회하세요.')
                    current_selected_paths = current_history_paths[current_history_offset:current_history_offset+current_history_limit]
                hermes_history_records = []
                for hermes_job_path in current_selected_paths:
                    hermes_job_record = self.read_hermes_job_record(hermes_job_path)
                    hermes_history_records.append({hermes_field_name: hermes_job_record[hermes_field_name] for hermes_field_name in ('id', 'request', 'status', 'result')})
                if not hermes_payload_record:
                    return {'records':hermes_history_records}
                current_next_offset=current_history_offset+len(hermes_history_records)
                return {'records':hermes_history_records,'offset':current_history_offset,'next_offset':current_next_offset if current_next_offset<len(current_history_paths) else None,'total':len(current_history_paths),'snapshot':current_history_digest}
            if hermes_command_name == 'hermes-diff':
                if set(hermes_payload_record) != {'id', 'offset', 'limit'}:
                    raise ValueError('작업 ID와 diff 시작 위치·크기를 전달하세요.')
                hermes_chunk_offset = hermes_payload_record['offset']
                hermes_chunk_limit = hermes_payload_record['limit']
                if type(hermes_chunk_offset) is not int or hermes_chunk_offset < 0 or type(hermes_chunk_limit) is not int or not 1 <= hermes_chunk_limit <= 262144:
                    raise ValueError('diff 시작 위치는 0 이상, 크기는 1~262144바이트여야 합니다.')
                hermes_job_path = self.resolve_hermes_job_path(hermes_payload_record['id'])
                hermes_status_path = hermes_job_path / 'status.json'
                if not hermes_status_path.is_file() or json.loads(hermes_status_path.read_text()).get('status') not in ('completed', 'failed', 'cancelled'):
                    raise ValueError('작업이 종료된 뒤 전체 diff를 조회할 수 있습니다.')
                hermes_diff_path = hermes_job_path / 'change.diff'
                if hermes_diff_path.is_symlink() or not hermes_diff_path.is_file():
                    raise ValueError('아직 저장된 diff가 없습니다.')
                with hermes_diff_path.open('rb') as hermes_diff_stream:
                    hermes_diff_stream.seek(0, 2)
                    hermes_total_bytes = hermes_diff_stream.tell()
                    if hermes_chunk_offset > hermes_total_bytes:
                        raise ValueError('diff 시작 위치가 파일 크기를 넘습니다.')
                    hermes_diff_stream.seek(hermes_chunk_offset)
                    hermes_chunk_bytes = hermes_diff_stream.read(hermes_chunk_limit)
                hermes_next_offset = hermes_chunk_offset + len(hermes_chunk_bytes)
                return {'id':hermes_job_path.name, 'offset':hermes_chunk_offset, 'size_bytes':hermes_total_bytes, 'data_base64':base64.b64encode(hermes_chunk_bytes).decode('ascii'), 'next_offset':hermes_next_offset if hermes_next_offset < hermes_total_bytes else None}
            if set(hermes_payload_record) != {'id'}:
                raise ValueError('작업 ID만 전달하세요.')
            hermes_job_path = self.resolve_hermes_job_path(hermes_payload_record['id'])
            if hermes_command_name == 'hermes-detail':
                return self.read_hermes_job_record(hermes_job_path)
            if hermes_command_name == 'hermes-cancel':
                current_cancel_response=cancel_gpu_generation(hermes_job_path)
                return {**current_cancel_response,'id':hermes_job_path.name}
            raise ValueError('지원하지 않는 Hermes 명령입니다.')

    def handle_hermes_request(self, hermes_http_handler):
        from workflow.common.management_gateway import identify_management_command
        try:
            validate_management_http_request(hermes_http_handler)
            hermes_command_match = identify_management_command(hermes_http_handler.path, hermes_http_handler.command, getattr(hermes_http_handler, 'management_command_payload', {}))
            if not hermes_command_match or hermes_command_match[0] != 'hermes-agent':
                raise ValueError('지원하지 않는 Hermes 요청입니다.')
            hermes_response_record = self.execute_hermes_command(hermes_command_match[1], hermes_command_match[2])
            send_management_json_response(hermes_http_handler, 200, hermes_response_record)
        except (OSError, ValueError, KeyError, TypeError) as hermes_request_error:
            send_management_json_response(hermes_http_handler, 400, {'error':str(hermes_request_error)})
        return True
