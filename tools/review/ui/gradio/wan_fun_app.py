"""Wan2.2 Fun Control 실험용 Gradio 입력과 공용 이력."""
import base64
import io
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageOps
import gradio as gr
from generators.wan_fun.contracts import FUN_JOB_STORAGE, FUN_DEFAULT_SETTINGS, FUN_CONTROL_TYPES, validate_fun_request
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_logs import build_execution_logs
from tools.review.common.gradio_video_results import describe_video_generation_status, render_video_generation_result
from tools.review.common.generation_status_lookup import read_existing_generation_status
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT


def execute_fun_command(current_command_name, current_payload_record):
    return execute_remote_management_command('wan22-fun-control', current_command_name, current_payload_record)


def encode_fun_image(current_image_object, current_padding_color):
    current_image_object = current_image_object.convert('RGBA')
    current_image_object = ImageOps.contain(current_image_object, (832, 480), Image.Resampling.LANCZOS)
    current_canvas_image = Image.new('RGB', (832, 480), current_padding_color)
    current_canvas_image.paste(current_image_object, ((832-current_image_object.width)//2, (480-current_image_object.height)//2), current_image_object)
    current_image_buffer = io.BytesIO()
    current_canvas_image.save(current_image_buffer, format='PNG')
    return base64.b64encode(current_image_buffer.getvalue()).decode()


def build_fun_payload(current_reference_path, current_video_path, current_frame_paths, current_control_type, current_prompt_text, current_negative_text, current_frame_count, current_seed_value, current_steps_value, current_shift_value, current_guidance_value, current_switch_ratio):
    if not current_reference_path or bool(current_video_path) == bool(current_frame_paths):
        raise ValueError('외형 참조 1장과 제어 영상 또는 PNG 목록 중 하나를 첨부하세요.')
    for current_integer_value in (current_frame_count, current_seed_value, current_steps_value):
        if isinstance(current_integer_value, bool) or not isinstance(current_integer_value, (int, float)) or not float(current_integer_value).is_integer():
            raise ValueError('프레임·시드·스텝은 정수여야 합니다.')
    current_frame_count = int(current_frame_count)
    if not 5 <= current_frame_count <= 81 or (current_frame_count-1) % 4:
        raise ValueError('프레임 수는 5~81 범위의 4n+1입니다.')
    with Image.open(current_reference_path) as current_reference_image:
        if current_reference_image.size != (832, 480):
            gr.Warning('참조 이미지를 비율 유지해 832×480 흰 여백으로 맞춥니다. 원본은 보존합니다.')
        current_encoded_images = [encode_fun_image(current_reference_image, 'white')]
    if current_video_path:
        current_video_capture = cv2.VideoCapture(str(current_video_path))
        try:
            if not current_video_capture.isOpened():
                raise ValueError('제어 영상 디코딩 실패')
            current_input_fps = current_video_capture.get(cv2.CAP_PROP_FPS)
            if abs(current_input_fps - 16) > 0.1:
                gr.Warning(f'입력 {current_input_fps:.2f}fps의 프레임을 순서대로 사용하고 결과는 16fps로 재생합니다.')
            for current_frame_index in range(current_frame_count):
                current_frame_ready, current_frame_array = current_video_capture.read()
                if not current_frame_ready:
                    raise ValueError(f'제어 영상이 부족합니다: {current_frame_index}/{current_frame_count}프레임. 반복·복제하지 않습니다.')
                current_encoded_images.append(encode_fun_image(Image.fromarray(cv2.cvtColor(current_frame_array, cv2.COLOR_BGR2RGB)), 'black'))
        finally:
            current_video_capture.release()
    else:
        if len(current_frame_paths) != current_frame_count:
            raise ValueError('PNG 목록은 출력 프레임 수와 같아야 합니다. 업로드 순서로 배치합니다.')
        for current_frame_path in current_frame_paths:
            with Image.open(current_frame_path) as current_frame_image:
                current_encoded_images.append(encode_fun_image(current_frame_image, 'black'))
    current_payload_record = {'action': 'generate', 'prompt': current_prompt_text, 'negative_prompt': current_negative_text, 'images': current_encoded_images, 'control_type': current_control_type, 'width': 832, 'height': 480, 'frames': current_frame_count, 'seed': int(current_seed_value), 'steps': int(current_steps_value), 'flow_shift': current_shift_value, 'guidance_scale': current_guidance_value, 'switch_ratio': current_switch_ratio}
    validate_fun_request(current_payload_record)
    return current_payload_record


def restore_fun_inputs(current_history_record):
    current_job_identifier = current_history_record['id']
    current_job_directory = (FUN_JOB_STORAGE/current_job_identifier).resolve()
    if current_job_directory.parent != FUN_JOB_STORAGE.resolve():
        raise ValueError('이력 경로 오류')
    current_request_record = current_history_record['request']
    current_reference_paths = []
    for current_reference_name in current_request_record['references']:
        current_reference_path = (current_job_directory/current_reference_name).resolve()
        if current_reference_path.parent != current_job_directory or not current_reference_path.is_file():
            raise ValueError('이력 입력 사본 누락 또는 경로 오류')
        current_reference_paths.append(str(current_reference_path))
    return (current_reference_paths[0], None, current_reference_paths[1:], current_request_record['control_type'], current_request_record['prompt'], current_request_record['negative_prompt'], current_request_record['frames'], current_request_record['seed'], current_request_record['steps'], current_request_record['flow_shift'], current_request_record['guidance_scale'], current_request_record['switch_ratio'], current_job_identifier)


def build_fun_interface(current_server_address, current_command_callback=None):
    current_execute_command = current_command_callback or execute_fun_command
    with gr.Blocks(title='Wan2.2 Fun Control 생성기') as current_interface_blocks:
        gr.Markdown('## Wan2.2 Fun Control A14B 실험 생성기\n외형 참조와 전처리된 제어 영상으로 애니메이션을 생성합니다. 애니리그 얼굴은 입력하지 않습니다.')
        current_model_status = gr.Markdown('모델 준비 상태 확인 중')
        current_model_refresh = gr.Button('모델 준비 상태 확인')
        def read_fun_model_status():
            try:
                return current_execute_command('model-status', {})['message']
            except Exception as current_status_error:
                return f'모델 상태 확인 실패: {current_status_error}'
        current_model_refresh.click(read_fun_model_status, outputs=current_model_status, queue=False)
        current_interface_blocks.load(read_fun_model_status, outputs=current_model_status)
        current_reference_control = gr.Image(type='filepath', sources=['upload'], label='캐릭터 외형 참조 · 1장')
        current_video_control = gr.File(file_types=['.mp4', '.webm', '.mov'], label='전처리된 제어 영상 · 앞에서부터 지정 프레임 사용')
        current_frames_control = gr.File(file_count='multiple', file_types=['.png'], label='또는 제어 PNG 목록 · 업로드 순서 · 영상과 중복 입력 불가')
        current_type_control = gr.Dropdown(choices=list(FUN_CONTROL_TYPES), value='pose', label='제어 종류 · 영상의 실제 표현과 일치시켜 주세요')
        gr.Markdown('ANNY 렌더 원본은 pose 영상이 아닙니다. pose는 추출·투영한 관절 영상, depth는 깊이 영상, canny/mlsd는 선 영상입니다. 이 페이지는 자동 전처리하지 않습니다. 참조는 흰색, 제어는 검은색 여백으로 비율 유지하여 832×480에 맞춥니다.')
        current_prompt_control = gr.Textbox(label='장면·동작 프롬프트', lines=3)
        current_prompt_summary = gr.Markdown('원문 0단어 · 최종 0단어 · 추가 문구 없음')
        current_prompt_control.change(lambda current_prompt_text: f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어 · 추가 문구 없음', current_prompt_control, current_prompt_summary, queue=False)
        with gr.Accordion('부정 프롬프트', open=False):
            current_negative_control = gr.Textbox(label='부정 프롬프트', value='')
            current_negative_summary = gr.Markdown('원문 0단어 · 최종 0단어')
            current_negative_control.change(lambda current_prompt_text: f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어', current_negative_control, current_negative_summary, queue=False)
        gr.Markdown('고정: 고·저노이즈 Q4_K_M · 832×480 · 16fps · Euler/simple · CUDA 연산/CPU 가중치 오프로드 · 가속 LoRA 없음. 8GB 추론은 아직 검증하지 않았습니다.')
        current_count_control = gr.Number(value=FUN_DEFAULT_SETTINGS['frames'], precision=0, minimum=5, maximum=81, step=4, label='출력 프레임 · 4n+1 · 5~81', info='21프레임으로 먼저 검토하세요. 부족한 제어 프레임은 자동 반복하지 않습니다.')
        current_seed_control = build_generation_seed(default_seed_value=FUN_DEFAULT_SETTINGS['seed'])
        with gr.Accordion('고급 설정', open=False):
            current_steps_control = gr.Number(value=FUN_DEFAULT_SETTINGS['steps'], precision=0, minimum=2, maximum=100, label='스텝 · 2~100', info='실험 기본 20. 증가하면 계산량이 늘며 동작 개선을 보장하지 않습니다.')
            current_shift_control = gr.Number(value=FUN_DEFAULT_SETTINGS['flow_shift'], minimum=0.1, maximum=20, label='Flow shift · 0.1~20', info='실험 기본 5. 노이즈 시간 배분을 변경합니다.')
            current_guidance_control = gr.Number(value=FUN_DEFAULT_SETTINGS['guidance_scale'], minimum=1, maximum=10, label='CFG · 1~10', info='실험 기본 6. 텍스트 유도 강도이며 외형만의 참조 강도가 아닙니다.')
            current_switch_control = gr.Number(value=FUN_DEFAULT_SETTINGS['switch_ratio'], minimum=0.1, maximum=0.9, label='고노이즈 스텝 비율 · 0.1~0.9', info='기본 0.5. 전체 스텝의 앞부분은 고노이즈 모델, 나머지는 저노이즈 모델을 사용합니다.')
            gr.Markdown('범위는 이 페이지의 실험 허용 범위입니다. [모델카드](https://huggingface.co/alibaba-pai/Wan2.2-Fun-A14B-Control) · [공식 ComfyUI 안내](https://docs.comfy.org/tutorials/video/wan/wan2-2-fun-control). 가속 4스텝 LoRA 예제와 현재 Q4 비가속 설정은 다릅니다.')
        current_input_controls = [current_reference_control,current_video_control,current_frames_control,current_type_control,current_prompt_control,current_negative_control,current_count_control,current_seed_control,current_steps_control,current_shift_control,current_guidance_control,current_switch_control]
        current_generate_button = gr.Button('대기열에 추가', variant='primary', interactive=False)
        build_button_guidance(current_generate_button, '참조·프롬프트와 제어 영상 또는 PNG 목록 중 하나를 입력하세요. 모델 파일이 준비되어야 등록할 수 있습니다.')
        with gr.Column() as current_confirmation_container:
            pass
        current_job_control = gr.Textbox(label='생성 ID')
        current_status_output = gr.Markdown('입력을 준비하세요.')
        current_result_output = gr.HTML('')
        current_result_identity = gr.State('')
        current_log_output,current_log_enabled,_ = build_execution_logs()
        def enqueue_fun_generation(*current_input_values):
            current_job_record = current_execute_command('generate',build_fun_payload(*current_input_values))
            return current_job_record['id'], '공용 GPU 대기열에 등록했습니다.'
        bind_gpu_generation_confirmation(current_generate_button,enqueue_fun_generation,current_input_controls,[current_job_control,current_status_output],generation_confirmation_container=current_confirmation_container,generation_readiness_callback=lambda current_reference_path,current_video_path,current_frame_paths,current_prompt_text: bool(current_reference_path and (bool(current_video_path)!=bool(current_frame_paths)) and current_prompt_text.strip()),generation_readiness_inputs=[current_reference_control,current_video_control,current_frames_control,current_prompt_control])
        current_generation_timer = gr.Timer(5,active=False)
        def refresh_fun_status(current_job_identifier,current_logs_enabled,current_previous_result):
            if not current_job_identifier:
                return gr.skip(),gr.skip(),gr.skip(),gr.skip(),gr.Timer(active=False)
            current_status_record = read_existing_generation_status(current_execute_command,current_job_identifier)
            if current_status_record is None:
                return '삭제된 이력입니다.','','','',gr.Timer(active=False)
            current_result_url = current_status_record.get('video','')
            return describe_video_generation_status(current_status_record),render_video_generation_result(current_job_identifier,current_status_record,current_server_address) if current_result_url and current_result_url!=current_previous_result else gr.skip(),current_status_record.get('log','') if current_logs_enabled else gr.skip(),current_result_url,gr.Timer(active=current_status_record.get('status') not in ('completed','failed','cancelled','paused'))
        current_generation_timer.tick(refresh_fun_status,[current_job_control,current_log_enabled,current_result_identity],[current_status_output,current_result_output,current_log_output,current_result_identity,current_generation_timer],queue=False,show_progress='hidden')
        current_job_control.change(lambda current_job_identifier:gr.Timer(active=bool(current_job_identifier)),current_job_control,current_generation_timer,queue=False)
        current_read_history,current_history_outputs = build_generation_history_view(current_execute_command,current_server_address,GENERATION_CLEANUP_SCOPE_TEXT,restore_input_callback=restore_fun_inputs,restore_output_components=[*current_input_controls,current_job_control],result_renderer_callback=render_video_generation_result,record_folder_route='/wan22-fun-control',allow_individual_delete=True,individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda:current_read_history(1),outputs=current_history_outputs)
    return current_interface_blocks
