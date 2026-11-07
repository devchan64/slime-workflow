import unittest,json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from hashlib import sha256
from PIL import Image
from tools.review.domains.character_animation import sprite_sheet_editor as editor
class BaselineSearchTests(unittest.TestCase):
    def test_search_load_and_hash_validation(self):
        with TemporaryDirectory() as current_temp_directory:
            current_root_path=Path(current_temp_directory)
            current_image_path=current_root_path/'rest.png'
            Image.new('RGB',(40,60),'white').save(current_image_path)
            current_sidecar_path=current_image_path.with_suffix('.yaml')
            current_sidecar_path.write_text('description: 기본 휴식\nlayout: {columns: 4, rows: 6}\n')
            with patch.object(editor,'SPRITE_BASELINE_ROOT',current_root_path):
                current_result_record=editor.execute_sprite_asset_command('sheet-search',{'query':'기본 휴식','source':'baseline'})
                self.assertEqual(len(current_result_record['items']),1)
                current_loaded_record=editor.execute_sprite_asset_command('sheet-image',{'path':'rest.png','source':'baseline'})
                self.assertEqual(current_loaded_record['layout'],{'columns':4,'rows':6})
                with self.assertRaises(ValueError):
                    editor.execute_sprite_asset_command('sheet-image',{'path':'../rest.png','source':'baseline'})
                current_sidecar_path.write_text(current_sidecar_path.read_text()+'coordinates: rest.json\n')
                current_coordinate_record={'sha256':sha256(current_image_path.read_bytes()).hexdigest(),'frames':[]}
                (current_root_path/'rest.json').write_text(json.dumps(current_coordinate_record))
                self.assertEqual(editor.execute_sprite_asset_command('sheet-image',{'path':'rest.png','source':'baseline'})['animation'],current_coordinate_record)
                current_coordinate_record['sha256']='invalid'
                (current_root_path/'rest.json').write_text(json.dumps(current_coordinate_record))
                with self.assertRaises(ValueError):
                    editor.execute_sprite_asset_command('sheet-image',{'path':'rest.png','source':'baseline'})
    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            editor.execute_sprite_asset_command('sheet-search',{'query':'','source':'unknown'})
