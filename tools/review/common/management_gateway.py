"""GUI·CLI의 명령 계약과 HTTP 게이트웨이. 셸 명령을 실행하지 않는다."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
import argparse
import base64
import time
import io
import json
import re
import urllib.error
import urllib.request
from email.message import Message
from urllib.parse import urlsplit, parse_qs

MANAGEMENT_SERVICE_ROUTES = {'tile-map':'/tile-map-generator','character-animation':'/character-animation','momask':'/momask-generator','qwen-2512':'/image-generation','qwen-2511':'/image-generation-2511'}
MANAGEMENT_COMMAND_ROUTES = {'resume':('POST','/resume'),'sprite-source':('POST','/sprite/source'),'sprite-save':('POST','/sprite/save'),'sprite-load':('POST','/sprite/load'),'catalog':('GET','/catalog'),'generate':('POST','/jobs'),'prepare':('POST','/jobs'),'status':('GET','/jobs/{id}'),'logs':('GET','/jobs/{id}/worker.log'),'history':('GET','/history'),'active':('GET','/active'),'model-status':('GET','/model-status'),'cancel':('POST','/cancel'),'history-reset':('POST','/history/reset'),'openpose-map':('POST','/openpose-map')}
MANAGEMENT_SERVICE_COMMANDS = {'tile-map':('catalog','generate','prepare','status','logs','history','active','model-status','cancel','history-reset'),'character-animation':('resume','sprite-source','sprite-save','sprite-load','catalog','generate','status','logs','history','active','cancel','history-reset'),'momask':('resume','generate','status','logs','history','cancel','history-reset','openpose-map'),'qwen-2512':('generate','prepare','status','logs','history','active','model-status','cancel','history-reset'),'qwen-2511':('generate','status','logs','history','active','model-status','cancel','history-reset')}


def resolve_management_command(service_command_name, operation_command_name, command_payload_value):
    if service_command_name not in MANAGEMENT_SERVICE_COMMANDS or operation_command_name not in MANAGEMENT_SERVICE_COMMANDS[service_command_name]:
        raise ValueError('지원하지 않는 관리 명령')
    if not isinstance(command_payload_value,dict):
        raise ValueError('명령 입력은 JSON 객체여야 합니다.')
    request_method_value, request_suffix_value = MANAGEMENT_COMMAND_ROUTES[operation_command_name]
    if '{id}' in request_suffix_value:
        generation_job_identifier=command_payload_value.get('id','')
        if not isinstance(generation_job_identifier,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',generation_job_identifier):
            raise ValueError('생성 ID 형식 오류')
        request_suffix_value=request_suffix_value.format(id=generation_job_identifier)
    if operation_command_name=='history' and 'page' in command_payload_value:
        request_suffix_value+='?page='+str(max(1,int(command_payload_value['page'])))
    return request_method_value, MANAGEMENT_SERVICE_ROUTES[service_command_name]+request_suffix_value


def identify_management_command(request_route_value, request_method_value, request_payload_value=None):
    request_url_parts=urlsplit(request_route_value)
    for service_command_name,service_route_prefix in MANAGEMENT_SERVICE_ROUTES.items():
        if not request_url_parts.path.startswith(service_route_prefix+'/'):
            continue
        request_route_suffix=request_url_parts.path[len(service_route_prefix):]
        for operation_command_name in MANAGEMENT_SERVICE_COMMANDS[service_command_name]:
            expected_method_value,expected_route_value=MANAGEMENT_COMMAND_ROUTES[operation_command_name]
            if expected_method_value!=request_method_value:
                continue
            request_match_value=re.fullmatch(re.escape(expected_route_value).replace(r'\{id\}',r'(?P<id>\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8})'),request_route_suffix)
            if request_match_value:
                command_payload_value=dict(request_payload_value or {})
                command_payload_value.update(request_match_value.groupdict())
                if operation_command_name=='generate' and command_payload_value.get('action')=='prepare':
                    operation_command_name='prepare'
                if operation_command_name=='history':
                    command_payload_value.update({key:values[0] for key,values in parse_qs(request_url_parts.query).items() if key=='page'})
                return service_command_name,operation_command_name,command_payload_value
    return None


def execute_momask_command(operation_command_name, command_payload_value):
    if __package__:
        from tools.review.domains.momask import momask_jobs
    else:
        import tools.review.domains.momask.momask_jobs as momask_jobs
    resolve_management_command('momask',operation_command_name,command_payload_value)
    if operation_command_name=='resume':
        return momask_jobs.resume_generation_job(command_payload_value['id'])
    if operation_command_name=='generate':
        return momask_jobs.start_generation_job(command_payload_value['action'],command_payload_value['directions'],command_payload_value.get('face',False))
    if operation_command_name=='history':
        return momask_jobs.list_generation_history()
    if operation_command_name=='status':
        return momask_jobs.read_generation_status(command_payload_value['id'])
    if operation_command_name=='logs':
        return (momask_jobs.resolve_generation_directory(command_payload_value['id'])/'worker.log').read_text(errors='replace')
    if operation_command_name=='openpose-map':
        from tools.review.domains.momask.openpose_maps import generate_openpose_maps
        if momask_jobs.read_generation_status(command_payload_value['id'])['status']!='completed':
            raise ValueError('완료된 생성 이력이 필요합니다.')
        return generate_openpose_maps(momask_jobs.resolve_generation_directory(command_payload_value['id']),command_payload_value.get('face',False))
    if operation_command_name=='cancel':
        return momask_jobs.cancel_generation_job(command_payload_value['id'])
    if operation_command_name=='history-reset':
        return momask_jobs.reset_generation_history()
    raise ValueError('지원하지 않는 로컬 명령')


class GatewayRequestAdapter:
    def __init__(self, original_request_handler, request_method_value, request_route_value, request_payload_value):
        self.original_request_handler=original_request_handler
        self.command=request_method_value
        self.path=request_route_value
        request_body_bytes=json.dumps(request_payload_value,ensure_ascii=False).encode()
        self.rfile=io.BytesIO(request_body_bytes)
        self.headers=Message()
        for request_header_name,request_header_value in original_request_handler.headers.items():
            if request_header_name.lower() not in ('content-type','content-length'):
                self.headers[request_header_name]=request_header_value
        self.headers['Content-Type']='application/json'
        self.headers['Content-Length']=str(len(request_body_bytes))

    def __getattr__(self, attribute_name_value):
        return getattr(self.original_request_handler,attribute_name_value)


class ManagementCommandGateway:
    def __init__(self, service_handler_values):
        self.service_handler_values=service_handler_values

    def handle(self, current_http_handler):
        gateway_request_path=urlsplit(current_http_handler.path).path
        gateway_envelope_request=gateway_request_path=='/management/command'
        legacy_command_match=identify_management_command(current_http_handler.path,current_http_handler.command)
        if not gateway_envelope_request and not legacy_command_match:
            return False
        try:
            expected_origin_value=f'http://127.0.0.1:{current_http_handler.server.server_port}'
            if current_http_handler.headers.get('Host')!=expected_origin_value.removeprefix('http://'):
                raise ValueError('허용하지 않는 Host')
            request_payload_value={}
            if current_http_handler.command=='POST':
                if current_http_handler.headers.get('Origin')!=expected_origin_value or current_http_handler.headers.get('Content-Type','').split(';')[0]!='application/json':
                    raise ValueError('동일 출처 JSON 요청만 허용합니다.')
                request_body_length=int(current_http_handler.headers.get('Content-Length','0'))
                if not 1<=request_body_length<=12_200_000:
                    raise ValueError('요청 크기 오류')
                def parse_unique_fields(request_field_pairs):
                    request_field_values={}
                    for request_field_name,request_field_value in request_field_pairs:
                        if request_field_name in request_field_values:raise ValueError('중복 요청 필드')
                        request_field_values[request_field_name]=request_field_value
                    return request_field_values
                request_payload_value=json.loads(current_http_handler.rfile.read(request_body_length),object_pairs_hook=parse_unique_fields)
            if gateway_envelope_request:
                if current_http_handler.command!='POST' or not isinstance(request_payload_value,dict) or set(request_payload_value)!={'service','command','payload'}:
                    raise ValueError('service·command·payload 명령 형식이 필요합니다.')
                service_command_name=request_payload_value['service'];operation_command_name=request_payload_value['command'];command_payload_value=request_payload_value['payload']
                if not isinstance(service_command_name,str) or not isinstance(operation_command_name,str):raise ValueError('명령 이름 오류')
            else:
                service_command_name,operation_command_name,command_payload_value=identify_management_command(current_http_handler.path,current_http_handler.command,request_payload_value)
            request_method_value,request_route_value=resolve_management_command(service_command_name,operation_command_name,command_payload_value)
            # 작업 파일 조회 이외의 임의 URL·프로그램 실행을 허용하지 않는다.
            if service_command_name=='momask' and operation_command_name=='logs':
                response_payload_bytes=execute_momask_command('logs',command_payload_value).encode()
                current_http_handler.send_response(200);current_http_handler.send_header('Content-Type','text/plain; charset=utf-8');current_http_handler.send_header('Content-Length',str(len(response_payload_bytes)));current_http_handler.end_headers();current_http_handler.wfile.write(response_payload_bytes)
            else:
                execute_management_command(service_command_name,operation_command_name,command_payload_value,gateway_request_handler=current_http_handler,service_handler_values=self.service_handler_values)
        except (ValueError,KeyError,TypeError,OSError) as gateway_error_value:
            response_payload_bytes=json.dumps({'error':str(gateway_error_value)},ensure_ascii=False).encode()
            current_http_handler.send_response(400);current_http_handler.send_header('Content-Type','application/json; charset=utf-8');current_http_handler.send_header('Content-Length',str(len(response_payload_bytes)));current_http_handler.end_headers();current_http_handler.wfile.write(response_payload_bytes)
        return True


MANAGEMENT_COMMAND_DESCRIPTIONS = {'tile-map':'타일 종류별 고정 기본·화풍과 사용자 지시로 생성 (관리 서버 필요)','character-animation':'등록 모션·캐릭터 기반 애니메이션 생성·이력·재생 결과 조회','momask': 'MoMask 생성·상태·로그·이력 조회·취소 (웹과 기록 공유)', 'qwen-2512': 'Qwen 2512 텍스트 이미지 생성 (관리 서버 필요)', 'qwen-2511': 'Qwen 2511 텍스트·1~3장 참조 이미지 생성 (관리 서버 필요)'}

def execute_management_command(service_command_name, operation_command_name, command_payload_value, server_base_address=None, *, gateway_request_handler=None, service_handler_values=None):
    request_method_value,request_route_value=resolve_management_command(service_command_name,operation_command_name,command_payload_value)
    if gateway_request_handler is not None:
        return service_handler_values[service_command_name](GatewayRequestAdapter(gateway_request_handler,request_method_value,request_route_value,command_payload_value))
    if service_command_name=='character-animation' and server_base_address is None:
        from tools.review.domains.character_animation.character_animation_jobs import execute_animation_command
        return execute_animation_command(operation_command_name,command_payload_value)
    if service_command_name=='momask' and server_base_address is None:
        return execute_momask_command(operation_command_name,command_payload_value)
    server_base_address=server_base_address or 'http://127.0.0.1:8770'
    return call_management_api(server_base_address,request_route_value,command_payload_value if request_method_value=='POST' else None,operation_command_name!='logs')


def execute_gateway_arguments(service_command_name, command_argument_list):
    command_argument_parser=argparse.ArgumentParser(prog=f'python3 tools/manager.py command {service_command_name}',description=MANAGEMENT_COMMAND_DESCRIPTIONS[service_command_name])
    command_argument_parser.add_argument('--server-url',help='HTTP 게이트웨이 주소. 생략 시 MoMask·character-animation은 로컬, Qwen은 127.0.0.1:8770')
    command_subparser_group=command_argument_parser.add_subparsers(dest='command',required=True)
    for operation_command_name in MANAGEMENT_SERVICE_COMMANDS[service_command_name]:
        operation_argument_parser=command_subparser_group.add_parser(operation_command_name)
        if service_command_name=='momask' and operation_command_name in ('generate','openpose-map'):
            operation_argument_parser.add_argument('--face',action=argparse.BooleanOptionalAction,default=False,help='ANNY 얼굴 5점 포함')
        if operation_command_name in ('sprite-source','sprite-save','sprite-load'):
            operation_argument_parser.add_argument('id')
            if operation_command_name=='sprite-save':operation_argument_parser.add_argument('--document-file',type=Path,required=True)
        if operation_command_name in ('status','logs','cancel','openpose-map','resume'):
            operation_argument_parser.add_argument('id')
        if operation_command_name=='generate':
            operation_argument_parser.add_argument('--detach',action='store_true',help='작업 ID 출력 후 반환')
            if service_command_name=='character-animation':
                operation_argument_parser.add_argument('--steps',type=int,choices=(4,30),default=None,help='4: Lightning, 30: 표준 생성 (기본 4)')
                operation_argument_parser.add_argument('--resolution',type=int,choices=(512,768,1024,1280),default=512)
                operation_argument_parser.add_argument('--speed',type=float,choices=(1,1.5,2,4),help='생성 배속. 기본 1, 2배는 절반 길이')
                operation_argument_parser.add_argument('--target-fps',type=int,help='초당 생성 장수. 원본 FPS 이하 정수 (기본 4)')
                operation_argument_parser.add_argument('--motion',required=True,help='catalog의 모션 ID')
                operation_argument_parser.add_argument('--character',required=True,help='catalog의 캐릭터 ID')
                operation_argument_parser.add_argument('--source',choices=('openpose','anny'),default='openpose')
                operation_argument_parser.add_argument('--directions',nargs='+',choices=('down_left','down_right','up_left','up_right'),default=['down_left','down_right','up_left','up_right'])
            elif service_command_name=='momask':
                operation_argument_parser.add_argument('--action',choices=('standing','deep_breath','stretch','walking'),required=True)
                operation_argument_parser.add_argument('--directions',nargs='+',choices=('down_left','down_right','up_left','up_right'),default=['down_left','down_right','up_left','up_right'])
            else:
                if service_command_name=='tile-map':operation_argument_parser.add_argument('--tile-type',choices=('rooftop','wall','ground'),required=True)
                if service_command_name=='tile-map':
                    operation_argument_parser.add_argument('--use-base-prompt',action=argparse.BooleanOptionalAction,default=True)
                    operation_argument_parser.add_argument('--use-style-prompt',action=argparse.BooleanOptionalAction,default=True)
                    operation_argument_parser.add_argument('--use-reference-style-prompt',action=argparse.BooleanOptionalAction,default=False)
                prompt_argument_group=operation_argument_parser.add_mutually_exclusive_group(required=True)
                prompt_argument_group.add_argument('--prompt')
                prompt_argument_group.add_argument('--prompt-file',type=Path,help='UTF-8 프롬프트 파일')
                operation_argument_parser.add_argument('--width',type=int,default=1024)
                operation_argument_parser.add_argument('--height',type=int,default=1024)
                operation_argument_parser.add_argument('--steps',type=int,choices=(4,30),default=4)
                operation_argument_parser.add_argument('--seed',type=int,default=10107 if service_command_name in ('qwen-2511','tile-map') else 251204)
                if service_command_name in ('qwen-2511','tile-map'):
                    operation_argument_parser.add_argument('--reference',type=Path,action='append',default=[],help='512×512 불투명 PNG, 최대 3장')
    command_argument_values=command_argument_parser.parse_args(command_argument_list)
    server_base_address=command_argument_values.server_url
    if server_base_address is not None:
        server_base_address=server_base_address.rstrip('/')
        server_address_parts=urlsplit(server_base_address)
        if server_address_parts.scheme!='http' or server_address_parts.hostname!='127.0.0.1' or server_address_parts.username or server_address_parts.password or server_address_parts.path or server_address_parts.query or server_address_parts.fragment:
            raise ValueError('관리도구 주소는 http://127.0.0.1:포트 형식이어야 합니다.')
    operation_command_name=command_argument_values.command
    command_payload_value={}
    if hasattr(command_argument_values,'face'):command_payload_value['face']=command_argument_values.face
    if hasattr(command_argument_values,'id'):
        command_payload_value['id']=command_argument_values.id
    if operation_command_name in ('sprite-source','sprite-save','sprite-load'):
        command_payload_value={'id':command_argument_values.id}
        if operation_command_name=='sprite-save':command_payload_value['document']=json.loads(command_argument_values.document_file.read_text())
    if operation_command_name=='history-reset':command_payload_value={'action':'reset'}
    if operation_command_name=='prepare':command_payload_value={'action':'prepare'}
    if operation_command_name=='generate':
        if service_command_name=='character-animation':
            command_payload_value={'motion':command_argument_values.motion,'character':command_argument_values.character,'source':command_argument_values.source,'directions':command_argument_values.directions}
            command_payload_value['resolution']=command_argument_values.resolution
            if command_argument_values.steps is not None:command_payload_value['steps']=command_argument_values.steps
            if command_argument_values.speed is not None:command_payload_value['speed']=command_argument_values.speed
            if command_argument_values.target_fps is not None:command_payload_value['target_fps']=command_argument_values.target_fps
        elif service_command_name=='momask':
            command_payload_value={'action':command_argument_values.action,'directions':command_argument_values.directions,'face':command_argument_values.face}
        else:
            command_payload_value={'action':'generate','prompt':command_argument_values.prompt if command_argument_values.prompt is not None else command_argument_values.prompt_file.read_text(encoding='utf-8'),'width':command_argument_values.width,'height':command_argument_values.height,'steps':command_argument_values.steps,'seed':command_argument_values.seed}
            if service_command_name=='tile-map':
                command_payload_value['tile_type']=command_argument_values.tile_type
                command_payload_value['use_base_prompt']=command_argument_values.use_base_prompt
                command_payload_value['use_style_prompt']=command_argument_values.use_style_prompt
                command_payload_value['use_reference_style_prompt']=command_argument_values.use_reference_style_prompt
                command_payload_value['user_prompt']=command_payload_value.pop('prompt')
            if service_command_name in ('qwen-2511','tile-map'):
                if len(command_argument_values.reference)>3:raise ValueError('참조 이미지는 최대 3장입니다.')
                command_payload_value['images']=[]
                for reference_image_path in command_argument_values.reference:
                    if reference_image_path.stat().st_size>3_000_000:raise ValueError('참조 이미지 크기 제한 초과')
                    command_payload_value['images'].append(base64.b64encode(reference_image_path.read_bytes()).decode())
    command_response_value=execute_management_command(service_command_name,operation_command_name,command_payload_value,server_base_address)
    print(command_response_value if isinstance(command_response_value,str) else json.dumps(command_response_value,ensure_ascii=False,indent=2),flush=True)
    if operation_command_name!='generate' or command_argument_values.detach:return 0
    generation_job_identifier=command_response_value['id']
    previous_status_text=None
    try:
        while True:
            generation_status_value=execute_management_command(service_command_name,'status',{'id':generation_job_identifier},server_base_address)
            current_status_text=json.dumps(generation_status_value,ensure_ascii=False)
            if current_status_text!=previous_status_text:
                print(current_status_text,flush=True)
                previous_status_text=current_status_text
            if generation_status_value['status']!='running':
                return 0 if generation_status_value['status']=='completed' else 1
            time.sleep(1)
    except KeyboardInterrupt:
        execute_management_command(service_command_name,'cancel',{'id':generation_job_identifier},server_base_address)
        print('취소 요청을 전달했습니다.',flush=True)
        return 130


def execute_gateway_cli(command_argument_list=None):
    management_argument_parser = argparse.ArgumentParser(description=__doc__)
    management_subparser_group = management_argument_parser.add_subparsers(dest='tool', required=True)
    command_argument_parser = management_subparser_group.add_parser('command', help='관리 명령 실행')
    command_argument_parser.add_argument('service', choices=MANAGEMENT_SERVICE_COMMANDS)
    command_argument_parser.add_argument('arguments', nargs=argparse.REMAINDER)
    help_argument_parser = management_subparser_group.add_parser('help', help='지원 명령과 사용법 조회')
    help_argument_parser.add_argument('service', nargs='?', choices=MANAGEMENT_SERVICE_COMMANDS)
    help_argument_parser.add_argument('arguments', nargs=argparse.REMAINDER)
    management_argument_values = management_argument_parser.parse_args(command_argument_list)
    if management_argument_values.tool == 'help':
        if not management_argument_values.service:
            management_argument_parser.print_help()
            for service_command_name, service_description_text in MANAGEMENT_COMMAND_DESCRIPTIONS.items():
                print(f'  {service_command_name}: {service_description_text}')
            print('\n예: python tools/manager.py help momask generate')
            return 0
        return execute_gateway_arguments(management_argument_values.service,management_argument_values.arguments+['--help'])
    return execute_gateway_arguments(management_argument_values.service,management_argument_values.arguments)


def call_management_api(server_base_address, request_route_path, request_body_value=None, expect_json_response=True):
    request_header_values = {'Origin':server_base_address}
    request_body_bytes = None
    if request_body_value is not None:
        request_body_bytes = json.dumps(request_body_value,ensure_ascii=False).encode()
        request_header_values['Content-Type']='application/json'
    command_envelope_parts=identify_management_command(request_route_path,'POST' if request_body_value is not None else 'GET',request_body_value)
    if command_envelope_parts is None:raise ValueError('지원하지 않는 관리 명령 경로')
    service_command_name,operation_command_name,command_payload_value=command_envelope_parts
    request_route_path='/management/command'
    request_body_bytes=json.dumps({'service':service_command_name,'command':operation_command_name,'payload':command_payload_value},ensure_ascii=False).encode()
    request_header_values['Content-Type']='application/json'
    management_request_value = urllib.request.Request(server_base_address+request_route_path, data=request_body_bytes, headers=request_header_values)
    try:
        with urllib.request.urlopen(management_request_value, timeout=30) as management_response_handle:
            response_body_text = management_response_handle.read().decode()
        return json.loads(response_body_text) if expect_json_response else response_body_text
    except urllib.error.HTTPError as management_http_error:
        response_error_text = management_http_error.read().decode(errors='replace')
        try:
            response_error_text=json.loads(response_error_text).get('error',response_error_text)
        except ValueError:
            pass
        raise ValueError(f'관리 API 오류 ({management_http_error.code}): {response_error_text}') from None
    except urllib.error.URLError as management_connection_error:
        raise ValueError(f'관리도구 서버에 연결할 수 없습니다: {server_base_address}. 서버 실행과 포트를 확인하세요.') from management_connection_error
