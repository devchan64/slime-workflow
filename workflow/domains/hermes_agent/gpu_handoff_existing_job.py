"""Track an existing experiment job without submitting a duplicate."""
import hashlib
from workflow.domains.hermes_agent.gpu_handoff_kimodo import KimodoHandoffAdapter
from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record


def fingerprint(job):
    return hashlib.sha256((job / 'gpu-command.json').read_bytes() + (job / 'request.json').read_bytes()).hexdigest()


class ExistingJobHandoffAdapter(KimodoHandoffAdapter):
    def lookup_target(self, record):
        job = self._job(record)
        return {'state':'accepted', 'service':record['service'], 'input_digest':record['input_digest'], 'job_id':job.name}

    submit_target = lookup_target

    def inspect_target(self, record):
        job = self._job(record)
        if job.name != record['job_id']:
            raise ValueError('작업이 일치하지 않습니다.')
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
