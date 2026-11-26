"""AnimationGPT 제3자 FP16 배포본의 다운로드 및 파일 검증."""
import hashlib
import json
import os
from pathlib import Path

from workflow.common.generation_records import write_record_atomically
from workflow.common.model_http_download import download_verified_http

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
ANIMATIONGPT_MODEL_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.model/animationgpt'
AUTHOR_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.model/animationgpt-author'
AUTHOR_MARKER = WORKFLOW_ROOT_DIRECTORY / '.local/animationgpt-legacy/author-weight-ready.json'
AUTHOR_WEIGHT_SHA256 = '80d822c7c34faf075d93a8b605569142a7d97e9feb31972a94fb9968621aaa6b'
AUTHOR_WEIGHT_SIZE = 1272532332
AUTHOR_T5_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.model/flan-t5-base'
AUTHOR_T5_MARKER = WORKFLOW_ROOT_DIRECTORY / '.local/animationgpt-legacy/flan-t5-base-ready.json'
AUTHOR_T5_WEIGHT_SHA256 = '1dfb70afdcedceb9f9fae2f9b68e004ad934361fb35b9b2bd50b45ea90790fc8'
FILENAME = 'AnimationGPT_fp16.safetensors'
REVISION = '511d227763e63acb1efbe28992636e3dd31d5f87'
SHA256 = 'abcc432b7ff2d43e049a5096b9214ed29e0805f7577af3a3189201b31d2d3fa2'
URL = f'https://huggingface.co/Kijai/AnimationGPT_pruned/resolve/{REVISION}/{FILENAME}'
T5_REVISION = '7bcac572ce56db69c1ea7c8af255c5d7c9672fc2'
MOTIONGPT_REVISION = '001aaca8d0ee218fc17f8265d11ac124044fe42f'
SUPPORT_FILES = {
    'flan-t5-base/config.json': '7c1853dbfa0e4aac093eb109a358b6ab25fe86b7c15185a91322f0ed26f0f940',
    'flan-t5-base/special_tokens_map.json': '5c87151ef0f72a99d1f766a4c418bd2a1f90aaa30a8e22fe5eca9641daebb64f',
    'flan-t5-base/spiece.model': 'd60acb128cf7b7f2536e8f38a5b18a05535c9e14c7a355904270e15b0945ea86',
    'flan-t5-base/tokenizer.json': 'fe2ebbbbde2985be723e0ce18217853e4020c5e9d35bd07be2c27ab9d3ead57a',
    'flan-t5-base/tokenizer_config.json': '4c55124402e4ce48c7125d04b9af152a125eda9e7c80829f8f99f2ec69f3f68d',
    'motion-stats/mean.npy': '0bdb5ba69a3a9e34d71990db15bc535ebc024c8d95ddb5574196f96058faa7d3',
    'motion-stats/std.npy': '6a5f7d60301c9465972fc225f8ad0ee8f957e7720431189123eb6d15873a9557',
}


def required_files():
    return {FILENAME: SHA256, **SUPPORT_FILES}


