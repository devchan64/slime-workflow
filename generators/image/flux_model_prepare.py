"""고정 공식 FLUX 파일을 격리 경로에 내려받고 검증해 게시한다."""
import ctypes
import errno
import fcntl
import hashlib
import os
from pathlib import Path, PurePosixPath

import yaml
from tools.management.common.strict_yaml import UniqueConfigLoader

FLUX_WORKSPACE_DIRECTORY = Path(__file__).resolve().parents[2]
FLUX_MODEL_DIRECTORY = FLUX_WORKSPACE_DIRECTORY / '.model/flux-3-image-klein'
FLUX_MODEL_LOCK_PATH = Path(__file__).with_name('flux-model-lock.yaml')
FLUX_MODEL_REPOSITORY = 'black-forest-labs/flux-3-image-klein'
FLUX_MODEL_REVISION = '09561231f44e41381c461caf53d5452005a60ac9'


def read_flux_model_lock(current_lock_path=FLUX_MODEL_LOCK_PATH):
    current_lock_record = yaml.load(current_lock_path.read_text(encoding='utf-8'), Loader=UniqueConfigLoader)
    if not isinstance(current_lock_record, dict) or set(current_lock_record) != {'repository', 'revision', 'files'}:
        raise ValueError('FLUX 모델 잠금 형식 오류')
    if current_lock_record['repository'] != FLUX_MODEL_REPOSITORY or current_lock_record['revision'] != FLUX_MODEL_REVISION:
        raise ValueError('FLUX 모델 출처 또는 리비전 오류')
    current_file_records = current_lock_record['files']
    if not isinstance(current_file_records, list) or not current_file_records:
        raise ValueError('FLUX 모델 잠금 파일 목록 오류')
    current_file_names = set()
    for current_file_record in current_file_records:
        if not isinstance(current_file_record, dict) or set(current_file_record) != {'path', 'size', 'hash_type', 'digest'}:
            raise ValueError('FLUX 모델 잠금 파일 항목 오류')
        current_file_name = current_file_record['path']
        if not isinstance(current_file_name, str) or not current_file_name or PurePosixPath(current_file_name).as_posix() != current_file_name or any(current_name_part in ('.', '..') for current_name_part in current_file_name.split('/')) or current_file_name.startswith('/') or current_file_name in current_file_names:
            raise ValueError('FLUX 모델 잠금 경로 오류')
        current_hash_type = current_file_record['hash_type']
        current_hash_length = {'sha256': 64, 'git-sha1': 40}.get(current_hash_type)
        current_file_digest = current_file_record['digest']
        if current_hash_length is None or not isinstance(current_file_digest, str) or len(current_file_digest) != current_hash_length or any(current_hex_digit not in '0123456789abcdef' for current_hex_digit in current_file_digest) or type(current_file_record['size']) is not int or current_file_record['size'] < 0:
            raise ValueError('FLUX 모델 잠금 해시 또는 크기 오류')
        current_file_names.add(current_file_name)
    current_required_names = {'LICENSE.md', 'NOTICE.md', 'manifest.json', 'modular_model_index.json',
        'text_encoder/config.json', 'text_encoder/tokenizer.json', 'text_encoder/tokenizer_config.json',
        'text_encoder/model.safetensors.index.json', 'text_encoder/model-00001-of-00002.safetensors',
        'text_encoder/model-00002-of-00002.safetensors', 'transformer/config.json',
        'transformer/diffusion_pytorch_model.safetensors.index.json',
        'transformer/diffusion_pytorch_model-00001-of-00002.safetensors',
        'transformer/diffusion_pytorch_model-00002-of-00002.safetensors',
        'vae/config.json', 'vae/diffusion_pytorch_model.safetensors'}
    if len(current_file_names) != 25 or not current_required_names.issubset(current_file_names):
        raise ValueError('FLUX 모델 잠금 필수 구성 파일 누락')
    return current_lock_record


def inspect_flux_model_file_sizes(current_model_root, current_lock_record):
    """링크를 따라가지 않고 잠금 파일의 존재와 크기만 확인한다."""
    try:
        if current_model_root.is_symlink() or not current_model_root.is_dir():
            return False
        for current_file_record in current_lock_record['files']:
            current_file_path = current_model_root
            for current_path_part in current_file_record['path'].split('/'):
                current_file_path = current_file_path / current_path_part
                if current_file_path.is_symlink():
                    return False
            if not current_file_path.is_file() or current_file_path.stat().st_size != current_file_record['size']:
                return False
    except OSError:
        return False
    return True


