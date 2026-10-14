"""음악 결과의 청취·WAV 다운로드와 공용 실행 지표 표시."""
import html
from tools.review.common.gradio_history import format_generation_status
from tools.review.common.generation_progress_display import render_generation_estimate


def render_audio_generation_result(current_job_identifier,current_status_record,current_server_address):
    if current_status_record.get('result',{}).get('prepared'):
        return '<p>모델 준비가 완료되었습니다. 음악 프롬프트를 입력해 생성하세요.</p>'
    if not current_status_record.get('audio'):
        return '<p>음악 생성 완료 후 WAV 청취와 다운로드를 표시합니다.</p>'
    current_audio_url = html.escape(current_server_address+current_status_record['audio'],quote=True)
    return f'<audio controls preload="metadata" src="{current_audio_url}"></audio><p><a href="{current_audio_url}" download="music.wav">WAV 다운로드</a> · MIDI 출력 없음 · 반복 연결은 청취 검수 필요</p>'


def describe_audio_generation_status(current_status_record):
    current_metrics_record = current_status_record.get('metrics',{})
    current_status_text = '상태: '+format_generation_status(current_status_record)+'\n\n'+render_generation_estimate(current_status_record.get('estimate',{}),current_status_record['status'])
    current_status_text += '\n\n단계: '+current_metrics_record.get('stage',current_status_record['status'])+' · 단계 진행률과 전체 예상 진행률은 별개입니다.'
    for current_gpu_identifier,current_gpu_record in current_metrics_record.get('gpu_observations',{}).items():
        current_status_text += f"\n\nGPU {current_gpu_identifier}: 현재 {current_gpu_record.get('process_current_mib')} MiB · 관측 피크 {current_gpu_record.get('process_peak_mib')} MiB · {current_gpu_record['scope']}"
    if current_metrics_record.get('measurement_gaps'):
        current_status_text += '\n\nVRAM 미측정 구간: 실행 기록에서 원인을 확인하세요.'
    if current_status_record.get('error'):
        current_status_text += '\n\n실패 원인: '+current_status_record['error']
    return current_status_text
