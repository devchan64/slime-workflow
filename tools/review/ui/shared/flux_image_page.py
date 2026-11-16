"""용도별 FLUX 이미지 생성 페이지의 공통 구성."""
import base64
import hashlib
import html
import importlib
import io
from pathlib import Path
import gradio as gr
from generators.image.common_art_style import compose_common_style_prompt
from tools.review.common.gradio_generator_changelog import build_generator_changelog
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_reference_restore import restore_reference_inputs, validate_history_input_settings
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.management_client import execute_remote_management_command
from tools.review.domains.image.flux_image_generation import require_flux_image_profile

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]


def restore_flux_image_inputs(current_history_record, current_profile_name):
    current_request_record = validate_history_input_settings(current_history_record)
    current_user_prompt = current_request_record.get('user_prompt')
    if not isinstance(current_user_prompt,str) or not current_user_prompt.strip() or current_request_record.get('profile') != current_profile_name:
        raise gr.Error('저장된 사용자 프롬프트 또는 생성기 정보가 없습니다.')
    current_final_prompt,_ = compose_common_style_prompt(current_user_prompt)
    if current_request_record.get('prompt') != current_final_prompt or current_request_record.get('prompt_sha256') != hashlib.sha256(current_final_prompt.encode()).hexdigest():
        raise gr.Error('저장된 프롬프트가 현재 화풍과 다르거나 변조되어 복원할 수 없습니다.')
    if current_request_record.get('steps') != 16 or type(current_request_record.get('seed')) is not int or not 0 <= current_request_record['seed'] <= 4294967295:
        raise gr.Error('저장된 스텝 또는 시드가 올바르지 않습니다.')
    if any(type(current_request_record.get(name)) is not int or not 256 <= current_request_record[name] <= 1664 or current_request_record[name] % 16 for name in ('width','height')):
        raise gr.Error('저장된 출력 크기가 올바르지 않습니다.')
    current_restored_values = restore_reference_inputs(current_history_record, WORKFLOW_ROOT_DIRECTORY/'.tmp/test'/(current_profile_name+'-generator'),reference_slot_limit=2)
    return (current_user_prompt,current_restored_values[6],current_restored_values[7],current_restored_values[2],current_restored_values[3],current_restored_values[5],current_restored_values[1])


def describe_flux_image_prompt(current_prompt_text):
    if not current_prompt_text or not current_prompt_text.strip():
        return '프롬프트를 입력하세요.'
    current_final_prompt,_ = compose_common_style_prompt(current_prompt_text)
    return f'입력 {len(current_prompt_text.split())}단어 · 최종 {len(current_final_prompt.split())}단어\n\n{current_final_prompt}'


def execute_flux_image_command(current_profile_name, current_command_name, current_payload_record):
    return execute_remote_management_command(current_profile_name,current_command_name,current_payload_record)


def render_flux_seamless_comparison(current_selected_identifier, current_status_record, current_server_address):
    current_result_path=current_status_record.get('image')
    if not current_result_path:
        return '<p>아직 저장된 결과 이미지가 없습니다.</p>'
    current_result_address=current_server_address.rstrip('/')+current_result_path
    current_preview_address=current_result_address.removesuffix('result.png')+'tiled-preview.png'
    current_raw_address=current_result_address.removesuffix('result.png')+'raw-result.png'
    return '<h3>FLUX 생성 원본</h3><img width="100%" src="'+html.escape(current_raw_address,quote=True)+'" alt="생성 원본"><h3>경계 보간 타일</h3><img width="100%" src="'+html.escape(current_result_address,quote=True)+'" alt="타일"><h3>3×3 반복 검수</h3><img width="100%" src="'+html.escape(current_preview_address,quote=True)+'" alt="3×3 반복 검수">'


