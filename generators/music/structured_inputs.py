"""별도 prompt/lyrics 입력 어댑터. 기존 준비 산출물과 구형 실행 계약을 보존한다."""
from contextlib import contextmanager
from pathlib import Path
from generators.music import runtime as music_runtime_module
from tools.review.common.generation_records import write_record_atomically


def generate_structured_minimax(current_request_record,current_model_root,current_attempt_root,current_metrics_recorder):
    import torch
    from diffusers.modular_pipelines.minimax_music3 import encoders as current_encoder_module
    current_music_pipeline = music_runtime_module.load_minimax_music(current_model_root)
    current_metrics_recorder.update_generation_stage('inference')
    with music_runtime_module.record_minimax_termination(current_encoder_module,current_music_pipeline,current_request_record['duration_seconds'],current_attempt_root):
        current_audio_outputs = current_music_pipeline(
            prompt=current_request_record['final_prompt'],lyrics=current_request_record['lyrics'],
            audio_duration=current_request_record['duration_seconds'],
            generator=torch.Generator('cuda').manual_seed(current_request_record['seed']),
            output='audios',output_type='pt')
    if len(current_audio_outputs) != 1 or current_audio_outputs[0].ndim != 2 or current_audio_outputs[0].shape[0] != 2:
        raise ValueError('MiniMax 출력은 1개 stereo 오디오여야 합니다.')
    return current_audio_outputs[0].T.float().cpu().numpy(),current_music_pipeline.sampling_rate


@contextmanager
def select_structured_adapter(current_request_record):
    """독립 작업 프로세스에서만 새 입력 어댑터를 선택하고 원래 등록을 복원한다."""
    current_original_adapter = music_runtime_module.MUSIC_GENERATION_ADAPTERS['music-minimax']
    current_adapter_checksum = None
    if 'lyrics' in current_request_record:
        music_runtime_module.MUSIC_GENERATION_ADAPTERS['music-minimax'] = generate_structured_minimax
        current_adapter_checksum = music_runtime_module.calculate_music_checksum(Path(__file__))
    try:
        yield current_adapter_checksum
    finally:
        music_runtime_module.MUSIC_GENERATION_ADAPTERS['music-minimax'] = current_original_adapter


def execute_structured_inference(current_service_name,current_request_record,current_attempt_root,current_metrics_recorder):
    with select_structured_adapter(current_request_record) as current_adapter_checksum:
        if current_adapter_checksum:
            write_record_atomically(current_attempt_root/'input-adapter.json',{'input_adapter_sha256':current_adapter_checksum,'lyrics':current_request_record['lyrics'],'prompt':current_request_record['final_prompt'],'audio_duration':current_request_record['duration_seconds']})
        current_result_record = music_runtime_module.execute_music_inference(current_service_name,current_request_record,current_attempt_root,current_metrics_recorder)
    if current_adapter_checksum:
        current_result_record['input_adapter_sha256'] = current_adapter_checksum
    return current_result_record
