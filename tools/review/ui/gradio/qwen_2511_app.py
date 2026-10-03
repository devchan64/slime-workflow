"""Qwen 2511 3참조 생성기의 Gradio 클라이언트."""
import argparse
import contextlib
import base64
import html
import io
import hashlib
import re
from PIL import Image
import os
from pathlib import Path
import sys
import threading
import time
import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.gradio_logs import build_execution_logs, LOG_PANEL_STYLES
from tools.review.common.gradio_history import HISTORY_CARD_SELECTION_SCRIPT, build_generation_history_view
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_reference_images import build_reference_image_inputs
from tools.review.common.gradio_seed import generate_random_seed_value
from tools.review.common.management_client import execute_remote_management_command as execute_management_command

def execute_reference_gateway(command_name_value,payload_value):return execute_management_command('qwen-2511',command_name_value,payload_value)
def build_reference_request(prompt_text_value,generation_tag_value,reference_file_values,width_value,height_value,step_value,seed_value):
    reference_bytes_values=[] if not reference_file_values else list(reference_file_values)
    return {'action':'generate','prompt':prompt_text_value.strip(),'tag':generation_tag_value.strip(),'images':[base64.b64encode(current_file_value).decode() for current_file_value in reference_bytes_values],'width':int(width_value),'height':int(height_value),'steps':int(step_value),'seed':int(seed_value)}

def prepare_reference_image_bytes(reference_image_values):
    from tools.review.domains.image.three_reference_generation import decode_reference_image
    reference_bytes_values=[]
    for reference_slot_number,current_reference_image in enumerate(reference_image_values,1):
        if current_reference_image is None:
            continue
        reference_image_buffer=io.BytesIO()
        current_reference_image.save(reference_image_buffer,format='PNG')
        current_reference_bytes=reference_image_buffer.getvalue()
        try:
            decode_reference_image(base64.b64encode(current_reference_bytes).decode())
        except ValueError as reference_validation_error:
            reference_width_value,reference_height_value=current_reference_image.size
            raise gr.Error(f'참조 이미지 {reference_slot_number}: {reference_width_value}×{reference_height_value}, {current_reference_image.mode}. {reference_validation_error} 불투명 RGB/RGBA PNG로 준비해 다시 첨부하세요.') from reference_validation_error
        reference_bytes_values.append(current_reference_bytes)
    return reference_bytes_values


def restore_reference_inputs(current_history_record, reference_storage_root=None, reference_slot_limit=3):
    current_request_record=current_history_record.get('request',{})
    restored_reference_images=[]
    reference_snapshot_records=current_request_record.get('reference_snapshots',[])
    if reference_snapshot_records:
        generation_identifier_value=current_history_record.get('id','')
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}-[a-f0-9]{8}',generation_identifier_value):
            raise gr.Error('생성 ID 형식 오류')
        reference_storage_root=Path(reference_storage_root or WORKFLOW_ROOT_DIRECTORY/'.tmp/test/qwen-image-2511-three-reference').resolve()
        for reference_slot_number,current_snapshot_record in enumerate(reference_snapshot_records,1):
            if reference_slot_number>reference_slot_limit or current_snapshot_record['path']!=f'reference-{reference_slot_number}.png':
                raise gr.Error('참조 이미지 순서 또는 경로 오류')
            reference_source_path=(reference_storage_root/generation_identifier_value/current_snapshot_record['path']).resolve()
            if not reference_source_path.is_relative_to(reference_storage_root):raise gr.Error('참조 이미지 경로 오류')
            if not reference_source_path.is_file():raise gr.Error('저장된 참조 이미지가 없습니다: '+current_snapshot_record['path'])
            reference_source_bytes=reference_source_path.read_bytes()
            if hashlib.sha256(reference_source_bytes).hexdigest()!=current_snapshot_record['sha256']:raise gr.Error('참조 이미지 해시 불일치')
            with Image.open(io.BytesIO(reference_source_bytes)) as reference_image_value:
                restored_reference_images.append(reference_image_value.copy())
    restored_reference_images.extend([None]*(reference_slot_limit-len(restored_reference_images)))
    return (current_request_record.get('prompt',''),current_request_record.get('tag',''),current_request_record.get('width',512),current_request_record.get('height',512),current_request_record.get('steps',4),current_request_record.get('seed',10107),*restored_reference_images,'선택한 이력의 설정과 참조 이미지 '+str(len(reference_snapshot_records))+'장을 불러왔습니다.')

