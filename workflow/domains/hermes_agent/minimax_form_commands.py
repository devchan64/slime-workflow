"""Gateway operations for persisted, versioned MiniMax form instances."""
from pathlib import Path
import hashlib

from workflow.domains.hermes_agent.flux_reports import proposal_request_id
from workflow.domains.hermes_agent.minimax_form_store import MiniMaxFormStore
from workflow.domains.hermes_agent.minimax_submission import resolve_proposal, submission_digest, submit_from_proposal
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore


def execute_minimax_form_command(command, payload, *, sessions, read_job, dispatch, forms=None, receipts=None, resolve_job_path=None):
    fields = {
        'hermes-minimax-form-create': {'session_id', 'form_id', 'proposal_job_id', 'service', 'request'},
        'hermes-minimax-form-prepare': {'session_id', 'proposal_job_id', 'service'},
        'hermes-minimax-form-list': {'session_id'},
        'hermes-minimax-form-read': {'session_id', 'form_id'},
        'hermes-minimax-form-save': {'session_id', 'form_id', 'revision', 'request'},
        'hermes-minimax-form-update': {'session_id', 'form_id', 'revision', 'request'},
        'hermes-minimax-form-submit': {'session_id', 'form_id', 'revision'},
    }
    if command not in fields or not isinstance(payload, dict) or set(payload) != fields[command]:
        raise ValueError('폼 명령 입력 형식 오류')
    session_id = payload['session_id']
    sessions.read_session_record(session_id)
    forms = forms or MiniMaxFormStore(Path(sessions.session_storage_root) / 'minimax-forms.sqlite3')
    def reconcile(form):
        if form['state'] == 'editing':
            expected = proposal_request_id(session_id, form['source_job_id'], form['service'])
            receipt = (receipts or HermesDelegationStore()).read_service_delegation(expected, form['service'])
            if receipt.get('state') in ('accepted', 'unknown', 'rejected'):
                return {**form, 'state':'external_receipt', 'receipt_state':receipt['state'], 'job_id':receipt.get('job_id')}
            return form
        if form['state'] != 'submitting':
            return form
        expected = proposal_request_id(session_id, form['source_job_id'], form['service'])
        if form.get('request_id') != expected:
            raise ValueError('폼 접수 ID가 제안과 일치하지 않습니다.')
        receipt = (receipts or HermesDelegationStore()).read_service_delegation(
            expected, form['service'], expected_request_sha256=submission_digest(form['service'], form['request']))
        if receipt.get('state') == 'accepted':
            return forms.mark_accepted(session_id, form['form_id'], expected, receipt['job_id'])
        # Absence or an indeterminate receipt cannot prove that dispatch did not
        # reach the generator. Keep the pinned version and never dispatch here.
        return {**form, 'receipt_state':receipt.get('state', 'unknown')}
    if command == 'hermes-minimax-form-list':
        rows = forms.list(session_id)
        for index, row in enumerate(rows):
            if row['state'] in ('editing', 'submitting'):
                recovered = reconcile(forms.read(session_id, row['form_id']))
                rows[index] = {key:value for key,value in recovered.items() if key not in ('request', 'sha256')}
        return {'forms': rows}
    if command == 'hermes-minimax-form-prepare':
        service, job = payload['service'], payload['proposal_job_id']
        request_id = proposal_request_id(session_id, job, service)
        origin = {'session_id':session_id, 'proposal_job_id':job, 'request_id':request_id}
        proposal, _ = resolve_proposal(origin, service, sessions=sessions, read_job=read_job)
        form_id = hashlib.sha256(('minimax-form:' + request_id).encode()).hexdigest()[:32]
        if service == 'minimax-h3-image':
            request = {'action':'generate', 'prompt':proposal['prompt'], 'images':[], 'width':proposal['width'],
                       'height':proposal['height'], 'steps':6, 'seed':proposal['seed']}
        else:
            request = {'action':'generate', 'prompt':proposal['prompt'], 'images':[], 'width':832, 'height':480,
                       'frames':124, 'steps':8, 'seed':42}
        # A previous submission through the legacy proposal path must not appear
        # as a fresh editable form.  Unknown/rejected receipts need reconciliation.
        existing = next((item for item in forms.list(session_id) if item['form_id'] == form_id), None)
        if not existing and (receipts or HermesDelegationStore()).read_service_delegation(request_id, service).get('state') != 'not_found':
            raise ValueError('기존 접수가 있어 폼을 새로 만들 수 없습니다. 원 접수 상태를 확인하세요.')
        if service == 'minimax-h3-image' and resolve_job_path:
            from workflow.domains.hermes_agent.flux_chat_submission import proposal_reference_paths, snapshot_reference_images
            detail = read_job(job)
            session = sessions.read_session_record(session_id)
            message = next(item for item in session['messages'] if item.get('job_id') == job)
            paths = proposal_reference_paths(message, detail, detail.get('final_response') or '')
            if paths:
                request['images'] = snapshot_reference_images(resolve_job_path(job), paths)
                if existing:
                    current = reconcile(forms.read(session_id, form_id))
                    pristine = {**request, 'images':[]}
                    if current['state'] == 'editing' and current['revision'] == 1 and current['request'] == pristine:
                        return forms.save(session_id, form_id, current['revision'], request)
                    return current
        return forms.create(session_id, form_id, service, job, request)
    form_id = payload['form_id']
    if command == 'hermes-minimax-form-create':
        service, job = payload['service'], payload['proposal_job_id']
        request_id = proposal_request_id(session_id, job, service)
        expected_form_id = hashlib.sha256(('minimax-form:' + request_id).encode()).hexdigest()[:32]
        if form_id != expected_form_id:
            raise ValueError('폼 ID가 원 제안과 일치하지 않습니다.')
        resolve_proposal({'session_id':session_id, 'proposal_job_id':job, 'request_id':request_id}, service,
                         sessions=sessions, read_job=read_job)
        existing = next((item for item in forms.list(session_id) if item['form_id'] == form_id), None)
        if not existing and (receipts or HermesDelegationStore()).read_service_delegation(request_id, service).get('state') != 'not_found':
            raise ValueError('기존 접수가 있어 폼을 새로 만들 수 없습니다. 원 접수 상태를 확인하세요.')
        return forms.create(session_id, form_id, service, job, payload['request'])
    if command == 'hermes-minimax-form-read':
        return reconcile(forms.read(session_id, form_id))
    if command == 'hermes-minimax-form-save':
        if reconcile(forms.read(session_id, form_id))['state'] != 'editing':
            raise ValueError('기존 접수 상태를 확인하세요.')
        return forms.save(session_id, form_id, payload['revision'], payload['request'])
    if command == 'hermes-minimax-form-update':
        changes = payload['request']
        if not isinstance(changes, dict) or not changes or set(changes) - {'prompt', 'seed', 'width', 'height'}:
            raise ValueError('변경할 프롬프트·시드·크기만 전달하세요.')
        form = reconcile(forms.read(session_id, form_id))
        if form['revision'] != payload['revision'] or form['state'] != 'editing':
            raise ValueError('폼이 변경됐거나 접수가 시작됐습니다. 최신 상태를 확인하세요.')
        request = {**form['request'], **changes}
        prompt, seed = request.get('prompt'), request.get('seed')
        max_seed = 2147483647 if form['service'] == 'minimax-h3-i2v' else 4294967295
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 8000 or type(seed) is not int or not 0 <= seed <= max_seed:
            raise ValueError('프롬프트 또는 시드를 확인하세요.')
        width, height = request.get('width'), request.get('height')
        if form['service'] == 'minimax-h3-image':
            if any(type(size) is not int or not 480 <= size <= 2048 or size % 32 for size in (width, height)):
                raise ValueError('이미지 크기는 480~2048의 32배수여야 합니다.')
        elif (type(width) is not int or type(height) is not int or (width, height) not in ((832, 480), (768, 448))):
            raise ValueError('영상 크기는 832×480 또는 768×448이어야 합니다.')
        if 'prompt' in changes:
            request.pop('expected_prompt_sha256', None)
        return forms.save(session_id, form_id, payload['revision'], request)
    form = reconcile(forms.read(session_id, form_id))
    if form['state'] == 'external_receipt':
        raise ValueError('기존 접수 상태를 확인하세요.')
    service, job = form['service'], form['source_job_id']
    request_id = proposal_request_id(session_id, job, service)
    origin = {'session_id':session_id, 'proposal_job_id':job, 'request_id':request_id}
    _, manager = resolve_proposal(origin, service, sessions=sessions, read_job=read_job)
    manager.validate_generation_request(form['request'])
    form = forms.pin_submission(session_id, form_id, payload['revision'], request_id)
    result = submit_from_proposal({**origin, 'service':service, 'request':form['request']}, sessions=sessions,
                                  read_job=read_job, dispatch=dispatch, store=receipts)
    if result.get('state') == 'accepted':
        forms.mark_accepted(session_id, form_id, request_id, result['job_id'])
    return result
