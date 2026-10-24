"""Magenta 실험 입력과 GPU 정책 차단·MiniMax 폐기를 검증한다."""
import unittest
from generators.music.contracts import build_music_request
from tools.review.domains.music.generation import MusicGenerationManager


class MagentaGenerationTests(unittest.TestCase):
    def test_magenta_request_contract(self):
        current_request_record = build_music_request('music-magenta',{'prompt':'warm harp','duration_seconds':75,'seed':7})
        self.assertEqual(current_request_record['final_prompt'],'warm harp')
        for current_invalid_payload in ({'lyrics':'test'},{'max_new_tokens':1000},{'loop_request':True},{'duration_seconds':121}):
            with self.subTest(payload=current_invalid_payload), self.assertRaises(ValueError):
                build_music_request('music-magenta',{'prompt':'harp',**current_invalid_payload})

    def test_unverified_and_retired_execution_blocked(self):
        for current_service_name in ('music-minimax','music-magenta'):
            current_service_manager = MusicGenerationManager(current_service_name)
            for current_command_name,current_payload_record in (('generate',{'prompt':'harp'}),('prepare',{'action':'prepare'}),('resume',{'id':'2026-10-24_19-44-27-113c612c'})):
                with self.subTest(service=current_service_name,command=current_command_name), self.assertRaises(ValueError):
                    current_service_manager.execute_music_command(current_command_name,current_payload_record)
            self.assertFalse(current_service_manager.execute_music_command('model-status',{})['ready'])
