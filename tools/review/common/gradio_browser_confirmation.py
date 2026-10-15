"""브라우저 소유 입력을 고정하고 Gradio 기본 영역에서 GPU 접수를 확인한다."""
import json
import uuid
import gradio as gr


def bind_browser_gpu_confirmation(current_start_button,current_prepare_script,current_execute_script,current_input_components,current_output_components):
    current_receipt_key='management-confirmation-'+uuid.uuid4().hex
    current_output_count=len(current_output_components)
    with gr.Group(visible=False) as current_confirmation_panel:
        gr.Markdown('### GPU 작업 대기열에 추가할까요?\nGPU 사용 또는 대기 작업이 있습니다. 확인한 입력으로 등록합니다. 모달 대신 인라인 확인 영역을 사용합니다.')
        with gr.Row():
            current_cancel_button=gr.Button('추가하지 않기')
            current_confirm_button=gr.Button('대기열에 추가',variant='primary')
    current_receipt_input=gr.JSON(visible=False)
    current_common_script="""
const currentReceiptKey=KEY;
const currentReceiptStore=window[currentReceiptKey]??=new Map();
const currentEmptyOutputs=()=>Array.from({length:COUNT},()=>({__type__:'update'}));
const currentErrorOutputs=currentErrorValue=>{const currentOutputs=currentEmptyOutputs();currentOutputs[currentOutputs.length-1]=currentErrorValue.message;return currentOutputs;};
const currentExecuteAction=EXECUTE;
""".replace('KEY',json.dumps(current_receipt_key)).replace('COUNT',str(current_output_count)).replace('EXECUTE',current_execute_script)
    current_prepare_code="async(...currentInputValues)=>{"+current_common_script+"""
if(currentReceiptStore.size)return [...currentErrorOutputs(new Error('확인 대기 중입니다. 대기열 추가 또는 취소를 선택하세요.')),{__type__:'update'},{__type__:'update'},{__type__:'update'}];
const currentReceiptToken=crypto.randomUUID();
let currentKeepReceipt=false;
currentReceiptStore.set(currentReceiptToken,null);
try{
 const currentSnapshotValue=await (PREPARE)(...currentInputValues);
 const currentQueueResponse=await fetch('/management/gpu-queue',{cache:'no-store'});
 if(!currentQueueResponse.ok)throw Error('GPU 대기열을 확인하지 못했습니다. 잠시 후 다시 시도하세요.');
 const currentQueueRecord=await currentQueueResponse.json();
 const currentNeedsConfirmation=(Array.isArray(currentQueueRecord.jobs)&&currentQueueRecord.jobs.length>0)||(currentQueueRecord.gpu_status?.status==='busy'&&Array.isArray(currentQueueRecord.gpu_status.processes)&&currentQueueRecord.gpu_status.processes.length>0);
 if(!currentNeedsConfirmation){const currentOutputs=await currentExecuteAction(currentSnapshotValue);return [...currentOutputs,{__type__:'update',visible:false},null,{__type__:'update',interactive:true}];}
 currentReceiptStore.set(currentReceiptToken,currentSnapshotValue);
 currentKeepReceipt=true;
 return [...currentEmptyOutputs(),{__type__:'update',visible:true},{token:currentReceiptToken},{__type__:'update',interactive:false}];
}catch(currentErrorValue){return [...currentErrorOutputs(currentErrorValue),{__type__:'update'},null,{__type__:'update',interactive:true}];}
finally{if(!currentKeepReceipt)currentReceiptStore.delete(currentReceiptToken);}
}""".replace('PREPARE',current_prepare_script)
    current_finish_code="async(currentReceiptValue)=>{"+current_common_script+"""
try{
 const currentReceiptToken=currentReceiptValue?.token;
 if(!currentReceiptStore.has(currentReceiptToken))throw Error('이미 접수되었거나 취소된 확인입니다. 새로 시작하세요.');
 const currentSnapshotValue=currentReceiptStore.get(currentReceiptToken);
 currentReceiptStore.delete(currentReceiptToken);
 const currentOutputs=await currentExecuteAction(currentSnapshotValue);
 return [...currentOutputs,{__type__:'update',visible:false},null,{__type__:'update',interactive:true}];
}catch(currentErrorValue){return [...currentErrorOutputs(currentErrorValue),{__type__:'update',visible:false},null,{__type__:'update',interactive:true}];}
}"""
    current_shared_outputs=[*current_output_components,current_confirmation_panel,current_receipt_input,current_start_button]
    current_start_button.click(fn=None,inputs=current_input_components,outputs=current_shared_outputs,queue=False,js=current_prepare_code)
    current_confirm_button.click(fn=None,inputs=current_receipt_input,outputs=current_shared_outputs,queue=False,js=current_finish_code)
    current_cancel_button.click(fn=None,inputs=current_receipt_input,outputs=[current_confirmation_panel,current_receipt_input,current_start_button],queue=False,js="currentReceiptValue=>{window["+json.dumps(current_receipt_key)+"]?.delete(currentReceiptValue?.token);return [{__type__:'update',visible:false},null,{__type__:'update',interactive:true}];}")
