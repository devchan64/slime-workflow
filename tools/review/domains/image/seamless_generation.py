"""반복 타일의 연결 보정과 중앙 추출 서비스."""
import hashlib
import io
import json
from datetime import datetime
from pathlib import Path

import yaml
from PIL import Image, ImageChops, ImageStat
from tools.review.common.map_tile_assets import UniqueAssetYamlLoader
from tools.review.domains.image.image_generation import ImageGenerationManager, MANAGER_HISTORY_ROOT
from tools.review.domains.image.three_reference_generation import validate_three_reference_request, decode_reference_image, verify_reference_snapshots

WORKFLOW_ROOT_PATH = Path(__file__).resolve().parents[4]
SEAMLESS_CONFIGURATION_PATH = WORKFLOW_ROOT_PATH / 'generators/image/config/seamless_tile.yaml'


def load_seamless_configuration():
    current_config_record = yaml.load(SEAMLESS_CONFIGURATION_PATH.read_text(), Loader=UniqueAssetYamlLoader)
    if not isinstance(current_config_record, dict) or set(current_config_record) != {'schema_version', 'tile_size', 'grid_size', 'base_prompt'}:
        raise ValueError('연결 타일 설정 필드 오류')
    for current_field_name, expected_field_value in (('schema_version', 2), ('tile_size', 256), ('grid_size', 3)):
        if type(current_config_record[current_field_name]) is not int or current_config_record[current_field_name] != expected_field_value:
            raise ValueError('연결 타일 고정 설정 오류: ' + current_field_name)
    if not isinstance(current_config_record['base_prompt'], str) or not current_config_record['base_prompt'].strip():
        raise ValueError('연결 보정 프롬프트가 없습니다.')
    return current_config_record


def build_seamless_prompt(user_prompt_text):
    current_config_record = load_seamless_configuration()
    final_prompt_text = user_prompt_text.strip() + '. ' + current_config_record['base_prompt'].strip()
    if len(final_prompt_text.split()) >= 100:
        raise ValueError('최종 프롬프트는 100단어 미만이어야 합니다.')
    return final_prompt_text, {**current_config_record, 'user_prompt': user_prompt_text.strip(),
        'prompt_word_count': len(final_prompt_text.split()),
        'prompt_sha256': hashlib.sha256(final_prompt_text.encode()).hexdigest(),
        'config_sha256': hashlib.sha256(SEAMLESS_CONFIGURATION_PATH.read_bytes()).hexdigest()}


def validate_seamless_request(request_record_value):
    current_request_record = validate_three_reference_request(request_record_value, allowed_inference_steps=(40,))
    if not current_request_record['images']:
        from tools.review.domains.image.seamless_pattern import build_pattern_request
        if (current_request_record['width'], current_request_record['height']) != (768,768):
            raise ValueError('패턴 생성 출력은 768×768 고정입니다.')
        final_prompt_text, prompt_source_record = build_pattern_request(current_request_record['prompt'])
        return {**current_request_record,'prompt':final_prompt_text,'seamless_tile':prompt_source_record}
    if len(current_request_record['images']) != 1:
        raise ValueError('정사각형 원본 타일 한 장을 첨부하세요.')
    with Image.open(io.BytesIO(decode_reference_image(current_request_record['images'][0]))) as source_tile_image:
        if source_tile_image.width != source_tile_image.height:
            raise ValueError('원본 타일은 정사각형이어야 합니다. 먼저 원하는 영역을 크롭하세요.')
    if (current_request_record['width'], current_request_record['height']) != (768, 768):
        raise ValueError('연결 보정 출력은 768×768 고정입니다.')
    final_prompt_text, prompt_source_record = build_seamless_prompt(current_request_record['prompt'])
    return {**current_request_record, 'prompt': final_prompt_text, 'seamless_tile': prompt_source_record}


def build_repeated_texture(source_tile_image):
    repeated_texture_image = Image.new('RGB', (source_tile_image.width * 3, source_tile_image.height * 3))
    for current_row_index in range(3):
        for current_column_index in range(3):
            repeated_texture_image.paste(source_tile_image, (current_column_index * source_tile_image.width, current_row_index * source_tile_image.height))
    return repeated_texture_image


