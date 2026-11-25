"""Reuse a completed chat proposal and the user's reference from its original snapshot."""
import base64
import json
import re
import subprocess
from pathlib import Path

from .delegation_store import HermesDelegationStore
from .flux_reports import proposal_request_id
from .gpu_handoff_store import GpuHandoffStore
from .session_store import HermesSessionStore
from .reference_intent import requires_reference, without_reference

GENERATE = {'생성해', '생성해줘', '생성해주세요', '생성해라', '생성해보자', '생성한다', '생성할게', '생성하자', '생성합니다'}
CONSENT = 'GPU 양도에 동의'
WORKFLOW_ROOT = Path(__file__).resolve().parents[3]


def _reference_paths(text):
    if not isinstance(text, str):
        return []
    prefixes = ('/workspace/', str(WORKFLOW_ROOT) + '/')
    pattern = r'(?:' + '|'.join(re.escape(prefix) for prefix in prefixes) + r')(baseline/[A-Za-z0-9_./-]+\.png)'
    paths = list(dict.fromkeys(re.findall(pattern,text)))
    if any('..' in path.split('/') or '.' in path.split('/') for path in paths):
        raise ValueError('참조 이미지 경로를 확인하세요.')
    return paths


def proposal_reference_paths(message, detail, answer):
    """Bind a reference to user-authored paths and the proposal's own description."""
    direct = _reference_paths(message.get('text',''))
    if direct:
        if len(direct)>2: raise ValueError('참조 이미지는 최대 2장입니다.')
        return direct
    request=detail.get('request') or {}
    context=request.get('context') if isinstance(request,dict) else None
    messages=context.get('messages',[]) if isinstance(context,dict) else []
    mentioned=set(_reference_paths(answer))
    for item in reversed(messages if isinstance(messages,list) else []):
        if not isinstance(item,dict) or item.get('role')!='user':continue
        paths=_reference_paths(item.get('content',''))
        if paths:
            matched=[path for path in paths if path in mentioned]
            if len(matched)!=len(paths) or len(matched)>2:
                raise ValueError('이전 요청과 생성 제안의 참조 이미지가 일치하지 않습니다. 폼에서 참조를 확인하세요.')
            return matched
    return []


def snapshot_reference_images(directory, paths):
    """Read requested baseline PNGs from the immutable proposal snapshot."""
    commit = json.loads((directory/'baseline.json').read_text())['baseline_commit']
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('제안 시점의 참조 버전을 확인하세요.')
    images = []
    for path in paths:
        blob = subprocess.check_output(['git','-C',str(directory/'workspace'),'show',commit+':'+path],timeout=10)
        if len(blob)>3*1024*1024 or not blob.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('참조 PNG를 확인하세요.')
        images.append(base64.b64encode(blob).decode('ascii'))
    return images


def image_submission_intent(prompt):
    if not isinstance(prompt, str):
        return None
    normalized = re.sub(r'\s+', '', re.sub(r'[.!。！]+$', '', prompt.strip()).strip())
    if normalized in GENERATE:
        return 'generate'
    return 'consent' if normalized == 'GPU양도에동의' else None


