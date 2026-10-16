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

    def test_create_rejects_linked_date_directory(self):
        from datetime import datetime
        current_fixed_time = datetime(2026, 1, 2, 3, 4, 5, tzinfo=sprite_editor_v2.SPRITE_V2_TIME_ZONE)
        with tempfile.TemporaryDirectory() as current_external_directory:
            current_external_path = Path(current_external_directory)
            current_date_path = sprite_editor_v2.SPRITE_V2_WORKSPACE_ROOT / '2026-01-02_03-04-05'
            current_date_path.symlink_to(current_external_path, target_is_directory=True)
            try:
                with patch.object(sprite_editor_v2, 'datetime') as current_datetime_mock:
                    current_datetime_mock.now.return_value = current_fixed_time
                    with self.assertRaisesRegex(ValueError, '작업 경로'):
                        self.execute_test_command('create', {'name': '차단 작업', 'cellSize': 256})
                self.assertEqual(list(current_external_path.iterdir()), [])
            finally:
                current_date_path.unlink()

    def test_new_project_default_fps(self):
        self.assertEqual(self.initial_project_record['document']['fps'],6)

    def test_list_rejects_mismatched_project_directory(self):
        current_project_path = sprite_editor_v2.resolve_v2_project(self.current_project_identifier)
        current_duplicate_path = sprite_editor_v2.SPRITE_V2_WORKSPACE_ROOT / 'wrong-date' / self.current_project_identifier
        current_duplicate_path.mkdir(parents=True)
        (current_duplicate_path / 'latest.json').write_bytes((current_project_path / 'latest.json').read_bytes())
        with self.assertRaisesRegex(ValueError, '날짜 경로'):
            self.execute_test_command('list', {})

    def test_all_project_commands_reject_linked_project_root(self):
        current_project_path = sprite_editor_v2.resolve_v2_project(self.current_project_identifier)
        with tempfile.TemporaryDirectory() as current_external_directory:
            current_external_path = Path(current_external_directory) / 'preserved-project'
            current_project_path.rename(current_external_path)
            current_project_path.symlink_to(current_external_path, target_is_directory=True)
            current_original_files = {str(current_file_path.relative_to(current_external_path)): current_file_path.read_bytes() for current_file_path in current_external_path.rglob('*') if current_file_path.is_file()}
            with self.assertRaisesRegex(ValueError, '작업 경로'):
                self.execute_test_command('list', {})
            current_command_payloads = {
                'load': {'revision': None}, 'history': {}, 'export': {'revision': None},
                'save': {'parent': self.initial_project_record['revision'], 'document': self.initial_project_record['document']},
                'upload': {'data': ''}, 'delete': {'confirm': True},
                'revision-delete': {'revision': self.initial_project_record['revision'], 'confirm': True}}
            for current_command_name, current_command_payload in current_command_payloads.items():
                with self.subTest(command=current_command_name), self.assertRaisesRegex(ValueError, '작업 경로'):
                    self.execute_test_command(current_command_name, {'id': self.current_project_identifier, **current_command_payload})
            self.assertEqual({str(current_file_path.relative_to(current_external_path)): current_file_path.read_bytes() for current_file_path in current_external_path.rglob('*') if current_file_path.is_file()}, current_original_files)
            current_project_path.unlink()

    def test_internal_links_cannot_read_or_modify_external_files(self):
        current_project_path = sprite_editor_v2.resolve_v2_project(self.current_project_identifier)
        with tempfile.TemporaryDirectory() as current_external_directory:
            current_external_path = Path(current_external_directory) / 'preserved.txt'
            current_external_path.write_bytes(b'external original')
            for current_relative_path in ('project.json', 'latest.json', 'images/linked.png', 'revisions/linked.json', 'exports'):
                with self.subTest(path=current_relative_path):
                    current_link_path = current_project_path / current_relative_path
                    current_original_bytes = current_link_path.read_bytes() if current_link_path.is_file() else None
                    current_link_path.parent.mkdir(parents=True, exist_ok=True)
                    current_link_path.unlink(missing_ok=True)
                    current_link_path.symlink_to(current_external_path)
                    try:
                        for current_command_name, current_payload_record in (
                            ('list', {}), ('load', {'id': self.current_project_identifier, 'revision': None}),
                            ('save', {'id': self.current_project_identifier, 'parent': self.initial_project_record['revision'], 'document': self.initial_project_record['document']}),
                            ('delete', {'id': self.current_project_identifier, 'confirm': True})):
                            with self.assertRaisesRegex(ValueError, '심볼릭 링크'):
                                self.execute_test_command(current_command_name, current_payload_record)
                        self.assertEqual(current_external_path.read_bytes(), b'external original')
                    finally:
                        current_link_path.unlink()
                        if current_original_bytes is not None:
                            current_link_path.write_bytes(current_original_bytes)

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

    def test_revision_delete_validation_and_last_revision_preserved(self):
        current_delete_payload={'id':self.current_project_identifier,'revision':self.initial_project_record['revision'],'confirm':True}
        with self.assertRaisesRegex(ValueError,'확인'):
            self.execute_test_command('revision-delete',{**current_delete_payload,'confirm':False})
        with self.assertRaisesRegex(ValueError,'마지막'):
            self.execute_test_command('revision-delete',current_delete_payload)
        with self.assertRaisesRegex(ValueError,'형식'):
            self.execute_test_command('revision-delete',{**current_delete_payload,'revision':'../latest'})
        with self.assertRaisesRegex(ValueError,'없습니다'):
            self.execute_test_command('revision-delete',{**current_delete_payload,'revision':'20000101T000000-00000000'})
        self.assertEqual(self.execute_test_command('load',{'id':self.current_project_identifier,'revision':None})['revision'],self.initial_project_record['revision'])

    def test_revision_delete_promotes_latest_and_preserves_images(self):
        current_document_record=copy.deepcopy(self.initial_project_record['document'])
        current_document_record['frames']=[self.create_test_frame()]
        current_first_saved=self.execute_test_command('save',{'id':self.current_project_identifier,'parent':self.initial_project_record['revision'],'document':current_document_record})
        current_second_saved=self.execute_test_command('save',{'id':self.current_project_identifier,'parent':current_first_saved['revision'],'document':current_document_record})
        current_delete_result=self.execute_test_command('revision-delete',{'id':self.current_project_identifier,'revision':self.initial_project_record['revision'],'confirm':True})
        self.assertEqual(current_delete_result['latest'],current_second_saved['revision'])
        current_delete_result=self.execute_test_command('revision-delete',{'id':self.current_project_identifier,'revision':current_second_saved['revision'],'confirm':True})
        self.assertEqual(current_delete_result['latest'],current_first_saved['revision'])
        current_loaded_record=self.execute_test_command('load',{'id':self.current_project_identifier,'revision':None})
        self.assertEqual(current_loaded_record['document'],current_document_record)
        self.assertIn(current_document_record['frames'][0]['asset'],current_loaded_record['images'])
        self.assertEqual([value['revision'] for value in self.execute_test_command('history',{'id':self.current_project_identifier})['items']],[current_first_saved['revision']])
        self.assertEqual(len(self.execute_test_command('list',{})['items']),1)

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

    def test_simultaneous_saves_accept_only_one_parent_revision(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        current_start_barrier = threading.Barrier(2)
        def save_competing_document(current_document_name):
            current_document_record = copy.deepcopy(self.initial_project_record['document'])
            current_document_record['name'] = current_document_name
            current_start_barrier.wait(timeout=5)
            return self.execute_test_command('save', {'id': self.current_project_identifier,
                'parent': self.initial_project_record['revision'], 'document': current_document_record})
        current_saved_records = []
        current_rejected_messages = []
        with ThreadPoolExecutor(max_workers=2) as current_worker_pool:
            current_save_futures = [current_worker_pool.submit(save_competing_document, current_document_name) for current_document_name in ('첫 화면', '둘째 화면')]
            for current_save_future in current_save_futures:
                try:
                    current_saved_records.append(current_save_future.result(timeout=5))
                except ValueError as current_conflict_error:
                    current_rejected_messages.append(str(current_conflict_error))
        self.assertEqual(len(current_saved_records), 1)
        self.assertEqual(len(current_rejected_messages), 1)
        self.assertIn('다른 화면에서 수정', current_rejected_messages[0])
        current_latest_record = self.execute_test_command('load', {'id': self.current_project_identifier, 'revision': None})
        self.assertEqual(current_latest_record['document'], current_saved_records[0]['document'])
        self.assertEqual(len(self.execute_test_command('history', {'id': self.current_project_identifier})['items']), 2)

    def test_independent_scale_saved_and_exported(self):
        current_frame_record=self.create_test_frame()
        current_image_buffer=io.BytesIO()
        Image.new('RGBA',(100,100),(255,0,0,255)).save(current_image_buffer,format='PNG')
        current_upload_record=self.execute_test_command('upload',{'id':self.current_project_identifier,'data':base64.b64encode(current_image_buffer.getvalue()).decode()})
        current_frame_record.update(asset=current_upload_record['asset'],x=0,y=0,scaleX=.5,scaleY=.25)
        current_document_record=copy.deepcopy(self.initial_project_record['document'])
        current_document_record['frames']=[current_frame_record]
        current_saved_record=self.execute_test_command('save',{'id':self.current_project_identifier,'parent':self.initial_project_record['revision'],'document':current_document_record})
        current_loaded_record=self.execute_test_command('load',{'id':self.current_project_identifier,'revision':None})
        self.assertEqual(current_loaded_record['document']['frames'][0]['scaleX'],.5)
        self.assertEqual(current_loaded_record['document']['frames'][0]['scaleY'],.25)
        current_export_record=self.execute_test_command('export',{'id':self.current_project_identifier,'revision':current_saved_record['revision']})
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(current_export_record['data']))) as current_archive_file:
            with Image.open(io.BytesIO(current_archive_file.read('frame-001.png'))) as current_export_image:
                self.assertEqual(current_export_image.getbbox(),(96,144,288,240))
        current_frame_record['scaleY']=0
        with self.assertRaises(ValueError):
            sprite_editor_v2.validate_v2_document(current_document_record,sprite_editor_v2.resolve_v2_project(self.current_project_identifier))

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
        for current_command_name in ('create','list','upload','save','load','history','export','revision-delete'):
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
