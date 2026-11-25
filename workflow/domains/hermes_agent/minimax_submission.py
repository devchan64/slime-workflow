"""헤르메스 대화의 MiniMax 제안과 생성 접수를 한 번만 연결한다."""
import re
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore, validate_service_job_identifier
from workflow.domains.hermes_agent.flux_reports import proposal_request_id

SERVICES = ('minimax-h3-image', 'minimax-h3-i2v')


def submission_digest(service, request):
    import hashlib
    import json
    if service not in SERVICES or not isinstance(request, dict):
        raise ValueError('MiniMax 접수 입력 오류')
    payload = json.dumps({'service':service, 'request':request}, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def validate_origin(origin, service):
    if service not in SERVICES or not isinstance(origin, dict) or set(origin) != {'session_id', 'proposal_job_id', 'request_id'}:
        raise ValueError('MiniMax 대화 접수 정보 오류')
    session, job, request = origin['session_id'], origin['proposal_job_id'], origin['request_id']
    if not isinstance(session, str) or not re.fullmatch(r'[a-f0-9]{32}', session) or not validate_service_job_identifier(service, job):
        raise ValueError('MiniMax 대화 또는 제안 식별자 오류')
    if request != proposal_request_id(session, job, service):
        raise ValueError('MiniMax 접수 식별자가 제안과 일치하지 않습니다.')


def resolve_proposal(origin, service, *, sessions, read_job):
    validate_origin(origin, service)
    session = sessions.read_session_record(origin['session_id'])
    if sum(isinstance(message, dict) and message.get('job_id') == origin['proposal_job_id'] for message in session.get('messages', [])) != 1:
        raise ValueError('대화의 생성 제안을 확인할 수 없습니다.')
    job = read_job(origin['proposal_job_id'])
    if job.get('status', {}).get('status') != 'completed' or job.get('final_response_truncated'):
        raise ValueError('완료된 생성 제안을 확인할 수 없습니다.')
    if service == 'minimax-h3-image':
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_image_proposal
        from workflow.domains.hermes_agent.image_selection import select_image_proposal
        from workflow.domains.minimax_h3_image.generation import MiniMaxH3ImageManager
        proposal = select_image_proposal(parse_hermes_image_proposal(job.get('final_response')), job['request'])
        manager = MiniMaxH3ImageManager()
    else:
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_video_proposal
        from workflow.domains.hermes_agent.video_selection import select_video_proposal
        from workflow.domains.minimax_h3.generation import MiniMaxH3GenerationManager
        proposal = select_video_proposal(parse_hermes_video_proposal(job.get('final_response')), job['request'])
        manager = MiniMaxH3GenerationManager()
    if proposal.get('service') != service:
        raise ValueError('확정된 생성 제안과 서비스가 일치하지 않습니다.')
    return proposal, manager


def submit_from_proposal(payload, *, sessions, read_job, dispatch, store=None):
    if not isinstance(payload, dict) or set(payload) != {'session_id', 'proposal_job_id', 'request_id', 'service', 'request'}:
        raise ValueError('대화·제안·서비스·생성 요청이 필요합니다.')
    service = payload['service']
    origin = {key: payload[key] for key in ('session_id', 'proposal_job_id', 'request_id')}
    _, manager = resolve_proposal(origin, service, sessions=sessions, read_job=read_job)
    return (store or HermesDelegationStore()).execute_service_delegation_once(
        origin['request_id'], service, payload['request'],
        lambda request: dispatch(service, 'generate', {**request, '_minimax_report_origin': origin}),
        manager.validate_generation_request)


def read_report_status(payload, *, sessions, store=None):
    """원 제안과 접수 기록을 확인한 뒤 보고 상태만 공개한다."""
    import json
    if not isinstance(payload, dict) or set(payload) != {'session_id', 'proposal_job_id', 'request_id', 'service'}:
        raise ValueError('대화·제안·접수 ID와 서비스가 필요합니다.')
    service = payload['service']
    origin = {key: payload[key] for key in ('session_id', 'proposal_job_id', 'request_id')}
    validate_origin(origin, service)
    session = sessions.read_session_record(origin['session_id'])
    if sum(isinstance(message, dict) and message.get('job_id') == origin['proposal_job_id'] for message in session.get('messages', [])) != 1:
        raise ValueError('대화의 생성 제안을 확인할 수 없습니다.')
    receipt = (store or HermesDelegationStore()).read_service_delegation(origin['request_id'], service)
    if receipt.get('state') != 'accepted':
        return {'receipt': receipt, 'report': None}
    if service == 'minimax-h3-image':
        from generators.minimax_h3_image.contracts import STORAGE
    else:
        from generators.minimax_h3.contracts import JOB_STORAGE as STORAGE
    root = STORAGE / receipt['job_id']
    path = root / 'hermes-report.json'
    if STORAGE.is_symlink() or root.is_symlink() or path.is_symlink():
        raise ValueError('보고서 상태를 확인할 수 없습니다.')
    if not path.exists():
        return {'receipt':receipt, 'report':{'state':'unknown','generation_state':'unknown',
                                              'last_error':'보고서 기록을 확인할 수 없습니다.', 'retry_available':False}}
    if not path.is_file() or path.stat().st_size > 4_000_000:
        raise ValueError('보고서 상태를 확인할 수 없습니다.')
    record = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(record, dict) or record.get('origin') != origin or record.get('state') not in ('waiting','analyzing','report_queued','writing','completed','failed'):
        raise ValueError('보고서 기록이 접수와 일치하지 않습니다.')
    from workflow.domains.hermes_agent.minimax_report_lifecycle import report_retry_available
    from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record
    try:
        generation = read_bounded_delegation_record(root/'status.json')
        generation_state = generation.get('status') if isinstance(generation, dict) else None
    except (OSError, ValueError, TypeError):
        generation_state = None
    revision = record.get('retry_revision', 0)
    if type(revision) is not int or not 0 <= revision <= 10:
        raise ValueError('보고서 재시도 기록 오류')
    report = {key:record[key] for key in ('state','last_error','error','hermes_job_id','writer_status') if key in record}
    retry_available = report_retry_available(record, generation_state)
    if retry_available:
        try:
            from workflow.domains.hermes_agent.minimax_report_evidence import inspect_minimax_result
            inspect_minimax_result(root, service)
        except (OSError, ValueError, KeyError, TypeError):
            retry_available = False
            report['retry_unavailable_reason'] = '생성 결과 무결성을 확인할 수 없습니다.'
    report.update(retry_revision=revision, retry_available=retry_available,
                  generation_state=generation_state if generation_state in ('queued','running','completed','failed','cancelled','canceled') else 'unknown')
    return {'receipt':receipt, 'report':report}


def retry_report(payload, *, sessions, store=None):
    """조회한 보고 리비전의 실패만 잠금 안에서 다시 대기시킨다."""
    import fcntl
    import os
    from workflow.common.generation_records import write_record_atomically
    from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record
    from workflow.domains.hermes_agent.minimax_report_evidence import inspect_minimax_result
    from workflow.domains.hermes_agent.minimax_report_lifecycle import REPORT_FILE
    if not isinstance(payload, dict) or set(payload) != {'session_id','proposal_job_id','request_id','service','expected_revision'}:
        raise ValueError('대화·접수 정보와 보고서 리비전이 필요합니다.')
    expected = payload['expected_revision']
    if type(expected) is not int or not 0 <= expected < 10:
        raise ValueError('보고서 재시도 리비전 오류')
    base = {key:value for key,value in payload.items() if key != 'expected_revision'}
    current = read_report_status(base, sessions=sessions, store=store)
    if current['receipt'].get('state') != 'accepted':
        raise ValueError('생성 접수 기록을 확인할 수 없습니다.')
    service = base['service']
    if service == 'minimax-h3-image':
        from generators.minimax_h3_image.contracts import STORAGE
    else:
        from generators.minimax_h3.contracts import JOB_STORAGE as STORAGE
    directory = STORAGE / current['receipt']['job_id']
    if STORAGE.is_symlink() or directory.is_symlink() or not directory.is_dir():
        raise ValueError('생성 작업 경로를 확인할 수 없습니다.')
    report_fd = os.open(directory/'hermes-report.lock', os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW, 0o600)
    with os.fdopen(report_fd,'r+') as report_lock:
        try:
            fcntl.flock(report_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            execution_fd = os.open(directory/'execution.lock', os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW, 0o600)
            with os.fdopen(execution_fd,'r+') as execution_lock:
                fcntl.flock(execution_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                current = read_report_status(base, sessions=sessions, store=store)
                report = current.get('report') or {}
                if report.get('retry_revision') != expected or report.get('retry_available') is not True:
                    raise ValueError('보고서 상태가 변경됐거나 재시도할 수 없습니다. 다시 조회하세요.')
                # 결과가 여전히 완료 상태이고 검사 가능한지 확인한다. 재생성하지 않는다.
                inspect_minimax_result(directory,service)
                path = directory/REPORT_FILE
                record = read_bounded_delegation_record(path)
                history = record.get('retry_history', [])
                if not isinstance(history,list) or len(history) != expected:
                    raise ValueError('보고서 재시도 이력이 일치하지 않습니다.')
                history.append({key:record[key] for key in ('state','error','report_request_id','hermes_job_id') if key in record})
                for key in ('evidence','observations','report_request_id','report_prompt','hermes_job_id','writer_status','writing_notice_sent','body','last_error','retry_at','error'):
                    record.pop(key,None)
                record.update(state='waiting', retry_revision=expected+1, retry_history=history)
                write_record_atomically(path,record)
                return {'state':'waiting','retry_revision':expected+1,'job_id':directory.name}
        except BlockingIOError as error:
            raise ValueError('보고 처리 또는 작업 정리 중입니다. 상태를 다시 확인하세요.') from error


def recover_completed_submission(directory, service, origin, *, store=None):
    """응답 유실 후 유일하고 완료된 원 작업만 접수 기록에 연결한다."""
    import json
    from pathlib import Path
    from workflow.common.generation_records import write_record_atomically
    from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record
    from workflow.domains.hermes_agent.minimax_report_evidence import inspect_minimax_result
    validate_origin(origin, service)
    directory = Path(directory)
    root = directory.parent
    if root.is_symlink() or directory.is_symlink() or not validate_service_job_identifier(service, directory.name):
        raise ValueError('복구할 작업 경로 오류')
    store = store or HermesDelegationStore()
    with store.hold_delegation_storage_lock():
        receipt_path = store.resolve_delegation_record_path(origin['request_id'])
        receipt = read_bounded_delegation_record(receipt_path)
        if (not isinstance(receipt, dict) or receipt.get('version') != 2 or receipt.get('id') != origin['request_id']
                or receipt.get('service') != service or receipt.get('state') != 'dispatching'):
            return False
        marker = read_bounded_delegation_record(directory/'hermes-report.json')
        if not isinstance(marker, dict):
            raise ValueError('보고서 기록 형식 오류')
        digest = marker.get('submission_sha256')
        if (marker.get('origin') != origin or not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest)
                or digest != receipt.get('request_sha256')):
            return False
        matches = []
        for path in root.glob('*/hermes-report.json'):
            if path.is_symlink() or path.parent.is_symlink() or not validate_service_job_identifier(service, path.parent.name):
                continue
            candidate = read_bounded_delegation_record(path)
            if isinstance(candidate, dict) and candidate.get('origin') == origin and candidate.get('submission_sha256') == digest:
                matches.append(path.parent)
        if matches != [directory]:
            return False
        command = read_bounded_delegation_record(directory/'gpu-command.json')
        if not isinstance(command, dict):
            raise ValueError('GPU 실행 기록 형식 오류')
        values = command.get('command')
        expected_runner = 'generators/minimax_h3_image/worker.py' if service == 'minimax-h3-image' else 'generators/minimax_h3/worker.py'
        expected_runner = Path(__file__).resolve().parents[3] / expected_runner
        if (command.get('service') != service or not isinstance(values, list) or len(values) != 4
                or not isinstance(values[1], str) or Path(values[1]).resolve() != expected_runner
                or values[2:] != ['--job-dir', str(directory)]):
            return False
        # 잠금을 보유한 호출자만 진입하며, 결과가 완성된 경우에만 복구한다.
        inspect_minimax_result(directory, service)
        receipt.update(state='accepted', job_id=directory.name)
        write_record_atomically(receipt_path, receipt)
        return True