def prepare_seamless_reference(current_job_root, current_request_record):
    current_source_record = current_request_record['seamless_tile']
    if current_source_record['schema_version'] not in (1, 2) or current_source_record['tile_size'] != 256 or current_source_record['grid_size'] != 3:
        raise ValueError('지원하지 않는 연결 타일 실행 설정')
    print(f'{datetime.now().isoformat()}/seamless-tile/prepare 256 타일 3×3 배열', flush=True)
    with Image.open(current_job_root / 'reference-1.png') as source_tile_image:
        if source_tile_image.width != source_tile_image.height:
            raise ValueError('저장된 원본 타일이 정사각형이 아닙니다.')
        normalized_tile_image = source_tile_image.convert('RGB').resize((256, 256), Image.Resampling.LANCZOS)
    grid_reference_path = current_job_root / 'grid-input.png'
    build_repeated_texture(normalized_tile_image).save(grid_reference_path)
    return grid_reference_path



def measure_texture_boundaries(source_tile_image):
    """반대편 픽셀의 RGB 평균 차이. 낮을수록 경계 색상 차이가 작다."""
    current_rgb_image = source_tile_image.convert('RGB')
    current_image_width, current_image_height = current_rgb_image.size
    horizontal_edge_difference = ImageChops.difference(
        current_rgb_image.crop((0, 0, 1, current_image_height)),
        current_rgb_image.crop((current_image_width - 1, 0, current_image_width, current_image_height)))
    vertical_edge_difference = ImageChops.difference(
        current_rgb_image.crop((0, 0, current_image_width, 1)),
        current_rgb_image.crop((0, current_image_height - 1, current_image_width, current_image_height)))
    return {
        'left_right_rgb_mae': round(sum(ImageStat.Stat(horizontal_edge_difference).mean) / 3, 3),
        'top_bottom_rgb_mae': round(sum(ImageStat.Stat(vertical_edge_difference).mean) / 3, 3),
        'note': '0~255 RGB 경계 차이이며 형태 연결·시각 품질을 보장하지 않습니다.',
    }


def finish_seamless_generation(current_job_root, current_request_record):
    print(f'{datetime.now().isoformat()}/seamless-tile/crop 중앙 256×256 추출', flush=True)
    with Image.open(current_job_root / 'result.png') as generated_grid_image:
        if generated_grid_image.size != (768, 768):
            raise ValueError('보정 결과는 768×768이어야 합니다.')
        generated_grid_image.save(current_job_root / 'grid-edited.png')
        center_tile_image = generated_grid_image.crop((256, 256, 512, 512)).convert('RGB')
    generation_result_path = current_job_root / 'result.json'
    generation_result_record = json.loads(generation_result_path.read_text())
    generation_result_record['generation_size'] = generation_result_record['size']
    generation_result_record['size'] = [256, 256]
    generation_result_record['boundary_metrics'] = measure_texture_boundaries(center_tile_image)
    generation_result_record['seamless_tile'] = current_request_record['seamless_tile']
    generation_result_record['quality_warnings'].append('중앙 크롭의 주기 경계는 반복 검수가 필요합니다.')
    generation_result_path.write_text(json.dumps(generation_result_record, ensure_ascii=False, indent=2))
    center_tile_image.save(current_job_root / 'result.png')
    build_repeated_texture(center_tile_image).save(current_job_root / 'tiled-preview.png')
    output_hash_records = {current_file_name: hashlib.sha256((current_job_root / current_file_name).read_bytes()).hexdigest()
        for current_file_name in ('reference-1.png', 'grid-input.png', 'grid-edited.png', 'result.png', 'tiled-preview.png')}
    (current_job_root / 'seamless-result.json').write_text(json.dumps({
        'source': current_request_record['seamless_tile'], 'crop_box': [256, 256, 512, 512],
        'boundary_metrics': generation_result_record['boundary_metrics'],
        'sha256': output_hash_records, 'quality_warnings': ['AI 편집은 주기 경계를 보장하지 않습니다. 반복 미리보기를 검수하세요.']}, ensure_ascii=False, indent=2))
    print(f'{datetime.now().isoformat()}/seamless-tile/complete 중앙 타일·반복 검수 이미지 저장', flush=True)


