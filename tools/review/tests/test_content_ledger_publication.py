"""개발 DB 원장 반영의 저장소 경계·해시·공개 전달 계약."""
from contextlib import ExitStack
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml

from tools.review.domains.map_assets.database_ledger import publish_content_asset_ledger


class ContentLedgerPublicationTests(unittest.TestCase):
    def setUp(current_test_case):
        current_test_case.current_resource_stack=ExitStack()
        current_test_case.addCleanup(current_test_case.current_resource_stack.close)
        current_directory_name=current_test_case.current_resource_stack.enter_context(tempfile.TemporaryDirectory())
        current_test_case.current_asset_root=Path(current_directory_name)/'slime-assets'
        current_test_case.current_asset_root.mkdir()
        (current_test_case.current_asset_root/'assets/billboards').mkdir(parents=True)
        current_source_documents={
            'assets/maps/sprite-display-properties.yaml':{'managementId':'properties','data':{'house':{'anchorX':0,'anchorY':0}}},
            'assets/maps/map_spawns/index.yaml':{'managementId':'starts','data':{'version':1,'maps':{}}},
        }
        current_registry_entries=[]
        for current_relative_name,current_document_record in current_source_documents.items():
            current_document_path=current_test_case.current_asset_root/current_relative_name
            current_document_path.parent.mkdir(parents=True,exist_ok=True)
            current_document_bytes=yaml.safe_dump(current_document_record).encode()
            current_document_path.write_bytes(current_document_bytes)
            current_registry_entries.append({'path':current_relative_name,'sha256':hashlib.sha256(current_document_bytes).hexdigest()})
        (current_test_case.current_asset_root/'asset-registry.yaml').write_text(yaml.safe_dump({'assets':current_registry_entries}))
        current_test_case.current_backend_lock=current_test_case.current_asset_root.parent/'slime-backend/map-data.lock.yaml'
        current_test_case.current_backend_lock.parent.mkdir()
        current_test_case.current_backend_lock.write_text(yaml.safe_dump({'schema_version':1,'repository':'slime-assets','files':current_registry_entries.copy()}))
        current_test_case.current_payload_record={
            'schemaVersion':1,'generation':2,'types':{},'assets':[],
            'mapDocuments':{'map_spawns/index.yaml':{'managementId':'starts','data':{'version':1,'maps':{'town':{'startPoint':{'column':1,'row':2},'safeRadius':1}}}}},
            'mapRevisions':{'map_spawns/index.yaml':2},
            'buildingProperties':{'house':{'anchorX':0.5,'anchorY':0}},'effects':[],
        }
        current_effect_path=current_test_case.current_asset_root/'assets/sprites/effects/catalog.yaml'
        current_effect_path.parent.mkdir(parents=True)
        current_effect_bytes=yaml.safe_dump({'schema_version':1,'category':'effects','name':'이펙트','effects':[]},allow_unicode=True,sort_keys=False).encode()
        current_effect_path.write_bytes(current_effect_bytes)
        current_registry_entries.append({'path':'assets/sprites/effects/catalog.yaml','sha256':hashlib.sha256(current_effect_bytes).hexdigest()})
        (current_test_case.current_asset_root/'asset-registry.yaml').write_text(yaml.safe_dump({'assets':current_registry_entries}))
        for current_helper_name,current_helper_result in (
            ('load_billboard_catalog',{'review_categories':{},'billboards':[],'families':{}}),
            ('write_billboard_catalog',None),('build_catalog_reference',{}),('list_billboard_catalog_paths',[])):
            current_test_case.current_resource_stack.enter_context(patch('tools.review.domains.map_assets.database_ledger.'+current_helper_name,return_value=current_helper_result))

    def test_publish_with_backend_lock_and_repeat(current_test_case):
        current_publish_result=publish_content_asset_ledger(current_test_case.current_asset_root,current_test_case.current_payload_record)
        current_test_case.assertTrue(current_publish_result['consumerLocksUpdated'])
        current_test_case.assertGreater(current_publish_result['updatedFiles'],0)
        for current_file_record in current_publish_result['changedFiles']:
            current_file_path=current_test_case.current_asset_root/current_file_record['path']
            current_test_case.assertEqual(hashlib.sha256(current_file_path.read_bytes()).hexdigest(),current_file_record['afterSha256'])
        current_repeat_result=publish_content_asset_ledger(current_test_case.current_asset_root,current_test_case.current_payload_record)
        current_test_case.assertEqual(current_repeat_result['updatedFiles'],0)
        current_lock_record=yaml.safe_load(current_test_case.current_backend_lock.read_text())
        for current_lock_entry in current_lock_record['files']:
            current_test_case.assertEqual(current_lock_entry['sha256'],hashlib.sha256((current_test_case.current_asset_root/current_lock_entry['path']).read_bytes()).hexdigest())

    def test_frontend_consumer_locks_unchanged(current_test_case):
        current_consumer_paths=[]
        for current_repository_name,current_lock_name in (('slime-frontend','map-assets.lock.yaml'),('slime-frontend','sprite-assets.lock.yaml')):
            current_lock_path=current_test_case.current_asset_root.parent/current_repository_name/current_lock_name
            current_lock_path.parent.mkdir(exist_ok=True)
            current_lock_path.write_text('소비자 배포 준비에서만 수정')
            current_consumer_paths.append(current_lock_path)
        publish_content_asset_ledger(current_test_case.current_asset_root,current_test_case.current_payload_record)
        for current_lock_path in current_consumer_paths:
            current_test_case.assertEqual(current_lock_path.read_text(),'소비자 배포 준비에서만 수정')

    def test_missing_or_stale_backend_lock_rejects_before_publication(current_test_case):
        current_original_registry=(current_test_case.current_asset_root/'asset-registry.yaml').read_bytes()
        current_original_map=(current_test_case.current_asset_root/'assets/maps/map_spawns/index.yaml').read_bytes()
        current_test_case.current_backend_lock.unlink()
        with current_test_case.assertRaisesRegex(ValueError,'잠금 목록'):
            publish_content_asset_ledger(current_test_case.current_asset_root,current_test_case.current_payload_record)
        current_test_case.current_backend_lock.write_text(yaml.safe_dump({'schema_version':1,'repository':'slime-assets','files':[{'path':'assets/maps/map_spawns/index.yaml','sha256':'0'*64}]}))
        with current_test_case.assertRaisesRegex(ValueError,'잠금 .*불일치'):
            publish_content_asset_ledger(current_test_case.current_asset_root,current_test_case.current_payload_record)
        current_test_case.assertEqual((current_test_case.current_asset_root/'asset-registry.yaml').read_bytes(),current_original_registry)
        current_test_case.assertEqual((current_test_case.current_asset_root/'assets/maps/map_spawns/index.yaml').read_bytes(),current_original_map)

    def test_write_failure_restores_originals_and_backend_lock(current_test_case):
        import os
        current_originals={current_path:current_path.read_bytes() for current_path in (
            current_test_case.current_asset_root/'asset-registry.yaml',current_test_case.current_asset_root/'assets/maps/map_spawns/index.yaml',
            current_test_case.current_asset_root/'assets/maps/sprite-display-properties.yaml',current_test_case.current_backend_lock)}
        current_replace=os.replace
        def fail_backend_replacement(current_source_path,current_target_path):
            if current_target_path==current_test_case.current_backend_lock:raise OSError('모의 잠금 기록 실패')
            return current_replace(current_source_path,current_target_path)
        with patch('tools.review.domains.map_assets.database_ledger.os.replace',side_effect=fail_backend_replacement):
            with current_test_case.assertRaises(OSError):publish_content_asset_ledger(current_test_case.current_asset_root,current_test_case.current_payload_record)
        for current_path,current_bytes in current_originals.items():current_test_case.assertEqual(current_path.read_bytes(),current_bytes)

    def test_rollback_preserves_external_change_after_partial_publication(current_test_case):
        import os
        current_property_path=current_test_case.current_asset_root/'assets/maps/sprite-display-properties.yaml'
        current_other_path=current_test_case.current_asset_root/'assets/maps/map_spawns/index.yaml'
        current_previous_other=current_other_path.read_bytes()
        current_previous_lock=current_test_case.current_backend_lock.read_bytes()
        current_replace=os.replace
        def fail_after_external_edit(current_source_path,current_target_path):
            if current_target_path==current_test_case.current_backend_lock:
                current_property_path.write_text('external edit preserved\n')
                raise OSError('모의 잠금 기록 실패')
            return current_replace(current_source_path,current_target_path)
        with patch('tools.review.domains.map_assets.database_ledger.os.replace',side_effect=fail_after_external_edit):
            with current_test_case.assertRaisesRegex(RuntimeError,'안전하게 복원하지 못했습니다'):
                publish_content_asset_ledger(current_test_case.current_asset_root,current_test_case.current_payload_record)
        current_test_case.assertEqual(current_property_path.read_text(),'external edit preserved\n')
        current_test_case.assertEqual(current_other_path.read_bytes(),current_previous_other)
        current_test_case.assertEqual(current_test_case.current_backend_lock.read_bytes(),current_previous_lock)
        current_test_case.assertFalse(list(current_test_case.current_backend_lock.parent.glob('.ledger-*.tmp')))

    def test_unchanged_payload_does_not_hide_stale_backend_lock(current_test_case):
        publish_content_asset_ledger(current_test_case.current_asset_root,current_test_case.current_payload_record)
        current_lock_record=yaml.safe_load(current_test_case.current_backend_lock.read_text())
        current_lock_record['files'][0]['sha256']='0'*64
        current_test_case.current_backend_lock.write_text(yaml.safe_dump(current_lock_record))
        with current_test_case.assertRaisesRegex(ValueError,'잠금 해시 불일치'):
            publish_content_asset_ledger(current_test_case.current_asset_root,current_test_case.current_payload_record)

    def test_unrelated_map_change_during_staging_aborts_without_overwriting(current_test_case):
        current_map_path=current_test_case.current_asset_root/'assets/maps/terrain/other.yaml'
        current_map_path.parent.mkdir(parents=True)
        current_map_path.write_text('data: {}\n')
        current_relative_name=current_map_path.relative_to(current_test_case.current_asset_root).as_posix()
        current_entry={'path':current_relative_name,'sha256':hashlib.sha256(current_map_path.read_bytes()).hexdigest()}
        current_registry_path=current_test_case.current_asset_root/'asset-registry.yaml'
        current_registry_record=yaml.safe_load(current_registry_path.read_text())
        current_registry_record['assets'].append(current_entry)
        current_registry_path.write_text(yaml.safe_dump(current_registry_record))
        current_lock_record=yaml.safe_load(current_test_case.current_backend_lock.read_text())
        current_lock_record['files'].append(current_entry)
        current_test_case.current_backend_lock.write_text(yaml.safe_dump(current_lock_record))
        current_previous_registry=current_registry_path.read_bytes()
        current_previous_lock=current_test_case.current_backend_lock.read_bytes()
        def mutate_during_staging(current_staging_root):
            current_map_path.write_text('data: {external: true}\n')
            return {}
        with patch('tools.review.domains.map_assets.database_ledger.build_catalog_reference',side_effect=mutate_during_staging):
            with current_test_case.assertRaisesRegex(ValueError,'준비 중 파일이 변경'):
                publish_content_asset_ledger(current_test_case.current_asset_root,current_test_case.current_payload_record)
        current_test_case.assertEqual(current_registry_path.read_bytes(),current_previous_registry)
        current_test_case.assertEqual(current_test_case.current_backend_lock.read_bytes(),current_previous_lock)
        current_test_case.assertIn('external',current_map_path.read_text())

    def test_unregistered_changes_rejected_before_write(current_test_case):
        current_property_path=current_test_case.current_asset_root/'assets/maps/sprite-display-properties.yaml'
        current_property_path.write_text(current_property_path.read_text()+'\n# 외부 수정\n')
        current_original_bytes=current_property_path.read_bytes()
        with current_test_case.assertRaisesRegex(ValueError,'해시 불일치'):
            publish_content_asset_ledger(current_test_case.current_asset_root,current_test_case.current_payload_record)
        current_test_case.assertEqual(current_property_path.read_bytes(),current_original_bytes)

    def test_monster_spawn_and_unknown_payload_rejected(current_test_case):
        for current_invalid_payload in (
            current_test_case.current_payload_record | {'monsterSpawns':{}},
            current_test_case.current_payload_record | {'mapDocuments':{'monster_spawns/index.yaml':{'managementId':'private','data':{}}},'mapRevisions':{'monster_spawns/index.yaml':1}},
            current_test_case.current_payload_record | {'mapRevisions':{}},
        ):
            with current_test_case.assertRaises(ValueError):
                publish_content_asset_ledger(current_test_case.current_asset_root,current_invalid_payload)

    def test_registration_symlink_rejected(current_test_case):
        current_registry_path=current_test_case.current_asset_root/'asset-registry.yaml'
        current_external_path=current_test_case.current_asset_root.parent/'external.yaml'
        current_external_path.write_bytes(current_registry_path.read_bytes())
        current_registry_path.unlink()
        current_registry_path.symlink_to(current_external_path)
        with current_test_case.assertRaisesRegex(ValueError,'경로 이탈'):
            publish_content_asset_ledger(current_test_case.current_asset_root,current_test_case.current_payload_record)

    def test_explicit_root_map_documents_allowed(current_test_case):
        from tools.review.domains.map_assets.database_ledger import validate_public_ledger_payload
        for current_document_name in ('world-map.yaml','battlefield_encounters.yaml'):
            current_payload_record=current_test_case.current_payload_record | {
                'mapDocuments':{current_document_name:{'managementId':'map.root','data':{}}},
                'mapRevisions':{current_document_name:1}}
            validate_public_ledger_payload(current_payload_record)
        for current_document_name in ('monster_spawns.yaml','unknown.yaml'):
            current_payload_record=current_test_case.current_payload_record | {
                'mapDocuments':{current_document_name:{'managementId':'map.root','data':{}}},
                'mapRevisions':{current_document_name:1}}
            with current_test_case.assertRaisesRegex(ValueError,'허용 경로'):
                validate_public_ledger_payload(current_payload_record)
