"""음악생성 분류의 공용 Gradio 클라이언트. 모델은 진입점에서 고정한다."""
import argparse
import math
from pathlib import Path
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
import gradio as gr
from generators.music.contracts import build_music_request, load_music_defaults, resolve_music_profile, validate_music_request, resolve_audio_minimum, convert_minimax_token_duration, MINIMAX_AUDIO_FRAME_RATE
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_logs import build_execution_logs
from tools.review.common.generation_status_lookup import read_existing_generation_status
from tools.review.common.gradio_audio_results import render_audio_generation_result, describe_audio_generation_status


def describe_music_prompt(current_service_name,current_prompt_text,current_loop_value,current_legacy_value=True):
    current_default_record = load_music_defaults(current_service_name)
    current_final_prompt = current_prompt_text.strip()
    if current_legacy_value:
        current_final_prompt += ' '+current_default_record['instrumental_suffix']
    if current_service_name == 'sfx-dasheng-audiogen':
        current_final_prompt = current_final_prompt.strip()
    if current_loop_value:
        current_final_prompt += ' '+current_default_record['loop_suffix']
    if current_service_name == 'sfx-dasheng-audiogen':
        current_final_prompt = '<|caption|> '+current_final_prompt.strip()
    return f'원문 {len(current_prompt_text.split())}단어 · 추가 {len(current_final_prompt.split())-len(current_prompt_text.split())}단어 · 최종 {len(current_final_prompt.split())}단어',current_final_prompt.strip()


