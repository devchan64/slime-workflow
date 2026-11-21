"""FLUX 표정 생성기 페이지."""
import base64
import io
from pathlib import Path
import gradio as gr
from PIL import Image
from tools.management.common.gradio_generator_changelog import build_generator_changelog
from tools.management.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.management.common.gradio_history import build_generation_history_view
from tools.management.common.reference_restore import HistoryInputError
from tools.management.common.gradio_seed import build_generation_seed
from tools.management.common.management_client import execute_remote_management_command
from tools.management.domains.image.expression_generation import load_expression_configuration
from tools.management.domains.image.flux_expression_generation import build_flux_expression_prompt, restore_flux_expression_inputs as restore_saved_expression

DEFAULT_FACE_IMAGE_PATH = Path(__file__).resolve().parents[3] / 'baseline/player/default/default-face-front-v1.png'


def load_default_face_reference():
    with Image.open(DEFAULT_FACE_IMAGE_PATH) as current_image_file:
        return current_image_file.convert('RGB').copy()


def execute_flux_expression_command(current_command_name, current_payload_record):
    return execute_remote_management_command('flux-expression', current_command_name, current_payload_record)


def describe_flux_expression_prompt(current_expression_identifier):
    current_prompt_text = build_flux_expression_prompt(current_expression_identifier)
    return f'{len(current_prompt_text.split())}단어 · {current_prompt_text}'


def restore_flux_expression_inputs(current_history_record, reference_storage_root=None):
    try:
        return restore_saved_expression(current_history_record, reference_storage_root)
    except HistoryInputError as error:
        raise gr.Error(str(error)) from error


def build_generator_page(current_server_address, current_review_port):
    current_preset_records = load_expression_configuration()['expressions']
    current_choices_list = [(item['label_ko'],item['id']) for item in current_preset_records]
    with gr.Blocks() as current_page_blocks:
        gr.Markdown('## FLUX 3 표정 생성기\n기본 얼굴 참조 1장과 표정을 선택하세요. 결과의 얼굴 특징과 피부·머리색을 원본과 비교해야 합니다.')
        build_generator_changelog(current_page_blocks, 'flux-expression-generator')
        current_reference_image = gr.Image(label='얼굴 참조 이미지', type='pil', image_mode='RGB')
        gr.Button('기본 캐릭터 정면 얼굴 불러오기').click(load_default_face_reference, outputs=current_reference_image, queue=False)
        current_expression_control = gr.Dropdown(choices=current_choices_list,value=current_choices_list[0][1],label='표정')
        current_korean_control = gr.Textbox(label='한국어 추가 지시 (선택)',lines=2,placeholder='예: 눈썹을 조금 올리고 부드럽게 웃는 표정')
        gr.Markdown('한국어 추가 지시는 번역 대기열에서 영어로 번역한 뒤 선택한 표정 프리셋에 결합해 자동 생성합니다. 번역과 검토 항목은 이력에서 확인하세요.')
        current_prompt_display = gr.Markdown(describe_flux_expression_prompt(current_choices_list[0][1]))
        current_expression_control.change(describe_flux_expression_prompt,current_expression_control,current_prompt_display,queue=False)
        with gr.Row():
            current_width_control = gr.Number(value=768,minimum=256,maximum=1664,precision=0,label='너비')
            current_height_control = gr.Number(value=512,minimum=256,maximum=1664,precision=0,label='높이')
        gr.Markdown('생성 단계: 16 · 프롬프트 확장기, 마스크와 VAE 타일링 사용 안 함 · 예상 시간은 작업 이력이 쌓일 때까지 계산 중')
        current_seed_control = build_generation_seed()
        current_tag_control = gr.Textbox(label='이력 태그 (선택)')
        current_start_button = gr.Button('대기열에 추가',interactive=False,variant='primary')
        gr.Markdown('얼굴 참조 이미지를 선택하면 생성할 수 있습니다.')
        with gr.Column() as current_confirmation_container:
            pass
        current_job_control = gr.Textbox(visible=False)
        current_status_control = gr.Markdown('결과와 작업 상태는 아래 생성 이력에서 확인하세요.')
        def start_flux_expression(current_image_value,current_expression_value,current_width_value,current_height_value,current_seed_value,current_tag_value,current_korean_value):
            if current_image_value is None:
                raise gr.Error('얼굴 참조 이미지를 선택하세요.')
            current_image_buffer = io.BytesIO()
            current_image_value.convert('RGB').save(current_image_buffer,format='PNG')
            current_payload_record = {'action':'generate','prompt':current_expression_value,'images':[base64.b64encode(current_image_buffer.getvalue()).decode()],'width':int(current_width_value),'height':int(current_height_value),'steps':16,'seed':int(current_seed_value),'tag':current_tag_value or ''}
            if current_korean_value and current_korean_value.strip(): current_payload_record['translation_source_ko']=current_korean_value.strip()
            current_result_record = execute_flux_expression_command('generate',current_payload_record)
            return current_result_record['id'],'대기열에 등록했습니다. 생성 이력을 새로고침해 확인하세요.'
        bind_gpu_generation_confirmation(current_start_button,start_flux_expression,[current_reference_image,current_expression_control,current_width_control,current_height_control,current_seed_control,current_tag_control,current_korean_control],[current_job_control,current_status_control],generation_confirmation_container=current_confirmation_container,generation_readiness_callback=lambda current_image_value: current_image_value is not None,generation_readiness_inputs=[current_reference_image])
        build_generation_history_view(execute_flux_expression_command,current_server_address,'FLUX 표정 생성 이력과 결과를 삭제합니다.',restore_input_callback=restore_flux_expression_inputs,restore_output_components=[current_reference_image,current_expression_control,current_width_control,current_height_control,current_seed_control,current_tag_control,current_korean_control],record_folder_route='/flux-expression-generator',allow_individual_delete=True,observed_job_control=current_job_control,history_deep_link_interface=current_page_blocks)
    return current_page_blocks
