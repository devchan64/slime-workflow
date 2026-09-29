"""생성 원본·보더 크롭 동시 저장 및 실패 시 원본 보존 검증."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from tools.review.domains.tile.tile_results import save_tile_border_result
from tools.review.domains.tile.tile_generation import TileGenerationManager, prepare_tile_request


class TileResultStorageTests(unittest.TestCase):
    def create_generation_files(self, current_job_root, *, with_black_frame=True):
        original_image_value=Image.new('RGB',(128,128),'white')
        if with_black_frame:
            original_image_draw=ImageDraw.Draw(original_image_value)
            original_image_draw.rectangle((8,8,119,119),fill='black')
            original_image_draw.rectangle((16,20,111,107),fill=(80,160,40))
        original_image_value.save(current_job_root/'result.png')
        (current_job_root/'result.json').write_text(json.dumps({'status':'completed','output':'result.png','elapsed_seconds':1}))
        (current_job_root/'status.json').write_text('{"status":"completed"}')
        (current_job_root/'request.json').write_text('{"action":"generate"}')

    def test_saves_both_images_and_measurements_without_modifying_original(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_job_root=Path(temporary_directory_name)
            self.create_generation_files(current_job_root)
            original_image_bytes=(current_job_root/'result.png').read_bytes()
            save_tile_border_result(current_job_root,{'border_crop':{'ratio':0.01}})
            self.assertEqual((current_job_root/'result.png').read_bytes(),original_image_bytes)
            result_record_value=json.loads((current_job_root/'result.json').read_text())
            self.assertEqual(result_record_value['output'],'result.png')
            self.assertEqual(result_record_value['outputs'],{'original':'result.png','border_crop':'border-crop.png'})
            self.assertEqual(result_record_value['border_crop']['border_pixels'],[1,1])
            self.assertEqual(result_record_value['border_crop']['source_sha256'],hashlib.sha256(original_image_bytes).hexdigest())
            with Image.open(current_job_root/'border-crop.png') as cropped_image_value:
                self.assertEqual(cropped_image_value.size,(98,90))
            self.assertEqual(json.loads((current_job_root/'border-crop.json').read_text()),result_record_value['border_crop'])

    def test_missing_frame_fails_but_preserves_original(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_job_root=Path(temporary_directory_name)
            self.create_generation_files(current_job_root,with_black_frame=False)
            original_image_bytes=(current_job_root/'result.png').read_bytes()
            with self.assertLogs(level='ERROR'), self.assertRaisesRegex(ValueError,'검출 근거 부족'):
                save_tile_border_result(current_job_root,{'border_crop':{'ratio':0.01}})
            self.assertEqual((current_job_root/'result.png').read_bytes(),original_image_bytes)
            self.assertFalse((current_job_root/'border-crop.png').exists())
            self.assertEqual(json.loads((current_job_root/'border-crop.json').read_text())['status'],'failed')

    def test_other_generators_and_legacy_requests_do_not_crop(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_job_root=Path(temporary_directory_name)
            save_tile_border_result(current_job_root,{'action':'generate'})
            self.assertEqual(list(current_job_root.iterdir()),[])

    def test_request_policy_and_history_status_share_crop_url(self):
        prepared_request_value=prepare_tile_request({'action':'generate','user_prompt':'잔디','width':512,'height':512,'steps':4})
        self.assertEqual(prepared_request_value['border_crop'],{'ratio':0.01})
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            storage_root_path=Path(temporary_directory_name)
            current_job_root=storage_root_path/'2026-09-29_12-00-00-abcdef12'
            current_job_root.mkdir()
            self.create_generation_files(current_job_root)
            save_tile_border_result(current_job_root,prepared_request_value)
            tile_manager_value=TileGenerationManager()
            with patch.object(tile_manager_value,'job_storage_root',storage_root_path),patch.object(tile_manager_value,'history_storage_path',return_value=storage_root_path/'history'):
                history_record_values=tile_manager_value.list_generation_history()
            status_record_value=tile_manager_value.enrich_generation_status(current_job_root,{'status':'completed'})
            self.assertEqual(history_record_values[0]['cropped_image'],status_record_value['cropped_image'])
            self.assertTrue(status_record_value['cropped_image'].endswith('/border-crop.png'))
