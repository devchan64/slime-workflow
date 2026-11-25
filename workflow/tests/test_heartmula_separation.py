"""MR 산출물의 이력 호환과 준비 실패 계약을 격리 검증한다."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from generators.music.heartmula.separation import prepare_separation_model, DEMUCS_CHECKPOINT_NAME
from workflow.domains.music.generation import MusicGenerationManager
from workflow.common.audio_results import render_audio_generation_result


class HeartmulaSeparationTests(unittest.TestCase):
    def test_heartcodec_uses_independent_directory_and_rejects_ambiguity(self):
        from generators.music.heartmula.runtime import resolve_heartcodec_directory
        from workflow.common.audio_model_download import resolve_audio_receipt_file
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / '.model' / 'audio' / 'heartmula'
            old = root / 'bundle' / 'HeartCodec-oss'
            old.mkdir(parents=True)
            (old / 'config.json').write_text('{}')
            self.assertEqual(resolve_heartcodec_directory(root), old)
            new = root.parent.parent / 'heartcodec-oss'
            old.rename(new)
            self.assertEqual(resolve_heartcodec_directory(root), new)
            self.assertEqual(resolve_audio_receipt_file('music-heartmula', root, 'bundle/HeartCodec-oss/config.json'), new/'config.json')
            old.mkdir()
            with self.assertRaisesRegex(ValueError, '두 위치'):
                resolve_heartcodec_directory(root)

    def test_demucs_location_supports_existing_and_separate_layout(self):
        from generators.music.heartmula.separation import resolve_demucs_directory
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'audio' / 'heartmula'
            old = root / 'demucs'
            old.mkdir(parents=True)
            new = root.parent / 'demucs'
            self.assertEqual(resolve_demucs_directory(root), old)
            old.rename(new)
            self.assertEqual(resolve_demucs_directory(root), new)
            top = root.parent.parent / 'demucs'
            new.rename(top)
            self.assertEqual(resolve_demucs_directory(root), top)
            old.mkdir()
            with self.assertRaisesRegex(ValueError, '두 위치'):
                resolve_demucs_directory(root)

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
            current_player_markup = render_audio_generation_result(current_job_root.name,current_status_record,'http://127.0.0.1:8770')
            self.assertEqual(current_player_markup.count('<audio '),3)
            self.assertNotIn('127.0.0.1', current_player_markup)
            self.assertIn('src="/music-heartmula/jobs/', current_player_markup)
            self.assertIn('/mr.wav',current_status_record['audio_stems']['mr'])
            self.assertIn('/music.wav',current_status_record['audio'])
            current_status_record['result']['duration_seconds'] = 70.32
            current_status_record['result']['mp3_outputs'] = {current_audio_name:{'filename':current_audio_name+'.mp3'} for current_audio_name in ('music','mr','vocals')}
            current_player_markup = render_audio_generation_result(current_job_root.name,current_status_record,'')
            self.assertIn('실제 길이: 70.32초',current_player_markup)
            self.assertLess(current_player_markup.index('/music.mp3'),current_player_markup.index('/mr.wav'))
            self.assertLess(current_player_markup.index('/mr.mp3'),current_player_markup.index('/vocals.wav'))
            del current_result_record['separation']
            (current_job_root/'result.json').write_text(json.dumps(current_result_record))
            current_status_record = current_music_manager.read_music_status(current_job_root,False)
            self.assertNotIn('audio_stems',current_status_record)
            self.assertEqual(render_audio_generation_result(current_job_root.name,current_status_record,'').count('<audio '),1)
