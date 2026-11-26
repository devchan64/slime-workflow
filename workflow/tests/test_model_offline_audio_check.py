import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workflow.common.model_backup_sync import sync_snapshot
from workflow.common.model_offline_audio_check import check_restored_audio


class OfflineAudioCheckTests(unittest.TestCase):
    def test_reads_backup_contents_once_and_rejects_change_during_local_scan(self):
        from workflow.common import model_backup_service as service
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root/'source', root/'backup'
            (source/'first').mkdir(parents=True)
            backup.mkdir()
            (source/'first'/'weights').write_bytes(b'good weights')
            sync_snapshot('first', 'a'*32, roots=(source, backup, None))
            config = root/'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            original = service.inventory_model_tree
            calls = []
            def observe(path, **kwargs):
                calls.append((Path(path), kwargs.get('hash_content', False)))
                return original(path, **kwargs)
            with patch.dict('workflow.common.model_offline_audio_check.COMPONENTS', {'test': ('first',)}), \
                 patch.object(service, 'inventory_model_tree', side_effect=observe):
                self.assertTrue(check_restored_audio('test', config)['matches'])
            backup_reads = [hash_content for path, hash_content in calls if path.is_relative_to(backup)]
            self.assertEqual(backup_reads, [True, False])
            def change_snapshot(path, **kwargs):
                result = original(path, **kwargs)
                if Path(path) == source/'first':
                    (backup/'.model-backup-snapshots'/'first'/('a'*32)/'weights').write_bytes(b'bad weights!')
                return result
            with patch.dict('workflow.common.model_offline_audio_check.COMPONENTS', {'test': ('first',)}), \
                 patch.object(service, 'inventory_model_tree', side_effect=change_snapshot):
                result = check_restored_audio('test', config)
            self.assertFalse(result['matches'])
            self.assertIn('변경', result['components'][0]['error'])

    def test_rejects_latest_snapshot_change_during_comparison(self):
        from workflow.common import model_backup_service as service
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root/'source', root/'backup'
            (source/'first').mkdir(parents=True)
            backup.mkdir()
            (source/'first'/'weights').write_bytes(b'good weights')
            sync_snapshot('first', 'a'*32, roots=(source, backup, None))
            config = root/'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            parent = backup/'.model-backup-snapshots'/'first'
            with patch.dict('workflow.common.model_offline_audio_check.COMPONENTS', {'test': ('first',)}), \
                 patch.object(service, 'latest_model_snapshot', side_effect=[parent/('a'*32), parent/('b'*32)]):
                result = check_restored_audio('test', config)
            self.assertFalse(result['matches'])
            self.assertIn('최신 스냅샷', result['components'][0]['error'])

    def test_rejects_manifest_change_during_local_comparison(self):
        from workflow.common import model_backup_service as service
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root/'source', root/'backup'
            (source/'first').mkdir(parents=True)
            backup.mkdir()
            (source/'first'/'weights').write_bytes(b'good weights')
            sync_snapshot('first', 'a'*32, roots=(source, backup, None))
            config = root/'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            manifest = backup/'.model-backup-snapshots'/'first'/('a'*32)/'.snapshot.json'
            original = service.inventory_model_tree
            def change_manifest(path, **kwargs):
                result = original(path, **kwargs)
                if Path(path) == source/'first':
                    manifest.write_text(manifest.read_text() + ' ')
                return result
            with patch.dict('workflow.common.model_offline_audio_check.COMPONENTS', {'test': ('first',)}), \
                 patch.object(service, 'inventory_model_tree', side_effect=change_manifest):
                result = check_restored_audio('test', config)
            self.assertFalse(result['matches'])
            self.assertIn('변경', result['components'][0]['error'])

    def test_detects_local_and_backup_damage_and_partial_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source, backup = root/'source', root/'backup'
            backup.mkdir()
            for name in ('first', 'second'):
                model = source/name
                model.mkdir(parents=True)
                (model/'weights').write_bytes(b'good weights')
                sync_snapshot(name, 'a'*32, roots=(source, backup, None))
            config = root/'config.json'
            config.write_text(json.dumps({'source_path': str(source), 'local_mount_path': str(backup)}))
            with patch.dict('workflow.common.model_offline_audio_check.COMPONENTS', {'test': ('first', 'second')}):
                progress = []
                self.assertTrue(check_restored_audio('test', config, progress=lambda *event: progress.append(event))['matches'])
                self.assertEqual({event[0] for event in progress}, {'first', 'second'})
                self.assertIn('스냅샷 해시 확인', {event[1] for event in progress})
                self.assertIn('원본 해시 확인', {event[1] for event in progress})
                (source/'first'/'weights').write_bytes(b'bad weights!')
                result = check_restored_audio('test', config)
                self.assertFalse(result['matches'])
                self.assertFalse(result['components'][0]['matches'])
                self.assertEqual(result['components'][0]['differences'], [{'stage': 'local', 'path': 'weights', 'status': 'different'}])
                (source/'first'/'weights').write_bytes(b'good weights')
                (backup/'.model-backup-snapshots'/'second'/('a'*32)/'weights').write_bytes(b'bad weights!')
                self.assertFalse(check_restored_audio('test', config)['matches'])
                (backup/'.model-backup-snapshots'/'second'/('a'*32)/'weights').write_bytes(b'good weights')
                (source/'first'/'download.partial').write_bytes(b'partial')
                self.assertFalse(check_restored_audio('test', config)['matches'])

    def test_unavailable_component_is_not_success(self):
        with patch.dict('workflow.common.model_offline_audio_check.COMPONENTS', {'test': ('missing',)}), \
             patch('workflow.common.model_offline_audio_check.verify_snapshot_manifest', side_effect=ValueError('missing')):
            result = check_restored_audio('test')
        self.assertFalse(result['matches'])
        self.assertIsNone(result['components'][0]['matches'])

    def test_different_snapshot_ids_cannot_be_reported_as_matching(self):
        item = {'path': 'weights', 'status': 'verified'}
        snapshot = {'snapshot_id': 'a'*32, 'complete': True, 'files': [item]}
        local = {'snapshot_id': 'b'*32, 'complete': True, 'files': [item]}
        snapshot['local_comparison'] = local
        with patch.dict('workflow.common.model_offline_audio_check.COMPONENTS', {'test': ('model',)}), \
             patch('workflow.common.model_offline_audio_check.verify_snapshot_manifest', return_value=snapshot):
            result = check_restored_audio('test')
        self.assertFalse(result['matches'])
        self.assertFalse(result['components'][0]['same_snapshot'])
        self.assertEqual(result['components'][0]['local_comparison_snapshot_id'], 'b'*32)

    def test_matching_snapshot_without_a_required_file_is_not_success(self):
        item = {'path': 'weights', 'status': 'verified'}
        comparison = {'snapshot_id': 'a'*32, 'complete': True, 'files': [item]}
        snapshot = {**comparison, 'local_comparison': comparison}
        with patch.dict('workflow.common.model_offline_audio_check.COMPONENTS', {'test': ('model',)}), \
             patch.dict('workflow.common.model_offline_audio_check.REQUIRED', {'test': {'model': ('config.json',)}}), \
             patch('workflow.common.model_offline_audio_check.verify_snapshot_manifest', return_value=snapshot):
            result = check_restored_audio('test')
        self.assertFalse(result['matches'])
        self.assertEqual(result['components'][0]['missing_required'], ['config.json'])

    def test_matching_empty_required_file_is_not_success(self):
        item = {'path': 'config.json', 'status': 'verified', 'source': {'size': 0}}
        comparison = {'snapshot_id': 'a'*32, 'complete': True, 'files': [item]}
        snapshot = {**comparison, 'local_comparison': comparison}
        with patch.dict('workflow.common.model_offline_audio_check.COMPONENTS', {'test': ('model',)}), \
             patch.dict('workflow.common.model_offline_audio_check.REQUIRED', {'test': {'model': ('config.json',)}}), \
             patch('workflow.common.model_offline_audio_check.verify_snapshot_manifest', return_value=snapshot):
            result = check_restored_audio('test')
        self.assertFalse(result['matches'])
        self.assertEqual(result['components'][0]['missing_required'], ['config.json'])
