import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workflow.common.model_backup_restore import restore_verified_backup
from workflow.common.model_backup_metadata import model_metadata
from workflow.common.model_backup_service import compare_backup_model, list_backup_models
from workflow.common.model_backup_sync import sync_snapshot


class CatalogBackupTargetTest(unittest.TestCase):
    def test_new_snapshot_reports_copy_verification_progress(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root/'local', root/'backup'
            model = source/'example'
            model.mkdir(parents=True)
            backup.mkdir()
            data = b'verify copied snapshot'
            (model/'weights').write_bytes(data)
            phases = []
            result = sync_snapshot('example', 'c'*32, roots=(source, backup, None),
                                   phase=lambda stage, path, done, total: phases.append((stage, path, done, total)))
            self.assertEqual(result['verification'], 'sha256_after_copy')
            self.assertIn(('백업 사본 해시 확인', 'weights', 0, len(data)), phases)
            self.assertIn(('백업 사본 해시 확인', 'weights', len(data), len(data)), phases)

    def test_relocated_audio_catalog_snapshots_restore_model_files(self):
        for name, directory in (('catalog-heartmula', 'heartmula-oss-3b'),
                                ('catalog-dasheng-audiogen', 'dasheng-audiogen')):
            with self.subTest(name=name), TemporaryDirectory() as temporary:
                root = Path(temporary)
                source, backup = root/'local', root/'backup'
                model = source/directory
                model.mkdir(parents=True)
                backup.mkdir()
                data = b'model snapshot content'
                (model/'weights').write_bytes(data)
                config = root/'config.json'
                config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
                sync_snapshot(name, 'a'*32, roots=(source, backup, None))
                (model/'weights').unlink()
                with patch('workflow.common.model_backup_restore.CONFIG_PATH', config):
                    self.assertFalse(restore_verified_backup(model/'weights', hashlib.sha256(b'wrong').hexdigest()))
                    self.assertFalse((model/'weights').exists())
                    self.assertTrue(restore_verified_backup(model/'weights', hashlib.sha256(data).hexdigest()))
                self.assertEqual((model/'weights').read_bytes(), data)

    def test_flattened_model_snapshot_compare_and_restore(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'local', root / 'backup'
            model = source / 'audio/heartmula'
            model.mkdir(parents=True)
            backup.mkdir()
            content = b'flattened model weight'
            (model / 'weights').write_bytes(content)
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            result = sync_snapshot('catalog-heartmula', 'f' * 32, roots=(source, backup, None))
            self.assertEqual(result['file_count'], 1)
            comparison = compare_backup_model('catalog-heartmula', config, hash_content=True, target='latest_snapshot')
            self.assertEqual(comparison['files'][0]['status'], 'verified')
            stage = source / 'stage'
            stage.mkdir()
            with patch('workflow.common.model_backup_restore.CONFIG_PATH', config):
                restored = restore_verified_backup(stage / 'weights', hashlib.sha256(content).hexdigest(),
                                                   backup_source_target=model / 'weights')
            self.assertTrue(restored)
            self.assertEqual((stage / 'weights').read_bytes(), content)

    def test_flattened_target_uses_source_layout_for_backup(self):
        from workflow.common.model_backup_targets import target_path
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'local', root / 'backup'
            (source / 'audio/heartmula').mkdir(parents=True)
            (backup / 'models/audio/heartmula').mkdir(parents=True)
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            item = next(x for x in list_backup_models(config)['models'] if x['name'] == 'catalog-heartmula')
            self.assertEqual(item['relative_path'], 'audio/heartmula')
            self.assertTrue(item['local_present'])
            self.assertFalse(item['backup_present'])
            self.assertEqual(target_path(backup, 'catalog-heartmula', layout_root=source), backup / 'audio/heartmula')
            (source / 'models/audio/heartmula').mkdir(parents=True)
            with self.assertRaises(ValueError):
                target_path(source, 'catalog-heartmula')

    def test_flattened_top_level_target_is_equivalent_not_its_own_parent(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'local', root / 'backup'
            (source / 'hermes-coding').mkdir(parents=True)
            backup.mkdir()
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            models = {item['name']: item for item in list_backup_models(config)['models']}
            item = models['catalog-hermes-coding']
            self.assertEqual(item['equivalent_target'], 'hermes-coding')
            self.assertNotIn('parent_target', item)
            self.assertNotIn('included_targets', models['hermes-coding'])

    def test_broken_snapshot_link_does_not_prevent_backup_restore(self):
        for backup_name, relative in [('models', 'audio/heartmula/weight'),
                                      ('catalog-heartmula', 'weight')]:
            with self.subTest(backup_name=backup_name), TemporaryDirectory() as temporary:
                root = Path(temporary)
                source, backup = root / 'local', root / 'backup'
                target = source / 'models/audio/heartmula/weight'
                target.parent.mkdir(parents=True)
                snapshots = backup / '.model-backup-snapshots' / backup_name
                valid = snapshots / ('a' * 32)
                (valid / relative).parent.mkdir(parents=True)
                (valid / '.snapshot.json').write_text('{}')
                (valid / relative).write_bytes(b'known')
                (snapshots / ('b' * 32)).symlink_to(root / 'missing')
                config = root / 'config.json'
                config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
                with patch('workflow.common.model_backup_restore.CONFIG_PATH', config):
                    self.assertTrue(restore_verified_backup(target, hashlib.sha256(b'known').hexdigest()))
                self.assertEqual(target.read_bytes(), b'known')

    def test_snapshot_listing_rejects_symlink_and_keeps_unknown(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup, outside = root / 'local', root / 'backup', root / 'outside'
            (source / 'models/audio/heartmula').mkdir(parents=True)
            backup.mkdir(); outside.mkdir()
            (backup / '.model-backup-snapshots').symlink_to(outside, target_is_directory=True)
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            result = list_backup_models(config)
            item = next(x for x in result['models'] if x['name'] == 'catalog-heartmula')
            self.assertIsNone(item['snapshot_present'])
            self.assertTrue(result['backup_error'])

    def test_parent_snapshot_restores_nested_audio_installation(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'local', root / 'backup'
            audio = source / 'models/audio/heartmula/bundle'
            audio.mkdir(parents=True)
            backup.mkdir()
            content = b'audio-weight'
            (audio / 'weight').write_bytes(content)
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            sync_snapshot('models', 'd' * 32, roots=(source, backup, None))
            comparison = compare_backup_model('models', config, hash_content=True, target='latest_snapshot')
            self.assertEqual([item['status'] for item in comparison['files']], ['verified'])
            staging = source / 'staging'
            staging.mkdir()
            with patch('workflow.common.model_backup_restore.CONFIG_PATH', config):
                self.assertTrue(restore_verified_backup(staging / 'weight', hashlib.sha256(content).hexdigest(),
                                                       backup_source_target=audio / 'weight'))
            self.assertEqual((staging / 'weight').read_bytes(), content)

    def test_remote_access_error_does_not_hide_local_installation(self):
        from workflow.common.model_backup_service import _directory_presence
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'local', root / 'backup'
            (source / 'models/audio/heartmula').mkdir(parents=True)
            backup.mkdir()
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            def check(directory, name, **kwargs):
                if directory == backup and name == 'catalog-heartmula':
                    raise PermissionError('inaccessible')
                return _directory_presence(directory, name, **kwargs)
            with patch('workflow.common.model_backup_service._directory_presence', side_effect=check):
                result = list_backup_models(config)
            item = next(x for x in result['models'] if x['name'] == 'catalog-heartmula')
            self.assertTrue(item['local_present'])
            self.assertIsNone(item['backup_present'])
            self.assertTrue(result['backup_error'])

    def test_audio_legacy_presence_is_distinct_from_new_backup(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'local', root / 'backup'
            (source / 'models/audio/heartmula').mkdir(parents=True)
            (backup / 'music/music-heartmula').mkdir(parents=True)
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            item = next(x for x in list_backup_models(config)['models'] if x['name'] == 'catalog-heartmula')
            self.assertTrue(item['local_present'])
            self.assertFalse(item['backup_present'])
            self.assertTrue(item['legacy_backup_present'])

    def test_relocated_hermes_readiness_and_backup_recovery(self):
        from workflow.common.model_storage_move import move_storage, rollback_storage
        from workflow.common import hermes_model_download as hermes
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / '.model', root / 'backup'
            old = source / 'hermes-agent'
            old.mkdir(parents=True); backup.mkdir()
            data = b'hermes-weights'
            weight = old / hermes.HERMES_MODEL_FILENAME
            weight.write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            (old / 'ready.sha256').write_text(json.dumps({'sha256': digest, 'size': len(data),
                                                        'mtime_ns': weight.stat().st_mtime_ns}))
            journal = root / 'hermes-migration.json'
            move_storage(source, 'hermes-coding', journal)
            new = source / 'models/hermes-coding'
            with patch.object(hermes, 'HERMES_MODEL_DIRECTORY', new), patch.object(hermes, 'HERMES_MODEL_SHA256', digest):
                self.assertTrue(hermes.inspect_hermes_model_files())
                hermes.verify_hermes_model_integrity()
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            sync_snapshot('catalog-hermes-coding', 'c' * 32, roots=(source, backup, None))
            self.assertEqual({item['status'] for item in compare_backup_model('catalog-hermes-coding', config, hash_content=True, target='latest_snapshot')['files']}, {'verified'})
            stage = source / 'temporary'
            stage.mkdir()
            with patch('workflow.common.model_backup_restore.CONFIG_PATH', config):
                self.assertTrue(restore_verified_backup(stage / 'weight', digest, backup_source_target=new / hermes.HERMES_MODEL_FILENAME))
            rollback_storage(source, 'hermes-coding', journal)
            self.assertEqual((old / hermes.HERMES_MODEL_FILENAME).read_bytes(), data)

    def test_relocated_cache_snapshot_comparison_and_recovery(self):
        from workflow.common.model_storage_move import move_storage, rollback_storage
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / '.model', root / 'backup'
            snapshot = source / 'huggingface/hub/repo/snapshots/revision'
            blobs = snapshot.parent.parent / 'blobs'
            snapshot.mkdir(parents=True); blobs.mkdir(); backup.mkdir()
            (blobs / 'weights').write_bytes(b'weights')
            (snapshot / 'weights').symlink_to('../../blobs/weights')
            journal = root / 'cache-migration.json'
            move_storage(source, 'minimax-hf-cache', journal)
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            result = sync_snapshot('catalog-minimax-hf-cache', 'b' * 32, roots=(source, backup, None))
            self.assertEqual(result['file_count'], 2)
            comparison = compare_backup_model('catalog-minimax-hf-cache', config, hash_content=True, target='latest_snapshot')
            self.assertEqual({item['status'] for item in comparison['files']}, {'verified'})
            destination = source / 'temporary'
            destination.mkdir()
            source_target = source / 'cache/huggingface/hub/repo/blobs/weights'
            with patch('workflow.common.model_backup_restore.CONFIG_PATH', config):
                self.assertTrue(restore_verified_backup(destination / 'weights', hashlib.sha256(b'weights').hexdigest(),
                                                       backup_source_target=source_target))
            self.assertEqual((destination / 'weights').read_bytes(), b'weights')
            rollback_storage(source, 'minimax-hf-cache', journal)
            self.assertEqual((snapshot / 'weights').read_bytes(), b'weights')

    def test_legacy_hash_worker_records_target_and_verified_result(self):
        import fcntl
        import os
        from workflow.common.model_backup_verification import read_verification, run_worker, start_backup_job
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'local', root / 'backup'
            model = source / 'models/flux-report-vision'
            legacy = backup / 'flux-report-vision'
            model.mkdir(parents=True); legacy.mkdir(parents=True)
            (model / 'weights').write_bytes(b'weights')
            (legacy / 'weights').write_bytes(b'weights')
            job_id = 'f' * 32
            with self.assertRaises(ValueError):
                start_backup_job('unregistered', target='legacy', state_root=root / 'state')
            with (root / 'worker.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                arguments = ['worker', '--model', 'catalog-flux-report-vision', '--target', 'legacy',
                             '--job-id', job_id, '--state-root', str(root), '--status-path', str(root / 'status.json'),
                             '--lock-fd', str(os.dup(lock.fileno()))]
                with patch('sys.argv', arguments), patch('workflow.common.model_backup_service.read_backup_roots', return_value=(source, backup, None)):
                    run_worker()
            record = read_verification(job_id, state_root=root)
            self.assertEqual((record['status'], record['target']), ('completed', 'legacy'))
            self.assertEqual(record['result']['files'][0]['status'], 'verified')

    def test_legacy_comparison_uses_old_share_for_new_installation(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'local', root / 'backup'
            model = source / 'models/flux-report-vision'
            legacy = backup / 'flux-report-vision'
            model.mkdir(parents=True); legacy.mkdir(parents=True)
            (model / 'weights').write_bytes(b'weights')
            (legacy / 'weights').write_bytes(b'weights')
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            old = compare_backup_model('catalog-flux-report-vision', config, hash_content=True, target='legacy')
            self.assertEqual(old['target'], 'legacy')
            self.assertEqual(old['files'][0]['status'], 'verified')
            current = compare_backup_model('catalog-flux-report-vision', config, target='canonical')
            self.assertEqual(current['files'][0]['status'], 'missing')
            (source / 'unregistered').mkdir()
            with self.assertRaises(ValueError):
                compare_backup_model('unregistered', config, target='legacy')

    def test_nested_target_snapshot_and_restore(self):
        for target, name in [('catalog-flux-report-vision', 'flux-report-vision'),
                             ('catalog-trellis-dinov2', 'trellis-dinov2'),
                             ('catalog-trellis-image-large', 'trellis-image-large'),
                             ('catalog-hermes-coding', 'hermes-coding'),
                             ('catalog-writer-agent', 'qwen3-embedding-0.6b')]:
            with self.subTest(target=target):
                self._check_nested_target(target, name)

    def _check_nested_target(self, target, name):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup = root / 'local', root / 'backup'
            model = source / 'models' / name
            model.mkdir(parents=True)
            backup.mkdir()
            (model / 'weights').write_bytes(b'weights')
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            listed = {item['name']: item for item in list_backup_models(config)['models']}
            self.assertEqual(listed[target]['parent_target'], 'models')
            self.assertIn(target, listed['models']['included_targets'])
            outcome = sync_snapshot(target, 'a' * 32, roots=(source, backup, None))
            self.assertEqual(outcome['file_count'], 1)
            comparison = compare_backup_model(target, config, hash_content=True, target='latest_snapshot')
            self.assertEqual(comparison['files'][0]['status'], 'verified')
            destination = source / 'temporary'
            destination.mkdir()
            with patch('workflow.common.model_backup_restore.CONFIG_PATH', config):
                self.assertTrue(restore_verified_backup(destination / 'weight', hashlib.sha256(b'weights').hexdigest(),
                                                       backup_source_target=model / 'weights'))
            self.assertEqual((destination / 'weight').read_bytes(), b'weights')

    def test_symlinked_parent_is_rejected(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, backup, outside = root / 'local', root / 'backup', root / 'outside'
            source.mkdir(); backup.mkdir(); outside.mkdir()
            (source / 'models').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                sync_snapshot('catalog-flux-report-vision', 'a' * 32, roots=(source, backup, None))

    def test_verified_manifest_is_declaration_not_live_hash_check(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'local'
            model = source / 'models/trellis-image-large'
            model.mkdir(parents=True)
            (model / 'verified-manifest.json').write_text(json.dumps({
                'repository': 'example/model', 'revision': 'rev',
                'files': [{'path': 'weight', 'sha256': 'a' * 64}]}))
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source)}))
            metadata = model_metadata('catalog-trellis-image-large', config_path=config, service_paths={})
            self.assertEqual(metadata['manifest_state'], 'read')
            self.assertEqual(metadata['declared_files'][0]['hash_origin'], 'local_manifest')
            self.assertEqual(metadata['declared_sources'][0]['revision'], 'rev')

    def test_hermes_ready_record_is_labeled_as_local_declaration(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'local'
            model = source / 'models/hermes-coding'
            model.mkdir(parents=True)
            (model / 'ready.sha256').write_text(json.dumps({'sha256': 'a' * 64, 'size': 12, 'mtime_ns': 123}))
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source)}))
            metadata = model_metadata('catalog-hermes-coding', config_path=config, service_paths={})
            self.assertEqual(metadata['manifest_state'], 'ready_record')
            self.assertEqual(metadata['declared_files'][0]['hash_origin'], 'local_ready_record')
            self.assertEqual(metadata['declared_sources'], [])
            (model / 'ready.sha256').write_text('{}')
            self.assertEqual(model_metadata('catalog-hermes-coding', config_path=config, service_paths={})['manifest_state'], 'unavailable')

    def test_audio_prepared_record_is_a_declaration_not_verification(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'local'
            model = source / 'models/audio/heartmula'
            model.mkdir(parents=True)
            (model / 'prepared.json').write_text(json.dumps({
                'sources': [['example/model', 'revision', 'bundle']],
                'files': [{'path': 'bundle/weight', 'sha256': 'a' * 64},
                          {'path': '../outside', 'sha256': 'b' * 64}]}))
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source)}))
            metadata = model_metadata('catalog-heartmula', config_path=config, service_paths={})
            self.assertEqual(metadata['manifest_state'], 'prepared_record')
            self.assertEqual(metadata['declared_sources'], [{'repository': 'example/model', 'revision': 'revision'}])
            self.assertEqual(len(metadata['declared_files']), 1)
            self.assertEqual(metadata['declared_files'][0]['hash_origin'], 'local_preparation_record')
            self.assertFalse((model / 'bundle/weight').exists())
