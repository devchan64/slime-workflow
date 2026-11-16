"""용도별 FLUX 입력, 페이지와 이력 복원 계약."""
import base64
import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from tools.review.domains.image.flux_image_generation import FLUX_IMAGE_PROFILE_RECORDS, FluxImageGenerationManager
from tools.review.domains.image.three_reference_generation import save_three_reference_inputs
from tools.review.ui.shared.flux_image_page import restore_flux_image_inputs
from tools.review.common.management_gateway import resolve_management_command


class FluxImageGenerationTests(unittest.TestCase):
    def test_seamless_method_defaults_and_validation(self):
        current_manager_value=FluxImageGenerationManager('flux-seamless')
        current_request_record={'action':'generate','prompt':'grass','images':[],'width':512,'height':512,'steps':16,'seed':42}
        self.assertEqual(current_manager_value.validate_generation_request(current_request_record)['seamless_method'],'circular-vae')
        self.assertEqual(current_manager_value.validate_generation_request({**current_request_record,'seamless_method':'edge-blend'})['seamless_method'],'edge-blend')
        with self.assertRaises(ValueError): current_manager_value.validate_generation_request({**current_request_record,'seamless_method':'unknown'})
        with self.assertRaises(ValueError): FluxImageGenerationManager('flux-image').validate_generation_request({**current_request_record,'seamless_method':'circular-vae'})

    def test_circular_preview_and_old_restore_method(self):
        from tools.review.ui.shared.flux_image_page import render_flux_seamless_comparison
        current_job_identifier='2026-11-16_18-54-49-49a54a00'
        current_result_path='/flux-seamless-generator/jobs/'+current_job_identifier+'/result.png'
        current_markup_value=render_flux_seamless_comparison(current_job_identifier,{'image':current_result_path,'seamless_method':'circular-vae'},'http://127.0.0.1:8770')
        self.assertIn('순환 VAE 타일',current_markup_value)
        self.assertIn('/blend-preview.png',current_markup_value)
        current_old_markup=render_flux_seamless_comparison(current_job_identifier,{'image':current_result_path},'http://127.0.0.1:8770')
        self.assertIn('경계 보간 타일',current_old_markup)
        self.assertNotIn('/blend-preview.png',current_old_markup)

    def test_seamless_preview_uses_same_origin_and_checks_job(self):
        from tools.review.ui.shared.flux_image_page import render_flux_seamless_comparison
        current_job_identifier='2026-11-16_18-54-49-49a54a00'
        current_result_path='/flux-seamless-generator/jobs/'+current_job_identifier+'/result.png'
        current_markup_value=render_flux_seamless_comparison(current_job_identifier,{'image':current_result_path},'http://127.0.0.1:8770')
        for current_image_name in ('raw-result.png','result.png','tiled-preview.png'):
            self.assertIn('src="/flux-seamless-generator/jobs/'+current_job_identifier+'/'+current_image_name+'"',current_markup_value)
        self.assertNotIn('127.0.0.1',current_markup_value)
        self.assertIn('일치하지',render_flux_seamless_comparison(current_job_identifier,{'image':'/other/result.png'},'http://127.0.0.1:8770'))
    def test_transparent_reference_is_composited_on_white(self):
        current_image_buffer=io.BytesIO(); Image.new('RGBA',(16,16),(0,0,0,0)).save(current_image_buffer,format='PNG')
        current_request_record=FluxImageGenerationManager('flux-mannequin').validate_generation_request({'action':'generate','prompt':'A figure','images':[base64.b64encode(current_image_buffer.getvalue()).decode()],'width':768,'height':1152,'steps':16,'seed':42})
        with Image.open(io.BytesIO(base64.b64decode(current_request_record['images'][0]))) as current_image_value:
            self.assertEqual(current_image_value.convert('RGB').getpixel((0,0)),(255,255,255))
    def test_seamless_boundary_and_preview(self):
        import numpy as np
        from tools.review.domains.image.flux_seamless_output import blend_opposite_tile_edges, build_repeated_tile_preview
        current_random_pixels=np.random.default_rng(42).integers(0,256,size=(64,64,3),dtype=np.uint8)
        current_result_image=blend_opposite_tile_edges(Image.fromarray(current_random_pixels))
        current_result_pixels=np.asarray(current_result_image)
        self.assertTrue(np.array_equal(current_result_pixels[0],current_result_pixels[-1]))
        self.assertTrue(np.array_equal(current_result_pixels[:,0],current_result_pixels[:,-1]))
        self.assertEqual(build_repeated_tile_preview(current_result_image).size,(192,192))

    def test_gpu_memory_identity_includes_image_settings(self):
        import json
        from tools.review.common.gpu_memory_history import identify_execution_command
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_root=Path(current_directory_name)
            (current_job_root/'request.json').write_text(json.dumps({'action':'generate','width':768,'height':1152,'steps':16,'references':['reference-1.png','reference-2.png']}))
            current_identity_text=identify_execution_command(['python','generators/image/run_flux_image.py'],current_job_root)
            self.assertIn('768x1152:steps=16:references=2',current_identity_text)
            self.assertIn('offload=model-v1',current_identity_text)
    def test_profile_requests_and_pages(self):
        from tools.review.common.management_asgi import build_management_blocks
        current_image_buffer=io.BytesIO(); Image.new('RGB',(16,16),'white').save(current_image_buffer,format='PNG')
        current_image_text=base64.b64encode(current_image_buffer.getvalue()).decode()
        for current_profile_name,current_profile_record in FLUX_IMAGE_PROFILE_RECORDS.items():
            with self.subTest(profile=current_profile_name):
                current_manager_value=FluxImageGenerationManager(current_profile_name)
                current_request_record=current_manager_value.validate_generation_request({'action':'generate','prompt':'A small tree','images':[current_image_text] if current_profile_record[4] else [],'width':768,'height':768,'steps':16,'seed':42})
                self.assertEqual(current_request_record['profile'],current_profile_name)
                self.assertEqual(current_request_record['common_style']['version'],'1.5.0')
                self.assertEqual(resolve_management_command(current_profile_name,'history',{})[1],'/'+current_profile_name+'-generator/history')
                from unittest.mock import patch
                with tempfile.TemporaryDirectory() as current_directory_name:
                    current_source_path=Path(current_directory_name)/'menu.json'; current_source_path.write_text('{"pages": []}')
                    with patch.dict('os.environ',{'SLIME_MANAGEMENT_MENU_SOURCE':str(current_source_path)}):
                        current_page_blocks,_=build_management_blocks(current_profile_name+'-generator',8770,current_source_path)
                self.assertGreater(len(current_page_blocks.blocks),0)
                if current_profile_record[4]:
                    with self.assertRaises(ValueError):
                        current_manager_value.validate_generation_request({'action':'generate','prompt':'A tree','images':[],'width':768,'height':768,'steps':16,'seed':42})

    def test_restore_saved_reference_and_prompt(self):
        current_image_buffer=io.BytesIO(); Image.new('RGB',(16,16),'blue').save(current_image_buffer,format='PNG')
        current_profile_name='flux-image'; current_manager_value=FluxImageGenerationManager(current_profile_name)
        current_request_record=current_manager_value.validate_generation_request({'action':'generate','prompt':'A tree','images':[base64.b64encode(current_image_buffer.getvalue()).decode()],'width':768,'height':512,'steps':16,'seed':42})
        with tempfile.TemporaryDirectory(dir=Path('.tmp/test')) as current_directory_name:
            current_job_identifier='2026-11-16_18-23-00-f1a2b3c4'; current_job_root=Path(current_directory_name)/'.tmp/test/flux-image-generator'/current_job_identifier; current_job_root.mkdir(parents=True)
            current_saved_record=save_three_reference_inputs(current_job_root,current_request_record)
            from unittest.mock import patch
            with patch('tools.review.ui.shared.flux_image_page.WORKFLOW_ROOT_DIRECTORY',Path(current_directory_name).resolve()):
                current_restored_values=restore_flux_image_inputs({'id':current_job_identifier,'request':current_saved_record},current_profile_name)
                self.assertEqual(current_restored_values[0],'A tree')
                self.assertEqual(current_restored_values[1].size,(16,16))
                self.assertIsNone(current_restored_values[2])
                self.assertEqual(current_restored_values[3:],(768,512,42,''))
                (current_job_root/'reference-1.png').write_bytes(b'changed')
                with self.assertRaises(Exception):
                    restore_flux_image_inputs({'id':current_job_identifier,'request':current_saved_record},current_profile_name)
