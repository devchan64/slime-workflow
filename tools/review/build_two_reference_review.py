"""리그 생성 리포트와 OpenPose 맵 생성 리포트를 한 시트로 비교한다."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.review.ui_assets import resolve_review_ui_asset

import argparse
import json
import shutil

from build_pose_transfer_review import FRAME_NUMBERS, SUPPORTED_DIRECTIONS, sha256_file

WORKFLOW_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def build_two_reference_review(rig_report_path: Path, openpose_report_path: Path, output_path: Path) -> Path:
    rig_report_path = rig_report_path.resolve()
    openpose_report_path = openpose_report_path.resolve()
    output_path = output_path.resolve()
    for report_path in (rig_report_path, openpose_report_path):
        if not report_path.is_relative_to(WORKFLOW_REPOSITORY_ROOT / 'report') or not report_path.is_dir():
            raise ValueError(f'리포트 경로가 올바르지 않습니다: {report_path}')
    if not output_path.is_relative_to(WORKFLOW_REPOSITORY_ROOT / '.tmp'):
        raise ValueError('검수 시트 출력은 워크플로우 .tmp 아래여야 합니다.')
    if output_path.exists():
        raise ValueError(f'검수 출력 폴더가 이미 있습니다: {output_path}')
    output_path.mkdir(parents=True)
    direction_records = []
    for direction_name in SUPPORTED_DIRECTIONS:
        frame_records = []
        for frame_number in FRAME_NUMBERS:
            rig_frame_path = rig_report_path / direction_name / f'frame-{frame_number:02d}'
            openpose_frame_path = openpose_report_path / direction_name / f'frame-{frame_number:02d}'
            rig_metadata = json.loads((rig_frame_path / 'result.json').read_text(encoding='utf-8'))
            openpose_metadata = json.loads((openpose_frame_path / 'result.json').read_text(encoding='utf-8'))
            files = {}
            for role_name, source_path in {
                'result': rig_frame_path / 'result.png',
                'rig': rig_frame_path / 'rig-reference.png',
                'openpose': openpose_frame_path / 'result.png',
            }.items():
                if not source_path.is_file():
                    raise ValueError(f'비교 이미지가 없습니다: {source_path}')
                relative_path = Path(direction_name) / f'frame-{frame_number:02d}' / f'{role_name}.png'
                destination_path = output_path / relative_path
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination_path)
                files[role_name] = {'path': relative_path.as_posix(), 'sha256': sha256_file(source_path)}
            frame_records.append({'frame': frame_number, 'files': files, 'size': rig_metadata['size'], 'modelRevision': rig_metadata.get('revision', ''), 'openposeRevision': openpose_metadata.get('revision', '')})
        direction_records.append({'direction': direction_name, 'frames': frame_records})
    template = (resolve_review_ui_asset('pose-transfer-review.html')).read_text(encoding='utf-8')
    template = template.replace('3참조 포즈 전이 비교', '리그 생성·OpenPose 맵 생성 비교').replace('결과·리그·OpenPose 기준 비교', '리그 생성 결과·리그 참조·OpenPose 맵 생성 결과 비교').replace('Qwen 결과 캐릭터', '리그용 생성 결과').replace('OpenPose 참조', 'OpenPose 맵용 생성 결과')
    page_data = {'report': f'{rig_report_path.name} + {openpose_report_path.name}', 'directions': direction_records}
    (output_path / 'preview.html').write_text(template.replace('__POSE_TRANSFER_DATA__', json.dumps(page_data, ensure_ascii=False).replace('<', '\\u003c')), encoding='utf-8')
    return output_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rig-root', type=Path, required=True)
    parser.add_argument('--openpose-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(build_two_reference_review(args.rig_root, args.openpose_root, args.output))