def inspect_animationgpt_model_files():
    marker = ANIMATIONGPT_MODEL_DIRECTORY / 'ready.sha256'
    try:
        if marker.is_symlink():
            return False
        records = {}
        for name, digest in required_files().items():
            path = ANIMATIONGPT_MODEL_DIRECTORY / name
            if path.is_symlink() or not path.is_file():
                return False
            stat = path.stat()
            records[name] = {'sha256': digest, 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
        return json.loads(marker.read_text(encoding='utf-8')) == records
    except (OSError, ValueError):
        return False


def prepare_animationgpt_model_files():
    records = {}
    for name, digest in required_files().items():
        path = ANIMATIONGPT_MODEL_DIRECTORY / name
        if name == FILENAME:
            url = URL
        elif name.startswith('flan-t5-base/'):
            url = f'https://huggingface.co/google/flan-t5-base/resolve/{T5_REVISION}/{name.split("/", 1)[1]}'
        else:
            url = f'https://raw.githubusercontent.com/OpenMotionLab/MotionGPT/{MOTIONGPT_REVISION}/assets/meta/{name.split("/", 1)[1]}'
        download_verified_http(url, path, digest, 'animationgpt/' + name)
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                raise ValueError(f'AnimationGPT 파일 SHA-256 불일치: {name}')
        stat = path.stat()
        records[name] = {'sha256': digest, 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
    write_record_atomically(ANIMATIONGPT_MODEL_DIRECTORY / 'ready.sha256', records)


def author_t5_required_files():
    return {'model.safetensors': AUTHOR_T5_WEIGHT_SHA256,
            **{name.split('/', 1)[1]: digest for name, digest in SUPPORT_FILES.items()
               if name.startswith('flan-t5-base/')}}


def inspect_author_t5_model_files():
    """Check a prior fixed-hash verification against current file metadata."""
    try:
        if AUTHOR_T5_DIRECTORY.is_symlink() or AUTHOR_T5_MARKER.is_symlink():
            return False
        records = {}
        for name, digest in author_t5_required_files().items():
            path = AUTHOR_T5_DIRECTORY / name
            if path.is_symlink() or not path.is_file():
                return False
            info = path.stat()
            records[name] = {'sha256': digest, 'size': info.st_size, 'mtime_ns': info.st_mtime_ns,
                             'change_token': f'{info.st_dev}:{info.st_ino}:{info.st_ctime_ns}'}
        return json.loads(AUTHOR_T5_MARKER.read_text(encoding='utf-8')) == records
    except (OSError, ValueError):
        return False


def prepare_author_t5_model_files():
    """Restore fixed-hash files from the configured backup before using HTTP."""
    if AUTHOR_T5_DIRECTORY.is_symlink():
        raise ValueError('FLAN-T5 모델 경로에 심볼릭 링크를 사용할 수 없습니다.')
    records = {}
    for name, digest in author_t5_required_files().items():
        path = AUTHOR_T5_DIRECTORY / name
        url = f'https://huggingface.co/google/flan-t5-base/resolve/{T5_REVISION}/{name}'
        download_verified_http(url, path, digest, 'flan-t5-base/' + name)
        with path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                raise ValueError(f'FLAN-T5 파일 SHA-256 불일치: {name}')
            after = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError(f'FLAN-T5 파일 검증 중 변경: {name}')
        info = path.stat()
        if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError(f'FLAN-T5 파일 검증 중 교체: {name}')
        records[name] = {'sha256': digest, 'size': info.st_size, 'mtime_ns': info.st_mtime_ns,
                         'change_token': f'{info.st_dev}:{info.st_ino}:{info.st_ctime_ns}'}
    AUTHOR_T5_MARKER.parent.mkdir(parents=True, exist_ok=True)
    write_record_atomically(AUTHOR_T5_MARKER, records)


def _author_weight_record(info):
    return {'sha256': AUTHOR_WEIGHT_SHA256, 'size': info.st_size, 'mtime_ns': info.st_mtime_ns,
            'change_token': f'{info.st_dev}:{info.st_ino}:{info.st_ctime_ns}'}


def inspect_author_weight():
    try:
        path = AUTHOR_DIRECTORY / FILENAME
        if AUTHOR_DIRECTORY.is_symlink() or path.is_symlink() or AUTHOR_MARKER.is_symlink() or not path.is_file():
            return False
        info = path.stat()
        return info.st_size == AUTHOR_WEIGHT_SIZE and json.loads(AUTHOR_MARKER.read_text(encoding='utf-8')) == _author_weight_record(info)
    except (OSError, ValueError):
        return False


def prepare_author_weight():
    """Restore the author weight only from a fixed-hash matching local backup."""
    from workflow.common.model_backup_restore import restore_verified_backup
    from workflow.common.model_download_records import track_model_download
    path = AUTHOR_DIRECTORY / FILENAME
    if AUTHOR_DIRECTORY.is_symlink() or path.is_symlink():
        raise ValueError('제작자 가중치 경로에 심볼릭 링크를 사용할 수 없습니다.')
    with track_model_download('animationgpt-author/' + FILENAME) as record:
        if not path.exists():
            AUTHOR_DIRECTORY.mkdir(parents=True, exist_ok=True)
            if AUTHOR_DIRECTORY.is_symlink():
                raise ValueError('제작자 가중치 경로에 심볼릭 링크를 사용할 수 없습니다.')
            record.update(stage='백업 확인 중')
            if not restore_verified_backup(path, AUTHOR_WEIGHT_SHA256, AUTHOR_WEIGHT_SIZE,
                    report=lambda size: record.update(stage='백업에서 복원', bytes=size, total_bytes=AUTHOR_WEIGHT_SIZE)):
                raise FileNotFoundError('제작자 가중치를 찾지 못했습니다. Samba 백업과 경로를 확인하세요.')
        if not path.is_file():
            raise ValueError('제작자 가중치가 일반 파일이 아닙니다.')
        with path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            if before.st_size != AUTHOR_WEIGHT_SIZE or hashlib.file_digest(stream, 'sha256').hexdigest() != AUTHOR_WEIGHT_SHA256:
                raise ValueError('제작자 가중치 크기 또는 SHA-256 불일치')
            after = os.fstat(stream.fileno())
        signature = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if signature(before) != signature(after) or signature(path.stat()) != signature(after):
            raise ValueError('검증 중 제작자 가중치가 변경됐습니다.')
        AUTHOR_MARKER.parent.mkdir(parents=True, exist_ok=True)
        write_record_atomically(AUTHOR_MARKER, _author_weight_record(after))
        record.update(stage='검증 완료', bytes=after.st_size, total_bytes=after.st_size)
