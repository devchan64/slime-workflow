"""작가 에이전트의 설정·학습·작성·중복 검토 명령."""
import argparse
import json
from pathlib import Path
from .documents import DEFAULT_WORKSPACE_CONFIG,load_workspace_config,save_yaml_document
from .jobs import create_writer_job,execute_writer_job
from .management import WriterAgentManager


def run_writer_command():
    current_argument_parser=argparse.ArgumentParser(description=__doc__)
    current_argument_parser.add_argument('--config',type=Path,default=DEFAULT_WORKSPACE_CONFIG)
    current_command_parsers=current_argument_parser.add_subparsers(dest='command_name',required=True)
    current_config_parser=current_command_parsers.add_parser('configure')
    current_config_parser.add_argument('--document-root',type=Path,required=True)
    current_config_parser.add_argument('--state-root',type=Path,required=True)
    current_config_parser.add_argument('--write-root',action='append',required=True)
    current_config_parser.add_argument('--exclude-root',action='append',default=[])
    current_config_parser.add_argument('--protect-path',action='append',default=[])
    for current_command_name in ('learn','write','deduplicate'):
        current_job_parser=current_command_parsers.add_parser(current_command_name)
        current_job_parser.add_argument('--prompt',default='')
    current_show_parser=current_command_parsers.add_parser('show')
    current_show_parser.add_argument('--job-id',required=True)
    current_argument_values=current_argument_parser.parse_args()
    if current_argument_values.command_name=='configure':
        if current_argument_values.config.exists():raise ValueError('기존 설정은 자동 덮어쓰지 않습니다.')
        current_config_values={'schema_version':1,'document_root':str(current_argument_values.document_root.resolve()),'state_root':str(current_argument_values.state_root.resolve()),'write_roots':current_argument_values.write_root,'excluded_roots':current_argument_values.exclude_root,'protected_paths':current_argument_values.protect_path}
        save_yaml_document(current_argument_values.config,current_config_values)
        try:load_workspace_config(current_argument_values.config)
        except Exception:
            current_argument_values.config.unlink()
            raise
        print(current_argument_values.config)
        return
    if current_argument_values.command_name=='show':
        print(json.dumps(WriterAgentManager(current_argument_values.config).read_writer_detail(current_argument_values.job_id),ensure_ascii=False,indent=2))
        return
    current_config_values=load_workspace_config(current_argument_values.config)
    current_job_identifier=create_writer_job(current_config_values,{'mode':current_argument_values.command_name,'prompt':current_argument_values.prompt})
    print(f'작업 ID: {current_job_identifier}',flush=True)
    execute_writer_job(current_argument_values.config,current_job_identifier)

if __name__=='__main__':run_writer_command()
