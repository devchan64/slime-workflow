"""Wan2.2 Animate의 참조·포즈·얼굴 입력과 공용 이력 화면."""
import base64
from pathlib import Path
import gradio as gr
from generators.wan_animate.contracts import ANIMATE_JOB_STORAGE, validate_animate_request
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_input_preview import build_input_preview
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_logs import build_execution_logs
from tools.review.common.gradio_video_results import describe_video_generation_status, render_video_generation_result
from tools.review.common.generation_status_lookup import read_existing_generation_status
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT

ANIMATE_DEFAULT_PROMPT_TEXT = '视频中的人在做动作'
ANIMATE_INPUT_MODE_CHOICES = ['몸 포즈 사용 · 얼굴 크롭 첨부 권장', '참조만 · 비표준 조건 제거 실험']


def execute_animate_command(current_command_name, current_payload_record):
    return execute_remote_management_command('wan22-animate', current_command_name, current_payload_record)


def build_animate_payload(current_reference_path, current_pose_paths, current_input_mode, current_prompt_text, current_face_paths=None, current_frame_count=21, current_step_count=20, current_seed_value=42, current_shift_value=5.0, current_guidance_value=1.0, current_output_fps=16, current_width_value=832, current_height_value=480):
    if not current_reference_path:
        raise ValueError('외형 참조 PNG 1장을 첨부하세요.')
    if current_input_mode not in ANIMATE_INPUT_MODE_CHOICES:
        raise ValueError('지원하지 않는 입력 방식입니다.')
    current_pose_paths = current_pose_paths or []
    if current_input_mode == ANIMATE_INPUT_MODE_CHOICES[0] and len(current_pose_paths) != current_frame_count:
        raise ValueError('몸 포즈 PNG 수와 프레임 수를 맞추세요.')
    if current_input_mode == ANIMATE_INPUT_MODE_CHOICES[1] and current_pose_paths:
        raise ValueError('참조만 실험하려면 몸 포즈 첨부를 비우세요.')
    current_face_paths = current_face_paths or []
    if current_face_paths and (not current_pose_paths or len(current_face_paths) != current_frame_count):
        raise ValueError('얼굴 크롭은 몸 포즈와 같은 프레임 수로 첨부하세요.')
    current_image_paths = [current_reference_path, *current_pose_paths, *current_face_paths]
    current_payload_record = {'action': 'generate', 'prompt': current_prompt_text, 'images': [base64.b64encode(Path(current_image_path).read_bytes()).decode() for current_image_path in current_image_paths], 'width':current_width_value, 'height':current_height_value, 'frames':current_frame_count, 'steps':current_step_count, 'seed':current_seed_value, 'flow_shift':current_shift_value, 'guidance_scale':current_guidance_value, 'fps':current_output_fps}
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
    current_frame_count = current_request_record['frames']
    if len(current_image_paths) not in (1, 1+current_frame_count, 1+2*current_frame_count):
        raise ValueError('저장된 참조·포즈·얼굴 개수 오류')
    return (current_image_paths[0], current_image_paths[1:1+current_frame_count], ANIMATE_INPUT_MODE_CHOICES[0 if len(current_image_paths)>1 else 1], current_request_record['prompt'], current_image_paths[1+current_frame_count:], current_frame_count, current_request_record['steps'], current_request_record['seed'], current_request_record['flow_shift'], current_request_record['guidance_scale'], current_request_record.get('fps',16), current_request_record['width'], current_request_record['height'], current_history_record['id'])


def check_animate_readiness(*current_input_values):
    try:
        build_animate_payload(*current_input_values)
        return True
    except (ValueError, OSError, TypeError):
        return False


def render_animation_video_result(current_job_identifier,current_status_record,current_server_address):
    import html
    current_result_html=render_video_generation_result(current_job_identifier,current_status_record,current_server_address)
    for current_preview_label,current_preview_url in current_status_record.get('preprocess_videos',{}).items():
        current_result_html+=f'<p>자동 전처리 · {html.escape(current_preview_label)}</p><video controls loop playsinline width="384" src="{html.escape(current_preview_url,quote=True)}"></video>'
    return current_result_html


