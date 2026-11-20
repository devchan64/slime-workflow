"""영상 재개 전 저장된 참조 사본을 CPU에서 확인한다."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager


class ReferenceVideoResumeValidationTests(unittest.TestCase):
    def test_resume_checks_saved_references_before_assets(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_path = Path(current_directory_name)
            current_image_bytes = b'original reference'
            current_image_path = current_job_path / 'reference-1.png'
            current_image_path.write_bytes(current_image_bytes)
            current_request_record = {'references': ['reference-1.png'], 'reference_snapshots': [
                {'path': 'reference-1.png', 'order': 1, 'bytes': len(current_image_bytes),
                 'sha256': hashlib.sha256(current_image_bytes).hexdigest()}]}
            (current_job_path / 'request.json').write_text(json.dumps(current_request_record))
            current_assets_check = Mock()
            current_manager_instance = ReferenceVideoGenerationManager('/test', current_job_path, 'unused', Mock(), current_assets_check)
            with patch('tools.review.common.reference_video_generation.recover_interrupted_video_job'):
                current_manager_instance.validate_generation_resume(current_job_path)
                current_assets_check.assert_called_once()
                current_assets_check.reset_mock()
                current_image_path.write_bytes(b'changed reference')
                with self.assertRaises(ValueError):
                    current_manager_instance.validate_generation_resume(current_job_path)
                current_assets_check.assert_not_called()
                current_image_path.unlink()
                with self.assertRaises(ValueError):
                    current_manager_instance.validate_generation_resume(current_job_path)
                current_request_record.pop('reference_snapshots')
                (current_job_path / 'request.json').write_text(json.dumps(current_request_record))
                with self.assertRaises(ValueError):
                    current_manager_instance.validate_generation_resume(current_job_path)
                current_image_path.write_bytes(current_image_bytes)
                current_manager_instance.validate_generation_resume(current_job_path)

    def test_resume_rejects_malformed_snapshot_metadata(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_path = Path(current_directory_name)
            (current_job_path / 'reference-1.png').write_bytes(b'reference')
            (current_job_path / 'request.json').write_text(json.dumps({'references': ['reference-1.png'], 'reference_snapshots': [None]}))
            current_assets_check = Mock()
            current_manager_instance = ReferenceVideoGenerationManager('/test', current_job_path, 'unused', Mock(), current_assets_check)
            with patch('tools.review.common.reference_video_generation.recover_interrupted_video_job'):
                with self.assertRaises(ValueError):
                    current_manager_instance.validate_generation_resume(current_job_path)
            current_assets_check.assert_not_called()


class VideoAttachmentResumeTests(unittest.TestCase):
    def test_service_resume_verifies_required_video_inputs(self):
        from tools.review.domains.wan_animate2.generation import AnimateTwoGenerationManager
        from tools.review.domains.wan_vace.generation import VaceVideoGenerationManager
        current_cases = (
            (AnimateTwoGenerationManager, None, ('driving_video',)),
            (VaceVideoGenerationManager, 'video_edit', ('edit_video', 'edit_mask')),
            (VaceVideoGenerationManager, 'video_condition', ('edit_video',)),
            (VaceVideoGenerationManager, 'pose', ('pose_video',)),
            (VaceVideoGenerationManager, 'text', ()),
        )
        for current_manager_class, current_mode_value, current_field_names in current_cases:
            with self.subTest(mode=current_mode_value), tempfile.TemporaryDirectory() as current_directory_name:
                current_job_path = Path(current_directory_name)
                saved_request_record = {'mode': current_mode_value, 'references': [] if current_mode_value == 'text' else ['reference-1.png']}
                for current_field_name in current_field_names:
                    current_file_name = 'driving.mp4' if current_field_name == 'driving_video' else current_field_name.replace('_', '-') + '.mp4'
                    current_video_bytes = current_field_name.encode()
                    (current_job_path / current_file_name).write_bytes(current_video_bytes)
                    saved_request_record[current_field_name + '_file'] = current_file_name
                    saved_request_record[current_field_name + '_sha256'] = hashlib.sha256(current_video_bytes).hexdigest()
                with patch.object(ReferenceVideoGenerationManager, 'validate_generation_resume', return_value=saved_request_record):
                    current_manager_instance = current_manager_class()
                    current_manager_instance.validate_generation_resume(current_job_path)
                    if current_field_names:
                        current_input_path = current_job_path / saved_request_record[current_field_names[0] + '_file']
                        current_input_path.write_bytes(b'changed')
                        with self.assertRaises(ValueError):
                            current_manager_instance.validate_generation_resume(current_job_path)
                        current_input_path.unlink()
                        current_input_path.symlink_to(current_job_path / 'elsewhere')
                        with self.assertRaises(ValueError):
                            current_manager_instance.validate_generation_resume(current_job_path)

    def test_unknown_vace_mode_is_rejected(self):
        from tools.review.domains.wan_vace.generation import VaceVideoGenerationManager
        with patch.object(ReferenceVideoGenerationManager, 'validate_generation_resume', return_value={'mode': 'unknown'}):
            with self.assertRaises(ValueError):
                VaceVideoGenerationManager().validate_generation_resume(Path('/unused'))


    def test_services_reject_wrong_reference_count(self):
        from tools.review.domains.dwpose.generation import DwposeGenerationManager
        from tools.review.domains.wan_animate2.generation import AnimateTwoGenerationManager
        from tools.review.domains.wan_vace.generation import VaceVideoGenerationManager
        current_cases = ((DwposeGenerationManager, {'references': []}),
                         (AnimateTwoGenerationManager, {'references': []}),
                         (VaceVideoGenerationManager, {'mode': 'pose', 'references': []}),
                         (VaceVideoGenerationManager, {'mode': 'text', 'references': ['reference-1.png']}))
        for current_manager_class, saved_request_record in current_cases:
            with self.subTest(manager=current_manager_class.__name__, request=saved_request_record):
                with patch.object(ReferenceVideoGenerationManager, 'validate_generation_resume', return_value=saved_request_record):
                    with self.assertRaises(ValueError):
                        current_manager_class().validate_generation_resume(Path('/unused'))


    def test_reference_validation_rejects_fifo_and_invalid_metadata(self):
        import os
        from tools.review.domains.image.three_reference_generation import verify_reference_snapshots
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_path = Path(current_directory_name)
            current_image_path = current_job_path / 'reference-1.png'
            os.mkfifo(current_image_path)
            with self.assertRaises(ValueError):
                verify_reference_snapshots(current_job_path, {'references': ['reference-1.png']})
            current_image_path.unlink()
            current_image_path.write_bytes(b'image')
            for current_metadata_value in (None, {}, [None], [{'path': 'reference-1.png', 'order': True, 'bytes': 5, 'sha256': 'x'}]):
                with self.subTest(metadata=current_metadata_value):
                    with self.assertRaises(ValueError):
                        verify_reference_snapshots(current_job_path, {'references': ['reference-1.png'], 'reference_snapshots': current_metadata_value})


    def test_video_resume_fingerprint_covers_saved_inputs(self):
        from tools.review.common.video_resume_fingerprint import fingerprint_video_resume_inputs
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_path = Path(current_directory_name)
            saved_request_record = {'references': ['reference-1.png'], 'driving_video_file': 'driving.mp4'}
            (current_job_path / 'request.json').write_text(json.dumps(saved_request_record))
            (current_job_path / 'status.json').write_text(json.dumps({'status': 'failed'}))
            (current_job_path / 'reference-1.png').write_bytes(b'image')
            (current_job_path / 'driving.mp4').write_bytes(b'video')
            original_fingerprint_value = fingerprint_video_resume_inputs(current_job_path, 'wan22-animate2')['fingerprint']
            for current_file_name in ('reference-1.png', 'driving.mp4'):
                current_input_path = current_job_path / current_file_name
                original_file_bytes = current_input_path.read_bytes()
                current_input_path.write_bytes(b'changed')
                self.assertNotEqual(original_fingerprint_value, fingerprint_video_resume_inputs(current_job_path, 'wan22-animate2')['fingerprint'])
                current_input_path.write_bytes(original_file_bytes)
            (current_job_path / 'gpu-command.json').write_text('{}')
            self.assertNotEqual(original_fingerprint_value, fingerprint_video_resume_inputs(current_job_path, 'wan22-animate2')['fingerprint'])
            (current_job_path / 'driving.mp4').unlink()
            (current_job_path / 'driving.mp4').symlink_to(current_job_path / 'reference-1.png')
            with self.assertRaises(ValueError):
                fingerprint_video_resume_inputs(current_job_path, 'wan22-animate2')

    def test_video_resume_fingerprint_validates_modes_and_status(self):
        from tools.review.common.video_resume_fingerprint import fingerprint_video_resume_inputs
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_path = Path(current_directory_name)
            (current_job_path / 'request.json').write_text(json.dumps({'mode': 'text', 'references': []}))
            (current_job_path / 'status.json').write_text(json.dumps({'status': 'paused'}))
            self.assertEqual(fingerprint_video_resume_inputs(current_job_path, 'wan22-vace')['status'], 'paused')
            (current_job_path / 'status.json').write_text(json.dumps({'status': 'running'}))
            with self.assertRaises(ValueError):
                fingerprint_video_resume_inputs(current_job_path, 'wan22-vace')
            with self.assertRaises(ValueError):
                fingerprint_video_resume_inputs(current_job_path, 'unknown')

    def test_video_preview_checks_inputs_under_execution_lock(self):
        import fcntl
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_path = Path(current_directory_name)
            current_job_path = current_storage_path / '2026-11-20_20-00-00-1234abcd'
            current_job_path.mkdir()
            (current_job_path / 'request.json').write_text(json.dumps({'references': ['reference-1.png']}))
            (current_job_path / 'status.json').write_text(json.dumps({'status': 'failed'}))
            (current_job_path / 'reference-1.png').write_bytes(b'image')
            current_assets_check = Mock()
            current_manager_instance = ReferenceVideoGenerationManager('/dwpose', current_storage_path, 'unused', Mock(), current_assets_check)
            current_preview_record = current_manager_instance.preview_generation_resume(current_job_path)
            self.assertEqual(current_preview_record['id'], current_job_path.name)
            self.assertEqual(len(current_preview_record['expected_resume_fingerprint']), 64)
            with (current_job_path / 'execution.lock').open('a') as current_lock_stream:
                fcntl.flock(current_lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaisesRegex(ValueError, '종료되지'):
                    current_manager_instance.preview_generation_resume(current_job_path)
            with self.assertRaises(ValueError):
                current_manager_instance.preview_generation_resume(current_storage_path)

    def test_video_preview_rejects_input_change_during_validation(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_path = Path(current_directory_name)
            current_job_path = current_storage_path / '2026-11-20_20-00-00-1234abcd'
            current_job_path.mkdir()
            (current_job_path / 'request.json').write_text(json.dumps({'references': ['reference-1.png']}))
            (current_job_path / 'status.json').write_text(json.dumps({'status': 'failed'}))
            current_image_path = current_job_path / 'reference-1.png'
            current_image_path.write_bytes(b'original')
            current_assets_check = Mock(side_effect=lambda: current_image_path.write_bytes(b'changed'))
            current_manager_instance = ReferenceVideoGenerationManager('/dwpose', current_storage_path, 'unused', Mock(), current_assets_check)
            with self.assertRaisesRegex(ValueError, '검토 중 입력이 변경'):
                current_manager_instance.preview_generation_resume(current_job_path)


    def test_video_preview_is_registered_for_only_supported_services(self):
        from tools.review.common.management_gateway import resolve_management_command
        current_job_identifier = '2026-11-20_20-00-00-1234abcd'
        for current_service_name in ('dwpose', 'wan22-animate2', 'wan22-vace'):
            self.assertEqual(resolve_management_command(current_service_name, 'resume-preview', {'id': current_job_identifier})[:2], ('POST', '/' + current_service_name + '/resume/preview'))
        with self.assertRaises(ValueError):
            resolve_management_command('wan22-fun-control', 'resume-preview', {'id': current_job_identifier})

    def test_reviewed_video_resume_checks_fingerprint_and_command(self):
        from contextlib import nullcontext
        from tools.review.common import gpu_job_queue, model_prepare_process
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_path = Path(current_directory_name)
            current_job_path = current_storage_path / '2026-11-20_20-00-00-1234abcd'
            current_job_path.mkdir()
            (current_job_path / 'request.json').write_text(json.dumps({'references': ['reference-1.png']}))
            (current_job_path / 'status.json').write_text(json.dumps({'status': 'failed'}))
            current_image_path = current_job_path / 'reference-1.png'
            current_image_path.write_bytes(b'original')
            current_manager_instance = ReferenceVideoGenerationManager('/dwpose', current_storage_path, 'unused', Mock(), Mock())
            expected_fingerprint_value = current_manager_instance.preview_generation_resume(current_job_path)['expected_resume_fingerprint']
            with patch.object(model_prepare_process, 'hold_registered_preparation_guard', return_value=nullcontext()), patch.object(gpu_job_queue, 'launch_gpu_process') as current_launch_mock:
                current_image_path.write_bytes(b'changed')
                with self.assertRaises(ValueError):
                    current_manager_instance.resume_reviewed_generation_job(current_job_path, expected_fingerprint_value)
                current_launch_mock.assert_not_called()
                current_image_path.write_bytes(b'original')
                (current_job_path / 'gpu-command.json').write_text(json.dumps({'command': ['wrong'], 'service': 'image'}))
                current_bad_fingerprint = current_manager_instance.preview_generation_resume(current_job_path)['expected_resume_fingerprint']
                with self.assertRaises(ValueError):
                    current_manager_instance.resume_reviewed_generation_job(current_job_path, current_bad_fingerprint)
                current_launch_mock.assert_not_called()
                (current_job_path / 'gpu-command.json').unlink()
                current_result_record = current_manager_instance.resume_reviewed_generation_job(current_job_path, expected_fingerprint_value)
                self.assertEqual(current_result_record['status'], 'queued')
                current_launch_mock.assert_called_once()

    def test_video_reviewed_resume_is_registered(self):
        from tools.review.common.management_gateway import resolve_management_command
        current_job_identifier = '2026-11-20_20-00-00-1234abcd'
        for current_service_name in ('dwpose', 'wan22-animate2', 'wan22-vace'):
            self.assertEqual(resolve_management_command(current_service_name, 'resume-reviewed', {'id': current_job_identifier, 'expected_resume_fingerprint': 'a' * 64})[:2], ('POST', '/' + current_service_name + '/resume/reviewed'))

    def test_hermes_video_resume_duplicate_and_unknown_receipts(self):
        from tools.review.domains.hermes_agent import video_resume_operations as video_operations
        current_job_identifier = '2026-11-20_20-00-00-1234abcd'
        current_other_identifier = '2026-11-20_20-00-00-1234abce'
        def simulate_video_service(current_service_name, current_command_name, current_payload_record):
            if current_command_name == 'resume-preview':
                return {'service': current_service_name, 'id': current_payload_record['id'], 'status': 'failed', 'resume_availability': 'available', 'expected_resume_fingerprint': 'a' * 64}
            if current_payload_record['id'] == current_other_identifier:
                raise OSError('lost response')
            return {'id': current_payload_record['id'], 'status': 'queued'}
        with tempfile.TemporaryDirectory() as current_directory_name, patch.object(video_operations, 'VIDEO_RESUME_RECEIPT_ROOT', Path(current_directory_name)), patch.object(video_operations, 'execute_remote_management_command', side_effect=simulate_video_service) as current_gateway_mock:
            current_result_record = video_operations.submit_hermes_video_resume_once('video_request_1', 'dwpose', current_job_identifier, 'a' * 64)
            self.assertEqual(current_result_record['state'], 'accepted')
            current_result_record = video_operations.submit_hermes_video_resume_once('video_request_1', 'dwpose', current_job_identifier, 'a' * 64)
            self.assertTrue(current_result_record['duplicate'])
            self.assertEqual(len([current_call for current_call in current_gateway_mock.call_args_list if current_call.args[1] == 'resume-reviewed']), 1)
            with self.assertRaises(OSError):
                video_operations.submit_hermes_video_resume_once('video_request_2', 'dwpose', current_other_identifier, 'a' * 64)
            self.assertEqual(video_operations.read_hermes_video_resume_receipt('video_request_2')['state'], 'unknown')
            with self.assertRaises(ValueError):
                video_operations.submit_hermes_video_resume_once('video_request_3', 'dwpose', current_other_identifier, 'a' * 64)

    def test_video_resume_proposal_accepts_only_valid_block(self):
        from tools.review.domains.hermes_agent.delegation_proposal import parse_hermes_video_resume_proposal
        current_proposal_record = {'service': 'wan22-vace', 'job_id': '2026-11-20_20-00-00-1234abcd', 'expected_resume_fingerprint': 'a' * 64}
        current_answer_text = '검토했습니다.\nHERMES_VIDEO_RESUME_PROPOSAL\n' + json.dumps(current_proposal_record) + '\nEND_HERMES_VIDEO_RESUME_PROPOSAL'
        self.assertEqual(parse_hermes_video_resume_proposal(current_answer_text), current_proposal_record)
        for current_invalid_text in (current_answer_text + '\n' + current_answer_text, current_answer_text.replace('wan22-vace', 'unknown'), current_answer_text.replace('a' * 64, 'bad')):
            with self.assertRaises(ValueError):
                parse_hermes_video_resume_proposal(current_invalid_text)

    def test_video_resume_blocks_model_preparation_or_unknown(self):
        from tools.review.domains.hermes_agent import video_resume_operations as video_operations
        current_job_identifier = '2026-11-20_20-00-00-1234abcd'
        for current_availability_value,current_expected_reason in (('download_running','download_running'),('unknown','unavailable')):
            with self.subTest(availability=current_availability_value), tempfile.TemporaryDirectory() as current_directory_name:
                current_preview_record={'service':'dwpose','id':current_job_identifier,'status':'failed','expected_resume_fingerprint':'a'*64,'resume_availability':current_availability_value}
                with patch.object(video_operations,'VIDEO_RESUME_RECEIPT_ROOT',Path(current_directory_name)), patch.object(video_operations,'execute_remote_management_command',return_value=current_preview_record) as current_gateway_mock:
                    current_result_record=video_operations.submit_hermes_video_resume_once('video_request_1','dwpose',current_job_identifier,'a'*64)
                    self.assertEqual((current_result_record['state'],current_result_record['reason']),('blocked',current_expected_reason))
                    self.assertEqual(video_operations.read_hermes_video_resume_receipt('video_request_1')['state'],'not_found')
                    self.assertEqual([current_call.args[1] for current_call in current_gateway_mock.call_args_list],['resume-preview'])

    def test_strict_model_preparation_state_rejects_damaged_record(self):
        import fcntl
        from tools.review.common.model_prepare_process import inspect_registered_preparation_strict
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_state_path=current_root_path/'.local/model-preparation/dwpose-pose'
            self.assertEqual(inspect_registered_preparation_strict(current_root_path,'dwpose-pose'),'idle')
            current_status_path=current_state_path/'status.json'
            for current_invalid_value in ('{', '{}', '{"status":"unknown"}'):
                current_status_path.write_text(current_invalid_value)
                with self.assertRaises(ValueError):
                    inspect_registered_preparation_strict(current_root_path,'dwpose-pose')
            current_status_path.write_text('{"status":"completed"}')
            self.assertEqual(inspect_registered_preparation_strict(current_root_path,'dwpose-pose'),'completed')
            with (current_state_path/'worker.lock').open('a') as current_lock_handle:
                fcntl.flock(current_lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                self.assertEqual(inspect_registered_preparation_strict(current_root_path,'dwpose-pose'),'running')
            current_status_path.unlink()
            current_status_path.symlink_to(current_root_path/'missing')
            with self.assertRaises(OSError):
                inspect_registered_preparation_strict(current_root_path,'dwpose-pose')

    def test_cleanup_summary_hides_paths_and_checks_counts(self):
        from tools.review.domains.hermes_agent.cleanup_preview_observer import summarize_cleanup_preview_record
        current_preview_record={'jobs':[{'path':'private/path','status':'failed'}],'job_count':1,'blocked_jobs':[{'path':'other/private','reason':'sensitive'}],'can_reset':True,'excludes_blocked':True}
        current_summary_record=summarize_cleanup_preview_record('dwpose',current_preview_record)
        self.assertEqual(current_summary_record['status_counts'],{'failed':1})
        self.assertEqual(current_summary_record['blocked_count'],1)
        self.assertNotIn('private',json.dumps(current_summary_record))
        for current_change_values in ({'job_count':2},{'jobs':None},{'blocked_jobs':[None]},{'can_reset':1},{'excludes_blocked':'yes'},{'can_reset':False}):
            with self.assertRaises(ValueError):
                summarize_cleanup_preview_record('dwpose',{**current_preview_record,**current_change_values})

    def test_cleanup_preview_service_masks_errors_and_only_queries(self):
        from tools.review.domains.hermes_agent.cleanup_preview_observer import read_hermes_cleanup_preview
        from tools.review.common import management_client
        current_preview_record={'jobs':[{'path':'secret/job','status':'completed'}],'job_count':1,'blocked_jobs':[],'can_reset':True}
        with patch.object(management_client,'execute_remote_management_command',return_value=current_preview_record) as current_gateway_mock:
            current_summary_record=read_hermes_cleanup_preview('dwpose')
            self.assertEqual(current_summary_record['job_count'],1)
            self.assertNotIn('secret',json.dumps(current_summary_record))
            current_gateway_mock.assert_called_once_with('dwpose','history-reset-preview',{})
        with patch.object(management_client,'execute_remote_management_command',side_effect=ValueError('secret/path')):
            with self.assertRaises(ValueError) as current_error_value:
                read_hermes_cleanup_preview('dwpose')
            self.assertNotIn('secret',str(current_error_value.exception))
        with self.assertRaises(ValueError):
            read_hermes_cleanup_preview('hermes-agent')

    def test_cleanup_preview_rejects_concurrent_same_service(self):
        import threading
        from tools.review.common import management_client
        from tools.review.domains.hermes_agent.cleanup_preview_observer import read_hermes_cleanup_preview
        current_started_event=threading.Event()
        current_release_event=threading.Event()
        current_result_values=[]
        def simulate_slow_preview(current_service_name,current_command_name,current_payload_record):
            current_started_event.set()
            if not current_release_event.wait(timeout=5):raise RuntimeError('test timeout')
            return {'jobs':[],'job_count':0,'blocked_jobs':[],'can_reset':True}
        def execute_first_preview():
            current_result_values.append(read_hermes_cleanup_preview('dwpose'))
        with patch.object(management_client,'execute_remote_management_command',side_effect=simulate_slow_preview) as current_gateway_mock:
            current_worker_thread=threading.Thread(target=execute_first_preview)
            current_worker_thread.start()
            try:
                self.assertTrue(current_started_event.wait(timeout=3))
                with self.assertRaisesRegex(ValueError,'이미 진행 중'):
                    read_hermes_cleanup_preview('dwpose')
                self.assertEqual(current_gateway_mock.call_count,1)
            finally:
                current_release_event.set()
                current_worker_thread.join(timeout=5)
            self.assertFalse(current_worker_thread.is_alive())
            self.assertEqual(current_result_values[0]['job_count'],0)

    def test_source_cleanup_guard_rejects_same_storage_until_scan_finishes(self):
        import threading
        from tools.review.domains.image.image_generation import ImageGenerationManager
        from tools.review.domains.image import image_generation
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_path=Path(current_directory_name)
            current_first_manager=ImageGenerationManager()
            current_second_manager=ImageGenerationManager()
            current_first_manager.job_storage_root=current_storage_path
            current_second_manager.job_storage_root=current_storage_path
            current_started_event=threading.Event()
            current_release_event=threading.Event()
            current_result_values=[]
            def simulate_slow_scan(current_root_path,current_job_targets):
                current_started_event.set()
                if not current_release_event.wait(timeout=5):raise RuntimeError('timeout')
                return {'jobs':[],'job_count':0,'blocked_jobs':[],'can_reset':True}
            with patch.object(image_generation,'describe_generation_cleanup',side_effect=simulate_slow_scan) as current_scan_mock:
                current_worker_thread=threading.Thread(target=lambda:current_result_values.append(current_first_manager.preview_generation_cleanup()))
                current_worker_thread.start()
                try:
                    self.assertTrue(current_started_event.wait(timeout=3))
                    with self.assertRaisesRegex(ValueError,'이미 진행 중'):
                        current_second_manager.preview_generation_cleanup()
                    self.assertEqual(current_scan_mock.call_count,1)
                finally:
                    current_release_event.set()
                    current_worker_thread.join(timeout=5)
                self.assertFalse(current_worker_thread.is_alive())
                self.assertEqual(current_second_manager.preview_generation_cleanup()['job_count'],0)

    def test_cleanup_scan_releases_shared_history_lock(self):
        from tools.review.domains.image import image_generation
        from tools.review.domains.kimodo.generation import KimodoGenerationManager
        from tools.review.common import generation_cleanup
        current_manager_classes=(image_generation.ImageGenerationManager,KimodoGenerationManager)
        for current_manager_class in current_manager_classes:
            with self.subTest(manager=current_manager_class.__name__),tempfile.TemporaryDirectory() as current_directory_name:
                current_manager_instance=current_manager_class()
                current_manager_instance.job_storage_root=Path(current_directory_name)
                def inspect_shared_lock(current_root_path,current_job_targets):
                    current_lock_acquired=image_generation.MANAGER_HISTORY_LOCK.acquire(blocking=False)
                    self.assertTrue(current_lock_acquired)
                    if current_lock_acquired:image_generation.MANAGER_HISTORY_LOCK.release()
                    return {'jobs':[],'job_count':0,'blocked_jobs':[],'can_reset':True}
                current_patch_target=(generation_cleanup if current_manager_class is KimodoGenerationManager else image_generation)
                current_patch_name=('describe_cleanup_excluding_blocked' if current_manager_class is KimodoGenerationManager else 'describe_generation_cleanup')
                with patch.object(current_patch_target,current_patch_name,side_effect=inspect_shared_lock):
                    self.assertEqual(current_manager_instance.preview_generation_cleanup()['job_count'],0)

    def test_cleanup_preview_handles_target_removed_during_scan(self):
        import shutil
        import threading
        from tools.review.domains.image import image_generation
        from tools.review.domains.kimodo.generation import KimodoGenerationManager
        from tools.review.common import generation_cleanup
        for current_manager_class in (image_generation.ImageGenerationManager,KimodoGenerationManager):
            with self.subTest(manager=current_manager_class.__name__), tempfile.TemporaryDirectory() as current_directory_name:
                current_job_root=Path(current_directory_name)/'2026-11-20_00-00-00-12345678'
                current_job_root.mkdir()
                (current_job_root/'status.json').write_text('{"status":"completed"}')
                current_manager_instance=current_manager_class()
                current_manager_instance.job_storage_root=Path(current_directory_name)
                current_entered_event=threading.Event()
                current_continue_event=threading.Event()
                current_result_values=[]
                current_exception_values=[]
                current_patch_target=(generation_cleanup if current_manager_class is KimodoGenerationManager else image_generation)
                current_patch_name=('describe_cleanup_excluding_blocked' if current_manager_class is KimodoGenerationManager else 'describe_generation_cleanup')
                original_scan_function=getattr(current_patch_target,current_patch_name)
                def simulate_late_scan(current_storage_root,current_target_paths):
                    current_entered_event.set()
                    if not current_continue_event.wait(timeout=5):raise RuntimeError('test timeout')
                    return original_scan_function(current_storage_root,current_target_paths)
                def execute_cleanup_preview():
                    try:current_result_values.append(current_manager_instance.preview_generation_cleanup())
                    except (ValueError,OSError) as current_error_value:current_exception_values.append(current_error_value)
                with patch.object(current_patch_target,current_patch_name,side_effect=simulate_late_scan):
                    current_preview_thread=threading.Thread(target=execute_cleanup_preview)
                    current_preview_thread.start()
                    try:
                        self.assertTrue(current_entered_event.wait(timeout=3))
                        shutil.rmtree(current_job_root)
                    finally:
                        current_continue_event.set()
                        current_preview_thread.join(timeout=5)
                    self.assertFalse(current_preview_thread.is_alive())
                if current_manager_class is KimodoGenerationManager:
                    self.assertEqual(current_result_values[0]['job_count'],0)
                    self.assertFalse(current_result_values[0]['can_reset'])
                    self.assertEqual(len(current_result_values[0]['blocked_jobs']),1)
                else:
                    self.assertEqual(len(current_exception_values),1)
                    self.assertEqual(current_result_values,[])

    def test_audio_and_translation_source_reject_duplicate_cleanup_previews(self):
        from tools.review.common.generation_cleanup import hold_cleanup_preview_guard
        from tools.review.domains.music.generation import MusicGenerationManager
        from tools.review.domains.translation.service import TranslationServiceManager
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_root=Path(current_directory_name)
            current_audio_manager=MusicGenerationManager('music-heartmula')
            current_audio_manager.job_storage_root=current_storage_root/'audio'
            current_audio_manager.history_storage_root=current_storage_root/'audio-history'
            current_translation_manager=TranslationServiceManager()
            current_translation_manager.job_storage_root=current_storage_root/'translation'
            for current_manager_instance,current_execute_method in ((current_audio_manager,current_audio_manager.execute_music_command),(current_translation_manager,current_translation_manager.execute_translation_command)):
                with self.subTest(manager=type(current_manager_instance).__name__):
                    with hold_cleanup_preview_guard(current_manager_instance.job_storage_root):
                        with self.assertRaisesRegex(ValueError,'이미 진행 중'):
                            current_execute_method('history-reset-preview',{})
