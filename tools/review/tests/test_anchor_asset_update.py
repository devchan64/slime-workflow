"""등록 좌표 저장의 원본·해시 동기화와 충돌 거절을 검증한다."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml
from tools.review.domains.character_animation import anchor_history, anchor_assets

class RegisteredAnchorSaveTests(unittest.TestCase):
    def test_save_updates_asset_lock_and_rejects_stale_source(self):
        with tempfile.TemporaryDirectory() as current_temporary_root:
            current_workspace_path=Path(current_temporary_root)
            current_asset_root=current_workspace_path/'slime-assets'
            current_animation_root=current_asset_root/'assets/characters/default/animations/idle'
            current_animation_root.mkdir(parents=True)
            current_frontend_root=current_workspace_path/'slime-frontend'
            current_frontend_root.mkdir()
            current_image_path=current_animation_root/'sheet.png'
            current_image_path.write_bytes(b'image-fixture')
            current_frame_record={'frameId':'down_left.0','rect':{'x':0,'y':0,'width':100,'height':100},'anchor':{'x':50,'y':90}}
            current_metadata_path=current_animation_root/'idle.animation.json'
            current_metadata_path.write_text(json.dumps({'animationId':'test.idle','version':'v1','frames':[current_frame_record],'clips':[{'direction':'down_left'}]}))
            current_asset_records=[]
            for current_index_value,current_file_path in enumerate((current_image_path,current_metadata_path)):
                current_asset_records.append({'managementId':str(current_index_value),'version':'v1','path':str(current_file_path.relative_to(current_asset_root)),'sha256':hashlib.sha256(current_file_path.read_bytes()).hexdigest(),'source':{}})
            current_registry_path=current_asset_root/'asset-registry.yaml'
            current_registry_path.write_text(yaml.safe_dump({'schema_version':1,'assets':current_asset_records}))
            current_lock_path=current_frontend_root/'sprite-assets.lock.yaml'
            current_lock_path.write_text(yaml.safe_dump({'files':[{'source_path':current_asset_record['path'],'sha256':current_asset_record['sha256']} for current_asset_record in current_asset_records]}))
            current_document_record={'schemaVersion':1,'artifactType':'character-animation-anchor-review','description':'등록 좌표','coordinateMode':'anchor','source':{'animationId':'test.idle','animationVersion':'v1','sheets':[{'image':'sheet.png','sha256':current_asset_records[0]['sha256']}]},'frames':[{**copy.deepcopy(current_frame_record),'image':'sheet.png','direction':'down_left','points':[{'x':51,'y':80}],'anchor':{'x':51,'y':80}}]}
            with patch.dict('os.environ',{'SLIME_ASSETS_ROOT':str(current_asset_root)}),patch.object(anchor_history,'ANCHOR_HISTORY_ROOT',current_workspace_path/'history'),patch.object(anchor_assets,'publish_registered_anchor_review') as current_publish_mock:
                current_saved_result=anchor_history.execute_anchor_history_command('anchor-save',{'document':current_document_record,'apply_registered':True})
                current_updated_metadata=json.loads(current_metadata_path.read_text())
                self.assertEqual(current_updated_metadata['frames'][0]['anchor'],{'x':51,'y':80})
                self.assertEqual(current_updated_metadata['clips'],[{'direction':'down_left'}])
                self.assertEqual(current_updated_metadata['version'],current_saved_result['assetUpdate']['version'])
                current_updated_digest=hashlib.sha256(current_metadata_path.read_bytes()).hexdigest()
                self.assertEqual(yaml.safe_load(current_registry_path.read_text())['assets'][1]['sha256'],current_updated_digest)
                self.assertEqual(yaml.safe_load(current_lock_path.read_text())['files'][1]['sha256'],current_updated_digest)
                current_publish_mock.assert_called_once()
                self.assertFalse((current_workspace_path/'history').exists())
                current_saved_bytes=current_metadata_path.read_bytes()
                with self.assertRaisesRegex(ValueError,'버전이 변경'):
                    anchor_history.execute_anchor_history_command('anchor-save',{'document':current_document_record,'apply_registered':True})
                self.assertEqual(current_metadata_path.read_bytes(),current_saved_bytes)
                current_document_record['source']['animationVersion']=current_updated_metadata['version']
                current_document_record['source']['sheets'][0]['sha256']='0'*64
                with self.assertRaisesRegex(ValueError,'원본 시트'):
                    anchor_history.execute_anchor_history_command('anchor-save',{'document':current_document_record,'apply_registered':True})
                self.assertEqual(current_metadata_path.read_bytes(),current_saved_bytes)
