"""고정 HY-Motion Lite 모델 준비와 GPU 연산·CPU 메모리 오프로드."""
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

from generators.hy_motion.contracts import MODEL_CACHE_DIRECTORY, SOURCE_BUNDLE_DIRECTORY, load_generation_defaults, build_prompt_provenance, read_encoder_system_prompt, build_encoder_input_preview
from tools.review.common.generation_records import write_record_atomically

MODEL_BUNDLE_REPOSITORY = 'https://github.com/Tencent-Hunyuan/HY-Motion-1.0.git'
TEXT_ENCODER_REPOSITORY = 'Qwen/Qwen3-8B'
CLIP_ENCODER_REPOSITORY = 'openai/clip-vit-large-patch14'
MODEL_REPOSITORY_REVISIONS = {'tencent/HY-Motion-1.0': '620dd559f8d964aac2f82f1204fe6a35ad8ad14d', 'Qwen/Qwen3-8B': 'b968826d9c46dd6066d109eabc6255188de91218', 'openai/clip-vit-large-patch14': '32bd64288804d66eefd0ccbe215aa642df71cc41'}
PREPARED_MANIFEST_PATH = MODEL_CACHE_DIRECTORY / 'prepared.json'
EXTERNAL_RIG_BUFFER_KEYS = frozenset('body_model.' + current_buffer_name for current_buffer_name in ('v_template', 'j_template', 'skin_weights', 'skin_indices', 'parents'))


def inspect_prepared_bundle():
    if not PREPARED_MANIFEST_PATH.is_file():
        return {'ready': False, 'message': '모델 준비를 실행하세요. 최초 다운로드에는 시간과 디스크 공간이 필요합니다.'}
    current_manifest_record = json.loads(PREPARED_MANIFEST_PATH.read_text())
    if current_manifest_record.get('source_revision') != load_generation_defaults()['source_revision']:
        return {'ready': False, 'message': '공식 소스 버전이 다릅니다. 모델 준비를 다시 실행하세요.'}
    current_missing_paths = [current_relative_path for current_relative_path in current_manifest_record['files'] if not (MODEL_CACHE_DIRECTORY / current_relative_path).is_file()]
    return {'ready': not current_missing_paths, 'message': '준비 완료 · GPU 추론·8GB 실측은 실행 기록에서 확인하세요.' if not current_missing_paths else '모델 파일 누락: ' + ', '.join(current_missing_paths[:3])}


