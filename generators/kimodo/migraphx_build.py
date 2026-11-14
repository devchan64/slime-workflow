"""Kimodo DWPose의 장치별 MIGraphX 컴파일 결과를 관리한다."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
POSE_BUILD_CACHE_ROOT = WORKFLOW_ROOT_DIRECTORY/'.local/model-builds/kimodo-dwpose'


def resolve_pose_cache_directories(current_torch_module, current_ort_module, current_provider_module):
    """가중치, GPU 및 실행 라이브러리별로 캐시 경로를 격리한다."""
    from generators.kimodo.dwpose_runtime import FUN_POSE_MODEL_DIRECTORY, FUN_POSE_MODEL_NAMES
    current_gpu_properties = current_torch_module.cuda.get_device_properties(0)
    current_provider_path = Path(current_provider_module.get_library_paths()[0])
    with current_provider_path.open('rb') as current_provider_stream:
        current_provider_hash = hashlib.file_digest(current_provider_stream, 'sha256').hexdigest()
    current_library_spec = importlib.util.find_spec('migraphx_libs')
    if not current_library_spec or not current_library_spec.submodule_search_locations:
        raise RuntimeError('MIGraphX 라이브러리 위치를 찾을 수 없습니다.')
    current_library_root = Path(next(iter(current_library_spec.submodule_search_locations)))
    current_library_paths = sorted(current_library_root.glob('libmigraphx*.so*'))
    if not current_library_paths:
        raise RuntimeError('MIGraphX 라이브러리를 찾을 수 없습니다.')
    current_library_hashes = {}
    for current_library_path in current_library_paths:
        with current_library_path.open('rb') as current_library_stream:
            current_library_hashes[current_library_path.name] = hashlib.file_digest(current_library_stream, 'sha256').hexdigest()
    current_identity_record = {
        'schema': 1, 'gpu': current_gpu_properties.name,
        'architecture': getattr(current_gpu_properties, 'gcnArchName', ''),
        'hip': current_torch_module.version.hip, 'torch': current_torch_module.__version__,
        'onnxruntime': current_ort_module.__version__, 'provider_sha256': current_provider_hash, 'libraries': current_library_hashes,
        'compile_environment': {current_key_name: current_key_value for current_key_name, current_key_value in os.environ.items()
                                if current_key_name.startswith('MIGRAPHX_') or (current_key_name.startswith('ORT_MIGRAPHX_') and current_key_name != 'ORT_MIGRAPHX_CACHE_DIR')},
    }
    current_cache_directories = {}
    for current_model_name in FUN_POSE_MODEL_NAMES:
        current_model_path = (FUN_POSE_MODEL_DIRECTORY/current_model_name).with_suffix('.cuda.onnx')
        with current_model_path.open('rb') as current_model_stream:
            current_model_hash = hashlib.file_digest(current_model_stream, 'sha256').hexdigest()
        current_cache_identity = {**current_identity_record, 'model_sha256': current_model_hash}
        current_identity_hash = hashlib.sha256(json.dumps(current_cache_identity, sort_keys=True).encode()).hexdigest()
        current_cache_directories[current_model_name] = POSE_BUILD_CACHE_ROOT/current_identity_hash
    return current_cache_directories


def verify_pose_cache_files(current_cache_directory):
    """빈 캐시 또는 손상된 빌드 결과는 준비 완료로 취급하지 않는다."""
    current_manifest_path = current_cache_directory/'verified.json'
    try:
        current_manifest_record = json.loads(current_manifest_path.read_text())
        current_file_records = current_manifest_record['files']
        if not isinstance(current_file_records, dict) or not current_file_records:
            return False
        for current_file_name, current_file_hash in current_file_records.items():
            if Path(current_file_name).name != current_file_name:
                return False
            with (current_cache_directory/current_file_name).open('rb') as current_file_stream:
                if hashlib.file_digest(current_file_stream, 'sha256').hexdigest() != current_file_hash:
                    return False
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False


def build_pose_execution_cache():
    """두 고정 그래프를 컴파일하고 각 캐시 파일의 해시를 기록한다."""
    import numpy as np
    import torch
    import onnxruntime as ort
    import onnxruntime_ep_migraphx as current_provider_plugin
    from generators.kimodo.dwpose_runtime import create_fun_pose_detector
    from tools.review.common.generation_records import write_record_atomically
    current_cache_directories = resolve_pose_cache_directories(torch, ort, current_provider_plugin)
    for current_cache_directory in current_cache_directories.values():
        if current_cache_directory.exists() and not verify_pose_cache_files(current_cache_directory):
            import uuid
            current_cache_directory.rename(current_cache_directory.with_name(current_cache_directory.name+'.invalid-'+uuid.uuid4().hex))
        (current_cache_directory/'verified.json').unlink(missing_ok=True)
    current_detector_value = create_fun_pose_detector(current_build_cache=True)
    def sample_detector_outputs(current_detector_instance):
        current_sample_outputs = []
        for current_session_field, current_input_shape in (('session_det', (1, 3, 640, 640)), ('session_pose', (1, 3, 384, 288))):
            current_session_value = getattr(current_detector_instance, current_session_field)
            current_input_name = current_session_value.get_inputs()[0].name
            current_output_values = current_session_value.run(None, {current_input_name: np.zeros(current_input_shape, dtype=np.float32)})
            if not all(np.isfinite(current_output_value).all() for current_output_value in current_output_values):
                raise RuntimeError(f'MIGraphX 출력이 유효하지 않습니다: {current_session_field}')
            current_sample_outputs.append(current_output_values)
        return current_sample_outputs
    current_original_outputs = sample_detector_outputs(current_detector_value)
    del current_detector_value
    current_all_file_hashes = {}
    for current_model_name, current_cache_directory in current_cache_directories.items():
        current_cache_files = sorted(current_cache_directory.glob('*.mxr'))
        if not current_cache_files:
            raise RuntimeError(f'MIGraphX 빌드 결과가 없습니다: {current_model_name} · {current_cache_directory}')
        current_file_hashes = {}
        for current_cache_file in current_cache_files:
            with current_cache_file.open('rb') as current_cache_stream:
                current_file_hashes[current_cache_file.name] = hashlib.file_digest(current_cache_stream, 'sha256').hexdigest()
        current_all_file_hashes[current_cache_directory] = current_file_hashes
        print(f'MIGraphX 빌드 생성: {current_model_name} · {len(current_cache_files)}개', flush=True)
    current_reloaded_detector = create_fun_pose_detector(current_build_cache=True)
    current_reloaded_outputs = sample_detector_outputs(current_reloaded_detector)
    for current_first_outputs, current_second_outputs in zip(current_original_outputs, current_reloaded_outputs):
        for current_first_value, current_second_value in zip(current_first_outputs, current_second_outputs):
            np.testing.assert_allclose(current_first_value, current_second_value, rtol=1e-4, atol=1e-5)
    for current_cache_directory, current_file_hashes in current_all_file_hashes.items():
        write_record_atomically(current_cache_directory/'verified.json', {'files': current_file_hashes})
    print('MIGraphX 캐시 재로드 및 GPU 출력 비교 완료', flush=True)


def inspect_pose_execution_cache():
    """실제 실행과 동일한 환경 식별자로 두 캐시의 무결성을 확인한다."""
    import torch
    import onnxruntime as ort
    import onnxruntime_ep_migraphx as current_provider_plugin
    current_cache_directories = resolve_pose_cache_directories(torch, ort, current_provider_plugin)
    return bool(current_cache_directories) and all(verify_pose_cache_files(current_cache_directory)
                                                    for current_cache_directory in current_cache_directories.values())


if __name__ == '__main__':
    import argparse
    current_argument_parser = argparse.ArgumentParser()
    current_argument_parser.add_argument('--check', action='store_true')
    if current_argument_parser.parse_args().check:
        print(json.dumps({'ready': inspect_pose_execution_cache()}), flush=True)
    else:
        build_pose_execution_cache()
