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
        current_result_html = '<p>가사 있는 버전 · 원곡</p>'+current_result_html
        for current_stem_name,current_stem_label in (('mr','가사 없는 버전 · MR'),('vocals','분리 보컬')):
            current_stem_url = html.escape(current_server_address+current_status_record['audio_stems'][current_stem_name],quote=True)
            current_result_html += f'<p>{current_stem_label}</p><audio controls style="width:100%" aria-label="{current_stem_label} 재생 및 구간 탐색" preload="metadata" src="{current_stem_url}"></audio><p><a href="{current_stem_url}" download="{current_stem_name}.wav">{current_stem_label} WAV 다운로드</a></p>'
        current_result_html += '<p>Demucs 분리 결과 · 보컬 잔향과 악기 손실은 원곡과 비교해 청취 검수하세요.</p>'
    for current_audio_name,current_audio_record in current_status_record.get('result',{}).get('mp3_outputs',{}).items():
        current_mp3_url = html.escape(current_server_address+current_status_record['audio'].rsplit('/',1)[0]+'/'+current_audio_record['filename'],quote=True)
        current_audio_label = {'music':'가사 있는 버전 · 원곡','mr':'가사 없는 버전 · MR','vocals':'분리 보컬'}[current_audio_name]
        current_result_html += f'<p><a href="{current_mp3_url}" download>{current_audio_label} MP3 다운로드 · 320kbps</a></p>'
    return current_result_html


def describe_audio_generation_status(current_status_record):
    return describe_generation_status(current_status_record)
