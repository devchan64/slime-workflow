"""복구를 실행하지 않고 현재 대기열 실행기의 추정만 관측한다."""
from datetime import datetime
import math
from pathlib import Path
import re

from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record


def observe_running_queue_estimate(job_root, job_id, status_record):
    """상태·시도·갱신 시각이 일치하지 않으면 추정을 제공하지 않는다."""
    if status_record.get('status') != 'running':
        return None
    root = Path(job_root)
    try:
        pointer_path = root / 'queue-telemetry.json'
        pointer = read_bounded_delegation_record(pointer_path)
        attempt = pointer['attempt_id']
        if not isinstance(attempt, str) or not re.fullmatch(r'\d{1,30}', attempt):
            return None
        telemetry = root / 'queue-telemetry'
        attempt_dir = telemetry / attempt
        if telemetry.is_symlink() or attempt_dir.is_symlink() or not attempt_dir.is_dir() or attempt_dir.resolve().parent != telemetry.resolve():
            return None
        metrics = read_bounded_delegation_record(attempt_dir / 'metrics.json')
        if not isinstance(metrics, dict) or metrics.get('job_id') != job_id or metrics.get('attempt_id') != attempt or metrics.get('status') != 'running':
            return None
        estimate = metrics.get('estimate')
        if not isinstance(estimate, dict) or not all(isinstance(estimate.get(key), str) for key in ('basis', 'scope', 'updated_at')):
            return None
        updated = datetime.fromisoformat(estimate['updated_at'])
        if updated.tzinfo is None or updated.timestamp() < (root / 'status.json').stat().st_mtime:
            return None
        if type(estimate.get('sample_count')) is not int or estimate['sample_count'] < 0:
            return None
        for key in ('remaining', 'total_seconds', 'estimated_progress'):
            value = estimate.get(key)
            if key not in estimate or (value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0)):
                return None
        if estimate['estimated_progress'] is not None and estimate['estimated_progress'] >= 100:
            return None
        if estimate['total_seconds'] is not None and estimate['total_seconds'] <= 0:
            return None
        completion = estimate.get('completion')
        if 'completion' not in estimate or (completion is not None and (not isinstance(completion, str) or datetime.fromisoformat(completion).tzinfo is None)):
            return None
        if read_bounded_delegation_record(pointer_path) != pointer or read_bounded_delegation_record(root / 'status.json') != status_record:
            return None
        return {key: estimate[key] for key in ('remaining', 'completion', 'total_seconds', 'estimated_progress', 'sample_count', 'updated_at', 'scope', 'basis')}
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        return None


def observe_running_queue_progress(job_root, job_id, status_record):
    """현재 대기열 시도의 작업자 단계만 읽으며 작업 상태를 변경하지 않는다."""
    if status_record.get('status') != 'running':
        return None
    root = Path(job_root)
    try:
        pointer_path = root / 'queue-telemetry.json'
        pointer = read_bounded_delegation_record(pointer_path)
        attempt = pointer['attempt_id']
        if not isinstance(attempt, str) or not re.fullmatch(r'\d{1,30}', attempt):
            return None
        telemetry = root / 'queue-telemetry'
        directory = telemetry / attempt
        if telemetry.is_symlink() or directory.is_symlink() or not directory.is_dir() or directory.resolve().parent != telemetry.resolve():
            return None
        metrics = read_bounded_delegation_record(directory / 'metrics.json')
        if not isinstance(metrics, dict) or metrics.get('job_id') != job_id or metrics.get('attempt_id') != attempt or metrics.get('status') != 'running':
            return None
        progress = metrics.get('worker_progress')
        if not isinstance(progress, dict):
            return None
        step, total = progress.get('step'), progress.get('total')
        if type(step) is not int or type(total) is not int or not 0 <= step <= total or total <= 0:
            return None
        if not isinstance(progress.get('stage'), str) or not progress['stage'] or not isinstance(progress.get('scope'), str):
            return None
        updated = datetime.fromisoformat(progress['updated_at'])
        if updated.tzinfo is None or updated.timestamp() < (root / 'status.json').stat().st_mtime:
            return None
        if read_bounded_delegation_record(pointer_path) != pointer or read_bounded_delegation_record(root / 'status.json') != status_record:
            return None
        return {'stage': progress['stage'], 'step': step, 'total': total, 'updated_at': progress['updated_at'], 'scope': progress['scope']}
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        return None
