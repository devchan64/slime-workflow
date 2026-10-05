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
from tools.review.common.gradio_identifiers import build_generation_identifier
from tools.review.common.gradio_logs import build_execution_logs, LOG_PANEL_STYLES
from tools.review.common.gradio_history import HISTORY_CARD_SELECTION_SCRIPT, build_generation_history_view, format_generation_status
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_reference_images import build_reference_image_inputs
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.management_client import execute_remote_management_command as execute_management_command

def execute_reference_gateway(command_name_value,payload_value):return execute_management_command('qwen-2511',command_name_value,payload_value)
def build_reference_request(prompt_text_value,generation_tag_value,reference_file_values,width_value,height_value,step_value,seed_value):
    reference_bytes_values=[] if not reference_file_values else list(reference_file_values)
    return {'action':'generate','prompt':prompt_text_value.strip(),'tag':generation_tag_value.strip(),'images':[base64.b64encode(current_file_value).decode() for current_file_value in reference_bytes_values],'width':int(width_value),'height':int(height_value),'steps':int(step_value),'seed':int(seed_value)}

def prepare_reference_image_bytes(reference_image_values, composite_transparent_background=False):
    from tools.review.domains.image.three_reference_generation import decode_reference_image
    reference_bytes_values=[]
    for reference_slot_number,current_reference_image in enumerate(reference_image_values,1):
        if current_reference_image is None:
            continue
        reference_image_buffer=io.BytesIO()
        current_reference_image.save(reference_image_buffer,format='PNG')
        current_reference_bytes=reference_image_buffer.getvalue()
        try:
            current_reference_bytes=decode_reference_image(base64.b64encode(current_reference_bytes).decode(), composite_transparent_background=composite_transparent_background)
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

def render_circular_comparison(current_selected_identifier, current_status_record, current_server_address):
    """공용 이력의 생성 ID·상태·서버 주소 계약으로 저장된 결과만 표시한다."""
    result_section_values = []
    for current_image_field, current_image_label in (
        ('image', '순환 VAE · 생성 원본'),
        ('baseline', '일반 VAE · 같은 잠재값'),
        ('baseline-preview', '일반 VAE · 3×3 반복 비교'),
    ):
        current_image_path = current_status_record.get(current_image_field)
        if not current_image_path:
            continue
        current_image_address = current_server_address.rstrip('/') + current_image_path
        result_section_values.append('<h3>' + current_image_label + '</h3>' + result_preview_html(current_image_address))
        if current_image_field == 'image':
            result_section_values.append('<h3>순환 VAE · 3×3 반복 검수</h3>' + result_preview_html(current_image_address.replace('/result.png', '/tiled-preview.png')))
    return ''.join(result_section_values) if result_section_values else '<p>아직 저장된 결과 이미지가 없습니다.</p>'


