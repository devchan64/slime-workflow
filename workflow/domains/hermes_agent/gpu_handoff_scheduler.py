"""승인된 GPU 양도를 서비스 재시작 뒤에도 단계별로 이어간다."""
import logging
import time
from threading import Event, Thread

from workflow.domains.hermes_agent.gpu_handoff_controller import advance_gpu_handoff
from workflow.domains.hermes_agent.gpu_handoff_kimodo import KimodoHandoffAdapter
from workflow.domains.hermes_agent.gpu_handoff_flux import FluxHandoffAdapter
from workflow.domains.hermes_agent.gpu_handoff_video import VideoHandoffAdapter
from workflow.domains.hermes_agent.gpu_handoff_audio import AudioHandoffAdapter
from workflow.domains.hermes_agent.gpu_handoff_writer import WriterHandoffAdapter
from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore


class HandoffServiceAdapter:
    """저장된 서비스에 맞는 기존 생성기 어댑터만 선택한다."""
    def __init__(self):
        self.kimodo = KimodoHandoffAdapter()
        self.flux = FluxHandoffAdapter()
        self.video = VideoHandoffAdapter()
        self.audio = AudioHandoffAdapter()
        self.writer = WriterHandoffAdapter()

    def __getattr__(self, name):
        if name not in ('ensure_release_requested','inspect_release','submit_target','lookup_target','seal_unsubmitted_target','inspect_target','submit_reload','inspect_reload','inspect_failed_reload_cleanup','cancel_target'):
            raise AttributeError(name)
        def dispatch(record):
            if record['service'] == 'kimodo':
                adapter = self.kimodo
            elif record['service'] == 'writer-agent':
                adapter = self.writer
            else:
                from workflow.domains.hermes_agent.flux_profile_operations import validate_hermes_flux_profile
                from workflow.domains.hermes_agent.video_operations import HERMES_VIDEO_SERVICES
                from workflow.domains.hermes_agent.audio_operations import HERMES_AUDIO_SERVICES
                if record['service'] in HERMES_VIDEO_SERVICES:
                    adapter = self.video
                elif record['service'] in HERMES_AUDIO_SERVICES:
                    adapter = self.audio
                else:
                    validate_hermes_flux_profile(record['service'])
                    adapter = self.flux
            return getattr(adapter, name)(record)
        return dispatch


def run_gpu_handoff_scheduler(store, adapter, stop_event, interval_seconds=5):
    if interval_seconds <= 0:
        raise ValueError('GPU 양도 조회 간격은 양수여야 합니다.')
    logger = logging.getLogger(__name__)
    next_preload = 0
    while not stop_event.is_set():
        if time.monotonic() >= next_preload:
            next_preload = time.monotonic() + 30
            try:
                from workflow.domains.hermes_agent.resident_preload import preload_if_idle
                preload_if_idle()
            except (OSError, ValueError, RuntimeError) as error:
                logger.warning('상주 모델 선적재 확인 필요: %s', type(error).__name__)
        try:
            identifiers = store.list_active_ids()
        except (OSError, ValueError) as error:
            logger.warning('GPU 양도 기록 조회 실패: %s', type(error).__name__)
            stop_event.wait(interval_seconds)
            continue
        for request_id in identifiers:
            if stop_event.is_set():
                return
            try:
                advance_gpu_handoff(store, request_id, adapter)
            except (OSError, ValueError, RuntimeError) as error:
                logger.warning('GPU 양도 진행 확인 필요 (%s, %s)', request_id, type(error).__name__)
        stop_event.wait(interval_seconds)


def start_gpu_handoff_scheduler():
    stop_event = Event()
    thread = Thread(target=run_gpu_handoff_scheduler, name='hermes-gpu-handoff-scheduler',
                    args=(GpuHandoffStore(), HandoffServiceAdapter(), stop_event), daemon=True)
    thread.start()
    return stop_event
