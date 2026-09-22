"""터미널에서 사용하는 도서 편집 등록·실행·조회·반영 CLI."""
import argparse
import contextlib
import fcntl
import json
from pathlib import Path
import re
import sys
import signal
import traceback
from jsonschema import Draft202012Validator
from .book_automation import AUTOMATION_REQUEST_SCHEMA,run_automated_book
from .book_collections import load_document_collections,resolve_collection_request
from .bookbinding import BOOK_IDENTIFIER_PATTERN
from .documents import load_workspace_config,load_yaml_document,save_yaml_document
from .reorganization import execute_document_reorganization

DEFAULT_WORKSPACE_CONFIG=Path(__file__).resolve().parents[2]/'.local/worldbuilding/workspace.yaml'


def parse_book_arguments(current_argument_values=None):
    current_argument_parser=argparse.ArgumentParser(description=__doc__)
    current_argument_parser.add_argument('--config',type=Path,default=DEFAULT_WORKSPACE_CONFIG,help='문서 작업 공간 설정 YAML')
    current_subcommand_parser=current_argument_parser.add_subparsers(dest='operation_name',required=True)
    current_subcommand_parser.add_parser('list',help='도서와 연결된 루트 조회')
    current_edit_parser=current_subcommand_parser.add_parser('edit',help='AI 자동 편집 실행 또는 작업 등록')
    current_edit_parser.add_argument('--collection',choices=['world','system-design'],required=True)
    current_instruction_group=current_edit_parser.add_mutually_exclusive_group(required=True)
    current_instruction_group.add_argument('--instruction',help='편집 지시')
    current_instruction_group.add_argument('--instruction-file',type=Path,help='UTF-8 지시 파일. - 는 표준 입력')
    current_edit_parser.add_argument('--submit',action='store_true',help='실행 중인 관리도구 큐에 등록 후 즉시 종료')
    for current_operation_name in ['status','result']:
        current_query_parser=current_subcommand_parser.add_parser(current_operation_name,help='작업 상태' if current_operation_name=='status' else '완료 결과와 파일 변경 미리보기')
        current_query_parser.add_argument('--task',required=True)
    for current_operation_name in ['apply','rollback']:
        current_mutation_parser=current_subcommand_parser.add_parser(current_operation_name,help='검토한 파일 변경 반영' if current_operation_name=='apply' else '파일 변경 되돌리기')
        current_mutation_parser.add_argument('--reorganization',required=True)
    return current_argument_parser.parse_args(current_argument_values)


