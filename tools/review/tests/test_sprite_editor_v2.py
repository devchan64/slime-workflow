"""v2 작업의 불변 이력, 입력 검증과 실제 출력 계약을 확인한다."""
import base64
import copy
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from tools.review.domains.character_animation import sprite_editor_v2
from tools.review.common.management_gateway import resolve_management_command, identify_management_command


class SpriteEditorV2Tests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory_value=tempfile.TemporaryDirectory()
        self.workspace_patch_value=patch.object(sprite_editor_v2,'SPRITE_V2_WORKSPACE_ROOT',Path(self.temporary_directory_value.name))
        self.workspace_patch_value.start()
        self.initial_project_record=self.execute_test_command('create',{'name':'검수','cellSize':384})
        self.current_project_identifier=self.initial_project_record['id']

    def tearDown(self):
        self.workspace_patch_value.stop()
        self.temporary_directory_value.cleanup()

    def execute_test_command(self,current_command_name,current_payload_record):
        return sprite_editor_v2.execute_v2_command('sprite-v2-'+current_command_name,current_payload_record)

    def test_delete_project_requires_confirmation_and_preserves_other_projects(self):
        current_other_project=self.execute_test_command('create',{'name':'보존','cellSize':384})
        current_project_path=sprite_editor_v2.resolve_v2_project(self.current_project_identifier)
        with self.assertRaises(ValueError):
            self.execute_test_command('delete',{'id':self.current_project_identifier,'confirm':False})
        self.assertTrue(current_project_path.exists())
        self.execute_test_command('delete',{'id':self.current_project_identifier,'confirm':True})
        self.assertFalse(current_project_path.exists())
        self.assertEqual([value['id'] for value in self.execute_test_command('list',{})['items']],[current_other_project['id']])
        with self.assertRaises(ValueError):
            self.execute_test_command('load',{'id':self.current_project_identifier,'revision':None})

    def create_test_frame(self):
        current_image_buffer=io.BytesIO()
        current_source_image=Image.new('RGBA',(384,384))
        current_source_image.putpixel((192,192),(255,0,0,255))
        current_source_image.save(current_image_buffer,format='PNG')
        current_upload_record=self.execute_test_command('upload',{'id':self.current_project_identifier,'data':base64.b64encode(current_image_buffer.getvalue()).decode()})
        return {'id':'frame-1','asset':current_upload_record['asset'],'name':'기준','x':1,'y':0,'scale':1,'duration':150,'face':{'x':192,'y':50,'radius':30},'guides':[{'label':'발바닥','axis':'y','position':360}]}

    def test_revision_conflict_and_old_version_restore(self):
        current_document_record=copy.deepcopy(self.initial_project_record['document'])
        current_document_record['frames']=[self.create_test_frame()]
        saved_revision_record=self.execute_test_command('save',{'id':self.current_project_identifier,'parent':self.initial_project_record['revision'],'document':current_document_record})
        with self.assertRaisesRegex(ValueError,'다른 화면'):
            self.execute_test_command('save',{'id':self.current_project_identifier,'parent':self.initial_project_record['revision'],'document':current_document_record})
        restored_revision_record=self.execute_test_command('load',{'id':self.current_project_identifier,'revision':self.initial_project_record['revision']})
        self.assertEqual(restored_revision_record['document']['frames'],[])
        self.assertEqual(restored_revision_record['latest'],saved_revision_record['revision'])
        self.assertEqual(len(self.execute_test_command('history',{'id':self.current_project_identifier})['items']),2)

    def test_export_position_alpha_frame_order_and_duration(self):
        current_document_record=copy.deepcopy(self.initial_project_record['document'])
        current_first_frame=self.create_test_frame()
        current_second_frame={**copy.deepcopy(current_first_frame),'id':'frame-2','x':2,'duration':250}
        current_document_record['frames']=[current_first_frame,current_second_frame]
        saved_revision_record=self.execute_test_command('save',{'id':self.current_project_identifier,'parent':self.initial_project_record['revision'],'document':current_document_record})
        export_result_record=self.execute_test_command('export',{'id':self.current_project_identifier,'revision':saved_revision_record['revision']})
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(export_result_record['data']))) as archive_source_value:
            with Image.open(io.BytesIO(archive_source_value.read('frame-001.png'))) as frame_source_image:
                self.assertEqual(frame_source_image.size,(384,384))
                self.assertEqual(frame_source_image.getpixel((193,192)),(255,0,0,255))
                self.assertEqual(frame_source_image.getpixel((0,0))[3],0)
            with Image.open(io.BytesIO(archive_source_value.read('sheet.png'))) as sheet_source_image:
                self.assertEqual(sheet_source_image.size,(768,384))
                self.assertEqual(sheet_source_image.getpixel((384+194,192)),(255,0,0,255))
            with Image.open(io.BytesIO(archive_source_value.read('review.gif'))) as gif_source_image:
                self.assertEqual(gif_source_image.n_frames,2)
                self.assertEqual(gif_source_image.info['duration'],150)
                gif_source_image.seek(1)
                self.assertEqual(gif_source_image.info['duration'],250)

    def test_export_balanced_sheet_preserves_frame_positions(self):
        current_source_frame=self.create_test_frame()
        for current_frame_count,expected_grid_shape in [(3,(3,1)),(7,(7,1)),(8,(4,2)),(9,(3,3)),(12,(4,3)),(16,(4,4))]:
            with self.subTest(frame_count=current_frame_count):
                current_document_record=copy.deepcopy(self.initial_project_record['document'])
                current_document_record['frames']=[{**copy.deepcopy(current_source_frame),'id':f'frame-{current_frame_index}','x':current_frame_index} for current_frame_index in range(current_frame_count)]
                current_project_path=sprite_editor_v2.resolve_v2_project(self.current_project_identifier)
                export_result_record=sprite_editor_v2.export_v2_revision(current_project_path,{'revision':f'test-{current_frame_count}','document':current_document_record})
                with zipfile.ZipFile(io.BytesIO(base64.b64decode(export_result_record['data']))) as archive_source_value:
                    current_export_metadata=json.loads(archive_source_value.read('metadata.json'))
                    self.assertEqual(current_export_metadata['columns'],expected_grid_shape[0])
                    with Image.open(io.BytesIO(archive_source_value.read('sheet.png'))) as sheet_source_image:
                        self.assertEqual(sheet_source_image.size,tuple(current_grid_count*384 for current_grid_count in expected_grid_shape))
                        for current_frame_index in range(current_frame_count):
                            current_pixel_left=(current_frame_index%expected_grid_shape[0])*384+192+current_frame_index
                            current_pixel_top=(current_frame_index//expected_grid_shape[0])*384+192
                            self.assertEqual(sheet_source_image.getpixel((current_pixel_left,current_pixel_top)),(255,0,0,255))
                        self.assertEqual(expected_grid_shape[0]*expected_grid_shape[1],current_frame_count)

    def test_invalid_input_and_unregistered_image_rejected(self):
        with self.assertRaises(ValueError):self.execute_test_command('create',{'name':'검수','cellSize':512})
        with self.assertRaises(ValueError):self.execute_test_command('load',{'id':'../x','revision':None})
        with self.assertRaises(ValueError):self.execute_test_command('upload',{'id':self.current_project_identifier,'data':'not an image'})
        current_document_record=copy.deepcopy(self.initial_project_record['document'])
        current_frame_record=self.create_test_frame()
        for current_field_name,current_invalid_value in [('scale',float('nan')),('asset','../file'),('duration',-1)]:
            current_document_record['frames']=[{**current_frame_record,current_field_name:current_invalid_value}]
            with self.assertRaises(ValueError):
                self.execute_test_command('save',{'id':self.current_project_identifier,'parent':self.initial_project_record['revision'],'document':current_document_record})
        current_document_record['frames']=[current_frame_record,current_frame_record]
        with self.assertRaises(ValueError):self.execute_test_command('save',{'id':self.current_project_identifier,'parent':self.initial_project_record['revision'],'document':current_document_record})

    def test_gateway_roundtrip_and_256_output(self):
        for current_command_name in ('create','list','upload','save','load','history','export'):
            current_method_name,current_route_path=resolve_management_command('character-animation','sprite-v2-'+current_command_name,{})
            self.assertEqual(identify_management_command(current_route_path,current_method_name,{})[:2],('character-animation','sprite-v2-'+current_command_name))
        current_document_record=copy.deepcopy(self.initial_project_record['document'])
        current_document_record['cellSize']=256
        current_document_record['frames']=[self.create_test_frame()]
        saved_revision_record=self.execute_test_command('save',{'id':self.current_project_identifier,'parent':self.initial_project_record['revision'],'document':current_document_record})
        export_result_record=self.execute_test_command('export',{'id':self.current_project_identifier,'revision':saved_revision_record['revision']})
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(export_result_record['data']))) as archive_source_value:
            with Image.open(io.BytesIO(archive_source_value.read('frame-001.png'))) as frame_source_image:self.assertEqual(frame_source_image.size,(256,256))

if __name__=='__main__':unittest.main()
