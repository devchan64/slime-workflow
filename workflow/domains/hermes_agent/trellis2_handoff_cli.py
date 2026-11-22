"""Track one previously authorized TRELLIS.2 job through the GPU handoff."""
import hashlib
import json
import sys
from threading import Event
from workflow.domains.hermes_agent.gpu_handoff_pixal import fingerprint
from workflow.domains.hermes_agent.gpu_handoff_trellis2 import ROOT
from workflow.domains.hermes_agent.gpu_handoff_scheduler import HandoffServiceAdapter, run_gpu_handoff_scheduler
from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore


def main():
    job_id, resident_id, session_id = sys.argv[1:]
    job = ROOT / job_id
    if job.is_symlink() or job.parent != ROOT or not job.is_dir():
        raise ValueError('TRELLIS.2 작업 경로 오류')
    if json.loads((job / 'status.json').read_text()).get('status') != 'queued':
        raise ValueError('대기 중인 TRELLIS.2 작업이 아닙니다.')
    target = {'job_id':job_id, 'fingerprint':fingerprint(job)}
    digest = hashlib.sha256(json.dumps(target, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    request_id = 'trellis2_' + hashlib.sha256(job_id.encode()).hexdigest()
    store = GpuHandoffStore()
    store.approve(request_id, session_id, 'trellis-experiment', digest, target_request=target, resident_id=resident_id, confirmed=True)
    run_gpu_handoff_scheduler(store, HandoffServiceAdapter(), Event())


if __name__ == '__main__': main()
