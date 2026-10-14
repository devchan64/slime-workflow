"""VACE V2V: 번호가 있는 포즈 이미지로 영상과 수정 마스크를 구성한다."""
import argparse
import base64
import io
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
import gradio as gr
from PIL import Image
from generators.vace.timeline import validate_timeline_request,VACE_TIMELINE_STORAGE_ROOT,VACE_TIMELINE_FLOW_SHIFT,VACE_PADDING_COLOR_DEFAULT
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_logs import build_execution_logs
from tools.review.common.gradio_video_results import render_video_generation_result,describe_video_generation_status
from tools.review.ui.gradio.management_menu_app import compose_management_interface


def execute_timeline_command(current_command_name,current_payload_record):
    return execute_remote_management_command('wan21-vace-v2v',current_command_name,current_payload_record)


def warn_image_resolution(current_file_paths):
    current_mismatch_count=0
    for current_file_path in current_file_paths or []:
        with Image.open(current_file_path) as current_source_image:
            current_mismatch_count += current_source_image.size != (832,480)
    if current_mismatch_count:
        gr.Warning(f'{current_mismatch_count}장 이미지가 832×480이 아닙니다. 생성 등록 시 비율을 유지해 리사이즈하고 선택한 여백 색상으로 채웁니다. 원본 파일은 보존합니다.')


