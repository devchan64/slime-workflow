"""기존 작가 HTTP 서비스의 Gradio 표준 UI 클라이언트."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time
from urllib.parse import urlencode,parse_qs

import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.gradio_identifiers import build_generation_identifier
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_logs import create_copyable_log_textbox, build_execution_logs

WRITER_REQUEST_TIMEOUT=15
WRITER_MODE_LABELS={'prepare':'환경 준비','learn':'문서 학습','write':'작성 제안','deduplicate':'중복 검토'}
WRITER_STAGE_LABELS={'queued':'대기','preparing':'환경 준비','indexing':'학습','searching':'탐색','reasoning':'작성·중복 판단','review':'변경 검토 대기','completed':'완료','applied':'원본 적용 완료','failed':'실패','interrupted':'중단'}


def request_writer_service(review_server_port,current_route_path,current_request_values=None):
    """공용 게이트웨이가 작가 세션 토큰과 기존 작업 경로를 유지한다."""
    if current_route_path=='state':
        return execute_remote_management_command('writer-agent','writer-state',{})
    if current_route_path.startswith('job?'):
        current_query_values=parse_qs(current_route_path.split('?',1)[1],strict_parsing=True)
        if set(current_query_values)!={'id'} or len(current_query_values['id'])!=1:
            raise gr.Error('작업 조회 인자 오류')
        return execute_remote_management_command('writer-agent','writer-detail',{'id':current_query_values['id'][0]})
    current_command_names={'jobs':'writer-submit','apply':'writer-apply'}
    if current_route_path not in current_command_names:
        raise gr.Error('지원하지 않는 작가 명령')
    return execute_remote_management_command('writer-agent',current_command_names[current_route_path],current_request_values)


def format_writer_detail(current_detail_record):
    """제안 내용은 Textbox·JSON에 표시해 문서의 HTML을 실행하지 않는다."""
    current_status_record=current_detail_record['status']
    current_proposal_record=current_detail_record.get('proposal') or {}
    current_application_record=current_detail_record.get('application')
    current_changes_text='\n\n'.join(current_change_record['path']+'\n'+current_change_record['diff'] for current_change_record in current_proposal_record.get('changes',[]))
    current_warning_text='\n'.join(current_proposal_record.get('warnings',[]))
    current_warning_text+='\n'+'\n'.join('보존: '+current_retained_record['path']+' · '+current_retained_record['reason'] for current_retained_record in current_proposal_record.get('retained',[]))
    current_apply_allowed=current_status_record['stage']=='review' and bool(current_status_record.get('proposal_hash')) and bool(current_changes_text) and not current_application_record
    return (current_detail_record,current_detail_record['id'],current_detail_record['job_path'],
            WRITER_STAGE_LABELS.get(current_status_record['stage'],current_status_record['stage'])+' · '+str(current_status_record.get('error') or current_status_record.get('summary') or current_status_record.get('progress') or ''),
            current_detail_record['request'],current_proposal_record.get('reason',''),current_proposal_record.get('coverage',{}),current_proposal_record.get('evidence',[]),current_changes_text,current_warning_text.strip(),current_detail_record.get('search',{}),current_detail_record.get('log',''),
            gr.update(interactive=False),False,
            '제안과 차이를 검토하고 적용 확인을 선택하세요.' if current_apply_allowed else '제안 해시가 없어 적용할 수 없습니다. 결과를 다시 조회하세요.' if current_status_record['stage']=='review' and not current_status_record.get('proposal_hash') else '변경 검토 대기 상태의 미적용 제안만 적용할 수 있습니다.',current_application_record or {})


def build_writer_agent_interface(review_server_port):
    with gr.Blocks(title='작가 AI 에이전트') as current_interface_blocks:
        gr.Markdown('## 작가 AI 에이전트\n문서 학습·작성 제안·변경 검토·실행 기록을 관리합니다.')
        current_detail_state=gr.State({})
        current_feedback_text=gr.Textbox(label='작업 안내',interactive=False)
        gr.Markdown('### 1. 문서 학습\n원문을 바꾸지 않고 검색용 색인을 만듭니다. 문서를 수정한 뒤 학습을 갱신하세요.')
        current_workspace_text=create_copyable_log_textbox(label='문서·색인·기록 경로',interactive=False,lines=3)
        current_readiness_text=gr.Textbox(label='준비 상태',interactive=False)
        with gr.Row():
            current_prepare_button=gr.Button('환경 준비',interactive=False)
            current_learn_button=gr.Button('학습 · 색인 갱신',interactive=False)
            current_refresh_button=gr.Button('새로고침')
        gr.Markdown('### 2. 아이디어와 작성 지시')
        current_prompt_input=gr.Textbox(label='추가하고 싶은 내용이나 정리할 범위',lines=4,max_length=6000)
        with gr.Row():
            current_write_button=gr.Button('관련 문서 탐색 · 작성 제안',variant='primary',interactive=False)
            current_deduplicate_button=gr.Button('중복 검토',interactive=False)
        current_write_notice=gr.Markdown('아이디어나 작성 지시를 입력하세요. 준비 상태도 확인하세요.')
        gr.Markdown('중복 검토는 입력을 비우면 전체 색인을 비교합니다. 삭제 후보는 아래에서 검토한 뒤 원본에 적용합니다.')
        gr.Markdown('### 3. 실행 기록')
        current_history_table=gr.Dataframe(headers=['ID','작업','상태','요약'],datatype='str',interactive=False,wrap=True)
        current_history_choice=gr.Dropdown(label='실행 기록 선택',choices=[],interactive=True)
        current_detail_button=gr.Button('결과 조회',interactive=False)
        current_detail_notice=gr.Markdown('실행 기록을 선택하면 결과를 조회할 수 있습니다.')
        current_identifier_text=build_generation_identifier('조회한 작업 ID')
        current_detail_status=gr.Textbox(label='선택 작업 상태',interactive=False)
        with gr.Accordion('기록 경로·실행 입력',open=False):
            current_detail_path=create_copyable_log_textbox(label='기록 폴더',interactive=False)
            current_request_json=gr.JSON(label='실행 입력')
        current_reason_text=gr.Textbox(label='변경 근거',interactive=False,lines=3)
        with gr.Accordion('검토 범위·탐색 근거',open=False):
            current_coverage_json=gr.JSON(label='검토 범위 · limited=true이면 일부 후보만 검토')
            current_evidence_json=gr.JSON(label='탐색 근거')
        current_changes_text=create_copyable_log_textbox(label='원본 변경 미리보기',interactive=False,lines=10)
        current_warning_text=gr.Textbox(label='경고·보존 판단',interactive=False,lines=3)
        current_apply_notice=gr.Markdown('결과 조회 후 변경 내용을 확인하세요.')
        current_apply_confirm=gr.Checkbox(label='표시된 변경을 검토했고 원본 적용에 동의합니다.',value=False)
        current_apply_button=gr.Button('확인한 변경을 원본에 적용',interactive=False)
        current_application_json=gr.JSON(label='적용 결과')
        with gr.Accordion('검색 결과',open=False):
            current_search_json=gr.JSON(label='검색 결과')
        current_log_text,current_log_refresh,current_log_panel=build_execution_logs(
            '선택한 작업의 execution.log를 표시합니다. 자동 갱신을 끄면 현재 내용을 유지합니다. 결과 조회는 선택한 기록을 새로 불러옵니다.',current_log_label='execution.log')

        def refresh_writer_workspace(current_selected_identifier,current_prompt_text=''):
            current_workspace_record=request_writer_service(review_server_port,'state')
            current_job_records=current_workspace_record.get('jobs',[])
            current_busy_flag=bool(current_workspace_record.get('active_job'))
            current_configured_flag=current_workspace_record.get('configured',False)
            current_ready_flag=current_workspace_record.get('ready',False)
            current_trained_flag=current_workspace_record.get('trained',False)
            current_workspace_paths='\n'.join(str(current_workspace_record.get(current_path_key,'')) for current_path_key in ('document_root','index_path','state_root')) if current_configured_flag else str(current_workspace_record.get('config_path',''))
            current_ready_text='실행 중인 작업 완료 후 사용할 수 있습니다.' if current_busy_flag else '운영자가 문서 폴더를 연결해야 합니다.' if not current_configured_flag else '환경 준비를 실행하세요.' if not current_ready_flag else '첫 학습을 실행하세요.' if not current_trained_flag else '색인 있음 · 원문을 수정했다면 학습을 갱신하세요.'
            current_job_rows=[[current_job_record['id'],WRITER_MODE_LABELS.get(current_job_record['mode'],current_job_record['mode']),WRITER_STAGE_LABELS.get(current_job_record['stage'],current_job_record['stage']),current_job_record.get('summary') or current_job_record.get('error') or ''] for current_job_record in current_job_records]
            current_job_choices=[(current_job_row[1]+' · '+current_job_row[2]+' · '+current_job_row[0],current_job_row[0]) for current_job_row in current_job_rows]
            return (current_workspace_paths,current_ready_text,current_job_rows,gr.update(choices=current_job_choices,value=current_selected_identifier if current_selected_identifier in [current_job_row[0] for current_job_row in current_job_rows] else None),gr.update(interactive=current_configured_flag and not current_busy_flag),gr.update(interactive=current_configured_flag and current_ready_flag and not current_busy_flag),gr.update(interactive=current_configured_flag and current_ready_flag and current_trained_flag and not current_busy_flag and bool(current_prompt_text.strip())),gr.update(interactive=current_configured_flag and current_ready_flag and current_trained_flag and not current_busy_flag),current_ready_text if not (current_configured_flag and current_ready_flag and current_trained_flag and not current_busy_flag) else '작성 제안을 요청할 수 있습니다.' if current_prompt_text.strip() else '아이디어나 작성 지시를 입력하세요.',gr.update(interactive=any(current_job_row[0]==current_selected_identifier for current_job_row in current_job_rows)),'선택한 실행 기록의 결과를 조회합니다.' if any(current_job_row[0]==current_selected_identifier for current_job_row in current_job_rows) else '실행 기록을 선택하면 결과를 조회할 수 있습니다.')

        current_workspace_outputs=[current_workspace_text,current_readiness_text,current_history_table,current_history_choice,current_prepare_button,current_learn_button,current_write_button,current_deduplicate_button,current_write_notice,current_detail_button,current_detail_notice]
        current_detail_outputs=[current_detail_state,current_identifier_text,current_detail_path,current_detail_status,current_request_json,current_reason_text,current_coverage_json,current_evidence_json,current_changes_text,current_warning_text,current_search_json,current_log_text,current_apply_button,current_apply_confirm,current_apply_notice,current_application_json]
        def read_writer_selection(current_selected_identifier):
            if not current_selected_identifier:raise gr.Error('실행 기록을 선택하세요.')
            try:
                return format_writer_detail(request_writer_service(review_server_port,'job?'+urlencode({'id':current_selected_identifier})))
            except (ValueError,RuntimeError,OSError) as current_detail_error:
                current_failure_outputs=list(clear_writer_selection_detail())
                current_failure_outputs[1]=current_selected_identifier
                current_failure_outputs[3]='결과 조회 실패 · '+str(current_detail_error)
                current_failure_outputs[14]='조회에 실패하여 이전 제안과 적용 확인을 해제했습니다. 원인을 해결한 뒤 결과를 다시 조회하세요.'
                return tuple(current_failure_outputs)
        current_detail_button.click(read_writer_selection,current_history_choice,current_detail_outputs)
        def clear_writer_selection_detail():
            return ({},'','','결과 조회가 필요합니다.',{},'',{},[],'','',{},'',gr.update(interactive=False),False,'결과 조회로 선택한 제안의 최신 내용을 확인하세요.',{})
        current_history_choice.change(clear_writer_selection_detail,outputs=current_detail_outputs,queue=False)
        def submit_writer_action(current_action_mode,current_prompt_value):
            current_prompt_text='' if current_action_mode in ('prepare','learn') else current_prompt_value.strip()
            if current_action_mode=='write' and not current_prompt_text:raise gr.Error('아이디어나 작성 지시를 입력하세요.')
            current_job_record=request_writer_service(review_server_port,'jobs',{'mode':current_action_mode,'prompt':current_prompt_text})
            return '작업을 접수했습니다. 실행 기록에서 조회하세요.',*refresh_writer_workspace(current_job_record['id'],current_prompt_value)
        for current_action_mode,current_action_button in (('prepare',current_prepare_button),('learn',current_learn_button),('write',current_write_button),('deduplicate',current_deduplicate_button)):
            current_action_button.click(lambda current_prompt_value,current_mode_value=current_action_mode:submit_writer_action(current_mode_value,current_prompt_value),current_prompt_input,[current_feedback_text,*current_workspace_outputs],trigger_mode='once')
        def apply_writer_proposal(current_detail_record,current_confirm_value,current_selected_identifier):
            if not current_confirm_value or not current_detail_record:raise gr.Error('결과를 조회하고 변경 검토 확인을 선택하세요.')
            if current_detail_record.get('id')!=current_selected_identifier:
                raise gr.Error('선택한 작업이 변경되었습니다. 결과를 다시 조회하고 확인하세요.')
            if current_detail_record.get('status',{}).get('stage')!='review' or current_detail_record.get('application'):
                raise gr.Error('변경 검토 대기 상태의 미적용 제안만 적용할 수 있습니다.')
            if not (current_detail_record.get('proposal') or {}).get('changes') or not current_detail_record['status'].get('proposal_hash'):
                raise gr.Error('적용할 변경이나 제안 해시가 없습니다. 결과를 다시 조회하세요.')
            try:
                request_writer_service(review_server_port,'apply',{'id':current_detail_record['id'],'proposal_hash':current_detail_record['status']['proposal_hash']})
            except (ValueError,RuntimeError,OSError) as current_apply_error:
                current_failure_outputs=list(clear_writer_selection_detail())
                current_failure_outputs[1]=current_detail_record['id']
                current_failure_outputs[3]='적용 결과 확인 필요 · '+str(current_apply_error)
                current_failure_outputs[14]='적용 확인을 해제했습니다. 결과를 다시 조회해 적용 여부와 원인을 확인하세요. 원문 변경으로 거절됐다면 학습 후 새 제안을 만드세요.'
                return (*current_failure_outputs,'적용 결과 확인 필요 · '+str(current_apply_error)+' 결과를 다시 조회하세요. 원문 변경으로 거절됐다면 학습 후 새 제안을 만드세요.')
            return (*read_writer_selection(current_detail_record['id']),'변경을 적용했습니다.')
        def refresh_applied_history_labels(current_selected_identifier):
            current_workspace_updates=refresh_writer_workspace(current_selected_identifier)
            # 선택값은 유지하고 표시 이름만 갱신해 상세와 확인 상태를 다시 지우지 않는다.
            current_choice_update=dict(current_workspace_updates[3])
            current_choice_update.pop('value',None)
            return current_workspace_updates[2],current_choice_update
        current_apply_button.click(apply_writer_proposal,[current_detail_state,current_apply_confirm,current_history_choice],[*current_detail_outputs,current_feedback_text],trigger_mode='once').success(
            refresh_applied_history_labels,current_history_choice,[current_history_table,current_history_choice],queue=False)
        def update_writer_apply_readiness(current_detail_record,current_confirm_value,current_selected_identifier):
            current_matches_selection = bool(current_detail_record) and current_detail_record.get('id') == current_selected_identifier
            current_review_available = current_matches_selection and current_detail_record.get('status',{}).get('stage') == 'review' and bool(current_detail_record.get('status',{}).get('proposal_hash')) and not current_detail_record.get('application') and bool((current_detail_record.get('proposal') or {}).get('changes'))
            current_apply_enabled = bool(current_confirm_value and current_review_available)
            current_apply_message = '확인한 변경을 원본에 적용할 수 있습니다.' if current_apply_enabled else '제안과 차이를 검토하고 적용 확인을 선택하세요.' if current_review_available else '제안 해시가 없어 적용할 수 없습니다. 결과를 다시 조회하세요.' if current_matches_selection and current_detail_record.get('status',{}).get('stage')=='review' and not current_detail_record.get('status',{}).get('proposal_hash') else '변경 검토 대기 상태의 미적용 제안을 먼저 조회하세요.'
            return gr.update(interactive=current_apply_enabled),current_apply_message
        current_apply_confirm.change(update_writer_apply_readiness,[current_detail_state,current_apply_confirm,current_history_choice],[current_apply_button,current_apply_notice],queue=False)
        def refresh_writer_progress(current_selected_identifier,current_prompt_text,current_log_refresh_enabled=True):
            try:
                current_workspace_updates=list(refresh_writer_workspace(current_selected_identifier,current_prompt_text))
                # 자동 갱신 출력에서 목록 자체를 제외해 열린 선택 메뉴를 보존한다.
                current_workspace_updates=current_workspace_updates[:2]+current_workspace_updates[4:]
                if not current_selected_identifier:return [*current_workspace_updates,gr.skip(),gr.skip()]
                current_detail_record=request_writer_service(review_server_port,'job?'+urlencode({'id':current_selected_identifier}))
                current_status_record=current_detail_record['status']
                return [*current_workspace_updates,WRITER_STAGE_LABELS.get(current_status_record['stage'],current_status_record['stage'])+' · '+str(current_status_record.get('error') or current_status_record.get('summary') or current_status_record.get('progress') or ''),current_detail_record.get('log','') if current_log_refresh_enabled else gr.skip()]
            except (ValueError,RuntimeError,OSError) as current_progress_error:
                current_failure_message='상태 조회 실패: '+str(current_progress_error)+' · 다음 자동 갱신에서 다시 확인합니다.'
                return [gr.update(interactive=False) if isinstance(current_output_component,gr.Button)
                        else current_failure_message if current_output_component in (current_readiness_text,current_detail_status,current_write_notice,current_detail_notice)
                        else gr.skip() for current_output_component in current_progress_outputs]
        current_progress_outputs=[*current_workspace_outputs[:2],*current_workspace_outputs[4:],current_detail_status,current_log_text]
        current_progress_inputs=[current_history_choice,current_prompt_input,current_log_refresh]
        gr.Timer(3).tick(refresh_writer_progress,current_progress_inputs,current_progress_outputs,queue=False,show_progress='hidden')
        current_refresh_button.click(refresh_writer_workspace,[current_history_choice,current_prompt_input],current_workspace_outputs,queue=False)
        current_prompt_input.input(refresh_writer_progress,current_progress_inputs,current_progress_outputs,queue=False)
        current_history_choice.change(refresh_writer_progress,current_progress_inputs,current_progress_outputs,queue=False)
        current_interface_blocks.load(lambda:refresh_writer_workspace(None),outputs=current_workspace_outputs)
    return current_interface_blocks


from tools.review.ui.gradio.management_menu_app import compose_management_interface

if __name__=='__main__':
    current_argument_parser=argparse.ArgumentParser()
    current_argument_parser.add_argument('--port',type=int,required=True)
    current_argument_parser.add_argument('--review-port',type=int,required=True)
    current_argument_parser.add_argument('--owner-pid',type=int,required=True)
    current_argument_parser.add_argument('--root-path',default='/management/frame/writer-agent/')
    current_argument_values=current_argument_parser.parse_args()
    def monitor_owner_process():
        while os.getppid()==current_argument_values.owner_pid:time.sleep(1)
        os._exit(0)
    threading.Thread(target=monitor_owner_process,daemon=True).start()
    compose_management_interface(build_writer_agent_interface(current_argument_values.review_port),current_argument_values.review_port).queue().launch(server_name='127.0.0.1',server_port=current_argument_values.port,root_path=current_argument_values.root_path,allowed_paths=[])
