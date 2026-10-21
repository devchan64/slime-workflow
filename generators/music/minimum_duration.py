"""MiniMax 실험용 최소 길이 제어. 작업 전용 프로세스에서만 종료 후보를 억제한다."""
from contextlib import contextmanager
import math


@contextmanager
def apply_minimax_minimum_duration(current_minimum_seconds):
    from generators.music import runtime as current_music_runtime
    current_original_recorder = current_music_runtime.record_minimax_termination

    @contextmanager
    def record_controlled_termination(current_encoder_module,current_music_pipeline,current_duration_seconds,current_attempt_root):
        current_minimum_frames = math.ceil(current_minimum_seconds*current_music_pipeline.frame_rate)
        with current_original_recorder(current_encoder_module,current_music_pipeline,current_duration_seconds,current_attempt_root) as current_trace_record:
            current_trace_record.update(minimum_duration_seconds=current_minimum_seconds,minimum_audio_frames=current_minimum_frames,suppressed_end_steps=0)
            def suppress_audio_ending(current_head_module,current_head_inputs,current_head_output):
                # top-k 후보 선정 이전에 마스킹한다. 첫 준비 샘플은 출력 프레임에서 제외된다.
                if current_trace_record['sampled_audio_frames'] < current_minimum_frames:
                    current_head_output = current_head_output.clone()
                    current_head_output[...,current_encoder_module._AUDIO_END_TOKEN_ID] = -math.inf
                    current_trace_record['suppressed_end_steps'] += 1
                return current_head_output
            current_hook_handle = current_music_pipeline.language_model.lm_head.register_forward_hook(suppress_audio_ending)
            try:
                yield current_trace_record
            finally:
                current_hook_handle.remove()

    current_music_runtime.record_minimax_termination = record_controlled_termination
    try:
        yield
    finally:
        current_music_runtime.record_minimax_termination = current_original_recorder
