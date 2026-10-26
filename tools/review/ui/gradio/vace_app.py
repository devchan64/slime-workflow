"""Wan2.1 VACE R2V의 Gradio 명령 클라이언트."""
import argparse
import base64
import html
import io
from pathlib import Path
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
import gradio as gr
from PIL import Image
from generators.vace.contracts import VACE_JOB_STORAGE_ROOT, validate_vace_request, load_vace_defaults
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_reference_images import build_reference_image_inputs
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_history import build_generation_history_view, format_generation_status
from tools.review.common.gradio_logs import build_execution_logs
from tools.review.common.generation_progress_display import render_generation_estimate


def execute_vace_command(current_command_name,current_payload_record):
    return execute_remote_management_command('wan21-vace',current_command_name,current_payload_record)


def describe_vace_prompt(current_prompt_text):
    return f'원문 {len(current_prompt_text.split())}단어 · 최종 입력 {len(current_prompt_text.split())}단어 · 추가 문구 없음'


def build_vace_payload(current_reference_image,current_prompt_text,current_frame_count,current_seed_value,current_negative_text,current_resolution_text="832×480",current_steps_value=50,current_shift_value=5.0,current_guidance_value=5.0,current_conditioning_value=1.0):
    if current_reference_image is None:
        raise ValueError('캐릭터 참조 이미지 1장을 첨부하세요.')
    if isinstance(current_seed_value,bool) or not isinstance(current_seed_value,(int,float)) or current_seed_value != int(current_seed_value):
        raise ValueError('시드는 정수여야 합니다.')
    current_image_buffer=io.BytesIO()
    current_reference_image.save(current_image_buffer,format='PNG')
    current_request_record={'action':'generate','images':[base64.b64encode(current_image_buffer.getvalue()).decode()],'prompt':current_prompt_text,'frames':current_frame_count,'seed':int(current_seed_value),'negative_prompt':current_negative_text}
    current_image_width,current_image_height=map(int,current_resolution_text.split('×'))
    current_request_record.update(width=current_image_width,height=current_image_height,steps=current_steps_value,flow_shift=current_shift_value,guidance_scale=current_guidance_value,conditioning_scale=current_conditioning_value)
    validate_vace_request(current_request_record)
    return current_request_record


def render_vace_result(current_job_identifier,current_status_record,current_server_address):
    if not current_status_record.get('video'):
        return '<p>완료 후 영상과 프레임 다운로드를 표시합니다.</p>'
    current_video_url=html.escape(current_server_address+current_status_record['video'],quote=True)
    current_download_url=html.escape(current_server_address+current_status_record['download'],quote=True)
    return f'<video controls loop playsinline width="512" src="{current_video_url}"></video><p><a href="{current_video_url}" target="_blank">MP4 열기</a> · <a href="{current_download_url}">PNG 프레임 ZIP</a></p>'


def describe_vace_status(current_status_record):
    current_status_text='상태: '+format_generation_status(current_status_record)+'\n\n'+render_generation_estimate(current_status_record.get('estimate',{}),current_status_record['status'])
    current_metrics_record=current_status_record.get('metrics',{})
    current_status_text+=f"\n\n단계: {current_metrics_record.get('stage','queued')} · 추론 {current_metrics_record.get('step',0)}/{current_status_record.get('progress',{}).get('total','?')}스텝"
    if current_metrics_record.get('inference_estimate'):
        current_status_text+='\n\n추론 종료까지의 참고 추정\n\n'+render_generation_estimate(current_metrics_record['inference_estimate'],current_status_record['status'])
    for current_gpu_identifier,current_gpu_record in current_metrics_record.get('gpu_observations',{}).items():
        current_status_text+=f"\n\nGPU {current_gpu_identifier}: 현재 {current_gpu_record.get('process_current_mib')} MiB · 관측 피크 {current_gpu_record.get('process_peak_mib')} MiB · {current_gpu_record['scope']}"
    if current_metrics_record.get('measurement_gaps'):
        current_status_text+='\n\nVRAM 측정 누락 구간 존재: 실행 기록을 확인하세요.'
    return current_status_text


def build_vace_interface(current_server_address):
    with gr.Blocks(title='VACE 운영 중지') as current_retired_blocks:
        gr.Markdown('## VACE 생성기 운영 중지\nV2V 또는 FL2V 생성기를 사용하세요. 기존 결과와 생성이력은 보존되어 CLI에서 조회할 수 있습니다.\n[V2V 생성기 열기](/management/frame/vace-v2v-generator/?tool=vace-v2v-generator&category=animation-tool)')
    return current_retired_blocks


if __name__=='__main__':
    current_argument_parser=argparse.ArgumentParser()
    current_argument_parser.add_argument('--port',type=int,required=True)
    current_argument_parser.add_argument('--review-port',type=int,required=True)
    current_argument_parser.add_argument('--owner-pid',type=int,required=True)
    current_argument_parser.add_argument('--root-path',default='/management/frame/wan21-vace-generator/')
    current_argument_values=current_argument_parser.parse_args()
    build_vace_interface(f'http://127.0.0.1:{current_argument_values.review_port}').queue().launch(server_name='127.0.0.1',server_port=current_argument_values.port,root_path=current_argument_values.root_path,allowed_paths=[])
