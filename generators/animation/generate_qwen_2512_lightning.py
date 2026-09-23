#!/usr/bin/env python3
"""Qwen-Image-2512 Lightning 표준 텍스트→이미지 생성기."""
import argparse
from pathlib import Path
from qwen_pose_2512 import generate_qwen_2512_lightning_image


def run_qwen_2512_lightning_command():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--prompt-file', type=Path, required=True)
    parser.add_argument('--width', type=int, default=1024)
    parser.add_argument('--height', type=int, default=1024)
    arguments = parser.parse_args()
    return generate_qwen_2512_lightning_image(
        output_directory=arguments.output_dir.resolve(),
        prompt_text=arguments.prompt_file.read_text(encoding='utf-8'),
        width=arguments.width,
        height=arguments.height,
    )


if __name__ == '__main__':
    run_qwen_2512_lightning_command()
