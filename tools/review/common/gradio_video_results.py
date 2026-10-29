"""영상 생성기의 공용 결과·상태 표시."""
import html
from tools.review.common.generation_status_display import describe_generation_status
from tools.review.common.generation_result_guidance import describe_missing_generation_result
from tools.review.common.generation_progress_display import render_generation_estimate

VIDEO_PREVIEW_FRAME_RATE = 16
VIDEO_ALLOWED_FRAME_COUNTS = tuple(range(1, 162, 4))


def describe_video_frame_duration(current_frame_count):
    """편집 중 빈 값은 길이로 계산하지 않고 입력 방법을 안내한다."""
    if type(current_frame_count) not in (int, float) or current_frame_count not in VIDEO_ALLOWED_FRAME_COUNTS:
        return '프레임 수를 1~161 사이의 4n+1 정수로 입력하세요. 예: 1, 5, 9, 81.'
    return f'{int(current_frame_count)}프레임 · 약 {current_frame_count / VIDEO_PREVIEW_FRAME_RATE:.2f}초 · {VIDEO_PREVIEW_FRAME_RATE}fps'


def render_video_generation_result(current_job_identifier,current_status_record,current_server_address):
    if current_status_record.get('result_error'):
        return '<p>결과 조회 불가: '+html.escape(current_status_record['result_error'])+'</p>'
    if not current_status_record.get('video'):
        return '<p>'+html.escape(describe_missing_generation_result(current_status_record,'영상'))+'</p>'
    # 게이트웨이의 루트 상대 경로를 유지해야 브라우저 접속 호스트와 출처가 같다.
    current_video_url=html.escape(current_status_record['video'],quote=True)
    current_download_url=html.escape(current_status_record['download'],quote=True)
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


def build_video_job_monitor(current_execute_command, current_server_address, current_job_control, current_status_output, result_renderer_callback=render_video_generation_result):
    """작업 ID를 기준으로 공용 상태·로그·영상만 갱신한다. 작업 수명은 서비스가 관리한다."""
    import gradio as gr
    from tools.review.common.gradio_logs import build_execution_logs
    from tools.review.common.generation_status_lookup import read_existing_generation_status
    current_result_output = gr.HTML('')
    current_result_identity = gr.State('')
    current_log_output, current_log_enabled, _ = build_execution_logs()
    current_generation_timer = gr.Timer(5, active=False)
    def refresh_video_status(current_job_identifier, current_logs_enabled, current_previous_result):
        if not current_job_identifier:
            return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.Timer(active=False)
        current_status_record = read_existing_generation_status(current_execute_command, current_job_identifier)
        if current_status_record is None:
            return '삭제된 이력입니다.', '', '', '', gr.Timer(active=False)
        current_result_url = current_status_record.get('comparison_video') or current_status_record.get('video', '')
        return (describe_video_generation_status(current_status_record),
                result_renderer_callback(current_job_identifier, current_status_record, current_server_address) if current_result_url and current_result_url != current_previous_result else gr.skip(),
                current_status_record.get('log', '') if current_logs_enabled else gr.skip(), current_result_url,
                gr.Timer(active=current_status_record.get('status') not in ('completed', 'failed', 'cancelled', 'paused')))
    current_generation_timer.tick(refresh_video_status, [current_job_control, current_log_enabled, current_result_identity], [current_status_output, current_result_output, current_log_output, current_result_identity, current_generation_timer], queue=False, show_progress='hidden')
    current_job_control.change(lambda current_job_identifier: gr.Timer(active=bool(current_job_identifier)), current_job_control, current_generation_timer, queue=False)
    return current_generation_timer
