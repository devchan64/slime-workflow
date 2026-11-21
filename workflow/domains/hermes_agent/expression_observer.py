"""표정 생성기의 등록 프리셋을 제한된 목록으로 조회한다."""
import hashlib
import json
import re


def read_hermes_expression_catalog(current_query_record):
    """프리셋 ID와 한국어 이름만 제공하며 페이지 간 목록 변경을 검출한다."""
    from workflow.domains.image.expression_generation import load_expression_configuration
    if not isinstance(current_query_record,dict) or set(current_query_record)-{'query','offset','limit','snapshot'}:raise ValueError('표정 검색 입력 오류')
    current_query_text=current_query_record.get('query','')
    current_offset_value=current_query_record.get('offset',0)
    current_limit_value=current_query_record.get('limit',20)
    if not isinstance(current_query_text,str) or len(current_query_text)>100 or type(current_offset_value) is not int or current_offset_value<0 or type(current_limit_value) is not int or not 1<=current_limit_value<=30:raise ValueError('표정 검색 범위 오류')
    current_records_value=[]
    for current_entry_value in load_expression_configuration()['expressions']:
        current_identifier_value=current_entry_value['id']
        current_label_value=current_entry_value['label_ko']
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,63}',current_identifier_value) or len(current_label_value)>100 or any(ord(char)<32 for char in current_label_value):raise ValueError('표정 프리셋 형식 오류')
        current_records_value.append({'id':current_identifier_value,'label':current_label_value})
    current_filter_value=current_query_text.strip().casefold()
    current_records_value=[item for item in current_records_value if current_filter_value in (item['id']+' '+item['label']).casefold()]
    current_snapshot_value=hashlib.sha256(json.dumps({'query':current_filter_value,'records':current_records_value},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if (current_offset_value and current_query_record.get('snapshot')!=current_snapshot_value) or ('snapshot' in current_query_record and current_query_record['snapshot']!=current_snapshot_value):raise ValueError('표정 목록이 변경됐습니다. 처음부터 다시 조회하세요.')
    current_page_values=current_records_value[current_offset_value:current_offset_value+current_limit_value]
    current_next_offset=current_offset_value+len(current_page_values)
    return {'records':current_page_values,'total':len(current_records_value),'offset':current_offset_value,'next_offset':current_next_offset if current_next_offset<len(current_records_value) else None,'snapshot':current_snapshot_value,'note':'등록된 표정 이름과 ID입니다. 실제 결과 품질은 생성 후 확인하세요.'}
