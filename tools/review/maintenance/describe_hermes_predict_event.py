"""실행 중인 Hermes 화면의 Gradio 이벤트 번호를 구성 정보와 대조한다."""
import argparse
import json
import re
from urllib.request import ProxyHandler, build_opener


def describe_hermes_predict_event(current_config_record, current_event_identifier):
    if type(current_event_identifier) is not int or not 0 <= current_event_identifier < 100000:
        raise ValueError('이벤트 번호는 0 이상 100000 미만 정수여야 합니다.')
    if not isinstance(current_config_record,dict) or not isinstance(current_config_record.get('dependencies'),list) or not isinstance(current_config_record.get('components'),list):
        raise ValueError('화면 구성 형식 오류')
    current_matches=[current_item for current_item in current_config_record['dependencies'] if isinstance(current_item,dict) and current_item.get('id')==current_event_identifier]
    if len(current_matches)!=1:raise ValueError('현재 화면에서 이벤트를 유일하게 찾을 수 없습니다.')
    current_event_record=current_matches[0]
    current_component_types={current_item.get('id'):current_item.get('type') for current_item in current_config_record['components'] if isinstance(current_item,dict) and type(current_item.get('id')) is int}
    current_target_records=[]
    for current_target_value in current_event_record.get('targets',[]):
        if isinstance(current_target_value,(list,tuple)) and len(current_target_value)==2 and current_target_value[0] is None and current_target_value[1]=='then':
            current_target_records.append({'component_id':None,'component_type':'chain','event':'then'})
            continue
        if not isinstance(current_target_value,(list,tuple)) or len(current_target_value)!=2 or type(current_target_value[0]) is not int or not isinstance(current_target_value[1],str) or not re.fullmatch(r'[A-Za-z_]{1,40}',current_target_value[1]):
            raise ValueError('이벤트 대상 형식 오류')
        current_component_type=current_component_types.get(current_target_value[0])
        if not isinstance(current_component_type,str) or not re.fullmatch(r'[a-z_]{1,40}',current_component_type):current_component_type='unknown'
        current_target_records.append({'component_id':current_target_value[0],'component_type':current_component_type,'event':current_target_value[1]})
    current_api_name=current_event_record.get('api_name')
    if not isinstance(current_api_name,str) or not re.fullmatch(r'[A-Za-z0-9_]{1,128}',current_api_name):current_api_name=None
    return {'event_id':current_event_identifier,'api_name':current_api_name,'targets':current_target_records,'note':'현재 GUI 설정에만 유효하며 실제 요청 내용이나 발생 원인은 제공하지 않습니다.'}


def main():
    current_parser_value=argparse.ArgumentParser(description=__doc__)
    current_parser_value.add_argument('event_id',type=int)
    current_argument_value=current_parser_value.parse_args()
    current_url_value='http://127.0.0.1:8770/management/frame/hermes-agent/config'
    with build_opener(ProxyHandler({})).open(current_url_value,timeout=10) as current_response_value:
        current_response_bytes=current_response_value.read(5000001)
    if len(current_response_bytes)>5000000:raise ValueError('화면 구성 크기 초과')
    print(json.dumps(describe_hermes_predict_event(json.loads(current_response_bytes),current_argument_value.event_id),ensure_ascii=False))


if __name__=='__main__':
    main()
