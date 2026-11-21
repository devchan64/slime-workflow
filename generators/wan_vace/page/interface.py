"""VACE-Fun 텍스트·외형 참조·첫 프레임 입력 화면."""
from pathlib import Path
from generators.wan_vace.page.inputs import VACE_INPUT_CHOICES, VACE_MODE_HELP_TEXT, build_vace_payload
import gradio as gr
from tools.review.common.gradio_generator_changelog import build_generator_changelog
from generators.wan_vace.contracts import VACE_DEFAULT_SETTINGS, VACE_JOB_STORAGE, VACE_MAXIMUM_SEED_VALUE
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_video_results import render_video_generation_result, describe_video_generation_status, describe_video_frame_duration
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT
from tools.review.common.gradio_reference_images import build_reference_image_inputs
from generators.wan_vace.page.video_preview import prepare_vace_browser_video

def describe_vace_mode(current_input_mode):
    if current_input_mode not in VACE_MODE_HELP_TEXT:
        raise ValueError('지원하지 않는 생성 모드')
    current_mode_description = VACE_MODE_HELP_TEXT[current_input_mode]
    if current_input_mode != 'text':
        current_mode_description += '\n\n참조 이미지는 비율을 유지해 832×480 흰 여백으로 맞춥니다. 원본은 보존하며, 여백도 영상 내용에 영향을 줄 수 있습니다.'
    return (current_mode_description,gr.update(visible=current_input_mode!='text'),
            gr.update(visible=current_input_mode=='pose'),gr.update(visible=current_input_mode in ('video_edit','video_condition')),
            gr.update(label='시작 장면 이미지 · 1장' if current_input_mode=='first_frame' else '캐릭터 외형 참조 · 1장'),gr.update(visible=current_input_mode=='video_edit'))


def select_vace_mode_inputs(current_input_values):
    current_selected_values = list(current_input_values)
    current_input_mode = current_selected_values[0]
    if current_input_mode == 'text': current_selected_values[1] = None
    if current_input_mode not in ('video_edit','video_condition'): current_selected_values[10:12] = [None,None]
    if current_input_mode == 'video_condition': current_selected_values[11] = None
    if current_input_mode != 'pose': current_selected_values[12] = None
    return current_selected_values


def check_visible_vace_readiness(current_model_ready,current_input_mode,current_reference_path,current_prompt_text,current_edit_video,current_edit_mask,current_pose_video):
    return check_vace_readiness(current_model_ready,current_input_mode,
        current_reference_path if current_input_mode!='text' else None,current_prompt_text,
        current_edit_video if current_input_mode in ('video_edit','video_condition') else None,
        current_edit_mask if current_input_mode=='video_edit' else None,
        current_pose_video if current_input_mode=='pose' else None)


def execute_vace_command(current_command_name, current_payload_record):
    return execute_remote_management_command('wan22-vace', current_command_name, current_payload_record)


def restore_vace_inputs(current_history_record):
    current_job_directory = (VACE_JOB_STORAGE/current_history_record['id']).resolve()
    if current_job_directory.parent != VACE_JOB_STORAGE.resolve():
        raise ValueError('이력 경로 오류')
    current_request_record = current_history_record['request']
    current_reference_path = None
    if current_request_record['references']:
        current_reference_file = (current_job_directory/current_request_record['references'][0]).resolve()
        if current_reference_file.parent != current_job_directory or not current_reference_file.is_file():
            raise ValueError('이력 입력 사본 누락 또는 경로 오류')
        current_reference_path = str(current_reference_file)
    return (current_request_record['mode'], current_reference_path, current_request_record['prompt'], current_request_record['negative_prompt'], current_request_record['frames'], current_request_record['seed'], current_request_record['steps'], current_request_record['flow_shift'], current_request_record['guidance_scale'], current_request_record['reference_strength'], str(current_job_directory/'edit-video.mp4') if current_request_record['mode'] in ('video_edit','video_condition') else None, str(current_job_directory/'edit-mask.mp4') if current_request_record['mode']=='video_edit' else None, prepare_vace_browser_video(current_job_directory/'pose-video.mp4') if current_request_record['mode']=='pose' else None, current_history_record['id'])


