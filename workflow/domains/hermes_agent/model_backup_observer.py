"""Read-only, bounded backup observations for the isolated Hermes worker."""
from collections import Counter
import os

from workflow.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from workflow.common.management_gateway import execute_management_command


def observe_backup(command, model=None):
    address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
    if command == 'models':
        result = execute_management_command('model-downloads', 'backup-models', {}, address)
        models = result['models']
        if not isinstance(models, list):
            raise ValueError('모델 목록 응답 오류')
        return {'models': models[:100], 'truncated': len(models) > 100,
                'backup_available': not bool(result.get('backup_error')),
                'note': 'backup_present가 null이면 백업 유무를 확인하지 못한 상태입니다.'}
    if command == 'history':
        result = execute_management_command('model-downloads', 'backup-verify-history', {}, address)
        records = result['records']
        if not isinstance(records, list):
            raise ValueError('백업 이력 응답 오류')
        return {'records': records[:20]}
    if command == 'compare':
        if not isinstance(model, str) or not model or len(model) > 200 or '/' in model or '\\' in model or model in ('.', '..'):
            raise ValueError('모델 이름 오류')
        result = execute_management_command('model-downloads', 'backup-compare', {'model': model}, address)
        files = result['files']
        if not isinstance(files, list):
            raise ValueError('백업 비교 응답 오류')
        return {'model': model, 'comparison_basis': result['comparison_basis'], 'complete': result['complete'],
                'counts': dict(Counter(item.get('status', 'unknown') for item in files if isinstance(item, dict))),
                'source_error_count': len(result['source_errors']), 'backup_error_count': len(result['backup_errors']),
                'note': '크기와 수정 시각 비교는 내용 해시 검증이 아닙니다.'}
    raise ValueError('지원하지 않는 백업 조회')
