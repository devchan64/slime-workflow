"""공식 Python API를 사용하는 두 음악 모델의 CUDA 전용 어댑터."""
import fcntl
import hashlib
import os
from pathlib import Path
import sys
from generators.music.contracts import read_music_record, resolve_music_paths, resolve_music_profile
from tools.review.common.generation_records import write_record_atomically

MUSIC_RUNTIME_MODULES = {'music-ace-step':'acestep','music-minimax':'diffusers'}


def configure_music_cache(current_model_root):
    # 외부 라이브러리가 사용자 홈에 모델을 내려받지 않도록 import 전에 설정한다.
    os.environ['HF_HOME'] = str(current_model_root/'hub-home')
    os.environ['HF_HUB_CACHE'] = str(current_model_root/'hub-home/hub')
    os.environ['TORCH_HOME'] = str(current_model_root/'torch-cache')
    os.environ['ACESTEP_CHECKPOINTS_DIR'] = str(current_model_root/'checkpoints')


def require_music_cuda():
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA 사용 불가: CPU 추론으로 전환하지 않습니다.')
    if not torch.cuda.is_bf16_supported():
        raise RuntimeError('이 음악 실행 설정에는 BF16 지원 CUDA GPU가 필요합니다.')
    torch.cuda.reset_peak_memory_stats()
    return torch


def calculate_music_checksum(current_artifact_path):
    current_digest_value = hashlib.sha256()
    with current_artifact_path.open('rb') as current_artifact_handle:
        for current_file_chunk in iter(lambda:current_artifact_handle.read(8*1024*1024),b''):
            current_digest_value.update(current_file_chunk)
    return current_digest_value.hexdigest()


def validate_prepared_music(current_service_name):
    _,current_model_root,current_python_path = resolve_music_paths(current_service_name)
    current_manifest_path = current_model_root/'prepared.json'
    if not current_python_path.is_file() or not current_manifest_path.is_file():
        raise FileNotFoundError(f'음악 실행 환경·모델 준비 필요: {current_python_path}, {current_manifest_path}')
    current_manifest_record = read_music_record(current_manifest_path)
    if current_manifest_record['model_id'] != resolve_music_profile(current_service_name)['model_id'] or current_manifest_record['runtime_sha256'] != calculate_music_checksum(Path(__file__)):
        raise ValueError('모델 준비 버전 불일치: prepare를 다시 실행하세요.')
    if not current_manifest_record['files']:
        raise ValueError('모델 준비 파일 목록이 비어 있습니다.')
    for current_file_record in current_manifest_record['files']:
        current_model_path = current_model_root/current_file_record['path']
        if not current_model_path.resolve().is_relative_to(current_model_root.resolve()) or not current_model_path.is_file() or current_model_path.stat().st_size != current_file_record['size']:
            raise ValueError(f'모델 준비 파일 누락·경로·크기 오류: {current_model_path}')
    return current_manifest_record


def reject_cpu_inference(current_model_module,current_input_values):
    """오프로드의 GPU 복귀 뒤, 실제 가중치 연산 직전에 검사한다."""
    for current_parameter_value in current_model_module.parameters(recurse=False):
        if current_parameter_value.device.type != 'cuda':
            raise RuntimeError(f'CPU 모델 연산 차단: {type(current_model_module).__name__}')


def attach_cuda_guards(current_model_module):
    for current_child_module in current_model_module.modules():
        current_child_module.register_forward_pre_hook(reject_cpu_inference)


def reject_ace_cpu_decode(*current_argument_values,**current_keyword_values):
    raise RuntimeError('ACE-Step CPU VAE 디코딩 전환 차단: GPU 메모리 부족 원인을 확인하세요.')


def load_ace_step(current_model_root):
    from acestep.handler import AceStepHandler
    from acestep.llm_inference import LLMHandler
    current_diffusion_handler = AceStepHandler()
    current_status_message,current_success_value = current_diffusion_handler.initialize_service(
        project_root=str(current_model_root),config_path='acestep-v15-turbo',device='cuda',
        offload_to_cpu=True,offload_dit_to_cpu=True,compile_model=False,use_mlx_dit=False,vae_checkpoint='official')
    if not current_success_value or current_diffusion_handler.device != 'cuda':
        raise RuntimeError(f'ACE-Step 초기화 실패: {current_status_message}')
    current_diffusion_handler._decode_on_cpu = reject_ace_cpu_decode
    current_diffusion_handler._tiled_decode_cpu_fallback = reject_ace_cpu_decode
    for current_model_module in (current_diffusion_handler.model,current_diffusion_handler.vae,current_diffusion_handler.text_encoder):
        attach_cuda_guards(current_model_module)
    current_language_handler = LLMHandler()
    current_status_message,current_success_value = current_language_handler.initialize(
        checkpoint_dir=str(current_model_root/'checkpoints'),lm_model_path='acestep-5Hz-lm-0.6B',
        backend='pt',device='cuda',offload_to_cpu=True)
    if not current_success_value or str(current_language_handler.device).split(':')[0] != 'cuda':
        raise RuntimeError(f'ACE-Step LM 초기화 실패: {current_status_message}')
    attach_cuda_guards(current_language_handler.llm)
    return current_diffusion_handler,current_language_handler


