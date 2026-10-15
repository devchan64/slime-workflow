"""Gradio 기본 컴포넌트로 생성 접수를 명시적으로 확인한다."""
import contextlib
import inspect
import uuid
import threading
import gradio as gr


def bind_gpu_generation_confirmation(generation_button_value, generation_callback_value, generation_input_values, generation_output_values, generation_confirmation_container=None, generation_readiness_callback=None, generation_readiness_inputs=None):
    generation_output_values = generation_output_values if isinstance(generation_output_values, list) else [generation_output_values]
    generation_input_values = generation_input_values if isinstance(generation_input_values, list) else [generation_input_values]
    current_readiness_controls = list(generation_readiness_inputs or [])
    pending_generation_inputs = gr.State(None)
    generation_confirmation_lock = threading.Lock()
    confirmation_element_identifier = 'gpu-confirmation-' + uuid.uuid4().hex
    with generation_confirmation_container if generation_confirmation_container is not None else contextlib.nullcontext():
        with gr.Group(visible=False, elem_id=confirmation_element_identifier) as generation_confirmation_group:
            gr.Markdown('### GPU 작업 대기열에 추가할까요?\n확인한 입력으로 작업을 등록합니다. GPU가 사용 중이면 대기하며, 실행 가능한 작업부터 처리합니다.')
            with gr.Row():
                cancel_generation_button = gr.Button('추가하지 않기', variant='secondary')
                confirm_generation_button = gr.Button('대기열에 추가', variant='primary')

    def prepare_generation_confirmation(*generation_argument_values):
        return {'inputs': tuple(generation_argument_values), 'consumed': False}, gr.update(visible=True), gr.update(interactive=False)

    def refresh_generation_readiness(saved_generation_inputs, *current_readiness_values):
        current_inputs_ready = generation_readiness_callback(*current_readiness_values) if generation_readiness_callback else True
        return gr.update(interactive=saved_generation_inputs is None and current_inputs_ready)

    for current_readiness_control in current_readiness_controls:
        current_readiness_control.change(refresh_generation_readiness, [pending_generation_inputs, *current_readiness_controls], generation_button_value, queue=False)

    def cancel_generation_confirmation(saved_generation_inputs, *current_readiness_values):
        with generation_confirmation_lock:
            if saved_generation_inputs is not None:
                saved_generation_inputs['consumed'] = True
        return None, gr.update(visible=False), refresh_generation_readiness(None, *current_readiness_values)

    def execute_confirmed_generation(saved_generation_inputs):
        with generation_confirmation_lock:
            if saved_generation_inputs is None or saved_generation_inputs['consumed']:
                raise gr.Error('이미 접수되었거나 취소된 확인입니다. 생성 시작 버튼으로 새 입력을 확인하세요.')
            saved_generation_inputs['consumed'] = True
            confirmed_generation_inputs = saved_generation_inputs['inputs']
        generation_callback_result = generation_callback_value(*confirmed_generation_inputs)
        if inspect.isgenerator(generation_callback_result):
            yield from generation_callback_result
        else:
            yield generation_callback_result

    confirmation_output_values = [pending_generation_inputs, generation_confirmation_group, generation_button_value]
    generation_start_event = generation_button_value.click(prepare_generation_confirmation, generation_input_values, confirmation_output_values, trigger_mode='once')
    generation_start_event.then(fn=None, js="() => {requestAnimationFrame(() => document.getElementById('" + confirmation_element_identifier + "')?.scrollIntoView({block: 'center', behavior: 'smooth'}));}")
    cancel_generation_button.click(cancel_generation_confirmation, inputs=[pending_generation_inputs, *current_readiness_controls], outputs=confirmation_output_values, queue=False)
    confirmation_start_event = confirm_generation_button.click(execute_confirmed_generation, pending_generation_inputs, generation_output_values, trigger_mode='once', concurrency_limit=1)
    confirmation_start_event.then(cancel_generation_confirmation, inputs=[pending_generation_inputs, *current_readiness_controls], outputs=confirmation_output_values)
    return generation_start_event
