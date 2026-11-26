"""검증된 H3 파일 경로와 크기·해시."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
ASSETS=ROOT/'.model/minimax-h3-diffusers';OLD=ROOT/'.model/minimax-h3-i2v'
FILES=[(OLD/'diffusion_models/minimax_h3_fl2va_pruned_fp8_scaled.safetensors',20958205608,'12944c1f7791637e7de12208aef04da82bd26b95271b1b47d817364315ade993'),(OLD/'text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors',27141342152,'bc2ced0fbea64757fa9acddccfc0b3f4819d1dcf1da6c124d690d368be283923'),(ASSETS/'audio_vae/diffusion_pytorch_model.safetensors',605429340,'52c59e67ba8de5477c81bfbced0327aabf500f1bfdeefd5ee754529241cb26cb'),(ASSETS/'vae/diffusion_pytorch_model-00001-of-00003.safetensors',5061033024,'72f4c6be84ac0674f27398cde991dd9d719762f3952c4921aa66b2ce542f6374'),(ASSETS/'vae/diffusion_pytorch_model-00002-of-00003.safetensors',4955986528,'2e05e8bc23fa4071043e17fd242be8acd0685e781a43987432b2eae925be4198'),(ASSETS/'vae/diffusion_pytorch_model-00003-of-00003.safetensors',398539336,'c05d6ac4b1a33de372799d708531da6320f6a3ce6d1ce6d895e770988e004a39'),(ASSETS/'loras/minimax_h3_fl2v_turbo_8step_v1.0_bf16.safetensors',1383677768,'e16ac20824d6e6649b193806f8fb095639bd9946c97b1bb84b4248eab1cc807f')]


def current_files(files=None):
    """Resolve the shared INT8 encoder when a new worker or status check starts."""
    from workflow.common.model_storage_layout import resolve_minimax_qwen_encoder
    records = FILES if files is None else files
    legacy = OLD/'text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors'
    return [(resolve_minimax_qwen_encoder(ROOT/'.model', 'int8-convrot') if path == legacy else path, size, digest)
            for path, size, digest in records]


def prepare_int8_encoder_from_backup():
    """Restore the pinned encoder from a configured backup without overwriting."""
    from workflow.common.model_backup_restore import restore_verified_backup
    from workflow.common.model_vace_encoder_move import _verify
    from workflow.common.model_download_records import track_model_download
    path, size, digest = current_files()[1]
    if path.is_symlink():
        raise ValueError('인코더 파일에 심볼릭 링크를 사용할 수 없습니다.')
    with track_model_download('minimax-h3-int8-encoder/weights') as record:
        if path.exists():
            record.update(stage='기존 파일 SHA-256 검증', total_bytes=size)
            info = _verify(path, size, digest)
            _write_int8_verification(path, info, digest)
            record.update(stage='기존 파일 검증 완료', bytes=size, total_bytes=size)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        record.update(stage='Samba 백업 확인 중', total_bytes=size)
        if not restore_verified_backup(path, digest, size,
                report=lambda count: record.update(stage='Samba에서 복원', bytes=count, total_bytes=size),
                outcome=lambda reason: record.update(backup_warning=reason)):
            raise ValueError('고정 해시와 일치하는 Samba 백업 인코더를 찾지 못했습니다.')
        info = _verify(path, size, digest)
        _write_int8_verification(path, info, digest)
        record.update(stage='Samba 복원 검증 완료', bytes=size, total_bytes=size)


def _int8_record_path():
    return ROOT/'.local/model-catalog/minimax-int8-verified.json'


def _signature_for(path, info):
    return [str(path.relative_to(ROOT)), info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def _write_int8_verification(path, info, digest):
    from workflow.common.generation_records import write_record_atomically
    record_path = _int8_record_path()
    if any(part.is_symlink() for part in (ROOT/'.local', record_path.parent, record_path)):
        raise ValueError('검증 기록 경로에 심볼릭 링크를 사용할 수 없습니다.')
    if path.is_symlink() or _signature_for(path, path.stat()) != _signature_for(path, info):
        raise ValueError('검증 후 인코더 파일이 변경됐습니다.')
    record_path.parent.mkdir(parents=True, exist_ok=True)
    write_record_atomically(record_path, {'signature': _signature_for(path, info), 'sha256': digest})


def _int8_signature():
    try:
        path, size, _ = current_files()[1]
        if path.is_symlink():
            return 'invalid', None
        if not path.exists():
            return 'missing', None
        if not path.is_file():
            return 'invalid', None
        info = path.stat()
        if info.st_size != size:
            return 'invalid', None
        return 'present', _signature_for(path, info)
    except (OSError, ValueError):
        return 'invalid', None


def inspect_int8_encoder_nonblocking():
    """Read a prior verification receipt without hashing during status lookup."""
    state, signature = _int8_signature()
    if state != 'present':
        return state
    try:
        path = _int8_record_path()
        if (path.is_symlink() or path.parent.is_symlink() or (ROOT/'.local').is_symlink()
                or not path.is_file() or path.stat().st_size > 4096):
            return 'unverified'
        record = json.loads(path.read_text(encoding='utf-8'))
        if record.get('signature') == signature and record.get('sha256') == current_files()[1][2]:
            return 'verified'
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return 'unverified'
