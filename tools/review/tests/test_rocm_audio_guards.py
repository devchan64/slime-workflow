"""음악·효과음의 ROCm 전용 실행 경계를 검증한다."""
from types import SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from generators.music.runtime import require_music_cuda
from generators.sound_effects.runtime import require_effects_cuda
from generators.sound_effects.runtime import attach_effects_stage_progress
from generators.music.heartmula.runtime import load_heartmula_resident_model


class RocmAudioGuardTests(unittest.TestCase):
    def test_setup_does_not_replace_existing_cuda_torch(self):
        from generators.sound_effects import setup_runtime
        with TemporaryDirectory() as current_directory_name:
            current_workspace_root = Path(current_directory_name)
            current_python_path = current_workspace_root/'.venv-sfx-dasheng/bin/python'
            current_python_path.parent.mkdir(parents=True)
            current_python_path.touch()
            with patch.object(setup_runtime, 'WORKFLOW_ROOT_DIRECTORY', current_workspace_root), patch.object(setup_runtime.shutil, 'which', return_value='/usr/bin/uv'), patch.object(setup_runtime.subprocess, 'check_output', return_value='2.8.0+cu128\n'), patch.object(setup_runtime, 'ManagementLaunchLogger'), patch.object(setup_runtime, 'run_logged_management_command') as current_command_mock:
                with self.assertRaisesRegex(RuntimeError, '교체하지 않습니다'):
                    setup_runtime.install_effects_runtime()
                current_command_mock.assert_not_called()

    def test_heartmula_loads_unquantized_on_gpu(self):
        current_model_class = Mock()
        current_torch_module = SimpleNamespace(bfloat16='bf16')
        load_heartmula_resident_model(current_model_class, '/model', current_torch_module)
        current_model_class.from_pretrained.assert_called_once_with('/model', local_files_only=True, device_map={'': 'cuda:0'}, dtype='bf16')

    def test_effects_stages_never_move_models_to_cpu(self):
        current_model_module = Mock()
        current_model_module.modules.return_value = []
        current_model_module.audio_tokenizer.upsampler = Mock()
        current_model_module.audio_tokenizer.decoder = Mock()
        current_metrics_recorder = Mock()
        attach_effects_stage_progress(current_model_module, current_metrics_recorder)
        current_model_module.to.assert_called_once_with('cuda')
        current_stage_hook = current_model_module.backbone.register_forward_pre_hook.call_args.args[0]
        current_stage_hook(current_model_module.backbone, ())
        current_metrics_recorder.update_generation_stage.assert_called_once_with('inference')
        current_model_module.backbone.to.assert_not_called()

    def test_available_nvidia_build_is_rejected(self):
        current_torch_module = SimpleNamespace(version=SimpleNamespace(hip=None), cuda=Mock())
        current_torch_module.cuda.is_available.return_value = True
        for current_guard_function in (require_music_cuda, require_effects_cuda):
            with self.subTest(guard=current_guard_function.__name__), patch.dict('sys.modules', {'torch': current_torch_module}), self.assertRaisesRegex(RuntimeError, 'ROCm'):
                current_guard_function()

    def test_rocm_gpu_with_bf16_is_accepted(self):
        current_torch_module = SimpleNamespace(version=SimpleNamespace(hip='test'), cuda=Mock())
        current_torch_module.cuda.is_available.return_value = True
        current_torch_module.cuda.is_bf16_supported.return_value = True
        for current_guard_function in (require_music_cuda, require_effects_cuda):
            with self.subTest(guard=current_guard_function.__name__), patch.dict('sys.modules', {'torch': current_torch_module}):
                self.assertIs(current_guard_function(), current_torch_module)
