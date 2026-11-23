"""고정된 LightX2V 가속 가중치의 독립 준비와 무결성 확인."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVISION = '924563469bb8ac056e6171c3123a12903317606d'
FILENAME = 'lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors'
PATH = ROOT / '.model/wan22-animate2-loras' / FILENAME
SIZE = 738005744
SHA256 = '85c4a61c30e0497aa44b91d93a893b624708461a56fe5485183b28fa07e2dfb3'
URL = f'https://huggingface.co/Comfy-Org/Wan-Animate-2/resolve/{REVISION}/loras/{FILENAME}'


def inspect_lightx2v():
    try:
        if PATH.is_symlink() or not PATH.is_file() or PATH.stat().st_size != SIZE:
            return False
        with PATH.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest() == SHA256
    except OSError:
        return False


def validate_lightx2v():
    if not inspect_lightx2v():
        raise ValueError('Animate-2 LightX2V LoRA가 없거나 SHA-256 검증에 실패했습니다. 모델 관리에서 준비하세요.')


def prepare_lightx2v():
    from workflow.common.model_http_download import download_verified_http
    download_verified_http(URL, PATH, SHA256, 'wan22-animate2-lightx2v/lora', expected_total_bytes=SIZE)
    validate_lightx2v()
