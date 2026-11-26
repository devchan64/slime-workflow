import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.common import animationgpt_model_download as model


class AuthorT5PreparationTest(unittest.TestCase):
    def test_preparation_records_verified_files_and_detects_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root/'flan-t5-base'
            marker = root/'runtime'/'ready.json'
            content = {'model.safetensors': b'weights', 'config.json': b'config'}
            hashes = {name: hashlib.sha256(data).hexdigest() for name, data in content.items()}
            calls = []
            def fake_download(url, path, digest, identifier):
                calls.append((url, identifier))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content[path.name])
            with patch.object(model, 'AUTHOR_T5_DIRECTORY', target), patch.object(model, 'AUTHOR_T5_MARKER', marker), \
                 patch.object(model, 'author_t5_required_files', return_value=hashes), patch.object(model, 'download_verified_http', side_effect=fake_download):
                self.assertFalse(model.inspect_author_t5_model_files())
                model.prepare_author_t5_model_files()
                self.assertTrue(model.inspect_author_t5_model_files())
                self.assertEqual(len(calls), 2)
                self.assertTrue(all(identifier.startswith('flan-t5-base/') for _, identifier in calls))
                (target/'config.json').write_bytes(b'different')
                self.assertFalse(model.inspect_author_t5_model_files())

    def test_bad_file_does_not_create_ready_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); target = root/'flan-t5-base'; marker = root/'ready.json'
            def bad_download(url, path, digest, identifier):
                path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'wrong')
            with patch.object(model, 'AUTHOR_T5_DIRECTORY', target), patch.object(model, 'AUTHOR_T5_MARKER', marker), \
                 patch.object(model, 'author_t5_required_files', return_value={'model.safetensors': hashlib.sha256(b'good').hexdigest()}), \
                 patch.object(model, 'download_verified_http', side_effect=bad_download):
                with self.assertRaises(ValueError):
                    model.prepare_author_t5_model_files()
                self.assertFalse(marker.exists())

    def test_gateway_prepares_when_flan_t5_is_missing(self):
        from workflow.common.management_gateway import execute_management_command
        with patch.object(model, 'inspect_animationgpt_model_files', return_value=True), \
             patch.object(model, 'inspect_author_t5_model_files', return_value=False), \
             patch('workflow.common.model_prepare_process.inspect_registered_preparation_strict', return_value='idle'), \
             patch('workflow.common.model_prepare_process.start_registered_preparation', return_value={'preparation_status':'running'}) as start, \
             patch('workflow.common.management_transport.send_management_json_response', side_effect=lambda handler, status, value: value):
            status = execute_management_command('animationgpt', 'model-status', {}, gateway_request_handler=object())
            self.assertFalse(status['ready'])
            self.assertIn('FLAN-T5', status['message'])
            self.assertFalse(start.called)
            receipt = execute_management_command('animationgpt', 'prepare', {'action':'prepare'}, gateway_request_handler=object())
            self.assertEqual(receipt['preparation_status'], 'running')
            self.assertEqual(start.call_args.args[1], 'animationgpt')

    def test_inventory_includes_both_actual_dependencies(self):
        from workflow.common.model_file_inventory import resolve_model_inventory_paths
        paths = resolve_model_inventory_paths()['animationgpt']
        self.assertIn(model.AUTHOR_T5_DIRECTORY, paths)
        self.assertIn(model.WORKFLOW_ROOT_DIRECTORY/'.model/animationgpt-author', paths)

    def test_author_weight_restores_and_detects_changed_file(self):
        import contextlib
        class Record:
            def update(self, **kwargs): pass
        @contextlib.contextmanager
        def tracking(_): yield Record()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); target = root/'author'; marker = root/'runtime/author.json'; content = b'author-weights'
            digest = hashlib.sha256(content).hexdigest()
            def restore(path, expected, size, **kwargs):
                self.assertEqual((expected,size),(digest,len(content)))
                path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(content); return True
            with patch.object(model,'AUTHOR_DIRECTORY',target), patch.object(model,'AUTHOR_MARKER',marker), \
                 patch.object(model,'AUTHOR_WEIGHT_SHA256',digest), patch.object(model,'AUTHOR_WEIGHT_SIZE',len(content)), \
                 patch('workflow.common.model_download_records.track_model_download',tracking), \
                 patch('workflow.common.model_backup_restore.restore_verified_backup',side_effect=restore):
                self.assertFalse(model.inspect_author_weight())
                model.prepare_author_weight()
                self.assertTrue(model.inspect_author_weight())
                (target/model.FILENAME).write_bytes(b'changed')
                self.assertFalse(model.inspect_author_weight())
                with self.assertRaises(ValueError): model.prepare_author_weight()
                self.assertEqual((target/model.FILENAME).read_bytes(), b'changed')

    def test_author_weight_without_backup_fails_without_creating_marker(self):
        import contextlib
        class Record:
            def update(self, **kwargs): pass
        @contextlib.contextmanager
        def tracking(_): yield Record()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(model,'AUTHOR_DIRECTORY',root/'author'), patch.object(model,'AUTHOR_MARKER',root/'ready.json'), \
                 patch('workflow.common.model_download_records.track_model_download',tracking), \
                 patch('workflow.common.model_backup_restore.restore_verified_backup',return_value=False):
                with self.assertRaises(FileNotFoundError): model.prepare_author_weight()
                self.assertFalse((root/'ready.json').exists())

    def test_backup_metadata_exposes_code_pinned_hashes(self):
        import json
        from workflow.common.model_backup_metadata import model_metadata
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root/'models'; source.mkdir()
            (source/'flan-t5-base').mkdir(); (source/'animationgpt-author').mkdir()
            config = root/'config.json'; config.write_text(json.dumps({'source_path':str(source)}))
            service_paths = {'animationgpt':[source/'flan-t5-base',source/'animationgpt-author']}
            t5 = model_metadata('flan-t5-base',config_path=config,service_paths=service_paths)
            self.assertEqual(t5['manifest_state'],'code_pinned')
            self.assertEqual(t5['services'],['animationgpt'])
            self.assertEqual(t5['declared_sources'],[{'repository':'google/flan-t5-base','revision':model.T5_REVISION}])
            self.assertEqual(len(t5['declared_files']),6)
            self.assertTrue(all(item['hash_origin']=='application_pinned' for item in t5['declared_files']))
            author = model_metadata('animationgpt-author',config_path=config,service_paths=service_paths)
            self.assertEqual(author['declared_sources'],[])
            self.assertEqual(author['declared_files'][0]['sha256'],model.AUTHOR_WEIGHT_SHA256)
