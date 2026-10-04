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
from tools.review.common.map_tile_assets import UniqueAssetYamlLoader, load_registered_tiles, resolve_registered_asset
from tools.review.common.generation_records import validate_history_tag
from .qwen_21_generation import QwenPlainGenerationManager, WORKFLOW_ROOT_PATH
from generators.image.qwen_21_runtime import QWEN_MODEL_IDENTIFIER, QWEN_MODEL_REVISION
from .image_generation import MANAGER_HISTORY_ROOT
from .three_reference_generation import verify_reference_snapshots

SEPARATION_STORAGE_ROOT = WORKFLOW_ROOT_PATH / '.tmp/test/animation-separation'
SEPARATION_FRAME_LIMIT = 64
SEPARATION_JOB_PATTERN = r'[0-9]{4}-[0-9-]{5}_[0-9-]{8}-[a-f0-9]{8}'


def load_separation_sources():
    asset_repository_path, registered_asset_records = load_registered_tiles()
    source_catalog_records = []
    for current_relative_path in sorted(registered_asset_records):
        if not current_relative_path.startswith('assets/characters/') or '/animations/' not in current_relative_path or not current_relative_path.endswith('.animation.json'):
            continue
        metadata_source_path, metadata_source_record = resolve_registered_asset(current_relative_path, asset_repository_path, registered_asset_records, 'assets/characters')
        current_image_relative = current_relative_path.removesuffix('.animation.json') + '.png'
        source_manifest_paths = [metadata_source_path.parent / current_file_name for current_file_name in ('source.json', 'source.yaml') if (metadata_source_path.parent / current_file_name).is_file()]
        if len(source_manifest_paths) > 1:
            raise ValueError('출처 메타데이터 중복')
        if source_manifest_paths:
            source_manifest_path = source_manifest_paths[0]
            source_manifest_record = json.loads(source_manifest_path.read_text()) if source_manifest_path.suffix == '.json' else yaml.load(source_manifest_path.read_text(), Loader=UniqueAssetYamlLoader)
            if 'image' in source_manifest_record:
                source_image_name = source_manifest_record['image']
                if not isinstance(source_image_name, str) or Path(source_image_name).name != source_image_name:
                    raise ValueError('출처 이미지 파일명 오류')
                current_image_relative = str(Path(current_relative_path).parent / source_image_name)
        image_source_path, image_source_record = resolve_registered_asset(current_image_relative, asset_repository_path, registered_asset_records, 'assets/characters')
        source_animation_record = json.loads(metadata_source_path.read_text())
        source_frame_records = [{**current_frame_record, 'direction': current_frame_record['frameId'].split('.')[0], 'source_path': str(image_source_path)} for current_frame_record in source_animation_record['frames']]
        source_catalog_records.append({'id': 'asset:' + current_relative_path, 'label': source_animation_record['animationId'] + ' · ' + source_animation_record['version'], 'fps': 8, 'frames': source_frame_records, 'provenance': [metadata_source_record, image_source_record]})
    return source_catalog_records


def load_sprite_editor_source(current_source_identifier):
    for current_source_record in load_separation_sources():
        if current_source_record['id'] == current_source_identifier:
            return current_source_record
    raise ValueError('등록되지 않은 캐릭터 애니메이션입니다.')


def resolve_sprite_image_path(current_source_record, current_frame_record):
    return Path(current_frame_record['source_path'])


def load_separation_defaults():
    configuration_path_value = WORKFLOW_ROOT_PATH / 'generators/image/config/animation_separation.yaml'
    configuration_record_value = yaml.load(configuration_path_value.read_text(), Loader=UniqueAssetYamlLoader)
    if not isinstance(configuration_record_value, dict) or set(configuration_record_value) != {'schema_version', 'prompt'} or configuration_record_value['schema_version'] != 1:
        raise ValueError('분리 기본 설정 형식 오류')
    validate_separation_prompt(configuration_record_value['prompt'])
    return configuration_record_value


