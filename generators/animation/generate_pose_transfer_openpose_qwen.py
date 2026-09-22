#!/usr/bin/env python3
"""캐릭터 아이덴티와 OpenPose 참조만 사용하는 Qwen 포즈 전환기."""
import argparse
import hashlib
from pathlib import Path
from qwen_pose import execute_pose_generation


def generate_pose_transfer_openpose_qwen_frame(output_directory, prompt_file_path):
    prompt_source_text = Path(prompt_file_path).read_text(encoding='utf-8').strip()
    return execute_pose_generation(
        trial_output_root=output_directory,
        prompt_text_value=prompt_source_text,
        character_image_path=Path(output_directory) / 'standing-reference.png',
        pose_reference_path=Path(output_directory) / 'openpose-reference.png',
        pose_reference_kind='openpose',
        selected_reference_order='standing-first',
        selected_inference_steps=4,
        prompt_source_record={'kind': 'qwen-lightning-openpose-reference', 'sha256': hashlib.sha256(prompt_source_text.encode()).hexdigest()},
        enable_anypose_adapter=False,
        enable_lightning_adapter=True,
        enable_standalone_lightning_adapter=True,
    )


def run_pose_transfer_openpose_qwen_command():
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument('--output-dir', type=Path, required=True)
    argument_parser.add_argument('--prompt-file', type=Path, required=True)
    parsed_arguments = argument_parser.parse_args()
    return generate_pose_transfer_openpose_qwen_frame(parsed_arguments.output_dir.resolve(), parsed_arguments.prompt_file)


if __name__ == '__main__':
    run_pose_transfer_openpose_qwen_command()
