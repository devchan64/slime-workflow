"""격리된 이미지로 크롭·공통 앵커 출력과 명령 계약을 검증한다."""
import base64
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from PIL import Image
from tools.review.common.management_gateway import execute_management_command, resolve_management_command
from tools.review.domains.character_animation import sprite_sheet_editor


class SpriteSheetEditorTests(unittest.TestCase):
    def test_gif_gateway_aligns_anchors_and_rejects_invalid_fps(self):
        current_source_image=Image.new('RGB',(8,4),'white')
        current_source_image.putpixel((1,1),(255,0,0))
        current_source_image.putpixel((6,2),(0,0,255))
        current_image_stream=BytesIO();current_source_image.save(current_image_stream,format='PNG')
        current_request_record={'image':base64.b64encode(current_image_stream.getvalue()).decode(),'frames':[{'x':0,'y':0,'width':4,'height':4,'anchorX':1,'anchorY':1},{'x':4,'y':0,'width':4,'height':4,'anchorX':2,'anchorY':2}],'columns':2,'fps':4}
        self.assertEqual(resolve_management_command('character-animation','sheet-gif',current_request_record),('POST','/character-animation/sheet/gif'))
        with TemporaryDirectory() as current_directory_name, patch.object(sprite_sheet_editor,'SPRITE_SHEET_JOB_ROOT',Path(current_directory_name)):
            current_result_record=execute_management_command('character-animation','sheet-gif',current_request_record)
            with Image.open(BytesIO(base64.b64decode(current_result_record['gif']))) as current_gif_image:
                self.assertEqual(current_gif_image.n_frames,2)
                self.assertEqual(current_gif_image.info['duration'],250)
                current_gif_image.seek(0);self.assertEqual(current_gif_image.convert('RGB').getpixel((2,2)),(255,0,0))
                current_gif_image.seek(1);self.assertEqual(current_gif_image.convert('RGB').getpixel((2,2)),(0,0,255))
            current_request_record['fps']=0
            with self.assertRaises(ValueError):execute_management_command('character-animation','sheet-gif',current_request_record)

    def test_unregistered_import_distributes_remainder_pixels(self):
        from tools.review.ui.gradio.sprite_sheet_editor_app import load_sprite_sheet_input
        with TemporaryDirectory() as current_temp_directory:
            current_image_path=Path(current_temp_directory)/'sheet.png'
            Image.new('RGB',(17,13),'white').save(current_image_path)
            current_loaded_values=load_sprite_sheet_input(str(current_image_path),4,3,{})
            current_frame_rows=current_loaded_values[1]
            self.assertEqual(len(current_frame_rows),12)
            current_covered_pixels=set()
            for current_left_value,current_top_value,current_width_value,current_height_value,*_ in current_frame_rows:
                for current_vertical_value in range(current_top_value,current_top_value+current_height_value):
                    for current_horizontal_value in range(current_left_value,current_left_value+current_width_value):
                        self.assertNotIn((current_horizontal_value,current_vertical_value),current_covered_pixels)
                        current_covered_pixels.add((current_horizontal_value,current_vertical_value))
            self.assertEqual(len(current_covered_pixels),17*13)
            self.assertLessEqual(max(row[2] for row in current_frame_rows)-min(row[2] for row in current_frame_rows),1)
            self.assertLessEqual(max(row[3] for row in current_frame_rows)-min(row[3] for row in current_frame_rows),1)

    def test_export_aligns_crops_and_preserves_source(self):
        current_source_image=Image.new('RGBA',(8,4))
        current_source_image.putpixel((1,1),(255,0,0,255))
        current_source_image.putpixel((6,2),(0,255,0,255))
        current_source_stream=BytesIO();current_source_image.save(current_source_stream,format='PNG')
        current_image_bytes=current_source_stream.getvalue()
        current_payload={'image':base64.b64encode(current_image_bytes).decode(),'frames':[{'x':0,'y':0,'width':4,'height':4,'anchorX':1,'anchorY':1},{'x':4,'y':0,'width':3,'height':3,'anchorX':2.25,'anchorY':2.75}],'columns':2}
        self.assertEqual(resolve_management_command('character-animation','sheet-export',current_payload),('POST','/character-animation/sheet/export'))
        with TemporaryDirectory() as current_directory_name, patch.object(sprite_sheet_editor,'SPRITE_SHEET_JOB_ROOT',Path(current_directory_name)):
            current_result=execute_management_command('character-animation','sheet-export',current_payload)
            current_job_path=Path(current_directory_name)/current_result['id'][:19]/current_result['id']
            self.assertEqual((current_job_path/'source.png').read_bytes(),current_image_bytes)
            current_output_image=Image.open(BytesIO(base64.b64decode(current_result['image'])))
            self.assertEqual(current_output_image.size,(7,4))
            self.assertEqual(current_output_image.getpixel((1,1)),(255,0,0,255))
            self.assertEqual(current_output_image.getpixel((6,2)),(0,255,0,255))
            self.assertEqual(current_result['coordinates']['frames'][1]['anchor'],{'x':2.25,'y':2.75})
            self.assertEqual(current_result['coordinates']['frames'][1]['rect'],{'x':4,'y':0,'width':3,'height':3})
            self.assertTrue((current_job_path/'coordinates.json').is_file())
            current_payload['frames'][0]['anchorX']=5
            with self.assertRaises(ValueError):execute_management_command('character-animation','sheet-export',current_payload)
            self.assertEqual(len(list(Path(current_directory_name).glob('*/*'))),1)

    def test_expanded_frames_pad_transparently_without_neighbor_pixels(self):
        current_source_image=Image.new('RGBA',(8,4),(0,255,0,255))
        current_source_image.paste((255,0,0,255),(0,0,4,4))
        current_image_stream=BytesIO()
        current_source_image.save(current_image_stream,format='PNG')
        current_request_record={'image':base64.b64encode(current_image_stream.getvalue()).decode(),'frames':[{'x':-2,'y':-1,'width':8,'height':6,'anchorX':4,'anchorY':4}],'columns':1,'sourceFrames':[[0,0,4,4]]}
        with TemporaryDirectory() as current_directory_name, patch.object(sprite_sheet_editor,'SPRITE_SHEET_JOB_ROOT',Path(current_directory_name)):
            current_result_record=execute_management_command('character-animation','sheet-export',current_request_record)
            with Image.open(BytesIO(base64.b64decode(current_result_record['image']))) as current_output_image:
                self.assertEqual(current_output_image.size,(8,6))
                self.assertEqual(current_output_image.getpixel((0,0)),(0,0,0,0))
                self.assertEqual(current_output_image.getpixel((2,1)),(255,0,0,255))
                self.assertEqual(current_output_image.getpixel((6,1)),(0,0,0,0))
            current_request_record['sourceFrames']=[[0,0,9,4]]
            with self.assertRaises(ValueError):
                execute_management_command('character-animation','sheet-export',current_request_record)

    def test_registered_update_preserves_clips_and_rejects_stale_input(self):
        import json
        import hashlib
        import yaml
        import os
        from tools.review.common.map_tile_assets import load_registered_tiles
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_asset_root=current_root_path/'slime-assets';current_frontend_root=current_root_path/'slime-frontend'
            current_sprite_directory=current_asset_root/'assets/characters/default/animations/test'
            current_sprite_directory.mkdir(parents=True);current_frontend_root.mkdir()
            current_image_path=current_sprite_directory/'sheet.png'
            Image.new('RGBA',(4,4),(10,20,30,255)).save(current_image_path)
            current_metadata_path=current_sprite_directory/'sheet.animation.json'
            current_metadata_record={'version':'v1','sheet':{'width':4,'height':4},'frames':[{'frameId':'idle.0','rect':{'x':0,'y':0,'width':4,'height':4},'anchor':{'x':1,'y':1}}],'clips':[{'clipId':'idle','frames':['idle.0']}]}
            current_metadata_path.write_text(json.dumps(current_metadata_record))
            current_records=[{'managementId':current_file_path.name,'version':'v1','path':current_file_path.relative_to(current_asset_root).as_posix(),'sha256':hashlib.sha256(current_file_path.read_bytes()).hexdigest(),'source':{}} for current_file_path in (current_image_path,current_metadata_path)]
            (current_asset_root/'asset-registry.yaml').write_text(yaml.safe_dump({'schema_version':1,'assets':current_records}))
            (current_frontend_root/'sprite-assets.lock.yaml').write_text(yaml.safe_dump({'files':[{'path':current_record['path'],'source_path':current_record['path'],'sha256':current_record['sha256']} for current_record in current_records]}))
            current_payload={'image':base64.b64encode(current_image_path.read_bytes()).decode(),'frames':[{'x':1,'y':1,'width':2,'height':2,'anchorX':0,'anchorY':0}],'columns':1}
            current_request={'path':current_records[0]['path'],'metadataSha256':current_records[1]['sha256'],'payload':current_payload,'confirm':True}
            with patch.dict(os.environ,{'SLIME_ASSETS_ROOT':str(current_asset_root)}),patch.object(sprite_sheet_editor,'SPRITE_SHEET_JOB_ROOT',current_root_path/'jobs'):
                execute_management_command('character-animation','sheet-update',current_request)
                current_updated_metadata=json.loads(current_metadata_path.read_text())
                self.assertEqual(current_updated_metadata['clips'],current_metadata_record['clips'])
                self.assertEqual(current_updated_metadata['frames'][0]['frameId'],'idle.0')
                self.assertEqual(current_updated_metadata['sheet'],{'width':2,'height':2})
                self.assertEqual(Image.open(current_image_path).size,(2,2))
                _,current_updated_registry=load_registered_tiles()
                current_lock_records=yaml.safe_load((current_frontend_root/'sprite-assets.lock.yaml').read_text())['files']
                for current_lock_record in current_lock_records:
                    self.assertEqual(current_lock_record['sha256'],current_updated_registry[current_lock_record['source_path']]['sha256'])
                with self.assertRaises(ValueError):execute_management_command('character-animation','sheet-update',current_request)

    def test_packed_update_preserves_other_texture_frames(self):
        import json
        import hashlib
        import yaml
        import os
        from tools.review.common.map_tile_assets import load_registered_tiles
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_asset_root=current_root_path/'slime-assets';current_frontend_root=current_root_path/'slime-frontend'
            current_sprite_directory=current_asset_root/'assets/characters/default/animations/test'
            current_sprite_directory.mkdir(parents=True);current_frontend_root.mkdir()
            current_image_path=current_sprite_directory/'sheet.png'
            Image.new('RGBA',(4,4),(10,20,30,255)).save(current_image_path)
            current_metadata_path=current_sprite_directory/'sheet.animation.json'
            current_metadata_record={'version':'v1','sheet':{'width':4,'height':4},'frames':[{'frameId':'idle.0','rect':{'x':0,'y':0,'width':4,'height':4},'anchor':{'x':1,'y':1}}],'clips':[{'clipId':'idle','frames':['idle.0']}]}
            current_other_image=current_sprite_directory/'other.png'
            Image.new('RGBA',(4,4),(40,50,60,255)).save(current_other_image)
            current_other_bytes=current_other_image.read_bytes()
            current_metadata_record.pop('sheet')
            current_metadata_record['sheets']=[{'image':'sheet.png','width':4,'height':4,'sha256':hashlib.sha256(current_image_path.read_bytes()).hexdigest()},{'image':'other.png','width':4,'height':4,'sha256':hashlib.sha256(current_other_bytes).hexdigest()}]
            current_metadata_record['frames'][0]['texture']='sheet.png'
            current_other_frame={'frameId':'other.0','texture':'other.png','rect':{'x':0,'y':0,'width':4,'height':4},'anchor':{'x':2,'y':3}}
            current_metadata_record['frames'].append(current_other_frame)
            current_metadata_record['clips']=[{'clipId':'idle','frames':[{'frameId':'idle.0'}]},{'clipId':'other','frames':[{'frameId':'other.0'}]}]
            current_metadata_path.write_text(json.dumps(current_metadata_record))
            current_records=[{'managementId':current_file_path.name,'version':'v1','path':current_file_path.relative_to(current_asset_root).as_posix(),'sha256':hashlib.sha256(current_file_path.read_bytes()).hexdigest(),'source':{}} for current_file_path in (current_image_path,current_metadata_path,current_other_image)]
            (current_asset_root/'asset-registry.yaml').write_text(yaml.safe_dump({'schema_version':1,'assets':current_records}))
            (current_frontend_root/'sprite-assets.lock.yaml').write_text(yaml.safe_dump({'files':[{'path':current_record['path'],'source_path':current_record['path'],'sha256':current_record['sha256']} for current_record in current_records]}))
            current_payload={'image':base64.b64encode(current_image_path.read_bytes()).decode(),'frames':[{'x':1,'y':1,'width':2,'height':2,'anchorX':0,'anchorY':0}],'columns':1}
            current_request={'path':current_records[0]['path'],'metadataSha256':current_records[1]['sha256'],'payload':current_payload,'confirm':True}
            with patch.dict(os.environ,{'SLIME_ASSETS_ROOT':str(current_asset_root)}),patch.object(sprite_sheet_editor,'SPRITE_SHEET_JOB_ROOT',current_root_path/'jobs'):
                execute_management_command('character-animation','sheet-update',current_request)
                current_updated_metadata=json.loads(current_metadata_path.read_text())
                self.assertEqual(current_updated_metadata['clips'],current_metadata_record['clips'])
                self.assertEqual(current_updated_metadata['frames'][0]['frameId'],'idle.0')
                self.assertNotIn('sheet',current_updated_metadata)
                self.assertEqual(current_updated_metadata['sheets'][0]['width'],2)
                self.assertEqual(current_updated_metadata['frames'][1],current_other_frame)
                self.assertEqual(current_other_image.read_bytes(),current_other_bytes)
                self.assertEqual(current_updated_metadata['sheets'][1],current_metadata_record['sheets'][1])
                self.assertEqual(Image.open(current_image_path).size,(2,2))
                _,current_updated_registry=load_registered_tiles()
                current_lock_records=yaml.safe_load((current_frontend_root/'sprite-assets.lock.yaml').read_text())['files']
                for current_lock_record in current_lock_records:
                    self.assertEqual(current_lock_record['sha256'],current_updated_registry[current_lock_record['source_path']]['sha256'])
                with self.assertRaises(ValueError):execute_management_command('character-animation','sheet-update',current_request)

    def test_yaml_source_update_preserves_runtime_dimensions(self):
        import json
        import hashlib
        import yaml
        import os
        from tools.review.common.map_tile_assets import load_registered_tiles
        with TemporaryDirectory() as current_directory_name:
            current_root_path=Path(current_directory_name)
            current_asset_root=current_root_path/'slime-assets';current_frontend_root=current_root_path/'slime-frontend'
            current_sprite_directory=current_asset_root/'assets/characters/default/animations/test'
            current_sprite_directory.mkdir(parents=True);current_frontend_root.mkdir()
            current_image_path=current_sprite_directory/'sheet.png'
            Image.new('RGBA',(4,4),(10,20,30,255)).save(current_image_path)
            current_metadata_path=current_sprite_directory/'sheet.animation.json'
            current_metadata_record={'version':'v1','sheet':{'width':4,'height':4},'frames':[{'frameId':'idle.0','rect':{'x':0,'y':0,'width':4,'height':4},'anchor':{'x':1,'y':1}}],'clips':[{'clipId':'idle','frames':['idle.0']}]}
            current_metadata_path.write_text(json.dumps(current_metadata_record))
            current_source_path=current_sprite_directory/'source.yaml'
            current_source_path.write_text(yaml.safe_dump({'image':'sheet.png','width':4,'height':4,'sha256':hashlib.sha256(current_image_path.read_bytes()).hexdigest(),'referenceBodyHeight':3.5,'gameBodyHeight':80}))
            current_records=[{'managementId':current_file_path.name,'version':'v1','path':current_file_path.relative_to(current_asset_root).as_posix(),'sha256':hashlib.sha256(current_file_path.read_bytes()).hexdigest(),'source':{}} for current_file_path in (current_image_path,current_metadata_path,current_source_path)]
            (current_asset_root/'asset-registry.yaml').write_text(yaml.safe_dump({'schema_version':1,'assets':current_records}))
            (current_frontend_root/'sprite-assets.lock.yaml').write_text(yaml.safe_dump({'files':[{'path':current_record['path'],'source_path':current_record['path'],'sha256':current_record['sha256']} for current_record in current_records]}))
            current_payload={'image':base64.b64encode(current_image_path.read_bytes()).decode(),'frames':[{'x':1,'y':1,'width':2,'height':2,'anchorX':0,'anchorY':0}],'columns':1}
            current_request={'path':current_records[0]['path'],'metadataSha256':current_records[1]['sha256'],'payload':current_payload,'confirm':True}
            with patch.dict(os.environ,{'SLIME_ASSETS_ROOT':str(current_asset_root)}),patch.object(sprite_sheet_editor,'SPRITE_SHEET_JOB_ROOT',current_root_path/'jobs'):
                execute_management_command('character-animation','sheet-update',current_request)
                current_updated_metadata=json.loads(current_metadata_path.read_text())
                self.assertEqual(current_updated_metadata['clips'],current_metadata_record['clips'])
                current_source_document=yaml.safe_load(current_source_path.read_text())
                self.assertEqual((current_source_document['width'],current_source_document['height']),(2,2))
                self.assertEqual(current_source_document['sha256'],hashlib.sha256(current_image_path.read_bytes()).hexdigest())
                current_loaded_image=execute_management_command('character-animation','sheet-image',{'path':current_records[0]['path']})
                self.assertEqual(current_loaded_image['runtimeDimensions'],{'referenceBodyHeight':3.5,'gameBodyHeight':80})

                self.assertEqual(current_updated_metadata['frames'][0]['frameId'],'idle.0')
                self.assertEqual(current_updated_metadata['sheet'],{'width':2,'height':2})
                self.assertEqual(Image.open(current_image_path).size,(2,2))
                _,current_updated_registry=load_registered_tiles()
                current_lock_records=yaml.safe_load((current_frontend_root/'sprite-assets.lock.yaml').read_text())['files']
                for current_lock_record in current_lock_records:
                    self.assertEqual(current_lock_record['sha256'],current_updated_registry[current_lock_record['source_path']]['sha256'])
                with self.assertRaises(ValueError):execute_management_command('character-animation','sheet-update',current_request)
