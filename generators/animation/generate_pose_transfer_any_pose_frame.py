#!/usr/bin/env python3
"""고정 AnyPose Base/Helper + Lightning 파이프라인. 모델 선택 인자를 제공하지 않는다."""
import argparse
import hashlib
from pathlib import Path
from qwen_pose import execute_pose_generation


def generate_pose_transfer_any_pose_frame(output_directory, prompt_file_path):
    prompt_source_text = Path(prompt_file_path).read_text(encoding='utf-8').strip()
    return execute_pose_generation(trial_output_root=output_directory, prompt_text_value=prompt_source_text,
        character_image_path=Path(output_directory)/'standing-reference.png', pose_reference_path=Path(output_directory)/'rig-reference.png',
        pose_reference_kind='rig', selected_reference_order='standing-first', selected_inference_steps=4,
        prompt_source_record={'kind':'anypose-model-card', 'sha256':hashlib.sha256(prompt_source_text.encode()).hexdigest()},
        enable_anypose_adapter=True)


def execute_anypose_generation():
    argument_value_parser = argparse.ArgumentParser(description=__doc__)
    argument_value_parser.add_argument('--output-dir', type=Path, required=True)
    argument_value_parser.add_argument('--prompt-file', type=Path, required=True)
    parsed_argument_values = argument_value_parser.parse_args()
    return generate_pose_transfer_any_pose_frame(parsed_argument_values.output_dir.resolve(), parsed_argument_values.prompt_file)


if __name__ == '__main__':
    execute_anypose_generation()
