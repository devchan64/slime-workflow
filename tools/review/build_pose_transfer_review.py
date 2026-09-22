"""3참조 Qwen 걷기 리포트의 결과·리그·OpenPose 비교 시트를 만든다."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

WORKFLOW_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_DIRECTIONS = ('down_left', 'down_right', 'up_left', 'up_right')
FRAME_NUMBERS = tuple(range(1, 9))


def sha256_file(file_path: Path) -> str:
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def build_pose_transfer_review(report_root_path: Path, output_directory_path: Path | None = None) -> Path:
    report_root_path = report_root_path.resolve()
    if not report_root_path.is_relative_to(WORKFLOW_REPOSITORY_ROOT / 'report'):
        raise ValueError('3참조 리포트는 워크플로우 report 아래에 있어야 합니다.')
    if not report_root_path.is_dir():
        raise ValueError(f'리포트 폴더가 없습니다: {report_root_path}')
    output_directory_path = (output_directory_path or WORKFLOW_REPOSITORY_ROOT / '.tmp' / report_root_path.name).resolve()
    if not output_directory_path.is_relative_to(WORKFLOW_REPOSITORY_ROOT / '.tmp'):
        raise ValueError('검수 시트 출력은 워크플로우 .tmp 아래여야 합니다.')
    if output_directory_path.exists():
        raise ValueError(f'검수 출력 폴더가 이미 있습니다: {output_directory_path}')
    output_directory_path.mkdir(parents=True)
    direction_records = []
    for direction_name in SUPPORTED_DIRECTIONS:
        frame_records = []
        for frame_number in FRAME_NUMBERS:
            frame_directory_path = report_root_path / direction_name / f'frame-{frame_number:02d}'
            result_record_path = frame_directory_path / 'result.json'
            if not result_record_path.is_file():
                raise ValueError(f'결과 메타데이터가 없습니다: {result_record_path}')
            result_record = json.loads(result_record_path.read_text(encoding='utf-8'))
            required_result_fields = {'status', 'size', 'input_order', 'input_sha256', 'output'}
            if set(result_record) < required_result_fields or result_record['status'] != 'completed' or result_record['output'] != 'result.png':
                raise ValueError(f'결과 메타데이터 계약이 올바르지 않습니다: {result_record_path}')
            expected_input_order = ['character-reference.png', 'rig-reference.png', 'openpose-reference.png']
            if result_record['input_order'] != expected_input_order:
                raise ValueError(f'입력 참조 순서가 올바르지 않습니다: {result_record_path}')
            if not isinstance(result_record['size'], list) or len(result_record['size']) != 2 or not all(isinstance(size_value, int) and size_value > 0 for size_value in result_record['size']):
                raise ValueError(f'결과 크기 메타데이터가 올바르지 않습니다: {result_record_path}')
            copied_file_records = {}
            for role_name, source_file_name in (('result', 'result.png'), ('rig', 'rig-reference.png'), ('openpose', 'openpose-reference.png')):
                source_file_path = frame_directory_path / source_file_name
                if not source_file_path.is_file() or source_file_path.is_symlink():
                    raise ValueError(f'비교 이미지가 없습니다: {source_file_path}')
                source_hash_value = sha256_file(source_file_path)
                if role_name != 'result' and result_record['input_sha256'].get(source_file_name) != source_hash_value:
                    raise ValueError(f'입력 참조 해시가 일치하지 않습니다: {source_file_path}')
                destination_relative_path = Path(direction_name) / f'frame-{frame_number:02d}' / source_file_name
                destination_file_path = output_directory_path / destination_relative_path
                destination_file_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file_path, destination_file_path)
                copied_file_records[role_name] = {'path': destination_relative_path.as_posix(), 'sha256': source_hash_value}
            frame_records.append({'frame': frame_number, 'files': copied_file_records, 'size': result_record['size'], 'modelRevision': result_record.get('revision', '')})
        direction_records.append({'direction': direction_name, 'frames': frame_records})
    template_text = (Path(__file__).with_name('pose-transfer-review.html')).read_text(encoding='utf-8')
    page_data = {'report': report_root_path.name, 'directions': direction_records}
    (output_directory_path / 'preview.html').write_text(template_text.replace('__POSE_TRANSFER_DATA__', json.dumps(page_data, ensure_ascii=False).replace('<', '\\u003c')), encoding='utf-8')
    return output_directory_path


if __name__ == '__main__':
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument('--root', type=Path, required=True)
    argument_parser.add_argument('--output', type=Path)
    arguments = argument_parser.parse_args()
    print(build_pose_transfer_review(arguments.root, arguments.output))
