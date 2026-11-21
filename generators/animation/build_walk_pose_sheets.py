"""등록된 8프레임 포즈를 이미지젠용 방향별 시트로 묶는다."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import json
import hashlib
import traceback
import yaml
from PIL import Image


WORKFLOW_REPO_ROOT = Path(__file__).resolve().parents[2]
SHEET_ASSET_DIRECTORY = WORKFLOW_REPO_ROOT / 'assets/rigs/mannequin-walk/pose-sheets-v1'
SHEET_MANIFEST_PATH = WORKFLOW_REPO_ROOT / 'generators/animation/config/default_walk_pose_sheets.yaml'
SHEET_COLUMN_COUNT = 4
SHEET_ROW_COUNT = 2
POSE_CELL_SIZE = 512
DIRECTION_NAME_VALUES = ('down_left', 'down_right', 'up_left', 'up_right')


def build_walk_pose_sheets(source_asset_directory):
    execution_output_directory = WORKFLOW_REPO_ROOT / '.tmp' / datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
    execution_output_directory.mkdir(parents=True, exist_ok=False)
    execution_log_path = execution_output_directory / 'execution.log'

    def record_sheet_progress(stage_name_value, message_text_value):
        trace_line_value = f'{datetime.now().isoformat()}/pose-sheets/{stage_name_value} {message_text_value}\n'
        with execution_log_path.open('a') as execution_log_handle:
            execution_log_handle.write(trace_line_value)
        print(trace_line_value, end='', flush=True)

    try:
        source_manifest_path = source_asset_directory / 'manifest.json'
        source_manifest_record = json.loads(source_manifest_path.read_text())
        if source_manifest_record['rig'] != 'mannequin-walk/v1' or source_manifest_record['sample_indices'] != list(range(0,24,3)) or source_manifest_record['frames_per_direction'] != 8:
            raise ValueError('mannequin-walk 8프레임 렌더 입력 계약 불일치')
        if SHEET_ASSET_DIRECTORY.exists() or SHEET_MANIFEST_PATH.exists():
            raise FileExistsError('등록 시트 또는 manifest가 이미 있습니다. 기존 불변 버전을 덮어쓰지 않습니다.')
        record_sheet_progress('prepare', str(source_asset_directory))
        generated_file_hashes = {}
        source_frame_hashes = {}
        for direction_name_value in DIRECTION_NAME_VALUES:
            generated_sheet_image = Image.new('RGB', (SHEET_COLUMN_COUNT * POSE_CELL_SIZE, SHEET_ROW_COUNT * POSE_CELL_SIZE), 'black')
            for frame_index_value in range(SHEET_COLUMN_COUNT * SHEET_ROW_COUNT):
                source_frame_path = source_asset_directory / direction_name_value / f'openpose-{frame_index_value + 1:04d}.png'
                with Image.open(source_frame_path) as source_pose_image:
                    if source_pose_image.size != (POSE_CELL_SIZE, POSE_CELL_SIZE) or source_pose_image.mode != 'RGB':
                        raise ValueError(f'포즈 입력 크기·모드 불일치: {source_frame_path}')
                    generated_sheet_image.paste(source_pose_image, ((frame_index_value % SHEET_COLUMN_COUNT) * POSE_CELL_SIZE, (frame_index_value // SHEET_COLUMN_COUNT) * POSE_CELL_SIZE))
                source_frame_hashes[str(source_frame_path.relative_to(source_asset_directory))] = hashlib.sha256(source_frame_path.read_bytes()).hexdigest()
            sheet_file_name = f'{direction_name_value}.png'
            generated_sheet_image.save(execution_output_directory / sheet_file_name)
            generated_file_hashes[sheet_file_name] = hashlib.sha256((execution_output_directory / sheet_file_name).read_bytes()).hexdigest()
            record_sheet_progress('sheet', sheet_file_name)
        manifest_record_value = {
            'asset_id': 'five-head-walk-8f-pose-sheets', 'version': 1,
            'asset_path': str(SHEET_ASSET_DIRECTORY.relative_to(WORKFLOW_REPO_ROOT)),
            'source_run_path': str(source_asset_directory),
            'source_manifest_sha256': hashlib.sha256(source_manifest_path.read_bytes()).hexdigest(),
            'layout': {'columns': SHEET_COLUMN_COUNT, 'rows': SHEET_ROW_COUNT, 'cell_size': [POSE_CELL_SIZE, POSE_CELL_SIZE], 'sheet_size': [2048, 1024], 'frame_order': list(range(1, 9)), 'order': 'row-major'},
            'frame_duration_ms': 150, 'cycle_seconds': 1.2,
            'transformation': '원본 RGB 픽셀 그대로 타일 배치; 리사이즈·색상·관절 보정 없음',
            'generator': 'generators/animation/build_walk_pose_sheets.py',
            'source_files': source_frame_hashes, 'files': generated_file_hashes,
        }
        SHEET_ASSET_DIRECTORY.mkdir(parents=True)
        for sheet_file_name in generated_file_hashes:
            (SHEET_ASSET_DIRECTORY / sheet_file_name).write_bytes((execution_output_directory / sheet_file_name).read_bytes())
        SHEET_MANIFEST_PATH.write_text(yaml.safe_dump(manifest_record_value, allow_unicode=True, sort_keys=False))
        record_sheet_progress('complete', str(SHEET_ASSET_DIRECTORY))
    except Exception:
        record_sheet_progress('failure', traceback.format_exc())
        raise


if __name__ == '__main__':
    source_argument_parser = argparse.ArgumentParser(description='렌더 실행 폴더의 8프레임 포즈를 시트로 등록')
    source_argument_parser.add_argument('--source-dir', required=True, type=Path)
    source_argument_values = source_argument_parser.parse_args()
    build_walk_pose_sheets(source_argument_values.source_dir.resolve())
