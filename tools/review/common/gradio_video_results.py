"""영상 생성기의 공용 결과·상태 표시."""
import html
from tools.review.common.gradio_history import format_generation_status
from tools.review.common.generation_progress_display import render_generation_estimate

def render_video_generation_result(current_job_identifier,current_status_record,current_server_address):
    if not current_status_record.get('video'):
        return '<p>완료 후 영상과 프레임 다운로드를 표시합니다.</p>'
    current_video_url=html.escape(current_server_address+current_status_record['video'],quote=True)
    current_download_url=html.escape(current_server_address+current_status_record['download'],quote=True)
    return f'<video controls loop playsinline width="512" src="{current_video_url}"></video><p><a href="{current_video_url}" target="_blank">MP4 열기</a> · <a href="{current_download_url}">PNG 프레임 ZIP</a></p>'


def describe_video_generation_status(current_status_record):
    current_status_text='상태: '+format_generation_status(current_status_record)+'\n\n'+render_generation_estimate(current_status_record.get('estimate',{}),current_status_record['status'])
    current_metrics_record=current_status_record.get('metrics',{})
    current_status_text+=f"\n\n단계: {current_metrics_record.get('stage','queued')} · 추론 {current_metrics_record.get('step',0)}/{current_status_record.get('progress',{}).get('total','?')}스텝"
    if current_metrics_record.get('inference_estimate'):
        current_status_text+='\n\n추론 종료까지의 참고 추정\n\n'+render_generation_estimate(current_metrics_record['inference_estimate'],current_status_record['status'])
    for current_gpu_identifier,current_gpu_record in current_metrics_record.get('gpu_observations',{}).items():
        current_status_text+=f"\n\nGPU {current_gpu_identifier}: 현재 {current_gpu_record.get('process_current_mib')} MiB · 관측 피크 {current_gpu_record.get('process_peak_mib')} MiB · {current_gpu_record['scope']}"
    if current_metrics_record.get('measurement_gaps'):
        current_status_text+='\n\nVRAM 측정 누락 구간 존재: 실행 기록을 확인하세요.'
    return current_status_text