def load_minimax_music(current_model_root):
    import torch
    from diffusers import ComponentsManager, ModularPipeline
    from diffusers.hooks import apply_group_offloading
    current_component_manager = ComponentsManager()
    current_component_manager.enable_auto_cpu_offload(device='cuda')
    current_music_pipeline = ModularPipeline.from_pretrained(str(current_model_root/'model'),components_manager=current_component_manager)
    current_music_pipeline.load_components(dtype=torch.bfloat16,pretrained_model_name_or_path=str(current_model_root/'model'),local_files_only=True)
    if current_music_pipeline.null_component_names:
        raise RuntimeError(f'MiniMax 구성요소 로딩 실패: {current_music_pipeline.null_component_names}')
    apply_group_offloading(current_music_pipeline.language_model,onload_device=torch.device('cuda'),offload_type='leaf_level',use_stream=True)
    # Diffusers의 offload hook가 forward 안에서 이동하므로 외부 pre-hook로 간섭하지 않는다.
    return current_music_pipeline


MUSIC_MODEL_LOADERS = {'music-ace-step':load_ace_step,'music-minimax':load_minimax_music}


def prepare_music_model(current_service_name,current_metrics_recorder,current_refresh_assets=False):
    import importlib
    _,current_model_root,current_python_path = resolve_music_paths(current_service_name)
    current_profile_record = resolve_music_profile(current_service_name)
    current_model_root.mkdir(parents=True,exist_ok=True)
    configure_music_cache(current_model_root)
    print(f"model_id={current_profile_record['model_id']} model_root={current_model_root} model_path={current_model_root} binary_path={current_python_path}",flush=True)
    with (current_model_root/'prepare.lock').open('a') as current_prepare_lock:
        fcntl.flock(current_prepare_lock,fcntl.LOCK_EX)
        if current_refresh_assets:
            (current_model_root/'prepared.json').unlink(missing_ok=True)
        if (current_model_root/'prepared.json').exists():
            current_manifest_record = validate_prepared_music(current_service_name)
            print(f'모델 준비 재사용: {current_model_root}',flush=True)
            return current_manifest_record
        require_music_cuda()
        importlib.import_module(MUSIC_RUNTIME_MODULES[current_service_name])
        from huggingface_hub import HfApi, snapshot_download
        current_metrics_recorder.update_generation_stage('download')
        current_download_records = []
        current_download_specs = [(current_profile_record['model_id'],current_model_root/('checkpoints' if current_service_name=='music-ace-step' else 'model'))]
        if current_service_name == 'music-ace-step':
            current_download_specs.append(('ACE-Step/acestep-5Hz-lm-0.6B',current_model_root/'checkpoints/acestep-5Hz-lm-0.6B'))
        for current_repository_name,current_target_path in current_download_specs:
            current_revision_value = HfApi().model_info(current_repository_name).sha
            current_download_options = {'repo_id':current_repository_name,'revision':current_revision_value}
            if current_target_path is not None:
                current_download_options['local_dir'] = str(current_target_path)
            current_resolved_path = snapshot_download(**current_download_options)
            current_download_records.append({'model_id':current_repository_name,'revision':current_revision_value,'path':str(current_resolved_path)})
        current_metrics_recorder.update_generation_stage('prepare')
        # 텍스트 인코더 등 종속 모델까지 다운로드·로딩 검증을 마친 뒤만 준비 완료로 기록한다.
        current_loaded_model = MUSIC_MODEL_LOADERS[current_service_name](current_model_root)
        del current_loaded_model
        require_music_cuda().cuda.empty_cache()
        current_file_records = []
        for current_artifact_path in sorted(current_model_root.rglob('*')):
            if not current_artifact_path.is_file() or current_artifact_path.name.endswith(('.lock','.incomplete')) or '.cache' in current_artifact_path.parts:
                continue
            if not current_artifact_path.resolve().is_relative_to(current_model_root.resolve()):
                raise ValueError('모델 캐시 외부 파일 참조 거절')
            current_file_records.append({'path':str(current_artifact_path.relative_to(current_model_root)),'size':current_artifact_path.stat().st_size})
        current_manifest_record = {'model_id':current_profile_record['model_id'],'runtime_sha256':calculate_music_checksum(Path(__file__)),
                                   'downloads':current_download_records,'files':current_file_records,'binary_path':str(current_python_path)}
        write_record_atomically(current_model_root/'prepared.json',current_manifest_record)
        print(f'모델 준비 완료: {current_model_root}',flush=True)
        return current_manifest_record


