"""에셋 편집 명령이 파일 대신 검증한 DB revision으로 저장되는지 확인한다."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.review.domains.map_assets import database_editor


class DatabaseAssetEditorTests(unittest.TestCase):
    def test_anchor_save_retries_request_without_reloading_changed_revision(self):
        current_property_values=dict(anchorX=0,anchorY=0,groundFootprintColumns=1,groundFootprintRows=1,
            displayHeight=128,billboardBlocksMovement=False,billboardAnchorMode='tile-intersection',
            shadowOffsetColumn=0,shadowOffsetRow=0,shadowScaleX=1,shadowScaleY=1,shadowCoordinateVersion=2,shadowSizeVersion=2)
        current_asset_record={'revision':3,'retired':False,'properties':current_property_values,
            'metadata':{'mapReferences':[{'path':'assets/maps/field_tiles/meadow.yaml'}]}}
        current_request_payload={'map':'meadow','kind':'field','texture':'grass-v1','anchorX':0,'anchorY':-0.2,
            'expected':current_property_values,'requestId':'anchor-test','expectedRevision':3}
        current_saved_requests=[]
        def execute_test_api_request(current_method,current_route,current_payload=None):
            if current_method=='GET':return current_asset_record
            current_saved_requests.append(current_payload)
            if len(current_saved_requests)==1:raise RuntimeError('응답 유실')
            return {'saved':True,'snapshot':'pending'}
        with TemporaryDirectory() as current_directory_name,patch.object(database_editor,'EDITOR_STORAGE_DIRECTORY',Path(current_directory_name)),patch.object(database_editor,'execute_content_api_request',side_effect=execute_test_api_request):
            with self.assertRaisesRegex(RuntimeError,'응답 유실'):
                database_editor.save_database_sprite_anchor(current_request_payload)
            current_asset_record['revision']=4
            self.assertTrue(database_editor.save_database_sprite_anchor(current_request_payload)['saved'])
            self.assertEqual(current_saved_requests[0],current_saved_requests[1])
            with self.assertRaisesRegex(ValueError,'새로고침'):
                database_editor.save_database_sprite_anchor({**current_request_payload,'requestId':'new-attempt'})

    def test_preview_then_save_reuses_exact_database_request(self):
        current_property_values=dict(anchorX=0,anchorY=0,groundFootprintColumns=1,groundFootprintRows=1,
            displayHeight=128,billboardBlocksMovement=False,billboardAnchorMode='tile-intersection',
            shadowOffsetColumn=0,shadowOffsetRow=0,shadowScaleX=1,shadowScaleY=1,shadowCoordinateVersion=2,shadowSizeVersion=2)
        current_request_payload={'revision':json.dumps({'grass-v1':3}),'changes':[{'texture':'grass-v1','values':{'anchorY':-0.2}}]}
        with TemporaryDirectory() as current_directory_name, patch.object(database_editor,'EDITOR_STORAGE_DIRECTORY',Path(current_directory_name)), patch.object(database_editor,'execute_content_api_request') as current_api_mock:
            current_api_mock.return_value={'revision':3,'properties':current_property_values}
            current_preview_result=database_editor.preview_database_editor_changes(current_request_payload)
            current_api_mock.return_value={'saved':True,'snapshot':'pending'}
            current_save_payload={**current_request_payload,'token':current_preview_result['token']}
            database_editor.save_database_editor_changes(current_save_payload)
            current_first_request=current_api_mock.call_args
            database_editor.save_database_editor_changes(current_save_payload)
            self.assertEqual(current_first_request,current_api_mock.call_args)
            self.assertEqual(current_first_request.args[2]['changes'][0]['expectedRevision'],3)
            self.assertEqual(current_first_request.args[2]['changes'][0]['properties']['anchorY'],-0.2)

    def test_preview_rejects_changed_revision(self):
        with patch.object(database_editor,'execute_content_api_request',return_value={'revision':4}):
            with self.assertRaisesRegex(ValueError,'변경되었습니다'):
                database_editor.preview_database_editor_changes({'revision':json.dumps({'grass-v1':3}),
                    'changes':[{'texture':'grass-v1','values':{'anchorY':-0.2}}]})
