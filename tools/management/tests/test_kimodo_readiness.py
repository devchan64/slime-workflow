"""생성기 모델 준비 확인과 모델 관리 이동 계약."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import gradio as gr

from tools.management.common.gradio_model_download import build_model_readiness_controls, read_model_readiness_status


class KimodoReadinessTests(unittest.TestCase):
    def test_model_status_requires_loadable_motion_correction(self):
        from generators.kimodo.contracts import inspect_kimodo_assets
        with patch('generators.kimodo.contracts.inspect_motion_correction_runtime', return_value=False):
            current_status_record = inspect_kimodo_assets()
        self.assertFalse(current_status_record['ready'])
        self.assertIn('motion_correction', current_status_record['message'])
        self.assertIn('공식 후처리 motion_correction 실행 환경', current_status_record['missing'])

    def test_missing_postprocess_runs_official_setup_without_redownload(self):
        from generators.kimodo import prepare
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_python_path = Path(current_directory_name) / 'python'
            current_python_path.touch()
            with patch.object(prepare, 'KIMODO_ENVIRONMENT_PYTHON', current_python_path), \
                 patch.object(prepare, 'KIMODO_MODEL_ROOT', Path(current_directory_name)), \
                 patch.object(prepare, 'inspect_kimodo_assets', return_value={'missing': ['공식 후처리 motion_correction 실행 환경']}), \
                 patch.object(prepare, 'install_kimodo_official_runtime') as current_install_mock, \
                 patch.object(prepare, 'download_kimodo_pinned_assets') as current_download_mock:
                prepare.prepare_kimodo_assets()
        current_install_mock.assert_called_once()
        current_download_mock.assert_not_called()

    def test_official_setup_builds_extension_without_replacing_dependencies(self):
        from types import SimpleNamespace
        from contextlib import nullcontext
        from generators.kimodo import prepare
        with patch.object(prepare, 'prepare_kimodo_source_repository'), \
             patch('tools.management.common.management_setup.hold_shared_environment_reservation', return_value=nullcontext()), \
             patch.object(prepare, 'inspect_motion_correction_runtime', side_effect=[False, False, True]), \
             patch.object(prepare.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as current_run_mock, \
             patch.object(prepare.subprocess, 'check_output', return_value='/tmp/pybind11-cmake\n'):
            prepare.install_kimodo_official_runtime()
        current_install_call = current_run_mock.call_args_list[-1]
        self.assertIn('--no-deps', current_install_call.args[0])
        self.assertIn('--no-build-isolation', current_install_call.args[0])
        self.assertEqual(current_install_call.kwargs['env']['SKIP_MOTION_CORRECTION_IN_SETUP'], '0')
        self.assertTrue(current_install_call.kwargs['env']['CMAKE_PREFIX_PATH'].startswith('/tmp/pybind11-cmake'))

    def test_kimodo_runtime_setup_preserves_existing_environment(self):
        from generators.kimodo import setup_runtime
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_environment_path = Path(temporary_directory_name) / 'runtime'
            current_environment_path.mkdir()
            current_marker_path = current_environment_path / 'keep.txt'
            current_marker_path.write_text('preserve')
            with patch.object(setup_runtime, 'KIMODO_ENVIRONMENT_PYTHON', current_environment_path / 'bin/python'), \
                    patch.object(setup_runtime, 'run_logged_management_command') as current_run_mock:
                with self.assertRaisesRegex(ValueError, '자동 변경하지 않습니다'):
                    setup_runtime.prepare_kimodo_runtime_environment()
            current_run_mock.assert_not_called()
            self.assertEqual(current_marker_path.read_text(), 'preserve')

    def test_existing_kimodo_source_changes_are_not_overwritten(self):
        import subprocess
        from generators.kimodo import prepare
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_source_path = Path(temporary_directory_name) / 'source'
            current_source_path.mkdir()
            subprocess.run(['git', 'init', '-q', str(current_source_path)], check=True)
            subprocess.run(['git', '-C', str(current_source_path), 'config', 'user.email', 'test@example.invalid'], check=True)
            subprocess.run(['git', '-C', str(current_source_path), 'config', 'user.name', 'Test'], check=True)
            current_source_file = current_source_path / 'content.txt'
            current_source_file.write_text('original')
            subprocess.run(['git', '-C', str(current_source_path), 'add', 'content.txt'], check=True)
            subprocess.run(['git', '-C', str(current_source_path), 'commit', '-qm', 'test'], check=True)
            current_revision_value = subprocess.check_output(['git', '-C', str(current_source_path), 'rev-parse', 'HEAD'], text=True).strip()
            with patch.object(prepare, 'KIMODO_SOURCE_ROOT', current_source_path), \
                    patch.object(prepare, 'KIMODO_ASSET_CONFIG', {'source_revision': current_revision_value}):
                self.assertEqual(prepare.prepare_kimodo_source_repository(), current_revision_value)
                current_source_file.write_text('user change')
                with self.assertRaisesRegex(ValueError, '자동 변경하지 않습니다'):
                    prepare.prepare_kimodo_source_repository()
                self.assertEqual(current_source_file.read_text(), 'user change')

    def test_missing_model_links_to_management_without_downloading(self):
        current_commands = []
        def execute_status_command(current_operation_name, current_request_payload):
            current_commands.append((current_operation_name, current_request_payload))
            return {'ready': False, 'message': '준비 필요', 'preparation_status': 'idle'}
        current_result = read_model_readiness_status(execute_status_command)
        self.assertEqual(current_commands, [('model-status', {})])
        self.assertFalse(current_result[1])
        self.assertTrue(current_result[2]['visible'])
        self.assertFalse(current_result[3].active)

    def test_ready_model_hides_link_and_running_preparation_refreshes(self):
        current_ready_result = read_model_readiness_status(lambda *_: {'ready': True, 'message': '완료'})
        self.assertTrue(current_ready_result[1])
        self.assertFalse(current_ready_result[2]['visible'])
        current_running_result = read_model_readiness_status(lambda *_: {'ready': False, 'message': '진행 중', 'preparation_status': 'running'})
        self.assertTrue(current_running_result[2]['visible'])
        self.assertTrue(current_running_result[3].active)
        current_blocked_result = read_model_readiness_status(lambda *_: {'ready': True, 'generation_ready': False, 'message': '실행 환경 준비 필요'})
        self.assertTrue(current_blocked_result[2]['visible'])

    def test_status_failure_offers_navigation_and_disables_generation(self):
        def fail_status_command(*_):
            raise OSError('연결 오류')
        current_result = read_model_readiness_status(fail_status_command)
        self.assertIn('연결 오류', current_result[0])
        self.assertFalse(current_result[1])
        self.assertTrue(current_result[2]['visible'])

    def test_controls_only_provide_status_and_management_link(self):
        with gr.Blocks() as current_interface:
            build_model_readiness_controls(current_interface, lambda *_: {'ready': False, 'message': '준비 필요'})
        current_components = current_interface.config['components']
        current_buttons = [current_component['props'] for current_component in current_components if current_component['type'] == 'button']
        self.assertEqual([current_button['value'] for current_button in current_buttons], ['모델 준비 상태 확인', '모델 관리로 이동'])
        self.assertEqual(current_buttons[1]['link'], '/management/?tool=model-management&category=model-management')
        self.assertEqual(current_buttons[1]['link_target'], '_self')
