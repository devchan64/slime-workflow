"""Gradio 기본 컴포넌트로 생성 접수를 명시적으로 확인한다."""
import contextlib
import inspect
import uuid
import threading
import gradio as gr


def build_gpu_confirmation_observation_script(current_group_identifier,current_status_identifier):
    """확인창을 열 때 브라우저에서 기존 관측을 한 번 조회한다."""
    import json
    current_group_json=json.dumps(current_group_identifier)
    current_status_json=json.dumps(current_status_identifier)
    return """async()=>{
 let currentStatus=null;
 for(let currentAttempt=0;currentAttempt<40&&!currentStatus;currentAttempt++){
  currentStatus=document.getElementById(STATUS);
  if(!currentStatus)await new Promise(resolve=>setTimeout(resolve,50));
 }
 if(!currentStatus)return;
 requestAnimationFrame(()=>document.getElementById(GROUP)?.scrollIntoView({block:'center',behavior:'smooth'}));
 const currentToken=crypto.randomUUID();currentStatus.dataset.observation=currentToken;
 currentStatus.textContent='GPU와 대기열 상태를 확인하고 있습니다.';
 try{
  const currentResponse=await fetch('/management/gpu-queue',{cache:'no-store',signal:AbortSignal.timeout(5000)});
  if(!currentResponse.ok)throw Error('unavailable');
  const currentRecord=await currentResponse.json();
  const currentGpu=currentRecord?.gpu_status;
  if(!Array.isArray(currentRecord?.jobs)||currentRecord.jobs.some(item=>!item||typeof item.service!=='string'||typeof item.id!=='string')||!['idle','busy'].includes(currentGpu?.status)||!Array.isArray(currentGpu.processes)||currentGpu.processes.some(item=>!item||typeof item!=='object'||Array.isArray(item))||(currentGpu.status==='busy')!==(currentGpu.processes.length>0)||(currentRecord.truncated!==undefined&&typeof currentRecord.truncated!=='boolean'))throw Error('invalid');
  if(currentStatus.dataset.observation!==currentToken)return;
  const currentGpuText=currentGpu.status==='busy'?'GPU 프로세스 '+currentGpu.processes.length+'개 관측':'GPU 프로세스 관측 없음';
  const currentTime=new Date().toLocaleTimeString('ko-KR',{hour12:false});
  currentStatus.textContent=currentGpuText+' · 대기 작업 '+currentRecord.jobs.length+'건'+(currentRecord.truncated?' 이상':'')+' · 조회 시각 '+currentTime+' (GPU 정보는 캐시될 수 있음) · 실행 가능성이나 외부 작업 보호를 보장하지 않습니다.';
 }catch(currentError){if(currentStatus.dataset.observation===currentToken)currentStatus.textContent='GPU 또는 대기열 상태 확인 불가 · 유휴나 실행 가능 상태로 판단하지 마세요.';}
}""".replace('GROUP',current_group_json).replace('STATUS',current_status_json)


