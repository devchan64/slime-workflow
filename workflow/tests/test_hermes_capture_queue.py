import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.domains.hermes_agent.capture_queue import submit_capture_queue_request
from workflow.domains.hermes_agent.delegation_store import HermesDelegationStore


class HermesCaptureQueueTests(unittest.TestCase):
    def test_unverified_execution_stays_disabled_even_with_memory_policy(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            with patch('workflow.common.gpu_job_queue.GPU_MEMORY_REQUIREMENTS',{'review-capture':1234}),patch('workflow.common.gpu_job_queue.GPU_EXCLUSIVE_SERVICES',frozenset({'review-capture'})),patch('workflow.common.gpu_job_queue.launch_gpu_process') as current_launch_mock:
                with self.assertRaisesRegex(ValueError,'검증되지 않았습니다'):
                    submit_capture_queue_request(current_store_value,current_root_path,'request_123','map-review',{'map':'ash-edge'},current_workflow_root=current_root_path)
                current_launch_mock.assert_not_called()
                self.assertFalse((current_root_path/'receipts').exists())

    def test_capture_reservation_identity_requires_exact_non_symlink_root(self):
        from workflow.common.gpu_job_queue import identify_dedicated_gpu_reservation_source, is_dedicated_gpu_source_verifiable
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_capture_root=current_root_path/'.tmp'/'test'/'review-capture'
            current_capture_root.mkdir(parents=True)
            current_job_path=current_capture_root/'2026-11-19_12-00-00-12345678'
            current_job_path.mkdir()
            self.assertTrue(is_dedicated_gpu_source_verifiable('review-capture'))
            self.assertEqual(identify_dedicated_gpu_reservation_source(str(current_job_path),'review-capture',current_root_path),'review-capture')
            self.assertIsNone(identify_dedicated_gpu_reservation_source(str(current_job_path.parent),'review-capture',current_root_path))
            current_link_path=current_capture_root/'linked-job'
            current_link_path.symlink_to(current_job_path,target_is_directory=True)
            self.assertIsNone(identify_dedicated_gpu_reservation_source(str(current_link_path),'review-capture',current_root_path))
            self.assertIsNone(identify_dedicated_gpu_reservation_source(str(current_job_path),'other-service',current_root_path))

    def test_launcher_failure_never_automatically_resubmits(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            current_capture_root=current_root_path/'.tmp'/'test'/'review-capture'
            current_capture_root.mkdir(parents=True)
            with patch('workflow.domains.hermes_agent.capture_queue.CAPTURE_QUEUE_EXECUTION_VERIFIED',True),patch('workflow.common.gpu_job_queue.GPU_MEMORY_REQUIREMENTS',{'review-capture':1234}),patch('workflow.common.gpu_job_queue.GPU_EXCLUSIVE_SERVICES',frozenset({'review-capture'})),patch('workflow.common.gpu_job_queue.launch_gpu_process',side_effect=OSError('launch failed')) as current_launch_mock:
                with self.assertRaises(OSError):submit_capture_queue_request(current_store_value,current_capture_root,'request_lost','map-review',{'map':'ash-edge'},current_workflow_root=current_root_path)
                current_retry_result=submit_capture_queue_request(current_store_value,current_capture_root,'request_lost','map-review',{'map':'ash-edge'},current_workflow_root=current_root_path)
                self.assertEqual(current_retry_result['state'],'unknown')
                self.assertTrue(current_retry_result['duplicate'])
                current_launch_mock.assert_called_once()

    def test_symlink_storage_root_is_rejected_before_record_or_launch(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_link_path=current_root_path/'linked'
            current_link_path.symlink_to(current_root_path,target_is_directory=True)
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            current_capture_root=current_root_path/'.tmp'/'test'/'review-capture'
            current_capture_root.mkdir(parents=True)
            with patch('workflow.domains.hermes_agent.capture_queue.CAPTURE_QUEUE_EXECUTION_VERIFIED',True),patch('workflow.common.gpu_job_queue.GPU_MEMORY_REQUIREMENTS',{'review-capture':1234}),patch('workflow.common.gpu_job_queue.GPU_EXCLUSIVE_SERVICES',frozenset({'review-capture'})),patch('workflow.common.gpu_job_queue.launch_gpu_process') as current_launch_mock:
                with self.assertRaises(ValueError):submit_capture_queue_request(current_store_value,current_link_path,'request_123','map-review',{'map':'ash-edge'},current_workflow_root=current_root_path)
                with self.assertRaises(ValueError):submit_capture_queue_request(current_store_value,current_root_path,'request_123','map-review',{'map':'ash-edge'},current_workflow_root=current_root_path)
                current_launch_mock.assert_not_called()
                self.assertFalse((current_root_path/'receipts').exists())

    def test_unconfigured_policy_rejects_without_receipt_or_process(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            current_capture_root=current_root_path/'.tmp'/'test'/'review-capture'
            current_capture_root.mkdir(parents=True)
            with patch('workflow.domains.hermes_agent.capture_queue.CAPTURE_QUEUE_EXECUTION_VERIFIED',True),patch('workflow.common.gpu_job_queue.GPU_MEMORY_REQUIREMENTS',{}),patch('workflow.common.gpu_job_queue.GPU_EXCLUSIVE_SERVICES',frozenset()),patch('workflow.common.gpu_job_queue.launch_gpu_process') as current_launch_mock:
                with self.assertRaises(ValueError):submit_capture_queue_request(current_store_value,current_capture_root,'request_123','map-review',{'map':'ash-edge'},current_workflow_root=current_root_path)
                current_launch_mock.assert_not_called()
                self.assertFalse((current_root_path/'receipts').exists())

    def test_queued_request_is_deduplicated_with_mocked_launcher(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_store_value=HermesDelegationStore(current_root_path/'receipts')
            current_capture_root=current_root_path/'.tmp'/'test'/'review-capture'
            current_capture_root.mkdir(parents=True)
            with patch('workflow.domains.hermes_agent.capture_queue.CAPTURE_QUEUE_EXECUTION_VERIFIED',True),patch('workflow.common.gpu_job_queue.GPU_MEMORY_REQUIREMENTS',{'review-capture':1234}),patch('workflow.common.gpu_job_queue.GPU_EXCLUSIVE_SERVICES',frozenset({'review-capture'})),patch('workflow.common.gpu_job_queue.launch_gpu_process') as current_launch_mock:
                current_first_result=submit_capture_queue_request(current_store_value,current_capture_root,'request_123','map-review',{'map':'ash-edge'},current_workflow_root=current_root_path)
                current_next_result=submit_capture_queue_request(current_store_value,current_capture_root,'request_123','map-review',{'map':'ash-edge','edges':False},current_workflow_root=current_root_path)
                self.assertEqual(current_first_result['state'],'accepted')
                self.assertTrue(current_next_result['duplicate'])
                current_launch_mock.assert_called_once()
                current_job_path=current_capture_root/current_first_result['job_id']
                self.assertEqual(json.loads((current_job_path/'request.json').read_text())['settings']['map'],'ash-edge')
                self.assertEqual(json.loads((current_job_path/'request.json').read_text())['request_id'],'request_123')
                self.assertEqual(current_launch_mock.call_args.args[2],'review-capture')
                with self.assertRaises(ValueError):submit_capture_queue_request(current_store_value,current_capture_root,'request_123','map-review',{'map':'ash-edge','edges':True},current_workflow_root=current_root_path)
                current_launch_mock.assert_called_once()
