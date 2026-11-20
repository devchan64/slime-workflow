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


def read_bounded_kimodo_source_file(current_file_path,current_byte_limit):
    """링크와 특수 파일을 거부하고 읽는 동안 파일 교체·변경을 확인한다."""
    try:
        current_descriptor_value=os.open(current_file_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(current_descriptor_value,'rb') as current_file_stream:
            current_before_stat=os.fstat(current_file_stream.fileno())
            if not stat.S_ISREG(current_before_stat.st_mode) or current_before_stat.st_size>current_byte_limit:raise ValueError('원본 파일 크기 또는 형식 오류')
            current_file_bytes=current_file_stream.read(current_byte_limit+1)
            current_after_stat=os.fstat(current_file_stream.fileno())
            current_path_stat=os.stat(current_file_path,follow_symlinks=False)
        def current_stat_signature(current_stat_record):
            return (current_stat_record.st_dev,current_stat_record.st_ino,current_stat_record.st_size,current_stat_record.st_mtime_ns,current_stat_record.st_ctime_ns)
        if len(current_file_bytes)>current_byte_limit or current_stat_signature(current_before_stat)!=current_stat_signature(current_after_stat) or current_stat_signature(current_after_stat)!=current_stat_signature(current_path_stat):raise ValueError('원본 파일이 조회 중 변경되었습니다.')
        return current_file_bytes
    except OSError as current_file_error:
        raise ValueError('원본 파일을 확인할 수 없습니다.') from current_file_error


def prepare_reviewed_kimodo_keyframe_source(current_job_identifier,current_attempt_identifier,current_frame_number,current_tag_text,*,current_job_storage=None):
    """상한과 배열 헤더를 먼저 검증한 동일 메모리 사본으로 검토한다."""
    import io
    import math
    import zipfile
    import zlib
    import numpy as np
    from tools.review.domains.kimodo.generation import KIMODO_JOB_STORAGE
    from tools.review.domains.kimodo.keyframe_storage import KIMODO_FRAME_ARRAY_SHAPES,prepare_kimodo_keyframe_source
    if not isinstance(current_tag_text,str) or not current_tag_text.strip() or len(current_tag_text.strip())>80 or any(ord(current_character)<32 for current_character in current_tag_text):raise ValueError('키프레임 태그 오류')
    current_storage_root=Path(KIMODO_JOB_STORAGE if current_job_storage is None else current_job_storage)
    current_frame_record=inspect_kimodo_source_frame(current_job_identifier,current_attempt_identifier,current_frame_number,current_job_storage=current_storage_root)
    current_job_root=current_storage_root/current_job_identifier
    current_attempt_root=current_job_root/'attempts'/current_attempt_identifier
    current_status_record=read_bounded_delegation_record(current_job_root/'status.json')
    current_result_record=read_bounded_delegation_record(current_attempt_root/'result.json')
    current_horizontal_removed=current_result_record.get('remove_horizontal_motion',False) if isinstance(current_result_record,dict) else None
    if type(current_horizontal_removed) is not bool:raise ValueError('원본 모션 유형 오류')
    current_motion_path=current_attempt_root/('motion-in-place.npz' if current_horizontal_removed else 'motion.npz')
    current_skeleton_path=current_attempt_root/'skeleton.json'
    current_preview_path=current_attempt_root/('output-'+format(current_frame_number-1,'03d')+'.png')
    current_snapshot_record={'status':current_status_record,'result':current_result_record,'skeleton':read_bounded_kimodo_source_file(current_skeleton_path,1024*1024),'preview':read_bounded_kimodo_source_file(current_preview_path,KIMODO_FRAME_PREVIEW_MAX_BYTES),'motion':read_bounded_kimodo_source_file(current_motion_path,128*1024*1024)}
    try:
        with zipfile.ZipFile(io.BytesIO(current_snapshot_record['motion'])) as current_motion_zip:
            current_zip_items=current_motion_zip.infolist()
            current_expected_names={current_name+'.npy' for current_name in KIMODO_FRAME_ARRAY_SHAPES}
            if len(current_zip_items)!=len(current_expected_names) or {current_item.filename for current_item in current_zip_items}!=current_expected_names or sum(current_item.file_size for current_item in current_zip_items)>256*1024*1024:raise ValueError('원본 모션 압축 파일 구성 오류')
            for current_zip_item in current_zip_items:
                current_array_name=current_zip_item.filename[:-4]
                with current_motion_zip.open(current_zip_item) as current_array_stream:
                    current_version_value=np.lib.format.read_magic(current_array_stream)
                    if current_version_value not in ((1,0),(2,0)):raise ValueError('원본 모션 배열 버전 오류')
                    current_header_reader=np.lib.format.read_array_header_1_0 if current_version_value==(1,0) else np.lib.format.read_array_header_2_0
                    current_shape_value,current_fortran_value,current_dtype_value=current_header_reader(current_array_stream,max_header_size=10000)
                    current_valid_dtype=np.issubdtype(current_dtype_value,np.integer) or np.issubdtype(current_dtype_value,np.floating) or (current_array_name=='foot_contacts' and np.issubdtype(current_dtype_value,np.bool_))
                    current_array_size=math.prod(current_shape_value)*current_dtype_value.itemsize
                    if current_shape_value!=(current_frame_record['frame_count'],*KIMODO_FRAME_ARRAY_SHAPES[current_array_name]) or not current_valid_dtype or current_array_size>256*1024*1024 or current_array_size!=current_zip_item.file_size-current_array_stream.tell():raise ValueError('원본 모션 배열 헤더 오류')
        current_prepared_value=prepare_kimodo_keyframe_source(current_job_identifier,current_attempt_identifier,current_frame_number,current_tag_text,current_job_storage=current_storage_root,current_source_snapshot=current_snapshot_record)
    except (zipfile.BadZipFile,zlib.error,EOFError,OverflowError,MemoryError,OSError) as current_archive_error:
        raise ValueError('원본 모션 압축 파일을 확인할 수 없습니다.') from current_archive_error
    current_after_record=inspect_kimodo_source_frame(current_job_identifier,current_attempt_identifier,current_frame_number,current_job_storage=current_storage_root)
    if current_frame_record!=current_after_record or read_bounded_delegation_record(current_job_root/'status.json')!=current_status_record or read_bounded_delegation_record(current_attempt_root/'result.json')!=current_result_record or read_bounded_kimodo_source_file(current_skeleton_path,1024*1024)!=current_snapshot_record['skeleton'] or read_bounded_kimodo_source_file(current_motion_path,128*1024*1024)!=current_snapshot_record['motion'] or hashlib.sha256(current_prepared_value['preview_bytes']).hexdigest()!=current_frame_record['image_sha256']:raise ValueError('키프레임 원본이 검토 중 변경되었습니다.')
    current_review_record={'job_id':current_job_identifier,'attempt_id':current_attempt_identifier,'frame':current_frame_number,'tag':current_tag_text.strip(),'frame_count':current_prepared_value['frame_count'],'source_motion':current_prepared_value['source_motion'],'image':current_frame_record['image'],'image_sha256':current_frame_record['image_sha256'],'review_sha256':current_prepared_value['review_sha256'],'note':'조회 시점의 원본을 검증한 결과입니다. 저장은 별도이며 외부 동시 수정은 제한될 수 있습니다.'}
    return current_review_record,current_prepared_value


def review_kimodo_keyframe_source(current_job_identifier,current_attempt_identifier,current_frame_number,current_tag_text,*,current_job_storage=None):
    """저장 없이 키프레임 원본 검토 결과를 반환한다."""
    return prepare_reviewed_kimodo_keyframe_source(current_job_identifier,current_attempt_identifier,current_frame_number,current_tag_text,current_job_storage=current_job_storage)[0]



def validate_kimodo_source_frame_response(current_job_identifier,current_attempt_identifier,current_frame_number,current_response_value):
    """전달된 프레임 응답의 신원과 고정 경로를 재검증한다."""
    if not validate_service_job_identifier('kimodo',current_job_identifier) or not isinstance(current_attempt_identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',current_attempt_identifier) or type(current_frame_number) is not int or not 1<=current_frame_number<=1000 or not isinstance(current_response_value,dict):raise ValueError('Kimodo 프레임 응답 형식 오류')
    current_expected_path='/kimodo/jobs/'+current_job_identifier+'/attempts/'+current_attempt_identifier+'/output-'+format(current_frame_number-1,'03d')+'.png'
    if current_response_value.get('job_id')!=current_job_identifier or current_response_value.get('attempt_id')!=current_attempt_identifier or type(current_response_value.get('frame')) is not int or current_response_value.get('frame')!=current_frame_number or type(current_response_value.get('frame_count')) is not int or not current_frame_number<=current_response_value['frame_count']<=1000 or current_response_value.get('fps')!=30 or current_response_value.get('image')!=current_expected_path or not isinstance(current_response_value.get('image_sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_response_value['image_sha256']):raise ValueError('Kimodo 프레임 응답 불일치')
    return current_response_value
