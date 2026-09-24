"""Qwen GUI와 동일한 관리 API를 사용하는 통합 CLI 명령."""
import argparse
import base64
import json
from pathlib import Path
import re
import time
from urllib.parse import urlsplit
from .management_gateway import call_management_api, MANAGEMENT_SERVICE_ROUTES, MANAGEMENT_SERVICE_COMMANDS

REFERENCE_FILE_BYTE_LIMIT = 3_000_000



def execute_qwen_command(service_command_name, command_argument_list=None):
    command_argument_parser = argparse.ArgumentParser(prog=f'python3 tools/manager.py command {service_command_name}', description='웹 관리도구와 같은 생성·로그·이력을 사용하는 Qwen CLI. 관리도구 서버 실행이 필요합니다.')
    command_argument_parser.add_argument('--server-url', default='http://127.0.0.1:8770', help='로컬 관리도구 주소')
    command_subparser_group = command_argument_parser.add_subparsers(dest='command',required=True)
    generate_argument_parser = command_subparser_group.add_parser('generate',help='이미지 생성')
    prompt_argument_group = generate_argument_parser.add_mutually_exclusive_group(required=True)
    prompt_argument_group.add_argument('--prompt')
    prompt_argument_group.add_argument('--prompt-file',type=Path,help='UTF-8 프롬프트 파일')
    generate_argument_parser.add_argument('--width',type=int,default=1024)
    generate_argument_parser.add_argument('--height',type=int,default=1024)
    generate_argument_parser.add_argument('--steps',type=int,choices=(4,30),default=4)
    generate_argument_parser.add_argument('--seed',type=int,default=10107 if service_command_name=='qwen-2511' else 251204)
    generate_argument_parser.add_argument('--detach',action='store_true',help='생성 ID 출력 후 반환')
    if service_command_name=='qwen-2511':
        generate_argument_parser.add_argument('--reference',type=Path,action='append',default=[],help='512×512 RGB/불투명 RGBA PNG, 최대 3회 지정; 생략 시 텍스트 생성')
    for command_name_value in MANAGEMENT_SERVICE_COMMANDS[service_command_name]:
        if command_name_value not in ('status','logs','cancel'):continue
        command_subparser_group.add_parser(command_name_value).add_argument('id')
    for command_name_value in MANAGEMENT_SERVICE_COMMANDS[service_command_name]:
        if command_name_value not in ('history','active','model-status','history-reset'):continue
        command_subparser_group.add_parser(command_name_value)
    if service_command_name=='qwen-2512':
        command_subparser_group.add_parser('prepare',help='웹과 동일한 모델 준비 작업 시작')
    command_argument_values = command_argument_parser.parse_args(command_argument_list)
    server_base_address = command_argument_values.server_url.rstrip('/')
    server_address_parts = urlsplit(server_base_address)
    if server_address_parts.scheme!='http' or server_address_parts.hostname!='127.0.0.1' or server_address_parts.username or server_address_parts.password or server_address_parts.path or server_address_parts.query or server_address_parts.fragment:
        raise ValueError('관리도구 주소는 http://127.0.0.1:포트 형식이어야 합니다.')
    request_route_prefix = MANAGEMENT_SERVICE_ROUTES[service_command_name]
    def invoke_management_api(request_route_suffix, request_body_value=None, expect_json_response=True):
        return call_management_api(server_base_address,request_route_prefix+request_route_suffix,request_body_value,expect_json_response)
    if command_argument_values.command in ('generate','prepare'):
        generation_request_body = {'action':command_argument_values.command}
        if command_argument_values.command=='generate':
            generation_request_body.update(prompt=command_argument_values.prompt if command_argument_values.prompt is not None else command_argument_values.prompt_file.read_text(encoding='utf-8'),width=command_argument_values.width,height=command_argument_values.height,steps=command_argument_values.steps,seed=command_argument_values.seed)
            if service_command_name=='qwen-2511':
                if len(command_argument_values.reference)>3:
                    raise ValueError('참조 이미지는 최대 3장입니다.')
                reference_image_payloads=[]
                for reference_image_path in command_argument_values.reference:
                    if reference_image_path.stat().st_size>REFERENCE_FILE_BYTE_LIMIT:
                        raise ValueError('참조 이미지 크기 제한 초과')
                    reference_image_payloads.append(base64.b64encode(reference_image_path.read_bytes()).decode())
                generation_request_body['images']=reference_image_payloads
        generation_response_value = invoke_management_api('/jobs',generation_request_body)
        print(json.dumps(generation_response_value,ensure_ascii=False),flush=True)
        if command_argument_values.command=='prepare' or command_argument_values.detach:
            return 0
        generation_job_identifier = generation_response_value['id']
        previous_progress_record = None
        try:
            while True:
                generation_status_record = invoke_management_api('/jobs/'+generation_job_identifier)
                current_progress_record = (generation_status_record['status'],generation_status_record.get('progress'))
                if current_progress_record!=previous_progress_record:
                    print(json.dumps({'status':current_progress_record[0],'progress':current_progress_record[1]},ensure_ascii=False),flush=True)
                    previous_progress_record=current_progress_record
                if generation_status_record['status']!='running':
                    print(json.dumps(generation_status_record,ensure_ascii=False),flush=True)
                    return 0 if generation_status_record['status']=='completed' else 1
                time.sleep(1)
        except KeyboardInterrupt:
            print(json.dumps(invoke_management_api('/cancel',{'id':generation_job_identifier}),ensure_ascii=False))
            return 130
    if hasattr(command_argument_values,'id') and not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',command_argument_values.id):
        raise ValueError('생성 ID 형식 오류')
    if command_argument_values.command=='cancel':
        command_response_value=invoke_management_api('/cancel',{'id':command_argument_values.id})
    elif command_argument_values.command=='history-reset':
        command_response_value=invoke_management_api('/history/reset',{'action':'reset'})
    elif command_argument_values.command in ('status','logs'):
        command_response_value=invoke_management_api('/jobs/'+command_argument_values.id+('/worker.log' if command_argument_values.command=='logs' else ''),expect_json_response=command_argument_values.command!='logs')
    else:
        command_response_value=invoke_management_api('/'+command_argument_values.command)
    print(command_response_value if isinstance(command_response_value,str) else json.dumps(command_response_value,ensure_ascii=False,indent=2))
    return 0
