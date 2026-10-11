"""복장 분리의 결과·이력 재생기 및 기존 결과 URL 계약."""
import json
import unittest
from tools.review.ui.gradio.animation_separation_app import build_separation_interface, build_separation_preview


class SeparationPreviewGradioTests(unittest.TestCase):
    def test_result_payload_preserves_existing_job_files(self):
        current_job_identifier = '2026-10-11_12-00-00-1234abcd'
        current_result_payload = json.loads(build_separation_preview('http://127.0.0.1:8765', current_job_identifier))
        self.assertEqual(current_result_payload['base'], f'http://127.0.0.1:8765/animation-separation/jobs/{current_job_identifier}/')
        self.assertEqual(build_separation_preview('http://127.0.0.1:8765', ''), '')
        with self.assertRaisesRegex(ValueError, 'ID'):
            build_separation_preview('http://127.0.0.1:8765', '../invalid')

    def test_result_and_history_have_independent_native_players(self):
        current_configuration_record = build_separation_interface('http://127.0.0.1:8765').config
        current_player_components = [current_component_record for current_component_record in current_configuration_record['components'] if current_component_record['props'].get('elem_id') in ('separationResultPlayer', 'separationHistoryPlayer')]
        self.assertEqual(len(current_player_components), 2)
        for current_component_record in current_player_components:
            self.assertIn('data-player-images', current_component_record['props']['html_template'])
            self.assertIn("watch('value',loadPreviewResult)", current_component_record['props']['js_on_load'])
        self.assertNotIn('<iframe', str(current_configuration_record))
        self.assertNotIn('contentWindow', str(current_configuration_record))