def require_active_manager(current_private_root):
    current_manager_path=current_private_root/'manager.lock'
    if not current_manager_path.exists():
        raise ValueError('--submit은 실행 중인 관리도구가 필요합니다. 서버에서 관리도구를 먼저 시작하세요.')
    with current_manager_path.open('r') as current_lock_stream:
        try:
            fcntl.flock(current_lock_stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            return
        fcntl.flock(current_lock_stream,fcntl.LOCK_UN)
    raise ValueError('관리도구가 실행 중이 아닙니다. --submit 없이 직접 실행하거나 관리도구를 시작하세요.')


def locate_book_task(current_private_root,current_task_identifier):
    if not re.fullmatch(BOOK_IDENTIFIER_PATTERN,current_task_identifier):
        raise ValueError('올바르지 않은 작업 ID입니다.')
    current_task_candidates=[current_private_root/current_queue_name/current_task_identifier for current_queue_name in ['jobs','book-cli-jobs']]
    current_task_matches=[current_task_path for current_task_path in current_task_candidates if current_task_path.is_dir()]
    if len(current_task_matches)!=1:
        raise ValueError('도서 작업을 찾을 수 없거나 ID가 중복되었습니다.')
    current_run_root=current_task_matches[0]
    if load_yaml_document(current_run_root/'request.yaml').get('task_kind_name')!='book-edit':
        raise ValueError('AI 도서 편집 작업만 조회할 수 있습니다.')
    return current_run_root


def execute_book_arguments(current_argument_values):
    import worldbuilding
    import runtime
    current_config_values=load_workspace_config(current_argument_values.config)
    current_private_root=Path(current_config_values['private_state_root'])
    if current_argument_values.operation_name=='list':
        return {'collection_entries':load_document_collections(current_config_values)}
    if current_argument_values.operation_name in {'apply','rollback'}:
        return execute_document_reorganization(current_config_values,current_argument_values.reorganization,current_argument_values.operation_name)
    if current_argument_values.operation_name in {'status','result'}:
        current_run_root=locate_book_task(current_private_root,current_argument_values.task)
        current_status_values=load_yaml_document(current_run_root/'status.yaml')
        if current_argument_values.operation_name=='status':
            return {**current_status_values,'execution_log_path':str(current_run_root/'execution.log')}
        if current_status_values['current_stage_name']!='completed':
            raise ValueError('완료된 작업만 결과를 조회할 수 있습니다: '+current_status_values['current_stage_name'])
        return {**load_yaml_document(current_run_root/'book-result.yaml'),'workflow_task_id':current_run_root.name}
    if current_argument_values.instruction_file is not None:
        current_instruction_text=sys.stdin.read() if str(current_argument_values.instruction_file)=='-' else current_argument_values.instruction_file.read_text(encoding='utf-8')
    else:
        current_instruction_text=current_argument_values.instruction
    current_collection_entry=next(current_collection_entry for current_collection_entry in load_document_collections(current_config_values) if current_collection_entry['collection_id']==current_argument_values.collection)
    current_request_values={**current_collection_entry,'requested_instruction_text':current_instruction_text.strip(),'task_kind_name':'book-edit'}
    Draft202012Validator(AUTOMATION_REQUEST_SCHEMA).validate(current_request_values)
    resolve_collection_request(current_config_values,current_request_values)
    if current_argument_values.submit:
        require_active_manager(current_private_root)
    from .jobs import register_document_job
    current_run_root=register_document_job(current_config_values,current_request_values,'queued' if current_argument_values.submit else 'direct')
    current_task_identifier=current_run_root.name
    worldbuilding.CURRENT_LOG_PATH=current_run_root/'execution.log'
    worldbuilding.emit_runtime_trace('registered',f'작업={current_task_identifier}')
    current_submission_values={'workflow_task_id':current_task_identifier,'current_stage_name':'queued','execution_log_path':str(current_run_root/'execution.log')}
    if current_argument_values.submit:
        return current_submission_values
    run_automated_book(current_config_values,current_run_root)
    return {**load_yaml_document(current_run_root/'book-result.yaml'),'workflow_task_id':current_task_identifier,'execution_log_path':str(current_run_root/'execution.log')}


def run_book_cli(current_argument_values=None):
    current_parsed_values=parse_book_arguments(current_argument_values)
    def handle_terminal_termination(current_signal_number,current_stack_frame):
        raise KeyboardInterrupt('터미널 도서 작업 종료 요청')
    previous_signal_handler=signal.signal(signal.SIGTERM,handle_terminal_termination)
    try:
        with contextlib.redirect_stdout(sys.stderr):
            current_result_values=execute_book_arguments(current_parsed_values)
    except (Exception,KeyboardInterrupt) as current_execution_error:
        import worldbuilding
        current_failure_text=traceback.format_exc()
        if worldbuilding.CURRENT_LOG_PATH is not None:
            with worldbuilding.CURRENT_LOG_PATH.open('a') as current_log_stream:
                current_log_stream.write(current_failure_text)
            print('\n'.join(worldbuilding.CURRENT_LOG_PATH.read_text().splitlines()[-30:]),file=sys.stderr)
        else:
            print(current_failure_text,file=sys.stderr)
        print(json.dumps({'failure_reason_text':str(current_execution_error)},ensure_ascii=False))
        raise SystemExit(130 if isinstance(current_execution_error,KeyboardInterrupt) else 1)
    finally:
        signal.signal(signal.SIGTERM,previous_signal_handler)
    print(json.dumps(current_result_values,ensure_ascii=False))
