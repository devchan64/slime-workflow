"""Wan Fun 작업 진행을 OpenTelemetry 로그와 시도별 최신 관측으로 기록한다."""
import logging
import os
from pathlib import Path
import sys

from workflow.common.generation_records import write_record_atomically
from workflow.common.generation_telemetry import GenerationTelemetryRecorder

_DEPENDENCIES = Path(__file__).resolve().parents[2] / '.local/otel/wan-fun'


class FunProgressRecorder(GenerationTelemetryRecorder):
    def __init__(self, attempt_root, step_total, historical_durations):
        super().__init__(attempt_root, step_total, historical_durations)
        self._otel_provider = None
        self._otel_logger = None
        try:
            # 별도 디렉터리에 둔 SDK가 모델 런타임의 라이브러리를 덮어쓰지 않는다.
            if str(_DEPENDENCIES) not in sys.path:
                sys.path.append(str(_DEPENDENCIES))
            from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
            from opentelemetry.sdk._logs.export import LogExporter, LogExportResult, SimpleLogRecordProcessor
            from opentelemetry.sdk.resources import Resource

            root = Path(attempt_root)
            class ProgressExporter(LogExporter):
                def export(self, batch):
                    for item in batch:
                        attributes = {key: value for key, value in (item.log_record.attributes or {}).items()
                                      if key == 'event.name' or key.startswith('generation.')}
                        write_record_atomically(root / 'otel-progress.json', attributes)
                    return LogExportResult.SUCCESS
                def shutdown(self):
                    pass

            provider = LoggerProvider(resource=Resource.create({'service.name': 'wan22-fun-control'}))
            provider.add_log_record_processor(SimpleLogRecordProcessor(ProgressExporter()))
            if os.environ.get('OTEL_EXPORTER_OTLP_LOGS_ENDPOINT') or os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT'):
                from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
                from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
                provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(timeout=2)))
            logger = logging.Logger('slime.wan_fun.progress.' + root.name)
            logger.propagate = False
            logger.setLevel(logging.INFO)
            logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=provider))
            self._otel_provider, self._otel_logger = provider, logger
        except Exception as error:
            logging.getLogger(__name__).warning('OpenTelemetry 진행 이벤트를 사용할 수 없습니다: %s', error)

    def save_generation_metrics(self):
        super().save_generation_metrics()
        if self._otel_logger is None:
            return
        try:
            with self.current_state_lock:
                state = self.current_run_state
                estimate = state['inference_estimate']
                attributes = {
                    'event.name': 'generation.progress',
                    'generation.job.id': self.current_attempt_root.parent.parent.name,
                    'generation.attempt.id': self.current_attempt_root.name,
                    'generation.status': state['status'],
                    'generation.stage': state['stage'],
                    'generation.step': state['step'],
                    'generation.step.total': state['step_total'],
                    'generation.started_at': state['started_at'],
                    'generation.updated_at': state['updated_at'],
                    'generation.estimate.scope': estimate['scope'],
                    'generation.estimate.basis': estimate['basis'],
                    'generation.estimate.sample_count': estimate['sample_count'],
                }
                if estimate['remaining'] is not None:
                    attributes['generation.estimate.remaining_seconds'] = estimate['remaining']
                if estimate['completion'] is not None:
                    attributes['generation.estimate.completion_time'] = estimate['completion']
                self._otel_logger.info('generation.progress', extra=attributes)
        except Exception:
            logging.getLogger(__name__).exception('OpenTelemetry 진행 이벤트 기록 실패')

    def finish_generation_telemetry(self, status):
        super().finish_generation_telemetry(status)
        if self._otel_provider:
            try:
                self._otel_provider.shutdown()
            except Exception:
                logging.getLogger(__name__).exception('OpenTelemetry 종료 실패')
