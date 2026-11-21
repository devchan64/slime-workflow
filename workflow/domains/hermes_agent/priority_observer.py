"""Hermes의 GPU 대기 작업 우선 실행 대상 조회."""


def inspect_hermes_priority_retirement(current_service_name):
    """소유 서비스에서 재개를 폐기한 작업은 우선 실행도 차단한다."""
    from generators.music.service_constants import inspect_retired_audio_rejection
    from workflow.domains.character_animation.retirement_policy import inspect_animation_retirement_policy
    if current_service_name == 'character-animation':
        return inspect_animation_retirement_policy('resume')
    return inspect_retired_audio_rejection(current_service_name,'resume')


def validate_hermes_priority_target(current_service_name,current_job_identifier):
    """기존 게이트웨이와 소유 서비스의 폐기 정책을 함께 검증한다."""
    from workflow.common.management_gateway import resolve_management_command
    resolve_management_command(current_service_name,'prioritize',{'id':current_job_identifier})
    current_reason_value = inspect_hermes_priority_retirement(current_service_name)
    if current_reason_value:
        raise ValueError('폐기된 작업은 우선 실행할 수 없습니다. '+current_reason_value)


def preview_hermes_queue_priority(current_service_name,current_job_identifier):
    """원 서비스가 확인된 유일한 대기 작업만 읽으며 순서를 변경하지 않는다."""
    from workflow.domains.hermes_agent.management_observer import read_hermes_management_snapshot
    validate_hermes_priority_target(current_service_name,current_job_identifier)
    current_snapshot=read_hermes_management_snapshot()
    current_queue=current_snapshot.get('queue') if isinstance(current_snapshot,dict) else None
    if not isinstance(current_queue,dict) or current_queue.get('status')!='available' or not isinstance(current_queue.get('jobs'),list):
        raise ValueError('GPU 대기열을 확인할 수 없습니다.')
    current_jobs=current_queue['jobs']
    if any(not isinstance(item,dict) or not isinstance(item.get('id'),str) or not isinstance(item.get('service'),str) for item in current_jobs):
        raise ValueError('GPU 대기열 형식 오류')
    current_matches=[(index,item) for index,item in enumerate(current_jobs) if item['id']==current_job_identifier]
    if len(current_matches)!=1:
        raise ValueError('유일한 대기 작업을 확인할 수 없습니다. 상태를 다시 확인하세요.')
    current_index,current_ticket=current_matches[0]
    current_executor_identity=current_ticket.get('executor_identity','unverified')
    if current_executor_identity not in ('verified','unverified'):raise ValueError('대기 실행기 신원 확인 불가')
    current_queue_service=current_ticket['service']
    from workflow.common.gpu_job_queue import is_dedicated_gpu_source_verifiable
    if current_queue_service in ('image','flux-image') or is_dedicated_gpu_source_verifiable(current_queue_service):
        current_owner=current_ticket.get('source_service')
    else:
        current_owner='wan22-fun-control' if current_queue_service=='wan-fun' else current_queue_service
    if current_owner!=current_service_name:
        raise ValueError('대기 작업의 원 서비스가 일치하지 않거나 확인되지 않습니다.')
    import re
    current_ticket_revision=current_ticket.get('ticket_revision')
    if not isinstance(current_ticket_revision,str) or not re.fullmatch(r'[a-f0-9]{64}',current_ticket_revision):
        raise ValueError('대기 티켓의 확인 정보가 없습니다. 갱신된 게이트웨이에서 다시 조회하세요.')
    return {'service':current_service_name,'job_id':current_job_identifier,'ticket_revision':current_ticket_revision,'queue_position':current_index+1,'queue_count':len(current_jobs),'observed_at':current_snapshot.get('queried_at'),'executor_identity':current_executor_identity,'note':'관측 시점의 대기 기록입니다. 실행기 신원은 부팅·시작 식별값 기준이며 미확인은 PID 재사용 여부를 알 수 없습니다. 순서를 변경하지 않았으며 이후 상태가 달라질 수 있습니다.'}
