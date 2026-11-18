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
            current_api_mock.return_value={'revision':3,'properties':current_property_values,'metadata':{'mapReferences':[]}}
            current_preview_result=database_editor.preview_database_editor_changes(current_request_payload)
            self.assertIn('전체 게임 통행 검증은 보장하지 않습니다',current_preview_result['note'])
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

    def test_preview_rejects_empty_noop_and_automatic_placement_changes(self):
        current_property_values=dict(anchorX=0,anchorY=0,groundFootprintColumns=1,groundFootprintRows=1,
            displayHeight=128,billboardBlocksMovement=False,billboardAnchorMode='tile-intersection',
            shadowOffsetColumn=0,shadowOffsetRow=0,shadowScaleX=1,shadowScaleY=1,shadowCoordinateVersion=2,shadowSizeVersion=2)
        with TemporaryDirectory() as current_directory_name, patch.object(database_editor,'EDITOR_STORAGE_DIRECTORY',Path(current_directory_name)), patch.object(database_editor,'execute_content_api_request',return_value={'revision':3,'properties':current_property_values}):
            for current_invalid_values in ({}, {'anchorY':0}, {'billboardPlacementAnchor':'top'}):
                with self.subTest(values=current_invalid_values), self.assertRaises(ValueError):
                    database_editor.preview_database_editor_changes({'revision':json.dumps({'grass-v1':3}),
                        'changes':[{'texture':'grass-v1','values':current_invalid_values}]})
            self.assertEqual(list(Path(current_directory_name).iterdir()),[])

    def test_preview_rejects_non_mapping_change_and_missing_properties(self):
        with patch.object(database_editor,'execute_content_api_request',return_value={'revision':3,'properties':None}):
            for current_invalid_change in ('bad', {'texture':'grass-v1','values':{'anchorY':0}}):
                with self.subTest(change=current_invalid_change), self.assertRaises(ValueError):
                    database_editor.preview_database_editor_changes({'revision':json.dumps({'grass-v1':3}),'changes':[current_invalid_change]})

    def test_preview_reports_database_map_placement_warning(self):
        current_property_values=dict(anchorX=0,anchorY=0,groundFootprintColumns=1,groundFootprintRows=1,
            displayHeight=128,billboardBlocksMovement=False,billboardAnchorMode='tile-intersection',
            shadowOffsetColumn=0,shadowOffsetRow=0,shadowScaleX=1,shadowScaleY=1,shadowCoordinateVersion=2,shadowSizeVersion=2)
        current_asset_record={'revision':3,'properties':current_property_values,'metadata':{'mapReferences':[{'path':'assets/maps/field_tiles/meadow.yaml'}]}}
        current_map_objects=[{'id':'one','kind':'decoration','textureKey':'grass-v1','position':{'column':1,'row':1}},{'id':'two','kind':'decoration','textureKey':'grass-v1','position':{'column':2,'row':1}}]
        current_bundle_record={'documents':{'sprite-display-properties.yaml':{'data':{'grass-v1':current_property_values}},
            'field_tiles/meadow.yaml':{'data':{'objects':current_map_objects}},'terrain/maps/meadow.yaml':{'data':{'elevations':[[0]*5 for current_row_index in range(5)]}}}}
        def execute_test_api_request(current_method_name,current_route_path):
            return current_bundle_record if 'review-bundle' in current_route_path else current_asset_record
        with TemporaryDirectory() as current_directory_name, patch.object(database_editor,'EDITOR_STORAGE_DIRECTORY',Path(current_directory_name)), patch.object(database_editor,'execute_content_api_request',side_effect=execute_test_api_request):
            current_result_record=database_editor.preview_database_editor_changes({'revision':json.dumps({'grass-v1':3}),
                'changes':[{'texture':'grass-v1','values':{'groundFootprintColumns':2}}]})
            self.assertEqual(current_result_record['maps'],['assets/maps/field_tiles/meadow.yaml'])
            self.assertIn('점유 영역 충돌',current_result_record['map_warnings'][0]['message'])
            current_bundle_record['documents']['sprite-display-properties.yaml']['data']['grass-v1']={**current_property_values,'anchorY':1}
            with self.assertRaisesRegex(ValueError,'검수 중 변경'):
                database_editor.preview_database_editor_changes({'revision':json.dumps({'grass-v1':3}),
                    'changes':[{'texture':'grass-v1','values':{'groundFootprintColumns':2}}]})

    def test_preview_rejects_missing_or_invalid_map_references(self):
        for current_metadata_record in ({}, {'mapReferences':[{'path':'../../other.yaml'}]}):
            with self.subTest(metadata=current_metadata_record), self.assertRaises(ValueError):
                database_editor.inspect_database_billboard_maps([{'metadata':current_metadata_record}],[])

    def test_city_review_uses_zero_elevation_when_not_declared(self):
        current_property_values=dict(anchorX=0,anchorY=0,groundFootprintColumns=1,groundFootprintRows=1,
            displayHeight=128,billboardBlocksMovement=False,billboardAnchorMode='tile-intersection',
            shadowOffsetColumn=0,shadowOffsetRow=0,shadowScaleX=1,shadowScaleY=1,shadowCoordinateVersion=2,shadowSizeVersion=2)
        current_asset_records=[{'metadata':{'mapReferences':[{'path':'assets/maps/city_layouts/iseulon.yaml'}]}}]
        current_bundle_record={'documents':{'sprite-display-properties.yaml':{'data':{'grass-v1':current_property_values}},
            'city_layouts/iseulon.yaml':{'data':{'columns':4,'rows':4,'objects':[{'id':'one','kind':'decoration','textureKey':'grass-v1','position':{'column':1,'row':1}}]}}}}
        with patch.object(database_editor,'execute_content_api_request',return_value=current_bundle_record):
            current_map_paths,current_map_warnings=database_editor.inspect_database_billboard_maps(current_asset_records,
                [{'texture':'grass-v1','before':current_property_values,'after':{**current_property_values,'displayHeight':130}}])
        self.assertEqual(current_map_paths,['assets/maps/city_layouts/iseulon.yaml'])
        self.assertEqual(current_map_warnings,[])

    def test_preview_does_not_prepare_save_when_map_unavailable(self):
        current_property_values=dict(anchorX=0,anchorY=0,groundFootprintColumns=1,groundFootprintRows=1,
            displayHeight=128,billboardBlocksMovement=False,billboardAnchorMode='tile-intersection',
            shadowOffsetColumn=0,shadowOffsetRow=0,shadowScaleX=1,shadowScaleY=1,shadowCoordinateVersion=2,shadowSizeVersion=2)
        current_asset_record={'revision':3,'properties':current_property_values,'metadata':{'mapReferences':[{'path':'assets/maps/field_tiles/meadow.yaml'}]}}
        with TemporaryDirectory() as current_directory_name, patch.object(database_editor,'EDITOR_STORAGE_DIRECTORY',Path(current_directory_name)), patch.object(database_editor,'execute_content_api_request',side_effect=[current_asset_record,RuntimeError('맵 조회 실패')]):
            with self.assertRaisesRegex(RuntimeError,'맵 조회 실패'):
                database_editor.preview_database_editor_changes({'revision':json.dumps({'grass-v1':3}),
                    'changes':[{'texture':'grass-v1','values':{'anchorY':-0.2}}]})
            self.assertEqual(list(Path(current_directory_name).iterdir()),[])
