"""Wan 2.1 Fun 1.3B 가중치와 참조 인코더의 고정 출처 및 무결성 검증."""
import hashlib
import os
from functools import lru_cache
from pathlib import Path

WAN13_REPOSITORY_NAME = 'alibaba-pai/Wan2.1-Fun-V1.1-1.3B-Control'
WAN13_REVISION_HASH = 'a116c52b08182f7a5916eae7a47fcd61a9467a04'
WAN13_CLIP_REPOSITORY_NAME = 'Comfy-Org/Wan-2.1'
WAN13_CLIP_REVISION_HASH = '2bb519992ec7fb8ca66f6807335f67a92bf13e0b'
WAN13_MODEL_FILES = {
    'diffusion_pytorch_model.safetensors': (3129305312, '4d51c942b0cfe92821c29b37fdb062756e026280084746ba1cc5d5dba39ee684'),
    'split_files/clip_vision/clip_vision_h.safetensors': (1264219396, '64a7ef761bfccbadbaa3da77366aac4185a6c58fa5de5f589b42a65bcc21f161'),
}
WAN13_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
WAN13_MODEL_DIRECTORY = WAN13_WORKSPACE_ROOT / '.model/wan21-fun-control-1.3b'


@lru_cache(maxsize=8)
def hash_wan13_cached_file(current_model_path, current_file_size, current_file_mtime, current_file_ctime):
    with current_model_path.open('rb') as current_model_stream:
        return hashlib.file_digest(current_model_stream, 'sha256').hexdigest()


def verify_wan13_model_file(current_model_path, expected_file_size, expected_file_hash):
    if current_model_path.is_symlink() or not current_model_path.is_file():
        return False
    current_file_stat = current_model_path.stat()
    if current_file_stat.st_size != expected_file_size:
        return False
    return hash_wan13_cached_file(current_model_path, current_file_stat.st_size, current_file_stat.st_mtime_ns, current_file_stat.st_ctime_ns) == expected_file_hash


def inspect_wan13_model_files():
    current_missing_files = [current_file_name for current_file_name, (current_file_size, current_file_hash) in WAN13_MODEL_FILES.items()
                             if not verify_wan13_model_file(WAN13_MODEL_DIRECTORY / current_file_name, current_file_size, current_file_hash)]
    return {'ready': not current_missing_files, 'missing': current_missing_files}


def validate_wan13_generation_assets():
    from generators.wan_fun.contracts import FUN_MODEL_FILES, FUN_PYTHON_EXECUTABLE, FUN_RUNTIME_DIRECTORY, FUN_WORKSPACE_ROOT
    current_model_status = inspect_wan13_model_files()
    if not current_model_status['ready']:
        raise ValueError('1.3B 모델과 참조 인코더를 먼저 준비하세요: ' + ', '.join(current_model_status['missing']))
    for current_shared_name in ('encoder', 'vae'):
        current_shared_path, current_shared_size = FUN_MODEL_FILES[current_shared_name]
        current_shared_file = FUN_WORKSPACE_ROOT / current_shared_path
        if not current_shared_file.is_file() or current_shared_file.stat().st_size != current_shared_size:
            raise ValueError('공용 텍스트 인코더와 VAE를 먼저 준비하세요.')
    current_revision_path = FUN_RUNTIME_DIRECTORY / 'ComfyUI/PINNED_REVISION'
    if not FUN_PYTHON_EXECUTABLE.is_file() or not current_revision_path.is_file() or current_revision_path.read_text().strip() != 'b8730510db30c8858e1e5d8e126ef19eac395560':
        raise ValueError('Wan Fun ROCm 실행 환경을 먼저 준비하세요.')


def download_wan13_model_files():
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    import huggingface_hub.constants as current_hub_constants
    current_hub_constants.HF_HUB_DISABLE_XET = True
    from tools.review.common.model_huggingface_download import tracked_hf_hub_download
    for current_file_name, (current_file_size, current_file_hash) in WAN13_MODEL_FILES.items():
        current_file_path = WAN13_MODEL_DIRECTORY / current_file_name
        if not verify_wan13_model_file(current_file_path, current_file_size, current_file_hash):
            if current_file_path.exists():
                raise ValueError(f'기존 모델 파일의 크기 또는 해시가 다릅니다: {current_file_name}')
            current_repository_name = WAN13_CLIP_REPOSITORY_NAME if current_file_name.startswith('split_files/') else WAN13_REPOSITORY_NAME
            current_revision_hash = WAN13_CLIP_REVISION_HASH if current_file_name.startswith('split_files/') else WAN13_REVISION_HASH
            tracked_hf_hub_download(repo_id=current_repository_name, revision=current_revision_hash,
                                    filename=current_file_name, local_dir=WAN13_MODEL_DIRECTORY)
            if not verify_wan13_model_file(current_file_path, current_file_size, current_file_hash):
                raise ValueError(f'다운로드한 모델 파일의 크기 또는 해시가 다릅니다: {current_file_name}')
