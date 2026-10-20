"""임시 저장소에서 폐기·취소·변경 감지·실패 원복을 검증한다."""
import hashlib
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml
from tools.review.domains.map_assets import retirement, editor


class BillboardRetirementTests(unittest.TestCase):
    def setUp(self):
        self.current_temp_directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.current_temp_directory.cleanup)
        self.current_asset_root=Path(self.current_temp_directory.name)/'slime-assets'
        self.current_catalog_document={'families':{'sample':{}},'billboards':[{'texture_key':'sample','family':'sample','source_file':{'path':'assets/billboards/sample.png'},'metadata_references':[]}]}
        current_property_document={'data':{'sample':{'anchorX':.5,'anchorY':1,'displayHeight':50,'groundFootprintColumns':1,'groundFootprintRows':1,'billboardBlocksMovement':False}}}
        self.write_test_document('assets/maps/sprite-display-properties.yaml',current_property_document)
        self.write_test_document('assets/maps/field_tiles/sample.yaml',{'data':{'objects':[{'textureKey':'sample','position':{'column':1,'row':1}}]}})
        self.write_test_document('assets/billboards/catalog.yaml',self.current_catalog_document)
        self.current_image_path=self.current_asset_root/'assets/billboards/sample.png'
        self.current_image_path.write_bytes(b'preserved-image')
        current_records=[]
        for current_relative_name in ['assets/maps/sprite-display-properties.yaml','assets/maps/field_tiles/sample.yaml','assets/billboards/sample.png']:
            current_records.append({'path':current_relative_name,'sha256':hashlib.sha256((self.current_asset_root/current_relative_name).read_bytes()).hexdigest(),'source':{}})
        self.write_test_document('asset-registry.yaml',{'assets':current_records})
        self.write_test_document('../slime-backend/map-data.lock.yaml',{'files':current_records[:2]})
        self.write_test_document('../slime-frontend/sprite-assets.lock.yaml',{'files':[current_records[2]]})
        self.write_test_document('../slime-frontend/src/game/terrain/scenery.asset-list.yaml',{'sample':'assets/billboards/sample.png'})
        self.current_editor_patch=patch.object(editor,'build_catalog_reference',side_effect=lambda current_asset_root:copy.deepcopy(self.current_catalog_document))
        self.current_editor_patch.start();self.addCleanup(self.current_editor_patch.stop)
        self.current_storage_patch=patch.object(retirement,'EDITOR_STORAGE_DIRECTORY',Path(self.current_temp_directory.name)/'receipts')
        self.current_storage_patch.start();self.addCleanup(self.current_storage_patch.stop)
        self.current_request_payload={'revision':editor.read_editor_snapshot(self.current_asset_root)[3],'texture':'sample'}

    def write_test_document(self,current_relative_name,current_document_value):
        current_file_path=self.current_asset_root/current_relative_name
        current_file_path.parent.mkdir(parents=True,exist_ok=True)
        current_file_path.write_text(yaml.safe_dump(current_document_value))

    def test_preview_preserves_and_confirm_retires(self):
        current_preview_result=retirement.preview_billboard_retirement(self.current_request_payload,self.current_asset_root)
        self.assertTrue(self.current_image_path.exists())
        self.assertEqual(current_preview_result['maps'][0]['removed'],1)
        with patch.object(retirement,'build_catalog_reference',return_value={'families':{},'billboards':[]}):
            retirement.execute_billboard_retirement({**self.current_request_payload,'token':current_preview_result['token']},self.current_asset_root)
        self.assertFalse(self.current_image_path.exists())
        self.assertEqual((self.current_asset_root/'assets/retired/billboards/sample.png').read_bytes(),b'preserved-image')
        self.assertEqual(yaml.safe_load((self.current_asset_root/'assets/maps/field_tiles/sample.yaml').read_text())['data']['objects'],[])

    def test_failed_sync_restores_originals(self):
        current_original_files={current_path:current_path.read_bytes() for current_path in Path(self.current_temp_directory.name).rglob('*') if current_path.is_file()}
        current_preview_result=retirement.preview_billboard_retirement(self.current_request_payload,self.current_asset_root)
        with patch.object(retirement,'build_catalog_reference',side_effect=ValueError('검증 실패')):
            with self.assertRaises(ValueError):retirement.execute_billboard_retirement({**self.current_request_payload,'token':current_preview_result['token']},self.current_asset_root)
        for current_file_path,current_file_bytes in current_original_files.items():self.assertEqual(current_file_path.read_bytes(),current_file_bytes)

    def test_changed_consumer_rejects_confirmation(self):
        current_preview_result=retirement.preview_billboard_retirement(self.current_request_payload,self.current_asset_root)
        current_consumer_path=self.current_asset_root.parent/'slime-frontend/sprite-assets.lock.yaml'
        current_consumer_path.write_text(current_consumer_path.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'원본이 변경'):retirement.execute_billboard_retirement({**self.current_request_payload,'token':current_preview_result['token']},self.current_asset_root)
        self.assertTrue(self.current_image_path.exists())
