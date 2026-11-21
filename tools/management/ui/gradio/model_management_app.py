"""게이트웨이의 모델 준비 상태를 한 화면에서 조회한다."""
import html
import gradio as gr

from tools.management.common.gradio_model_download import build_model_download_controls, build_model_progress_display, format_model_download_status
from tools.management.common.management_client import execute_remote_management_command

from tools.management.common.model_management_catalog import MODEL_PREPARATION_SERVICES

MODEL_JOB_SERVICES = ()
MODEL_OBSERVATION_SERVICES = ()


def format_model_file_size(current_file_bytes):
    if current_file_bytes >= 1024**3:
        return f'{current_file_bytes / (1024**3):.2f} GiB'
    if current_file_bytes >= 1024**2:
        return f'{current_file_bytes / (1024**2):.2f} MiB'
    return f'{current_file_bytes:,}바이트'


def format_model_inventory_summary(current_inventory_record):
    current_file_count = current_inventory_record.get('count', 0)
    current_total_bytes = current_inventory_record.get('total_bytes')
    current_summary_text = f'저장된 파일 {current_file_count:,}개'
    if current_total_bytes is not None:
        current_summary_text += f' · {format_model_file_size(current_total_bytes)}'
    if current_inventory_record.get('incomplete'):
        current_summary_text += ' · 일부 저장 위치 확인 실패'
    return current_summary_text


def format_model_inventory_files(current_inventory_record):
    current_file_records = current_inventory_record.get('files', [])
    current_file_count = current_inventory_record.get('count', 0)
    if not current_file_records and current_inventory_record.get('incomplete'):
        return '일부 저장 위치를 확인하지 못했습니다. 권한과 저장 장치를 확인하세요.'
    if not current_file_records:
        return '저장된 모델 파일이 없습니다.'
    current_lines = [f'저장된 파일 {current_file_count:,}개 · 파일 존재 기준이며 해시 검증 결과는 아닙니다.']
    for current_file_record in current_file_records:
        current_file_path = html.escape(current_file_record['path']).replace('`', '&#96;')
        current_file_bytes = current_file_record['bytes']
        current_size_text = format_model_file_size(current_file_bytes)
        current_lines.append(f'- `{current_file_path}` · {current_size_text}')
    if current_inventory_record.get('truncated'):
        current_lines.append('파일이 많아 앞의 500개만 표시합니다.')
    if current_inventory_record.get('incomplete'):
        current_lines.append('일부 저장 위치를 확인하지 못했습니다.')
    return '\n'.join(current_lines)


def execute_model_preparation_command(current_service_name, current_command_name, current_payload_record):
    from tools.management.common.model_preparation_controls import execute_model_preparation_command as execute
    return execute(current_service_name, current_command_name, current_payload_record, execute_remote_management_command)


def execute_wan13_model_command(current_command_name, current_payload_record):
    from tools.management.common.model_preparation_controls import execute_wan13_model_command as execute
    return execute(current_command_name, current_payload_record, execute_remote_management_command)


def read_model_observation_status(current_service_name, current_execute_command=execute_remote_management_command):
    """게이트웨이의 모델 구성 상태를 파일 목록과 구분해 표시한다."""
    try:
        current_status_record = current_execute_command(current_service_name, 'model-status', {})
        current_status_message = current_status_record.get('message', '상세 상태가 없습니다.')
        return f'서비스 상태: {current_status_message} · 전체 해시와 GPU 실행은 별도 확인'
    except Exception as current_status_error:
        return f'서비스 상태 확인 실패: {current_status_error}'


def read_model_job_status(current_service_name, current_execute_command=execute_remote_management_command):
    """작업 이력에서 준비 요청의 상태를 읽는다."""
    try:
        current_history_record = current_execute_command(current_service_name, 'history', {})
        current_prepare_records = [current_job_record for current_job_record in current_history_record.get('records', [])
                                   if current_job_record.get('request', {}).get('action') == 'prepare']
        current_active_records = [current_job_record for current_job_record in current_prepare_records
                                  if current_job_record.get('status', {}).get('status') in ('queued', 'running')]
        current_job_record = (current_active_records or current_prepare_records or [None])[0]
        if current_job_record:
            current_state_name = current_job_record.get('status', {}).get('status', 'unknown')
            current_state_label = {'queued': '대기 중', 'running': '진행 중', 'completed': '완료', 'failed': '실패', 'cancelled': '취소됨'}.get(current_state_name, current_state_name)
            return f"최근 모델 준비: {current_state_label} · 작업 ID `{current_job_record['id']}`"
        return '최근 모델 준비 작업이 없습니다.'
    except Exception as current_status_error:
        return f'모델 준비 이력 조회 실패: {current_status_error}'


