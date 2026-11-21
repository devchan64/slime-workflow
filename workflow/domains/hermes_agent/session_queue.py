"""세션에 저장된 직접 접수의 기록 상태를 워크플로우 목록에 보탠다."""
from datetime import datetime, timezone
import hashlib
import re

from .delegation_store import HermesDelegationStore
from .session_store import HermesSessionStore
from .video_operations import read_hermes_video_source_job


def append_session_video_jobs(result, payload, session_root=None):
    session_id = payload['session_id']
    store = HermesSessionStore(session_root) if session_root is not None else HermesSessionStore()
    session = store.read_session_record(session_id)
    forms = [item for item in session['messages'] if item.get('form_id')]
    receipts = HermesDelegationStore()
    filters = payload.get('search_filters', {})
    known = {row.get('source_job_id') for row in result['steps'] if row.get('source_job_id')}
    rows = []
    for message in reversed(forms[-100:]):
        form_id = message.get('form_id')
        if not isinstance(form_id, str) or not re.fullmatch(r'[a-f0-9]{32}', form_id):
            continue
        request_id = 'vf_' + hashlib.sha256((session_id + ':' + form_id).encode()).hexdigest()
        try:
            receipt = receipts.read_service_delegation(request_id, 'wan22-fun-control')
        except (OSError, ValueError, KeyError, TypeError):
            receipt = {'state': 'unknown'}
        if receipt.get('state') == 'not_found':
            continue
        job_id = receipt.get('job_id') if receipt.get('state') == 'accepted' else None
        if job_id in known:
            continue
        state = 'unknown'
        observed_at = None
        if job_id:
            try:
                observed = read_hermes_video_source_job('wan22-fun-control', job_id)
                state = observed['status']
                observed_at = observed.get('queried_at')
            except (OSError, ValueError, KeyError, TypeError):
                pass
        if state == 'canceled': state = 'cancelled'
        if payload['category'] not in ('', 'motion') or payload['state'] not in ('', state):
            continue
        if filters.get('generator') not in (None, '', 'wan22-fun-control') or filters.get('run_id'):
            continue
        if filters.get('job_id') and filters['job_id'] not in (job_id, request_id, form_id):
            continue
        created = message.get('created_at') or ''
        if filters.get('created_from') and created[:10] < filters['created_from']:
            continue
        if filters.get('created_through') and created[:10] > filters['created_through']:
            continue
        rows.append({'source_kind':'video_form','generator':'wan22-fun-control','category':'motion',
                     'state':state,'source_job_id':job_id,'request_id':request_id,'form_id':form_id,
                     'created_at':created,'observed_at':observed_at})
        if job_id: known.add(job_id)
    return {**result, 'direct_jobs':rows, 'direct_truncated':len(forms)>100,
            'queried_at':datetime.now(timezone.utc).isoformat()}
