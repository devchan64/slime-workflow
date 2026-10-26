"""Phantom R2V의 Gradio 명령 클라이언트."""
import argparse
import base64
import html
import io
from pathlib import Path
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
import gradio as gr
from tools.review.common.gradio_video_results import describe_video_frame_duration
from PIL import Image
from generators.phantom.contracts import PHANTOM_JOB_STORAGE_ROOT, validate_phantom_request, load_phantom_defaults
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_reference_images import build_reference_image_inputs
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_history import build_generation_history_view, format_generation_status
from tools.review.common.gradio_logs import build_execution_logs
from tools.review.common.generation_status_lookup import read_existing_generation_status
from tools.review.common.generation_progress_display import render_generation_estimate


def execute_phantom_command(current_command_name,current_payload_record):
    return execute_remote_management_command('phantom',current_command_name,current_payload_record)


def describe_phantom_prompt(current_prompt_text):
    return f'원문 {len(current_prompt_text.split())}단어 · 최종 입력 {len(current_prompt_text.split())}단어 · 추가 문구 없음'


def build_phantom_payload(current_reference_images,current_prompt_text,current_frame_count,current_seed_value,current_negative_text,current_resolution_text="832×480",current_steps_value=50,current_shift_value=5.0,current_guidance_value=7.5,current_conditioning_value=5.0):
    current_encoded_images=[]
    for current_reference_image in current_reference_images:
        if current_reference_image is not None:
            current_image_buffer=io.BytesIO()
            current_reference_image.save(current_image_buffer,format='PNG')
            current_encoded_images.append(base64.b64encode(current_image_buffer.getvalue()).decode())
    if isinstance(current_seed_value,bool) or not isinstance(current_seed_value,(int,float)) or current_seed_value != int(current_seed_value):
        raise ValueError('시드는 정수여야 합니다.')
    current_request_record={'action':'generate','images':current_encoded_images,'prompt':current_prompt_text,'frames':current_frame_count,'seed':int(current_seed_value),'negative_prompt':current_negative_text}
    current_image_width,current_image_height=map(int,current_resolution_text.split('×'))
    current_request_record.update(width=current_image_width,height=current_image_height,steps=current_steps_value,flow_shift=current_shift_value,guidance_scale=current_guidance_value,conditioning_scale=current_conditioning_value)
    validate_phantom_request(current_request_record)
    return current_request_record


from tools.review.common.gradio_video_results import render_video_generation_result as render_phantom_result, describe_video_generation_status as describe_phantom_status


def restore_phantom_inputs(current_history_record):
    from tools.review.common.gradio_reference_restore import restore_reference_inputs, validate_history_input_settings
    from generators.phantom.contracts import verify_phantom_request
    current_request_record = validate_history_input_settings(current_history_record)
    current_phantom_config = current_request_record.get('phantom')
    if not isinstance(current_phantom_config, dict) or current_phantom_config.get('task') != 's2v':
        raise gr.Error('이 이력은 비디오·마스크 조건 실험입니다. 현재 R2V 입력 화면으로 복원할 수 없습니다. 기록 위치에서 원본 입력을 확인하세요.')
    current_snapshot_records = current_request_record.get('reference_snapshots')
    if not isinstance(current_snapshot_records, list) or not 1 <= len(current_snapshot_records) <= 4:
        raise gr.Error('저장된 참조 이미지 사본 1~4장이 필요합니다.')
    current_reference_images=restore_reference_inputs(current_history_record, PHANTOM_JOB_STORAGE_ROOT, reference_slot_limit=4)[6:10]
    try:
        current_verified_request = verify_phantom_request(PHANTOM_JOB_STORAGE_ROOT/current_history_record['id'])
        if current_verified_request != current_request_record:
            raise ValueError('저장 요청이 선택한 이력과 다릅니다. 이력을 새로고침하세요.')
    except (ValueError, TypeError, KeyError, OSError) as current_restore_error:
        raise gr.Error(f'저장된 Phantom 입력을 복원할 수 없습니다: {current_restore_error}') from current_restore_error
    return *current_reference_images,*([None]*(4-len(current_reference_images))),current_request_record['prompt'],current_request_record['frames'],current_request_record['seed'],current_request_record['phantom']['negative_prompt'],f"{current_request_record['width']}×{current_request_record['height']}",current_request_record['steps'],current_request_record['phantom']['flow_shift'],current_request_record['phantom']['guidance_scale'],current_request_record['phantom']['conditioning_scale'],current_history_record['id']

def build_phantom_interface(current_server_address):
    with gr.Blocks(title='Phantom 생성기 폐기') as current_interface_blocks:
        gr.Markdown('## Phantom 생성기는 폐기되었습니다.\n전용 가중치와 생성 화면을 제거했습니다. 생성이력과 작업 파일도 정리했습니다.\n[V2V 생성기](/management/frame/vace-v2v-generator/?tool=vace-v2v-generator&category=animation-tool) · [FL2V 생성기](/management/frame/vace-fl2v-generator/?tool=vace-fl2v-generator&category=animation-tool)')
    return current_interface_blocks


from tools.review.ui.gradio.management_menu_app import compose_management_interface

if __name__=='__main__':
    current_argument_parser=argparse.ArgumentParser()
    current_argument_parser.add_argument('--port',type=int,required=True)
    current_argument_parser.add_argument('--review-port',type=int,required=True)
    current_argument_parser.add_argument('--owner-pid',type=int,required=True)
    current_argument_parser.add_argument('--root-path',default='/management/frame/phantom-generator/')
    current_argument_values=current_argument_parser.parse_args()
    compose_management_interface(build_phantom_interface(f'http://127.0.0.1:{current_argument_values.review_port}'),current_argument_values.review_port).queue().launch(server_name='127.0.0.1',server_port=current_argument_values.port,root_path=current_argument_values.root_path,allowed_paths=[])
