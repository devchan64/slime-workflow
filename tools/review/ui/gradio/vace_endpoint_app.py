"""VACE 경계 프레임 생성기의 공용 입력·이력 화면."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import gradio as gr
from tools.review.ui.gradio.vace_timeline_app import (
    build_timeline_payload, restore_timeline_inputs,
    warn_image_resolution,
)
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


def build_endpoint_frame_interface(current_server_address, *, current_endpoint_mode=True,
        current_command_callback=None, current_payload_callback=None, current_restore_callback=None):
    current_execute_command = current_command_callback
    current_build_payload = current_payload_callback
    current_restore_inputs = current_restore_callback
    current_mode_label = 'FL2V' if current_endpoint_mode else 'F2V'
    current_service_route = '/wan21-vace-fl2v' if current_endpoint_mode else '/wan21-vace-f2v'
    with gr.Blocks(title=f'Wan2.1 VACE {current_mode_label} 생성기') as current_interface_blocks:
        gr.Markdown(f'## Wan2.1 VACE 1.3B {current_mode_label} 생성기\n' + ('첫·끝 이미지 2장을 보존 조건으로 사용하고 사이 프레임을 생성합니다.' if current_endpoint_mode else '첫 프레임 이미지 1장을 보존 조건으로 사용하고 이후 프레임을 생성합니다. 참조 전용 R2V와 구분됩니다.'))
        current_image_control = gr.Image(type='filepath', sources=['upload'], label='첫 프레임 이미지 · 필수 1장')
        current_image_control.change(lambda current_image_path: warn_image_resolution([current_image_path] if current_image_path else []), current_image_control, queue=False)
        current_image_controls = [current_image_control]
        if current_endpoint_mode:
            current_last_control = gr.Image(type='filepath', sources=['upload'], label='마지막 프레임 이미지 · 필수 1장')
            current_last_control.change(lambda current_image_path: warn_image_resolution([current_image_path] if current_image_path else []), current_last_control, queue=False)
            current_image_controls.append(current_last_control)
        gr.Markdown(('첫·끝 프레임은 검은 마스크, 사이 프레임은 흰 마스크로 고정합니다. 마지막 이미지는 설정한 마지막 프레임에 자동 배치됩니다.' if current_endpoint_mode else '첫 프레임은 검은 마스크, 이후 프레임은 흰 마스크로 고정합니다.') + ' VAE 복원에 따른 미세한 차이는 생길 수 있습니다. 입력 원본은 보존합니다.')
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
        current_frames_control = gr.Number(value=FIRST_FRAME_DEFAULT_COUNT, precision=0, minimum=5 if current_endpoint_mode else 1, maximum=161, step=4, label='프레임 수 · 4n+1 · ' + ('5~161' if current_endpoint_mode else '1~161'))
        current_duration_output = gr.Markdown(describe_video_frame_duration(FIRST_FRAME_DEFAULT_COUNT))
        current_frames_control.change(describe_video_frame_duration, current_frames_control, current_duration_output, queue=False)
        current_seed_control = build_generation_seed(default_seed_value=42)
        with gr.Accordion('고급 설정', open=False):
            gr.Markdown('공식 예제와 이 페이지의 실험 기준을 구분해 안내합니다. 입력 범위는 이 생성기의 허용 범위이며 공식 권장 범위가 아닙니다.')
            current_steps_control = gr.Number(value=FIRST_FRAME_DEFAULT_STEPS, precision=0, minimum=1, maximum=200, label='추론 스텝 · 1~200', info='페이지 실험 기준: 20 빠른 검토용 · 30 레퍼런스 · 50 안정값(기본). 공식 모델카드 예제는 30, Diffusers API 기본은 50입니다. 스텝을 늘리면 시간이 늘며 걷기·방향 개선을 보장하지 않습니다.')
            current_shift_control = gr.Number(value=FIRST_FRAME_DEFAULT_SHIFT, minimum=0.1, maximum=30, label='Flow shift · 0.1~30', info='기본 3. 노이즈 구간별 추론 스텝 배분을 조절합니다. 모델카드 주석은 480P에 3, 720P에 5를 안내합니다. 현재 480P 페이지는 3을 기준으로 비교하세요. 동작이나 카메라 방향을 직접 고정하는 값은 아닙니다.')
            current_guidance_control = gr.Number(value=FIRST_FRAME_DEFAULT_GUIDANCE, minimum=1, maximum=20, label='텍스트 가이던스 (CFG) · 1~20', info='공식 예제·API 기본 5. 텍스트 지시의 영향력입니다. 1보다 클 때 CFG가 활성화되며, 높이면 문구를 더 따르도록 유도하지만 화질이 떨어질 수 있습니다. 방향 유지를 보장하지 않습니다.')
            current_conditioning_control = gr.Number(value=FIRST_FRAME_DEFAULT_CONDITIONING, minimum=0, maximum=2, label='조건 강도 · 0~2', info='API 기본 1. 입력 프레임·마스크에서 만든 조건을 모델에 반영하는 배율입니다. 첫 프레임만의 별도 참조 강도는 아닙니다. 페이지 실험 기준: 다른 입력값을 유지하고 0~2 범위에서 0.5씩 비교하세요. 강도가 높다고 보행이나 방향이 더 잘 유지되지는 않습니다.')
            gr.Markdown('출처: [Wan2.1 VACE 1.3B 모델카드](https://huggingface.co/Wan-AI/Wan2.1-VACE-1.3B-diffusers) · [Diffusers WanVACEPipeline](https://huggingface.co/docs/diffusers/api/pipelines/wan#diffusers.WanVACEPipeline)\n\n모델카드의 30스텝 예제는 첫·끝 프레임 입력 방식입니다. 입력 이미지와 장면에 따라 품질은 달라집니다. 20/50 용도 구분과 조건강도 0.5 간격은 페이지 실험 안내입니다. 같은 이미지·프롬프트·시드에서 한 값씩 바꿔 비교하세요.')
        current_input_controls = [*current_image_controls, current_prompt_control, current_negative_control, current_frames_control, current_seed_control, current_steps_control, current_shift_control, current_guidance_control, current_conditioning_control, current_padding_control]
        current_generate_button = gr.Button('대기열에 추가', variant='primary', interactive=False)
        build_button_guidance(current_generate_button, ('첫·끝 프레임 이미지와 장면 프롬프트를 입력하세요.' if current_endpoint_mode else '첫 프레임 이미지와 장면 프롬프트를 입력하세요.') + ' 확인 후 대기열에 등록됩니다.')
        with gr.Column() as current_confirmation_container:
            pass
        current_job_control = gr.Textbox(label='생성 ID')
        current_status_display = gr.Markdown('입력을 확인한 뒤 대기열에 추가하세요.')
        current_result_display = gr.HTML('')
        current_result_identity = gr.State('')
        current_log_output, current_log_refresh, _ = build_execution_logs()
        def start_first_frame_generation(*current_input_values):
            current_job_record = current_execute_command('generate', current_build_payload(*current_input_values))
            return current_job_record['id'], 'GPU 대기열에 등록했습니다.'
        bind_gpu_generation_confirmation(current_generate_button, start_first_frame_generation, current_input_controls, [current_job_control, current_status_display], generation_confirmation_container=current_confirmation_container, generation_readiness_callback=lambda *current_input_values: bool(all(current_input_values[:-1]) and current_input_values[-1].strip()), generation_readiness_inputs=[*current_image_controls, current_prompt_control])
        current_generation_timer = gr.Timer(5, active=False)
        def refresh_first_frame_result(current_job_identifier, current_logs_enabled, current_previous_result):
            if not current_job_identifier:
                return (*((gr.skip(),) * 4), gr.Timer(active=False))
            current_status_record = read_existing_generation_status(current_execute_command, current_job_identifier)
            if current_status_record is None:
                return '삭제된 이력입니다.', '', '', '', gr.Timer(active=False)
            current_result_url = current_status_record.get('video', '')
            return (describe_video_generation_status(current_status_record),
                    render_video_generation_result(current_job_identifier, current_status_record, current_server_address) if current_result_url and current_result_url != current_previous_result else gr.skip(),
                    current_status_record.get('log', '') if current_logs_enabled else gr.skip(), current_result_url, gr.Timer(active=current_status_record.get('status') not in ('completed', 'failed', 'cancelled', 'paused')))
        current_generation_timer.tick(refresh_first_frame_result, [current_job_control, current_log_refresh, current_result_identity], [current_status_display, current_result_display, current_log_output, current_result_identity, current_generation_timer], queue=False, show_progress='hidden')
        current_job_control.change(lambda current_job_identifier: gr.Timer(active=bool(current_job_identifier)), current_job_control, current_generation_timer, queue=False)
        gr.Markdown(f'{current_mode_label} 대기열과 생성 이력은 다른 생성기와 분리됩니다. 이력 삭제·초기화는 {current_mode_label} 작업에만 적용됩니다. GPU 자원은 공용 실행기가 순서대로 배정합니다.')
        current_read_history, current_history_outputs = build_generation_history_view(current_execute_command, current_server_address, GENERATION_CLEANUP_SCOPE_TEXT, restore_input_callback=current_restore_inputs, restore_output_components=[*current_input_controls, current_job_control], result_renderer_callback=render_video_generation_result, record_folder_route=current_service_route, allow_individual_delete=True, individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda: current_read_history(1), outputs=current_history_outputs)
    return current_interface_blocks
