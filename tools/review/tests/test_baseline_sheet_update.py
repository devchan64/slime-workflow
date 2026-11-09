"""베이스라인 원본 저장과 오래된 입력 거절을 격리 검증한다."""
import base64
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import yaml
from PIL import Image
from tools.review.domains.character_animation import sprite_sheet_editor as editor


class BaselineSheetUpdateTests(unittest.TestCase):
    def test_gui_prepares_new_coordinates_for_baseline_without_map(self):
        from tools.review.ui.gradio.sprite_sheet_editor_app import load_sprite_sheet_input, prepare_sprite_sheet_update, select_sprite_asset_image
        from tools.review.common.management_gateway import execute_management_command
        with TemporaryDirectory() as current_temp_directory:
            current_root_path=Path(current_temp_directory)
            current_image_path=current_root_path/'sheet.png'
            Image.new('RGB',(16,8),'white').save(current_image_path)
            current_image_path.with_suffix('.yaml').write_text(yaml.safe_dump({'layout':{'columns':2,'rows':1,'frame_count':2}}))
            with patch.object(editor,'SPRITE_BASELINE_ROOT',current_root_path),patch.object(editor,'SPRITE_SHEET_JOB_ROOT',current_root_path/'jobs'),patch('tools.review.ui.gradio.sprite_sheet_editor_app.execute_remote_management_command',side_effect=execute_management_command):
                current_file_path,current_asset_record,_,current_columns_value,current_rows_value=select_sprite_asset_image('sheet.png','baseline')
                current_loaded_values=load_sprite_sheet_input(current_file_path,current_columns_value,current_rows_value,current_asset_record)
                current_image_data,current_frame_rows=current_loaded_values[:2]
                current_pending_record,_,current_summary_text=prepare_sprite_sheet_update(current_asset_record,'sheet.png',current_image_data,current_frame_rows,2,[current_row[:4] for current_row in current_frame_rows])
                self.assertIn('좌표맵 없음',current_summary_text)
                self.assertEqual(len(current_pending_record['payload']['frames']),2)
                current_saved_record=execute_management_command('character-animation','sheet-update',current_pending_record)
                self.assertEqual(current_saved_record['path'],'sheet.png')
                self.assertEqual(len(editor.execute_sprite_asset_command('sheet-image',{'path':'sheet.png','source':'baseline'})['animation']['frames']),2)
                with self.assertRaisesRegex(Exception,'프레임 수'):
                    prepare_sprite_sheet_update(current_asset_record,'sheet.png',current_image_data,current_frame_rows[:1],2,[current_frame_rows[0][:4]])

    def test_update_and_stale_source_rejection(self):
        with TemporaryDirectory() as current_temp_directory:
            current_root_path=Path(current_temp_directory)
            current_image_path=current_root_path/'sheet.png'
            Image.new('RGB',(12,12),'white').save(current_image_path)
            current_yaml_path=current_image_path.with_suffix('.yaml')
            current_yaml_path.write_text(yaml.safe_dump({'layout':{'columns':1,'rows':1},'motions':[{'name':'rest','first_frame':1,'frame_count':1}]}))
            with patch.object(editor,'SPRITE_BASELINE_ROOT',current_root_path),patch.object(editor,'SPRITE_SHEET_JOB_ROOT',current_root_path/'jobs'):
                current_loaded_record=editor.execute_sprite_asset_command('sheet-image',{'path':'sheet.png','source':'baseline'})
                current_request_record={'source':'baseline','path':'sheet.png','metadataSha256':current_loaded_record['metadataSha256'],'confirm':True,'payload':{'image':current_loaded_record['image'],'columns':1,'frames':[{'x':0,'y':0,'width':10,'height':11,'anchorX':4,'anchorY':9}]}}
                current_saved_record=editor.update_registered_sprite_sheet(current_request_record)
                current_updated_record=editor.execute_sprite_asset_command('sheet-image',{'path':'sheet.png','source':'baseline'})
                self.assertEqual(current_updated_record['animation']['frames'][0]['anchor'],{'x':4,'y':9})
                self.assertEqual(current_updated_record['animation']['sheet'],{'width':10,'height':11})
                self.assertEqual(yaml.safe_load(current_yaml_path.read_text())['motions'][0]['name'],'rest')
                self.assertTrue(list((current_root_path/'jobs').rglob('before/paths.json')))
                with self.assertRaisesRegex(ValueError,'변경'):
                    editor.update_registered_sprite_sheet(current_request_record)
                with self.assertRaises(ValueError):
                    editor.update_registered_sprite_sheet({**current_request_record,'confirm':False})
                with self.assertRaises(ValueError):
                    editor.update_registered_sprite_sheet({**current_request_record,'path':'../outside.png'})
