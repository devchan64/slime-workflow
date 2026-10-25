"""음악생성 분류의 공용 Gradio 클라이언트. 모델은 진입점에서 고정한다."""
import argparse
from pathlib import Path
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
import gradio as gr
from generators.music.contracts import build_music_request, load_music_defaults, resolve_music_profile, validate_music_request, resolve_audio_minimum, MINIMAX_AUDIO_FRAME_RATE
from generators.music.examples import load_music_examples, resolve_music_example
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


def load_instrumental_example(current_example_identifier='iseulon-bgm',current_service_name='music-minimax'):
    """선택한 예제의 입력값만 반환하며 실행하지 않는다."""
    current_example_record = resolve_music_example(current_example_identifier,current_service_name)['request']
    return (current_example_record['prompt'],current_example_record['lyrics'],current_example_record['duration_seconds'],
            current_example_record['seed'],current_example_record['loop_request'],current_example_record['min_duration_seconds'],False)


def preview_music_example(current_example_identifier,current_service_name='music-minimax'):
    current_example_record = resolve_music_example(current_example_identifier,current_service_name)
    current_request_record = current_example_record['request']
    current_summary_text = (current_example_record['description']+f"\n\n상한 {current_request_record['duration_seconds']}초 · 시드 {current_request_record['seed']} · 반복 요청 {current_request_record['loop_request']} · 최소 길이 {current_request_record['min_duration_seconds']}초"
                            +f"\n\n출처 작업: `{current_example_record['source_generation_id']}` · 원문/최종 prompt {len(current_request_record['prompt'].split())}단어 · lyrics {len(current_request_record['lyrics'].split())}단어")
    if current_service_name == 'music-heartmula':
        current_summary_text = current_example_record['description']+f"\n\n출력 상한 {current_request_record['duration_seconds']}초 · 시드 {current_request_record['seed']} · 가사 {len(current_request_record['lyrics'].split())}단어"
    return current_summary_text,current_request_record['prompt'],current_request_record['lyrics']


