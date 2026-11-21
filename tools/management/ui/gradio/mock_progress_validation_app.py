"""실제 작업 서비스와 분리된 공용 진행 상태 브라우저 검증 화면."""
from time import monotonic
from uuid import uuid4
import gradio as gr
from tools.management.common.gradio_history import build_generation_history_view


def build_mock_progress_validation_interface(current_server_address):
    current_mock_jobs = {}

    def execute_mock_command(current_command_name, current_payload_record):
        if current_command_name == 'history':
            return {'records': [current_job_record['history'] for current_job_record in current_mock_jobs.values()]}
        if current_command_name == 'status':
            current_job_record = current_mock_jobs[current_payload_record['id']]
            current_elapsed_seconds = monotonic() - current_job_record['started']
            if current_elapsed_seconds < 5:
                return {'status': 'queued', 'progress': {'stage': 'queued'}, 'message': '모의 대기열'}
            if current_elapsed_seconds < 15:
                return {'status': 'running', 'progress': {'stage': 'inference', 'step': 1, 'total': 2}, 'message': '모의 실행'}
            return {'status': 'completed', 'progress': {'stage': 'completed'}, 'message': '모의 작업 완료'}
        raise ValueError('모의 검증에서는 해당 명령을 지원하지 않습니다.')

    def start_mock_generation():
        current_job_identifier = 'mock-' + uuid4().hex[:8]
        current_mock_jobs[current_job_identifier] = {'started': monotonic(), 'history': {'id': current_job_identifier, 'request': {}, 'status': {'status': 'queued'}}}
        return current_job_identifier, '모의 작업을 등록했습니다.'

    def render_mock_result(current_job_identifier, current_status_record, current_server_address):
        return '<p>모의 결과 표시 완료</p>' if current_status_record['status'] == 'completed' else '<p>모의 결과 대기 중</p>'

    with gr.Blocks(title='모의 진행 상태 검증') as current_interface_blocks:
        gr.Markdown('## 모의 진행 상태 검증\n실제 GPU·작업 서비스·기존 이력을 사용하지 않습니다.')
        current_start_button = gr.Button('모의 작업 시작')
        current_job_control = gr.Textbox(value='', visible=False)
        current_start_notice = gr.Markdown('모의 작업을 시작하세요.')
        current_start_button.click(start_mock_generation, outputs=[current_job_control, current_start_notice], queue=False)
        current_read_history, current_history_outputs = build_generation_history_view(execute_mock_command, current_server_address, '모의 이력만 사용합니다.', result_renderer_callback=render_mock_result, observed_job_control=current_job_control)
        current_interface_blocks.load(lambda: current_read_history(1), outputs=current_history_outputs)
    return current_interface_blocks


def build_mock_generator_interface(current_server_address, current_builder_function):
    """실제 생성기 Blocks에 메모리 모의 게이트웨이와 검증 버튼을 연결한다."""
    from unittest.mock import patch
    current_mock_jobs = {}

    def execute_mock_command(current_command_name, current_payload_record):
        if current_command_name == 'model-status':
            return {'ready': True, 'generation_ready': True, 'message': '모의 모델 준비됨'}
        if current_command_name == 'history':
            return {'records': [current_job_record['history'] for current_job_record in current_mock_jobs.values()]}
        if current_command_name == 'status':
            current_mock_record = current_mock_jobs[current_payload_record['id']]
            current_elapsed_seconds = monotonic() - current_mock_record['started']
            if current_elapsed_seconds < 7:
                return {'status': 'queued', 'progress': {'stage': 'queued'}, 'message': '격리 모의 대기'}
            if current_elapsed_seconds < 18:
                return {'status': 'running', 'progress': {'stage': 'inference', 'step': 1, 'total': 2}, 'message': '격리 모의 실행'}
            return {'status': 'completed', 'progress': {'stage': 'completed'}, 'message': '격리 모의 완료'}
        raise ValueError('격리 모의 화면에서는 실제 작업 명령을 사용할 수 없습니다.')

    def build_isolated_history(*current_arguments, **current_options):
        current_options['record_folder_route'] = None
        return build_generation_history_view(*current_arguments, **current_options)

    with patch('tools.management.common.gradio_model_download.build_model_progress_display', lambda *current_arguments, **current_options: None), patch(current_builder_function.__module__ + '.build_generation_history_view', build_isolated_history):
        current_interface_blocks = current_builder_function(current_server_address, execute_mock_command)
    current_observe_function = next(current_function for current_function in current_interface_blocks.fns.values() if current_function.name == 'observe_requested_job')
    current_job_control = current_observe_function.inputs[0]

    def start_mock_generation():
        current_job_identifier = 'mock-' + uuid4().hex[:8]
        current_mock_jobs[current_job_identifier] = {'started': monotonic(), 'history': {'id': current_job_identifier, 'request': {}, 'status': {'status': 'queued'}}}
        return current_job_identifier

    with current_interface_blocks:
        gr.Markdown('### 격리 모의 검증\n이 화면의 작업 버튼은 메모리 모의 작업만 만듭니다. 실제 생성·모델·이력 서비스에는 연결하지 않습니다.')
        current_mock_button = gr.Button('격리 모의 작업 시작')
        current_mock_button.click(start_mock_generation, outputs=current_job_control, queue=False)
    return current_interface_blocks


def build_mock_dwpose_interface(current_server_address):
    from tools.management.ui.gradio.dwpose_app import build_dwpose_interface
    return build_mock_generator_interface(current_server_address, build_dwpose_interface)


def build_mock_animate_interface(current_server_address):
    from tools.management.ui.gradio.wan_animate2_app import build_animate_interface
    return build_mock_generator_interface(current_server_address, build_animate_interface)
