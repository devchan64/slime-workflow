"""고정된 Wan 2.2 I2V 및 Lightning 파일 준비."""
import hashlib
import os
from pathlib import Path
import threading

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / '.model/wan22-i2v'
FILES = (
    ('base/high.safetensors', 'Comfy-Org/Wan-2.2', '5df3a4a3ed0628002308022198249dbbbd045d09', 'split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp16.safetensors', 28577914792, 'c21c21efa368d529a982a7d89dd11d86608b5937cae9a125d0ffe5491918a100'),
    ('base/low.safetensors', 'Comfy-Org/Wan-2.2', '5df3a4a3ed0628002308022198249dbbbd045d09', 'split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp16.safetensors', 28577914792, 'edb89340c8a6fbf1a70e76a839ae01eaf7d289f05ea1ebd6b1a3fc6f533826e9'),
    ('lightning/high.safetensors', 'lightx2v/Wan2.2-Lightning', '18bccf8884ec0a078eed79785eb4ef13ea16ce1e', 'Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1/high_noise_model.safetensors', 1226977424, 'd176c808d6fc461999b68e321efcb7501b20b8c3797523ed0df14f7d1deff11e'),
    ('lightning/low.safetensors', 'lightx2v/Wan2.2-Lightning', '18bccf8884ec0a078eed79785eb4ef13ea16ce1e', 'Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1/low_noise_model.safetensors', 1226977424, '024f21de095bc8fad9809ded3e9e49a2e170dcf27075da8145ba7d60d8aab7f9'),
)


def asset_path(relative):
    if relative.startswith('lightning/'):
        from workflow.common.model_storage_layout import resolve_wan_i2v_lightning_directory
        return resolve_wan_i2v_lightning_directory(DIRECTORY.parent) / relative.split('/', 1)[1]
    if relative.startswith('kungfu/'):
        from workflow.common.model_storage_layout import resolve_wan_i2v_kungfu_directory
        return resolve_wan_i2v_kungfu_directory(DIRECTORY.parent) / relative.split('/', 1)[1]
    return DIRECTORY / relative


def inspect_assets():
    for relative, _, _, _, size, digest in FILES:
        try:
            path = asset_path(relative)
        except ValueError:
            return False
        try:
            if path.is_symlink() or not path.is_file():
                return False
            before = path.stat()
            if before.st_size != size:
                return False
            with path.open('rb') as stream:
                opened = os.fstat(stream.fileno())
                identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
                if identity(opened) != identity(before) or hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                    return False
                if identity(os.fstat(stream.fileno())) != identity(before):
                    return False
            if path.is_symlink() or identity(path.stat()) != identity(before):
                return False
        except OSError:
            return False
    return True


_status_lock = threading.Lock()
_status_state = {'signature': None, 'state': 'unverified', 'thread': None}


def _asset_signature():
    """Observe file identity without treating file presence as integrity."""
    signature = []
    for relative, _, _, _, size, _ in FILES:
        try:
            path = asset_path(relative)
        except ValueError:
            return None
        try:
            if path.is_symlink() or not path.is_file():
                return None
            info = path.stat()
            if info.st_size != size:
                return None
            signature.append((info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns))
        except OSError:
            return None
    return tuple(signature)


def inspect_assets_nonblocking():
    """Return promptly; a verified result applies only to unchanged files."""
    signature = _asset_signature()
    with _status_lock:
        if signature is None:
            _status_state.update(signature=None, state='missing')
            return 'missing'
        if _status_state['signature'] == signature and _status_state['state'] in ('verified', 'invalid'):
            return _status_state['state']
        if _status_state['thread'] is not None and _status_state['thread'].is_alive():
            return 'verifying'
        _status_state.update(signature=signature, state='verifying')
        def verify():
            try:
                valid = inspect_assets()
                unchanged = _asset_signature() == signature
            except Exception:
                valid, unchanged = False, False
            with _status_lock:
                if _status_state['signature'] == signature:
                    _status_state['state'] = ('verified' if valid else 'invalid') if unchanged else 'unverified'
        worker = threading.Thread(target=verify, name='wan22-i2v-asset-verification', daemon=True)
        _status_state['thread'] = worker
        worker.start()
        return 'verifying'


def prepare_assets():
    from workflow.common.model_http_download import download_verified_http
    for relative, repo, revision, remote, size, digest in FILES:
        url = f'https://huggingface.co/{repo}/resolve/{revision}/{remote}'
        download_verified_http(url, asset_path(relative), digest, 'wan22-i2v-assets/' + relative, expected_total_bytes=size)
    if not inspect_assets():
        raise ValueError('I2V 모델 또는 LoRA 파일 검증 실패')
