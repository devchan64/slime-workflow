"""첨부 참조의 GUI·CLI·저장 계약을 GPU 실행 없이 검증한다."""
import base64
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import sys
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from PIL import Image
from tools.review.domains.character_animation import character_animation_assets as assets
from tools.review.domains.character_animation import character_animation_jobs as jobs
from tools.review.common import management_gateway as gateway
from tools.review.ui.gradio import character_animation_app as interface

class CharacterReferenceTests(unittest.TestCase):
    def create_reference_request(self):
        current_reference_image=Image.new('RGBA',(640,400),(70,90,110,128))
        return interface.build_animation_request('walking-v13',current_reference_image,'anny','down_left',1,3,512,4,8,2,'첨부 검증')

    def test_uploaded_request_ignores_retired_character_catalog(self):
        current_request_record=assets.prepare_animation_request(self.create_reference_request())
        self.assertEqual(current_request_record['selected_frame_numbers'],[1,3])
        self.assertIsNone(current_request_record['character_manifest_sha256'])
        self.assertEqual(current_request_record['frames'][0]['character_sha256'],assets.hashlib.sha256(base64.b64decode(current_request_record['character_image'])).hexdigest())

    def test_invalid_images_and_multiple_directions_rejected(self):
        current_request_record=self.create_reference_request()
        for current_invalid_fields in ({'character_image':'broken'}, {'character':'character-default'}, {'directions':['down_left','up_left']}):
            with self.assertRaises(ValueError):
                assets.prepare_animation_request({**current_request_record,**current_invalid_fields})

    def test_saved_reference_reuse_and_history_restore(self):
        with tempfile.TemporaryDirectory(dir=assets.WORKFLOW_ROOT_DIRECTORY/'.tmp') as current_temporary_directory:
            current_test_root=Path(current_temporary_directory)
            with patch.object(jobs,'GENERATION_ROOT_DIRECTORY',current_test_root),patch.object(jobs,'GENERATION_HISTORY_DIRECTORY',current_test_root/'history'),patch.object(jobs,'GENERATION_LOCK_PATH',current_test_root/'generation.lock'),patch.object(jobs.subprocess,'Popen') as current_worker_mock:
                current_request_record=self.create_reference_request()
                current_first_job=jobs.start_animation_generation(current_request_record)
                current_second_job=jobs.start_animation_generation(current_request_record)
                self.assertEqual(current_first_job['id'],current_second_job['id'])
                self.assertEqual(current_worker_mock.call_count,1)
                current_saved_request=json.loads((Path(current_first_job['path'])/'request.json').read_text())
                current_saved_reference=assets.WORKFLOW_ROOT_DIRECTORY/current_saved_request['frames'][0]['character_path']
                self.assertEqual(current_saved_reference.read_bytes(),base64.b64decode(current_request_record['character_image']))
                current_restored_inputs=interface.restore_animation_inputs({'request':current_saved_request})
                self.assertEqual(current_restored_inputs[1].size,(640,400))
                self.assertEqual(current_restored_inputs[3],'down_left')

    def test_worker_preserves_uploaded_aspect_and_composites_alpha(self):
        from generators.animation.run_character_animation import generate_character_frame
        current_request_record=assets.prepare_animation_request(self.create_reference_request())
        with tempfile.TemporaryDirectory(dir=assets.WORKFLOW_ROOT_DIRECTORY/'.tmp') as current_temporary_directory:
            current_job_path=Path(current_temporary_directory)
            current_reference_path=current_job_path/'character-reference.png'
            current_reference_path.write_bytes(base64.b64decode(current_request_record['character_image']))
            current_request_record['frames'][0]['character_path']=str(current_reference_path.relative_to(assets.WORKFLOW_ROOT_DIRECTORY))
            (current_job_path/'request.json').write_text(json.dumps(current_request_record))
            current_pose_mock=MagicMock()
            with patch.dict(sys.modules,{'qwen_pose':SimpleNamespace(execute_pose_generation=current_pose_mock)}):
                generate_character_frame(current_job_path,0)
            with Image.open(current_pose_mock.call_args.kwargs['character_image_path']) as current_normalized_image:
                self.assertEqual(current_normalized_image.size,(512,512))
                self.assertEqual(current_normalized_image.mode,'RGB')
                self.assertEqual(current_normalized_image.getpixel((256,95)),(255,255,255))
                self.assertNotEqual(current_normalized_image.getpixel((256,96)),(255,255,255))
                self.assertNotEqual(current_normalized_image.getpixel((256,415)),(255,255,255))
                self.assertEqual(current_normalized_image.getpixel((256,416)),(255,255,255))

    def test_cli_reference_payload_matches_gui(self):
        current_request_record=self.create_reference_request()
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_reference_path=Path(current_temporary_directory)/'reference.png'
            current_reference_path.write_bytes(base64.b64decode(current_request_record['character_image']))
            with patch.object(gateway,'execute_management_command',return_value={'id':'test'}) as current_gateway_mock,contextlib.redirect_stdout(io.StringIO()):
                gateway.execute_gateway_cli(['command','character-animation','generate','--motion','walking-v13','--reference',str(current_reference_path),'--directions','down_left','--detach'])
            current_cli_payload=current_gateway_mock.call_args.args[2]
            self.assertEqual(current_cli_payload['character_image'],current_request_record['character_image'])
            self.assertEqual(current_cli_payload['directions'],['down_left'])
            self.assertNotIn('character',current_cli_payload)

    def test_interface_has_upload_and_radio_without_character_selector(self):
        current_catalog_record=assets.build_animation_catalog()
        with patch.object(interface,'read_animation_catalog',return_value=current_catalog_record):
            current_interface_blocks=interface.build_character_animation_interface('http://127.0.0.1:8770')
        current_component_records=current_interface_blocks.get_config_file()['components']
        current_direction_control=next(value for value in current_component_records if value['props'].get('label')=='생성 방향')
        self.assertEqual(current_direction_control['type'],'radio')
        self.assertEqual(current_direction_control['props']['value'],'down_left')
        current_image_control=next(value for value in current_component_records if value['props'].get('label')=='캐릭터 참조')
        self.assertEqual(current_image_control['props']['sources'],['upload','clipboard'])
        self.assertFalse(any(value['props'].get('label')=='캐릭터' for value in current_component_records))
