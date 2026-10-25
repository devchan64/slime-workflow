"""MR 산출물의 이력 호환과 준비 실패 계약을 격리 검증한다."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from generators.music.heartmula.separation import prepare_separation_model, DEMUCS_CHECKPOINT_NAME
from tools.review.domains.music.generation import MusicGenerationManager
from tools.review.common.gradio_audio_results import render_audio_generation_result


class HeartmulaSeparationTests(unittest.TestCase):
    def test_missing_checkpoint_fails_without_download(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            with self.assertRaises(FileNotFoundError):
                prepare_separation_model(Path(current_temp_directory), False)

    def test_corrupted_checkpoint_rejected_before_loading(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_model_root = Path(current_temp_directory)
            (current_model_root/'demucs').mkdir()
            (current_model_root/'demucs'/DEMUCS_CHECKPOINT_NAME).write_bytes(b'bad checkpoint')
            with self.assertRaisesRegex(ValueError, '해시 불일치'):
                prepare_separation_model(current_model_root, False)

    def test_completed_stems_and_legacy_result_share_history(self):
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_job_root = Path(current_temp_directory)/'2026-10-25_00-00-00-12345678'
            current_job_root.mkdir()
            (current_job_root/'status.json').write_text(json.dumps({'status':'completed'}))
            current_result_record = {'format':'wav','attempt':'a'*32,'separation':{'model_id':'demucs/htdemucs'}}
            (current_job_root/'result.json').write_text(json.dumps(current_result_record))
            current_music_manager = MusicGenerationManager('music-heartmula')
            current_status_record = current_music_manager.read_music_status(current_job_root,False)
            current_player_markup = render_audio_generation_result(current_job_root.name,current_status_record,'')
            self.assertEqual(current_player_markup.count('<audio '),3)
            self.assertIn('/mr.wav',current_status_record['audio_stems']['mr'])
            self.assertIn('/music.wav',current_status_record['audio'])
            del current_result_record['separation']
            (current_job_root/'result.json').write_text(json.dumps(current_result_record))
            current_status_record = current_music_manager.read_music_status(current_job_root,False)
            self.assertNotIn('audio_stems',current_status_record)
            self.assertEqual(render_audio_generation_result(current_job_root.name,current_status_record,'').count('<audio '),1)
