"""도서 편집 네 단계의 순차 실행과 영속 기록을 관리한다."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .bookbinding import collect_book_sources
from .documents import load_yaml_document, save_yaml_document

BOOK_PIPELINE_STAGE_LABELS = {
    'document-summary': '문서 요약',
    'table-of-contents': '목차 구성',
    'document-reconstruction': '원문 순서 재구성',
    'document-cleanup': '문서 정리·검수',
}


def current_pipeline_timestamp():
    return datetime.now(ZoneInfo('Asia/Seoul')).isoformat()


def initialize_book_pipeline(current_run_root, current_request_values):
    current_stage_entries = []
    for current_stage_number, (current_stage_name, current_stage_label) in enumerate(BOOK_PIPELINE_STAGE_LABELS.items(), 1):
        current_stage_root = current_run_root/'stages'/f'{current_stage_number:02d}-{current_stage_name}'
        current_stage_entries.append({'stage_number': current_stage_number, 'book_edit_stage_name': current_stage_name, 'stage_label': current_stage_label, 'current_stage_name': 'pending', 'run_directory': str(current_stage_root), 'started_timestamp_text': None, 'finished_timestamp_text': None})
    current_pipeline_values = {'pipeline_schema_version': 1, 'workflow_task_id': current_run_root.name, 'collection_id': current_request_values['collection_id'], 'created_timestamp_text': current_pipeline_timestamp(), 'current_stage_name': 'queued', 'stage_entries': current_stage_entries}
    save_yaml_document(current_run_root/'pipeline.yaml', current_pipeline_values)
    return current_pipeline_values


def execute_book_pipeline(current_config_values, current_run_root, current_request_values):
    import runtime
    import worldbuilding
    from .book_automation import run_automated_book

    current_pipeline_values = load_yaml_document(current_run_root/'pipeline.yaml') if (current_run_root/'pipeline.yaml').exists() else initialize_book_pipeline(current_run_root, current_request_values)
    if any(current_stage_entry['current_stage_name']!='pending' for current_stage_entry in current_pipeline_values['stage_entries']):
        raise ValueError('이미 실행한 도서 작업은 덮어쓰지 않습니다. 새 작업으로 실행하세요.')
    current_pipeline_values['current_stage_name'] = 'running'
    current_parent_log_path = current_run_root/'execution.log'
    current_previous_result = None
    try:
        current_source_hashes = {current_source_path: current_source_entry['source_content_hash'] for current_source_path, current_source_entry in collect_book_sources(current_config_values, current_request_values['source_directory_paths']).items()}
        save_yaml_document(current_run_root/'source-snapshot.yaml', {'source_hashes': current_source_hashes})
        for current_stage_entry in current_pipeline_values['stage_entries']:
            current_stage_root = Path(current_stage_entry['run_directory'])
            current_stage_root.mkdir(parents=True, exist_ok=False)
            current_stage_request = {**current_request_values, 'book_edit_stage_name': current_stage_entry['book_edit_stage_name']}
            save_yaml_document(current_stage_root/'request.yaml', current_stage_request)
            save_yaml_document(current_stage_root/'status.yaml', {'workflow_task_id': current_run_root.name, 'current_stage_name': 'queued'})
            save_yaml_document(current_stage_root/'stage-input.yaml', {'previous_result_path': str(current_previous_result) if current_previous_result else None, 'source_snapshot_path': str(current_run_root/'source-snapshot.yaml')})
            current_stage_entry.update(current_stage_name='running', started_timestamp_text=current_pipeline_timestamp())
            save_yaml_document(current_run_root/'pipeline.yaml', current_pipeline_values)
            runtime.update_task_status(current_run_root, 'generating', active_book_stage_name=current_stage_entry['book_edit_stage_name'], result_summary_text=f"{current_stage_entry['stage_number']}/4 {current_stage_entry['stage_label']} 실행 중")
            worldbuilding.emit_runtime_trace('book-pipeline', f"{current_stage_entry['stage_number']}/4 시작 · 경로={current_stage_root}")
            try:
                run_automated_book(current_config_values, current_stage_root)
                current_latest_hashes = {current_source_path: current_source_entry['source_content_hash'] for current_source_path, current_source_entry in collect_book_sources(current_config_values, current_request_values['source_directory_paths']).items()}
                if current_latest_hashes!=current_source_hashes:
                    raise ValueError('단계 실행 중 원본이 변경되었습니다. 같은 원본으로 새 작업을 실행하세요.')
                current_previous_result = current_stage_root/'book-result.yaml'
                if not current_previous_result.is_file():
                    raise ValueError('단계 결과 파일이 없습니다: '+str(current_previous_result))
                current_stage_entry['current_stage_name'] = 'completed'
            except BaseException as current_stage_error:
                current_stage_entry.update(current_stage_name='failed', failure_reason_text=str(current_stage_error) or type(current_stage_error).__name__)
                raise
            finally:
                worldbuilding.CURRENT_LOG_PATH = current_parent_log_path
                current_stage_entry['finished_timestamp_text'] = current_pipeline_timestamp()
                save_yaml_document(current_run_root/'pipeline.yaml', current_pipeline_values)
            worldbuilding.emit_runtime_trace('book-pipeline', f"{current_stage_entry['stage_number']}/4 완료 · 결과={current_previous_result}")
        current_final_result = load_yaml_document(current_previous_result)
        save_yaml_document(current_run_root/'book-result.yaml', {**current_final_result, 'book_edit_stage_name': 'all-stages', 'stage_entries': current_pipeline_values['stage_entries']})
        current_pipeline_values['current_stage_name'] = 'completed'
        runtime.update_task_status(current_run_root, 'completed', result_summary_text='1~4단계 완료 · 문서 요약·목차·재구성·정리 결과를 확인하세요.')
    except BaseException as current_pipeline_error:
        current_pipeline_values['current_stage_name'] = 'failed'
        for current_stage_entry in current_pipeline_values['stage_entries']:
            if current_stage_entry['current_stage_name']=='running':
                current_stage_entry.update(current_stage_name='failed', failure_reason_text=str(current_pipeline_error), finished_timestamp_text=current_pipeline_timestamp())
            if current_stage_entry['current_stage_name']=='pending':
                current_stage_entry.update(current_stage_name='skipped', failure_reason_text='앞 단계 실패로 실행하지 않았습니다.')
        raise
    finally:
        worldbuilding.CURRENT_LOG_PATH = current_parent_log_path
        current_pipeline_values['finished_timestamp_text'] = current_pipeline_timestamp()
        save_yaml_document(current_run_root/'pipeline.yaml', current_pipeline_values)
