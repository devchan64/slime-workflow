"""Hermes 작업 접수·취소·결과를 공용 관리 명령과 GPU 대기열에 연결한다."""
from contextlib import contextmanager
import base64
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import shutil
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
        with self.hermes_thread_lock, (self.hermes_storage_root / '.service.lock').open('a') as hermes_lock_stream:
            fcntl.flock(hermes_lock_stream, fcntl.LOCK_EX)
            yield

    def resolve_hermes_job_path(self, hermes_job_identifier):
        if not isinstance(hermes_job_identifier, str) or not HERMES_JOB_PATTERN.fullmatch(hermes_job_identifier):
            raise ValueError('Hermes 작업 ID 형식 오류')
        hermes_job_path = self.hermes_storage_root / hermes_job_identifier
        if hermes_job_path.is_symlink() or not hermes_job_path.is_dir():
            raise ValueError('Hermes 작업을 찾을 수 없습니다.')
        return hermes_job_path

    def list_hermes_job_paths(self):
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
        if set(hermes_payload_record) != {'session_id'}:
            raise ValueError('세션 ID만 전달하세요.')
        from tools.review.domains.hermes_agent.session_store import HermesSessionStore
        hermes_session_store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
        hermes_session_record = hermes_session_store.read_session_record(hermes_payload_record['session_id'])
        hermes_view_messages = []
        for current_message_record in hermes_session_record['messages'][-20:]:
            current_view_record = {'text': current_message_record['text'], 'job_id': current_message_record.get('job_id'), 'context_truncated': current_message_record.get('context_truncated', False), 'job': None}
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
        return {'id': hermes_session_record['id'], 'message_count': len(hermes_session_record['messages']), 'messages': hermes_view_messages, 'truncated': len(hermes_session_record['messages']) > 20, 'queried_at': datetime.now(timezone.utc).isoformat()}

    def execute_hermes_command(self, hermes_command_name, hermes_payload_record):
        if not isinstance(hermes_payload_record, dict):
            raise ValueError('입력은 객체여야 합니다.')
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
            current_receipt_record = HermesDelegationStore().read_delegation_status(hermes_payload_record['request_id'])
            if current_receipt_record.get('state') != 'accepted':
                return {'receipt': current_receipt_record}
            current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
            current_job_status = execute_management_command('kimodo', 'status', {'id': current_receipt_record['job_id']}, current_gateway_address)
            if not isinstance(current_job_status, dict):
                raise ValueError('Kimodo 작업 상태 응답 형식 오류')
            return {'receipt': current_receipt_record, 'job': current_job_status}
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
            if not isinstance(current_cancel_result, dict) or current_cancel_result.get('cancel_requested') is not True:
                raise ValueError('중지 요청 접수 여부를 확인할 수 없습니다. Kimodo 상태를 조회하세요.')
            return {'job_id': current_receipt_record['job_id'], 'cancel_requested': True, 'status': current_cancel_result.get('status', 'unknown')}
        if hermes_command_name == 'hermes-delegation-status':
            if set(hermes_payload_record) != {'request_id'}:
                raise ValueError('위임 접수 ID만 전달하세요.')
            from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
            return HermesDelegationStore().read_delegation_status(hermes_payload_record['request_id'])
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
        if hermes_command_name == 'hermes-management-status':
            if hermes_payload_record:
                raise ValueError('관리 상태 조회에는 입력을 전달할 수 없습니다.')
            from tools.review.domains.hermes_agent.management_observer import read_hermes_management_snapshot
            return read_hermes_management_snapshot()
        if hermes_command_name in ('hermes-session-create', 'hermes-session-read', 'hermes-session-list'):
            from tools.review.domains.hermes_agent.session_store import HermesSessionStore, HERMES_SESSION_ID_PATTERN
            hermes_session_store = HermesSessionStore(self.hermes_session_root) if self.hermes_session_root is not None else HermesSessionStore()
            if hermes_command_name == 'hermes-session-list':
                if hermes_payload_record:
                    raise ValueError('세션 목록 조회에는 입력을 전달할 수 없습니다.')
                return hermes_session_store.list_session_records()
            if set(hermes_payload_record) != {'session_id'}:
                raise ValueError('세션 ID만 전달하세요.')
            if not isinstance(hermes_payload_record['session_id'], str) or not HERMES_SESSION_ID_PATTERN.fullmatch(hermes_payload_record['session_id']):
                raise ValueError('세션 ID 형식 오류')
            if hermes_command_name == 'hermes-session-create':
                return hermes_session_store.create_session_record(hermes_payload_record['session_id'])
            return hermes_session_store.read_session_record(hermes_payload_record['session_id'])
        with self.hold_hermes_service_lock():
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
                if hermes_payload_record:
                    raise ValueError('이력 조회는 입력을 받지 않습니다.')
                hermes_history_records = []
                for hermes_job_path in self.list_hermes_job_paths()[:100]:
                    hermes_job_record = self.read_hermes_job_record(hermes_job_path)
                    hermes_history_records.append({hermes_field_name: hermes_job_record[hermes_field_name] for hermes_field_name in ('id', 'request', 'status', 'result')})
                return {'records':hermes_history_records}
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
                return cancel_gpu_generation(hermes_job_path)
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