def build_animation_video_payload(current_reference_path,current_video_path,current_step_count=20,current_seed_value=42,current_shift_value=5.0,current_guidance_value=1.0,current_width_value=832,current_height_value=480):
    from generators.wan_animate.video_input import ANIMATE_MAX_VIDEO_BYTES
    if not current_reference_path or not current_video_path:
        raise ValueError('캐릭터 참조 이미지와 동작 영상이 필요합니다.')
    if Path(current_video_path).stat().st_size>ANIMATE_MAX_VIDEO_BYTES:
        raise ValueError('MP4 동작 영상은 32MiB 이하여야 합니다.')
    return {'action':'generate','mode':'animation','images':[base64.b64encode(Path(current_reference_path).read_bytes()).decode()],'driving_video':base64.b64encode(Path(current_video_path).read_bytes()).decode(),'steps':current_step_count,'seed':current_seed_value,'flow_shift':current_shift_value,'guidance_scale':current_guidance_value,'width':current_width_value,'height':current_height_value}


def check_animation_video_readiness(current_reference_path,current_video_path,*current_setting_values):
    return bool(current_reference_path and current_video_path)


def restore_animation_video_inputs(current_history_record):
    current_job_root=(ANIMATE_JOB_STORAGE/current_history_record['id']).resolve()
    current_request_record=current_history_record['request']
    if current_job_root.parent!=ANIMATE_JOB_STORAGE.resolve():
        raise ValueError('이력 경로 오류')
    if current_request_record.get('driving_video_file')!='driving.mp4':
        raise gr.Error('이전 PNG 입력 이력입니다. 결과 조회는 가능하며 새 생성에는 원본 동작 영상을 첨부하세요.')
    current_reference_path=(current_job_root/current_request_record['references'][0]).resolve()
    current_video_path=(current_job_root/'driving.mp4').resolve()
    if any(current_input_path.parent!=current_job_root or not current_input_path.is_file() for current_input_path in (current_reference_path,current_video_path)):
        raise ValueError('입력 사본 경로 오류 또는 누락')
    return (str(current_reference_path),str(current_video_path),*(current_request_record[current_field_name] for current_field_name in ('steps','seed','flow_shift','guidance_scale','width','height')),current_history_record['id'])


