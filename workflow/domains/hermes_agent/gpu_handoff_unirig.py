"""Track an existing UniRig experiment without submitting a duplicate."""
from pathlib import Path
import re

from workflow.domains.hermes_agent.gpu_handoff_pixal import PixalHandoffAdapter, fingerprint
from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record

ROOT = Path(__file__).resolve().parents[3] / '.tmp/unirig-experiment'


class UniRigHandoffAdapter(PixalHandoffAdapter):
    def _job(self, record):
        request = record['target_request']
        job_id = request.get('job_id')
        if not isinstance(job_id, str) or not re.fullmatch(r'generate-[a-f0-9]{32}', job_id):
            raise ValueError('UniRig 작업 ID 오류')
        job = ROOT / job_id
        if ROOT.is_symlink() or job.is_symlink() or not job.is_dir():
            raise ValueError('UniRig 작업 경로 오류')
        command = read_bounded_delegation_record(job / 'gpu-command.json')
        if not isinstance(command, dict) or command.get('service') != 'unirig-experiment' or fingerprint(job) != request.get('fingerprint'):
            raise ValueError('UniRig 작업 입력이 변경되었습니다.')
        return job
