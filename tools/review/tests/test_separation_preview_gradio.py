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

    def test_resume_cancel_rechecks_current_identifier_before_readiness_event(self):
        current_interface_blocks = build_separation_interface('http://127.0.0.1:8765')
        current_cancel_binding = next(
            current_binding for current_binding in current_interface_blocks.fns.values()
            if current_binding.fn and current_binding.fn.__name__ == 'cancel_generation_confirmation'
            and len(current_binding.inputs) == 4
            and getattr(current_binding.inputs[2], 'label', None) == '조회할 생성 ID'
        )
        current_pending_record = {'inputs': ('original',), 'consumed': False}
        current_cancel_result = current_cancel_binding.fn(current_pending_record, True, 'different', 'original')
        self.assertTrue(current_pending_record['consumed'])
        self.assertFalse(current_cancel_result[2]['interactive'])
        self.assertTrue(current_cancel_binding.fn(None, True, 'original', 'original')[2]['interactive'])
        self.assertFalse(current_cancel_binding.fn(None, False, 'original', 'original')[2]['interactive'])
        self.assertFalse(current_cancel_binding.fn(None, True, '', '')[2]['interactive'])

    def test_live_progress_preserves_player_and_clears_deleted_job(self):
        from unittest.mock import patch
        from tools.review.ui.gradio import animation_separation_app
        current_interface_blocks=build_separation_interface('http://127.0.0.1:8765')
        current_refresh_binding=next(current_binding for current_binding in current_interface_blocks.fns.values() if current_binding.fn and current_binding.fn.__name__=='refresh_separation_progress')
        self.assertEqual(len(current_refresh_binding.outputs),8)
        with patch.object(animation_separation_app,'execute_separation_gateway') as current_gateway_mock:
            self.assertEqual(current_refresh_binding.fn('',True,'')[:6],({'__type__':'update'},)*6)
            self.assertEqual(current_refresh_binding.fn('typing',True,'existing')[:6],({'__type__':'update'},)*6)
            current_gateway_mock.assert_not_called()
        for current_status_name in ('running','completed','failed','cancelled'):
            with self.subTest(status=current_status_name),patch.object(animation_separation_app,'execute_separation_gateway',return_value={'status':current_status_name,'log':'최신 로그','estimate':{'remaining':12}}):
                current_output_values=current_refresh_binding.fn('existing',True,'existing')
                self.assertEqual(current_output_values[1],'최신 로그')
                self.assertEqual(current_output_values[2:6],({'__type__':'update'},)*4)
                if current_status_name=='running':self.assertIn('약 12초',current_output_values[0])
        with patch.object(animation_separation_app,'execute_separation_gateway',side_effect=[ValueError('missing'),{'records':[]}]):
            current_output_values=current_refresh_binding.fn('removed',True,'removed')
        self.assertIn('삭제',current_output_values[0])
        self.assertEqual(current_output_values[1:6],('','','','',''))

        self.assertFalse(current_output_values[6]['interactive'])
        self.assertFalse(current_output_values[7])
        current_result_binding=next(current_binding for current_binding in current_interface_blocks.fns.values() if current_binding.fn and current_binding.fn.__name__=='read_current_result')
        self.assertEqual(len(current_result_binding.outputs),7)
        with patch.object(animation_separation_app,'execute_separation_gateway',return_value={'status':'failed','resume_allowed':False}):
            current_output_values=current_result_binding.fn('existing',False)
        self.assertEqual(current_output_values[4],'existing')
        self.assertFalse(current_output_values[5]['interactive'])
        self.assertFalse(current_output_values[6])


class SeparationInputRestoreTests(unittest.TestCase):
    def test_restores_saved_reference_and_rejects_modified_or_legacy_input(self):
        import base64
        import io
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from PIL import Image
        import gradio as gr
        from tools.review.domains.image.three_reference_generation import save_three_reference_inputs
        from tools.review.ui.gradio import animation_separation_app
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_root = Path(current_directory_name)
            current_job_identifier = '2026-10-15_13-00-00-1234abcd'
            current_job_root = current_storage_root / current_job_identifier
            current_job_root.mkdir()
            current_image_buffer = io.BytesIO()
            Image.new('RGB', (32, 32), 'red').save(current_image_buffer, format='PNG')
            current_request_record = {'action':'generate','images':[base64.b64encode(current_image_buffer.getvalue()).decode()],'prompt':'Body reference.','width':512,'height':512,'seed':12,'steps':40}
            current_saved_request = save_three_reference_inputs(current_job_root, current_request_record)
            current_saved_request.update(schema_version=2, outfit_prompt='Clothes reference.')
            current_history_record = {'id':current_job_identifier,'request':current_saved_request}
            with patch.object(animation_separation_app,'SEPARATION_STORAGE_ROOT',current_storage_root):
                current_restored_values = animation_separation_app.restore_separation_inputs(current_history_record)
                self.assertEqual(current_restored_values[0].getpixel((0,0)), (255,0,0))
                self.assertEqual(current_restored_values[1:], (512,12,'Body reference.','Clothes reference.'))
                (current_job_root/'reference-1.png').write_bytes(b'changed')
                with self.assertRaisesRegex(gr.Error,'해시'):
                    animation_separation_app.restore_separation_inputs(current_history_record)
                current_saved_request['schema_version']=1
                with self.assertRaisesRegex(gr.Error,'이전 프레임'):
                    animation_separation_app.restore_separation_inputs(current_history_record)
