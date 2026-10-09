"""Qwen Lightning 고정 어댑터 검증. 기존 모델 캐시 경로를 유지한다."""
from pathlib import Path
import hashlib

WORKFLOW_REPO_ROOT = Path(__file__).resolve().parents[3]
FIXED_ADAPTER_RECORDS = (
    {'name': 'lightning', 'repository': 'lightx2v/Qwen-Image-Edit-2511-Lightning', 'revision': 'd74eba145674fd7e31b949324e148e21e7118abd', 'filename': 'Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors', 'sha256': '22226e8d05d354bb356627d428809f5afd7819399b077238a2b70a82883a904f', 'size': 849608296, 'strength': 1.0},
)


def resolve_adapter_path(adapter_record_values):
    return WORKFLOW_REPO_ROOT/'.model/qwen-anypose'/adapter_record_values['repository'].replace('/', '--')/adapter_record_values['revision']/adapter_record_values['filename']


def calculate_file_digest(source_file_path):
    with Path(source_file_path).open('rb') as source_input_file:
        return hashlib.file_digest(source_input_file, 'sha256').hexdigest()


def validate_adapter_files(*, include_lightning_adapter=True):
    if type(include_lightning_adapter) is not bool:
        raise ValueError('Lightning 선택은 bool이어야 합니다.')
    resolved_adapter_records = []
    for adapter_record_values in FIXED_ADAPTER_RECORDS:
        if adapter_record_values['name'] != 'lightning':
            continue
        if adapter_record_values['name'] == 'lightning' and not include_lightning_adapter:
            continue
        adapter_file_path = resolve_adapter_path(adapter_record_values)
        if not adapter_file_path.is_file():
            raise FileNotFoundError(f"어댑터 준비 필요 model_id={adapter_record_values['repository']} model_path={adapter_file_path}")
        if adapter_file_path.stat().st_size != adapter_record_values['size'] or calculate_file_digest(adapter_file_path) != adapter_record_values['sha256']:
            raise ValueError(f'어댑터 크기/SHA-256 불일치: {adapter_file_path}')
        resolved_adapter_records.append({**adapter_record_values, 'path': str(adapter_file_path)})
    return resolved_adapter_records

