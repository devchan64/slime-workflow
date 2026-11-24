"""단일 참조 이미지 영상 작업의 저장 입력을 검증한다."""
import base64
import hashlib
import json
from pathlib import Path

from workflow.domains.hermes_agent.delegation_store import validate_service_job_identifier
from workflow.domains.image.three_reference_generation import verify_reference_snapshots


def load_video_saved_input(root, job, service, allowed, validator):
    if not validate_service_job_identifier(service, job):
        raise ValueError('작업 ID가 올바르지 않습니다.')
    root = Path(root)
    directory = root / job
    metadata = directory / 'request.json'
    if root.is_symlink() or directory.is_symlink() or metadata.is_symlink() or not metadata.is_file():
        raise ValueError('저장된 입력을 찾을 수 없습니다.')
    saved = json.loads(metadata.read_bytes())
    if not isinstance(saved, dict) or saved.get('references') != ['reference-1.png']:
        raise ValueError('저장된 참조 이미지가 올바르지 않습니다.')
    snapshots = saved.get('reference_snapshots')
    if not isinstance(snapshots, list) or len(snapshots) != 1:
        raise ValueError('참조 이미지 무결성 기록이 없습니다.')
    verify_reference_snapshots(directory, saved)
    image = (directory / 'reference-1.png').read_bytes()
    if len(image) != snapshots[0]['bytes'] or hashlib.sha256(image).hexdigest() != snapshots[0]['sha256']:
        raise ValueError('참조 이미지가 변경됐습니다.')
    if set(saved) - allowed - {'tag','references','reference_snapshots'}:
        raise ValueError('지원하지 않는 저장 입력이 있습니다.')
    request = {key:value for key,value in saved.items() if key in allowed}
    request['images'] = [base64.b64encode(image).decode('ascii')]
    validator(request)
    return {'id':job, 'request':request}
