import tempfile
import unittest
import json
import fcntl
import hashlib
import os
import stat
import subprocess
import sys
from unittest.mock import patch
from pathlib import Path

from workflow.common.model_backup_inventory import compare_inventories, inventory_model_tree
from workflow.common.model_backup_service import compare_backup_model, list_backup_models, verify_snapshot_manifest
from workflow.common.model_backup_metadata import model_metadata
from workflow.common.model_backup_restore import restore_verified_backup, _default_file_mode
from workflow.common.model_backup_mount import verify_smb_mount
from workflow.common.model_backup_sync import sync_snapshot
from workflow.common.management_gateway import resolve_management_command
from workflow.common.model_backup_verification import read_verification, list_verifications, run_worker, start_backup_job


class ModelBackupInventoryTest(unittest.TestCase):
    def test_snapshot_records_that_internal_links_are_copied_as_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            model = source / 'model'
            model.mkdir(parents=True); backup.mkdir()
            (source / 'shared').mkdir()
            (source / 'shared' / 'weights').write_bytes(b'weights')
            (model / 'weights').symlink_to('../shared/weights')
            result = sync_snapshot('model', 'a' * 32, roots=(source, backup, None))
            snapshot = Path(result['path'])
            manifest = json.loads((snapshot / '.snapshot.json').read_text())
            self.assertEqual(manifest['link_policy'], 'follow_within_model_root_as_files')
            self.assertFalse((snapshot / 'weights').is_symlink())
            self.assertEqual((snapshot / 'weights').read_bytes(), b'weights')

    def test_hash_comparison_identifies_content_and_backup_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            source.mkdir()
            backup.mkdir()
            (source / 'same').write_bytes(b'model')
            (backup / 'same').write_bytes(b'model')
            (source / 'different').write_bytes(b'one')
            (backup / 'different').write_bytes(b'two')
            (source / 'missing').write_bytes(b'new')
            (backup / 'old').write_bytes(b'old')
            result = compare_inventories(inventory_model_tree(source, hash_content=True), inventory_model_tree(backup, hash_content=True))
            self.assertTrue(result['complete'])
            self.assertEqual({item['path']: item['status'] for item in result['files']},
                             {'different': 'different', 'missing': 'missing', 'old': 'backup_only', 'same': 'verified'})
            self.assertEqual(result['files'][-1]['source']['hash_origin'], 'observed')

    def test_external_and_cyclic_links_are_reported_and_make_comparison_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            source.mkdir()
            backup.mkdir()
            (source / 'external').symlink_to(root, target_is_directory=True)
            (source / 'cycle').symlink_to(source, target_is_directory=True)
            (backup / 'only').write_bytes(b'old')
            local = inventory_model_tree(source)
            result = compare_inventories(local, inventory_model_tree(backup))
            self.assertFalse(result['complete'])
            self.assertEqual(len(local['errors']), 2)
            self.assertEqual(result['files'][0]['status'], 'unknown')

    def test_metadata_match_is_not_content_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'file').write_bytes(b'data')
            inventory = inventory_model_tree(root)
            result = compare_inventories(inventory, inventory)
            self.assertEqual(result['files'][0]['status'], 'matches_metadata')

    def test_hash_inventory_reports_current_file_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'weight').write_bytes(b'weights')
            reports = []
            inventory_model_tree(root, hash_content=True, progress=lambda path, done, total: reports.append((path, done, total)))
            self.assertEqual(reports[-1], ('weight', 7, 7))

    def test_configured_service_compares_one_model_and_rejects_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            source.mkdir()
            backup.mkdir()
            (source / 'model').mkdir()
            (source / 'model' / 'weight').write_bytes(b'weights')
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            self.assertEqual(list_backup_models(config)['models'], [{'name': 'model', 'local_present': True, 'backup_present': False, 'snapshot_present': False}])
            result = compare_backup_model('model', config)
            self.assertEqual(result['files'][0]['status'], 'missing')
            for name in ('../backup', '.', 'model/weight'):
                with self.assertRaises(ValueError):
                    compare_backup_model(name, config)

    def test_backup_access_error_is_not_reported_as_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            (source / 'model').mkdir(parents=True)
            backup.mkdir()
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            original = Path.lstat
            def fail_backup(path, *args, **kwargs):
                if path == backup / 'model':
                    raise PermissionError('access denied')
                return original(path, *args, **kwargs)
            with patch.object(Path, 'lstat', fail_backup):
                with self.assertRaisesRegex(ValueError, '확인할 수 없습니다'):
                    compare_backup_model('model', config)

    def test_samba_config_rejects_unmounted_or_wrong_share(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mount = root / 'mount'
            target = mount / 'models'
            target.mkdir(parents=True)
            mounts = root / 'mountinfo'
            mounts.write_text(f'1 0 0:1 / {mount} rw - cifs //server/public rw\n')
            verify_smb_mount(target, 'smb://server/public/models', mountinfo_path=mounts)
            with self.assertRaisesRegex(ValueError, '일치하지 않습니다'):
                verify_smb_mount(target, 'smb://server/other/models', mountinfo_path=mounts)
            mounts.write_text(f'1 0 0:1 / {mount} rw - cifs //server/public/models rw\n')
            verify_smb_mount(mount, 'smb://server/public/models', mountinfo_path=mounts)
            mounts.write_text(f'1 0 0:1 / {root} rw - ext4 /dev/root rw\n')
            with self.assertRaisesRegex(ValueError, '마운트되어 있지 않습니다'):
                verify_smb_mount(target, 'smb://server/public/models', mountinfo_path=mounts)

    def test_disconnected_backup_still_lists_models_as_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            (source / 'model').mkdir(parents=True)
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(root / 'offline')}))
            result = list_backup_models(config)
            self.assertEqual(result['models'], [{'name': 'model', 'local_present': True, 'backup_present': None, 'snapshot_present': None}])
            self.assertTrue(result['backup_error'])
            with self.assertRaises(ValueError):
                compare_backup_model('model', config)

    def test_gateway_routes_and_rejects_extra_payload(self):
        self.assertEqual(resolve_management_command('model-downloads', 'backup-compare', {'model': 'model'}), ('POST', '/model-downloads/backup/compare'))
        with self.assertRaises(ValueError):
            resolve_management_command('model-downloads', 'backup-compare', {'model': 'model', 'path': '/tmp'})

    def test_metadata_normalizes_existing_manifest_without_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'models'
            model = source / 'sample'
            model.mkdir(parents=True)
            digest = 'a' * 64
            (model / 'manifest.json').write_text(json.dumps([
                {'repo': 'org/model', 'revision': 'fixed', 'path': '.model/sample/weight', 'sha256': digest},
                {'path': '../outside', 'sha256': digest},
                {'path': 'bad', 'sha256': 'invalid'},
            ]))
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(root / 'offline')}))
            result = model_metadata('sample', config_path=config, service_paths={'generator': [model]})
            self.assertEqual(result['services'], ['generator'])
            self.assertEqual(result['declared_sources'], [{'repository': 'org/model', 'revision': 'fixed'}])
            self.assertEqual(result['declared_files'], [{'path': 'weight', 'sha256': digest, 'hash_origin': 'local_manifest', 'repository': 'org/model', 'revision': 'fixed'}])

    def test_restore_stage_uses_final_model_backup_and_checks_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'models', root / 'backup'
            stage, final = source / '.model.preparing', source / 'model'
            stage.mkdir(parents=True)
            (backup / 'model').mkdir(parents=True)
            (backup / 'model' / 'weight').write_bytes(b'verified weights')
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            digest = hashlib.sha256(b'verified weights').hexdigest()
            with patch('workflow.common.model_backup_restore.CONFIG_PATH', config), patch('workflow.common.model_backup_restore._default_file_mode', return_value=0o600):
                self.assertTrue(restore_verified_backup(stage / 'weight', digest, backup_source_target=final / 'weight'))
                self.assertEqual((stage / 'weight').read_bytes(), b'verified weights')
                self.assertEqual(stat.S_IMODE((stage / 'weight').stat().st_mode), 0o600)
                self.assertFalse(restore_verified_backup(stage / 'other', digest, backup_source_target=root / 'outside'))

    def test_restore_mode_respects_restrictive_umask(self):
        code = 'from workflow.common.model_backup_restore import _default_file_mode; print(oct(_default_file_mode()))'
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                                check=True, preexec_fn=lambda: os.umask(0o077))
        self.assertEqual(result.stdout.strip(), '0o600')

    def test_curl_model_download_restores_verified_backup_before_network(self):
        from workflow.common import model_http_download
        from workflow.common.model_download_records import list_model_download_records, track_model_download
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            source.mkdir()
            (backup / 'kimodo').mkdir(parents=True)
            data = b'model weights'
            (backup / 'kimodo' / 'encoder.gguf').write_bytes(data)
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            target = source / 'kimodo' / 'encoder.gguf'
            with patch('workflow.common.model_backup_restore.CONFIG_PATH', config), \
                    patch.object(model_http_download, 'track_model_download', lambda name: track_model_download(name, root / 'records')), \
                    patch('subprocess.run') as curl:
                model_http_download.download_verified_curl('https://example.invalid/model', target,
                                                           hashlib.sha256(data).hexdigest(), len(data), 'kimodo-test')
            curl.assert_not_called()
            self.assertEqual(target.read_bytes(), data)
            self.assertEqual(list_model_download_records(root / 'records')[0]['stage'], '백업 SHA-256 검증 완료')

    def test_kimodo_pinned_asset_restores_before_network_and_rejects_bad_hash(self):
        from generators.kimodo import prepare
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            source.mkdir()
            (backup / 'kimodo' / 'motion').mkdir(parents=True)
            data = b'pinned weights'
            (backup / 'kimodo' / 'motion' / 'file.bin').write_bytes(data)
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            asset = {'role': 'motion', 'repository': 'example/model', 'revision': 'fixed'}
            file_record = {'path': 'file.bin', 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            with patch.object(prepare, 'KIMODO_MODEL_ROOT', source / 'kimodo'), patch('workflow.common.model_backup_restore.CONFIG_PATH', config):
                from unittest.mock import Mock
                download = Mock()
                restored = prepare.prepare_pinned_kimodo_file(asset, file_record, download)
                self.assertEqual(restored.read_bytes(), data)
                download.assert_not_called()
                file_record = {'path': 'other.bin', 'size': len(data), 'sha256': '0' * 64}
                (backup / 'kimodo' / 'motion' / 'other.bin').write_bytes(data)
                download.return_value = source / 'downloaded.bin'
                self.assertEqual(prepare.prepare_pinned_kimodo_file(asset, file_record, download), source / 'downloaded.bin')
                download.assert_called_once()

    def test_unreadable_process_status_uses_private_restore_mode(self):
        error = UnicodeDecodeError('ascii', b'\xff', 0, 1, 'invalid byte')
        with patch('builtins.open', side_effect=error):
            self.assertEqual(_default_file_mode(), 0o600)

    def test_sync_publishes_verified_snapshot_without_touching_existing_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            (source / 'model').mkdir(parents=True)
            (backup / 'model').mkdir(parents=True)
            (source / 'model' / 'weight').write_bytes(b'new model')
            (backup / 'model' / 'weight').write_bytes(b'old model')
            metadata = {'model': 'model', 'declared_sources': [{'repository': 'example/model', 'revision': 'v1'}]}
            result = sync_snapshot('model', 'a' * 32, roots=(source, backup, None), model_info=metadata)
            snapshot = Path(result['path'])
            self.assertEqual((snapshot / 'weight').read_bytes(), b'new model')
            self.assertEqual((backup / 'model' / 'weight').read_bytes(), b'old model')
            manifest = json.loads((snapshot / '.snapshot.json').read_text())
            self.assertEqual(manifest['files'][0]['sha256'], hashlib.sha256(b'new model').hexdigest())
            self.assertEqual(manifest['model_metadata'], metadata)
            self.assertEqual(result['verification'], 'sha256_after_copy')
            repeated = sync_snapshot('model', 'b' * 32, roots=(source, backup, None), model_info=metadata)
            self.assertTrue(repeated['reused'])
            self.assertEqual(repeated['snapshot_id'], 'a' * 32)
            self.assertEqual(repeated['bytes'], 0)
            self.assertFalse((snapshot.parent / ('b' * 32)).exists())
            stage = source / 'stage'
            stage.mkdir()
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            comparison = compare_backup_model('model', config, hash_content=True, target='latest_snapshot')
            self.assertEqual(comparison['snapshot_id'], 'a' * 32)
            self.assertEqual([(item['path'], item['status']) for item in comparison['files']], [('weight', 'verified')])
            with patch('workflow.common.model_backup_restore.CONFIG_PATH', config):
                self.assertTrue(restore_verified_backup(stage / 'weight', manifest['files'][0]['sha256'], backup_source_target=source / 'model' / 'weight'))
            self.assertEqual((stage / 'weight').read_bytes(), b'new model')

    def test_sync_creates_snapshot_when_content_or_metadata_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            (source / 'model').mkdir(parents=True)
            backup.mkdir()
            weight = source / 'model' / 'weight'
            weight.write_bytes(b'one')
            sync_snapshot('model', 'a' * 32, roots=(source, backup, None), model_info={'revision': '1'})
            weight.write_bytes(b'two')
            changed = sync_snapshot('model', 'b' * 32, roots=(source, backup, None), model_info={'revision': '1'})
            self.assertFalse(changed['reused'])
            self.assertEqual((Path(changed['path']) / 'weight').read_bytes(), b'two')
            changed_metadata = sync_snapshot('model', 'c' * 32, roots=(source, backup, None), model_info={'revision': '2'})
            self.assertFalse(changed_metadata['reused'])
            self.assertEqual(changed_metadata['snapshot_id'], 'c' * 32)

    def test_backup_only_model_remains_listed_with_snapshot_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            (source / 'model').mkdir(parents=True)
            backup.mkdir()
            (source / 'model' / 'weight').write_bytes(b'weights')
            metadata = {'model': 'model', 'manifest_state': 'read', 'services': ['generator'],
                        'declared_sources': [{'repository': 'org/model', 'revision': 'fixed'}], 'declared_files': []}
            sync_snapshot('model', 'a' * 32, roots=(source, backup, None), model_info=metadata)
            (source / 'model').rename(root / 'removed-local-model')
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            models = list_backup_models(config)['models']
            self.assertEqual(models, [{'name': 'model', 'local_present': False, 'backup_present': False, 'snapshot_present': True}])
            recovered_metadata = model_metadata('model', config_path=config, service_paths={})
            self.assertEqual(recovered_metadata['origin'], 'backup_snapshot')
            self.assertEqual(recovered_metadata['declared_sources'], metadata['declared_sources'])
            verified = verify_snapshot_manifest('model', config)
            self.assertEqual(verified['files'][0]['status'], 'verified')
            snapshot_file = backup / '.model-backup-snapshots' / 'model' / ('a' * 32) / 'weight'
            snapshot_file.write_bytes(b'altered')
            changed = verify_snapshot_manifest('model', config)
            self.assertEqual(changed['files'][0]['status'], 'different')

    def test_snapshot_integrity_rejects_manifest_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            (source / 'model').mkdir(parents=True)
            backup.mkdir()
            (source / 'model' / 'weight').write_bytes(b'weights')
            sync_snapshot('model', 'a' * 32, roots=(source, backup, None))
            manifest = backup / '.model-backup-snapshots' / 'model' / ('a' * 32) / '.snapshot.json'
            record = json.loads(manifest.read_text())
            record['files'][0]['path'] = '../outside'
            manifest.write_text(json.dumps(record))
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            with self.assertRaisesRegex(ValueError, '파일 목록'):
                verify_snapshot_manifest('model', config)

    def test_snapshot_integrity_rechecks_manifest_type_before_open(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            source.mkdir()
            snapshot = backup / 'snapshot'
            snapshot.mkdir(parents=True)
            outside = root / 'outside.json'
            outside.write_text('{}')
            (snapshot / '.snapshot.json').symlink_to(outside)
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            with patch('workflow.common.model_backup_service.latest_model_snapshot', return_value=snapshot):
                with self.assertRaisesRegex(ValueError, '매니페스트를 읽을 수 없습니다'):
                    verify_snapshot_manifest('model', config)

    def test_corrupt_completed_snapshot_blocks_latest_selection_and_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            (source / 'model').mkdir(parents=True)
            backup.mkdir()
            (source / 'model' / 'weight').write_bytes(b'model')
            sync_snapshot('model', 'a' * 32, roots=(source, backup, None))
            corrupt = backup / '.model-backup-snapshots' / 'model' / ('b' * 32)
            corrupt.mkdir()
            (corrupt / '.snapshot.json').write_text('{')
            config = root / 'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            with self.assertRaisesRegex(ValueError, '스냅샷을 확인할 수 없습니다'):
                compare_backup_model('model', config, target='latest_snapshot')
            with self.assertRaisesRegex(ValueError, '스냅샷을 확인할 수 없습니다'):
                sync_snapshot('model', 'c' * 32, roots=(source, backup, None))
            self.assertFalse((corrupt.parent / ('c' * 32)).exists())

    def test_sync_does_not_publish_when_source_is_unsafe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            (source / 'model').mkdir(parents=True)
            backup.mkdir()
            (source / 'model' / 'external').symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                sync_snapshot('model', 'b' * 32, roots=(source, backup, None))
            self.assertFalse((backup / '.model-backup-snapshots').exists())

    def test_sync_does_not_publish_if_file_is_added_during_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            (source / 'model').mkdir(parents=True)
            backup.mkdir()
            (source / 'model' / 'weight').write_bytes(b'model')

            def add_file(done, total, path):
                (source / 'model' / 'new').write_bytes(b'new')

            with self.assertRaisesRegex(ValueError, '파일 목록'):
                sync_snapshot('model', 'c' * 32, roots=(source, backup, None), progress=add_file)
            model_snapshots = backup / '.model-backup-snapshots' / 'model'
            self.assertFalse((model_snapshots / ('c' * 32)).exists())
            self.assertTrue((model_snapshots / ('.pending-' + 'c' * 32)).exists())

    def test_sync_detects_replaced_file_even_when_size_and_mtime_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root / 'source', root / 'backup'
            model = source / 'model'
            model.mkdir(parents=True)
            backup.mkdir()
            first = model / 'a'
            first.write_bytes(b'old')
            (model / 'b').write_bytes(b'next')
            before = first.stat()

            def replace_first(done, total, path):
                if path == 'b':
                    replacement = model / 'replacement'
                    replacement.write_bytes(b'new')
                    os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
                    os.replace(replacement, first)

            with self.assertRaisesRegex(ValueError, '파일 목록 또는 파일 상태'):
                sync_snapshot('model', 'd' * 32, roots=(source, backup, None), progress=replace_first)
            self.assertFalse((backup / '.model-backup-snapshots' / 'model' / ('d' * 32)).exists())

    def test_verification_records_completion_and_interrupted_job(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job_id = 'a' * 32
            lock_path = root / 'worker.lock'
            with lock_path.open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                os.set_inheritable(lock.fileno(), True)
                arguments = ['worker', '--model', 'm', '--job-id', job_id, '--state-root', str(root),
                             '--status-path', str(root / 'status.json'), '--lock-fd', str(os.dup(lock.fileno()))]
                with patch('sys.argv', arguments), patch('workflow.common.model_backup_verification.compare_backup_model', return_value={'complete': True, 'files': []}):
                    run_worker()
            self.assertEqual(read_verification(job_id, state_root=root)['status'], 'completed')
            self.assertEqual(list_verifications(state_root=root)[0]['job_id'], job_id)
            job_path = root / 'jobs' / (job_id + '.json')
            job_path.write_text(json.dumps({'job_id': job_id, 'status': 'running'}))
            (root / 'current.json').write_text(json.dumps({'job_id': job_id}))
            self.assertEqual(read_verification(job_id, state_root=root)['status'], 'interrupted')

    def test_sync_worker_records_progress_and_snapshot_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job_id = 'd' * 32
            def sync(model, requested_id, progress, model_info, phase):
                self.assertEqual((model, requested_id), ('sample', job_id))
                self.assertEqual(model_info, {'model': 'sample'})
                phase('원본 해시 확인', 'weight', 3, 5)
                progress(3, 5, 'weight')
                return {'snapshot_id': requested_id, 'file_count': 1, 'bytes': 5}
            with (root / 'worker.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                arguments = ['worker', '--model', 'sample', '--job-id', job_id, '--state-root', str(root),
                             '--status-path', str(root / 'status.json'), '--lock-fd', str(os.dup(lock.fileno())), '--operation', 'sync']
                with patch('sys.argv', arguments), patch('workflow.common.model_backup_sync.sync_snapshot', side_effect=sync), patch('workflow.common.model_backup_metadata.model_metadata', return_value={'model': 'sample'}):
                    run_worker()
            record = read_verification(job_id, state_root=root)
            self.assertEqual(record['status'], 'completed')
            self.assertEqual(record['operation'], 'sync')
            self.assertEqual(record['result']['snapshot_id'], job_id)
            self.assertEqual((record['bytes'], record['total_bytes']), (5, 5))
            job_path = root / 'jobs' / (job_id + '.json')
            old_record = json.loads(job_path.read_text())
            old_record['bytes'] = 3
            job_path.write_text(json.dumps(old_record))
            self.assertEqual(read_verification(job_id, state_root=root)['bytes'], 5)

    def test_retry_uses_same_job_and_rejects_changed_request(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_id = 'e' * 32
            with patch('workflow.common.model_backup_verification.subprocess.Popen') as popen:
                first = start_backup_job('sample', 'sync', request_id=request_id, state_root=root)
                retry = start_backup_job('sample', 'sync', request_id=request_id, state_root=root)
                self.assertEqual(first['job_id'], retry['job_id'])
                self.assertEqual(popen.call_count, 1)
                with self.assertRaises(ValueError):
                    start_backup_job('different', 'sync', request_id=request_id, state_root=root)


if __name__ == '__main__':
    unittest.main()
