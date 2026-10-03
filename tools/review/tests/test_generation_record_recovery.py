"""공용 이력 조회의 재시작·삭제·화면 재생성 계약."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.review.common.generation_records import load_generation_history_records
from tools.review.build_frontend_review import clear_generated_review_files
from tools.review.domains.image.image_generation import ImageGenerationManager


class GenerationRecordRecoveryTests(unittest.TestCase):
    def test_restart_recovers_job_without_index_and_preserves_new_service(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            generation_job_identifier = '2026-10-03_12-00-00-abcdef12'
            generation_jobs_directory = temporary_root_path / 'jobs'
            generation_job_path = generation_jobs_directory / generation_job_identifier
            generation_job_path.mkdir(parents=True)
            (generation_job_path / 'request.json').write_text(json.dumps({'prompt': '잔디밭'}))
            (generation_job_path / 'status.json').write_text(json.dumps({'status': 'completed'}))
            history_directory_path = temporary_root_path / 'review' / 'future-generator'
            history_directory_path.mkdir(parents=True)
            (history_directory_path / '.reset-marker').write_text('')
            os.utime(history_directory_path / '.reset-marker', (1, 1))
            clear_generated_review_files(history_directory_path.parent)
            self.assertTrue((history_directory_path / '.reset-marker').exists())
            for restart_sequence_index in range(2):
                generation_manager_value = ImageGenerationManager()
                with patch.object(generation_manager_value, 'job_storage_root', generation_jobs_directory), patch.object(generation_manager_value, 'history_storage_path', return_value=history_directory_path):
                    history_record_values = generation_manager_value.list_generation_history()
                self.assertEqual([current_record_value['id'] for current_record_value in history_record_values], [generation_job_identifier])

    def test_deleted_and_reset_jobs_are_not_recovered(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            temporary_root_path = Path(temporary_directory_name)
            generation_job_path = temporary_root_path / 'jobs' / '2026-10-03_12-00-00-abcdef12'
            generation_job_path.mkdir(parents=True)
            (generation_job_path / 'request.json').write_text('{}')
            (generation_job_path / 'status.json').write_text('{"status":"completed"}')
            history_directory_path = temporary_root_path / 'history'
            history_directory_path.mkdir()
            deletion_marker_path = generation_job_path / '.history-deleted'
            deletion_marker_path.touch()
            self.assertEqual(load_generation_history_records(history_directory_path, generation_job_path.parent), [])
            deletion_marker_path.unlink()
            (history_directory_path / '.reset-marker').touch()
            os.utime(generation_job_path / 'request.json', (1, 1))
            self.assertEqual(load_generation_history_records(history_directory_path, generation_job_path.parent), [])
