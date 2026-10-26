"""Wan2.2 Animate의 고정 실험 입력과 공용 이력 화면."""
import base64
from pathlib import Path
import gradio as gr
from generators.wan_animate.contracts import ANIMATE_JOB_STORAGE, validate_animate_request
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_logs import build_execution_logs
from tools.review.common.gradio_video_results import describe_video_generation_status, render_video_generation_result
from tools.review.common.generation_status_lookup import read_existing_generation_status
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT

ANIMATE_INPUT_MODE_CHOICES = ['외형 참조 + 몸 포즈 21장', '외형 참조만 · 실험']
ANIMATE_FIXED_INPUT_SETTINGS = {'width': 832, 'height': 480, 'frames': 21, 'steps': 20, 'seed': 42, 'flow_shift': 5.0, 'guidance_scale': 1.0}


def execute_animate_command(current_command_name, current_payload_record):
    return execute_remote_management_command('wan22-animate', current_command_name, current_payload_record)


def build_animate_payload(current_reference_path, current_pose_paths, current_input_mode, current_prompt_text):
    if not current_reference_path:
        raise ValueError('외형 참조 PNG 1장을 첨부하세요.')
    if current_input_mode not in ANIMATE_INPUT_MODE_CHOICES:
        raise ValueError('지원하지 않는 입력 방식입니다.')
    current_pose_paths = current_pose_paths or []
    if current_input_mode == ANIMATE_INPUT_MODE_CHOICES[0] and len(current_pose_paths) != 21:
        raise ValueError('몸 포즈 PNG를 정확히 21장 첨부하세요.')
    if current_input_mode == ANIMATE_INPUT_MODE_CHOICES[1] and current_pose_paths:
        raise ValueError('참조만 실험하려면 몸 포즈 첨부를 비우세요.')
    current_image_paths = [current_reference_path, *current_pose_paths]
    current_payload_record = {'action': 'generate', 'prompt': current_prompt_text, 'images': [base64.b64encode(Path(current_image_path).read_bytes()).decode() for current_image_path in current_image_paths], **ANIMATE_FIXED_INPUT_SETTINGS}
    validate_animate_request(current_payload_record)
    return current_payload_record


def restore_animate_inputs(current_history_record):
    current_job_directory = (ANIMATE_JOB_STORAGE / current_history_record['id']).resolve()
    if current_job_directory.parent != ANIMATE_JOB_STORAGE.resolve():
        raise ValueError('이력 경로 오류')
    current_request_record = current_history_record['request']
    current_image_paths = []
    for current_reference_name in current_request_record['references']:
        current_reference_path = (current_job_directory / current_reference_name).resolve()
        if current_reference_path.parent != current_job_directory or not current_reference_path.is_file():
            raise ValueError('이력 입력 사본 누락 또는 경로 오류')
        current_image_paths.append(str(current_reference_path))
    if len(current_image_paths) not in (1, 22):
        raise ValueError('저장된 참조·포즈 개수 오류')
    return current_image_paths[0], current_image_paths[1:], ANIMATE_INPUT_MODE_CHOICES[0 if len(current_image_paths) == 22 else 1], current_request_record['prompt'], current_history_record['id']


def check_animate_readiness(current_reference_path, current_pose_paths, current_input_mode, current_prompt_text):
    return bool(current_reference_path and current_prompt_text.strip() and ((current_input_mode == ANIMATE_INPUT_MODE_CHOICES[0] and len(current_pose_paths or []) == 21) or (current_input_mode == ANIMATE_INPUT_MODE_CHOICES[1] and not current_pose_paths)))


