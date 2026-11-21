"""모델 준비 요청의 중복 접수와 불확실한 응답을 보존한다."""
from datetime import datetime, timezone

from workflow.common.generation_records import write_record_atomically
from workflow.common.model_management_catalog import MODEL_PREPARATION_SERVICES
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore, list_delegation_record_paths, check_delegation_record_exists, HERMES_DELEGATION_JOB_PATTERN, read_bounded_delegation_record


class HermesModelPreparationStore(HermesDelegationStore):
    """서비스별 준비 요청 영수증을 기존 위임 잠금과 함께 관리한다."""

    def validate_model_service_name(self, model_service_name):
        if not isinstance(model_service_name, str) or model_service_name not in {name for _, name in MODEL_PREPARATION_SERVICES}:
            raise ValueError('등록된 모델 서비스가 아닙니다.')

    def inspect_model_preparation_record(self, request_identifier_value, model_service_name, preparation_record_value):
        if (not isinstance(preparation_record_value, dict)
                or preparation_record_value.get('version') != 3
                or preparation_record_value.get('id') != request_identifier_value
                or preparation_record_value.get('service') != model_service_name):
            raise ValueError('모델 준비 서비스 또는 접수 기록이 일치하지 않습니다.')
        if preparation_record_value.get('state') == 'dispatching':
            return {'state': 'unknown', 'request_id':request_identifier_value, 'service': model_service_name,
                    'message': '기존 모델 준비 상태를 확인하세요. 자동 재접수하지 않습니다.'}
        if preparation_record_value.get('state') != 'accepted':
            raise ValueError('모델 준비 접수 상태 오류')
        current_result_value = {'state': 'accepted', 'request_id':request_identifier_value, 'service': model_service_name,
                                'message': '요청 응답을 받았습니다. 완료 여부는 모델 준비 상태에서 확인하세요.'}
        if 'preparation_status' in preparation_record_value:
            current_preparation_status=preparation_record_value['preparation_status']
            if current_preparation_status not in ('running','completed','idle','failed','queued'):
                raise ValueError('모델 준비 응답 상태 오류')
            current_result_value['preparation_status']=current_preparation_status
            current_result_value['message']+=' 접수 응답 당시 상태: '+{'running':'진행 중','completed':'완료','idle':'대기','failed':'실패','queued':'대기열'}[current_preparation_status]+'. 현재 상태는 별도로 확인하세요.'
        if 'job_id' in preparation_record_value:
            current_job_value = preparation_record_value['job_id']
            if not isinstance(current_job_value, str) or not HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_job_value):
                raise ValueError('모델 준비 작업 ID 오류')
            current_result_value['job_id'] = current_job_value
        return current_result_value

    def read_model_preparation_receipt(self, request_identifier_value, model_service_name):
        self.validate_model_service_name(model_service_name)
        with self.hold_delegation_storage_lock():
            current_record_path = self.resolve_delegation_record_path(request_identifier_value)
            if not check_delegation_record_exists(current_record_path):
                return {'state': 'not_found', 'request_id':request_identifier_value, 'service':model_service_name}
            current_record_value = read_bounded_delegation_record(current_record_path)
            return self.inspect_model_preparation_record(request_identifier_value, model_service_name, current_record_value)

    def list_model_preparation_receipts(self):
        """재시작 후에도 최근 모델 준비 접수 ID를 찾는다."""
        with self.hold_delegation_storage_lock():
            current_records_list = []
            for current_record_path in list_delegation_record_paths(self.delegation_storage_root):
                if current_record_path.is_symlink() or not current_record_path.is_file():
                    continue
                try:
                    current_request_identifier = current_record_path.stem
                    self.resolve_delegation_record_path(current_request_identifier)
                    current_record_value = read_bounded_delegation_record(current_record_path)
                    if not isinstance(current_record_value, dict) or current_record_value.get('version') != 3:
                        continue
                    current_service_name = current_record_value.get('service')
                    self.validate_model_service_name(current_service_name)
                    current_result_value = self.inspect_model_preparation_record(current_request_identifier, current_service_name, current_record_value)
                    current_updated_time = current_record_path.stat().st_mtime
                    current_records_list.append({**current_result_value, 'request_id':current_request_identifier,
                        'updated_at':datetime.fromtimestamp(current_updated_time, timezone.utc).isoformat(), '_sort_time':current_updated_time})
                except (OSError, ValueError, TypeError, KeyError):
                    continue
            current_records_list.sort(key=lambda current_record_value:(current_record_value['_sort_time'], current_record_value['request_id']), reverse=True)
            for current_record_value in current_records_list:
                current_record_value.pop('_sort_time')
            return {'records':current_records_list[:100], 'truncated':len(current_records_list)>100,
                    'note':'손상되거나 서비스를 확인할 수 없는 기록은 제외됩니다.'}

    def execute_model_preparation_once(self, request_identifier_value, model_service_name,
                                       preparation_validate_callback, preparation_submit_callback):
        """서버 정책을 확인한 뒤 기록하고, 응답이 유실되면 재실행하지 않는다."""
        self.validate_model_service_name(model_service_name)
        if not callable(preparation_validate_callback) or not callable(preparation_submit_callback):
            raise ValueError('모델 준비 검증과 접수 함수가 필요합니다.')
        with self.hold_delegation_storage_lock():
            current_record_path = self.resolve_delegation_record_path(request_identifier_value)
            if check_delegation_record_exists(current_record_path):
                current_record_value = read_bounded_delegation_record(current_record_path)
                current_result_value = self.inspect_model_preparation_record(request_identifier_value, model_service_name, current_record_value)
                return {**current_result_value, 'duplicate': True}
            preparation_validate_callback(model_service_name)
            current_record_value = {'version': 3, 'id': request_identifier_value,
                                    'service': model_service_name, 'state': 'dispatching'}
            write_record_atomically(current_record_path, current_record_value)
            current_response_value = preparation_submit_callback(model_service_name)
            if read_bounded_delegation_record(current_record_path)!=current_record_value:
                raise ValueError('모델 준비 중 접수 기록이 변경됐습니다. 기존 상태를 확인하고 자동 재접수하지 마세요.')
            current_status_value = current_response_value.get('preparation_status') if isinstance(current_response_value, dict) else None
            current_job_value = current_response_value.get('id') if isinstance(current_response_value, dict) else None
            if (current_status_value not in ('running', 'completed', 'idle', 'failed', 'queued')
                    and not (isinstance(current_job_value, str) and HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_job_value))):
                raise ValueError('모델 준비 응답을 확인할 수 없습니다. 자동 재접수하지 않습니다.')
            if current_status_value in ('running','completed','idle','failed','queued'):
                current_record_value['preparation_status']=current_status_value
            if isinstance(current_job_value, str) and HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_job_value):
                current_record_value['job_id'] = current_job_value
            current_record_value['state'] = 'accepted'
            write_record_atomically(current_record_path, current_record_value)
            return {**self.inspect_model_preparation_record(request_identifier_value, model_service_name, current_record_value), 'duplicate': False}