def validate_separation_prompt(current_prompt_text):
    if not isinstance(current_prompt_text, str) or not 0 < len(current_prompt_text.split()) < 100 or len(current_prompt_text) > 8000:
        raise ValueError('분리 프롬프트는 1~99단어여야 합니다.')


def calculate_separation_signature(current_request_record):
    signature_record_value = {current_field_name: current_request_record[current_field_name] for current_field_name in ('source_id', 'source_digest', 'prompt', 'width', 'height', 'seed', 'steps', 'model_id', 'model_revision')}
    return hashlib.sha256(json.dumps(signature_record_value, sort_keys=True).encode()).hexdigest()


def verify_separation_request(current_job_directory):
    current_request_record = json.loads((current_job_directory / 'request.json').read_text())
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
        required_request_fields = {'action', 'source_id', 'start_frame', 'end_frame', 'width', 'height', 'steps', 'seed', 'prompt'}
        if not isinstance(current_request_record, dict) or set(current_request_record) - required_request_fields - {'tag', 'sample_id'} or not required_request_fields <= set(current_request_record) or current_request_record['action'] != 'generate':
            raise ValueError('애니메이션 분리 요청 필드 오류')
        validate_separation_prompt(current_request_record['prompt'])
        for current_field_name in ('start_frame', 'end_frame', 'width', 'height', 'steps', 'seed'):
            if type(current_request_record[current_field_name]) is not int:
                raise ValueError('분리 설정은 정수여야 합니다: ' + current_field_name)
        if current_request_record['width'] not in (512, 768) or current_request_record['height'] != current_request_record['width'] or current_request_record['steps'] != 40 or not 0 <= current_request_record['seed'] <= 4294967295:
            raise ValueError('512/768 정사각형·40스텝·uint32 시드만 지원합니다.')
        current_source_identifier = current_request_record['source_id']
        if not isinstance(current_source_identifier, str) or not current_source_identifier.startswith('asset:'):
            raise ValueError('등록된 애니메이션 에셋 ID를 선택하세요.')
        current_source_record = load_sprite_editor_source(current_source_identifier)
        current_source_frames = current_source_record['frames']
        first_frame_number, last_frame_number = current_request_record['start_frame'], current_request_record['end_frame']
        if not 1 <= first_frame_number <= last_frame_number <= len(current_source_frames) or last_frame_number - first_frame_number >= SEPARATION_FRAME_LIMIT:
            raise ValueError('원본 범위 안에서 최대 64프레임을 선택하세요.')
        source_hash_records = {}
        for current_frame_record in current_source_frames:
            current_image_path = resolve_sprite_image_path(current_source_record, current_frame_record)
            if str(current_image_path) not in source_hash_records:
                source_hash_records[str(current_image_path)] = hashlib.sha256(current_image_path.read_bytes()).hexdigest()
        source_digest_value = hashlib.sha256(json.dumps({'source': current_source_record, 'images': source_hash_records}, sort_keys=True).encode()).hexdigest()
        saved_request_record = {**current_request_record, 'tag': validate_history_tag(current_request_record.get('tag', '')), 'source_digest': source_digest_value, 'model_id': QWEN_MODEL_IDENTIFIER, 'model_revision': QWEN_MODEL_REVISION,
            'fps': current_source_record.get('fps', 8), 'frames': current_source_frames[first_frame_number-1:last_frame_number],
            'prompt_word_count': len(current_request_record['prompt'].split()), 'prompt_sha256': hashlib.sha256(current_request_record['prompt'].encode()).hexdigest()}
        saved_request_record['signature'] = calculate_separation_signature(saved_request_record)
        if last_frame_number > first_frame_number:
            sample_identifier_value = current_request_record.get('sample_id', '')
            if not isinstance(sample_identifier_value, str) or not re.fullmatch(SEPARATION_JOB_PATTERN, sample_identifier_value):
                raise ValueError('전체 생성 전에 완료된 1프레임 샘플 ID를 지정하세요.')
            sample_directory_path = self.job_storage_root / sample_identifier_value
            sample_request_record = verify_separation_request(sample_directory_path)
            sample_completion_record = json.loads((sample_directory_path / 'frame-001/complete.json').read_text())
            if sample_completion_record['sha256'] != hashlib.sha256((sample_directory_path / 'frame-001/result.png').read_bytes()).hexdigest():
                raise ValueError('샘플 결과 해시 불일치')
            if len(sample_request_record['frames']) != 1 or sample_request_record['signature'] != saved_request_record['signature'] or json.loads((sample_directory_path / 'status.json').read_text())['status'] != 'completed':
                raise ValueError('샘플의 원본·프롬프트·크기·시드가 현재 설정과 일치하고 완료되어야 합니다.')
        saved_request_record['images'] = []
        for current_frame_record in saved_request_record['frames']:
            current_frame_rectangle = current_frame_record['rect']
            with Image.open(resolve_sprite_image_path(current_source_record, current_frame_record)) as source_image_value:
                current_crop_bounds = (current_frame_rectangle['x'], current_frame_rectangle['y'], current_frame_rectangle['x']+current_frame_rectangle['width'], current_frame_rectangle['y']+current_frame_rectangle['height'])
                if current_crop_bounds[0] < 0 or current_crop_bounds[1] < 0 or current_crop_bounds[2] > source_image_value.width or current_crop_bounds[3] > source_image_value.height:
                    raise ValueError('원본 시트 밖의 프레임 영역')
                source_frame_image = source_image_value.convert('RGBA').crop(current_crop_bounds)
                opaque_frame_image = Image.new('RGB', source_frame_image.size, 'white')
                opaque_frame_image.paste(source_frame_image, mask=source_frame_image.getchannel('A'))
                image_output_buffer = io.BytesIO()
                opaque_frame_image.save(image_output_buffer, format='PNG')
            saved_request_record['images'].append(base64.b64encode(image_output_buffer.getvalue()).decode())
        return saved_request_record

    def enrich_generation_status(self, current_job_root, current_status_record):
        progress_record_path = current_job_root / 'separation-progress.json'
        if progress_record_path.exists():
            current_status_record['separation'] = json.loads(progress_record_path.read_text())
        if (current_job_root / 'separation.zip').is_file():
            current_status_record['download'] = f'{self.route_prefix_value}/jobs/{current_job_root.name}/separation.zip'
        return current_status_record

    def handle_image_request(self, current_http_handler):
        current_route_path = urlsplit(current_http_handler.path).path
        current_file_match = re.fullmatch(self.route_prefix_value + '/jobs/(' + SEPARATION_JOB_PATTERN + r')/(separation.zip|manifest.json|head-sheet.png|body-sheet.png|source-sheet.png)', current_route_path)
        if current_http_handler.command == 'GET' and (current_route_path == self.route_prefix_value + '/catalog' or current_file_match):
            try:
                if current_http_handler.headers.get('Host') != f'127.0.0.1:{current_http_handler.server.server_port}':
                    raise ValueError('허용하지 않는 Host')
                if current_file_match:
                    current_file_path = self.job_storage_root / current_file_match[1] / current_file_match[2]
                    response_body_bytes = current_file_path.read_bytes()
                    response_content_type = 'application/zip' if current_file_path.suffix == '.zip' else 'image/png' if current_file_path.suffix == '.png' else 'application/json'
                else:
                    catalog_source_record = {'assets': load_separation_sources()}
                    response_body_bytes = json.dumps({'sources': [{'id': current_source_record['id'], 'label': current_source_record['label'], 'frames': len(current_source_record['frames'])} for current_source_record in catalog_source_record['assets']], 'defaults': load_separation_defaults()}, ensure_ascii=False).encode()
                    response_content_type = 'application/json'
                current_http_handler.send_response(200)
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
