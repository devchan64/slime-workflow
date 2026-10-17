"""Stable Audio 3 Small SFX의 고정 CUDA 어댑터와 준비 기록."""
from datetime import datetime
import fcntl
import os
from pathlib import Path
import re

from generators.music.contracts import read_music_record, resolve_music_paths, resolve_music_profile
from generators.music.runtime import attach_cuda_guards, calculate_music_checksum, configure_music_cache
from tools.review.common.generation_records import write_record_atomically

STABLE_AUDIO_SERVICE = 'sfx-stable-audio'
STABLE_AUDIO_REVISION = '77e0398c26f7d22d801ec1bb036307e8b231f741'


def require_effects_cuda():
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('Stable Audio CUDA 사용 불가: CPU 추론으로 대체하지 않습니다.')
    return torch


def configure_effects_cache(current_model_root):
    # 토큰 값은 읽거나 출력하지 않는다. 기존 로그인 파일의 위치만 유지한다.
    current_original_home = Path(os.environ.get('HF_HOME', Path.home()/'.cache/huggingface'))
    os.environ.setdefault('HF_TOKEN_PATH', str(current_original_home/'token'))
    configure_music_cache(current_model_root)


def validate_effects_model(current_service_name):
    _, current_model_root, current_python_path = resolve_music_paths(current_service_name)
    if not current_python_path.is_file():
        raise FileNotFoundError('효과음 실행 환경 설치 필요: '+str(current_python_path)+' · generators/sound_effects/README.md 참조')
    if not (current_model_root/'prepared.json').is_file():
        raise FileNotFoundError('모델 준비 전입니다. 공식 모델 접근 승인 후 모델 다운로드·준비 버튼을 누르세요.')
    current_manifest_record = read_music_record(current_model_root/'prepared.json')
    if current_manifest_record['model_id'] != resolve_music_profile(current_service_name)['model_id'] or current_manifest_record['runtime_sha256'] != calculate_music_checksum(Path(__file__)):
        raise ValueError('효과음 모델 준비 버전 불일치: 모델 준비를 다시 실행하세요.')
    if not current_manifest_record['files']:
        raise ValueError('효과음 준비 파일 목록이 비어 있습니다.')
    for current_file_record in current_manifest_record['files']:
        current_file_path = current_model_root/current_file_record['path']
        if not current_file_path.resolve().is_relative_to(current_model_root.resolve()) or not current_file_path.is_file() or current_file_path.stat().st_size != current_file_record['size']:
            raise ValueError('효과음 모델 준비 파일 누락·경로·크기 오류: '+str(current_file_path))
    return current_manifest_record


def load_effects_model(current_model_root):
    from stable_audio_3 import StableAudioModel
    from stable_audio_3.loading_utils import load_diffusion_cond
    current_model_config = read_music_record(current_model_root/'model/model_config.json')
    if current_model_config['sample_rate'] != 44100:
        raise ValueError('Stable Audio 모델 샘플레이트 계약 오류')
    current_model_module = load_diffusion_cond(current_model_config, str(current_model_root/'model/model.safetensors'), device='cuda', model_half=True)
    current_model_module.use_lora = False
    current_model_module.lora_names = []
    attach_cuda_guards(current_model_module)
    return StableAudioModel(current_model_module, current_model_config, 'cuda', True)


def prepare_effects_model(current_service_name, current_metrics_recorder, current_refresh_assets=False):
    _, current_model_root, current_python_path = resolve_music_paths(current_service_name)
    current_profile_record = resolve_music_profile(current_service_name)
    current_model_root.mkdir(parents=True, exist_ok=True)
    configure_effects_cache(current_model_root)
    print(f"{datetime.now().isoformat()}/stable-audio/prepare model_id={current_profile_record['model_id']} model_root={current_model_root} model_path={current_model_root/'model'} binary_path={current_python_path}", flush=True)
    with (current_model_root/'prepare.lock').open('a') as current_lock_handle:
        fcntl.flock(current_lock_handle, fcntl.LOCK_EX)
        if current_refresh_assets:
            (current_model_root/'prepared.json').unlink(missing_ok=True)
        if (current_model_root/'prepared.json').exists():
            return validate_effects_model(current_service_name)
        current_torch_module = require_effects_cuda()
        from huggingface_hub import HfApi, snapshot_download
        current_metrics_recorder.update_generation_stage('download')
        current_revision_value = HfApi().model_info(current_profile_record['model_id']).sha
        if not isinstance(current_revision_value, str) or not re.fullmatch('[a-f0-9]{40}', current_revision_value):
            raise ValueError('모델 다운로드 revision 형식 오류')
        current_resolved_path = snapshot_download(repo_id=current_profile_record['model_id'], revision=current_revision_value, local_dir=str(current_model_root/'model'))
        current_metrics_recorder.update_generation_stage('load')
        # 텍스트 인코더·토크나이저 종속 파일까지 준비한 뒤 완료로 기록한다.
        current_loaded_model = load_effects_model(current_model_root)
        del current_loaded_model
        current_torch_module.cuda.empty_cache()
        current_file_records = []
        for current_file_path in sorted(current_model_root.rglob('*')):
            if not current_file_path.is_file() or current_file_path.name.endswith(('.lock', '.incomplete')) or '.cache' in current_file_path.parts:
                continue
            if not current_file_path.resolve().is_relative_to(current_model_root.resolve()):
                raise ValueError('모델 캐시 외부 참조 거절')
            current_file_records.append({'path':str(current_file_path.relative_to(current_model_root)), 'size':current_file_path.stat().st_size})
        current_manifest_record = {'model_id':current_profile_record['model_id'], 'runtime_sha256':calculate_music_checksum(Path(__file__)),
            'upstream_revision':STABLE_AUDIO_REVISION, 'revision':current_revision_value, 'model_path':current_resolved_path,
            'binary_path':str(current_python_path), 'files':current_file_records}
        write_record_atomically(current_model_root/'prepared.json', current_manifest_record)
        print(f'{datetime.now().isoformat()}/stable-audio/prepared model_path={current_resolved_path}', flush=True)
        return current_manifest_record


