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
    current_defaults_record=load_vace_defaults()
    with gr.Blocks(title='Wan2.1 VACE 영상 생성기') as current_interface_blocks:
        gr.Markdown('## Wan2.1 VACE 영상 생성기\nR2V: 캐릭터 참조 1장과 장면 묘사로 영상을 생성합니다. 비디오·첫 프레임·마스크는 입력하지 않습니다. 생성 결과는 검수 전 후보입니다.')
        with gr.Row():
            with gr.Column():
                current_reference_group,current_reference_controls=build_reference_image_inputs(reference_image_mode=None,reference_slot_count=1)
                current_prompt_control=gr.Textbox(label='장면·동작 프롬프트',lines=4)
                current_prompt_summary=gr.Markdown(describe_vace_prompt(''))
                current_prompt_control.change(describe_vace_prompt,current_prompt_control,current_prompt_summary,queue=False)
                current_resolution_control=gr.Dropdown(['832×480','480×832','512×512'],value='832×480',label='해상도 · 가로×세로')
                current_frames_control=gr.Number(value=current_defaults_record['frames'],precision=0,minimum=1,maximum=161,step=4,label='프레임 수 · 4n+1 (1~161) · 16fps')
                current_seed_control=build_generation_seed(default_seed_value=42)
                gr.Markdown('고정: Wan2.1 VACE 1.3B · R2V · 16fps · UniPC · CUDA 연산 / CPU 메모리 오프로드. 1프레임은 정지 샘플입니다.')
                with gr.Accordion('추론 파라미터',open=True):
                    current_steps_control=gr.Number(value=current_defaults_record['steps'],precision=0,minimum=1,maximum=100,label='추론 스텝')
                    current_shift_control=gr.Number(value=current_defaults_record['flow_shift'],minimum=0.1,maximum=30,label='Flow shift')
                    current_guidance_control=gr.Number(value=current_defaults_record['guidance_scale'],minimum=1,maximum=20,label='CFG')
                    current_conditioning_control=gr.Number(value=current_defaults_record['conditioning_scale'],minimum=0,maximum=2,label='참조 조건 강도')
                with gr.Accordion('부정 프롬프트',open=False):
                    current_negative_control=gr.Textbox(value=current_defaults_record['negative_prompt'],label='부정 프롬프트',lines=2)
                    current_negative_summary=gr.Markdown(describe_vace_prompt(current_defaults_record['negative_prompt']))
                    current_negative_control.change(describe_vace_prompt,current_negative_control,current_negative_summary,queue=False)
                current_generate_button=gr.Button('영상 생성',variant='primary')
                gr.Markdown('생성 중에는 버튼이 비활성화됩니다. 완료를 기다리거나 이력에서 선택 작업을 중지하세요.')
            with gr.Column():
                current_job_control=gr.Textbox(label='생성 ID')
                current_status_display=gr.Markdown('생성 후 상태가 5초마다 갱신됩니다. 이력에서 이전 입력을 불러올 수 있습니다.')
                current_result_display=gr.HTML('<p>완료 후 결과를 표시합니다.</p>')
        current_result_identity=gr.State('')
        current_log_output,current_log_refresh,_=build_execution_logs()
        def start_vace_generation(*current_input_values):
            current_job_record=execute_vace_command('generate',build_vace_payload(*current_input_values))
            return current_job_record['id'],'GPU 대기열에 등록했습니다.',gr.update(interactive=False)
        current_generate_button.click(start_vace_generation,[*current_reference_controls,current_prompt_control,current_frames_control,current_seed_control,current_negative_control,current_resolution_control,current_steps_control,current_shift_control,current_guidance_control,current_conditioning_control],[current_job_control,current_status_display,current_generate_button],trigger_mode='once')
        def refresh_vace_result(current_job_identifier,current_logs_enabled,current_previous_result):
            if not current_job_identifier:
                return gr.skip(),gr.skip(),gr.skip(),gr.skip(),gr.skip()
            current_status_record=execute_vace_command('status',{'id':current_job_identifier})
            current_result_identity_value=current_status_record.get('video','')
            return describe_vace_status(current_status_record),render_vace_result(current_job_identifier,current_status_record,current_server_address) if current_result_identity_value and current_result_identity_value!=current_previous_result else gr.skip(),current_status_record.get('log','') if current_logs_enabled else gr.skip(),current_result_identity_value,gr.update(interactive=current_status_record['status'] not in ('running','queued'))
        current_refresh_timer=gr.Timer(5)
        current_refresh_timer.tick(refresh_vace_result,[current_job_control,current_log_refresh,current_result_identity],[current_status_display,current_result_display,current_log_output,current_result_identity,current_generate_button],queue=False,show_progress='hidden')
        def restore_vace_inputs(current_history_record):
            if current_history_record['request'].get('vace',{}).get('task') != 'r2v':
                raise gr.Error('이 이력은 비디오·마스크 조건 실험입니다. 현재 R2V 입력 화면으로 복원할 수 없습니다. 기록 위치에서 원본 입력을 확인하세요.')
            current_reference_path=VACE_JOB_STORAGE_ROOT/current_history_record['id']/'reference-1.png'
            if not current_reference_path.resolve().is_relative_to(VACE_JOB_STORAGE_ROOT.resolve()):
                raise ValueError('참조 경로 오류')
            current_request_record=current_history_record['request']
            return Image.open(current_reference_path).copy(),current_request_record['prompt'],current_request_record['frames'],current_request_record['seed'],current_request_record['vace']['negative_prompt'],f"{current_request_record['width']}×{current_request_record['height']}",current_request_record['steps'],current_request_record['vace']['flow_shift'],current_request_record['vace']['guidance_scale'],current_request_record['vace']['conditioning_scale'],current_history_record['id']
        current_read_history,current_history_outputs=build_generation_history_view(execute_vace_command,current_server_address,'목록에서만 제거하며 입력·결과·로그는 보존합니다.',restore_input_callback=restore_vace_inputs,restore_output_components=[*current_reference_controls,current_prompt_control,current_frames_control,current_seed_control,current_negative_control,current_resolution_control,current_steps_control,current_shift_control,current_guidance_control,current_conditioning_control,current_job_control],result_renderer_callback=render_vace_result,record_folder_route='/wan21-vace',allow_individual_delete=True,individual_delete_scope_text='목록에서만 제거합니다. 파일은 보존합니다.')
        current_interface_blocks.load(lambda:current_read_history(1),outputs=current_history_outputs)
        current_interface_blocks.load(lambda:execute_vace_command('active',{}).get('id') or '',outputs=current_job_control)
    return current_interface_blocks


if __name__=='__main__':
    current_argument_parser=argparse.ArgumentParser()
    current_argument_parser.add_argument('--port',type=int,required=True)
    current_argument_parser.add_argument('--review-port',type=int,required=True)
    current_argument_parser.add_argument('--owner-pid',type=int,required=True)
    current_argument_parser.add_argument('--root-path',default='/management/frame/wan21-vace-generator/')
    current_argument_values=current_argument_parser.parse_args()
    build_vace_interface(f'http://127.0.0.1:{current_argument_values.review_port}').queue().launch(server_name='127.0.0.1',server_port=current_argument_values.port,root_path=current_argument_values.root_path,allowed_paths=[])
