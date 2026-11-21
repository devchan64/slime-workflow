"""작가 자료 JSON의 지문과 연속 페이지 계약."""
import hashlib
import json
import re
from .jobs import JOB_IDENTIFIER_PATTERN


def validate_writer_material_request(current_request_record):
    if not isinstance(current_request_record,dict) or set(current_request_record)-{'job_id','section','offset','limit','snapshot'} or not {'job_id','section'}<=set(current_request_record):
        raise ValueError('작가 작업 ID와 자료 종류·페이지 필드만 허용합니다.')
    current_job_identifier=current_request_record['job_id']
    current_section_name=current_request_record['section']
    current_offset_value=current_request_record.get('offset',0)
    current_limit_value=current_request_record.get('limit',20000)
    current_snapshot_value=current_request_record.get('snapshot')
    if not isinstance(current_job_identifier,str) or not JOB_IDENTIFIER_PATTERN.fullmatch(current_job_identifier) or current_section_name not in ('search','proposal'):
        raise ValueError('작가 작업 ID 또는 자료 종류 오류')
    if type(current_offset_value) is not int or current_offset_value<0 or type(current_limit_value) is not int or not 1<=current_limit_value<=40000:
        raise ValueError('작가 자료 페이지 범위 오류')
    if current_snapshot_value is not None and (not isinstance(current_snapshot_value,str) or not re.fullmatch('[a-f0-9]{64}',current_snapshot_value)):
        raise ValueError('작가 자료 지문 오류')
    if current_offset_value>0 and current_snapshot_value is None:
        raise ValueError('다음 페이지에는 첫 조회의 snapshot이 필요합니다.')
    return current_job_identifier,current_section_name,current_offset_value,current_limit_value,current_snapshot_value


def build_writer_material_page(current_request_record,current_material_value):
    current_job_identifier,current_section_name,current_offset_value,current_limit_value,current_snapshot_value=validate_writer_material_request(current_request_record)
    if not isinstance(current_material_value,dict):raise ValueError('해당 작가 자료가 없습니다.')
    current_material_value=dict(current_material_value)
    current_material_value.pop('snapshot_hashes',None)
    current_material_hash_value=hashlib.sha256()
    current_material_encoder=json.JSONEncoder(ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    current_page_fragments=[]
    current_total_characters=0
    current_page_end=current_offset_value+current_limit_value
    try:
        for current_json_fragment in current_material_encoder.iterencode(current_material_value):
            # 인코더는 긴 문자열을 하나의 조각으로 반환할 수 있으므로 UTF-8 사본도 나누어 만든다.
            for current_fragment_start in range(0,len(current_json_fragment),65536):
                current_fragment_value=current_json_fragment[current_fragment_start:current_fragment_start+65536]
                current_fragment_end=current_total_characters+len(current_fragment_value)
                current_material_hash_value.update(current_fragment_value.encode('utf-8'))
                if current_total_characters<current_page_end and current_fragment_end>current_offset_value:
                    current_page_fragments.append(current_fragment_value[max(0,current_offset_value-current_total_characters):current_page_end-current_total_characters])
                current_total_characters=current_fragment_end
        current_material_hash=current_material_hash_value.hexdigest()
    except (TypeError,ValueError,UnicodeError,RecursionError) as current_material_error:
        raise ValueError('작가 자료를 JSON으로 표현할 수 없습니다.') from current_material_error
    if current_snapshot_value is not None and current_snapshot_value!=current_material_hash:
        raise ValueError('작가 자료가 변경됐습니다. 첫 페이지부터 다시 조회하세요.')
    if current_offset_value>current_total_characters:raise ValueError('작가 자료 페이지가 범위를 벗어났습니다.')
    current_next_offset=current_offset_value+current_limit_value
    return {'job_id':current_job_identifier,'section':current_section_name,'format':'json','snapshot':current_material_hash,'offset':current_offset_value,'total_characters':current_total_characters,'content':''.join(current_page_fragments),'next_offset':current_next_offset if current_next_offset<current_total_characters else None,'note':'원 서비스가 제공한 해당 레코드의 JSON을 순서대로 이어 붙여 읽습니다. 제안 적용이나 현재 문서 동일성은 확인하지 않습니다.'}
