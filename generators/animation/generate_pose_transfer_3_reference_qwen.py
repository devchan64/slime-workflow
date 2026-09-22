#!/usr/bin/env python3
"""AnyPose 없이 캐릭터·리그·OpenPose 세 참조를 사용하는 Qwen Lightning 실험기."""
import argparse
import hashlib
from pathlib import Path
from qwen_pose import execute_pose_generation


def generate_pose_transfer_three_reference_qwen_frame(output_directory, prompt_file_path, character_image_path, rig_image_path, openpose_image_path):
    prompt_source_text = Path(prompt_file_path).read_text(encoding='utf-8').strip()
    return execute_pose_generation(
        trial_output_root=output_directory,
        prompt_text_value=prompt_source_text,
        character_image_path=character_image_path,
        pose_reference_path=rig_image_path,
        additional_reference_paths=(openpose_image_path,),
        pose_reference_kind='rig',
        selected_reference_order='standing-first',
        selected_inference_steps=4,
        prompt_source_record={'kind': 'qwen-lightning-multi-reference-experiment', 'sha256': hashlib.sha256(prompt_source_text.encode()).hexdigest()},
        enable_anypose_adapter=False,
        enable_lightning_adapter=True,
        enable_standalone_lightning_adapter=True,
    )


def execute_pose_transfer_three_reference_qwen_generation():
    argument_value_parser = argparse.ArgumentParser(description=__doc__)
    argument_value_parser.add_argument('--output-dir', type=Path, required=True)
    argument_value_parser.add_argument('--prompt-file', type=Path, required=True)
    argument_value_parser.add_argument('--character-image', type=Path, required=True)
    argument_value_parser.add_argument('--rig-image', type=Path, required=True)
    argument_value_parser.add_argument('--openpose-image', type=Path, required=True)
    parsed_argument_values = argument_value_parser.parse_args()
    return generate_pose_transfer_three_reference_qwen_frame(parsed_argument_values.output_dir, parsed_argument_values.prompt_file, parsed_argument_values.character_image, parsed_argument_values.rig_image, parsed_argument_values.openpose_image)


if __name__ == '__main__':
    execute_pose_transfer_three_reference_qwen_generation()
