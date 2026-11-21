"""Hermes 대화 세션의 로컬 기록과 중복 요청을 관리한다."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import threading
import uuid

from workflow.common.generation_records import write_record_atomically

HERMES_SESSION_ROOT = Path(__file__).resolve().parents[3] / '.local/hermes-agent/sessions'
HERMES_SESSION_ID_PATTERN = re.compile(r'[0-9a-f]{32}')
HERMES_SESSION_REQUEST_PATTERN = re.compile(r'[A-Za-z0-9_-]{8,80}')
HERMES_SESSION_JOB_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}')
HERMES_SESSION_MAX_MESSAGES = 200


def title_from_first_request(text):
    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    for line in lines:
        if line.startswith(("사용할 도구:", "사용할 생성기:")):
            continue
        subject = re.sub(r"\s*(?:해\s*주세요|해\s*줘|해주세요|해줘)[.!?。]*$", "", line).strip() or line
        return subject if len(subject) <= 48 else subject[:47].rstrip() + "…"
    return (lines[0].split(":", 1)[-1].strip()[:48] if lines else "") or "새 대화"


class HermesSessionStore:
    """작업 기록은 소유하지 않고 사용자 메시지와 작업 ID만 연결한다."""

    def __init__(self, session_storage_root=HERMES_SESSION_ROOT):
        self.session_storage_root = Path(session_storage_root)
        self.session_thread_lock = threading.RLock()

    def _form_path(self, session_id, form_id):
        self.resolve_session_record_path(session_id)
        if not isinstance(form_id, str) or not re.fullmatch(r'[a-f0-9]{32}', form_id):
            raise ValueError('폼 식별자 형식 오류')
        directory = self.session_storage_root / 'form-snapshots'
        if directory.is_symlink():
            raise ValueError('폼 저장 경로에 심볼릭 링크를 사용할 수 없습니다.')
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (session_id + '-' + form_id + '.json')
        if path.is_symlink():
            raise ValueError('폼 저장본은 심볼릭 링크일 수 없습니다.')
        return path

    def save_video_form(self, session_id, form_id, request, video_info):
        if not isinstance(request, dict) or not isinstance(video_info, (dict, type(None))):
            raise ValueError('폼 입력 형식 오류')
        if (not isinstance(request.get('images'), list) or len(request['images']) > 1
                or any(not isinstance(value, str) for value in request['images'])
                or not isinstance(request.get('pose_video'), str)
                or any(not isinstance(request.get(key), str) or len(request[key]) > 8000 for key in ('prompt', 'negative_prompt'))
                or any(type(request.get(key)) not in (int, float) for key in ('frames','steps','seed','flow_shift','guidance_scale','switch_ratio'))):
            raise ValueError('폼 필드 형식 오류')
        snapshot = {'request': request, 'video_info': video_info}
        raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        if len(raw) > 39000000:
            raise ValueError('폼 첨부를 포함해 39MB 이하여야 합니다.')
        digest = hashlib.sha256(raw).hexdigest()
        with self.hold_session_storage_lock():
            session = self.read_session_record_locked(session_id)
            path = self._form_path(session_id, form_id)
            previous = next((m for m in session['messages'] if m.get('form_id') == form_id), None)
            if previous:
                if previous.get('form_sha256') != digest:
                    raise ValueError('같은 폼 ID를 다른 입력에 사용할 수 없습니다.')
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ValueError('저장된 폼을 확인할 수 없습니다.')
                return {'form_id': form_id, 'duplicate': True}
            if len(session['messages']) >= HERMES_SESSION_MAX_MESSAGES:
                raise ValueError('세션 메시지 한도에 도달했습니다.')
            # A deterministic snapshot can be safely rewritten after an interrupted append.
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('동일 폼 ID의 저장본이 다릅니다.')
            if not path.exists():
                import os, tempfile
                fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.form-')
                try:
                    with os.fdopen(fd, 'wb') as stream:
                        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
                    os.replace(temp, path)
                finally:
                    if os.path.exists(temp): os.unlink(temp)
            now = datetime.now(timezone.utc).isoformat()
            if not session['messages']:
                session['title'] = 'Wan Fun Control 생성 폼'
            session['messages'].append({'id':form_id, 'role':'user', 'text':'Wan Fun Control 생성 폼', 'created_at':now, 'job_id':None, 'form_id':form_id, 'form_sha256':digest})
            session['updated_at'] = now
            write_record_atomically(self.resolve_session_record_path(session_id), session)
            return {'form_id': form_id, 'duplicate': False}

    def read_video_form(self, session_id, form_id):
        with self.hold_session_storage_lock():
            session = self.read_session_record_locked(session_id)
            message = next((m for m in session['messages'] if m.get('form_id') == form_id), None)
            if not message: raise ValueError('이 대화에서 폼을 찾을 수 없습니다.')
            path = self._form_path(session_id, form_id)
            if not path.is_file() or path.stat().st_size > 39000000: raise ValueError('폼 저장본을 읽을 수 없습니다.')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != message.get('form_sha256'): raise ValueError('폼 저장본이 변경됐습니다.')
            return json.loads(raw)

    @contextmanager
    def hold_session_storage_lock(self):
        if self.session_storage_root.is_symlink():
            raise ValueError('세션 저장 경로에 심볼릭 링크를 사용할 수 없습니다.')
        self.session_storage_root.mkdir(parents=True, exist_ok=True)
        current_lock_path = self.session_storage_root / '.sessions.lock'
        if current_lock_path.is_symlink():
            raise ValueError('세션 잠금 경로에 심볼릭 링크를 사용할 수 없습니다.')
        with self.session_thread_lock, current_lock_path.open('a') as current_lock_stream:
            fcntl.flock(current_lock_stream, fcntl.LOCK_EX)
            yield

    def resolve_session_record_path(self, session_identifier_value):
        if not isinstance(session_identifier_value, str) or not HERMES_SESSION_ID_PATTERN.fullmatch(session_identifier_value):
            raise ValueError('세션 ID 형식 오류')
        current_record_path = self.session_storage_root / (session_identifier_value + '.json')
        if current_record_path.is_symlink():
            raise ValueError('세션 기록은 심볼릭 링크일 수 없습니다.')
        return current_record_path

    def read_session_record_locked(self, session_identifier_value, archived=False):
        current_record_path = self.resolve_session_record_path(session_identifier_value)
        if archived:
            current_record_path = current_record_path.with_suffix(".archived")
        if current_record_path.is_symlink() or not current_record_path.is_file():
            raise ValueError('세션을 찾을 수 없습니다.')
        current_session_record = json.loads(current_record_path.read_text(encoding='utf-8'))
        if not isinstance(current_session_record, dict) or current_session_record.get('version') != 1 or current_session_record.get('id') != session_identifier_value or not isinstance(current_session_record.get('messages'), list):
            raise ValueError('세션 기록 형식 오류')
        if not current_session_record.get("title"):
            first = next((message["text"] for message in current_session_record["messages"]
                          if isinstance(message, dict) and isinstance(message.get("text"), str) and message["text"].strip()), "")
            current_session_record["title"] = title_from_first_request(first)
        return current_session_record

    def create_session_record(self, session_identifier_value=None):
        with self.hold_session_storage_lock():
            current_session_identifier = session_identifier_value if session_identifier_value is not None else uuid.uuid4().hex
            current_created_timestamp = datetime.now(timezone.utc).isoformat()
            current_session_record = {'version': 1, 'id': current_session_identifier, 'created_at': current_created_timestamp, 'updated_at': current_created_timestamp, 'messages': [], 'title': '새 대화'}
            current_record_path = self.resolve_session_record_path(current_session_identifier)
            if current_record_path.with_suffix(".archived").exists():
                raise ValueError("보관된 세션입니다. 먼저 복원하세요.")
            try:
                current_record_path.lstat()
            except FileNotFoundError:
                pass
            else:
                return self.read_session_record_locked(current_session_identifier)
            write_record_atomically(current_record_path, current_session_record)
            return current_session_record

    def read_session_record(self, session_identifier_value):
        with self.hold_session_storage_lock():
            return self.read_session_record_locked(session_identifier_value)

    def change_session_lifecycle(self, session_id, operation, expected_update):
        with self.hold_session_storage_lock():
            active = self.resolve_session_record_path(session_id)
            archive = active.with_suffix(".archived")
            record = self.read_session_record_locked(session_id, archived=operation != "archive")
            if record["updated_at"] != expected_update:
                raise ValueError("세션이 변경되었습니다. 목록을 다시 조회하세요.")
            if any(message.get("job_id") is None and not message.get("form_id") for message in record["messages"]):
                raise ValueError("접수 확인 중인 메시지가 있습니다. 세션에서 접수 결과를 먼저 확인하세요.")
            if operation == "delete":
                archive.unlink()
                for message in record['messages']:
                    if message.get('form_id'):
                        self._form_path(session_id, message['form_id']).unlink(missing_ok=True)
            elif operation in ("archive", "restore"):
                source, destination = (active, archive) if operation == "archive" else (archive, active)
                if destination.exists() or destination.is_symlink():
                    raise ValueError("대상 세션 기록이 이미 있습니다.")
                record["updated_at"] = datetime.now(timezone.utc).isoformat()
                write_record_atomically(source, record)
                source.rename(destination)
            else:
                raise ValueError("지원하지 않는 세션 작업입니다.")
            return {"session_id": session_id, "operation": operation}

    def list_session_records(self, current_page_request=None, archived=False):
        if current_page_request is not None and (not isinstance(current_page_request,dict) or set(current_page_request)-{'offset','limit','snapshot','query'}):
            raise ValueError('세션 목록 조회 필드 오류')
        current_query_value=(current_page_request or {}).get('query','')
        if not isinstance(current_query_value,str) or len(current_query_value)>100 or any(ord(char)<32 for char in current_query_value):
            raise ValueError('세션 목록 검색 조건 오류')
        current_query_value=current_query_value.strip().casefold()
        with self.hold_session_storage_lock():
            current_session_summaries = []
            current_unreadable_identifiers = []
            for current_record_path in self.session_storage_root.glob('*.archived' if archived else '*.json'):
                current_session_identifier = current_record_path.stem
                if not HERMES_SESSION_ID_PATTERN.fullmatch(current_session_identifier):
                    continue
                try:
                    current_session_record = self.read_session_record_locked(current_session_identifier, archived=archived)
                    current_message_records=current_session_record['messages']
                    if not isinstance(current_session_record.get('created_at'),str) or not isinstance(current_session_record.get('updated_at'),str) or any(not isinstance(item,dict) or not isinstance(item.get('text'),str) for item in current_message_records):
                        raise ValueError('세션 지시 기록 오류')
                except (OSError,ValueError,TypeError,UnicodeError):
                    current_unreadable_identifiers.append(current_session_identifier)
                    continue
                if current_query_value and current_query_value not in current_session_identifier and current_query_value not in current_session_record['title'].casefold() and not any(current_query_value in item['text'].casefold() for item in current_message_records):continue
                current_session_summaries.append({'id': current_session_identifier, 'title': current_session_record['title'], 'created_at': current_session_record['created_at'], 'updated_at': current_session_record['updated_at'], 'message_count': len(current_message_records)})
            current_unreadable_identifiers.sort()
            current_session_summaries.sort(key=lambda current_session_record: (current_session_record['updated_at'], current_session_record['id']), reverse=True)
            if not current_page_request:
                return {'sessions': current_session_summaries[:100], 'truncated': len(current_session_summaries) > 100, 'unreadable_count':len(current_unreadable_identifiers)}
            current_offset_value=current_page_request.get('offset',0)
            current_limit_value=current_page_request.get('limit',30)
            if type(current_offset_value) is not int or current_offset_value<0 or type(current_limit_value) is not int or not 1<=current_limit_value<=30:
                raise ValueError('세션 목록 검색 조건 오류')
            current_matching_summaries=current_session_summaries
            current_snapshot_value=hashlib.sha256(json.dumps({'query':current_query_value,'sessions':current_matching_summaries,'unreadable':current_unreadable_identifiers},sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
            if (current_offset_value>0 and current_page_request.get('snapshot')!=current_snapshot_value) or ('snapshot' in current_page_request and current_page_request['snapshot']!=current_snapshot_value):
                raise ValueError('세션 목록이 변경됐습니다. 처음부터 다시 조회하세요.')
            current_page_values=current_matching_summaries[current_offset_value:current_offset_value+current_limit_value]
            if current_query_value and not archived:
                # 검색 응답에 첫 요청 원문에서 파생한 제목이 포함되지 않도록 한다.
                current_page_values = [{key: value for key, value in row.items() if key != "title"}
                                       for row in current_page_values]
            current_next_offset=current_offset_value+len(current_page_values)
            return {'sessions':current_page_values,'offset':current_offset_value,'next_offset':current_next_offset if current_next_offset<len(current_matching_summaries) else None,'total':len(current_matching_summaries),'snapshot':current_snapshot_value,'unreadable_count':len(current_unreadable_identifiers)}

    def append_session_request(self, session_identifier_value, request_identifier_value, request_message_text, execution_prompt_text=None, verification_module_names=None, context_truncated=False):
        if not isinstance(request_identifier_value, str) or not HERMES_SESSION_REQUEST_PATTERN.fullmatch(request_identifier_value):
            raise ValueError('접수 식별자 형식 오류')
        if not isinstance(request_message_text, str) or not request_message_text.strip() or len(request_message_text) > 12000:
            raise ValueError('메시지는 1~12000자여야 합니다.')
        with self.hold_session_storage_lock():
            current_session_record = self.read_session_record_locked(session_identifier_value)
            for current_message_record in current_session_record['messages']:
                if current_message_record.get('request_id') == request_identifier_value:
                    if current_message_record.get('text') != request_message_text or current_message_record.get('verification_modules', []) != (verification_module_names or []):
                        raise ValueError('같은 접수 식별자를 다른 메시지에 사용할 수 없습니다.')
                    return {'message': current_message_record, 'duplicate': True}
            if len(current_session_record['messages']) >= HERMES_SESSION_MAX_MESSAGES:
                raise ValueError('세션 메시지 한도에 도달했습니다. 새 세션을 시작하세요.')
            current_created_timestamp = datetime.now(timezone.utc).isoformat()
            current_message_record = {'id': uuid.uuid4().hex, 'request_id': request_identifier_value, 'role': 'user', 'text': request_message_text, 'created_at': current_created_timestamp, 'job_id': None, 'execution_prompt': execution_prompt_text if execution_prompt_text is not None else request_message_text, 'verification_modules': verification_module_names or [], 'context_truncated': context_truncated}
            if not current_session_record['messages']:
                current_session_record['title'] = title_from_first_request(request_message_text)
            current_session_record['messages'].append(current_message_record)
            current_session_record['updated_at'] = current_created_timestamp
            write_record_atomically(self.resolve_session_record_path(session_identifier_value), current_session_record)
            return {'message': current_message_record, 'duplicate': False}

    def attach_session_job(self, session_identifier_value, request_identifier_value, job_identifier_value):
        if not isinstance(job_identifier_value, str) or not HERMES_SESSION_JOB_PATTERN.fullmatch(job_identifier_value):
            raise ValueError('작업 ID 형식 오류')
        with self.hold_session_storage_lock():
            current_session_record = self.read_session_record_locked(session_identifier_value)
            current_message_record = next((current_message_record for current_message_record in current_session_record['messages'] if current_message_record.get('request_id') == request_identifier_value), None)
            if current_message_record is None:
                raise ValueError('세션 메시지를 찾을 수 없습니다.')
            if current_message_record['job_id'] not in (None, job_identifier_value):
                raise ValueError('메시지에 다른 작업이 이미 연결되어 있습니다.')
            if current_message_record['job_id'] is None:
                current_message_record['job_id'] = job_identifier_value
                current_session_record['updated_at'] = datetime.now(timezone.utc).isoformat()
                write_record_atomically(self.resolve_session_record_path(session_identifier_value), current_session_record)
            return current_message_record
