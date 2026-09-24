#!/usr/bin/env python3
"""캐릭터 아이덴티와 OpenPose 참조만 사용하는 Qwen 포즈 전환기."""
import argparse
import hashlib
from pathlib import Path
from qwen_pose import execute_pose_generation

# Qwen 방향 토큰 규칙: forward/backward가 up/down보다 진행 방향 해석에 안정적이다.
# down_left/down_right/up_left/up_right 키는 기존 에셋·배치 계약 때문에 유지하지만,
# 보조 프롬프트에는 up/down·upper/lower를 쓰지 않아 머리의 수직 움직임으로 오인되지 않게 한다.
# 매핑: down_left=forward-left(좌측앞), down_right=forward-right(우측앞),
# up_left=backward-left(좌측뒤편), up_right=backward-right(우측뒤편).
DIRECTION_POSE_INSTRUCTIONS = {
    'down_left': 'Direction: forward-left. The character walks forward toward the left side, showing the left-front side, with the head and gaze aligned to the forward-left direction.',
    'down_right': 'Direction: forward-right. The character walks forward toward the right side, showing the right-front side, with the head and gaze aligned to the forward-right direction.',
    'up_left': 'Direction: backward-left. The character walks backward toward the left side, showing the left-rear back view, with the head level and aligned to the torso.',
    'up_right': 'Direction: backward-right. The character walks backward toward the right side, showing the right-rear back view, with the head level and aligned to the torso.',
}

def generate_pose_transfer_openpose_qwen_frame(output_directory, prompt_file_path, direction_name):
    if direction_name not in DIRECTION_POSE_INSTRUCTIONS:
        raise ValueError(f'지원하지 않는 방향입니다: {direction_name}')
    prompt_source_text = Path(prompt_file_path).read_text(encoding='utf-8').strip()
    prompt_text = f'{prompt_source_text} {DIRECTION_POSE_INSTRUCTIONS[direction_name]}'
    return execute_pose_generation(
        trial_output_root=output_directory,
        prompt_text_value=prompt_text,
        character_image_path=Path(output_directory) / 'standing-reference.png',
        pose_reference_path=Path(output_directory) / 'openpose-reference.png',
        pose_reference_kind='openpose',
        selected_reference_order='standing-first',
        selected_inference_steps=4,
        prompt_source_record={'kind': 'qwen-lightning-openpose-reference', 'direction': direction_name, 'sha256': hashlib.sha256(prompt_text.encode()).hexdigest()},
        enable_anypose_adapter=False,
        enable_lightning_adapter=True,
        enable_standalone_lightning_adapter=True,
    )


def run_pose_transfer_openpose_qwen_command():
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument('--output-dir', type=Path, required=True)
    argument_parser.add_argument('--prompt-file', type=Path, required=True)
    argument_parser.add_argument('--direction', choices=tuple(DIRECTION_POSE_INSTRUCTIONS), required=True)
    parsed_arguments = argument_parser.parse_args()
    return generate_pose_transfer_openpose_qwen_frame(parsed_arguments.output_dir.resolve(), parsed_arguments.prompt_file, parsed_arguments.direction)


if __name__ == '__main__':
    run_pose_transfer_openpose_qwen_command()