def execute_effects_inference(current_service_name, current_request_record, current_attempt_root, current_metrics_recorder):
    import numpy
    import soundfile
    _, current_model_root, _ = resolve_music_paths(current_service_name)
    configure_effects_cache(current_model_root)
    validate_effects_model(current_service_name)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import huggingface_hub.constants
    huggingface_hub.constants.HF_HUB_OFFLINE = True
    current_torch_module = require_effects_cuda()
    current_profile_record = resolve_music_profile(current_service_name)
    current_metrics_recorder.update_generation_stage('load')
    current_loaded_model = load_effects_model(current_model_root)
    current_metrics_recorder.update_generation_stage('inference')
    current_audio_tensor = current_loaded_model.generate(prompt=current_request_record['final_prompt'], duration=current_request_record['duration_seconds'],
        seed=current_request_record['seed'], steps=current_profile_record['steps'], cfg_scale=1.0, batch_size=1, chunked_decode=True)
    if not isinstance(current_audio_tensor, current_torch_module.Tensor) or current_audio_tensor.ndim != 3 or tuple(current_audio_tensor.shape[:2]) != (1, 2):
        raise ValueError('Stable Audio 출력은 [1, 2, samples] Tensor여야 합니다.')
    current_audio_samples = current_audio_tensor[0].transpose(0, 1).float().cpu().numpy()
    current_sample_rate = current_loaded_model.model.sample_rate
    current_expected_samples = int(current_request_record['duration_seconds']*current_profile_record['sample_rate'])
    if current_sample_rate != current_profile_record['sample_rate'] or len(current_audio_samples) != current_expected_samples or not numpy.isfinite(current_audio_samples).all():
        raise ValueError('Stable Audio 출력 길이·샘플레이트·유한값 계약 위반')
    current_quality_warnings = []
    if numpy.max(numpy.abs(current_audio_samples)) < 0.0001:
        current_quality_warnings.append('출력 진폭이 매우 낮습니다. 청취 검수가 필요합니다.')
    if numpy.max(numpy.abs(current_audio_samples)) > 1:
        current_quality_warnings.append('PCM16 저장 시 진폭 초과 샘플이 클리핑됩니다.')
    current_metrics_recorder.update_generation_stage('saving')
    current_audio_path = current_attempt_root/'sound.wav'
    soundfile.write(current_audio_path, current_audio_samples, current_sample_rate, format='WAV', subtype='PCM_16')
    for current_warning_text in current_quality_warnings:
        print(f'{datetime.now().isoformat()}/stable-audio/quality WARN {current_warning_text}', flush=True)
    return {'attempt':current_attempt_root.name, 'model_id':current_profile_record['model_id'], 'format':'wav', 'channels':2,
        'sample_rate':current_sample_rate, 'duration_seconds':len(current_audio_samples)/current_sample_rate,
        'output_sha256':calculate_music_checksum(current_audio_path), 'prompt_sha256':current_request_record['prompt_sha256'],
        'runtime_sha256':calculate_music_checksum(Path(__file__)), 'model_compute_device':'cuda',
        'torch_peak_allocated_mib':current_torch_module.cuda.max_memory_allocated()/2**20,
        'torch_peak_reserved_mib':current_torch_module.cuda.max_memory_reserved()/2**20,
        'quality_warnings':current_quality_warnings, 'quality_status':'사용자 청취 검수 대기', 'seamless_loop_guaranteed':False}
