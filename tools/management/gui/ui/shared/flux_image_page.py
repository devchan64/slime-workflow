"""용도별 FLUX 이미지 생성 페이지의 공통 구성."""
import base64
import html
import importlib
import io
import re
from pathlib import Path
import gradio as gr
from generators.image.common_art_style import compose_common_style_prompt
from tools.management.common.gradio_generator_changelog import build_generator_changelog
from tools.management.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.management.common.gradio_history import build_generation_history_view
from tools.management.common.reference_restore import HistoryInputError
from tools.management.domains.image.flux_input_restore import restore_flux_image_inputs as restore_saved_inputs
from tools.management.common.gradio_seed import build_generation_seed
from tools.management.common.management_client import execute_remote_management_command
from tools.management.domains.image.flux_image_generation import require_flux_image_profile

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[5]


def restore_flux_image_inputs(current_history_record, current_profile_name):
    storage_root = WORKFLOW_ROOT_DIRECTORY / '.tmp/test' / (current_profile_name + '-generator')
    try:
        return restore_saved_inputs(current_history_record, current_profile_name, storage_root)
    except HistoryInputError as error:
        raise gr.Error(str(error)) from error


def describe_flux_image_prompt(current_prompt_text):
    if not current_prompt_text or not current_prompt_text.strip():
        return '프롬프트를 입력하세요.'
    if re.search('[가-힣]',current_prompt_text):
        return '한국어 입력은 번역 대기열에서 처리하며, 번역 완료 후 공용 화풍과 결합한 최종 모델 입력이 결정됩니다.'
    current_final_prompt,current_style_record = compose_common_style_prompt(current_prompt_text)
    current_style_note = '입력에 포함됨' if current_style_record['already_present'] else '자동 적용'
    return (f'**최종 모델 입력** · 입력 {len(current_prompt_text.split())}단어 · '
            f'공용 화풍 v{current_style_record["version"]} {len(current_style_record["prompt"].split())}단어 ({current_style_note}) · '
            f'최종 {len(current_final_prompt.split())}단어\n\n{current_final_prompt}')


def execute_flux_image_command(current_profile_name, current_command_name, current_payload_record):
    return execute_remote_management_command(current_profile_name,current_command_name,current_payload_record)


def render_flux_seamless_comparison(current_selected_identifier, current_status_record, current_server_address):
    current_result_path=current_status_record.get('image')
    if not current_result_path:
        return '<p>아직 저장된 결과 이미지가 없습니다.</p>'
    if not isinstance(current_selected_identifier,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_selected_identifier):
        return '<p>생성 ID가 올바르지 않아 결과를 표시할 수 없습니다.</p>'
    current_result_address=f'/flux-seamless-generator/jobs/{current_selected_identifier}/result.png'
    if current_result_path != current_result_address:
        return '<p>저장된 결과 경로가 선택한 이력과 일치하지 않습니다.</p>'
    current_preview_address=current_result_address.removesuffix('result.png')+'tiled-preview.png'
    current_raw_address=current_result_address.removesuffix('result.png')+'raw-result.png'
    current_method_value=current_status_record.get('seamless_method','edge-blend')
    if current_method_value in ('global-periodic-v1','circular-vae-v2'):
        current_label_value='전역 주기 어텐션 · 순환 VAE 타일' if current_method_value=='global-periodic-v1' else '순환 VAE 타일'
        return '<h3>'+current_label_value+'</h3><img width="100%" src="'+html.escape(current_result_address,quote=True)+'" alt="타일"><h3>3×3 반복 검수</h3><img width="100%" src="'+html.escape(current_preview_address,quote=True)+'" alt="3×3 반복 검수">'
    current_result_label='순환 VAE 타일' if current_method_value=='circular-vae' else '경계 보간 타일'
    current_html_value='<h3>일반 VAE 생성 원본</h3><img width="100%" src="'+html.escape(current_raw_address,quote=True)+'" alt="생성 원본"><h3>'+current_result_label+'</h3><img width="100%" src="'+html.escape(current_result_address,quote=True)+'" alt="타일"><h3>3×3 반복 검수</h3><img width="100%" src="'+html.escape(current_preview_address,quote=True)+'" alt="3×3 반복 검수">'
    if current_method_value=='circular-vae':
        current_blend_address=current_result_address.removesuffix('result.png')+'blend-preview.png'
        current_html_value += '<h3>동일 잠재값 · 기존 경계 보간 3×3</h3><img width="100%" src="'+html.escape(current_blend_address,quote=True)+'" alt="경계 보간 반복 비교">'
    return current_html_value


