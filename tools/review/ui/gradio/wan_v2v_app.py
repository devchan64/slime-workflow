"""Wan2.2 RGB V2V 실험 화면."""
import base64
from pathlib import Path
import gradio as gr
from generators.wan_v2v.contracts import V2V_JOB_STORAGE, validate_v2v_request
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_video_results import build_video_job_monitor, render_video_generation_result
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT


def execute_v2v_command(current_command_name,current_payload_record):
    return execute_remote_management_command('wan22-v2v',current_command_name,current_payload_record)


def build_v2v_payload(current_motion_path,current_prompt_text,current_negative_text,current_strength_value,current_frame_count,current_steps_value,current_seed_value):
    if not current_motion_path:
        raise ValueError('편집할 RGB MP4를 첨부하세요.')
    for current_integer_value in (current_frame_count,current_steps_value,current_seed_value):
        if isinstance(current_integer_value,bool) or not float(current_integer_value).is_integer():
            raise ValueError('프레임·스텝·시드는 정수입니다.')
    current_payload_record=dict(action='generate',input_video=base64.b64encode(Path(current_motion_path).read_bytes()).decode(),prompt=current_prompt_text,negative_prompt=current_negative_text,denoising_strength=current_strength_value,frames=int(current_frame_count),steps=int(current_steps_value),seed=int(current_seed_value),width=832,height=480)
    validate_v2v_request(current_payload_record)
    return current_payload_record


def restore_v2v_inputs(current_history_record):
    current_job_directory=(V2V_JOB_STORAGE/current_history_record['id']).resolve()
    if current_job_directory.parent!=V2V_JOB_STORAGE.resolve():
        raise ValueError('이력 경로 오류')
    current_saved_request=current_history_record['request']
    current_video_path=current_job_directory/'input.mp4'
    if not current_video_path.is_file() or current_video_path.is_symlink():
        raise ValueError('입력 영상 사본 누락 또는 경로 오류')
    return (str(current_video_path),current_saved_request['prompt'],current_saved_request['negative_prompt'],current_saved_request['denoising_strength'],current_saved_request['frames'],current_saved_request['steps'],current_saved_request['seed'],current_history_record['id'])