def submit_chat_flux(manager, session_id, prompt):
    store = HermesSessionStore(manager.hermes_session_root) if manager.hermes_session_root else HermesSessionStore()
    session = store.read_session_record(session_id)
    intent = image_submission_intent(prompt)
    if not intent:
        return {'handled': False}
    command = manager.execute_hermes_command
    for message in reversed(session['messages']):
        job = message.get('job_id')
        if not job or message.get('report_job_id'):
            continue
        detail = manager.read_context_job(job)
        answer = detail.get('final_response') or ''
        if any(marker in answer for marker in ('HERMES_IMAGE_PROPOSAL', 'HERMES_FLUX_PROPOSAL')):
            proposal = command('hermes-flux-proposal', {'id': job})['proposal']
            break
        if re.search(r'HERMES_[A-Z_]+_PROPOSAL', answer):
            return {'handled': False}
    else:
        return {'handled': False}
    service = proposal.get('service', 'flux-image')
    if not service.startswith('flux-') and service!='minimax-h3-image':
        return {'handled': False}
    rid = proposal_request_id(session_id, job, service)
    receipt = HermesDelegationStore().read_service_delegation(rid, service)
    def accepted(job_id):
        store.append_result_notice(session_id, 'queued_'+rid, f'{service} 이미지 생성 대기열에 등록했습니다. 작업 ID: {job_id}')
        return {'handled': True, 'state': 'accepted', 'job_id': job_id}
    if receipt.get('state') == 'accepted':
        return accepted(receipt['job_id'])
    handoff = GpuHandoffStore().read(rid)
    if handoff:
        return {'handled': True, 'state': handoff['state']}
    if receipt.get('state') != 'not_found':
        raise ValueError('기존 FLUX 접수 상태를 먼저 확인하세요.')
    request = {k: proposal[k] for k in ('prompt', 'width', 'height', 'seed')}
    request.update(action='generate', steps=16, images=[])
    directory = manager.resolve_hermes_job_path(job)
    form = None
    if service == 'minimax-h3-image':
        from hashlib import sha256
        form_id = sha256(('minimax-form:'+rid).encode()).hexdigest()[:32]
        forms = command('hermes-minimax-form-list',dict(session_id=session_id))['forms']
        if any(row['form_id']==form_id for row in forms):
            form = command('hermes-minimax-form-read',dict(session_id=session_id,form_id=form_id))
    refs = [] if (form and form['request'].get('images')) or without_reference(proposal.get('prompt')) else proposal_reference_paths(message, detail, answer)
    if refs:
        commit = json.loads((directory/'baseline.json').read_text())['baseline_commit']
        if not re.fullmatch('[0-9a-f]{40}',commit):
            raise ValueError('제안 시점의 참조 버전을 확인하세요.')
        for path in refs:
            blob = subprocess.check_output(['git','-C',str(directory/'workspace'),'show',commit+':'+path],timeout=10)
            if len(blob)>10*1024*1024 or not blob.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError('참조 PNG를 확인하세요.')
            request['images'].append(base64.b64encode(blob).decode('ascii'))
    target = request
    if service == 'minimax-h3-image':
        request['steps'] = 6
        if form:
            if refs and not form['request'].get('images') and form['state']=='editing':
                payload=dict(form['request'],images=request['images'])
                form=command('hermes-minimax-form-save',dict(session_id=session_id,form_id=form_id,revision=form['revision'],request=payload))
        else:
            form=command('hermes-minimax-form-create',dict(session_id=session_id,form_id=form_id,proposal_job_id=job,service=service,request=request))
        target=dict(form_id=form_id,revision=form['revision'],request=form['request'])
        request=form['request']
    if requires_reference(proposal.get('prompt')) and not request.get('images'):
        raise ValueError('참조 이미지가 필요한 제안입니다. 생성 폼에 참조 PNG를 첨부하고 저장한 뒤 다시 확인하세요.')
    owner = command('hermes-resident-status', {'session_id': session_id})
    if owner['resident']['state']=='not_found':
        if service == 'minimax-h3-image':
            result=command('hermes-minimax-form-submit',dict(session_id=session_id,form_id=form_id,revision=form['revision']))
        else:
            result=command('hermes-delegate-flux-profile',dict(request_id=rid,service=service,request=request,session_id=session_id,proposal_job_id=job))
        if result.get('state')!='accepted':
            raise ValueError('FLUX 접수 결과 확인 필요')
        return accepted(result['job_id'])
    values=dict(session_id=session_id,resident_id=owner['resident_id'],service=service,request=target)
    review=command('hermes-gpu-handoff-preview',values)
    notice_id='consent_'+review['review_hash']
    if intent!='consent' or not any(m['request_id']==notice_id and m.get('result_notice') for m in session['messages']):
        store.append_result_notice(session_id,notice_id,f'{service} · {request["width"]}×{request["height"]} · 시드 {request["seed"]} · 참조 {len(request["images"])}장. 현재 대화가 끝나면 Qwen을 해제해 이미지를 생성하고 다시 적재합니다. 진행하려면 “GPU 양도에 동의”라고 답해 주세요.')
        return {'handled':True,'state':'awaiting_consent'}
    result=command('hermes-gpu-handoff-approve',dict(values,request_id=rid,review_hash=review['review_hash'],confirmed=True))
    store.append_result_notice(session_id,'approved_'+rid,'GPU 양도에 동의했습니다. 이미지 접수가 확인되면 이 대화에 작업 ID를 전달합니다.')
    return {'handled':True,'state':result['state']}
