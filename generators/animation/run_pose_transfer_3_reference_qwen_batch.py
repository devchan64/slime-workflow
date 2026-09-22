#!/usr/bin/env python3
"""YAML 목록으로 4방향 8프레임을 순차 생성하는 3참조 Qwen 실행기."""
import argparse
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import yaml
from PIL import Image

from qwen_pose import execute_pose_generation
from qwen_pose.prompts import UniqueKeySafeLoader


WORKFLOW_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_BATCH_FIELDS = {'schema_version', 'prompt_file', 'output_root', 'references', 'jobs'}
REQUIRED_REFERENCE_FIELDS = {'baseline_root', 'rig_root', 'openpose_root'}
REQUIRED_JOB_FIELDS = {'direction', 'frame_numbers'}
SUPPORTED_DIRECTIONS = ('down_left', 'down_right', 'up_left', 'up_right')
FRAME_COUNT_PER_DIRECTION = 8
REFERENCE_SHEET_SIZE = (2048, 1024)
REFERENCE_CELL_SIZE = (512, 512)


def resolve_relative_workflow_path(relative_path_value, field_name_value):
    if not isinstance(relative_path_value, str) or not relative_path_value.strip() or Path(relative_path_value).is_absolute():
        raise ValueError(f'{field_name_value}는 워크플로 루트 기준 상대 경로여야 합니다.')
    resolved_path_value = (WORKFLOW_REPOSITORY_ROOT / relative_path_value).resolve()
    if not resolved_path_value.is_relative_to(WORKFLOW_REPOSITORY_ROOT.resolve()):
        raise ValueError(f'{field_name_value}가 워크플로 루트를 벗어납니다.')
    return resolved_path_value


def load_batch_definition_file(batch_definition_path):
    parsed_batch_values = yaml.load(batch_definition_path.read_bytes(), Loader=UniqueKeySafeLoader)
    if not isinstance(parsed_batch_values, dict) or set(parsed_batch_values) != REQUIRED_BATCH_FIELDS:
        raise ValueError('배치 YAML 필드는 schema_version/prompt_file/output_root/references/jobs여야 합니다.')
    if parsed_batch_values['schema_version'] != 1:
        raise ValueError('지원하는 배치 YAML schema_version은 1입니다.')
    if not isinstance(parsed_batch_values['references'], dict) or set(parsed_batch_values['references']) != REQUIRED_REFERENCE_FIELDS:
        raise ValueError('references는 baseline_root/rig_root/openpose_root만 가져야 합니다.')
    if not isinstance(parsed_batch_values['jobs'], list) or len(parsed_batch_values['jobs']) != 4:
        raise ValueError('jobs는 4방향을 정확히 가져야 합니다.')
    seen_direction_values = set()
    expanded_job_values = []
    for job_value in parsed_batch_values['jobs']:
        if not isinstance(job_value, dict) or set(job_value) != REQUIRED_JOB_FIELDS:
            raise ValueError('각 jobs 항목은 direction/frame_numbers만 가져야 합니다.')
        direction_value = job_value['direction']
        frame_number_values = job_value['frame_numbers']
        if direction_value not in SUPPORTED_DIRECTIONS or direction_value in seen_direction_values:
            raise ValueError('jobs에는 중복 없는 4방향만 지정해야 합니다.')
        if frame_number_values != list(range(1, FRAME_COUNT_PER_DIRECTION + 1)):
            raise ValueError('각 방향의 frame_numbers는 1부터 8까지여야 합니다.')
        seen_direction_values.add(direction_value)
        expanded_job_values.extend({'direction': direction_value, 'frame_number': frame_number_value} for frame_number_value in frame_number_values)
    if tuple(sorted(seen_direction_values)) != tuple(sorted(SUPPORTED_DIRECTIONS)) or len(expanded_job_values) != 32:
        raise ValueError('배치 목록은 4방향×8프레임, 총 32프레임이어야 합니다.')
    return parsed_batch_values, expanded_job_values


def crop_reference_sheet_cell(source_sheet_path, direction_value, frame_number_value, destination_path):
    with Image.open(source_sheet_path) as source_sheet_image:
        if source_sheet_image.size != REFERENCE_SHEET_SIZE:
            raise ValueError(f'참조 시트 크기 불일치: {source_sheet_path}')
        column_index_value = (frame_number_value - 1) % 4
        row_index_value = (frame_number_value - 1) // 4
        cell_box_values = (column_index_value * 512, row_index_value * 512, (column_index_value + 1) * 512, (row_index_value + 1) * 512)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        source_sheet_image.crop(cell_box_values).convert('RGB').save(destination_path)


