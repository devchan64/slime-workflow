"""Kimodo NF4 실험 폼. 실행과 기록 수명은 공용 게이트웨이가 담당한다."""
import gradio as gr
import yaml
from generators.kimodo.contracts import KIMODO_CONFIG_ROOT, UniqueConfigLoader, KIMODO_DIRECTION_RECORDS
from tools.review.common.gradio_identifiers import build_generation_identifier
from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS,normalize_kimodo_prompt,validate_kimodo_request
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_video_results import build_video_job_monitor,render_video_generation_result
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT


KIMODO_INPUT_MINIMUM_WIDTH = 320

def execute_kimodo_command(current_command_name,current_payload_record):
    return execute_remote_management_command('kimodo',current_command_name,current_payload_record)


def build_kimodo_payload(current_prompt_text,current_frame_count,current_step_count,current_seed_value,current_guidance_value,current_heading_value,current_postprocessing_value,current_direction_names=None):
    for current_integer_value in (current_frame_count,current_step_count,current_seed_value):
        if type(current_integer_value) not in (int,float) or not float(current_integer_value).is_integer():
            raise ValueError('프레임·스텝·시드는 정수로 입력하세요.')
    current_request_record = {'action':'generate','prompt':current_prompt_text,'frames':int(current_frame_count),'steps':int(current_step_count),'seed':int(current_seed_value),'guidance_scale':current_guidance_value,'heading_degrees':current_heading_value,'post_processing':current_postprocessing_value,'directions':list(KIMODO_DEFAULT_SETTINGS['directions']) if current_direction_names is None else current_direction_names}
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
    return tuple(current_request_record[current_field_name] for current_field_name in ('prompt','frames','steps','seed','guidance_scale','heading_degrees','post_processing'))+(current_request_record.get('directions',['front_left']),current_history_record['id'])


def check_kimodo_readiness(current_model_ready,current_prompt_text,current_direction_names):
    return bool(current_model_ready and current_prompt_text and current_prompt_text.strip() and current_direction_names)


def load_kimodo_examples():
    current_example_record = yaml.load((KIMODO_CONFIG_ROOT/'prompt-examples.yaml').read_text(), Loader=UniqueConfigLoader)
    if not isinstance(current_example_record,dict) or set(current_example_record)!={'schema_version','examples'} or current_example_record['schema_version']!=1 or not isinstance(current_example_record['examples'],list) or not current_example_record['examples']:
        raise ValueError('Kimodo 프롬프트 예시 계약 오류')
    current_example_mapping = {}
    for current_example_value in current_example_record['examples']:
        if not isinstance(current_example_value,dict) or set(current_example_value)!={'id','label','prompt','frames'} or any(not isinstance(current_example_value[current_field_name],str) or not current_example_value[current_field_name].strip() for current_field_name in ('id','label','prompt')):
            raise ValueError('Kimodo 예시 필드 오류')
        if current_example_value['id'] in current_example_mapping:
            raise ValueError('Kimodo 예시 ID 중복')
        build_kimodo_payload(current_example_value['prompt'],current_example_value['frames'],KIMODO_DEFAULT_SETTINGS['steps'],KIMODO_DEFAULT_SETTINGS['seed'],KIMODO_DEFAULT_SETTINGS['guidance_scale'],KIMODO_DEFAULT_SETTINGS['heading_degrees'],KIMODO_DEFAULT_SETTINGS['post_processing'])
        current_example_mapping[current_example_value['id']] = current_example_value
    return current_example_mapping


def apply_kimodo_example(current_example_identifier):
    current_example_mapping = load_kimodo_examples()
    if current_example_identifier not in current_example_mapping:
        raise ValueError('불러올 동작 예시를 선택하세요.')
    current_example_record = current_example_mapping[current_example_identifier]
    return current_example_record['prompt'],current_example_record['frames']


def describe_kimodo_duration(current_frame_count):
    if type(current_frame_count) not in (int,float) or not 30<=current_frame_count<=300 or not float(current_frame_count).is_integer():
        return '프레임 수를 30~300 사이의 정수로 입력하세요.'
    return f'모션 길이 **{current_frame_count/30:g}초** · {int(current_frame_count)}프레임 · 30fps'