def bind_gpu_generation_confirmation(generation_button_value, generation_callback_value, generation_input_values, generation_output_values, generation_confirmation_container=None, generation_readiness_callback=None, generation_readiness_inputs=None, generation_readiness_events=None, generation_confirmation_validator=None, generation_confirmation_inputs=None):
    generation_output_values = generation_output_values if isinstance(generation_output_values, list) else [generation_output_values]
    generation_input_values = generation_input_values if isinstance(generation_input_values, list) else [generation_input_values]
    current_readiness_controls = list(generation_readiness_inputs or [])
    current_confirmation_controls = list(generation_confirmation_inputs or [])
    pending_generation_inputs = gr.State(None)
    generation_confirmation_lock = threading.Lock()
    confirmation_element_identifier = 'gpu-confirmation-' + uuid.uuid4().hex
    confirmation_status_identifier = 'gpu-observation-' + uuid.uuid4().hex
    with generation_confirmation_container if generation_confirmation_container is not None else contextlib.nullcontext():
        with gr.Group(visible=False, elem_id=confirmation_element_identifier) as generation_confirmation_group:
            gr.Markdown('### GPU 작업 대기열에 추가할까요?\n대기열에 추가 버튼을 누른 시점의 입력으로 등록합니다. 이후 입력을 수정했다면 추가하지 않기를 누른 뒤 다시 대기열에 추가하세요. GPU 사용 중에도 여유 메모리와 예약 상태에 따라 실행될 수 있습니다. 외부 GPU 작업의 성능이나 메모리는 보호하지 않으므로, 다른 작업이 중요하다면 완료 후 추가하세요.')
            gr.HTML('<p id="'+confirmation_status_identifier+'">GPU와 대기열 상태를 확인하고 있습니다.</p>')
            refresh_gpu_observation_button=gr.Button('GPU 상태 다시 확인',variant='secondary')
            with gr.Row():
                cancel_generation_button = gr.Button('추가하지 않기', variant='secondary')
                confirm_generation_button = gr.Button('확인 후 대기열에 추가', variant='primary')

    def prepare_generation_confirmation(*generation_argument_values):
        return {'inputs': tuple(generation_argument_values), 'consumed': False}, gr.update(visible=True), gr.update(interactive=False)

    def refresh_generation_readiness(saved_generation_inputs, *current_readiness_values):
        current_inputs_ready = generation_readiness_callback(*current_readiness_values) if generation_readiness_callback else True
        return gr.update(interactive=saved_generation_inputs is None and current_inputs_ready)

    for current_readiness_control in current_readiness_controls:
        current_readiness_control.change(refresh_generation_readiness, [pending_generation_inputs, *current_readiness_controls], generation_button_value, queue=False)

    for current_readiness_event in generation_readiness_events or []:
        current_readiness_event.success(refresh_generation_readiness, [pending_generation_inputs, *current_readiness_controls], generation_button_value, queue=False)

    def cancel_generation_confirmation(saved_generation_inputs, *current_readiness_values):
        with generation_confirmation_lock:
            if saved_generation_inputs is not None:
                saved_generation_inputs['consumed'] = True
        return None, gr.update(visible=False), refresh_generation_readiness(None, *current_readiness_values)

    def execute_confirmed_generation(saved_generation_inputs, *current_confirmation_values):
        with generation_confirmation_lock:
            if saved_generation_inputs is None or saved_generation_inputs['consumed']:
                raise gr.Error('이미 접수되었거나 취소된 확인입니다. 대기열에 추가 버튼으로 새 입력을 확인하세요.')
            saved_generation_inputs['consumed'] = True
            confirmed_generation_inputs = saved_generation_inputs['inputs']
        if generation_confirmation_validator is not None and not generation_confirmation_validator(confirmed_generation_inputs, current_confirmation_values):
            raise gr.Error('확인 중 입력이 변경됐습니다. 취소하고 입력을 다시 검토하세요.')
        generation_callback_result = generation_callback_value(*confirmed_generation_inputs)
        if inspect.isgenerator(generation_callback_result):
            yield from generation_callback_result
        else:
            yield generation_callback_result

    confirmation_output_values = [pending_generation_inputs, generation_confirmation_group, generation_button_value]
    generation_start_event = generation_button_value.click(prepare_generation_confirmation, generation_input_values, confirmation_output_values, trigger_mode='once')
    generation_start_event.then(fn=None, js=build_gpu_confirmation_observation_script(confirmation_element_identifier,confirmation_status_identifier),queue=False)
    refresh_gpu_observation_button.click(fn=None,js=build_gpu_confirmation_observation_script(confirmation_element_identifier,confirmation_status_identifier),queue=False)
    cancel_generation_button.click(cancel_generation_confirmation, inputs=[pending_generation_inputs, *current_readiness_controls], outputs=confirmation_output_values, queue=False)
    confirmation_start_event = confirm_generation_button.click(execute_confirmed_generation, [pending_generation_inputs, *current_confirmation_controls], generation_output_values, trigger_mode='once', concurrency_limit=1)
    confirmation_start_event.success(cancel_generation_confirmation, inputs=[pending_generation_inputs, *current_readiness_controls], outputs=confirmation_output_values)
    confirmation_start_event.failure(cancel_generation_confirmation, inputs=[pending_generation_inputs, *current_readiness_controls], outputs=confirmation_output_values, queue=False)
    return generation_start_event
