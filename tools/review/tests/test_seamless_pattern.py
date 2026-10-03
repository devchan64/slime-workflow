"""패턴 단계 실행·재개·입력 계약 검증."""
import tempfile
import json
import unittest
from pathlib import Path
from PIL import Image
from tools.review.domains.image.seamless_generation import validate_seamless_request
from tools.review.domains.image.seamless_pattern import execute_pattern_pipeline

class SeamlessPatternTests(unittest.TestCase):
    def create_pattern_request(self):
        return validate_seamless_request({'action':'generate','prompt':'낙엽','images':[],'steps':40,'seed':1,'width':768,'height':768})

    def test_stage_resume_and_integrity(self):
        current_request_record=self.create_pattern_request()
        executed_stage_names=[]
        def generate_test_stage(current_stage_root,current_stage_request,current_reference_paths):
            executed_stage_names.append(current_stage_root.name)
            if current_stage_root.name=='stage-2-repair':
                self.assertEqual(len(current_reference_paths),2)
                self.assertEqual(Image.open(current_reference_paths[0]).getpixel((255,10)),(0,128,0))
                self.assertEqual(Image.open(current_reference_paths[1]).getpixel((255,10)),(255,255,255))
                self.assertEqual(Image.open(current_reference_paths[1]).getpixel((10,10)),(0,0,0))
                if len(executed_stage_names)==2:
                    raise RuntimeError('2단계 실패 재현')
            Image.new('RGB',(current_stage_request['width'],current_stage_request['height']),'green').save(current_stage_root/'result.png')
            (current_stage_root/'result.json').write_text('{}')
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_job_root=Path(temporary_directory_name)
            with self.assertRaises(RuntimeError):
                execute_pattern_pipeline(current_job_root,current_request_record,generate_test_stage)
            execute_pattern_pipeline(current_job_root,current_request_record,generate_test_stage)
            self.assertEqual(executed_stage_names,['stage-1-pattern','stage-2-repair','stage-2-repair'])
            self.assertEqual(Image.open(current_job_root/'result.png').size,(256,256))
            self.assertEqual(Image.open(current_job_root/'tiled-preview.png').size,(768,768))
            (current_job_root/'stage-1-pattern/result.png').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'무결성'):
                execute_pattern_pipeline(current_job_root,current_request_record,generate_test_stage)

    def test_text_prompt_contract(self):
        current_request_record=self.create_pattern_request()
        self.assertEqual(current_request_record['seamless_tile']['schema_version'],4)
        self.assertTrue(current_request_record['seamless_tile']['stage_prompts'][0].startswith('낙엽.'))
        self.assertTrue(current_request_record['seamless_tile']['stage_prompts'][1].startswith('Image 2'))
        self.assertTrue(all(current_word_count<100 for current_word_count in current_request_record['seamless_tile']['stage_prompt_words']))

    def test_cli_text_request_and_partial_preview(self):
        import contextlib
        import io
        from unittest.mock import patch
        from tools.review.common.management_gateway import execute_gateway_arguments
        from tools.review.domains.image.seamless_generation import SeamlessGenerationManager
        with patch('tools.review.common.management_gateway.call_management_api',return_value={'id':'test'}) as gateway_call_mock, contextlib.redirect_stdout(io.StringIO()):
            execute_gateway_arguments('seamless-tile',['generate','--prompt','낙엽','--detach'])
        self.assertEqual(validate_seamless_request(gateway_call_mock.call_args.args[2])['seamless_tile']['schema_version'],4)
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_job_root=Path(temporary_directory_name)
            (current_job_root/'grid-input.png').touch()
            (current_job_root/'pipeline-progress.json').write_text('{"stage":"stage-2-repair","index":2,"total":2}')
            current_status_record=SeamlessGenerationManager().enrich_generation_status(current_job_root,{'status':'running'})
            self.assertEqual(current_status_record['pipeline']['index'],2)
            self.assertIn('grid-input.png',current_status_record['previews'])
            self.assertNotIn('tiled-preview.png',current_status_record['previews'])

    def test_mask_composite_preserves_outside_pixels_and_legacy_resume(self):
        for schema_version_number in (3,4):
            current_request_record=self.create_pattern_request()
            if schema_version_number==3:
                current_request_record['seamless_tile'].update(schema_version=3,vertical_erasure=32,horizontal_erasure=32,feather_width=16)
            def generate_test_stage(current_stage_root,current_stage_request,current_reference_paths):
                if current_stage_root.name=='stage-2-repair':
                    self.assertEqual(len(current_reference_paths),2 if schema_version_number==4 else 1)
                Image.new('RGB',(current_stage_request['width'],current_stage_request['height']),'red' if current_reference_paths else 'green').save(current_stage_root/'result.png')
                (current_stage_root/'result.json').write_text('{}')
            with tempfile.TemporaryDirectory() as temporary_directory_name:
                current_job_root=Path(temporary_directory_name)
                execute_pattern_pipeline(current_job_root,current_request_record,generate_test_stage)
                with Image.open(current_job_root/'repair-composite.png') as composite_result_image:
                    self.assertEqual(composite_result_image.getpixel((10,10)),(0,128,0))
                    self.assertEqual(composite_result_image.getpixel((255,10)),(255,0,0))
                    if schema_version_number==4:
                        import numpy as np
                        original_pixel_values=np.asarray(Image.open(current_job_root/'repair-input.png'))
                        mask_pixel_values=np.asarray(Image.open(current_job_root/'repair-mask.png').convert('L'))>0
                        self.assertTrue(np.array_equal(np.asarray(composite_result_image)[~mask_pixel_values],original_pixel_values[~mask_pixel_values]))
                execute_pattern_pipeline(current_job_root,current_request_record,lambda *unused_callback_arguments:self.fail('완료 단계 재실행'))
