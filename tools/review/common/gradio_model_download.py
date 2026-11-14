"""공용 Gradio 모델 다운로드 및 준비 상태 표시."""
import gradio as gr


def read_model_readiness_status(current_execute_command):
    """모델 준비 상태와 생성 가능 여부를 읽고 미준비 시 관리 화면을 안내한다."""
    try:
        current_asset_record = current_execute_command('model-status', {})
        current_model_ready = current_asset_record.get('generation_ready', current_asset_record['ready'])
        current_preparation_running = current_asset_record.get('preparation_status') == 'running'
        return (current_asset_record['message'], current_model_ready,
                gr.update(visible=not current_model_ready), gr.Timer(active=current_preparation_running))
    except Exception as current_asset_error:
        return (f'모델 상태 확인 실패: {current_asset_error}. 모델 준비 상태 확인을 다시 눌러 주세요.', False,
                gr.update(visible=True), gr.Timer(active=False))


def build_model_readiness_controls(current_interface_blocks, current_execute_command):
    """다운로드를 실행하지 않고 상태와 모델 관리 이동만 제공한다."""
    current_model_ready = gr.State(False)
    current_model_output = gr.Markdown('모델 상태 확인 중')
    with gr.Row():
        current_refresh_button = gr.Button('모델 준비 상태 확인')
        current_management_button = gr.Button('모델 관리로 이동', link='/management/?tool=model-management&category=model-management', link_target='_self', visible=False)
    current_readiness_timer = gr.Timer(5, active=False)
    current_model_outputs = [current_model_output, current_model_ready, current_management_button, current_readiness_timer]
    def refresh_model_readiness_status():
        return read_model_readiness_status(current_execute_command)
    current_refresh_event = current_refresh_button.click(refresh_model_readiness_status, outputs=current_model_outputs, queue=False)
    current_load_event = current_interface_blocks.load(refresh_model_readiness_status, outputs=current_model_outputs)
    current_timer_event = current_readiness_timer.tick(refresh_model_readiness_status, outputs=current_model_outputs, queue=False)
    return current_model_ready, [current_refresh_event, current_load_event, current_timer_event]


def build_model_download_controls(current_interface_blocks, current_execute_command, poll_always_enabled=False, model_service_name=None):
    current_model_ready = gr.State(False)
    current_model_output = gr.Markdown('모델 상태 확인 중')
    if model_service_name is not None:
        build_model_progress_display(current_interface_blocks, model_service_name)
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
            elif current_asset_record['ready']:
                current_status_message += ' · 모델이 준비되어 다운로드할 필요가 없습니다.'
            elif not current_asset_record.get('can_prepare', True):
                current_status_message += ' · 현재 준비 작업이 끝난 뒤 다운로드할 수 있습니다.'
            return (
                current_status_message,
                current_asset_record.get('generation_ready', current_asset_record['ready']),
                gr.update(interactive=not current_asset_record['ready'] and not current_download_running and current_asset_record.get('can_prepare', True)),
                gr.Timer(active=poll_always_enabled or current_download_running),
            )
        except Exception as current_asset_error:
            return f'모델 상태 확인 실패: {current_asset_error}. 모델 준비 상태 확인을 다시 눌러 주세요.',False,gr.update(interactive=False),gr.Timer(active=poll_always_enabled)

    def request_model_download():
        try:
            current_execute_command('prepare',{'action':'prepare'})
        except Exception as current_download_error:
            return f'다운로드 요청 실패: {current_download_error}',False,gr.update(interactive=False),gr.Timer(active=True)
        return refresh_model_download_status()

    current_refresh_event = current_refresh_button.click(refresh_model_download_status,outputs=current_model_outputs,queue=False)
    current_load_event = current_interface_blocks.load(refresh_model_download_status,outputs=current_model_outputs)
    current_download_event = current_download_button.click(request_model_download,outputs=current_model_outputs,queue=False)
    current_download_tick = current_download_timer.tick(refresh_model_download_status,outputs=current_model_outputs,queue=False)
    return current_model_ready, [current_refresh_event, current_load_event, current_download_event, current_download_tick]

