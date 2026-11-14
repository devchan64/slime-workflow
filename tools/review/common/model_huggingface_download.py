"""Hugging Face 다운로드를 기존 캐시·이어받기 동작과 공용 상태에 연결한다."""
import inspect
import logging
import threading
import time
from tqdm.auto import tqdm
from tools.review.common.model_download_records import track_model_download


def execute_huggingface_download(current_function_name, current_argument_values, current_keyword_values):
    from huggingface_hub import hf_hub_download, snapshot_download
    current_download_function = {'file': hf_hub_download, 'snapshot': snapshot_download}[current_function_name]
    current_repo_name = current_keyword_values.get('repo_id', current_argument_values[0] if current_argument_values else '')
    current_file_name = current_keyword_values.get('filename', current_argument_values[1] if len(current_argument_values) > 1 else '')
    current_model_name = str(current_repo_name) + ('/' + str(current_file_name) if current_file_name else '')
    current_record_lock = threading.RLock()
    with track_model_download(current_model_name) as current_download_record:
        current_snapshot_total = None
        current_cached_bytes = 0
        if current_function_name == 'snapshot' and not current_keyword_values.get('dry_run') and 'dry_run' in inspect.signature(current_download_function).parameters:
            try:
                current_probe_options = dict(current_keyword_values)
                current_probe_options['dry_run'] = True
                current_probe_options.pop('tqdm_class', None)
                current_probe_records = current_download_function(*current_argument_values, **current_probe_options)
                if isinstance(current_probe_records, list) and current_probe_records and all(isinstance(getattr(current_file_record, 'file_size', None), int) and current_file_record.file_size >= 0 for current_file_record in current_probe_records):
                    current_snapshot_total = sum(current_file_record.file_size for current_file_record in current_probe_records)
                    current_cached_bytes = sum(current_file_record.file_size for current_file_record in current_probe_records if current_file_record.is_cached and not current_file_record.will_download)
                    current_download_record.update(stage='다운로드', bytes=current_cached_bytes, total_bytes=current_snapshot_total, resumed_bytes=None)
                    if current_keyword_values.get('local_dir') and not current_keyword_values.get('force_download') and not current_keyword_values.get('local_files_only') and current_keyword_values.get('token') in (None, False) and current_keyword_values.get('repo_type') in (None, 'model') and not current_keyword_values.get('headers'):
                        from tools.review.common.model_huggingface_recovery import recover_huggingface_partial
                        for current_file_record in current_probe_records:
                            if current_file_record.will_download:
                                try:
                                    if recover_huggingface_partial(current_repo_name, current_file_record.commit_hash, current_keyword_values['local_dir'], current_file_record, current_keyword_values.get('endpoint')):
                                        current_cached_bytes += current_file_record.file_size
                                        current_download_record.update(bytes=current_cached_bytes)
                                except Exception as current_recovery_error:
                                    # 원본을 보존하고 기존 다운로드 경로를 사용한다.
                                    logging.getLogger(__name__).warning('기존 부분 파일 복구 건너뜀: %s · %s', current_file_record.filename, type(current_recovery_error).__name__)
                                    continue
            except Exception:
                # 메타데이터를 얻지 못해도 실제 다운로드와 기존 캐시 계약을 유지한다.
                pass
        class ModelDownloadProgress(tqdm):
            def __init__(self, *current_progress_args, **current_progress_kwargs):
                self.current_byte_progress = current_progress_kwargs.get('unit') == 'B' and (current_function_name == 'file' or str(current_progress_kwargs.get('desc', '')).startswith('Reconstructing'))
                self.current_received_bytes = int(current_progress_kwargs.get('initial') or 0)
                self.current_report_time = 0.0
                self.current_resume_bytes = self.current_received_bytes if current_function_name == 'file' else None
                super().__init__(*current_progress_args, **current_progress_kwargs)
                if self.current_byte_progress:
                    self.publish_download_progress(True)

            def publish_download_progress(self, force_report_value=False):
                current_clock_value = time.monotonic()
                if force_report_value or current_clock_value - self.current_report_time >= 1:
                    with current_record_lock:
                        current_download_record.update(stage='다운로드', bytes=self.current_received_bytes + current_cached_bytes, total_bytes=current_snapshot_total if current_snapshot_total is not None else (int(self.total) if self.total else None), resumed_bytes=self.current_resume_bytes)
                    self.current_report_time = current_clock_value

            def update(self, current_increment_value=1):
                if self.current_byte_progress:
                    with current_record_lock:
                        self.current_received_bytes += int(current_increment_value or 0)
                        self.publish_download_progress()
                return super().update(current_increment_value)

            def close(self):
                if getattr(self, 'current_byte_progress', False):
                    self.publish_download_progress(True)
                    self.current_byte_progress = False
                return super().close()

        current_download_options = dict(current_keyword_values)
        if 'tqdm_class' in current_download_options:
            raise ValueError('공용 다운로드 기록과 별도 진행률 클래스는 함께 사용할 수 없습니다.')
        current_download_options['tqdm_class'] = ModelDownloadProgress
        current_download_result = current_download_function(*current_argument_values, **current_download_options)
        if current_snapshot_total is not None:
            current_download_record.update(bytes=current_snapshot_total, total_bytes=current_snapshot_total)
        return current_download_result


def tracked_hf_hub_download(*current_argument_values, **current_keyword_values):
    return execute_huggingface_download('file', current_argument_values, current_keyword_values)


def tracked_snapshot_download(*current_argument_values, **current_keyword_values):
    return execute_huggingface_download('snapshot', current_argument_values, current_keyword_values)
