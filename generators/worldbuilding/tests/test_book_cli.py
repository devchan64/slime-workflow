"""터미널 지시 등록과 직접 실행의 작업 기록·입출력 계약을 검증한다."""
import fcntl
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import worldbuilding
from generators.worldbuilding.book_cli import parse_book_arguments,execute_book_arguments,run_book_cli
from generators.worldbuilding.documents import save_yaml_document,load_yaml_document


class BookCommandTests(unittest.TestCase):
    def setUp(self):
        self.current_temp_handle=tempfile.TemporaryDirectory()
        self.current_source_root=Path(self.current_temp_handle.name)/'docs'
        (self.current_source_root/'world').mkdir(parents=True)
        (self.current_source_root/'world/README.md').write_text('# 항구\n')
        self.current_private_root=Path(self.current_temp_handle.name)/'state'
        self.current_private_root.mkdir()
        self.current_config_path=Path(self.current_temp_handle.name)/'config.yaml'
        save_yaml_document(self.current_config_path,{'workspace_schema_version':1,'source_document_root':str(self.current_source_root),'private_state_root':str(self.current_private_root),'allowed_write_roots':['world'],'required_source_paths':['world/README.md'],'protected_document_paths':['world/README.md'],'managed_catalog_path':''})
        self.current_base_arguments=['--config',str(self.current_config_path)]
        self.previous_log_path=worldbuilding.CURRENT_LOG_PATH
        worldbuilding.CURRENT_LOG_PATH=None

    def tearDown(self):
        worldbuilding.CURRENT_LOG_PATH=self.previous_log_path
        self.current_temp_handle.cleanup()

    def test_submits_stdin_instruction_and_queries_persistent_status(self):
        current_lock_path=self.current_private_root/'manager.lock'
        with current_lock_path.open('w') as current_lock_stream:
            fcntl.flock(current_lock_stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with patch('sys.stdin',io.StringIO('원문을 보존하여 목차를 정리한다.')):
                current_task_values=execute_book_arguments(parse_book_arguments(self.current_base_arguments+['edit','--collection','world','--instruction-file','-','--submit']))
        current_run_root=self.current_private_root/'jobs'/current_task_values['workflow_task_id']
        self.assertEqual(load_yaml_document(current_run_root/'request.yaml')['requested_instruction_text'],'원문을 보존하여 목차를 정리한다.')
        self.assertEqual(execute_book_arguments(parse_book_arguments(self.current_base_arguments+['status','--task',current_run_root.name]))['current_stage_name'],'queued')
        with self.assertRaises(ValueError):
            execute_book_arguments(parse_book_arguments(self.current_base_arguments+['result','--task',current_run_root.name]))

    def test_rejects_submit_without_manager_and_path_escape(self):
        with self.assertRaisesRegex(ValueError,'관리도구'):
            execute_book_arguments(parse_book_arguments(self.current_base_arguments+['edit','--collection','world','--instruction','도서를 정리한다.','--submit']))
        self.assertFalse((self.current_private_root/'jobs').exists())
        with self.assertRaises(ValueError):
            execute_book_arguments(parse_book_arguments(self.current_base_arguments+['status','--task','../../secret']))

    def test_direct_failure_is_recorded_outside_manager_queue(self):
        with patch('generators.worldbuilding.book_automation.execute_automated_book',side_effect=ValueError('모델 실패')):
            with self.assertRaisesRegex(ValueError,'모델 실패'):
                execute_book_arguments(parse_book_arguments(self.current_base_arguments+['edit','--collection','world','--instruction','도서를 정리한다.']))
        current_status_path=next((self.current_private_root/'book-cli-jobs').glob('*/status.yaml'))
        self.assertEqual(load_yaml_document(current_status_path)['current_stage_name'],'failed')
        self.assertFalse((self.current_private_root/'jobs').exists())

    def test_stdout_is_json_and_errors_exit_nonzero(self):
        current_output_stream=io.StringIO()
        with patch('sys.stdout',current_output_stream):
            run_book_cli(self.current_base_arguments+['list'])
        self.assertEqual(len(json.loads(current_output_stream.getvalue())['collection_entries']),2)
        current_output_stream=io.StringIO()
        with patch('sys.stdout',current_output_stream),patch('sys.stderr',io.StringIO()),self.assertRaises(SystemExit) as current_exit_error:
            run_book_cli(self.current_base_arguments+['status','--task','invalid'])
        self.assertEqual(current_exit_error.exception.code,1)
        self.assertIn('failure_reason_text',json.loads(current_output_stream.getvalue()))
