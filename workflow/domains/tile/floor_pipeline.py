"""9칸 생성과 참조 이미지 분리를 하나의 GPU 작업에서 순차 실행한다."""
import base64
import hashlib
import json
import logging
from pathlib import Path
import shutil
import subprocess
import sys
import time
import threading
from PIL import Image
from workflow.common.worker_generation_progress import WorkerGenerationProgress
from workflow.domains.image.three_reference_generation import save_three_reference_inputs

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[3]


def calculate_file_digest(current_file_path):
    return hashlib.sha256(current_file_path.read_bytes()).hexdigest()


def write_pipeline_record(current_file_path, current_record_value):
    temporary_record_path = current_file_path.with_suffix('.pending')
    temporary_record_path.write_text(json.dumps(current_record_value,ensure_ascii=False,indent=2))
    temporary_record_path.replace(current_file_path)


def execute_floor_stage(current_job_root, stage_directory_name, worker_file_name, stage_request_record):
    stage_output_directory = current_job_root/stage_directory_name
    stage_output_directory.mkdir(exist_ok=True)
    stage_request_path = stage_output_directory/'request.json'
    if stage_request_path.exists() and json.loads(stage_request_path.read_text()) != stage_request_record:
        raise ValueError('재개 단계 요청이 기존 기록과 다릅니다: '+stage_directory_name)
    write_pipeline_record(stage_request_path,stage_request_record)
    current_progress_writer = WorkerGenerationProgress(current_job_root)
    current_stage_progress = {'stage':stage_directory_name+' · 준비','step':0,'total':stage_request_record['steps']}
    def publish_child_progress():
        current_progress_path = stage_output_directory/'worker-progress.json'
        if current_progress_path.is_file():
            current_child_record = json.loads(current_progress_path.read_text())
            current_stage_progress.update(stage=stage_directory_name+' · '+current_child_record['stage'],step=current_child_record['step'],total=current_child_record['step_total'])
        current_progress_writer.record_worker_progress(current_stage_progress)
    stage_checkpoint_path = stage_output_directory/'checkpoint.json'
    if stage_checkpoint_path.exists():
        stage_checkpoint_record = json.loads(stage_checkpoint_path.read_text())
        for current_file_name in ('result.png','result.json'):
            if calculate_file_digest(stage_output_directory/current_file_name) != stage_checkpoint_record[current_file_name]:
                raise ValueError('완료 단계 산출물 무결성 오류: '+stage_directory_name)
        current_progress_writer.record_worker_progress({'stage':stage_directory_name+' · 완료 단계 재사용','step':stage_request_record['steps'],'total':stage_request_record['steps']})
        logging.info('resume 완료 단계 재사용: %s',stage_directory_name)
        return stage_output_directory
    previous_output_paths = [current_output_path for current_output_path in stage_output_directory.iterdir() if current_output_path.name not in ('request.json','reference-1.png') and not current_output_path.name.startswith('attempt-')]
    if previous_output_paths:
        previous_attempt_directory = stage_output_directory/f'attempt-{time.time_ns()}'
        previous_attempt_directory.mkdir()
        for current_output_path in previous_output_paths:
            current_output_path.rename(previous_attempt_directory/current_output_path.name)
    current_progress_writer.record_worker_progress(current_stage_progress)
    # 하위 작업은 같은 프로세스 그룹을 상속하여 공용 취소 명령이 함께 종료한다.
    with (stage_output_directory/'worker.log').open('a') as stage_log_stream:
        stage_worker_process = subprocess.Popen([sys.executable,str(WORKFLOW_ROOT_DIRECTORY/'generators/image'/worker_file_name),'--job-dir',str(stage_output_directory)],stdout=stage_log_stream,stderr=subprocess.STDOUT)
        while True:
            try:
                stage_exit_code = stage_worker_process.wait(timeout=5)
                publish_child_progress()
                break
            except subprocess.TimeoutExpired:
                publish_child_progress()
                logging.info('heartbeat stage=%s log_bytes=%s',stage_directory_name,(stage_output_directory/'worker.log').stat().st_size)
        if stage_exit_code != 0:
            stage_log_tail = (stage_output_directory/'worker.log').read_text(errors='replace')[-4000:]
            raise RuntimeError(f'{stage_directory_name} 실패 · 종료 코드 {stage_exit_code}\n{stage_log_tail}')
    stage_status_record = json.loads((stage_output_directory/'status.json').read_text())
    if stage_status_record.get('status') != 'completed':
        raise ValueError('단계 완료 상태 누락: '+stage_directory_name)
    write_pipeline_record(stage_checkpoint_path,{current_file_name:calculate_file_digest(stage_output_directory/current_file_name) for current_file_name in ('result.png','result.json')})
    return stage_output_directory


