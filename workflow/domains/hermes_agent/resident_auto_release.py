"""대기 생성 작업을 위해 확인된 Qwen 상주 예약을 정상 반환한다."""
import os
from pathlib import Path

from workflow.common import gpu_job_queue
from workflow.common.gpu_chat_admission import hold_gpu_queue_lock, list_chat_queue_intents_locked
from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record
from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
from workflow.domains.hermes_agent.resident_queue import request_resident_release


def select_resident_release_candidate(active_reservation_root, resident_reservation_record):
    """GPU 잠금 안에서 상주 예약과 반환 후 실행 가능성을 다시 확인한다."""
    if not gpu_job_queue.read_priority_tickets():
        return None
    active_reservation_paths = gpu_job_queue.list_gpu_queue_record_paths(active_reservation_root)
    if not 1 <= len(active_reservation_paths) <= 2:
        return None
    active_reservation_records = [read_bounded_delegation_record(active_reservation_path) for active_reservation_path in active_reservation_paths]
    if active_reservation_records.count(resident_reservation_record) != 1:
        return None
    queue_intent_records = list_chat_queue_intents_locked(active_reservation_root.parent)
    for current_reservation_record in active_reservation_records:
        if not isinstance(current_reservation_record, dict) or current_reservation_record.get('service') != 'hermes-agent':
            return None
        resident_job_directory = Path(current_reservation_record.get('path', ''))
        if (not gpu_job_queue.verify_hermes_resident_queue_job_path(resident_job_directory)
                or any(queue_intent_record['resident_id'] == resident_job_directory.name for queue_intent_record in queue_intent_records)):
            return None
    memory_domain_name = gpu_job_queue.read_gpu_memory_domain()
    total_gpu_memory, free_gpu_memory = gpu_job_queue.read_gpu_memory()
    available_host_memory = gpu_job_queue.read_host_available_memory()
    if free_gpu_memory > total_gpu_memory:
        return None
    resident_session_identifiers = []
    total_resident_gpu_memory = 0
    total_resident_host_memory = 0
    remaining_reserved_memory = 0
    remaining_host_reservation = 0
    for current_reservation_record in active_reservation_records:
        if not isinstance(current_reservation_record, dict) or current_reservation_record.get('service') != 'hermes-agent':
            return None
        resident_job_directory = Path(current_reservation_record.get('path', ''))
        if not gpu_job_queue.verify_hermes_resident_queue_job_path(resident_job_directory):
            return None
        if any(queue_intent_record['resident_id'] == resident_job_directory.name for queue_intent_record in queue_intent_records):
            return None
        resident_request_record = read_bounded_delegation_record(resident_job_directory / 'request.json')
        resident_session_identifiers.append(resident_request_record['context']['session_id'])
        resident_worker_identifier = current_reservation_record.get('worker_pgid')
        resident_reserved_memory = current_reservation_record.get('required_memory_mib')
        if (type(resident_worker_identifier) is not int or resident_worker_identifier <= 1
                or type(resident_reserved_memory) is not int or resident_reserved_memory < 0):
            return None
        if len(active_reservation_records) > 1:
            resident_status_record = read_bounded_delegation_record(resident_job_directory / 'resident-status.json')
            if (not isinstance(resident_status_record, dict) or resident_status_record.get('status') != 'ready'
                    or resident_status_record.get('worker_pid') != resident_worker_identifier
                    or gpu_job_queue.inspect_gpu_ticket_executor_identity(current_reservation_record) != 'verified'):
                return None
            resident_process_descriptor = gpu_job_queue.open_verified_hermes_process_group(current_reservation_record)
            if resident_process_descriptor is None:
                return None
            os.close(resident_process_descriptor)
        resident_gpu_memory = gpu_job_queue.read_worker_memory(resident_worker_identifier, current_memory_domain=memory_domain_name)
        resident_host_memory = gpu_job_queue.read_worker_group_rss_kib(resident_worker_identifier) // 1024
        if resident_gpu_memory <= 0:
            return None
        total_resident_gpu_memory += resident_gpu_memory
        total_resident_host_memory += max(0, resident_host_memory)
        remaining_reserved_memory += max(0, resident_reserved_memory - resident_gpu_memory)
        if memory_domain_name == 'vram':
            remaining_host_reservation += max(0, gpu_job_queue.HERMES_RESIDENT_HOST_FLOOR_MIB - resident_host_memory)
    current_unreserved_host = max(0, available_host_memory - remaining_host_reservation)
    available_pool_memory = gpu_job_queue.calculate_gpu_pool_capacity(memory_domain_name, free_gpu_memory, current_unreserved_host)
    current_available_memory = max(0, available_pool_memory - remaining_reserved_memory)
    # RSS는 반환 가능량의 추정치다. 실제 실행 전 공용 실행기가 여유를 다시 읽는다.
    released_host_memory = available_host_memory + total_resident_host_memory
    released_gpu_memory = min(total_gpu_memory, free_gpu_memory + total_resident_gpu_memory)
    released_available_memory = gpu_job_queue.calculate_gpu_pool_capacity(memory_domain_name, released_gpu_memory, released_host_memory)
    host_reserve_memory = gpu_job_queue.HOST_MEMORY_RESERVE_KIB // 1024
    usable_host_memory = max(0, current_unreserved_host - host_reserve_memory)
    released_usable_host_memory = max(0, released_host_memory - host_reserve_memory)
    selected_generation_ticket = gpu_job_queue.select_ticket_after_resident_release(current_available_memory, released_available_memory,
        memory_domain_name, resident_session_identifiers, usable_host_memory, released_usable_host_memory)
    if selected_generation_ticket is None:
        return None
    resident_chat_intents = [queue_intent_record for queue_intent_record in queue_intent_records
                             if queue_intent_record['session_id'] in resident_session_identifiers]
    if resident_chat_intents:
        selected_ticket_path = Path(selected_generation_ticket)
        queue_priority_values = gpu_job_queue.read_gpu_priority_order()
        ticket_order_key = (queue_priority_values.get(selected_ticket_path.name, 0), selected_ticket_path.name)
        if any((0, f"{queue_intent_record['order_ns']:020d}-0.json") < ticket_order_key for queue_intent_record in resident_chat_intents):
            return None
    return selected_generation_ticket


