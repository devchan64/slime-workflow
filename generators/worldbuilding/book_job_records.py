"""도서 작업과 단계별 산출물을 제한된 읽기 API로 제공한다."""
from pathlib import Path
import re
from urllib.parse import quote

from .bookbinding import BOOK_IDENTIFIER_PATTERN
from .documents import load_yaml_document, resolve_document_path
from .book_pipeline import BOOK_PIPELINE_STAGE_LABELS

BOOK_RECORD_READ_LIMIT = 128_000
BOOK_HISTORY_PAGE_SIZE = 20
BOOK_RECORD_SUFFIXES = {'.yaml', '.md', '.log'}
BOOK_TERMINAL_STATES = {'completed', 'failed', 'rolled_back'}


def locate_record_directory(current_private_root, current_task_identifier):
    if not isinstance(current_task_identifier, str) or not re.fullmatch(BOOK_IDENTIFIER_PATTERN, current_task_identifier):
        raise ValueError('올바르지 않은 도서 작업 ID입니다.')
    current_matching_roots = [resolve_document_path(current_private_root, current_queue_name+'/'+current_task_identifier) for current_queue_name in ('jobs', 'book-cli-jobs') if (current_private_root/current_queue_name/current_task_identifier).is_dir()]
    if len(current_matching_roots)!=1:
        raise ValueError('도서 작업을 찾을 수 없거나 ID가 중복되었습니다.')
    current_run_root = current_matching_roots[0]
    if load_yaml_document(current_run_root/'request.yaml').get('task_kind_name')!='book-edit':
        raise ValueError('도서 편집 작업만 조회할 수 있습니다.')
    return current_run_root


def describe_record_artifact(current_run_root, current_file_path):
    current_relative_path = current_file_path.relative_to(current_run_root).as_posix()
    return {'relative_path': current_relative_path, 'absolute_path': str(current_file_path), 'byte_count': current_file_path.stat().st_size, 'read_url': '/worldbuilding/book-jobs/'+current_run_root.name+'/artifacts/'+quote(current_relative_path, safe='/')}


def read_book_job(current_private_root, current_task_identifier, current_include_artifacts=False):
    current_run_root = locate_record_directory(current_private_root, current_task_identifier)
    current_request_values = load_yaml_document(current_run_root/'request.yaml')
    current_status_values = load_yaml_document(current_run_root/'status.yaml')
    current_result_values = {**current_status_values, 'workflow_task_id': current_run_root.name, 'collection_id': current_request_values['collection_id'], 'requested_instruction_text': current_request_values['requested_instruction_text'], 'book_edit_stage_name': current_request_values.get('book_edit_stage_name', 'document-reconstruction'), 'run_directory': str(current_run_root)}
    if (current_run_root/'pipeline.yaml').is_file():
        current_stage_entries = load_yaml_document(current_run_root/'pipeline.yaml')['stage_entries']
    else:
        current_stage_name = current_result_values['book_edit_stage_name']
        current_stage_entries = [{'stage_number': None, 'book_edit_stage_name': current_stage_name, 'stage_label': BOOK_PIPELINE_STAGE_LABELS.get(current_stage_name, '기존 자동 편집'), 'current_stage_name': current_status_values['current_stage_name'], 'run_directory': str(current_run_root)}]
    for current_stage_entry in current_stage_entries:
        current_stage_root = Path(current_stage_entry['run_directory'])
        if not current_stage_root.resolve().is_relative_to(current_run_root.resolve()) or current_stage_root.is_symlink():
            raise ValueError('단계 기록 경로가 작업 범위를 벗어났습니다.')
        if (current_stage_root/'status.yaml').is_file():
            current_stage_status = load_yaml_document(current_stage_root/'status.yaml')
            current_stage_entry['result_summary_text'] = current_stage_status.get('result_summary_text', '')
            if current_stage_entry['current_stage_name'] not in BOOK_TERMINAL_STATES|{'skipped'}:
                current_stage_entry['current_stage_name'] = current_stage_status['current_stage_name']
            if current_stage_status.get('failure_reason_text'):
                current_stage_entry['failure_reason_text'] = current_stage_status['failure_reason_text']
        if current_status_values['current_stage_name']=='failed' and current_stage_entry['current_stage_name'] not in BOOK_TERMINAL_STATES|{'skipped'}:
            current_stage_entry['current_stage_name'] = 'skipped' if current_stage_entry['current_stage_name']=='pending' else 'failed'
            current_stage_entry['failure_reason_text'] = current_status_values.get('failure_reason_text', '작업이 중단되었습니다.')
        current_stage_entry['artifacts'] = [describe_record_artifact(current_run_root, current_stage_root/current_record_name) for current_record_name in ('request.yaml', 'stage-input.yaml', 'status.yaml', 'execution.log', 'book-result.yaml') if (current_stage_root/current_record_name).is_file()]
    current_result_values['stage_entries'] = current_stage_entries
    if current_include_artifacts:
        current_result_values['artifacts'] = [describe_record_artifact(current_run_root, current_file_path) for current_file_path in sorted(current_run_root.rglob('*')) if current_file_path.is_file() and not current_file_path.is_symlink() and current_file_path.suffix in BOOK_RECORD_SUFFIXES and not any(current_path_part.startswith('.') for current_path_part in current_file_path.relative_to(current_run_root).parts)]
    return current_result_values


