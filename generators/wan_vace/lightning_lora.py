"""LightX2V T2V V1.1 가속 LoRA의 고정 다운로드와 무결성 검사."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVISION = '18bccf8884ec0a078eed79785eb4ef13ea16ce1e'
MODEL_FOLDER = 'Wan2.2-T2V-A14B-4steps-lora-rank64-Seko-V1.1'
FILES = {
    'high': ('high_noise_model.safetensors', 1226977424, '698321cb86bd30c4af06c9b84e656a1048c8cb54e06d50694536fb5de37fde41'),
    'low': ('low_noise_model.safetensors', 1226977424, 'ec95216e614b3c132c11bfb387b11feedf62163150ccc9068bca8a189771e75a'),
}
DIRECTORY = ROOT / '.model/wan22-vace-loras/lightning-t2v-v1.1'


def current_lightning_lora_directory():
    from workflow.common.model_storage_layout import resolve_wan_vace_lora_directory
    return resolve_wan_vace_lora_directory(ROOT/'.model', 'lightning')


def inspect_lightning_loras():
    for filename, size, digest in FILES.values():
        try:
            path = current_lightning_lora_directory() / filename
            if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
                return False
            with path.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                    return False
        except (OSError, ValueError):
            return False
    return True


def prepare_lightning_loras():
    from workflow.common.model_http_download import download_verified_http
    for name, (filename, size, digest) in FILES.items():
        url = f'https://huggingface.co/lightx2v/Wan2.2-Lightning/resolve/{REVISION}/{MODEL_FOLDER}/{filename}'
        download_verified_http(url, current_lightning_lora_directory() / filename, digest, 'wan22-vace-lightning/' + name, expected_total_bytes=size)
    if not inspect_lightning_loras():
        raise ValueError('Lightning LoRA 파일 검증 실패')
