"""Dasheng-AudioGen 고정 로컬 모델·단계별 CUDA 추론 어댑터."""
from datetime import datetime
from functools import lru_cache
import fcntl
import os
from pathlib import Path

from generators.music.contracts import read_music_record, resolve_music_paths, resolve_music_profile
from generators.music.runtime import attach_cuda_guards, calculate_music_checksum, configure_music_cache
from tools.review.common.generation_records import write_record_atomically

DASHENG_MODEL_REVISIONS = (
    ('mispeech/Dasheng-AudioGen','e269f58e700d627b67600cbced86316c6585eae3','model'),
    ('google/flan-t5-large','0613663d0d48ea86ba8cb3d7a44f0f65dc596a2a','text-encoder'),
    ('mispeech/dashengtokenizer','46a0902499644aaf63bc7ba18698eea04ef160f9','audio-tokenizer'),
)
DASHENG_GUIDANCE_SCALE = 5.0


@lru_cache(maxsize=256)
def calculate_cached_checksum(current_file_path,current_file_size,current_modified_time,current_changed_time):
    """파일 상태가 같은 동안 대용량 가중치의 반복 UI 해시 계산을 피한다."""
    return calculate_music_checksum(current_file_path)


def require_effects_cuda():
    import torch
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError('Dasheng-AudioGen에는 BF16 지원 CUDA GPU가 필요합니다. CPU 추론으로 대체하지 않습니다.')
    return torch


def configure_effects_cache(current_model_root):
    configure_music_cache(current_model_root)
    os.environ['HF_MODULES_CACHE'] = str(current_model_root/'modules-cache')


def validate_effects_model(current_service_name):
    _,current_model_root,current_python_path = resolve_music_paths(current_service_name)
    if not current_python_path.is_file():
        raise FileNotFoundError('효과음 실행 환경 설치 필요: '+str(current_python_path))
    if not (current_model_root/'prepared.json').is_file():
        raise FileNotFoundError('Dasheng 모델 준비 전입니다. 모델 다운로드·준비를 실행하세요.')
    current_manifest_record = read_music_record(current_model_root/'prepared.json')
    if current_manifest_record['model_id'] != resolve_music_profile(current_service_name)['model_id'] or current_manifest_record['runtime_sha256'] != calculate_music_checksum(Path(__file__)):
        raise ValueError('효과음 모델 준비 버전 불일치: 모델 준비를 다시 실행하세요.')
    if not current_manifest_record['files']:
        raise ValueError('효과음 준비 파일 목록이 비어 있습니다.')
    for current_file_record in current_manifest_record['files']:
        current_file_path = current_model_root/current_file_record['path']
        if not current_file_path.resolve().is_relative_to(current_model_root.resolve()) or not current_file_path.is_file():
            raise ValueError('효과음 모델 파일 누락·경로 오류: '+str(current_file_path))
        current_file_status = current_file_path.stat()
        if calculate_cached_checksum(current_file_path,current_file_status.st_size,current_file_status.st_mtime_ns,current_file_status.st_ctime_ns) != current_file_record['sha256']:
            raise ValueError('효과음 모델 파일 누락·경로·해시 오류: '+str(current_file_path))
    return current_manifest_record


def attach_effects_offload(current_model_module,current_metrics_recorder=None):
    """CPU는 가중치 대기용이며 텍스트·DiT·디코더 연산은 모두 CUDA다."""
    import torch
    current_stage_modules = {
        'text':(current_model_module.text_encoder_backbone,),
        'inference':(current_model_module.backbone,),
        'decode':tuple(current_module_value for current_module_value in (current_model_module.audio_tokenizer.upsampler,current_model_module.audio_tokenizer.decoder) if current_module_value is not None),
    }
    current_active_stage = [None]
    def build_stage_transition(current_stage_name):
        def activate_effects_stage(current_target_module,current_input_values):
            if current_active_stage[0] == current_stage_name:
                return
            for current_other_name,current_module_values in current_stage_modules.items():
                if current_other_name != current_stage_name:
                    for current_module_value in current_module_values:
                        current_module_value.to('cpu')
            torch.cuda.empty_cache()
            for current_module_value in current_stage_modules[current_stage_name]:
                current_module_value.to('cuda')
            current_active_stage[0] = current_stage_name
            print(f'{datetime.now().isoformat()}/dasheng/{current_stage_name} compute=cuda weight_offload=cpu',flush=True)
            if current_metrics_recorder is not None:
                current_metrics_recorder.update_generation_stage(current_stage_name)
        return activate_effects_stage
    for current_stage_name,current_module_values in current_stage_modules.items():
        for current_module_value in current_module_values:
            current_module_value.register_forward_pre_hook(build_stage_transition(current_stage_name))
    current_model_module.content_adapter.to('cuda')
    current_model_module.content_encoder.to('cuda')
    for current_parameter_value in current_model_module.parameters(recurse=False):
        current_parameter_value.data = current_parameter_value.data.to('cuda')
    for current_buffer_name,current_buffer_value in current_model_module.named_buffers(recurse=False):
        setattr(current_model_module,current_buffer_name,current_buffer_value.to('cuda'))
    attach_cuda_guards(current_model_module)
    return current_model_module


