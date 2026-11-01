"""VACE-Fun 텍스트·외형 참조·첫 프레임 입력 화면."""
from pathlib import Path
import base64
import io
from contextlib import nullcontext
from PIL import Image, ImageOps
import gradio as gr
from generators.wan_vace.contracts import VACE_DEFAULT_SETTINGS, VACE_JOB_STORAGE, validate_vace_request
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_video_results import render_video_generation_result, build_video_job_monitor, describe_video_frame_duration
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT
from tools.review.common.gradio_reference_images import build_reference_image_inputs

VACE_INPUT_CHOICES = [('키모도 DWPose 영상 + 캐릭터 참조', 'pose'), ('영상 부분 편집 + 외형 참조', 'video_edit'), ('외형 참조 + 텍스트 (R2V)', 'reference'), ('첫 프레임 + 텍스트 (I2V)', 'first_frame'), ('텍스트만 (T2V)', 'text')]


def execute_vace_command(current_command_name, current_payload_record):
    return execute_remote_management_command('wan22-vace', current_command_name, current_payload_record)


def build_vace_payload(current_input_mode, current_reference_path, current_prompt_text, current_negative_text, current_frame_count, current_seed_value, current_steps_value, current_shift_value, current_guidance_value, current_strength_value, current_edit_video=None, current_edit_mask=None, current_pose_video=None):
    for current_integer_value in (current_frame_count, current_seed_value, current_steps_value):
        if isinstance(current_integer_value, bool) or not isinstance(current_integer_value, (int, float)) or not float(current_integer_value).is_integer():
            raise ValueError('프레임·시드·스텝은 정수여야 합니다.')
    current_encoded_images = []
    if current_input_mode == 'text' and current_reference_path:
        raise ValueError('텍스트만 모드에서는 첨부 이미지를 지워 주세요.')
    if current_reference_path:
        with (nullcontext(current_reference_path) if isinstance(current_reference_path, Image.Image) else Image.open(current_reference_path)) as current_image_object:
            current_image_object = ImageOps.contain(current_image_object.convert('RGBA'), (832, 480), Image.Resampling.LANCZOS)
            current_canvas_image = Image.new('RGB', (832, 480), 'white')
            current_canvas_image.paste(current_image_object, ((832-current_image_object.width)//2, (480-current_image_object.height)//2), current_image_object)
            current_image_buffer = io.BytesIO()
            current_canvas_image.save(current_image_buffer, format='PNG')
            current_encoded_images.append(base64.b64encode(current_image_buffer.getvalue()).decode())
    current_payload_record = dict(action='generate', mode=current_input_mode, prompt=current_prompt_text, negative_prompt=current_negative_text, images=current_encoded_images, width=832, height=480, frames=int(current_frame_count), seed=int(current_seed_value), steps=int(current_steps_value), flow_shift=current_shift_value, guidance_scale=current_guidance_value, reference_strength=current_strength_value)
    if current_input_mode == 'pose':
        if not current_pose_video or current_edit_video or current_edit_mask:
            raise ValueError('DWPose MP4를 첨부하고 부분 편집 영상·마스크는 비워 주세요.')
        current_payload_record['pose_video'] = base64.b64encode(Path(current_pose_video).read_bytes()).decode()
    elif current_pose_video:
        raise ValueError('포즈 모드 외에는 DWPose 영상을 비워 주세요.')
    if current_input_mode == 'video_edit':
        if not current_edit_video or not current_edit_mask:
            raise ValueError('원본 MP4와 편집 마스크 MP4가 필요합니다.')
        current_payload_record.update(edit_video=base64.b64encode(Path(current_edit_video).read_bytes()).decode(), edit_mask=base64.b64encode(Path(current_edit_mask).read_bytes()).decode())
    elif current_edit_video or current_edit_mask:
        raise ValueError('영상 편집 외 모드에서는 영상·마스크를 비워 주세요.')
    validate_vace_request(current_payload_record)
    return current_payload_record


def restore_vace_inputs(current_history_record):
    current_job_directory = (VACE_JOB_STORAGE/current_history_record['id']).resolve()
    if current_job_directory.parent != VACE_JOB_STORAGE.resolve():
        raise ValueError('이력 경로 오류')
    current_request_record = current_history_record['request']
    current_reference_path = None
    if current_request_record['references']:
        current_reference_file = (current_job_directory/current_request_record['references'][0]).resolve()
        if current_reference_file.parent != current_job_directory or not current_reference_file.is_file():
            raise ValueError('이력 입력 사본 누락 또는 경로 오류')
        current_reference_path = str(current_reference_file)
    return (current_request_record['mode'], current_reference_path, current_request_record['prompt'], current_request_record['negative_prompt'], current_request_record['frames'], current_request_record['seed'], current_request_record['steps'], current_request_record['flow_shift'], current_request_record['guidance_scale'], current_request_record['reference_strength'], str(current_job_directory/'edit-video.mp4') if current_request_record['mode']=='video_edit' else None, str(current_job_directory/'edit-mask.mp4') if current_request_record['mode']=='video_edit' else None, str(current_job_directory/'pose-video.mp4') if current_request_record['mode']=='pose' else None, current_history_record['id'])


def check_vace_readiness(current_model_ready, current_input_mode, current_reference_path, current_prompt_text, current_edit_video=None, current_edit_mask=None, current_pose_video=None):
    if current_input_mode == 'pose':
        return bool(current_model_ready and current_prompt_text.strip() and current_reference_path and current_pose_video and not current_edit_video and not current_edit_mask)
    if current_pose_video:
        return False
    if current_input_mode == 'video_edit':
        return bool(current_model_ready and current_prompt_text.strip() and current_reference_path and current_edit_video and current_edit_mask)
    if current_edit_video or current_edit_mask:
        return False
    return bool(current_model_ready and current_prompt_text and current_prompt_text.strip() and ((current_input_mode == 'text' and not current_reference_path) or (current_input_mode in ('reference', 'first_frame') and current_reference_path)))


def build_vace_interface(current_server_address, current_command_callback=None):
    current_execute_command = current_command_callback or execute_vace_command
    with gr.Blocks(title='Wan2.2 VACE-Fun 생성기') as current_interface_blocks:
        gr.Markdown('## Wan2.2 VACE-Fun A14B 생성기\n키모도 DWPose 영상과 캐릭터 참조 이미지로 동작을 따라 생성할 수 있습니다. 텍스트·이미지 생성도 지원합니다. 영상 부분 편집은 원본 MP4·흰색 편집 마스크·외형 참조를 함께 사용합니다.')
        current_model_ready = gr.State(False)
        current_model_status = gr.Markdown('모델 준비 상태 확인 중')
        current_model_refresh = gr.Button('모델 준비 상태 확인')
        def read_vace_model_status():
            try:
                current_model_record = current_execute_command('model-status', {})
                return current_model_record['message'], current_model_record['ready']
            except Exception as current_status_error:
                return f'모델 상태 확인 실패: {current_status_error}', False
        current_refresh_event = current_model_refresh.click(read_vace_model_status, outputs=[current_model_status, current_model_ready], queue=False)
        current_model_load = current_interface_blocks.load(read_vace_model_status, outputs=[current_model_status, current_model_ready])
        current_mode_control = gr.Radio(choices=VACE_INPUT_CHOICES, value=VACE_DEFAULT_SETTINGS['mode'], label='생성 모드')
        current_reference_panel, current_reference_controls = build_reference_image_inputs(reference_image_mode='RGBA', reference_slot_count=1, reference_slot_labels=['외형 참조 또는 첫 프레임 · 1장'])
        current_reference_control = current_reference_controls[0]
        gr.Markdown('**외형 참조:** 캐릭터의 외형을 전달하며 첫 화면을 고정하지 않습니다. **첫 프레임:** 첨부 이미지를 시작 장면 조건으로 전달합니다. **텍스트만:** 이미지를 비우세요.\n\n입력은 비율을 유지해 832×480 흰 여백으로 맞추며 원본은 보존합니다. 여백도 이미지 내용으로 인식될 수 있으므로 가능하면 출력과 같은 비율의 이미지를 사용하세요.')
        current_pose_video = gr.Video(sources=['upload'], label='키모도 DWPose MP4 · 832×480 · 16fps · 포즈 모드 전용')
        gr.Markdown('포즈 모드는 키모도의 처리된 DWPose MP4와 캐릭터 참조 이미지 1장을 사용합니다. 포즈를 재추출하지 않으며 앞에서부터 지정 프레임을 사용합니다. 부족한 프레임은 반복하지 않습니다. 편집 마스크는 첨부하지 마세요.')
        with gr.Row():
            current_edit_video = gr.Video(sources=['upload'], label='부분 편집 원본 · 832×480 · 16fps MP4')
            current_edit_mask = gr.Video(sources=['upload'], label='편집 마스크 · 흰색 재생성 / 검정 보존 조건')
        gr.Markdown('부분 편집은 원본 영상의 얼굴 등 지정 영역을 다시 생성합니다. 마스크 밖도 모델 출력에서 달라질 수 있으며 원본과 자동 합성하지 않습니다.')
        current_prompt_control = gr.Textbox(label='장면·동작 프롬프트', lines=3, placeholder='The character walks four steps. Full body, fixed camera.', info='주체 → 동작 → 카메라 순서로 짧게 작성하세요. 입력한 문구를 그대로 전달합니다. 걸음 수는 보장되지 않습니다.')
        current_prompt_summary = gr.Markdown('원문 0단어 · 최종 0단어 · 추가 문구 없음')
        current_prompt_control.change(lambda current_prompt_text: f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어 · 추가 문구 없음', current_prompt_control, current_prompt_summary, queue=False)
        with gr.Accordion('예시 목록 · 프롬프트와 생성 속성', open=False):
            gr.Markdown('''입력 참고용 실행 예시입니다. 참조 이미지는 직접 첨부하세요.

| 예시 | 양성 프롬프트 원문 | 단어 수 · 원문/최종 | 부정 프롬프트 | 입력 모드 | 해상도 | 프레임 / FPS | 스텝 | 시드 | CFG | Flow shift | 참조 강도 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 앞을 보며 같은 방향으로 걷기 | The character walks while looking ahead, maintaining the same heading. Show the full body. | 14 / 14 · 추가 문구 없음 | 없음 | 외형 참조 1장 (R2V) | 832×480 | 81 / 16 | 30 | 42 | 5 | 12 | 1 |

기준 생성 ID: `2026-10-28_21-53-52-058bb9fb` · VACE-Fun A14B Q4_K_M · UMT5 BF16 비양자화 · Wan2.1 VAE · Euler/FlowMatch · 전문가 경계 0.875.
''')
        with gr.Accordion('부정 프롬프트', open=False):
            current_negative_control = gr.Textbox(label='부정 프롬프트', value='', info='필요한 제외 항목만 입력하세요. 자동으로 문구를 추가하지 않습니다.')
            current_negative_summary = gr.Markdown('원문 0단어 · 최종 0단어')
            current_negative_control.change(lambda current_prompt_text: f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어', current_negative_control, current_negative_summary, queue=False)
        gr.Markdown('고정: VACE-Fun A14B 고·저노이즈 Q4_K_M · UMT5 BF16 비양자화 · Wan2.1 VAE · 832×480 · 16fps · Euler/FlowMatch · 전문가 경계 0.875 · CUDA 연산/CPU 가중치 오프로드. LoRA는 사용하지 않습니다.')
        current_count_control = gr.Number(value=VACE_DEFAULT_SETTINGS['frames'], precision=0, minimum=5, maximum=129, step=4, label='출력 프레임', info='5~129의 4n+1. 81 초과는 장영상 실험 범위입니다. 로컬 기본 21장, 제작자 학습·예제는 81장/16fps. 프레임이 늘면 계산·메모리 요구량이 증가합니다.')
        current_duration_output = gr.Markdown(describe_video_frame_duration(VACE_DEFAULT_SETTINGS['frames']))
        current_count_control.change(describe_video_frame_duration, current_count_control, current_duration_output, queue=False)
        current_seed_control = build_generation_seed(default_seed_value=VACE_DEFAULT_SETTINGS['seed'])
        with gr.Accordion('고급 설정 · 설정값 안내', open=False):
            current_steps_control = gr.Number(value=VACE_DEFAULT_SETTINGS['steps'], precision=0, minimum=2, maximum=100, label='스텝', info='현재 실험 기준으로 매끄러운 영상 생성을 위해 30스텝 이상을 권장합니다. 제작자 예제는 50스텝입니다. 2스텝은 연결 확인용이며 품질 평가용이 아닙니다.')
            current_shift_control = gr.Number(value=VACE_DEFAULT_SETTINGS['flow_shift'], minimum=0.1, maximum=20, label='Flow shift', info='제작자 Flow 설정 12. 노이즈 시간 배분을 바꾸며 고·저노이즈 단계 수에도 영향을 줍니다.')
            current_guidance_control = gr.Number(value=VACE_DEFAULT_SETTINGS['guidance_scale'], minimum=1, maximum=10, label='CFG', info='제작자 예제 5. 텍스트 유도 강도이며 동작량 조절값은 아닙니다.')
            current_strength_control = gr.Number(value=VACE_DEFAULT_SETTINGS['reference_strength'], minimum=0.1, maximum=2, label='VACE 조건 강도', info='제작자 기본 1. 외형 참조·첫 프레임 조건의 영향입니다. 크게 올려도 보존·동작 개선을 보장하지 않습니다.')
            gr.Markdown('**검증 범위:** 공식 VideoX-Fun 파이프라인에 기존 Q4_K_M 가중치를 독립 GGUF 어댑터로 연결합니다. 텍스트 인코더는 비양자화 BF16이며 ComfyUI를 사용하지 않습니다. 원본 구현과 동일한 결과나 8GB의 모든 길이 실행을 보장하지 않습니다.\n\n[모델카드](https://huggingface.co/alibaba-pai/Wan2.2-VACE-Fun-A14B) · [제작자 외형 참조 예제](https://github.com/aigc-apps/VideoX-Fun/blob/13bb3c625e8b1e457d7124d92207b49e00e4a6fe/examples/wan2.2_vace_fun/predict_s2v.py) · [제작자 첫 프레임 예제](https://github.com/aigc-apps/VideoX-Fun/blob/13bb3c625e8b1e457d7124d92207b49e00e4a6fe/examples/wan2.2_vace_fun/predict_i2v.py)')
        current_input_controls = [current_mode_control,current_reference_control,current_prompt_control,current_negative_control,current_count_control,current_seed_control,current_steps_control,current_shift_control,current_guidance_control,current_strength_control,current_edit_video,current_edit_mask,current_pose_video]
        current_generate_button = gr.Button('대기열에 추가', variant='primary', interactive=False)
        build_button_guidance(current_generate_button, '모델 준비 상태를 확인하고 프롬프트와 선택 모드에 맞는 이미지 수를 준비하세요. 텍스트 모드는 첨부를 지우세요.')
        with gr.Column() as current_confirmation_container:
            pass
        current_job_control = gr.Textbox(label='생성 ID')
        current_status_output = gr.Markdown('입력을 준비하세요.')
        def enqueue_vace_generation(*current_input_values):
            current_job_record = current_execute_command('generate', build_vace_payload(*current_input_values))
            return current_job_record['id'], '공용 GPU 대기열에 등록했습니다.'
        bind_gpu_generation_confirmation(current_generate_button, enqueue_vace_generation, current_input_controls, [current_job_control,current_status_output], generation_confirmation_container=current_confirmation_container, generation_readiness_callback=check_vace_readiness, generation_readiness_inputs=[current_model_ready,current_mode_control,current_reference_control,current_prompt_control,current_edit_video,current_edit_mask,current_pose_video], generation_readiness_events=[current_refresh_event,current_model_load])
        build_video_job_monitor(current_execute_command,current_server_address,current_job_control,current_status_output)
        current_read_history,current_history_outputs = build_generation_history_view(current_execute_command,current_server_address,GENERATION_CLEANUP_SCOPE_TEXT,restore_input_callback=restore_vace_inputs,restore_output_components=[*current_input_controls,current_job_control],result_renderer_callback=render_video_generation_result,record_folder_route='/wan22-vace',allow_individual_delete=True,individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda:current_read_history(1),outputs=current_history_outputs)
    return current_interface_blocks
