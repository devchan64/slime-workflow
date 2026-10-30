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

    def test_publish_without_sibling_repositories_and_repeat(current_test_case):
        current_publish_result=publish_content_asset_ledger(current_test_case.current_asset_root,current_test_case.current_payload_record)
        current_test_case.assertFalse(current_publish_result['consumerLocksUpdated'])
        current_test_case.assertGreater(current_publish_result['updatedFiles'],0)
        for current_file_record in current_publish_result['changedFiles']:
            current_file_path=current_test_case.current_asset_root/current_file_record['path']
            current_test_case.assertEqual(hashlib.sha256(current_file_path.read_bytes()).hexdigest(),current_file_record['afterSha256'])
        current_repeat_result=publish_content_asset_ledger(current_test_case.current_asset_root,current_test_case.current_payload_record)
        current_test_case.assertEqual(current_repeat_result['updatedFiles'],0)

    def test_existing_consumer_locks_unchanged(current_test_case):
        current_consumer_paths=[]
        for current_repository_name,current_lock_name in (('slime-backend','map-data.lock.yaml'),('slime-frontend','map-assets.lock.yaml'),('slime-frontend','sprite-assets.lock.yaml')):
            current_lock_path=current_test_case.current_asset_root.parent/current_repository_name/current_lock_name
            current_lock_path.parent.mkdir(exist_ok=True)
            current_lock_path.write_text('소비자 배포 준비에서만 수정')
            current_consumer_paths.append(current_lock_path)
        publish_content_asset_ledger(current_test_case.current_asset_root,current_test_case.current_payload_record)
        for current_lock_path in current_consumer_paths:
            current_test_case.assertEqual(current_lock_path.read_text(),'소비자 배포 준비에서만 수정')

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
