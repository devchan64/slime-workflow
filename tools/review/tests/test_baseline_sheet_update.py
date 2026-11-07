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