def verify_flux_model_files(current_model_root, current_lock_record):
    """각 파일의 실제 크기와 LFS SHA-256 또는 Git 객체 해시를 확인한다."""
    if current_model_root.is_symlink() or not current_model_root.is_dir():
        raise ValueError('FLUX 모델 디렉터리가 없거나 심볼릭 링크입니다.')
    for current_file_record in current_lock_record['files']:
        current_file_path = current_model_root
        for current_path_part in current_file_record['path'].split('/'):
            current_file_path = current_file_path / current_path_part
            if current_file_path.is_symlink():
                raise ValueError('FLUX 모델 경로가 심볼릭 링크입니다: ' + current_file_record['path'])
        if not current_file_path.is_file() or current_file_path.stat().st_size != current_file_record['size']:
            raise ValueError('FLUX 모델 파일 누락 또는 크기 불일치: ' + current_file_record['path'])
        current_hash_type = current_file_record['hash_type']
        print(f"FLUX 검증 시작: {current_file_record['path']} ({current_file_record['size']}바이트)", flush=True)
        current_hash_value = hashlib.sha256() if current_hash_type == 'sha256' else hashlib.sha1()
        if current_hash_type == 'git-sha1':
            current_hash_value.update(f"blob {current_file_record['size']}\0".encode())
        with current_file_path.open('rb') as current_file_stream:
            for current_file_chunk in iter(lambda: current_file_stream.read(8 * 1024 * 1024), b''):
                current_hash_value.update(current_file_chunk)
        if current_hash_value.hexdigest() != current_file_record['digest']:
            raise ValueError('FLUX 모델 해시 불일치: ' + current_file_record['path'])
        print(f"FLUX 검증 완료: {current_file_record['path']}", flush=True)


def publish_flux_model_directory(current_stage_path, current_model_path):
    """기존 대상이 있으면 원자적으로 거절한다."""
    current_libc_handle = ctypes.CDLL(None, use_errno=True)
    current_rename_function = getattr(current_libc_handle, 'renameat2', None)
    if current_rename_function is None:
        raise RuntimeError('원자적 게시를 지원하지 않는 시스템입니다.')
    current_rename_function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    current_rename_function.restype = ctypes.c_int
    if current_rename_function(-100, os.fsencode(current_stage_path), -100, os.fsencode(current_model_path), 1) != 0:
        current_error_number = ctypes.get_errno()
        if current_error_number == errno.EEXIST:
            raise FileExistsError('기존 FLUX 모델을 덮어쓰지 않습니다.')
        raise OSError(current_error_number, os.strerror(current_error_number))


def prepare_flux_model_files():
    """기존 모델은 검증만 하고 새 모델은 전용 작업 경로에서 준비한다."""
    from tools.management.common.model_huggingface_download import tracked_snapshot_download
    current_lock_record = read_flux_model_lock()
    current_model_path = FLUX_MODEL_DIRECTORY
    current_model_parent = current_model_path.parent
    if current_model_parent.is_symlink():
        raise ValueError('모델 저장소가 심볼릭 링크입니다.')
    current_model_parent.mkdir(parents=True, exist_ok=True)
    current_lock_path = current_model_parent / '.flux-3-image-klein.prepare.lock'
    current_lock_descriptor = os.open(current_lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(current_lock_descriptor, 'a') as current_lock_stream:
        fcntl.flock(current_lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if current_model_path.exists() or current_model_path.is_symlink():
            verify_flux_model_files(current_model_path, current_lock_record)
            return
        current_stage_path = current_model_parent / '.flux-3-image-klein.preparing'
        current_marker_path = current_stage_path / '.flux-preparation-revision'
        if current_stage_path.is_symlink():
            raise ValueError('FLUX 준비 경로가 심볼릭 링크입니다.')
        if current_stage_path.exists():
            if current_marker_path.is_symlink() or not current_marker_path.is_file() or current_marker_path.read_text() != FLUX_MODEL_REVISION:
                raise ValueError('기존 FLUX 준비 경로를 자동 변경하지 않습니다.')
        else:
            current_stage_path.mkdir()
            current_marker_path.write_text(FLUX_MODEL_REVISION)
        for current_file_record in current_lock_record['files']:
            current_file_path = current_stage_path
            for current_path_part in current_file_record['path'].split('/'):
                current_file_path = current_file_path / current_path_part
                if current_file_path.is_symlink():
                    raise ValueError('FLUX 준비 경로가 심볼릭 링크입니다: ' + current_file_record['path'])
            if current_file_path.exists():
                verify_flux_model_files(current_stage_path, {'files': [current_file_record]})
        tracked_snapshot_download(FLUX_MODEL_REPOSITORY, revision=FLUX_MODEL_REVISION, local_dir=current_stage_path,
                                  allow_patterns=[current_record_value['path'] for current_record_value in current_lock_record['files']], max_workers=2)
        verify_flux_model_files(current_stage_path, current_lock_record)
        publish_flux_model_directory(current_stage_path, current_model_path)
