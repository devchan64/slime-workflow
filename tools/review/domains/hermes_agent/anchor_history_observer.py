"""과거 앵커 이력의 경로 없는 제한된 요약을 조회한다."""
import hashlib
import json
import os
import re
from pathlib import Path
from datetime import datetime

from tools.review.domains.hermes_agent.delegation_store import read_bounded_delegation_record

ANCHOR_OBSERVER_MAXIMUM_ENTRIES = 4096
ANCHOR_OBSERVER_IDENTIFIER_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}')
ANCHOR_OBSERVER_SOURCE_PATTERN = re.compile(r'[A-Za-z0-9._-]{1,160}')


def read_hermes_anchor_history(current_query_record):
    """저장된 이력의 요약만 읽으며 문서·시트 경로는 반환하지 않는다."""
    from tools.review.domains.character_animation.anchor_history import ANCHOR_HISTORY_ROOT
    if not isinstance(current_query_record,dict) or set(current_query_record)-{'animation_id','animation_version','offset','limit','snapshot'}:
        raise ValueError('앵커 이력 조회 입력 오류')
    current_animation_identifier=current_query_record.get('animation_id')
    current_animation_version=current_query_record.get('animation_version')
    current_offset_value=current_query_record.get('offset',0)
    current_limit_value=current_query_record.get('limit',20)
    if not all(isinstance(current_value,str) and ANCHOR_OBSERVER_SOURCE_PATTERN.fullmatch(current_value) for current_value in (current_animation_identifier,current_animation_version)) or type(current_offset_value) is not int or current_offset_value<0 or type(current_limit_value) is not int or not 1<=current_limit_value<=30:
        raise ValueError('앵커 이력 조회 범위 오류')
    current_root_path=Path(ANCHOR_HISTORY_ROOT)
    current_record_values=[]
    current_entry_count=0
    try:
        current_root_stat=current_root_path.lstat()
    except FileNotFoundError:
        current_root_stat=None
    if current_root_stat is not None:
        if current_root_path.is_symlink() or not current_root_path.is_dir():raise ValueError('앵커 이력 저장소 오류')
        with os.scandir(current_root_path) as current_date_entries:
            for current_date_entry in current_date_entries:
                current_entry_count+=1
                if current_entry_count>ANCHOR_OBSERVER_MAXIMUM_ENTRIES:raise ValueError('앵커 이력 조회 한도 초과')
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}',current_date_entry.name):continue
                if not current_date_entry.is_dir(follow_symlinks=False):raise ValueError('앵커 이력 날짜 경로 오류')
                with os.scandir(current_date_entry.path) as current_job_entries:
                    for current_job_entry in current_job_entries:
                        current_entry_count+=1
                        if current_entry_count>ANCHOR_OBSERVER_MAXIMUM_ENTRIES:raise ValueError('앵커 이력 조회 한도 초과')
                        if not ANCHOR_OBSERVER_IDENTIFIER_PATTERN.fullmatch(current_job_entry.name):continue
                        if current_job_entry.name[:19]!=current_date_entry.name or not current_job_entry.is_dir(follow_symlinks=False):raise ValueError('앵커 이력 작업 경로 오류')
                        current_job_path=Path(current_job_entry.path)
                        try:(current_job_path/'history-hidden.json').lstat()
                        except FileNotFoundError:pass
                        else:continue
                        current_result_record=read_bounded_delegation_record(current_job_path/'result.json')
                        if not isinstance(current_result_record,dict) or current_result_record.get('id')!=current_job_entry.name or current_result_record.get('status')!='completed' or type(current_result_record.get('frames')) is not int or not 0<=current_result_record['frames']<=10000 or not isinstance(current_result_record.get('created_at'),str) or len(current_result_record['created_at'])>64 or not isinstance(current_result_record.get('source'),dict):raise ValueError('앵커 이력 기록 오류')
                        try:current_created_time=datetime.fromisoformat(current_result_record['created_at'])
                        except ValueError as current_time_error:raise ValueError('앵커 이력 시간 오류') from current_time_error
                        if current_created_time.tzinfo is None:raise ValueError('앵커 이력 시간대 오류')
                        current_source_record=current_result_record['source']
                        if not all(isinstance(current_source_record.get(current_field_name),str) and ANCHOR_OBSERVER_SOURCE_PATTERN.fullmatch(current_source_record[current_field_name]) for current_field_name in ('animationId','animationVersion')):raise ValueError('앵커 이력 출처 오류')
                        if current_source_record.get('animationId')==current_animation_identifier and current_source_record.get('animationVersion')==current_animation_version:
                            current_record_values.append({'id':current_job_entry.name,'created_at':current_result_record['created_at'],'frames':current_result_record['frames']})
    current_record_values.sort(key=lambda current_record_value:current_record_value['id'],reverse=True)
    current_snapshot_value=hashlib.sha256(json.dumps({'animation_id':current_animation_identifier,'animation_version':current_animation_version,'records':current_record_values},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if (current_offset_value and current_query_record.get('snapshot')!=current_snapshot_value) or ('snapshot' in current_query_record and current_query_record['snapshot']!=current_snapshot_value):raise ValueError('앵커 이력이 변경됐습니다. 처음부터 다시 조회하세요.')
    current_page_values=current_record_values[current_offset_value:current_offset_value+current_limit_value]
    current_next_offset=current_offset_value+len(current_page_values)
    return {'records':current_page_values,'total':len(current_record_values),'offset':current_offset_value,'next_offset':current_next_offset if current_next_offset<len(current_record_values) else None,'snapshot':current_snapshot_value,'note':'과거 좌표 검수 이력 요약입니다. 현재 등록 앵커·문서 적용 여부와 일치하지 않을 수 있습니다.'}
