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
from PIL import Image
from tools.review.domains.image.three_reference_generation import save_three_reference_inputs

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]


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
    stage_checkpoint_path = stage_output_directory/'checkpoint.json'
    if stage_checkpoint_path.exists():
        stage_checkpoint_record = json.loads(stage_checkpoint_path.read_text())
        for current_file_name in ('result.png','result.json'):
            if calculate_file_digest(stage_output_directory/current_file_name) != stage_checkpoint_record[current_file_name]:
                raise ValueError('완료 단계 산출물 무결성 오류: '+stage_directory_name)
        logging.info('resume 완료 단계 재사용: %s',stage_directory_name)
        return stage_output_directory
    previous_output_paths = [current_output_path for current_output_path in stage_output_directory.iterdir() if current_output_path.name not in ('request.json','reference-1.png') and not current_output_path.name.startswith('attempt-')]
    if previous_output_paths:
        previous_attempt_directory = stage_output_directory/f'attempt-{time.time_ns()}'
        previous_attempt_directory.mkdir()
        for current_output_path in previous_output_paths:
            current_output_path.rename(previous_attempt_directory/current_output_path.name)
    # 하위 작업은 같은 프로세스 그룹을 상속하여 공용 취소 명령이 함께 종료한다.
    with (stage_output_directory/'worker.log').open('a') as stage_log_stream:
        stage_worker_process = subprocess.Popen([sys.executable,str(WORKFLOW_ROOT_DIRECTORY/'generators/image'/worker_file_name),'--job-dir',str(stage_output_directory)],stdout=stage_log_stream,stderr=subprocess.STDOUT)
        while True:
            try:
                stage_exit_code = stage_worker_process.wait(timeout=5)
                break
            except subprocess.TimeoutExpired:
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
    pipeline_start_seconds = time.monotonic()
    mechanical_crop_enabled = current_request_record['floor_separation']['version'] == 2
    pipeline_stage_count = 3 if mechanical_crop_enabled else 2
    current_stage_name = f'1/{pipeline_stage_count} · 9칸 생성'
    try:
        separation_request_record = current_request_record['floor_separation']
        if separation_request_record['version'] not in (1,2):
            raise ValueError('지원하지 않는 바닥 분리 단계 버전')
        write_pipeline_record(current_job_root/'status.json',{'status':'running','stage':current_stage_name})
        grid_request_record = {current_field_name:current_request_record[current_field_name] for current_field_name in ('action','prompt','width','height','steps','seed')}
        grid_output_directory = execute_floor_stage(current_job_root,'stage-1-grid','run_qwen_2512.py',grid_request_record)
        shutil.copyfile(grid_output_directory/'result.png',current_job_root/'result.png')
        reference_source_path = current_job_root/'result.png'
        crop_output_directory = None
        if mechanical_crop_enabled:
            current_stage_name = '2/3 · 중앙 몰딩 기계식 크롭'
            write_pipeline_record(current_job_root/'status.json',{'status':'running','stage':current_stage_name})
            crop_output_directory = execute_mechanical_crop(current_job_root)
            reference_source_path = crop_output_directory/'result.png'
        current_stage_name = f'{pipeline_stage_count}/{pipeline_stage_count} · 사용자 설명으로 다시 그리기'
        reference_stage_directory = 'stage-3-redraw' if mechanical_crop_enabled else 'stage-2-separation'
        write_pipeline_record(current_job_root/'status.json',{'status':'running','stage':current_stage_name})
        reference_output_directory = current_job_root/reference_stage_directory
        reference_output_directory.mkdir(exist_ok=True)
        reference_image_path = reference_output_directory/'reference-1.png'
        if not (reference_output_directory/'request.json').exists():
            with Image.open(reference_source_path) as original_image_value:
                original_image_value.convert('RGB').resize((512,512),Image.Resampling.LANCZOS).save(current_job_root/'reference-1.png')
            # 중단된 참조 저장 단계만 재시도한다. 완료된 단계는 아래 해시로 검증한다.
            reference_image_path.unlink(missing_ok=True)
            reference_request_record = save_three_reference_inputs(reference_output_directory,{
                'action':'generate',**{current_field_name:separation_request_record[current_field_name] for current_field_name in ('prompt','width','height','steps','seed')},
                'images':[base64.b64encode((current_job_root/'reference-1.png').read_bytes()).decode()]})
            reference_request_record.update({current_field_name:separation_request_record[current_field_name] for current_field_name in ('prompt_words','prompt_sha256')})
            reference_request_record['source_sha256'] = calculate_file_digest(reference_source_path)
            write_pipeline_record(reference_output_directory/'request.json',reference_request_record)
        reference_request_record = json.loads((reference_output_directory/'request.json').read_text())
        if any(reference_request_record[current_field_name] != separation_request_record[current_field_name] for current_field_name in ('prompt','width','height','steps','seed','prompt_words','prompt_sha256')):
            raise ValueError('저장된 참조 생성 요청과 원래 설정 불일치')
        if reference_request_record['source_sha256'] != calculate_file_digest(reference_source_path):
            raise ValueError('참조 생성 입력의 출처 불일치')
        from tools.review.domains.image.three_reference_generation import verify_reference_snapshots
        verify_reference_snapshots(reference_output_directory,reference_request_record)
        separated_output_directory = execute_floor_stage(current_job_root,reference_stage_directory,'run_qwen_2511_three_reference.py',reference_request_record)
        shutil.copyfile(separated_output_directory/'result.png',current_job_root/'single-tile.png')
        completed_stage_directories = (grid_output_directory,crop_output_directory,separated_output_directory) if mechanical_crop_enabled else (grid_output_directory,separated_output_directory)
        write_pipeline_record(current_job_root/'result.json',{'elapsed_seconds':sum(json.loads((current_stage_directory/'result.json').read_text())['elapsed_seconds'] for current_stage_directory in completed_stage_directories),'last_attempt_seconds':time.monotonic()-pipeline_start_seconds,'pipeline_version':separation_request_record['version'],'stages':[{'path':str(current_stage_directory.relative_to(current_job_root)),'request':json.loads((current_stage_directory/'request.json').read_text()),'result':json.loads((current_stage_directory/'result.json').read_text())} for current_stage_directory in completed_stage_directories],'original_sha256':calculate_file_digest(current_job_root/'result.png'),'separated_sha256':calculate_file_digest(current_job_root/'single-tile.png')})
        write_pipeline_record(current_job_root/'status.json',{'status':'completed','stage':f'{pipeline_stage_count}/{pipeline_stage_count} · 완료'})
        logging.info('complete output=%s',current_job_root/'single-tile.png')
    except Exception as current_error_value:
        write_pipeline_record(current_job_root/'status.json',{'status':'failed','stage':current_stage_name,'error':str(current_error_value)})
        logging.exception('failed stage=%s output=%s',current_stage_name,current_job_root)
        raise


def execute_mechanical_crop(current_job_root):
    """기계식 단계 결과와 원본 해시를 보존하고 재개 시 검증한다."""
    import cv2
    from tools.review.domains.tile.floor_crop import extract_molding_center
    crop_start_seconds = time.monotonic()
    crop_output_directory = current_job_root/'stage-2-crop'
    crop_output_directory.mkdir(exist_ok=True)
    source_image_path = current_job_root/'result.png'
    crop_request_record = {'version':1,'source_sha256':calculate_file_digest(source_image_path)}
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
            cropped_image_value,detected_image_value,crop_result_record = extract_molding_center(cv2.imread(str(source_image_path)))
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
