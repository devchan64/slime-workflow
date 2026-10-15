"""두 음악 생성기의 폐기 경계·파일 삭제·UI 갱신 계약을 격리 검증한다."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from generators.music.contracts import MUSIC_SERVICE_NAMES, resolve_music_profile
from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, resolve_management_command
from tools.review.common.generation_records import write_record_atomically
from tools.review.domains.music.generation import MusicGenerationManager


class MusicManagementAuditTests(unittest.TestCase):
    def test_retired_model_cannot_return_from_cached_menu(self):
        from tools.review.ui.gradio.management_menu_app import load_manager_page_records
        self.assertEqual(MUSIC_SERVICE_NAMES,('music-ace-step','music-minimax'))
        self.assertNotIn('music-stable-audio',MANAGEMENT_SERVICE_COMMANDS)
        with self.assertRaises(ValueError):
            resolve_management_command('music-stable-audio','generate',{})
        with self.assertRaises(ValueError):
            resolve_music_profile('music-stable-audio')
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_menu_path=Path(current_temp_directory)/'menu.json'
            current_menu_path.write_text(json.dumps({'pages':[{'id':'music-stable-audio','label':'폐기','path':'/management/frame/music-stable-audio/','category':'music-generation','description':'이전 메뉴'}]}))
            current_music_records=[current_page_record['id'] for current_page_record in load_manager_page_records(current_menu_path) if current_page_record['category']=='music-generation']
            self.assertEqual(current_music_records,list(MUSIC_SERVICE_NAMES))

    def test_both_services_delete_files_and_reset_hidden_jobs(self):
        for current_service_name in MUSIC_SERVICE_NAMES:
            with self.subTest(service=current_service_name),tempfile.TemporaryDirectory() as current_temp_directory,patch('tools.review.domains.music.generation.launch_gpu_process'):
                current_test_root=Path(current_temp_directory)
                current_music_service=MusicGenerationManager(current_service_name)
                current_music_service.job_storage_root=current_test_root/'jobs'
                current_music_service.history_storage_root=current_test_root/'history'
                current_music_service.runtime_python_path=current_test_root/'python'
                current_music_service.runtime_python_path.touch()
                current_protected_path=current_test_root/'external-source.wav'
                current_protected_path.write_bytes(b'protected')
                current_job_paths=[]
                for current_job_number in range(3):
                    current_job_record=current_music_service.create_music_job({'prompt':'flute','seed':current_job_number})
                    current_job_root=current_music_service.resolve_music_job(current_job_record['id'])
                    write_record_atomically(current_job_root/'status.json',{'status':'completed'})
                    for current_relative_name in ('input.wav','intermediate.bin','attempts/first/music.wav','attempts/first/metrics.json','attempts/second/request.json','attempts/second/worker.log'):
                        current_artifact_path=current_job_root/current_relative_name
                        current_artifact_path.parent.mkdir(parents=True,exist_ok=True)
                        current_artifact_path.write_bytes(b'test')
                    current_job_paths.append(current_job_root)
                current_expected_bytes=sum(current_artifact_path.stat().st_size for current_artifact_path in current_job_paths[0].rglob('*') if current_artifact_path.is_file())+(current_music_service.history_storage_root/(current_job_paths[0].name+'.json')).stat().st_size
                current_delete_result=current_music_service.execute_music_command('history-delete',{'id':current_job_paths[0].name})
                self.assertEqual(current_delete_result['deleted_jobs'],1)
                self.assertEqual(current_delete_result['deleted_bytes'],current_expected_bytes)
                self.assertFalse(current_job_paths[0].exists())
                self.assertTrue(current_job_paths[1].exists())
                (current_music_service.history_storage_root/(current_job_paths[2].name+'.json')).unlink()
                self.assertEqual(current_music_service.execute_music_command('history-reset-preview',{})['job_count'],2)
                current_job_paths[1].joinpath('external-link').symlink_to(current_protected_path)
                with self.assertRaises(ValueError):
                    current_music_service.execute_music_command('history-reset',{'action':'reset'})
                self.assertTrue(current_job_paths[2].exists())
                current_job_paths[1].joinpath('external-link').unlink()
                for current_live_state in ('queued','running'):
                    write_record_atomically(current_job_paths[1]/'status.json',{'status':current_live_state})
                    self.assertFalse(current_music_service.execute_music_command('history-reset-preview',{})['can_reset'])
                    with self.assertRaises(ValueError):
                        current_music_service.execute_music_command('history-delete',{'id':current_job_paths[1].name})
                    with self.assertRaises(ValueError):
                        current_music_service.execute_music_command('history-reset',{'action':'reset'})
                write_record_atomically(current_job_paths[1]/'status.json',{'status':'completed'})
                current_reset_result=current_music_service.execute_music_command('history-reset',{'action':'reset'})
                self.assertEqual(current_reset_result['deleted_jobs'],2)
                self.assertGreater(current_reset_result['deleted_bytes'],0)
                self.assertFalse(any(current_job_path.exists() for current_job_path in current_job_paths))
                self.assertEqual(current_protected_path.read_bytes(),b'protected')
                self.assertEqual(current_music_service.execute_music_command('history',{})['records'],[])

    def test_deleted_active_record_clears_preview_without_hiding_existing_errors(self):
        from tools.review.ui.gradio.music_app import build_music_interface
        for current_service_name in MUSIC_SERVICE_NAMES:
            current_interface_blocks=build_music_interface(current_service_name,'http://127.0.0.1:9988')
            current_refresh_callback=next(current_callback.fn for current_callback in current_interface_blocks.fns.values() if current_callback.fn and current_callback.fn.__name__=='refresh_music_result')
            def execute_deleted_command(current_service_value,current_command_value,current_payload_value):
                if current_command_value=='status':raise ValueError('작업 경로가 없습니다')
                return {'records':[]}
            with patch('tools.review.ui.gradio.music_app.execute_remote_management_command',side_effect=execute_deleted_command):
                current_update_values=current_refresh_callback('removed',True,'old.wav')
                self.assertEqual(current_update_values[-1],'')
                self.assertIn('삭제',current_update_values[0])
                self.assertNotIn('old.wav',current_update_values[1])
            with patch('tools.review.ui.gradio.music_app.execute_remote_management_command',side_effect=[ValueError('손상된 기록'),{'records':[{'id':'existing'}]}]):
                with self.assertRaisesRegex(ValueError,'손상된 기록'):
                    current_refresh_callback('existing',True,'')
