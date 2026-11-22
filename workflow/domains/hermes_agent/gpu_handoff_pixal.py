"""Track an already queued Pixal experiment through a resident handoff."""
import hashlib
import json
from pathlib import Path
import re

from workflow.domains.hermes_agent.gpu_handoff_kimodo import KimodoHandoffAdapter
from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record

ROOT = Path(__file__).resolve().parents[3] / '.tmp/pixal-experiment'


def fingerprint(job):
    return hashlib.sha256((job / 'gpu-command.json').read_bytes() + (job / 'request.json').read_bytes()).hexdigest()


class PixalHandoffAdapter(KimodoHandoffAdapter):
    def _job(self, record):
        request = record['target_request']
        job_id = request.get('job_id')
        if not isinstance(job_id, str) or not re.fullmatch(r'generate-[a-f0-9]{32}', job_id):
            raise ValueError('Pixal 작업 ID 오류')
        job = ROOT / job_id
        if ROOT.is_symlink() or job.is_symlink() or not job.is_dir():
            raise ValueError('Pixal 작업 경로 오류')
        command = read_bounded_delegation_record(job / 'gpu-command.json')
        if not isinstance(command, dict) or command.get('service') != 'pixal-experiment' or fingerprint(job) != request.get('fingerprint'):
            raise ValueError('Pixal 작업 입력이 변경되었습니다.')
        return job

    def lookup_target(self, record):
        job = self._job(record)
        return {'state':'accepted', 'service':record['service'], 'input_digest':record['input_digest'], 'job_id':job.name}

    submit_target = lookup_target

    def inspect_target(self, record):
        job = self._job(record)
        if job.name != record['job_id']:
            raise ValueError('Pixal 작업이 일치하지 않습니다.')
        status = read_bounded_delegation_record(job / 'status.json').get('status')
        result = {'service':record['service'], 'job_id':job.name, 'status':status}
        if status in ('completed', 'failed', 'cancelled'):
            from workflow.domains.hermes_agent.writer_reservation import hold_writer_reservation_queue_lock
            from workflow.common import gpu_job_queue
            with hold_writer_reservation_queue_lock() as active:
                paths = list(active.glob('*.json')) + list(gpu_job_queue.GPU_QUEUE_DIRECTORY.glob('*.json'))
                records = [read_bounded_delegation_record(path) for path in paths]
                result['reservation_released'] = all(isinstance(item, dict) and isinstance(item.get('path'), str) and item['path'] != str(job.resolve()) for item in records)
        return result
