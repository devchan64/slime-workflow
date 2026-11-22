"""기존 동작·영상 생성기의 접수와 GPU 양도를 연결한다."""
from workflow.domains.hermes_agent.gpu_handoff_flux import FluxHandoffAdapter
from workflow.domains.hermes_agent.gpu_handoff_kimodo import _derived_id, inspect_target_release
from workflow.domains.hermes_agent.video_operations import validate_hermes_video_service, make_hermes_video_manager


def inspect_video_release(service, job_id, status):
    validate_hermes_video_service(service)
    return inspect_target_release(make_hermes_video_manager(service).job_storage_root, job_id, status)


class VideoHandoffAdapter(FluxHandoffAdapter):
    def target_request_id(self, record):
        return _derived_id('handoff_', record['id'])

    def __init__(self, *, release_observer=inspect_video_release, **kwargs):
        super().__init__(**kwargs)
        self.video_release_observer = release_observer

    def validate_service(self, service):
        validate_hermes_video_service(service)

    def submit_target(self, record):
        self.validate_service(record['service'])
        self.gateway('hermes-delegate-video', {'request_id':_derived_id('handoff_',record['id']),
                     'service':record['service'], 'request':record['target_request']})
        return self.lookup_target(record)

    def inspect_target(self, record):
        service = record['service']
        receipt = self.lookup_target(record)
        if receipt.get('state') != 'accepted' or receipt.get('job_id') != record['job_id']:
            return {'state':'unknown'}
        response = self.gateway('hermes-video-status', {'request_id':_derived_id('handoff_',record['id']), 'service':service})
        if not isinstance(response, dict) or not isinstance(response.get('receipt'), dict) or not isinstance(response.get('job'), dict):
            return {'state':'unknown'}
        observed, job = response['receipt'], response['job']
        if (observed.get('state') != 'accepted' or observed.get('service') != service
                or observed.get('job_id') != record['job_id'] or job.get('id', record['job_id']) != record['job_id']):
            return {'state':'unknown'}
        status = job.get('status')
        result = {'service':service, 'job_id':record['job_id'], 'status':status}
        if status in ('completed','failed','cancelled'):
            result['reservation_released'] = self.video_release_observer(service, record['job_id'], status)
        return result

    def cancel_target(self, record):
        receipt = self.lookup_target(record)
        if receipt.get('state') != 'accepted' or receipt.get('job_id') != record['job_id']:
            raise ValueError('중지할 영상 작업의 접수 기록을 확인할 수 없습니다.')
        response = self.gateway('hermes-video-cancel', {'request_id':_derived_id('handoff_',record['id']),
                                'service':record['service'], 'job_id':record['job_id']})
        if not isinstance(response, dict) or response.get('job_id') != record['job_id'] or response.get('cancel_requested') is not True:
            raise ValueError('영상 작업 중지 요청을 확인할 수 없습니다.')
        return response
