#!/usr/bin/env python3
"""Qwen 타일 세트 후보 생성 명령행 진입점이다."""
from __future__ import annotations

import argparse
from pathlib import Path

from qwen_tile import execute_tile_set_generation


def parse_command_arguments():
    """고정 모델 타일 생성 인자를 읽는다."""
    argument_parser = argparse.ArgumentParser(description='Qwen-Image-Edit-2511 타일 세트 후보 생성기')
    argument_parser.add_argument('--ticket', required=True, type=Path, help='엄격한 YAML 타일 세트 티켓')
    argument_parser.add_argument('--style-reference', required=True, type=Path, help='승인된 불투명 PNG 스타일 참조')
    argument_parser.add_argument('--shape-reference', type=Path, help='선택: 투명 벽 형태·알파 마스크 참조')
    argument_parser.add_argument('--material-reference', type=Path, help='선택: 벽의 불투명 돌·흙 재질 참조')
    argument_parser.add_argument('--map-preview', type=Path, help='선택: 지정 타일 적용 검수용 맵 스냅샷 YAML')
    argument_parser.add_argument('--output-dir', required=True, type=Path, help='비어 있는 .tmp 실행 폴더')
    return argument_parser.parse_args()


def main_generation_command():
    """사용자 채택 전 Qwen 후보만 생성한다."""
    command_arguments = parse_command_arguments()
    result_values = execute_tile_set_generation(ticket_file_path=command_arguments.ticket, style_reference_path=command_arguments.style_reference, shape_reference_path=command_arguments.shape_reference, material_reference_path=command_arguments.material_reference, map_preview_path=command_arguments.map_preview, trial_output_root=command_arguments.output_dir)
    print(f"candidate generated: {result_values['asset_id']} -> {command_arguments.output_dir}")


if __name__ == '__main__':
    main_generation_command()
