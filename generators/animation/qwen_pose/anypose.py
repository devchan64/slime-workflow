"""AnyPose의 고정 어댑터 준비·해시 검증·적용. 가중치는 .model에서만 관리한다."""
from pathlib import Path
import hashlib
import logging
import json
import threading
import urllib.request

WORKFLOW_REPO_ROOT = Path(__file__).resolve().parents[3]
FIXED_ADAPTER_RECORDS = (
    {'name': 'anypose_base', 'repository': 'lilylilith/AnyPose', 'revision': '27c4b1f7688940d39767e652fe8d87faf44a0881', 'filename': '2511-AnyPose-base-000006250.safetensors', 'sha256': '0396314e43b94f7520cf5242e6aa6e8e9095d784f7e87ee45980c2e541ee8c4d', 'size': 295146208, 'strength': 0.7},
    {'name': 'anypose_helper', 'repository': 'lilylilith/AnyPose', 'revision': '27c4b1f7688940d39767e652fe8d87faf44a0881', 'filename': '2511-AnyPose-helper-00006000.safetensors', 'sha256': '674340c62fff3cf981d0cfc55daf2f0e6f51c56b50159e241d931748200cf1eb', 'size': 295146216, 'strength': 0.7},
    {'name': 'lightning', 'repository': 'lightx2v/Qwen-Image-Edit-2511-Lightning', 'revision': 'd74eba145674fd7e31b949324e148e21e7118abd', 'filename': 'Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors', 'sha256': '22226e8d05d354bb356627d428809f5afd7819399b077238a2b70a82883a904f', 'size': 849608296, 'strength': 1.0},
)


def resolve_adapter_path(adapter_record_values):
    return WORKFLOW_REPO_ROOT/'.model/qwen-anypose'/adapter_record_values['repository'].replace('/', '--')/adapter_record_values['revision']/adapter_record_values['filename']


def calculate_file_digest(source_file_path):
    with Path(source_file_path).open('rb') as source_input_file:
        return hashlib.file_digest(source_input_file, 'sha256').hexdigest()


def validate_adapter_files(*, include_lightning_adapter=True, include_anypose_adapter=True):
    if include_anypose_adapter is not False:
        raise ValueError('AnyPose LoRA는 폐기되었습니다.')
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


def prepare_anypose_models():
    raise ValueError('AnyPose LoRA는 폐기되어 다운로드·준비를 지원하지 않습니다.')


if __name__ == '__main__':
    prepare_anypose_models()
