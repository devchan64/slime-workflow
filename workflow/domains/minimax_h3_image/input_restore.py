"""Read and verify saved MiniMax image inputs without changing the job."""
import base64
import hashlib
import json
import os
import stat
from pathlib import Path

from generators.minimax_h3_image.contracts import validate_request, verify_saved_request
from workflow.domains.hermes_agent.delegation_store import validate_service_job_identifier
from workflow.domains.image.three_reference_generation import REFERENCE_IMAGE_LIMIT, verify_reference_snapshots


def load_saved_input(root, job):
    if not validate_service_job_identifier('minimax-h3-image', job):
        raise ValueError('작업 ID가 올바르지 않습니다.')
    root = Path(root)
    directory = root / job
    metadata = directory / 'request.json'
    if root.is_symlink() or directory.is_symlink() or metadata.is_symlink() or not metadata.is_file():
        raise ValueError('저장된 입력을 찾을 수 없습니다.')
    saved = json.loads(metadata.read_bytes())
    if not isinstance(saved, dict):
        raise ValueError('저장된 입력 형식 오류')
    verify_saved_request(saved)
    names = saved.get('references')
    snapshots = saved.get('reference_snapshots')
    if not isinstance(names, list) or len(names) > 2 or not isinstance(snapshots, list) or len(snapshots) != len(names):
        raise ValueError('참조 이미지 무결성 기록이 없습니다.')
    verify_reference_snapshots(directory, saved)
    images = []
    for name, snapshot in zip(names, snapshots):
        descriptor = os.open(directory / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('참조 이미지 파일 오류')
            data = stream.read(REFERENCE_IMAGE_LIMIT + 1)
        if len(data) > REFERENCE_IMAGE_LIMIT or len(data) != snapshot['bytes'] or hashlib.sha256(data).hexdigest() != snapshot['sha256']:
            raise ValueError('참조 이미지가 변경됐습니다.')
        images.append(base64.b64encode(data).decode('ascii'))
    request = {key: saved[key] for key in ('action', 'width', 'height', 'steps', 'seed')}
    request['sampler'] = saved.get('sampler', 'euler')
    request['prompt'] = saved['user_prompt']
    request['images'] = images
    if 'output_size' in saved:
        request['output_size'] = saved['output_size']
    validate_request(request)
    return {'id': job, 'request': request}
