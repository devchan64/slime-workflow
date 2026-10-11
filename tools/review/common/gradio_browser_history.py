"""브라우저가 기존 이력 API를 호출하는 도구의 표준 이력 컨트롤."""
import json
import gradio as gr
from tools.review.common.gradio_identifiers import build_generation_identifier
from tools.review.common.gradio_logs import create_copyable_log_textbox


def build_browser_history_controls(history_bridge_name, history_element_identifier, current_supported_actions=None, current_reset_target_handler=None):
    current_allowed_actions={"list","result","restore","logs","resume","cancel","delete","reset"}
    current_enabled_actions=current_allowed_actions if current_supported_actions is None else set(current_supported_actions)
    if not current_enabled_actions<=current_allowed_actions or "list" not in current_enabled_actions:
        raise ValueError("이력 컨트롤의 지원 명령이 올바르지 않습니다.")
    with gr.Column(elem_id=history_element_identifier):
        gr.Markdown('## 생성 이력')
        current_history_refresh=gr.Checkbox(label='이력 자동 갱신',value=True)
        current_history_choice=gr.Dropdown(label='이력 선택 · ID·상태 검색',choices=[],interactive=True)
        current_history_identifier=build_generation_identifier('선택한 생성 ID')
        current_history_feedback=gr.Textbox(label='이력 안내',value='목록을 읽고 작업을 선택하세요.',interactive=False)
        with gr.Row():
            current_history_buttons=[(gr.Button(current_action_label),current_action_name) for current_action_name,current_action_label in [('list','이력 새로고침'),('result','결과 조회'),('restore','입력값 불러오기'),('logs','로그 조회'),('resume','생성 재개'),('cancel','작업 중지')] if current_action_name in current_enabled_actions]
        with gr.Accordion('저장된 입력·기록',open=False):
            current_history_record=gr.JSON(label='선택한 생성 기록')
        with gr.Accordion('선택한 작업 로그',open=False,visible='logs' in current_enabled_actions):
            current_history_log=create_copyable_log_textbox(label='저장된 로그 · 최근 12,000자',lines=12,interactive=False)
        with gr.Accordion('이력 수동 정리',open=False,visible=bool(current_enabled_actions&{'delete','reset'})):
            gr.Markdown('목록에서만 제외합니다. 결과·입력·로그 파일은 유지됩니다. 실행 또는 대기 중인 작업은 정리할 수 없습니다.')
            with gr.Row():
                for current_action_name,current_action_label in [('delete','선택 이력 삭제'),('reset','이력 목록 초기화')]:
                    if current_action_name in current_enabled_actions:current_history_buttons.append((gr.Button(current_action_label),current_action_name))
        if current_reset_target_handler:
            with gr.Group(visible=False) as current_reset_confirmation:
                gr.Markdown('### 이력 목록 초기화 확인\n현재 동작·버전의 이력 목록만 비웁니다. 원본 파일과 편집 중 좌표는 유지됩니다. 모달 대신 인라인 확인 영역을 사용합니다.')
                current_reset_target=gr.Textbox(label='초기화 대상 동작·버전',interactive=False)
                with gr.Row():
                    current_reset_confirm=gr.Button('확인 · 이력 목록 초기화',variant='stop')
                    current_reset_cancel=gr.Button('취소 · 이력 유지')
        current_history_outputs=[current_history_choice,current_history_identifier,current_history_record,current_history_log,current_history_feedback]
        def create_history_script(current_action_name, current_automatic_mode=False):
            current_bridge_key=json.dumps(history_bridge_name)
            current_state_key=json.dumps(history_element_identifier+'-refresh-state')
            return """async(currentSelectedId,currentRefreshEnabled,currentConfirmedTarget)=>{
                const currentNoChanges=()=>Array.from({length:5},()=>({__type__:'update'}));
                const currentAutomaticMode="""+json.dumps(current_automatic_mode)+""";
                const currentBridgeFunction=window["""+current_bridge_key+"""];
                if(currentAutomaticMode&&(!currentRefreshEnabled||typeof currentBridgeFunction!=='function'))return currentNoChanges();
                const currentRefreshState=window["""+current_state_key+"""]??={revision:0,pending:0};
                if(currentRefreshState.pending&&currentAutomaticMode)return currentNoChanges();
                const currentConfirmedReset="""+json.dumps(current_action_name=='reset' and bool(current_reset_target_handler))+""";
                if(currentConfirmedReset&&currentRefreshState.resetPending)return [...currentNoChanges().slice(0,4),'이력 초기화 중입니다. 완료 후 다시 확인하세요.'];
                if(currentConfirmedReset)currentRefreshState.resetPending=true;
                if(!currentAutomaticMode)currentRefreshState.revision++;
                const currentRequestRevision=currentRefreshState.revision;
                currentRefreshState.pending++;
                try{
                    const currentResultValues=await currentBridgeFunction("""+json.dumps(current_action_name)+""",currentSelectedId,currentConfirmedTarget);
                    if(currentRequestRevision!==currentRefreshState.revision)return currentNoChanges();
                    if(currentAutomaticMode)currentResultValues[4]={__type__:'update'};
                    return currentResultValues;
                }catch(currentErrorValue){return [{__type__:'update'},{__type__:'update'},{__type__:'update'},{__type__:'update'},currentErrorValue.message];}
                finally{currentRefreshState.pending--;if(currentConfirmedReset)currentRefreshState.resetPending=false;}
            }"""
        current_history_inputs=[current_history_choice,current_history_refresh]
        for current_action_button,current_action_name in current_history_buttons:
            if current_action_name=='reset' and current_reset_target_handler:
                current_action_button.click(fn=None,outputs=[current_reset_confirmation,current_reset_target,current_history_feedback],queue=False,js="()=>{try{const currentTargetValue=window["+json.dumps(current_reset_target_handler)+"]();return [{__type__:'update',visible:true},currentTargetValue,'대상 동작·버전과 목록 초기화 범위를 확인하세요.'];}catch(currentErrorValue){return [{__type__:'update',visible:false},'',currentErrorValue.message];}}")
                current_reset_confirm.click(fn=None,inputs=[*current_history_inputs,current_reset_target],outputs=[*current_history_outputs,current_reset_confirmation,current_reset_target],queue=False,js="async(currentSelectedId,currentRefreshEnabled,currentConfirmedTarget)=>{const currentResultValues=await ("+create_history_script('reset')+")(currentSelectedId,currentRefreshEnabled,currentConfirmedTarget);return [...currentResultValues,{__type__:'update',visible:false},''];}")
                current_reset_cancel.click(lambda:(gr.update(visible=False),'','이력 초기화를 취소했습니다.'),outputs=[current_reset_confirmation,current_reset_target,current_history_feedback],queue=False)
            else:
                current_action_button.click(fn=None,inputs=current_history_inputs,outputs=current_history_outputs,queue=False,js=create_history_script(current_action_name))
        current_history_choice.input(fn=None,inputs=current_history_inputs,outputs=current_history_outputs,queue=False,js=create_history_script('inspect'))
        current_history_timer=gr.Timer(5)
        current_history_timer.tick(fn=None,inputs=current_history_inputs,outputs=current_history_outputs,queue=False,js=create_history_script('list',True),show_progress='hidden')
