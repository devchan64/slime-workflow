"""Kimodo NF4 실험 폼. 실행과 기록 수명은 공용 게이트웨이가 담당한다."""
import gradio as gr
from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS,normalize_kimodo_prompt,validate_kimodo_request
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_video_results import build_video_job_monitor,render_video_generation_result
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT


def execute_kimodo_command(current_command_name,current_payload_record):
    return execute_remote_management_command('kimodo',current_command_name,current_payload_record)


def build_kimodo_payload(current_prompt_text,current_frame_count,current_step_count,current_seed_value,current_guidance_value,current_heading_value,current_postprocessing_value):
    for current_integer_value in (current_frame_count,current_step_count,current_seed_value):
        if type(current_integer_value) not in (int,float) or not float(current_integer_value).is_integer():
            raise ValueError('프레임·스텝·시드는 정수로 입력하세요.')
    current_request_record = {'action':'generate','prompt':current_prompt_text,'frames':int(current_frame_count),'steps':int(current_step_count),'seed':int(current_seed_value),'guidance_scale':current_guidance_value,'heading_degrees':current_heading_value,'post_processing':current_postprocessing_value}
    validate_kimodo_request(current_request_record)
    return current_request_record


def describe_kimodo_prompt(current_prompt_text):
    if not current_prompt_text or not current_prompt_text.strip():
        return '원문 0단어 · 최종 0단어'
    try:
        current_final_prompt = normalize_kimodo_prompt(current_prompt_text)
        return f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_final_prompt.split())}단어 · 공식 공백·대소문자·문장부호 정규화\n\n최종 입력: {current_final_prompt}'
    except (OSError,ValueError) as current_prompt_error:
        return f'원문 {len(current_prompt_text.split())}단어 · 최종 확인 불가: {current_prompt_error}'


def restore_kimodo_inputs(current_history_record):
    current_request_record = current_history_record['request']
    return tuple(current_request_record[current_field_name] for current_field_name in ('prompt','frames','steps','seed','guidance_scale','heading_degrees','post_processing'))+(current_history_record['id'],)


def check_kimodo_readiness(current_model_ready,current_prompt_text):
    return bool(current_model_ready and current_prompt_text and current_prompt_text.strip())