def build_flux_image_page(current_profile_name, current_server_address, current_review_port):
    current_label_text,current_description_text,current_default_width,current_default_height,current_minimum_references = require_flux_image_profile(current_profile_name)
    def execute_profile_command(current_command_name,current_payload_record):
        return execute_flux_image_command(current_profile_name,current_command_name,current_payload_record)
    with gr.Blocks() as current_page_blocks:
        gr.Markdown(f'## FLUX 3 {current_label_text} 생성기\n{current_description_text}\n\n결과는 검수용 후보이며 비율·색상·화풍을 보장하지 않습니다. 투명 참조는 흰 배경에 합성하며 투명 출력은 제공하지 않습니다.')
        if current_profile_name == 'flux-seamless':
            gr.Markdown('전역 최단 주기 어텐션과 16개 위치 순환 이동, 순환 패딩 VAE를 적용합니다. 새 작업은 512×512·참조 이미지 없음만 지원합니다. 기존 이력 재개는 저장 당시 설정을 유지합니다. VAE 타일링은 사용하지 않습니다.')
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
            from tools.management.domains.image.billboard_guide_prompt import BILLBOARD_LAYOUT_PROFILES, BILLBOARD_DEFAULT_SUBJECT, load_billboard_guide_image, compose_billboard_guide_prompt
            current_guide_control=gr.Dropdown(choices=list(BILLBOARD_LAYOUT_PROFILES),value=BILLBOARD_LAYOUT_PROFILES[0],label='점유 가이드 검색·선택',filterable=True)
            current_subject_control=gr.Textbox(value=BILLBOARD_DEFAULT_SUBJECT,label='생성 대상')
            current_guide_button=gr.Button('선택한 가이드와 프롬프트 적용')
        if current_profile_name == 'flux-building':
            from tools.management.ui.gradio.building_guide_gallery import build_building_guide_gallery, apply_selected_building_guide
            current_building_control,current_building_button=build_building_guide_gallery()
        current_default_prompt=''
        if current_profile_name == 'flux-seamless':
            current_default_prompt='Top-down repeatable ground texture with even lighting. Material: '
        if current_profile_name in ('flux-prop','flux-vegetation'):
            current_source_name={'flux-prop':'prop-qwen-prompt.txt','flux-vegetation':'vegetation-qwen-prompt.txt','flux-building':'building-qwen-prompt.txt'}[current_profile_name]
            current_default_prompt=(WORKFLOW_ROOT_DIRECTORY/'generators/image/config'/current_source_name).read_text().strip().replace('transparent background','plain background')
        current_prompt_control=gr.Textbox(value=current_default_prompt,label='건물 디자인 (한국어)' if current_profile_name=='flux-building' else '프롬프트',lines=4)
        if current_profile_name == 'flux-building':
            from tools.management.domains.image.building_prompt import load_building_base_prompt
            current_prepared_prompt=load_building_base_prompt().replace('transparent background','plain background')
            gr.Markdown('한국어 디자인은 번역 대기열에서 영어로 번역한 뒤 건물 기본 문구·공용 화풍과 결합하여 자동 생성합니다. 번역 결과와 검토 항목은 생성 이력에서 확인하세요.')
            current_prepared_final,current_prepared_style=compose_common_style_prompt(current_prepared_prompt)
            current_final_display=gr.Markdown(f'**준비 문구 · 번역 전** · 건물 기본 {len(current_prepared_prompt.split())}단어 · 공용 화풍 v{current_prepared_style["version"]} {len(current_prepared_style["prompt"].split())}단어\n\n{current_prepared_final}\n\n번역 완료 후 영어 디자인이 추가되어 최종 모델 입력이 결정됩니다.')
        else:
            current_korean_control=gr.Textbox(label='한국어 설명 (선택)',lines=3,placeholder='생성할 대상과 원하는 세부 사항을 한국어로 입력하세요.')
            gr.Markdown('한국어 설명은 번역 대기열을 거쳐 영어로 변환한 뒤 위 준비 문구와 공용 화풍에 결합해 자동 생성합니다. 번역 결과와 검토 항목은 이력에서 확인하세요.')
            current_final_display=gr.Markdown(describe_flux_image_prompt(current_default_prompt))
            current_prompt_control.change(describe_flux_image_prompt,current_prompt_control,current_final_display,queue=False)
        with gr.Row():
            current_first_reference=gr.Image(label='참조 1 · 새 심리스 작업 사용 불가' if current_profile_name=='flux-seamless' else '참조 1',type='pil',image_mode='RGBA')
            current_second_reference=gr.Image(label='참조 2 · 새 심리스 작업 사용 불가' if current_profile_name=='flux-seamless' else '참조 2 (선택)',type='pil',image_mode='RGBA')
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
            current_building_button.click(apply_selected_building_guide,current_building_control,current_first_reference,queue=False)
        current_maximum_size=2048 if current_profile_name=='flux-character' else 1664
        with gr.Row():
            current_width_control=gr.Number(value=current_default_width,minimum=256,maximum=current_maximum_size,precision=0,label='너비')
            current_height_control=gr.Number(value=current_default_height,minimum=256,maximum=current_maximum_size,precision=0,label='높이')
        if current_profile_name=='flux-character':
            gr.Markdown('출력 크기는 가로·세로 각각 256~2048px의 16 배수입니다. 1664px 초과 크기는 이 장비에서 실제 생성·메모리 사용량을 아직 검증하지 않았습니다.')
        if current_profile_name == 'flux-mannequin':
            def apply_mannequin_stage(current_preset_identifier):
                current_prompt_text,current_first_image,current_second_image=current_mannequin_module.load_mannequin_preset(current_preset_identifier)
                current_width_value,current_height_value=(1024,1024) if current_preset_identifier=='face' else (768,1152)
                return current_prompt_text,current_first_image,current_second_image,current_width_value,current_height_value
            current_preset_button.click(apply_mannequin_stage,current_preset_control,[current_prompt_control,current_first_reference,current_second_reference,current_width_control,current_height_control],queue=False)
        current_step_control=gr.Number(value=16,minimum=1 if current_profile_name=='flux-character' else 16,maximum=50 if current_profile_name=='flux-character' else 16,precision=0,label='생성 스텝',interactive=current_profile_name=='flux-character')
        if current_profile_name == 'flux-character':
            gr.Markdown('스텝은 1~50에서 선택합니다. 50은 이 생성기의 운영상 상한이며 모델의 최대 스텝이나 최적값을 뜻하지 않습니다.')
        gr.Markdown('공용 화풍 v1.5.0 · 프롬프트 확장기, 마스크와 VAE 타일링 사용 안 함 · 16 이외 스텝의 품질은 별도 검수 · 예상 시간 계산 중')
        current_seed_control=build_generation_seed()
        current_tag_control=gr.Textbox(label='이력 태그 (선택)')
        current_start_button=gr.Button('대기열에 추가',interactive=False,variant='primary')
        gr.Markdown('프롬프트와 필수 첫 참조를 입력하면 생성할 수 있습니다.')
        with gr.Column() as current_confirmation_container: pass
        current_job_control=gr.Textbox(visible=False)
        current_status_control=gr.Markdown('결과와 작업 상태는 아래 생성 이력에서 확인하세요.')
        def check_flux_image_readiness(current_prompt_text,current_first_image,current_korean_value=''):
            return bool(((current_prompt_text and current_prompt_text.strip()) or (current_korean_value and current_korean_value.strip())) and (not current_minimum_references or current_first_image is not None))
        def start_flux_image_generation(current_prompt_text,current_first_image,current_second_image,current_width_value,current_height_value,current_step_value,current_seed_value,current_tag_value,current_korean_value=''):
            if current_profile_name == 'flux-seamless' and (current_first_image is not None or current_second_image is not None or current_width_value != 512 or current_height_value != 512):
                raise gr.Error('새 심리스 작업은 512×512와 참조 이미지 없음만 지원합니다. 이전 이력은 원래 방식으로 재개할 수 있습니다.')
            if current_second_image is not None and current_first_image is None: raise gr.Error('두 번째 참조는 첫 참조와 함께 사용하세요.')
            current_image_values=[]
            for current_image_value in (current_first_image,current_second_image):
                if current_image_value is not None:
                    current_image_buffer=io.BytesIO(); current_image_value.save(current_image_buffer,format='PNG'); current_image_values.append(base64.b64encode(current_image_buffer.getvalue()).decode())
            current_payload_record={'action':'generate','prompt':current_prompt_text or '','images':current_image_values,'width':int(current_width_value),'height':int(current_height_value),'steps':int(current_step_value),'seed':int(current_seed_value),'tag':current_tag_value or ''}
            if current_profile_name == 'flux-building' and re.search('[가-힣]',current_prompt_text):
                current_payload_record['building_design_ko']=current_prompt_text
            elif current_profile_name != 'flux-building' and current_korean_value and current_korean_value.strip():
                current_payload_record['translation_source_ko']=current_korean_value.strip()
            current_result_record=execute_profile_command('generate',current_payload_record)
            return current_result_record['id'],'대기열에 등록했습니다. 생성 이력을 새로고침해 확인하세요.'
        current_input_controls=[current_prompt_control,current_first_reference,current_second_reference,current_width_control,current_height_control,current_step_control,current_seed_control,current_tag_control]+([current_korean_control] if current_profile_name!='flux-building' else [])
        current_readiness_inputs=[current_prompt_control,current_first_reference]+([current_korean_control] if current_profile_name!='flux-building' else [])
        bind_gpu_generation_confirmation(current_start_button,start_flux_image_generation,current_input_controls,[current_job_control,current_status_control],generation_confirmation_container=current_confirmation_container,generation_readiness_callback=check_flux_image_readiness,generation_readiness_inputs=current_readiness_inputs)
        build_generation_history_view(execute_profile_command,current_server_address,'이 생성기의 FLUX 이력과 결과를 삭제합니다.',restore_input_callback=lambda current_history_record:restore_flux_image_inputs(current_history_record,current_profile_name),restore_output_components=current_input_controls,result_renderer_callback=render_flux_seamless_comparison if current_profile_name=='flux-seamless' else None,record_folder_route='/'+current_profile_name+'-generator',allow_individual_delete=True,observed_job_control=current_job_control,history_deep_link_interface=current_page_blocks)
    return current_page_blocks
