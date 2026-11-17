"""Hermes가 제공하는 주요 관리 기능의 범위와 영향 안내."""

HERMES_CAPABILITY_RECORDS = (
    {'command':'hermes-management-status', 'label':'관리 상태 조회', 'required':[], 'optional':[], 'effect':'read', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp','isolated_fixed_bridge'], 'result':'model_gpu_queue_and_recent_jobs', 'note':'GPU 관측은 캐시될 수 있다.'},
    {'command':'hermes-session-submit', 'label':'대화·격리 작업 접수', 'required':['session_id','request_id','prompt'], 'optional':['verification_modules'], 'effect':'enqueue', 'gpu':'exclusive', 'retry':'request_id', 'interfaces':['gui','mcp'], 'result':'hermes_job_id', 'note':'동일 ID와 입력의 재접수만 허용한다.'},
    {'command':'hermes-kimodo-proposal', 'label':'Kimodo 제안 읽기', 'required':['id'], 'optional':[], 'effect':'read', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'validated_untrusted_proposal', 'note':'제안은 실행되지 않는다.'},
    {'command':'hermes-delegate-kimodo', 'label':'Kimodo 생성 위임', 'required':['request_id','request'], 'optional':[], 'effect':'enqueue', 'gpu':'queued', 'retry':'request_id_or_unknown', 'interfaces':['gui','mcp'], 'result':'receipt_and_job_id', 'note':'화면은 입력과 GPU 사용 확인 후 접수한다. 응답 불확실 시 재실행하지 않는다.'},
    {'command':'hermes-delegation-status', 'label':'위임 접수 확인', 'required':['request_id'], 'optional':[], 'effect':'read', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'receipt', 'note':'생성 작업을 실행하지 않는다.'},
    {'command':'hermes-delegation-job-status', 'label':'Kimodo 작업 상태', 'required':['request_id'], 'optional':[], 'effect':'recovery_possible', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'receipt_and_job_status', 'note':'MCP는 접수 ID로 조회한다. 화면은 같은 Kimodo 상태 명령을 작업 ID로 조회하며 중단 작업 복구가 발생할 수 있다.'},
    {'command':'hermes-delegation-cancel', 'label':'위임 작업 중지', 'required':['request_id','job_id'], 'optional':[], 'effect':'cancel_request', 'gpu':'none', 'retry':'check_status', 'interfaces':['gui','mcp'], 'result':'cancel_request_status', 'note':'확인한 작업에 중지를 요청하며 실제 종료는 별도다.'},
    {'command':'hermes-diff', 'label':'격리 변경 전체 조회', 'required':['id','offset','limit'], 'optional':[], 'effect':'read', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'base64_byte_chunk', 'note':'종료된 작업의 바이트 조각을 읽는다.'},
)


HERMES_FIELD_SCHEMAS = {
    'session_id': {'type':'string', 'pattern':'^[0-9a-f]{32}$'},
    'request_id': {'type':'string', 'pattern':'^[A-Za-z0-9_-]{8,80}$'},
    'prompt': {'type':'string', 'minLength':1, 'maxLength':8000},
    'verification_modules': {'type':'array', 'items':{'type':'string'}, 'maxItems':5, 'note':'공용 회귀 모듈 허용 목록'},
    'id': {'type':'string', 'pattern':'^\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}-[a-f0-9]{8}$'},
    'job_id': {'type':'string', 'pattern':'^\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}-[a-f0-9]{8}$'},
    'offset': {'type':'integer', 'minimum':0},
    'limit': {'type':'integer', 'minimum':1, 'maximum':262144},
    'request': {'type':'object', 'validation':'generators.kimodo.contracts.validate_kimodo_request'},
}


def list_hermes_capability_catalog():
    """경로·방식은 공용 게이트웨이 등록을 원본으로 사용한다."""
    from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, MANAGEMENT_COMMAND_ROUTES
    current_catalog_records = []
    for current_capability_record in HERMES_CAPABILITY_RECORDS:
        current_command_name = current_capability_record['command']
        if current_command_name not in MANAGEMENT_SERVICE_COMMANDS['hermes-agent']:
            raise ValueError('등록되지 않은 Hermes 관리 명령: ' + current_command_name)
        current_method_value, current_route_suffix = MANAGEMENT_COMMAND_ROUTES[current_command_name]
        current_field_names = current_capability_record['required'] + current_capability_record['optional']
        current_payload_schema = {'type':'object', 'required':current_capability_record['required'], 'properties':{current_field_name:HERMES_FIELD_SCHEMAS[current_field_name] for current_field_name in current_field_names}, 'additionalProperties':False}
        current_catalog_records.append({**current_capability_record, 'payload_schema':current_payload_schema, 'service':'hermes-agent', 'method':current_method_value, 'route':'/hermes-agent' + current_route_suffix})
    return {'version':1, 'records':current_catalog_records, 'note':'표시된 인터페이스는 실제 연결 범위이며 별도 사용자 인증·역할 권한 체계를 의미하지 않는다. 각 명령의 입력 검증과 확인은 기존 서비스 및 클라이언트가 수행한다.'}
