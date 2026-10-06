"""기존 작가 HTTP 서비스의 Gradio 표준 UI 클라이언트."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.gradio_identifiers import build_generation_identifier
from tools.review.common.gradio_logs import create_copyable_log_textbox

WRITER_REQUEST_TIMEOUT=15
WRITER_MODE_LABELS={'prepare':'환경 준비','learn':'문서 학습','write':'작성 제안','deduplicate':'중복 검토'}
WRITER_STAGE_LABELS={'queued':'대기','preparing':'환경 준비','indexing':'학습','searching':'탐색','reasoning':'작성·중복 판단','review':'변경 검토 대기','completed':'완료','applied':'원본 적용 완료','failed':'실패','interrupted':'중단'}


def request_writer_service(review_server_port,current_route_path,current_request_values=None):
    """기존 HTTP 어댑터의 Host·Origin·CSRF 및 작업 서비스 계약을 유지한다."""
    current_server_address=f'http://127.0.0.1:{review_server_port}'
    current_request_headers={}
    current_request_body=None
    if current_request_values is not None:
        current_workspace_state=request_writer_service(review_server_port,'state')
        current_request_headers={'Origin':current_server_address,'X-Writer-Token':current_workspace_state['csrf_token'],'Content-Type':'application/json'}
        current_request_body=json.dumps(current_request_values).encode()
    current_http_request=Request(current_server_address+'/writer-agent/api/'+current_route_path,data=current_request_body,headers=current_request_headers)
    try:
        with urlopen(current_http_request,timeout=WRITER_REQUEST_TIMEOUT) as current_http_response:
            return json.load(current_http_response)
    except HTTPError as current_http_error:
        raise gr.Error(json.load(current_http_error).get('error','작가 서비스 요청 실패')) from current_http_error


def format_writer_detail(current_detail_record):
    """제안 내용은 Textbox·JSON에 표시해 문서의 HTML을 실행하지 않는다."""
    current_status_record=current_detail_record['status']
    current_proposal_record=current_detail_record.get('proposal') or {}
    current_application_record=current_detail_record.get('application')
    current_changes_text='\n\n'.join(current_change_record['path']+'\n'+current_change_record['diff'] for current_change_record in current_proposal_record.get('changes',[]))
    current_warning_text='\n'.join(current_proposal_record.get('warnings',[]))
    current_warning_text+='\n'+'\n'.join('보존: '+current_retained_record['path']+' · '+current_retained_record['reason'] for current_retained_record in current_proposal_record.get('retained',[]))
    current_apply_allowed=current_status_record['stage']=='review' and bool(current_changes_text) and not current_application_record
    return (current_detail_record,current_detail_record['id'],current_detail_record['job_path'],
            WRITER_STAGE_LABELS.get(current_status_record['stage'],current_status_record['stage'])+' · '+str(current_status_record.get('error') or current_status_record.get('summary') or current_status_record.get('progress') or ''),
            current_detail_record['request'],current_proposal_record.get('reason',''),current_proposal_record.get('coverage',{}),current_proposal_record.get('evidence',[]),current_changes_text,current_warning_text.strip(),current_detail_record.get('search',{}),current_detail_record.get('log',''),
            gr.update(interactive=current_apply_allowed),False,
            '제안과 차이를 검토하고 적용 확인을 선택하세요.' if current_apply_allowed else '변경 검토 대기 상태의 미적용 제안만 적용할 수 있습니다.',current_application_record or {})


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
        gr.Markdown('중복 검토는 입력을 비우면 전체 색인을 비교합니다. 삭제 후보는 아래에서 검토한 뒤 원본에 적용합니다.')
        gr.Markdown('### 3. 실행 기록')
        current_history_table=gr.Dataframe(headers=['ID','작업','상태','요약'],datatype='str',interactive=False,wrap=True)
        current_history_choice=gr.Dropdown(label='실행 기록 선택',choices=[],interactive=True)
        current_detail_button=gr.Button('결과 조회')
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
        with gr.Accordion('실행 로그',open=False):
            current_log_text=create_copyable_log_textbox(label='execution.log',interactive=False,lines=15)

        def refresh_writer_workspace(current_selected_identifier):
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
            return (current_workspace_paths,current_ready_text,current_job_rows,gr.update(choices=current_job_choices,value=current_selected_identifier if current_selected_identifier in [current_job_row[0] for current_job_row in current_job_rows] else None),gr.update(interactive=current_configured_flag and not current_busy_flag),gr.update(interactive=current_configured_flag and current_ready_flag and not current_busy_flag),*[gr.update(interactive=current_configured_flag and current_ready_flag and current_trained_flag and not current_busy_flag)]*2)

        current_workspace_outputs=[current_workspace_text,current_readiness_text,current_history_table,current_history_choice,current_prepare_button,current_learn_button,current_write_button,current_deduplicate_button]
        current_detail_outputs=[current_detail_state,current_identifier_text,current_detail_path,current_detail_status,current_request_json,current_reason_text,current_coverage_json,current_evidence_json,current_changes_text,current_warning_text,current_search_json,current_log_text,current_apply_button,current_apply_confirm,current_apply_notice,current_application_json]
        def read_writer_selection(current_selected_identifier):
            if not current_selected_identifier:raise gr.Error('실행 기록을 선택하세요.')
            return format_writer_detail(request_writer_service(review_server_port,'job?'+urlencode({'id':current_selected_identifier})))
        current_detail_button.click(read_writer_selection,current_history_choice,current_detail_outputs)
        current_history_choice.input(lambda: ({},False,gr.update(interactive=False),'결과 조회로 선택한 제안의 최신 내용을 확인하세요.'),outputs=[current_detail_state,current_apply_confirm,current_apply_button,current_apply_notice],queue=False)
        def submit_writer_action(current_action_mode,current_prompt_value):
            current_prompt_text='' if current_action_mode in ('prepare','learn') else current_prompt_value.strip()
            if current_action_mode=='write' and not current_prompt_text:raise gr.Error('아이디어나 작성 지시를 입력하세요.')
            current_job_record=request_writer_service(review_server_port,'jobs',{'mode':current_action_mode,'prompt':current_prompt_text})
            return '작업을 접수했습니다. 실행 기록에서 조회하세요.',*refresh_writer_workspace(current_job_record['id'])
        for current_action_mode,current_action_button in (('prepare',current_prepare_button),('learn',current_learn_button),('write',current_write_button),('deduplicate',current_deduplicate_button)):
            current_action_button.click(lambda current_prompt_value,current_mode_value=current_action_mode:submit_writer_action(current_mode_value,current_prompt_value),current_prompt_input,[current_feedback_text,*current_workspace_outputs],trigger_mode='once')
        def apply_writer_proposal(current_detail_record,current_confirm_value):
            if not current_confirm_value or not current_detail_record:raise gr.Error('결과를 조회하고 변경 검토 확인을 선택하세요.')
            request_writer_service(review_server_port,'apply',{'id':current_detail_record['id'],'proposal_hash':current_detail_record['status']['proposal_hash']})
            return read_writer_selection(current_detail_record['id'])
        current_apply_button.click(apply_writer_proposal,[current_detail_state,current_apply_confirm],current_detail_outputs,trigger_mode='once')
        def refresh_writer_progress(current_selected_identifier):
            current_workspace_updates=list(refresh_writer_workspace(current_selected_identifier))
            current_workspace_updates[2:4]=[gr.skip(),gr.skip()]
            if not current_selected_identifier:return [*current_workspace_updates,gr.skip(),gr.skip()]
            current_detail_record=request_writer_service(review_server_port,'job?'+urlencode({'id':current_selected_identifier}))
            current_status_record=current_detail_record['status']
            return [*current_workspace_updates,WRITER_STAGE_LABELS.get(current_status_record['stage'],current_status_record['stage'])+' · '+str(current_status_record.get('error') or current_status_record.get('summary') or current_status_record.get('progress') or ''),current_detail_record.get('log','')]
        gr.Timer(3).tick(refresh_writer_progress,current_history_choice,[*current_workspace_outputs,current_detail_status,current_log_text],queue=False,show_progress='hidden')
        current_refresh_button.click(refresh_writer_workspace,current_history_choice,current_workspace_outputs,queue=False)
        current_interface_blocks.load(lambda:refresh_writer_workspace(None),outputs=current_workspace_outputs)
    return current_interface_blocks


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
    build_writer_agent_interface(current_argument_values.review_port).queue().launch(server_name='127.0.0.1',server_port=current_argument_values.port,root_path=current_argument_values.root_path,allowed_paths=[])
