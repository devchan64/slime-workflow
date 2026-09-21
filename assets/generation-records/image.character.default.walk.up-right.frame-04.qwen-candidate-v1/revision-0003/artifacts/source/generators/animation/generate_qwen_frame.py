#!/usr/bin/env python3
"""Qwen 포즈 편집 라이브러리의 CLI. GPU 작업은 샌드박스 밖에서 실행한다."""
import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
from qwen_pose import execute_pose_generation, load_pose_prompt

WORKFLOW_REPO_ROOT = Path(__file__).resolve().parents[2]


def execute_pose_experiment():
    argument_value_parser = argparse.ArgumentParser(description=__doc__)
    argument_value_parser.add_argument('--output-dir', type=Path, default=WORKFLOW_REPO_ROOT/'.tmp'/datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S'))
    prompt_argument_group = argument_value_parser.add_mutually_exclusive_group(required=True)
    prompt_argument_group.add_argument('--prompt-profile', type=Path)
    prompt_argument_group.add_argument('--prompt-file', type=Path, help='실험용 완성 프롬프트: 참조 번호는 작성자가 확인')
    argument_value_parser.add_argument('--omit-optional-prompt', action='store_true', help='기준 포즈 프롬프트만 사용')
    # 기본 제작은 리그 참조다. OpenPose는 명시적 비교 실험에서만 선택한다.
    argument_value_parser.add_argument('--pose-kind', choices=('rig', 'openpose'), default='rig')
    argument_value_parser.add_argument('--character-image', type=Path)
    argument_value_parser.add_argument('--pose-image', type=Path)
    argument_value_parser.add_argument('--steps', type=int, choices=(4, 10, 20), default=10)
    argument_value_parser.add_argument('--reference-order', choices=('standing-first', 'pose-first'), default='standing-first')
    parsed_argument_values = argument_value_parser.parse_args()
    trial_output_root = parsed_argument_values.output_dir.resolve()
    if parsed_argument_values.prompt_profile:
        prompt_text_value, prompt_source_record = load_pose_prompt(parsed_argument_values.prompt_profile, parsed_argument_values.pose_kind, parsed_argument_values.reference_order, include_optional_prompt=not parsed_argument_values.omit_optional_prompt)
    else:
        if parsed_argument_values.omit_optional_prompt:
            argument_value_parser.error('--omit-optional-prompt는 --prompt-profile과 함께 사용하세요.')
        prompt_text_value = parsed_argument_values.prompt_file.read_text().strip()
        prompt_source_record = {'kind': 'experiment-override', 'sha256': hashlib.sha256(prompt_text_value.encode()).hexdigest()}
    return execute_pose_generation(trial_output_root=trial_output_root, prompt_text_value=prompt_text_value,
        character_image_path=parsed_argument_values.character_image or trial_output_root/'standing-reference.png',
        pose_reference_path=parsed_argument_values.pose_image or trial_output_root/f'{parsed_argument_values.pose_kind}-reference.png',
        pose_reference_kind=parsed_argument_values.pose_kind, selected_reference_order=parsed_argument_values.reference_order,
        selected_inference_steps=parsed_argument_values.steps, prompt_source_record=prompt_source_record)


if __name__ == '__main__':
    execute_pose_experiment()
