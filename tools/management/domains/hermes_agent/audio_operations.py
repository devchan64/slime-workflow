"""기존 음악·효과음 생성기의 GPU 작업을 안전하게 위임한다."""
import os
import re
import threading
from contextlib import contextmanager
from tools.management.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from tools.management.common.management_gateway import execute_management_command
from tools.management.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.management.domains.hermes_agent.failure_observer import observe_hermes_generator_failure

HERMES_AUDIO_SERVICES = ('music-heartmula','sfx-dasheng-audiogen')


def validate_hermes_audio_service(current_service_name):
    if not isinstance(current_service_name,str) or current_service_name not in HERMES_AUDIO_SERVICES:
        raise ValueError('지원하는 음악 또는 효과음 서비스가 아닙니다.')


def call_hermes_audio_service(current_service_name,current_command_name,current_payload_record):
    validate_hermes_audio_service(current_service_name)
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    return execute_management_command(current_service_name,current_command_name,current_payload_record,current_gateway_address)


def validate_hermes_audio_request(current_service_name,current_request_record):
    from generators.music.contracts import validate_music_request
    validate_hermes_audio_service(current_service_name)
    if not isinstance(current_request_record,dict) or current_request_record.get('action','generate')!='generate':
        raise ValueError('오디오 위임에는 생성 요청만 허용합니다.')
    validate_music_request(current_service_name,current_request_record)


def submit_hermes_audio_request(current_request_identifier,current_service_name,current_request_record):
    validate_hermes_audio_service(current_service_name)
    return HermesDelegationStore().execute_service_delegation_once(current_request_identifier,current_service_name,current_request_record,
        lambda current_request_value:call_hermes_audio_service(current_service_name,'generate',current_request_value),
        lambda current_request_value:validate_hermes_audio_request(current_service_name,current_request_value))


def read_hermes_audio_status(current_request_identifier,current_service_name):
    validate_hermes_audio_service(current_service_name)
    current_receipt_value=HermesDelegationStore().read_service_delegation(current_request_identifier,current_service_name)
    if current_receipt_value.get('state')!='accepted':
        return {'receipt':current_receipt_value}
    return {'receipt':current_receipt_value,'job':read_hermes_audio_source_job(current_service_name,current_receipt_value['job_id'])}


def observe_hermes_audio_file(current_service_name,current_job_identifier,current_audio_path):
    """원본 상태·시도 불일치나 조회 중 변경은 링크를 표시할 수 없는 상태다."""
    from pathlib import Path
    from tools.management.domains.hermes_agent.delegation_store import read_bounded_delegation_record
    from tools.management.domains.music.generation import MusicGenerationManager
    try:
        filenames = r'(music\.wav|mr\.wav|vocals\.wav|music\.mp3|mr\.mp3|vocals\.mp3)' if current_service_name == 'music-heartmula' else r'(sound\.wav)'
        current_path_match=re.fullmatch('/'+re.escape(current_service_name)+'/jobs/'+re.escape(current_job_identifier)+r'/attempts/([a-f0-9]{32})/'+filenames,current_audio_path)
        if not current_path_match:return 'unknown'
        current_storage_root=Path(MusicGenerationManager(current_service_name).job_storage_root)
        current_job_root=current_storage_root/current_job_identifier
        if current_storage_root.is_symlink() or not current_storage_root.is_dir() or current_job_root.is_symlink() or not current_job_root.is_dir() or current_job_root.resolve().parent!=current_storage_root.resolve():return 'unknown'
        current_status_path=current_job_root/'status.json'
        current_result_path=current_job_root/'result.json'
        current_status_record=read_bounded_delegation_record(current_status_path)
        current_result_record=read_bounded_delegation_record(current_result_path)
        if not isinstance(current_status_record,dict) or current_status_record.get('status')!='completed' or not isinstance(current_result_record,dict) or current_result_record.get('format')!='wav' or current_result_record.get('attempt')!=current_path_match[1]:return 'unavailable'
        current_attempts_root=current_job_root/'attempts'
        current_attempt_root=current_attempts_root/current_path_match[1]
        current_audio_file=current_attempt_root/current_path_match[2]
        current_present_value=(not current_attempts_root.is_symlink() and current_attempts_root.is_dir() and not current_attempt_root.is_symlink() and current_attempt_root.is_dir() and current_attempt_root.resolve().parent==current_attempts_root.resolve() and not current_audio_file.is_symlink() and current_audio_file.is_file())
        if read_bounded_delegation_record(current_status_path)!=current_status_record or read_bounded_delegation_record(current_result_path)!=current_result_record:return 'unavailable'
        return 'present' if current_present_value else 'unavailable'
    except OSError:
        return 'unknown'
    except (ValueError,TypeError,KeyError):
        return 'unavailable'


