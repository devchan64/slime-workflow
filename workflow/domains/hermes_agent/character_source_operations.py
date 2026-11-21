"""폐기된 캐릭터 애니메이션 작업의 기록과 프레임을 읽는다."""
import re
from pathlib import Path
from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record,validate_service_job_identifier
from workflow.domains.hermes_agent.failure_observer import observe_hermes_generator_failure


def read_character_source_job(current_job_identifier):
    from workflow.domains.character_animation.character_animation_jobs import GENERATION_ROOT_DIRECTORY
    from workflow.domains.character_animation.character_animation_assets import SUPPORTED_DIRECTION_NAMES
    if not validate_service_job_identifier('character-animation',current_job_identifier):raise ValueError('캐릭터 작업 ID 오류')
    current_root_path=Path(GENERATION_ROOT_DIRECTORY)
    current_timestamp_path=current_root_path/current_job_identifier[:19]
    current_job_path=current_timestamp_path/current_job_identifier
    if any(current_path.is_symlink() or not current_path.is_dir() for current_path in (current_root_path,current_timestamp_path,current_job_path)) or current_timestamp_path.resolve().parent!=current_root_path.resolve() or current_job_path.resolve().parent!=current_timestamp_path.resolve():raise ValueError('캐릭터 작업 경로 오류')
    current_status_path=current_job_path/'status.json'
    current_status_record=read_bounded_delegation_record(current_status_path)
    if not isinstance(current_status_record,dict):raise ValueError('캐릭터 작업 상태 오류')
    current_status_value=current_status_record.get('status')
    if current_status_value not in ('queued','running','completed','failed','cancelled','canceled','paused','unknown'):current_status_value='unknown'
    current_preview_url=None
    current_request_record=None
    current_progress_observed=None
    current_progress_path=current_job_path/'progress.json'
    try:
        current_request_record=read_bounded_delegation_record(current_job_path/'request.json')
        current_frame_records=current_request_record['frames']
        if not isinstance(current_frame_records,list) or not 1<=len(current_frame_records)<=512:raise ValueError('프레임 목록 오류')
        current_progress_record=current_status_record.get('progress',{})
        if current_status_value!='completed':
            try:
                current_progress_observed=read_bounded_delegation_record(current_progress_path)
            except FileNotFoundError:
                pass
            else:
                current_progress_record=current_progress_observed
        current_completed_count=len(current_frame_records) if current_status_value=='completed' else current_progress_record.get('completed',0) if isinstance(current_progress_record,dict) else 0
        if type(current_completed_count) is not int or not 0<=current_completed_count<=len(current_frame_records):raise ValueError('프레임 진행 오류')
        if current_completed_count:
            current_frame_record=current_frame_records[current_completed_count-1]
            if not isinstance(current_frame_record,dict) or current_frame_record.get('direction') not in SUPPORTED_DIRECTION_NAMES or type(current_frame_record.get('frame')) is not int or not 0<=current_frame_record['frame']<=9999:raise ValueError('프레임 식별 오류')
            current_direction_path=current_job_path/current_frame_record['direction']
            current_frame_path=current_direction_path/('frame-'+format(current_frame_record['frame'],'04d'))
            current_image_path=current_frame_path/'result.png'
            if not current_direction_path.is_symlink() and current_direction_path.is_dir() and not current_frame_path.is_symlink() and current_frame_path.is_dir() and not current_image_path.is_symlink() and current_image_path.is_file():
                current_preview_url='/character-animation/files/'+current_job_identifier+'/'+current_frame_record['direction']+'/'+current_frame_path.name+'/result.png'
    except (OSError,ValueError,TypeError,KeyError):
        pass
    if read_bounded_delegation_record(current_status_path)!=current_status_record:raise ValueError('캐릭터 상태가 조회 중 변경되었습니다.')
    if current_preview_url is not None and (read_bounded_delegation_record(current_job_path/'request.json')!=current_request_record or (current_progress_observed is not None and read_bounded_delegation_record(current_progress_path)!=current_progress_observed)):raise ValueError('캐릭터 프레임 정보가 조회 중 변경되었습니다.')
    return {'status':current_status_value,'image':current_preview_url,'result_status':'available' if current_preview_url else 'unavailable' if current_status_value=='completed' else 'not_ready','note':'조회 시점의 마지막 완료 프레임 파일만 확인합니다. 전체 결과·이미지 품질·프로세스 생존은 별도 확인하세요.',**observe_hermes_generator_failure(current_status_value,current_status_record.get('error'))}


def validate_character_source_response(current_job_identifier,current_response_value):
    if not validate_service_job_identifier('character-animation',current_job_identifier) or not isinstance(current_response_value,dict) or current_response_value.get('service')!='character-animation' or current_response_value.get('job_id')!=current_job_identifier or not isinstance(current_response_value.get('job'),dict):raise ValueError('캐릭터 원본 응답 불일치')
    current_job_record=current_response_value['job']
    if current_job_record.get('status') not in ('queued','running','completed','failed','cancelled','canceled','paused','unknown'):raise ValueError('캐릭터 상태 오류')
    current_image_path=current_job_record.get('image')
    current_expected_prefix='/character-animation/files/'+current_job_identifier+'/'
    if current_image_path is not None and (not isinstance(current_image_path,str) or not re.fullmatch(re.escape(current_expected_prefix)+r'(?:down_left|down_right|up_left|up_right)/frame-[0-9]{4}/result\.png',current_image_path)):raise ValueError('캐릭터 프레임 경로 오류')
    current_expected_status='available' if current_image_path else 'unavailable' if current_job_record['status']=='completed' else 'not_ready'
    if current_job_record.get('result_status')!=current_expected_status:raise ValueError('캐릭터 결과 상태 오류')
    return current_job_record
