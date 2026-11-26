import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from workflow.common import audio_model_download


class AudioDownloadCompletenessTests(unittest.TestCase):
    def test_heartmula_shard_index_cannot_escape_model_directory(self):
        from generators.music.heartmula.separation import DEMUCS_CHECKPOINT_NAME
        with TemporaryDirectory() as directory:
            model = Path(directory)/'.model/music/music-heartmula'
            files = {'bundle/tokenizer.json': '{}', 'bundle/gen_config.json': '{}',
                     'demucs/'+DEMUCS_CHECKPOINT_NAME: 'demucs'}
            for component in ('HeartMuLa-oss-3B', 'HeartCodec-oss'):
                files[f'bundle/{component}/config.json'] = '{}'
                files[f'bundle/{component}/model.safetensors.index.json'] = json.dumps({'weight_map': {'x': '../../outside'}})
            for name, content in files.items():
                path = model/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            with self.assertRaises(ValueError):
                audio_model_download.validate_heartmula_required_files(model)
            component = model/'bundle/HeartMuLa-oss-3B'
            (component/'model.safetensors.index.json').write_text(json.dumps({'weight_map': {'x': 'weights.safetensors'}}))
            (component/'weights.safetensors').symlink_to(model/'bundle/tokenizer.json')
            with self.assertRaises(ValueError):
                audio_model_download.validate_heartmula_required_files(model)

    def test_heartmula_receipt_with_missing_indexed_shard_is_not_ready(self):
        from generators.music.heartmula.separation import DEMUCS_CHECKPOINT_NAME
        with TemporaryDirectory() as directory:
            root = Path(directory)
            model = root/'.model/music/music-heartmula'
            sources = (('repo/bundle', 'a'*40, 'bundle'),)
            files = {'bundle/tokenizer.json': '{}', 'bundle/gen_config.json': '{}',
                     'demucs/'+DEMUCS_CHECKPOINT_NAME: 'demucs'}
            for component in ('HeartMuLa-oss-3B', 'HeartCodec-oss'):
                files[f'bundle/{component}/config.json'] = '{}'
                files[f'bundle/{component}/model.safetensors.index.json'] = json.dumps({'weight_map': {'x': 'missing.safetensors'}})
            receipt_files = {}
            for name, text in files.items():
                path = model/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
                info = path.stat()
                receipt_files[name] = [info.st_size, info.st_mtime_ns, info.st_ctime_ns]
            receipt = root/'.local/model-preparation/heartmula-model/files.json'
            receipt.parent.mkdir(parents=True)
            receipt.write_text(json.dumps({'sources': [list(source) for source in sources], 'files': receipt_files}))
            with patch.object(audio_model_download, 'WORKFLOW_ROOT_DIRECTORY', root), \
                 patch.object(audio_model_download, 'resolve_music_paths', return_value=(None, model, None)), \
                 patch.object(audio_model_download, 'resolve_audio_download_sources', return_value=sources):
                self.assertFalse(audio_model_download.inspect_audio_download_files('music-heartmula'))

    def test_old_receipt_with_only_unrelated_file_is_not_ready(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            model = root/'.model'/'music'/'sfx-dasheng-audiogen'
            unrelated = model/'model'/'unrelated.txt'
            unrelated.parent.mkdir(parents=True)
            unrelated.write_text('not a model')
            info = unrelated.stat()
            sources = (('repo/model', 'a'*40, 'model'),)
            receipt = root/'.local/model-preparation/dasheng-model/files.json'
            receipt.parent.mkdir(parents=True)
            receipt.write_text(json.dumps({'sources': [list(source) for source in sources],
                                           'files': {'model/unrelated.txt': [info.st_size, info.st_mtime_ns, info.st_ctime_ns]}}))
            with patch.object(audio_model_download, 'WORKFLOW_ROOT_DIRECTORY', root), \
                 patch.object(audio_model_download, 'resolve_music_paths', return_value=(None, model, None)), \
                 patch.object(audio_model_download, 'resolve_audio_download_sources', return_value=sources):
                self.assertFalse(audio_model_download.inspect_audio_download_files('sfx-dasheng-audiogen'))
                from workflow.common.management_gateway import ManagementCommandGateway
                from workflow.tests.test_management_gateway import GatewayContractTest
                handler = GatewayContractTest().create_request_handler('/management/command',
                    {'service': 'sfx-dasheng-audiogen', 'command': 'download-model-status', 'payload': {}})
                with patch('workflow.common.model_prepare_process.inspect_registered_preparation', return_value='idle'):
                    self.assertTrue(ManagementCommandGateway({'sfx-dasheng-audiogen': Mock()}).handle(handler))
                self.assertFalse(json.loads(handler.wfile.getvalue())['ready'])

    def test_incomplete_offline_directory_does_not_create_ready_receipt(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            model = root/'.model'/'music'/'sfx-dasheng-audiogen'
            sources = (('repo/model', 'a'*40, 'model'),)
            def incomplete(**options):
                target = Path(options['local_dir'])
                target.mkdir(parents=True, exist_ok=True)
                (target/'unrelated.txt').write_text('not a model')
                return str(target)
            with patch.object(audio_model_download, 'WORKFLOW_ROOT_DIRECTORY', root), \
                 patch.object(audio_model_download, 'resolve_music_paths', return_value=(None, model, None)), \
                 patch.object(audio_model_download, 'resolve_audio_download_sources', return_value=sources), \
                 patch('workflow.common.model_huggingface_download.tracked_snapshot_download', side_effect=incomplete):
                with self.assertRaisesRegex(ValueError, '필수 모델 파일'):
                    audio_model_download.download_audio_model_files('sfx-dasheng-audiogen')
                self.assertFalse(audio_model_download.inspect_audio_download_files('sfx-dasheng-audiogen'))
            self.assertEqual((model/'model'/'unrelated.txt').read_text(), 'not a model')

    def test_empty_required_weight_does_not_create_ready_receipt(self):
        from workflow.common.model_offline_audio_check import REQUIRED
        with TemporaryDirectory() as directory:
            root = Path(directory)
            model = root/'.model'/'music'/'sfx-dasheng-audiogen'
            sources = (('repo/model', 'a'*40, 'model'),)
            def incomplete(**options):
                target = Path(options['local_dir'])
                target.mkdir(parents=True, exist_ok=True)
                for name in REQUIRED['sfx-dasheng-audiogen']['dasheng-audiogen']:
                    (target/name).write_bytes(b'' if name == 'model.safetensors' else b'fixture')
                return str(target)
            with patch.object(audio_model_download, 'WORKFLOW_ROOT_DIRECTORY', root), \
                 patch.object(audio_model_download, 'resolve_music_paths', return_value=(None, model, None)), \
                 patch.object(audio_model_download, 'resolve_audio_download_sources', return_value=sources), \
                 patch('workflow.common.model_huggingface_download.tracked_snapshot_download', side_effect=incomplete):
                with self.assertRaisesRegex(ValueError, 'model.safetensors'):
                    audio_model_download.download_audio_model_files('sfx-dasheng-audiogen')
                self.assertFalse(audio_model_download.inspect_audio_download_files('sfx-dasheng-audiogen'))
            self.assertEqual((model/'model'/'model.safetensors').stat().st_size, 0)


if __name__ == '__main__':
    unittest.main()
