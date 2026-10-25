"""파일 스냅샷의 재시작·외부 수정·세대 역전 방지를 검증한다."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import yaml
from tools.review.domains.map_assets.database_snapshot import encode_content_snapshot_payload, publish_content_snapshot_bundle
from tools.review.domains.map_assets.database_restore import read_verified_snapshot_payload


class ContentSnapshotFileTests(unittest.TestCase):
    def build_snapshot_export(self,current_generation_number):
        current_payload_record={'schemaVersion':1,'generation':current_generation_number,
            'types':{'vegetation':'자연물'},'assets':[{'assetId':'grass-v1','assetType':'vegetation','properties':{'anchorY':-0.2}}],
            'mapDocuments':{'field_tiles/test.yaml':{'managementId':'test','data':{'rows':['gg']}}},
            'mapRevisions':{'field_tiles/test.yaml':3},'buildingProperties':{'house':{'anchorX':0,'anchorY':0}}}
        return {'payload':current_payload_record,'payloadHash':hashlib.sha256(encode_content_snapshot_payload(current_payload_record)).hexdigest()}

    def test_restart_reuses_completed_generation(self):
        with TemporaryDirectory() as current_directory_name:
            current_export_record=self.build_snapshot_export(1)
            current_manifest_hash=publish_content_snapshot_bundle(current_directory_name,current_export_record)
            self.assertEqual(publish_content_snapshot_bundle(current_directory_name,current_export_record),current_manifest_hash)
            publish_content_snapshot_bundle(current_directory_name,self.build_snapshot_export(2))
            with self.assertRaisesRegex(ValueError,'이전 세대'):
                publish_content_snapshot_bundle(current_directory_name,current_export_record)

    def test_manual_edit_preserved_and_reported(self):
        with TemporaryDirectory() as current_directory_name:
            current_snapshot_root=Path(current_directory_name)
            publish_content_snapshot_bundle(current_snapshot_root,self.build_snapshot_export(1))
            current_manifest_record=yaml.safe_load((current_snapshot_root/'current.yaml').read_text())
            current_changed_path=current_snapshot_root/current_manifest_record['files'][0]['path']
            current_changed_path.write_text('사용자가 편집한 내용')
            with self.assertRaisesRegex(ValueError,'외부에서 변경'):
                publish_content_snapshot_bundle(current_snapshot_root,self.build_snapshot_export(2))
            self.assertEqual(current_changed_path.read_text(),'사용자가 편집한 내용')
            self.assertEqual(yaml.safe_load((current_snapshot_root/'current.yaml').read_text())['generation'],1)

    def test_snapshot_read_recovers_exact_export_payload(self):
        with TemporaryDirectory() as current_directory_name:
            current_export_record=self.build_snapshot_export(5)
            current_export_record['payload']['types']['props']='소품'
            current_export_record['payload']['assets'].insert(0,{'assetId':'z-cart','assetType':'props','properties':{}})
            current_export_record['payload']['assets'].append({'assetId':'a-cart','assetType':'props','properties':{}})
            current_export_record['payloadHash']=hashlib.sha256(encode_content_snapshot_payload(current_export_record['payload'])).hexdigest()
            publish_content_snapshot_bundle(current_directory_name,current_export_record)
            self.assertEqual(read_verified_snapshot_payload(current_directory_name),current_export_record['payload'])

    def test_snapshot_read_rejects_removed_manifest_entry(self):
        with TemporaryDirectory() as current_directory_name:
            publish_content_snapshot_bundle(current_directory_name,self.build_snapshot_export(5))
            current_manifest_path=Path(current_directory_name)/'current.yaml'
            current_manifest_record=yaml.safe_load(current_manifest_path.read_text())
            current_manifest_record['files']=[current_file_record for current_file_record in current_manifest_record['files'] if '/maps/' not in current_file_record['path']]
            current_manifest_path.write_text(yaml.safe_dump(current_manifest_record))
            with self.assertRaisesRegex(ValueError,'전체 내용 해시'):
                read_verified_snapshot_payload(current_directory_name)

    def test_snapshot_read_rejects_generation_directory_symlink(self):
        with TemporaryDirectory() as current_directory_name:
            current_snapshot_root=Path(current_directory_name)
            publish_content_snapshot_bundle(current_snapshot_root,self.build_snapshot_export(5))
            current_generation_directory=next(current_snapshot_root.glob('generation-*'))
            current_saved_directory=current_snapshot_root/'renamed'
            current_generation_directory.rename(current_saved_directory)
            current_generation_directory.symlink_to(current_saved_directory,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'심볼릭'):
                read_verified_snapshot_payload(current_snapshot_root)

    def test_pointer_publish_failure_recovers_complete_bundle(self):
        from unittest.mock import patch
        with TemporaryDirectory() as current_directory_name:
            current_snapshot_root=Path(current_directory_name)
            current_previous_export=self.build_snapshot_export(1)
            current_pending_export=self.build_snapshot_export(2)
            publish_content_snapshot_bundle(current_snapshot_root,current_previous_export)
            with patch('tools.review.domains.map_assets.database_snapshot.os.replace',side_effect=OSError('게시 직전 디스크 오류')):
                with self.assertRaisesRegex(OSError,'디스크 오류'):
                    publish_content_snapshot_bundle(current_snapshot_root,current_pending_export)
            self.assertEqual(read_verified_snapshot_payload(current_snapshot_root),current_previous_export['payload'])
            self.assertEqual(len(list(current_snapshot_root.glob('generation-*'))),2)
            publish_content_snapshot_bundle(current_snapshot_root,current_pending_export)
            self.assertEqual(read_verified_snapshot_payload(current_snapshot_root),current_pending_export['payload'])
            self.assertEqual(len(list(current_snapshot_root.glob('generation-*'))),2)
