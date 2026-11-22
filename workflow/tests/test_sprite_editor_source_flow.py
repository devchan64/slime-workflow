"""검색 선택과 편집 원본 분리 및 교체 확인을 검증한다."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


class SpriteEditorSourceFlowTests(unittest.TestCase):
    def test_link_and_restore_contracts_in_current_frontend(self):
        import subprocess
        root=Path(__file__).resolve().parents[2]
        for name in ('sprite_source_link.test.mjs','sprite_anchor_restore.test.mjs'):
            result=subprocess.run(['node',str(root/'workflow/tests'/name)],cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_asset_search_indexes_verified_animation_identifier(self):
        import json,hashlib
        from workflow.domains.character_animation.sprite_sheet_editor import execute_sprite_asset_command
        with TemporaryDirectory() as current_temp_directory:
            current_root_path=Path(current_temp_directory)
            current_image_name='assets/characters/default/animations/rest/sheet.png'
            current_metadata_name='assets/characters/default/animations/rest/sheet.animation.json'
            current_metadata_path=current_root_path/current_metadata_name
            current_metadata_path.parent.mkdir(parents=True)
            current_metadata_path.write_text(json.dumps({'animationId':'character.rest'}))
            current_registry_records={current_image_name:{'source':{},'sha256':'a'*64,'managementId':'image.rest'},current_metadata_name:{'source':{},'sha256':hashlib.sha256(current_metadata_path.read_bytes()).hexdigest()}}
            with patch('workflow.common.map_tile_assets.load_registered_tiles',return_value=(current_root_path,current_registry_records)):
                current_search_result=execute_sprite_asset_command('sheet-search',{'query':'character.rest'})
                self.assertEqual(current_search_result['items'][0]['animationIds'],['character.rest'])
                current_metadata_path.write_text('{}')
                with self.assertRaises(ValueError):execute_sprite_asset_command('sheet-search',{'query':'character.rest'})
