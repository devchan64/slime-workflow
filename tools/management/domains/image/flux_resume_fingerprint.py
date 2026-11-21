"""FLUX 재개 검토에 사용할 저장 기록과 참조 내용의 지문."""
import hashlib
import json
import os
import stat
from contextlib import ExitStack
from pathlib import Path


def fingerprint_flux_resume_inputs(current_job_directory,current_profile_name):
    """저장 파일을 안정적으로 읽어 지문을 만들며 작업을 실행하지 않는다."""
    if not isinstance(current_profile_name,str) or not current_profile_name.startswith('flux-'):
        raise ValueError('FLUX 프로필 오류')
    current_combined_hash=hashlib.sha256()
    try:
        with ExitStack() as current_open_resources:
            current_directory_descriptor=os.open(Path(current_job_directory),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            current_open_resources.callback(os.close,current_directory_descriptor)
            def read_stable_resume_file(current_file_name,current_optional_file=False,current_parse_json=False):
                try:
                    current_file_descriptor=os.open(current_file_name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=current_directory_descriptor)
                except FileNotFoundError:
                    if not current_optional_file:raise
                    current_combined_hash.update((current_file_name+'\\0missing\\0').encode())
                    return None
                with os.fdopen(current_file_descriptor,'rb') as current_file_stream:
                    current_before_stat=os.fstat(current_file_stream.fileno())
                    if not stat.S_ISREG(current_before_stat.st_mode):raise ValueError('FLUX 재개 기록은 일반 파일이어야 합니다.')
                    if current_parse_json and current_before_stat.st_size>8*1024*1024:raise ValueError('FLUX 재개 기록이 너무 큽니다.')
                    current_file_hash=hashlib.sha256()
                    current_file_parts=[]
                    for current_file_chunk in iter(lambda:current_file_stream.read(1048576),b''):
                        current_file_hash.update(current_file_chunk)
                        if current_parse_json:current_file_parts.append(current_file_chunk)
                    current_after_stat=os.fstat(current_file_stream.fileno())
                    current_path_stat=os.stat(current_file_name,dir_fd=current_directory_descriptor,follow_symlinks=False)
                    def compare_resume_file_identity(current_stat_value):
                        return (current_stat_value.st_dev,current_stat_value.st_ino,current_stat_value.st_size,current_stat_value.st_mtime_ns,current_stat_value.st_ctime_ns)
                    if compare_resume_file_identity(current_before_stat)!=compare_resume_file_identity(current_after_stat) or compare_resume_file_identity(current_after_stat)!=compare_resume_file_identity(current_path_stat):
                        raise ValueError('FLUX 재개 기록이 조회 중 변경됐습니다.')
                    current_combined_hash.update((current_file_name+'\\0present\\0').encode())
                    current_combined_hash.update(current_file_hash.digest())
                    return json.loads(b''.join(current_file_parts)) if current_parse_json else None
            current_request_record=read_stable_resume_file('request.json',current_parse_json=True)
            current_status_record=read_stable_resume_file('status.json',current_parse_json=True)
            if not isinstance(current_request_record,dict) or current_request_record.get('profile')!=current_profile_name:
                raise ValueError('FLUX 재개 요청 프로필 오류')
            if not isinstance(current_status_record,dict) or current_status_record.get('status') not in ('failed','cancelled','paused'):
                raise ValueError('실패·취소·일시정지 작업만 재개를 검토할 수 있습니다.')
            current_reference_values=current_request_record.get('references')
            if not isinstance(current_reference_values,list) or len(current_reference_values)>2:
                raise ValueError('FLUX 참조 목록 오류')
            for current_reference_index,current_reference_name in enumerate(current_reference_values,1):
                if current_reference_name!=f'reference-{current_reference_index}.png':raise ValueError('FLUX 참조 순서 오류')
                read_stable_resume_file(current_reference_name)
            read_stable_resume_file('gpu-command.json',current_optional_file=True)
            read_stable_resume_file('translation-pipeline.json',current_optional_file=True)
            return {'status':current_status_record['status'],'fingerprint':current_combined_hash.hexdigest()}
    except (OSError,UnicodeError,json.JSONDecodeError) as current_read_error:
        raise ValueError('FLUX 재개 기록을 확인할 수 없습니다.') from current_read_error
