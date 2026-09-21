#!/usr/bin/env python3
"""고정 AnyPose Base/Helper 비Lightning 파이프라인. 모델 선택 인자를 제공하지 않는다."""
import argparse
import hashlib
from pathlib import Path
from qwen_pose import execute_pose_generation


def execute_anypose_generation():
    argument_value_parser = argparse.ArgumentParser(description=__doc__)
    argument_value_parser.add_argument('--output-dir', type=Path, required=True)
    argument_value_parser.add_argument('--prompt-file', type=Path, required=True)
    argument_value_parser.add_argument('--base-strength', type=float, default=0.7)
    argument_value_parser.add_argument('--helper-strength', type=float, default=0.7)
    argument_value_parser.add_argument('--steps', type=int, choices=(10, 20, 30), default=10)
    parsed_argument_values = argument_value_parser.parse_args()
    trial_output_root = parsed_argument_values.output_dir.resolve()
    prompt_source_text = parsed_argument_values.prompt_file.read_text().strip()
    return execute_pose_generation(trial_output_root=trial_output_root, prompt_text_value=prompt_source_text,
        character_image_path=trial_output_root/'standing-reference.png', pose_reference_path=trial_output_root/'rig-reference.png',
        pose_reference_kind='rig', selected_reference_order='standing-first', selected_inference_steps=parsed_argument_values.steps,
        prompt_source_record={'kind':'anypose-model-card', 'sha256':hashlib.sha256(prompt_source_text.encode()).hexdigest()},
        enable_anypose_adapter=True, enable_lightning_adapter=False,
        selected_base_strength=parsed_argument_values.base_strength, selected_helper_strength=parsed_argument_values.helper_strength)


if __name__ == '__main__':
    execute_anypose_generation()