class SeamlessGenerationManager(ImageGenerationManager):
    def __init__(self):
        super().__init__(three_reference_mode=True)
        self.route_prefix_value = '/seamless-tile-generator'
        self.job_storage_root = WORKFLOW_ROOT_PATH / '.tmp/test/seamless-tile-generator'

    def select_generation_runner(self, saved_request_record=None):
        if saved_request_record and saved_request_record.get('seamless_tile', {}).get('schema_version') == 1:
            return 'generators/image/run_qwen_2511_three_reference.py'
        return 'generators/image/run_qwen_21_reference.py'

    def validate_generation_runtime(self, saved_request_record=None):
        if self.select_generation_runner(saved_request_record).endswith('run_qwen_21_reference.py'):
            from generators.image.qwen_21_runtime import validate_qwen_model_assets
            validate_qwen_model_assets()
            from tools.review.domains.image.image_runtime import validate_image_runtime
            validate_image_runtime(WORKFLOW_ROOT_PATH / '.venv-qwen21')
        else:
            super().validate_generation_runtime(saved_request_record)

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'seamless-tile'

    def validate_generation_request(self, request_record_value):
        return validate_seamless_request(request_record_value)

    def validate_generation_resume(self, selected_job_directory):
        current_request_record = json.loads((selected_job_directory / 'request.json').read_text())
        verify_reference_snapshots(selected_job_directory, current_request_record)
        if current_request_record.get('seamless_tile', {}).get('schema_version') not in (1, 2, 3, 4, 6, 7):
            raise ValueError('폐기되었거나 지원하지 않는 심리스 실행 버전입니다. 기존 결과를 조회하거나 새 작업을 생성하세요.')
        if hashlib.sha256(current_request_record['prompt'].encode()).hexdigest() != current_request_record['seamless_tile']['prompt_sha256']:
            raise ValueError('저장된 프롬프트 해시가 일치하지 않습니다.')

    def read_generation_status_record(self, current_job_root, fallback_status_record=None, include_log_value=False):
        return self.enrich_generation_status(current_job_root,super().read_generation_status_record(current_job_root,fallback_status_record,include_log_value))

    def pause_generation_stage(self, selected_job_directory):
        current_request_record = json.loads((selected_job_directory/'request.json').read_text())
        if current_request_record.get('seamless_tile',{}).get('schema_version') not in (6,7):
            raise ValueError('단계별 패턴 생성 작업만 일시정지할 수 있습니다.')
        current_status_record = json.loads((selected_job_directory/'status.json').read_text())
        if current_status_record['status'] not in ('running','queued','paused'):
            raise ValueError('실행·대기·검수 대기 작업만 일시정지할 수 있습니다.')
        (selected_job_directory/'pause.request').touch()
        return {'id':selected_job_directory.name,'status':current_status_record['status'],'message':'현재 단계 저장 후 일시정지합니다. 완료한 단계는 유지합니다.'}

    def enrich_generation_status(self, current_job_root, current_status_record):
        progress_record_path = current_job_root/'pipeline-progress.json'
        if progress_record_path.exists():
            current_status_record['pipeline'] = json.loads(progress_record_path.read_text())
        if current_status_record.get('pipeline',{}).get('total') == 5:
            current_pipeline_record = current_status_record['pipeline']
            current_status_record['progress'] = {'stage':current_status_record['status'],'label':current_pipeline_record['stage'],'step':current_pipeline_record.get('completed',0),'total':current_pipeline_record['total'],'percent':round(current_pipeline_record.get('completed',0)*100/current_pipeline_record['total']),'unit':'단계'}
        current_status_record['previews'] = {current_file_name:f'{self.route_prefix_value}/jobs/{current_job_root.name}/{current_file_name}' for current_file_name in ('grid-input.png','split-preview.png','sample-grid.png','center-tile.png','repair-input.png','repair-mask.png','repair-composite.png','grid-edited.png','result.png','tiled-preview.png') if (current_job_root/current_file_name).is_file()}
        if current_status_record['status'] == 'completed':
            current_status_record['repeated_image'] = f'{self.route_prefix_value}/jobs/{current_job_root.name}/tiled-preview.png'
        return current_status_record
