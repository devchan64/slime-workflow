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