def build_animate_interface(current_server_address, current_command_callback=None):
    current_execute_command = current_command_callback or execute_animate_command
    with gr.Blocks(title='Wan2.2 Animate 영상 생성기') as current_interface_blocks:
        gr.Markdown('## Wan2.2 Animate 14B Q4 실험 생성기\n외형 참조와 전처리된 몸 포즈를 사용합니다. 얼굴 영상·배경 교체·가속 LoRA는 사용하지 않습니다.')
        current_model_status = gr.Markdown('모델 준비 상태 확인 중')
        current_model_refresh = gr.Button('모델 준비 상태 확인')
        def read_animate_model_status():
            try:
                return current_execute_command('model-status', {})['message']
            except Exception as current_status_error:
                return f'모델 상태 확인 실패: {current_status_error}'
        current_model_refresh.click(read_animate_model_status, outputs=current_model_status, queue=False)
        current_interface_blocks.load(read_animate_model_status, outputs=current_model_status)
        current_mode_control = gr.Radio(choices=ANIMATE_INPUT_MODE_CHOICES, value=ANIMATE_INPUT_MODE_CHOICES[0], label='입력 방식')
        current_reference_control = gr.Image(type='filepath', sources=['upload'], image_mode='RGB', format='png', label='외형 참조 PNG · 832×480 · 1장')
        current_poses_control = gr.File(file_count='multiple', file_types=['.png'], label='몸 포즈 PNG · 832×480 · 정확히 21장 · 업로드 순서')
        gr.Markdown('전처리된 관절 포즈를 순서대로 첨부하세요. ANNY RGB 렌더 원본은 포즈 입력이 아닙니다. 자동 전처리·크기 보정·프레임 반복은 하지 않습니다. 참조만 실험할 때는 포즈 첨부를 비우세요.')
        current_prompt_control = gr.Textbox(label='장면·동작 프롬프트', lines=3, info='입력한 문구가 그대로 전달됩니다. 얼굴·헤어·복장은 외형 참조에서 공급합니다.')
        current_prompt_summary = gr.Markdown('원문 0단어 · 최종 0단어 · 추가 문구 없음')
        current_prompt_control.change(lambda current_prompt_text: f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어 · 추가 문구 없음', current_prompt_control, current_prompt_summary, queue=False)
        gr.Markdown('**고정 실험 설정:** 832×480 · 21프레임(약 1.31초) · 16fps · 20스텝 · Seed 42 · Shift 5 · CFG 1 · UniPC/sgm_uniform. 현재 서비스가 고정값만 허용하므로 시드·설정을 편집하지 않습니다.\n\nAnimate Q4_K_M · UMT5 Q4 · CLIP Vision · 공유 Wan2.1 VAE · CUDA 연산/CPU 가중치 오프로드. 모델 준비 완료는 8GB 추론 성공이나 품질 승인을 뜻하지 않습니다.')
        current_input_controls = [current_reference_control, current_poses_control, current_mode_control, current_prompt_control]
        current_generate_button = gr.Button('대기열에 추가', variant='primary', interactive=False)
        build_button_guidance(current_generate_button, '외형 참조·프롬프트와 선택 방식에 맞는 포즈 21장을 준비하세요. 참조만 실험은 포즈를 비우세요. 모델 준비가 필요합니다.')
        with gr.Column() as current_confirmation_container:
            pass
        current_job_control = gr.Textbox(label='생성 ID')
        current_status_output = gr.Markdown('입력을 준비하세요.')
        current_result_output = gr.HTML('')
        current_result_identity = gr.State('')
        current_log_output, current_log_enabled, _ = build_execution_logs()
        def enqueue_animate_generation(*current_input_values):
            current_job_record = current_execute_command('generate', build_animate_payload(*current_input_values))
            return current_job_record['id'], '공용 GPU 대기열에 등록했습니다.'
        bind_gpu_generation_confirmation(current_generate_button, enqueue_animate_generation, current_input_controls, [current_job_control, current_status_output], generation_confirmation_container=current_confirmation_container, generation_readiness_callback=check_animate_readiness, generation_readiness_inputs=current_input_controls)
        current_generation_timer = gr.Timer(5, active=False)
        def refresh_animate_status(current_job_identifier, current_logs_enabled, current_previous_result):
            if not current_job_identifier:
                return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.Timer(active=False)
            current_status_record = read_existing_generation_status(current_execute_command, current_job_identifier)
            if current_status_record is None:
                return '삭제된 이력입니다.', '', '', '', gr.Timer(active=False)
            current_result_url = current_status_record.get('video', '')
            return describe_video_generation_status(current_status_record), render_video_generation_result(current_job_identifier, current_status_record, current_server_address) if current_result_url and current_result_url != current_previous_result else gr.skip(), current_status_record.get('log', '') if current_logs_enabled else gr.skip(), current_result_url, gr.Timer(active=current_status_record.get('status') not in ('completed', 'failed', 'cancelled', 'paused'))
        current_generation_timer.tick(refresh_animate_status, [current_job_control, current_log_enabled, current_result_identity], [current_status_output, current_result_output, current_log_output, current_result_identity, current_generation_timer], queue=False, show_progress='hidden')
        current_job_control.change(lambda current_job_identifier: gr.Timer(active=bool(current_job_identifier)), current_job_control, current_generation_timer, queue=False)
        current_read_history, current_history_outputs = build_generation_history_view(current_execute_command, current_server_address, GENERATION_CLEANUP_SCOPE_TEXT, restore_input_callback=restore_animate_inputs, restore_output_components=[*current_input_controls, current_job_control], result_renderer_callback=render_video_generation_result, record_folder_route='/wan22-animate', allow_individual_delete=True, individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda: current_read_history(1), outputs=current_history_outputs)
    return current_interface_blocks
