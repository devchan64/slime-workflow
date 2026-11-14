"""MIGraphX 빌드의 격리·무결성·대기열 접수 계약."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from generators.kimodo.migraphx_build import verify_pose_cache_files
from tools.review.common.management_gateway import resolve_management_command
from tools.review.ui.gradio.model_management_app import format_migraphx_build_status


class KimodoMigraphxBuildTests(unittest.TestCase):
    def test_model_and_device_changes_isolate_build_cache(self):
        from generators.kimodo import migraphx_build, dwpose_runtime
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_directory_root = Path(current_directory_name)
            current_library_root = current_directory_root/'libraries'
            current_library_root.mkdir()
            (current_library_root/'libmigraphx.so').write_bytes(b'library')
            current_provider_path = current_directory_root/'provider.so'
            current_provider_path.write_bytes(b'provider')
            current_model_paths = []
            for current_model_name in dwpose_runtime.FUN_POSE_MODEL_NAMES:
                current_model_path = (current_directory_root/current_model_name).with_suffix('.cuda.onnx')
                current_model_path.write_bytes(current_model_name.encode())
                current_model_paths.append(current_model_path)
            current_gpu_properties = SimpleNamespace(name='GPU', gcnArchName='gfx1151')
            current_torch_module = SimpleNamespace(cuda=SimpleNamespace(get_device_properties=lambda index: current_gpu_properties),
                                                   version=SimpleNamespace(hip='7'), __version__='2')
            current_provider_module = SimpleNamespace(get_library_paths=lambda: [str(current_provider_path)])
            current_ort_module = SimpleNamespace(__version__='1')
            with patch.object(dwpose_runtime, 'FUN_POSE_MODEL_DIRECTORY', current_directory_root), \
                 patch.object(migraphx_build, 'POSE_BUILD_CACHE_ROOT', current_directory_root/'cache'), \
                 patch.object(migraphx_build.importlib.util, 'find_spec', return_value=SimpleNamespace(submodule_search_locations=[str(current_library_root)])):
                current_initial_paths = migraphx_build.resolve_pose_cache_directories(current_torch_module, current_ort_module, current_provider_module)
                self.assertNotEqual(*current_initial_paths.values())
                current_model_paths[0].write_bytes(b'changed')
                current_changed_paths = migraphx_build.resolve_pose_cache_directories(current_torch_module, current_ort_module, current_provider_module)
                self.assertNotEqual(current_initial_paths[dwpose_runtime.FUN_POSE_MODEL_NAMES[0]], current_changed_paths[dwpose_runtime.FUN_POSE_MODEL_NAMES[0]])
                self.assertEqual(current_initial_paths[dwpose_runtime.FUN_POSE_MODEL_NAMES[1]], current_changed_paths[dwpose_runtime.FUN_POSE_MODEL_NAMES[1]])
                current_gpu_properties.gcnArchName = 'gfx9999'
                current_other_gpu_paths = migraphx_build.resolve_pose_cache_directories(current_torch_module, current_ort_module, current_provider_module)
                self.assertNotEqual(current_changed_paths, current_other_gpu_paths)

    def test_cache_manifest_detects_corruption_and_path_traversal(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_cache_directory = Path(current_directory_name)
            current_cache_path = current_cache_directory/'pose.mxr'
            current_cache_path.write_bytes(b'compiled')
            current_cache_hash = hashlib.sha256(b'compiled').hexdigest()
            current_manifest_path = current_cache_directory/'verified.json'
            current_manifest_path.write_text(json.dumps({'files': {'pose.mxr': current_cache_hash}}))
            self.assertTrue(verify_pose_cache_files(current_cache_directory))
            current_cache_path.write_bytes(b'corrupted')
            self.assertFalse(verify_pose_cache_files(current_cache_directory))
            current_manifest_path.write_text(json.dumps({'files': {'../pose.mxr': current_cache_hash}}))
            self.assertFalse(verify_pose_cache_files(current_cache_directory))

    def test_gateway_build_commands_reject_extra_input(self):
        self.assertEqual(resolve_management_command('kimodo', 'migraphx-build', {}), ('POST', '/kimodo/migraphx-build'))
        self.assertEqual(resolve_management_command('kimodo', 'migraphx-build-status', {}), ('GET', '/kimodo/migraphx-build-status'))
        with self.assertRaises(ValueError):
            resolve_management_command('kimodo', 'migraphx-build', {'path': '/tmp'})

    def test_duplicate_build_returns_existing_job(self):
        from tools.review.domains.kimodo import migraphx_build
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_root = Path(current_directory_name)
            current_job_directory = current_job_root/'existing'
            current_job_directory.mkdir()
            (current_job_root/'latest.json').write_text(json.dumps({'job': 'existing'}))
            (current_job_directory/'status.json').write_text(json.dumps({'status': 'queued'}))
            with patch.object(migraphx_build, 'POSE_BUILD_JOB_ROOT', current_job_root), patch.object(migraphx_build, 'launch_gpu_process') as current_launch_mock:
                self.assertEqual(migraphx_build.start_pose_build_job()['id'], 'existing')
                current_launch_mock.assert_not_called()

    def test_build_status_shows_failure(self):
        self.assertIn('빌드 실패', format_migraphx_build_status({'status': 'failed', 'error': '실행 오류'}))
        self.assertIn('실행 오류', format_migraphx_build_status({'status': 'failed', 'error': '실행 오류'}))

    def test_build_button_is_disabled_after_completion(self):
        import gradio as gr
        from tools.review.ui.gradio.model_management_app import build_migraphx_build_controls
        with gr.Blocks() as current_interface_blocks:
            build_migraphx_build_controls(current_interface_blocks)
        current_refresh_callback = next(current_function.fn for current_function in current_interface_blocks.fns.values()
                                        if current_function.fn and current_function.fn.__name__ == 'refresh_migraphx_build_status')
        for current_status_name, current_expected_value in [('ready', False), ('checking', False), ('unavailable', False),
                                                            ('running', False), ('queued', False), ('rebuild_required', True)]:
            with self.subTest(status=current_status_name), patch('tools.review.ui.gradio.model_management_app.execute_remote_management_command', return_value={'status': current_status_name}):
                _, current_button_update = current_refresh_callback()
                self.assertEqual(current_button_update['interactive'], current_expected_value)

    def test_cache_state_controls_build_submission(self):
        from tools.review.domains.kimodo import migraphx_build
        with tempfile.TemporaryDirectory() as current_directory_name:
            with patch.object(migraphx_build, 'POSE_BUILD_JOB_ROOT', Path(current_directory_name)), \
                 patch.object(migraphx_build, 'inspect_pose_cache_validity', return_value={'status': 'ready'}), \
                 patch.object(migraphx_build, 'launch_gpu_process') as current_launch_mock:
                self.assertEqual(migraphx_build.inspect_pose_build_status()['status'], 'ready')
                self.assertEqual(migraphx_build.start_pose_build_job()['status'], 'ready')
                current_launch_mock.assert_not_called()
            with patch.object(migraphx_build, 'POSE_BUILD_JOB_ROOT', Path(current_directory_name)), \
                 patch.object(migraphx_build, 'inspect_pose_cache_validity', return_value={'status': 'checking'}), \
                 patch.object(migraphx_build, 'launch_gpu_process') as current_launch_mock:
                self.assertEqual(migraphx_build.start_pose_build_job()['status'], 'checking')
                current_launch_mock.assert_not_called()
            current_python_path = Path(current_directory_name)/'python'
            current_python_path.touch()
            with patch.object(migraphx_build, 'POSE_BUILD_JOB_ROOT', Path(current_directory_name)/'jobs'), \
                 patch.object(migraphx_build, 'KIMODO_ENVIRONMENT_PYTHON', current_python_path), \
                 patch.object(migraphx_build, 'inspect_pose_cache_validity', return_value={'status': 'rebuild_required'}), \
                 patch.object(migraphx_build, 'check_pose_cache_environment', return_value=False), \
                 patch.object(migraphx_build, 'validate_fun_pose_assets'), \
                 patch.object(migraphx_build, 'launch_gpu_process') as current_launch_mock:
                self.assertEqual(migraphx_build.start_pose_build_job()['status'], 'queued')
                current_launch_mock.assert_called_once()
            current_check_state = {'future': object(), 'signature': 'old', 'completed': 1}
            with patch.object(migraphx_build, 'POSE_BUILD_JOB_ROOT', Path(current_directory_name)/'ready-jobs'), \
                 patch.object(migraphx_build, 'POSE_CACHE_CHECK_STATE', current_check_state), \
                 patch.object(migraphx_build, 'inspect_pose_cache_validity', return_value={'status': 'rebuild_required'}), \
                 patch.object(migraphx_build, 'check_pose_cache_environment', return_value=True), \
                 patch.object(migraphx_build, 'launch_gpu_process') as current_launch_mock:
                self.assertEqual(migraphx_build.start_pose_build_job()['status'], 'ready')
                self.assertIsNone(current_check_state['future'])
                current_launch_mock.assert_not_called()

    def test_model_or_gpu_change_requires_valid_matching_cache(self):
        import sys
        from generators.kimodo import migraphx_build, dwpose_runtime
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path = Path(current_directory_name)
            current_library_root = current_root_path/'libs'
            current_library_root.mkdir()
            (current_library_root/'libmigraphx.so').write_bytes(b'library')
            current_provider_path = current_root_path/'provider.so'
            current_provider_path.write_bytes(b'provider')
            for current_model_name in dwpose_runtime.FUN_POSE_MODEL_NAMES:
                (current_root_path/current_model_name).with_suffix('.cuda.onnx').write_bytes(current_model_name.encode())
            current_gpu_properties = SimpleNamespace(name='GPU', gcnArchName='gfx1151')
            current_torch_module = SimpleNamespace(cuda=SimpleNamespace(get_device_properties=lambda _: current_gpu_properties), version=SimpleNamespace(hip='7'), __version__='2')
            current_ort_module = SimpleNamespace(__version__='1')
            current_provider_module = SimpleNamespace(get_library_paths=lambda: [str(current_provider_path)])
            with patch.object(dwpose_runtime, 'FUN_POSE_MODEL_DIRECTORY', current_root_path), \
                 patch.object(migraphx_build, 'POSE_BUILD_CACHE_ROOT', current_root_path/'cache'), \
                 patch.object(migraphx_build.importlib.util, 'find_spec', return_value=SimpleNamespace(submodule_search_locations=[str(current_library_root)])), \
                 patch.dict(sys.modules, {'torch': current_torch_module, 'onnxruntime': current_ort_module, 'onnxruntime_ep_migraphx': current_provider_module}):
                current_cache_paths = migraphx_build.resolve_pose_cache_directories(current_torch_module, current_ort_module, current_provider_module)
                for current_cache_path in current_cache_paths.values():
                    current_cache_path.mkdir(parents=True)
                    (current_cache_path/'graph.mxr').write_bytes(b'graph')
                    (current_cache_path/'verified.json').write_text(json.dumps({'files': {'graph.mxr': hashlib.sha256(b'graph').hexdigest()}}))
                self.assertTrue(migraphx_build.inspect_pose_execution_cache())
                (next(iter(current_cache_paths.values()))/'graph.mxr').write_bytes(b'corrupted')
                self.assertFalse(migraphx_build.inspect_pose_execution_cache())
                (next(iter(current_cache_paths.values()))/'graph.mxr').write_bytes(b'graph')
                current_gpu_properties.gcnArchName = 'gfx9999'
                self.assertFalse(migraphx_build.inspect_pose_execution_cache())
                current_gpu_properties.gcnArchName = 'gfx1151'
                (current_root_path/dwpose_runtime.FUN_POSE_MODEL_NAMES[0]).with_suffix('.cuda.onnx').write_bytes(b'changed')
                self.assertFalse(migraphx_build.inspect_pose_execution_cache())

    def test_failed_cache_check_never_enables_build(self):
        from concurrent.futures import Future
        from tools.review.domains.kimodo import migraphx_build
        current_failed_future = Future()
        current_failed_future.set_exception(RuntimeError('GPU 확인 실패'))
        current_check_state = {'future': current_failed_future, 'signature': ('job', 'completed', 0), 'completed': None}
        with patch.object(migraphx_build, 'POSE_CACHE_CHECK_STATE', current_check_state):
            current_result_value = migraphx_build.inspect_pose_cache_validity(('job', 'completed', 0))
        self.assertEqual(current_result_value['status'], 'unavailable')
        self.assertIn('GPU 확인 실패', current_result_value['error'])
