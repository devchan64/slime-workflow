"""고정 MoMask 모델로 HumanML3D 관절 모션을 실험 경로에 생성한다."""
from __future__ import annotations

import ast
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import os
import sys
import threading
import time
import traceback
import yaml
from pathlib import Path
from types import SimpleNamespace

WORKFLOW_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CONFIG_PATH = WORKFLOW_REPOSITORY_ROOT / 'generators/momask/config/momask-runtime.yaml'
MOTION_MODEL_SOURCE = None
MOTION_MODEL_BUNDLE = None
MOTION_CLIP_WEIGHTS = None
MODEL_MANIFEST_PATH = None
MOTION_RUN_DIRECTORY = WORKFLOW_REPOSITORY_ROOT / '.tmp' / datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
MOTION_ASSET_DIRECTORY = MOTION_RUN_DIRECTORY / 'motion'
MOTION_FRAME_COUNT = 96
MOTION_FRAME_RATE = 20
MOTION_RANDOM_SEED = 10107
MOTION_TEXT_PROMPT = 'A person walks in a straight line across the room.'
MOTION_TRANSFORMER_NAME = 't2m_nlayer8_nhead6_ld384_ff1024_cdp0.1_rvq6ns'
MOTION_RESIDUAL_NAME = 'tres_nlayer8_ld384_ff1024_rvq6ns_cdp0.2_sw'


def load_runtime_config(config_path):
    values = yaml.safe_load(Path(config_path).read_text(encoding='utf-8'))
    required = {'schema_version', 'runtime_id', 'source_root', 'model_manifest', 'model_bundle', 'clip_weights', 'models', 'inference'}
    if not isinstance(values, dict) or set(values) != required or values['schema_version'] != 1:
        raise ValueError(f'잘못된 MoMask 실행기 설정: {config_path}')
    if values['runtime_id'] != 'momask-humanml3d-runner-v1':
        raise ValueError('지원하지 않는 MoMask 실행기')
    return values


def configure_runtime(config_path):
    global MOTION_MODEL_SOURCE, MOTION_MODEL_BUNDLE, MOTION_CLIP_WEIGHTS, MODEL_MANIFEST_PATH, MOTION_FRAME_RATE, MOTION_RANDOM_SEED, MOTION_TRANSFORMER_NAME, MOTION_RESIDUAL_NAME
    values = load_runtime_config(config_path)
    MOTION_MODEL_SOURCE = (WORKFLOW_REPOSITORY_ROOT / values['source_root']).resolve()
    MOTION_MODEL_BUNDLE = (WORKFLOW_REPOSITORY_ROOT / values['model_bundle']).resolve()
    MOTION_CLIP_WEIGHTS = (WORKFLOW_REPOSITORY_ROOT / values['clip_weights']).resolve()
    MODEL_MANIFEST_PATH = (WORKFLOW_REPOSITORY_ROOT / values['model_manifest']).resolve()
    MOTION_FRAME_RATE = values['inference']['fps']
    MOTION_RANDOM_SEED = values['inference']['seed']
    MOTION_TRANSFORMER_NAME = values['models']['transformer']
    MOTION_RESIDUAL_NAME = values['models']['residual']


def calculate_file_digest(model_file_path):
    model_file_digest = hashlib.sha256()
    with model_file_path.open('rb') as model_file_handle:
        for model_file_chunk in iter(lambda: model_file_handle.read(1024 * 1024), b''):
            model_file_digest.update(model_file_chunk)
    return model_file_digest.hexdigest()