def build_animate_interface(current_server_address, current_command_callback=None):
    current_execute_command = current_command_callback or execute_animate_command
    with gr.Blocks(title='Wan2.2 Animate 영상 생성기') as current_interface_blocks:
        gr.Markdown('## Wan2.2 Animate 14B Q4 실험 생성기\n캐릭터 이미지와 동작 영상을 입력하면 포즈·얼굴을 자동 추출해 애니메이션을 생성합니다.')
        current_model_status = gr.Markdown('모델 준비 상태 확인 중')
        current_model_refresh = gr.Button('모델 준비 상태 확인')
        def read_animate_model_status():
            try:
                return current_execute_command('model-status', {})['message']
            except Exception as current_status_error:
                return f'모델 상태 확인 실패: {current_status_error}'
        current_model_refresh.click(read_animate_model_status, outputs=current_model_status, queue=False)
        current_interface_blocks.load(read_animate_model_status, outputs=current_model_status)
        gr.Markdown('**용도: 애니메이션** — 참조 캐릭터가 동작 영상의 움직임·표정을 따라 합니다. 인물 교체용은 배경·마스크 처리 미구현으로 사용할 수 없습니다.')
        with gr.Row():
            current_reference_control = gr.Image(type='filepath', sources=['upload'], image_mode='RGB', format='png', label='캐릭터 참조 이미지')
            current_video_control = gr.Video(sources=['upload'], label='동작 영상 · MP4 · 최대 32MiB', include_audio=True)
        gr.Markdown('참조 이미지와 동작 영상을 첨부하면 GPU 작업에서 몸 포즈·얼굴 크롭을 자동 추출합니다. 원본 FPS와 프레임 수를 유지합니다. 현재 로컬 단일 구간 구현은 121프레임까지 지원하며 공식 모델의 길이 제한은 아닙니다. 입력은 출력 비율에 맞춰 여백을 추가합니다.')
        with gr.Row():
            current_steps_control = gr.Number(value=20, minimum=1, maximum=100, precision=0, label='샘플링 스텝 · 공식 기본 20')
            current_seed_control = build_generation_seed(42)
        with gr.Accordion('고급 설정', open=False):
            with gr.Row():
                current_width_control = gr.Number(value=832, minimum=64, maximum=1280, precision=0, label='너비 · 16배수')
                current_height_control = gr.Number(value=480, minimum=64, maximum=1280, precision=0, label='높이 · 16배수')
                current_shift_control = gr.Number(value=5, minimum=0.1, maximum=20, label='Flow Shift · 공식 기본 5')
                current_guidance_control = gr.Number(value=1, minimum=1, maximum=20, label='CFG · 공식 기본 1')
            gr.Markdown('텍스트는 공식 기본 문구 `视频中的人在做动作`를 자동 적용합니다. 원문·최종 1단어(공백 기준). 리타게팅은 미사용으로 고정합니다. 참조와 동작의 체형 차이는 결과에 영향을 줄 수 있습니다. 기본·FLUX 보강 리타게팅과 장편 구간 연결은 아직 지원하지 않습니다.')
        gr.Markdown('[공식 모델카드](https://huggingface.co/Wan-AI/Wan2.2-Animate-14B) · [공식 전처리 가이드](https://github.com/Wan-Video/Wan2.2/blob/main/wan/modules/animate/preprocess/UserGuider.md)\n\n고정: Q4_K_M Animate·UMT5 Q4·CLIP Vision·Wan2.1 VAE·UniPC/sgm_uniform·CUDA 연산/CPU 가중치 오프로드. 양자화·타일 VAE·ComfyUI 실행은 공식 원본과 다릅니다.')
        current_input_controls = [current_reference_control,current_video_control,current_steps_control,current_seed_control,current_shift_control,current_guidance_control,current_width_control,current_height_control]
        current_generate_button = gr.Button('대기열에 추가', variant='primary', interactive=False)
        build_button_guidance(current_generate_button, '캐릭터 이미지와 MP4 동작 영상을 첨부하세요. 모델과 CUDA 전처리 준비가 필요합니다.')
        with gr.Column() as current_confirmation_container:
            pass
        current_job_control = gr.Textbox(label='생성 ID')
        current_status_output = gr.Markdown('입력을 준비하세요.')
        current_result_output = gr.HTML('')
        current_result_identity = gr.State('')
        current_log_output, current_log_enabled, _ = build_execution_logs()
        def enqueue_animate_generation(*current_input_values):
            current_job_record = current_execute_command('generate', build_animation_video_payload(*current_input_values))
            return current_job_record['id'], '공용 GPU 대기열에 등록했습니다.'
        bind_gpu_generation_confirmation(current_generate_button, enqueue_animate_generation, current_input_controls, [current_job_control, current_status_output], generation_confirmation_container=current_confirmation_container, generation_readiness_callback=check_animation_video_readiness, generation_readiness_inputs=current_input_controls)
        current_generation_timer = gr.Timer(5, active=False)
        def refresh_animate_status(current_job_identifier, current_logs_enabled, current_previous_result):
            if not current_job_identifier:
                return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.Timer(active=False)
            current_status_record = read_existing_generation_status(current_execute_command, current_job_identifier)
            if current_status_record is None:
                return '삭제된 이력입니다.', '', '', '', gr.Timer(active=False)
            current_result_url = current_status_record.get('video', '')
            return describe_video_generation_status(current_status_record), render_animation_video_result(current_job_identifier, current_status_record, current_server_address) if current_result_url and current_result_url != current_previous_result else gr.skip(), current_status_record.get('log', '') if current_logs_enabled else gr.skip(), current_result_url, gr.Timer(active=current_status_record.get('status') not in ('completed', 'failed', 'cancelled', 'paused'))
        current_generation_timer.tick(refresh_animate_status, [current_job_control, current_log_enabled, current_result_identity], [current_status_output, current_result_output, current_log_output, current_result_identity, current_generation_timer], queue=False, show_progress='hidden')
        current_job_control.change(lambda current_job_identifier: gr.Timer(active=bool(current_job_identifier)), current_job_control, current_generation_timer, queue=False)
        current_read_history, current_history_outputs = build_generation_history_view(current_execute_command, current_server_address, GENERATION_CLEANUP_SCOPE_TEXT, restore_input_callback=restore_animation_video_inputs, restore_output_components=[*current_input_controls, current_job_control], result_renderer_callback=render_animation_video_result, record_folder_route='/wan22-animate', allow_individual_delete=True, individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda: current_read_history(1), outputs=current_history_outputs)
    return current_interface_blocks
