"""영상 생성기의 공용 결과·상태 표시."""
import html
from tools.review.common.generation_status_display import describe_generation_status
from tools.review.common.generation_result_guidance import describe_missing_generation_result
from tools.review.common.generation_progress_display import render_generation_estimate

def render_video_generation_result(current_job_identifier,current_status_record,current_server_address):
    if not current_status_record.get('video'):
        return '<p>'+html.escape(describe_missing_generation_result(current_status_record,'영상'))+'</p>'
    current_video_url=html.escape(current_server_address+current_status_record['video'],quote=True)
    current_download_url=html.escape(current_server_address+current_status_record['download'],quote=True)
    return f'<video controls loop playsinline width="512" src="{current_video_url}"></video><p><a href="{current_video_url}" target="_blank">MP4 열기</a> · <a href="{current_download_url}">PNG 프레임 ZIP</a></p>'


def describe_video_generation_status(current_status_record):
    current_status_text=describe_generation_status(current_status_record)
    current_metrics_record=current_status_record.get('metrics') or {}
    # 서비스에서 현재 실행 시도와 대조한 작업자 추정을 별도 범위로 표시한다.
    current_worker_metrics = current_status_record.get('worker_metrics')
    if current_worker_metrics is not None:
        current_metrics_record = current_worker_metrics
    if current_metrics_record.get('inference_estimate'):
        current_status_text+='\n\n추론 종료까지의 참고 추정\n\n'+render_generation_estimate(current_metrics_record['inference_estimate'],current_status_record['status'])
    return current_status_text
