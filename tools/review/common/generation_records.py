"""도메인 공용 생성 기록의 원자적 저장."""
import json
import uuid

def validate_history_tag(history_tag_value):
    if not isinstance(history_tag_value,str):raise ValueError('생성 이력 태그는 문자열이어야 합니다.')
    normalized_tag_value=history_tag_value.strip()
    if len(normalized_tag_value)>80 or '\n' in normalized_tag_value or '\r' in normalized_tag_value:raise ValueError('생성 이력 태그는 줄바꿈 없이 80자 이하여야 합니다.')
    return normalized_tag_value

def write_record_atomically(record_file_path, record_payload_value):
    temporary_record_path = record_file_path.with_name(record_file_path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary_record_path.write_text(json.dumps(record_payload_value, ensure_ascii=False)+'\n')
    temporary_record_path.replace(record_file_path)


def load_generation_history_records(history_directory_path, generation_jobs_directory):
    """색인과 작업 원본을 합쳐 조회한다. 명시적으로 숨긴 과거 기록은 복구하지 않는다."""
    import re
    from datetime import datetime
    from zoneinfo import ZoneInfo

    generation_identifier_pattern = r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}"
    history_reset_path = history_directory_path / '.reset-marker'
    history_reset_timestamp = history_reset_path.stat().st_mtime if history_reset_path.is_file() else 0
    history_records_by_identifier = {}
    for history_record_path in sorted(history_directory_path.glob('*.json')):
        current_history_record = json.loads(history_record_path.read_text())
        generation_job_identifier = current_history_record.get('id')
        if not isinstance(generation_job_identifier, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', generation_job_identifier):
            raise ValueError(f'생성 이력 ID가 올바르지 않습니다: {history_record_path}')
        history_records_by_identifier[generation_job_identifier] = current_history_record
    if generation_jobs_directory.is_dir():
        for generation_job_path in generation_jobs_directory.iterdir():
            if not re.fullmatch(generation_identifier_pattern, generation_job_path.name):
                continue
            if generation_job_path.is_symlink():
                raise ValueError(f'생성 작업 경로는 심볼릭 링크일 수 없습니다: {generation_job_path}')
            generation_request_path = generation_job_path / 'request.json'
            generation_status_path = generation_job_path / 'status.json'
            if not generation_request_path.is_file() or not generation_status_path.is_file():
                continue
            if generation_request_path.stat().st_mtime <= history_reset_timestamp:
                continue
            generation_job_identifier = generation_job_path.name
            if generation_job_identifier not in history_records_by_identifier:
                history_records_by_identifier[generation_job_identifier] = {
                    'id': generation_job_identifier,
                    'created_at': datetime.strptime(generation_job_identifier[:19], '%Y-%m-%d_%H-%M-%S').replace(tzinfo=ZoneInfo('Asia/Seoul')).isoformat(),
                    'request': json.loads(generation_request_path.read_text()),
                    'status': json.loads(generation_status_path.read_text()),
                    'job_path': str(generation_job_path),
                }
    for generation_job_identifier in list(history_records_by_identifier):
        if (generation_jobs_directory / generation_job_identifier / '.history-deleted').exists() or (history_directory_path / 'deleted' / generation_job_identifier).exists():
            del history_records_by_identifier[generation_job_identifier]
    return sorted(history_records_by_identifier.values(), key=lambda current_history_record: current_history_record.get('created_at', current_history_record['id']), reverse=True)



def observe_generation_history_records(history_directory_path, generation_jobs_directory, current_page_request):
    """숨김 이력 정책을 유지하고 복구·로그 없이 작업 ID와 기록 상태만 페이지로 읽는다."""
    import hashlib
    import re
    if not isinstance(current_page_request,dict) or set(current_page_request)-{'offset','limit','snapshot','query'}:
        raise ValueError('이력 관측 필드 오류')
    current_offset_value=current_page_request.get('offset',0)
    current_limit_value=current_page_request.get('limit',10)
    current_snapshot_value=current_page_request.get('snapshot')
    current_query_text=current_page_request.get('query','')
    if not isinstance(current_query_text,str) or len(current_query_text)>80 or (current_query_text and not re.fullmatch(r'[A-Za-z0-9_-]+',current_query_text)):
        raise ValueError('이력 ID 검색 오류')
    current_query_text=current_query_text.casefold()
    if type(current_offset_value) is not int or current_offset_value<0 or type(current_limit_value) is not int or not 1<=current_limit_value<=30:
        raise ValueError('이력 관측 페이지 오류')
    if current_snapshot_value is not None and (not isinstance(current_snapshot_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_snapshot_value)):
        raise ValueError('이력 관측 스냅샷 오류')
    if current_offset_value and current_snapshot_value is None:
        raise ValueError('후속 페이지에는 스냅샷이 필요합니다.')
    from datetime import datetime
    from zoneinfo import ZoneInfo
    current_identifier_pattern=r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}'
    current_reset_path=history_directory_path/'.reset-marker' if history_directory_path is not None else None
    current_reset_timestamp=current_reset_path.stat().st_mtime if current_reset_path is not None and current_reset_path.is_file() else 0
    current_history_order={}
    current_index_statuses={}
    current_duplicate_identifiers=set()
    current_unavailable_count=0
    for current_history_path in sorted(history_directory_path.glob('*.json')) if history_directory_path is not None else ():
        try:
            if current_history_path.is_symlink():
                raise ValueError('이력 색인 경로 오류')
            current_history_record=json.loads(current_history_path.read_text())
            current_job_identifier=current_history_record.get('id')
            current_created_value=current_history_record.get('created_at',current_job_identifier)
            if not isinstance(current_job_identifier,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',current_job_identifier) or not isinstance(current_created_value,str):
                raise ValueError('이력 색인 필드 오류')
            if current_job_identifier in current_duplicate_identifiers:
                continue
            if current_job_identifier in current_history_order:
                current_duplicate_identifiers.add(current_job_identifier)
                current_history_order.pop(current_job_identifier,None)
                current_index_statuses.pop(current_job_identifier,None)
                current_unavailable_count+=1
                continue
            current_history_order[current_job_identifier]=current_created_value
            current_index_statuses.pop(current_job_identifier,None)
            current_index_status=current_history_record.get('status')
            if isinstance(current_index_status,dict) and ('id' not in current_index_status or current_index_status['id']==current_job_identifier) and current_index_status.get('status') in ('queued','running','completed','failed','cancelled','canceled','paused'):
                current_index_statuses[current_job_identifier]=current_index_status['status']
        except (OSError,ValueError,TypeError,AttributeError):
            current_unavailable_count+=1
    if generation_jobs_directory.is_dir():
        for current_job_path in generation_jobs_directory.iterdir():
            current_job_identifier=current_job_path.name
            if current_job_identifier in current_duplicate_identifiers:
                continue
            if not re.fullmatch(current_identifier_pattern,current_job_identifier):
                continue
            if current_job_path.is_symlink():
                raise ValueError('생성 작업 경로는 심볼릭 링크일 수 없습니다.')
            current_request_path=current_job_path/'request.json'
            current_status_path=current_job_path/'status.json'
            if not current_request_path.is_file() or not current_status_path.is_file() or current_request_path.stat().st_mtime<=current_reset_timestamp:
                continue
            if current_job_identifier not in current_history_order:
                current_history_order[current_job_identifier]=datetime.strptime(current_job_identifier[:19],'%Y-%m-%d_%H-%M-%S').replace(tzinfo=ZoneInfo('Asia/Seoul')).isoformat()
    current_identifiers=sorted((current_job_identifier for current_job_identifier in current_history_order if not (generation_jobs_directory/current_job_identifier/'.history-deleted').exists() and not (history_directory_path is not None and (history_directory_path/'deleted'/current_job_identifier).exists())),key=lambda current_job_identifier:current_history_order[current_job_identifier],reverse=True)
    if current_query_text:current_identifiers=[current_identifier for current_identifier in current_identifiers if current_query_text in current_identifier.casefold()]
    current_snapshot_payload={'ids':current_identifiers,'unavailable_count':current_unavailable_count}
    if current_query_text:current_snapshot_payload['query']=current_query_text
    current_snapshot_hash=hashlib.sha256(json.dumps(current_snapshot_payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if current_snapshot_value is not None and current_snapshot_value!=current_snapshot_hash:
        raise ValueError('이력이 변경되었습니다. 첫 페이지부터 다시 조회하세요.')
    current_output_records=[]
    for current_job_identifier in current_identifiers[current_offset_value:current_offset_value+current_limit_value]:
        current_status_path=generation_jobs_directory/current_job_identifier/'status.json'
        try:
            if current_status_path.is_symlink() or current_status_path.parent.is_symlink():
                raise ValueError('이력 상태 경로 오류')
            current_status_record=json.loads(current_status_path.read_text())
            if not isinstance(current_status_record,dict) or ('id' in current_status_record and current_status_record['id']!=current_job_identifier):
                raise ValueError('이력 상태 ID 불일치')
            current_status_value=current_status_record['status']
            current_status_source='job'
            if current_status_value not in ('queued','running','completed','failed','cancelled','canceled','paused'):
                current_status_value='unknown'
        except FileNotFoundError:
            current_status_value=current_index_statuses.get(current_job_identifier,'unknown')
            current_status_source='index' if current_job_identifier in current_index_statuses else 'unavailable'
        except (OSError,ValueError,TypeError,KeyError):
            current_status_value='unknown'
            current_status_source='unavailable'
        current_output_records.append({'id':current_job_identifier,'recorded_status':current_status_value,'status_source':current_status_source})
    current_next_offset=current_offset_value+len(current_output_records)
    return {'records':current_output_records,'total':len(current_identifiers),'offset':current_offset_value,
            'next_offset':current_next_offset if current_next_offset<len(current_identifiers) else None,'snapshot':current_snapshot_hash,'unavailable_count':current_unavailable_count,
            'note':'기록된 상태이며 실제 프로세스 생존·결과 품질은 확인하지 않습니다.'}
