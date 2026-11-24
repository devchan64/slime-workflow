"""Detached SHA-256 backup verification and durable result records."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import uuid
import time

from workflow.common.generation_records import write_record_atomically
from workflow.common.model_backup_service import compare_backup_model

ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ROOT / '.local/hermes/model-backup-verification'


def start_backup_job(model, operation='verify', *, target='canonical', request_id=None, state_root=STATE_ROOT):
    if not isinstance(model, str) or not model or model in ('.', '..') or '/' in model or '\\' in model or '\x00' in model:
        raise ValueError('모델 이름이 올바르지 않습니다.')
    if operation not in ('verify', 'sync'):
        raise ValueError('백업 작업 종류가 올바르지 않습니다.')
    if target not in ('canonical', 'latest_snapshot', 'snapshot_manifest') or (operation == 'sync' and target != 'canonical'):
        raise ValueError('백업 작업 대상이 올바르지 않습니다.')
    job_id = request_id if request_id is not None else uuid.uuid4().hex
    if not isinstance(job_id, str) or len(job_id) != 32 or any(char not in '0123456789abcdef' for char in job_id):
        raise ValueError('백업 요청 ID가 올바르지 않습니다.')
    state_root = Path(state_root)
    state_root.mkdir(parents=True, exist_ok=True)
    jobs = state_root / 'jobs'
    jobs.mkdir(exist_ok=True)
    job_path = jobs / (job_id + '.json')
    def existing_result():
        record = read_verification(job_id, state_root=state_root)
        if (record.get('model'), record.get('operation', 'verify'), record.get('target', 'canonical')) != (model, operation, target):
            raise ValueError('요청 ID가 다른 백업 작업에 이미 사용됐습니다.')
        return {key: record[key] for key in ('job_id', 'model', 'operation', 'target', 'status') if key in record}
    if job_path.exists():
        return existing_result()
    command = [sys.executable, '-m', 'workflow.common.model_backup_verification', '--model', model,
               '--job-id', job_id, '--state-root', str(state_root), '--operation', operation, '--target', target]
    with (state_root / 'worker.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            if job_path.exists():
                return existing_result()
            raise ValueError('다른 백업 작업이 진행 중입니다.') from error
        if job_path.exists():
            record = json.loads(job_path.read_text(encoding='utf-8'))
            if (record.get('model'), record.get('operation', 'verify'), record.get('target', 'canonical')) != (model, operation, target):
                raise ValueError('요청 ID가 다른 백업 작업에 이미 사용됐습니다.')
            if record.get('status') == 'running':
                record['status'] = 'interrupted'
            return {key: record[key] for key in ('job_id', 'model', 'operation', 'target', 'status') if key in record}
        record = {'job_id': job_id, 'model': model, 'operation': operation, 'target': target, 'status': 'running',
                  'started_at': datetime.now(timezone.utc).isoformat()}
        write_record_atomically(jobs / (job_id + '.json'), record)
        write_record_atomically(state_root / 'current.json', {'job_id': job_id})
        try:
            with (state_root / 'worker.log').open('ab') as log:
                subprocess.Popen([*command, '--status-path', str(state_root / 'status.json'), '--lock-fd', str(lock.fileno())],
                                 cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True, pass_fds=(lock.fileno(),))
        except BaseException:
            record['status'] = 'failed'
            record['error'] = '검증 작업을 시작하지 못했습니다.'
            write_record_atomically(jobs / (job_id + '.json'), record)
            raise
    return {'job_id': job_id, 'status': 'running', 'model': model, 'operation': operation}


def start_verification(model, *, target='canonical', request_id=None, state_root=STATE_ROOT):
    return start_backup_job(model, 'verify', target=target, request_id=request_id, state_root=state_root)


def read_verification(job_id, *, state_root=STATE_ROOT):
    if not isinstance(job_id, str) or len(job_id) != 32 or any(char not in '0123456789abcdef' for char in job_id):
        raise ValueError('검증 작업 ID가 올바르지 않습니다.')
    path = Path(state_root) / 'jobs' / (job_id + '.json')
    try:
        record = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        raise ValueError('검증 작업을 찾을 수 없습니다.') from None
    if record.get('status') == 'completed' and record.get('operation') == 'sync':
        result = record.get('result')
        if isinstance(result, dict) and type(result.get('bytes')) is int and result['bytes'] >= 0:
            record['bytes'] = record['total_bytes'] = result['bytes']
    if record.get('status') == 'running':
        try:
            current = json.loads((Path(state_root) / 'current.json').read_text(encoding='utf-8'))
            with (Path(state_root) / 'worker.lock').open('a') as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    active = current.get('job_id') == job_id
                else:
                    active = False
            if not active:
                record['status'] = 'interrupted'
        except (OSError, ValueError, TypeError):
            record['status'] = 'unknown'
    return record


def list_verifications(*, state_root=STATE_ROOT, limit=20):
    jobs = Path(state_root) / 'jobs'
    if not jobs.exists():
        return []
    paths = sorted(jobs.glob('*.json'), key=lambda path: path.stat().st_mtime_ns, reverse=True)
    records = []
    for path in paths[:limit]:
        try:
            record = read_verification(path.stem, state_root=state_root)
            records.append({key: value for key, value in record.items() if key != 'result'})
        except (OSError, ValueError, json.JSONDecodeError):
            records.append({'job_id': path.stem, 'status': 'unknown'})
    return records


def run_worker():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--job-id', required=True)
    parser.add_argument('--state-root', type=Path, required=True)
    parser.add_argument('--status-path', type=Path, required=True)
    parser.add_argument('--lock-fd', type=int, required=True)
    parser.add_argument('--operation', choices=('verify', 'sync'), default='verify')
    parser.add_argument('--target', choices=('canonical', 'latest_snapshot', 'snapshot_manifest'), default='canonical')
    args = parser.parse_args()
    job_path = args.state_root / 'jobs' / (args.job_id + '.json')
    job_path.parent.mkdir(parents=True, exist_ok=True)
    record = {'job_id': args.job_id, 'model': args.model, 'operation': args.operation, 'target': args.target, 'status': 'running',
              'started_at': datetime.now(timezone.utc).isoformat()}
    with os.fdopen(args.lock_fd, 'a'):
        try:
            write_record_atomically(job_path, record)
            last_update = [0.0]
            def report_scan(stage, path, done, total):
                now = time.monotonic()
                if now - last_update[0] >= 1:
                    record.update(stage=stage, current_file=path, file_bytes=done, file_total_bytes=total)
                    write_record_atomically(job_path, record)
                    last_update[0] = now
            if args.operation == 'sync':
                from workflow.common.model_backup_sync import sync_snapshot
                from workflow.common.model_backup_metadata import model_metadata
                try:
                    model_info = model_metadata(args.model)
                except (OSError, ValueError, TypeError, KeyError, ImportError):
                    model_info = {'state': 'unavailable'}
                def report_progress(done, total, path):
                    now = time.monotonic()
                    if now - last_update[0] >= 1:
                        record.pop('file_bytes', None)
                        record.pop('file_total_bytes', None)
                        record.update(stage='스냅샷 복사', bytes=done, total_bytes=total, current_file=path)
                        write_record_atomically(job_path, record)
                        last_update[0] = now
                result = sync_snapshot(args.model, args.job_id, progress=report_progress, model_info=model_info, phase=report_scan)
                record.update(bytes=result['bytes'], total_bytes=result['bytes'])
            else:
                if args.target == 'snapshot_manifest':
                    from workflow.common.model_backup_service import verify_snapshot_manifest
                    result = verify_snapshot_manifest(args.model, progress=report_scan)
                else:
                    result = compare_backup_model(args.model, hash_content=True, target=args.target, progress=report_scan)
            record.pop('file_bytes', None)
            record.pop('file_total_bytes', None)
            record.pop('current_file', None)
            record.update(status='completed', stage='완료', result=result)
        except BaseException as error:
            traceback.print_exc()
            record.update(status='failed', error=str(error))
        record['finished_at'] = datetime.now(timezone.utc).isoformat()
        write_record_atomically(job_path, record)
        write_record_atomically(args.status_path, {'status': record['status']})


if __name__ == '__main__':
    run_worker()
