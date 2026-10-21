"""최소 길이 제어의 준비 프레임·종료 경계·복원 검증."""
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from generators.music.contracts import build_music_request,verify_music_request
from generators.music import runtime
from generators.music.minimum_duration import apply_minimax_minimum_duration

class MinimaxMinimumDurationTests(unittest.TestCase):
    def test_minimum_end_token_boundary(self):
        import torch
        current_original_recorder=runtime.record_minimax_termination
        current_head_module=torch.nn.Identity()
        current_encoder_module=SimpleNamespace(_AUDIO_END_TOKEN_ID=3,_MAX_AUDIO_FRAMES=1500,_sample_top_k=lambda current_logits_tensor,current_random_generator: current_logits_tensor.argmax(-1))
        current_pipeline_record=SimpleNamespace(frame_rate=25,language_model=SimpleNamespace(config=SimpleNamespace(vocab_size=4),lm_head=current_head_module))
        with tempfile.TemporaryDirectory() as current_temp_name:
         with apply_minimax_minimum_duration(0.08):
          with runtime.record_minimax_termination(current_encoder_module,current_pipeline_record,1,Path(current_temp_name)) as current_trace_record:
           for current_frame_index in range(3):
            current_logits_tensor=current_head_module(torch.tensor([[0.,1.,2.,9.]]))
            assert current_encoder_module._sample_top_k(current_logits_tensor,None).item()==2
           assert current_trace_record['sampled_audio_frames']==2
           assert current_encoder_module._sample_top_k(current_head_module(torch.tensor([[0.,1.,2.,9.]])),None).item()==3
          assert not current_head_module._forward_hooks
        assert runtime.record_minimax_termination is current_original_recorder
        for current_invalid_minimum in (-1,61,True,float('nan')):
         try:build_music_request('music-minimax',{'prompt':'flute','max_new_tokens':1500,'min_duration_seconds':current_invalid_minimum})
         except ValueError:pass
         else:raise AssertionError(current_invalid_minimum)
        current_saved_request=build_music_request('music-minimax',{'prompt':'flute','max_new_tokens':1500,'min_duration_seconds':50})
        assert verify_music_request('music-minimax',current_saved_request)==current_saved_request
        print('최소 길이 경계·종료 토큰 재허용·훅 복원·입력 검증 통과')
