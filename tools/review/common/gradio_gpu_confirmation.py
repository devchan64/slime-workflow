"""생성 전 GPU 대기열 확인 모달을 모든 Gradio 생성 버튼에 연결한다."""
import inspect
import gradio as gr
GPU_CONFIRMATION_SCRIPT = """
async function confirmGpuQueueStart() {
 const currentQueueResponse = await fetch('/management/gpu-queue', {cache: 'no-store'});
 if (!currentQueueResponse.ok) throw new Error('GPU 대기열을 확인하지 못했습니다. 잠시 후 다시 시도하세요.');
 const currentQueueRecord = await currentQueueResponse.json();
 const currentPendingJobs = currentQueueRecord.jobs || [];
 const currentActiveProcesses = currentQueueRecord.gpu_status?.status === 'busy' ? (currentQueueRecord.gpu_status.processes || []) : [];
 if (!currentPendingJobs.length && !currentActiveProcesses.length) return true;
 const currentQueueLines = [
  ...currentActiveProcesses.map(currentProcessRecord => 'GPU 사용 중 · ' + (currentProcessRecord.command || currentProcessRecord.id || '외부 작업')),
  ...currentPendingJobs.map(currentJobRecord => '대기 중 · ' + (currentJobRecord.service || '') + ' · ' + (currentJobRecord.id || ''))
 ];
 return window.confirm('GPU 작업 대기열에 추가할까요?\\n현재 GPU 메모리로 실행 가능한 작업부터 처리합니다.\\n\\n' + currentQueueLines.join('\\n'));
}
"""


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
