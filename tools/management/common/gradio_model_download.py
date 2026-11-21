"""공용 Gradio 모델 다운로드 및 준비 상태 표시."""
import gradio as gr
from tools.management.common.model_download_progress import MODEL_DOWNLOAD_PREFIXES, format_model_download_status


def read_model_readiness_status(current_execute_command):
    """모델 준비 상태와 생성 가능 여부를 읽고 미준비 시 관리 화면을 안내한다."""
    try:
        current_asset_record = current_execute_command('model-status', {})
        current_model_ready = current_asset_record.get('generation_ready', current_asset_record['ready'])
        current_preparation_running = current_asset_record.get('preparation_status') == 'running'
        return (current_asset_record['message'], current_model_ready,
                gr.update(visible=not current_model_ready), gr.Timer(value=5, active=current_preparation_running))
    except Exception as current_asset_error:
        return (f'모델 상태 확인 실패: {current_asset_error}. 모델 준비 상태 확인을 다시 눌러 주세요.', False,
                gr.update(visible=True), gr.Timer(value=5, active=False))


def build_model_readiness_controls(current_interface_blocks, current_execute_command, show_management_always=False):
    """다운로드를 실행하지 않고 상태와 모델 관리 이동만 제공한다."""
    current_model_ready = gr.Checkbox(value=False, visible=False)
    current_model_output = gr.Markdown('모델 상태 확인 중')
    with gr.Row():
        current_refresh_button = gr.Button('모델 준비 상태 확인')
        current_management_button = gr.Button('모델 관리로 이동', link='/management/?tool=model-management&category=model-management', link_target='_self', visible=show_management_always)
    current_readiness_timer = gr.Timer(5, active=False)
    current_model_outputs = [current_model_output, current_model_ready, current_management_button, current_readiness_timer]
    def refresh_model_readiness_status():
        current_status_values = list(read_model_readiness_status(current_execute_command))
        if show_management_always:
            current_status_values[2] = gr.update(visible=True)
        return current_status_values
    current_refresh_event = current_refresh_button.click(refresh_model_readiness_status, outputs=current_model_outputs, queue=False)
    current_load_event = current_interface_blocks.load(refresh_model_readiness_status, outputs=current_model_outputs)
    current_timer_event = current_readiness_timer.tick(refresh_model_readiness_status, outputs=current_model_outputs, queue=False)
    return current_model_ready, [current_refresh_event, current_load_event, current_timer_event]


def build_model_download_controls(current_interface_blocks, current_execute_command, poll_always_enabled=False, model_service_name=None, shared_refresh_records=None, shared_progress_outputs=None):
    current_model_ready = gr.State(False)
    current_model_output = gr.Markdown('모델 상태 확인 중')
    if model_service_name is not None:
        if shared_progress_outputs is None:
            build_model_progress_display(current_interface_blocks, model_service_name)
        else:
            shared_progress_outputs.append((model_service_name, gr.Markdown('다운로드 상태 확인 중')))
    with gr.Row():
        current_refresh_button = gr.Button('모델 준비 상태 확인')
        current_download_button = gr.Button('모델 다운로드',interactive=False)
    current_download_timer = gr.Timer(5,active=poll_always_enabled)
    current_model_outputs = [current_model_output,current_model_ready,current_download_button,current_download_timer]

    def refresh_model_download_status():
        try:
            current_asset_record = current_execute_command('model-status',{})
            current_preparation_status = current_asset_record.get('preparation_status')
            current_download_running = current_preparation_status in ('queued', 'running')
            current_status_message = current_asset_record['message']
            if current_download_running:
                current_status_message += (' · 모델 준비가 대기 중이므로 중복 요청을 막고 있습니다.' if current_preparation_status == 'queued'
                                           else ' · 모델 준비가 진행 중이므로 중복 요청을 막고 있습니다.')
            elif not current_asset_record.get('can_prepare', True):
                current_status_message += ' · ' + current_asset_record.get('prepare_blocked_reason', '현재 준비 작업이 끝난 뒤 다운로드할 수 있습니다.')
            elif current_asset_record['ready']:
                current_status_message += ' · 모델이 준비되어 다운로드할 필요가 없습니다.'
            return (
                current_status_message,
                current_asset_record.get('generation_ready', current_asset_record['ready']),
                gr.update(interactive=not current_asset_record['ready'] and not current_download_running and current_asset_record.get('can_prepare', True)),
                gr.Timer(value=5, active=poll_always_enabled or current_download_running),
            )
        except Exception as current_asset_error:
            return f'모델 상태 확인 실패: {current_asset_error}. 모델 준비 상태 확인을 다시 눌러 주세요.',False,gr.update(interactive=False),gr.Timer(value=5, active=poll_always_enabled)

    def request_model_download():
        try:
            current_execute_command('prepare',{'action':'prepare'})
        except Exception as current_download_error:
            return f'다운로드 요청 실패: {current_download_error}',False,gr.update(interactive=False),gr.Timer(value=5, active=True)
        return refresh_model_download_status()

    if shared_refresh_records is not None:
        shared_refresh_records.append((refresh_model_download_status, current_model_outputs))
    current_refresh_event = current_refresh_button.click(refresh_model_download_status,outputs=current_model_outputs,queue=False)
    current_load_event = current_interface_blocks.load(refresh_model_download_status,outputs=current_model_outputs)
    current_download_event = current_download_button.click(request_model_download,outputs=current_model_outputs,queue=False)
    current_download_tick = current_download_timer.tick(refresh_model_download_status,outputs=current_model_outputs,queue=False)
    return current_model_ready, [current_refresh_event, current_load_event, current_download_event, current_download_tick]

def build_model_progress_display(current_interface_blocks, model_service_name):
    from tools.management.common.management_client import execute_remote_management_command
    current_progress_output = gr.Markdown('다운로드 상태 확인 중')
    current_progress_timer = gr.Timer(30)
    def refresh_model_progress_status():
        try:
            current_status_response = execute_remote_management_command('model-downloads', 'download-status', {})
            current_matching_records = [current_status_value for current_status_value in current_status_response['records']
                                        if isinstance(current_status_value.get('model'), str)
                                        and current_status_value['model'].startswith(MODEL_DOWNLOAD_PREFIXES[model_service_name])]
            current_running_download = any(current_status_value.get('status') == 'running' for current_status_value in current_matching_records)
            return format_model_download_status(current_status_response['records'], model_service_name), gr.Timer(value=5 if current_running_download else 30, active=True)
        except Exception as current_status_error:
            return f'다운로드 상태 확인 실패: {current_status_error}', gr.Timer(value=30, active=True)
    current_progress_outputs = [current_progress_output, current_progress_timer]
    current_interface_blocks.load(refresh_model_progress_status, outputs=current_progress_outputs, queue=False, show_progress='hidden')
    current_progress_timer.tick(refresh_model_progress_status, outputs=current_progress_outputs, queue=False, show_progress='hidden')
    return current_progress_output
