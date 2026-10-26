"""Wan2.2 TI2V 5B의 텍스트·첫 프레임 영상 생성 화면."""
import base64
import io

import gradio as gr
from PIL import Image, ImageOps

from generators.wan_ti2v.contracts import TI2V_DEFAULT_SETTINGS, TI2V_JOB_STORAGE, validate_ti2v_request
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT
from tools.review.common.generation_status_lookup import read_existing_generation_status
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_logs import build_execution_logs
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_video_results import describe_video_generation_status, render_video_generation_result
from tools.review.common.management_client import execute_remote_management_command


def execute_ti2v_command(current_command_name, current_payload_record):
    return execute_remote_management_command('wan22-ti2v', current_command_name, current_payload_record)


def encode_ti2v_reference(current_reference_path):
    with Image.open(current_reference_path) as current_image_file:
        current_image_value = ImageOps.contain(current_image_file.convert('RGBA'), (832, 480), Image.Resampling.LANCZOS)
    current_canvas_image = Image.new('RGB', (832, 480), 'white')
    current_canvas_image.paste(current_image_value, ((832 - current_image_value.width) // 2, (480 - current_image_value.height) // 2), current_image_value)
    current_bytes_buffer = io.BytesIO()
    current_canvas_image.save(current_bytes_buffer, format='PNG')
    return base64.b64encode(current_bytes_buffer.getvalue()).decode()


def build_ti2v_payload(current_reference_path, current_prompt_text, current_negative_text, current_frame_count, current_seed_value, current_steps_value, current_shift_value, current_guidance_value):
    for current_integer_value in (current_frame_count, current_seed_value, current_steps_value):
        if isinstance(current_integer_value, bool) or not isinstance(current_integer_value, (int, float)) or not float(current_integer_value).is_integer():
            raise ValueError('프레임·시드·스텝은 정수여야 합니다.')
    current_payload_record = {'action': 'generate', 'prompt': current_prompt_text, 'negative_prompt': current_negative_text, 'images': [encode_ti2v_reference(current_reference_path)] if current_reference_path else [], 'width': 832, 'height': 480, 'frames': int(current_frame_count), 'seed': int(current_seed_value), 'steps': int(current_steps_value), 'flow_shift': current_shift_value, 'guidance_scale': current_guidance_value}
    validate_ti2v_request(current_payload_record)
    return current_payload_record


def restore_ti2v_inputs(current_history_record):
    current_request_record = current_history_record['request']
    current_job_directory = (TI2V_JOB_STORAGE / current_history_record['id']).resolve()
    if current_job_directory.parent != TI2V_JOB_STORAGE.resolve():
        raise ValueError('이력 경로 오류')
    current_reference_path = None
    if current_request_record['references']:
        current_reference_file = (current_job_directory / current_request_record['references'][0]).resolve()
        if current_reference_file.parent != current_job_directory or not current_reference_file.is_file():
            raise ValueError('기준 이미지 사본이 없습니다.')
        current_reference_path = str(current_reference_file)
    return (current_reference_path, current_request_record['prompt'], current_request_record['negative_prompt'], current_request_record['frames'], current_request_record['seed'], current_request_record['steps'], current_request_record['flow_shift'], current_request_record['guidance_scale'], current_history_record['id'])


def build_ti2v_interface(current_server_address, current_command_callback=None):
    current_execute_command = current_command_callback or execute_ti2v_command
    with gr.Blocks(title='Wan2.2 TI2V 5B 영상 생성기') as current_interface_blocks:
        gr.Markdown('## Wan2.2 TI2V 5B 걷기 실험\n텍스트만으로 시작하거나 기준 이미지 1장을 첫 프레임으로 사용합니다. 포즈를 강제하지 않으므로 보행의 정확한 관절 제어는 Fun-Control을 사용하세요.')
        current_model_status = gr.Markdown('모델 준비 상태 확인 중')
        current_model_refresh = gr.Button('모델 준비 상태 확인')
        def read_ti2v_model_status():
            try:
                return current_execute_command('model-status', {})['message']
            except Exception as current_status_error:
                return f'모델 상태 확인 실패: {current_status_error}'
        current_model_refresh.click(read_ti2v_model_status, outputs=current_model_status, queue=False)
        current_interface_blocks.load(read_ti2v_model_status, outputs=current_model_status)
        current_reference_control = gr.Image(type='filepath', sources=['upload'], label='선택 · 첫 프레임 기준 이미지 1장')
        gr.Markdown('기준 이미지가 없으면 텍스트 생성, 있으면 첫 프레임 조건 생성입니다. 발·손이 잘리지 않은 전신 단일컷을 사용하세요. 이미지는 비율을 유지해 832×480 흰 여백으로 맞춥니다.')
        current_prompt_control = gr.Textbox(label='장면·동작 프롬프트', lines=3, info='최종 100단어 미만(로컬 제한). 동작을 먼저 쓰고 방향·카메라·외형을 덧붙이세요. 걷기는 좌우 발 들기·내딛기·체중 이동이 영상 전체에서 반복되도록 설명하세요.', placeholder='A full-body character walks forward naturally, fixed camera, consistent identity.')
        current_prompt_summary = gr.Markdown('원문 0단어 · 최종 0단어 · 추가 문구 없음')
        current_prompt_control.change(lambda current_prompt_value: f'원문 {len(current_prompt_value.split())}단어 · 최종 {len(current_prompt_value.split())}단어 · 추가 문구 없음', current_prompt_control, current_prompt_summary, queue=False)
        with gr.Accordion('부정 프롬프트', open=False):
            current_negative_control = gr.Textbox(label='부정 프롬프트', value='', info='현재 비교 기준은 빈 값입니다. 긴 금지 목록과 동작 프롬프트를 동시에 바꾸면 개선 원인을 구분하기 어렵습니다.')
        gr.Markdown('고정: Wan2.2 TI2V 5B Q4_K_M · UMT5 Q4 · 832×480 · 24fps · UniPC/simple · CUDA 연산/CPU 가중치 오프로드. 8GB 대상 실험 구성이며 입력 길이별 성공을 보장하지 않습니다. VAE는 공간 타일·시간축 전체 디코딩을 사용합니다.')
        current_frame_control = gr.Number(value=TI2V_DEFAULT_SETTINGS['frames'], precision=0, minimum=5, maximum=81, step=4, label='출력 프레임 · 4n+1 · 5~81', info='24fps: 21장 약 0.88초 · 41장 약 1.71초 · 81장 약 3.38초. 프레임 수를 늘리면 새로 생성하며 이전 동작을 연장하거나 앞부분을 보존하지 않습니다.')
        current_seed_control = build_generation_seed(default_seed_value=TI2V_DEFAULT_SETTINGS['seed'])
        gr.Markdown('시드 비교 안내: 한 설정의 효과를 비교할 때 시드를 고정하세요. 프레임 수가 달라지면 같은 시드라도 동작이 같지 않습니다.')
        with gr.Accordion('고급 설정', open=False):
            current_steps_control = gr.Number(value=TI2V_DEFAULT_SETTINGS['steps'], precision=0, minimum=2, maximum=50, label='스텝 · 2~50', info='잡음 제거 반복 횟수. ComfyUI 예제 20, Wan 공식 구현 50. 2는 실행 점검용이며 30·50은 품질 비교 후보입니다. 증가가 보행 개선을 보장하지 않습니다.')
            current_shift_control = gr.Number(value=TI2V_DEFAULT_SETTINGS['flow_shift'], minimum=0.1, maximum=20.0, label='Flow shift · 0.1~20', info='노이즈 시간 스케줄 조정값. ComfyUI 예제 8, Wan 공식 구현 5. 현재 8을 기준으로 5를 별도 비교하세요. 보폭·움직임 강도를 직접 지정하는 값은 아닙니다.')
            current_guidance_control = gr.Number(value=TI2V_DEFAULT_SETTINGS['guidance_scale'], minimum=1.0, maximum=10.0, label='CFG · 1~10', info='프롬프트 조건의 결합 강도. 두 공식 레퍼런스 모두 5. 필요하면 4·6을 하나씩 비교하세요. 높일수록 동작이나 외형 보존이 좋아지는 것은 아닙니다.')
        with gr.Accordion('설정 근거 · 8GB 적용 범위 · 비교 순서', open=False):
            gr.Markdown('**공식 레퍼런스 확인일: 2026-10-26**\n\n| 기준 | 스텝 | Shift | CFG | 크기·프레임 |\n| --- | --- | --- | --- | --- |\n| Wan 공식 구현 | 50 | 5 | 5 | 1280×704 · 121장 · 24fps |\n| ComfyUI 공식 예제 | 20 | 8 | 5 | 1280×704 · 121장 · 24fps |\n| 현재 생성기 | 기본 20 | 기본 8 | 기본 5 | 832×480 · 기본 21장 · 최대 81장 · 24fps |\n\n현재 UniPC/simple 설정은 ComfyUI 예제를 따릅니다. 원본·FP16 예제와 달리 확산 모델과 UMT5에 Q4를 사용하므로 동일 품질을 보장하지 않습니다. 공식 121프레임·720P는 현재 입력 범위 밖입니다.\n\n**8GB 안내:** 원본 모델카드의 24GB 실행 예와 ComfyUI의 8GB 오프로드 안내는 서로 다른 구성입니다. 로컬은 CUDA 연산·CPU 가중치 대기·단계별 로드·공간 타일 VAE를 사용합니다. 모델 파일 크기는 전체 VRAM 사용량이 아니며 모든 길이의 성공을 보장하지 않습니다.\n\n**움직임이 약할 때:** 참조·시드·81프레임을 고정하고 동작 문구만 먼저 비교 → Shift 8/5 → 스텝 20/30/50 → 필요할 때 CFG 4/5/6 순서로 한 변수씩 검수하세요. 이 순서는 로컬 실험 제안이며 공식 최적값이 아닙니다. 발 교대·착지·체중 이동·후반 동작 지속과 외형·밝기를 함께 확인하세요. 41프레임에서 성공한 보행이 81프레임에서도 유지된다고 보장하지 않습니다.\n\n출처: [Wan 모델카드](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B) · [Wan 기본 설정](https://github.com/Wan-Video/Wan2.2/blob/main/wan/configs/wan_ti2v_5B.py) · [ComfyUI 공식 예제](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_wan2_2_5B_ti2v.json) · [ComfyUI 8GB 안내](https://docs.comfy.org/tutorials/video/wan/wan2_2) · [GGUF 모델카드](https://huggingface.co/QuantStack/Wan2.2-TI2V-5B-GGUF)\n')
        current_input_controls = [current_reference_control, current_prompt_control, current_negative_control, current_frame_control, current_seed_control, current_steps_control, current_shift_control, current_guidance_control]
        current_generate_button = gr.Button('대기열에 추가', variant='primary', interactive=False)
        build_button_guidance(current_generate_button, '프롬프트를 입력하고 모델 준비 상태를 확인하세요.')
        with gr.Column() as current_confirmation_container:
            pass
        current_job_control = gr.Textbox(label='생성 ID')
        current_status_output = gr.Markdown('프롬프트를 입력하세요.')
        current_result_output = gr.HTML('')
        current_result_identity = gr.State('')
        current_log_output, current_log_enabled, _ = build_execution_logs()
        def enqueue_ti2v_generation(*current_input_values):
            current_job_record = current_execute_command('generate', build_ti2v_payload(*current_input_values))
            return current_job_record['id'], '공용 GPU 대기열에 등록했습니다.'
        bind_gpu_generation_confirmation(current_generate_button, enqueue_ti2v_generation, current_input_controls, [current_job_control, current_status_output], generation_confirmation_container=current_confirmation_container, generation_readiness_callback=lambda current_reference_path, current_prompt_text: bool(current_prompt_text.strip()), generation_readiness_inputs=[current_reference_control, current_prompt_control])
        current_generation_timer = gr.Timer(5, active=False)
        def refresh_ti2v_status(current_job_identifier, current_logs_enabled, current_previous_result):
            if not current_job_identifier:
                return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.Timer(active=False)
            current_status_record = read_existing_generation_status(current_execute_command, current_job_identifier)
            if current_status_record is None:
                return '삭제된 이력입니다.', '', '', '', gr.Timer(active=False)
            current_result_url = current_status_record.get('video', '')
            return describe_video_generation_status(current_status_record), render_video_generation_result(current_job_identifier, current_status_record, current_server_address) if current_result_url and current_result_url != current_previous_result else gr.skip(), current_status_record.get('log', '') if current_logs_enabled else gr.skip(), current_result_url, gr.Timer(active=current_status_record.get('status') not in ('completed', 'failed', 'cancelled', 'paused'))
        current_generation_timer.tick(refresh_ti2v_status, [current_job_control, current_log_enabled, current_result_identity], [current_status_output, current_result_output, current_log_output, current_result_identity, current_generation_timer], queue=False, show_progress='hidden')
        current_job_control.change(lambda current_job_identifier: gr.Timer(active=bool(current_job_identifier)), current_job_control, current_generation_timer, queue=False)
        current_read_history, current_history_outputs = build_generation_history_view(current_execute_command, current_server_address, GENERATION_CLEANUP_SCOPE_TEXT, restore_input_callback=restore_ti2v_inputs, restore_output_components=[*current_input_controls, current_job_control], result_renderer_callback=render_video_generation_result, record_folder_route='/wan22-ti2v', allow_individual_delete=True, individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda: current_read_history(1), outputs=current_history_outputs)
    return current_interface_blocks