def build_music_interface(current_service_name,current_server_address):
    current_profile_record = resolve_music_profile(current_service_name)
    current_default_record = load_music_defaults(current_service_name)
    current_effects_mode = current_service_name == 'sfx-dasheng-audiogen'
    current_content_label = '효과음' if current_effects_mode else '음악'
    current_prompt_label = '소리·재질·동작 설명' if current_effects_mode else '장르·악기·분위기 프롬프트'
    current_content_description = '짧은 게임 효과음과 환경음 후보를 로컬 CUDA에서 생성합니다. 출력은 16kHz mono PCM16 WAV입니다.' if current_effects_mode else '게임 BGM 후보를 로컬 CUDA에서 생성합니다. 출력은 stereo WAV이며 MIDI는 생성하지 않습니다.'
    current_hardware_notice = '25스텝 · CUDA BF16 · 길이는 모델 자동 예측 · 실제 VRAM 피크·음질은 생성 후 확인' if current_effects_mode else '8GB GPU 로딩 검증 완료, 음악 생성 피크는 별도 확인 필요'
    def execute_music_command(current_command_name,current_payload_record):
        return execute_remote_management_command(current_service_name,current_command_name,current_payload_record)
    with gr.Blocks(title=current_profile_record['label']+' '+current_content_label+' 생성') as current_interface_blocks:
        gr.Markdown('## '+current_profile_record['label']+' · '+current_content_label+' 생성\n'+current_content_description)
        gr.Markdown(f"고정 모델: `{current_profile_record['model_id']}` · {('길이 자동 예측' if current_effects_mode else '최대 생성 길이 기본값 '+str(current_default_record['duration_seconds'])+'초')} · batch 1 · {current_hardware_notice}\n\n[{current_profile_record['license_notice']}]({current_profile_record['license_url']})")
        current_model_status = gr.Markdown('모델 준비 상태 확인 중')
        current_prepare_button = gr.Button('모델 다운로드·준비')
        with gr.Column() as current_prepare_container:
            pass
        current_prompt_control = gr.Textbox(value=current_default_record['prompt'],label=current_prompt_label,lines=4,placeholder='영어로 원하는 소리와 동작을 설명하세요.' if current_effects_mode else '예: Calm fantasy village music with flute and acoustic strings')
        current_lyrics_control = gr.State(None) if current_effects_mode else gr.Textbox(value='[Instrumental]',label='lyrics · 가사 / 구간 태그',lines=6,info='반주는 [Instrumental]. 보컬은 [verse], [chorus]와 가사를 입력하세요. 프롬프트의 보컬 지시와 일치시켜 주세요.')
        current_legacy_control = gr.State(True) if current_effects_mode else gr.Checkbox(value=False,label='이전 방식: 반주 문구 자동 추가·가사 고정',info='예제 입력은 해제합니다. 이전 이력을 불러오면 해당 방식이 복원됩니다.')
        current_prompt_reset = gr.Button('프롬프트 초기화',size='sm')
        current_prompt_reset.click(lambda:'',outputs=current_prompt_control,queue=False)
        with gr.Row():
            current_length_control = gr.State(None) if current_effects_mode else gr.Number(value=current_default_record['duration_seconds']*MINIMAX_AUDIO_FRAME_RATE,minimum=resolve_audio_minimum(current_service_name)*MINIMAX_AUDIO_FRAME_RATE,maximum=current_profile_record['max_duration_seconds']*MINIMAX_AUDIO_FRAME_RATE,step=1,label='max_new_tokens · 최대 오디오 프레임 수',info='125~3,000 정수. 25개≈1초이며 조기 종료할 수 있습니다.')
            if not current_effects_mode:
                current_duration_display = gr.Number(value=current_default_record['duration_seconds'],label='환산 최대 생성 길이(초)',interactive=False)
                def update_minimax_duration(current_token_value):
                    if type(current_token_value) not in (int,float) or not math.isfinite(current_token_value) or current_token_value != int(current_token_value):
                        raise gr.Error('max_new_tokens는 정수여야 합니다.')
                    return convert_minimax_token_duration(int(current_token_value))
                current_length_control.change(update_minimax_duration,current_length_control,current_duration_display,queue=False)
            current_seed_control = build_generation_seed(default_seed_value=current_default_record['seed'])
        if not current_effects_mode:
            gr.Markdown('**길이 입력 가이드** · 250 ≈ 10초 · 750 ≈ 30초 · 1,500 ≈ 60초 · 3,000 ≈ 120초\n\n여기서 토큰은 프롬프트 단어 수가 아니라 오디오 프레임 상한입니다. 현재 관리도구는 8GB 로컬 운영 범위를 5~120초로 제한합니다. 값이 커지면 최대 연산량이 늘지만 정확한 길이나 최소 길이를 보장하지 않습니다. 종료 토큰이 나오면 먼저 끝납니다. 로컬 Diffusers에는 `max_new_tokens ÷ 25`를 `audio_duration`으로 전달하며, 저장 이력도 환산 초를 사용합니다. 공식 모델 한도와 이 관리도구의 운영 한도는 다릅니다.')
        current_minimum_control = gr.State(0) if current_effects_mode else gr.Number(value=0,minimum=0,maximum=current_profile_record['max_duration_seconds'],label='실험 · 최소 생성 길이(초)',info='0은 해제. 예: 최소 50초 / 상한 1500프레임(60초). 종료 토큰을 후보에서 제외하여 계속 생성하며 반복·음질 저하 가능성이 있습니다. 기존 이력에는 자동 적용하지 않습니다.')
        current_loop_control = gr.Checkbox(value=False if not current_effects_mode else current_default_record['loop_request'],label='반복 구조 요청 · 선택 사항, 이음새 없는 루프 보장 없음')
        gr.Markdown('영어 프롬프트를 권장합니다. 반복 요청은 환경음 문구를 추가하며 이음새 없는 루프를 보장하지 않습니다. 길이는 모델이 예측하며 초 단위 지정은 지원하지 않습니다.' if current_effects_mode else 'prompt는 음악 설명, lyrics는 가사·구간 태그입니다. 자동 문구 추가와 반복 요청을 모두 해제하면 입력한 설명을 그대로 전달합니다. 최대 생성 길이를 60초로 설정해도 모델이 먼저 종료하면 더 짧게 생성됩니다. 보컬 미포함은 보장되지 않으므로 결과를 청취하세요. 반복 구조 요청은 프롬프트 문구를 추가하는 옵션이며, 별도 루프 파라미터나 자동 접합 기능이 아닙니다.')
        current_prompt_counts,current_final_prompt = describe_music_prompt(current_service_name,current_default_record['prompt'],current_default_record['loop_request'] if current_effects_mode else False,current_effects_mode)
        current_prompt_summary = gr.Markdown(current_prompt_counts)
        with gr.Accordion('최종 모델 입력 원문',open=False):
            current_final_control = gr.Textbox(value=current_final_prompt,interactive=False,label='최종 프롬프트',lines=4)
            if not current_effects_mode:
                current_final_lyrics = gr.Textbox(value='[Instrumental]',label='최종 lyrics',interactive=False,lines=4)
                current_lyrics_summary = gr.Markdown('가사 입력 1단어 · 최종 lyrics 1단어')
                def update_music_lyrics(current_lyrics_text,current_legacy_value):
                    current_final_lyrics = '[Instrumental]' if current_legacy_value else current_lyrics_text
                    return current_final_lyrics,f'가사 입력 {len(current_lyrics_text.split())}단어 · 최종 lyrics {len(current_final_lyrics.split())}단어'
                for current_lyrics_source in (current_lyrics_control,current_legacy_control):
                    current_lyrics_source.change(update_music_lyrics,[current_lyrics_control,current_legacy_control],[current_final_lyrics,current_lyrics_summary],queue=False)
                gr.Markdown('최종 프롬프트는 `prompt`, 가사 입력은 `lyrics`, 최대 생성 길이는 `audio_duration`으로 전달합니다. 시드는 난수 생성기에 적용하며 이력 태그는 모델에 전달하지 않습니다.')
        def update_music_prompt(current_prompt_text,current_loop_value,current_legacy_value):
            return describe_music_prompt(current_service_name,current_prompt_text,current_loop_value,current_legacy_value)
        current_tag_control = gr.Textbox(label='이력 태그',max_lines=1)
        current_generate_button = gr.Button('대기열에 추가',variant='primary',interactive=bool(current_default_record['prompt'].strip()))
        current_generate_notice = build_button_guidance(current_generate_button, current_prompt_label+'을 입력하면 생성할 수 있습니다.')
        for current_prompt_source in (current_prompt_control,current_loop_control,current_legacy_control):
            current_prompt_source.change(update_music_prompt,[current_prompt_control,current_loop_control,current_legacy_control],[current_prompt_summary,current_final_control],queue=False)
        current_prompt_control.change(lambda current_prompt_text:'입력한 설정으로 생성 대기열에 등록합니다.' if current_prompt_text.strip() else current_prompt_label+'을 입력하면 생성할 수 있습니다.',current_prompt_control,current_generate_notice,queue=False)
        with gr.Column() as current_generation_container:
            pass
        gr.Markdown('모델 준비가 없으면 생성 작업에서 먼저 준비합니다. 다운로드 권한·실행 환경 오류는 로그에 기록하며 다른 모델로 대체하지 않습니다.')
        current_job_control = gr.Textbox(label='생성 ID')
        current_status_display = gr.Markdown('실행 관측이 없으면 예상 시간은 계산 중으로 표시합니다.')
        current_result_display = gr.HTML('<p>생성 완료 후 오디오를 표시합니다.</p>')
        current_result_identity = gr.State('')
        current_log_output,current_log_refresh,_ = build_execution_logs()
        def start_music_generation(current_prompt_text,current_duration_value,current_seed_value,current_loop_value,current_tag_value,current_minimum_value=0,current_lyrics_text='[Instrumental]',current_legacy_value=True):
            if type(current_seed_value) not in (int,float) or current_seed_value != int(current_seed_value):
                raise gr.Error('시드는 정수여야 합니다.')
            current_payload_record = {'action':'generate','prompt':current_prompt_text,'duration_seconds':current_duration_value,'seed':int(current_seed_value),'loop_request':current_loop_value,'tag':current_tag_value}
            if not current_effects_mode:
                if type(current_duration_value) not in (int,float) or not math.isfinite(current_duration_value) or current_duration_value != int(current_duration_value):
                    raise gr.Error('max_new_tokens는 정수여야 합니다.')
                if not current_legacy_value:
                    current_payload_record['lyrics'] = current_lyrics_text
                current_payload_record.pop('duration_seconds')
                current_payload_record['max_new_tokens'] = int(current_duration_value)
            if current_minimum_value:
                current_payload_record['min_duration_seconds'] = current_minimum_value
            build_music_request(current_service_name,current_payload_record)
            current_job_record = execute_music_command('generate',current_payload_record)
            return current_job_record['id'],current_content_label+' 생성 대기열에 등록했습니다.', '<p>새 작업의 결과를 기다립니다.</p>',''
        bind_gpu_generation_confirmation(current_generate_button,start_music_generation,[current_prompt_control,current_length_control,current_seed_control,current_loop_control,current_tag_control,current_minimum_control,current_lyrics_control,current_legacy_control],[current_job_control,current_status_display,current_result_display,current_result_identity],generation_confirmation_container=current_generation_container, generation_readiness_callback=lambda current_prompt_text: bool(current_prompt_text and current_prompt_text.strip()), generation_readiness_inputs=[current_prompt_control])
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
                **({'lyrics':current_request_record['lyrics']} if 'lyrics' in current_request_record else {}),
                'action': 'generate',
                'min_duration_seconds':current_request_record.get('min_duration_seconds',0),
                **{current_field_name: current_request_record[current_field_name] for current_field_name in current_input_fields},
            })
            return current_request_record['prompt'],(None if current_effects_mode else int(current_request_record['duration_seconds']*MINIMAX_AUDIO_FRAME_RATE)),current_request_record['seed'],current_request_record['loop_request'],current_request_record['tag'],current_history_record['id'],current_request_record.get('min_duration_seconds',0),current_request_record.get('lyrics','[Instrumental]'),'lyrics' not in current_request_record
        current_cleanup_scope = current_profile_record['label']+' · '+GENERATION_CLEANUP_SCOPE_TEXT
        current_read_history,current_history_outputs = build_generation_history_view(execute_music_command,current_server_address,current_cleanup_scope,
            restore_input_callback=restore_music_inputs,restore_output_components=[current_prompt_control,current_length_control,current_seed_control,current_loop_control,current_tag_control,current_job_control,current_minimum_control,current_lyrics_control,current_legacy_control],
            result_renderer_callback=render_audio_generation_result,record_folder_route='/'+current_service_name,allow_individual_delete=True,individual_delete_scope_text=current_cleanup_scope,show_thumbnail_column=False)
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
