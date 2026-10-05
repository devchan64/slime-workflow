"""순환 생성기의 게이트웨이·설정 분리 검증."""
import unittest
from tools.review.domains.image.qwen_circular_generation import QwenCircularGenerationManager
from tools.review.domains.image.qwen_21_generation import validate_qwen_plain_request
from generators.image.qwen_21_circular import CIRCULAR_DEFAULT_PROMPT, CIRCULAR_VAE_CONFIGURATION
from tools.review.common.management_gateway import MANAGEMENT_SERVICE_ROUTES, MANAGEMENT_SERVICE_COMMANDS

class CircularGenerationTests(unittest.TestCase):
    def test_circular_request_isolation(self):
        current_input_record = {'action':'generate','prompt':CIRCULAR_DEFAULT_PROMPT,'images':[], 'tag':'', 'width':768,'height':768,'steps':40,'seed':10107}
        current_service_manager = QwenCircularGenerationManager()
        current_output_record = current_service_manager.validate_generation_request(current_input_record)
        self.assertEqual(current_output_record['circular_vae'], {**CIRCULAR_VAE_CONFIGURATION, 'baseline_decode': False})
        self.assertEqual(current_output_record['prompt'], CIRCULAR_DEFAULT_PROMPT + ' Top view. Repeat pattern. Close-up')
        self.assertNotIn('circular_vae', validate_qwen_plain_request(current_input_record))
        self.assertEqual(current_service_manager.route_prefix_value, MANAGEMENT_SERVICE_ROUTES['qwen-21-circular'])
        self.assertIn('resume', MANAGEMENT_SERVICE_COMMANDS['qwen-21-circular'])
        self.assertEqual(current_service_manager.job_storage_root.name, 'qwen-image-21-circular')

    def test_history_renderer_contract_and_partial_results(self):
        from tools.review.ui.gradio.qwen_2511_app import render_circular_comparison
        completed_result_html = render_circular_comparison('example-id', {
            'image':'/jobs/example-id/result.png',
            'baseline':'/jobs/example-id/baseline.png',
            'baseline-preview':'/jobs/example-id/baseline-preview.png',
        }, 'http://localhost:8770')
        for expected_image_name in ('result.png','tiled-preview.png','baseline.png','baseline-preview.png'):
            self.assertIn(expected_image_name, completed_result_html)
        partial_result_html = render_circular_comparison('example-id', {
            'status':'failed', 'baseline':'/jobs/example-id/baseline.png',
        }, 'http://localhost:8770')
        self.assertIn('/baseline.png', partial_result_html)
        self.assertNotIn('/baseline-preview.png', partial_result_html)
        self.assertNotIn('/tiled-preview.png', partial_result_html)
        self.assertIn('저장된 결과', render_circular_comparison('example-id', {}, 'http://localhost:8770'))

    def test_boundary_strip_coordinates(self):
        from generators.image.qwen_21_toroidal import build_toroidal_boundary
        source_index_values, height_offset_values, width_offset_values = build_toroidal_boundary(3, 4, 2)
        actual_coordinate_set = {
            (current_source_index // 4 + current_height_offset, current_source_index % 4 + current_width_offset)
            for current_source_index, current_height_offset, current_width_offset
            in zip(source_index_values, height_offset_values, width_offset_values)
        }
        expected_coordinate_set = {(current_row_index, current_column_index)
            for current_row_index in (-2, -1, 3, 4) for current_column_index in range(4)}
        expected_coordinate_set |= {(current_row_index, current_column_index)
            for current_row_index in range(3) for current_column_index in (-2, -1, 4, 5)}
        self.assertEqual(actual_coordinate_set, expected_coordinate_set)
        self.assertEqual(len(source_index_values), len(expected_coordinate_set))
        self.assertEqual(build_toroidal_boundary(3, 4), tuple(current_values[:14] for current_values in (source_index_values, height_offset_values, width_offset_values)))
        with self.assertRaises(ValueError):
            build_toroidal_boundary(3, 4, 4)

    def test_corner_reference_coordinates(self):
        from generators.image.qwen_21_toroidal import build_toroidal_boundary
        original_boundary_values = build_toroidal_boundary(3, 4)
        extended_boundary_values = build_toroidal_boundary(3, 4, 1, True)
        self.assertEqual(tuple(current_values[:-4] for current_values in extended_boundary_values), original_boundary_values)
        actual_corner_coordinates = {
            (current_source_index // 4 + current_height_offset, current_source_index % 4 + current_width_offset)
            for current_source_index, current_height_offset, current_width_offset
            in zip(*(current_values[-4:] for current_values in extended_boundary_values))
        }
        self.assertEqual(actual_corner_coordinates, {(-1, -1), (-1, 4), (3, -1), (3, 4)})

    def test_selectable_circular_radius(self):
        current_service_manager = QwenCircularGenerationManager()
        current_request_values = dict(action='generate', prompt=CIRCULAR_DEFAULT_PROMPT, images=[], tag='', width=512, height=512, steps=40, seed=10107)
        for current_radius_value in (8, 12, 16):
            current_output_values = current_service_manager.validate_generation_request({**current_request_values, 'circular_radius': current_radius_value})
            self.assertEqual(current_output_values['circular_vae']['boundary_radius'], current_radius_value)
            self.assertEqual(current_output_values['circular_vae']['vertical_boundary_radius'], current_radius_value)
        for invalid_radius_value in (4, 24, True, '8', 8.0):
            with self.assertRaises(ValueError):
                current_service_manager.validate_generation_request({**current_request_values, 'circular_radius': invalid_radius_value})

    def test_soft_shading_prompt_contract(self):
        from generators.image.qwen_21_circular import CIRCULAR_SOFT_SHADING_PROMPT
        current_service_manager = QwenCircularGenerationManager()
        current_request_values = dict(action='generate', prompt='Grass and flowers.', images=[], tag='', width=512, height=512, steps=40, seed=10107)
        for soft_shading_enabled in (False, True):
            current_output_values=current_service_manager.validate_generation_request({**current_request_values, 'soft_shading':soft_shading_enabled, 'pattern_view':False})
            expected_prompt_text=current_request_values['prompt'] + (' ' + CIRCULAR_SOFT_SHADING_PROMPT if soft_shading_enabled else '')
            self.assertEqual(current_output_values['prompt'],expected_prompt_text)
            self.assertEqual(current_output_values['user_prompt'],current_request_values['prompt'])
            self.assertEqual(current_output_values['qwen21']['prompt_word_count'],len(expected_prompt_text.split()))

    def test_pattern_view_prompt_toggle(self):
        current_service_manager=QwenCircularGenerationManager()
        current_request_values=dict(action='generate',prompt='Grass.',images=[],tag='',width=512,height=512,steps=40,seed=10107)
        for pattern_view_enabled in (False,True):
            current_output_values=current_service_manager.validate_generation_request({**current_request_values,'pattern_view':pattern_view_enabled,'soft_shading':True})
            expected_prompt_text='Grass.' + (' Top view. Repeat pattern. Close-up' if pattern_view_enabled else '') + ' Illustration with soft shading.'
            self.assertEqual(current_output_values['prompt'],expected_prompt_text)
            self.assertEqual(current_output_values['pattern_view'],pattern_view_enabled)
            self.assertEqual(current_output_values['qwen21']['prompt_word_count'],len(expected_prompt_text.split()))

    def test_optional_baseline_decode(self):
        current_service_manager=QwenCircularGenerationManager()
        current_request_values=dict(action='generate',prompt='Grass.',images=[],tag='',width=512,height=512,steps=40,seed=10107)
        for baseline_decode_enabled in (False, True):
            current_output_values=current_service_manager.validate_generation_request({**current_request_values,'baseline_decode':baseline_decode_enabled})
            self.assertEqual(current_output_values['circular_vae']['baseline_decode'],baseline_decode_enabled)
        with self.assertRaises(ValueError):
            current_service_manager.validate_generation_request({**current_request_values,'baseline_decode':'false'})
