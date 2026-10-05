"""패턴 생성 → 중앙 추출 → 십자 채우기 → 반복 검수 파이프라인."""
import hashlib
import json
from pathlib import Path
from datetime import datetime
import numpy as np
import yaml
from PIL import Image, ImageChops, ImageDraw
from tools.review.common.generation_records import write_record_atomically
from tools.review.common.map_tile_assets import UniqueAssetYamlLoader

PATTERN_CONFIGURATION_PATH = Path(__file__).resolve().parents[4] / 'generators/image/config/seamless_pattern.yaml'


def build_pattern_request(user_prompt_text):
    pattern_config_record = yaml.load(PATTERN_CONFIGURATION_PATH.read_text(), Loader=UniqueAssetYamlLoader)
    expected_config_fields = {'schema_version','grid_size','tile_size','repair_size','grid_prompt','horizontal_prompt','vertical_prompt'}
    if set(pattern_config_record) != expected_config_fields:
        raise ValueError('패턴 생성 설정 필드 오류')
    for config_field_name, expected_field_value in {'schema_version':7,'grid_size':768,'tile_size':256,'repair_size':768}.items():
        if type(pattern_config_record[config_field_name]) is not int or pattern_config_record[config_field_name] != expected_field_value:
            raise ValueError('패턴 생성 고정 설정 오류: '+config_field_name)
    if any(not isinstance(pattern_config_record[current_field_name],str) or not pattern_config_record[current_field_name].strip() for current_field_name in ('horizontal_prompt','vertical_prompt')):
        raise ValueError('단계 프롬프트가 없습니다.')
    if not isinstance(pattern_config_record['grid_prompt'], str) or not pattern_config_record['grid_prompt'].strip():
        raise ValueError('1단계 기본 프롬프트가 없습니다.')
    if not user_prompt_text.strip():
        raise ValueError('패턴 소재를 입력하세요.')
    grid_prompt_text = user_prompt_text.strip()+'\n'+pattern_config_record['grid_prompt']
    repair_prompt_text = pattern_config_record['horizontal_prompt']
    vertical_prompt_text = pattern_config_record['vertical_prompt']
    if any(not 0 < len(current_prompt_text.split()) < 100 for current_prompt_text in (grid_prompt_text,repair_prompt_text,vertical_prompt_text)):
        raise ValueError('각 단계 최종 프롬프트는 100단어 미만이어야 합니다.')
    return grid_prompt_text, {**pattern_config_record,'user_prompt':user_prompt_text.strip(),
        'stage_prompts':[grid_prompt_text,repair_prompt_text,vertical_prompt_text],
        'stage_prompt_words':[len(current_prompt_text.split()) for current_prompt_text in (grid_prompt_text,repair_prompt_text,vertical_prompt_text)],
        'stage_prompt_hashes':[hashlib.sha256(current_prompt_text.encode()).hexdigest() for current_prompt_text in (grid_prompt_text,repair_prompt_text,vertical_prompt_text)],
        'prompt_sha256':hashlib.sha256(grid_prompt_text.encode()).hexdigest(),
        'config_sha256':hashlib.sha256(PATTERN_CONFIGURATION_PATH.read_bytes()).hexdigest()}


