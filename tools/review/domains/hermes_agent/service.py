"""Hermes 작업 접수·취소·결과를 공용 관리 명령과 GPU 대기열에 연결한다."""
from contextlib import contextmanager
import base64
from datetime import datetime
import fcntl
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


class HermesServiceManager:
    def __init__(self, hermes_storage_root=HERMES_JOB_DIRECTORY):
        self.hermes_storage_root = Path(hermes_storage_root)
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
        return {'id':hermes_job_path.name, 'request':hermes_request_record, 'status':hermes_status_record, 'result':hermes_result_record, 'diff':hermes_diff_text[:500000], 'diff_truncated':hermes_diff_truncated, 'log':hermes_log_text}

    def execute_hermes_command(self, hermes_command_name, hermes_payload_record):
        if not isinstance(hermes_payload_record, dict):
            raise ValueError('입력은 객체여야 합니다.')
        with self.hold_hermes_service_lock():
            if hermes_command_name == 'hermes-submit':
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
