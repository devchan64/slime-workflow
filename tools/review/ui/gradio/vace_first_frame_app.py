"""첫 프레임 한 장으로 VACE 영상을 만드는 F2V GUI."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import gradio as gr
from tools.review.ui.gradio.vace_timeline_app import (
    build_timeline_payload, restore_timeline_inputs,
    warn_image_resolution,
)
from generators.vace.first_frame import VACE_FIRST_FRAME_ROOT
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_logs import build_execution_logs
from tools.review.common.gradio_video_results import (
    describe_video_frame_duration, describe_video_generation_status,
    render_video_generation_result,
)
from tools.review.common.generation_status_lookup import read_existing_generation_status
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT
from tools.review.ui.gradio.management_menu_app import compose_management_interface

FIRST_FRAME_DEFAULT_COUNT = 81
FIRST_FRAME_DEFAULT_STEPS = 50
FIRST_FRAME_DEFAULT_SHIFT = 3.0
FIRST_FRAME_DEFAULT_GUIDANCE = 5.0
FIRST_FRAME_DEFAULT_CONDITIONING = 1.0


def execute_first_frame_command(current_command_name, current_payload_record):
    return execute_remote_management_command('wan21-vace-f2v', current_command_name, current_payload_record)


def build_first_frame_payload(current_image_path, current_prompt_text, current_negative_text,
        current_frame_count, current_seed_value, current_steps_value, current_shift_value,
        current_guidance_value, current_conditioning_value, current_padding_color):
    if not current_image_path:
        raise ValueError('첫 프레임 이미지를 첨부하세요.')
    current_payload_record = build_timeline_payload(
        [current_image_path], [[1, False]], current_prompt_text, current_negative_text,
        current_frame_count, current_seed_value, '832×480', current_steps_value,
        current_shift_value, current_guidance_value, current_conditioning_value,
        None, current_padding_color)
    current_payload_record['tag'] = 'F2V · 첫 프레임 보존'
    return current_payload_record


def restore_first_frame_inputs(current_history_record):
    current_saved_inputs = restore_timeline_inputs(current_history_record, VACE_FIRST_FRAME_ROOT)
    if current_saved_inputs[1] != [[1, False]] or len(current_saved_inputs[0]) != 1 or current_saved_inputs[11]:
        raise gr.Error('첫 프레임 1장 보존 방식의 이력만 불러올 수 있습니다. 다른 작업은 V2V에서 불러오세요.')
    return (current_saved_inputs[0][0], *current_saved_inputs[2:6],
            *current_saved_inputs[7:11], current_saved_inputs[12], current_saved_inputs[-1])


def build_first_frame_interface(current_server_address):
    with gr.Blocks(title='Wan2.1 VACE F2V 생성기') as current_interface_blocks:
        gr.Markdown('## Wan2.1 VACE 1.3B F2V 생성기\n첫 프레임 이미지 1장을 보존 조건으로 사용하고 이후 프레임을 생성합니다. 참조 전용 R2V와 구분됩니다.')
        current_image_control = gr.Image(type='filepath', sources=['upload'], label='첫 프레임 이미지 · 필수 1장')
        current_image_control.change(lambda current_image_path: warn_image_resolution([current_image_path] if current_image_path else []), current_image_control, queue=False)
        gr.Markdown('첫 프레임은 검은 마스크, 이후 프레임은 흰 마스크로 고정합니다. VAE 복원에 따른 미세한 차이는 생길 수 있습니다. 입력 원본은 보존합니다.')
        current_prompt_control = gr.Textbox(label='장면·동작 프롬프트', value='', lines=4)
        current_prompt_summary = gr.Markdown('원문 0단어 · 최종 0단어 · 추가 문구 없음')
        current_prompt_control.change(lambda current_prompt_text: f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어 · 추가 문구 없음', current_prompt_control, current_prompt_summary, queue=False)
        gr.Button('장면 프롬프트 초기화').click(lambda: '', outputs=current_prompt_control, queue=False)
        with gr.Accordion('부정 프롬프트 · 기본값 없음', open=False):
            current_negative_control = gr.Textbox(value='', label='부정 프롬프트', lines=2)
            current_negative_summary = gr.Markdown('원문 0단어 · 최종 0단어')
            current_negative_control.change(lambda current_prompt_text: f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어', current_negative_control, current_negative_summary, queue=False)
            gr.Button('부정 프롬프트 초기화').click(lambda: '', outputs=current_negative_control, queue=False)
        gr.Markdown('고정: Wan2.1 VACE 1.3B · 832×480 · 16fps · UniPC · CUDA 연산 / CPU 가중치 오프로드. 다른 크기는 비율을 유지해 맞추고 여백을 채웁니다.')
        current_padding_control = gr.ColorPicker(value='#FFFFFF', label='여백 색상 · 기본 흰색')
        current_frames_control = gr.Number(value=FIRST_FRAME_DEFAULT_COUNT, precision=0, minimum=1, maximum=161, step=4, label='프레임 수 · 4n+1 · 1~161')
        current_duration_output = gr.Markdown(describe_video_frame_duration(FIRST_FRAME_DEFAULT_COUNT))
        current_frames_control.change(describe_video_frame_duration, current_frames_control, current_duration_output, queue=False)
        current_seed_control = build_generation_seed(default_seed_value=42)
        with gr.Accordion('고급 설정', open=False):
            current_steps_control = gr.Number(value=FIRST_FRAME_DEFAULT_STEPS, precision=0, minimum=1, maximum=200, label='추론 스텝 · 1~200', info='20: 빠른 검토용 · 30: 레퍼런스 · 50: 안정값(기본값). 반복 횟수이며 높을수록 생성 시간이 늘어납니다.')
            current_shift_control = gr.Number(value=FIRST_FRAME_DEFAULT_SHIFT, minimum=0.1, maximum=30, label='Flow shift · 0.1~30', info='기본 3. 추론 스텝의 노이즈 구간 배분을 조절합니다.')
            current_guidance_control = gr.Number(value=FIRST_FRAME_DEFAULT_GUIDANCE, minimum=1, maximum=20, label='텍스트 가이던스 (CFG) · 1~20', info='기본 5. 프롬프트 유도 강도이며 높으면 왜곡이 늘 수 있습니다.')
            current_conditioning_control = gr.Number(value=FIRST_FRAME_DEFAULT_CONDITIONING, minimum=0, maximum=2, label='조건 강도 · 0~2', info='기본 1. 첫 프레임과 마스크 조건의 영향력입니다. 결과 변화를 비교하기 쉽도록 다른 입력값은 유지하고, 0~2 범위에서 0.5씩 조정하며 확인하세요.')
        current_input_controls = [current_image_control, current_prompt_control, current_negative_control, current_frames_control, current_seed_control, current_steps_control, current_shift_control, current_guidance_control, current_conditioning_control, current_padding_control]
        current_generate_button = gr.Button('대기열에 추가', variant='primary', interactive=False)
        build_button_guidance(current_generate_button, '첫 프레임 이미지와 장면 프롬프트를 입력하세요. 확인 후 대기열에 등록됩니다.')
        with gr.Column() as current_confirmation_container:
            pass
        current_job_control = gr.Textbox(label='생성 ID')
        current_status_display = gr.Markdown('입력을 확인한 뒤 대기열에 추가하세요.')
        current_result_display = gr.HTML('')
        current_result_identity = gr.State('')
        current_log_output, current_log_refresh, _ = build_execution_logs()
        def start_first_frame_generation(*current_input_values):
            current_job_record = execute_first_frame_command('generate', build_first_frame_payload(*current_input_values))
            return current_job_record['id'], 'GPU 대기열에 등록했습니다.'
        bind_gpu_generation_confirmation(current_generate_button, start_first_frame_generation, current_input_controls, [current_job_control, current_status_display], generation_confirmation_container=current_confirmation_container, generation_readiness_callback=lambda current_image_path, current_prompt_text: bool(current_image_path and current_prompt_text.strip()), generation_readiness_inputs=[current_image_control, current_prompt_control])
        def refresh_first_frame_result(current_job_identifier, current_logs_enabled, current_previous_result):
            if not current_job_identifier:
                return (gr.skip(),) * 4
            current_status_record = read_existing_generation_status(execute_first_frame_command, current_job_identifier)
            if current_status_record is None:
                return '삭제된 이력입니다.', '', '', ''
            current_result_url = current_status_record.get('video', '')
            return (describe_video_generation_status(current_status_record),
                    render_video_generation_result(current_job_identifier, current_status_record, current_server_address) if current_result_url and current_result_url != current_previous_result else gr.skip(),
                    current_status_record.get('log', '') if current_logs_enabled else gr.skip(), current_result_url)
        gr.Timer(5).tick(refresh_first_frame_result, [current_job_control, current_log_refresh, current_result_identity], [current_status_display, current_result_display, current_log_output, current_result_identity], queue=False, show_progress='hidden')
        gr.Markdown('F2V 대기열과 생성 이력은 V2V와 분리됩니다. 이력 삭제·초기화는 F2V 작업에만 적용됩니다. GPU 자원은 공용 실행기가 순서대로 배정합니다.')
        current_read_history, current_history_outputs = build_generation_history_view(execute_first_frame_command, current_server_address, GENERATION_CLEANUP_SCOPE_TEXT, restore_input_callback=restore_first_frame_inputs, restore_output_components=[*current_input_controls, current_job_control], result_renderer_callback=render_video_generation_result, record_folder_route='/wan21-vace-f2v', allow_individual_delete=True, individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda: current_read_history(1), outputs=current_history_outputs)
    return current_interface_blocks


if __name__ == '__main__':
    current_argument_parser = argparse.ArgumentParser()
    current_argument_parser.add_argument('--port', type=int, required=True)
    current_argument_parser.add_argument('--review-port', type=int, required=True)
    current_argument_parser.add_argument('--owner-pid', type=int, required=True)
    current_argument_parser.add_argument('--root-path', default='/management/frame/vace-f2v-generator/')
    current_argument_values = current_argument_parser.parse_args()
    compose_management_interface(build_first_frame_interface(f'http://127.0.0.1:{current_argument_values.review_port}'), current_argument_values.review_port).queue().launch(server_name='127.0.0.1', server_port=current_argument_values.port, root_path=current_argument_values.root_path, allowed_paths=[])
