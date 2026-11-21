"""Hermes 작업의 독립 검증 범위를 공용 회귀 등록부로 제한한다."""


def validate_hermes_verification_modules(hermes_verification_modules):
    if not isinstance(hermes_verification_modules, list) or len(hermes_verification_modules) > 5 or any(not isinstance(hermes_module_name, str) for hermes_module_name in hermes_verification_modules) or len(set(hermes_verification_modules)) != len(hermes_verification_modules):
        raise ValueError('검증 모듈은 중복 없는 문자열 목록 최대 5개여야 합니다.')
    if hermes_verification_modules:
        from workflow.tests.run_management_audit import MANAGEMENT_AUDIT_MODULES
        if any(hermes_module_name not in MANAGEMENT_AUDIT_MODULES for hermes_module_name in hermes_verification_modules):
            raise ValueError('공용 회귀 실행기에 등록된 검증 모듈만 지정할 수 있습니다.')
    return list(hermes_verification_modules)
