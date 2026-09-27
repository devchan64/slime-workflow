"""생성 전 GPU 대기열 확인 모달을 모든 Gradio 생성 버튼에 연결한다."""
from pathlib import Path
import inspect
import gradio as gr
GPU_CONFIRMATION_SCRIPT = (Path(__file__).parents[1]/'ui/shared/gpu-queue-confirmation.js').read_text()


def bind_gpu_generation_confirmation(generation_button_value, generation_callback_value, generation_input_values, generation_output_values):
    confirmation_input_value=gr.Checkbox(value=False,visible=False)
    generation_output_values=generation_output_values if isinstance(generation_output_values,list) else [generation_output_values]
    generation_input_values=generation_input_values if isinstance(generation_input_values,list) else [generation_input_values]
    def execute_confirmed_generation(*generation_argument_values):
        if generation_argument_values[-1] is not True:
            yield tuple(gr.skip() for _ in generation_output_values) if len(generation_output_values)>1 else gr.skip()
            return
        generation_callback_result=generation_callback_value(*generation_argument_values[:-1])
        if inspect.isgenerator(generation_callback_result):yield from generation_callback_result
        else:yield generation_callback_result
    confirmation_script_value='async (...values)=>{'+GPU_CONFIRMATION_SCRIPT+';if(window.__gpuConfirmationPending){values[values.length-1]=false;return values;}window.__gpuConfirmationPending=true;try{values[values.length-1]=await confirmGpuQueueStart();return values;}finally{window.__gpuConfirmationPending=false;}}'
    return generation_button_value.click(execute_confirmed_generation,[*generation_input_values,confirmation_input_value],generation_output_values,js=confirmation_script_value,trigger_mode='once',concurrency_limit=1)
