"""AnyPose 폐기 후 실행 차단과 공유 기능 보존을 검증한다."""
import unittest
from unittest.mock import patch
from tools.review.domains.character_animation import character_animation_jobs
from generators.animation.qwen_pose import anypose
from generators.animation.qwen_pose.runtime import execute_pose_generation


class AnyPoseRetirementTests(unittest.TestCase):
    def test_retired_screen_is_not_registered(self):
        import json
        import tempfile
        from pathlib import Path
        from tools.review.ui.gradio.management_menu_app import load_manager_page_records
        from tools.review.build_animation_tools import build_animation_tools
        self.assertNotIn('character-animation', [current_record['id'] for current_record in build_animation_tools(None)])
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_source_path = Path(current_temporary_directory) / 'menu.json'
            current_source_path.write_text(json.dumps({'pages': [{'id': 'character-animation', 'label': '과거 생성기', 'path': '/character-animation/', 'category': 'animation-tool', 'description': '이전 화면'}]}))
            self.assertNotIn('character-animation', [current_record['id'] for current_record in load_manager_page_records(current_source_path)])

    def test_generation_commands_fail_before_writes(self):
        with patch.object(character_animation_jobs, 'prepare_animation_request') as current_prepare_mock:
            for current_command_name in ('generate', 'resume', 'record-alpha-vnccs'):
                with self.assertRaisesRegex(ValueError, '폐기'):
                    character_animation_jobs.execute_animation_command(current_command_name, {})
            current_prepare_mock.assert_not_called()

    def test_anypose_prepare_and_direct_runtime_rejected(self):
        with self.assertRaisesRegex(ValueError, '폐기'):
            anypose.prepare_anypose_models()
        with self.assertRaisesRegex(ValueError, '폐기'):
            anypose.validate_adapter_files()
        with self.assertRaisesRegex(ValueError, '폐기'):
            execute_pose_generation(trial_output_root='/unused', prompt_text_value='test', character_image_path='/missing', pose_reference_path='/missing', pose_reference_kind='rig', enable_anypose_adapter=True)

    def test_standalone_lightning_does_not_require_anypose(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_adapter_path = Path(current_temporary_directory) / 'lightning.safetensors'
            current_adapter_path.write_bytes(b'weight')
            current_adapter_records = ({'name': 'anypose_base'}, {'name': 'lightning', 'size': 6, 'sha256': anypose.calculate_file_digest(current_adapter_path)})
            with patch.object(anypose, 'FIXED_ADAPTER_RECORDS', current_adapter_records), patch.object(anypose, 'resolve_adapter_path', return_value=current_adapter_path) as current_resolve_mock:
                current_result_records = anypose.validate_adapter_files(include_anypose_adapter=False)
                self.assertEqual([current_record['name'] for current_record in current_result_records], ['lightning'])
                self.assertEqual(current_resolve_mock.call_count, 1)