def render_kimodo_result(current_job_identifier,current_status_record,current_server_address):
    import html
    current_comparison_url = current_status_record.get('comparison_video')
    if not current_comparison_url:
        return render_video_generation_result(current_job_identifier,current_status_record,current_server_address)+'<p>이 결과에는 오픈포즈 비교 영상이 없습니다.</p>'
    current_comparison_html = render_video_generation_result(current_job_identifier,{**current_status_record,'video':current_comparison_url},current_server_address)
    current_pose_description = 'SOMA 원본(정면·측면) → SOMA 직접 투영 오픈포즈. 같은 프레임을 재생하며 카메라 높이·배율은 서로 다릅니다. 오픈포즈는 리타게팅 전 몸 관절이며 얼굴·손 상세 점은 포함하지 않습니다.' if current_status_record.get('pose_source')=='soma' else '이전 비교 결과: 오픈포즈는 리타게팅 후 ANNY 관절 투영입니다. SOMA 원본 패널은 결과에 따라 없을 수 있습니다.'
    return '<p>'+current_pose_description+'</p>'+current_comparison_html+f'<p><a href="{html.escape(current_status_record["video"],quote=True)}" target="_blank">원본 MP4</a></p>'


def build_kimodo_interface(current_server_address,current_command_callback=None):
    current_execute_command = current_command_callback or execute_kimodo_command
    with gr.Blocks(title='Kimodo 모션 생성기') as current_interface_blocks:
        gr.Markdown('## Kimodo 모션 생성기 · NF4 실험\n텍스트로 SOMA 모션을 생성하고 선택 방향의 오픈포즈를 직접 투영합니다. SOMA 원본·포즈 비교 영상과 모션·프레임을 ZIP으로 받습니다.')
        with gr.Accordion('고정 설정 · 모델 준비',open=False):
            gr.Markdown('고정: Kimodo-SOMA-RP-v1.2 · 모션 FP32 · LLM2Vec Llama 3 8B NF4 / BF16 연산 · CUDA · 30fps · 1개 샘플 · DDIM. 인코딩 후 인코더를 해제하고 모션을 생성합니다. 이후 모션 모델을 해제하고 SOMA 몸 관절을 512×512·30fps 정사영 포즈로 변환합니다. 모델 선택·부정 프롬프트·이미지 참조는 제공하지 않습니다.')
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
        current_example_mapping = load_kimodo_examples()
        with gr.Row():
            current_example_selector = gr.Dropdown(choices=[(current_example_record['label'],current_example_name) for current_example_name,current_example_record in current_example_mapping.items()],value='standing',label='동작 예시',info='불러오면 프롬프트와 프레임만 변경합니다. 자동 생성하지 않습니다.')
            current_example_button = gr.Button('예시 불러오기')
        with gr.Row():
            with gr.Column(min_width=KIMODO_INPUT_MINIMUM_WIDTH):
                current_prompt_control = gr.Textbox(label='동작 프롬프트',value=KIMODO_DEFAULT_SETTINGS['prompt'],lines=3,info='영문으로 주체와 신체 동작을 간결하게 작성하세요. 카메라·외형 묘사보다 실제 행동을 지정하세요. 100단어·400토큰 이내. 문장 여러 개도 하나의 동작 설명으로 사용합니다.')
            with gr.Column(min_width=KIMODO_INPUT_MINIMUM_WIDTH):
                current_direction_control = gr.CheckboxGroup(choices=[(f"{current_direction_record['label']} ({current_direction_record['angle']}°)",current_direction_name) for current_direction_name,current_direction_record in KIMODO_DIRECTION_RECORDS.items()],value=KIMODO_DEFAULT_SETTINGS['directions'],label='출력 방향 · 복수 선택',info='카메라 방향입니다. 동작 프롬프트·초기 방향은 변경하지 않습니다. 여러 방향은 같은 프레임으로 비교하며 렌더 시간·저장 용량이 늘어납니다.')
        current_prompt_summary = gr.Markdown(describe_kimodo_prompt(KIMODO_DEFAULT_SETTINGS['prompt']))
        current_prompt_control.change(describe_kimodo_prompt,current_prompt_control,current_prompt_summary,queue=False)
        current_frame_control = gr.Number(label='프레임 수',value=KIMODO_DEFAULT_SETTINGS['frames'],minimum=30,maximum=300,precision=0,info='30fps: 90프레임=3초, 150프레임=5초, 300프레임=10초. 8GB의 모든 길이를 보장하지 않습니다.')
        current_duration_output = gr.Markdown(describe_kimodo_duration(KIMODO_DEFAULT_SETTINGS['frames']))
        current_frame_control.change(describe_kimodo_duration,current_frame_control,current_duration_output,queue=False)
        current_example_button.click(apply_kimodo_example,current_example_selector,[current_prompt_control,current_frame_control],queue=False)
        current_seed_control = build_generation_seed(default_seed_value=KIMODO_DEFAULT_SETTINGS['seed'])
        with gr.Accordion('고급 설정',open=False):
            current_steps_control = gr.Number(label='샘플링 스텝',value=KIMODO_DEFAULT_SETTINGS['steps'],minimum=2,maximum=100,precision=0,info='공식 기본 100. 2스텝은 실행 연결 확인용이며 품질 평가에 사용하지 마세요.')
            current_guidance_control = gr.Number(label='텍스트 CFG',value=KIMODO_DEFAULT_SETTINGS['guidance_scale'],minimum=0,maximum=10,info='공식 기본 2. 텍스트 조건의 영향이며 원하는 동작의 성공을 보장하지 않습니다.')
            current_heading_control = gr.Number(label='초기 방향 (도)',value=KIMODO_DEFAULT_SETTINGS['heading_degrees'],minimum=-180,maximum=180,info='0은 +Z 방향. 시작 방향 조건이며 이후 방향을 계속 고정하는 기능이 아닙니다.')
            current_postprocessing_control = gr.Checkbox(label='공식 발 미끄러짐 후처리',value=KIMODO_DEFAULT_SETTINGS['post_processing'],info='기본 해제: 원본 동작 비교. 활성화하면 공식 후처리를 적용하고 실행 기록에 남깁니다.')
            gr.Markdown('[공식 모델카드](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.2) · [NF4 인코더](https://huggingface.co/matbee/kimodo-llm2vec-nf4)\n\nANNY 리그 기능은 폐기되었습니다. SOMA 몸 포즈에는 얼굴·손 상세 점이 포함되지 않습니다.\n\nNF4는 커뮤니티 양자화본입니다. BF16과 동작이 달라질 수 있으며 실제 품질은 결과를 검수하세요. 내부 30관절 추론을 공식 API가 77관절로 확장해 저장합니다.')
        current_input_controls = [current_prompt_control,current_frame_control,current_steps_control,current_seed_control,current_guidance_control,current_heading_control,current_postprocessing_control,current_direction_control]
        gr.Markdown('예시는 시작점입니다. 심호흡·서 있기에서도 머리나 몸이 움직일 수 있으므로 결과를 검수하세요.')
        current_generate_button = gr.Button('대기열에 추가',variant='primary',interactive=False)
        build_button_guidance(current_generate_button,'모델 자료와 전용 환경을 준비한 뒤 상태를 새로 확인하고 동작 프롬프트와 출력 방향을 한 개 이상 선택하세요.')
        with gr.Column() as current_confirmation_container:
            pass
        gr.Markdown('### 진행 상태 · 최신 결과\n접수한 작업의 진행률·예상 시간·VRAM과 완료 영상을 표시합니다. 이전 작업은 아래 생성 이력에서 조회하세요.')
        current_job_control = build_generation_identifier('접수한 생성 ID')
        current_status_output = gr.Markdown('입력을 준비하세요.')
        def enqueue_kimodo_generation(*current_input_values):
            current_job_record = current_execute_command('generate',build_kimodo_payload(*current_input_values))
            return current_job_record['id'],'공용 GPU 대기열에 등록했습니다.'
        bind_gpu_generation_confirmation(current_generate_button,enqueue_kimodo_generation,current_input_controls,[current_job_control,current_status_output],generation_confirmation_container=current_confirmation_container,generation_readiness_callback=check_kimodo_readiness,generation_readiness_inputs=[current_model_ready,current_prompt_control,current_direction_control],generation_readiness_events=[current_refresh_event,current_load_event])
        build_video_job_monitor(current_execute_command,current_server_address,current_job_control,current_status_output,result_renderer_callback=render_kimodo_result)
        current_read_history,current_history_outputs = build_generation_history_view(current_execute_command,current_server_address,GENERATION_CLEANUP_SCOPE_TEXT,restore_input_callback=restore_kimodo_inputs,restore_output_components=[*current_input_controls,current_job_control],result_renderer_callback=render_kimodo_result,record_folder_route='/kimodo',allow_individual_delete=True,individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda:current_read_history(1),outputs=current_history_outputs)
    return current_interface_blocks