def load_effects_model(current_model_root,current_metrics_recorder=None):
    import torch
    from transformers import AutoConfig, AutoModel
    current_model_path = current_model_root/'model'
    current_model_config = AutoConfig.from_pretrained(str(current_model_path),trust_remote_code=True,local_files_only=True)
    if current_model_config.sample_rate != 16000 or current_model_config.text_encoder_name != 'google/flan-t5-large' or current_model_config.tokenizer_name != 'mispeech/dashengtokenizer':
        raise ValueError('Dasheng 고정 모델·종속 모델·샘플레이트 계약 오류')
    # 원본 config는 수정하지 않고 고정 revision으로 준비한 로컬 종속 모델만 지정한다.
    current_model_config.text_encoder_name = str(current_model_root/'text-encoder')
    current_model_config.tokenizer_name = str(current_model_root/'audio-tokenizer')
    current_model_module = AutoModel.from_pretrained(str(current_model_path),config=current_model_config,trust_remote_code=True,local_files_only=True,torch_dtype=torch.bfloat16)
    current_model_module.eval().to(dtype=torch.bfloat16)
    # 공식 Vocos는 최종 ISTFT head에서 autocast를 끄고 FP32 입력을 사용한다.
    current_model_module.audio_tokenizer.decoder.head.float()
    return attach_effects_offload(current_model_module,current_metrics_recorder)


def prepare_effects_model(current_service_name,current_metrics_recorder,current_refresh_assets=False):
    _,current_model_root,current_python_path = resolve_music_paths(current_service_name)
    current_profile_record = resolve_music_profile(current_service_name)
    current_model_root.mkdir(parents=True,exist_ok=True)
    configure_effects_cache(current_model_root)
    print(f"{datetime.now().isoformat()}/dasheng/prepare model_id={current_profile_record['model_id']} model_root={current_model_root} model_path={current_model_root/'model'} binary_path={current_python_path}",flush=True)
    with (current_model_root/'prepare.lock').open('a') as current_lock_handle:
        fcntl.flock(current_lock_handle,fcntl.LOCK_EX)
        if current_refresh_assets:
            (current_model_root/'prepared.json').unlink(missing_ok=True)
        if (current_model_root/'prepared.json').exists():
            return validate_effects_model(current_service_name)
        current_torch_module = require_effects_cuda()
        from huggingface_hub import snapshot_download
        current_metrics_recorder.update_generation_stage('download')
        current_file_records = []
        for current_repository_name,current_revision_value,current_directory_name in DASHENG_MODEL_REVISIONS:
            current_resolved_path = Path(snapshot_download(repo_id=current_repository_name,revision=current_revision_value,local_dir=str(current_model_root/current_directory_name),allow_patterns=['*.json','*.py','*.safetensors','*.model','*.txt','README.md','LICENSE*']))
            print(f'{datetime.now().isoformat()}/dasheng/download model_id={current_repository_name} model_path={current_resolved_path} revision={current_revision_value}',flush=True)
            for current_file_path in sorted(current_resolved_path.rglob('*')):
                if not current_file_path.is_file() or '.cache' in current_file_path.parts:
                    continue
                if not current_file_path.resolve().is_relative_to(current_model_root.resolve()):
                    raise ValueError('모델 캐시 외부 참조 거절')
                current_file_records.append({'path':str(current_file_path.relative_to(current_model_root)),'sha256':calculate_music_checksum(current_file_path)})
        current_metrics_recorder.update_generation_stage('load')
        current_loaded_model = load_effects_model(current_model_root)
        del current_loaded_model
        current_torch_module.cuda.empty_cache()
        current_manifest_record = {'model_id':current_profile_record['model_id'],'runtime_sha256':calculate_music_checksum(Path(__file__)),
            'revisions':DASHENG_MODEL_REVISIONS,'model_path':str(current_model_root/'model'),'binary_path':str(current_python_path),'files':current_file_records}
        write_record_atomically(current_model_root/'prepared.json',current_manifest_record)
        print(f'{datetime.now().isoformat()}/dasheng/prepared model_path={current_model_root / "model"}',flush=True)
        return current_manifest_record


