"""검색 선택과 편집 원본 분리 및 교체 확인을 검증한다."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PIL import Image
from tools.review.ui.gradio import sprite_sheet_editor_app as editor


class SpriteEditorSourceFlowTests(unittest.TestCase):
    def test_registered_load_preserves_coordinates_and_cancel_candidate(self):
        with TemporaryDirectory() as current_temp_directory:
            current_image_path=Path(current_temp_directory)/'sheet.png'
            Image.new('RGB',(16,12),'white').save(current_image_path)
            import hashlib
            current_source_record={'source':'baseline','path':'rest.png','metadataSha256':None,
                'imageSha256':hashlib.sha256(current_image_path.read_bytes()).hexdigest(),
                'animation':{'frames':[{'rect':{'x':1,'y':2,'width':6,'height':8},'anchor':{'x':3,'y':7}}]}}
            with patch.object(editor,'select_sprite_asset_image',return_value=(str(current_image_path),current_source_record,'',1,1)):
                current_first_result=editor.prepare_registered_sprite_load('rest.png','baseline','')
                self.assertEqual(len(current_first_result),18)
                self.assertEqual(current_first_result[1],[[1,2,6,8,3,7]])
                self.assertEqual(current_first_result[13],current_source_record)
                current_pending_result=editor.prepare_registered_sprite_load('rest.png','baseline',current_first_result[0])
                self.assertEqual(len(current_pending_result),18)
                # 확인 전에는 좌표·현재 원본을 갱신하지 않는다. 취소는 후보만 폐기한다.
                self.assertEqual(current_pending_result[1],{'__type__':'update'})
                self.assertEqual(current_pending_result[13],{'__type__':'update'})
                with self.assertRaises(Exception):
                    editor.confirm_selected_sprite_load(current_pending_result[6],'other.png','baseline',None,4,2)
                current_confirmed_result=editor.confirm_selected_sprite_load(current_pending_result[6],'rest.png','baseline',None,4,2)
                self.assertEqual(current_confirmed_result[1],current_first_result[1])
                self.assertFalse(current_confirmed_result[-1])

    def test_uploaded_grid_does_not_inherit_registered_metadata(self):
        with TemporaryDirectory() as current_temp_directory:
            current_image_path=Path(current_temp_directory)/'sheet.png'
            Image.new('RGB',(16,12),'white').save(current_image_path)
            current_result_record=editor.prepare_uploaded_sprite_load(str(current_image_path),4,3,'')
            self.assertEqual(len(current_result_record[1]),12)
            self.assertEqual(current_result_record[13],{'source':'upload'})
            self.assertEqual(current_result_record[14],'')
            current_pending_record=editor.prepare_uploaded_sprite_load(str(current_image_path),4,2,current_result_record[0])[6]
            with self.assertRaises(Exception):
                editor.confirm_selected_sprite_load(current_pending_record,None,'assets',str(current_image_path),4,3)
            self.assertEqual(len(editor.confirm_selected_sprite_load(current_pending_record,None,'assets',str(current_image_path),4,2)[1]),8)

    def test_update_summary_counts_changes_and_rejects_changed_frame_count(self):
        current_source_record={'path':'rest.png','source':'baseline','metadataSha256':'hash','animation':{'frames':[{'rect':{'x':0,'y':0,'width':10,'height':20},'anchor':{'x':5,'y':19}}]}}
        current_payload_record={'image':'bytes','frames':[{'x':0,'y':0,'width':10,'height':20,'anchorX':6,'anchorY':19}],'columns':4}
        with patch.object(editor,'build_sprite_sheet_payload',return_value=current_payload_record):
            current_pending_record,_,current_summary_text=editor.prepare_sprite_sheet_update(current_source_record,'rest.png')
            self.assertIn('1 / 1프레임',current_summary_text)
            self.assertEqual(current_pending_record['source'],'baseline')
            current_payload_record['frames']=[]
            with self.assertRaises(Exception):editor.prepare_sprite_sheet_update(current_source_record,'rest.png')

    def test_successful_update_reloads_and_reload_failure_blocks_stale_save(self):
        current_source_record={'source':'baseline','path':'rest.png','metadataSha256':'old'}
        current_loaded_values=list(range(18))
        with patch.object(editor,'confirm_sprite_sheet_update',return_value=({}, {}, '완료 · 추가 편집 전 다시 불러오세요.')):
            with patch.object(editor,'prepare_registered_sprite_load',return_value=current_loaded_values) as current_reload_mock:
                current_result_values=editor.update_and_reload_sprite_sheet({},current_source_record,'rest.png')
                self.assertEqual(len(current_result_values),20)
                self.assertIn('계속 편집',current_result_values[4])
                current_reload_mock.assert_called_once_with('rest.png','baseline','')
            with patch.object(editor,'prepare_registered_sprite_load',side_effect=ValueError('읽기 실패')):
                current_result_values=editor.update_and_reload_sprite_sheet({},current_source_record,'rest.png')
                self.assertIsNone(current_result_values[13]['metadataSha256'])
                self.assertIn('재조회 실패',current_result_values[4])

    def test_anchor_history_restore_validates_source_and_pending_edit(self):
        current_frame_rect={'x':0,'y':0,'width':10,'height':20}
        current_source_record={'imageSha256':'a'*64,'animation':{'animationId':'test.rest','version':'v1','frames':[{'frameId':'down_left.0','rect':current_frame_rect}]}}
        current_history_document={'coordinateMode':'anchor','source':{'animationId':'test.rest','animationVersion':'v1','sheets':[{'image':'sheet.png','sha256':'a'*64}]},'frames':[{'frameId':'down_left.0','rect':current_frame_rect,'image':'sheet.png','anchor':{'x':5,'y':18}}]}
        current_frame_rows=[[0,0,10,20,4,17]]
        with patch.object(editor,'execute_remote_management_command',return_value={'document':current_history_document}) as current_gateway_mock:
            current_pending_record,_=editor.prepare_sprite_anchor_restore('history-id',current_source_record,current_frame_rows)
            current_gateway_mock.assert_called_once_with('character-animation','anchor-load',{'id':'history-id'})
            self.assertEqual(editor.confirm_sprite_anchor_restore(current_pending_record,current_source_record,current_frame_rows)[0],[[0,0,10,20,5,18]])
            for current_coordinate_mode in ('foot-centers','endpoints'):
                current_history_document['coordinateMode']=current_coordinate_mode
                current_history_document['frames'][0]['points']=[{'x':2,'y':17},{'x':6,'y':19}]* (2 if current_coordinate_mode=='endpoints' else 1)
                current_mode_pending,_=editor.prepare_sprite_anchor_restore('history-id',current_source_record,current_frame_rows)
                self.assertEqual(editor.confirm_sprite_anchor_restore(current_mode_pending,current_source_record,current_frame_rows)[0],[[0,0,10,20,5,18]])
            with self.assertRaises(Exception):editor.confirm_sprite_anchor_restore(current_pending_record,current_source_record,[[0,0,10,20,3,17]])
            with self.assertRaises(Exception):editor.prepare_sprite_anchor_restore('history-id',{**current_source_record,'imageSha256':'b'*64},current_frame_rows)

    def test_anchor_save_uses_shared_history_without_asset_apply(self):
        from tools.review.domains.character_animation import anchor_history
        current_source_record={'path':'baseline/rest.png','imageSha256':'a'*64,'animation':{'animationId':'character.rest','version':'v1','frames':[{'frameId':'rest.0','direction':'down_left','rect':{'x':0,'y':0,'width':10,'height':20}}]}}
        def execute_isolated_history(current_service_name,current_command_name,current_payload_record):
            self.assertEqual(current_service_name,'character-animation')
            self.assertNotIn('apply_registered',current_payload_record)
            return anchor_history.execute_anchor_history_command(current_command_name,current_payload_record)
        with TemporaryDirectory() as current_temp_directory,patch.object(anchor_history,'ANCHOR_HISTORY_ROOT',Path(current_temp_directory)),patch.object(editor,'execute_remote_management_command',side_effect=execute_isolated_history):
            current_choices_update,current_status_text=editor.save_sprite_anchor_history(current_source_record,[[0,0,10,20,4.5,18]])
            self.assertEqual(len(current_choices_update['choices']),1)
            current_history_identifier=current_choices_update['choices'][0][0]
            current_pending_record,_=editor.prepare_sprite_anchor_restore(current_history_identifier,current_source_record,[[0,0,10,20,2,15]])
            self.assertEqual(current_pending_record['rows'],[[0,0,10,20,4.5,18]])
            with self.assertRaises(Exception):editor.save_sprite_anchor_history(current_source_record,[[1,0,10,20,4.5,18]])

    def test_linked_sheet_uses_registered_source_loader(self):
        from types import SimpleNamespace
        current_loaded_outputs=tuple(range(18))
        with patch.object(editor,'prepare_registered_sprite_load',return_value=current_loaded_outputs) as current_loader_mock:
            self.assertEqual(editor.load_linked_sprite_sheet(SimpleNamespace(query_params={'sprite_path':'rest.png','sprite_source':'baseline'})),current_loaded_outputs)
            current_loader_mock.assert_called_once_with('rest.png','baseline','')
            with self.assertRaises(Exception):editor.load_linked_sprite_sheet(SimpleNamespace(query_params={'sprite_path':'rest.png','sprite_source':'outside'}))
            self.assertEqual(len(editor.load_linked_sprite_sheet(SimpleNamespace(query_params={}))),18)

    def test_legacy_action_link_requires_exact_single_match(self):
        from types import SimpleNamespace
        current_request_value=SimpleNamespace(query_params={'action':'asset:character.rest'})
        current_search_record={'items':[{'path':'rest.png','animationIds':['character.rest']},{'path':'other.png','animationIds':['character.rest.extra']}]}
        with patch.object(editor,'execute_remote_management_command',return_value=current_search_record),patch.object(editor,'prepare_registered_sprite_load',return_value=tuple(range(18))) as current_loader_mock:
            editor.load_linked_sprite_sheet(current_request_value)
            current_loader_mock.assert_called_once_with('rest.png','assets','')
            current_search_record['items'].append({'path':'rest-second.png','animationIds':['character.rest']})
            with self.assertRaises(Exception):editor.load_linked_sprite_sheet(current_request_value)

    def test_asset_search_indexes_verified_animation_identifier(self):
        import json,hashlib
        from tools.review.domains.character_animation.sprite_sheet_editor import execute_sprite_asset_command
        with TemporaryDirectory() as current_temp_directory:
            current_root_path=Path(current_temp_directory)
            current_image_name='assets/characters/default/animations/rest/sheet.png'
            current_metadata_name='assets/characters/default/animations/rest/sheet.animation.json'
            current_metadata_path=current_root_path/current_metadata_name
            current_metadata_path.parent.mkdir(parents=True)
            current_metadata_path.write_text(json.dumps({'animationId':'character.rest'}))
            current_registry_records={current_image_name:{'source':{},'sha256':'a'*64,'managementId':'image.rest'},current_metadata_name:{'source':{},'sha256':hashlib.sha256(current_metadata_path.read_bytes()).hexdigest()}}
            with patch('tools.review.common.map_tile_assets.load_registered_tiles',return_value=(current_root_path,current_registry_records)):
                current_search_result=execute_sprite_asset_command('sheet-search',{'query':'character.rest'})
                self.assertEqual(current_search_result['items'][0]['animationIds'],['character.rest'])
                current_metadata_path.write_text('{}')
                with self.assertRaises(ValueError):execute_sprite_asset_command('sheet-search',{'query':'character.rest'})
