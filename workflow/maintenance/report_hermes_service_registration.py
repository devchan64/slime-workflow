"""코드에 등록된 관리 서비스·연결·제한의 시점 보고서를 표준 출력에 작성한다."""
from datetime import datetime, timezone

from workflow.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS
from workflow.domains.hermes_agent.capabilities import list_hermes_capability_catalog, list_management_service_registration


def render_hermes_registration_report(current_timestamp_value):
    """기능 등록을 읽기만 하며 서비스 실행 가능성은 추정하지 않는다."""
    current_service_records = list_management_service_registration()['services']
    current_capability_records = list_hermes_capability_catalog()['records']
    current_command_count = sum(len(current_command_names) for current_command_names in MANAGEMENT_SERVICE_COMMANDS.values())
    current_report_lines = [
        '# Hermes 관리 서비스 등록 현황',
        '',
        f'- 생성 시각(UTC): {current_timestamp_value}',
        f'- 게이트웨이 서비스: {len(current_service_records)}개 · 서비스별 등록 명령 합계: {current_command_count}개 · Hermes 기능 명령: {len(current_capability_records)}개.',
        '- 코드 등록과 알려진 제한을 정리한 시점 기록이다. 등록이나 연결은 실행 권한·가용성·GPU 시험 또는 개별 명령의 입력·효과·오류 계약 검증을 뜻하지 않는다.',
        '- Hermes 연결은 서비스 단위의 관련 기능 목록이며 원 서비스 명령과 일대일로 대응하지 않는다. 알려진 제한이 없다는 표시는 완전한 제한 목록이라는 뜻이 아니다.',
    ]
    for current_service_record in current_service_records:
        current_command_text = ', '.join(f'`{current_command_name}`' for current_command_name in current_service_record['commands'])
        current_link_text = ', '.join(f'`{current_link_name}`' for current_link_name in current_service_record['hermes_links']) or '없음'
        current_report_lines.extend(['', f'## {current_service_record["service"]}', '', '- 등록 명령: '+current_command_text, '- Hermes 연결: '+current_link_text])
        for current_record_key, current_label_text, current_value_key in (('gateway_blocked','게이트웨이 차단','reason'), ('known_service_blocked','원 서비스 차단','reason'), ('conditional_limitations','확인된 조건부 제한','note')):
            current_limit_records = current_service_record[current_record_key]
            if current_limit_records:
                current_limit_text = '; '.join(f'`{current_limit_record["command"]}` {current_limit_record[current_value_key]}' for current_limit_record in current_limit_records)
                current_report_lines.append('- '+current_label_text+': '+current_limit_text)
    return '\n'.join(current_report_lines)+'\n'


if __name__ == '__main__':
    print(render_hermes_registration_report(datetime.now(timezone.utc).isoformat()), end='')
