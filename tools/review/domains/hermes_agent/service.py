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
import shutil
import stat
import subprocess
import sys
import threading
import uuid
from zoneinfo import ZoneInfo

from tools.review.common.generation_records import write_record_atomically
from tools.review.common.gpu_job_queue import launch_gpu_process, cancel_gpu_generation
from tools.review.common.management_transport import validate_management_http_request, send_management_json_response
from tools.review.common.hermes_model_download import inspect_hermes_model_files
from tools.review.domains.hermes_agent.runtime_integrity import verify_hermes_runtime_integrity
from tools.review.domains.hermes_agent.verification import validate_hermes_verification_modules

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
HERMES_JOB_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.tmp/test/hermes-agent/jobs'
HERMES_JOB_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}')
HERMES_JOB_OBSERVATION_MAXIMUM_ENTRIES = 5000
HERMES_REQUEST_PATTERN = re.compile(r'[A-Za-z0-9_-]{8,80}')


def validate_hermes_runtime_ready():
    if not inspect_hermes_model_files():
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
        else:
            current_error_flag = current_event_record.get('is_error')
            current_output_value = current_event_record.get('output')
            try:
                current_parsed_output = json.loads(current_output_value) if isinstance(current_output_value, str) else None
            except ValueError:
                current_parsed_output = None
            current_exit_value = current_parsed_output.get('exit_code') if isinstance(current_parsed_output, dict) else None
            if type(current_exit_value) is int:
                current_event_value['result'] = 'success' if current_exit_value == 0 and current_error_flag is not True else 'error'
            elif current_error_flag is True:
                current_event_value['result'] = 'error'
            else:
                current_event_value['result'] = 'recorded'
        current_tool_events.append(current_event_value)
    return {'events': current_tool_events[-8:], 'truncated': current_file_size > 128000 or len(current_tool_events) > 8}



