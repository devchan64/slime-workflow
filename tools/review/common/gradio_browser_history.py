"""브라우저가 기존 이력 API를 호출하는 도구의 표준 이력 컨트롤."""
import json
import gradio as gr
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT, describe_cleanup_blocked_jobs
from tools.review.common.gradio_identifiers import build_generation_identifier
from tools.review.common.gradio_logs import create_copyable_log_textbox
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_browser_confirmation import bind_browser_gpu_confirmation


def build_browser_history_controls(history_bridge_name, history_element_identifier, current_supported_actions=None, current_reset_target_handler=None, current_service_name=None):
    current_allowed_actions={"list","result","restore","logs","resume","cancel","delete","reset","prioritize"}
    current_enabled_actions=current_allowed_actions if current_supported_actions is None else set(current_supported_actions)
    if not current_enabled_actions<=current_allowed_actions or "list" not in current_enabled_actions:
        raise ValueError("이력 컨트롤의 지원 명령이 올바르지 않습니다.")
    with gr.Column(elem_id=history_element_identifier):
        gr.Markdown('## 생성 이력')
        current_history_refresh=gr.Checkbox(label='이력 자동 갱신',value=True)
        current_history_choice=gr.Dropdown(label='이력 선택 · ID·상태 검색',choices=[],interactive=True)
        current_history_identifier=build_generation_identifier('선택한 생성 ID')
        current_history_feedback=gr.Textbox(label='이력 안내',value='목록을 읽고 작업을 선택하세요.',interactive=False)
        current_history_buttons=[]
        with gr.Row():
            for current_action_name,current_action_label in [('list','이력 새로고침'),('logs','로그 조회')]:
                if current_action_name in current_enabled_actions:
                    current_history_buttons.append((gr.Button(current_action_label,interactive=current_action_name!='logs'),current_action_name))
        with gr.Row(equal_height=True):
            for current_action_name,current_action_label in [('result','결과 조회'),('restore','입력값 불러오기'),('resume','생성 재개'),('prioritize','우선 실행'),('cancel','작업 중지'),('delete','선택 이력 삭제')]:
                if current_action_name in current_enabled_actions:
                    current_history_buttons.append((gr.Button(current_action_label,interactive=False,min_width=0),current_action_name))
        with gr.Accordion('저장된 입력·기록',open=False):
            current_history_record=gr.JSON(label='선택한 생성 기록')
        with gr.Accordion('선택한 작업 로그',open=False,visible='logs' in current_enabled_actions):
            current_history_log=create_copyable_log_textbox(label='저장된 로그 · 최근 12,000자',lines=12,interactive=False)
        with gr.Accordion('이력 수동 정리',open=False,visible=bool(current_enabled_actions&{'delete','reset'})):
            gr.Markdown('현재 동작·버전의 편집 이력 목록만 초기화합니다.' if current_reset_target_handler else GENERATION_CLEANUP_SCOPE_TEXT)
            with gr.Row():
                for current_action_name,current_action_label in [('reset','생성 이력 초기화' if not current_reset_target_handler else '이력 목록 초기화')]:
                    if current_action_name in current_enabled_actions:current_history_buttons.append((gr.Button(current_action_label,interactive=current_action_name!='logs'),current_action_name))
        if not current_reset_target_handler:
            current_file_action=gr.Textbox(value='',visible=False)
            current_file_target=gr.JSON(value=None,visible=False)
            with gr.Group(visible=False) as current_file_panel:
                gr.Markdown('### 생성 작업 파일 삭제 확인\n'+GENERATION_CLEANUP_SCOPE_TEXT)
                current_file_display=gr.Textbox(label='삭제 대상',interactive=False)
                with gr.Row():
                    current_file_confirm=gr.Button('확인 · 파일과 이력 삭제',variant='stop')
                    current_file_cancel=gr.Button('취소')
        if current_reset_target_handler:
            with gr.Group(visible=False) as current_reset_confirmation:
                gr.Markdown('### 이력 목록 초기화 확인\n현재 동작·버전의 이력 목록만 비웁니다. 원본 파일과 편집 중 좌표는 유지됩니다. 모달 대신 인라인 확인 영역을 사용합니다.')
                current_reset_target=gr.Textbox(label='초기화 대상 동작·버전',interactive=False)
                with gr.Row():
                    current_reset_confirm=gr.Button('확인 · 이력 목록 초기화',variant='stop')
                    current_reset_cancel=gr.Button('취소 · 이력 유지')
        current_selection_buttons=[(current_action_button,current_action_name) for current_action_button,current_action_name in current_history_buttons if current_action_name in ('logs','result','restore','resume','prioritize','cancel','delete')]
        def update_browser_history_actions(current_selected_record):
            current_status_record=(current_selected_record or {}).get('status') or {}
            current_status_name=current_status_record.get('status') if isinstance(current_status_record,dict) else current_status_record
            current_result_available=bool(current_selected_record) and (bool(current_reset_target_handler) or current_status_name=='completed' or bool(current_selected_record.get('preview_ready')))
            current_enabled_states={'logs':bool(current_selected_record),'result':current_result_available,'restore':bool(current_selected_record),'resume':current_status_name in ('failed','cancelled'),'prioritize':current_status_name=='queued','cancel':current_status_name in ('running','queued'),'delete':current_status_name in ('completed','failed','cancelled','paused')}
            current_disabled_labels={'logs':'로그 조회 · 이력 선택','result':'결과 조회 · 결과 생성 후 선택','restore':'입력값 불러오기 · 이력 선택','resume':'생성 재개 · 실패·중지 작업 선택','prioritize':'우선 실행 · 대기 작업 선택','cancel':'작업 중지 · 실행·대기 작업 선택','delete':'선택 이력 삭제 · 완료·중지 후 가능'}
            current_action_labels={'logs':'로그 조회','result':'결과 조회','restore':'입력값 불러오기','resume':'생성 재개','prioritize':'우선 실행','cancel':'작업 중지','delete':'선택 이력 삭제'}
            return [gr.update(interactive=current_enabled_states[current_action_name],value=current_action_labels[current_action_name] if current_enabled_states[current_action_name] else current_disabled_labels[current_action_name]) for _,current_action_name in current_selection_buttons]
        current_history_record.change(update_browser_history_actions,current_history_record,[current_action_button for current_action_button,_ in current_selection_buttons],queue=False)
        current_history_outputs=[current_history_choice,current_history_identifier,current_history_record,current_history_log,current_history_feedback]
        def create_history_script(current_action_name, current_automatic_mode=False):
            current_bridge_key=json.dumps(history_bridge_name)
            current_state_key=json.dumps(history_element_identifier+'-refresh-state')
            return """async(currentSelectedId,currentRefreshEnabled,currentConfirmedTarget)=>{
                const currentNoChanges=()=>Array.from({length:5},()=>({__type__:'update'}));
                const currentAutomaticMode="""+json.dumps(current_automatic_mode)+""";
                const currentInspectMode="""+json.dumps(current_action_name=='inspect')+""";
                const currentBridgeFunction=window["""+current_bridge_key+"""];
                if(currentAutomaticMode&&(!currentRefreshEnabled||typeof currentBridgeFunction!=='function'))return currentNoChanges();
                const currentRefreshState=window["""+current_state_key+"""]??={revision:0,pending:0};
                if(currentRefreshState.pending&&currentAutomaticMode)return currentNoChanges();
                const currentConfirmedReset="""+json.dumps(current_action_name in ('delete','reset'))+""";
                if(currentConfirmedReset&&currentRefreshState.resetPending)return [...currentNoChanges().slice(0,4),'이력 초기화 중입니다. 완료 후 다시 확인하세요.'];
                if(currentConfirmedReset)currentRefreshState.resetPending=true;
                if(!currentAutomaticMode)currentRefreshState.revision++;
                const currentRequestRevision=currentRefreshState.revision;
                currentRefreshState.pending++;
                try{
                    const currentResultValues=await currentBridgeFunction("""+json.dumps(current_action_name)+""",currentSelectedId,currentConfirmedTarget);
                    if(currentRequestRevision!==currentRefreshState.revision)return currentNoChanges();
                    if(currentAutomaticMode&&!currentRefreshState.lookupFailed)currentResultValues[4]={__type__:'update'};
                    currentRefreshState.lookupFailed=false;
                    return currentResultValues;
                }catch(currentErrorValue){if(currentRequestRevision!==currentRefreshState.revision)return currentNoChanges();if(currentAutomaticMode){currentRefreshState.lookupFailed=true;return [{__type__:'update'},currentSelectedId||'',null,{__type__:'update'},'이력 상태 확인 실패: '+currentErrorValue.message+' · 자동 재확인 중'];}if(currentInspectMode)return [{__type__:'update'},currentSelectedId||'',null,'',currentErrorValue.message];return [{__type__:'update'},{__type__:'update'},{__type__:'update'},{__type__:'update'},currentErrorValue.message];}
                finally{currentRefreshState.pending--;if(currentConfirmedReset)currentRefreshState.resetPending=false;}
            }"""
        current_history_inputs=[current_history_choice,current_history_refresh]
        for current_action_button,current_action_name in current_history_buttons:
            if current_action_name=='reset' and current_reset_target_handler:
                current_action_button.click(fn=None,outputs=[current_reset_confirmation,current_reset_target,current_history_feedback],queue=False,js="()=>{try{const currentTargetValue=window["+json.dumps(current_reset_target_handler)+"]();return [{__type__:'update',visible:true},currentTargetValue,'대상 동작·버전과 목록 초기화 범위를 확인하세요.'];}catch(currentErrorValue){return [{__type__:'update',visible:false},'',currentErrorValue.message];}}")
                current_reset_confirm.click(fn=None,inputs=[*current_history_inputs,current_reset_target],outputs=[*current_history_outputs,current_reset_confirmation,current_reset_target],queue=False,js="async(currentSelectedId,currentRefreshEnabled,currentConfirmedTarget)=>{const currentResultValues=await ("+create_history_script('reset')+")(currentSelectedId,currentRefreshEnabled,currentConfirmedTarget);return [...currentResultValues,{__type__:'update',visible:false},''];}")
                current_reset_cancel.click(lambda:(gr.update(visible=False),'','이력 초기화를 취소했습니다.'),outputs=[current_reset_confirmation,current_reset_target,current_history_feedback],queue=False)
            elif current_action_name in ('delete','reset'):
                def open_file_confirmation(current_selected_identifier,current_requested_action=current_action_name):
                    if current_requested_action=='delete' and (not isinstance(current_selected_identifier,str) or not current_selected_identifier.strip()):
                        raise gr.Error('삭제할 작업을 선택하세요.')
                    current_target_value=current_selected_identifier or ''
                    if current_requested_action=='reset':
                        if not current_service_name:raise gr.Error('초기화 대상 조회 서비스가 연결되지 않았습니다.')
                        current_preview_record=execute_remote_management_command(current_service_name,'history-reset-preview',{})
                        if not current_preview_record['can_reset']:
                            current_blocked_summary = describe_cleanup_blocked_jobs(current_preview_record['blocked_jobs'])
                            current_blocked_message = '실행·대기 또는 최종 기록 저장 중인 작업은 삭제할 수 없습니다. '+current_blocked_summary+' · 작업 종료 후 다시 확인하세요.'
                            return gr.update(visible=False),'',{},'',current_blocked_message
                        return gr.update(visible=True),current_requested_action,current_preview_record,f"{current_service_name} · {current_preview_record['job_count']}개 작업 · {current_preview_record['notice']}",'삭제 범위를 확인한 뒤 확인 또는 취소를 선택하세요.'
                    return gr.update(visible=True),current_requested_action,{'id':current_target_value},current_target_value if current_requested_action=='delete' else '이 생성기의 전체 작업 파일','삭제 범위를 확인한 뒤 확인 또는 취소를 선택하세요.'
                current_action_button.click(open_file_confirmation,current_history_choice,[current_file_panel,current_file_action,current_file_target,current_file_display,current_history_feedback],queue=False,preprocess=False)
            elif current_action_name=='resume':
                current_prepare_resume="currentSelectedId=>{if(!currentSelectedId)throw Error('재개할 작업을 선택하세요.');return {id:currentSelectedId};}"
                current_execute_resume="currentSnapshotValue=>("+create_history_script('resume')+")(currentSnapshotValue.id,false,{confirmed:true})"
                bind_browser_gpu_confirmation(current_action_button,current_prepare_resume,current_execute_resume,[current_history_choice],current_history_outputs)
            else:
                current_action_button.click(fn=None,inputs=current_history_inputs,outputs=current_history_outputs,queue=False,js=create_history_script(current_action_name))
        if not current_reset_target_handler:
            current_file_confirm.click(fn=None,inputs=[*current_history_inputs,current_file_action,current_file_target],outputs=[*current_history_outputs,current_file_panel],queue=False,js="async(currentSelectedId,currentRefreshEnabled,currentAction,currentTarget)=>{if(!['delete','reset'].includes(currentAction))return [{__type__:'update'},{__type__:'update'},{__type__:'update'},{__type__:'update'},'삭제 확인이 만료되었습니다.',{__type__:'update',visible:false}];if(currentAction==='delete'&&currentSelectedId!==currentTarget?.id)return [{__type__:'update'},{__type__:'update'},{__type__:'update'},{__type__:'update'},'삭제 대상이 변경되었습니다.',{__type__:'update',visible:false}];const currentResult=await (currentAction==='delete'?("+create_history_script('delete')+"):("+create_history_script('reset')+"))(currentSelectedId,currentRefreshEnabled,{confirmed:true,id:currentAction==='delete'?currentTarget.id:currentTarget,preview:currentAction==='reset'?currentTarget:null});return [...currentResult,{__type__:'update',visible:false}];}")
            current_file_cancel.click(lambda:(gr.update(visible=False),''),outputs=[current_file_panel,current_file_action],queue=False)
            current_history_choice.input(lambda:(gr.update(visible=False),''),outputs=[current_file_panel,current_file_action],queue=False)
        current_history_choice.input(fn=None,inputs=current_history_inputs,outputs=current_history_outputs,queue=False,js=create_history_script('inspect'))
        current_history_timer=gr.Timer(5)
        current_history_timer.tick(fn=None,inputs=current_history_inputs,outputs=current_history_outputs,queue=False,js=create_history_script('list',True),show_progress='hidden')