def load_timeline_images(current_file_paths):
    if not current_file_paths or any(not Path(current_file_path).stem.isdigit() or not 1 <= int(Path(current_file_path).stem) <= 161 for current_file_path in current_file_paths):
        raise gr.Error('1.png처럼 1부터 시작하는 원래 프레임 번호의 PNG를 첨부하세요.')
    warn_image_resolution(current_file_paths)
    current_sorted_paths=sorted(current_file_paths,key=lambda current_file_path:int(Path(current_file_path).stem))
    current_table_rows=[[int(Path(current_file_path).stem),True] for current_file_path in current_sorted_paths]
    current_preview_images=[(current_file_path,Path(current_file_path).name) for current_file_path in current_sorted_paths]
    current_last_frame=max(current_row_value[0] for current_row_value in current_table_rows)
    return current_sorted_paths,current_table_rows,current_preview_images,((current_last_frame-1+3)//4)*4+1


def build_timeline_payload(current_file_paths,current_table_rows,current_prompt_text,current_negative_text,current_frame_count,current_seed_value,current_resolution_text,current_steps_value,current_shift_value,current_guidance_value,current_conditioning_value,current_identity_path=None,current_padding_color=VACE_PADDING_COLOR_DEFAULT):
    if len(current_file_paths or [])!=len(current_table_rows or []):
        raise ValueError('이미지 목록과 배치표가 일치하지 않습니다. 이미지를 다시 불러오세요.')
    current_encoded_images=[]
    current_frame_entries=[]
    for current_file_path,current_table_row in zip(current_file_paths,current_table_rows):
        current_frame_number=current_table_row[0]
        if isinstance(current_frame_number,bool) or float(current_frame_number)!=int(current_frame_number):
            raise ValueError('배치 프레임 번호는 정수여야 합니다.')
        with Image.open(current_file_path) as current_source_image:
            current_image_buffer=io.BytesIO()
            current_source_image.save(current_image_buffer,format='PNG')
        current_encoded_images.append(base64.b64encode(current_image_buffer.getvalue()).decode())
        current_frame_entries.append({'frame':int(current_frame_number)-1,'editable':current_table_row[1]})
    if current_identity_path:
        with Image.open(current_identity_path) as current_identity_image:
            current_identity_buffer=io.BytesIO()
            current_identity_image.save(current_identity_buffer,format='PNG')
        current_encoded_images.append(base64.b64encode(current_identity_buffer.getvalue()).decode())
    current_image_width,current_image_height=map(int,current_resolution_text.split('×'))
    current_payload_record=dict(action='generate',images=current_encoded_images,frame_entries=current_frame_entries,prompt=current_prompt_text,negative_prompt=current_negative_text,frames=current_frame_count,seed=current_seed_value,width=current_image_width,height=current_image_height,steps=current_steps_value,flow_shift=current_shift_value,guidance_scale=current_guidance_value,conditioning_scale=current_conditioning_value)
    current_payload_record['padding_color']=current_padding_color
    current_payload_record['identity_reference_count']=int(bool(current_identity_path))
    validate_timeline_request(current_payload_record)
    return current_payload_record


def build_timeline_interface(current_server_address):
    with gr.Blocks(title='Wan2.1 VACE V2V 생성기') as current_interface_blocks:
        gr.Markdown('## Wan2.1 VACE 1.3B V2V 생성기\n중간 포즈 이미지를 원래 프레임 번호에 배치해 영상을 다시 생성합니다. 입력 원본은 보존합니다.')
        current_input_files=gr.File(file_count='multiple',file_types=['.png'],label='번호가 있는 포즈 PNG · 예: 1.png, 18.png, 35.png')
        current_sorted_files=gr.State([])
        current_frame_table=gr.Dataframe(headers=['프레임 번호 · 1부터','수정 가능 · 흰 마스크'],datatype=['number','bool'],type='array',col_count=(2,'fixed'),interactive=True,label='이미지 순서대로 배치 · 체크 해제 시 검은 마스크로 보존')
        gr.Markdown('빠진 프레임은 회색(127) 영상과 흰 마스크로 생성합니다. 수정 가능한 이미지도 다시 그려지므로 포즈·신체 비율 유지가 보장되지는 않습니다. 현재 마스크는 프레임 전체에 적용합니다.')
        current_input_gallery=gr.Gallery(label='배치 이미지',allow_preview=False,columns=4)
        current_identity_control=gr.Image(type='filepath',label='외형 참조 이미지 · 선택 1장',sources=['upload'],height=240)
        current_identity_control.change(lambda current_image_path:warn_image_resolution([current_image_path] if current_image_path else []),current_identity_control,queue=False)
        gr.Markdown('얼굴·색상·그림체의 기준입니다. 영상 프레임에 배치하거나 첫 프레임을 고정하지 않습니다.')
        current_prompt_control=gr.Textbox(label='장면 프롬프트',value='',lines=4)
        current_prompt_summary=gr.Markdown('원문 0단어 · 최종 0단어')
        current_prompt_control.change(lambda current_prompt_text:f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어 · 추가 문구 없음',current_prompt_control,current_prompt_summary,queue=False)
        gr.Button('장면 프롬프트 초기화').click(lambda:'',outputs=current_prompt_control,queue=False)
        with gr.Accordion('부정 프롬프트 · 기본값 없음',open=False):
            current_negative_control=gr.Textbox(value='',label='부정 프롬프트',lines=2)
            current_negative_summary=gr.Markdown('원문 0단어 · 최종 0단어')
            current_negative_control.change(lambda current_prompt_text:f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어',current_negative_control,current_negative_summary,queue=False)
            gr.Button('부정 프롬프트 초기화').click(lambda:'',outputs=current_negative_control,queue=False)
        current_resolution_control=gr.Textbox(value='832×480',label='출력 해상도 · 480P 고정',interactive=False)
        gr.Markdown('출력은 832×480으로 고정됩니다. 이전 이력을 불러와도 새 생성은 이 해상도를 사용하며, 내용을 자르지 않고 비율을 유지해 맞춘 뒤 남는 공간을 선택한 색상으로 채웁니다.')
        current_padding_control=gr.ColorPicker(value=VACE_PADDING_COLOR_DEFAULT,label="여백 색상 · 기본 흰색")
        current_frames_control=gr.Number(value=37,precision=0,minimum=1,maximum=161,step=4,label='프레임 수 · 4n+1 · 16fps')
        current_duration_text=gr.Markdown('37프레임 · 약 2.31초 · 16fps')
        current_frames_control.change(lambda current_frame_count:f'{current_frame_count}프레임 · 약 {current_frame_count/16:.2f}초 · 16fps',current_frames_control,current_duration_text,queue=False)
        current_input_files.change(load_timeline_images,current_input_files,[current_sorted_files,current_frame_table,current_input_gallery,current_frames_control])
        current_seed_control=build_generation_seed(default_seed_value=42)
        gr.Markdown('고정 모델: Wan2.1 VACE 1.3B · CUDA 연산 · CPU 가중치 오프로드 · UniPC · 16fps')
        with gr.Accordion('고급 설정',open=False):
            current_steps_control=gr.Number(value=50,precision=0,minimum=1,maximum=100,label='추론 스텝 · 1~100 정수',info='기본값 50. 노이즈를 정리하는 반복 횟수입니다. 높이면 생성 시간이 늘어나며, 품질이 반드시 좋아지지는 않습니다.')
            current_shift_control=gr.Number(value=VACE_TIMELINE_FLOW_SHIFT,minimum=0.1,maximum=30,label='Flow shift · 0.1~30',info='기본값 3. 추론 스텝을 어느 노이즈 구간에 배분할지 조절합니다. 높이면 노이즈가 많은 구간에 더 배분합니다. 움직임의 크기나 원본 보존율을 직접 정하는 값은 아닙니다.')
            current_guidance_control=gr.Number(value=5.0,minimum=1,maximum=20,label='텍스트 가이던스 (CFG) · 1~20',info='기본값 5. 텍스트 프롬프트의 유도 강도입니다. 높이면 문구의 영향이 강해지지만 왜곡이나 과한 표현이 생길 수 있습니다. 낮추면 시선·구도 등 지시가 약해질 수 있습니다.')
            current_conditioning_control=gr.Number(value=1.0,minimum=0,maximum=2,label='조건 강도 · 0~2',info='기본값 1.0. 입력 영상·마스크·외형 참조로 만든 조건의 영향력입니다. 높이면 입력 조건의 영향이 커지고, 낮추면 자유롭게 생성할 여지가 커집니다. 포즈와 외형 참조에 함께 적용되며 참조만의 독립 강도는 없습니다. 높다고 외형 유사도가 반드시 좋아지지는 않습니다.')
        current_generate_button=gr.Button('영상 생성 설정 확인',variant='primary')
        gr.Markdown('설정 확인 후 아래 확인 영역의 **대기열에 추가**를 눌러 등록하세요. **추가하지 않기**를 누르면 등록하지 않습니다.')
        with gr.Column() as current_confirmation_container:
            pass
        current_job_control=gr.Textbox(label='생성 ID')
        current_status_display=gr.Markdown('입력을 확인한 후 생성하세요.')
        current_result_display=gr.HTML('')
        current_result_identity=gr.State('')
        current_log_output,current_log_refresh,_=build_execution_logs()
        current_input_controls=[current_sorted_files,current_frame_table,current_prompt_control,current_negative_control,current_frames_control,current_seed_control,current_resolution_control,current_steps_control,current_shift_control,current_guidance_control,current_conditioning_control,current_identity_control,current_padding_control]
        def start_timeline_generation(*current_input_values):
            current_job_record=execute_timeline_command('generate',build_timeline_payload(*current_input_values))
            return current_job_record['id'],'GPU 대기열에 등록했습니다.'
        bind_gpu_generation_confirmation(current_generate_button,start_timeline_generation,current_input_controls,[current_job_control,current_status_display],generation_confirmation_container=current_confirmation_container)
        def refresh_timeline_result(current_job_identifier,current_logs_enabled,current_previous_result):
            if not current_job_identifier:return gr.skip(),gr.skip(),gr.skip(),gr.skip()
            current_status_record=execute_timeline_command('status',{'id':current_job_identifier})
            current_result_url=current_status_record.get('video','')
            return describe_video_generation_status(current_status_record),render_video_generation_result(current_job_identifier,current_status_record,current_server_address) if current_result_url and current_result_url!=current_previous_result else gr.skip(),current_status_record.get('log','') if current_logs_enabled else gr.skip(),current_result_url
        gr.Timer(5).tick(refresh_timeline_result,[current_job_control,current_log_refresh,current_result_identity],[current_status_display,current_result_display,current_log_output,current_result_identity],queue=False,show_progress='hidden')
        def restore_timeline_inputs(current_history_record):
            current_request_record=current_history_record['request']
            current_job_root=VACE_TIMELINE_STORAGE_ROOT/current_history_record['id']
            from generators.vace.timeline import verify_timeline_request
            verify_timeline_request(current_job_root)
            current_file_paths=[str(current_job_root/current_file_name) for current_file_name in current_request_record['references'][:len(current_request_record['frame_entries'])]]
            current_table_rows=[[current_frame_entry['frame']+1,current_frame_entry['editable']] for current_frame_entry in current_request_record['frame_entries']]
            current_model_config=current_request_record['vace']
            return current_file_paths,current_table_rows,current_request_record['prompt'],current_model_config['negative_prompt'],current_request_record['frames'],current_request_record['seed'],'832×480',current_request_record['steps'],current_model_config['flow_shift'],current_model_config['guidance_scale'],current_model_config['conditioning_scale'],str(current_job_root/current_request_record['references'][-1]) if current_request_record.get('identity_reference_count') else None,current_request_record.get('padding_color',VACE_PADDING_COLOR_DEFAULT),current_file_paths,current_history_record['id']
        current_read_history,current_history_outputs=build_generation_history_view(execute_timeline_command,current_server_address,GENERATION_CLEANUP_SCOPE_TEXT,restore_input_callback=restore_timeline_inputs,restore_output_components=[*current_input_controls,current_input_gallery,current_job_control],result_renderer_callback=render_video_generation_result,record_folder_route='/wan21-vace-v2v',allow_individual_delete=True,individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda:current_read_history(1),outputs=current_history_outputs)
        current_interface_blocks.load(lambda:execute_timeline_command('active',{}).get('id') or '',outputs=current_job_control)
    return current_interface_blocks


if __name__=='__main__':
    current_argument_parser=argparse.ArgumentParser()
    current_argument_parser.add_argument('--port',type=int,required=True)
    current_argument_parser.add_argument('--review-port',type=int,required=True)
    current_argument_parser.add_argument('--owner-pid',type=int,required=True)
    current_argument_parser.add_argument('--root-path',default='/management/frame/vace-v2v-generator/')
    current_argument_values=current_argument_parser.parse_args()
    compose_management_interface(build_timeline_interface(f'http://127.0.0.1:{current_argument_values.review_port}'),current_argument_values.review_port).queue().launch(server_name='127.0.0.1',server_port=current_argument_values.port,root_path=current_argument_values.root_path,allowed_paths=[])
