"""등록 애니메이션을 Qwen 2.1로 분리하는 후보 생성 서비스."""
import base64
import hashlib
import io
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from PIL import Image
from tools.review.common.map_tile_assets import UniqueAssetYamlLoader
from tools.review.common.generation_records import validate_history_tag
from .qwen_21_generation import QwenPlainGenerationManager, WORKFLOW_ROOT_PATH
from generators.image.qwen_21_runtime import QWEN_MODEL_IDENTIFIER, QWEN_MODEL_REVISION
from .image_generation import MANAGER_HISTORY_ROOT
from .three_reference_generation import verify_reference_snapshots

SEPARATION_STORAGE_ROOT = WORKFLOW_ROOT_PATH / '.tmp/test/animation-separation'
SEPARATION_FRAME_LIMIT = 64
SEPARATION_JOB_PATTERN = r'[0-9]{4}-[0-9-]{5}_[0-9-]{8}-[a-f0-9]{8}'


def load_separation_defaults():
    configuration_path_value = WORKFLOW_ROOT_PATH / 'generators/image/config/animation_separation.yaml'
    configuration_record_value = yaml.load(configuration_path_value.read_text(), Loader=UniqueAssetYamlLoader)
    if not isinstance(configuration_record_value, dict) or set(configuration_record_value) != {'schema_version', 'prompt', 'outfit_prompt'} or configuration_record_value['schema_version'] != 2:
        raise ValueError('분리 기본 설정 형식 오류')
    validate_separation_prompt(configuration_record_value['prompt'])
    validate_separation_prompt(configuration_record_value['outfit_prompt'])
    return configuration_record_value


def validate_separation_prompt(current_prompt_text):
    if not isinstance(current_prompt_text, str) or not 0 < len(current_prompt_text.split()) < 100 or len(current_prompt_text) > 8000:
        raise ValueError('분리 프롬프트는 1~99단어여야 합니다.')


def calculate_separation_signature(current_request_record):
    signature_record_value = {current_field_name: current_request_record[current_field_name] for current_field_name in ('schema_version', 'source_id', 'source_digest', 'prompt', 'outfit_prompt', 'width', 'height', 'seed', 'steps', 'model_id', 'model_revision')}
    return hashlib.sha256(json.dumps(signature_record_value, sort_keys=True).encode()).hexdigest()


def verify_separation_request(current_job_directory):
    current_request_record = json.loads((current_job_directory / 'request.json').read_text())
    if current_request_record.get('schema_version') != 2:
        raise ValueError('이전 머리·좌우 분리 작업은 재개할 수 없습니다. 두 프롬프트로 새로 생성하세요.')
    validate_separation_prompt(current_request_record.get('outfit_prompt'))
    if not isinstance(current_request_record.get('reference_snapshots'), list) or not current_request_record['reference_snapshots']:
        raise ValueError('분리 참조 스냅샷 기록 누락')
    verify_reference_snapshots(current_job_directory, current_request_record)
    if current_request_record.get('model_id') != QWEN_MODEL_IDENTIFIER or current_request_record.get('model_revision') != QWEN_MODEL_REVISION:
        raise ValueError('분리 모델 버전 불일치')
    validate_separation_prompt(current_request_record['prompt'])
    if current_request_record.get('signature') != calculate_separation_signature(current_request_record):
        raise ValueError('분리 요청 설정 무결성 오류')
    if current_request_record['steps'] != 40 or current_request_record['width'] not in (512, 768) or current_request_record['height'] != current_request_record['width']:
        raise ValueError('분리 실행 규격 오류')
    if not 1 <= len(current_request_record['frames']) <= SEPARATION_FRAME_LIMIT or len(current_request_record['frames']) != len(current_request_record['references']):
        raise ValueError('분리 프레임과 참조 수 불일치')
    return current_request_record


