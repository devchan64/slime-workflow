"""FLUX 양도에서 서비스별 입력과 기존 접수 영수증을 확인한다."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore
from workflow.domains.hermes_agent.gpu_handoff_controller import advance_gpu_handoff
from workflow.domains.hermes_agent.gpu_handoff_flux import FluxHandoffAdapter
from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore

SESSION = 'a'*32
JOB = '2026-11-22_12-00-00-12345678'
PAYLOAD = {'prompt':'tree','width':512,'height':512,'steps':16,'seed':42,'images':[],'action':'generate'}
DIGEST = hashlib.sha256(json.dumps(PAYLOAD,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


class FluxHandoffTests(unittest.TestCase):
    def test_direct_and_handoff_simultaneously_submit_only_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier, Event
        with TemporaryDirectory() as root:
            receipts = HermesDelegationStore(Path(root) / 'receipts')
            proposal_id = 'flux_' + 'c' * 64
            start, entered, release = Barrier(2), Event(), Event()
            calls = []
            def enqueue(request):
                calls.append(request)
                entered.set()
                if not release.wait(5):
                    raise TimeoutError('test submission not released')
                return {'id':JOB}
            def direct():
                start.wait(timeout=5)
                return receipts.execute_service_delegation_once(proposal_id, 'flux-image', PAYLOAD, enqueue, lambda value: None)
            def gateway(command, payload):
                return receipts.execute_service_delegation_once(payload['request_id'], payload['service'], payload['request'], enqueue, lambda value: None)
            def handoff():
                start.wait(timeout=5)
                adapter = FluxHandoffAdapter(gateway=gateway, delegation_store=receipts)
                return adapter.submit_target({'id':proposal_id, 'service':'flux-image', 'target_request':PAYLOAD, 'input_digest':DIGEST})
            with ThreadPoolExecutor(max_workers=2) as pool:
                direct_result, handoff_result = pool.submit(direct), pool.submit(handoff)
                try:
                    self.assertTrue(entered.wait(5))
                finally:
                    release.set()
                self.assertEqual(direct_result.result(timeout=5)['job_id'], JOB)
                self.assertEqual(handoff_result.result(timeout=5)['job_id'], JOB)
            self.assertEqual(calls, [PAYLOAD])

    def test_proposal_handoff_and_direct_submit_share_receipt(self):
        with TemporaryDirectory() as root:
            receipts = HermesDelegationStore(Path(root) / 'receipts')
            proposal_id = 'flux_' + 'a' * 64
            calls = []
            def submit(request_id, request):
                return receipts.execute_service_delegation_once(request_id, 'flux-image', request,
                    lambda value: (calls.append(value) or {'id': JOB}), lambda value: None)
            def gateway(command, payload):
                self.assertEqual(command, 'hermes-delegate-flux-profile')
                return submit(payload['request_id'], payload['request'])
            adapter = FluxHandoffAdapter(gateway=gateway, delegation_store=receipts)
            record = {'id':proposal_id, 'service':'flux-image', 'target_request':PAYLOAD, 'input_digest':DIGEST}
            submit(proposal_id, PAYLOAD)
            self.assertEqual(adapter.submit_target(record)['job_id'], JOB)
            self.assertEqual(len(calls), 1)
            with self.assertRaises(ValueError):
                submit(proposal_id, {**PAYLOAD, 'prompt':'different'})

    def test_proposal_direct_submit_after_handoff_is_idempotent(self):
        with TemporaryDirectory() as root:
            receipts = HermesDelegationStore(Path(root) / 'receipts')
            proposal_id = 'flux_' + 'b' * 64
            calls = []
            def gateway(command, payload):
                return receipts.execute_service_delegation_once(payload['request_id'], payload['service'], payload['request'],
                    lambda value: (calls.append(value) or {'id': JOB}), lambda value: None)
            adapter = FluxHandoffAdapter(gateway=gateway, delegation_store=receipts)
            record = {'id':proposal_id, 'service':'flux-image', 'target_request':PAYLOAD, 'input_digest':DIGEST}
            self.assertEqual(adapter.submit_target(record)['job_id'], JOB)
            receipts.execute_service_delegation_once(proposal_id, 'flux-image', PAYLOAD,
                lambda value: (calls.append(value) or {'id': JOB}), lambda value: None)
            self.assertEqual(len(calls), 1)

    def test_existing_profile_receipt_and_service_identity_are_preserved(self):
        with TemporaryDirectory() as root:
            store = GpuHandoffStore(Path(root) / 'handoffs')
            receipts = HermesDelegationStore(Path(root) / 'receipts')
            store.approve('request_123', SESSION, 'flux-image', DIGEST, target_request=PAYLOAD, resident_id='resident_123', confirmed=True)
            submitted = []
            def gateway(command, payload):
                if command == 'hermes-delegate-flux-profile':
                    return receipts.execute_service_delegation_once(payload['request_id'], payload['service'], payload['request'],
                        lambda request: (submitted.append(request) or {'id':JOB}), lambda request: None)
                if command == 'hermes-flux-profile-status':
                    return {'receipt':receipts.read_service_delegation(payload['request_id'],payload['service']),
                            'job':{'id':JOB,'status':'completed'}}
                raise AssertionError(command)
            adapter = FluxHandoffAdapter(gateway=gateway, delegation_store=receipts, release_observer=lambda service,job,status: True)
            with patch.object(adapter,'ensure_release_requested'), patch.object(adapter,'inspect_release',return_value='released'):
                advance_gpu_handoff(store,'request_123',adapter)
                row = advance_gpu_handoff(store,'request_123',adapter)
                self.assertEqual(row['job_id'],JOB)
                self.assertEqual(advance_gpu_handoff(store,'request_123',adapter)['state'],'reload_queued')
                self.assertEqual(submitted,[PAYLOAD])
                tampered = {**row,'service':'flux-character'}
                self.assertEqual(adapter.lookup_target(tampered)['state'],'unknown')

    def test_review_hash_binds_flux_service_and_rejects_unknown_target(self):
        from workflow.domains.hermes_agent.gpu_handoff_operations import preview_handoff, approve_handoff
        class Sessions:
            def read_session_record(self, value): return {'id':value}
        resident = lambda *_: {'state':'ready','model':'qwen3.8-27b','gpu_loaded':True,'reservation_verified':True}
        reservations = lambda: {'status':'available','truncated':False,'records':[{'state':'recorded','service':'hermes-agent'}]}
        with TemporaryDirectory() as root, patch('workflow.domains.image.flux_image_generation.FluxImageGenerationManager.validate_generation_request'):
            options={'session_store':Sessions(),'resident_inspector':resident,'reservation_snapshot':reservations}
            review=preview_handoff(SESSION,'resident_123','flux-image',PAYLOAD,**options)
            with self.assertRaises(ValueError):
                approve_handoff('request_123',SESSION,'resident_123','flux-character',PAYLOAD,review['review_hash'],confirmed=True,store=GpuHandoffStore(root),**options)
            with self.assertRaises(ValueError):
                preview_handoff(SESSION,'resident_123','unsupported',PAYLOAD,**options)
            result=approve_handoff('request_123',SESSION,'resident_123','flux-image',PAYLOAD,review['review_hash'],confirmed=True,store=GpuHandoffStore(root),resident_conflict_check=lambda _:None,**options)
            self.assertEqual(result['service'],'flux-image')


if __name__ == '__main__': unittest.main()