def build_v2v_interface(current_server_address,current_command_callback=None):
    current_execute_command=current_command_callback or execute_v2v_command
    with gr.Blocks(title='Wan2.2 RGB 영상 재생성 · V2V') as current_interface_blocks:
        gr.Markdown('## Wan2.2 RGB 영상 재생성 · V2V\n기존 RGB 영상을 초기 잠재값으로 사용하여 프롬프트와 변경 강도로 다시 생성합니다. DiffSynth-Studio 공식 input_video 경로입니다. 캐릭터 참조 이미지 조건·포즈 추출은 사용하지 않습니다.')
        current_model_ready=gr.State(False)
        current_model_status=gr.Markdown('모델 준비 확인 중')
        current_model_button=gr.Button('모델 준비 상태 확인')
        def read_v2v_model_status():
            current_status_record=current_execute_command('model-status',{})
            return current_status_record['message'],current_status_record['ready']
        current_refresh_event=current_model_button.click(read_v2v_model_status,outputs=[current_model_status,current_model_ready])
        current_model_load=current_interface_blocks.load(read_v2v_model_status,outputs=[current_model_status,current_model_ready])
        with gr.Row():
            with gr.Column():
                gr.Markdown('### 1. 입력 준비\n832×480 RGB MP4를 넣으세요. 앞에서부터 지정한 프레임 수를 사용하며 원본 FPS와 순서를 보존합니다. 프레임 보간·자동 반복·크롭을 하지 않습니다.')
                current_motion_control=gr.Video(sources=['upload'],label='편집할 RGB MP4 · 최대 32MiB')
                current_prompt_control=gr.Textbox(label='생성될 영상의 동작·외형·배경',lines=3,info='원하는 결과를 짧게 기술하세요. 예: 빠르게 잽을 뻗고 곧바로 회수한다. 자동 문구 추가 없음.')
                current_prompt_summary=gr.Markdown('원문 0단어 · 최종 0단어')
                current_prompt_control.change(lambda current_prompt_text:f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어 · 원문 그대로 전달',current_prompt_control,current_prompt_summary,queue=False)
                current_negative_control=gr.Textbox(label='부정 프롬프트',lines=2,value='')
                current_negative_summary=gr.Markdown('부정 원문 0단어 · 최종 0단어')
                current_negative_control.change(lambda current_prompt_text:f'부정 원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어',current_negative_control,current_negative_summary,queue=False)
                current_strength_control=gr.Slider(minimum=0.01,maximum=0.99,step=0.01,value=0.3,label='변경 강도',info='낮으면 원본 보존, 높으면 재생성 범위 증가. 0.3은 비교 실험의 시작값이며 품질 보장은 아닙니다.')
                current_frame_control=gr.Number(value=21,precision=0,minimum=5,maximum=81,step=4,label='출력 프레임 · 원본 FPS 유지 · 4n+1')
                current_steps_control=gr.Number(value=20,precision=0,minimum=2,maximum=50,label='추론 스텝 · 실험 기본 20 (공식 예제 기본 50)')
                current_seed_control=build_generation_seed(default_seed_value=42)
                gr.Markdown('고정: Wan2.2 T2V-A14B BF16 · CFG 5 · shift 5 · 전문가 경계 0.875 · 공식 타일 VAE · CUDA 연산/디스크·CPU 가중치 오프로드. 기존 Fun Control의 자체 타일 래퍼를 사용하지 않습니다. 8GB 실행 미검증. 강도에 따라 고노이즈 전문가를 거치지 않을 수 있습니다.')
                current_generate_button=gr.Button('대기열에 추가',variant='primary',interactive=False)
                gr.Markdown('모델 준비와 필수 입력을 갖추면 등록할 수 있습니다. 등록 전 인라인 확인 영역에서 확인·취소합니다.')
                with gr.Column() as current_confirmation_container:
                    pass
            with gr.Column():
                gr.Markdown('### 2. 진행·결과 검수\n입력과 결과를 비교하여 얼굴·체형·팔의 최대 신전·동작 속도를 확인하세요. 강도를 높이면 정체성과 자세도 달라질 수 있으며, 동작 개선을 보장하지 않습니다.')
                current_job_control=gr.Textbox(label='생성 ID')
                current_status_output=gr.Markdown('입력을 준비하세요.')
                build_video_job_monitor(current_execute_command,current_server_address,current_job_control,current_status_output)
        current_input_controls=[current_motion_control,current_prompt_control,current_negative_control,current_strength_control,current_frame_control,current_steps_control,current_seed_control]
        def enqueue_v2v_generation(*current_input_values):
            current_job_record=current_execute_command('generate',build_v2v_payload(*current_input_values))
            return current_job_record['id'],'공용 GPU 대기열에 등록했습니다.'
        def check_v2v_readiness(current_ready_flag,current_motion_path,current_prompt_text):
            return bool(current_ready_flag and current_motion_path and current_prompt_text.strip())
        bind_gpu_generation_confirmation(current_generate_button,enqueue_v2v_generation,current_input_controls,[current_job_control,current_status_output],generation_confirmation_container=current_confirmation_container,generation_readiness_callback=check_v2v_readiness,generation_readiness_inputs=[current_model_ready,current_motion_control,current_prompt_control],generation_readiness_events=[current_refresh_event,current_model_load])
        current_read_history,current_history_outputs=build_generation_history_view(current_execute_command,current_server_address,GENERATION_CLEANUP_SCOPE_TEXT,restore_input_callback=restore_v2v_inputs,restore_output_components=[*current_input_controls,current_job_control],result_renderer_callback=render_video_generation_result,record_folder_route='/wan22-v2v',allow_individual_delete=True,individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda:current_read_history(1),outputs=current_history_outputs)
    return current_interface_blocks
