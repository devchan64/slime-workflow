"""Wan Fun Control 입력 화면에서 공유하는 모델과 제작 예제."""
import base64
from pathlib import Path
import yaml
from tools.review.common.strict_yaml import UniqueConfigLoader
from generators.wan_fun.contracts import validate_fun_request

FUN_EXAMPLE_STORAGE_ROOT = Path(__file__).resolve().parents[1] / 'examples'
FUN_MODEL_CHOICES = [('Wan 2.2 A14B', 'wan22-14b'), ('Wan 2.1 1.3B', 'wan21-1.3b')]

def load_fun_example_catalog():
    current_catalog_record = yaml.load((FUN_EXAMPLE_STORAGE_ROOT / 'index.yaml').read_text(), Loader=UniqueConfigLoader)
    if not isinstance(current_catalog_record, dict) or set(current_catalog_record) != {'schema_version', 'examples'} or current_catalog_record['schema_version'] != 1 or not isinstance(current_catalog_record['examples'], list):
        raise ValueError('예제 목록 계약 오류')
    current_example_mapping = {}
    for current_example_record in current_catalog_record['examples']:
        if not isinstance(current_example_record, dict) or set(current_example_record) != {'id', 'label'} or any(not isinstance(current_example_record[current_field_name], str) or not current_example_record[current_field_name].strip() for current_field_name in ('id', 'label')):
            raise ValueError('예제 목록 필드 오류')
        current_example_identifier = current_example_record['id']
        if current_example_identifier in current_example_mapping or Path(current_example_identifier).name != current_example_identifier or current_example_identifier in ('.', '..'):
            raise ValueError('예제 ID 중복 또는 경로 오류')
        current_example_mapping[current_example_identifier] = current_example_record['label']
    return current_example_mapping


def read_fun_example_request(current_example_identifier):
    if current_example_identifier not in load_fun_example_catalog():
        raise ValueError('예제를 선택하세요.')
    current_example_directory = FUN_EXAMPLE_STORAGE_ROOT / current_example_identifier
    current_example_record = yaml.load((current_example_directory / 'input.yaml').read_text(), Loader=UniqueConfigLoader)
    if not isinstance(current_example_record, dict) or set(current_example_record) != {'source_job', 'request'} or not isinstance(current_example_record['source_job'], str) or not isinstance(current_example_record['request'], dict):
        raise ValueError('Fun Control 예제 필드 오류')
    current_request_record = current_example_record['request']
    current_reference_path = current_example_directory / 'reference-1.png'
    current_video_path = current_example_directory / 'pose-input.mp4'
    current_validation_record = dict(current_request_record)
    current_validation_record['images'] = [base64.b64encode(current_reference_path.read_bytes()).decode()]
    current_validation_record['pose_video'] = base64.b64encode(current_video_path.read_bytes()).decode()
    validate_fun_request(current_validation_record)
    return current_validation_record


def load_fun_selected_example(current_example_identifier):
    current_request_record = read_fun_example_request(current_example_identifier)
    current_example_directory = FUN_EXAMPLE_STORAGE_ROOT / current_example_identifier
    current_reference_path = current_example_directory / 'reference-1.png'
    current_video_path = current_example_directory / 'pose-input.mp4'
    return (str(current_reference_path), str(current_video_path), None, current_request_record['control_type'], current_request_record['prompt'], current_request_record['negative_prompt'], current_request_record['frames'], current_request_record['seed'], current_request_record['steps'], current_request_record['flow_shift'], current_request_record['guidance_scale'], current_request_record['switch_ratio'], 'pose-video', False, False, None, None, False, 'wan22-14b')