class HermesServiceManager:
    def __init__(self, hermes_storage_root=HERMES_JOB_DIRECTORY, hermes_session_root=None):
        self.hermes_storage_root = Path(hermes_storage_root)
        self.hermes_session_root = hermes_session_root
        self.hermes_thread_lock = threading.RLock()

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

    def submit_hermes_job_locked(self, hermes_payload_record):
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
                return {'id':hermes_previous_path.name, 'duplicate':True}
        validate_hermes_runtime_ready()
        hermes_job_identifier = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S') + '-' + uuid.uuid4().hex[:8]
        hermes_job_path = self.hermes_storage_root / hermes_job_identifier
        hermes_job_path.mkdir()
        write_record_atomically(hermes_job_path / 'request.json', hermes_payload_record)
        with (hermes_job_path / 'worker.log').open('a') as hermes_log_stream:
            launch_gpu_process([sys.executable, str(WORKFLOW_ROOT_DIRECTORY / 'tools/review/domains/hermes_agent/worker.py'), str(hermes_job_path)], hermes_job_path, 'hermes-agent', stdout=hermes_log_stream, stderr=subprocess.STDOUT, start_new_session=True, cwd=WORKFLOW_ROOT_DIRECTORY)
        return {'id':hermes_job_identifier, 'status':'queued', 'duplicate':False}

    def submit_hermes_session_message_locked(self, hermes_payload_record):
        from tools.review.domains.hermes_agent.session_store import HermesSessionStore, HERMES_SESSION_ID_PATTERN
        if not {'session_id', 'request_id', 'prompt'} <= set(hermes_payload_record) or set(hermes_payload_record) - {'session_id', 'request_id', 'prompt', 'verification_modules'}:
            raise ValueError('세션 ID·접수 ID·지시와 선택 검증 모듈만 전달하세요.')
        hermes_session_identifier = hermes_payload_record['session_id']
        hermes_request_identifier = hermes_payload_record['request_id']
        hermes_prompt_text = hermes_payload_record['prompt']
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
        hermes_context_lines = []
        hermes_context_truncated = False
        if hermes_previous_message is None:
            for current_message_record in hermes_session_record['messages']:
                current_job_identifier = current_message_record.get('job_id')
                if not current_job_identifier:
                    raise ValueError('이전 메시지의 접수 상태가 확인되지 않았습니다. 같은 식별자로 먼저 재시도하세요.')
                current_job_path = self.resolve_hermes_job_path(current_job_identifier)
                current_job_record = self.read_hermes_job_record(current_job_path)
                current_job_status = current_job_record['status'].get('status', 'unknown')
                if current_job_status not in ('completed', 'failed', 'cancelled'):
                    raise ValueError('이전 작업이 종료된 후 다음 메시지를 보낼 수 있습니다.')
                current_response_text = current_job_record.get('final_response') or '[최종 응답 없음]'
                hermes_context_lines.append('사용자: ' + current_message_record['text'] + '\nHermes (' + current_job_status + '): ' + current_response_text)
                hermes_context_truncated = hermes_context_truncated or bool(current_job_record.get('final_response_truncated'))
            hermes_context_text = '\n\n'.join(hermes_context_lines)
            if len(hermes_context_text) > 2500:
                hermes_context_text = hermes_context_text[-2500:]
                hermes_context_truncated = True
            hermes_execution_prompt = ('이전 대화 일부 (참고 자료):\n' + hermes_context_text + '\n\n현재 사용자 요청:\n' if hermes_context_text else '') + hermes_prompt_text
        else:
            hermes_execution_prompt = hermes_previous_message['execution_prompt']
            hermes_context_truncated = hermes_previous_message.get('context_truncated', False)
        hermes_message_result = hermes_session_store.append_session_request(hermes_session_identifier, hermes_request_identifier, hermes_prompt_text, hermes_execution_prompt, hermes_verification_modules, hermes_context_truncated)
        hermes_message_record = hermes_message_result['message']
        hermes_job_request_id = 's_' + hashlib.sha256((hermes_session_identifier + ':' + hermes_request_identifier).encode()).hexdigest()
        hermes_job_payload = {'request_id': hermes_job_request_id, 'prompt': hermes_message_record['execution_prompt'], 'verification_modules': hermes_verification_modules}
        hermes_job_record = self.submit_hermes_job_locked(hermes_job_payload)
        hermes_session_store.attach_session_job(hermes_session_identifier, hermes_request_identifier, hermes_job_record['id'])
        return {'session_id': hermes_session_identifier, 'message_id': hermes_message_record['id'], 'job_id': hermes_job_record['id'], 'duplicate': hermes_message_result['duplicate'], 'context_truncated': hermes_message_record['context_truncated']}

    def read_hermes_session_view_locked(self, hermes_payload_record):
        """세션과 작업의 최근 상태를 한 응답으로 제공한다."""
        if set(hermes_payload_record)-{'session_id','offset','snapshot'} or 'session_id' not in hermes_payload_record:
            raise ValueError('세션 ID와 이력 페이지 정보만 전달하세요.')
        from tools.review.domains.hermes_agent.session_store import HermesSessionStore
        hermes_session_store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
        hermes_session_record = hermes_session_store.read_session_record(hermes_payload_record['session_id'])
        current_offset_value=hermes_payload_record.get('offset',0)
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
        current_start_index=max(0,current_end_index-20)
        hermes_view_messages = []
        for current_message_record in hermes_session_record['messages'][current_start_index:current_end_index]:
            current_view_record = {'text': current_message_record['text'], 'created_at':current_message_record.get('created_at'), 'job_id': current_message_record.get('job_id'), 'session_job_unique':current_session_job_counts[current_message_record['job_id']]==1 if isinstance(current_message_record.get('job_id'),str) else None, 'context_truncated': current_message_record.get('context_truncated', False), 'job': None}
            if current_view_record['job_id']:
                try:
                    current_job_path = self.resolve_hermes_job_path(current_view_record['job_id'])
                    current_status_path = current_job_path / 'status.json'
                    current_status_record = json.loads(current_status_path.read_text()) if current_status_path.is_file() and not current_status_path.is_symlink() else {'status':'unknown'}
                    if not isinstance(current_status_record, dict):
                        raise ValueError('작업 상태 형식 오류')
                    current_final_answer, current_answer_truncated = read_hermes_final_response(current_job_path)
                    current_view_record['job'] = {'status': current_status_record, 'final_response': current_final_answer, 'final_response_truncated': current_answer_truncated, 'tool_activity': read_hermes_tool_activity(current_job_path)}
                except (OSError, ValueError, TypeError, KeyError):
                    current_view_record['job'] = {'status': {'status':'unavailable', 'message':'작업 상태를 읽을 수 없습니다.'}, 'final_response': None, 'final_response_truncated': False}
            hermes_view_messages.append(current_view_record)
        return {'id': hermes_session_record['id'], 'message_count': len(hermes_session_record['messages']), 'messages': hermes_view_messages, 'truncated': current_start_index > 0, 'offset':current_offset_value, 'next_offset':current_offset_value+len(hermes_view_messages) if current_start_index>0 else None, 'snapshot':current_snapshot_value, 'queried_at': datetime.now(timezone.utc).isoformat()}

    def execute_hermes_command(self, hermes_command_name, hermes_payload_record):
        if not isinstance(hermes_payload_record, dict):
            raise ValueError('입력은 객체여야 합니다.')
        if hermes_command_name in ("hermes-workflow-list", "hermes-workflow-catalog", "hermes-workflow-register", "hermes-workflow-view", 'hermes-workflow-cancel'):
            from .workflow_commands import execute_workflow_command
            return execute_workflow_command(WORKFLOW_ROOT_DIRECTORY, hermes_command_name, hermes_payload_record)
        if hermes_command_name=='hermes-anchor-history-observe':
            from tools.review.domains.hermes_agent.anchor_history_observer import read_hermes_anchor_history
            return read_hermes_anchor_history(hermes_payload_record)
        if hermes_command_name=='hermes-expression-catalog':
            from tools.review.domains.hermes_agent.expression_observer import read_hermes_expression_catalog
            return read_hermes_expression_catalog(hermes_payload_record)
        if hermes_command_name == 'hermes-capture-proposal':
            if set(hermes_payload_record) != {'id'}:
                raise ValueError('Hermes 작업 ID만 전달하세요.')
            current_job_path = self.resolve_hermes_job_path(hermes_payload_record['id'])
            current_job_record = self.read_hermes_job_record(current_job_path)
            if current_job_record['status'].get('status') != 'completed' or current_job_record.get('final_response_truncated'):
                raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
            from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_capture_proposal
            from tools.review.domains.hermes_agent.capture_delegation import inspect_capture_map_registration
            current_capture_proposal=parse_hermes_capture_proposal(current_job_record.get('final_response'))
            return {'job_id':hermes_payload_record['id'],'proposal':current_capture_proposal,'map_registration':inspect_capture_map_registration(current_capture_proposal)}
        if hermes_command_name == 'hermes-capture-status':
            if set(hermes_payload_record) != {'request_id','service'}:
                raise ValueError('캡처 접수 ID와 서비스가 필요합니다.')
            from tools.review.domains.hermes_agent.capture_status import read_capture_delegation_status
            from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
            return read_capture_delegation_status(HermesDelegationStore(),hermes_payload_record['request_id'],hermes_payload_record['service'],WORKFLOW_ROOT_DIRECTORY)
        if hermes_command_name=='hermes-service-receipt':
            if set(hermes_payload_record)!={'request_id','service'}:
                raise ValueError('접수 ID와 서비스가 필요합니다.')
            from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore, list_hermes_service_receipt_names
            if hermes_payload_record['service'] not in list_hermes_service_receipt_names():
                raise ValueError('지원하는 접수 서비스가 아닙니다.')
            current_receipt_record=HermesDelegationStore().read_service_delegation(hermes_payload_record['request_id'],hermes_payload_record['service'])
            return {**current_receipt_record,'request_id':hermes_payload_record['request_id']}
        if hermes_command_name == 'hermes-kimodo-build-status':
            if hermes_payload_record:
                raise ValueError('빌드 상태 조회에는 입력을 전달할 수 없습니다.')
            from tools.review.domains.hermes_agent.management_observer import read_hermes_kimodo_build_status
            return read_hermes_kimodo_build_status()
        if hermes_command_name == 'hermes-service-registration':
            from tools.review.domains.hermes_agent.capabilities import list_management_service_registration, search_management_service_registration
            return search_management_service_registration(hermes_payload_record) if hermes_payload_record else list_management_service_registration()
        if hermes_command_name=='hermes-sprite-clip-playback':
            if set(hermes_payload_record)!={'draft','token','review_sha256','clip'}:
                raise ValueError('검토한 초안·토큰·검수 해시·클립 ID가 필요합니다.')
            from tools.review.domains.hermes_agent.sprite_operations import render_hermes_sprite_clip_playback
            return render_hermes_sprite_clip_playback(hermes_payload_record['draft'],hermes_payload_record['token'],hermes_payload_record['review_sha256'],hermes_payload_record['clip'])
        if hermes_command_name=='hermes-sprite-playback':
            if set(hermes_payload_record)!={'draft','token','review_sha256','fps'}:
                raise ValueError('검토한 초안·토큰·검수 해시·FPS가 필요합니다.')
            from tools.review.domains.hermes_agent.sprite_operations import render_hermes_sprite_anchor_playback
            return render_hermes_sprite_anchor_playback(hermes_payload_record['draft'],hermes_payload_record['token'],hermes_payload_record['review_sha256'],hermes_payload_record['fps'])
        if hermes_command_name == 'hermes-sprite-pending-status':
            if hermes_payload_record:raise ValueError('스프라이트 저장 상태 조회에는 입력을 전달할 수 없습니다.')
            from tools.review.domains.hermes_agent.sprite_pending_observer import inspect_hermes_sprite_pending_status
            return inspect_hermes_sprite_pending_status()
        if hermes_command_name in ('hermes-sprite-preview','hermes-sprite-save','hermes-sprite-receipt'):
            from tools.review.domains.hermes_agent.sprite_operations import preview_hermes_sprite_anchor_edit, save_hermes_sprite_anchor_once, read_hermes_sprite_anchor_receipt
            if hermes_command_name=='hermes-sprite-preview' and set(hermes_payload_record)=={'draft'}:
                return preview_hermes_sprite_anchor_edit(hermes_payload_record['draft'])
            if hermes_command_name=='hermes-sprite-save' and set(hermes_payload_record)=={'request_id','draft','token','review_sha256'}:
                return save_hermes_sprite_anchor_once(hermes_payload_record['request_id'],hermes_payload_record['draft'],hermes_payload_record['token'],hermes_payload_record['review_sha256'])
            if hermes_command_name=='hermes-sprite-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_sprite_anchor_receipt(hermes_payload_record['request_id'])
            raise ValueError('스프라이트 편집 요청 필드 오류')
        if hermes_command_name in ('hermes-sprite-catalog','hermes-sprite-detail'):
            from tools.review.domains.hermes_agent.sprite_observer import read_hermes_sprite_catalog, read_hermes_sprite_sheet
            return (read_hermes_sprite_catalog if hermes_command_name=='hermes-sprite-catalog' else read_hermes_sprite_sheet)(hermes_payload_record)
        if hermes_command_name=='hermes-kimodo-keyframe-validate':
            from tools.review.domains.hermes_agent.keyframe_observer import validate_hermes_kimodo_keyframe_batch
            return validate_hermes_kimodo_keyframe_batch(hermes_payload_record)
        if hermes_command_name=='hermes-kimodo-source-frame':
            if set(hermes_payload_record)!={'job_id','attempt_id','frame'}:raise ValueError('Kimodo 작업·시도·프레임이 필요합니다.')
            from tools.review.domains.hermes_agent.kimodo_frame_observer import inspect_kimodo_source_frame
            return inspect_kimodo_source_frame(hermes_payload_record['job_id'],hermes_payload_record['attempt_id'],hermes_payload_record['frame'])
        if hermes_command_name=='hermes-kimodo-keyframe-preview':
            from tools.review.domains.hermes_agent.keyframe_observer import read_hermes_kimodo_keyframe_preview
            if set(hermes_payload_record)!={'keyframe_id'}:
                raise ValueError('키프레임 ID만 전달하세요.')
            return read_hermes_kimodo_keyframe_preview(hermes_payload_record['keyframe_id'])
        if hermes_command_name=='hermes-kimodo-keyframes':
            from tools.review.domains.hermes_agent.keyframe_observer import read_hermes_kimodo_keyframe_catalog
            return read_hermes_kimodo_keyframe_catalog(hermes_payload_record)
        if hermes_command_name in ('hermes-effect-register-preview','hermes-effect-register','hermes-effect-register-receipt'):
            from tools.review.domains.hermes_agent.effect_operations import preview_hermes_effect_registration, register_hermes_effect_once, read_hermes_effect_registration_receipt
            if hermes_command_name=='hermes-effect-register-preview' and set(hermes_payload_record)=={'draft'}:
                return preview_hermes_effect_registration(hermes_payload_record['draft'])
            if hermes_command_name=='hermes-effect-register' and set(hermes_payload_record)=={'request_id','draft','review_sha256'}:
                return register_hermes_effect_once(hermes_payload_record['request_id'],hermes_payload_record['draft'],hermes_payload_record['review_sha256'])
            if hermes_command_name=='hermes-effect-register-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_effect_registration_receipt(hermes_payload_record['request_id'])
            raise ValueError('이펙트 등록 입력 필드 오류')
        if hermes_command_name in ('hermes-waypoint-preview','hermes-waypoint-replace','hermes-waypoint-receipt'):
            from tools.review.domains.hermes_agent.effect_operations import preview_hermes_waypoint_replacement, replace_hermes_waypoint_once, read_hermes_waypoint_replacement_receipt
            if hermes_command_name=='hermes-waypoint-preview' and set(hermes_payload_record)=={'draft'}:
                return preview_hermes_waypoint_replacement(hermes_payload_record['draft'])
            if hermes_command_name=='hermes-waypoint-replace' and set(hermes_payload_record)=={'request_id','draft','review_sha256'}:
                return replace_hermes_waypoint_once(hermes_payload_record['request_id'],hermes_payload_record['draft'],hermes_payload_record['review_sha256'])
            if hermes_command_name=='hermes-waypoint-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_waypoint_replacement_receipt(hermes_payload_record['request_id'])
            raise ValueError('웨이포인트 교체 입력 필드 오류')
        if hermes_command_name in ('hermes-effect-preview','hermes-effect-save','hermes-effect-receipt'):
            from tools.review.domains.hermes_agent.effect_operations import preview_hermes_effect_edit, save_hermes_effect_edit_once, read_hermes_effect_edit_receipt
            if hermes_command_name=='hermes-effect-preview' and set(hermes_payload_record)=={'draft'}:
                return preview_hermes_effect_edit(hermes_payload_record['draft'])
            if hermes_command_name=='hermes-effect-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_effect_edit_receipt(hermes_payload_record['request_id'])
            if hermes_command_name=='hermes-effect-save' and set(hermes_payload_record)=={'request_id','draft','token'}:
                return save_hermes_effect_edit_once(hermes_payload_record['request_id'],hermes_payload_record['draft'],hermes_payload_record['token'])
            raise ValueError('이펙트 편집 입력 필드 오류')
        if hermes_command_name in ('hermes-effect-catalog','hermes-effect-detail'):
            from tools.review.domains.hermes_agent.effect_observer import list_hermes_effect_catalog, read_hermes_effect_detail
            if hermes_command_name=='hermes-effect-catalog':
                return list_hermes_effect_catalog(hermes_payload_record)
            if set(hermes_payload_record)!={'id'}:
                raise ValueError('이펙트 ID만 전달하세요.')
            return read_hermes_effect_detail(hermes_payload_record['id'])
        if hermes_command_name in ('hermes-kimodo-keyframe-source-review','hermes-kimodo-keyframe-save','hermes-kimodo-keyframe-receipt'):
            from tools.review.domains.hermes_agent.kimodo_keyframe_operations import preview_hermes_keyframe_source, save_hermes_keyframe_once, read_hermes_keyframe_receipt
            if hermes_command_name=='hermes-kimodo-keyframe-source-review' and set(hermes_payload_record)=={'job_id','attempt_id','frame','tag'}:
                return preview_hermes_keyframe_source(hermes_payload_record['job_id'],hermes_payload_record['attempt_id'],hermes_payload_record['frame'],hermes_payload_record['tag'])
            if hermes_command_name=='hermes-kimodo-keyframe-save' and set(hermes_payload_record)=={'request_id','job_id','attempt_id','frame','tag','review_sha256'}:
                return save_hermes_keyframe_once(hermes_payload_record['request_id'],{current_key_name:hermes_payload_record[current_key_name] for current_key_name in ('job_id','attempt_id','frame','tag','review_sha256')})
            if hermes_command_name=='hermes-kimodo-keyframe-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_keyframe_receipt(hermes_payload_record['request_id'])
            raise ValueError('Kimodo 키프레임 요청 필드 오류')
        if hermes_command_name in ('hermes-billboard-load','hermes-billboard-preview','hermes-billboard-save','hermes-billboard-receipt'):
            from tools.review.domains.hermes_agent.billboard_operations import load_hermes_billboard_edit, preview_hermes_billboard_edit, save_hermes_billboard_edit_once, read_hermes_billboard_edit_receipt
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
            from tools.review.domains.hermes_agent.city_map_operations import read_hermes_city_source
            return read_hermes_city_source(hermes_payload_record['map'])
        if hermes_command_name in ('hermes-city-load','hermes-city-preview','hermes-city-save','hermes-city-receipt','hermes-city-history'):
            from tools.review.domains.hermes_agent.city_map_operations import load_hermes_city_map, preview_hermes_city_map, save_hermes_city_map_once, read_hermes_city_receipt, list_hermes_city_receipts
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
            from tools.review.domains.hermes_agent.field_map_operations import read_hermes_field_region
            return read_hermes_field_region(hermes_payload_record)
        if hermes_command_name in ('hermes-field-receipt','hermes-field-history'):
            from tools.review.domains.hermes_agent.field_map_operations import read_hermes_field_receipt, list_hermes_field_receipts
            if hermes_command_name == 'hermes-field-history':
                if hermes_payload_record:
                    raise ValueError('맵 저장 이력에는 입력을 전달할 수 없습니다.')
                return list_hermes_field_receipts()
            if set(hermes_payload_record) != {'request_id'}:
                raise ValueError('접수 ID만 전달하세요.')
            return read_hermes_field_receipt(hermes_payload_record['request_id'])
        if hermes_command_name in ('hermes-field-load','hermes-field-preview','hermes-field-save'):
            from tools.review.domains.hermes_agent.field_map_operations import load_hermes_field_map, preview_hermes_field_map, save_hermes_field_map_once
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
            from tools.review.domains.hermes_agent.asset_observer import read_hermes_world_map_catalog
            return read_hermes_world_map_catalog(hermes_payload_record.get('map'))
        if hermes_command_name in ('hermes-building-preview','hermes-building-save','hermes-building-receipt'):
            from tools.review.domains.hermes_agent.building_operations import preview_hermes_building_anchor, save_hermes_building_anchor, read_hermes_building_receipt
            if hermes_command_name=='hermes-building-preview' and set(hermes_payload_record)=={'draft'}:
                return preview_hermes_building_anchor(hermes_payload_record['draft'])
            if hermes_command_name=='hermes-building-save' and set(hermes_payload_record)=={'request_id','draft','review_sha256'}:
                return save_hermes_building_anchor(hermes_payload_record['request_id'],hermes_payload_record['draft'],hermes_payload_record['review_sha256'])
            if hermes_command_name=='hermes-building-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_building_receipt(hermes_payload_record['request_id'])
            raise ValueError('건물 앵커 위임 입력 오류')
        if hermes_command_name == 'hermes-building-catalog':
            from tools.review.domains.hermes_agent.asset_observer import read_hermes_building_catalog
            return read_hermes_building_catalog(hermes_payload_record)
        if hermes_command_name == 'hermes-billboard-catalog':
            from tools.review.domains.hermes_agent.asset_observer import read_hermes_billboard_catalog
            return read_hermes_billboard_catalog(hermes_payload_record)
        if hermes_command_name == 'hermes-model-prepare-history':
            if hermes_payload_record:
                raise ValueError('모델 준비 이력에는 입력을 전달할 수 없습니다.')
            from tools.review.domains.hermes_agent.model_preparation_store import HermesModelPreparationStore
            return HermesModelPreparationStore().list_model_preparation_receipts()
        if hermes_command_name in ('hermes-model-prepare', 'hermes-model-prepare-status'):
            if set(hermes_payload_record) != {'request_id', 'service'}:
                raise ValueError('모델 서비스와 접수 ID만 전달하세요.')
            from tools.review.domains.hermes_agent.model_preparation_store import HermesModelPreparationStore
            current_model_store = HermesModelPreparationStore()
            current_service_name = hermes_payload_record['service']
            current_request_identifier = hermes_payload_record['request_id']
            if hermes_command_name == 'hermes-model-prepare-status':
                return current_model_store.read_model_preparation_receipt(current_request_identifier, current_service_name)
            import os
            from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
            from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, inspect_registered_model_operation, execute_management_command
            current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
            class ModelPreparationPreflightBlocked(ValueError):
                pass
            def validate_current_model_service(model_service_name):
                current_operation_name = inspect_registered_model_operation(model_service_name, MANAGEMENT_SERVICE_COMMANDS.get(model_service_name, ()), 'prepare')
                if current_operation_name is None:
                    raise ValueError('이 모델의 준비는 기존 관리 정책에서 제한됩니다.')
                if model_service_name == 'hermes-model':
                    from tools.review.common.hermes_model_download import inspect_hermes_model_files
                    from tools.review.common.model_prepare_process import inspect_registered_preparation_strict, hold_hermes_model_usage_guard, HermesModelUsageBusy
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
            from tools.review.domains.hermes_agent.management_observer import read_hermes_model_readiness
            return read_hermes_model_readiness(hermes_payload_record['service'])
        if hermes_command_name == 'hermes-map-database-receipt':
            if set(hermes_payload_record)!={'database_request_id','request_sha256'}:
                raise ValueError('DB 맵 변경 요청 ID와 원본 요청 해시가 필요합니다.')
            from tools.review.domains.map_assets.database_client import read_content_map_receipt_by_hash
            return read_content_map_receipt_by_hash(hermes_payload_record['database_request_id'],hermes_payload_record['request_sha256'])
        if hermes_command_name == 'hermes-content-database-status':
            if hermes_payload_record:
                raise ValueError('콘텐츠 DB 상태 조회에는 입력을 전달할 수 없습니다.')
            from tools.review.domains.hermes_agent.management_observer import read_hermes_content_database_status
            return read_hermes_content_database_status()
        if hermes_command_name == 'hermes-model-download-status':
            if hermes_payload_record:raise ValueError('모델 다운로드 상태 조회에는 입력을 전달할 수 없습니다.')
            from tools.review.domains.hermes_agent.management_observer import read_hermes_model_download_status
            return read_hermes_model_download_status()
        if hermes_command_name == 'hermes-model-inventory':
            if hermes_payload_record:
                raise ValueError('모델 보유량 조회에는 입력을 전달할 수 없습니다.')
            from tools.review.domains.hermes_agent.management_observer import read_hermes_model_inventory
            return read_hermes_model_inventory()
        if hermes_command_name == 'hermes-capabilities':
            if hermes_payload_record:
                raise ValueError('관리 기능 목록에는 입력을 전달할 수 없습니다.')
            from tools.review.domains.hermes_agent.capabilities import list_hermes_capability_catalog
            return list_hermes_capability_catalog()
        if hermes_command_name == 'hermes-delegation-history':
            if hermes_payload_record:
                raise ValueError('위임 접수 이력에는 입력을 전달할 수 없습니다.')
            from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
            return HermesDelegationStore().list_delegation_receipts()
        if hermes_command_name == 'hermes-delegation-job-status':
            if set(hermes_payload_record) != {'request_id'}:
                raise ValueError('위임 접수 ID만 전달하세요.')
            from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
            from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
            from tools.review.common.management_gateway import execute_management_command
            import os
            current_receipt_record = {**HermesDelegationStore().read_delegation_status(hermes_payload_record['request_id']),'request_id':hermes_payload_record['request_id'],'service':'kimodo'}
            if current_receipt_record.get('state') != 'accepted':
                return {'receipt': current_receipt_record}
            current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
            current_job_status = execute_management_command('kimodo', 'status', {'id': current_receipt_record['job_id']}, current_gateway_address)
            if not isinstance(current_job_status, dict) or ('id' in current_job_status and current_job_status['id'] != current_receipt_record['job_id']):
                raise ValueError('Kimodo 작업 상태 응답 또는 작업 ID 오류')
            from tools.review.domains.hermes_agent.failure_observer import observe_hermes_generator_failure
            current_failure_record=observe_hermes_generator_failure(current_job_status.get('status'),current_job_status.get('error'))
            return {'receipt': current_receipt_record, 'job': {**current_job_status,**current_failure_record}}
        if hermes_command_name == 'hermes-delegation-cancel':
            if set(hermes_payload_record) != {'request_id', 'job_id'}:
                raise ValueError('위임 접수 ID와 확인한 작업 ID가 필요합니다.')
            from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
            from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
            from tools.review.common.management_gateway import execute_management_command
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
            from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
            return {**HermesDelegationStore().read_delegation_status(hermes_payload_record['request_id']),'request_id':hermes_payload_record['request_id'],'service':'kimodo'}
        if hermes_command_name in ('hermes-writer-apply','hermes-writer-apply-status','hermes-writer-apply-history'):
            from tools.review.domains.hermes_agent.writer_operations import apply_hermes_writer_proposal_once, read_writer_apply_receipt, list_writer_apply_receipts
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
            from tools.review.domains.hermes_agent.writer_reservation import recover_writer_reservation_once, read_writer_recovery_receipt
            if hermes_command_name=='hermes-writer-reservation-recover' and set(hermes_payload_record)=={'request_id','job_id','review_sha256','outside_processes_checked'}:
                return recover_writer_reservation_once(hermes_payload_record['request_id'],hermes_payload_record['job_id'],hermes_payload_record['review_sha256'],hermes_payload_record['outside_processes_checked'])
            if hermes_command_name=='hermes-writer-reservation-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_writer_recovery_receipt(hermes_payload_record['request_id'])
            raise ValueError('작가 예약 정리 입력 필드 오류')
        if hermes_command_name in ('hermes-generator-reservation-recover','hermes-generator-reservation-receipt'):
            from tools.review.domains.hermes_agent.generator_reservation_recovery import recover_generator_reservation_once, read_generator_recovery_receipt
            if hermes_command_name=='hermes-generator-reservation-recover' and set(hermes_payload_record)=={'request_id','service','job_id','review_sha256','outside_processes_checked'}:
                return recover_generator_reservation_once(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['job_id'],hermes_payload_record['review_sha256'],hermes_payload_record['outside_processes_checked'])
            if hermes_command_name=='hermes-generator-reservation-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_generator_recovery_receipt(hermes_payload_record['request_id'])
            raise ValueError('생성기 예약 정리 입력 필드 오류')
        if hermes_command_name=='hermes-generator-reservation-inspect':
            if set(hermes_payload_record)!={'service','job_id'}:raise ValueError('서비스와 작업 ID가 필요합니다.')
            from tools.review.domains.hermes_agent.reservation_observer import inspect_generator_reservation_identity
            return inspect_generator_reservation_identity(hermes_payload_record['service'],hermes_payload_record['job_id'])
        if hermes_command_name=='hermes-writer-reservation-preview':
            if set(hermes_payload_record)!={'job_id'}:raise ValueError('작가 작업 ID가 필요합니다.')
            from tools.review.domains.hermes_agent.writer_reservation import preview_writer_reservation_recovery
            return preview_writer_reservation_recovery(hermes_payload_record['job_id'])
        if hermes_command_name=='hermes-writer-cancel':
            if set(hermes_payload_record)!={'request_id','job_id'}:raise ValueError('작가 접수 ID와 확인한 작업 ID가 필요합니다.')
            from tools.review.domains.hermes_agent.writer_operations import cancel_hermes_writer_request
            return cancel_hermes_writer_request(hermes_payload_record['request_id'],hermes_payload_record['job_id'])
        if hermes_command_name == 'hermes-writer-search-paths':
            if set(hermes_payload_record) != {'request_id'}:raise ValueError('작가 위임 접수 ID만 전달하세요.')
            from tools.review.domains.hermes_agent.writer_operations import read_hermes_writer_search_paths
            return read_hermes_writer_search_paths(hermes_payload_record['request_id'])
        if hermes_command_name == 'hermes-writer-job-material':
            from tools.review.domains.hermes_agent.writer_operations import read_writer_job_material_page
            return read_writer_job_material_page(hermes_payload_record)
        if hermes_command_name == 'hermes-writer-job-review':
            if set(hermes_payload_record) != {'job_id'}:raise ValueError('작가 작업 ID만 전달하세요.')
            from tools.review.domains.hermes_agent.writer_operations import read_writer_job_review
            return {'job_id':hermes_payload_record['job_id'],'job':read_writer_job_review(hermes_payload_record['job_id'])}
        if hermes_command_name == 'hermes-writer-job-search-paths':
            if set(hermes_payload_record) != {'job_id'}:raise ValueError('작가 작업 ID만 전달하세요.')
            from tools.review.domains.hermes_agent.writer_operations import read_writer_job_search_paths
            return read_writer_job_search_paths(hermes_payload_record['job_id'])
        if hermes_command_name == 'hermes-writer-index-status':
            from tools.review.domains.hermes_agent.writer_operations import read_hermes_writer_index_status
            if hermes_payload_record:
                raise ValueError('작가 색인 상태 조회에는 입력을 전달할 수 없습니다.')
            return read_hermes_writer_index_status()
        if hermes_command_name in ('hermes-delegate-writer','hermes-writer-status','hermes-writer-history'):
            from tools.review.domains.hermes_agent.writer_operations import submit_hermes_writer_request, read_hermes_writer_status
            from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
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
            from tools.review.domains.hermes_agent.translation_operations import search_hermes_translation_evidence
            if set(hermes_payload_record)!={'text'}:
                raise ValueError('번역 근거 검색에는 원문이 필요합니다.')
            return search_hermes_translation_evidence(hermes_payload_record['text'])
        if hermes_command_name in ('hermes-delegate-translation','hermes-translation-status','hermes-translation-history','hermes-translation-cancel'):
            from tools.review.domains.hermes_agent.translation_operations import submit_hermes_translation_request, read_hermes_translation_status, cancel_hermes_translation_request
            from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
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
            from tools.review.domains.hermes_agent.character_source_operations import read_character_source_job
            return {'service':'character-animation','job_id':hermes_payload_record['job_id'],'job':read_character_source_job(hermes_payload_record['job_id'])}
        if hermes_command_name=='hermes-image-source-status':
            if set(hermes_payload_record)!={'service','job_id'}:raise ValueError('이미지 서비스와 원본 작업 ID가 필요합니다.')
            from tools.review.domains.hermes_agent.image_source_operations import read_hermes_image_source_job
            return {'service':hermes_payload_record['service'],'job_id':hermes_payload_record['job_id'],'job':read_hermes_image_source_job(hermes_payload_record['service'],hermes_payload_record['job_id'])}
        if hermes_command_name=='hermes-flux-source-status':
            if set(hermes_payload_record)!={'service','job_id'}:raise ValueError('FLUX 서비스와 원본 작업 ID가 필요합니다.')
            from tools.review.domains.hermes_agent.flux_profile_operations import read_hermes_flux_source_job
            return {'service':hermes_payload_record['service'],'job_id':hermes_payload_record['job_id'],'job':read_hermes_flux_source_job(hermes_payload_record['service'],hermes_payload_record['job_id'])}
        if hermes_command_name=='hermes-video-source-status':
            if set(hermes_payload_record)!={'service','job_id'}:raise ValueError('영상 서비스와 원본 작업 ID가 필요합니다.')
            from tools.review.domains.hermes_agent.video_operations import read_hermes_video_source_job
            return {'service':hermes_payload_record['service'],'job_id':hermes_payload_record['job_id'],'job':read_hermes_video_source_job(hermes_payload_record['service'],hermes_payload_record['job_id'])}
        if hermes_command_name in ('hermes-delegate-video','hermes-video-status','hermes-video-history','hermes-video-cancel'):
            from tools.review.domains.hermes_agent.video_operations import submit_hermes_video_request, read_hermes_video_status, list_hermes_video_receipts, cancel_hermes_video_request
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
            from tools.review.domains.hermes_agent.cleanup_preview_observer import read_hermes_cleanup_preview
            return read_hermes_cleanup_preview(hermes_payload_record['service'])
        if hermes_command_name=='hermes-generator-source-history':
            if 'service' not in hermes_payload_record or set(hermes_payload_record)-{'service','offset','limit','snapshot','query'}:
                raise ValueError('생성기 서비스와 이력 페이지 입력을 확인하세요.')
            from tools.review.domains.hermes_agent.audio_operations import read_hermes_generator_source_history
            return read_hermes_generator_source_history(hermes_payload_record['service'],{key:value for key,value in hermes_payload_record.items() if key!='service'})
        if hermes_command_name=='hermes-audio-source-status':
            if set(hermes_payload_record)!={'service','job_id'}:
                raise ValueError('오디오 서비스와 원본 작업 ID가 필요합니다.')
            from tools.review.domains.hermes_agent.audio_operations import read_hermes_audio_source_job
            return {'service':hermes_payload_record['service'],'job_id':hermes_payload_record['job_id'],'job':read_hermes_audio_source_job(hermes_payload_record['service'],hermes_payload_record['job_id'])}
        if hermes_command_name=='hermes-audio-source-history':
            if 'service' not in hermes_payload_record or set(hermes_payload_record)-{'service','offset','limit','snapshot','query'}:
                raise ValueError('오디오 서비스와 이력 페이지 입력을 확인하세요.')
            from tools.review.domains.hermes_agent.audio_operations import read_hermes_audio_source_history
            return read_hermes_audio_source_history(hermes_payload_record['service'],{key:value for key,value in hermes_payload_record.items() if key!='service'})
        if hermes_command_name in ('hermes-delegate-audio','hermes-audio-status','hermes-audio-history','hermes-audio-cancel'):
            from tools.review.domains.hermes_agent.audio_operations import submit_hermes_audio_request, read_hermes_audio_status, list_hermes_audio_receipts, cancel_hermes_audio_request
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
            from tools.review.domains.hermes_agent.flux_profile_operations import submit_hermes_flux_profile, read_hermes_flux_profile_status, list_hermes_flux_profile_receipts, cancel_hermes_flux_profile
            if hermes_command_name=='hermes-flux-profile-history':
                if set(hermes_payload_record)!={'service'}:
                    raise ValueError('생성기 서비스만 전달하세요.')
                return list_hermes_flux_profile_receipts(hermes_payload_record['service'])
            if hermes_command_name=='hermes-delegate-flux-profile':
                if set(hermes_payload_record)!={'request_id','service','request'}:
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
            from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
            from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
            from tools.review.common.management_gateway import execute_management_command
            import os
            current_delegation_store = HermesDelegationStore()
            if hermes_command_name == 'hermes-flux-delegation-history':
                if hermes_payload_record:
                    raise ValueError('FLUX 위임 이력에는 입력을 전달할 수 없습니다.')
                return current_delegation_store.list_service_delegations('flux-image')
            if hermes_command_name == 'hermes-delegate-flux-image':
                if set(hermes_payload_record) != {'request_id', 'request'} or not isinstance(hermes_payload_record['request'], dict):
                    raise ValueError('위임 접수 ID와 FLUX 요청 객체가 필요합니다.')
                from tools.review.domains.image.flux_image_generation import FluxImageGenerationManager
                current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
                return current_delegation_store.execute_service_delegation_once(
                    hermes_payload_record['request_id'], 'flux-image', hermes_payload_record['request'],
                    lambda current_request_record: execute_management_command('flux-image', 'generate', current_request_record, current_gateway_address),
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
                from tools.review.domains.hermes_agent.flux_profile_operations import inspect_hermes_flux_result
                current_result_record=inspect_hermes_flux_result('flux-image',current_receipt_record['job_id'],current_job_record)
                from tools.review.domains.hermes_agent.failure_observer import observe_hermes_generator_failure
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
            from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
            from tools.review.common.management_gateway import execute_management_command
            from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
            import os
            current_request_value = hermes_payload_record['request']
            current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
            current_delegation_store = HermesDelegationStore()
            return current_delegation_store.execute_delegation_once(
                hermes_payload_record['request_id'], {'service': 'kimodo', 'request': current_request_value},
                lambda current_delegation_record: execute_management_command('kimodo', 'generate', current_delegation_record['request'], current_gateway_address),
                lambda current_delegation_record: validate_kimodo_request(current_delegation_record['request']))
        if hermes_command_name in ('hermes-kimodo-resume-submit','hermes-kimodo-resume-receipt'):
            from tools.review.domains.hermes_agent.kimodo_resume_operations import submit_hermes_kimodo_resume_once,read_hermes_kimodo_resume_receipt
            if hermes_command_name=='hermes-kimodo-resume-receipt' and set(hermes_payload_record)=={'request_id'}:return read_hermes_kimodo_resume_receipt(hermes_payload_record['request_id'])
            if hermes_command_name=='hermes-kimodo-resume-submit' and set(hermes_payload_record)=={'request_id','job_id','expected_resume_fingerprint'}:return submit_hermes_kimodo_resume_once(hermes_payload_record['request_id'],hermes_payload_record['job_id'],hermes_payload_record['expected_resume_fingerprint'])
            raise ValueError('Kimodo 재개 입력 필드 오류')
        if hermes_command_name in ('hermes-video-resume-preview','hermes-video-resume-submit','hermes-video-resume-receipt'):
            from tools.review.domains.hermes_agent.video_resume_operations import preview_hermes_video_resume, submit_hermes_video_resume_once, read_hermes_video_resume_receipt
            if hermes_command_name=='hermes-video-resume-preview' and set(hermes_payload_record)=={'service','job_id'}:return preview_hermes_video_resume(hermes_payload_record['service'],hermes_payload_record['job_id'])
            if hermes_command_name=='hermes-video-resume-receipt' and set(hermes_payload_record)=={'request_id'}:return read_hermes_video_resume_receipt(hermes_payload_record['request_id'])
            if hermes_command_name=='hermes-video-resume-submit' and set(hermes_payload_record)=={'request_id','service','job_id','expected_resume_fingerprint'}:return submit_hermes_video_resume_once(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['job_id'],hermes_payload_record['expected_resume_fingerprint'])
            raise ValueError('영상 재개 입력 필드 오류')
        if hermes_command_name in ('hermes-flux-resume-submit','hermes-flux-resume-receipt'):
            from tools.review.domains.hermes_agent.flux_resume_operations import submit_hermes_flux_resume_once,read_hermes_flux_resume_receipt
            if hermes_command_name=='hermes-flux-resume-receipt' and set(hermes_payload_record)=={'request_id'}:return read_hermes_flux_resume_receipt(hermes_payload_record['request_id'])
            if hermes_command_name=='hermes-flux-resume-submit' and set(hermes_payload_record)=={'request_id','service','job_id','expected_resume_fingerprint'}:return submit_hermes_flux_resume_once(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['job_id'],hermes_payload_record['expected_resume_fingerprint'])
            raise ValueError('FLUX 재개 입력 필드 오류')
        if hermes_command_name=='hermes-flux-resume-preview':
            if set(hermes_payload_record)!={'service','job_id'}:raise ValueError('FLUX 서비스와 작업 ID가 필요합니다.')
            from tools.review.domains.hermes_agent.flux_resume_operations import preview_hermes_flux_resume
            return preview_hermes_flux_resume(hermes_payload_record['service'],hermes_payload_record['job_id'])
        if hermes_command_name=='hermes-kimodo-resume-preview':
            if set(hermes_payload_record)!={'job_id'}:raise ValueError('Kimodo 작업 ID만 전달하세요.')
            from tools.review.domains.hermes_agent.kimodo_resume_operations import preview_hermes_kimodo_resume
            return preview_hermes_kimodo_resume(hermes_payload_record['job_id'])
        if hermes_command_name in ('hermes-translation-resume-preview','hermes-translation-resume-submit','hermes-translation-resume-receipt'):
            from tools.review.domains.hermes_agent.translation_resume_operations import preview_hermes_translation_resume,submit_hermes_translation_resume_once,read_hermes_translation_resume_receipt
            if hermes_command_name=='hermes-translation-resume-preview' and set(hermes_payload_record)=={'job_id'}:
                return preview_hermes_translation_resume(hermes_payload_record['job_id'])
            if hermes_command_name=='hermes-translation-resume-submit' and set(hermes_payload_record)=={'request_id','job_id','expected_resume_fingerprint'}:
                return submit_hermes_translation_resume_once(hermes_payload_record['request_id'],hermes_payload_record['job_id'],hermes_payload_record['expected_resume_fingerprint'])
            if hermes_command_name=='hermes-translation-resume-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_translation_resume_receipt(hermes_payload_record['request_id'])
            raise ValueError('번역 재개 요청 필드 오류')
        if hermes_command_name in ('hermes-audio-resume-preview','hermes-audio-resume-submit','hermes-audio-resume-receipt'):
            from tools.review.domains.hermes_agent.audio_resume_operations import preview_hermes_audio_resume, submit_hermes_audio_resume_once, read_hermes_audio_resume_receipt
            if hermes_command_name=='hermes-audio-resume-preview' and set(hermes_payload_record)=={'service','job_id'}:
                return preview_hermes_audio_resume(hermes_payload_record['service'],hermes_payload_record['job_id'])
            if hermes_command_name=='hermes-audio-resume-submit' and set(hermes_payload_record)=={'request_id','service','job_id','expected_resume_fingerprint'}:
                return submit_hermes_audio_resume_once(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['job_id'],hermes_payload_record['expected_resume_fingerprint'])
            if hermes_command_name=='hermes-audio-resume-receipt' and set(hermes_payload_record)=={'request_id'}:
                return read_hermes_audio_resume_receipt(hermes_payload_record['request_id'])
            raise ValueError('음악 재개 요청 필드 오류')
        if hermes_command_name == 'hermes-priority-receipt':
            if set(hermes_payload_record) != {'request_id'}:raise ValueError('접수 ID만 전달하세요.')
            from tools.review.domains.hermes_agent.priority_operations import read_hermes_priority_receipt
            return read_hermes_priority_receipt(hermes_payload_record['request_id'])
        if hermes_command_name == 'hermes-priority-submit':
            if set(hermes_payload_record) != {'request_id','service','id','ticket_revision'}:raise ValueError('접수 ID·서비스·작업 ID·티켓 확인값이 필요합니다.')
            from tools.review.domains.hermes_agent.priority_operations import submit_hermes_priority_once
            return submit_hermes_priority_once(hermes_payload_record['request_id'],hermes_payload_record['service'],hermes_payload_record['id'],hermes_payload_record['ticket_revision'])
        if hermes_command_name == 'hermes-priority-preview':
            if set(hermes_payload_record) != {'service','id'}:
                raise ValueError('서비스와 대기 작업 ID가 필요합니다.')
            from tools.review.domains.hermes_agent.priority_observer import preview_hermes_queue_priority
            return preview_hermes_queue_priority(hermes_payload_record['service'],hermes_payload_record['id'])
        if hermes_command_name == 'hermes-management-status':
            if hermes_payload_record:
                raise ValueError('관리 상태 조회에는 입력을 전달할 수 없습니다.')
            from tools.review.domains.hermes_agent.management_observer import read_hermes_management_snapshot
            return read_hermes_management_snapshot()
        if hermes_command_name in ('hermes-session-create', 'hermes-session-read', 'hermes-session-list'):
            from tools.review.domains.hermes_agent.session_store import HermesSessionStore, HERMES_SESSION_ID_PATTERN
            hermes_session_store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
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
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_video_resume_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_video_resume_proposal(current_job_record.get('final_response'))}
            if hermes_command_name=='hermes-flux-resume-proposal':
                if set(hermes_payload_record)!={'id'}:raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated') is not False:raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_flux_resume_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_flux_resume_proposal(current_job_record.get('final_response'))}
            if hermes_command_name=='hermes-kimodo-resume-proposal':
                if set(hermes_payload_record)!={'id'}:raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated') is not False:raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_kimodo_resume_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_kimodo_resume_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-model-preparation-proposal':
                if set(hermes_payload_record)!={'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated') is not False:
                    raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_model_preparation_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_model_preparation_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-writer-proposal':
                if set(hermes_payload_record) != {'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path = self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record = self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status') != 'completed' or current_job_record.get('final_response_truncated'):
                    raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_writer_proposal
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
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_video_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_video_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-audio-proposal':
                if set(hermes_payload_record) != {'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path = self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record = self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status') != 'completed':
                    raise ValueError('완료된 Hermes 작업에서만 제안을 확인할 수 있습니다.')
                if current_job_record.get('final_response_truncated'):
                    raise ValueError('최종 답변이 잘려 제안을 확인할 수 없습니다.')
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_audio_proposal
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
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_translation_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_translation_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-sprite-proposal':
                if set(hermes_payload_record)!={'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated'):
                    raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_sprite_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_sprite_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-effect-proposal':
                if set(hermes_payload_record)!={'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated'):
                    raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_effect_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_effect_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-billboard-proposal':
                if set(hermes_payload_record) != {'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated'):
                    raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_billboard_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_billboard_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-building-proposal':
                if set(hermes_payload_record)!={'id'}:raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated'):
                    raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_building_proposal
                return {'job_id':hermes_payload_record['id'],'proposal':parse_hermes_building_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-city-proposal':
                if set(hermes_payload_record)!={'id'}:raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path=self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record=self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status')!='completed' or current_job_record.get('final_response_truncated'):
                    raise ValueError('완료되고 잘리지 않은 Hermes 답변이 필요합니다.')
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_city_proposal
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
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_field_proposal
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
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_flux_proposal
                return {'job_id':hermes_payload_record['id'], 'proposal':parse_hermes_flux_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-kimodo-proposal':
                if set(hermes_payload_record) != {'id'}:
                    raise ValueError('Hermes 작업 ID만 전달하세요.')
                current_job_path = self.resolve_hermes_job_path(hermes_payload_record['id'])
                current_job_record = self.read_hermes_job_record(current_job_path)
                if current_job_record['status'].get('status') != 'completed':
                    raise ValueError('완료된 Hermes 작업에서만 제안을 확인할 수 있습니다.')
                if current_job_record.get('final_response_truncated'):
                    raise ValueError('최종 답변이 잘려 제안을 확인할 수 없습니다.')
                from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_kimodo_proposal
                return {'job_id': hermes_payload_record['id'], 'proposal': parse_hermes_kimodo_proposal(current_job_record.get('final_response'))}
            if hermes_command_name == 'hermes-session-view':
                return self.read_hermes_session_view_locked(hermes_payload_record)
            if hermes_command_name == 'hermes-submit':
                return self.submit_hermes_job_locked(hermes_payload_record)
            if hermes_command_name == 'hermes-session-submit':
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
                    from tools.review.domains.hermes_agent.history_catalog import HERMES_HISTORY_STATUS_LABELS, normalize_hermes_history_status
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
        from tools.review.common.management_gateway import identify_management_command
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
