"""고정 출처의 VACE Q8_0 GGUF 전문가 파일 준비와 무결성 검증."""
import hashlib
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / '.model/wan22-vace-q8'
REPOSITORY = 'QuantStack/Wan2.2-VACE-Fun-A14B-GGUF'
REVISION = '93b339260b1d819e2c171dd7ca9e66a761d4a84d'
_VERIFIED_SIGNATURE = None
_VERIFY_LOCK = threading.Lock()
FILES = {
    'high': ('HighNoise/Wan2.2-VACE-Fun-A14B-high-noise-Q8_0.gguf', 18663274400, '89b43d99ff72434c6cb7ad7df0053396d879f9c407c43f896b1e80b42a384eea'),
    'low': ('LowNoise/Wan2.2-VACE-Fun-A14B-low-noise-Q8_0.gguf', 18663274400, '854d70e55c565201332cc7ea21a37b81a5aa5882d1a00368d9d237ea65c37cf9'),
}

def inspect_q8_assets():
    global _VERIFIED_SIGNATURE
    with _VERIFY_LOCK:
        try:
            signatures = []
            for name, size, digest in FILES.values():
                path = DIRECTORY / name
                if path.is_symlink() or not path.is_file():
                    return False
                stat = path.stat()
                if stat.st_size != size:
                    return False
                signatures.append((str(path), stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, digest))
            signature = tuple(signatures)
            if signature == _VERIFIED_SIGNATURE:
                return True
            for name, _, digest in FILES.values():
                with (DIRECTORY / name).open('rb') as stream:
                    if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                        return False
            for name, size, digest in FILES.values():
                path = DIRECTORY / name
                stat = path.stat()
                if (str(path), stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, digest) not in signatures or path.is_symlink():
                    return False
            _VERIFIED_SIGNATURE = signature
            return True
        except OSError:
            return False


def prepare_q8_assets():
    from workflow.common.model_http_download import download_verified_http
    for stage, (name, size, digest) in FILES.items():
        url = f'https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{name}'
        download_verified_http(url, DIRECTORY / name, digest, 'wan22-vace-q8/' + stage, expected_total_bytes=size)
    if not inspect_q8_assets():
        raise ValueError('VACE Q8 모델 파일 검증 실패')