def build_qwen_2511_interface(server_base_address, expression_mode_enabled=False, qwen21_mode_enabled=False, circular_mode_enabled=False, pose_transfer_enabled=False):
    if expression_mode_enabled and qwen21_mode_enabled:
        raise ValueError("표정 생성과 Qwen 2.1 일반 생성은 별도 모드입니다.")
    from tools.review.domains.image.pose_transfer_generation import load_pose_transfer_prompt
    default_prompt_text = load_pose_transfer_prompt() if pose_transfer_enabled else ''
    reference_slot_count = 2 if pose_transfer_enabled else 10 if qwen21_mode_enabled else 3
    current_service_name = 'pose-transfer' if pose_transfer_enabled else 'qwen-21-circular' if circular_mode_enabled else 'qwen-21' if qwen21_mode_enabled else 'expression' if expression_mode_enabled else 'qwen-2511'
    current_page_title = '포즈 변환 생성기' if pose_transfer_enabled else 'Qwen 2.1 순환 VAE 생성기' if circular_mode_enabled else 'Qwen 2.1 이미지 생성기' if qwen21_mode_enabled else '표정 생성기' if expression_mode_enabled else 'Qwen 2511 3참조 생성기'
    def render_generation_preview(current_image_address):
        original_preview_html = result_preview_html(current_image_address)
        if circular_mode_enabled and current_image_address:
            return '<h3>생성 원본</h3>' + original_preview_html + '<h3>전체 이미지 · 3×3 반복 검수</h3>' + result_preview_html(current_image_address.replace('/result.png', '/tiled-preview.png'))
        return original_preview_html
    def execute_reference_gateway(command_name_value, payload_value):
        return execute_management_command(current_service_name, command_name_value, payload_value)
    def restore_selected_inputs(current_history_record):
        restored_input_values = list(restore_reference_inputs(current_history_record, WORKFLOW_ROOT_DIRECTORY/'.tmp/test/pose-transfer' if pose_transfer_enabled else WORKFLOW_ROOT_DIRECTORY/'.tmp/test/qwen-image-21-circular' if circular_mode_enabled else WORKFLOW_ROOT_DIRECTORY/'.tmp/test/qwen-image-21' if qwen21_mode_enabled else WORKFLOW_ROOT_DIRECTORY/'.tmp/test/expression-generator' if expression_mode_enabled else None, reference_slot_limit=reference_slot_count))
        if expression_mode_enabled:
            restored_input_values[0] = current_history_record['request']['expression']['id']
        if qwen21_mode_enabled and not pose_transfer_enabled:
            restored_input_values.extend(reference_upload_group.build_reference_updates(max(1, len(current_history_record["request"].get("references", [])))))
        if pose_transfer_enabled:
            restored_input_values[0] = gr.update(value=restored_input_values[0], interactive=True)
            restored_input_values.extend([False, current_history_record['request']['prompt']])
        if circular_mode_enabled:
            restored_input_values[0] = current_history_record['request'].get('user_prompt', restored_input_values[0])
            restored_input_values.extend([current_history_record['request'].get('circular_vae', {}).get('boundary_radius', 12), current_history_record['request'].get('soft_shading', False), current_history_record['request'].get('pattern_view', False), current_history_record['request'].get('circular_vae', {}).get('baseline_decode', False)])
        return tuple(restored_input_values)
    with gr.Blocks(title=current_page_title,js=HISTORY_CARD_SELECTION_SCRIPT) as interface_blocks_value:
        gr.Markdown('## '+current_page_title+'\n참조 이미지는 업로드한 순서대로 모델에 전달됩니다.')
        if circular_mode_enabled:
            gr.Markdown('생성 토큰 순환 Attention · 일반 VAE 비교 선택 · 참조 없는 텍스트 생성 실험 · 출력 전체가 타일입니다. 반복 경계의 형태 연결은 결과에서 검수하세요.')
        if expression_mode_enabled:
            gr.Markdown('Qwen-Image-Edit-2511 고정 · 참조 1~3장. 첫 이미지를 편집하고 추가 이미지는 동일 캐릭터의 외형 참고로 사용합니다. AU는 움직임 설계 참고이며 검출값·감정 판정·강도 측정이 아닙니다.')
        if pose_transfer_enabled:
            fixed_prompt_enabled = gr.Checkbox(value=True, label='고정 프롬프트 사용', info='ON: 기본 문구를 사용합니다. OFF: 프롬프트를 직접 편집합니다. 전환만으로 생성하지 않습니다.')
            custom_prompt_memory = gr.State(default_prompt_text)
        with gr.Row(equal_height=True):
            if expression_mode_enabled:
                from tools.review.domains.image.expression_generation import load_expression_configuration, build_expression_prompt
                expression_preset_records = load_expression_configuration()['expressions']
                prompt_text_value=gr.Dropdown([(record['label_ko'],record['id']) for record in expression_preset_records],value=expression_preset_records[0]['id'],label='표정 · AU 프리셋',scale=1,min_width=240)
            else:
                from generators.image.qwen_21_circular import CIRCULAR_DEFAULT_PROMPT
                prompt_text_value=gr.Textbox(value=CIRCULAR_DEFAULT_PROMPT if circular_mode_enabled else default_prompt_text,interactive=not pose_transfer_enabled,label='프롬프트',lines=3,scale=1,min_width=240)
            generation_tag_value=gr.Textbox(label='생성 이력 태그 · 선택 사항',placeholder='예: 돌온재 참조 후보',lines=3,scale=1,min_width=240)
        if qwen21_mode_enabled:
            gr.Markdown('아이덴티티 1장: 외형·비율·화풍. 포즈 1장: 자세·관절 배치. 두 장 모두 필수이며 한 장면을 생성합니다.' if pose_transfer_enabled else 'Qwen Image 2.1 · 추가 프롬프트 없음. 입력 원문을 그대로 전달합니다. 참조 없이 텍스트만으로도 생성할 수 있습니다.')
            def describe_plain_prompt(current_prompt_text):
                current_word_count = len(current_prompt_text.split())
                return f'사용자 {current_word_count}단어 · 추가 0단어 · 최종 {current_word_count}단어 (최대 99단어)'
            prompt_count_control = gr.Markdown(describe_plain_prompt(CIRCULAR_DEFAULT_PROMPT if circular_mode_enabled else default_prompt_text))
            if not circular_mode_enabled: prompt_text_value.change(describe_plain_prompt, prompt_text_value, prompt_count_control, queue=False)
        if circular_mode_enabled:
            from generators.image.qwen_21_circular import CIRCULAR_SOFT_SHADING_PROMPT, CIRCULAR_PATTERN_VIEW_PROMPT
            pattern_view_control=gr.Checkbox(value=True,label='탑뷰·반복 패턴·클로즈업 추가',info=CIRCULAR_PATTERN_VIEW_PROMPT)
            soft_shading_control=gr.Checkbox(value=False,label='부드러운 음영 일러스트 추가',info=CIRCULAR_SOFT_SHADING_PROMPT)
            def describe_circular_prompt(current_prompt_text, soft_shading_enabled, pattern_view_enabled):
                user_word_count=len(current_prompt_text.split())
                added_word_count=(len(CIRCULAR_SOFT_SHADING_PROMPT.split()) if soft_shading_enabled else 0)+(len(CIRCULAR_PATTERN_VIEW_PROMPT.split()) if pattern_view_enabled else 0)
                return f'사용자 {user_word_count}단어 · 추가 {added_word_count}단어 · 최종 {user_word_count+added_word_count}단어 (최대 99단어)'
            prompt_count_control.value=describe_circular_prompt(CIRCULAR_DEFAULT_PROMPT,False,True)
            for current_prompt_control in (prompt_text_value,soft_shading_control,pattern_view_control):
                current_prompt_control.change(describe_circular_prompt,[prompt_text_value,soft_shading_control,pattern_view_control],prompt_count_control,queue=False)
        if pose_transfer_enabled:
            def toggle_fixed_prompt(selected_fixed_enabled, current_prompt_text, saved_custom_prompt):
                if selected_fixed_enabled:
                    return gr.update(value=load_pose_transfer_prompt(), interactive=False), current_prompt_text
                return gr.update(value=saved_custom_prompt, interactive=True), saved_custom_prompt
            fixed_prompt_enabled.input(toggle_fixed_prompt, [fixed_prompt_enabled, prompt_text_value, custom_prompt_memory], [prompt_text_value, custom_prompt_memory], queue=False)
            def remember_custom_prompt(current_prompt_text):
                return current_prompt_text
            prompt_text_value.input(remember_custom_prompt, prompt_text_value, custom_prompt_memory, queue=False)
        elif not expression_mode_enabled:
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
        with gr.Accordion('참조 이미지 · 선택 · 최대 10장', open=False) if qwen21_mode_enabled and not pose_transfer_enabled else contextlib.nullcontext():
            reference_upload_group,reference_image_controls=build_reference_image_inputs(reference_image_mode=None, reference_slot_count=reference_slot_count, reference_slot_labels=['아이덴티티 이미지 · 필수','포즈 이미지 · 필수'] if pose_transfer_enabled else None)
        gr.Markdown(('생성 출력: 512×512 또는 768×768.' if pose_transfer_enabled else '생성 출력 최소 크기: 256×256.' if qwen21_mode_enabled else '생성 출력 최소 크기: 512×512.') + ' 참조 이미지의 크기·비율은 자유입니다. RGB/RGBA PNG, 장당 3MB 이하. ' + ('투명 영역은 흰색 배경에 합성해 전달합니다.' if qwen21_mode_enabled else '투명 배경은 사용할 수 없습니다.'))
        with gr.Row():
            width_value=gr.Dropdown([512,768] if pose_transfer_enabled else [256,512,768,1024,1280] if qwen21_mode_enabled else [512,768,1024,1280],value=512 if circular_mode_enabled else 768 if qwen21_mode_enabled else 512,label='해상도' if pose_transfer_enabled else '너비',scale=1,min_width=120)
            height_value=gr.Dropdown([512,768] if pose_transfer_enabled else [256,512,768,1024,1280] if qwen21_mode_enabled else [512,768,1024,1280],value=512 if circular_mode_enabled else 768 if qwen21_mode_enabled else 512,label='높이',visible=not pose_transfer_enabled,scale=1,min_width=120)
            step_value=gr.Dropdown([20,30,40,50],value=40,label='생성 스텝',scale=1,min_width=120) if qwen21_mode_enabled else gr.Radio([4,30],value=4,label='생성 스텝',scale=1,min_width=120)
            seed_value=build_generation_seed(10107)
            if circular_mode_enabled:
                baseline_decode_control=gr.Checkbox(value=False,label='일반 VAE 비교 생성',info='ON이면 동일 잠재값의 일반 VAE 결과와 반복 비교 이미지를 추가로 생성합니다.')
                circular_radius_control=gr.Dropdown([8,12,16],value=12,label='순환 참조 반경 · 토큰',info='좌우·상하 동일 적용 · 경계 1줄 참조 · 모서리 참조 없음')
        if pose_transfer_enabled:
            width_value.change(lambda selected_resolution_value: selected_resolution_value,width_value,height_value,queue=False)
        gr.Markdown('예상 시간: 실행 이력 기반 추정 자료를 수집 중입니다. 실행 로그에서 진행 단계를 확인하세요.')
        generation_button_value=gr.Button('이미지 생성 시작',variant='primary')
        status_value=gr.Markdown('생성 가능 · 설정을 확인하세요.')
        gr.Markdown('실행 중인 작업은 아래 생성 이력에서 선택한 뒤 **작업 중지**를 사용하세요.')
        identifier_value=build_generation_identifier()
        preview_value=gr.HTML(result_preview_html(None),elem_classes=['reference-result-preview'])
        gr.Markdown('포즈 변환 전용 생성 이력입니다. 기존 이미지 생성 이력과 별도로 관리합니다.' if pose_transfer_enabled else 'Qwen 2.1 전용 생성 이력입니다. 조회·삭제·초기화는 현재 생성기에만 적용됩니다.' if qwen21_mode_enabled else '표정 생성 이력은 Qwen 2511 참조 생성 이력과 별도로 관리합니다. 조회·삭제·초기화는 현재 생성기에만 적용됩니다.' if expression_mode_enabled else 'Qwen 2511 참조 생성 이력은 표정 생성 이력과 별도로 관리합니다. 조회·삭제·초기화는 현재 생성기에만 적용됩니다.')
        log_value,refresh_log_value,_=build_execution_logs()
        read_history_page,history_output_values=build_generation_history_view(
            execute_reference_gateway,server_base_address,
            '이력과 해당 생성기의 임시 작업 폴더(결과·참조 입력 사본·로그)를 함께 삭제합니다. 이전에 목록에서 제거한 작업도 포함합니다. 정식 에셋과 모델 캐시는 유지합니다. 대기·실행 중에는 초기화할 수 없습니다.',
            result_renderer_callback=render_circular_comparison if circular_mode_enabled else None,
            restore_input_callback=restore_selected_inputs,
            restore_output_components=[prompt_text_value,generation_tag_value,width_value,height_value,step_value,seed_value,*reference_image_controls,status_value]+(reference_upload_group.reference_slot_outputs if qwen21_mode_enabled and not pose_transfer_enabled else [])+([fixed_prompt_enabled, custom_prompt_memory] if pose_transfer_enabled else [])+([circular_radius_control,soft_shading_control,pattern_view_control,baseline_decode_control] if circular_mode_enabled else []),
            record_folder_route='/pose-transfer' if pose_transfer_enabled else '/image-generation-21-circular' if circular_mode_enabled else '/image-generation-21' if qwen21_mode_enabled else '/expression-generator' if expression_mode_enabled else '/image-generation-2511',allow_individual_delete=True)
        def start_reference_generation(prompt_text_value,generation_tag_value,*generation_input_values):
            if pose_transfer_enabled and any(current_reference_image is None for current_reference_image in generation_input_values[:2]):
                raise gr.Error('아이덴티티 이미지와 포즈 이미지를 각각 한 장 첨부하세요.')
            reference_bytes_values=prepare_reference_image_bytes(generation_input_values[:reference_slot_count], composite_transparent_background=qwen21_mode_enabled)
            width_value,height_value,step_value,seed_value=generation_input_values[reference_slot_count:reference_slot_count+4]
            if pose_transfer_enabled:height_value=width_value
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
                if circular_mode_enabled:
                    generation_request_value['circular_radius']=generation_input_values[-4]
                    generation_request_value['soft_shading']=generation_input_values[-3]
                    generation_request_value['pattern_view']=generation_input_values[-2]
                    generation_request_value['baseline_decode']=generation_input_values[-1]
                generation_record_value=execute_reference_gateway('generate',generation_request_value)
            except (ValueError,OSError) as generation_request_error:
                raise gr.Error(str(generation_request_error)) from generation_request_error
            return generation_record_value['id'],'상태: running'
        bind_gpu_generation_confirmation(generation_button_value,start_reference_generation,[prompt_text_value,generation_tag_value,*reference_image_controls,width_value,height_value,step_value,seed_value]+([circular_radius_control,soft_shading_control,pattern_view_control,baseline_decode_control] if circular_mode_enabled else []),[identifier_value,status_value])
        def refresh_status(identifier_text_value,refresh_log_enabled):
            if not identifier_text_value:return gr.skip(),gr.skip(),gr.skip()
            status_record_value=execute_reference_gateway('status',{'id':identifier_text_value});return '상태: '+format_generation_status(status_record_value),gr.update(value=status_record_value.get('log','')) if refresh_log_enabled else gr.skip(),render_generation_preview(status_record_value.get('image')) if status_record_value.get('image') else gr.skip()
        interface_blocks_value.load(lambda:read_history_page(1),outputs=history_output_values);gr.Button('상태 새로고침').click(refresh_status,[identifier_value,refresh_log_value],[status_value,log_value,preview_value],queue=False)
        if hasattr(gr,'Timer'):gr.Timer(2).tick(refresh_status,[identifier_value,refresh_log_value],[status_value,log_value,preview_value],queue=False,show_progress='hidden')
    return interface_blocks_value

from pathlib import Path as ManagementStylePath
MANAGEMENT_DENSITY_STYLES=(ManagementStylePath(__file__).parents[1]/'shared/management-density.css').read_text()
MANAGEMENT_SHARED_STYLES=(ManagementStylePath(__file__).parents[1]/'shared/management.css').read_text()+MANAGEMENT_DENSITY_STYLES

if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/management/frame/three-reference-generator/');arguments_value=parser_value.parse_args()
    threading.Thread(target=lambda: (time.sleep(1),os._exit(0)) if os.getppid()!=arguments_value.owner_pid else None,daemon=True).start()
    build_qwen_2511_interface(f'http://127.0.0.1:{arguments_value.review_port}').queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,theme=gr.themes.Soft(),css=LOG_PANEL_STYLES+'.qwen-result-image{max-width:100%;max-height:700px}.reference-result-preview .image-result-empty{min-height:0!important;display:grid;place-items:center}'+MANAGEMENT_SHARED_STYLES,allowed_paths=[])