def execute_effects_inference(current_service_name,current_request_record,current_attempt_root,current_metrics_recorder):
    import numpy
    import soundfile
    _,current_model_root,_ = resolve_music_paths(current_service_name)
    configure_effects_cache(current_model_root)
    validate_effects_model(current_service_name)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    current_torch_module = require_effects_cuda()
    current_profile_record = resolve_music_profile(current_service_name)
    current_metrics_recorder.update_generation_stage('load')
    current_loaded_model = load_effects_model(current_model_root,current_metrics_recorder)
    current_metrics_recorder.current_step_total = current_profile_record['steps']
    current_metrics_recorder.current_run_state['step_total'] = current_profile_record['steps']
    current_completed_steps = [0]
    def record_effects_step(current_target_module,current_input_values,current_output_value):
        current_torch_module.cuda.synchronize()
        # Sway 스케줄러는 끝점을 포함하므로 설정 25에 실제 평가 26회다.
        current_actual_steps = len(current_loaded_model.scheduler.timesteps)
        current_metrics_recorder.current_step_total = current_actual_steps
        current_metrics_recorder.current_run_state['step_total'] = current_actual_steps
        current_completed_steps[0] += 1
        current_metrics_recorder.record_generation_step(current_completed_steps[0])
    current_loaded_model.backbone.register_forward_hook(record_effects_step)
    current_torch_module.manual_seed(current_request_record['seed'])
    with current_torch_module.inference_mode(),current_torch_module.autocast('cuda',dtype=current_torch_module.bfloat16):
        current_audio_tensor = current_loaded_model.generate(prompts=current_request_record['final_prompt'],num_steps=current_profile_record['steps'],guidance_scale=DASHENG_GUIDANCE_SCALE)
    if not isinstance(current_audio_tensor,current_torch_module.Tensor) or current_audio_tensor.ndim != 2 or current_audio_tensor.shape[0] != 1:
        raise ValueError('Dasheng 출력은 [1, samples] 모노 Tensor여야 합니다.')
    current_audio_samples = current_audio_tensor[0].float().cpu().numpy()
    current_sample_rate = current_profile_record['sample_rate']
    if len(current_audio_samples) == 0 or not numpy.isfinite(current_audio_samples).all():
        raise ValueError('Dasheng 출력 길이·유한값 계약 위반')
    current_quality_warnings = []
    if numpy.max(numpy.abs(current_audio_samples)) < 0.0001:
        current_quality_warnings.append('출력 진폭이 매우 낮습니다. 청취 검수가 필요합니다.')
    if numpy.max(numpy.abs(current_audio_samples)) > 1:
        current_quality_warnings.append('PCM16 저장 시 진폭 초과 샘플이 클리핑됩니다.')
    current_metrics_recorder.update_generation_stage('saving')
    current_audio_path = current_attempt_root/'sound.wav'
    soundfile.write(current_audio_path,current_audio_samples,current_sample_rate,format='WAV',subtype='PCM_16')
    for current_warning_text in current_quality_warnings:
        print(f'{datetime.now().isoformat()}/dasheng/quality WARN {current_warning_text}',flush=True)
    return {'attempt':current_attempt_root.name,'model_id':current_profile_record['model_id'],'format':'wav','channels':1,
        'sample_rate':current_sample_rate,'duration_seconds':len(current_audio_samples)/current_sample_rate,'duration_mode':'model_predicted',
        'output_sha256':calculate_music_checksum(current_audio_path),'prompt_sha256':current_request_record['prompt_sha256'],
        'runtime_sha256':calculate_music_checksum(Path(__file__)),'model_compute_device':'cuda',
        'torch_peak_allocated_mib':current_torch_module.cuda.max_memory_allocated()/2**20,
        'torch_peak_reserved_mib':current_torch_module.cuda.max_memory_reserved()/2**20,
        'quality_warnings':current_quality_warnings,'quality_status':'사용자 청취 검수 대기','seamless_loop_guaranteed':False}
