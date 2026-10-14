"""VAE의 전체 인코딩·CPU 대기·CUDA 복원 순서를 검증한다."""
import unittest
from unittest.mock import Mock, patch

from generators.vace.memory import StageOffloadedVacePipeline, StageOffloadedWanAutoencoder


class VaceMemoryStageTests(unittest.TestCase):
    def test_complete_encoding_precedes_offload(self):
        current_fake_pipeline = Mock()
        current_event_order = []
        current_fake_pipeline.vae.to.side_effect = lambda current_device_name: current_event_order.append(current_device_name)
        def finish_condition_encoding(*current_call_args, **current_call_kwargs):
            current_event_order.append('all_encodes')
            return 'latents'
        with patch('generators.vace.memory.WanVACEPipeline.prepare_video_latents', side_effect=finish_condition_encoding), patch('generators.vace.memory.torch.cuda.empty_cache'), patch('generators.vace.memory.record_memory_transition'):
            # 실제 상속 디스패치를 유지하고 모델 로드는 생략한다.
            current_pipeline_object = object.__new__(StageOffloadedVacePipeline)
            object.__setattr__(current_pipeline_object, 'vae', current_fake_pipeline.vae)
            self.assertEqual(current_pipeline_object.prepare_video_latents(), 'latents')
        self.assertEqual(current_event_order, ['cuda', 'all_encodes', 'cpu'])

    def test_decode_restores_cuda_before_compute(self):
        current_event_order = []
        current_vae_object = object.__new__(StageOffloadedWanAutoencoder)
        with patch.object(StageOffloadedWanAutoencoder, 'to', side_effect=lambda *current_call_args: current_event_order.append('cuda')), patch('generators.vace.memory.AutoencoderKLWan.decode', side_effect=lambda *current_call_args: current_event_order.append('decode')), patch('generators.vace.memory.record_memory_transition'):
            current_vae_object.decode('latents')
        self.assertEqual(current_event_order, ['cuda', 'decode'])