def build_kimodo_interface(current_server_address,current_command_callback=None):
    current_execute_command = current_command_callback or execute_kimodo_command
    with gr.Blocks(title='Kimodo 모션 생성기') as current_interface_blocks:
        gr.Markdown('## Kimodo 모션 생성기 · NF4 실험\n텍스트로 SOMA 모션을 생성한 뒤 ANNY 중성형 v4 리그 적용·CUDA 렌더를 자동 실행합니다. 새 결과 영상은 ANNY이며 ZIP에는 원본 모션·관절 영상·ANNY GLB/Blend·프레임을 함께 저장합니다. 기존 이력은 생성 당시 결과를 유지합니다.')
        gr.Markdown('고정: Kimodo-SOMA-RP-v1.2 · 모션 FP32 · LLM2Vec Llama 3 8B NF4 / BF16 연산 · CUDA · 30fps · 1개 샘플 · DDIM. 인코딩 후 인코더를 해제하고 모션을 생성합니다. 이후 모션 모델을 해제하고 ANNY 512×512·30fps·정사영 렌더를 실행합니다. 모델 선택·부정 프롬프트·이미지 참조는 제공하지 않습니다.')
        current_model_ready = gr.State(False)
        current_model_output = gr.Markdown('모델 상태 확인 중')
        current_refresh_button = gr.Button('모델 준비 상태 확인')
        def refresh_kimodo_assets():
            try:
                current_asset_record = current_execute_command('model-status',{})
                return current_asset_record['message'],current_asset_record['ready']
            except Exception as current_asset_error:
                return f'모델 상태 확인 실패: {current_asset_error}',False
        current_refresh_event = current_refresh_button.click(refresh_kimodo_assets,outputs=[current_model_output,current_model_ready],queue=False)
        current_load_event = current_interface_blocks.load(refresh_kimodo_assets,outputs=[current_model_output,current_model_ready])
        current_prompt_control = gr.Textbox(label='동작 프롬프트',value=KIMODO_DEFAULT_SETTINGS['prompt'],lines=3,info='영문으로 주체와 신체 동작을 간결하게 작성하세요. 카메라·외형 묘사보다 실제 행동을 지정하세요. 100단어·400토큰 이내. 문장 여러 개도 하나의 동작 설명으로 사용합니다.')
        current_prompt_summary = gr.Markdown(describe_kimodo_prompt(KIMODO_DEFAULT_SETTINGS['prompt']))
        current_prompt_control.change(describe_kimodo_prompt,current_prompt_control,current_prompt_summary,queue=False)
        current_frame_control = gr.Number(label='프레임 수',value=KIMODO_DEFAULT_SETTINGS['frames'],minimum=30,maximum=300,precision=0,info='30fps: 90프레임=3초, 150프레임=5초, 300프레임=10초. 8GB의 모든 길이를 보장하지 않습니다.')
        current_seed_control = build_generation_seed(default_seed_value=KIMODO_DEFAULT_SETTINGS['seed'])
        with gr.Accordion('고급 설정',open=False):
            current_steps_control = gr.Number(label='샘플링 스텝',value=KIMODO_DEFAULT_SETTINGS['steps'],minimum=2,maximum=100,precision=0,info='공식 기본 100. 2스텝은 실행 연결 확인용이며 품질 평가에 사용하지 마세요.')
            current_guidance_control = gr.Number(label='텍스트 CFG',value=KIMODO_DEFAULT_SETTINGS['guidance_scale'],minimum=0,maximum=10,info='공식 기본 2. 텍스트 조건의 영향이며 원하는 동작의 성공을 보장하지 않습니다.')
            current_heading_control = gr.Number(label='초기 방향 (도)',value=KIMODO_DEFAULT_SETTINGS['heading_degrees'],minimum=-180,maximum=180,info='0은 +Z 방향. 시작 방향 조건이며 이후 방향을 계속 고정하는 기능이 아닙니다.')
            current_postprocessing_control = gr.Checkbox(label='공식 발 미끄러짐 후처리',value=KIMODO_DEFAULT_SETTINGS['post_processing'],info='기본 해제: 원본 동작 비교. 활성화하면 공식 후처리를 적용하고 실행 기록에 남깁니다.')
            gr.Markdown('[공식 모델카드](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.2) · [NF4 인코더](https://huggingface.co/matbee/kimodo-llm2vec-nf4)\n\nANNY는 위치 기반 몸통·사지·루트 전달입니다. 손가락 세부 회전·접지 보정·피부 충돌 보정은 적용하지 않으며 결과 검수가 필요합니다.\n\nNF4는 커뮤니티 양자화본입니다. BF16과 동작이 달라질 수 있으며 실제 품질은 결과를 검수하세요. 내부 30관절 추론을 공식 API가 77관절로 확장해 저장합니다.')
        current_input_controls = [current_prompt_control,current_frame_control,current_steps_control,current_seed_control,current_guidance_control,current_heading_control,current_postprocessing_control]
        current_generate_button = gr.Button('대기열에 추가',variant='primary',interactive=False)
        build_button_guidance(current_generate_button,'모델 자료와 전용 환경을 준비한 뒤 상태를 새로 확인하고 동작 프롬프트를 입력하세요.')
        with gr.Column() as current_confirmation_container:
            pass
        current_job_control = gr.Textbox(label='생성 ID',visible=False)
        current_status_output = gr.Markdown('입력을 준비하세요.')
        def enqueue_kimodo_generation(*current_input_values):
            current_job_record = current_execute_command('generate',build_kimodo_payload(*current_input_values))
            return current_job_record['id'],'공용 GPU 대기열에 등록했습니다.'
        bind_gpu_generation_confirmation(current_generate_button,enqueue_kimodo_generation,current_input_controls,[current_job_control,current_status_output],generation_confirmation_container=current_confirmation_container,generation_readiness_callback=check_kimodo_readiness,generation_readiness_inputs=[current_model_ready,current_prompt_control],generation_readiness_events=[current_refresh_event,current_load_event])
        build_video_job_monitor(current_execute_command,current_server_address,current_job_control,current_status_output)
        current_read_history,current_history_outputs = build_generation_history_view(current_execute_command,current_server_address,GENERATION_CLEANUP_SCOPE_TEXT,restore_input_callback=restore_kimodo_inputs,restore_output_components=[*current_input_controls,current_job_control],result_renderer_callback=render_video_generation_result,record_folder_route='/kimodo',allow_individual_delete=True,individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda:current_read_history(1),outputs=current_history_outputs)
    return current_interface_blocks