def read_hermes_audio_source_job(current_service_name,current_job_identifier):
    """원 서비스 작업 ID를 검증하고 상태와 동일 출처 결과 경로만 반환한다."""
    from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier
    validate_hermes_audio_service(current_service_name)
    if not validate_service_job_identifier(current_service_name,current_job_identifier):
        raise ValueError('음악 또는 효과음 작업 ID 형식 오류')
    current_job_value=call_hermes_audio_service(current_service_name,'status',{'id':current_job_identifier})
    if not isinstance(current_job_value,dict) or current_job_value.get('id')!=current_job_identifier:
        raise ValueError('오디오 작업 상태 응답 형식 오류')
    current_status_value=current_job_value.get('status')
    if current_status_value not in ('queued','running','completed','failed','cancelled','canceled','paused','unknown'):
        current_status_value='unknown'
    from tools.management.domains.hermes_agent.media_result_paths import validate_hermes_audio_result_path
    current_audio_path=validate_hermes_audio_result_path(current_service_name,current_job_identifier,{**current_job_value,'status':current_status_value})
    current_result_status='available' if current_audio_path else 'unavailable' if current_status_value=='completed' else 'not_ready'
    current_file_observation=observe_hermes_audio_file(current_service_name,current_job_identifier,current_audio_path) if current_audio_path else 'not_ready'
    tracks = []
    stems = current_job_value.get('audio_stems')
    if current_service_name == 'music-heartmula' and current_audio_path and isinstance(stems, dict) and stems:
        base = current_audio_path.rsplit('/', 1)[0]
        result = current_job_value.get('result') or {}
        mp3_outputs = result.get('mp3_outputs') or {}
        for name, label in (('music', '원곡'), ('mr', 'MR'), ('vocals', '분리 보컬')):
            wav = f'{base}/{name}.wav'
            if name != 'music' and (stems.get(name) != wav or observe_hermes_audio_file(current_service_name,current_job_identifier,wav) != 'present'):
                continue
            track = {'label': label, 'wav': wav}
            mp3 = f'{base}/{name}.mp3'
            metadata = mp3_outputs.get(name) if isinstance(mp3_outputs, dict) else None
            if isinstance(metadata, dict) and metadata.get('filename') == name+'.mp3' and observe_hermes_audio_file(current_service_name,current_job_identifier,mp3) == 'present':
                track['mp3'] = mp3
            tracks.append(track)
    return {'status':current_status_value,'audio':current_audio_path,'result_status':current_result_status,'file_observation':current_file_observation, **({'tracks':tracks} if tracks else {}),
        'note':'완료 결과와 상세 로그·분리 음원은 해당 생성기 이력에서 확인하세요. 생성 결과는 자동으로 에셋에 등록되지 않습니다.', **observe_hermes_generator_failure(current_status_value,current_job_value.get('error'))}


def validate_hermes_audio_source_response(current_service_name,current_job_identifier,current_response_value):
    """서비스·작업 ID와 상태별 결과 경로의 일관성을 검사한다."""
    from tools.management.domains.hermes_agent.delegation_store import validate_service_job_identifier
    from tools.management.domains.hermes_agent.media_result_paths import validate_hermes_audio_result_path
    validate_hermes_audio_service(current_service_name)
    if not validate_service_job_identifier(current_service_name,current_job_identifier):raise ValueError('오디오 작업 ID 형식 오류')
    if not isinstance(current_response_value,dict) or current_response_value.get('service')!=current_service_name or current_response_value.get('job_id')!=current_job_identifier or not isinstance(current_response_value.get('job'),dict):raise ValueError('오디오 상태 응답 불일치')
    current_job_record=current_response_value['job']
    if current_job_record.get('status') not in ('queued','running','completed','failed','cancelled','canceled','paused','unknown') or current_job_record.get('result_status') not in ('available','unavailable','not_ready'):raise ValueError('오디오 상태 형식 오류')
    current_audio_path=validate_hermes_audio_result_path(current_service_name,current_job_identifier,current_job_record)
    current_expected_result='available' if current_audio_path else 'unavailable' if current_job_record['status']=='completed' else 'not_ready'
    if (current_job_record.get('audio') is not None and current_audio_path is None) or current_job_record['result_status']!=current_expected_result:raise ValueError('오디오 결과 경로 오류')
    current_file_observation=current_job_record.get('file_observation','unknown')
    if current_file_observation not in ('present','unavailable','unknown','not_ready') or (current_file_observation in ('present','unavailable') and not current_audio_path) or (current_audio_path and current_file_observation=='not_ready'):raise ValueError('오디오 파일 관측 오류')
    return current_job_record


