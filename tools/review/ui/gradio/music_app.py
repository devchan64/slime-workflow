"""음악생성 분류의 공용 Gradio 클라이언트. 모델은 진입점에서 고정한다."""
import argparse
from pathlib import Path
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
import gradio as gr
from generators.music.contracts import build_music_request, load_music_defaults, resolve_music_profile, validate_music_request
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_logs import build_execution_logs
from tools.review.common.generation_status_lookup import read_existing_generation_status
from tools.review.common.gradio_audio_results import render_audio_generation_result, describe_audio_generation_status


def describe_music_prompt(current_service_name,current_prompt_text,current_loop_value):
    current_default_record = load_music_defaults()
    current_final_prompt = current_prompt_text.strip()+' '+current_default_record['instrumental_suffix']
    if current_loop_value:
        current_final_prompt += ' '+current_default_record['loop_suffix']
    return f'원문 {len(current_prompt_text.split())}단어 · 추가 {len(current_final_prompt.split())-len(current_prompt_text.split())}단어 · 최종 {len(current_final_prompt.split())}단어',current_final_prompt.strip()


def build_music_interface(current_service_name,current_server_address):
    current_profile_record = resolve_music_profile(current_service_name)
    current_default_record = load_music_defaults()
    def execute_music_command(current_command_name,current_payload_record):
        return execute_remote_management_command(current_service_name,current_command_name,current_payload_record)
    with gr.Blocks(title=current_profile_record['label']+' 음악생성') as current_interface_blocks:
        gr.Markdown('## '+current_profile_record['label']+' · 음악생성\n게임 BGM 후보를 로컬 CUDA에서 생성합니다. 출력은 stereo WAV이며 MIDI는 생성하지 않습니다.')
        gr.Markdown(f"고정 모델: `{current_profile_record['model_id']}` · 기본 {current_default_record['duration_seconds']}초 · batch 1 · 8GB GPU 로딩 검증 완료, 음악 생성 피크는 별도 확인 필요\n\n[{current_profile_record['license_notice']}]({current_profile_record['license_url']})")
        current_model_status = gr.Markdown('모델 준비 상태 확인 중')
        current_prepare_button = gr.Button('모델 다운로드·준비')
        with gr.Column() as current_prepare_container:
            pass
        current_prompt_control = gr.Textbox(value=current_default_record['prompt'],label='장르·악기·분위기 프롬프트',lines=4,placeholder='예: Calm fantasy village music with flute and acoustic strings')
        current_prompt_reset = gr.Button('프롬프트 초기화',size='sm')
        current_prompt_reset.click(lambda:'',outputs=current_prompt_control,queue=False)
        with gr.Row():
            current_duration_control = gr.Number(value=current_default_record['duration_seconds'],minimum=5,maximum=current_profile_record['max_duration_seconds'],label='요청 길이(초)')
            current_seed_control = build_generation_seed(default_seed_value=current_default_record['seed'])
        current_loop_control = gr.Checkbox(value=current_default_record['loop_request'],label='반복 구조 요청 · 선택 사항, 이음새 없는 루프 보장 없음')
        gr.Markdown('반주는 프롬프트로 요청합니다. 보컬이 섞이거나 길이가 달라질 수 있으므로 결과를 청취하세요. 반복 구조 요청은 생성 문구를 추가하며 오디오를 자동 접합하지 않습니다.')
        current_prompt_counts,current_final_prompt = describe_music_prompt(current_service_name,current_default_record['prompt'],current_default_record['loop_request'])
        current_prompt_summary = gr.Markdown(current_prompt_counts)
        with gr.Accordion('최종 모델 입력 원문',open=False):
            current_final_control = gr.Textbox(value=current_final_prompt,interactive=False,label='최종 프롬프트',lines=4)
        def update_music_prompt(current_prompt_text,current_loop_value):
            return describe_music_prompt(current_service_name,current_prompt_text,current_loop_value)
        current_tag_control = gr.Textbox(label='이력 태그',max_lines=1)
        current_generate_button = gr.Button('음악 생성 · 대기열 등록',variant='primary',interactive=bool(current_default_record['prompt'].strip()))
        current_generate_notice = build_button_guidance(current_generate_button, '장르·악기·분위기 프롬프트를 입력하면 생성할 수 있습니다.')
        for current_prompt_source in (current_prompt_control,current_loop_control):
            current_prompt_source.change(update_music_prompt,[current_prompt_control,current_loop_control],[current_prompt_summary,current_final_control],queue=False)
        current_prompt_control.change(lambda current_prompt_text:'입력한 설정으로 생성 대기열에 등록합니다.' if current_prompt_text.strip() else '장르·악기·분위기 프롬프트를 입력하면 생성할 수 있습니다.',current_prompt_control,current_generate_notice,queue=False)
        with gr.Column() as current_generation_container:
            pass
        gr.Markdown('모델 준비가 없으면 생성 작업에서 먼저 준비합니다. 다운로드 권한·실행 환경 오류는 로그에 기록하며 다른 모델로 대체하지 않습니다.')
        current_job_control = gr.Textbox(label='생성 ID')
        current_status_display = gr.Markdown('실행 관측이 없으면 예상 시간은 계산 중으로 표시합니다.')
        current_result_display = gr.HTML('<p>생성 완료 후 오디오를 표시합니다.</p>')
        current_result_identity = gr.State('')
        current_log_output,current_log_refresh,_ = build_execution_logs()
        def start_music_generation(current_prompt_text,current_duration_value,current_seed_value,current_loop_value,current_tag_value):
            if type(current_seed_value) not in (int,float) or current_seed_value != int(current_seed_value):
                raise gr.Error('시드는 정수여야 합니다.')
            current_payload_record = {'action':'generate','prompt':current_prompt_text,'duration_seconds':current_duration_value,'seed':int(current_seed_value),'loop_request':current_loop_value,'tag':current_tag_value}
            build_music_request(current_service_name,current_payload_record)
            current_job_record = execute_music_command('generate',current_payload_record)
            return current_job_record['id'],'음악 생성 대기열에 등록했습니다.', '<p>새 작업의 결과를 기다립니다.</p>',''
        bind_gpu_generation_confirmation(current_generate_button,start_music_generation,[current_prompt_control,current_duration_control,current_seed_control,current_loop_control,current_tag_control],[current_job_control,current_status_display,current_result_display,current_result_identity],generation_confirmation_container=current_generation_container, generation_readiness_callback=lambda current_prompt_text: bool(current_prompt_text and current_prompt_text.strip()), generation_readiness_inputs=[current_prompt_control])
        def prepare_music_assets():
            current_job_record = execute_music_command('prepare',{'action':'prepare'})
            return current_job_record['id'],'모델 준비 대기열에 등록했습니다.','<p>모델 준비 작업입니다.</p>',''
        bind_gpu_generation_confirmation(current_prepare_button,prepare_music_assets,[],[current_job_control,current_status_display,current_result_display,current_result_identity],generation_confirmation_container=current_prepare_container)
        def refresh_music_result(current_job_identifier,current_logs_enabled,current_previous_result):
            if not current_job_identifier:
                return (gr.skip(),)*6
            current_status_record = read_existing_generation_status(execute_music_command,current_job_identifier)
            if current_status_record is None:
                return '선택한 작업 이력이 삭제되었습니다.','<p>생성 이력에서 다른 작업을 선택하세요.</p>','','',gr.skip(),''
            current_audio_identity = current_status_record.get('audio') or (current_job_identifier+':prepared' if current_status_record.get('result',{}).get('prepared') else '')
            current_model_message = execute_music_command('model-status',{})['message'] if current_audio_identity and current_audio_identity!=current_previous_result else gr.skip()
            return describe_audio_generation_status(current_status_record),render_audio_generation_result(current_job_identifier,current_status_record,current_server_address) if current_audio_identity and current_audio_identity!=current_previous_result else gr.skip(),current_status_record.get('log','') if current_logs_enabled else gr.skip(),current_audio_identity,current_model_message,gr.skip()
        current_refresh_timer = gr.Timer(5)
        current_refresh_timer.tick(refresh_music_result,[current_job_control,current_log_refresh,current_result_identity],[current_status_display,current_result_display,current_log_output,current_result_identity,current_model_status,current_job_control],queue=False,show_progress='hidden')
        def restore_music_inputs(current_history_record):
            from tools.review.common.gradio_reference_restore import validate_history_input_settings
            current_request_record = validate_history_input_settings(current_history_record)
            if current_request_record.get('action')!='generate':
                raise gr.Error('모델 준비 이력에는 음악 입력이 없습니다.')
            current_input_fields = ('prompt', 'duration_seconds', 'seed', 'loop_request', 'tag')
            if any(current_field_name not in current_request_record for current_field_name in current_input_fields):
                raise gr.Error('저장된 음악 생성 입력에 필수 설정이 없습니다.')
            current_request_record = validate_music_request(current_service_name, {
                'action': 'generate',
                **{current_field_name: current_request_record[current_field_name] for current_field_name in current_input_fields},
            })
            return current_request_record['prompt'],current_request_record['duration_seconds'],current_request_record['seed'],current_request_record['loop_request'],current_request_record['tag'],current_history_record['id']
        current_cleanup_scope = current_profile_record['label']+' · '+GENERATION_CLEANUP_SCOPE_TEXT
        current_read_history,current_history_outputs = build_generation_history_view(execute_music_command,current_server_address,current_cleanup_scope,
            restore_input_callback=restore_music_inputs,restore_output_components=[current_prompt_control,current_duration_control,current_seed_control,current_loop_control,current_tag_control,current_job_control],
            result_renderer_callback=render_audio_generation_result,record_folder_route='/'+current_service_name,allow_individual_delete=True,individual_delete_scope_text=current_cleanup_scope)
        current_interface_blocks.load(lambda:current_read_history(1),outputs=current_history_outputs)
        current_job_control.change(lambda:current_read_history(1),outputs=current_history_outputs,queue=False)
        current_interface_blocks.load(lambda:execute_music_command('active',{}).get('id') or '',outputs=current_job_control)
        current_interface_blocks.load(lambda:execute_music_command('model-status',{})['message'],outputs=current_model_status)
    return current_interface_blocks


def launch_music_interface(current_service_name):
    from tools.review.ui.gradio.management_menu_app import compose_management_interface
    current_argument_parser = argparse.ArgumentParser()
    current_argument_parser.add_argument('--port',type=int,required=True)
    current_argument_parser.add_argument('--review-port',type=int,required=True)
    current_argument_parser.add_argument('--owner-pid',type=int,required=True)
    current_argument_parser.add_argument('--root-path',required=True)
    current_argument_values = current_argument_parser.parse_args()
    compose_management_interface(build_music_interface(current_service_name,f'http://127.0.0.1:{current_argument_values.review_port}'),current_argument_values.review_port).queue().launch(
        server_name='127.0.0.1',server_port=current_argument_values.port,root_path=current_argument_values.root_path,allowed_paths=[])
