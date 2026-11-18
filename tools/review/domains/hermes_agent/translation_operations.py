"""Hermes의 프롬프트 번역 위임과 결과 확인."""
import os
from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from tools.review.common.management_gateway import execute_management_command
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.review.domains.hermes_agent.failure_observer import observe_hermes_failure_reason


def validate_hermes_translation_request(current_request_record):
    from tools.review.domains.translation.service import validate_translation_submission, TRANSLATION_PYTHON_PATH, TRANSLATION_MODEL_ROOT
    if not isinstance(current_request_record,dict):
        raise ValueError('번역 요청은 객체여야 합니다.')
    validate_translation_submission(current_request_record)
    if not TRANSLATION_PYTHON_PATH.is_file() or not (TRANSLATION_MODEL_ROOT/'manifest.json').is_file():
        raise ValueError('TranslateGemma 모델과 ROCm 환경을 먼저 준비하세요.')


def call_hermes_translation_service(current_command_name,current_payload_record):
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    return execute_management_command('prompt-translation',current_command_name,current_payload_record,current_gateway_address)


def submit_hermes_translation_request(current_request_identifier,current_request_record):
    return HermesDelegationStore().execute_service_delegation_once(current_request_identifier,'prompt-translation',current_request_record,
        lambda current_request_value:call_hermes_translation_service('translation-submit',current_request_value),validate_hermes_translation_request)


def read_hermes_translation_status(current_request_identifier):
    current_receipt_value=HermesDelegationStore().read_service_delegation(current_request_identifier,'prompt-translation')
    if current_receipt_value.get('state') != 'accepted':
        return {'receipt':current_receipt_value}
    current_job_value=call_hermes_translation_service('translation-status',{'id':current_receipt_value['job_id']})
    if not isinstance(current_job_value,dict) or current_job_value.get('id')!=current_receipt_value['job_id'] or not isinstance(current_job_value.get('status'),dict):
        raise ValueError('번역 상태 응답 형식 오류')
    current_status_value=current_job_value['status'].get('status')
    if current_status_value not in ('queued','running','completed','failed','cancelled','canceled','paused','unknown'):
        current_status_value='unknown'
    current_output_value={'status':current_status_value,'result':None, **observe_hermes_failure_reason(current_status_value,current_job_value['status'].get('error'))}
    if current_status_value=='completed':
        current_result_value=current_job_value.get('result')
        if not isinstance(current_result_value,dict) or not isinstance(current_result_value.get('text'),str) or len(current_result_value['text'])>12000:
            raise ValueError('번역 결과 형식 오류')
        current_checks_list=[]
        for current_check_name in ('term_checks','quality_checks'):
            current_check_values=current_result_value.get(current_check_name,[])
            if not isinstance(current_check_values,list) or len(current_check_values)>200:
                raise ValueError('번역 검사 결과 형식 오류')
            current_safe_checks=[]
            for current_check_value in current_check_values:
                if not isinstance(current_check_value,dict):
                    raise ValueError('번역 검사 항목 형식 오류')
                current_safe_value={}
                for current_field_name in ('source','target','status','source_count','target_count'):
                    current_field_value=current_check_value.get(current_field_name)
                    if isinstance(current_field_value,str):
                        current_safe_value[current_field_name]='검토 미완료' if current_field_name=='target' and current_field_value.startswith('검토 미완료:') else current_field_value[:1200]
                    elif type(current_field_value) is int and 0<=current_field_value<=100000:
                        current_safe_value[current_field_name]=current_field_value
                current_safe_checks.append(current_safe_value)
            current_checks_list.append(current_safe_checks)
        current_output_value['result']={'text':current_result_value['text'],'term_checks':current_checks_list[0],'quality_checks':current_checks_list[1],
            'note':'용어·조건 검사는 완전한 번역 품질 보증이 아닙니다. 결과와 검토 항목을 확인하세요.'}
    return {'receipt':current_receipt_value,'job':current_output_value}


def cancel_hermes_translation_request(current_request_identifier,current_job_identifier):
    current_receipt_value=HermesDelegationStore().read_service_delegation(current_request_identifier,'prompt-translation')
    if current_receipt_value.get('state')!='accepted' or current_receipt_value.get('job_id')!=current_job_identifier:
        raise ValueError('번역 접수와 확인한 작업 ID가 일치하지 않습니다.')
    current_cancel_value=call_hermes_translation_service('translation-cancel',{'id':current_job_identifier})
    if not isinstance(current_cancel_value,dict) or current_cancel_value.get('cancel_requested') is not True:
        raise ValueError('번역 중지 응답 형식 오류')
    return {'job_id':current_job_identifier,'cancel_requested':True,'status':current_cancel_value.get('status','unknown')}
