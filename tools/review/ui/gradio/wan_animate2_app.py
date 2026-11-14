"""Animate-2 RGB 동작 전사 실험 화면."""
import base64
import io
from pathlib import Path
import gradio as gr
from generators.wan_animate2.contracts import ANIMATE_JOB_STORAGE, validate_animate_request
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_model_download import build_model_download_controls
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_reference_images import build_reference_image_inputs
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_video_results import build_video_job_monitor, render_video_generation_result
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT


def execute_animate_command(current_command_name,current_payload_record):
    return execute_remote_management_command('wan22-animate2',current_command_name,current_payload_record)


def build_animate_payload(current_reference_path,current_motion_path,current_prompt_text,current_frame_count,current_steps_value,current_seed_value):
    if not current_reference_path or not current_motion_path:
        raise ValueError('캐릭터 PNG와 RGB 동작 MP4를 첨부하세요.')
    for current_integer_value in (current_frame_count,current_steps_value,current_seed_value):
        if isinstance(current_integer_value,bool) or not float(current_integer_value).is_integer():
            raise ValueError('프레임·스텝·시드는 정수입니다.')
    current_reference_buffer=io.BytesIO()
    current_reference_path.save(current_reference_buffer,format='PNG')
    current_payload_record=dict(action='generate',images=[base64.b64encode(current_reference_buffer.getvalue()).decode()],driving_video=base64.b64encode(Path(current_motion_path).read_bytes()).decode(),prompt=current_prompt_text,frames=int(current_frame_count),steps=int(current_steps_value),seed=int(current_seed_value),width=832,height=480)
    validate_animate_request(current_payload_record)
    return current_payload_record


def restore_animate_inputs(current_history_record):
    current_job_directory=(ANIMATE_JOB_STORAGE/current_history_record['id']).resolve()
    if current_job_directory.parent!=ANIMATE_JOB_STORAGE.resolve():
        raise ValueError('이력 경로 오류')
    current_saved_request=current_history_record['request']
    current_reference_path=(current_job_directory/current_saved_request['references'][0]).resolve()
    if current_reference_path.parent!=current_job_directory or not current_reference_path.is_file():
        raise ValueError('참조 사본 누락 또는 경로 오류')
    return (str(current_reference_path),str(current_job_directory/'driving.mp4'),current_saved_request['prompt'],current_saved_request['frames'],current_saved_request['steps'],current_saved_request['seed'],current_history_record['id'])


def build_animate_interface(current_server_address,current_command_callback=None):
    current_execute_command=current_command_callback or execute_animate_command
    with gr.Blocks(title='Wan Animate-2 캐릭터 동작 전사') as current_interface_blocks:
        gr.Markdown('## Wan Animate-2 캐릭터 동작 전사\nRGB 동작 영상과 기본 캐릭터 참조로 외형 일관성을 검증합니다. 포즈 선 영상·관절 JSON 입력이나 자유로운 영상 편집 기능이 아닙니다.')
        gr.Markdown('**사용 보류:** 현재 장비에서 시스템 RAM과 GPU 메모리 부족이 관측되었습니다. 안정적인 실행이 검증될 때까지 신규 생성과 재개를 보류합니다. 기존 이력과 결과는 보존합니다.')
        current_model_ready, current_model_events = build_model_download_controls(current_interface_blocks, current_execute_command)
        with gr.Row():
            with gr.Column():
                gr.Markdown('### 1. 입력 준비\n캐릭터 PNG 1장(832×480)과 SOMA 인체 렌더 또는 RGB 동작 MP4를 넣으세요. 입력 시간 기준 24fps로 샘플링하며, 부족한 구간을 임의 반복하지 않습니다.')
                _,current_reference_controls=build_reference_image_inputs(reference_slot_count=1,reference_slot_labels=['캐릭터 외형 참조 · 832×480'])
                current_reference_control=current_reference_controls[0]
                current_motion_control=gr.Video(sources=['upload'],label='RGB 동작 MP4 · SOMA 렌더 품질은 실험 대상')
                current_prompt_control=gr.Textbox(label='캐릭터 외형·배경 설명',lines=3,info='참조의 외형과 배경을 기술하세요. 동작은 입력 영상이 제공합니다. 자동 문구 추가 없음.')
                current_prompt_summary=gr.Markdown('원문 0단어 · 최종 0단어')
                current_prompt_control.change(lambda current_prompt_text:f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어 · 원문 그대로 전달',current_prompt_control,current_prompt_summary,queue=False)
                current_frame_control=gr.Number(value=21,precision=0,minimum=5,maximum=81,step=4,label='실험 프레임 · 24fps · 4n+1')
                current_steps_control=gr.Number(value=40,precision=0,minimum=2,maximum=50,label='스텝 · 공식 Base 기본 40')
                current_seed_control=build_generation_seed(default_seed_value=42)
                gr.Markdown('고정: 공식 Base BF16 · 공식 스케줄러/CFG · CUDA 연산 · CPU 가중치 오프로드. 8GB 실행과 캐릭터 비율 보존은 미검증입니다.')
                current_generate_button=gr.Button('대기열에 추가',variant='primary',interactive=False)
                gr.Markdown('모델 준비와 필수 입력을 갖추면 등록할 수 있습니다. 등록 전 인라인 확인 영역에서 확인·취소합니다.')
                with gr.Column() as current_confirmation_container:
                    pass
            with gr.Column():
                gr.Markdown('### 2. 진행·결과 검수\n참조 대비 얼굴·머리·어깨·골반·팔다리 비율과 입력 대비 동작을 확인하세요. SOMA 체형이 자동 교정된다고 보장하지 않습니다.')
                current_job_control=gr.Textbox(label='생성 ID')
                current_status_output=gr.Markdown('입력을 준비하세요.')
                build_video_job_monitor(current_execute_command,current_server_address,current_job_control,current_status_output)
        current_input_controls=[current_reference_control,current_motion_control,current_prompt_control,current_frame_control,current_steps_control,current_seed_control]
        def enqueue_animate_generation(*current_input_values):
            current_job_record=current_execute_command('generate',build_animate_payload(*current_input_values))
            return current_job_record['id'],'공용 GPU 대기열에 등록했습니다.'
        def check_animate_readiness(current_ready_flag,current_reference_path,current_motion_path,current_prompt_text):
            return bool(current_ready_flag and current_reference_path and current_motion_path and current_prompt_text.strip())
        bind_gpu_generation_confirmation(current_generate_button,enqueue_animate_generation,current_input_controls,[current_job_control,current_status_output],generation_confirmation_container=current_confirmation_container,generation_readiness_callback=check_animate_readiness,generation_readiness_inputs=[current_model_ready,current_reference_control,current_motion_control,current_prompt_control],generation_readiness_events=[*current_model_events])
        current_read_history,current_history_outputs=build_generation_history_view(current_execute_command,current_server_address,GENERATION_CLEANUP_SCOPE_TEXT,restore_input_callback=restore_animate_inputs,restore_output_components=[*current_input_controls,current_job_control],result_renderer_callback=render_video_generation_result,record_folder_route='/wan22-animate2',allow_individual_delete=True,individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda:current_read_history(1),outputs=current_history_outputs)
    return current_interface_blocks
