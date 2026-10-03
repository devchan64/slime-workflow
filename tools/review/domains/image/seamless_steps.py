"""Qwen 2.1 심리스 패턴의 일곱 단계·검수 체크포인트."""
import hashlib
import json
from datetime import datetime
from PIL import Image
from tools.review.common.generation_records import write_record_atomically

SEAMLESS_STAGE_LABELS = ('패턴 이미지 생성', '9등분', '중앙 패턴 샘플', '샘플 3×3 배열', '중앙 심리스 보정', '중앙 심리스 패턴 추출', '3×3 반복 검수')
SEAMLESS_STAGE_OUTPUTS = (
    ('grid-input.png', 'stage-1-pattern/result.png', 'stage-1-pattern/result.json'),
    tuple(f'cell-{row_index_value}-{column_index_value}.png' for row_index_value in range(1,4) for column_index_value in range(1,4)) + ('split-preview.png',),
    ('center-tile.png',), ('sample-grid.png',),
    ('grid-edited.png', 'stage-5-repair/result.png', 'stage-5-repair/result.json'),
    ('result.png',), ('tiled-preview.png', 'result.json'),
)


def calculate_stage_file_hash(current_file_path):
    return hashlib.sha256(current_file_path.read_bytes()).hexdigest()


def read_seamless_stage_checkpoints(current_job_root, current_request_record):
    request_digest_value = hashlib.sha256(json.dumps(current_request_record,sort_keys=True).encode()).hexdigest()
    completed_stage_count = 0
    for stage_index_value in range(1,8):
        checkpoint_file_path = current_job_root/f'stage-{stage_index_value}.checkpoint.json'
        if not checkpoint_file_path.exists():
            if any((current_job_root/f'stage-{later_stage_index}.checkpoint.json').exists() for later_stage_index in range(stage_index_value+1,8)):
                raise ValueError('단계 체크포인트 순서 오류')
            break
        checkpoint_record_value = json.loads(checkpoint_file_path.read_text())
        expected_hash_values = {current_file_name:calculate_stage_file_hash(current_job_root/current_file_name) for current_file_name in SEAMLESS_STAGE_OUTPUTS[stage_index_value-1]}
        if checkpoint_record_value != {'request_sha256':request_digest_value,'files':expected_hash_values}:
            raise ValueError(f'{stage_index_value}단계 체크포인트 무결성 오류')
        completed_stage_count = stage_index_value
    return completed_stage_count, request_digest_value


