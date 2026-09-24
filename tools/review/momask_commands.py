"""웹과 동일한 경로에 MoMask 모션·로그·이력을 저장한다."""
from pathlib import Path
import argparse
import json
import sys
import time

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
from .management_gateway import execute_momask_command, MANAGEMENT_SERVICE_COMMANDS
from .momask_jobs import start_generation_job, cancel_generation_job, resolve_generation_directory, SUPPORTED_ACTION_NAMES, SUPPORTED_DIRECTION_NAMES, list_generation_history, read_generation_status, reset_generation_history


def execute_cli_command(command_argument_list=None):
    command_argument_parser = argparse.ArgumentParser(prog='python tools/manager.py command momask', description=__doc__)
    command_subparser_group = command_argument_parser.add_subparsers(dest='command', required=True)
    generate_argument_parser = command_subparser_group.add_parser('generate', help='모션 생성과 이력 저장')
    generate_argument_parser.add_argument('--action', choices=SUPPORTED_ACTION_NAMES, required=True)
    generate_argument_parser.add_argument('--directions', nargs='+', choices=SUPPORTED_DIRECTION_NAMES, default=list(SUPPORTED_DIRECTION_NAMES))
    generate_argument_parser.add_argument('--detach', action='store_true', help='백그라운드에서 계속 실행')
    for command_name_value in MANAGEMENT_SERVICE_COMMANDS['momask']:
        if command_name_value not in ('status','logs','cancel','openpose-map'):continue
        command_subparser_group.add_parser(command_name_value).add_argument('id')
    command_subparser_group.add_parser('history')
    command_subparser_group.add_parser('history-reset', help='누적 이력만 수동 초기화; 결과 파일 보존')
    command_argument_values = command_argument_parser.parse_args(command_argument_list)
    if command_argument_values.command == 'history':
        print(json.dumps(execute_momask_command('history',{}), ensure_ascii=False, indent=2))
        return 0
    if command_argument_values.command == 'history-reset':
        print(json.dumps(execute_momask_command('history-reset',{})))
        return 0
    if command_argument_values.command == 'generate':
        generation_record_value = execute_momask_command('generate',{'action':command_argument_values.action,'directions':command_argument_values.directions})
        generation_job_identifier = generation_record_value['id']
        print(json.dumps(generation_record_value, ensure_ascii=False), flush=True)
        generation_job_path = resolve_generation_directory(generation_job_identifier)
        print('기록 경로: '+str(generation_job_path), flush=True)
        if command_argument_values.detach:
            return 0
        generation_log_offset = 0
        try:
            while True:
                with (generation_job_path/'worker.log').open() as generation_log_handle:
                    generation_log_handle.seek(generation_log_offset)
                    print(generation_log_handle.read(), end='', flush=True)
                    generation_log_offset = generation_log_handle.tell()
                generation_status_value = json.loads((generation_job_path/'status.json').read_text())
                if generation_status_value['status'] != 'running':
                    print(json.dumps(generation_status_value, ensure_ascii=False))
                    return 0 if generation_status_value['status']=='completed' else 1
                time.sleep(1)
        except KeyboardInterrupt:
            execute_momask_command('cancel',{'id':generation_job_identifier})
            print('\n취소 요청을 기록했습니다.')
            return 130
    generation_job_path = resolve_generation_directory(command_argument_values.id)
    if command_argument_values.command == 'openpose-map':
        print(json.dumps(execute_momask_command('openpose-map',{'id':command_argument_values.id}),ensure_ascii=False))
    elif command_argument_values.command == 'cancel':
        print(json.dumps(execute_momask_command('cancel',{'id':command_argument_values.id})))
    elif command_argument_values.command == 'status':
        print(json.dumps(execute_momask_command('status',{'id':command_argument_values.id}),ensure_ascii=False,indent=2))
    else:
        print(execute_momask_command('logs',{'id':command_argument_values.id}))
    return 0
