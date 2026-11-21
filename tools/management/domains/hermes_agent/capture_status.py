"""접수 기록과 대기열 작업의 신원이 맞는 캡처 상태만 읽는다."""
import hashlib
import json
import os
import stat
from pathlib import Path

from tools.management.domains.hermes_agent.capture_delegation import normalize_capture_delegation_request


CAPTURE_RECORD_MAXIMUM_BYTES = 1048576


def read_bounded_capture_record(current_record_path):
    """일반 파일만 열고 크기가 증가해도 정해진 한도만 읽는다."""
    current_descriptor_value=os.open(current_record_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(current_descriptor_value,'rb') as current_file_handle:
        if not stat.S_ISREG(os.fstat(current_file_handle.fileno()).st_mode):
            raise ValueError('캡처 기록 파일 형식 오류')
        current_record_bytes=current_file_handle.read(CAPTURE_RECORD_MAXIMUM_BYTES+1)
    if len(current_record_bytes)>CAPTURE_RECORD_MAXIMUM_BYTES:
        raise ValueError('캡처 기록 크기 초과')
    return current_record_bytes


def verify_capture_result_files(current_result_record, current_service_name, current_workflow_root, current_capture_settings):
    """원 캡처 저장소 안의 예상 PNG가 모두 존재하고 읽히는지 확인한다."""
    from PIL import Image
    if not isinstance(current_result_record,dict) or current_result_record.get('status') != 'completed' or current_result_record.get('settings') != current_capture_settings or not isinstance(current_result_record.get('directory'),str):
        return False
    current_expected_names = ('map',) if current_service_name == 'map-review' else ('baseline','adjusted','comparison')
    current_image_values = current_result_record.get('images')
    if not isinstance(current_image_values,dict) or set(current_image_values) != set(current_expected_names):
        return False
    current_capture_root = Path(current_workflow_root)/'.tmp'/'test'/'character-review-capture'
    current_capture_directory = Path(current_result_record['directory'])
    if not current_capture_directory.is_absolute() or current_capture_directory.parent != current_capture_root:
        return False
    for current_path_value in (current_capture_root,current_capture_directory):
        if current_path_value.is_symlink() or not current_path_value.is_dir() or current_path_value.resolve() != current_path_value.absolute():
            return False
    from yaml import safe_load, YAMLError
    current_original_record_path = current_capture_directory/'result.yaml'
    if current_original_record_path.is_symlink() or not current_original_record_path.is_file() or current_original_record_path.stat().st_size > 1048576:
        return False
    try:
        current_original_record = safe_load(read_bounded_capture_record(current_original_record_path))
    except (OSError,UnicodeError,ValueError,YAMLError):
        return False
    if not isinstance(current_original_record,dict) or any(current_original_record.get(current_key_name) != current_result_record.get(current_key_name) for current_key_name in ('status','settings','directory','images')):
        return False
    for current_image_name in current_expected_names:
        current_image_path = current_capture_directory/(current_image_name+'.png')
        if current_image_values[current_image_name] != str(current_image_path) or current_image_path.is_symlink() or not current_image_path.is_file():
            return False
        try:
            with Image.open(current_image_path) as current_image_object:
                if current_image_object.format != 'PNG':
                    return False
                if current_service_name == 'map-review':
                    from tools.management.domains.map_review.capture import MAP_CAPTURE_MAXIMUM_EDGE
                    if current_image_object.mode != 'RGBA' or max(current_image_object.size) > MAP_CAPTURE_MAXIMUM_EDGE:
                        return False
                else:
                    from tools.management.domains.character_review.capture import CAPTURE_INTERNAL_RESOLUTION_SCALE
                    current_width_value = current_capture_settings['width'] * CAPTURE_INTERNAL_RESOLUTION_SCALE * (2 if current_image_name == 'comparison' else 1)
                    current_height_value = current_capture_settings['height'] * CAPTURE_INTERNAL_RESOLUTION_SCALE
                    if current_image_object.size != (current_width_value,current_height_value):
                        return False
                current_image_object.verify()
            with Image.open(current_image_path) as current_image_object:
                if current_image_object.convert('RGBA').getchannel('A').getbbox() is None:
                    return False
        except (OSError,ValueError,Image.DecompressionBombError):
            return False
    return True


def read_capture_delegation_status(current_delegation_store, current_request_identifier, current_service_name, current_workflow_root):
    """불완전하거나 바뀐 기록은 불명으로 반환하며 복구·재실행하지 않는다."""
    if current_service_name not in ('map-review', 'character-review'):
        raise ValueError('지원하지 않는 검수 캡처 서비스입니다.')
    current_receipt_record = current_delegation_store.read_service_delegation(current_request_identifier, current_service_name)
    if current_receipt_record.get('state') != 'accepted':
        return {'receipt':current_receipt_record, 'job':None}
    current_unknown_result = {'receipt':current_receipt_record, 'job':{'status':'unknown', 'result_available':False}}
    current_root_path = Path(current_workflow_root)
    current_job_root = current_root_path / '.tmp' / 'test' / 'review-capture'
    current_job_directory = current_job_root / current_receipt_record['job_id']
    try:
        for current_path_value in (current_root_path, current_root_path/'.tmp', current_root_path/'.tmp'/'test', current_job_root, current_job_directory):
            if current_path_value.is_symlink() or not current_path_value.is_dir():
                return current_unknown_result
        if current_job_directory.resolve() != current_job_directory.absolute():
            return current_unknown_result
        current_request_path = current_job_directory/'request.json'
        current_status_path = current_job_directory/'status.json'
        current_command_path = current_job_directory/'gpu-command.json'
        for current_file_path in (current_request_path,current_status_path,current_command_path):
            if current_file_path.is_symlink() or not current_file_path.is_file():
                return current_unknown_result
        current_request_record = json.loads(read_bounded_capture_record(current_request_path))
        if not isinstance(current_request_record,dict) or set(current_request_record) != {'request_id','service','settings'} or current_request_record['request_id'] != current_request_identifier or current_request_record['service'] != current_service_name:
            return current_unknown_result
        current_normalized_settings = normalize_capture_delegation_request(current_service_name,current_request_record['settings'])
        if current_normalized_settings != current_request_record['settings']:
            return current_unknown_result
        current_digest_bytes = json.dumps({'service':current_service_name,'request':current_normalized_settings},ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
        with current_delegation_store.hold_delegation_storage_lock():
            current_receipt_path = current_delegation_store.resolve_delegation_record_path(current_request_identifier)
            current_stored_receipt = json.loads(read_bounded_capture_record(current_receipt_path))
        if not isinstance(current_stored_receipt,dict) or current_stored_receipt.get('version') != 2 or current_stored_receipt.get('id') != current_request_identifier or current_stored_receipt.get('service') != current_service_name or current_stored_receipt.get('state') != 'accepted' or current_stored_receipt.get('job_id') != current_receipt_record['job_id'] or current_stored_receipt.get('request_sha256') != hashlib.sha256(current_digest_bytes).hexdigest():
            return current_unknown_result
        current_command_record = json.loads(read_bounded_capture_record(current_command_path))
        current_command_values = current_command_record.get('command') if isinstance(current_command_record,dict) else None
        if not isinstance(current_command_record,dict) or current_command_record.get('service') != 'review-capture' or not isinstance(current_command_values,list) or len(current_command_values) != 5 or not isinstance(current_command_values[0],str) or current_command_values[1:] != ['-m','tools.management.domains.hermes_agent.capture_worker','--job-dir',str(current_job_directory)]:
            return current_unknown_result
        current_status_record = json.loads(read_bounded_capture_record(current_status_path))
        current_status_name = current_status_record.get('status') if isinstance(current_status_record,dict) else None
        if current_status_name not in ('queued','running','completed','failed','cancelled'):
            return current_unknown_result
        current_result_available = False
        current_result_path = current_job_directory/'capture-result.json'
        if current_status_name == 'completed' and not current_result_path.is_symlink() and current_result_path.is_file():
            current_result_record = json.loads(read_bounded_capture_record(current_result_path))
            current_result_available = verify_capture_result_files(current_result_record,current_service_name,current_root_path,current_normalized_settings)
        return {'receipt':current_receipt_record, 'job':{'status':current_status_name, 'result_available':current_result_available}}
    except (OSError,ValueError,TypeError,KeyError):
        return current_unknown_result


def find_verified_capture_request_identity(current_delegation_store, current_job_identifier, current_workflow_root):
    """경로와 접수·작업 기록이 일치할 때만 대기 작업의 접수 ID를 반환한다."""
    from tools.management.domains.hermes_agent.delegation_store import HERMES_DELEGATION_JOB_PATTERN
    if not isinstance(current_job_identifier,str) or not HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_job_identifier):
        return None
    current_job_directory=Path(current_workflow_root)/'.tmp'/'test'/'review-capture'/current_job_identifier
    current_request_path=current_job_directory/'request.json'
    try:
        if current_job_directory.is_symlink() or not current_job_directory.is_dir() or current_request_path.is_symlink() or not current_request_path.is_file():
            return None
        current_request_record=json.loads(read_bounded_capture_record(current_request_path))
        if not isinstance(current_request_record,dict) or set(current_request_record)!={'request_id','service','settings'}:
            return None
        current_result_value=read_capture_delegation_status(current_delegation_store,current_request_record['request_id'],current_request_record['service'],current_workflow_root)
        current_receipt_value=current_result_value.get('receipt') or {}
        current_job_value=current_result_value.get('job') or {}
        if current_receipt_value.get('state') != 'accepted' or current_receipt_value.get('job_id') != current_job_identifier or current_job_value.get('status') not in ('queued','running'):
            return None
        return {'request_id':current_receipt_value['request_id'],'capture_service':current_receipt_value['service']}
    except (OSError,ValueError,TypeError,KeyError):
        return None
