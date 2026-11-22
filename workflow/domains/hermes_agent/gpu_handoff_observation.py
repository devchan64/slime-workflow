"""GPU 양도 관측을 보수적으로 분류한다. 조회나 프로세스 제어는 하지 않는다."""


def classify_hermes_release(job, reservations, gpu):
    """3.8 작업의 종료, 공용 예약 부재 및 GPU 유휴 관측을 모두 요구한다.

    결과는 조회 시점 관측이지 이후 예약을 보장하지 않는다. 실제 접수는
    공용 대기열의 잠금과 별도 예약 절차로 다시 보호해야 한다.
    """
    if not isinstance(job, dict) or job.get('model_profile') != 'qwen3.8-27b':
        return 'unknown'
    status = job.get('status')
    if status in ('queued', 'running'):
        return 'waiting'
    if status not in ('completed', 'failed', 'cancelled'):
        return 'unknown'
    if (not isinstance(reservations, dict) or reservations.get('status') != 'available'
            or reservations.get('truncated') is not False or not isinstance(reservations.get('records'), list)):
        return 'unknown'
    for record in reservations['records']:
        if not isinstance(record, dict) or record.get('state') != 'recorded' or not isinstance(record.get('service'), str):
            return 'unknown'
        if record['service'] == 'hermes-agent':
            return 'waiting'
    if not isinstance(gpu, dict) or gpu.get('status') not in ('idle', 'busy') or type(gpu.get('process_count')) is not int or gpu['process_count'] < 0:
        return 'unknown'
    if (gpu['status'] == 'idle') != (gpu['process_count'] == 0):
        return 'unknown'
    return 'released' if gpu['status'] == 'idle' else 'waiting'
