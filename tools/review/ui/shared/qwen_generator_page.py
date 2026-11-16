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
from tools.review.common.gradio_generator_changelog import build_generator_changelog, GENERATOR_CHANGELOG_PATHS
WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.generation_status_lookup import read_existing_generation_status
from tools.review.common.generation_status_display import describe_generation_status
from tools.review.common.gradio_identifiers import build_generation_identifier
from tools.review.common.gradio_results import build_generation_gallery, collect_generation_gallery
from tools.review.common.gradio_logs import build_execution_logs
from tools.review.common.gradio_history import build_generation_history_view, format_generation_status
from tools.review.common.gradio_model_download import build_model_readiness_controls
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_reference_images import build_reference_image_inputs, REFERENCE_IMAGE_CARD_HEIGHT
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_reference_restore import restore_reference_inputs
from tools.review.common.gradio_seed import build_generation_seed, select_generation_seed_value, QWEN_SEED_GUIDANCE
from tools.review.common.management_client import execute_remote_management_command as execute_management_command

def check_circular_prompt_readiness(current_prompt_text, current_shading_enabled, current_pattern_enabled):
    from generators.image.qwen_21_circular import CIRCULAR_SOFT_SHADING_PROMPT, CIRCULAR_PATTERN_VIEW_PROMPT
    from generators.image.common_art_style import compose_common_style_prompt
    current_styled_prompt, current_style_record = compose_common_style_prompt(' '.join((current_prompt_text, CIRCULAR_SOFT_SHADING_PROMPT if current_shading_enabled else '', CIRCULAR_PATTERN_VIEW_PROMPT if current_pattern_enabled else '')))
    current_word_count = len(current_styled_prompt.split())
    return bool(current_prompt_text.strip() or current_shading_enabled or current_pattern_enabled) and 0 < current_word_count < 100

def check_expression_reference_readiness(*current_reference_values):
    return any((current_reference_value is not None for current_reference_value in current_reference_values))

def check_plain_prompt_readiness(current_prompt_text, current_style_enabled, current_transparency_enabled):
    from generators.image.qwen_21_prompt_options import compose_qwen_option_prompt
    from generators.image.common_art_style import compose_common_style_prompt
    current_styled_prompt, current_style_record = compose_common_style_prompt(current_prompt_text)
    current_final_prompt, current_added_prompt = compose_qwen_option_prompt(current_styled_prompt, False, current_transparency_enabled)
    return bool(current_prompt_text.strip()) and 0 < len(current_final_prompt.split()) < 100

def execute_reference_gateway(command_name_value, payload_value):
    return execute_management_command('qwen-2511', command_name_value, payload_value)

def build_reference_request(prompt_text_value, generation_tag_value, reference_file_values, width_value, height_value, step_value, seed_value):
    reference_bytes_values = [] if not reference_file_values else list(reference_file_values)
    return {'action': 'generate', 'prompt': prompt_text_value.strip(), 'tag': generation_tag_value.strip(), 'images': [base64.b64encode(current_file_value).decode() for current_file_value in reference_bytes_values], 'width': int(width_value), 'height': int(height_value), 'steps': int(step_value), 'seed': int(seed_value)}

def prepare_reference_image_bytes(reference_image_values, composite_transparent_background=False):
    from tools.review.domains.image.three_reference_generation import decode_reference_image
    reference_bytes_values = []
    for reference_slot_number, current_reference_image in enumerate(reference_image_values, 1):
        if current_reference_image is None:
            continue
        reference_image_buffer = io.BytesIO()
        current_reference_image.save(reference_image_buffer, format='PNG')
        current_reference_bytes = reference_image_buffer.getvalue()
        try:
            current_reference_bytes = decode_reference_image(base64.b64encode(current_reference_bytes).decode(), composite_transparent_background=composite_transparent_background)
        except ValueError as reference_validation_error:
            reference_width_value, reference_height_value = current_reference_image.size
            raise gr.Error(f'참조 이미지 {reference_slot_number}: {reference_width_value}×{reference_height_value}, {current_reference_image.mode}. {reference_validation_error} 불투명 RGB/RGBA PNG로 준비해 다시 첨부하세요.') from reference_validation_error
        reference_bytes_values.append(current_reference_bytes)
    return reference_bytes_values

def result_preview_html(image_url_value, current_image_label='Qwen 생성 결과'):
    return f'<img width="100%" class="qwen-result-image" src="{html.escape(image_url_value, quote=True)}" alt="{html.escape(current_image_label, quote=True)}">' if image_url_value else '<div class="image-result-empty">완료된 결과를 선택하세요.</div>'

def render_circular_comparison(current_selected_identifier, current_status_record, current_server_address):
    """공용 이력의 생성 ID·상태·서버 주소 계약으로 저장된 결과만 표시한다."""
    result_section_values = []
    for current_image_field, current_image_label in (('image', '순환 VAE · 생성 원본'), ('baseline', '일반 VAE · 같은 잠재값'), ('baseline-preview', '일반 VAE · 3×3 반복 비교')):
        current_image_path = current_status_record.get(current_image_field)
        if not current_image_path:
            continue
        current_image_address = current_server_address.rstrip('/') + current_image_path
        result_section_values.append('<h3>' + current_image_label + '</h3>' + result_preview_html(current_image_address, current_image_label))
        if current_image_field == 'image':
            result_section_values.append('<h3>순환 VAE · 3×3 반복 검수</h3>' + result_preview_html(current_image_address.replace('/result.png', '/tiled-preview.png'), '순환 VAE · 3×3 반복 검수'))
    return ''.join(result_section_values) if result_section_values else '<p>아직 저장된 결과 이미지가 없습니다.</p>'

