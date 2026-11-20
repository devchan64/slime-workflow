"""Kimodo 원본 모션의 특정 프레임을 저장 없이 검토한다."""
import hashlib
import os
from pathlib import Path
import re
import stat

from tools.review.domains.hermes_agent.delegation_store import read_bounded_delegation_record,validate_service_job_identifier

KIMODO_FRAME_PREVIEW_MAX_BYTES=12*1024*1024


def inspect_kimodo_source_frame(current_job_identifier,current_attempt_identifier,current_frame_number,*,current_job_storage=None):
    """완료 작업의 현재 시도·프레임 해시를 확인한다. 키프레임 저장은 하지 않는다."""
    from tools.review.domains.kimodo.generation import KIMODO_JOB_STORAGE
    if not validate_service_job_identifier('kimodo',current_job_identifier) or not isinstance(current_attempt_identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',current_attempt_identifier) or type(current_frame_number) is not int or not 1<=current_frame_number<=1000:
        raise ValueError('Kimodo 작업·시도·프레임 형식 오류')
    current_storage_root=Path(KIMODO_JOB_STORAGE if current_job_storage is None else current_job_storage)
    current_job_root=current_storage_root/current_job_identifier
    current_attempts_root=current_job_root/'attempts'
    current_attempt_root=current_attempts_root/current_attempt_identifier
    if any(current_path.is_symlink() or not current_path.is_dir() for current_path in (current_storage_root,current_job_root,current_attempts_root,current_attempt_root)) or current_job_root.resolve().parent!=current_storage_root.resolve() or current_attempt_root.resolve().parent!=current_attempts_root.resolve():raise ValueError('Kimodo 원본 작업 경로 오류')
    current_status_path=current_job_root/'status.json'
    current_root_result_path=current_job_root/'result.json'
    current_attempt_result_path=current_attempt_root/'result.json'
    current_status_record=read_bounded_delegation_record(current_status_path)
    current_root_result=read_bounded_delegation_record(current_root_result_path)
    current_attempt_result=read_bounded_delegation_record(current_attempt_result_path)
    if not isinstance(current_status_record,dict) or current_status_record.get('status')!='completed' or not isinstance(current_root_result,dict) or current_root_result.get('attempt')!=current_attempt_identifier or not isinstance(current_attempt_result,dict) or current_attempt_result.get('attempt')!=current_attempt_identifier:raise ValueError('완료된 현재 시도를 확인할 수 없습니다.')
    current_frame_count=current_attempt_result.get('frames')
    current_frame_hashes=current_attempt_result.get('frame_sha256')
    if type(current_frame_count) is not int or not 1<=current_frame_count<=1000 or current_frame_number>current_frame_count or current_attempt_result.get('fps')!=30 or not isinstance(current_frame_hashes,list) or len(current_frame_hashes)!=current_frame_count or not isinstance(current_frame_hashes[current_frame_number-1],str) or not re.fullmatch(r'[a-f0-9]{64}',current_frame_hashes[current_frame_number-1]):raise ValueError('Kimodo 프레임 범위 또는 해시 기록 오류')
    current_frame_filename='output-'+format(current_frame_number-1,'03d')+'.png'
    current_frame_path=current_attempt_root/current_frame_filename
    current_file_descriptor=os.open(current_frame_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(current_file_descriptor,'rb') as current_frame_stream:
        current_file_stat=os.fstat(current_frame_stream.fileno())
        if not stat.S_ISREG(current_file_stat.st_mode) or current_file_stat.st_size>KIMODO_FRAME_PREVIEW_MAX_BYTES:raise ValueError('프레임 파일 크기 또는 형식 오류')
        current_frame_bytes=current_frame_stream.read(KIMODO_FRAME_PREVIEW_MAX_BYTES+1)
    if len(current_frame_bytes)>KIMODO_FRAME_PREVIEW_MAX_BYTES or not current_frame_bytes.startswith(b'\x89PNG\r\n\x1a\n') or hashlib.sha256(current_frame_bytes).hexdigest()!=current_frame_hashes[current_frame_number-1]:raise ValueError('프레임 이미지 또는 해시가 일치하지 않습니다.')
    if read_bounded_delegation_record(current_status_path)!=current_status_record or read_bounded_delegation_record(current_root_result_path)!=current_root_result or read_bounded_delegation_record(current_attempt_result_path)!=current_attempt_result:raise ValueError('Kimodo 원본 기록이 조회 중 변경되었습니다.')
    return {'job_id':current_job_identifier,'attempt_id':current_attempt_identifier,'frame':current_frame_number,'frame_count':current_frame_count,'fps':30,'image':'/kimodo/jobs/'+current_job_identifier+'/attempts/'+current_attempt_identifier+'/'+current_frame_filename,'image_sha256':current_frame_hashes[current_frame_number-1],'note':'프레임 해시와 PNG 시그니처만 확인했습니다. 이미지 내용·모션·골격 유효성 및 키프레임 저장 가능성은 별도입니다.'}


def validate_kimodo_source_frame_response(current_job_identifier,current_attempt_identifier,current_frame_number,current_response_value):
    """전달된 프레임 응답의 신원과 고정 경로를 재검증한다."""
    if not validate_service_job_identifier('kimodo',current_job_identifier) or not isinstance(current_attempt_identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',current_attempt_identifier) or type(current_frame_number) is not int or not 1<=current_frame_number<=1000 or not isinstance(current_response_value,dict):raise ValueError('Kimodo 프레임 응답 형식 오류')
    current_expected_path='/kimodo/jobs/'+current_job_identifier+'/attempts/'+current_attempt_identifier+'/output-'+format(current_frame_number-1,'03d')+'.png'
    if current_response_value.get('job_id')!=current_job_identifier or current_response_value.get('attempt_id')!=current_attempt_identifier or type(current_response_value.get('frame')) is not int or current_response_value.get('frame')!=current_frame_number or type(current_response_value.get('frame_count')) is not int or not current_frame_number<=current_response_value['frame_count']<=1000 or current_response_value.get('fps')!=30 or current_response_value.get('image')!=current_expected_path or not isinstance(current_response_value.get('image_sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_response_value['image_sha256']):raise ValueError('Kimodo 프레임 응답 불일치')
    return current_response_value
