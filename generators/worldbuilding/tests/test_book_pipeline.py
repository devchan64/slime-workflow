"""전체 도서 실행·실패 중단·단계 기록 조회를 검증한다."""
import contextlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime
import worldbuilding
from generators.worldbuilding.book_automation import run_automated_book
from generators.worldbuilding.book_job_records import list_book_jobs, read_book_job, read_book_record
from generators.worldbuilding.documents import load_yaml_document, save_yaml_document
from generators.worldbuilding.jobs import register_document_job


class BookPipelineTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, worldbuilding, 'CURRENT_LOG_PATH', worldbuilding.CURRENT_LOG_PATH)
        self.current_temp_handle = tempfile.TemporaryDirectory()
        self.addCleanup(self.current_temp_handle.cleanup)
        self.current_workspace_root = Path(self.current_temp_handle.name)
        self.current_source_root = self.current_workspace_root/'docs'
        (self.current_source_root/'world').mkdir(parents=True)
        (self.current_source_root/'world/README.md').write_text('# 합성 도시\n\n도시의 소개.\n\n## 길드\n\n길드의 설명.\n')
        self.current_config_values = {'source_document_root': str(self.current_source_root), 'private_state_root': str(self.current_workspace_root/'state'), 'protected_document_paths': [], 'allowed_write_roots': ['world'], 'managed_catalog_path': ''}
        self.current_request_values = {'collection_id': 'world', 'source_directory_paths': ['world'], 'book_title_text': '세계관', 'requested_instruction_text': '내용을 보존하고 도서를 정리한다.', 'task_kind_name': 'book-edit', 'book_edit_stage_name': 'all-stages'}
        self.current_run_root = register_document_job(self.current_config_values, self.current_request_values)
        self.current_model_payloads = []

    def request_model_response(self, current_endpoint_path, current_request_body):
        if current_endpoint_path=='/apply-template':
            return {'prompt': 'test prompt'}
        if current_endpoint_path=='/tokenize':
            return {'tokens': [1, 2, 3]}
        current_payload_values = json.loads(current_request_body['messages'][1]['content'])
        self.current_model_payloads.append(current_payload_values)
        if 'documents' in current_payload_values:
            current_result_values = {'document_summaries': [{'document_path': 'world/README.md', 'summary_text': '합성 도시와 길드', 'purpose_text': '기초 설정', 'topic_group': '도시'}]}
        else:
            current_result_values = {'chapter_titles': ['도시와 길드']}
        return {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(current_result_values, ensure_ascii=False)}}]}

    def run_mocked_pipeline(self, current_model_request=None):
        with patch.object(worldbuilding, 'lock_gpu_runtime', contextlib.nullcontext), patch.object(runtime, 'start_managed_server', lambda *current_argument_values: contextlib.nullcontext()), patch.object(runtime, 'request_local_model', current_model_request or self.request_model_response):
            run_automated_book(self.current_config_values, self.current_run_root)

    def test_runs_all_stages_once_and_exposes_records(self):
        self.run_mocked_pipeline()
        current_pipeline_values = load_yaml_document(self.current_run_root/'pipeline.yaml')
        self.assertEqual([current_stage_entry['current_stage_name'] for current_stage_entry in current_pipeline_values['stage_entries']], ['completed']*4)
        self.assertTrue(all(current_stage_entry['started_timestamp_text'] and current_stage_entry['finished_timestamp_text'] for current_stage_entry in current_pipeline_values['stage_entries']))
        self.assertTrue(any('document_summaries' in current_payload_values for current_payload_values in self.current_model_payloads))
        current_last_root = Path(current_pipeline_values['stage_entries'][-1]['run_directory'])
        self.assertTrue((current_last_root/'completed-book/README.md').is_file())
        current_record_values = read_book_job(self.current_run_root.parents[1], self.current_run_root.name, True)
        self.assertEqual(current_record_values['current_stage_name'], 'completed')
        self.assertEqual(len(current_record_values['stage_entries']), 4)
        self.assertTrue(any(current_artifact_entry['relative_path'].endswith('document-summary-0001.yaml') for current_artifact_entry in current_record_values['artifacts']))
        current_input_values = load_yaml_document(current_last_root/'stage-input.yaml')
        self.assertTrue(current_input_values['previous_result_path'].endswith('03-document-reconstruction/book-result.yaml'))
        self.assertEqual(load_yaml_document(self.current_run_root/'book-result.yaml')['book_edit_stage_name'], 'all-stages')
        self.assertEqual(list_book_jobs(self.current_run_root.parents[1], 'world')['active_task_identifiers'], [])

    def test_failure_preserves_completed_stage_and_skips_remaining_stages(self):
        def fail_outline_request(current_endpoint_path, current_request_body):
            if current_endpoint_path=='/v1/chat/completions' and 'document_summaries' in json.loads(current_request_body['messages'][1]['content']):
                raise RuntimeError('합성 목차 실패')
            return self.request_model_response(current_endpoint_path, current_request_body)
        with self.assertRaisesRegex(RuntimeError, '목차 실패'):
            self.run_mocked_pipeline(fail_outline_request)
        current_record_values = read_book_job(self.current_run_root.parents[1], self.current_run_root.name, True)
        self.assertEqual(current_record_values['current_stage_name'], 'failed')
        self.assertEqual([current_stage_entry['current_stage_name'] for current_stage_entry in current_record_values['stage_entries']], ['completed', 'failed', 'skipped', 'skipped'])
        self.assertTrue((self.current_run_root/'stages/01-document-summary/book-result.yaml').is_file())
        self.assertFalse((self.current_run_root/'stages/03-document-reconstruction').exists())
        self.assertIn('합성 목차 실패', read_book_record(self.current_run_root.parents[1], self.current_run_root.name, 'stages/02-table-of-contents/execution.log')['content_text'])

    def test_rejects_traversal_symlinks_and_nonrecord_artifacts(self):
        (self.current_run_root/'unsafe.yaml').symlink_to(self.current_source_root/'world/README.md')
        (self.current_run_root/'code.py').write_text('private code')
        for current_bad_path in ('../request.yaml', '/etc/passwd', 'unsafe.yaml', 'code.py'):
            with self.assertRaises(ValueError):
                read_book_record(self.current_run_root.parents[1], self.current_run_root.name, current_bad_path)
        with self.assertRaises(ValueError):
            read_book_job(self.current_run_root.parents[1], '../escape')

    def test_records_interrupted_stage_after_manager_restart(self):
        current_pipeline_values = load_yaml_document(self.current_run_root/'pipeline.yaml')
        current_pipeline_values['stage_entries'][0]['current_stage_name'] = 'running'
        save_yaml_document(self.current_run_root/'pipeline.yaml', current_pipeline_values)
        save_yaml_document(self.current_run_root/'status.yaml', {'current_stage_name': 'failed', 'failure_reason_text': '관리도구 재시작으로 중단'})
        current_record_values = read_book_job(self.current_run_root.parents[1], self.current_run_root.name)
        self.assertEqual([current_stage_entry['current_stage_name'] for current_stage_entry in current_record_values['stage_entries']], ['failed', 'skipped', 'skipped', 'skipped'])

    def test_history_includes_direct_jobs_and_limits_large_log_reads(self):
        current_direct_root = register_document_job(self.current_config_values, {**self.current_request_values, 'book_edit_stage_name': 'document-cleanup'}, 'direct')
        (current_direct_root/'execution.log').write_text('가'*150000+'마지막 로그')
        current_history_values = list_book_jobs(self.current_run_root.parents[1], 'world')
        self.assertEqual(current_history_values['total_count'], 2)
        current_record_values = read_book_record(self.current_run_root.parents[1], current_direct_root.name, 'execution.log')
        self.assertTrue(current_record_values['truncated_flag'])
        self.assertTrue(current_record_values['content_text'].endswith('마지막 로그'))

    def test_source_change_stops_before_next_stage(self):
        from generators.worldbuilding.book_automation import execute_automated_book
        def change_source_after_summary(current_config_values, current_stage_root):
            execute_automated_book(current_config_values, current_stage_root)
            if current_stage_root.name=='01-document-summary':
                (self.current_source_root/'world/README.md').write_text('# 변경된 원본\n')
        with patch('generators.worldbuilding.book_automation.execute_automated_book', side_effect=change_source_after_summary):
            with self.assertRaisesRegex(ValueError, '원본이 변경'):
                self.run_mocked_pipeline()
        current_pipeline_values=load_yaml_document(self.current_run_root/'pipeline.yaml')
        self.assertEqual([current_stage_entry['current_stage_name'] for current_stage_entry in current_pipeline_values['stage_entries']], ['failed','skipped','skipped','skipped'])
        self.assertFalse((self.current_run_root/'stages/02-table-of-contents').exists())

    def test_history_paginates_without_losing_old_runs(self):
        for current_job_number in range(21):
            register_document_job(self.current_config_values, self.current_request_values)
        current_first_page=list_book_jobs(self.current_run_root.parents[1], 'world')
        current_next_page=list_book_jobs(self.current_run_root.parents[1], 'world', 20)
        self.assertEqual(current_first_page['total_count'], 22)
        self.assertEqual(len(current_first_page['job_entries']), 20)
        self.assertEqual(len(current_next_page['job_entries']), 2)
        self.assertFalse({current_job_entry['workflow_task_id'] for current_job_entry in current_first_page['job_entries']} & {current_job_entry['workflow_task_id'] for current_job_entry in current_next_page['job_entries']})
