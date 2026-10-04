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
        return validate_seamless_request({'action':'generate','prompt':'낙엽','images':[],'steps':40,'seed':1,'width':1024,'height':1024})

    def create_legacy_pattern_request(self):
        current_request_record=self.create_pattern_request()
        current_request_record['seamless_tile'].update(schema_version=4,grid_size=768,repair_size=512,vertical_erasure=16,horizontal_erasure=16,feather_width=0)
        return current_request_record

    def test_stage_resume_and_integrity(self):
        current_request_record=self.create_legacy_pattern_request()
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
        self.assertEqual(current_request_record['seamless_tile']['schema_version'],6)
        self.assertEqual(current_request_record['seamless_tile']['stage_prompts'][0], '낙엽\nClose-up of the described subject, viewed from directly above. Softly shaded illustration.')
        self.assertEqual(current_request_record['seamless_tile']['grid_prompt'], 'Close-up of the described subject, viewed from directly above. Softly shaded illustration.')
        self.assertTrue(current_request_record['seamless_tile']['stage_prompts'][1].startswith('중앙의 흰 세로 띠'))
        self.assertTrue(all(current_word_count<100 for current_word_count in current_request_record['seamless_tile']['stage_prompt_words']))

    def test_cli_text_request_and_partial_preview(self):
        import contextlib
        import io
        from unittest.mock import patch
        from tools.review.common.management_gateway import execute_gateway_arguments
        from tools.review.domains.image.seamless_generation import SeamlessGenerationManager
        with patch('tools.review.common.management_gateway.call_management_api',return_value={'id':'test'}) as gateway_call_mock, contextlib.redirect_stdout(io.StringIO()):
            execute_gateway_arguments('seamless-tile',['generate','--prompt','낙엽','--detach'])
        self.assertEqual(validate_seamless_request(gateway_call_mock.call_args.args[2])['seamless_tile']['schema_version'],6)
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
            current_request_record=self.create_legacy_pattern_request()
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

    def test_retired_pipeline_rejected_before_generation(self):
        current_request_record = self.create_pattern_request()
        current_request_record['seamless_tile']['schema_version'] = 5
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            with self.assertRaisesRegex(ValueError,'폐기'):
                execute_pattern_pipeline(Path(temporary_directory_name),current_request_record,lambda *unused_callback_arguments:self.fail('폐기된 작업 실행'))

    def test_directional_pipeline_geometry_and_resume(self):
        from tools.review.domains.image.seamless_directional import DIRECTIONAL_STAGE_OUTPUTS
        from tools.review.domains.image.seamless_steps import read_seamless_stage_checkpoints
        current_request_record = self.create_pattern_request()
        generated_stage_names = []
        def generate_test_stage(current_stage_root, current_stage_request, current_reference_paths):
            generated_stage_names.append(current_stage_root.name)
            if current_reference_paths:
                self.assertEqual(len(current_reference_paths),1)
                with Image.open(current_reference_paths[0]) as erased_input_image:
                    self.assertEqual(erased_input_image.getpixel((erased_input_image.width//2,erased_input_image.height//2)),(255,255,255))
                    self.assertEqual(erased_input_image.getpixel((0,0)),(0,128,0))
                    if current_stage_root.name == 'stage-3-horizontal':
                        self.assertEqual(erased_input_image.size,(1023,1024))
                        self.assertEqual(erased_input_image.getpixel((511,0)),(255,255,255))
                        self.assertEqual(erased_input_image.getpixel((0,512)),(0,128,0))
                    else:
                        self.assertEqual(erased_input_image.size,(768,768))
                        self.assertEqual(erased_input_image.getpixel((0,384)),(255,255,255))
                        self.assertEqual(erased_input_image.getpixel((384,0)),(0,128,0))
            Image.new('RGB',(current_stage_request['width'],current_stage_request['height']),'green').save(current_stage_root/'result.png')
            (current_stage_root/'result.json').write_text('{}')
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_job_root = Path(temporary_directory_name)
            for stage_index_value in range(1,6):
                (current_job_root/'stage-pause.json').unlink(missing_ok=True)
                execute_pattern_pipeline(current_job_root,current_request_record,generate_test_stage)
                self.assertEqual(read_seamless_stage_checkpoints(current_job_root,current_request_record,DIRECTIONAL_STAGE_OUTPUTS)[0],stage_index_value)
                self.assertEqual((current_job_root/'stage-pause.json').exists(),stage_index_value<5)
            self.assertEqual(generated_stage_names,['stage-1-pattern','stage-3-horizontal','stage-5-vertical'])
            self.assertEqual(Image.open(current_job_root/'center-tile.png').size,(341,1024))
            self.assertEqual(Image.open(current_job_root/'split-preview.png').size,(768,256))
            self.assertEqual(Image.open(current_job_root/'result.png').size,(768,768))
            execute_pattern_pipeline(current_job_root,current_request_record,lambda *unused_callback_arguments:self.fail('완료 단계 재실행'))
            (current_job_root/'sample-grid.png').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'무결성'):
                execute_pattern_pipeline(current_job_root,current_request_record,generate_test_stage)
