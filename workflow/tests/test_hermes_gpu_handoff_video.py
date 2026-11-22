"""영상 양도의 입력·접수 신원과 종료 관측을 검사한다."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
from workflow.domains.hermes_agent.gpu_handoff_controller import advance_gpu_handoff
from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
from workflow.domains.hermes_agent.gpu_handoff_video import VideoHandoffAdapter

SESSION = 'a'*32
JOB = '2026-11-22_12-00-00-12345678'
PAYLOAD = {'action':'generate','prompt':'walk','images':['reference'],'pose_video':'video'}
DIGEST = hashlib.sha256(json.dumps(PAYLOAD,sort_keys=True,separators=(',',':')).encode()).hexdigest()


class VideoHandoffTests(unittest.TestCase):
    def test_audio_handoff_binds_receipt_and_waits_for_gpu_release(self):
        from workflow.domains.hermes_agent.gpu_handoff_audio import AudioHandoffAdapter
        service='sfx-dasheng-audiogen'
        with TemporaryDirectory() as root:
            store=GpuHandoffStore(Path(root)/'handoffs');receipts=HermesDelegationStore(Path(root)/'receipts')
            store.approve('request_123',SESSION,service,DIGEST,target_request=PAYLOAD,resident_id='resident_123',confirmed=True)
            submitted=[]
            def gateway(command,payload):
                if command=='hermes-delegate-audio':
                    return receipts.execute_service_delegation_once(payload['request_id'],payload['service'],payload['request'],
                        lambda request:(submitted.append(request) or {'id':JOB}),lambda request:None)
                if command=='hermes-audio-status':
                    return {'receipt':receipts.read_service_delegation(payload['request_id'],service),'job':{'status':'completed'}}
                raise AssertionError(command)
            released=[False]
            adapter=AudioHandoffAdapter(gateway=gateway,delegation_store=receipts,release_observer=lambda *_:released[0])
            with patch.object(adapter,'ensure_release_requested'),patch.object(adapter,'inspect_release',return_value='released'):
                advance_gpu_handoff(store,'request_123',adapter)
                row=advance_gpu_handoff(store,'request_123',adapter)
                self.assertEqual(row['job_id'],JOB)
                self.assertEqual(advance_gpu_handoff(store,'request_123',adapter)['state'],'running')
                released[0]=True
                self.assertEqual(advance_gpu_handoff(store,'request_123',adapter)['state'],'reload_queued')
            self.assertEqual(submitted,[PAYLOAD])
            self.assertEqual(adapter.lookup_target({**row,'service':'music-heartmula'})['state'],'unknown')

    def test_video_receipt_is_bound_to_service_and_terminal_reservation(self):
        with TemporaryDirectory() as root:
            store=GpuHandoffStore(Path(root)/'handoffs'); receipts=HermesDelegationStore(Path(root)/'receipts')
            store.approve('request_123', SESSION, 'wan22-fun-control', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            submitted=[]
            def gateway(command, payload):
                if command=='hermes-delegate-video':
                    return receipts.execute_service_delegation_once(payload['request_id'],payload['service'],payload['request'],
                        lambda request:(submitted.append(request) or {'id':JOB}),lambda request:None)
                if command=='hermes-video-status':
                    return {'receipt':receipts.read_service_delegation(payload['request_id'],payload['service']), 'job':{'status':'completed'}}
                raise AssertionError(command)
            adapter=VideoHandoffAdapter(gateway=gateway,delegation_store=receipts,release_observer=lambda service,job,status: True)
            with patch.object(adapter,'ensure_release_requested'),patch.object(adapter,'inspect_release',return_value='released'):
                advance_gpu_handoff(store,'request_123',adapter)
                row=advance_gpu_handoff(store,'request_123',adapter)
                self.assertEqual(row['job_id'],JOB)
                self.assertEqual(advance_gpu_handoff(store,'request_123',adapter)['state'],'reload_queued')
                self.assertEqual(submitted,[PAYLOAD])
                self.assertEqual(adapter.lookup_target({**row,'service':'wan22-vace'})['state'],'unknown')

    def test_video_review_uses_existing_validator_and_binds_service(self):
        from workflow.domains.hermes_agent.gpu_handoff_operations import preview_handoff, approve_handoff
        class Sessions:
            def read_session_record(self,value): return {'id':value}
        ready=lambda *_:{'state':'ready','model':'qwen3.8-27b','gpu_loaded':True,'reservation_verified':True}
        reservations=lambda:{'status':'available','truncated':False,'records':[{'state':'recorded','service':'hermes-agent'}]}
        options={'session_store':Sessions(),'resident_inspector':ready,'reservation_snapshot':reservations}
        with TemporaryDirectory() as root,patch('workflow.domains.hermes_agent.video_operations.validate_hermes_video_request') as validate:
            review=preview_handoff(SESSION,'resident_123','wan22-fun-control',PAYLOAD,**options)
            validate.assert_called_once_with('wan22-fun-control',PAYLOAD)
            with self.assertRaises(ValueError):
                approve_handoff('request_123',SESSION,'resident_123','wan22-vace',PAYLOAD,review['review_hash'],confirmed=True,store=GpuHandoffStore(root),**options)
            self.assertEqual(approve_handoff('request_123',SESSION,'resident_123','wan22-fun-control',PAYLOAD,review['review_hash'],confirmed=True,store=GpuHandoffStore(root),resident_conflict_check=lambda _:None,**options)['state'],'approved')


if __name__ == '__main__': unittest.main()
