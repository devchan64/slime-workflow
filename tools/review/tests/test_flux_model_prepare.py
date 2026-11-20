"""FLUX 고정 모델 준비의 파일 보존과 원자적 게시 검증."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from generators.image import flux_model_prepare


class FluxModelPrepareTests(unittest.TestCase):
    def test_preparation_guard_blocks_new_preparation_until_release(self):
        from tools.review.common.model_prepare_process import hold_registered_preparation_guard,start_registered_preparation
        with tempfile.TemporaryDirectory() as current_directory_name:
            with hold_registered_preparation_guard(current_directory_name,'flux-image'):
                with patch('tools.review.common.model_prepare_process.subprocess.Popen') as current_spawn_mock:
                    current_result_value=start_registered_preparation(current_directory_name,'flux-image')
                    self.assertEqual(current_result_value['preparation_status'],'running')
                    current_spawn_mock.assert_not_called()
                with self.assertRaisesRegex(ValueError,'모델 준비가 진행 중'):
                    with hold_registered_preparation_guard(current_directory_name,'flux-image'):pass
            with hold_registered_preparation_guard(current_directory_name,'flux-image'):pass
            with self.assertRaisesRegex(OSError,'inner failure'):
                with hold_registered_preparation_guard(current_directory_name,'flux-image'):
                    raise OSError('inner failure')
            current_lock_path=Path(current_directory_name)/'.local/model-preparation/flux-image/worker.lock'
            current_lock_path.unlink()
            current_outside_path=Path(current_directory_name)/'outside'
            current_outside_path.write_text('unchanged')
            current_lock_path.symlink_to(current_outside_path)
            with self.assertRaises(ValueError):
                with hold_registered_preparation_guard(current_directory_name,'flux-image'):pass
            self.assertEqual(current_outside_path.read_text(),'unchanged')

    def setUp(self):
        self.current_temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.current_temp_directory.cleanup)
        self.current_model_root = Path(self.current_temp_directory.name) / 'model'
        self.current_payload_bytes = b'flux-locked-test'
        self.current_lock_record = {'repository': flux_model_prepare.FLUX_MODEL_REPOSITORY,
            'revision': flux_model_prepare.FLUX_MODEL_REVISION, 'files': [
                {'path': 'transformer/config.json', 'size': len(self.current_payload_bytes),
                 'hash_type': 'sha256', 'digest': hashlib.sha256(self.current_payload_bytes).hexdigest()}]}
        self.current_model_patch = patch.object(flux_model_prepare, 'FLUX_MODEL_DIRECTORY', self.current_model_root)
        self.current_lock_patch = patch.object(flux_model_prepare, 'read_flux_model_lock', return_value=self.current_lock_record)
        self.current_model_patch.start()
        self.current_lock_patch.start()
        self.addCleanup(self.current_model_patch.stop)
        self.addCleanup(self.current_lock_patch.stop)

    def write_trial_download(self, current_repository_name, **current_download_options):
        current_stage_path = current_download_options['local_dir']
        current_file_path = current_stage_path / 'transformer/config.json'
        current_file_path.parent.mkdir(parents=True, exist_ok=True)
        current_file_path.write_bytes(self.current_payload_bytes)
        self.assertEqual(current_download_options['revision'], flux_model_prepare.FLUX_MODEL_REVISION)
        self.assertEqual(current_download_options['allow_patterns'], ['transformer/config.json'])

    def test_prepare_downloads_verifies_and_publishes(self):
        with patch('tools.review.common.model_huggingface_download.tracked_snapshot_download', side_effect=self.write_trial_download) as current_download_mock:
            flux_model_prepare.prepare_flux_model_files()
            flux_model_prepare.prepare_flux_model_files()
        current_download_mock.assert_called_once()
        self.assertEqual((self.current_model_root / 'transformer/config.json').read_bytes(), self.current_payload_bytes)

    def test_existing_incomplete_model_is_preserved(self):
        self.current_model_root.mkdir()
        current_file_path = self.current_model_root / 'user.txt'
        current_file_path.write_text('보존')
        with patch('tools.review.common.model_huggingface_download.tracked_snapshot_download') as current_download_mock:
            with self.assertRaises(ValueError):
                flux_model_prepare.prepare_flux_model_files()
        current_download_mock.assert_not_called()
        self.assertEqual(current_file_path.read_text(), '보존')

    def test_existing_modified_stage_file_is_not_overwritten(self):
        current_stage_path = self.current_model_root.parent / '.flux-3-image-klein.preparing'
        current_stage_path.mkdir()
        (current_stage_path / '.flux-preparation-revision').write_text(flux_model_prepare.FLUX_MODEL_REVISION)
        current_file_path = current_stage_path / 'transformer/config.json'
        current_file_path.parent.mkdir()
        current_file_path.write_bytes(b'changed')
        with patch('tools.review.common.model_huggingface_download.tracked_snapshot_download') as current_download_mock:
            with self.assertRaises(ValueError):
                flux_model_prepare.prepare_flux_model_files()
        current_download_mock.assert_not_called()
        self.assertEqual(current_file_path.read_bytes(), b'changed')

    def test_status_blocks_incomplete_existing_model_and_allows_missing_model(self):
        from tools.review.domains.image.flux_image_generation import FluxImageGenerationManager
        current_service_manager = FluxImageGenerationManager('flux-image')
        with patch('tools.review.common.model_prepare_process.inspect_registered_preparation', return_value='idle'):
            current_missing_status = current_service_manager.inspect_flux_model_status()
            self.assertFalse(current_missing_status['ready'])
            self.assertTrue(current_missing_status['can_prepare'])
            self.current_model_root.mkdir()
            current_incomplete_status = current_service_manager.inspect_flux_model_status()
            self.assertFalse(current_incomplete_status['ready'])
            self.assertFalse(current_incomplete_status['can_prepare'])
            self.assertIn('덮어쓰지 않습니다', current_incomplete_status['message'])

    def test_model_status_rejects_linked_file_and_directory(self):
        self.current_model_root.mkdir()
        current_external_root = self.current_model_root.parent / 'external'
        current_external_root.mkdir()
        (current_external_root / 'config.json').write_bytes(self.current_payload_bytes)
        current_model_link = self.current_model_root / 'transformer'
        current_model_link.symlink_to(current_external_root, target_is_directory=True)
        self.assertFalse(flux_model_prepare.inspect_flux_model_file_sizes(self.current_model_root, self.current_lock_record))
        current_model_link.unlink()
        current_model_link.mkdir()
        (current_model_link / 'config.json').symlink_to(current_external_root / 'config.json')
        self.assertFalse(flux_model_prepare.inspect_flux_model_file_sizes(self.current_model_root, self.current_lock_record))
        self.assertEqual((current_external_root / 'config.json').read_bytes(), self.current_payload_bytes)

    def test_stage_parent_symlink_is_not_followed(self):
        current_stage_path = self.current_model_root.parent / '.flux-3-image-klein.preparing'
        current_stage_path.mkdir()
        (current_stage_path / '.flux-preparation-revision').write_text(flux_model_prepare.FLUX_MODEL_REVISION)
        current_other_directory = self.current_model_root.parent / 'other'
        current_other_directory.mkdir()
        (current_stage_path / 'transformer').symlink_to(current_other_directory, target_is_directory=True)
        with patch('tools.review.common.model_huggingface_download.tracked_snapshot_download') as current_download_mock:
            with self.assertRaises(ValueError):
                flux_model_prepare.prepare_flux_model_files()
        current_download_mock.assert_not_called()
        self.assertEqual(list(current_other_directory.iterdir()), [])

    def test_publish_does_not_replace_existing_directory(self):
        current_stage_path = self.current_model_root.parent / 'stage'
        current_stage_path.mkdir()
        self.current_model_root.mkdir()
        with self.assertRaises(FileExistsError):
            flux_model_prepare.publish_flux_model_directory(current_stage_path, self.current_model_root)
        self.assertTrue(current_stage_path.is_dir())
        self.assertTrue(self.current_model_root.is_dir())


class FluxResidentRuntimeTests(unittest.TestCase):
    def test_components_load_one_at_a_time_and_remain_on_gpu(self):
        from types import SimpleNamespace
        from generators.image.flux_gpu_resident import load_flux_resident_components
        current_events = []
        class CurrentTensorValue:
            def __init__(self):
                self.device = SimpleNamespace(type='cpu')
        class CurrentModelModule:
            def __init__(self, current_model_name):
                self.current_model_name = current_model_name
                self.current_tensor_value = CurrentTensorValue()
            def to(self, current_device_name):
                current_events.append(('move', self.current_model_name, current_device_name))
                self.current_tensor_value.device.type = current_device_name
            def parameters(self):
                return [self.current_tensor_value]
            def buffers(self):
                return []
        class CurrentPipelineValue:
            def load_components(self, names, **current_options):
                current_name_value = names[0]
                current_events.append(('load', current_name_value))
                setattr(self,current_name_value, object() if current_name_value == 'tokenizer' else CurrentModelModule(current_name_value))
        current_torch_value = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:True), version=SimpleNamespace(hip='test'), nn=SimpleNamespace(Module=CurrentModelModule), float32='float32', bfloat16='bfloat16')
        load_flux_resident_components(CurrentPipelineValue(),current_torch_value,'/model')
        self.assertEqual(current_events, [('load','text_encoder'),('move','text_encoder','cuda'),('load','tokenizer'),('load','transformer'),('move','transformer','cuda'),('load','vae'),('move','vae','cuda')])
        current_torch_value.version.hip = None
        with self.assertRaisesRegex(ValueError,'ROCm'):
            load_flux_resident_components(CurrentPipelineValue(),current_torch_value,'/model')

    def test_failed_or_non_gpu_component_stops_execution(self):
        from types import SimpleNamespace
        from generators.image.flux_gpu_resident import load_flux_resident_components
        class CurrentModelModule:
            def to(self, current_device_name):
                pass
            def parameters(self):
                return [SimpleNamespace(device=SimpleNamespace(type='cpu'))]
            def buffers(self):
                return []
        class CurrentPipelineValue:
            def load_components(self, names, **current_options):
                setattr(self,names[0], CurrentModelModule())
        current_torch_value = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:True), version=SimpleNamespace(hip='test'), nn=SimpleNamespace(Module=CurrentModelModule), float32='float32', bfloat16='bfloat16')
        with self.assertRaisesRegex(ValueError,'GPU 적재'):
            load_flux_resident_components(CurrentPipelineValue(),current_torch_value,'/model')


class FluxModelLockTests(unittest.TestCase):
    def test_lock_rejects_duplicate_fields_and_missing_required_files(self):
        import yaml
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_lock_path = Path(temporary_directory_name) / 'lock.yaml'
            current_lock_path.write_text('repository: one\nrepository: two\n')
            with self.assertRaisesRegex(ValueError, '중복'):
                flux_model_prepare.read_flux_model_lock(current_lock_path)
            current_valid_lock = flux_model_prepare.read_flux_model_lock()
            current_valid_lock['files'] = current_valid_lock['files'][:-1]
            current_lock_path.write_text(yaml.safe_dump(current_valid_lock))
            with self.assertRaisesRegex(ValueError, '필수 구성 파일 누락'):
                flux_model_prepare.read_flux_model_lock(current_lock_path)


if __name__ == '__main__':
    unittest.main()
