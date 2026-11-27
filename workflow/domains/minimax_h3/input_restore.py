"""MiniMax H3 저장 입력 복원 및 참조 무결성 확인."""
import base64
import json
from pathlib import Path
from generators.minimax_h3.contracts import validate_request
from workflow.domains.hermes_agent.delegation_store import validate_service_job_identifier
from workflow.domains.image.three_reference_generation import verify_reference_snapshots


def load_saved_input(root, job):
    if not validate_service_job_identifier('minimax-h3-i2v', job):
        raise ValueError('작업 ID가 올바르지 않습니다.')
    root=Path(root); directory=root/job; metadata=directory/'request.json'
    if root.is_symlink() or directory.is_symlink() or metadata.is_symlink() or not metadata.is_file():
        raise ValueError('저장된 입력을 찾을 수 없습니다.')
    saved=json.loads(metadata.read_bytes())
    allowed={'action','prompt','width','height','frames','steps','seed','mode'}
    if not isinstance(saved,dict) or set(saved)-allowed-{'tag','references','reference_snapshots'}:
        raise ValueError('지원하지 않는 저장 입력이 있습니다.')
    verify_reference_snapshots(directory,saved)
    if not isinstance(saved.get('reference_snapshots'),list):
        raise ValueError('참조 이미지 무결성 기록이 없습니다.')
    request={k:v for k,v in saved.items() if k in allowed}
    request['images']=[base64.b64encode((directory/name).read_bytes()).decode('ascii') for name in saved['references']]
    validate_request(request)
    return {'id':job,'request':request}
