"""모델 준비 상태와 서비스별 게이트웨이 명령을 연결한다."""
def execute_model_preparation_command(current_service_name, current_command_name, current_payload_record, execute_remote_management_command):
    """대기열 모델의 준비 상태를 공용 다운로드 컨트롤 계약에 맞춘다."""
    from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, inspect_registered_model_operation
    current_command_names = MANAGEMENT_SERVICE_COMMANDS.get(current_service_name, ())
    current_prepare_allowed = inspect_registered_model_operation(current_service_name, current_command_names, 'prepare') is not None
    if not current_prepare_allowed and current_command_name == 'prepare':
        raise ValueError('현재 서비스 정책상 모델 다운로드가 중단되었습니다.')
    current_audio_services = ('music-heartmula', 'sfx-dasheng-audiogen')
    if current_service_name in current_audio_services and current_command_name == 'prepare':
        return execute_remote_management_command(current_service_name, 'download-model', {})
    current_result_record = execute_remote_management_command(current_service_name, current_command_name, current_payload_record)
    if not current_prepare_allowed and current_command_name == 'model-status':
        current_result_record = {**current_result_record, 'generation_ready': False, 'can_prepare': False, 'prepare_blocked_reason': '현재 서비스 정책상 모델 다운로드가 중단되었습니다.'}
    if current_service_name not in ('wan22-fun-control', *current_audio_services) or current_command_name != 'model-status':
        return current_result_record
    if current_service_name in current_audio_services:
        current_file_status = execute_remote_management_command(current_service_name, 'download-model-status', {})
        current_original_ready = current_result_record['ready']
        current_result_record = {**current_file_status, 'generation_ready': current_original_ready,
                                 'ready': current_file_status['ready'] or current_result_record.get('artifacts_ready', False) or current_original_ready,
                                 'message': current_file_status['message'] + ' · ' + current_result_record['message']}
    current_history_record = execute_remote_management_command(current_service_name, 'history', {})
    current_prepare_records = [current_job_record for current_job_record in current_history_record.get('records', [])
                               if current_job_record.get('request', {}).get('action') == 'prepare'
                               and (current_service_name != 'wan22-fun-control' or current_job_record.get('request', {}).get('model_profile', 'wan22-14b') == 'wan22-14b')]
    current_active_records = [current_job_record for current_job_record in current_prepare_records
                              if current_job_record.get('status', {}).get('status') in ('queued', 'running')]
    current_selected_record = (current_active_records or current_prepare_records or [None])[0]
    if current_selected_record:
        current_state_name = current_selected_record.get('status', {}).get('status', 'unknown')
        current_state_label = {'queued': '대기 중', 'running': '진행 중', 'completed': '완료', 'failed': '실패', 'cancelled': '취소됨'}.get(current_state_name, current_state_name)
        current_result_record['message'] += f' · 최근 모델 준비: {current_state_label}'
        if current_result_record.get('preparation_status') != 'running':
            current_result_record['preparation_status'] = current_state_name
        if current_service_name == 'wan22-fun-control' and current_state_name in ('failed', 'cancelled'):
            # 파일은 남아 있어도 ROCm 설치·검증이 실패했을 수 있으므로 재시도를 허용한다.
            current_result_record['ready'] = False
    return current_result_record


def execute_wan13_model_command(current_command_name, current_payload_record, execute_remote_management_command):
    """1.3B 다운로드는 기존 Fun Control 준비 대기열을 공유한다."""
    if current_command_name == 'prepare':
        raise ValueError('Wan 2.1 Fun Control 모델 준비 기능은 폐기되었습니다.')
    if current_command_name != 'model-status':
        raise ValueError('지원하지 않는 1.3B 모델 명령입니다.')
    from generators.wan_fun.wan13_model_assets import inspect_wan13_model_files
    current_file_record = inspect_wan13_model_files()
    current_history_record = execute_remote_management_command('wan22-fun-control', 'history', {})
    current_active_records = [current_job_record for current_job_record in current_history_record.get('records', [])
                              if current_job_record.get('request', {}).get('action') == 'prepare'
                              and current_job_record.get('status', {}).get('status') in ('queued', 'running')]
    current_prepare_state = current_active_records[0]['status']['status'] if current_active_records else 'idle'
    return {'ready': current_file_record['ready'], 'preparation_status': current_prepare_state,
            'message': '1.3B 모델·참조 인코더 해시 검증 완료' if current_file_record['ready'] else '1.3B 모델·참조 인코더 준비 필요',
            'can_prepare': False}
