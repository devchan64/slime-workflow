"""공용 Gradio 모델 다운로드 및 준비 상태 표시."""
import gradio as gr


def build_model_download_controls(current_interface_blocks, current_execute_command):
    current_model_ready = gr.State(False)
    current_model_output = gr.Markdown('모델 상태 확인 중')
    with gr.Row():
        current_refresh_button = gr.Button('모델 준비 상태 확인')
        current_download_button = gr.Button('모델 다운로드',interactive=False)
    current_download_timer = gr.Timer(5,active=False)
    current_model_outputs = [current_model_output,current_model_ready,current_download_button,current_download_timer]

    def refresh_model_download_status():
        try:
            current_asset_record = current_execute_command('model-status',{})
            current_download_running = current_asset_record.get('preparation_status') == 'running'
            return (
                current_asset_record['message'],
                current_asset_record.get('generation_ready', current_asset_record['ready']),
                gr.update(interactive=not current_asset_record['ready'] and not current_download_running),
                gr.Timer(active=current_download_running),
            )
        except Exception as current_asset_error:
            return f'모델 상태 확인 실패: {current_asset_error}. 모델 준비 상태 확인을 다시 눌러 주세요.',False,gr.update(interactive=False),gr.Timer(active=False)

    def request_model_download():
        try:
            current_execute_command('prepare',{'action':'prepare'})
        except Exception as current_download_error:
            return f'다운로드 요청 실패: {current_download_error}',False,gr.update(interactive=True),gr.Timer(active=False)
        return refresh_model_download_status()

    current_refresh_event = current_refresh_button.click(refresh_model_download_status,outputs=current_model_outputs,queue=False)
    current_load_event = current_interface_blocks.load(refresh_model_download_status,outputs=current_model_outputs)
    current_download_event = current_download_button.click(request_model_download,outputs=current_model_outputs,queue=False)
    current_download_tick = current_download_timer.tick(refresh_model_download_status,outputs=current_model_outputs,queue=False)
    return current_model_ready, [current_refresh_event, current_load_event, current_download_event, current_download_tick]