MODEL_DOWNLOAD_PREFIXES = {
    'prop-generator': ('Qwen/Qwen-Image-2.1',),
    'kimodo': ('nvidia/Kimodo', 'McGill-NLP/LLM2Vec', 'ollama/llama3', 'Wan-AI/Wan2.2-Animate-14B'),
    'wan22-animate2': ('Wan-AI/Wan2.2-Animate-2-14B-Diffusers',),
    'wan22-fun-control': ('Comfy-Org/Wan-2.2', 'Comfy-Org/Wan-2.1', 'yzd-v/DWPose'),
    'wan22-vace': ('wan22-vace', 'wan-vace/', 'QuantStack/Wan2.2-VACE', 'alibaba-pai/Wan2.2-VACE', 'Comfy-Org/Wan-2.1/split_files/vae/wan_2.1_vae.safetensors'),
    'music-heartmula': ('HeartMuLa/', 'heartmula/'),
    'sfx-dasheng-audiogen': ('mispeech/Dasheng-AudioGen', 'mispeech/dashengtokenizer', 'google/flan-t5-large'),
    'writer-agent': ('writer-agent/',),
    'qwen-2512': ('Qwen/Qwen-Image-2512', 'lightx2v/Qwen-Image-2512-Lightning'),
}


def format_model_download_status(current_status_values, model_service_name):
    current_model_prefixes = MODEL_DOWNLOAD_PREFIXES[model_service_name]
    current_matching_values = [current_status_value for current_status_value in current_status_values
                               if isinstance(current_status_value.get('model'), str) and current_status_value['model'].startswith(current_model_prefixes)]
    current_active_values = [current_status_value for current_status_value in current_matching_values if current_status_value.get('status') == 'running']
    current_recent_values = [current_status_value for current_status_value in current_matching_values if current_status_value.get('status') in ('completed', 'failed', 'interrupted')]
    current_status_labels = {'running': '진행 중', 'completed': '완료', 'failed': '실패', 'interrupted': '중단됨'}
    current_result_lines = []
    for current_status_value in current_active_values + current_recent_values[:1]:
        current_received_bytes = current_status_value.get('bytes', 0)
        current_total_bytes = current_status_value.get('total_bytes')
        current_progress_text = f'{current_received_bytes / current_total_bytes * 100:.1f}% ({current_received_bytes:,} / {current_total_bytes:,}바이트)' if current_total_bytes else f'{current_received_bytes:,}바이트 · 전체 크기 확인 중'
        current_status_name = current_status_value['status']
        if current_status_name == 'completed' and not current_total_bytes:
            current_progress_text = '크기 정보 없음'
        current_existing_bytes = current_status_value.get('existing_bytes')
        if current_status_value.get('stage') == '기존 부분 파일 검증' and isinstance(current_existing_bytes, int) and current_existing_bytes > 0:
            current_progress_text = (f'기존 부분 {current_existing_bytes:,}바이트 보존 · '
                                     f'검증 {current_received_bytes / current_existing_bytes * 100:.1f}% '
                                     f'({current_received_bytes:,} / {current_existing_bytes:,}바이트)')
        elif current_status_value.get('stage') == '기존 부분 파일 검증':
            # 이전 버전에서 시작한 작업은 기존 부분 크기를 보고하지 않는다.
            current_progress_text = f'검증한 데이터 {current_received_bytes:,}바이트 · 전체 파일 기준 {current_progress_text}'
        current_resume_bytes = current_status_value.get('resumed_bytes')
        current_resume_text = f'{current_resume_bytes:,}바이트' if current_resume_bytes is not None else '확인 불가'
        current_resume_label = '시작 시 검증 지점' if current_status_value.get('stage') == '기존 부분 파일 검증' else '시작 시 이어받은 바이트'
        current_result_lines.append(f"- {current_status_value['model']} · {current_status_labels[current_status_name]} · {current_status_value.get('stage', '준비')} · {current_progress_text} · {current_resume_label} {current_resume_text}")
    return '\n'.join(current_result_lines) if current_result_lines else '진행 중인 다운로드와 최근 결과가 없습니다.'


def build_model_progress_display(current_interface_blocks, model_service_name):
    from tools.review.common.management_client import execute_remote_management_command
    current_progress_output = gr.Markdown('다운로드 상태 확인 중')
    def refresh_model_progress_status():
        try:
            current_status_response = execute_remote_management_command('model-downloads', 'download-status', {})
            return format_model_download_status(current_status_response['records'], model_service_name)
        except Exception as current_status_error:
            return f'다운로드 상태 확인 실패: {current_status_error}'
    current_interface_blocks.load(refresh_model_progress_status, outputs=current_progress_output)
    gr.Timer(5).tick(refresh_model_progress_status, outputs=current_progress_output, queue=False)
    return current_progress_output