def check_vace_readiness(current_model_ready, current_input_mode, current_reference_path, current_prompt_text, current_edit_video=None, current_edit_mask=None, current_pose_video=None):
    if current_input_mode == 'pose':
        return bool(current_model_ready and current_prompt_text.strip() and current_reference_path and current_pose_video and not current_edit_video and not current_edit_mask)
    if current_pose_video:
        return False
    if current_input_mode == 'video_edit':
        return bool(current_model_ready and current_prompt_text.strip() and current_reference_path and current_edit_video and current_edit_mask)
    if current_input_mode == 'video_condition':
        return bool(current_model_ready and current_prompt_text.strip() and current_reference_path and current_edit_video and not current_edit_mask)
    if current_edit_video or current_edit_mask:
        return False
    return bool(current_model_ready and current_prompt_text and current_prompt_text.strip() and ((current_input_mode == 'text' and not current_reference_path) or (current_input_mode in ('reference', 'first_frame') and current_reference_path)))


def build_vace_interface(current_server_address, current_command_callback=None):
    current_execute_command = current_command_callback or execute_vace_command
    with gr.Blocks(title='Wan2.2 VACE-Fun 생성기') as current_interface_blocks:
        build_generator_changelog(current_interface_blocks, 'wan22-vace-generator')
        gr.Markdown('## Wan2.2 VACE-Fun A14B 생성기\n키모도 DWPose 영상과 캐릭터 참조 이미지로 동작을 따라 생성할 수 있습니다. 텍스트·이미지 생성도 지원합니다. 영상 부분 편집은 원본 MP4·흰색 편집 마스크·외형 참조를 함께 사용하며, 영상 전체 조건은 원본 MP4와 참조를 사용하는 별도 실험입니다.')
        current_model_ready = gr.State(False)
        current_model_status = gr.Markdown('모델 준비 상태 확인 중')
        from tools.review.common.gradio_model_download import build_model_progress_display
        build_model_progress_display(current_interface_blocks, 'wan22-vace')
        current_model_refresh = gr.Button('모델 준비 상태 확인')
        def read_vace_model_status():
            try:
                current_model_record = current_execute_command('model-status', {})
                return current_model_record['message'], current_model_record['ready']
            except Exception as current_status_error:
                return f'모델 상태 확인 실패: {current_status_error}', False
        current_refresh_event = current_model_refresh.click(read_vace_model_status, outputs=[current_model_status, current_model_ready], queue=False)
        current_model_load = current_interface_blocks.load(read_vace_model_status, outputs=[current_model_status, current_model_ready], queue=False, show_progress='hidden')
        current_mode_control = gr.Radio(choices=VACE_INPUT_CHOICES, value=VACE_DEFAULT_SETTINGS['mode'], label='생성 모드')
        current_mode_help = gr.Markdown(describe_vace_mode(VACE_DEFAULT_SETTINGS['mode'])[0])
        gr.Markdown('모드 전환 시 첨부값은 보관되며, 현재 모드에 표시되는 입력만 전송합니다. 입력을 준비한 뒤 **대기열에 추가 → 확인 후 대기열에 추가**를 누르세요.')
        current_reference_panel, current_reference_controls = build_reference_image_inputs(reference_image_mode='RGBA', reference_slot_count=1, reference_slot_labels=['외형 참조 또는 첫 프레임 · 1장'])
        current_reference_control = current_reference_controls[0]
        with gr.Group(visible=False) as current_pose_group:
            current_pose_video = gr.Video(sources=['upload'], label='키모도 DWPose MP4 · 832×480 · 16fps')
        with gr.Row(visible=False) as current_edit_group:
            current_edit_video = gr.Video(sources=['upload'], label='편집할 원본 MP4 · 832×480 · 16fps')
            current_edit_mask = gr.Video(sources=['upload'], label='마스크 MP4 · 흰색 재생성 / 검정 보존 조건')
        current_pose_video.upload(prepare_vace_browser_video, current_pose_video, current_pose_video, queue=False)
        current_mode_control.change(describe_vace_mode,current_mode_control,[current_mode_help,current_reference_panel,current_pose_group,current_edit_group,current_reference_control,current_edit_mask],queue=False)
        current_prompt_control = gr.Textbox(label='장면·동작 프롬프트', lines=3, placeholder='The character walks four steps. Full body, fixed camera.', info='주체 → 동작 → 카메라 순서로 짧게 작성하세요. 입력한 문구를 그대로 전달합니다. 걸음 수는 보장되지 않습니다.')
        current_prompt_summary = gr.Markdown('원문 0단어 · 최종 0단어 · 추가 문구 없음')
        current_prompt_control.change(lambda current_prompt_text: f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어 · 추가 문구 없음', current_prompt_control, current_prompt_summary, queue=False)
        with gr.Accordion('예시 목록 · 프롬프트와 생성 속성', open=False):
            gr.Markdown('''입력 참고용 실행 예시입니다. 참조 이미지는 직접 첨부하세요.

| 예시 | 양성 프롬프트 원문 | 단어 수 · 원문/최종 | 부정 프롬프트 | 입력 모드 | 해상도 | 프레임 / FPS | 스텝 | 시드 | CFG | Flow shift | 참조 강도 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 앞을 보며 같은 방향으로 걷기 | The character walks while looking ahead, maintaining the same heading. Show the full body. | 14 / 14 · 추가 문구 없음 | 없음 | 외형 참조 1장 (R2V) | 832×480 | 81 / 16 | 30 | 42 | 5 | 12 | 1 |

과거 Q4 예시 생성 ID: `2026-10-28_21-53-52-058bb9fb` · VACE-Fun A14B Q4_K_M · UMT5 BF16 비양자화 · Wan2.1 VAE · Euler/FlowMatch · 전문가 경계 0.875.
''')
        with gr.Accordion('부정 프롬프트', open=False):
            current_negative_control = gr.Textbox(label='부정 프롬프트', value='', info='필요한 제외 항목만 입력하세요. 자동으로 문구를 추가하지 않습니다.')
            current_negative_summary = gr.Markdown('원문 0단어 · 최종 0단어')
            current_negative_control.change(lambda current_prompt_text: f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_prompt_text.split())}단어', current_negative_control, current_negative_summary, queue=False)
        gr.Markdown('고정: VACE-Fun A14B 고·저노이즈 BF16 · UMT5 BF16 · Wan2.1 VAE · 832×480 · 16fps · Euler/FlowMatch · 전문가 경계 0.875 · AMD GPU 상주, CPU 오프로드 없음. LoRA는 사용하지 않습니다.')
        current_count_control = gr.Number(value=VACE_DEFAULT_SETTINGS['frames'], precision=0, minimum=5, maximum=129, step=4, label='출력 프레임', info='5~129의 4n+1. 81 초과는 장영상 실험 범위입니다. 로컬 기본 21장, 제작자 학습·예제는 81장/16fps. 프레임이 늘면 계산·메모리 요구량이 증가합니다.')
        current_duration_output = gr.Markdown(describe_video_frame_duration(VACE_DEFAULT_SETTINGS['frames']))
        current_count_control.change(describe_video_frame_duration, current_count_control, current_duration_output, queue=False)
        current_seed_control = build_generation_seed(default_seed_value=VACE_DEFAULT_SETTINGS['seed'], maximum_seed_value=VACE_MAXIMUM_SEED_VALUE)
        with gr.Group():
            gr.Markdown('### 고급 설정 · 설정값 안내')
            gr.Markdown('[모델카드](https://huggingface.co/alibaba-pai/Wan2.2-VACE-Fun-A14B)는 81프레임·16fps 학습과 포즈 등 제어 입력을 설명합니다. 아래 비교값은 [제작자의 제어 영상 + 참조 이미지 예제](https://github.com/aigc-apps/VideoX-Fun/blob/13bb3c625e8b1e457d7124d92207b49e00e4a6fe/examples/wan2.2_vace_fun/predict_v2v_control_ref.py)의 설정이며 모든 입력의 최적값이나 품질을 보장하지 않습니다. 값을 직접 바꾸며, 모드 전환 시 자동 적용하지 않습니다.')
            current_steps_control = gr.Number(value=VACE_DEFAULT_SETTINGS['steps'], precision=0, minimum=2, maximum=100, label='스텝', info='기본 20, 제작자 제어 예제 50. 반복 횟수이며 변경하면 시간과 결과가 달라집니다. 2스텝은 연결 확인용입니다.')
            current_shift_control = gr.Number(value=VACE_DEFAULT_SETTINGS['flow_shift'], minimum=0.1, maximum=20, label='Flow shift', info='제작자 제어 예제 12. 이 도구의 Euler/FlowMatch 노이즈 시간 배분에 적용됩니다.')
            current_guidance_control = gr.Number(value=VACE_DEFAULT_SETTINGS['guidance_scale'], minimum=1, maximum=10, label='CFG', info='제작자 제어 예제 5. 프롬프트 유도 강도이며 1은 classifier-free guidance를 사용하지 않습니다.')
            current_strength_control = gr.Number(value=VACE_DEFAULT_SETTINGS['reference_strength'], minimum=0.1, maximum=2, label='VACE 조건 강도', info='제작자 제어 예제 1. 제어 영상과 참조 등을 포함한 VACE 조건 전체에 적용하며 외형 참조 전용 강도가 아닙니다.')
            gr.Markdown('**검증 범위:** 공식 VideoX-Fun과 비양자화 BF16 가중치를 사용합니다. AMD GPU에서 포즈 65프레임·20스텝 생성과 수치 검사를 확인했습니다. 다른 입력의 결과 품질은 별도 검수해야 합니다.\n\n[모델카드](https://huggingface.co/alibaba-pai/Wan2.2-VACE-Fun-A14B) · [제작자 외형 참조 예제](https://github.com/aigc-apps/VideoX-Fun/blob/13bb3c625e8b1e457d7124d92207b49e00e4a6fe/examples/wan2.2_vace_fun/predict_s2v.py) · [제작자 첫 프레임 예제](https://github.com/aigc-apps/VideoX-Fun/blob/13bb3c625e8b1e457d7124d92207b49e00e4a6fe/examples/wan2.2_vace_fun/predict_i2v.py)')
        current_input_controls = [current_mode_control,current_reference_control,current_prompt_control,current_negative_control,current_count_control,current_seed_control,current_steps_control,current_shift_control,current_guidance_control,current_strength_control,current_edit_video,current_edit_mask,current_pose_video]
        current_generate_button = gr.Button('대기열에 추가', variant='primary', interactive=False)
        build_button_guidance(current_generate_button, '모델 준비 상태를 확인하고 모드별 안내에 표시된 필수 첨부와 프롬프트를 입력하세요.')
        with gr.Column() as current_confirmation_container:
            pass
        current_job_control = gr.Textbox(value='', visible=False)
        current_status_output = gr.Markdown('입력을 준비하세요.')
        def enqueue_vace_generation(*current_input_values):
            current_job_record = current_execute_command('generate', build_vace_payload(*select_vace_mode_inputs(current_input_values)))
            return current_job_record['id'], '공용 GPU 대기열에 등록했습니다.'
        bind_gpu_generation_confirmation(current_generate_button, enqueue_vace_generation, current_input_controls, [current_job_control,current_status_output], generation_confirmation_container=current_confirmation_container, generation_readiness_callback=check_visible_vace_readiness, generation_readiness_inputs=[current_model_ready,current_mode_control,current_reference_control,current_prompt_control,current_edit_video,current_edit_mask,current_pose_video], generation_readiness_events=[current_refresh_event,current_model_load])
        current_read_history,current_history_outputs = build_generation_history_view(current_execute_command,current_server_address,GENERATION_CLEANUP_SCOPE_TEXT,restore_input_callback=restore_vace_inputs,restore_output_components=[*current_input_controls,current_job_control],result_renderer_callback=render_video_generation_result,record_folder_route='/wan22-vace',allow_individual_delete=True,individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT, observed_job_control=current_job_control, status_formatter_callback=describe_video_generation_status,history_deep_link_interface=current_interface_blocks)
        def load_vace_history_initially():
            try:
                return current_read_history(1)
            except (ValueError, RuntimeError, OSError) as current_history_error:
                return [gr.skip(), f'이력 조회 실패: {current_history_error} · 새로고침으로 다시 시도하세요.', *[gr.skip() for _ in range(len(current_history_outputs)-2)]]
        current_interface_blocks.load(load_vace_history_initially,outputs=current_history_outputs,queue=False,show_progress='hidden')
    return current_interface_blocks
