"""관리도구 통합 CLI: command로 실행하고 help로 사용법을 조회한다."""
import argparse
import sys
from functools import partial
from review.qwen_commands import execute_qwen_command
from review.momask_commands import execute_cli_command

MANAGEMENT_COMMAND_HANDLERS = {'momask': execute_cli_command, 'qwen-2512': partial(execute_qwen_command,'qwen-2512'), 'qwen-2511': partial(execute_qwen_command,'qwen-2511')}
MANAGEMENT_COMMAND_DESCRIPTIONS = {'momask': 'MoMask 생성·상태·로그·이력 조회·취소 (웹과 기록 공유)', 'qwen-2512': 'Qwen 2512 텍스트 이미지 생성 (관리 서버 필요)', 'qwen-2511': 'Qwen 2511 텍스트·1~3장 참조 이미지 생성 (관리 서버 필요)'}


def execute_management_client(command_argument_list=None):
    management_argument_parser = argparse.ArgumentParser(description=__doc__)
    management_subparser_group = management_argument_parser.add_subparsers(dest='tool', required=True)
    command_argument_parser = management_subparser_group.add_parser('command', help='관리 명령 실행')
    command_argument_parser.add_argument('service', choices=MANAGEMENT_COMMAND_HANDLERS)
    command_argument_parser.add_argument('arguments', nargs=argparse.REMAINDER)
    help_argument_parser = management_subparser_group.add_parser('help', help='지원 명령과 사용법 조회')
    help_argument_parser.add_argument('service', nargs='?', choices=MANAGEMENT_COMMAND_HANDLERS)
    help_argument_parser.add_argument('arguments', nargs=argparse.REMAINDER)
    management_argument_values = management_argument_parser.parse_args(command_argument_list)
    if management_argument_values.tool == 'help':
        if not management_argument_values.service:
            management_argument_parser.print_help()
            for service_command_name, service_description_text in MANAGEMENT_COMMAND_DESCRIPTIONS.items():
                print(f'  {service_command_name}: {service_description_text}')
            print('\n예: python tools/manager.py help momask generate')
            return 0
        return MANAGEMENT_COMMAND_HANDLERS[management_argument_values.service](management_argument_values.arguments+['--help'])
    return MANAGEMENT_COMMAND_HANDLERS[management_argument_values.service](management_argument_values.arguments)


if __name__ == '__main__':
    try:
        sys.exit(execute_management_client())
    except (ValueError, OSError) as management_command_error:
        print(str(management_command_error), file=sys.stderr)
        sys.exit(1)