class AnimationSeparationManager(QwenPlainGenerationManager):
    def __init__(self):
        super().__init__()
        self.route_prefix_value = '/animation-separation'
        self.job_storage_root = SEPARATION_STORAGE_ROOT

    def select_generation_runner(self, saved_request_record=None):
        return 'generators/image/run_animation_separation.py'

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'animation-separation'

    def validate_generation_resume(self, selected_job_directory):
        verify_separation_request(selected_job_directory)

    def validate_generation_request(self, current_request_record):
        from .three_reference_generation import decode_reference_image
        required_request_fields = {'action', 'images', 'width', 'height', 'steps', 'seed', 'prompt', 'outfit_prompt'}
        if not isinstance(current_request_record, dict) or set(current_request_record) - required_request_fields - {'tag'} or not required_request_fields <= set(current_request_record) or current_request_record['action'] != 'generate':
            raise ValueError('이미지 분리 요청 필드 오류')
        validate_separation_prompt(current_request_record['prompt'])
        validate_separation_prompt(current_request_record['outfit_prompt'])
        for current_field_name in ('width', 'height', 'steps', 'seed'):
            if type(current_request_record[current_field_name]) is not int:
                raise ValueError('분리 설정은 정수여야 합니다: ' + current_field_name)
        if current_request_record['width'] not in (512, 768) or current_request_record['height'] != current_request_record['width'] or current_request_record['steps'] != 40 or not 0 <= current_request_record['seed'] <= 4294967295:
            raise ValueError('512/768 정사각형·40스텝·uint32 시드만 지원합니다.')
        current_image_records = current_request_record['images']
        if not isinstance(current_image_records, list) or len(current_image_records) != 1:
            raise ValueError('참조 이미지는 정확히 1장을 첨부하세요.')
        current_image_bytes = decode_reference_image(current_image_records[0], composite_transparent_background=True)
        source_digest_value = hashlib.sha256(current_image_bytes).hexdigest()
        with Image.open(io.BytesIO(current_image_bytes)) as current_source_image:
            current_frame_rectangle = {'x': 0, 'y': 0, 'width': current_source_image.width, 'height': current_source_image.height}
        saved_request_record = {**current_request_record, 'images': [base64.b64encode(current_image_bytes).decode()],
            'schema_version': 2, 'source_id': 'upload:' + source_digest_value, 'source_digest': source_digest_value,
            'tag': validate_history_tag(current_request_record.get('tag', '')), 'fps': 8,
            'frames': [{'frameId': 'reference.0', 'direction': 'reference', 'rect': current_frame_rectangle}],
            'model_id': QWEN_MODEL_IDENTIFIER, 'model_revision': QWEN_MODEL_REVISION,
            'prompt_word_count': len(current_request_record['prompt'].split()),
            'prompt_sha256': hashlib.sha256(current_request_record['prompt'].encode()).hexdigest(),
            'outfit_prompt_word_count': len(current_request_record['outfit_prompt'].split()),
            'outfit_prompt_sha256': hashlib.sha256(current_request_record['outfit_prompt'].encode()).hexdigest()}
        saved_request_record['signature'] = calculate_separation_signature(saved_request_record)
        return saved_request_record

    def enrich_generation_status(self, current_job_root, current_status_record):
        request_record_path = current_job_root / 'request.json'
        if request_record_path.exists() and json.loads(request_record_path.read_text()).get('schema_version') != 2:
            current_status_record['resume_allowed'] = False
            current_status_record['resume_block_reason'] = '폐기된 머리·좌우 분리 방식입니다. 새로 생성하세요.'
        progress_record_path = current_job_root / 'separation-progress.json'
        if progress_record_path.exists():
            current_status_record['separation'] = json.loads(progress_record_path.read_text())
        if (current_job_root / 'separation.zip').is_file():
            current_status_record['download'] = f'{self.route_prefix_value}/jobs/{current_job_root.name}/separation.zip'
        return current_status_record

    def handle_image_request(self, current_http_handler):
        current_route_path = urlsplit(current_http_handler.path).path
        current_file_match = re.fullmatch(self.route_prefix_value + '/jobs/(' + SEPARATION_JOB_PATTERN + r')/(separation.zip|manifest.json|base-sheet.png|outfit-sheet.png|source-sheet.png)', current_route_path)
        if current_http_handler.command == 'GET' and (current_route_path in (self.route_prefix_value + '/catalog', self.route_prefix_value + '/source-preview') or current_file_match):
            try:
                if current_http_handler.headers.get('Host') != f'127.0.0.1:{current_http_handler.server.server_port}':
                    raise ValueError('허용하지 않는 Host')
                if current_file_match:
                    current_file_path = self.job_storage_root / current_file_match[1] / current_file_match[2]
                    response_body_bytes = current_file_path.read_bytes()
                    response_content_type = 'application/zip' if current_file_path.suffix == '.zip' else 'image/png' if current_file_path.suffix == '.png' else 'application/json'
                    current_http_handler.send_response(200)
                else:
                    response_body_bytes = json.dumps({'error': '원본 목록 선택과 프레임 미리보기는 폐기되었습니다. 참조 PNG 1장을 첨부해 생성하세요.', 'code': 'source_selection_retired'}, ensure_ascii=False).encode()
                    response_content_type = 'application/json'
                    current_http_handler.send_response(410)
            except (ValueError, FileNotFoundError) as current_error_value:
                response_body_bytes = json.dumps({'error': str(current_error_value)}, ensure_ascii=False).encode()
                response_content_type = 'application/json'
                current_http_handler.send_response(400)
            current_http_handler.send_header('Content-Type', response_content_type)
            current_http_handler.send_header('Content-Length', str(len(response_body_bytes)))
            current_http_handler.send_header('Cache-Control', 'no-store')
            current_http_handler.end_headers()
            current_http_handler.wfile.write(response_body_bytes)
            return True
        return super().handle_image_request(current_http_handler)