def execute_floor_pipeline(current_job_root, current_request_record):
    raise ValueError('폐기된 바닥 타일 생성 파이프라인은 실행할 수 없습니다.')


def execute_mechanical_crop(current_job_root, crop_algorithm_version=9):
    """기계식 단계 결과와 원본 해시를 보존하고 재개 시 검증한다."""
    import cv2
    from workflow.domains.tile.floor_crop import extract_molding_center, extract_legacy_molding_center
    if crop_algorithm_version not in (1,2,3,4,5,6,7,8,9):
        raise ValueError('지원하지 않는 기계식 크롭 알고리즘 버전')
    crop_start_seconds = time.monotonic()
    crop_output_directory = current_job_root/'stage-2-crop'
    crop_output_directory.mkdir(exist_ok=True)
    source_image_path = current_job_root/'result.png'
    crop_request_record = {'version':crop_algorithm_version,'source_sha256':calculate_file_digest(source_image_path)}
    crop_request_path = crop_output_directory/'request.json'
    if crop_request_path.exists() and json.loads(crop_request_path.read_text()) != crop_request_record:
        raise ValueError('기계식 크롭 원본 해시 불일치')
    write_pipeline_record(crop_request_path,crop_request_record)
    crop_checkpoint_path = crop_output_directory/'checkpoint.json'
    if crop_checkpoint_path.exists():
        for current_file_name,current_digest_value in json.loads(crop_checkpoint_path.read_text()).items():
            if calculate_file_digest(crop_output_directory/current_file_name) != current_digest_value:
                raise ValueError('기계식 크롭 산출물 무결성 오류')
        logging.info('resume 완료 단계 재사용: stage-2-crop')
    else:
        logging.info('floor-crop/start source=%s',source_image_path)
        try:
            cropped_image_value,detected_image_value,crop_result_record = (extract_legacy_molding_center(cv2.imread(str(source_image_path))) if crop_algorithm_version==1 else extract_molding_center(cv2.imread(str(source_image_path)),crop_algorithm_version))
            for current_file_name,current_image_value in (('result.png',cropped_image_value),('detected.png',detected_image_value)):
                if not cv2.imwrite(str(crop_output_directory/current_file_name),current_image_value):
                    raise OSError('기계식 크롭 이미지 저장 실패: '+current_file_name)
            write_pipeline_record(crop_output_directory/'result.json',crop_result_record|crop_request_record|{'status':'completed','elapsed_seconds':time.monotonic()-crop_start_seconds})
            write_pipeline_record(crop_checkpoint_path,{current_file_name:calculate_file_digest(crop_output_directory/current_file_name) for current_file_name in ('result.png','detected.png','result.json')})
            logging.info('floor-crop/complete bounds=%s',crop_result_record['crop_box'])
        except Exception as current_error_value:
            write_pipeline_record(crop_output_directory/'status.json',{'status':'failed','error':str(current_error_value)})
            raise
    write_pipeline_record(crop_output_directory/'status.json',{'status':'completed'})
    shutil.copyfile(crop_output_directory/'result.png',current_job_root/'center-tile.png')
    shutil.copyfile(crop_output_directory/'detected.png',current_job_root/'quadrilateral.png')
    return crop_output_directory
