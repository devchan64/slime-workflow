#!/usr/bin/env python3
"""채택된 캐릭터·v5 리그 2참조 AnyPose 배치 생성기 진입점."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
from run_pose_transfer_anypose_baseline_rig_batch import execute_anypose_openpose_batch

WORKFLOW_ROOT_PATH = Path(__file__).resolve().parents[2]
DEFAULT_BATCH_CONFIG = WORKFLOW_ROOT_PATH / 'generators/animation/config/pose_transfer_anypose_baseline_rig_default_walk.yaml'


def execute_pose_transfer_any_pose_batch(batch_definition_path=DEFAULT_BATCH_CONFIG, run_output_root=None, resume=False):
    current_output_root = Path(run_output_root) if run_output_root is not None else WORKFLOW_ROOT_PATH / '.tmp' / datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
    return execute_anypose_openpose_batch(Path(batch_definition_path).resolve(), current_output_root, resume)


def run_pose_transfer_any_pose_batch_command():
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument('--batch-file', type=Path, default=DEFAULT_BATCH_CONFIG)
    argument_parser.add_argument('--output-dir', type=Path)
    argument_parser.add_argument('--resume', action='store_true')
    parsed_arguments = argument_parser.parse_args()
    execute_pose_transfer_any_pose_batch(parsed_arguments.batch_file, parsed_arguments.output_dir, parsed_arguments.resume)


if __name__ == '__main__':
    run_pose_transfer_any_pose_batch_command()