def execute_seamless_next_stage(current_job_root, current_request_record, generation_callback_value):
    from tools.review.domains.image.seamless_generation import build_repeated_texture, measure_texture_boundaries
    completed_stage_count, request_digest_value = read_seamless_stage_checkpoints(current_job_root,current_request_record)
    if completed_stage_count == 7:
        return
    if (current_job_root/'pause.request').exists():
        write_record_atomically(current_job_root/'stage-pause.json',{'completed':completed_stage_count})
        return
    stage_index_value = completed_stage_count+1
    pattern_config_record = current_request_record['seamless_tile']
    stage_prompt_values = pattern_config_record['stage_prompts']
    if [hashlib.sha256(current_prompt_text.encode()).hexdigest() for current_prompt_text in stage_prompt_values] != pattern_config_record['stage_prompt_hashes']:
        raise ValueError('단계 프롬프트 해시 오류')
    write_record_atomically(current_job_root/'pipeline-progress.json',{'stage':SEAMLESS_STAGE_LABELS[stage_index_value-1],'index':stage_index_value,'completed':completed_stage_count,'total':7})
    print(f'{datetime.now().isoformat()}/seamless-pattern/stage {stage_index_value}/7 {SEAMLESS_STAGE_LABELS[stage_index_value-1]}',flush=True)
    if stage_index_value in (1,5):
        stage_output_root = current_job_root/('stage-1-pattern' if stage_index_value==1 else 'stage-5-repair')
        stage_output_root.mkdir(exist_ok=True)
        selected_prompt_index = 0 if stage_index_value==1 else 1
        output_image_size = pattern_config_record['grid_size' if stage_index_value==1 else 'repair_size']
        stage_request_record = {'prompt':stage_prompt_values[selected_prompt_index], 'width':output_image_size,'height':output_image_size,'steps':40,'seed':current_request_record['seed']}
        write_record_atomically(stage_output_root/'request.json',stage_request_record)
        generation_callback_value(stage_output_root,stage_request_record,[] if stage_index_value==1 else [current_job_root/'sample-grid.png'])
        with Image.open(stage_output_root/'result.png') as generated_image_value:
            if generated_image_value.size != (output_image_size,output_image_size):
                raise ValueError('단계 출력 크기 오류')
            generated_image_value.convert('RGB').save(current_job_root/('grid-input.png' if stage_index_value==1 else 'grid-edited.png'))
    elif stage_index_value==2:
        with Image.open(current_job_root/'grid-input.png') as source_grid_image:
            preview_grid_image = Image.new('RGB',(3*256,3*256))
            for row_index_value in range(3):
                for column_index_value in range(3):
                    crop_box_value=(column_index_value*source_grid_image.width//3,row_index_value*source_grid_image.height//3,(column_index_value+1)*source_grid_image.width//3,(row_index_value+1)*source_grid_image.height//3)
                    cell_image_value=source_grid_image.crop(crop_box_value)
                    cell_image_value.save(current_job_root/f'cell-{row_index_value+1}-{column_index_value+1}.png')
                    preview_grid_image.paste(cell_image_value.resize((252,252)),(column_index_value*256+2,row_index_value*256+2))
            preview_grid_image.save(current_job_root/'split-preview.png')
    elif stage_index_value==3:
        with Image.open(current_job_root/'cell-2-2.png') as center_sample_image:
            center_sample_image.save(current_job_root/'center-tile.png')
    elif stage_index_value==4:
        with Image.open(current_job_root/'center-tile.png') as center_sample_image:
            build_repeated_texture(center_sample_image).save(current_job_root/'sample-grid.png')
    elif stage_index_value==6:
        with Image.open(current_job_root/'grid-edited.png') as repaired_grid_image:
            center_crop_box=(repaired_grid_image.width//3,repaired_grid_image.height//3,2*repaired_grid_image.width//3,2*repaired_grid_image.height//3)
            repaired_grid_image.crop(center_crop_box).resize((pattern_config_record['tile_size'],)*2,Image.Resampling.LANCZOS).save(current_job_root/'result.png')
    elif stage_index_value==7:
        with Image.open(current_job_root/'result.png') as final_pattern_image, Image.open(current_job_root/'center-tile.png') as original_sample_image:
            build_repeated_texture(final_pattern_image).save(current_job_root/'tiled-preview.png')
            result_record_value={'size':list(final_pattern_image.size),'boundary_metrics':measure_texture_boundaries(final_pattern_image),'original_boundary_metrics':measure_texture_boundaries(original_sample_image.resize(final_pattern_image.size)), 'seamless_tile':pattern_config_record,'quality_warnings':['AI 보정만으로 심리스 연결을 보장하지 않습니다. 3×3 반복 화면에서 검수하세요.']}
        write_record_atomically(current_job_root/'result.json',result_record_value)
    write_record_atomically(current_job_root/f'stage-{stage_index_value}.checkpoint.json',{'request_sha256':request_digest_value,'files':{current_file_name:calculate_stage_file_hash(current_job_root/current_file_name) for current_file_name in SEAMLESS_STAGE_OUTPUTS[stage_index_value-1]}})
    write_record_atomically(current_job_root/'pipeline-progress.json',{'stage':SEAMLESS_STAGE_LABELS[stage_index_value-1]+' 완료','index':stage_index_value,'completed':stage_index_value,'total':7})
    if stage_index_value < 4 and not (current_job_root/'cancel.request').exists():
        return execute_seamless_next_stage(current_job_root, current_request_record, generation_callback_value)
    if stage_index_value<7:
        write_record_atomically(current_job_root/'stage-pause.json',{'completed':stage_index_value})
    print(f'{datetime.now().isoformat()}/seamless-pattern/finish {stage_index_value}/7 저장 완료',flush=True)
