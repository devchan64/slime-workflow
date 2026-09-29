"""원본을 변경하지 않는 스프라이트 편집 저장 계약을 검증한다."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.review.domains.character_animation import sprite_editor

class SpriteEditorPersistenceTests(unittest.TestCase):
    def setUp(self):
        renderer_patch_value=patch.object(sprite_editor,'render_sprite_saved_sheet',return_value={'file':'test.png','width':1536,'height':1536})
        renderer_patch_value.start()
        self.addCleanup(renderer_patch_value.stop)

    def test_failed_sheet_does_not_publish_revision(self):
        source_asset_record={'id':'asset:test','frames':[{'frameId':'front.0'}]}
        project_document_value={'version':1,'source':'asset:test','frames':{'front.0':dict(center=20,floor=80,head=0,anchorX=20,anchorY=80,x=0,y=0,scale=1)}}
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(sprite_editor,'SPRITE_PROJECT_DIRECTORY',Path(temporary_directory_name)), patch.object(sprite_editor,'load_sprite_editor_source',return_value=source_asset_record), patch.object(sprite_editor,'render_sprite_saved_sheet',side_effect=ValueError('원본 이미지 없음')):
            with self.assertRaises(ValueError):sprite_editor.execute_sprite_editor_command('sprite-save',{'id':'asset:test','document':project_document_value})
            self.assertEqual(list(Path(temporary_directory_name).rglob('*.json')),[])

    def test_revision_restore_and_source_change(self):
        source_asset_record={'id':'asset:test','frames':[{'frameId':'front.0'}]}
        project_document_value={'version':1,'source':'asset:test','frames':{'front.0':dict(center=20,floor=80,head=0,anchorX=20,anchorY=80,x=0,y=0,scale=1)}}
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(sprite_editor,'SPRITE_PROJECT_DIRECTORY',Path(temporary_directory_name)), patch.object(sprite_editor,'load_sprite_editor_source',return_value=source_asset_record):
            first_saved_record=sprite_editor.execute_sprite_editor_command('sprite-save',{'id':'asset:test','document':project_document_value})
            second_saved_record=sprite_editor.execute_sprite_editor_command('sprite-save',{'id':'asset:test','document':project_document_value})
            self.assertNotEqual(first_saved_record['revision'],second_saved_record['revision'])
            history_response_value=sprite_editor.execute_sprite_editor_command('sprite-history',{'id':'asset:test'})
            self.assertEqual(len(history_response_value['items']),2)
            self.assertTrue(all(current_history_record['compatible'] for current_history_record in history_response_value['items']))
            self.assertEqual(history_response_value['items'][0]['document'],project_document_value)
            self.assertTrue(Path(first_saved_record['path']).exists())
            self.assertEqual(sprite_editor.execute_sprite_editor_command('sprite-load',{'id':'asset:test'})['document'],project_document_value)
            source_asset_record['version']=2
            self.assertFalse(sprite_editor.execute_sprite_editor_command('sprite-history',{'id':'asset:test'})['items'][0]['compatible'])
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
            project_document_value['guides']=[{'axis':'horizontal','position':.25},{'axis':'vertical','position':.75}]
            sprite_editor.execute_sprite_editor_command('sprite-save',{'id':'asset:test','document':project_document_value})
            self.assertEqual(sprite_editor.execute_sprite_editor_command('sprite-load',{'id':'asset:test'})['document']['guides'],project_document_value['guides'])
            for invalid_guide_records in [None,[{'axis':'diagonal','position':.5}],[{'axis':'vertical','position':True}],[{'axis':'horizontal','position':float('nan')}],[{'axis':'horizontal','position':1.1}],[{'axis':'vertical','position':.5,'unknown':1}],[{'axis':'vertical','position':.5}]*33]:
                project_document_value['guides']=invalid_guide_records
                with self.assertRaises(ValueError):sprite_editor.execute_sprite_editor_command('sprite-save',{'id':'asset:test','document':project_document_value})
            project_document_value['guides']=[]
            for invalid_output_record in [{'cellSize':4097,'targetHeight':360},{'cellSize':True,'targetHeight':1},{'cellSize':384,'targetHeight':385},{'cellSize':384,'targetHeight':float('nan')},{'cellSize':384,'targetHeight':360,'unknown':1}]:
                with self.subTest(invalid_output_record=invalid_output_record):
                    project_document_value['output']=invalid_output_record
                    with self.assertRaises(ValueError):sprite_editor.execute_sprite_editor_command('sprite-save',{'id':'asset:test','document':project_document_value})
            with self.assertRaises(ValueError):sprite_editor.execute_sprite_editor_command('unsupported',{'id':'asset:test'})

    def test_history_reset_preserves_files_and_new_saves(self):
        source_asset_record={'id':'asset:test','frames':[{'frameId':'front.0'}]}
        project_document_value={'version':1,'source':'asset:test','frames':{'front.0':dict(center=20,floor=80,head=0,anchorX=20,anchorY=80,x=0,y=0,scale=1)}}
        with tempfile.TemporaryDirectory() as temporary_directory_name, patch.object(sprite_editor,'SPRITE_PROJECT_DIRECTORY',Path(temporary_directory_name)), patch.object(sprite_editor,'load_sprite_editor_source',return_value=source_asset_record):
            first_saved_record=sprite_editor.execute_sprite_editor_command('sprite-save',{'id':'asset:test','document':project_document_value})
            second_saved_record=sprite_editor.execute_sprite_editor_command('sprite-save',{'id':'asset:test','document':project_document_value})
            sprite_editor.execute_sprite_editor_command('sprite-history-delete',{'id':'asset:test','revision':first_saved_record['revision']})
            self.assertEqual(len(sprite_editor.execute_sprite_editor_command('sprite-history',{'id':'asset:test'})['items']),1)
            with self.assertRaises(ValueError):sprite_editor.execute_sprite_editor_command('sprite-history-delete',{'id':'asset:test','revision':'../latest'})
            sprite_editor.execute_sprite_editor_command('sprite-history-reset',{'id':'asset:test'})
            self.assertEqual(sprite_editor.execute_sprite_editor_command('sprite-history',{'id':'asset:test'})['items'],[])
            self.assertIsNone(sprite_editor.execute_sprite_editor_command('sprite-load',{'id':'asset:test'})['document'])
            self.assertTrue(Path(first_saved_record['path']).exists())
            self.assertTrue(Path(second_saved_record['path']).exists())
            third_saved_record=sprite_editor.execute_sprite_editor_command('sprite-save',{'id':'asset:test','document':project_document_value})
            self.assertEqual([current_history_record['id'] for current_history_record in sprite_editor.execute_sprite_editor_command('sprite-history',{'id':'asset:test'})['items']],[third_saved_record['revision']])

class SpriteSheetRenderingTests(unittest.TestCase):
    def test_saved_sheet_applies_translation_and_transparency(self):
        from PIL import Image
        from tools.review.domains.character_animation import sprite_sheet
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_test_root=Path(temporary_directory_name)
            source_image_path=current_test_root/'source.png'
            source_image_value=Image.new('RGBA',(128,128));source_image_value.putpixel((20,30),(255,0,0,255));source_image_value.save(source_image_path)
            source_asset_record={'id':'asset:test','frames':[{'frameId':'down_left.0','direction':'down_left','rect':{'x':0,'y':0,'width':128,'height':128},'url':'/animation-1/source.png'}]}
            project_document_value={'version':2,'output':{'cellSize':128},'frames':{'down_left.0':{'anchorX':64,'anchorY':123,'x':3,'y':-2,'scale':1}}}
            with patch.object(sprite_sheet,'resolve_sprite_image_path',return_value=source_image_path):
                sheet_result_value=sprite_sheet.render_sprite_saved_sheet(source_asset_record,project_document_value,current_test_root/'saved.png')
            with Image.open(current_test_root/'saved.png') as saved_image_value:
                self.assertEqual(saved_image_value.getpixel((23,28)),(255,0,0,255))
                self.assertEqual(saved_image_value.getpixel((20,30)),(0,0,0,0))
                self.assertEqual(saved_image_value.size,(128,128))
            self.assertEqual(sheet_result_value['anchor'],{'x':64,'y':123})

    def test_v3_retains_pixels_below_anchor(self):
        from PIL import Image
        from tools.review.domains.character_animation import sprite_sheet
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_test_root=Path(temporary_directory_name)
            source_image_path=current_test_root/'source.png'
            source_image_value=Image.new('RGBA',(384,384))
            source_image_value.putpixel((192,374),(255,0,0,255))
            source_image_value.putpixel((192,2),(0,255,0,255))
            source_image_value.save(source_image_path)
            source_asset_record={'id':'asset:test','frames':[{'frameId':'down_left.0','direction':'down_left','rect':{'x':0,'y':0,'width':384,'height':384},'url':'/animation-1/source.png'}]}
            project_document_value={'version':3,'output':{'cellSize':384},'frames':{'down_left.0':{'anchorX':192,'anchorY':346,'x':0,'y':0,'scale':1}}}
            with patch.object(sprite_sheet,'resolve_sprite_image_path',return_value=source_image_path):
                sheet_result_value=sprite_sheet.render_sprite_saved_sheet(source_asset_record,project_document_value,current_test_root/'saved.png')
            with Image.open(current_test_root/'saved.png') as saved_image_value:
                self.assertEqual(saved_image_value.getpixel((192,374)),(255,0,0,255))
                self.assertEqual(saved_image_value.getpixel((192,2)),(0,255,0,255))
            self.assertEqual(sheet_result_value['anchor'],{'x':192,'y':346})
