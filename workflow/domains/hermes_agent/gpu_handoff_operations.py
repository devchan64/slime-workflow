"""Kimodo GPU 양도 확인의 입력·세션·모델을 하나의 검토값으로 고정한다."""
import hashlib
import hmac
import re

from generators.kimodo.contracts import validate_kimodo_request
from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore, _canonical_input
from workflow.domains.hermes_agent.resident_queue import inspect_resident
from workflow.domains.hermes_agent.session_store import HermesSessionStore
from workflow.domains.hermes_agent.management_observer import read_hermes_gpu_reservation_snapshot


def _review_hash(session_id, resident_id, request, service='kimodo'):
    binding = {'session_id':session_id, 'resident_id':resident_id, 'model':'qwen3.8-27b',
               'service':service, 'request':request}
    return hashlib.sha256(_canonical_input(binding)).hexdigest()


def preview_handoff(session_id, resident_id, service, request, *, session_store=None, resident_inspector=inspect_resident,
                           reservation_snapshot=read_hermes_gpu_reservation_snapshot):
    """승인 없이 확인 대상과 유효한 상주 모델만 읽는다."""
    (session_store or HermesSessionStore()).read_session_record(session_id)
    if service == 'kimodo':
        validate_kimodo_request(request)
    elif service == 'minimax-h3-image':
        from .gpu_handoff_minimax_image import verify_form
        verify_form(session_id,request)
    elif service == 'writer-agent':
        from workflow.domains.hermes_agent.gpu_handoff_writer import validate_bound_writer_request
        validate_bound_writer_request(request)
    else:
        from workflow.domains.hermes_agent.video_operations import HERMES_VIDEO_SERVICES, validate_hermes_video_request
        from workflow.domains.hermes_agent.audio_operations import HERMES_AUDIO_SERVICES, validate_hermes_audio_request
        if service in HERMES_VIDEO_SERVICES:
            validate_hermes_video_request(service, request)
        elif service in HERMES_AUDIO_SERVICES:
            validate_hermes_audio_request(service, request)
        else:
            _validate_flux_handoff(service, request)
    input_bytes = _canonical_input(request)
    resident = resident_inspector(resident_id, session_id)
    if not isinstance(resident, dict) or resident.get('state') != 'ready' or resident.get('model') != 'qwen3.8-27b' or resident.get('gpu_loaded') is not True or resident.get('reservation_verified') is not True:
        raise ValueError('해제할 Qwen 3.8 상주 모델과 GPU 예약을 확인할 수 없습니다.')
    reservations = reservation_snapshot()
    if (not isinstance(reservations, dict) or reservations.get('status') != 'available' or reservations.get('truncated') is not False
            or not isinstance(reservations.get('records'), list)
            or any(not isinstance(item, dict) or item.get('state') != 'recorded' or not isinstance(item.get('service'), str) for item in reservations['records'])):
        raise ValueError('GPU 예약 전체를 확인할 수 없어 양도를 검토할 수 없습니다.')
    if sum(item['service'] == 'hermes-agent' for item in reservations['records']) != 1:
        raise ValueError('다른 헤르메스 GPU 작업이 있거나 예약이 확인되지 않습니다. 해당 작업이 끝난 뒤 다시 검토하세요.')
    return {'session_id':session_id, 'resident_id':resident_id, 'service':service, 'model':'qwen3.8-27b',
            'input_digest':hashlib.sha256(input_bytes).hexdigest(), 'review_hash':_review_hash(session_id, resident_id, request, service),
            'sequence':['wait_and_release', 'generate', 'reload']}


def _validate_flux_handoff(service, request):
    from workflow.domains.hermes_agent.flux_profile_operations import validate_hermes_flux_profile
    validate_hermes_flux_profile(service)
    if service == 'flux-expression':
        from workflow.domains.image.flux_expression_generation import FluxExpressionGenerationManager
        manager = FluxExpressionGenerationManager()
    else:
        from workflow.domains.image.flux_image_generation import FluxImageGenerationManager
        manager = FluxImageGenerationManager(service)
    manager.validate_generation_request(request)


def approve_handoff(request_id, session_id, resident_id, service, request, review_hash, *, confirmed,
                           store=None, session_store=None, resident_inspector=inspect_resident,
                           reservation_snapshot=read_hermes_gpu_reservation_snapshot, resident_conflict_check=None, writer_receipt_store=None):
    """명시적 확인과 동일 검토값이 있을 때만 재시작 가능한 양도를 저장한다."""
    if confirmed is not True or not isinstance(review_hash, str) or not re.fullmatch(r'[a-f0-9]{64}', review_hash):
        raise ValueError('해제와 작업 후 재적재에 대한 명시적 확인이 필요합니다.')
    expected = _review_hash(session_id, resident_id, request, service)
    if not hmac.compare_digest(review_hash, expected):
        raise ValueError('검토한 세션, 모델 또는 생성 입력이 변경되었습니다.')
    store = store or GpuHandoffStore()
    existing = store.read(request_id)
    if existing is not None:
        if (existing['session_id'] != session_id or existing['resident_id'] != resident_id
                or existing['service'] != service or existing['target_request'] != request):
            raise ValueError('같은 접수 ID를 다른 확인 대상에 사용할 수 없습니다.')
        return {**existing, 'duplicate':True}
    review = preview_handoff(session_id, resident_id, service, request, session_store=session_store,
                                   resident_inspector=resident_inspector, reservation_snapshot=reservation_snapshot)
    if resident_conflict_check is None:
        from workflow.domains.hermes_agent.resident_queue import ensure_no_other_active_residents
        resident_conflict_check = ensure_no_other_active_residents
    def precommit():
        resident_conflict_check(resident_id)
        if service=='writer-agent':
            from workflow.domains.hermes_agent.gpu_handoff_writer import ensure_writer_target_unclaimed
            ensure_writer_target_unclaimed(request_id,writer_receipt_store)
    return store.approve(request_id, session_id, service, review['input_digest'], target_request=request,
                         resident_id=resident_id, confirmed=True, precommit_check=precommit)


def preview_kimodo_handoff(session_id, resident_id, request, **kwargs):
    return preview_handoff(session_id, resident_id, 'kimodo', request, **kwargs)


def approve_kimodo_handoff(request_id, session_id, resident_id, request, review_hash, **kwargs):
    return approve_handoff(request_id, session_id, resident_id, 'kimodo', request, review_hash, **kwargs)
