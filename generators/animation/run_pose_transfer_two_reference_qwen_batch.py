#!/usr/bin/env python3
"""OpenPose 단일 참조로 32프레임을 생성하는 Qwen 배치 실행기."""
import argparse
import hashlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import yaml
from PIL import Image
from qwen_pose import execute_pose_generation
from qwen_pose.prompts import UniqueKeySafeLoader
from generate_pose_transfer_openpose_qwen import DIRECTION_POSE_INSTRUCTIONS

WORKFLOW_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DIRECTIONS = ('down_left', 'down_right', 'up_left', 'up_right')


def load_two_reference_batch_definition(batch_file_path, selected_direction_names):
    values = yaml.load(batch_file_path.read_bytes(), Loader=UniqueKeySafeLoader)
    if set(values) != {'schema_version', 'prompt_file', 'output_root', 'references', 'jobs'} or values['schema_version'] != 1:
        raise ValueError('배치 YAML 형식이 올바르지 않습니다.')
    if set(values['references']) != {'baseline_root', 'openpose_root'}:
        raise ValueError('references가 필요합니다.')
    expanded_jobs = []
    for job in values['jobs']:
        if set(job) != {'direction', 'frame_numbers'} or job['direction'] not in DIRECTIONS or job['frame_numbers'] != list(range(1, 9)):
            raise ValueError('각 방향은 1~8프레임을 가져야 합니다.')
        if job['direction'] not in selected_direction_names:
            continue
        expanded_jobs.extend({'direction': job['direction'], 'frame': frame} for frame in job['frame_numbers'])
    if len(expanded_jobs) != len(selected_direction_names) * 8:
        raise ValueError('선택 방향의 프레임 수가 올바르지 않습니다.')
    return values, expanded_jobs


def resolve_workflow_relative_path(relative_path_value):
    path_value = Path(relative_path_value)
    if path_value.is_absolute():
        raise ValueError('참조 경로는 상대 경로여야 합니다.')
    resolved_path = (WORKFLOW_REPOSITORY_ROOT / path_value).resolve()
    if not resolved_path.is_relative_to(WORKFLOW_REPOSITORY_ROOT.resolve()):
        raise ValueError('참조 경로가 저장소 밖입니다.')
    return resolved_path


def crop_sheet_frame(source_sheet_path, frame_number, destination_path):
    with Image.open(source_sheet_path) as source_image:
        if source_image.size != (2048, 1024):
            raise ValueError(f'시트 크기 불일치: {source_sheet_path}')
        column = (frame_number - 1) % 4
        row = (frame_number - 1) // 4
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        source_image.crop((column * 512, row * 512, (column + 1) * 512, (row + 1) * 512)).convert('RGB').save(destination_path)


def execute_openpose_qwen_batch(batch_file_path, output_directory, selected_direction_names):
    values, jobs = load_two_reference_batch_definition(batch_file_path, selected_direction_names)
    prompt_path = resolve_workflow_relative_path(values['prompt_file'])
    reference_roots = {key: resolve_workflow_relative_path(value) for key, value in values['references'].items()}
    prompt_source_text = prompt_path.read_text(encoding='utf-8').strip()
    output_root = Path(output_directory).resolve()
    if not output_root.is_relative_to((WORKFLOW_REPOSITORY_ROOT / '.tmp').resolve()):
        raise ValueError('출력은 .tmp 아래여야 합니다.')
    output_root.mkdir(parents=True, exist_ok=True)
    results = []
    for index, job in enumerate(jobs, 1):
        direction, frame = job['direction'], job['frame']
        frame_root = output_root / direction / f'frame-{frame:02d}'
        frame_root.mkdir(parents=True, exist_ok=False)
        character_path = reference_roots['baseline_root'] / f'{direction}.png'
        pose_path = frame_root / 'openpose-reference.png'
        crop_sheet_frame(reference_roots['openpose_root'] / f'{direction}.png', frame, pose_path)
        prompt_text = f'{prompt_source_text} {DIRECTION_POSE_INSTRUCTIONS[direction]}'
        result = execute_pose_generation(trial_output_root=frame_root, prompt_text_value=prompt_text, character_image_path=character_path, pose_reference_path=pose_path, pose_reference_kind='openpose', selected_reference_order='standing-first', selected_inference_steps=4, prompt_source_record={'kind': 'qwen-lightning-openpose-reference-batch', 'direction': direction, 'batch_file': str(batch_file_path.relative_to(WORKFLOW_REPOSITORY_ROOT)), 'sha256': hashlib.sha256(prompt_text.encode()).hexdigest()}, enable_anypose_adapter=False, enable_lightning_adapter=True, enable_standalone_lightning_adapter=True)
        results.append({'direction': direction, 'frame': frame, 'status': result['status'], 'output': str(frame_root.relative_to(output_root))})
        print(f'{datetime.now(ZoneInfo("Asia/Seoul")).isoformat()}/qwen-openpose-batch/complete {index}/{len(jobs)}', flush=True)
    (output_root / 'batch-result.yaml').write_text(yaml.safe_dump({'schema_version': 1, 'reference_kind': 'openpose', 'steps': 4, 'frame_count': len(jobs), 'directions': list(selected_direction_names), 'status': 'completed', 'frames': results}, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return results


def run_two_reference_qwen_batch_command():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch-file', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--directions', nargs='+', choices=DIRECTIONS, default=list(DIRECTIONS))
    arguments = parser.parse_args()
    execute_openpose_qwen_batch(arguments.batch_file.resolve(), arguments.output_dir, tuple(dict.fromkeys(arguments.directions)))


if __name__ == '__main__':
    run_two_reference_qwen_batch_command()
