"""음악 결과의 청취·WAV 다운로드와 공용 실행 지표 표시."""
import html
from tools.review.common.generation_status_display import describe_generation_status
from tools.review.common.generation_result_guidance import describe_missing_generation_result


def render_audio_generation_result(current_job_identifier,current_status_record,current_server_address):
    if current_status_record.get('result',{}).get('prepared'):
        return '<p>모델 준비가 완료되었습니다. 프롬프트를 입력해 생성하세요.</p>'
    if not current_status_record.get('audio'):
        return '<p>'+html.escape(describe_missing_generation_result(current_status_record,'WAV'))+'</p>'
    current_audio_url = html.escape(current_server_address+current_status_record['audio'],quote=True)
    current_download_name = 'sound.wav' if current_status_record['audio'].startswith('/sfx-dasheng-audiogen/') else 'music.wav'
    current_result_html = f'<audio controls style="width:100%" aria-label="생성 오디오 재생 및 구간 탐색" preload="metadata" src="{current_audio_url}"></audio><p><a href="{current_audio_url}" download="{current_download_name}">WAV 다운로드</a> · 반복 연결은 청취 검수 필요</p>'
    if current_status_record.get('audio_stems'):
        current_result_record = current_status_record.get('result',{})
        current_duration_value = current_result_record.get('duration_seconds')
        current_result_html = ''
        if current_duration_value is not None:
            current_result_html += f'<p>실제 길이: {float(current_duration_value):.2f}초 · WAV 원본 / MP3 320kbps</p>'
        current_termination_reason = current_result_record.get('termination',{}).get('reason')
        if current_termination_reason == 'max_audio_length_ms':
            current_result_html += '<p><strong>시간 상한 도달 · EOS 미감지</strong> — 곡 중간에 끊겼을 수 있습니다. 종료 토큰 번호는 EOS 감지 여부를 뜻하지 않습니다.</p>'
        elif current_termination_reason == 'audio_eos':
            current_result_html += '<p>모델 종료 토큰(EOS) 감지 · 음악적 끝맺음은 청취로 확인하세요.</p>'
        for current_audio_name,current_audio_label in (('music','가사 있는 버전 · 원곡'),('mr','가사 없는 버전 · MR'),('vocals','분리 보컬')):
            current_source_url = current_status_record['audio'] if current_audio_name == 'music' else current_status_record['audio_stems'][current_audio_name]
            current_escaped_url = html.escape(current_server_address+current_source_url,quote=True)
            current_result_html += f'<p><strong>{current_audio_label}</strong></p><audio controls style="width:100%" aria-label="{current_audio_label} 재생 및 구간 탐색" preload="metadata" src="{current_escaped_url}"></audio><p><a href="{current_escaped_url}" download="{current_audio_name}.wav">{current_audio_label} WAV 다운로드</a>'
            current_mp3_record = current_result_record.get('mp3_outputs',{}).get(current_audio_name)
            if current_mp3_record:
                current_mp3_url = html.escape(current_server_address+current_source_url.rsplit('/',1)[0]+'/'+current_mp3_record['filename'],quote=True)
                current_result_html += f' · <a href="{current_mp3_url}" download>{current_audio_label} MP3 다운로드 · 320kbps</a>'
            current_result_html += '</p>'
        current_result_html += '<p>MR은 보컬 잔향·악기 손실·끝맺음을 원곡과 비교해 검수하세요. 에셋 등록은 채택 후 별도로 진행합니다.</p>'
    return current_result_html


def describe_audio_generation_status(current_status_record):
    return describe_generation_status(current_status_record)