def result_preview_html(image_url_value):return f'<img class="qwen-result-image" src="{html.escape(image_url_value,quote=True)}" alt="Qwen 생성 결과">' if image_url_value else '<div class="image-result-empty">완료된 결과를 선택하세요.</div>'

def build_qwen_2511_interface(server_base_address, expression_mode_enabled=False, qwen21_mode_enabled=False):
    if expression_mode_enabled and qwen21_mode_enabled:
        raise ValueError("표정 생성과 Qwen 2.1 일반 생성은 별도 모드입니다.")
    reference_slot_count = 10 if qwen21_mode_enabled else 3
    current_service_name = 'qwen-21' if qwen21_mode_enabled else 'expression' if expression_mode_enabled else 'qwen-2511'
    current_page_title = 'Qwen 2.1 이미지 생성기' if qwen21_mode_enabled else '표정 생성기' if expression_mode_enabled else 'Qwen 2511 3참조 생성기'
    def execute_reference_gateway(command_name_value, payload_value):
        return execute_management_command(current_service_name, command_name_value, payload_value)
    def restore_selected_inputs(current_history_record):
        restored_input_values = list(restore_reference_inputs(current_history_record, WORKFLOW_ROOT_DIRECTORY/'.tmp/test/qwen-image-21' if qwen21_mode_enabled else WORKFLOW_ROOT_DIRECTORY/'.tmp/test/expression-generator' if expression_mode_enabled else None, reference_slot_limit=reference_slot_count))
        if expression_mode_enabled:
            restored_input_values[0] = current_history_record['request']['expression']['id']
        if qwen21_mode_enabled:
            restored_input_values.extend(reference_upload_group.build_reference_updates(max(1, len(current_history_record["request"].get("references", [])))))
        return tuple(restored_input_values)
    with gr.Blocks(title=current_page_title,js=HISTORY_CARD_SELECTION_SCRIPT) as interface_blocks_value:
        gr.Markdown('## '+current_page_title+'\n참조 이미지는 업로드한 순서대로 모델에 전달됩니다.')
        if expression_mode_enabled:
            gr.Markdown('Qwen-Image-Edit-2511 고정 · 참조 1~3장. 첫 이미지를 편집하고 추가 이미지는 동일 캐릭터의 외형 참고로 사용합니다. AU는 움직임 설계 참고이며 검출값·감정 판정·강도 측정이 아닙니다.')
        with gr.Row(equal_height=True):
            if expression_mode_enabled:
                from tools.review.domains.image.expression_generation import load_expression_configuration, build_expression_prompt
                expression_preset_records = load_expression_configuration()['expressions']
                prompt_text_value=gr.Dropdown([(record['label_ko'],record['id']) for record in expression_preset_records],value=expression_preset_records[0]['id'],label='표정 · AU 프리셋',scale=1,min_width=240)
            else:
                prompt_text_value=gr.Textbox(label='프롬프트',lines=3,scale=1,min_width=240)
            generation_tag_value=gr.Textbox(label='생성 이력 태그 · 선택 사항',placeholder='예: 돌온재 참조 후보',lines=3,scale=1,min_width=240)
        if qwen21_mode_enabled:
            gr.Markdown('Qwen Image 2.1 · 추가 프롬프트 없음. 입력 원문을 그대로 전달합니다. 참조 없이 텍스트만으로도 생성할 수 있습니다.')
            def describe_plain_prompt(current_prompt_text):
                current_word_count = len(current_prompt_text.split())
                return f'사용자 {current_word_count}단어 · 추가 0단어 · 최종 {current_word_count}단어 (최대 99단어)'
            prompt_count_control = gr.Markdown(describe_plain_prompt(''))
            prompt_text_value.change(describe_plain_prompt, prompt_text_value, prompt_count_control, queue=False)
        if not expression_mode_enabled:
            prompt_reset_button=gr.ClearButton([prompt_text_value],value='프롬프트 초기화',variant='secondary',size='sm')
        if expression_mode_enabled:
            def describe_expression_prompt(expression_identifier_value):
                final_prompt_value, expression_source_record = build_expression_prompt(expression_identifier_value)
                base_prompt_value = load_expression_configuration()['base_prompt']
                return ('AU 참고: '+', '.join('AU'+str(value) for value in expression_source_record['au_hints'])+
                        '\n\n움직임 ('+str(len(expression_source_record['movement_prompt'].split()))+'단어): '+expression_source_record['movement_prompt']+
                        '\n\n외형 유지 ('+str(len(base_prompt_value.split()))+'단어): '+base_prompt_value+
                        '\n\n최종 입력 ('+str(expression_source_record['prompt_word_count'])+'단어): '+final_prompt_value)
            expression_prompt_preview = gr.Markdown(describe_expression_prompt(expression_preset_records[0]['id']))
            prompt_text_value.change(describe_expression_prompt,prompt_text_value,expression_prompt_preview,queue=False)
        with gr.Accordion('참조 이미지 · 선택 · 최대 10장', open=False) if qwen21_mode_enabled else contextlib.nullcontext():
            reference_upload_group,reference_image_controls=build_reference_image_inputs(reference_image_mode=None, reference_slot_count=reference_slot_count)
        gr.Markdown('생성 출력 최소 크기: 512×512. 참조 이미지의 크기·비율은 자유입니다. RGB/RGBA PNG, 장당 3MB 이하이며 투명 배경은 사용할 수 없습니다.')
        with gr.Row():
            width_value=gr.Dropdown([512,768,1024,1280],value=1024 if qwen21_mode_enabled else 512,label='너비',scale=1,min_width=120)
            height_value=gr.Dropdown([512,768,1024,1280],value=1024 if qwen21_mode_enabled else 512,label='높이',scale=1,min_width=120)
            step_value=gr.Number(value=40,precision=0,label='생성 스텝 · 고정',interactive=False,scale=1,min_width=120) if qwen21_mode_enabled else gr.Radio([4,30],value=4,label='생성 스텝',scale=1,min_width=120)
            seed_value=gr.Number(value=10107,precision=0,label='Seed',scale=1,min_width=120)
            random_seed_button=gr.Button('무작위 생성',size='sm',scale=1,min_width=120)
        random_seed_button.click(generate_random_seed_value,outputs=seed_value,queue=False)
        gr.Markdown('예상 시간: 실행 이력 기반 추정 자료를 수집 중입니다. 실행 로그에서 진행 단계를 확인하세요.')
        generation_button_value=gr.Button('이미지 생성 시작',variant='primary')
        status_value=gr.Markdown('생성 가능 · 설정을 확인하세요.')
        gr.Markdown('실행 중인 작업은 아래 생성 이력에서 선택한 뒤 **작업 중지**를 사용하세요.')
        identifier_value=gr.Textbox(label='생성 ID',interactive=False,lines=1,max_lines=1)
        preview_value=gr.HTML(result_preview_html(None),elem_classes=['reference-result-preview'])
        gr.Markdown('Qwen 2.1 전용 생성 이력입니다. 조회·삭제·초기화는 현재 생성기에만 적용됩니다.' if qwen21_mode_enabled else '표정 생성 이력은 Qwen 2511 참조 생성 이력과 별도로 관리합니다. 조회·삭제·초기화는 현재 생성기에만 적용됩니다.' if expression_mode_enabled else 'Qwen 2511 참조 생성 이력은 표정 생성 이력과 별도로 관리합니다. 조회·삭제·초기화는 현재 생성기에만 적용됩니다.')
        log_value,refresh_log_value,_=build_execution_logs()
        read_history_page,history_output_values=build_generation_history_view(
            execute_reference_gateway,server_base_address,
            '이력과 해당 생성기의 임시 작업 폴더(결과·참조 입력 사본·로그)를 함께 삭제합니다. 이전에 목록에서 제거한 작업도 포함합니다. 정식 에셋과 모델 캐시는 유지합니다. 대기·실행 중에는 초기화할 수 없습니다.',
            restore_input_callback=restore_selected_inputs,
            restore_output_components=[prompt_text_value,generation_tag_value,width_value,height_value,step_value,seed_value,*reference_image_controls,status_value]+(reference_upload_group.reference_slot_outputs if qwen21_mode_enabled else []),
            record_folder_route='/image-generation-21' if qwen21_mode_enabled else '/expression-generator' if expression_mode_enabled else '/image-generation-2511',allow_individual_delete=True)
        def start_reference_generation(prompt_text_value,generation_tag_value,*generation_input_values):
            reference_bytes_values=prepare_reference_image_bytes(generation_input_values[:reference_slot_count])
            width_value,height_value,step_value,seed_value=generation_input_values[reference_slot_count:]
            from tools.review.domains.image.three_reference_generation import validate_three_reference_request
            try:
                generation_request_value=build_reference_request(prompt_text_value,generation_tag_value,reference_bytes_values,width_value,height_value,step_value,seed_value)
                if qwen21_mode_enabled:
                    from tools.review.domains.image.qwen_21_generation import validate_qwen_plain_request
                    generation_request_value['prompt'] = prompt_text_value
                    validate_qwen_plain_request(generation_request_value)
                elif expression_mode_enabled:
                    from tools.review.domains.image.expression_generation import ExpressionGenerationManager
                    ExpressionGenerationManager().validate_generation_request(generation_request_value)
                else:
                    validate_three_reference_request(generation_request_value)
                generation_record_value=execute_reference_gateway('generate',generation_request_value)
            except (ValueError,OSError) as generation_request_error:
                raise gr.Error(str(generation_request_error)) from generation_request_error
            return generation_record_value['id'],'상태: running'
        bind_gpu_generation_confirmation(generation_button_value,start_reference_generation,[prompt_text_value,generation_tag_value,*reference_image_controls,width_value,height_value,step_value,seed_value],[identifier_value,status_value])
        def refresh_status(identifier_text_value,refresh_log_enabled):
            if not identifier_text_value:return gr.skip(),gr.skip(),gr.skip()
            status_record_value=execute_reference_gateway('status',{'id':identifier_text_value});return '상태: '+status_record_value['status'],gr.update(value=status_record_value.get('log','')) if refresh_log_enabled else gr.skip(),result_preview_html(status_record_value.get('image')) if status_record_value.get('image') else gr.skip()
        interface_blocks_value.load(lambda:read_history_page(1),outputs=history_output_values);gr.Button('상태 새로고침').click(refresh_status,[identifier_value,refresh_log_value],[status_value,log_value,preview_value],queue=False)
        if hasattr(gr,'Timer'):gr.Timer(2).tick(refresh_status,[identifier_value,refresh_log_value],[status_value,log_value,preview_value],show_progress='hidden')
    return interface_blocks_value

from pathlib import Path as ManagementStylePath
MANAGEMENT_DENSITY_STYLES=(ManagementStylePath(__file__).parents[1]/'shared/management-density.css').read_text()
MANAGEMENT_SHARED_STYLES=(ManagementStylePath(__file__).parents[1]/'shared/management.css').read_text()+MANAGEMENT_DENSITY_STYLES

if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/management/frame/three-reference-generator/');arguments_value=parser_value.parse_args()
    threading.Thread(target=lambda: (time.sleep(1),os._exit(0)) if os.getppid()!=arguments_value.owner_pid else None,daemon=True).start()
    build_qwen_2511_interface(f'http://127.0.0.1:{arguments_value.review_port}').queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,theme=gr.themes.Soft(),css=LOG_PANEL_STYLES+'.qwen-result-image{max-width:100%;max-height:700px}.reference-result-preview .image-result-empty{min-height:0!important;display:grid;place-items:center}'+MANAGEMENT_SHARED_STYLES,allowed_paths=[])