def prepare_model_bundle(current_progress_callback):
    from huggingface_hub import snapshot_download
    current_config_values = load_generation_defaults()
    MODEL_CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    current_progress_callback('prepare', '공식 소스·모델 다운로드 중')
    if not (SOURCE_BUNDLE_DIRECTORY / '.git').is_dir():
        subprocess.run(['git', 'clone', MODEL_BUNDLE_REPOSITORY, str(SOURCE_BUNDLE_DIRECTORY)], check=True, env={**os.environ, 'GIT_LFS_SKIP_SMUDGE': '1'})
    subprocess.run(['git', '-C', str(SOURCE_BUNDLE_DIRECTORY), 'checkout', '--detach', current_config_values['source_revision']], check=True)
    # 공식 모델 번들에 포함된 Wooden 리그·통계도 동일 소스 버전으로 준비한다.
    for current_asset_directory in (SOURCE_BUNDLE_DIRECTORY / 'stats', SOURCE_BUNDLE_DIRECTORY / 'scripts/gradio/static/assets/dump_wooden'):
        for current_asset_path in current_asset_directory.iterdir():
            if current_asset_path.suffix not in ('.bin', '.npy'):
                continue
            current_pointer_bytes = current_asset_path.read_bytes()
            if not current_pointer_bytes.startswith(b'version https://git-lfs.github.com/spec/v1'):
                continue
            current_pointer_fields = dict(current_pointer_line.split(' ', 1) for current_pointer_line in current_pointer_bytes.decode().splitlines())
            current_download_url = 'https://media.githubusercontent.com/media/Tencent-Hunyuan/HY-Motion-1.0/' + current_config_values['source_revision'] + '/' + current_asset_path.relative_to(SOURCE_BUNDLE_DIRECTORY).as_posix()
            with urllib.request.urlopen(current_download_url, timeout=120) as current_download_response:
                current_asset_bytes = current_download_response.read()
            if len(current_asset_bytes) != int(current_pointer_fields['size']) or hashlib.sha256(current_asset_bytes).hexdigest() != current_pointer_fields['oid'].removeprefix('sha256:'):
                raise ValueError(f'공식 LFS 에셋 크기·해시 불일치: {current_asset_path}')
            current_asset_path.write_bytes(current_asset_bytes)
    current_snapshot_paths = {}
    for current_model_name, current_repository_id, current_allow_patterns in (
        ('motion', current_config_values['model_id'], ['HY-Motion-1.0-Lite/*']),
        ('qwen', TEXT_ENCODER_REPOSITORY, ['*.json', '*.safetensors', '*.txt', '*.model', '*.jinja']),
        ('clip', CLIP_ENCODER_REPOSITORY, ['*.json', '*.safetensors', '*.txt']),
    ):
        current_progress_callback('prepare', f'모델 준비: {current_repository_id}')
        current_snapshot_paths[current_model_name] = snapshot_download(current_repository_id, revision=MODEL_REPOSITORY_REVISIONS[current_repository_id], cache_dir=str(MODEL_CACHE_DIRECTORY / 'hub'), allow_patterns=current_allow_patterns)
    current_manifest_record = {'source_revision': current_config_values['source_revision'], 'snapshots': current_snapshot_paths, 'files': {}}
    for current_snapshot_root in [SOURCE_BUNDLE_DIRECTORY / 'stats', SOURCE_BUNDLE_DIRECTORY / 'scripts/gradio/static/assets/dump_wooden', *(Path(current_snapshot_path) for current_snapshot_path in current_snapshot_paths.values())]:
        for current_artifact_path in current_snapshot_root.rglob('*'):
            if current_artifact_path.is_file():
                current_artifact_hash = hashlib.sha256()
                with current_artifact_path.open('rb') as current_artifact_stream:
                    for current_data_chunk in iter(lambda: current_artifact_stream.read(8 * 1024 * 1024), b''):
                        current_artifact_hash.update(current_data_chunk)
                current_manifest_record['files'][str(current_artifact_path.relative_to(MODEL_CACHE_DIRECTORY))] = current_artifact_hash.hexdigest()
    if not current_manifest_record['files']:
        raise ValueError('모델 다운로드 결과가 비어 있습니다.')
    write_record_atomically(PREPARED_MANIFEST_PATH, current_manifest_record)
    current_progress_callback('prepare', f'모델 준비 완료: {MODEL_CACHE_DIRECTORY}')
    return current_manifest_record