def execute_pattern_pipeline(current_job_root, current_request_record, generation_callback_value):
    if current_request_record['seamless_tile']['schema_version'] in (6,7):
        from tools.review.domains.image.seamless_directional import execute_directional_next_stage
        return execute_directional_next_stage(current_job_root, current_request_record, generation_callback_value)
    if current_request_record['seamless_tile']['schema_version'] not in (3,4):
        raise ValueError('폐기되었거나 지원하지 않는 심리스 실행 버전입니다. 새 작업을 생성하세요.')
    from tools.review.domains.image.seamless_generation import build_repeated_texture, measure_texture_boundaries
    pattern_config_record = current_request_record['seamless_tile']
    stage_prompt_values = pattern_config_record['stage_prompts']
    pattern_grid_size = pattern_config_record['grid_size']
    pattern_tile_size = pattern_config_record['tile_size']
    pattern_repair_size = pattern_config_record['repair_size']
    repair_half_size = pattern_repair_size // 2
    vertical_half_width = pattern_config_record['vertical_erasure'] // 2
    horizontal_half_width = pattern_config_record['horizontal_erasure'] // 2
    repair_feather_width = pattern_config_record['feather_width']
    if [hashlib.sha256(current_prompt_text.encode()).hexdigest() for current_prompt_text in stage_prompt_values] != pattern_config_record['stage_prompt_hashes']:
        raise ValueError('단계 프롬프트 해시 오류')

    def execute_pattern_stage(stage_directory_name, stage_index_value, output_image_size, reference_image_paths):
        stage_output_root = current_job_root / stage_directory_name
        stage_output_root.mkdir(exist_ok=True)
        stage_request_record = {'prompt':stage_prompt_values[stage_index_value-1],'width':output_image_size,'height':output_image_size,'steps':40,'seed':current_request_record['seed']}
        stage_request_hash = hashlib.sha256(json.dumps(stage_request_record,sort_keys=True).encode()+b''.join(current_reference_path.read_bytes() for current_reference_path in reference_image_paths)).hexdigest()
        stage_checkpoint_path = stage_output_root/'checkpoint.json'
        write_record_atomically(current_job_root/'pipeline-progress.json',{'stage':stage_directory_name,'index':stage_index_value,'total':2})
        print(f'{datetime.now().isoformat()}/seamless-pattern/stage {stage_directory_name}',flush=True)
        if stage_checkpoint_path.exists():
            stage_checkpoint_record = json.loads(stage_checkpoint_path.read_text())
            if stage_checkpoint_record != {'request_sha256':stage_request_hash,'image_sha256':hashlib.sha256((stage_output_root/'result.png').read_bytes()).hexdigest(),'record_sha256':hashlib.sha256((stage_output_root/'result.json').read_bytes()).hexdigest()}:
                raise ValueError('완료 단계 무결성 오류: '+stage_directory_name)
        else:
            write_record_atomically(stage_output_root/'request.json',stage_request_record)
            generation_callback_value(stage_output_root,stage_request_record,reference_image_paths)
            with Image.open(stage_output_root/'result.png') as stage_result_image:
                if stage_result_image.size != (output_image_size,output_image_size):
                    raise ValueError('단계 출력 크기 오류')
            write_record_atomically(stage_checkpoint_path,{'request_sha256':stage_request_hash,'image_sha256':hashlib.sha256((stage_output_root/'result.png').read_bytes()).hexdigest(),'record_sha256':hashlib.sha256((stage_output_root/'result.json').read_bytes()).hexdigest()})
        return Image.open(stage_output_root/'result.png').convert('RGB')

    generated_grid_image = execute_pattern_stage('stage-1-pattern',1,pattern_grid_size,[])
    generated_grid_image.save(current_job_root/'grid-input.png')
    source_tile_image = generated_grid_image.crop((pattern_tile_size,pattern_tile_size,pattern_tile_size*2,pattern_tile_size*2))
    source_tile_image.save(current_job_root/'center-tile.png')
    shifted_source_image = ImageChops.offset(source_tile_image,pattern_tile_size//2,pattern_tile_size//2).resize((pattern_repair_size,pattern_repair_size),Image.Resampling.LANCZOS)
    separate_mask_enabled = pattern_config_record['schema_version'] == 4
    if pattern_config_record['schema_version'] not in (3,4):
        raise ValueError('패턴 파이프라인 버전 오류')
    erased_reference_image = Image.new('RGB',shifted_source_image.size,'black') if separate_mask_enabled else shifted_source_image.copy()
    reference_image_draw = ImageDraw.Draw(erased_reference_image)
    reference_image_draw.rectangle((repair_half_size-vertical_half_width,0,repair_half_size+vertical_half_width-1,pattern_repair_size-1),fill='white')
    reference_image_draw.rectangle((0,repair_half_size-horizontal_half_width,pattern_repair_size-1,repair_half_size+horizontal_half_width-1),fill='white')
    repair_reference_paths = [current_job_root/'repair-input.png']
    if separate_mask_enabled:
        shifted_source_image.save(current_job_root/'repair-input.png')
        erased_reference_image.save(current_job_root/'repair-mask.png')
        repair_reference_paths.append(current_job_root/'repair-mask.png')
    else:
        erased_reference_image.save(current_job_root/'repair-input.png')
    repaired_pattern_image = execute_pattern_stage('stage-2-repair',2,pattern_repair_size,repair_reference_paths)
    repaired_pattern_image.save(current_job_root/'grid-edited.png')
    if separate_mask_enabled:
        blend_mask_image = erased_reference_image.convert('L')
    else:
        image_row_indices,image_column_indices = np.indices((pattern_repair_size,pattern_repair_size))
        vertical_blend_values = np.clip((vertical_half_width+repair_feather_width-abs(image_column_indices-(repair_half_size-0.5)))/repair_feather_width,0,1)
        horizontal_blend_values = np.clip((horizontal_half_width+repair_feather_width-abs(image_row_indices-(repair_half_size-0.5)))/repair_feather_width,0,1)
        blend_weight_values = np.maximum(vertical_blend_values,horizontal_blend_values)
        blend_mask_image = Image.fromarray((blend_weight_values*255).astype('uint8'))
    composite_repair_image = Image.composite(repaired_pattern_image,shifted_source_image,blend_mask_image)
    composite_repair_image.save(current_job_root/'repair-composite.png')
    final_tile_image = ImageChops.offset(composite_repair_image,repair_half_size,repair_half_size).resize((pattern_tile_size,pattern_tile_size),Image.Resampling.LANCZOS)
    final_tile_image.save(current_job_root/'result.png')
    build_repeated_texture(final_tile_image).save(current_job_root/'tiled-preview.png')
    stage_result_records = [json.loads((current_job_root/current_stage_name/'result.json').read_text()) for current_stage_name in ('stage-1-pattern','stage-2-repair')]
    output_file_names = ('grid-input.png','center-tile.png','repair-input.png','grid-edited.png','result.png','tiled-preview.png')
    if separate_mask_enabled:
        output_file_names += ('repair-mask.png','repair-composite.png')
    write_record_atomically(current_job_root/'result.json',{'size':[pattern_tile_size,pattern_tile_size],'seamless_tile':pattern_config_record,'stages':stage_result_records,'peak_gpu_bytes':max(current_stage_record.get('peak_gpu_bytes',0) for current_stage_record in stage_result_records),'boundary_metrics':measure_texture_boundaries(final_tile_image),'original_boundary_metrics':measure_texture_boundaries(source_tile_image),'sha256':{current_file_name:hashlib.sha256((current_job_root/current_file_name).read_bytes()).hexdigest() for current_file_name in output_file_names},'quality_warnings':['3×3 배열 준수·흰 띠 잔존·반복 연결은 시각 검수가 필요합니다. 경계 점수만으로 채택하지 않습니다.']})
    write_record_atomically(current_job_root/'pipeline-progress.json',{'stage':'completed','index':2,'total':2})
