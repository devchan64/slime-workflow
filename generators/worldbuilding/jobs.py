"""웹 관리도구와 터미널이 공유하는 문서 작업 등록 계약."""
from datetime import datetime
from pathlib import Path
import uuid
from zoneinfo import ZoneInfo
from jsonschema import Draft202012Validator
from .documents import REQUEST_INPUT_SCHEMA,save_yaml_document


def register_document_job(current_config_values,current_request_values,current_execution_mode='queued'):
    if current_execution_mode not in {'queued','direct'}:
        raise ValueError('지원하지 않는 작업 실행 방식입니다.')
    if current_request_values.get('task_kind_name')=='book-edit':
        from .book_automation import AUTOMATION_REQUEST_SCHEMA
        from .book_collections import resolve_collection_request
        Draft202012Validator(AUTOMATION_REQUEST_SCHEMA).validate(current_request_values)
        resolve_collection_request(current_config_values,current_request_values)
    else:
        Draft202012Validator(REQUEST_INPUT_SCHEMA).validate(current_request_values)
    current_task_identifier=datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:8]
    current_queue_name='jobs' if current_execution_mode=='queued' else 'book-cli-jobs'
    current_run_root=Path(current_config_values['private_state_root'])/current_queue_name/current_task_identifier
    current_run_root.mkdir(parents=True,mode=0o700)
    save_yaml_document(current_run_root/'request.yaml',current_request_values)
    # 상태 파일은 요청 기록이 끝난 뒤 공개한다. 직접 실행은 웹 큐와 분리해 이중 실행을 막는다.
    save_yaml_document(current_run_root/'status.yaml',{'workflow_task_id':current_task_identifier,'current_stage_name':'queued' if current_execution_mode=='queued' else 'context','updated_timestamp_text':datetime.now(ZoneInfo('Asia/Seoul')).isoformat()})
    return current_run_root
