"""음악 결과의 청취·WAV 다운로드와 공용 실행 지표 표시."""
import html
from tools.review.common.generation_status_display import describe_generation_status
from tools.review.common.generation_result_guidance import describe_missing_generation_result


def render_audio_generation_result(current_job_identifier,current_status_record,current_server_address):
    if current_status_record.get('result',{}).get('prepared'):
        return '<p>모델 준비가 완료되었습니다. 음악 프롬프트를 입력해 생성하세요.</p>'
    if not current_status_record.get('audio'):
        return '<p>'+html.escape(describe_missing_generation_result(current_status_record,'WAV'))+'</p>'
    current_audio_url = html.escape(current_server_address+current_status_record['audio'],quote=True)
    return f'<audio controls preload="metadata" src="{current_audio_url}"></audio><p><a href="{current_audio_url}" download="music.wav">WAV 다운로드</a> · MIDI 출력 없음 · 반복 연결은 청취 검수 필요</p>'


def describe_audio_generation_status(current_status_record):
    return describe_generation_status(current_status_record)
