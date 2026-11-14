"""게이트웨이의 모델 준비 상태를 한 화면에서 조회한다."""
import gradio as gr

from tools.review.common.gradio_model_download import build_model_download_controls, build_model_progress_display
from tools.review.common.management_client import execute_remote_management_command

MODEL_PREPARATION_SERVICES = (
    ('Qwen Image 2.1', 'prop-generator'),
    ('Kimodo', 'kimodo'),
    ('Wan Animate-2', 'wan22-animate2'),
)
MODEL_JOB_SERVICES = (
    ('Wan Fun Control', 'wan22-fun-control'),
    ('HeartMuLa', 'music-heartmula'),
    ('Dasheng-AudioGen', 'sfx-dasheng-audiogen'),
)


def read_model_job_status(current_service_name, current_execute_command=execute_remote_management_command):
    """작업 이력에서 준비 요청의 상태를 읽는다."""
    try:
        current_history_record = current_execute_command(current_service_name, 'history', {})
        current_prepare_records = [current_job_record for current_job_record in current_history_record.get('records', [])
                                   if current_job_record.get('request', {}).get('action') == 'prepare']
        current_active_records = [current_job_record for current_job_record in current_prepare_records
                                  if current_job_record.get('status', {}).get('status') in ('queued', 'running')]
        current_job_record = (current_active_records or current_prepare_records or [None])[0]
        if current_job_record:
            current_state_name = current_job_record.get('status', {}).get('status', 'unknown')
            current_state_label = {'queued': '대기 중', 'running': '진행 중', 'completed': '완료', 'failed': '실패', 'cancelled': '취소됨'}.get(current_state_name, current_state_name)
            return f"최근 모델 준비: {current_state_label} · 작업 ID `{current_job_record['id']}`"
        return '최근 모델 준비 작업이 없습니다.'
    except Exception as current_status_error:
        return f'모델 준비 이력 조회 실패: {current_status_error}'


def format_migraphx_build_status(current_status_record):
    current_state_name = current_status_record.get('status', 'idle')
    current_state_label = {'idle': '빌드 이력 없음', 'queued': 'GPU 대기 중', 'running': '빌드 중',
                           'completed': '최근 빌드 완료', 'failed': '빌드 실패', 'cancelled': '취소됨',
                           'checking': '모델·GPU 환경 및 빌드 확인 중', 'ready': '현재 환경에서 빌드 준비 완료',
                           'rebuild_required': '현재 환경에 맞는 빌드 필요', 'unavailable': '빌드 유효성 확인 실패'}.get(current_state_name, current_state_name)
    current_job_identifier = current_status_record.get('id')
    current_job_text = f' · 작업 ID `{current_job_identifier}`' if current_job_identifier else ''
    current_error_text = f" · {current_status_record['error']}" if current_status_record.get('error') else ''
    current_log_text = f' · 상세 로그: `.tmp/test/kimodo-migraphx-build/{current_job_identifier}/worker.log`' if current_state_name == 'failed' and current_job_identifier else ''
    return f'{current_state_label}{current_job_text}{current_error_text}{current_log_text}'


def build_migraphx_build_controls(current_interface_blocks):
    gr.Markdown('### Kimodo DWPose MIGraphX 빌드\n참조 포즈와 출력 포즈에 사용할 GPU 실행 그래프를 미리 빌드합니다. GPU 대기열에서 실행하며 최초 빌드에는 시간이 걸립니다. 모델과 GPU 실행 환경이 바뀌면 다시 빌드해야 합니다.')
    current_build_status = gr.Markdown('빌드 상태 확인 중')
    current_build_button = gr.Button('MIGraphX 빌드 시작', interactive=False)
    def refresh_migraphx_build_status():
        try:
            current_status_record = execute_remote_management_command('kimodo', 'migraphx-build-status', {})
            return format_migraphx_build_status(current_status_record), gr.update(interactive=current_status_record.get('status') == 'rebuild_required')
        except Exception as current_status_error:
            return f'빌드 상태 조회 실패: {current_status_error}', gr.update(interactive=False)
    def request_migraphx_build_job():
        try:
            current_status_record = execute_remote_management_command('kimodo', 'migraphx-build', {})
            return format_migraphx_build_status(current_status_record), gr.update(interactive=False)
        except Exception as current_build_error:
            return f'빌드 요청 실패: {current_build_error}', gr.update(interactive=False)
    current_interface_blocks.load(refresh_migraphx_build_status, outputs=[current_build_status, current_build_button])
    gr.Timer(5).tick(refresh_migraphx_build_status, outputs=[current_build_status, current_build_button], queue=False)
    current_build_button.click(request_migraphx_build_job, outputs=[current_build_status, current_build_button], queue=False)


def build_model_management_interface():
    with gr.Blocks(title='모델 다운로드·빌드 상태') as current_interface_blocks:
        gr.Markdown('## 모델 다운로드·빌드 상태\n다른 생성기 화면이나 통합 CLI에서 시작한 모델 준비도 같은 게이트웨이 상태에서 확인합니다. 5초마다 갱신됩니다. 각 모델에서 현재 다운로드와 최근 완료·실패 상태를 표시합니다. 스냅샷 다운로드는 전체 크기가 확인되는 동안 진행률이 바뀔 수 있습니다.')
        for current_label_name, current_service_name in MODEL_PREPARATION_SERVICES:
            with gr.Group():
                gr.Markdown(f'### {current_label_name}')
                def execute_model_command(current_command_name, current_payload_record, service_name_value=current_service_name):
                    return execute_remote_management_command(service_name_value, current_command_name, current_payload_record)
                build_model_download_controls(current_interface_blocks, execute_model_command, poll_always_enabled=True, model_service_name=current_service_name)
                if current_service_name == 'kimodo':
                    build_migraphx_build_controls(current_interface_blocks)
        gr.Markdown('### 대기열로 준비하는 모델\n다운로드 요청은 각 생성기 화면에서 실행합니다.')
        for current_label_name, current_service_name in MODEL_JOB_SERVICES:
            with gr.Group():
                gr.Markdown(f'#### {current_label_name}')
                build_model_progress_display(current_interface_blocks, current_service_name)
                current_status_output = gr.Markdown('모델 준비 상태 확인 중')
                def refresh_model_job_status(service_name_value=current_service_name):
                    return read_model_job_status(service_name_value)
                current_interface_blocks.load(refresh_model_job_status, outputs=current_status_output)
                gr.Timer(5).tick(refresh_model_job_status, outputs=current_status_output, queue=False)
        for current_label_name, current_service_name in (('Wan VACE', 'wan22-vace'), ('작가 AI', 'writer-agent'), ('Qwen Image 2512', 'qwen-2512')):
            with gr.Group():
                gr.Markdown(f'### {current_label_name}')
                build_model_progress_display(current_interface_blocks, current_service_name)
    return current_interface_blocks
