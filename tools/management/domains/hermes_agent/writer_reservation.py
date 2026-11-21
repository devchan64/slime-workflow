"""정리 미확인 작가 GPU 예약의 검토 및 조건부 복구."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
import re
import stat
from pathlib import Path

from tools.management.common.generation_records import write_record_atomically
from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore, check_delegation_record_exists, read_bounded_delegation_record


@contextmanager
def hold_writer_reservation_queue_lock():
    from tools.management.common import gpu_job_queue as current_queue_module
    current_queue_root=Path(current_queue_module.GPU_QUEUE_DIRECTORY)
    current_active_root=current_queue_root/'active'
    current_lock_path=current_queue_root/'execution.lock'
    if current_queue_root.is_symlink() or current_active_root.is_symlink() or not current_active_root.is_dir() or current_lock_path.is_symlink():
        raise ValueError('GPU 예약 목록 또는 잠금을 확인할 수 없습니다.')
    current_lock_descriptor=os.open(current_lock_path,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o666)
    with os.fdopen(current_lock_descriptor,'a') as current_lock_stream:
        if not stat.S_ISREG(os.fstat(current_lock_stream.fileno()).st_mode):
            raise ValueError('GPU 예약 잠금 파일 형식 오류')
        fcntl.flock(current_lock_stream,fcntl.LOCK_EX)
        yield current_active_root


def find_writer_reservation_record(current_active_root,current_job_identifier):
    if not isinstance(current_job_identifier,str) or not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[a-f0-9]{8}',current_job_identifier):
        raise ValueError('작가 작업 ID 형식 오류')
    current_matches_list=[]
    for current_record_path in current_active_root.glob('*.json'):
        if current_record_path.is_symlink() or not current_record_path.is_file():raise ValueError('GPU 예약 기록을 확인할 수 없습니다.')
        try:current_record_value=read_bounded_delegation_record(current_record_path)
        except (OSError,ValueError,TypeError) as current_record_error:raise ValueError('GPU 예약 기록을 확인할 수 없습니다.') from current_record_error
        if not isinstance(current_record_value,dict) or not isinstance(current_record_value.get('path'),str) or not isinstance(current_record_value.get('service'),str):raise ValueError('GPU 예약 식별 정보를 확인할 수 없습니다.')
        if Path(current_record_value['path']).name==current_job_identifier:
            current_matches_list.append((current_record_path,current_record_value))
    if len(current_matches_list)!=1:raise ValueError('일치하는 작가 예약이 없거나 둘 이상입니다.')
    if current_matches_list[0][1]['service']!='writer-agent':raise ValueError('예약의 원 서비스가 작가와 일치하지 않습니다.')
    return current_matches_list[0]


def is_writer_executor_definitely_absent(current_executor_pid):
    """PID가 현재 존재하지 않는 경우만 부재로 인정한다."""
    if type(current_executor_pid) is not int or not 1<current_executor_pid<=2147483647:
        return False
    try:
        os.kill(current_executor_pid,0)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    return False


def inspect_writer_reservation_record(current_record_path,current_record_value,current_job_identifier):
    from tools.management.common import gpu_job_queue as current_queue_module
    if current_record_value.get('recovery_in_progress') is not None:
        return {'job_id':current_job_identifier,'recoverable':False,'reason':'이미 정리 결과 확인이 필요한 예약입니다.'},None
    current_executor_pid=current_record_value.get('pid')
    current_executor_token=current_record_value.get('pid_start_token')
    if type(current_executor_pid) is not int or not 1<current_executor_pid<=2147483647 or not isinstance(current_executor_token,str) or not current_executor_token.isascii() or not current_executor_token.isdigit():
        return {'job_id':current_job_identifier,'recoverable':False,'reason':'실행기 신원을 확인할 수 없습니다. 예약을 유지합니다.'},None
    if not is_writer_executor_definitely_absent(current_executor_pid):
        return {'job_id':current_job_identifier,'recoverable':False,'reason':'실행기 PID의 부재를 확인할 수 없습니다. 예약을 유지합니다.'},None
    current_worker_descriptor=current_queue_module.open_verified_hermes_process_group(current_record_value)
    if current_worker_descriptor is None:
        return {'job_id':current_job_identifier,'recoverable':False,'reason':'작업자 그룹 리더의 신원을 확인할 수 없습니다. 예약을 유지합니다.'},None
    try:
        current_preview_bytes=json.dumps({'filename':current_record_path.name,'record':current_record_value},sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    except (TypeError,ValueError):
        os.close(current_worker_descriptor)
        raise ValueError('GPU 예약 기록 형식 오류') from None
    return {'job_id':current_job_identifier,'recoverable':True,'preview_sha256':hashlib.sha256(current_preview_bytes).hexdigest(),'reason':'검증된 작업자 그룹이 실행 중입니다. 정리하면 해당 그룹을 강제 종료합니다. 별도 그룹의 GPU 프로세스는 운영자가 직접 확인해야 합니다.'},current_worker_descriptor


def preview_writer_reservation_recovery(current_job_identifier):
    with hold_writer_reservation_queue_lock() as current_active_root:
        current_record_path,current_record_value=find_writer_reservation_record(current_active_root,current_job_identifier)
        current_preview_value,current_worker_descriptor=inspect_writer_reservation_record(current_record_path,current_record_value,current_job_identifier)
        if current_worker_descriptor is not None:os.close(current_worker_descriptor)
        return current_preview_value


def inspect_writer_recovery_receipt(current_receipt_value,current_request_identifier):
    from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier
    if (not isinstance(current_receipt_value,dict) or set(current_receipt_value)!={'version','id','job_id','preview_sha256','state'}
            or type(current_receipt_value.get('version')) is not int or current_receipt_value.get('version')!=12
            or current_receipt_value.get('id')!=current_request_identifier or current_receipt_value.get('state') not in ('dispatching','completed')
            or not validate_service_job_identifier('writer-agent',current_receipt_value.get('job_id'))
            or not isinstance(current_receipt_value.get('preview_sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_receipt_value['preview_sha256'])):
        raise ValueError('작가 예약 정리 접수 기록 오류')
    return {'request_id':current_request_identifier,'job_id':current_receipt_value['job_id'],'state':'unknown' if current_receipt_value['state']=='dispatching' else 'completed'}


def recover_writer_reservation_once(current_request_identifier,current_job_identifier,current_preview_digest,current_outside_processes_checked):
    from tools.management.common import gpu_job_queue as current_queue_module
    if current_outside_processes_checked is not True:raise ValueError('별도 그룹 GPU 프로세스를 확인해야 합니다.')
    if not isinstance(current_preview_digest,str) or not re.fullmatch(r'[a-f0-9]{64}',current_preview_digest):raise ValueError('예약 검토 해시 오류')
    current_store_value=HermesDelegationStore()
    current_worker_descriptor=None
    with current_store_value.hold_delegation_storage_lock():
        current_receipt_path=current_store_value.resolve_delegation_record_path(current_request_identifier)
        if check_delegation_record_exists(current_receipt_path):
            current_receipt_value=read_bounded_delegation_record(current_receipt_path)
            current_result_value=inspect_writer_recovery_receipt(current_receipt_value,current_request_identifier)
            if (current_receipt_value.get('job_id'),current_receipt_value.get('preview_sha256'))!=(current_job_identifier,current_preview_digest):raise ValueError('같은 접수 ID를 다른 예약에 사용할 수 없습니다.')
            return {**current_result_value,'duplicate':True}
        with hold_writer_reservation_queue_lock() as current_active_root:
            current_record_path,current_record_value=find_writer_reservation_record(current_active_root,current_job_identifier)
            current_preview_value,current_worker_descriptor=inspect_writer_reservation_record(current_record_path,current_record_value,current_job_identifier)
            if not current_preview_value['recoverable'] or current_preview_value['preview_sha256']!=current_preview_digest:
                if current_worker_descriptor is not None:os.close(current_worker_descriptor)
                raise ValueError('예약 상태가 바뀌었거나 신원을 확인할 수 없습니다. 다시 검토하세요.')
            try:
                current_receipt_value={'version':12,'id':current_request_identifier,'job_id':current_job_identifier,'preview_sha256':current_preview_digest,'state':'dispatching'}
                write_record_atomically(current_receipt_path,current_receipt_value)
                current_marked_record={**current_record_value,'cleanup_unverified':True,'recovery_in_progress':current_request_identifier}
                write_record_atomically(current_record_path,current_marked_record)
            except BaseException:
                os.close(current_worker_descriptor)
                raise
    try:
        current_queue_module.stop_hermes_worker_process_group(current_record_value['worker_pgid'],current_worker_descriptor)
    finally:
        os.close(current_worker_descriptor)
    with hold_writer_reservation_queue_lock() as current_active_root:
        current_current_path,current_current_record=find_writer_reservation_record(current_active_root,current_job_identifier)
        if current_current_path!=current_record_path or current_current_record!=current_marked_record:
            raise ValueError('정리 중 예약이 변경됐습니다. 결과를 확인하세요.')
        if not is_writer_executor_definitely_absent(current_record_value['pid']):
            raise ValueError('실행기 상태가 변경됐습니다. 예약을 유지합니다.')
        current_current_path.unlink()
    with current_store_value.hold_delegation_storage_lock():
        current_receipt_value=read_bounded_delegation_record(current_receipt_path)
        current_expected_value={'version':12,'id':current_request_identifier,'job_id':current_job_identifier,'preview_sha256':current_preview_digest,'state':'dispatching'}
        if current_receipt_value!=current_expected_value or type(current_receipt_value.get('version')) is not int:
            raise ValueError('정리 접수 기록이 변경됐습니다. 결과를 확인하세요.')
        current_receipt_value['state']='completed'
        write_record_atomically(current_receipt_path,current_receipt_value)
        return {**inspect_writer_recovery_receipt(current_receipt_value,current_request_identifier),'duplicate':False}


def read_writer_recovery_receipt(current_request_identifier):
    current_store_value=HermesDelegationStore()
    with current_store_value.hold_delegation_storage_lock():
        current_receipt_path=current_store_value.resolve_delegation_record_path(current_request_identifier)
        if not check_delegation_record_exists(current_receipt_path):return {'state':'not_found'}
        return inspect_writer_recovery_receipt(read_bounded_delegation_record(current_receipt_path),current_request_identifier)
