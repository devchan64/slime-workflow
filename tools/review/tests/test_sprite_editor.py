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