def format_migraphx_build_status(current_status_record):
    current_state_name = current_status_record.get('status', 'idle')
    current_state_label = {'idle': '빌드 이력 없음', 'queued': 'GPU 대기 중', 'running': '빌드 중',
                           'completed': '최근 빌드 완료', 'failed': '빌드 실패', 'cancelled': '취소됨',
                           'checking': '모델·GPU 환경 및 빌드 확인 중', 'ready': '현재 환경에서 빌드 준비 완료',
                           'rebuild_required': '현재 환경에 맞는 빌드 필요', 'unavailable': '빌드 유효성 확인 실패'}.get(current_state_name, current_state_name)
    current_job_identifier = current_status_record.get('id')
    current_job_text = f' · 작업 ID `{current_job_identifier}`' if current_job_identifier else ''
    current_error_text = f" · {current_status_record['error']}" if current_status_record.get('error') else ''
    current_log_text = f' · 상세 로그: `.tmp/test/kimodo-migraphx-build/{current_job_identifier}/worker.log`' if current_state_name == 'failed' and current_job_identifier else ''
    return f'{current_state_label}{current_job_text}{current_error_text}{current_log_text}'


def build_migraphx_build_controls(current_interface_blocks):
    gr.Markdown('### Kimodo DWPose MIGraphX 빌드\n참조 포즈와 출력 포즈에 사용할 GPU 실행 그래프를 미리 빌드합니다. GPU 대기열에서 실행하며 최초 빌드에는 시간이 걸립니다. 모델과 GPU 실행 환경이 바뀌면 다시 빌드해야 합니다.')
    current_build_status = gr.Markdown('빌드 상태 확인 중')
    current_build_button = gr.Button('MIGraphX 빌드 시작', interactive=False)
    def refresh_migraphx_build_status():
        try:
            current_status_record = execute_remote_management_command('kimodo', 'migraphx-build-status', {})
            return format_migraphx_build_status(current_status_record), gr.update(interactive=current_status_record.get('status') == 'rebuild_required')
        except Exception as current_status_error:
            return f'빌드 상태 조회 실패: {current_status_error}', gr.update(interactive=False)
    def request_migraphx_build_job():
        try:
            current_status_record = execute_remote_management_command('kimodo', 'migraphx-build', {})
            return format_migraphx_build_status(current_status_record), gr.update(interactive=False)
        except Exception as current_build_error:
            return f'빌드 요청 실패: {current_build_error}', gr.update(interactive=False)
    current_interface_blocks.load(refresh_migraphx_build_status, outputs=[current_build_status, current_build_button])
    gr.Timer(5).tick(refresh_migraphx_build_status, outputs=[current_build_status, current_build_button], queue=False)
    current_build_button.click(request_migraphx_build_job, outputs=[current_build_status, current_build_button], queue=False)