def build_music_interface(current_service_name,current_server_address):
    current_profile_record = resolve_music_profile(current_service_name)
    current_default_record = load_music_defaults(current_service_name)
    current_effects_mode = current_service_name == 'sfx-dasheng-audiogen'
    current_minimax_mode = current_service_name == 'music-minimax'
    current_heartmula_mode = current_service_name == 'music-heartmula'
    current_magenta_mode = current_service_name in ('music-magenta','music-heartmula')
    current_content_label = '효과음' if current_effects_mode else '음악'
    current_prompt_label = '소리·재질·동작 설명' if current_effects_mode else '음악 설명 · prompt'
    current_content_description = '짧은 게임 효과음과 환경음 후보를 로컬 CUDA에서 생성합니다. 출력은 16kHz mono PCM16 WAV입니다.' if current_effects_mode else '게임 BGM 후보를 로컬 CUDA에서 생성합니다. 출력은 stereo WAV이며 MIDI는 생성하지 않습니다.'
    current_hardware_notice = '25스텝 · CUDA BF16 · 길이는 모델 자동 예측 · 실제 VRAM 피크·음질은 생성 후 확인' if current_effects_mode else '8GB GPU 로딩 검증 완료, 음악 생성 피크는 별도 확인 필요'
    if current_magenta_mode:
        current_hardware_notice = 'ONNX CUDA 인코더·JAX 생성·디코더 검증 완료 · 5초 관측 피크 5974MiB'
        current_content_description = 'Magenta RT2 Small(230M) 반주 실험 입력 화면입니다. 출력 목표는 48kHz stereo WAV입니다. 허밍·보컬 미포함과 자연스러운 종결은 보장하지 않습니다.'
    if current_heartmula_mode:
        current_prompt_label = '음악 태그 · tags (쉼표로 구분)'
        current_content_description = 'HeartMuLa로 가사가 있는 음악을 생성하고 Demucs로 MR을 분리합니다. 두 모델을 8GB CUDA에서 순차 실행하며, 원곡과 MR을 함께 확인할 수 있습니다.'
        current_hardware_notice = 'HeartCodec FP32 · 생성 모델 NF4/BF16 · CUDA 순차 로드 · 실제 준비 상태는 아래 표시'
    def execute_music_command(current_command_name,current_payload_record):
        return execute_remote_management_command(current_service_name,current_command_name,current_payload_record)
    with gr.Blocks(title=current_profile_record['label']+' '+current_content_label+' 생성') as current_interface_blocks:
        gr.Markdown('## '+current_profile_record['label']+' · '+current_content_label+' 생성\n'+current_content_description)
        if current_heartmula_mode:
            gr.Markdown('**HeartMuLa 3B**: 태그·가사로 원곡 생성 → **Demucs htdemucs**: 보컬·MR 분리 → **WAV + 320kbps MP3** 저장.\n\n'
                        '**사용 순서** · 예제 불러오기 → 입력 확인 → 대기열 등록 → 완료 이력에서 원곡·MR 비교')
            with gr.Accordion('두 모델 소개 · 실행 방식과 품질 안내',open=False):
                gr.Markdown(f"**HeartMuLa** · `{current_profile_record['model_id']}` · [모델 카드]({current_profile_record['license_url']})\n\n"
                            '**Demucs** · `htdemucs`, 4.0.1 · [공식 저장소](https://github.com/facebookresearch/demucs)\n\n'
                            '두 모델은 CUDA에서 순차 실행합니다. MR에는 보컬 잔향이나 악기 손실이 생길 수 있습니다. '
                            '최대 출력 시간은 상한이며 자연스러운 끝맺음이나 정확한 길이를 보장하지 않습니다.')
        gr.Markdown(f"고정 모델: `{current_profile_record['model_id']}` · {('길이 자동 예측' if current_effects_mode else '최대 생성 길이 기본값 '+str(current_default_record['duration_seconds'])+'초')} · batch 1 · {current_hardware_notice}\n\n[{current_profile_record['license_notice']}]({current_profile_record['license_url']})")
        current_model_status = gr.Markdown('모델 준비 상태 확인 중')
        with gr.Accordion('모델 준비 · 다운로드 / 재점검',open=False):
            current_prepare_button = gr.Button('준비 파일 재점검' if current_magenta_mode and not current_heartmula_mode else '모델 다운로드·준비',interactive=not current_heartmula_mode)
            if current_heartmula_mode:
                gr.Markdown('가사가 있는 원곡을 생성한 뒤 Demucs로 MR·보컬을 분리합니다. 원곡과 분리 파일을 모두 보존합니다. 생성은 GPU 검증 완료 및 tags·lyrics 직접 입력 후 활성화됩니다.')
            elif current_magenta_mode:
                gr.Markdown('GPU 실험 경로: ONNX 변환 인코더와 공식 JAX Small을 사용합니다. 원본 TFLite와 수치 동등성은 미검증입니다. 시드는 스타일 매퍼에 적용하며 음악 샘플러 시드는 공식 구현의 0으로 고정됩니다.')
            with gr.Column() as current_prepare_container:
                pass
        if current_minimax_mode or current_heartmula_mode:
            current_example_records = load_music_examples(current_service_name)
            with gr.Accordion('예제 프롬프트 목록',open=current_heartmula_mode):
                current_example_selector = gr.Dropdown(choices=[(current_example_record['label'],current_example_record['id']) for current_example_record in current_example_records],value=current_example_records[0]['id'],label='예제 선택',allow_custom_value=False)
                current_example_preview = preview_music_example(current_example_records[0]['id'],current_service_name)
                current_example_summary = gr.Markdown(current_example_preview[0])
                with gr.Accordion('예제 원문 미리보기',open=False):
                    current_example_prompt = gr.Textbox(value=current_example_preview[1],label='예제 음악 설명 · 읽기 전용',lines=4,interactive=False)
                    current_example_lyrics = gr.Textbox(value=current_example_preview[2],label='예제 가사·태그 · 읽기 전용',lines=6,interactive=False)
                current_example_selector.change(lambda current_example_identifier: preview_music_example(current_example_identifier,current_service_name),current_example_selector,[current_example_summary,current_example_prompt,current_example_lyrics],queue=False)
                current_example_button = gr.Button('선택한 예제를 폼에 불러오기')
                gr.Markdown('불러오기는 태그·가사·출력 상한·시드를 바꿉니다. 기존 입력은 덮어쓰며 생성은 실행하지 않습니다.' if current_heartmula_mode else '목록 선택은 미리보기만 바꿉니다. 불러오기는 음악 설명·가사·길이·시드·반복·최소 길이를 덮어쓰며 생성은 실행하지 않습니다.')
        current_prompt_control = gr.Textbox(value=current_default_record['prompt'],label=current_prompt_label,lines=4,placeholder='예: piano,harp,flute,acoustic,peaceful,female vocals' if current_heartmula_mode else '영어로 원하는 소리와 동작을 설명하세요.' if current_effects_mode else '예: Calm fantasy village music with flute and acoustic strings')
        current_vocal_draft = gr.State('')
        current_vocal_control = gr.State('반주') if not current_minimax_mode else gr.Radio(choices=['반주','보컬'],value='반주',label='음악 유형',info='반주는 가창 없이 생성합니다. 보컬은 가사를 입력하고 음악 설명에도 원하는 목소리를 적어 주세요.')
        current_lyrics_control = gr.Textbox(value='',label='가사·구간 태그 · lyrics',lines=6,info='예제를 불러오거나 직접 작성하세요. [Verse], [Chorus], [Outro] 아래에 가사를 입력합니다. MR도 먼저 가사곡을 생성한 뒤 분리합니다.') if current_heartmula_mode else gr.State(None) if not current_minimax_mode else gr.Textbox(value='[Instrumental]',label='가사·구간 구성 · lyrics',lines=6,interactive=False,info='반주는 [Instrumental]. 보컬은 [verse], [chorus]와 가사를 입력하세요. 프롬프트의 보컬 지시와 일치시켜 주세요.')
        current_prompt_reset = gr.Button('음악 설명만 비우기' if not current_effects_mode else '프롬프트 초기화',size='sm')
        current_prompt_reset.click(lambda:'',outputs=current_prompt_control,queue=False)
        with gr.Row():
            current_length_control = gr.State(None) if current_effects_mode else gr.Number(value=current_default_record['duration_seconds'],minimum=resolve_audio_minimum(current_service_name),maximum=current_profile_record['max_duration_seconds'],label='최대 출력 시간(초) · max_audio_length_ms 환산' if current_heartmula_mode else '생성 길이(초)' if current_magenta_mode else 'audio_duration · 최대 생성 길이(초)',info='5~240초. 완결 길이가 아닌 최대 오디오 출력 상한입니다.' if current_heartmula_mode else '5~120초 실험 입력. 자연스러운 종결은 보장하지 않습니다.' if current_magenta_mode else '5~120초. 선택한 예제의 상한을 확인하세요. 종료 토큰이 나오면 먼저 끝날 수 있습니다.')
            if current_minimax_mode:
                current_duration_display = gr.Number(value=current_default_record['duration_seconds']*MINIMAX_AUDIO_FRAME_RATE,label='환산 오디오 프레임 상한 · max_new_tokens',interactive=False)
                def update_minimax_duration(current_duration_value):
                    current_validated_request = validate_music_request(current_service_name,{'prompt':'preview','duration_seconds':current_duration_value})
                    return int(current_validated_request['duration_seconds']*MINIMAX_AUDIO_FRAME_RATE)
                current_length_control.change(update_minimax_duration,current_length_control,current_duration_display,queue=False)
            current_seed_control = build_generation_seed(default_seed_value=current_default_record['seed'])
        if current_minimax_mode:
            gr.Markdown('**예제 입력** · 음악 설명은 prompt, 가사·구간 태그는 lyrics에 입력합니다. 예제 목록에서 원문과 길이·시드를 확인한 뒤 불러오세요.\n\n길이는 `audio_duration`으로 전달합니다. 30초=750프레임, 60초=1,500프레임, 120초=3,000프레임이며 실제 길이를 보장하지 않습니다.')
        with gr.Accordion('고급 설정 · 이전 입력 호환 / 길이 실험',open=False,visible=not current_magenta_mode):
            current_legacy_control = gr.State(True) if not current_minimax_mode else gr.Checkbox(value=False,label='이전 방식: 반주 문구 자동 추가·가사 고정',info='예제 입력은 해제합니다. 이전 이력을 불러오면 해당 방식이 복원됩니다.')
            current_minimum_control = gr.State(0) if not current_minimax_mode else gr.Number(value=0,minimum=0,maximum=current_profile_record['max_duration_seconds'],label='실험 · 최소 생성 길이(초)',info='0은 해제. 예: 최소 50초 / 상한 1500프레임(60초). 종료 토큰을 억제합니다. 이전 실험에서 긴 무음이 발생했으므로 기본값 0을 권장합니다. 기존 이력에는 자동 적용하지 않습니다.')
        current_loop_control = gr.State(False) if current_magenta_mode else gr.Checkbox(value=False if not current_effects_mode else current_default_record['loop_request'],label='반복 구조 요청 · 선택 사항, 이음새 없는 루프 보장 없음')
        gr.Markdown('공식 입력: 쉼표 구분 tags와 lyrics. 시간은 밀리초 상한으로 환산하며 완결된 곡 길이를 보장하지 않습니다. 고정값: topk 50, temperature 1.0, cfg_scale 3.0. EOS가 나오면 먼저 종료하고, 시간 상한에 도달하면 곡 중간에도 종료합니다. [Instrumental]을 자동 삽입하지 않습니다.' if current_heartmula_mode else 'Magenta 실험: 음악 설명·길이·시드만 사용합니다. 반복 지시와 음량 후처리는 적용하지 않습니다. 127 SentencePiece 토큰을 초과하면 오류로 종료합니다. 지정 길이에서 스트리밍을 종료하므로 자연스러운 종결은 보장하지 않습니다.' if current_magenta_mode else '영어 프롬프트를 권장합니다. 반복 요청은 환경음 문구를 추가하며 이음새 없는 루프를 보장하지 않습니다. 길이는 모델이 예측하며 초 단위 지정은 지원하지 않습니다.' if current_effects_mode else 'prompt는 음악 설명, lyrics는 가사·구간 태그입니다. 자동 문구 추가와 반복 요청을 모두 해제하면 입력한 설명을 그대로 전달합니다. 최대 생성 길이를 60초로 설정해도 모델이 먼저 종료하면 더 짧게 생성됩니다. 보컬 미포함은 보장되지 않으므로 결과를 청취하세요. 반복 구조 요청은 프롬프트 문구를 추가하는 옵션이며, 별도 루프 파라미터나 자동 접합 기능이 아닙니다.')
        if current_minimax_mode:
            def switch_music_vocals(current_vocal_mode,current_saved_draft):
                if current_vocal_mode not in ('반주','보컬'):
                    raise gr.Error('반주 또는 보컬을 선택하세요.')
                return gr.update(value='[Instrumental]' if current_vocal_mode=='반주' else current_saved_draft,interactive=current_vocal_mode=='보컬'),False
            def synchronize_music_vocals(current_lyrics_text,current_saved_draft,current_legacy_value):
                current_instrumental_mode = current_legacy_value or current_lyrics_text.strip().lower() == '[instrumental]'
                return ('반주' if current_instrumental_mode else '보컬',
                        current_saved_draft if current_instrumental_mode else current_lyrics_text,
                        gr.update(interactive=not current_instrumental_mode,info='반주 모드: [Instrumental]을 전달합니다. 보컬을 선택하면 작성한 가사를 다시 편집할 수 있습니다.' if current_instrumental_mode else '[verse], [chorus]는 별도 줄에 쓰고 다음 줄에 가사를 입력하세요.'))
            current_vocal_control.input(switch_music_vocals,[current_vocal_control,current_vocal_draft],[current_lyrics_control,current_legacy_control],queue=False)
            for current_mode_source in (current_lyrics_control,current_legacy_control):
                current_mode_source.change(synchronize_music_vocals,[current_lyrics_control,current_vocal_draft,current_legacy_control],[current_vocal_control,current_vocal_draft,current_lyrics_control],queue=False)

        if current_minimax_mode or current_heartmula_mode:
            current_example_button.click(lambda current_example_identifier: load_instrumental_example(current_example_identifier,current_service_name),inputs=current_example_selector,outputs=[current_prompt_control,current_lyrics_control,current_length_control,current_seed_control,current_loop_control,current_minimum_control,current_legacy_control],queue=False)
        current_prompt_counts,current_final_prompt = describe_music_prompt(current_service_name,current_default_record['prompt'],current_default_record['loop_request'] if current_effects_mode else False,current_effects_mode)
        current_prompt_summary = gr.Markdown(current_prompt_counts)
        with gr.Accordion('최종 모델 입력 원문',open=False):
            current_final_control = gr.Textbox(value=current_final_prompt,interactive=False,label='최종 프롬프트',lines=4)
            if current_minimax_mode or current_heartmula_mode:
                current_final_lyrics = gr.Textbox(value='' if current_heartmula_mode else '[Instrumental]',label='최종 lyrics',interactive=False,lines=4)
                current_lyrics_summary = gr.Markdown('가사 입력 0단어 · 최종 lyrics 0단어' if current_heartmula_mode else '가사 입력 1단어 · 최종 lyrics 1단어')
                def update_music_lyrics(current_lyrics_text,current_legacy_value):
                    current_final_lyrics = '[Instrumental]' if current_minimax_mode and current_legacy_value else current_lyrics_text
                    return current_final_lyrics,f'가사 입력 {len(current_lyrics_text.split())}단어 · 최종 lyrics {len(current_final_lyrics.split())}단어'
                for current_lyrics_source in (current_lyrics_control,current_legacy_control):
                    current_lyrics_source.change(update_music_lyrics,[current_lyrics_control,current_legacy_control],[current_final_lyrics,current_lyrics_summary],queue=False)
                gr.Markdown('태그와 가사는 위 원문 그대로 전달합니다. 출력 상한은 밀리초로 환산하며 이력 태그는 모델 입력에 포함하지 않습니다.' if current_heartmula_mode else '최종 프롬프트는 prompt, 가사는 lyrics, 길이는 audio_duration으로 전달합니다.')
        def update_music_prompt(current_prompt_text,current_loop_value,current_legacy_value):
            return describe_music_prompt(current_service_name,current_prompt_text,current_loop_value,current_legacy_value)
        current_tag_control = gr.Textbox(label='이력 태그 · 선택 사항',max_lines=1,info='예: 초원 낮 · 비교 실험 1. 모델 입력에는 포함되지 않습니다.')
        current_generate_button = gr.Button('대기열에 추가',variant='primary',interactive=bool(current_default_record['prompt'].strip()) and not current_heartmula_mode)
        def describe_music_readiness(current_prompt_text,current_lyrics_text,current_legacy_value):
            if current_heartmula_mode:
                return '예제를 불러오거나 음악 태그와 가사를 입력하세요. MR은 원곡 생성 후 자동 분리됩니다.' if not (current_prompt_text and current_prompt_text.strip() and current_lyrics_text and current_lyrics_text.strip()) else '입력한 설정을 확인한 뒤 대기열에 등록합니다.'
            if not current_prompt_text or not current_prompt_text.strip():
                return '음악 설명을 입력하세요.' if not current_effects_mode else '소리·재질·동작 설명을 입력하세요.'
            if current_minimax_mode and not current_legacy_value and (not current_lyrics_text or not current_lyrics_text.strip()):
                return '가사를 입력하세요. 반주만 만들 때는 [Instrumental]을 입력하세요.'
            return '입력한 설정을 확인한 뒤 대기열에 등록합니다.'
        def check_music_readiness(current_prompt_text,current_lyrics_text,current_legacy_value):
            if current_heartmula_mode:
                return bool(current_prompt_text and current_prompt_text.strip() and current_lyrics_text and current_lyrics_text.strip() and execute_music_command('model-status',{}).get('ready'))
            if current_magenta_mode:
                return bool(current_prompt_text and current_prompt_text.strip())
            return bool(current_prompt_text and current_prompt_text.strip() and (current_effects_mode or current_legacy_value or (current_lyrics_text and current_lyrics_text.strip())))
        current_readiness_controls = [current_prompt_control,current_lyrics_control,current_legacy_control]
        current_generate_notice = build_button_guidance(current_generate_button,describe_music_readiness(current_default_record['prompt'],'' if current_heartmula_mode else '[Instrumental]',current_effects_mode))
        for current_readiness_control in current_readiness_controls:
            current_readiness_control.change(describe_music_readiness,current_readiness_controls,current_generate_notice,queue=False)
        for current_prompt_source in (current_prompt_control,current_loop_control,current_legacy_control):
            current_prompt_source.change(update_music_prompt,[current_prompt_control,current_loop_control,current_legacy_control],[current_prompt_summary,current_final_control],queue=False)

        with gr.Column() as current_generation_container:
            pass
        gr.Markdown('모델 준비가 없으면 생성 작업에서 먼저 준비합니다. 다운로드 권한·실행 환경 오류는 로그에 기록하며 다른 모델로 대체하지 않습니다.')
        current_job_control = gr.Textbox(label='생성 ID')
        current_status_display = gr.Markdown('실행 관측이 없으면 예상 시간은 계산 중으로 표시합니다.')
        current_result_display = gr.HTML('<p>생성 완료 후 오디오를 표시합니다.</p>')
        current_result_identity = gr.State('')
        current_log_output,current_log_refresh,_ = build_execution_logs()
        def start_music_generation(current_prompt_text,current_duration_value,current_seed_value,current_loop_value,current_tag_value,current_minimum_value=0,current_lyrics_text='[Instrumental]',current_legacy_value=False):
            if type(current_seed_value) not in (int,float) or current_seed_value != int(current_seed_value):
                raise gr.Error('시드는 정수여야 합니다.')
            current_payload_record = {'action':'generate','prompt':current_prompt_text,'duration_seconds':current_duration_value,'seed':int(current_seed_value),'loop_request':current_loop_value,'tag':current_tag_value}
            if current_minimax_mode:
                if not current_legacy_value:
                    current_payload_record['lyrics'] = current_lyrics_text
            if current_heartmula_mode:
                current_payload_record['lyrics'] = current_lyrics_text
            if current_minimum_value:
                current_payload_record['min_duration_seconds'] = current_minimum_value
            build_music_request(current_service_name,current_payload_record)
            current_job_record = execute_music_command('generate',current_payload_record)
            return current_job_record['id'],current_content_label+' 생성 대기열에 등록했습니다.', '<p>새 작업의 결과를 기다립니다.</p>',''
        bind_gpu_generation_confirmation(current_generate_button,start_music_generation,[current_prompt_control,current_length_control,current_seed_control,current_loop_control,current_tag_control,current_minimum_control,current_lyrics_control,current_legacy_control],[current_job_control,current_status_display,current_result_display,current_result_identity],generation_confirmation_container=current_generation_container, generation_readiness_callback=check_music_readiness, generation_readiness_inputs=current_readiness_controls)
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
        if current_heartmula_mode:
            def refresh_heartmula_readiness(current_prompt_text,current_lyrics_text,current_legacy_value):
                current_model_record = execute_music_command('model-status',{})
                current_inputs_ready = bool(current_prompt_text and current_prompt_text.strip() and current_lyrics_text and current_lyrics_text.strip())
                return gr.update(interactive=bool(current_model_record.get('ready')) and current_inputs_ready),gr.update(interactive=bool(current_model_record.get('artifacts_ready'))),describe_music_readiness(current_prompt_text,current_lyrics_text,current_legacy_value) if current_model_record.get('ready') else current_model_record['message']
            gr.Timer(5).tick(refresh_heartmula_readiness,current_readiness_controls,[current_generate_button,current_prepare_button,current_generate_notice],queue=False,show_progress='hidden')
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
            return current_request_record['prompt'],current_request_record['duration_seconds'],current_request_record['seed'],current_request_record['loop_request'],current_request_record['tag'],current_history_record['id'],current_request_record.get('min_duration_seconds',0),current_request_record.get('lyrics','[Instrumental]'),'lyrics' not in current_request_record
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