def build_flux_image_page(current_profile_name, current_server_address, current_review_port):
    current_label_text,current_description_text,current_default_width,current_default_height,current_minimum_references = require_flux_image_profile(current_profile_name)
    def execute_profile_command(current_command_name,current_payload_record):
        return execute_flux_image_command(current_profile_name,current_command_name,current_payload_record)
    with gr.Blocks() as current_page_blocks:
        gr.Markdown(f'## FLUX 3 {current_label_text} 생성기\n{current_description_text}\n\n결과는 검수용 후보이며 비율·색상·화풍을 보장하지 않습니다. 투명 참조는 흰 배경에 합성하며 투명 출력은 제공하지 않습니다. 기존 Qwen 이력은 이미지 생성 아카이브에서 조회하세요.')
        if current_profile_name == 'flux-seamless':
            gr.Markdown('FLUX 출력의 반대편 가장자리 색을 보간합니다. 이는 Qwen 순환 VAE나 다단계 보정이 아니며 무늬 연결과 흐림은 반복 미리보기로 검수하세요.')
        build_generator_changelog(current_page_blocks,current_profile_name+'-generator')
        if current_profile_name == 'flux-mannequin':
            current_mannequin_module=importlib.import_module('generators.mannequin-generator.page.interface')
            current_preset_choices=[(v[0],k) for k,v in current_mannequin_module.MANNEQUIN_PRESET_RECORDS.items()]
            current_preset_control=gr.Dropdown(choices=current_preset_choices,value=current_preset_choices[0][1],label='마네킨 제작 단계')
            current_preset_button=gr.Button('선택한 단계와 프롬프트 예시 불러오기')
        if current_profile_name == 'flux-character':
            current_body_module=importlib.import_module('generators.character-generator.body_references')
            current_body_gallery=importlib.import_module('generators.character-generator.page.body_reference_gallery')
            current_body_control,current_body_button=current_body_gallery.build_body_reference_gallery()
        if current_profile_name == 'flux-billboard':
            from tools.review.domains.image.billboard_guide_prompt import BILLBOARD_LAYOUT_PROFILES, BILLBOARD_DEFAULT_SUBJECT, load_billboard_guide_image, compose_billboard_guide_prompt
            current_guide_control=gr.Dropdown(choices=list(BILLBOARD_LAYOUT_PROFILES),value=BILLBOARD_LAYOUT_PROFILES[0],label='점유 가이드 검색·선택',filterable=True)
            current_subject_control=gr.Textbox(value=BILLBOARD_DEFAULT_SUBJECT,label='생성 대상')
            current_guide_button=gr.Button('선택한 가이드와 프롬프트 적용')
        if current_profile_name == 'flux-building':
            from tools.review.domains.image.building_prompt import BUILDING_LAYOUT_PRESET_NAMES, load_building_layout_preset
            current_building_control=gr.Dropdown(choices=list(BUILDING_LAYOUT_PRESET_NAMES),label='건물 배치 가이드 검색·선택',filterable=True)
            current_building_button=gr.Button('선택한 건물 가이드를 첫 참조에 적용')
        current_default_prompt=''
        if current_profile_name == 'flux-seamless':
            current_default_prompt='Top-down repeatable ground texture with even lighting. Material: '
        if current_profile_name in ('flux-prop','flux-vegetation','flux-building'):
            current_source_name={'flux-prop':'prop-qwen-prompt.txt','flux-vegetation':'vegetation-qwen-prompt.txt','flux-building':'building-qwen-prompt.txt'}[current_profile_name]
            current_default_prompt=(WORKFLOW_ROOT_DIRECTORY/'generators/image/config'/current_source_name).read_text().strip().replace('transparent background','plain background')
        current_prompt_control=gr.Textbox(value=current_default_prompt,label='프롬프트',lines=4)
        current_final_display=gr.Markdown(describe_flux_image_prompt(current_default_prompt))
        current_prompt_control.change(describe_flux_image_prompt,current_prompt_control,current_final_display,queue=False)
        with gr.Row():
            current_first_reference=gr.Image(label='참조 1',type='pil',image_mode='RGBA')
            current_second_reference=gr.Image(label='참조 2 (선택)',type='pil',image_mode='RGBA')
        if current_profile_name == 'flux-character':
            def apply_body_reference(current_reference_id,current_prompt_text):
                if not current_reference_id: raise gr.Error('신체 비율 기준을 선택하세요.')
                current_role_text=current_body_module.BODY_REFERENCE_ROLE_PROMPT
                return current_body_module.load_body_reference_image(current_reference_id), current_prompt_text if current_role_text in current_prompt_text else (current_prompt_text.strip()+' '+current_role_text).strip()
            current_body_button.click(apply_body_reference,[current_body_control,current_prompt_control],[current_first_reference,current_prompt_control],queue=False)
        if current_profile_name == 'flux-billboard':
            def apply_billboard_reference(current_profile_identifier,current_subject_text):
                return load_billboard_guide_image(current_profile_identifier),compose_billboard_guide_prompt(current_profile_identifier,current_subject_text).replace('transparent background','plain background')
            current_guide_button.click(apply_billboard_reference,[current_guide_control,current_subject_control],[current_first_reference,current_prompt_control],queue=False)
        if current_profile_name == 'flux-building':
            current_building_button.click(load_building_layout_preset,current_building_control,current_first_reference,queue=False)
        with gr.Row():
            current_width_control=gr.Number(value=current_default_width,minimum=256,maximum=1664,precision=0,label='너비')
            current_height_control=gr.Number(value=current_default_height,minimum=256,maximum=1664,precision=0,label='높이')
        if current_profile_name == 'flux-mannequin':
            def apply_mannequin_stage(current_preset_identifier):
                current_prompt_text,current_first_image,current_second_image=current_mannequin_module.load_mannequin_preset(current_preset_identifier)
                current_width_value,current_height_value=(1024,1024) if current_preset_identifier=='face' else (768,1152)
                return current_prompt_text,current_first_image,current_second_image,current_width_value,current_height_value
            current_preset_button.click(apply_mannequin_stage,current_preset_control,[current_prompt_control,current_first_reference,current_second_reference,current_width_control,current_height_control],queue=False)
        gr.Markdown('16단계 · 공용 화풍 v1.5.0 · 프롬프트 확장기, 마스크와 VAE 타일링 사용 안 함 · 예상 시간 계산 중')
        current_seed_control=build_generation_seed()
        current_tag_control=gr.Textbox(label='이력 태그 (선택)')
        current_start_button=gr.Button('대기열에 추가',interactive=False,variant='primary')
        gr.Markdown('프롬프트와 필수 첫 참조를 입력하면 생성할 수 있습니다.')
        with gr.Column() as current_confirmation_container: pass
        current_job_control=gr.Textbox(visible=False)
        current_status_control=gr.Markdown('결과와 작업 상태는 아래 생성 이력에서 확인하세요.')
        def check_flux_image_readiness(current_prompt_text,current_first_image):
            return bool(current_prompt_text and current_prompt_text.strip() and (not current_minimum_references or current_first_image is not None))
        def start_flux_image_generation(current_prompt_text,current_first_image,current_second_image,current_width_value,current_height_value,current_seed_value,current_tag_value):
            if current_second_image is not None and current_first_image is None: raise gr.Error('두 번째 참조는 첫 참조와 함께 사용하세요.')
            current_image_values=[]
            for current_image_value in (current_first_image,current_second_image):
                if current_image_value is not None:
                    current_image_buffer=io.BytesIO(); current_image_value.save(current_image_buffer,format='PNG'); current_image_values.append(base64.b64encode(current_image_buffer.getvalue()).decode())
            current_payload_record={'action':'generate','prompt':current_prompt_text,'images':current_image_values,'width':int(current_width_value),'height':int(current_height_value),'steps':16,'seed':int(current_seed_value),'tag':current_tag_value or ''}
            current_result_record=execute_profile_command('generate',current_payload_record)
            return current_result_record['id'],'대기열에 등록했습니다. 생성 이력을 새로고침해 확인하세요.'
        bind_gpu_generation_confirmation(current_start_button,start_flux_image_generation,[current_prompt_control,current_first_reference,current_second_reference,current_width_control,current_height_control,current_seed_control,current_tag_control],[current_job_control,current_status_control],generation_confirmation_container=current_confirmation_container,generation_readiness_callback=check_flux_image_readiness,generation_readiness_inputs=[current_prompt_control,current_first_reference])
        build_generation_history_view(execute_profile_command,current_server_address,'이 생성기의 FLUX 이력과 결과를 삭제합니다.',restore_input_callback=lambda current_history_record:restore_flux_image_inputs(current_history_record,current_profile_name),restore_output_components=[current_prompt_control,current_first_reference,current_second_reference,current_width_control,current_height_control,current_seed_control,current_tag_control],result_renderer_callback=render_flux_seamless_comparison if current_profile_name=='flux-seamless' else None,record_folder_route='/'+current_profile_name+'-generator',allow_individual_delete=True,observed_job_control=current_job_control)
    return current_page_blocks