def execute_motion_attempt():
    """모델은 고정된 준비 기록으로 검증하고 CUDA에서만 추론한다."""
    prepared_model_record = json.loads(MODEL_MANIFEST_PATH.read_text())
    for prepared_file_record in prepared_model_record['files']:
        prepared_model_path = WORKFLOW_REPOSITORY_ROOT / prepared_file_record['path']
        if calculate_file_digest(prepared_model_path) != prepared_file_record['sha256']:
            raise ValueError(f'준비 파일 SHA-256 불일치: {prepared_model_path}')
    if MOTION_ASSET_DIRECTORY.exists():
        raise FileExistsError(f'불변 모션 자산 덮어쓰기 금지: {MOTION_ASSET_DIRECTORY}')

    import numpy as numpy_runtime_module
    import torch as torch_runtime_module

    if not torch_runtime_module.cuda.is_available():
        raise RuntimeError('샌드박스 밖 실행에서 CUDA를 사용할 수 없음')
    torch_runtime_module.set_num_threads(4)
    motion_device_handle = torch_runtime_module.device('cuda:0')
    # 고정 upstream의 제거된 np.float 사용에 대한 명시적 NumPy 2 호환 처리다.
    numpy_runtime_module.float = float
    sys.path.insert(0, str(MOTION_MODEL_SOURCE))
    from models.vq.model import RVQVAE, LengthEstimator
    from models.mask_transformer.transformer import MaskTransformer, ResidualTransformer
    from utils.get_opt import get_opt
    from utils.fixseed import fixseed
    from utils.motion_process import recover_from_ric

    # AiBook P7-5.15와 같이 변경 없는 upstream 로더만 사용한다.
    # BVH 렌더러의 불필요한 구버전 의존성은 이 관절 생성 단계에서 로드하지 않는다.
    upstream_module_tree = ast.parse((MOTION_MODEL_SOURCE / 'gen_t2m.py').read_text())
    upstream_function_module = ast.Module(body=[upstream_tree_node for upstream_tree_node in upstream_module_tree.body if isinstance(upstream_tree_node, ast.FunctionDef)], type_ignores=[])
    upstream_loader_scope = dict(torch=torch_runtime_module, pjoin=os.path.join, RVQVAE=RVQVAE, LengthEstimator=LengthEstimator, MaskTransformer=MaskTransformer, ResidualTransformer=ResidualTransformer, clip_version=str(MOTION_CLIP_WEIGHTS))
    exec(compile(upstream_function_module, str(MOTION_MODEL_SOURCE / 'gen_t2m.py'), 'exec'), upstream_loader_scope)
    checkpoint_stage_root = MOTION_RUN_DIRECTORY / 'checkpoints'
    checkpoint_stage_root.mkdir(exist_ok=True)
    checkpoint_bundle_link = checkpoint_stage_root / 't2m'
    if checkpoint_bundle_link.exists():
        if checkpoint_bundle_link.resolve() != MOTION_MODEL_BUNDLE:
            raise ValueError('체크포인트 링크 대상 불일치')
    else:
        checkpoint_bundle_link.symlink_to(MOTION_MODEL_BUNDLE, target_is_directory=True)
    motion_runtime_options = SimpleNamespace(name=MOTION_TRANSFORMER_NAME, device=motion_device_handle)
    motion_transformer_options = get_opt(str(MOTION_MODEL_BUNDLE / MOTION_TRANSFORMER_NAME / 'opt.txt'), motion_device_handle, checkpoints_dir=str(checkpoint_stage_root))
    motion_quantizer_options = get_opt(str(MOTION_MODEL_BUNDLE / motion_transformer_options.vq_name / 'opt.txt'), motion_device_handle, checkpoints_dir=str(checkpoint_stage_root))
    motion_quantizer_options.dim_pose = 263
    motion_residual_options = get_opt(str(MOTION_MODEL_BUNDLE / MOTION_RESIDUAL_NAME / 'opt.txt'), motion_device_handle, checkpoints_dir=str(checkpoint_stage_root))
    print('모델 GPU 로딩 시작', flush=True)
    motion_quantizer_model, _ = upstream_loader_scope['load_vq_model'](motion_quantizer_options)
    motion_transformer_options.num_tokens = motion_quantizer_options.nb_code
    motion_transformer_options.num_quantizers = motion_quantizer_options.num_quantizers
    motion_transformer_options.code_dim = motion_quantizer_options.code_dim
    motion_residual_model = upstream_loader_scope['load_res_model'](motion_residual_options, motion_quantizer_options, motion_runtime_options)
    motion_transformer_model = upstream_loader_scope['load_trans_model'](motion_transformer_options, motion_runtime_options, 'latest.tar')
    for motion_inference_model in [motion_quantizer_model, motion_residual_model, motion_transformer_model]:
        motion_inference_model.eval().to(motion_device_handle)
    motion_normalization_mean = numpy_runtime_module.load(MOTION_MODEL_BUNDLE / motion_transformer_options.vq_name / 'meta/mean.npy')
    motion_normalization_std = numpy_runtime_module.load(MOTION_MODEL_BUNDLE / motion_transformer_options.vq_name / 'meta/std.npy')
    fixseed(MOTION_RANDOM_SEED)
    print(f'{MOTION_FRAME_COUNT}프레임 MoMask 관절 모션 추론 시작', flush=True)
    with torch_runtime_module.inference_mode():
        motion_token_lengths = torch_runtime_module.tensor([MOTION_FRAME_COUNT // 4], device=motion_device_handle)
        motion_generated_tokens = motion_transformer_model.generate([MOTION_TEXT_PROMPT], motion_token_lengths, timesteps=18, cond_scale=4, temperature=1, topk_filter_thres=.9, gsample=False)
        motion_generated_tokens = motion_residual_model.generate(motion_generated_tokens, [MOTION_TEXT_PROMPT], motion_token_lengths, temperature=1, cond_scale=5)
        motion_feature_array = motion_quantizer_model.forward_decoder(motion_generated_tokens).cpu().numpy()[0] * motion_normalization_std + motion_normalization_mean
        motion_joint_array = recover_from_ric(torch_runtime_module.from_numpy(motion_feature_array).float(), 22).numpy()
    if motion_joint_array.shape != (MOTION_FRAME_COUNT, 22, 3) or not numpy_runtime_module.isfinite(motion_joint_array).all():
        raise ValueError('MoMask 관절 출력 형태 또는 유한값 검증 실패')
    MOTION_ASSET_DIRECTORY.mkdir(parents=True)
    motion_output_path = MOTION_ASSET_DIRECTORY / 'motion.npz'
    numpy_runtime_module.savez_compressed(motion_output_path, joints=motion_joint_array, features=motion_feature_array)
    motion_asset_record = {
        'asset_id': 'walk-travel', 'version': 1, 'status': 'generated_review_required',
        'file': 'motion.npz', 'sha256': calculate_file_digest(motion_output_path),
        'fps': MOTION_FRAME_RATE, 'frames': MOTION_FRAME_COUNT, 'joint_schema': 'HumanML3D-22',
        'coordinate_system': 'upstream recover_from_ric: y-up, meters', 'root_motion': 'preserved',
        'prompt': MOTION_TEXT_PROMPT, 'seed': MOTION_RANDOM_SEED, 'mask_steps': 18,
        'mask_guidance': 4, 'residual_guidance': 5, 'temperature': 1, 'topk_filter_threshold': .9,
        'source_revision': prepared_model_record['source_revision'],
        'model_manifest_sha256': calculate_file_digest(MODEL_MANIFEST_PATH),
        'gpu': torch_runtime_module.cuda.get_device_name(), 'torch': torch_runtime_module.__version__,
        'quality_warnings': ['WARN: 접지·발 교대·루프 구간 검수 전 원본 모션'],
    }
    (MOTION_ASSET_DIRECTORY / 'artifact.json').write_text(json.dumps(motion_asset_record, ensure_ascii=False, indent=2) + '\n')
    print(f'재사용 모션 보존 완료: {motion_output_path}', flush=True)


def run_logged_attempt():
    """자식 GPU 작업의 로그·5초 heartbeat와 실패 원인을 보존한다."""
    import subprocess

    MOTION_RUN_DIRECTORY.mkdir(parents=True, exist_ok=True)
    motion_log_path = MOTION_RUN_DIRECTORY / 'generation.log'
    heartbeat_stop_event = threading.Event()
    motion_log_lines = []

    def print_heartbeat_message():
        while not heartbeat_stop_event.wait(5):
            heartbeat_log_line = f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")}/motion-depth/heartbeat 로그행={len(motion_log_lines)} 최근={motion_log_lines[-1:]}; 모션파일존재={(MOTION_ASSET_DIRECTORY / "motion.npz").exists()}'
            print(heartbeat_log_line, flush=True)
            with motion_log_path.open('a') as heartbeat_log_handle:
                heartbeat_log_handle.write(heartbeat_log_line + '\n')

    threading.Thread(target=print_heartbeat_message, daemon=True).start()
    print(f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")}/motion-depth/start model_id=MoMask-HumanML3D model_root={MOTION_MODEL_BUNDLE} binary_path={sys.executable}', flush=True)
    try:
        with subprocess.Popen([sys.executable, '-u', str(Path(__file__).resolve()), '--worker', '--output-dir', str(MOTION_RUN_DIRECTORY), '--runtime-config', str(RUNTIME_CONFIG_PATH), '--frames', str(MOTION_FRAME_COUNT), '--prompt', MOTION_TEXT_PROMPT], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as motion_process_handle:
            for motion_output_line in motion_process_handle.stdout:
                motion_log_lines.append(motion_output_line.rstrip())
                print(motion_output_line, end='', flush=True)
                with motion_log_path.open('a') as motion_log_handle:
                    motion_log_handle.write(motion_output_line)
            motion_return_code = motion_process_handle.wait()
        (MOTION_RUN_DIRECTORY / 'attempt.json').write_text(json.dumps({'exit_code': motion_return_code, 'motion_created': (MOTION_ASSET_DIRECTORY / 'motion.npz').is_file(), 'smpl_created': False, 'depth_created': False, 'log': str(motion_log_path), 'failure_tail': motion_log_lines[-15:] if motion_return_code else []}, ensure_ascii=False, indent=2) + '\n')
        if motion_return_code:
            print('실패 로그 tail:\n' + '\n'.join(motion_log_lines[-15:]), flush=True)
            raise SystemExit(motion_return_code)
    finally:
        heartbeat_stop_event.set()


if __name__ == '__main__':
    argument_value_parser = argparse.ArgumentParser(description=__doc__)
    argument_value_parser.add_argument('--worker', action='store_true')
    argument_value_parser.add_argument('--output-dir', type=Path, default=MOTION_RUN_DIRECTORY)
    argument_value_parser.add_argument('--runtime-config', type=Path, default=RUNTIME_CONFIG_PATH)
    argument_value_parser.add_argument('--prompt')
    argument_value_parser.add_argument('--frames', type=int)
    parsed_argument_values = argument_value_parser.parse_args()
    MOTION_RUN_DIRECTORY = parsed_argument_values.output_dir.resolve()
    if parsed_argument_values.prompt:
        MOTION_TEXT_PROMPT = parsed_argument_values.prompt
    if parsed_argument_values.frames:
        if parsed_argument_values.frames < 8 or parsed_argument_values.frames % 4:
            raise ValueError('프레임 수는 8 이상 4의 배수여야 합니다.')
        MOTION_FRAME_COUNT = parsed_argument_values.frames
    if not MOTION_RUN_DIRECTORY.is_relative_to(WORKFLOW_REPOSITORY_ROOT / '.tmp'):
        raise ValueError('후보 모션 출력은 저장소 .tmp 하위만 허용합니다.')
    MOTION_ASSET_DIRECTORY = MOTION_RUN_DIRECTORY / 'motion'
    RUNTIME_CONFIG_PATH = parsed_argument_values.runtime_config.resolve()
    configure_runtime(RUNTIME_CONFIG_PATH)
    if parsed_argument_values.worker:
        try:
            execute_motion_attempt()
        except Exception:
            traceback.print_exc()
            raise SystemExit(1)
    else:
        if not MODEL_MANIFEST_PATH.is_file():
            raise FileNotFoundError(f'MoMask 모델 무결성 매니페스트 누락: {MODEL_MANIFEST_PATH}')
        if MOTION_RUN_DIRECTORY.exists():
            raise FileExistsError(f'실험 경로 덮어쓰기 금지: {MOTION_RUN_DIRECTORY}')
        MOTION_RUN_DIRECTORY.mkdir(parents=True)
        (MOTION_RUN_DIRECTORY / 'prompt.txt').write_text(MOTION_TEXT_PROMPT + '\n')
        run_logged_attempt()
