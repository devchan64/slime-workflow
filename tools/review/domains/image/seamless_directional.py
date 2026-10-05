"""가로 연결 후 세로 연결을 수행하는 다섯 단계 파이프라인."""
import hashlib
from datetime import datetime
from PIL import Image
from tools.review.common.generation_records import write_record_atomically
from tools.review.domains.image.seamless_steps import read_seamless_stage_checkpoints, calculate_stage_file_hash

DIRECTIONAL_STAGE_LABELS = ('패턴 이미지 생성', '가로 3등분 · 중앙 샘플 3열 배열', '좌우 경계 연결', '세로 3등분 · 중앙 샘플 3행 배열', '상하 경계 연결')
DIRECTIONAL_STAGE_OUTPUTS = (
    ('grid-input.png','stage-1-pattern/result.png','stage-1-pattern/result.json'),
    ('center-tile.png','sample-grid.png'),
    ('repair-input.png','grid-edited.png','stage-3-horizontal/result.png','stage-3-horizontal/result.json'),
    ('split-preview.png','repair-composite.png'),
    ('repair-mask.png','result.png','tiled-preview.png','result.json','stage-5-vertical/result.png','stage-5-vertical/result.json'),
)
DIRECTIONAL_PREVIEW_LABELS = (
    ('grid-input.png','1단계 · 패턴 원본'),
    ('center-tile.png','2단계 · 가운데 세로 띠 샘플'),('sample-grid.png','2단계 · 가로 3열 배열'),
    ('repair-input.png','3단계 · 연결 보정 참조'),('grid-edited.png','3단계 · 좌우 연결 결과'),
    ('split-preview.png','4단계 · 가운데 가로 띠 샘플'),('repair-composite.png','4단계 · 세로 3행 배열'),
    ('repair-mask.png','5단계 · 연결 보정 참조'),('stage-5-vertical/result.png','5단계 · 상하 연결 원본'),('result.png','최종 산출물 · 중앙 타일'),
    ('tiled-preview.png','최종 중앙 타일 · 3×3 반복 검수'),
)