def execute_pose_transfer_batch_generation(batch_definition_path, run_output_root=None, generation_mode='three-reference-qwen', selected_inference_steps=4):
    if generation_mode not in ('three-reference-qwen', 'anypose-lightning'):
        raise ValueError('지원하지 않는 배치 생성 모드입니다.')
    if selected_inference_steps not in (4, 10, 20, 30):
        raise ValueError('배치 steps는 4, 10, 20, 30만 허용합니다.')
    batch_values, expanded_job_values = load_batch_definition_file(batch_definition_path)
    prompt_file_path = resolve_relative_workflow_path(batch_values['prompt_file'], 'prompt_file')
    output_root_base_value = resolve_relative_workflow_path(batch_values['output_root'], 'output_root')
    output_root_value = (run_output_root or output_root_base_value / datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')).resolve()
    if not output_root_value.is_relative_to((WORKFLOW_REPOSITORY_ROOT / '.tmp').resolve()):
        raise ValueError('배치 출력은 워크플로 .tmp 아래여야 합니다.')
    reference_root_values = {reference_name_value: resolve_relative_workflow_path(reference_path_value, f'references.{reference_name_value}') for reference_name_value, reference_path_value in batch_values['references'].items()}
    prompt_source_text = prompt_file_path.read_text(encoding='utf-8').strip()
    if not prompt_source_text:
        raise ValueError('프롬프트 파일이 비어 있습니다.')
    output_root_value.mkdir(parents=True, exist_ok=True)
    batch_logger = logging.getLogger('pose-transfer-3-reference-qwen-batch')
    batch_logger.setLevel(logging.INFO)
    batch_logger.handlers.clear()
    batch_logger.addHandler(logging.FileHandler(output_root_value / 'batch.log'))
    batch_logger.addHandler(logging.StreamHandler())
    completed_result_values = []
    for job_index_value, job_value in enumerate(expanded_job_values, 1):
        direction_value = job_value['direction']
        frame_number_value = job_value['frame_number']
        frame_output_root = output_root_value / direction_value / f'frame-{frame_number_value:02d}'
        frame_output_root.mkdir(parents=True, exist_ok=False)
        batch_logger.info('%s/pose-transfer-3-reference-qwen/start %s/32 direction=%s frame=%s', __import__('datetime').datetime.now().isoformat(), job_index_value, direction_value, frame_number_value)
        character_reference_path = reference_root_values['baseline_root'] / f'{direction_value}.png'
        rig_sheet_path = reference_root_values['rig_root'] / f'{direction_value}.png'
        openpose_sheet_path = reference_root_values['openpose_root'] / f'{direction_value}.png'
        rig_reference_path = frame_output_root / 'rig-reference.png'
        openpose_reference_path = frame_output_root / 'openpose-reference.png'
        crop_reference_sheet_cell(rig_sheet_path, direction_value, frame_number_value, rig_reference_path)
        crop_reference_sheet_cell(openpose_sheet_path, direction_value, frame_number_value, openpose_reference_path)
        character_reference_copy_path = frame_output_root / 'character-reference.png'
        with Image.open(character_reference_path) as character_reference_image:
            if character_reference_image.size != REFERENCE_CELL_SIZE:
                raise ValueError(f'베이스라인 셀 크기 불일치: {character_reference_path}')
            if character_reference_image.mode == 'RGBA':
                white_background_image = Image.new('RGBA', character_reference_image.size, (255, 255, 255, 255))
                character_reference_image = Image.alpha_composite(white_background_image, character_reference_image)
            character_reference_image.convert('RGB').save(character_reference_copy_path)
        generation_arguments = {'trial_output_root': frame_output_root, 'prompt_text_value': prompt_source_text, 'character_image_path': character_reference_copy_path, 'pose_reference_path': rig_reference_path, 'pose_reference_kind': 'rig', 'selected_reference_order': 'standing-first', 'selected_inference_steps': selected_inference_steps, 'prompt_source_record': {'kind': 'yaml-batch', 'batch_file': str(batch_definition_path.relative_to(WORKFLOW_REPOSITORY_ROOT)), 'sha256': hashlib.sha256(prompt_source_text.encode()).hexdigest()}}
        if generation_mode == 'three-reference-qwen':
            generation_arguments.update(additional_reference_paths=(openpose_reference_path,), enable_anypose_adapter=False, enable_lightning_adapter=True, enable_standalone_lightning_adapter=True)
        else:
            generation_arguments.update(enable_anypose_adapter=True, enable_lightning_adapter=True)
        result_record_value = execute_pose_generation(**generation_arguments)
        completed_result_values.append({'direction': direction_value, 'frame': frame_number_value, 'output': str(frame_output_root.relative_to(output_root_value)), 'result_sha256': hashlib.sha256((frame_output_root / 'result.png').read_bytes()).hexdigest(), 'status': result_record_value['status']})
        batch_logger.info('%s/pose-transfer-3-reference-qwen/complete %s/32', __import__('datetime').datetime.now().isoformat(), job_index_value)
    (output_root_value / 'batch-result.yaml').write_text(yaml.safe_dump({'schema_version': 1, 'status': 'completed', 'frame_count': len(completed_result_values), 'frames': completed_result_values}, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return completed_result_values


def run_pose_transfer_batch_command():
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument('--batch-file', type=Path, required=True)
    argument_parser.add_argument('--output-dir', type=Path)
    argument_parser.add_argument('--mode', choices=('three-reference-qwen', 'anypose-lightning'), default='three-reference-qwen')
    argument_parser.add_argument('--steps', type=int, choices=(4, 10, 20, 30), default=4)
    parsed_arguments = argument_parser.parse_args()
    execute_pose_transfer_batch_generation(parsed_arguments.batch_file.resolve(), parsed_arguments.output_dir, parsed_arguments.mode, parsed_arguments.steps)


if __name__ == '__main__':
    run_pose_transfer_batch_command()