def build_model_management_interface():
    with gr.Blocks(title='모델 다운로드·빌드 상태') as current_interface_blocks:
        gr.Markdown('## 모델 다운로드·빌드 상태\n모델을 이름순으로 표시합니다. 각 모델에서 다운로드와 이어받기 상태를 확인하고 파일 목록을 펼칠 수 있습니다. 다운로드 진행률은 5초마다, 모델 준비 상태와 파일 목록은 30초마다 갱신합니다. 다운로드 중인 모델의 준비 상태는 5초마다 확인합니다. 파일 수와 용량은 저장된 파일의 존재 기준이며 부분 파일은 제외합니다. 파일 존재는 무결성 검증이나 실행 준비 완료를 뜻하지 않습니다.')
        current_inventory_refresh = gr.Button('저장된 파일 목록 새로고침')
        current_shared_refresh_records = []
        current_shared_progress_outputs = []
        current_inventory_outputs = []
        current_inventory_services = []
        current_all_services = sorted((*MODEL_PREPARATION_SERVICES, *MODEL_JOB_SERVICES, *MODEL_OBSERVATION_SERVICES), key=lambda current_item: current_item[0].casefold())
        current_preparation_names = {current_service_name for _, current_service_name in MODEL_PREPARATION_SERVICES}
        current_job_names = {current_service_name for _, current_service_name in MODEL_JOB_SERVICES}
        for current_label_name, current_service_name in current_all_services:
            with gr.Group():
                gr.Markdown(f'### {current_label_name}')
                if current_service_name in current_preparation_names:
                    if current_service_name == 'wan22-fun-control':
                        gr.Markdown('**Wan 2.2 Fun Control 14B**')
                    if current_service_name == 'flux-image':
                        gr.Markdown('공식 고정 리비전 약 20.32GB를 검증합니다. [모델 사용 조건](https://huggingface.co/black-forest-labs/flux-3-image-klein)을 확인하고 Hugging Face 접근 권한과 로그인을 준비하세요. 기존 파일은 덮어쓰지 않습니다.')
                    if current_service_name == 'prompt-translation':
                        gr.Markdown('[Gemma 이용약관과 모델 접근 조건](https://huggingface.co/google/translategemma-4b-it)을 검토·동의하고 Hugging Face에 로그인해야 다운로드할 수 있습니다. 실패 시 `.local/model-preparation/prompt-translation-model/worker.log`를 확인하세요.')
                    def execute_model_command(current_command_name, current_payload_record, service_name_value=current_service_name):
                        return execute_model_preparation_command(service_name_value, current_command_name, current_payload_record)
                    build_model_download_controls(current_interface_blocks, execute_model_command, model_service_name=current_service_name, shared_refresh_records=current_shared_refresh_records, shared_progress_outputs=current_shared_progress_outputs)
                    if current_service_name == 'wan22-fun-control':
                        gr.Markdown('**Wan 2.1 Fun Control 1.3B** · 모델과 참조 이미지 인코더를 준비합니다. 공용 텍스트 인코더와 VAE는 14B 준비 환경을 사용합니다.')
                        build_model_download_controls(current_interface_blocks, execute_wan13_model_command, model_service_name='wan21-fun-1.3b', shared_refresh_records=current_shared_refresh_records, shared_progress_outputs=current_shared_progress_outputs)
                        current_inventory_outputs.append(gr.Markdown('1.3B 저장 파일 확인 중'))
                        with gr.Accordion('1.3B 저장 모델 파일 보기', open=False):
                            current_inventory_outputs.append(gr.Markdown('파일 목록 확인 중'))
                            current_inventory_services.append('wan21-fun-1.3b')
                    if current_service_name == 'kimodo':
                        build_migraphx_build_controls(current_interface_blocks)
                else:
                    if current_service_name in current_job_names:
                        build_model_progress_display(current_interface_blocks, current_service_name)
                    if current_service_name in current_job_names:
                        gr.Markdown('다운로드 요청은 해당 생성기 화면에서 실행합니다.')
                        current_status_output = gr.Markdown('모델 준비 상태 확인 중')
                        def refresh_model_job_status(service_name_value=current_service_name):
                            return read_model_job_status(service_name_value)
                        current_interface_blocks.load(refresh_model_job_status, outputs=current_status_output)
                        gr.Timer(5).tick(refresh_model_job_status, outputs=current_status_output, queue=False)
                current_inventory_outputs.append(gr.Markdown('저장된 파일 확인 중'))
                with gr.Accordion('저장된 모델 파일 보기', open=False):
                    current_inventory_outputs.append(gr.Markdown('파일 목록 확인 중'))
                    current_inventory_services.append(current_service_name)
        def refresh_all_model_statuses():
            return [current_result_value for current_refresh_callback, _ in current_shared_refresh_records
                    for current_result_value in current_refresh_callback()]
        current_status_outputs = [current_output_value for _, current_output_values in current_shared_refresh_records
                                  for current_output_value in current_output_values]
        if current_status_outputs:
            gr.Timer(30).tick(refresh_all_model_statuses, outputs=current_status_outputs, queue=False, show_progress='hidden')
        def refresh_all_download_progress():
            try:
                current_download_records = execute_remote_management_command('model-downloads', 'download-status', {})['records']
                return [format_model_download_status(current_download_records, current_service_name)
                        for current_service_name, _ in current_shared_progress_outputs]
            except Exception as current_status_error:
                return [f'다운로드 상태 확인 실패: {current_status_error}' for _ in current_shared_progress_outputs]
        if current_shared_progress_outputs:
            current_progress_outputs = [current_output_value for _, current_output_value in current_shared_progress_outputs]
            current_interface_blocks.load(refresh_all_download_progress, outputs=current_progress_outputs)
            gr.Timer(5).tick(refresh_all_download_progress, outputs=current_progress_outputs, queue=False, show_progress='hidden')
        def refresh_model_inventory_files():
            try:
                current_inventory_records = execute_remote_management_command('model-downloads', 'download-inventory', {})['models']
                return [current_display_text for current_service_name in current_inventory_services
                        for current_display_text in (format_model_inventory_summary(current_inventory_records.get(current_service_name, {})),
                                                     format_model_inventory_files(current_inventory_records.get(current_service_name, {})))]
            except Exception as current_inventory_error:
                return [f'파일 목록 확인 실패: {current_inventory_error}' for _ in current_inventory_outputs]
        current_interface_blocks.load(refresh_model_inventory_files, outputs=current_inventory_outputs)
        current_inventory_refresh.click(refresh_model_inventory_files, outputs=current_inventory_outputs, queue=False)
        gr.Timer(30).tick(refresh_model_inventory_files, outputs=current_inventory_outputs, queue=False)
    return current_interface_blocks