def release_resident_for_waiting_generation():
    """현재 공용 대기열을 재검증해 상주 서버의 정상 반환을 요청한다."""
    queue_root_directory = Path(gpu_job_queue.GPU_QUEUE_DIRECTORY)
    active_reservation_root = queue_root_directory / 'active'
    if not active_reservation_root.is_dir() or active_reservation_root.is_symlink():
        return None
    with hold_gpu_queue_lock(queue_root_directory):
        active_reservation_paths = gpu_job_queue.list_gpu_queue_record_paths(active_reservation_root)
        if not 1 <= len(active_reservation_paths) <= 2:
            return None
        active_reservation_records = [read_bounded_delegation_record(active_reservation_path) for active_reservation_path in active_reservation_paths]
        if any(not isinstance(reservation_record, dict) or reservation_record.get('service') != 'hermes-agent' for reservation_record in active_reservation_records):
            return None
        resident_reservation_record = active_reservation_records[0]
        if not isinstance(resident_reservation_record, dict) or resident_reservation_record.get('service') != 'hermes-agent':
            return None
        resident_job_directory = Path(resident_reservation_record.get('path', ''))
        if not gpu_job_queue.verify_hermes_resident_queue_job_path(resident_job_directory):
            return None
        resident_status_record = read_bounded_delegation_record(resident_job_directory / 'resident-status.json')
        if not isinstance(resident_status_record, dict) or resident_status_record.get('status') != 'ready':
            return None
        resident_request_record = read_bounded_delegation_record(resident_job_directory / 'request.json')
        resident_session_identifier = resident_request_record['context']['session_id']
    def verify_waiting_generation(active_root_directory, current_reservation_record):
        return select_resident_release_candidate(active_root_directory, current_reservation_record) is not None
    return GpuHandoffStore().run_without_open_session_handoff(resident_session_identifier,
        lambda: request_resident_release(resident_job_directory.name, resident_session_identifier,
            release_condition_check=verify_waiting_generation), all_sessions=True)


def release_resident_with_chat_guard(hermes_service_manager):
    """대화 작업 생성과 반환을 직렬화하고 접수된 대화가 끝날 때까지 기다린다."""
    from workflow.domains.hermes_agent.session_store import HermesSessionStore
    queue_root_directory = Path(gpu_job_queue.GPU_QUEUE_DIRECTORY)
    active_reservation_root = queue_root_directory / 'active'
    with hermes_service_manager.hold_hermes_service_lock():
        if not active_reservation_root.is_dir() or active_reservation_root.is_symlink():
            return None
        with hold_gpu_queue_lock(queue_root_directory):
            if not gpu_job_queue.read_priority_tickets():
                return None
            active_reservation_paths = gpu_job_queue.list_gpu_queue_record_paths(active_reservation_root)
            if not 1 <= len(active_reservation_paths) <= 2:
                return None
            resident_session_identifiers = []
            for active_reservation_path in active_reservation_paths:
                current_reservation_record = read_bounded_delegation_record(active_reservation_path)
                if not isinstance(current_reservation_record, dict) or current_reservation_record.get('service') != 'hermes-agent':
                    return None
                resident_job_directory = Path(current_reservation_record.get('path', ''))
                if not gpu_job_queue.verify_hermes_resident_queue_job_path(resident_job_directory):
                    return None
                resident_request_record = read_bounded_delegation_record(resident_job_directory / 'request.json')
                resident_session_identifiers.append(resident_request_record['context']['session_id'])
        session_store_instance = (HermesSessionStore(hermes_service_manager.hermes_session_root)
                                  if hermes_service_manager.hermes_session_root is not None else HermesSessionStore())
        for resident_session_identifier in resident_session_identifiers:
            session_record_value = session_store_instance.read_session_record(resident_session_identifier)
            session_message_records = session_record_value.get('messages')
            if not isinstance(session_message_records, list) or len(session_message_records) > 10000:
                return None
            for session_message_record in session_message_records:
                if not isinstance(session_message_record, dict):
                    return None
                session_job_identifier = session_message_record.get('job_id')
                if session_job_identifier is None:
                    continue
                session_job_directory = hermes_service_manager.resolve_hermes_job_path(session_job_identifier)
                session_job_status = read_bounded_delegation_record(session_job_directory / 'status.json')
                if not isinstance(session_job_status, dict) or session_job_status.get('status') not in ('completed', 'failed', 'cancelled'):
                    return None
        return release_resident_for_waiting_generation()
