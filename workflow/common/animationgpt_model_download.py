"""AnimationGPT 제3자 FP16 배포본의 다운로드 및 파일 검증."""
import hashlib
import json
from pathlib import Path

from workflow.common.generation_records import write_record_atomically
from workflow.common.model_http_download import download_verified_http

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
ANIMATIONGPT_MODEL_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.model/animationgpt'
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