def generate_ace_step(current_request_record,current_model_root,current_attempt_root,current_metrics_recorder):
    import soundfile
    from acestep.inference import GenerationParams, GenerationConfig, generate_music
    current_diffusion_handler,current_language_handler = load_ace_step(current_model_root)
    current_generation_params = GenerationParams(caption=current_request_record['final_prompt'],lyrics='',instrumental=True,
        duration=current_request_record['duration_seconds'],seed=current_request_record['seed'],inference_steps=8,
        thinking=True,use_cot_caption=False,use_cot_lyrics=False,guidance_scale=1.0)
    current_generation_config = GenerationConfig(batch_size=1,audio_format='wav',use_random_seed=False,seeds=[current_request_record['seed']])
    current_metrics_recorder.update_generation_stage('inference')
    current_generation_result = generate_music(current_diffusion_handler,current_language_handler,current_generation_params,current_generation_config,save_dir=str(current_attempt_root/'raw'))
    if not current_generation_result.success or len(current_generation_result.audios) != 1:
        raise RuntimeError(f'ACE-Step 생성 실패: {current_generation_result.error}')
    current_audio_path = Path(current_generation_result.audios[0]['path']).resolve()
    if not current_audio_path.is_relative_to(current_attempt_root.resolve()) or current_audio_path.suffix != '.wav':
        raise ValueError('ACE-Step WAV 결과 경로 오류')
    return soundfile.read(current_audio_path,always_2d=True,dtype='float32')


def generate_minimax_music(current_request_record,current_model_root,current_attempt_root,current_metrics_recorder):
    import torch
    current_music_pipeline = load_minimax_music(current_model_root)
    current_metrics_recorder.update_generation_stage('inference')
    current_audio_outputs = current_music_pipeline(prompt=current_request_record['final_prompt'],lyrics='[Instrumental]',
        audio_duration=current_request_record['duration_seconds'],generator=torch.Generator('cuda').manual_seed(current_request_record['seed']),output='audios',output_type='pt')
    if len(current_audio_outputs) != 1 or current_audio_outputs[0].ndim != 2 or current_audio_outputs[0].shape[0] != 2:
        raise ValueError('MiniMax 출력은 1개 stereo 오디오여야 합니다.')
    return current_audio_outputs[0].T.float().cpu().numpy(),current_music_pipeline.sampling_rate


MUSIC_GENERATION_ADAPTERS = {'music-ace-step':generate_ace_step,'music-minimax':generate_minimax_music}


def execute_music_inference(current_service_name,current_request_record,current_attempt_root,current_metrics_recorder):
    import numpy
    import soundfile
    _,current_model_root,_ = resolve_music_paths(current_service_name)
    configure_music_cache(current_model_root)
    validate_prepared_music(current_service_name)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import huggingface_hub.constants
    huggingface_hub.constants.HF_HUB_OFFLINE = True
    current_torch_module = require_music_cuda()
    current_metrics_recorder.update_generation_stage('load')
    current_audio_samples,current_sample_rate = MUSIC_GENERATION_ADAPTERS[current_service_name](current_request_record,current_model_root,current_attempt_root,current_metrics_recorder)
    current_profile_record = resolve_music_profile(current_service_name)
    if current_sample_rate != current_profile_record['sample_rate'] or current_audio_samples.ndim != 2 or current_audio_samples.shape[1] != 2 or len(current_audio_samples) == 0 or not numpy.isfinite(current_audio_samples).all():
        raise ValueError('출력 오디오 sample rate·stereo·유한값 계약 위반')
    current_quality_warnings = []
    if numpy.max(numpy.abs(current_audio_samples)) > 1:
        current_quality_warnings.append('PCM16 저장 시 최대 진폭을 넘는 샘플이 클리핑됩니다.')
    if numpy.max(numpy.abs(current_audio_samples)) < 0.0001:
        current_quality_warnings.append('출력 진폭이 매우 낮습니다. 청취 검수가 필요합니다.')
    current_metrics_recorder.update_generation_stage('saving')
    current_audio_path = current_attempt_root/'music.wav'
    soundfile.write(current_audio_path,current_audio_samples,current_sample_rate,format='WAV',subtype='PCM_16')
    for current_warning_text in current_quality_warnings:
        print('WARN '+current_warning_text,flush=True)
    return {'attempt':current_attempt_root.name,'model_id':current_profile_record['model_id'],'format':'wav','channels':2,
        'sample_rate':current_sample_rate,'duration_seconds':len(current_audio_samples)/current_sample_rate,
        'output_sha256':calculate_music_checksum(current_audio_path),'prompt_sha256':current_request_record['prompt_sha256'],
        'runtime_sha256':calculate_music_checksum(Path(__file__)),'model_compute_device':'cuda','torch_peak_allocated_mib':current_torch_module.cuda.max_memory_allocated()/2**20,
        'torch_peak_reserved_mib':current_torch_module.cuda.max_memory_reserved()/2**20,'torch_version':current_torch_module.__version__,
        'quality_warnings':current_quality_warnings,'quality_status':'사용자 청취 검수 대기','seamless_loop_guaranteed':False}
