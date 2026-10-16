"""GPU 없이 프롬프트 계약·참조 순서·입력 거부를 검증한다."""
import tempfile
from pathlib import Path
import unittest
import yaml
from generators.animation.qwen_pose import load_pose_prompt, execute_pose_generation


class QwenPoseContractTests(unittest.TestCase):
    def test_reference_order_and_options(self):
        with tempfile.TemporaryDirectory() as temporary_root_path:
            profile_output_path = Path(temporary_root_path)/'profile.yaml'
            profile_output_values = {'id': 'test-profile', 'version': 1, 'templates': {
                reference_kind_value: {'pose_prompt': 'character {character_image_index} pose {pose_image_index}', 'optional_prompt': 'optional appearance', 'validation_status': 'unverified'}
                for reference_kind_value in ('rig', 'openpose')}}
            profile_output_path.write_text(yaml.safe_dump(profile_output_values))
            for reference_kind_value in ('rig', 'openpose'):
                for reference_order_value, expected_prompt_value in [('standing-first', 'character 1 pose 2'), ('pose-first', 'character 2 pose 1')]:
                    for include_optional_value in (True, False):
                        with self.subTest(kind=reference_kind_value, order=reference_order_value, optional=include_optional_value):
                            rendered_prompt_text, prompt_source_record = load_pose_prompt(profile_output_path, reference_kind_value, reference_order_value, include_optional_prompt=include_optional_value)
                            self.assertEqual(rendered_prompt_text, expected_prompt_value + (' optional appearance' if include_optional_value else ''))
                            self.assertEqual(prompt_source_record['optional_prompt_enabled'], include_optional_value)

    def test_invalid_profile_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_root_path:
            profile_output_path = Path(temporary_root_path)/'profile.yaml'
            for invalid_profile_text in ('id: a\nid: b\n', 'id: a\nversion: true\ntemplates: {}\n', 'id: a\nversion: 1\ntemplates: {}\nextra: 1\n'):
                with self.subTest(profile=invalid_profile_text):
                    profile_output_path.write_text(invalid_profile_text)
                    with self.assertRaises(ValueError):
                        load_pose_prompt(profile_output_path, 'rig')

    def test_output_boundary_before_gpu(self):
        with self.assertRaisesRegex(ValueError, '.tmp'):
            execute_pose_generation(trial_output_root='/tmp/invalid-qwen-output', prompt_text_value='test', character_image_path='/missing.png', pose_reference_path='/missing.png', pose_reference_kind='rig')

    def test_anypose_contract_before_gpu(self):
        for reference_order_value, inference_steps_value in [('pose-first', 4), ('standing-first', 10)]:
            with self.subTest(order=reference_order_value, steps=inference_steps_value):
                with self.assertRaisesRegex(ValueError, 'AnyPose'):
                    execute_pose_generation(trial_output_root='/tmp/unused', prompt_text_value='test', character_image_path='/missing.png', pose_reference_path='/missing.png', pose_reference_kind='rig', selected_reference_order=reference_order_value, selected_inference_steps=inference_steps_value, enable_anypose_adapter=True)

    def test_anypose_without_lightning_contract(self):
        with self.assertRaisesRegex(ValueError, '폐기'):
            execute_pose_generation(trial_output_root='/tmp/unused', prompt_text_value='test', character_image_path='/missing.png', pose_reference_path='/missing.png', pose_reference_kind='rig', selected_inference_steps=10, enable_anypose_adapter=True, enable_lightning_adapter=False)
        with self.assertRaisesRegex(ValueError, 'AnyPose'):
            execute_pose_generation(trial_output_root='/tmp/unused', prompt_text_value='test', character_image_path='/missing.png', pose_reference_path='/missing.png', pose_reference_kind='rig', selected_inference_steps=4, enable_anypose_adapter=True, enable_lightning_adapter=False)

    def test_retired_adapter_entrypoints_reject(self):
        from generators.animation.qwen_pose import anypose
        with self.assertRaisesRegex(ValueError, '폐기'):
            anypose.validate_adapter_files()
        with self.assertRaisesRegex(ValueError, '폐기'):
            anypose.validate_adapter_files(include_lightning_adapter=False)
        with self.assertRaisesRegex(ValueError, '폐기'):
            anypose.prepare_anypose_models()

    def test_anypose_strength_validation(self):
        for invalid_strength_value in (-0.1, 1.6, float('nan'), float('inf'), True, '1'):
            for strength_field_name in ('selected_base_strength', 'selected_helper_strength'):
                with self.subTest(value=invalid_strength_value, field=strength_field_name):
                    with self.assertRaisesRegex(ValueError, 'strength'):
                        execute_pose_generation(trial_output_root='/tmp/unused', prompt_text_value='test', character_image_path='/missing.png', pose_reference_path='/missing.png', pose_reference_kind='rig', selected_inference_steps=10, enable_anypose_adapter=False, enable_lightning_adapter=False, **{strength_field_name: invalid_strength_value})

    def test_invalid_kind_before_gpu(self):
        with self.assertRaisesRegex(ValueError, 'pose kind'):
            execute_pose_generation(trial_output_root='/tmp/unused', prompt_text_value='test', character_image_path='/missing.png', pose_reference_path='/missing.png', pose_reference_kind='guessed')


if __name__ == '__main__':
    unittest.main()
