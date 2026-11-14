"""Wan2.2 Fun Control 실험용 Gradio 입력과 공용 이력."""
import base64
import io
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageOps
import gradio as gr
import yaml
from tools.review.common.strict_yaml import UniqueConfigLoader
from generators.wan_fun.contracts import reject_retired_rgb_input, FUN_JOB_STORAGE, FUN_DEFAULT_SETTINGS, FUN_MAX_FRAME_COUNT, validate_fun_request
from generators.wan_fun.video_input import FUN_VIDEO_MAXIMUM_BYTES
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_logs import build_execution_logs
from tools.review.common.gradio_video_results import describe_video_generation_status, render_video_generation_result
from tools.review.common.generation_status_lookup import read_existing_generation_status
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT

FUN_EXAMPLE_STORAGE_ROOT = Path(__file__).resolve().parents[4] / 'generators/wan_fun/examples'


def inspect_fun_pose_video(current_video_path):
    """업로드 영상의 조건과 추천 프레임 수를 확인한다."""
    if not current_video_path:
        return None, '포즈 MP4를 첨부하세요.'
    try:
        current_video_file = Path(current_video_path)
        if current_video_file.stat().st_size > FUN_VIDEO_MAXIMUM_BYTES:
            return None, '영상이 32MiB를 초과합니다. 크기를 줄여 다시 첨부하세요.'
        with current_video_file.open('rb') as current_video_stream:
            if current_video_stream.read(8)[4:8] != b'ftyp':
                return None, 'MP4 영상을 첨부하세요.'
        current_video_capture = cv2.VideoCapture(str(current_video_file))
        try:
            if not current_video_capture.isOpened():
                return None, '영상을 읽을 수 없습니다. MP4를 다시 첨부하세요.'
            current_frame_rate = current_video_capture.get(cv2.CAP_PROP_FPS)
            current_frame_count = int(current_video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
            current_frame_width = int(current_video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            current_frame_height = int(current_video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        finally:
            current_video_capture.release()
        current_description_text = f'입력: {current_frame_width}×{current_frame_height} · {current_frame_rate:.2f}fps · {current_frame_count}프레임.'
        if (current_frame_width, current_frame_height) != (832, 480) or not 15.99 <= current_frame_rate <= 16.01:
            return None, current_description_text + ' 832×480·16fps로 변환해 다시 첨부하세요.'
        current_recommended_count = min(FUN_MAX_FRAME_COUNT, 1 + 4 * ((current_frame_count - 1) // 4))
        if current_recommended_count < 5:
            return None, current_description_text + ' 최소 5프레임의 영상을 첨부하세요.'
        return current_recommended_count, current_description_text + f' 사용 가능 · 최대 {current_recommended_count}프레임 선택 가능.'
    except (OSError, ValueError, OverflowError):
        return None, '영상 정보를 읽을 수 없습니다. MP4를 다시 첨부하세요.'


def describe_fun_input_readiness(current_reference_path, current_video_path, current_prompt_text, current_frame_count):
    current_recommended_count, current_video_description = inspect_fun_pose_video(current_video_path)
    current_missing_items = []
    if not current_reference_path:
        current_missing_items.append('외형 참조 이미지를 첨부하세요.')
    if not current_prompt_text or not current_prompt_text.strip():
        current_missing_items.append('동작 프롬프트를 입력하세요.')
    if current_recommended_count is None:
        current_missing_items.append(current_video_description)
    elif not isinstance(current_frame_count, (int, float)) or isinstance(current_frame_count, bool) or not float(current_frame_count).is_integer() or not 5 <= current_frame_count <= current_recommended_count or (int(current_frame_count) - 1) % 4:
        current_missing_items.append(f'출력 프레임은 5~{current_recommended_count}의 4n+1로 선택하세요.')
    return not current_missing_items, ' '.join(current_missing_items) if current_missing_items else '입력 조건 확인 완료. 대기열 등록을 진행하세요.'


def load_fun_example_catalog():
    current_catalog_record = yaml.load((FUN_EXAMPLE_STORAGE_ROOT / 'index.yaml').read_text(), Loader=UniqueConfigLoader)
    if not isinstance(current_catalog_record, dict) or set(current_catalog_record) != {'schema_version', 'examples'} or current_catalog_record['schema_version'] != 1 or not isinstance(current_catalog_record['examples'], list):
        raise ValueError('예제 목록 계약 오류')
    current_example_mapping = {}
    for current_example_record in current_catalog_record['examples']:
        if not isinstance(current_example_record, dict) or set(current_example_record) != {'id', 'label'} or any(not isinstance(current_example_record[current_field_name], str) or not current_example_record[current_field_name].strip() for current_field_name in ('id', 'label')):
            raise ValueError('예제 목록 필드 오류')
        current_example_identifier = current_example_record['id']
        if current_example_identifier in current_example_mapping or Path(current_example_identifier).name != current_example_identifier or current_example_identifier in ('.', '..'):
            raise ValueError('예제 ID 중복 또는 경로 오류')
        current_example_mapping[current_example_identifier] = current_example_record['label']
    return current_example_mapping


def load_fun_selected_example(current_example_identifier):
    if current_example_identifier not in load_fun_example_catalog():
        raise ValueError('예제를 선택하세요.')
    current_example_directory = FUN_EXAMPLE_STORAGE_ROOT / current_example_identifier
    """이력 삭제와 독립된 제작 기준 예제를 입력에만 적용한다."""
    current_example_record = yaml.load((current_example_directory / 'input.yaml').read_text(), Loader=UniqueConfigLoader)
    if not isinstance(current_example_record, dict) or set(current_example_record) != {'source_job', 'request'} or not isinstance(current_example_record['source_job'], str) or not isinstance(current_example_record['request'], dict):
        raise ValueError('Fun Control 예제 필드 오류')
    current_request_record = current_example_record['request']
    current_reference_path = current_example_directory / 'reference-1.png'
    current_video_path = current_example_directory / 'pose-input.mp4'
    current_validation_record = dict(current_request_record)
    current_validation_record['images'] = [base64.b64encode(current_reference_path.read_bytes()).decode()]
    current_validation_record['pose_video'] = base64.b64encode(current_video_path.read_bytes()).decode()
    validate_fun_request(current_validation_record)
    return (str(current_reference_path), str(current_video_path), None, current_request_record['control_type'], current_request_record['prompt'], current_request_record['negative_prompt'], current_request_record['frames'], current_request_record['seed'], current_request_record['steps'], current_request_record['flow_shift'], current_request_record['guidance_scale'], current_request_record['switch_ratio'], 'pose-video', False, False, None, None, False)


def render_fun_video_result(current_job_identifier, current_status_record, current_server_address):
    from tools.review.common.gradio_video_results import render_condition_video_previews
    return render_video_generation_result(current_job_identifier, current_status_record, current_server_address)+render_condition_video_previews(current_status_record)


def execute_fun_command(current_command_name, current_payload_record):
    return execute_remote_management_command('wan22-fun-control', current_command_name, current_payload_record)


def encode_fun_image(current_image_object, current_padding_color):
    current_image_object = current_image_object.convert('RGBA')
    current_image_object = ImageOps.contain(current_image_object, (832, 480), Image.Resampling.LANCZOS)
    current_canvas_image = Image.new('RGB', (832, 480), current_padding_color)
    current_canvas_image.paste(current_image_object, ((832-current_image_object.width)//2, (480-current_image_object.height)//2), current_image_object)
    current_image_buffer = io.BytesIO()
    current_canvas_image.save(current_image_buffer, format='PNG')
    return base64.b64encode(current_image_buffer.getvalue()).decode()


def build_fun_payload(current_reference_path, current_video_path, current_frame_paths, current_control_type, current_prompt_text, current_negative_text, current_frame_count, current_seed_value, current_steps_value, current_shift_value, current_guidance_value, current_switch_ratio, current_input_mode="preprocessed", current_include_hands=False, current_include_face=False, current_start_path=None, current_end_path=None, current_same_endpoint=False):
    reject_retired_rgb_input({'input_mode': current_input_mode})
    if current_start_path or current_end_path or current_same_endpoint:
        raise ValueError('시작·종료 이미지 자체 확장은 폐기되었습니다.')
    if not current_reference_path or (bool(current_video_path) == bool(current_frame_paths)):
        raise ValueError('외형 참조 1장과 제어 영상 또는 PNG 목록 중 하나를 첨부하세요.')
    for current_integer_value in (current_frame_count, current_seed_value, current_steps_value):
        if isinstance(current_integer_value, bool) or not isinstance(current_integer_value, (int, float)) or not float(current_integer_value).is_integer():
            raise ValueError('프레임·시드·스텝은 정수여야 합니다.')
    current_frame_count = int(current_frame_count)
    if not 5 <= current_frame_count <= FUN_MAX_FRAME_COUNT or (current_frame_count-1) % 4:
        raise ValueError(f'프레임 수는 5~{FUN_MAX_FRAME_COUNT} 범위의 4n+1입니다.')
    with Image.open(current_reference_path) as current_reference_image:
        if current_reference_image.size != (832, 480):
            gr.Warning('참조 이미지를 비율 유지해 832×480 흰 여백으로 맞춥니다. 원본은 보존합니다.')
        current_encoded_images = [encode_fun_image(current_reference_image, 'white')]
    if current_input_mode == 'pose-video':
        current_payload_record = {'action':'generate','prompt':current_prompt_text,'negative_prompt':current_negative_text,'images':current_encoded_images,'control_type':'pose','width':832,'height':480,'frames':current_frame_count,'seed':int(current_seed_value),'steps':int(current_steps_value),'flow_shift':current_shift_value,'guidance_scale':current_guidance_value,'switch_ratio':current_switch_ratio,'pose_video':base64.b64encode(Path(current_video_path).read_bytes()).decode()}
        validate_fun_request(current_payload_record)
        return current_payload_record
    if current_input_mode == 'soma-video':
        if not current_video_path or current_frame_paths or current_control_type != 'pose':
            raise ValueError('SOMA 입력은 렌더 MP4 영상과 pose 제어를 선택하세요.')
    elif current_input_mode != 'preprocessed':
        raise ValueError('지원하지 않는 입력 방식')
    if current_video_path and current_input_mode == 'preprocessed':
        current_video_capture = cv2.VideoCapture(str(current_video_path))
        try:
            if not current_video_capture.isOpened():
                raise ValueError('제어 영상 디코딩 실패')
            current_input_fps = current_video_capture.get(cv2.CAP_PROP_FPS)
            if abs(current_input_fps - 16) > 0.1:
                gr.Warning(f'입력 {current_input_fps:.2f}fps의 프레임을 순서대로 사용하고 결과는 16fps로 재생합니다.')
            for current_frame_index in range(current_frame_count):
                current_frame_ready, current_frame_array = current_video_capture.read()
                if not current_frame_ready:
                    raise ValueError(f'제어 영상이 부족합니다: {current_frame_index}/{current_frame_count}프레임. 반복·복제하지 않습니다.')
                current_encoded_images.append(encode_fun_image(Image.fromarray(cv2.cvtColor(current_frame_array, cv2.COLOR_BGR2RGB)), 'black'))
        finally:
            current_video_capture.release()
    elif current_input_mode == 'preprocessed':
        if len(current_frame_paths) != current_frame_count:
            raise ValueError('PNG 목록은 출력 프레임 수와 같아야 합니다. 업로드 순서로 배치합니다.')
        for current_frame_path in current_frame_paths:
            with Image.open(current_frame_path) as current_frame_image:
                current_encoded_images.append(encode_fun_image(current_frame_image, 'black'))
    current_payload_record = {'action': 'generate', 'prompt': current_prompt_text, 'negative_prompt': current_negative_text, 'images': current_encoded_images, 'control_type': current_control_type, 'width': 832, 'height': 480, 'frames': current_frame_count, 'seed': int(current_seed_value), 'steps': int(current_steps_value), 'flow_shift': current_shift_value, 'guidance_scale': current_guidance_value, 'switch_ratio': current_switch_ratio}
    if current_input_mode == 'soma-video':
        current_payload_record.update(pose_include_hands=current_include_hands, pose_include_face=current_include_face)
        current_payload_record['driving_video'] = base64.b64encode(Path(current_video_path).read_bytes()).decode()
    validate_fun_request(current_payload_record)
    return current_payload_record


def restore_fun_inputs(current_history_record):
    current_job_identifier = current_history_record['id']
    current_job_directory = (FUN_JOB_STORAGE/current_job_identifier).resolve()
    if current_job_directory.parent != FUN_JOB_STORAGE.resolve():
        raise ValueError('이력 경로 오류')
    current_request_record = current_history_record['request']
    reject_retired_rgb_input(current_request_record)
    if (current_request_record.get('pose_video_file') != 'pose-input.mp4' or not (current_job_directory/'pose-input.mp4').is_file()):
        raise ValueError('이전 작업은 처리된 포즈 MP4 입력이 없습니다. Kimodo의 DWPose MP4를 첨부해 새 작업을 생성하세요. 기존 결과는 조회할 수 있습니다.')
    current_reference_paths = []
    for current_reference_name in current_request_record['references']:
        current_reference_path = (current_job_directory/current_reference_name).resolve()
        if current_reference_path.parent != current_job_directory or not current_reference_path.is_file():
            raise ValueError('이력 입력 사본 누락 또는 경로 오류')
        current_reference_paths.append(str(current_reference_path))
    return (current_reference_paths[0], str(current_job_directory/'pose-input.mp4'), current_reference_paths[1:] or None, current_request_record['control_type'], current_request_record['prompt'], current_request_record['negative_prompt'], current_request_record['frames'], current_request_record['seed'], current_request_record['steps'], current_request_record['flow_shift'], current_request_record['guidance_scale'], current_request_record['switch_ratio'], 'pose-video', current_request_record.get('pose_include_hands', bool(current_request_record.get('driving_video_file'))), current_request_record.get('pose_include_face', bool(current_request_record.get('driving_video_file'))), str(current_job_directory/'start-image.png') if current_request_record.get('start_image_file') else None, str(current_job_directory/'end-image.png') if current_request_record.get('end_image_file') else None, current_request_record.get('end_image_same_as_start', False), current_job_identifier)


def describe_fun_step_split(current_steps_value, current_switch_ratio):
    if current_steps_value is None or current_switch_ratio is None:
        return '스텝과 전환 비율을 입력하세요.'
    current_total_steps = int(current_steps_value)
    current_high_steps = max(1, min(current_total_steps - 1, round(current_total_steps * current_switch_ratio)))
    return f'실제 배분: 고노이즈 {current_high_steps}스텝 + 저노이즈 {current_total_steps-current_high_steps}스텝 · 시간값 기준 전환이 아닌 스텝 비율입니다.'


def build_fun_interface(current_server_address, current_command_callback=None):
    current_execute_command = current_command_callback or execute_fun_command
    with gr.Blocks(title='Wan2.2 Fun Control 생성기') as current_interface_blocks:
        gr.Markdown('## Wan2.2 Fun Control A14B 실험 생성기\n포즈 영상과 참조 이미지로 애니메이션을 생성합니다. VideoX-Fun DWPose 추출과 관절 길이 보정은 Kimodo 생성기에서 수행합니다.')
        current_model_status = gr.Markdown('모델 준비 상태 확인 중')
        current_model_refresh = gr.Button('모델 준비 상태 확인')
        def read_fun_model_status():
            try:
                return current_execute_command('model-status', {})['message']
            except Exception as current_status_error:
                return f'모델 상태 확인 실패: {current_status_error}'
        current_model_refresh.click(read_fun_model_status, outputs=current_model_status, queue=False)
        current_interface_blocks.load(read_fun_model_status, outputs=current_model_status)
        gr.Markdown('### 1. 입력 준비')
        with gr.Row():
            current_example_selector = gr.Dropdown(choices=[(current_example_label, current_example_identifier) for current_example_identifier, current_example_label in load_fun_example_catalog().items()], value=None, label='동작 예제', filterable=True, info='이름을 입력해 검색하고 예제를 선택하세요. 불러오기는 입력만 교체하며 생성하지 않습니다.')
            current_example_button = gr.Button('예제 불러오기')
        current_pending_example = gr.State(None)
        with gr.Group(visible=False) as current_example_confirmation:
            gr.Markdown('현재 참조·포즈·프롬프트·생성 설정을 선택한 예제로 교체합니다. 생성은 실행하지 않습니다.')
            with gr.Row():
                current_example_confirm = gr.Button('입력 교체 확인')
                current_example_cancel = gr.Button('취소')
        current_mode_control = gr.State('pose-video')
        current_frames_control = gr.State(None)
        current_type_control = gr.State('pose')
        gr.Markdown('포즈 영상의 동작을 따릅니다. 참조 이미지는 캐릭터 조건이며 첫 프레임을 고정하지 않습니다. 참조의 자세도 결과에 영향을 줄 수 있습니다.')
        with gr.Row():
            with gr.Column():
                current_reference_control = gr.Image(type='filepath', sources=['upload'], label='캐릭터 외형 참조 · 1장')
                with gr.Accordion('참조 자세 권장 사항', open=False):
                    gr.Markdown('포즈 영상의 첫 프레임과 비슷한 몸 방향·팔다리 위치·크기의 참조를 권장합니다. 첫 프레임 고정은 아니며 결과의 외형과 비율을 검수하세요.')
            with gr.Column():
                current_video_control = gr.Video(sources=['upload'], label='처리된 포즈 영상 · MP4 · 832×480 · 16fps', include_audio=True, buttons=['download'])
                current_video_summary = gr.Markdown('포즈 MP4를 첨부하세요.')
                current_recommended_button = gr.Button('입력 영상의 최대 프레임 적용', interactive=False)
        current_start_control = gr.State(None)
        current_end_control = gr.State(None)
        current_same_control = gr.State(False)
        current_hands_control = gr.State(False)
        current_face_control = gr.State(False)
        current_pose_help = gr.Markdown('**포즈 모드:** Kimodo 결과의 DWPose 포즈 MP4를 입력하세요. SOMA 인체 렌더 영상은 입력 대상이 아닙니다. 832×480 · 16fps 영상을 앞에서부터 지정 프레임 수만큼 사용하며 포즈 재검출·관절 길이 보정은 수행하지 않습니다.')
        with gr.Accordion('시작 프레임이 흐릴 때 · 포즈 준비 구간 가이드', open=False) as current_pose_guide:
            gr.Markdown('시작 구간이 흐리고 뒤로 갈수록 선명해질 때, 포즈 영상 앞에 첫 프레임을 반복한 준비 구간을 추가해 보세요. 이번 휴식 동작 실험에서는 첫 프레임 4장을 앞에 추가한 20스텝 결과가 개선됐습니다. 모든 동작에서 같은 효과를 보장하거나 원인이 확정된 것은 아닙니다.')
            gr.Markdown('**적용 예:** 기존 109프레임 앞에 첫 포즈 4장을 추가하면 113프레임입니다. 원래 첫 프레임까지 같은 포즈가 5프레임 연속이며, 추가 시간은 16fps 기준 0.25초입니다. 준비 구간을 포함한 출력 프레임 수를 지정하세요. 출력은 4n+1, 최대 129프레임이며 입력 영상은 그 길이 이상이어야 합니다. 이 안내가 영상을 자동으로 수정하지는 않습니다.')
            gr.Markdown('**검수:** 처음 1~5프레임과 동작 시작 이후의 선명도·잔상·캐릭터 크기를 비교하세요. 필요한 경우 생성 후 준비 구간을 잘라 사용할 수 있지만, 제거할 길이는 결과를 보고 결정하세요.')
        gr.Markdown('### 2. 동작과 생성 설정')
        current_prompt_control = gr.Textbox(label='장면·동작 프롬프트', lines=3)
        current_prompt_summary = gr.Markdown('원문 0단어 · 최종 0단어 · 추가 문구 없음')
        current_prompt_control.change(lambda current_prompt_text: f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어 · 추가 문구 없음', current_prompt_control, current_prompt_summary, queue=False)
        with gr.Accordion('부정 프롬프트', open=False):
            current_negative_control = gr.Textbox(label='부정 프롬프트', value='')
            current_negative_summary = gr.Markdown('원문 0단어 · 최종 0단어')
            current_negative_control.change(lambda current_prompt_text: f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어', current_negative_control, current_negative_summary, queue=False)
        gr.Markdown('출력 고정: 832×480 · 16fps. 8GB에서 129프레임 완료 기록이 있으나 모든 조건을 보장하지 않습니다.')
        current_count_control = gr.Number(value=FUN_DEFAULT_SETTINGS['frames'], precision=0, minimum=5, maximum=FUN_MAX_FRAME_COUNT, step=4, label=f'출력 프레임 · 4n+1 · 5~{FUN_MAX_FRAME_COUNT}', info='최대 129프레임입니다. 8GB 환경에서 129프레임 생성 완료를 확인했으며 품질은 별도 검수합니다. 부족한 제어 프레임은 자동 반복하지 않습니다.')
        def update_fun_video_summary(current_video_path):
            current_recommended_count, current_video_description = inspect_fun_pose_video(current_video_path)
            return current_video_description, gr.update(interactive=current_recommended_count is not None)
        current_video_control.change(update_fun_video_summary, current_video_control, [current_video_summary, current_recommended_button], queue=False)
        current_recommended_button.click(lambda current_video_path: inspect_fun_pose_video(current_video_path)[0], current_video_control, current_count_control, queue=False)
        current_steps_control = gr.Number(value=FUN_DEFAULT_SETTINGS['steps'], precision=0, minimum=2, maximum=100, label='스텝 · 2~100', info='실험 기본 20. 증가하면 계산량이 늘며 동작 개선을 보장하지 않습니다.')
        current_duration_output = gr.Markdown()
        current_count_control.change(lambda current_frame_value: f'{current_frame_value}프레임 · {current_frame_value/16:.3f}초 · 16fps' if current_frame_value else '프레임 수를 입력하세요.',current_count_control,current_duration_output,queue=False)
        current_interface_blocks.load(lambda: f"{FUN_DEFAULT_SETTINGS['frames']}프레임 · {FUN_DEFAULT_SETTINGS['frames']/16:.3f}초 · 16fps",outputs=current_duration_output)
        current_frame_presets = gr.Radio(choices=[21,41,81,129],value=None,label='프레임 빠른 선택 · 직접 입력도 가능')
        current_count_control.change(lambda current_frame_value: gr.update(value=current_frame_value if current_frame_value in (21,41,81,129) else None),current_count_control,current_frame_presets,queue=False)
        current_frame_presets.input(lambda current_frame_value: current_frame_value,current_frame_presets,current_count_control,queue=False)
        current_seed_control = build_generation_seed(default_seed_value=FUN_DEFAULT_SETTINGS['seed'])
        with gr.Group():
            gr.Markdown('### 고급 설정')
            gr.Markdown('고정: 고·저노이즈 Q4_K_M · Euler/simple · CUDA 연산/CPU 가중치 오프로드 · 가속 LoRA 없음.')
            current_shift_control = gr.Number(value=FUN_DEFAULT_SETTINGS['flow_shift'], minimum=0.1, maximum=20, label='Flow shift · 노이즈 시간 배분', info='기본 5. 높이면 같은 스텝 위치의 노이즈 수준이 높아집니다. CFG와 독립적으로 입력합니다. 동작 속도나 참조 강도가 아닙니다.')
            current_guidance_control = gr.Number(value=FUN_DEFAULT_SETTINGS['guidance_scale'], minimum=1, maximum=10, label='CFG 강도 · 조건 유도', info='기본 6. 조건부·무조건부 예측 차이에 적용하는 배율입니다. Flow shift나 참조 이미지 전용 강도가 아닙니다.')
            current_switch_control = gr.Number(value=FUN_DEFAULT_SETTINGS['switch_ratio'], minimum=0.1, maximum=0.9, label='고노이즈 스텝 비율 · 0.1~0.9', info='기본 0.5. 전체 스텝의 앞부분은 고노이즈 모델, 나머지는 저노이즈 모델을 사용합니다.')
            gr.Markdown('VAE 고정: 일반 인코딩·디코딩. 타일 처리와 OOM 자동 대체는 사용하지 않습니다. 이전 타일 이력을 불러와 새로 생성해도 일반 VAE를 사용합니다.')
            current_split_summary = gr.Markdown(describe_fun_step_split(FUN_DEFAULT_SETTINGS['steps'], FUN_DEFAULT_SETTINGS['switch_ratio']))
            current_steps_control.change(describe_fun_step_split, [current_steps_control,current_switch_control], current_split_summary, queue=False)
            current_switch_control.change(describe_fun_step_split, [current_steps_control,current_switch_control], current_split_summary, queue=False)
            gr.Markdown('범위는 이 페이지의 실험 허용 범위입니다. [모델카드](https://huggingface.co/alibaba-pai/Wan2.2-Fun-A14B-Control) · [공식 ComfyUI 안내](https://docs.comfy.org/tutorials/video/wan/wan2-2-fun-control). 가속 4스텝 LoRA 예제와 현재 Q4 비가속 설정은 다릅니다.')
        current_input_controls = [current_reference_control,current_video_control,current_frames_control,current_type_control,current_prompt_control,current_negative_control,current_count_control,current_seed_control,current_steps_control,current_shift_control,current_guidance_control,current_switch_control,current_mode_control,current_hands_control,current_face_control,current_start_control,current_end_control,current_same_control]
        current_example_button.click(lambda current_example_identifier: (current_example_identifier, gr.update(visible=True)),current_example_selector,[current_pending_example,current_example_confirmation],queue=False)
        current_example_cancel.click(lambda: gr.update(visible=False),outputs=current_example_confirmation,queue=False)
        current_example_confirm.click(lambda current_example_identifier: (*load_fun_selected_example(current_example_identifier),gr.update(visible=False)),inputs=current_pending_example,outputs=[*current_input_controls,current_example_confirmation],queue=False)
        gr.Markdown('### 3. 실행 조건 확인')
        current_request_summary = gr.Markdown()
        def describe_current_fun_settings(current_mode_value,current_frame_value,current_steps_value,current_seed_value,current_shift_value,current_cfg_value,current_ratio_value):
            current_duration_text = f'{current_frame_value / 16:.3f}초' if isinstance(current_frame_value, (int, float)) else '미정'
            return f"입력: 처리된 포즈 영상 · 출력 {current_frame_value}프레임 · 16fps · {current_duration_text} · 스텝 {current_steps_value} · 시드 {current_seed_value} · Flow shift {current_shift_value} · CFG {current_cfg_value}\n\n{describe_fun_step_split(current_steps_value,current_ratio_value)}"
        current_summary_inputs=[current_mode_control,current_count_control,current_steps_control,current_seed_control,current_shift_control,current_guidance_control,current_switch_control]
        for current_summary_control in current_summary_inputs:
            current_summary_control.change(describe_current_fun_settings,current_summary_inputs,current_request_summary,queue=False)
        current_interface_blocks.load(describe_current_fun_settings,current_summary_inputs,current_request_summary)
        current_required_help=gr.Markdown('필수: 외형 참조 · 처리된 포즈 MP4 · 동작 프롬프트. 입력 후 대기열 등록 확인을 진행하세요.')
        current_readiness_inputs = [current_reference_control, current_video_control, current_prompt_control, current_count_control]
        for current_readiness_control in current_readiness_inputs:
            current_readiness_control.change(lambda *current_values: describe_fun_input_readiness(*current_values)[1], current_readiness_inputs, current_required_help, queue=False)
        current_generate_button = gr.Button('대기열에 추가', variant='primary', interactive=False)
        build_button_guidance(current_generate_button, '현재 모드의 필수 입력을 준비하세요. 확인 후 대기열에 등록하며 취소하면 실행하지 않습니다.')
        with gr.Column() as current_confirmation_container:
            pass
        gr.Markdown('### 4. 현재 작업과 결과 검수')
        current_job_control = gr.Textbox(label='조회 중인 생성 ID')
        current_status_output = gr.Markdown('입력을 준비하세요.')
        current_result_output = gr.HTML('')
        current_result_identity = gr.State('')
        current_log_output,current_log_enabled,_ = build_execution_logs()
        def enqueue_fun_generation(*current_input_values):
            current_job_record = current_execute_command('generate',build_fun_payload(*current_input_values))
            return current_job_record['id'], '공용 GPU 대기열에 등록했습니다.'
        bind_gpu_generation_confirmation(current_generate_button,enqueue_fun_generation,current_input_controls,[current_job_control,current_status_output],generation_confirmation_container=current_confirmation_container,generation_readiness_callback=lambda *current_values: describe_fun_input_readiness(*current_values)[0],generation_readiness_inputs=current_readiness_inputs)
        current_generation_timer = gr.Timer(5,active=False)
        def refresh_fun_status(current_job_identifier,current_logs_enabled,current_previous_result):
            if not current_job_identifier:
                return gr.skip(),gr.skip(),gr.skip(),gr.skip(),gr.Timer(active=False)
            current_status_record = read_existing_generation_status(current_execute_command,current_job_identifier)
            if current_status_record is None:
                return '삭제된 이력입니다.','','','',gr.Timer(active=False)
            current_result_url = current_status_record.get('video','')
            return describe_video_generation_status(current_status_record),render_fun_video_result(current_job_identifier,current_status_record,current_server_address) if current_result_url and current_result_url!=current_previous_result else gr.skip(),current_status_record.get('log','') if current_logs_enabled else gr.skip(),current_result_url,gr.Timer(active=current_status_record.get('status') not in ('completed','failed','cancelled','paused'))
        current_generation_timer.tick(refresh_fun_status,[current_job_control,current_log_enabled,current_result_identity],[current_status_output,current_result_output,current_log_output,current_result_identity,current_generation_timer],queue=False,show_progress='hidden')
        current_job_control.change(lambda current_job_identifier:gr.Timer(active=bool(current_job_identifier)),current_job_control,current_generation_timer,queue=False)
        current_read_history,current_history_outputs = build_generation_history_view(current_execute_command,current_server_address,GENERATION_CLEANUP_SCOPE_TEXT,restore_input_callback=restore_fun_inputs,restore_output_components=[*current_input_controls,current_job_control],result_renderer_callback=render_fun_video_result,record_folder_route='/wan22-fun-control',allow_individual_delete=True,individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda:current_read_history(1),outputs=current_history_outputs)
    return current_interface_blocks
