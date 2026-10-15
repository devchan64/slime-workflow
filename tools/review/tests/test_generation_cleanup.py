"""실제 운영 파일 대신 임시 디렉터리에서 삭제 계약을 검증한다."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.review.common.generation_cleanup import delete_generation_job_files
from tools.review.domains.vace.generation import VaceGenerationManager


class GenerationCleanupTests(unittest.TestCase):
    def test_selected_files_and_size_with_external_preservation(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_storage_root=Path(current_temp_root)/'jobs'
            current_job_root=current_storage_root/'one'
            current_job_root.mkdir(parents=True)
            (current_job_root/'status.json').write_text('{"status":"completed"}')
            (current_job_root/'input.png').write_bytes(b'input')
            (current_job_root/'attempts').mkdir()
            (current_job_root/'attempts'/'output.mp4').write_bytes(b'output')
            current_external_path=Path(current_temp_root)/'original.png'
            current_external_path.write_bytes(b'original')
            current_expected_bytes=sum(current_file_path.stat().st_size for current_file_path in current_job_root.rglob('*') if current_file_path.is_file())
            current_cleanup_result=delete_generation_job_files(current_storage_root,[current_job_root])
            self.assertEqual(current_cleanup_result['deleted_bytes'],current_expected_bytes)
            self.assertFalse(current_job_root.exists())
            self.assertEqual(current_external_path.read_bytes(),b'original')

    def test_preflight_rejects_live_unknown_and_symlink_before_deleting(self):
        for current_status_value in ('running','queued','missing'):
            with self.subTest(status=current_status_value),tempfile.TemporaryDirectory() as current_temp_root:
                current_storage_root=Path(current_temp_root)
                for current_job_name,current_job_status in (('a','completed'),('b',current_status_value)):
                    current_job_path=current_storage_root/current_job_name
                    current_job_path.mkdir()
                    (current_job_path/'status.json').write_text(json.dumps({'status':current_job_status}))
                with self.assertRaises(ValueError):
                    delete_generation_job_files(current_storage_root,[current_storage_root/'a',current_storage_root/'b'])
                self.assertTrue((current_storage_root/'a'/'status.json').exists())
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_storage_root=Path(current_temp_root)/'jobs'; current_storage_root.mkdir()
            current_outside_root=Path(current_temp_root)/'outside'; current_outside_root.mkdir()
            (current_storage_root/'link').symlink_to(current_outside_root,target_is_directory=True)
            with self.assertRaises(ValueError):
                delete_generation_job_files(current_storage_root,[current_storage_root/'link'])
            self.assertTrue(current_outside_root.exists())

    def test_reset_includes_hidden_jobs_and_preserves_other_folders(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_manager_value=VaceGenerationManager()
            current_manager_value.job_storage_root=Path(current_temp_root)/'jobs'
            current_job_root=current_manager_value.job_storage_root/'2026-10-14_00-00-00-12345678'
            current_job_root.mkdir(parents=True)
            (current_job_root/'status.json').write_text('{"status":"completed"}')
            (current_job_root/'.history-deleted').touch()
            current_other_root=current_manager_value.job_storage_root/'registered-assets'; current_other_root.mkdir()
            with patch.object(current_manager_value,'history_storage_path',return_value=Path(current_temp_root)/'history'):
                current_cleanup_result=current_manager_value.reset_generation_history()
            self.assertEqual(current_cleanup_result['deleted_jobs'],1)
            self.assertFalse(current_job_root.exists())
            self.assertTrue(current_other_root.exists())

    def test_legacy_selected_cleanup_preserves_other_jobs(self):
        from tools.review.domains.character_animation import character_animation_jobs as current_jobs_module
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_storage_root=Path(current_temp_root)
            current_job_identifier='2026-10-14_00-00-00-12345678'
            current_other_identifier='2026-10-14_00-00-00-87654321'
            for current_identifier_value in (current_job_identifier,current_other_identifier):
                current_job_path=current_storage_root/current_identifier_value[:19]/current_identifier_value
                current_job_path.mkdir(parents=True)
                (current_job_path/'status.json').write_text('{"status":"completed"}')
            with patch.object(current_jobs_module,'GENERATION_ROOT_DIRECTORY',current_storage_root),patch.object(current_jobs_module,'GENERATION_HISTORY_DIRECTORY',current_storage_root/'history'),patch.object(current_jobs_module,'GENERATION_LOCK_PATH',current_storage_root/'generation.lock'):
                current_delete_result=current_jobs_module.execute_animation_command('history-delete',{'id':current_job_identifier})
                self.assertEqual(current_delete_result['deleted_jobs'],1)
                self.assertTrue(current_jobs_module.resolve_generation_directory(current_other_identifier).exists())
                current_reset_result=current_jobs_module.execute_animation_command('history-reset',{})
                self.assertEqual(current_reset_result['deleted_jobs'],1)

    def test_partial_failure_reports_incomplete_deletion(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_job_path=Path(current_temp_root)/'job'
            current_job_path.mkdir()
            (current_job_path/'status.json').write_text('{"status":"completed"}')
            with patch('tools.review.common.generation_cleanup.shutil.rmtree',side_effect=PermissionError('test denial')):
                with self.assertRaisesRegex(OSError,'일부 실패'):
                    delete_generation_job_files(Path(current_temp_root),[current_job_path])
            self.assertTrue((current_job_path/'status.json').exists())


class CleanupPreviewTests(unittest.TestCase):
    def test_preview_counts_hidden_jobs_without_writes(self):
        from tools.review.common.generation_cleanup import describe_generation_cleanup
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_root=Path(current_directory_name)
            current_job_targets=[]
            for current_job_name,current_status_name in [('visible','completed'),('hidden','queued')]:
                current_job_root=current_storage_root/current_job_name
                current_job_root.mkdir()
                (current_job_root/'status.json').write_text(json.dumps({'status':current_status_name}))
                current_job_targets.append(current_job_root)
            current_before_files=sorted(str(current_file_path) for current_file_path in current_storage_root.rglob('*'))
            current_preview_record=describe_generation_cleanup(current_storage_root,current_job_targets)
            self.assertEqual(current_preview_record['job_count'],2)
            self.assertFalse(current_preview_record['can_reset'])
            self.assertEqual(current_preview_record['blocked_jobs'],[{'path':'hidden','status':'queued'}])
            self.assertEqual(current_before_files,sorted(str(current_file_path) for current_file_path in current_storage_root.rglob('*')))

    def test_preview_rejects_symlinks_and_missing_status(self):
        from tools.review.common.generation_cleanup import describe_generation_cleanup
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_root=Path(current_directory_name)
            current_job_root=current_storage_root/'job'
            current_job_root.mkdir()
            with self.assertRaises(ValueError):describe_generation_cleanup(current_storage_root,[current_job_root])
            (current_job_root/'status.json').write_text('{"status":"completed"}')
            (current_job_root/'outside').symlink_to('/tmp')
            with self.assertRaises(ValueError):describe_generation_cleanup(current_storage_root,[current_job_root])

    def test_image_service_preview_uses_same_hidden_targets_as_reset(self):
        from tools.review.domains.image.image_generation import ImageGenerationManager
        from tools.review.common.management_gateway import resolve_management_command
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_service_instance=ImageGenerationManager()
            current_service_instance.job_storage_root=Path(current_directory_name)
            current_job_root=current_service_instance.job_storage_root/'2026-10-15_00-00-00-12345678'
            current_job_root.mkdir()
            (current_job_root/'status.json').write_text('{"status":"completed"}')
            self.assertEqual(current_service_instance.preview_generation_cleanup()['job_count'],1)
            self.assertTrue(current_job_root.exists())
        self.assertEqual(resolve_management_command('pose-transfer','history-reset-preview',{}),('GET','/pose-transfer/history/reset-preview'))
        with self.assertRaises(ValueError):resolve_management_command('pose-transfer','history-reset-preview',{'action':'reset'})


class AnnyCleanupPreviewTests(unittest.TestCase):
    def test_preview_reports_hidden_jobs_and_blocks_running_without_deletion(self):
        from tools.review.domains.anny import anny_attributes as current_anny_module
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_root=Path(current_directory_name)
            for current_identifier_value,current_status_name in [('12345678','completed'),('abcdef12','queued')]:
                current_job_path=current_storage_root/current_identifier_value
                current_job_path.mkdir()
                (current_job_path/'status.json').write_text(json.dumps({'status':current_status_name}))
                (current_job_path/'.history-deleted').touch()
            with patch.object(current_anny_module,'JOBS',current_storage_root):
                current_preview_record=current_anny_module.preview_anny_history_cleanup()
            self.assertEqual(current_preview_record['job_count'],2)
            self.assertFalse(current_preview_record['can_reset'])
            self.assertTrue((current_storage_root/'12345678'/'status.json').exists())

class CleanupConfirmationTests(unittest.TestCase):
    def test_snapshot_rejects_new_jobs_and_changed_terminal_status(self):
        for current_expected_jobs in ([], [{'path':'job','status':'failed'}]):
            with self.subTest(snapshot=current_expected_jobs), tempfile.TemporaryDirectory() as current_directory_name:
                current_storage_root=Path(current_directory_name)
                current_job_path=current_storage_root/'job'
                current_job_path.mkdir()
                (current_job_path/'status.json').write_text('{"status":"completed"}')
                with self.assertRaisesRegex(ValueError,'변경'):
                    delete_generation_job_files(current_storage_root,[current_job_path],current_expected_jobs=current_expected_jobs)
                self.assertTrue(current_job_path.exists())
                current_delete_result=delete_generation_job_files(current_storage_root,[current_job_path],current_expected_jobs=[{'path':'job','status':'completed'}])
                self.assertEqual(current_delete_result['deleted_jobs'],1)

    def test_confirmation_requires_valid_snapshot_shape(self):
        from tools.review.common.generation_cleanup import read_cleanup_confirmation
        for current_invalid_value in (None, {}, [{'path':'job'}], [{'path':1,'status':'completed'}]):
            with self.subTest(snapshot=current_invalid_value), self.assertRaises(ValueError):
                read_cleanup_confirmation({'action':'reset','expected_jobs':current_invalid_value})
        self.assertEqual(read_cleanup_confirmation({'action':'reset','expected_jobs':[]}),[])

class CleanupServiceSnapshotTests(unittest.TestCase):
    def test_service_reset_rejects_jobs_created_after_empty_preview(self):
        from contextlib import ExitStack
        from tools.review.domains.image.image_generation import ImageGenerationManager
        from tools.review.domains.hy_motion import jobs as current_hymotion_module
        from tools.review.domains.anny import anny_attributes as current_anny_module
        from tools.review.domains.music.generation import MusicGenerationManager
        for current_service_name in ('image','hy-motion','anny','music'):
            with self.subTest(service=current_service_name), tempfile.TemporaryDirectory() as current_directory_name, ExitStack() as current_patch_stack:
                current_storage_root=Path(current_directory_name)/'jobs'
                current_history_root=Path(current_directory_name)/'history'
                current_job_relative='2026-10-15_00-00-00-12345678'
                current_reset_payload={'action':'reset','expected_jobs':[]}
                if current_service_name=='image':
                    current_service_instance=ImageGenerationManager()
                    current_service_instance.job_storage_root=current_storage_root
                    current_patch_stack.enter_context(patch.object(current_service_instance,'history_storage_path',return_value=current_history_root))
                    current_reset_callback=lambda:current_service_instance.reset_generation_history([])
                    self.assertEqual(current_service_instance.preview_generation_cleanup()['jobs'],[])
                elif current_service_name=='hy-motion':
                    current_job_relative='2026-10-15_00-00-00/12345678'
                    current_patch_stack.enter_context(patch.object(current_hymotion_module,'GENERATION_STORAGE_ROOT',current_storage_root))
                    current_patch_stack.enter_context(patch.object(current_hymotion_module,'GENERATION_HISTORY_ROOT',current_history_root))
                    current_reset_callback=lambda:current_hymotion_module.execute_hymotion_command('history-reset',current_reset_payload)
                    self.assertEqual(current_hymotion_module.execute_hymotion_command('history-reset-preview',{})['jobs'],[])
                elif current_service_name=='anny':
                    current_job_relative='12345678'
                    current_patch_stack.enter_context(patch.object(current_anny_module,'JOBS',current_storage_root))
                    current_reset_callback=lambda:current_anny_module.clear_anny_history_records([])
                    self.assertEqual(current_anny_module.preview_anny_history_cleanup()['jobs'],[])
                else:
                    current_service_instance=MusicGenerationManager('music-ace-step')
                    current_service_instance.job_storage_root=current_storage_root
                    current_service_instance.history_storage_root=current_history_root
                    current_reset_callback=lambda:current_service_instance.execute_music_command('history-reset',current_reset_payload)
                    self.assertEqual(current_service_instance.execute_music_command('history-reset-preview',{})['jobs'],[])
                current_job_path=current_storage_root/current_job_relative
                current_job_path.mkdir(parents=True)
                (current_job_path/'status.json').write_text('{"status":"completed"}')
                (current_job_path/'result.bin').write_bytes(b'keep')
                with self.assertRaisesRegex(ValueError,'변경'):
                    current_reset_callback()
                self.assertEqual((current_job_path/'result.bin').read_bytes(),b'keep')


class ImageFamilyCleanupContractTests(unittest.TestCase):
    def test_each_manager_removes_copies_and_indexes_but_rejects_live_jobs(self):
        from importlib import import_module
        current_manager_definitions = (
            ('image.image_generation', 'ImageGenerationManager'),
            ('image.qwen_21_generation', 'QwenPlainGenerationManager'),
            ('image.expression_generation', 'ExpressionGenerationManager'),
            ('image.pose_transfer_generation', 'PoseTransferGenerationManager'),
            ('image.outfit_transfer_generation', 'OutfitTransferGenerationManager'),
            ('image.qwen_circular_generation', 'QwenCircularGenerationManager'),
            ('image.animation_separation', 'AnimationSeparationManager'),
            ('image.seamless_generation', 'SeamlessGenerationManager'),
            ('vace.generation', 'VaceGenerationManager'),
            ('vace.timeline_generation', 'VaceTimelineGenerationManager'),
            ('phantom.generation', 'PhantomGenerationManager'),
        )
        for current_module_name, current_class_name in current_manager_definitions:
            with self.subTest(service=current_class_name), tempfile.TemporaryDirectory() as current_directory_name:
                current_service_instance = getattr(import_module('tools.review.domains.' + current_module_name), current_class_name)()
                current_storage_root = Path(current_directory_name) / 'jobs'
                current_history_root = Path(current_directory_name) / 'history'
                current_history_root.mkdir()
                current_service_instance.job_storage_root = current_storage_root
                current_job_identifiers = ['2026-10-15_00-00-00-' + current_suffix_value for current_suffix_value in ('12345678', '87654321')]
                for current_job_identifier in current_job_identifiers:
                    current_job_root = current_storage_root / current_job_identifier
                    (current_job_root / 'attempts' / 'one').mkdir(parents=True)
                    (current_job_root / 'status.json').write_text('{"status":"completed"}')
                    (current_job_root / 'input.png').write_bytes(b'input copy')
                    (current_job_root / 'attempts' / 'one' / 'worker.log').write_text('실행 기록')
                    (current_job_root / 'result.png').write_bytes(b'result')
                    (current_history_root / (current_job_identifier + '.json')).write_text('{}')
                current_selected_root = current_storage_root / current_job_identifiers[0]
                current_hidden_root = current_storage_root / current_job_identifiers[1]
                (current_hidden_root / '.history-deleted').touch()
                current_external_original = Path(current_directory_name) / 'original.png'
                current_external_original.write_bytes(b'preserve')
                current_registered_root = current_storage_root / 'registered-assets'
                current_registered_root.mkdir()
                with patch.object(current_service_instance, 'history_storage_path', return_value=current_history_root):
                    (current_hidden_root / 'status.json').write_text('{"status":"queued"}')
                    with self.assertRaises(ValueError):
                        current_service_instance.reset_generation_history()
                    self.assertTrue((current_selected_root / 'input.png').exists())
                    with self.assertRaises(ValueError):
                        current_service_instance.delete_generation_history(current_job_identifiers[1])
                    (current_hidden_root / 'status.json').write_text('{"status":"completed"}')
                    current_expected_bytes = sum(current_file_path.stat().st_size for current_file_path in current_selected_root.rglob('*') if current_file_path.is_file()) + 2
                    current_delete_result = current_service_instance.delete_generation_history(current_job_identifiers[0])
                    self.assertEqual(current_delete_result['deleted_bytes'], current_expected_bytes)
                    self.assertFalse(current_selected_root.exists())
                    self.assertFalse((current_history_root / (current_job_identifiers[0] + '.json')).exists())
                    self.assertTrue(current_hidden_root.exists())
                    current_reset_result = current_service_instance.reset_generation_history()
                    self.assertEqual(current_reset_result['deleted_jobs'], 1)
                    self.assertFalse(current_hidden_root.exists())
                    self.assertEqual(list(current_history_root.glob('*.json')), [])
                    self.assertTrue(current_registered_root.is_dir())
                    self.assertEqual(current_external_original.read_bytes(), b'preserve')


class CleanupResumeConcurrencyTests(unittest.TestCase):
    def test_resume_and_delete_share_lock_in_both_orders(self):
        from concurrent.futures import ThreadPoolExecutor
        import fcntl
        import shutil
        import threading
        from tools.review.common.gpu_job_queue import resume_gpu_generation
        current_original_flock = fcntl.flock
        current_original_rmtree = shutil.rmtree
        for current_first_operation in ('resume', 'delete'):
            with self.subTest(first=current_first_operation), tempfile.TemporaryDirectory() as current_directory_name:
                current_storage_root = Path(current_directory_name)
                current_job_root = current_storage_root / 'job'
                current_job_root.mkdir()
                (current_job_root / 'status.json').write_text('{"status":"failed"}')
                (current_job_root / 'gpu-command.json').write_text('{"command":["mock-worker"],"service":"image"}')
                (current_job_root / 'result.png').write_bytes(b'preserve until deleted')
                current_first_entered = threading.Event()
                current_second_waiting = threading.Event()
                current_release_first = threading.Event()

                def observe_cleanup_lock(current_lock_handle, current_lock_operation):
                    if threading.current_thread().name.startswith('second-operation'):
                        current_second_waiting.set()
                    return current_original_flock(current_lock_handle, current_lock_operation)

                def simulate_generation_launch(*current_command_values, **current_process_options):
                    current_first_entered.set()
                    if not current_release_first.wait(5):
                        raise TimeoutError('재개 경합 검증 해제 지연')

                def delay_cleanup_removal(current_target_path):
                    current_first_entered.set()
                    if not current_release_first.wait(5):
                        raise TimeoutError('삭제 경합 검증 해제 지연')
                    return current_original_rmtree(current_target_path)

                def execute_cleanup_action():
                    return delete_generation_job_files(current_storage_root, [current_job_root])

                with patch('fcntl.flock', side_effect=observe_cleanup_lock), patch('tools.review.common.gpu_job_queue.launch_gpu_process', side_effect=simulate_generation_launch) as current_launch_mock, patch('tools.review.common.generation_cleanup.shutil.rmtree', side_effect=delay_cleanup_removal), ThreadPoolExecutor(max_workers=1, thread_name_prefix='first-operation') as current_first_pool, ThreadPoolExecutor(max_workers=1, thread_name_prefix='second-operation') as current_second_pool:
                    current_first_callback = (lambda: resume_gpu_generation(current_job_root)) if current_first_operation == 'resume' else execute_cleanup_action
                    current_second_callback = execute_cleanup_action if current_first_operation == 'resume' else (lambda: resume_gpu_generation(current_job_root))
                    current_first_future = current_first_pool.submit(current_first_callback)
                    try:
                        self.assertTrue(current_first_entered.wait(5))
                        current_second_future = current_second_pool.submit(current_second_callback)
                        self.assertTrue(current_second_waiting.wait(5))
                        self.assertFalse(current_second_future.done())
                    finally:
                        current_release_first.set()
                    current_first_future.result(timeout=5)
                    if current_first_operation == 'resume':
                        with self.assertRaises(ValueError):
                            current_second_future.result(timeout=5)
                        self.assertTrue((current_job_root / 'result.png').is_file())
                        self.assertEqual(json.loads((current_job_root / 'status.json').read_text())['status'], 'queued')
                        current_launch_mock.assert_called_once()
                    else:
                        with self.assertRaises(FileNotFoundError):
                            current_second_future.result(timeout=5)
                        self.assertFalse(current_job_root.exists())
                        current_launch_mock.assert_not_called()