def build_directional_sample_array(source_image_value, horizontal_axis_enabled):
    """정수 비례 중앙 구간을 크기 변형 없이 세 번 배열한다."""
    source_image_width, source_image_height = source_image_value.size
    center_sample_box = (source_image_width//3,0,2*source_image_width//3,source_image_height) if horizontal_axis_enabled else (0,source_image_height//3,source_image_width,2*source_image_height//3)
    center_sample_image = source_image_value.crop(center_sample_box).convert('RGB')
    repeated_array_size = (center_sample_image.width*3,center_sample_image.height) if horizontal_axis_enabled else (center_sample_image.width,center_sample_image.height*3)
    repeated_array_image = Image.new('RGB',repeated_array_size)
    for sample_copy_index in range(3):
        sample_paste_position = (sample_copy_index*center_sample_image.width,0) if horizontal_axis_enabled else (0,sample_copy_index*center_sample_image.height)
        repeated_array_image.paste(center_sample_image,sample_paste_position)
    return center_sample_image, repeated_array_image


def execute_directional_next_stage(current_job_root, current_request_record, generation_callback_value):
    from tools.review.domains.image.seamless_generation import build_repeated_texture, measure_texture_boundaries
    completed_stage_count, request_digest_value = read_seamless_stage_checkpoints(current_job_root,current_request_record,DIRECTIONAL_STAGE_OUTPUTS)
    if completed_stage_count == 5:
        return
    if (current_job_root/'pause.request').exists():
        write_record_atomically(current_job_root/'stage-pause.json',{'completed':completed_stage_count})
        return
    stage_index_value = completed_stage_count+1
    pattern_config_record = current_request_record['seamless_tile']
    stage_prompt_values = pattern_config_record['stage_prompts']
    if [hashlib.sha256(current_prompt_text.encode()).hexdigest() for current_prompt_text in stage_prompt_values] != pattern_config_record['stage_prompt_hashes']:
        raise ValueError('단계 프롬프트 해시 오류')
    write_record_atomically(current_job_root/'pipeline-progress.json',{'stage':DIRECTIONAL_STAGE_LABELS[stage_index_value-1],'index':stage_index_value,'completed':completed_stage_count,'total':5})
    print(f'{datetime.now().isoformat()}/seamless-pattern/stage {stage_index_value}/5 {DIRECTIONAL_STAGE_LABELS[stage_index_value-1]}',flush=True)
    if stage_index_value in (2,4):
        source_image_name = 'grid-input.png' if stage_index_value==2 else 'grid-edited.png'
        with Image.open(current_job_root/source_image_name) as source_image_value:
            center_sample_image, repeated_array_image = build_directional_sample_array(source_image_value,stage_index_value==2)
        center_sample_image.save(current_job_root/('center-tile.png' if stage_index_value==2 else 'split-preview.png'))
        repeated_array_image.save(current_job_root/('sample-grid.png' if stage_index_value==2 else 'repair-composite.png'))
    else:
        stage_directory_name = {1:'stage-1-pattern',3:'stage-3-horizontal',5:'stage-5-vertical'}[stage_index_value]
        stage_output_root = current_job_root/stage_directory_name
        stage_output_root.mkdir(exist_ok=True)
        reference_image_paths = []
        if stage_index_value != 1:
            with Image.open(current_job_root/('sample-grid.png' if stage_index_value==3 else 'repair-composite.png')) as repeated_array_image:
                repair_reference_image = repeated_array_image.convert('RGB')
            # 기존 기록의 게시 경로를 유지하며 원본 배열을 그대로 전달한다.
            reference_image_path = current_job_root/('repair-input.png' if stage_index_value==3 else 'repair-mask.png')
            repair_reference_image.save(reference_image_path)
            reference_image_paths.append(reference_image_path)
        output_image_size = pattern_config_record['grid_size' if stage_index_value==1 else 'repair_size']
        actual_stage_prompt = stage_prompt_values[stage_index_value//2]
        if stage_index_value != 1 and pattern_config_record['schema_version'] == 6:
            # 구버전 재개도 중앙 삭제 지시를 사용하지 않는다. 실제 입력은 단계 기록에 보존한다.
            from tools.review.domains.image.seamless_pattern import build_pattern_request
            unused_grid_prompt, latest_pattern_config = build_pattern_request(pattern_config_record['user_prompt'])
            actual_stage_prompt = latest_pattern_config['stage_prompts'][stage_index_value//2]
        stage_request_record = {'prompt':actual_stage_prompt,'width':output_image_size,'height':output_image_size,'steps':40,'seed':current_request_record['seed']}
        write_record_atomically(stage_output_root/'request.json',stage_request_record)
        generation_callback_value(stage_output_root,stage_request_record,reference_image_paths)
        with Image.open(stage_output_root/'result.png') as generated_image_value:
            if generated_image_value.size != (output_image_size,output_image_size):
                raise ValueError('단계 출력 크기 오류')
            final_result_image = generated_image_value.convert('RGB')
        final_result_image.save(current_job_root/{1:'grid-input.png',3:'grid-edited.png',5:'result.png'}[stage_index_value])
        if stage_index_value==5:
            final_image_width, final_image_height = final_result_image.size
            central_preview_box = (final_image_width//3,final_image_height//3,2*final_image_width//3,2*final_image_height//3)
            central_preview_tile = final_result_image.crop(central_preview_box)
            central_preview_tile.save(current_job_root/'result.png')
            build_repeated_texture(central_preview_tile).save(current_job_root/'tiled-preview.png')
            write_record_atomically(current_job_root/'result.json',{'size':list(central_preview_tile.size),'source_image':'stage-5-vertical/result.png','source_size':list(final_result_image.size),'crop_box':list(central_preview_box),'seamless_tile':pattern_config_record,'preview_crop_box':list(central_preview_box),'preview_tile_size':list(central_preview_tile.size),'boundary_metrics':measure_texture_boundaries(central_preview_tile),'quality_warnings':['중앙 타일이 최종 산출물입니다. 3×3 반복 검수 후 채택하세요. 정식 등록은 하지 않습니다.']})
    write_record_atomically(current_job_root/f'stage-{stage_index_value}.checkpoint.json',{'request_sha256':request_digest_value,'files':{current_file_name:calculate_stage_file_hash(current_job_root/current_file_name) for current_file_name in DIRECTIONAL_STAGE_OUTPUTS[stage_index_value-1]}})
    write_record_atomically(current_job_root/'pipeline-progress.json',{'stage':DIRECTIONAL_STAGE_LABELS[stage_index_value-1]+' 완료','index':stage_index_value,'completed':stage_index_value,'total':5})
    if stage_index_value<5:
        write_record_atomically(current_job_root/'stage-pause.json',{'completed':stage_index_value})
    print(f'{datetime.now().isoformat()}/seamless-pattern/finish {stage_index_value}/5 저장 완료',flush=True)
