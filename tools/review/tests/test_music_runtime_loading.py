"""MiniMax 오프라인 구성요소 연결과 불완전 로딩 거절 검증."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from generators.music.runtime import load_minimax_music


class MusicRuntimeLoadingTests(unittest.TestCase):
    def test_local_components_load_without_remote_lookup(self):
        current_pipeline_mock = Mock(null_component_names=[])
        current_diffusers_mock = SimpleNamespace(ComponentsManager=Mock(),ModularPipeline=Mock())
        current_diffusers_mock.ModularPipeline.from_pretrained.return_value = current_pipeline_mock
        current_hooks_mock = SimpleNamespace(apply_group_offloading=Mock())
        current_torch_mock = SimpleNamespace(bfloat16='bf16',device=Mock(return_value='cuda'))
        with patch.dict('sys.modules',{'torch':current_torch_mock,'diffusers':current_diffusers_mock,'diffusers.hooks':current_hooks_mock}):
            self.assertIs(load_minimax_music(Path('/models/minimax')),current_pipeline_mock)
        current_pipeline_mock.load_components.assert_called_once_with(dtype='bf16',pretrained_model_name_or_path='/models/minimax/model',local_files_only=True)
        current_hooks_mock.apply_group_offloading.assert_called_once()

    def test_missing_component_fails_before_offload_setup(self):
        current_pipeline_mock = Mock(null_component_names=['language_model'])
        current_diffusers_mock = SimpleNamespace(ComponentsManager=Mock(),ModularPipeline=Mock())
        current_diffusers_mock.ModularPipeline.from_pretrained.return_value = current_pipeline_mock
        current_hooks_mock = SimpleNamespace(apply_group_offloading=Mock())
        with patch.dict('sys.modules',{'torch':Mock(),'diffusers':current_diffusers_mock,'diffusers.hooks':current_hooks_mock}):
            with self.assertRaisesRegex(RuntimeError,'language_model'):
                load_minimax_music(Path('/models/minimax'))
        current_hooks_mock.apply_group_offloading.assert_not_called()
