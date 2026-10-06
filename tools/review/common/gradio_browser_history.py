"""브라우저가 기존 이력 API를 호출하는 도구의 표준 이력 컨트롤."""
import json
import gradio as gr
from tools.review.common.gradio_identifiers import build_generation_identifier
from tools.review.common.gradio_logs import create_copyable_log_textbox


def build_browser_history_controls(history_bridge_name, history_element_identifier):
    with gr.Column(elem_id=history_element_identifier):
        gr.Markdown('## 생성 이력')
        current_history_refresh=gr.Checkbox(label='이력 자동 갱신',value=True)
        current_history_choice=gr.Dropdown(label='이력 선택 · ID·상태 검색',choices=[],interactive=True)
        current_history_identifier=build_generation_identifier('선택한 생성 ID')
        current_history_feedback=gr.Textbox(label='이력 안내',value='목록을 읽고 작업을 선택하세요.',interactive=False)
        with gr.Row():
            current_history_buttons=[(gr.Button(current_action_label),current_action_name) for current_action_name,current_action_label in [('list','이력 새로고침'),('result','결과 조회'),('restore','입력값 불러오기'),('logs','로그 조회'),('resume','생성 재개'),('cancel','작업 중지')]]
        with gr.Accordion('저장된 입력·기록',open=False):
            current_history_record=gr.JSON(label='선택한 생성 기록')
        with gr.Accordion('선택한 작업 로그',open=False):
            current_history_log=create_copyable_log_textbox(label='저장된 로그 · 최근 12,000자',lines=12,interactive=False)
        with gr.Accordion('이력 수동 정리',open=False):
            gr.Markdown('목록에서만 제외합니다. 결과·입력·로그 파일은 유지됩니다. 실행 또는 대기 중인 작업은 정리할 수 없습니다.')
            with gr.Row():
                current_history_buttons.extend([(gr.Button('선택 이력 삭제'),'delete'),(gr.Button('이력 목록 초기화'),'reset')])
        current_history_outputs=[current_history_choice,current_history_identifier,current_history_record,current_history_log,current_history_feedback]
        def create_history_script(current_action_name, current_automatic_mode=False):
            current_bridge_key=json.dumps(history_bridge_name)
            current_state_key=json.dumps(history_element_identifier+'-refresh-state')
            return """async(currentSelectedId,currentRefreshEnabled)=>{
                const currentNoChanges=()=>Array.from({length:5},()=>({__type__:'update'}));
                const currentAutomaticMode="""+json.dumps(current_automatic_mode)+""";
                const currentBridgeFunction=window["""+current_bridge_key+"""];
                if(currentAutomaticMode&&(!currentRefreshEnabled||typeof currentBridgeFunction!=='function'))return currentNoChanges();
                const currentRefreshState=window["""+current_state_key+"""]??={revision:0,pending:0};
                if(currentAutomaticMode&&currentRefreshState.pending)return currentNoChanges();
                if(!currentAutomaticMode)currentRefreshState.revision++;
                const currentRequestRevision=currentRefreshState.revision;
                currentRefreshState.pending++;
                try{
                    const currentResultValues=await currentBridgeFunction("""+json.dumps(current_action_name)+""",currentSelectedId);
                    if(currentRequestRevision!==currentRefreshState.revision)return currentNoChanges();
                    if(currentAutomaticMode)currentResultValues[4]={__type__:'update'};
                    return currentResultValues;
                }catch(currentErrorValue){return [{__type__:'update'},{__type__:'update'},{__type__:'update'},{__type__:'update'},currentErrorValue.message];}
                finally{currentRefreshState.pending--;}
            }"""
        current_history_inputs=[current_history_choice,current_history_refresh]
        for current_action_button,current_action_name in current_history_buttons:
            current_action_button.click(fn=None,inputs=current_history_inputs,outputs=current_history_outputs,queue=False,js=create_history_script(current_action_name))
        current_history_choice.input(fn=None,inputs=current_history_inputs,outputs=current_history_outputs,queue=False,js=create_history_script('inspect'))
        current_history_timer=gr.Timer(5)
        current_history_timer.tick(fn=None,inputs=current_history_inputs,outputs=current_history_outputs,queue=False,js=create_history_script('list',True),show_progress='hidden')