def run_motion_inference(current_request_record, current_config_record, current_attempt_path, current_progress_callback):
    import sys
    import torch
    from accelerate import cpu_offload
    from accelerate.hooks import remove_hook_from_module
    from transformers import AutoModelForCausalLM, AutoTokenizer, CLIPTextModel, CLIPTokenizer
    from generators.hy_motion.contracts import UniqueConfigLoader
    import yaml

    if not torch.cuda.is_available():
        raise RuntimeError('HY-Motion 실행에 CUDA GPU가 필요합니다. CPU 추론으로 대체하지 않습니다.')
    if not inspect_prepared_bundle()['ready']:
        raise FileNotFoundError(f'HY-Motion 모델 준비 필요: {MODEL_CACHE_DIRECTORY}')
    current_manifest_record = json.loads(PREPARED_MANIFEST_PATH.read_text())
    current_source_revision = subprocess.check_output(['git', '-C', str(SOURCE_BUNDLE_DIRECTORY), 'rev-parse', 'HEAD'], text=True).strip()
    if current_source_revision != current_config_record['source_revision']:
        raise ValueError('HY-Motion 공식 소스 SHA 불일치')
    sys.path.insert(0, str(SOURCE_BUNDLE_DIRECTORY))
    os.chdir(SOURCE_BUNDLE_DIRECTORY)
    from hymotion.pipeline.motion_diffusion import MotionFlowMatching
    current_motion_path = Path(current_manifest_record['snapshots']['motion']) / current_config_record['model_variant']
    current_qwen_path = current_manifest_record['snapshots']['qwen']
    current_clip_path = current_manifest_record['snapshots']['clip']
    current_model_config = yaml.load((current_motion_path / 'config.yml').read_text(), Loader=UniqueConfigLoader)
    current_gpu_device = torch.device('cuda:0')
    current_tensor_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    torch.cuda.reset_peak_memory_stats()

    current_progress_callback('encoding', 'Qwen3 텍스트 인코딩 · 가중치 CPU 대기 / 레이어 연산 CUDA')
    current_tokenizer_value = AutoTokenizer.from_pretrained(current_qwen_path, local_files_only=True, padding_side='right')
    current_system_prompt = read_encoder_system_prompt()
    current_message_records = [{'role': 'system', 'content': current_system_prompt}, {'role': 'user', 'content': current_request_record['prompt']}]
    current_encoded_text = current_tokenizer_value.apply_chat_template(current_message_records, tokenize=False, add_generation_prompt=False, enable_thinking=False)
    if current_encoded_text != build_encoder_input_preview(current_request_record['prompt']):
        raise ValueError('GUI 최종 프롬프트와 Qwen tokenizer 템플릿이 일치하지 않습니다.')
    write_record_atomically(current_attempt_path / 'encoder-prompt.json', build_prompt_provenance(current_encoded_text))
    current_encoder_config = current_model_config['train_pipeline_args']['text_encoder_cfg']
    current_maximum_tokens = current_encoder_config.get('max_length_llm', 512)
    current_marker_messages = [{'role': 'system', 'content': current_system_prompt}, {'role': 'user', 'content': '<BOC>'}]
    current_marker_text = current_tokenizer_value.apply_chat_template(current_marker_messages, tokenize=False, add_generation_prompt=False, enable_thinking=False)
    current_template_tokens = current_tokenizer_value(current_marker_text, add_special_tokens=True)['input_ids']
    current_marker_tokens = current_tokenizer_value('<BOC>', add_special_tokens=False)['input_ids']
    current_start_offsets = [current_token_index for current_token_index in range(len(current_template_tokens) - len(current_marker_tokens) + 1) if current_template_tokens[current_token_index:current_token_index + len(current_marker_tokens)] == current_marker_tokens]
    if len(current_start_offsets) != 1:
        raise ValueError('Qwen 입력 템플릿의 사용자 프롬프트 시작점을 찾지 못했습니다.')
    current_crop_start = current_start_offsets[0]
    current_token_batch = current_tokenizer_value(current_encoded_text, return_tensors='pt', truncation=False)
    if current_token_batch['input_ids'].shape[1] > current_crop_start + current_maximum_tokens:
        raise ValueError('텍스트 인코더 토큰 한도를 초과했습니다.')
    current_language_model = AutoModelForCausalLM.from_pretrained(current_qwen_path, local_files_only=True, torch_dtype=current_tensor_dtype, low_cpu_mem_usage=True).eval()
    # 전체 모델을 CUDA에 올리지 않는다. 각 레이어 forward 시에만 CUDA로 이동한다.
    cpu_offload(current_language_model, execution_device=current_gpu_device)
    with torch.inference_mode():
        current_language_output = current_language_model(**{current_field_name: current_tensor_value.to(current_gpu_device) for current_field_name, current_tensor_value in current_token_batch.items()}, output_hidden_states=True, use_cache=False)
        current_context_tensor = current_language_output.hidden_states[-1][:, current_crop_start:current_crop_start + current_maximum_tokens].float().cpu().clone()
        current_context_length = torch.tensor([current_context_tensor.shape[1]], dtype=torch.long)
    remove_hook_from_module(current_language_model, recurse=True)
    del current_language_output, current_language_model, current_token_batch, current_tokenizer_value
    gc.collect()
    torch.cuda.empty_cache()

    current_progress_callback('encoding', 'CLIP 텍스트 인코딩 · CUDA')
    current_clip_tokenizer = CLIPTokenizer.from_pretrained(current_clip_path, local_files_only=True)
    current_clip_inputs = current_clip_tokenizer([current_request_record['prompt']], return_tensors='pt', padding=True, truncation=False)
    if current_clip_inputs['input_ids'].shape[1] > 77:
        raise ValueError('CLIP 입력이 77토큰을 초과했습니다. 프롬프트를 줄이세요.')
    current_clip_model = CLIPTextModel.from_pretrained(current_clip_path, local_files_only=True).eval().to(current_gpu_device)
    with torch.inference_mode():
        current_sentence_tensor = current_clip_model(**{current_field_name: current_tensor_value.to(current_gpu_device) for current_field_name, current_tensor_value in current_clip_inputs.items()}).pooler_output.unsqueeze(1).cpu()
    del current_clip_model, current_clip_inputs
    gc.collect()
    torch.cuda.empty_cache()

    current_progress_callback('load', 'HY-Motion Lite 로딩 · 텍스트 인코더 해제 완료')
    current_pipeline_arguments = dict(current_model_config['train_pipeline_args'])
    current_pipeline_arguments['mean_std_dir'] = str(SOURCE_BUNDLE_DIRECTORY / 'stats')
    current_motion_pipeline = MotionFlowMatching(network_module=current_model_config['network_module'], network_module_args=current_model_config['network_module_args'], **current_pipeline_arguments)
    current_checkpoint_record = torch.load(current_motion_path / 'latest.ckpt', map_location='cpu', weights_only=True)
    current_load_result = current_motion_pipeline.load_state_dict(current_checkpoint_record['model_state_dict'], strict=False)
    # 공식 체크포인트는 별도 LFS 리그에서 로드한 이 다섯 버퍼를 포함하지 않는다.
    if set(current_load_result.missing_keys) != EXTERNAL_RIG_BUFFER_KEYS or current_load_result.unexpected_keys:
        raise ValueError(f'모션 체크포인트 스키마 불일치: {current_load_result}')
    del current_checkpoint_record
    current_motion_pipeline.eval().to(current_gpu_device)
    current_motion_pipeline.validation_steps = current_config_record['steps']
    current_progress_callback('inference', '모션 생성 중 · 원본 루트 이동·회전 유지')
    with torch.inference_mode(), torch.autocast('cuda', dtype=current_tensor_dtype):
        current_motion_output = current_motion_pipeline.generate(text=current_request_record['prompt'], seed_input=[current_request_record['seed']], duration_slider=current_request_record['duration_seconds'], cfg_scale=current_config_record['guidance_scale'], hidden_state_dict={'text_vec_raw': current_sentence_tensor.to(current_gpu_device), 'text_ctxt_raw': current_context_tensor.to(current_gpu_device), 'text_ctxt_raw_length': current_context_length.to(current_gpu_device)})
    current_output_arrays = {current_field_name: current_motion_output[current_field_name][0].float().cpu().numpy() for current_field_name in ('keypoints3d', 'rot6d', 'transl', 'root_rotations_mat', 'latent_denorm')}
    # 공식 keypoints3d에는 루트 평행이동이 포함되지 않는다. 월드 좌표를 별도로 복원한다.
    with torch.inference_mode():
        current_body_output = current_motion_pipeline.body_model({'rot6d': current_motion_output['rot6d'][0].float().to(current_gpu_device), 'trans': current_motion_output['transl'][0].float().to(current_gpu_device)})
        current_world_joints = current_body_output['keypoints3d'] + current_motion_output['transl'][0].float().to(current_gpu_device)[:, None, :]
        current_output_arrays['world_joints'] = current_world_joints.cpu().numpy()
    current_peak_memory = torch.cuda.max_memory_allocated() / 1024**2
    return current_output_arrays, {'source_revision': current_source_revision, 'model_snapshots': current_manifest_record['snapshots'], 'model_files': current_manifest_record['files'], 'peak_allocated_mib': round(current_peak_memory, 1), 'offload': 'Qwen CPU weights / CUDA layer execution; CLIP and motion sequential CUDA', 'postprocessing': 'upstream smoothing only; no in-place correction'}