def build_qwen_2511_interface(server_base_address, expression_mode_enabled=False, qwen21_mode_enabled=False, circular_mode_enabled=False, pose_transfer_enabled=False, outfit_transfer_enabled=False, building_mode_enabled=False, prop_mode_enabled=False, vegetation_mode_enabled=False, billboard_guide_enabled=False, character_mode_enabled=False, mannequin_mode_enabled=False):
    if billboard_guide_enabled and (not (prop_mode_enabled and qwen21_mode_enabled)):
        raise ValueError('빌보드 가이드는 소품 Qwen 2.1 모드에서 사용합니다.')
    if sum((building_mode_enabled, prop_mode_enabled, vegetation_mode_enabled)) > 1:
        raise ValueError('건물·소품·자연물 페이지는 별도 모드입니다.')
    if (building_mode_enabled or prop_mode_enabled or vegetation_mode_enabled) and (not qwen21_mode_enabled or expression_mode_enabled or circular_mode_enabled or pose_transfer_enabled or outfit_transfer_enabled):
        raise ValueError('에셋 페이지는 Qwen 2.1 일반 생성 모드만 지원합니다.')
    from tools.review.domains.image.building_prompt import load_building_base_prompt, load_prop_base_prompt, load_vegetation_base_prompt, check_building_input_readiness
    if pose_transfer_enabled:
        raise ValueError('포즈 변환 생성기는 폐기되었습니다.')
    if expression_mode_enabled and qwen21_mode_enabled:
        raise ValueError('표정 생성과 Qwen 2.1 일반 생성은 별도 모드입니다.')
    if outfit_transfer_enabled:
        raise ValueError('복장 착용 생성기와 이력은 폐기되었습니다.')
    if character_mode_enabled and (not qwen21_mode_enabled or any((expression_mode_enabled, circular_mode_enabled, building_mode_enabled, prop_mode_enabled, vegetation_mode_enabled, billboard_guide_enabled))):
        raise ValueError('캐릭터 화면은 일반 Qwen 2.1 모드만 지원합니다.')
    if mannequin_mode_enabled and (not qwen21_mode_enabled or any((character_mode_enabled, expression_mode_enabled, circular_mode_enabled, building_mode_enabled, prop_mode_enabled, vegetation_mode_enabled, billboard_guide_enabled))):
        raise ValueError('마네킨 화면은 일반 Qwen 2.1 모드만 지원합니다.')
    from importlib import import_module
    character_default_prompt = import_module('generators.character-generator.page.interface').load_character_default_prompt() if character_mode_enabled else ''
    default_prompt_text = character_default_prompt if character_mode_enabled else load_vegetation_base_prompt() if vegetation_mode_enabled else load_prop_base_prompt() if prop_mode_enabled else '' if building_mode_enabled else load_outfit_transfer_prompt() if outfit_transfer_enabled else ''
    plain_options_enabled = qwen21_mode_enabled and (not circular_mode_enabled) and (not outfit_transfer_enabled) and (not outfit_transfer_enabled)
    reference_slot_count = 2 if outfit_transfer_enabled else 10 if qwen21_mode_enabled else 3
    current_service_name = 'mannequin-generator' if mannequin_mode_enabled else 'billboard-generator' if billboard_guide_enabled else 'prop-generator' if prop_mode_enabled else 'vegetation-generator' if vegetation_mode_enabled else 'building-generator' if building_mode_enabled else 'outfit-transfer' if outfit_transfer_enabled else 'qwen-21-circular' if circular_mode_enabled else 'qwen-21' if qwen21_mode_enabled else 'expression' if expression_mode_enabled else 'qwen-2511'
    current_page_title = 'Qwen 2.1 빌보드 자연물타입 생성기' if vegetation_mode_enabled else 'Qwen 2.1 빌보드 소품타입 생성기' if prop_mode_enabled else 'Qwen 2.1 건물 생성기' if building_mode_enabled else '복장 착용 생성기' if outfit_transfer_enabled else 'Qwen 2.1 순환 VAE 생성기' if circular_mode_enabled else 'Qwen 2.1 이미지 생성기' if qwen21_mode_enabled else 'Qwen 2.1 표정 생성기' if expression_mode_enabled else 'Qwen 2511 3참조 생성기'
    if character_mode_enabled:
        current_page_title = 'Qwen 2.1 캐릭터 이미지 생성기'
    if mannequin_mode_enabled:
        current_page_title = 'Qwen 2.1 마네킨 생성기'
    if billboard_guide_enabled:
        current_page_title = 'Qwen2.1 빌보드 가이드참조 생성기'

    def execute_reference_gateway(command_name_value, payload_value):
        return execute_management_command(current_service_name, command_name_value, payload_value)

    def restore_selected_inputs(current_history_record):
        restored_input_values = list(restore_reference_inputs(current_history_record, WORKFLOW_ROOT_DIRECTORY / '.tmp/test/mannequin-generator' if mannequin_mode_enabled else WORKFLOW_ROOT_DIRECTORY / '.tmp/test/billboard-generator' if billboard_guide_enabled else WORKFLOW_ROOT_DIRECTORY / '.tmp/test/prop-generator' if prop_mode_enabled else WORKFLOW_ROOT_DIRECTORY / '.tmp/test/vegetation-generator' if vegetation_mode_enabled else WORKFLOW_ROOT_DIRECTORY / '.tmp/test/building-generator' if building_mode_enabled else WORKFLOW_ROOT_DIRECTORY / '.tmp/test/outfit-transfer' if outfit_transfer_enabled else WORKFLOW_ROOT_DIRECTORY / '.tmp/test/qwen-image-21-circular' if circular_mode_enabled else WORKFLOW_ROOT_DIRECTORY / '.tmp/test/qwen-image-21' if qwen21_mode_enabled else WORKFLOW_ROOT_DIRECTORY / '.tmp/test/expression-generator' if expression_mode_enabled else None, reference_slot_limit=reference_slot_count))
        if expression_mode_enabled:
            current_expression_record = current_history_record['request'].get('expression')
            if not isinstance(current_expression_record, dict):
                raise ValueError('저장 이력에 표정 프리셋 정보가 없거나 형식이 잘못되었습니다.')
            current_expression_identifier = current_expression_record.get('id')
            if not isinstance(current_expression_identifier, str) or current_expression_identifier not in {current_preset_record['id'] for current_preset_record in expression_preset_records}:
                raise ValueError('저장 이력의 표정 ID가 현재 프리셋에 없습니다. 이력 원문을 확인하세요.')
            restored_input_values[0] = current_expression_identifier
        if qwen21_mode_enabled and (not outfit_transfer_enabled):
            restored_input_values.extend(reference_upload_group.build_reference_updates(max(1, len(current_history_record['request'].get('references', [])))))
        if outfit_transfer_enabled:
            restored_input_values[0] = gr.update(value=restored_input_values[0], interactive=True)
            restored_input_values.extend([False, current_history_record['request']['prompt']])
        if circular_mode_enabled:
            restored_input_values[0] = current_history_record['request'].get('user_prompt', restored_input_values[0])
            restored_input_values.extend([current_history_record['request'].get('circular_vae', {}).get('boundary_radius', 12), current_history_record['request'].get('soft_shading', False), current_history_record['request'].get('pattern_view', False), current_history_record['request'].get('circular_vae', {}).get('baseline_decode', False)])
        if plain_options_enabled:
            current_prompt_metadata = current_history_record['request'].get('qwen21', {})
            restored_input_values[0] = current_history_record['request'].get('common_style_v1', {}).get('user_prompt', current_prompt_metadata.get('user_prompt', restored_input_values[0]))
            restored_input_values.extend([current_prompt_metadata.get('prompt_options', {}).get('common_style', False), current_prompt_metadata.get('prompt_options', {}).get('transparent_background', False)])
        if building_mode_enabled or billboard_guide_enabled:
            restored_input_values.append(False)
        if character_mode_enabled:
            current_sources = current_history_record['request'].get('body_reference_sources', [])
            current_known_records = import_module('generators.character-generator.body_references').load_body_reference_catalog()
            current_known_ids = {current_record['id']: current_record['sha256'] for current_record in current_known_records}
            current_restored_id = next((current_record['id'] for current_record in current_sources if current_record.get('order') == 1 and current_known_ids.get(current_record.get('id')) == current_record.get('source_sha256')), None)
            restored_input_values.append(current_restored_id)
        restored_input_values.append(False)
        return tuple(restored_input_values)
    with gr.Blocks(title=current_page_title) as interface_blocks_value:
        current_changelog_name = 'mannequin-generator' if mannequin_mode_enabled else 'character-generator' if character_mode_enabled else current_service_name
        if current_changelog_name in GENERATOR_CHANGELOG_PATHS:
            build_generator_changelog(interface_blocks_value, current_changelog_name)
        gr.Markdown('## ' + current_page_title + '\n**아카이브:** 신규 생성·재개·우선 실행은 중단되었습니다. 기존 이력과 결과는 확인할 수 있습니다.')
        gr.Markdown(QWEN_SEED_GUIDANCE)
        if current_service_name == 'prop-generator':
            gr.Markdown('공식 Qwen Image 2.1 비양자화 모델 · BF16 · AMD ROCm')
        current_prop_ready, current_prop_model_events = build_model_readiness_controls(interface_blocks_value, execute_reference_gateway)
        if billboard_guide_enabled:
            from tools.review.ui.gradio.billboard_guide_controls import build_billboard_guide_controls
            from tools.review.domains.image.billboard_guide_prompt import load_billboard_guide_image, compose_billboard_guide_prompt
            gr.Markdown('로컬 Qwen 2.1 고정 · 빌보드와 건물은 공용 대기열·이력을 사용합니다. 점유 가이드 또는 건물 구도를 첫 참조에 적용하세요. 건물은 짧은 용도·재질 문구와 건물 기본 프롬프트 옵션을 함께 사용할 수 있습니다. 가이드 적용 → 입력 확인 → 대기열 추가 → 결과 검수 순서로 진행하세요.')
            billboard_profile_control, billboard_subject_control, billboard_apply_button = build_billboard_guide_controls()
        if character_mode_enabled:
            gr.Markdown('공용 화풍 v1.5.0 영문 원문과 캐릭터 외관 v1.2.0의 축약 예시를 기본 입력에 포함합니다. 캐릭터 조건을 편집하세요. 일반 Qwen 2.1과 대기열·이력을 공유하므로 이력 삭제·초기화는 일반 Qwen 작업에도 적용됩니다. 결과는 검수용 후보입니다.')
        if mannequin_mode_enabled:
            gr.Markdown('마네킨 제작 단계를 선택해 프롬프트와 참조를 적용한 뒤 필요한 변경 조건을 입력하세요. 제작 단계에 맞춰 전신 2:3 또는 얼굴 1:1 출력 비율이 적용됩니다. 생성 모델은 신체 비율을 고정하지 않으므로 원본과 결과를 반드시 비교하세요. 공용 화풍 v1.5.0과 GPU 대기열을 사용하며 이력은 마네킨 전용입니다. 이전 공유 이력은 일반 Qwen 2.1에서 확인하세요. 결과는 후보이며 기준 원본을 자동으로 교체하지 않습니다.')
        if mannequin_mode_enabled:
            current_mannequin_module = import_module('generators.mannequin-generator.page.interface')
            with gr.Group():
                gr.Markdown('### 마네킨 제작 단계\n적용하면 프롬프트와 참조 이미지 1·2를 교체하고 출력 크기를 전신 768×1152, 얼굴 1056×1056으로 설정합니다. 참조 3 이후는 유지됩니다.')
                current_mannequin_selector = gr.Dropdown([(current_record[0], current_key) for current_key, current_record in current_mannequin_module.MANNEQUIN_PRESET_RECORDS.items()], value='jointed', label='제작 단계')
                current_mannequin_description, current_first_preview, current_second_preview = current_mannequin_module.preview_mannequin_preset('jointed')
                current_mannequin_description_control = gr.Markdown(current_mannequin_description)
                with gr.Row():
                    current_first_preview_control = gr.Image(value=current_first_preview, type='pil', interactive=False, label='기준 이미지 1 미리보기', height=REFERENCE_IMAGE_CARD_HEIGHT)
                    current_second_preview_control = gr.Image(value=current_second_preview, type='pil', interactive=False, label='기준 이미지 2 미리보기', height=REFERENCE_IMAGE_CARD_HEIGHT)
                current_example_prompt = gr.Textbox(value=current_mannequin_module.MANNEQUIN_PRESET_RECORDS['jointed'][3], label='제작 단계 프롬프트 예시', lines=3, interactive=False, info='선택한 단계의 예시입니다. 적용 후 아래 프롬프트에서 편집할 수 있습니다. 공용 화풍은 생성 시 추가됩니다.')

                def preview_mannequin_stage(current_stage_identifier):
                    return (*current_mannequin_module.preview_mannequin_preset(current_stage_identifier), current_mannequin_module.MANNEQUIN_PRESET_RECORDS[current_stage_identifier][3])

                current_mannequin_selector.change(preview_mannequin_stage, [current_mannequin_selector], [current_mannequin_description_control, current_first_preview_control, current_second_preview_control, current_example_prompt], queue=False)
                current_mannequin_apply = gr.Button('선택한 제작 단계 적용')
        if vegetation_mode_enabled:
            gr.Markdown('나무·관목·풀·꽃·갈대 등 자연물 빌보드를 생성합니다. 기본 문구 뒤에 식물 종류·계절·색상·군락 밀도를 추가하세요. 레이아웃은 투영·바닥 영역, 식물 참조는 잎·줄기 형태 기준입니다. 참조는 선택 사항이며 결과는 검수 후 slime-assets/assets/billboards/에 자연물으로 등록합니다.')
        if prop_mode_enabled and (not billboard_guide_enabled):
            gr.Markdown('상자·가판대·작업대·표지판 등 소품 스프라이트를 생성합니다. 기본 문구 뒤에 대상·용도·자재를 추가하세요. 레이아웃은 투영·바닥 영역, 외형 참조는 형태·자재 기준입니다. 참조는 선택 사항이며 결과는 검수 후 slime-assets/assets/billboards/에 등록합니다. 기본 문구의 투명 배경 표현과 별개로, 네이티브 RGBA 출력 검증은 아래 투명 배경 옵션을 선택할 때 적용됩니다.')
        if building_mode_enabled:
            gr.Markdown('레이아웃 이미지 → 건물 후보 생성. 첫 참조는 실제 맵의 타일 축·건물 바닥 영역·출입구를 표시한 이미지입니다. 건물 용도·자재를 입력하고 건물 기본 프롬프트 추가를 선택하세요. 옵션을 합친 최종 문구는 99단어 이내여야 합니다. 생성 결과는 검수 후 slime-assets/assets/buildings/에 등록합니다.')
        if circular_mode_enabled:
            gr.Markdown('생성 토큰 순환 Attention · 일반 VAE 비교 선택 · 참조 이미지 선택 · 생성 영역만 순환 처리 · 출력 전체가 타일입니다. 반복 경계의 형태 연결은 결과에서 검수하세요.')
        if expression_mode_enabled:
            gr.Markdown('Qwen Image 2.1 · Anime consistency LoRA 0.7 고정 · 참조 1~3장. 첫 이미지를 편집하고 추가 이미지는 동일 캐릭터의 외형 참고로 사용합니다. AU는 움직임 설계 참고이며 검출값·감정 판정·강도 측정이 아닙니다.')
        if outfit_transfer_enabled:
            fixed_prompt_enabled = gr.Checkbox(value=True, label='고정 프롬프트 사용', info='ON: 기본 문구를 사용합니다. OFF: 프롬프트를 직접 편집합니다. 전환만으로 생성하지 않습니다.')
            custom_prompt_memory = gr.State(default_prompt_text)
        with gr.Row(equal_height=True):
            if expression_mode_enabled:
                from tools.review.domains.image.expression_generation import load_expression_configuration, build_expression_prompt
                expression_preset_records = load_expression_configuration()['expressions']
                prompt_text_value = gr.Dropdown([(record['label_ko'], record['id']) for record in expression_preset_records], value=expression_preset_records[0]['id'], label='표정 · AU 프리셋', scale=1, min_width=240)
            else:
                from generators.image.qwen_21_circular import CIRCULAR_DEFAULT_PROMPT
                prompt_text_value = gr.Textbox(value=CIRCULAR_DEFAULT_PROMPT if circular_mode_enabled else default_prompt_text, interactive=not outfit_transfer_enabled, label='프롬프트', lines=3, scale=1, min_width=240)
            generation_tag_value = gr.Textbox(label='생성 이력 태그 · 선택 사항', placeholder='예: 돌온재 참조 후보', lines=3, scale=1, min_width=240)
        if plain_options_enabled and not (prop_mode_enabled and not billboard_guide_enabled):
            gr.ClearButton(components=[prompt_text_value], value='프롬프트 초기화', variant='secondary')
        if qwen21_mode_enabled:
            gr.Markdown('Qwen Image 2.1 고정 · 첫 참조 레이아웃 필수 · 건물 용도와 자재를 문구에 추가하세요.' if building_mode_enabled else '바디 1장: 신체 비율·자세·외형 기준. 아웃핏 1장: 입힐 의상·신발 기준. 바디를 유지하고 복장을 입힙니다.' if outfit_transfer_enabled else 'Qwen Image 2.1 · 참조 최대 10장. 선택한 프롬프트 옵션을 입력 문구에 추가합니다.' if circular_mode_enabled else 'Qwen Image 2.1 · 기본 입력에 화풍 원문이 포함됩니다. 참조 없이 텍스트만으로도 생성할 수 있습니다.' if character_mode_enabled else 'Qwen Image 2.1 · 공용 화풍 v1.5.0을 기본 적용합니다. 참조 없이 텍스트만으로도 생성할 수 있습니다.')

            def describe_plain_prompt(current_prompt_text):
                current_word_count = len(current_prompt_text.split())
                return f'사용자 {current_word_count}단어 · 추가 0단어 · 최종 {current_word_count}단어 (최대 99단어)'
            prompt_count_control = gr.Markdown(describe_plain_prompt(CIRCULAR_DEFAULT_PROMPT if circular_mode_enabled else default_prompt_text))
            if not circular_mode_enabled and (not plain_options_enabled):
                prompt_text_value.change(describe_plain_prompt, prompt_text_value, prompt_count_control, queue=False)
        if plain_options_enabled:
            from generators.image.qwen_21_prompt_options import compose_qwen_option_prompt, load_qwen_prompt_options
            current_option_prompts = load_qwen_prompt_options()
            building_prompt_control = gr.Checkbox(value=building_mode_enabled, label='건물 기본 프롬프트 추가', info=str(len(load_building_base_prompt().split())) + '단어 · ' + load_building_base_prompt(), visible=building_mode_enabled or billboard_guide_enabled)
            common_style_control = gr.Checkbox(value=False, visible=False)
            current_transparency_prompt = current_option_prompts['transparent_background'] + ' … ' + current_option_prompts['transparent_background_suffix']
            current_transparency_count = len(current_option_prompts['transparent_background'].split()) + len(current_option_prompts['transparent_background_suffix'].split())
            gr.Markdown('공용 화풍 v1.5.0 원문을 기본 적용합니다. 투명 배경을 선택하면 시작·마무리 문구가 추가됩니다.')
            transparent_background_control = gr.Checkbox(value=False, label='투명 배경 요청 · 네이티브 RGBA', info=str(current_transparency_count) + '단어 · ' + current_transparency_prompt)
            with gr.Accordion('최종 모델 입력', open=False):
                plain_final_preview = gr.Textbox(value=default_prompt_text, label='옵션 포함 최종 프롬프트', interactive=False)

            def describe_plain_options(current_prompt_text, common_style_enabled, transparent_background_enabled, building_prompt_enabled=False):
                current_user_word_count = len(current_prompt_text.split())
                if building_prompt_enabled:
                    current_prompt_text = (current_prompt_text.strip() + ' ' + load_building_base_prompt()).strip()
                from generators.image.common_art_style import compose_common_style_prompt
                current_styled_prompt, current_style_record = compose_common_style_prompt(current_prompt_text)
                current_final_prompt, current_added_prompt = compose_qwen_option_prompt(current_styled_prompt, False, transparent_background_enabled)
                return (f'사용자 {current_user_word_count}단어 · 추가 {len(current_final_prompt.split()) - current_user_word_count}단어 · 최종 {len(current_final_prompt.split())}단어 (최대 99단어)', current_final_prompt)
            for current_option_control in (prompt_text_value, common_style_control, transparent_background_control, building_prompt_control):
                current_option_control.change(describe_plain_options, [prompt_text_value, common_style_control, transparent_background_control, building_prompt_control], [prompt_count_control, plain_final_preview], queue=False)
            prompt_count_control.value, plain_final_preview.value = describe_plain_options(default_prompt_text, False, False, building_mode_enabled)
        if circular_mode_enabled:
            from generators.image.qwen_21_circular import CIRCULAR_SOFT_SHADING_PROMPT, CIRCULAR_PATTERN_VIEW_PROMPT
            pattern_view_control = gr.Checkbox(value=True, label='탑뷰·반복 패턴·클로즈업 추가', info=str(len(CIRCULAR_PATTERN_VIEW_PROMPT.split())) + '단어 · ' + CIRCULAR_PATTERN_VIEW_PROMPT)
            soft_shading_control = gr.Checkbox(value=True, label='부드러운 음영 일러스트 추가', info=str(len(CIRCULAR_SOFT_SHADING_PROMPT.split())) + '단어 · ' + CIRCULAR_SOFT_SHADING_PROMPT)

            def describe_circular_prompt(current_prompt_text, soft_shading_enabled, pattern_view_enabled):
                user_word_count = len(current_prompt_text.split())
                from generators.image.common_art_style import compose_common_style_prompt
                current_styled_prompt, current_style_record = compose_common_style_prompt(' '.join((current_prompt_text, CIRCULAR_PATTERN_VIEW_PROMPT if pattern_view_enabled else '', CIRCULAR_SOFT_SHADING_PROMPT if soft_shading_enabled else '')))
                current_total_count = len(current_styled_prompt.split())
                return f'사용자 {user_word_count}단어 · 추가 {current_total_count - user_word_count}단어 · 최종 {current_total_count}단어 (최대 99단어)'
            def describe_circular_final_prompt(current_prompt_text, soft_shading_enabled, pattern_view_enabled):
                from generators.image.common_art_style import compose_common_style_prompt
                current_combined_prompt = ' '.join((current_prompt_text, CIRCULAR_PATTERN_VIEW_PROMPT if pattern_view_enabled else '', CIRCULAR_SOFT_SHADING_PROMPT if soft_shading_enabled else ''))
                return compose_common_style_prompt(current_combined_prompt)[0]
            gr.Markdown('공용 화풍 v1.5.0 원문: 41단어 · 기본 적용')
            with gr.Accordion('최종 모델 입력', open=False):
                circular_final_preview = gr.Textbox(value=describe_circular_final_prompt(CIRCULAR_DEFAULT_PROMPT, True, True), label='최종 프롬프트', interactive=False)
            prompt_count_control.value = describe_circular_prompt(CIRCULAR_DEFAULT_PROMPT, True, True)
            for current_prompt_control in (prompt_text_value, soft_shading_control, pattern_view_control):
                current_prompt_control.change(describe_circular_prompt, [prompt_text_value, soft_shading_control, pattern_view_control], prompt_count_control, queue=False)
                current_prompt_control.change(describe_circular_final_prompt, [prompt_text_value, soft_shading_control, pattern_view_control], circular_final_preview, queue=False)
        if outfit_transfer_enabled:

            def toggle_fixed_prompt(selected_fixed_enabled, current_prompt_text, saved_custom_prompt):
                if selected_fixed_enabled:
                    return (gr.update(value=load_outfit_transfer_prompt(), interactive=False), current_prompt_text)
                return (gr.update(value=saved_custom_prompt, interactive=True), saved_custom_prompt)
            fixed_prompt_enabled.input(toggle_fixed_prompt, [fixed_prompt_enabled, prompt_text_value, custom_prompt_memory], [prompt_text_value, custom_prompt_memory], queue=False)

            def remember_custom_prompt(current_prompt_text):
                return current_prompt_text
            prompt_text_value.input(remember_custom_prompt, prompt_text_value, custom_prompt_memory, queue=False)
        elif vegetation_mode_enabled:
            gr.Button('자연물 기본 프롬프트 복원', size='sm').click(load_vegetation_base_prompt, outputs=prompt_text_value, queue=False)
        elif billboard_guide_enabled:
            gr.Markdown('가이드·대상을 바꾼 뒤 적용 버튼을 다시 누르면 문구와 첫 참조가 함께 갱신됩니다.')
        elif prop_mode_enabled:
            gr.Button('소품 기본 프롬프트 복원', size='sm').click(load_prop_base_prompt, outputs=prompt_text_value, queue=False)
        elif building_mode_enabled:
            gr.Markdown('건물 용도·자재를 입력하고 건물 기본 프롬프트 추가 옵션을 선택하세요.')
        elif not expression_mode_enabled:
            prompt_reset_button = gr.ClearButton([prompt_text_value], value='프롬프트 초기화', variant='secondary', size='sm')
        if expression_mode_enabled:

            def describe_expression_prompt(expression_identifier_value):
                final_prompt_value, expression_source_record = build_expression_prompt(expression_identifier_value)
                from generators.image.common_art_style import compose_common_style_prompt
                final_prompt_value, current_style_record = compose_common_style_prompt(final_prompt_value)
                base_prompt_value = load_expression_configuration()['base_prompt']
                return '공용 화풍 v1.5.0: 41단어 · 기본 적용\n\nAU 참고: ' + ', '.join(('AU' + str(value) for value in expression_source_record['au_hints'])) + '\n\n움직임 (' + str(len(expression_source_record['movement_prompt'].split())) + '단어): ' + expression_source_record['movement_prompt'] + '\n\n외형 유지 (' + str(len(base_prompt_value.split())) + '단어): ' + base_prompt_value + '\n\n최종 입력 (' + str(len(final_prompt_value.split())) + '단어): ' + final_prompt_value
            expression_prompt_preview = gr.Markdown(describe_expression_prompt(expression_preset_records[0]['id']))
            prompt_text_value.change(describe_expression_prompt, prompt_text_value, expression_prompt_preview, queue=False)
        if building_mode_enabled:
            from tools.review.domains.image.building_prompt import BUILDING_LAYOUT_PRESET_NAMES, describe_building_structure_label, load_building_layout_preset
            with gr.Group():
                gr.Markdown('### 구도 참조 프리셋\n도시맵 80×40 타일의 직교투영 가이드입니다. 지붕·층수·문 방향이 고정된 50종입니다. 층당 80px, 문 높이 64px이며 가이드는 2배 배율로 표시합니다. 선택 후 적용하면 첫 참조를 교체합니다. 실제 맵 구도 그림을 직접 업로드할 수도 있습니다.')
                with gr.Row():
                    with gr.Column():
                        building_layout_selector = gr.Dropdown([(describe_building_structure_label(current_preset_name), current_preset_name) for current_preset_name in BUILDING_LAYOUT_PRESET_NAMES], value=BUILDING_LAYOUT_PRESET_NAMES[0], label='건물 구도 프리셋')
                        gr.Markdown('한 층은 80px이며 지붕은 벽 상단 위에 고정됩니다. 층수는 선택한 구조에 따릅니다. 맵 배치 크기는 바뀌지 않습니다.')
                        building_layout_apply_button = gr.Button('선택한 구도를 레이아웃 참조에 적용')
                    building_layout_preview = gr.Image(value=load_building_layout_preset(BUILDING_LAYOUT_PRESET_NAMES[0]), type='pil', interactive=False, label='구도 그림 미리보기', height=REFERENCE_IMAGE_CARD_HEIGHT)
                building_layout_selector.change(load_building_layout_preset, [building_layout_selector], building_layout_preview, queue=False)
        if character_mode_enabled:
            from importlib import import_module
            current_body_module = import_module('generators.character-generator.body_references')
            character_body_state = gr.State(None)
            current_body_gallery = import_module('generators.character-generator.page.body_reference_gallery')
            character_body_selector, character_body_apply = current_body_gallery.build_body_reference_gallery()
        with gr.Accordion('자연물 레이아웃·외형 참조 · 선택' if vegetation_mode_enabled else '소품 레이아웃·외형 참조 · 선택' if prop_mode_enabled else '레이아웃 이미지 · 필수 / 추가 외형 참조 · 선택' if building_mode_enabled else '참조 이미지 · 선택 · 최대 10장', open=building_mode_enabled or prop_mode_enabled or vegetation_mode_enabled or mannequin_mode_enabled) if qwen21_mode_enabled and (not outfit_transfer_enabled) else contextlib.nullcontext():
            reference_upload_group, reference_image_controls = build_reference_image_inputs(reference_image_mode=None, reference_image_format='png' if character_mode_enabled or mannequin_mode_enabled else 'webp', reference_slot_count=reference_slot_count, reference_slot_labels=[f'자연물 레이아웃·외형 참조 {current_slot_number} · 선택' for current_slot_number in range(1, 11)] if vegetation_mode_enabled else [f'소품 레이아웃·외형 참조 {current_slot_number} · 선택' for current_slot_number in range(1, 11)] if prop_mode_enabled else ['레이아웃 이미지 · 필수 (투영·바닥·출입구)'] + [f'외형·자재 참조 {current_slot_number} · 선택' for current_slot_number in range(2, 11)] if building_mode_enabled else ['바디 레퍼런스 · 필수', '아웃핏 레퍼런스 · 필수'] if outfit_transfer_enabled else None)
        if character_mode_enabled:
            def apply_character_body(current_reference_id, current_prompt_text, current_alpha_enabled):
                if not current_reference_id:
                    raise gr.Error('신체 비율 참조를 먼저 선택하세요.')
                current_role_text = current_body_module.BODY_REFERENCE_ROLE_PROMPT
                current_updated_prompt = current_prompt_text if current_role_text in current_prompt_text else (current_prompt_text.strip() + ' ' + current_role_text).strip()
                if not check_plain_prompt_readiness(current_updated_prompt, False, current_alpha_enabled):
                    raise gr.Error('신체 기준 설명과 공용 화풍을 포함해 99단어 이내로 프롬프트를 줄이세요.')
                return current_body_module.load_body_reference_image(current_reference_id), current_updated_prompt, current_reference_id

            character_body_apply.click(apply_character_body, [character_body_selector, prompt_text_value, transparent_background_control], [reference_image_controls[0], prompt_text_value, character_body_state], queue=False)
            reference_image_controls[0].input(lambda: None, outputs=character_body_state, queue=False)
            reference_upload_group.reference_delete_buttons[0].click(lambda: None, outputs=character_body_state, queue=False)
        if billboard_guide_enabled:

            def apply_billboard_guide_inputs(selected_profile_name, selected_subject_text):
                from tools.review.ui.gradio.billboard_guide_controls import BUILDING_PROFILE_PREFIX, compose_building_guide_subject, parse_building_guide_profile, validate_guide_subject_input
                validate_guide_subject_input(selected_profile_name, selected_subject_text)
                if selected_profile_name.startswith(BUILDING_PROFILE_PREFIX):
                    from tools.review.domains.image.building_prompt import load_building_layout_preset
                    current_building_name, current_height_value = parse_building_guide_profile(selected_profile_name)
                    return (load_building_layout_preset(current_building_name, current_height_value), compose_building_guide_subject(selected_profile_name, selected_subject_text), True)
                return (load_billboard_guide_image(selected_profile_name), compose_billboard_guide_prompt(selected_profile_name, selected_subject_text), False)
            billboard_apply_button.click(apply_billboard_guide_inputs, [billboard_profile_control, billboard_subject_control], [reference_image_controls[0], prompt_text_value, building_prompt_control], queue=False)
        if building_mode_enabled:
            building_layout_apply_button.click(load_building_layout_preset, [building_layout_selector], reference_image_controls[0], queue=False)
        gr.Markdown(('생성 출력: 512×512 또는 768×768.' if outfit_transfer_enabled else '생성 출력 최소 크기: 256×256.' if qwen21_mode_enabled else '생성 출력 최소 크기: 512×512.') + ' 참조 이미지의 크기·비율은 자유입니다. RGB/RGBA PNG, 장당 3MB 이하. ' + ('투명 영역은 흰색 배경에 합성해 전달합니다.' if qwen21_mode_enabled else '투명 배경은 사용할 수 없습니다.'))
        with gr.Row():
            width_value = gr.Dropdown([512, 768] if outfit_transfer_enabled else [256, 384, 512, 768, 1024, 1056, 1152, 1280] if mannequin_mode_enabled else [256, 384, 512, 768, 1024, 1280] if qwen21_mode_enabled else [512, 768, 1024, 1280], value=512 if vegetation_mode_enabled or prop_mode_enabled or building_mode_enabled or circular_mode_enabled else 768 if qwen21_mode_enabled else 512, label='해상도' if outfit_transfer_enabled else '너비', interactive=True, scale=1, min_width=120)
            height_value = gr.Dropdown([512, 768] if outfit_transfer_enabled else [256, 384, 512, 768, 1024, 1056, 1152, 1280] if mannequin_mode_enabled else [256, 384, 512, 768, 1024, 1280] if qwen21_mode_enabled else [512, 768, 1024, 1280], value=512 if vegetation_mode_enabled or prop_mode_enabled or building_mode_enabled or circular_mode_enabled else 768 if qwen21_mode_enabled else 512, label='높이', visible=not outfit_transfer_enabled, scale=1, min_width=120)
            step_value = gr.Dropdown([20, 30, 40, 50], value=40, label='생성 스텝', interactive=True, scale=1, min_width=120) if qwen21_mode_enabled or expression_mode_enabled else gr.Radio([4, 30], value=4, label='생성 스텝', scale=1, min_width=120)
            if circular_mode_enabled:
                circular_radius_control = gr.Dropdown([4, 8, 12, 16, 24], value=12, label='순환 반경 · 토큰', scale=1, min_width=120)
            else:
                seed_value = build_generation_seed(10107, random_initial_enabled=True)
        if mannequin_mode_enabled:
            def apply_mannequin_stage(current_stage_identifier):
                return (*current_mannequin_module.load_mannequin_preset(current_stage_identifier), *((1056, 1056) if current_stage_identifier == 'face' else (768, 1152)))
            current_mannequin_apply.click(apply_mannequin_stage, [current_mannequin_selector], [prompt_text_value, reference_image_controls[0], reference_image_controls[1], width_value, height_value], queue=False)
        if circular_mode_enabled:
            with gr.Row(equal_height=False):
                seed_value = build_generation_seed(10107, random_initial_enabled=True)
                with gr.Column(min_width=220):
                    baseline_decode_control = gr.Checkbox(value=False, label='일반 VAE 비교 생성', info='동일 잠재값의 일반 VAE 결과를 추가합니다.')
            gr.Markdown('순환 반경은 좌우·상하에 동일 적용합니다. 경계 1줄 참조 · 모서리 참조 없음.')
        automatic_seed_control = gr.Checkbox(value=True, label='생성마다 무작위 시드', info='끄면 표시된 시드를 사용합니다. 이력을 불러오면 자동으로 꺼집니다.')
        if outfit_transfer_enabled:
            width_value.change(lambda selected_resolution_value: selected_resolution_value, width_value, height_value, queue=False)
        generation_button_value = gr.Button('생성 불가 · 아카이브', interactive=False)
        build_button_guidance(generation_button_value, 'Qwen 이미지 생성기는 아카이브되어 신규 생성을 지원하지 않습니다. 기존 이력에서 결과를 확인하세요.')
        with gr.Column() as generation_confirmation_container:
            pass
        status_value = gr.Markdown('참조 이미지와 설정을 확인하세요.' if outfit_transfer_enabled else '프롬프트와 옵션을 확인하세요.' if plain_options_enabled or circular_mode_enabled else '참조 이미지를 1장 이상 첨부하세요.' if expression_mode_enabled else '생성 가능 · 설정을 확인하세요.')
        gr.Markdown('실행 중인 작업은 아래 생성 이력에서 선택한 뒤 **작업 중지**를 사용하세요.')
        identifier_value = gr.State('')
        gr.Markdown('마네킨 전용 생성 이력입니다. 이전 공유 이력은 일반 Qwen 2.1에서 확인하세요.' if mannequin_mode_enabled else '일반 Qwen 2.1과 공유하는 생성 이력입니다. 삭제·초기화는 공유 이력 전체에 적용됩니다.' if character_mode_enabled else '빌보드·건물 공용 생성 이력입니다. 기존 건물 CLI도 이 이력을 사용합니다.' if billboard_guide_enabled else '건물 전용 대기열·생성 이력입니다. 기존 공유 Qwen 이력은 일반 Qwen 생성기에서 조회하세요.' if building_mode_enabled else '소품 전용 대기열·생성 이력입니다. 기존 공유 이력은 일반 Qwen에서 조회하세요.' if prop_mode_enabled else '자연물 전용 대기열·생성 이력입니다. 기존 공유 이력은 일반 Qwen에서 조회하세요.' if vegetation_mode_enabled else '복장 착용 전용 생성 이력입니다.' if outfit_transfer_enabled else 'Qwen 2.1 전용 생성 이력입니다. 조회·삭제·초기화는 현재 생성기에만 적용됩니다.' if qwen21_mode_enabled else '표정 생성 이력은 별도로 관리합니다. 이전 Qwen 2511 작업은 조회할 수 있지만 재개할 수 없습니다.' if expression_mode_enabled else 'Qwen 2511 참조 생성 이력은 표정 생성 이력과 별도로 관리합니다. 조회·삭제·초기화는 현재 생성기에만 적용됩니다.')
        read_history_page, history_output_values = build_generation_history_view(execute_reference_gateway, server_base_address, '이력과 해당 생성기의 임시 작업 폴더(결과·참조 입력 사본·로그)를 함께 삭제합니다. 이전에 목록에서 제거한 작업도 포함합니다. 정식 에셋과 모델 캐시는 유지합니다. 대기·실행 중에는 초기화할 수 없습니다.', result_renderer_callback=render_circular_comparison if circular_mode_enabled else None, restore_input_callback=restore_selected_inputs, restore_output_components=[prompt_text_value, generation_tag_value, width_value, height_value, step_value, seed_value, *reference_image_controls, status_value] + (reference_upload_group.reference_slot_outputs if qwen21_mode_enabled and (not outfit_transfer_enabled) else []) + ([fixed_prompt_enabled, custom_prompt_memory] if outfit_transfer_enabled else []) + ([circular_radius_control, soft_shading_control, pattern_view_control, baseline_decode_control] if circular_mode_enabled else []) + ([common_style_control, transparent_background_control] if plain_options_enabled else []) + ([building_prompt_control] if building_mode_enabled or billboard_guide_enabled else []) + ([character_body_state] if character_mode_enabled else []) + [automatic_seed_control], record_folder_route='/mannequin-generator' if mannequin_mode_enabled else '/billboard-generator' if billboard_guide_enabled else '/prop-generator' if prop_mode_enabled else '/vegetation-generator' if vegetation_mode_enabled else '/building-generator' if building_mode_enabled else '/outfit-transfer' if outfit_transfer_enabled else '/image-generation-21-circular' if circular_mode_enabled else '/image-generation-21' if qwen21_mode_enabled else '/expression-generator' if expression_mode_enabled else '/image-generation-2511', allow_individual_delete=True, archive_mode_enabled=True)

        def start_reference_generation(prompt_text_value, generation_tag_value, *generation_input_values):
            automatic_seed_enabled = generation_input_values[-1]
            generation_input_values = generation_input_values[:-1]
            current_body_reference_id = generation_input_values[-1] if character_mode_enabled else None
            if character_mode_enabled:
                generation_input_values = generation_input_values[:-1]
            if building_mode_enabled or billboard_guide_enabled:
                building_prompt_enabled = generation_input_values[-1]
                generation_input_values = generation_input_values[:-1]
                if building_prompt_enabled:
                    prompt_text_value = (prompt_text_value.strip() + ' ' + load_building_base_prompt()).strip()
            if billboard_guide_enabled and generation_input_values[0] is None:
                raise gr.Error('가이드와 문구를 생성 입력에 먼저 적용하세요.')
            if building_mode_enabled and generation_input_values[0] is None:
                raise gr.Error('첫 참조 슬롯에 건물 레이아웃 이미지를 선택하세요.')
            if outfit_transfer_enabled and any((current_reference_image is None for current_reference_image in generation_input_values[:2])):
                raise gr.Error('바디와 아웃핏 이미지를 각각 한 장 첨부하세요.')
            reference_bytes_values = prepare_reference_image_bytes(generation_input_values[:reference_slot_count], composite_transparent_background=qwen21_mode_enabled)
            width_value, height_value, step_value, seed_value = generation_input_values[reference_slot_count:reference_slot_count + 4]
            seed_value = select_generation_seed_value(seed_value, automatic_seed_enabled)
            if outfit_transfer_enabled:
                height_value = width_value
            from tools.review.domains.image.three_reference_generation import validate_three_reference_request
            try:
                generation_request_value = build_reference_request(prompt_text_value, generation_tag_value, reference_bytes_values, width_value, height_value, step_value, seed_value)
                if circular_mode_enabled:
                    from tools.review.domains.image.qwen_circular_generation import QwenCircularGenerationManager
                    generation_request_value.update(circular_radius=generation_input_values[-4], soft_shading=generation_input_values[-3], pattern_view=generation_input_values[-2], baseline_decode=generation_input_values[-1])
                    QwenCircularGenerationManager().validate_generation_request(generation_request_value)
                elif qwen21_mode_enabled:
                    from tools.review.domains.image.qwen_21_generation import validate_styled_qwen_request
                    generation_request_value['prompt'] = prompt_text_value
                    if current_body_reference_id is not None:
                        generation_request_value['body_reference_id'] = current_body_reference_id
                    if plain_options_enabled:
                        generation_request_value['common_style'] = generation_input_values[-2]
                        generation_request_value['transparent_background'] = generation_input_values[-1]
                    validate_styled_qwen_request(generation_request_value)
                elif expression_mode_enabled:
                    from tools.review.domains.image.expression_generation import ExpressionGenerationManager
                    ExpressionGenerationManager().validate_generation_request(generation_request_value)
                else:
                    validate_three_reference_request(generation_request_value)
                generation_record_value = execute_reference_gateway('generate', generation_request_value)
            except (ValueError, OSError) as generation_request_error:
                raise gr.Error(str(generation_request_error)) from generation_request_error
            return (generation_record_value['id'], '상태: ' + format_generation_status(generation_record_value) + f' · 사용 시드: {seed_value}', seed_value)
        def check_prop_generation_readiness(current_model_ready, *current_prompt_options):
            return current_model_ready and check_plain_prompt_readiness(*current_prompt_options)


        interface_blocks_value.load(lambda: read_history_page(1), outputs=history_output_values)
        identifier_value.change(lambda: read_history_page(1), outputs=history_output_values, queue=False)
    return interface_blocks_value
if __name__ == '__main__':
    parser_value = argparse.ArgumentParser()
    parser_value.add_argument('--port', type=int, required=True)
    parser_value.add_argument('--review-port', type=int, required=True)
    parser_value.add_argument('--owner-pid', type=int, required=True)
    parser_value.add_argument('--root-path', default='/management/frame/three-reference-generator/')
    arguments_value = parser_value.parse_args()
    threading.Thread(target=lambda: (time.sleep(1), os._exit(0)) if os.getppid() != arguments_value.owner_pid else None, daemon=True).start()
    build_qwen_2511_interface(f'http://127.0.0.1:{arguments_value.review_port}').queue().launch(server_name='127.0.0.1', server_port=arguments_value.port, root_path=arguments_value.root_path, allowed_paths=[])