def list_hermes_audio_receipts(current_service_name):
    validate_hermes_audio_service(current_service_name)
    return HermesDelegationStore().list_service_delegations(current_service_name)


def cancel_hermes_audio_request(current_request_identifier,current_service_name,current_job_identifier):
    validate_hermes_audio_service(current_service_name)
    current_receipt_value=HermesDelegationStore().read_service_delegation(current_request_identifier,current_service_name)
    if current_receipt_value.get('state')!='accepted' or current_receipt_value.get('job_id')!=current_job_identifier:
        raise ValueError('접수 기록과 확인한 오디오 작업 ID가 일치하지 않습니다.')
    current_cancel_value=call_hermes_audio_service(current_service_name,'cancel',{'id':current_job_identifier})
    if (not isinstance(current_cancel_value,dict) or current_cancel_value.get('cancel_requested') is not True
            or ('id' in current_cancel_value and current_cancel_value['id']!=current_job_identifier)):
        raise ValueError('오디오 중지 응답 형식 오류')
    return {'job_id':current_job_identifier,'cancel_requested':True,'status':current_cancel_value.get('status','unknown')}



SOURCE_HISTORY_LOCK_GUARD = threading.Lock()
SOURCE_HISTORY_SERVICE_LOCKS = {}


@contextmanager
def hold_hermes_source_history_guard(current_service_name):
    """같은 원본의 동시 이력 순회를 한 프로세스에서 거부한다."""
    from tools.management.common.source_history_catalog import SOURCE_HISTORY_SERVICE_ALIASES
    current_source_service=SOURCE_HISTORY_SERVICE_ALIASES.get(current_service_name,current_service_name)
    with SOURCE_HISTORY_LOCK_GUARD:
        current_source_lock=SOURCE_HISTORY_SERVICE_LOCKS.setdefault(current_source_service,threading.Lock())
    if not current_source_lock.acquire(blocking=False):
        raise ValueError('해당 원본 이력을 조회 중입니다. 완료 후 다시 조회하세요.')
    try:
        yield
    finally:
        current_source_lock.release()


def validate_hermes_source_history_request(current_page_request):
    """원 서비스 호출 전에 공통 이력 페이지 입력을 검증한다."""
    if not isinstance(current_page_request,dict) or set(current_page_request)-{'offset','limit','snapshot','query'}:
        raise ValueError('생성기 이력 페이지 입력 오류')
    current_offset_value=current_page_request.get('offset',0)
    current_limit_value=current_page_request.get('limit',10)
    current_snapshot_value=current_page_request.get('snapshot')
    current_query_value=current_page_request.get('query','')
    if type(current_offset_value) is not int or current_offset_value<0 or type(current_limit_value) is not int or not 1<=current_limit_value<=30:
        raise ValueError('생성기 이력 페이지 범위 오류')
    if not isinstance(current_query_value,str) or len(current_query_value)>80 or (current_query_value and not re.fullmatch(r'[A-Za-z0-9_-]+',current_query_value)):
        raise ValueError('생성기 이력 검색어 오류')
    if current_snapshot_value is not None and (not isinstance(current_snapshot_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_snapshot_value)):
        raise ValueError('생성기 이력 스냅샷 오류')
    if current_offset_value>0 and current_snapshot_value is None:
        raise ValueError('후속 페이지에는 스냅샷이 필요합니다.')


def read_hermes_audio_source_history(current_service_name,current_page_request):
    """기존 서비스의 기록 상태만 읽는다. 접수 ID나 입력·로그를 만들지 않는다."""
    from tools.management.common.source_history_catalog import SOURCE_HISTORY_AUDIO_SERVICES
    if not isinstance(current_service_name,str) or current_service_name not in SOURCE_HISTORY_AUDIO_SERVICES:
        raise ValueError('지원하는 오디오 이력 서비스가 아닙니다.')
    validate_hermes_source_history_request(current_page_request)
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    with hold_hermes_source_history_guard(current_service_name):
        current_result_value=execute_management_command(current_service_name,'history-observe',current_page_request,current_gateway_address)
        return sanitize_hermes_source_history(current_service_name,current_page_request,current_result_value)


