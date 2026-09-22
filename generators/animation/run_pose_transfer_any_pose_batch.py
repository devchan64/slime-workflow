#!/usr/bin/env python3
"""YAML 목록으로 AnyPose 4방향 8프레임을 순차 생성하는 배치 실행기."""
from pathlib import Path
import argparse

from run_pose_transfer_3_reference_qwen_batch import execute_pose_transfer_batch_generation


def execute_pose_transfer_any_pose_batch(batch_definition_path, run_output_root=None):
    return execute_pose_transfer_batch_generation(batch_definition_path, run_output_root, 'anypose-lightning')


def run_pose_transfer_any_pose_batch_command():
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument('--batch-file', type=Path, required=True)
    argument_parser.add_argument('--output-dir', type=Path)
    parsed_arguments = argument_parser.parse_args()
    execute_pose_transfer_any_pose_batch(parsed_arguments.batch_file.resolve(), parsed_arguments.output_dir)


if __name__ == '__main__':
    run_pose_transfer_any_pose_batch_command()
