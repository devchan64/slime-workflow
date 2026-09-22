#!/usr/bin/env python3
"""YAML 목록의 방향·프레임 쌍으로 AnyPose 2참조 32프레임을 생성한다."""
import argparse
import hashlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from PIL import Image

from qwen_pose import execute_pose_generation
from qwen_pose.prompts import UniqueKeySafeLoader

WORKFLOW_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DIRECTIONS = ('down_left', 'down_right', 'up_left', 'up_right')


def resolve_workflow_relative_path(relative_path_value):
    path_value = Path(relative_path_value)
    if path_value.is_absolute():
        raise ValueError('참조 경로는 상대 경로여야 합니다.')
    resolved_path = (WORKFLOW_REPOSITORY_ROOT / path_value).resolve()
    if not resolved_path.is_relative_to(WORKFLOW_REPOSITORY_ROOT.resolve()):
        raise ValueError('참조 경로가 저장소 밖입니다.')
    return resolved_path


def load_anypose_openpose_batch_definition(batch_file_path):
    values = yaml.load(batch_file_path.read_bytes(), Loader=UniqueKeySafeLoader)
    if set(values) != {'schema_version', 'prompt_file', 'references', 'jobs'} or values['schema_version'] != 1:
        raise ValueError('배치 YAML 형식이 올바르지 않습니다.')
    if set(values['references']) != {'baseline_root', 'rig_root'}:
        raise ValueError('베이스라인과 리그 참조 경로가 필요합니다.')
    expanded_jobs = []
    for job in values['jobs']:
        if set(job) != {'direction', 'frame_numbers'} or job['direction'] not in DIRECTIONS or job['frame_numbers'] != list(range(1, 9)):
            raise ValueError('각 방향은 1~8프레임을 가져야 합니다.')
        expanded_jobs.extend({'direction': job['direction'], 'frame': frame} for frame in job['frame_numbers'])
    if len(expanded_jobs) != 32:
        raise ValueError('배치는 32프레임이어야 합니다.')
    return values, expanded_jobs


def crop_sheet_frame(source_sheet_path, frame_number, destination_path):
    with Image.open(source_sheet_path) as source_image:
        if source_image.size != (2048, 1024):
            raise ValueError(f'시트 크기 불일치: {source_sheet_path}')
        column = (frame_number - 1) % 4
        row = (frame_number - 1) // 4
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        source_image.crop((column * 512, row * 512, (column + 1) * 512, (row + 1) * 512)).convert('RGB').save(destination_path)


def execute_anypose_openpose_batch(batch_file_path, output_directory):
    values, jobs = load_anypose_openpose_batch_definition(batch_file_path)
    prompt_path = resolve_workflow_relative_path(values['prompt_file'])
    reference_roots = {key: resolve_workflow_relative_path(value) for key, value in values['references'].items()}
    prompt_text = prompt_path.read_text(encoding='utf-8').strip()
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
        rig_path = frame_root / 'rig-reference.png'
        crop_sheet_frame(reference_roots['rig_root'] / f'{direction}.png', frame, rig_path)
        result = execute_pose_generation(trial_output_root=frame_root, prompt_text_value=prompt_text, character_image_path=character_path, pose_reference_path=rig_path, pose_reference_kind='rig', selected_reference_order='standing-first', selected_inference_steps=4, prompt_source_record={'kind': 'anypose-baseline-rig-batch', 'direction': direction, 'frame': frame, 'batch_file': str(batch_file_path.relative_to(WORKFLOW_REPOSITORY_ROOT)), 'sha256': hashlib.sha256(prompt_text.encode()).hexdigest()}, enable_anypose_adapter=True, enable_lightning_adapter=True)
        results.append({'direction': direction, 'frame': frame, 'status': result['status'], 'output': str(frame_root.relative_to(output_root))})
        print(f'{datetime.now(ZoneInfo("Asia/Seoul")).isoformat()}/anypose-openpose-batch/complete {index}/32', flush=True)
    (output_root / 'batch-result.yaml').write_text(yaml.safe_dump({'schema_version': 1, 'reference_kind': 'baseline-plus-rig', 'steps': 4, 'frame_count': 32, 'status': 'completed', 'frames': results}, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return results


def run_anypose_openpose_batch_command():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch-file', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    arguments = parser.parse_args()
    execute_anypose_openpose_batch(arguments.batch_file.resolve(), arguments.output_dir)


if __name__ == '__main__':
    run_anypose_openpose_batch_command()