def sanitize_hermes_source_history(current_service_name,current_page_request,current_result_value):
    """기존 서비스 응답에서 ID·기록 상태와 페이지 정보만 허용한다."""
    validate_hermes_source_history_request(current_page_request)
    if not isinstance(current_result_value,dict) or not isinstance(current_result_value.get('records'),list):
        raise ValueError('오디오 원본 이력 응답 오류')
    current_query_text=current_page_request.get('query','')
    if not isinstance(current_query_text,str) or len(current_query_text)>80 or (current_query_text and not re.fullmatch(r'[A-Za-z0-9_-]+',current_query_text)):
        raise ValueError('생성기 이력 검색어 오류')
    current_query_text=current_query_text.casefold()
    current_safe_records=[]
    for current_record_value in current_result_value['records']:
        if not isinstance(current_record_value,dict) or not isinstance(current_record_value.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',current_record_value['id']) or current_record_value.get('recorded_status') not in ('queued','running','completed','failed','cancelled','canceled','paused','unknown','preparing','indexing','searching','reasoning','review','applied','interrupted'):
            raise ValueError('오디오 이력 레코드 오류')
        if current_query_text and current_query_text not in current_record_value['id'].casefold():raise ValueError('검색 결과 ID 불일치')
        current_status_source=current_record_value.get('status_source')
        if current_status_source not in ('job','index','unavailable') or (current_status_source=='unavailable' and current_record_value['recorded_status']!='unknown'):
            raise ValueError('생성기 이력 상태 출처 오류')
        current_safe_records.append({'id':current_record_value['id'],'recorded_status':current_record_value['recorded_status'],'status_source':current_status_source})
    current_total_value=current_result_value.get('total')
    current_offset_value=current_result_value.get('offset')
    current_next_offset=current_result_value.get('next_offset')
    current_snapshot_value=current_result_value.get('snapshot')
    current_unavailable_count=current_result_value.get('unavailable_count')
    current_request_offset=current_page_request.get('offset',0)
    current_request_limit=current_page_request.get('limit',10)
    current_request_snapshot=current_page_request.get('snapshot')
    if (type(current_request_offset) is not int or current_request_offset<0 or type(current_request_limit) is not int or not 1<=current_request_limit<=30
            or type(current_unavailable_count) is not int or current_unavailable_count<0 or type(current_total_value) is not int or current_total_value<0 or type(current_offset_value) is not int or current_offset_value!=current_request_offset or current_offset_value>current_total_value
            or not isinstance(current_snapshot_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_snapshot_value)
            or (current_request_offset>0 and current_request_snapshot is None)
            or (current_request_snapshot is not None and current_snapshot_value!=current_request_snapshot)):
        raise ValueError('생성기 이력 페이지 오류')
    current_expected_count=min(current_request_limit,max(0,current_total_value-current_offset_value))
    current_expected_next=current_offset_value+current_expected_count if current_offset_value+current_expected_count<current_total_value else None
    if (len(current_safe_records)!=current_expected_count or len({current_record['id'] for current_record in current_safe_records})!=len(current_safe_records)
            or current_next_offset!=current_expected_next or (current_next_offset is not None and type(current_next_offset) is not int)):
        raise ValueError('생성기 이력 페이지 오류')
    return {'service':current_service_name,'records':current_safe_records,'total':current_total_value,'offset':current_offset_value,'next_offset':current_next_offset,'snapshot':current_snapshot_value,'unavailable_count':current_unavailable_count,'note':'기록 상태이며 실제 작업 생존과 결과 품질은 해당 생성기에서 확인하세요. 확인 불가 수에는 손상 색인과 중복 ID가 포함될 수 있습니다.'}



def read_hermes_generator_source_history(current_service_name,current_page_request):
    """이미지·영상·번역·작가 서비스의 원본 이력에서 기록 상태만 관측한다."""
    from tools.management.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES,SOURCE_HISTORY_SERVICE_ALIASES
    if not isinstance(current_service_name,str) or current_service_name not in SOURCE_HISTORY_GENERATOR_SERVICES:
        raise ValueError('지원하는 이미지·영상 생성기가 아닙니다.')
    validate_hermes_source_history_request(current_page_request)
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    current_command_name='writer-history-observe' if current_service_name=='writer-agent' else 'history-observe'
    with hold_hermes_source_history_guard(current_service_name):
        current_result_value=execute_management_command(current_service_name,current_command_name,current_page_request,current_gateway_address)
        current_sanitized_value=sanitize_hermes_source_history(current_service_name,current_page_request,current_result_value)
    current_sanitized_value['source_service']=SOURCE_HISTORY_SERVICE_ALIASES.get(current_service_name,current_service_name)
    if current_service_name=='building-generator':
        current_sanitized_value['note']+=' 건물 생성기는 빌보드 생성기 이력을 공유하는 호환 경로입니다.'
    return current_sanitized_value
