"""격투 LoRA의 고정 출처와 독립 모델 준비."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / '.model/wan22-vace-loras/wan2.2fighting_high_noise.safetensors'
SHA256 = '48a0b95c45aaa27e7c3c9bc2aa17d2ec19c37002b44b9997924d41a91b759fa2'
SIZE = 38435368
URL = 'https://huggingface.co/r4tn4/Bubble/resolve/338e12cb179abf0573b61c310db6163018effdde/wan2.2fighting_high_noise.safetensors'


def inspect_fighting_lora():
    try:
        if PATH.is_symlink() or not PATH.is_file() or PATH.stat().st_size != SIZE:
            return False
        with PATH.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest() == SHA256
    except OSError:
        return False


def prepare_fighting_lora():
    from workflow.common.model_http_download import download_verified_http
    download_verified_http(URL, PATH, SHA256, 'wan22-fighting-lora/high', expected_total_bytes=SIZE)
    if not inspect_fighting_lora():
        raise ValueError('격투 LoRA 파일 검증 실패')
