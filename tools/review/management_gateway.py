"""GUI·CLI의 명령 계약과 HTTP 게이트웨이. 셸 명령을 실행하지 않는다."""
import io
import json
import re
from email.message import Message
from urllib.parse import urlsplit, parse_qs

MANAGEMENT_SERVICE_ROUTES = {'momask':'/momask-generator','qwen-2512':'/image-generation','qwen-2511':'/image-generation-2511'}
MANAGEMENT_COMMAND_ROUTES = {'generate':('POST','/jobs'),'prepare':('POST','/jobs'),'status':('GET','/jobs/{id}'),'logs':('GET','/jobs/{id}/worker.log'),'history':('GET','/history'),'active':('GET','/active'),'model-status':('GET','/model-status'),'cancel':('POST','/cancel'),'history-reset':('POST','/history/reset'),'openpose-map':('POST','/openpose-map')}
MANAGEMENT_SERVICE_COMMANDS = {'momask':('generate','status','logs','history','cancel','history-reset','openpose-map'),'qwen-2512':('generate','prepare','status','logs','history','active','model-status','cancel','history-reset'),'qwen-2511':('generate','status','logs','history','active','model-status','cancel','history-reset')}


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
        from . import momask_jobs
    else:
        import momask_jobs
    resolve_management_command('momask',operation_command_name,command_payload_value)
    if operation_command_name=='generate':
        return momask_jobs.start_generation_job(command_payload_value['action'],command_payload_value['directions'])
    if operation_command_name=='history':
        return momask_jobs.list_generation_history()
    if operation_command_name=='status':
        return momask_jobs.read_generation_status(command_payload_value['id'])
    if operation_command_name=='logs':
        return (momask_jobs.resolve_generation_directory(command_payload_value['id'])/'worker.log').read_text(errors='replace')
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
                self.service_handler_values[service_command_name](GatewayRequestAdapter(current_http_handler,request_method_value,request_route_value,command_payload_value))
        except (ValueError,KeyError,TypeError,OSError) as gateway_error_value:
            response_payload_bytes=json.dumps({'error':str(gateway_error_value)},ensure_ascii=False).encode()
            current_http_handler.send_response(400);current_http_handler.send_header('Content-Type','application/json; charset=utf-8');current_http_handler.send_header('Content-Length',str(len(response_payload_bytes)));current_http_handler.end_headers();current_http_handler.wfile.write(response_payload_bytes)
        return True