def list_book_jobs(current_private_root, current_collection_id, current_page_offset=0):
    if current_collection_id not in {'world', 'system-design'} or not isinstance(current_page_offset, int) or current_page_offset<0:
        raise ValueError('올바르지 않은 도서 작업 목록 요청입니다.')
    current_matching_tasks = []
    for current_queue_name in ('jobs', 'book-cli-jobs'):
        for current_status_path in (current_private_root/current_queue_name).glob('*/status.yaml'):
            current_request_values = load_yaml_document(current_status_path.parent/'request.yaml')
            if current_request_values.get('task_kind_name')=='book-edit' and current_request_values.get('collection_id')==current_collection_id:
                current_matching_tasks.append(current_status_path.parent.name)
    current_matching_tasks.sort(reverse=True)
    current_job_entries = [read_book_job(current_private_root, current_task_identifier) for current_task_identifier in current_matching_tasks[current_page_offset:current_page_offset+BOOK_HISTORY_PAGE_SIZE]]
    current_active_identifiers = [current_task_identifier for current_task_identifier in current_matching_tasks if load_yaml_document(locate_record_directory(current_private_root, current_task_identifier)/'status.yaml')['current_stage_name'] not in BOOK_TERMINAL_STATES]
    return {'job_entries': current_job_entries, 'total_count': len(current_matching_tasks), 'page_offset': current_page_offset, 'page_size': BOOK_HISTORY_PAGE_SIZE, 'active_task_identifiers': current_active_identifiers}


def read_book_record(current_private_root, current_task_identifier, current_relative_path):
    current_run_root = locate_record_directory(current_private_root, current_task_identifier)
    current_record_path = resolve_document_path(current_run_root, current_relative_path)
    if not current_record_path.is_file() or current_record_path.suffix not in BOOK_RECORD_SUFFIXES:
        raise ValueError('조회할 수 없는 도서 기록입니다.')
    current_byte_count = current_record_path.stat().st_size
    with current_record_path.open('rb') as current_record_stream:
        if current_record_path.suffix=='.log' and current_byte_count>BOOK_RECORD_READ_LIMIT:
            current_record_stream.seek(-BOOK_RECORD_READ_LIMIT, 2)
        current_record_bytes = current_record_stream.read(BOOK_RECORD_READ_LIMIT)
    return {**describe_record_artifact(current_run_root, current_record_path), 'content_text': current_record_bytes.decode('utf-8', errors='replace'), 'truncated_flag': current_byte_count>BOOK_RECORD_READ_LIMIT, 'tail_flag': current_record_path.suffix=='.log'}
