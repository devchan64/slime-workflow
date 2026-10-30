"""명시한 DB export를 에셋 사본에 출력하고 실제 카탈로그 생성기를 검증한다."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from tools.review.domains.map_assets.database_ledger import publish_content_asset_ledger
from tools.review.maintenance.sync_billboard_catalog import load_unique_yaml_document, load_billboard_catalog


@unittest.skipUnless(os.environ.get('ASSET_LEDGER_EXPORT_FILE'), '격리 DB export 자료가 필요합니다.')
class AssetLedgerRoundtripTests(unittest.TestCase):
    def test_real_catalog_publication_and_repeat(current_test_case):
        current_source_root=Path(os.environ['ASSET_LEDGER_SOURCE_ROOT']).resolve()
        current_export_payload=json.loads(Path(os.environ['ASSET_LEDGER_EXPORT_FILE']).read_text())
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_asset_root=Path(current_directory_name)/'slime-assets'
            current_asset_root.mkdir()
            shutil.copy2(current_source_root/'asset-registry.yaml',current_asset_root/'asset-registry.yaml')
            for current_relative_path in ('assets/maps','assets/billboards','assets/sprites/effects'):
                shutil.copytree(current_source_root/current_relative_path,current_asset_root/current_relative_path)
            current_first_result=publish_content_asset_ledger(current_asset_root,current_export_payload)
            current_test_case.assertFalse(current_first_result['consumerLocksUpdated'])
            current_test_case.assertEqual(publish_content_asset_ledger(current_asset_root,current_export_payload)['updatedFiles'],0)
            current_changed_payload=copy.deepcopy(current_export_payload)
            current_selected_asset=current_changed_payload['assets'][0]
            current_selected_asset['properties']['anchorY']+=0.125
            current_changed_payload['generation']+=1
            current_changed_result=publish_content_asset_ledger(current_asset_root,current_changed_payload)
            current_test_case.assertGreater(current_changed_result['updatedFiles'],0)
            current_property_document=load_unique_yaml_document(current_asset_root/'assets/maps/sprite-display-properties.yaml')
            current_test_case.assertEqual(current_property_document['data'][current_selected_asset['assetId']]['anchorY'],current_selected_asset['properties']['anchorY'])
            for current_file_record in current_changed_result['changedFiles']:
                current_file_path=current_asset_root/current_file_record['path']
                current_test_case.assertEqual(hashlib.sha256(current_file_path.read_bytes()).hexdigest(),current_file_record['afterSha256'])
            current_catalog_record=load_billboard_catalog(current_asset_root)
            current_test_case.assertEqual(len(current_catalog_record['billboards']),len(current_export_payload['assets']))
            current_test_case.assertEqual(publish_content_asset_ledger(current_asset_root,current_changed_payload)['updatedFiles'],0)

            current_previous_image=copy.deepcopy(current_selected_asset['image'])
            current_previous_bytes=(current_asset_root/current_previous_image['path']).read_bytes()
            current_replacement_image=current_changed_payload['assets'][1]['image']
            current_replacement_bytes=(current_asset_root/current_replacement_image['path']).read_bytes()
            current_version_path='assets/billboards/versions/'+current_replacement_image['sha256']+'.png'
            (current_asset_root/current_version_path).parent.mkdir(parents=True,exist_ok=True)
            (current_asset_root/current_version_path).write_bytes(current_replacement_bytes)
            current_selected_asset['image']={**current_previous_image,
                'path':current_version_path,'version':'source-sha256-'+current_replacement_image['sha256'],
                'sha256':current_replacement_image['sha256'],'width':current_replacement_image['width'],
                'height':current_replacement_image['height'],'publishedPath':'/assets/'+current_version_path}
            current_changed_payload['generation']+=1
            publish_content_asset_ledger(current_asset_root,current_changed_payload)
            current_test_case.assertEqual((current_asset_root/current_previous_image['path']).read_bytes(),current_previous_bytes)
            current_image_versions=[current_registry_record for current_registry_record in load_unique_yaml_document(current_asset_root/'asset-registry.yaml')['assets']
                if current_registry_record['managementId']==current_previous_image['imageId']]
            current_test_case.assertIn(current_previous_image['version'],{current_registry_record['version'] for current_registry_record in current_image_versions})
            current_test_case.assertIn(current_selected_asset['image']['version'],{current_registry_record['version'] for current_registry_record in current_image_versions})
            current_test_case.assertEqual(publish_content_asset_ledger(current_asset_root,current_changed_payload)['updatedFiles'],0)
            current_retired_payload=copy.deepcopy(current_changed_payload)
            current_retired_asset=current_retired_payload['assets'][0]
            current_retired_asset['retired']=True
            current_retired_payload['generation']+=1
            for current_map_document in current_retired_payload['mapDocuments'].values():
                if 'objects' in current_map_document['data']:
                    current_map_document['data']['objects']=[current_object_record for current_object_record in current_map_document['data']['objects']
                        if current_object_record.get('textureKey')!=current_retired_asset['assetId']]
            current_original_image=current_asset_root/current_retired_asset['image']['path']
            current_original_hash=hashlib.sha256(current_original_image.read_bytes()).hexdigest()
            publish_content_asset_ledger(current_asset_root,current_retired_payload)
            current_test_case.assertNotIn(current_retired_asset['assetId'],
                {current_catalog_asset['texture_key'] for current_catalog_asset in load_billboard_catalog(current_asset_root)['billboards']})
            current_test_case.assertNotIn(current_retired_asset['assetId'],load_unique_yaml_document(current_asset_root/'assets/maps/sprite-display-properties.yaml')['data'])
            current_test_case.assertEqual(hashlib.sha256(current_original_image.read_bytes()).hexdigest(),current_original_hash)
            current_registry_records=load_unique_yaml_document(current_asset_root/'asset-registry.yaml')['assets']
            current_test_case.assertEqual(next(current_registry_record for current_registry_record in current_registry_records
                if current_registry_record['path']==current_retired_asset['image']['path'])['source']['lifecycle_status'],'retired')
            current_test_case.assertEqual(publish_content_asset_ledger(current_asset_root,current_retired_payload)['updatedFiles'],0)
