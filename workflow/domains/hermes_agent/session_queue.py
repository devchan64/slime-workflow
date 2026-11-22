"""세션에 저장된 직접 접수의 기록 상태를 워크플로우 목록에 보탠다."""
from datetime import datetime, timedelta, timezone
from collections import Counter
import hashlib
import json
import re

from .delegation_store import HermesDelegationStore
from .session_store import HermesSessionStore
from .video_operations import read_hermes_video_source_job


def _matches_created_dates(created, filters):
    if not filters.get('created_from') and not filters.get('created_through'):
        return True
    try:
        timestamp = datetime.fromisoformat(created)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        day = timestamp.astimezone(timezone(timedelta(hours=9))).date().isoformat()
    except (TypeError, ValueError):
        return False
    return (not filters.get('created_from') or day >= filters['created_from']) and (not filters.get('created_through') or day <= filters['created_through'])


def append_session_video_jobs(result, payload, session_root=None):
    session_id = payload['session_id']
    store = HermesSessionStore(session_root) if session_root is not None else HermesSessionStore()
    session = store.read_session_record(session_id)
    messages = session['messages']
    forms = [(index, item) for index, item in enumerate(messages) if item.get('form_id')]
    snapshot = hashlib.sha256(json.dumps(messages, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()
    receipts = HermesDelegationStore()
    filters = payload.get('search_filters', {})
    known = {row.get('source_job_id') for row in result['steps'] if row.get('source_job_id')}
    rows = []
    for index, message in reversed(forms[-100:]):
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
        if (filters.get('generator') and filters['generator'].lower() not in 'wan22-fun-control') or filters.get('run_id'):
            continue
        if filters.get('job_id') and not any(filters['job_id'].lower() in (value or '').lower() for value in (job_id, request_id, form_id)):
            continue
        created = message.get('created_at') or ''
        if not _matches_created_dates(created, filters):
            continue
        rows.append({'source_kind':'video_form','generator':'wan22-fun-control','category':'motion',
                     'state':state,'source_job_id':job_id,'request_id':request_id,'form_id':form_id,
                     'created_at':created,'observed_at':observed_at,
                     'message_offset':len(messages)-index-1,'message_snapshot':snapshot})
        if job_id: known.add(job_id)
    return {**result, 'direct_jobs':rows, 'direct_truncated':len(forms)>100, 'session_message_snapshot':snapshot,
            'queried_at':datetime.now(timezone.utc).isoformat()}


def append_session_flux_proposals(result, payload, job_reader, session_root=None):
    """세션 메시지에 속한 유효 FLUX 제안의 접수만 현재 원본과 함께 표시한다."""
    from .delegation_proposal import parse_hermes_flux_proposal
    from .flux_profile_operations import read_hermes_flux_source_job
    from .gpu_handoff_store import GpuHandoffStore
    session_id = payload['session_id']
    store = HermesSessionStore(session_root) if session_root is not None else HermesSessionStore()
    messages = store.read_session_record(session_id)['messages']
    snapshot = hashlib.sha256(json.dumps(messages, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    if result.get('session_message_snapshot', snapshot) != snapshot:
        raise ValueError('세션 이력이 조회 중 변경되었습니다. 다시 조회하세요.')
    receipts = HermesDelegationStore()
    filters = payload.get('search_filters', {})
    rows = list(result.get('direct_jobs', []))
    known = {(row.get('generator'), row.get('source_job_id')) for row in [*result['steps'], *rows] if row.get('source_job_id')}
    candidates = [(index, item) for index, item in enumerate(messages) if isinstance(item.get('job_id'), str)]
    job_counts = Counter(item['job_id'] for _, item in candidates)
    seen = set()
    unreadable = 0
    for index, message in reversed(candidates[-100:]):
        proposal_job = message['job_id']
        if proposal_job in seen:
            continue
        seen.add(proposal_job)
        if job_counts[proposal_job] != 1:
            unreadable += 1
            continue
        try:
            record = job_reader(proposal_job)
            if not isinstance(record, dict) or not isinstance(record.get('status'), dict):
                raise ValueError('작업 기록 형식 오류')
        except (OSError, ValueError, KeyError, TypeError):
            unreadable += 1
            continue
        job_state = record['status'].get('status')
        if job_state not in ('completed', 'queued', 'running', 'failed', 'cancelled', 'canceled'):
            unreadable += 1
            continue
        if job_state != 'completed':
            continue
        answer = record.get('final_response')
        if record.get('final_response_truncated') or not isinstance(answer, str):
            unreadable += 1
            continue
        if 'HERMES_FLUX_PROPOSAL' not in answer:
            continue
        try:
            proposal = parse_hermes_flux_proposal(answer)
            service = proposal.get('service', 'flux-image')
            encoded = json.dumps([session_id, proposal_job, service], ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            request_id = 'flux_' + hashlib.sha256(encoded).hexdigest()
        except (OSError, ValueError, KeyError, TypeError):
            unreadable += 1
            continue
        try:
            receipt = receipts.read_service_delegation(request_id, service)
        except (OSError, ValueError, KeyError, TypeError):
            receipt = {'state':'unknown'}
        handoff_state = None
        observed_at = None
        if receipt.get('state') in ('not_found', 'rejected'):
            try:
                handoff = GpuHandoffStore().read(request_id)
                if handoff is None:
                    if receipt.get('state') == 'not_found':
                        continue
                    handoff_state = 'rejected'
                    observed_at = datetime.now(timezone.utc).isoformat()
                else:
                    if handoff['session_id'] != session_id or handoff['service'] != service:
                        raise ValueError('GPU 양도 요청이 제안과 일치하지 않습니다.')
                    handoff_state = handoff['state']
                    observed_at = datetime.now(timezone.utc).isoformat()
            except (OSError, ValueError, KeyError, TypeError):
                handoff_state = 'unknown'
        job_id = receipt.get('job_id') if receipt.get('state') == 'accepted' else None
        if job_id and (service, job_id) in known:
            continue
        state = {'approved':'queued', 'waiting_release':'queued', 'submitting':'queued',
                 'cancel_waiting_release':'running', 'cancel_reload_queued':'running',
                 'cancel_reloading':'running', 'cancelled':'cancelled', 'withdrawn':'cancelled',
                 'rejected_reload_queued':'running', 'rejected_reloading':'running', 'rejected':'failed'}.get(handoff_state, 'failed' if receipt.get('state') == 'rejected' else 'unknown')
        if job_id:
            try:
                state = read_hermes_flux_source_job(service, job_id)['status']
                observed_at = datetime.now(timezone.utc).isoformat()
            except (OSError, ValueError, KeyError, TypeError):
                pass
        if state == 'canceled': state = 'cancelled'
        if payload['category'] not in ('', 'image') or payload['state'] not in ('', state):
            continue
        if (filters.get('generator') and filters['generator'].lower() not in service.lower()) or filters.get('run_id'):
            continue
        if filters.get('job_id') and not any(filters['job_id'].lower() in (value or '').lower() for value in (job_id, request_id, proposal_job)):
            continue
        created = message.get('created_at') or ''
        if not _matches_created_dates(created, filters): continue
        rows.append({'source_kind':'flux_proposal','generator':service,'category':'image','state':state,
                     'source_job_id':job_id,'request_id':request_id,'proposal_job_id':proposal_job,
                     'handoff_state':handoff_state,'receipt_state':receipt.get('state'),
                     'created_at':created,'observed_at':observed_at,
                     'message_offset':len(messages)-index-1,'message_snapshot':snapshot})
        if job_id: known.add((service, job_id))
    final_messages = store.read_session_record(session_id)['messages']
    final_snapshot = hashlib.sha256(json.dumps(final_messages, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    if final_snapshot != snapshot:
        raise ValueError('세션 이력이 조회 중 변경되었습니다. 다시 조회하세요.')
    return {**result, 'direct_jobs':rows, 'direct_truncated':result.get('direct_truncated', False) or len(candidates)>100,
            'flux_proposal_unreadable_count':unreadable}


def append_session_writer_proposals(result,payload,job_reader,session_root=None):
    """작가 제안의 공유 접수 기록을 세션 작업 목록에 연결한다."""
    from .delegation_proposal import parse_hermes_writer_proposal
    from .gpu_handoff_kimodo import _derived_id
    from .gpu_handoff_store import GpuHandoffStore
    from .writer_operations import read_writer_job_review
    session_id=payload['session_id'];store=HermesSessionStore(session_root) if session_root is not None else HermesSessionStore()
    messages=store.read_session_record(session_id)['messages']
    snapshot=hashlib.sha256(json.dumps(messages,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    if result.get('session_message_snapshot',snapshot)!=snapshot:raise ValueError('세션 이력이 조회 중 변경되었습니다. 다시 조회하세요.')
    rows=list(result.get('direct_jobs',[]));filters=payload.get('search_filters',{});receipts=HermesDelegationStore()
    candidates=[(index,item) for index,item in enumerate(messages) if isinstance(item.get('job_id'),str)]
    counts=Counter(item['job_id'] for _,item in candidates);unreadable=0
    for index,message in reversed(candidates[-100:]):
        job=message['job_id']
        if counts[job]!=1:continue
        try:
            record=job_reader(job)
            if record['status'].get('status')!='completed' or record.get('final_response_truncated'):continue
            answer=record.get('final_response')
            if not isinstance(answer,str) or 'HERMES_WRITER_PROPOSAL' not in answer:continue
            parse_hermes_writer_proposal(answer)
            request_id='writer_'+hashlib.sha256(json.dumps([session_id,job],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
            receipt=receipts.read_service_delegation(_derived_id('handoff_',request_id),'writer-agent')
            handoff_store=GpuHandoffStore();handoff=handoff_store.read(request_id)
            if handoff is None:
                withdrawal=handoff_store.read_withdrawal(request_id,session_id)
                if withdrawal is not None:handoff={'session_id':session_id,'service':'writer-agent','state':'withdrawn'}
            if handoff and (handoff['session_id']!=session_id or handoff['service']!='writer-agent'):raise ValueError('작가 양도 기록 불일치')
        except (OSError,ValueError,KeyError,TypeError):unreadable+=1;continue
        if receipt['state']=='not_found' and handoff is None:continue
        handoff_state=handoff['state'] if handoff else None
        job_id=receipt.get('job_id') if receipt['state']=='accepted' else None
        state={'approved':'queued','waiting_release':'queued','submitting':'queued','running':'running','cancel_waiting_release':'running','cancel_reload_queued':'running','cancel_reloading':'running','cancelled':'cancelled','withdrawn':'cancelled','rejected_reload_queued':'running','rejected_reloading':'running','rejected':'failed'}.get(handoff_state,'failed' if receipt['state']=='rejected' else 'unknown')
        if job_id:
            try:
                stage=read_writer_job_review(job_id,current_include_diagnostics=False)['stage']
                state={'queued':'queued','preparing':'running','indexing':'running','searching':'running','reasoning':'running','review':'completed','completed':'completed','applied':'completed','failed':'failed','interrupted':'cancelled'}.get(stage,'unknown')
            except (OSError,ValueError,KeyError,TypeError):pass
        if payload['category'] or payload['state'] not in ('',state) or filters.get('run_id'):continue
        if filters.get('generator') and filters['generator'].lower() not in 'writer-agent':continue
        if filters.get('job_id') and not any(filters['job_id'].lower() in (value or '').lower() for value in (job_id,request_id,job)):continue
        created=message.get('created_at') or ''
        if not _matches_created_dates(created,filters):continue
        rows.append({'source_kind':'writer_proposal','generator':'writer-agent','category':'writer','state':state,'source_job_id':job_id,
                     'request_id':request_id,'proposal_job_id':job,'handoff_state':handoff_state,'receipt_state':receipt['state'],
                     'created_at':created,'observed_at':datetime.now(timezone.utc).isoformat(),
                     'message_offset':len(messages)-index-1,'message_snapshot':snapshot})
    final=store.read_session_record(session_id)['messages']
    if hashlib.sha256(json.dumps(final,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()!=snapshot:raise ValueError('세션 이력이 조회 중 변경되었습니다. 다시 조회하세요.')
    return {**result,'direct_jobs':rows,'direct_truncated':result.get('direct_truncated',False) or len(candidates)>100,'writer_proposal_unreadable_count':unreadable}
