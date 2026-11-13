"""단일 이미지 DWPose 추출 관리 화면."""
import base64
import html
from pathlib import Path
import gradio as gr
from generators.dwpose.contracts import DWPOSE_JOB_STORAGE, validate_dwpose_request
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_video_results import build_video_job_monitor
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT


def execute_dwpose_command(current_command_name, current_payload_record):
    return execute_remote_management_command('dwpose', current_command_name, current_payload_record)


def render_dwpose_result(current_job_identifier, current_status_record, current_server_address):
    if not current_status_record.get('image'):
        return '<p>포즈 추출 결과가 아직 없습니다.</p>'
    return '<img alt="DWPose 추출 결과" src="'+html.escape(current_status_record['image'], quote=True)+'"><p><a href="'+html.escape(current_status_record['download'], quote=True)+'">포즈 PNG·좌표 YAML 다운로드</a></p>'


def restore_dwpose_inputs(current_history_record):
    current_job_directory = (DWPOSE_JOB_STORAGE/current_history_record['id']).resolve()
    if current_job_directory.parent != DWPOSE_JOB_STORAGE.resolve():
        raise ValueError('이력 경로 오류')
    current_request_record = current_history_record['request']
    return str(current_job_directory/'reference-1.png'), current_request_record.get('pose_include_hands', False), current_request_record.get('pose_include_face', False), current_history_record['id']


def build_dwpose_interface(current_server_address, current_command_callback=None):
    current_execute_command = current_command_callback or execute_dwpose_command
    with gr.Blocks(title='DWPose 이미지 추출') as current_interface_blocks:
        gr.Markdown('## DWPose 이미지 추출\n832×480 PNG 한 장에서 관절을 검출합니다. 원본 위치·크기를 유지하며 비율 보정이나 축소를 적용하지 않습니다. 몸 18점에 눈·코·귀가 포함됩니다. 검출되지 않은 점은 좌표에서 null로 기록합니다.')
        current_image_control = gr.File(label='입력 PNG · 832×480', file_types=['.png'], type='filepath')
        current_hands_control = gr.Checkbox(label='손 상세 표시', value=False)
        current_face_control = gr.Checkbox(label='얼굴 상세 표시', value=False)
        gr.Markdown('CUDA 추론 · 공용 GPU 대기열 사용 · 프롬프트·시드 없음. 결과 ZIP은 포즈 PNG와 원본 픽셀 좌표·신뢰도 YAML을 포함합니다. 기준 데이터 등록은 검수 후 별도로 수행합니다.')
        current_model_output = gr.Markdown()
        def read_dwpose_model_status():
            try:
                return current_execute_command('model-status', {})['message']
            except (ValueError, RuntimeError, OSError) as current_status_error:
                return str(current_status_error)
        current_interface_blocks.load(read_dwpose_model_status, outputs=current_model_output)
        current_generate_button = gr.Button('대기열에 추가', interactive=False, variant='primary')
        with gr.Column() as current_confirmation_container:
            pass
        current_job_control = gr.Textbox(label='생성 ID')
        current_status_output = gr.Markdown('PNG를 첨부하세요. 실행 중 작업이 있으면 종료 후 추출합니다.')
        current_input_controls = [current_image_control, current_hands_control, current_face_control]
        def enqueue_dwpose_generation(current_image_path, current_include_hands, current_include_face):
            current_payload_record = {'action':'generate', 'images':[base64.b64encode(Path(current_image_path).read_bytes()).decode()], 'pose_include_hands':current_include_hands, 'pose_include_face':current_include_face}
            validate_dwpose_request(current_payload_record)
            current_job_record = current_execute_command('generate', current_payload_record)
            return current_job_record['id'], '공용 GPU 대기열에 등록했습니다.'
        bind_gpu_generation_confirmation(current_generate_button, enqueue_dwpose_generation, current_input_controls, [current_job_control, current_status_output], generation_confirmation_container=current_confirmation_container, generation_readiness_callback=lambda current_image_path: bool(current_image_path), generation_readiness_inputs=[current_image_control])
        build_video_job_monitor(current_execute_command, current_server_address, current_job_control, current_status_output, result_renderer_callback=render_dwpose_result)
        current_read_history, current_history_outputs = build_generation_history_view(current_execute_command, current_server_address, GENERATION_CLEANUP_SCOPE_TEXT, restore_input_callback=restore_dwpose_inputs, restore_output_components=[*current_input_controls,current_job_control], result_renderer_callback=render_dwpose_result, record_folder_route='/dwpose', allow_individual_delete=True, individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda: current_read_history(1), outputs=current_history_outputs)
    return current_interface_blocks
