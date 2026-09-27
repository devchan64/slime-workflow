"""원본을 변경하지 않는 스프라이트 편집 저장 계약을 검증한다."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.review.domains.character_animation import sprite_editor

class SpriteEditorPersistenceTests(unittest.TestCase):
    def test_revision_restore_and_source_change(self):
        source_asset_record={'id':'asset:test','frames':[{'frameId':'front.0'}]}
        project_document_value={'version':1,'source':'asset:test','frames':{'front.0':dict(center=20,floor=80,head=0,anchorX=20,anchorY=80,x=0,y=0,scale=1)}}
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(sprite_editor,'SPRITE_PROJECT_DIRECTORY',Path(temporary_directory_name)), patch.object(sprite_editor,'load_sprite_editor_source',return_value=source_asset_record):
            first_saved_record=sprite_editor.execute_sprite_editor_command('sprite-save',{'id':'asset:test','document':project_document_value})
            second_saved_record=sprite_editor.execute_sprite_editor_command('sprite-save',{'id':'asset:test','document':project_document_value})
            self.assertNotEqual(first_saved_record['revision'],second_saved_record['revision'])
            self.assertTrue(Path(first_saved_record['path']).exists())
            self.assertEqual(sprite_editor.execute_sprite_editor_command('sprite-load',{'id':'asset:test'})['document'],project_document_value)
            source_asset_record['version']=2
            self.assertIsNone(sprite_editor.execute_sprite_editor_command('sprite-load',{'id':'asset:test'})['document'])
            project_document_value['frames']['front.0']['scale']=float('nan')
            with self.assertRaises(ValueError):sprite_editor.execute_sprite_editor_command('sprite-save',{'id':'asset:test','document':project_document_value})
            project_document_value['frames']={}
            with self.assertRaises(ValueError):sprite_editor.execute_sprite_editor_command('sprite-save',{'id':'asset:test','document':project_document_value})

    def test_output_size_persists_and_invalid_output_is_rejected(self):
        source_asset_record={'id':'asset:test','frames':[{'frameId':'down_left.0'}]}
        project_document_value={'version':2,'source':'asset:test','output':{'cellSize':384,'targetHeight':367.5},'frames':{'down_left.0':dict(center=192,floor=374,head=1,anchorX=192,anchorY=374,x=0,y=5,scale=1)}}
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(sprite_editor,'SPRITE_PROJECT_DIRECTORY',Path(temporary_directory_name)), patch.object(sprite_editor,'load_sprite_editor_source',return_value=source_asset_record):
            sprite_editor.execute_sprite_editor_command('sprite-save',{'id':'asset:test','document':project_document_value})
            self.assertEqual(sprite_editor.execute_sprite_editor_command('sprite-load',{'id':'asset:test'})['document'],project_document_value)
            for invalid_output_record in [{'cellSize':385,'targetHeight':360},{'cellSize':True,'targetHeight':1},{'cellSize':384,'targetHeight':385},{'cellSize':384,'targetHeight':float('nan')},{'cellSize':384,'targetHeight':360,'unknown':1}]:
                with self.subTest(invalid_output_record=invalid_output_record):
                    project_document_value['output']=invalid_output_record
                    with self.assertRaises(ValueError):sprite_editor.execute_sprite_editor_command('sprite-save',{'id':'asset:test','document':project_document_value})
            with self.assertRaises(ValueError):sprite_editor.execute_sprite_editor_command('unsupported',{'id':'asset:test'})
