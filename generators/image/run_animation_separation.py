"""공용 GPU 대기열에서 프레임별 Qwen 분리 후보를 생성한다."""
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import traceback
import zipfile

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
QWEN_ENVIRONMENT_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.venv-qwen21'


def render_separation_outputs(current_job_directory, current_request_record, generation_callback_value):
    from PIL import Image
    from tools.review.common.generation_records import write_record_atomically
    output_frame_size = current_request_record['width']
    current_frame_count = len(current_request_record['frames'])
    output_column_count = min(8, current_frame_count)
    output_row_count = math.ceil(current_frame_count / output_column_count)
    result_sheet_image = Image.new('RGB', (output_column_count * output_frame_size, output_row_count * output_frame_size), 'white')
    source_sheet_image = Image.new('RGB', result_sheet_image.size, 'white')
    head_sheet_image = Image.new('RGB', (output_column_count * output_frame_size // 2, output_row_count * output_frame_size), 'white')
    body_sheet_image = head_sheet_image.copy()
    output_frame_records = []
    for current_frame_index, current_source_frame in enumerate(current_request_record['frames']):
        current_frame_directory = current_job_directory / f'frame-{current_frame_index+1:03d}'
        current_frame_directory.mkdir(exist_ok=True)
        current_completion_path = current_frame_directory / 'complete.json'
        current_reference_path = current_job_directory / current_request_record['references'][current_frame_index]
        write_record_atomically(current_job_directory / 'separation-progress.json', {'completed': current_frame_index, 'total': current_frame_count, 'frameId': current_source_frame['frameId'], 'stage': 'generating'})
        print(f'{datetime.now(ZoneInfo("Asia/Seoul")).isoformat()}/animation-separation/frame {current_frame_index+1}/{current_frame_count} {current_source_frame["frameId"]}', flush=True)
        if current_completion_path.exists():
            current_completion_record = json.loads(current_completion_path.read_text())
            if current_completion_record['signature'] != current_request_record['signature'] or current_completion_record['referenceSha256'] != hashlib.sha256(current_reference_path.read_bytes()).hexdigest() or current_completion_record['sha256'] != hashlib.sha256((current_frame_directory / 'result.png').read_bytes()).hexdigest():
                raise ValueError('완료 프레임의 입력 또는 출력 무결성 오류')
        else:
            generation_callback_value(current_frame_directory, current_request_record, [current_reference_path])
            write_record_atomically(current_completion_path, {'signature': current_request_record['signature'], 'referenceSha256': hashlib.sha256(current_reference_path.read_bytes()).hexdigest(), 'sha256': hashlib.sha256((current_frame_directory / 'result.png').read_bytes()).hexdigest()})
        with Image.open(current_frame_directory / 'result.png') as current_frame_image:
            if current_frame_image.size != (output_frame_size, output_frame_size):
                raise ValueError('분리 결과 프레임 크기 불일치')
            current_sheet_position = ((current_frame_index % output_column_count) * output_frame_size, (current_frame_index // output_column_count) * output_frame_size)
            current_part_position = (current_sheet_position[0] // 2, current_sheet_position[1])
            result_sheet_image.paste(current_frame_image, current_sheet_position)
            head_sheet_image.paste(current_frame_image.crop((0, 0, output_frame_size // 2, output_frame_size)), current_part_position)
            body_sheet_image.paste(current_frame_image.crop((output_frame_size // 2, 0, output_frame_size, output_frame_size)), current_part_position)
        with Image.open(current_reference_path) as current_source_image:
            current_source_image.thumbnail((output_frame_size, output_frame_size))
            source_sheet_image.paste(current_source_image, (current_sheet_position[0]+(output_frame_size-current_source_image.width)//2, current_sheet_position[1]+(output_frame_size-current_source_image.height)//2))
        output_frame_records.append({'source': current_source_frame, 'column': current_frame_index % output_column_count, 'row': current_frame_index // output_column_count})
    for output_file_name, output_image_value in [('result.png', result_sheet_image), ('source-sheet.png', source_sheet_image), ('head-sheet.png', head_sheet_image), ('body-sheet.png', body_sheet_image)]:
        output_image_value.save(current_job_directory / output_file_name)
    output_manifest_record = {'schema_version': 1, 'source_id': current_request_record['source_id'], 'source_digest': current_request_record['source_digest'], 'signature': current_request_record['signature'],
        'size': output_frame_size, 'columns': output_column_count, 'rows': output_row_count, 'fps': current_request_record['fps'], 'frames': output_frame_records,
        'quality_warnings': ['AI 생성 후보: 원본 픽셀·앵커 보존을 보장하지 않음', '좌우 절반을 파츠 후보로 추출함: 경계 침범·목 연결 검수 필요', '흰 배경 RGB: 투명화·실제 조합 정렬은 별도 검수']}
    write_record_atomically(current_job_directory / 'manifest.json', output_manifest_record)
    write_record_atomically(current_job_directory / 'result.json', output_manifest_record)
    with zipfile.ZipFile(current_job_directory / 'separation.zip', 'w', zipfile.ZIP_DEFLATED) as archive_output_handle:
        for current_file_name in ('manifest.json', 'request.json', 'result.png', 'source-sheet.png', 'head-sheet.png', 'body-sheet.png'):
            archive_output_handle.write(current_job_directory / current_file_name, current_file_name)
        for current_reference_name in current_request_record['references']:
            archive_output_handle.write(current_job_directory / current_reference_name, current_reference_name)
    write_record_atomically(current_job_directory / 'separation-progress.json', {'completed': current_frame_count, 'total': current_frame_count, 'stage': 'completed'})


def execute_separation_worker():
    if Path(sys.prefix) != QWEN_ENVIRONMENT_DIRECTORY:
        python_executable_path = QWEN_ENVIRONMENT_DIRECTORY / 'bin/python'
        os.execv(str(python_executable_path), [str(python_executable_path), str(Path(__file__).resolve()), *sys.argv[1:]])
    sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
    from generators.image.worker_lock import acquire_worker_lock
    from generators.image.qwen_21_runtime import execute_qwen_reference_generation
    from tools.review.common.generation_records import write_record_atomically
    from tools.review.domains.image.animation_separation import SEPARATION_STORAGE_ROOT, verify_separation_request
    argument_parser_value = argparse.ArgumentParser(description=__doc__)
    argument_parser_value.add_argument('--job-dir', type=Path, required=True)
    current_job_directory = argument_parser_value.parse_args().job_dir.resolve()
    if current_job_directory.parent != SEPARATION_STORAGE_ROOT.resolve():
        raise ValueError('분리 작업 저장 경로 오류')
    try:
        current_request_record = verify_separation_request(current_job_directory)
        current_lock_path = WORKFLOW_ROOT_DIRECTORY / '.local/image-generation-gpu.lock'
        current_lock_path.parent.mkdir(exist_ok=True)
        with current_lock_path.open('a') as current_lock_handle:
            acquire_worker_lock(current_lock_handle, 'waiting-gpu')
            render_separation_outputs(current_job_directory, current_request_record, execute_qwen_reference_generation)
        write_record_atomically(current_job_directory / 'status.json', {'status': 'completed'})
    except Exception as current_error_value:
        traceback.print_exc()
        write_record_atomically(current_job_directory / 'status.json', {'status': 'failed', 'error': str(current_error_value)})
        raise


if __name__ == '__main__':
    execute_separation_worker()
