import base64
import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from tools.review.domains.image.three_reference_generation import ALLOWED_REFERENCE_JOB_ROOTS, validate_three_reference_job_path, validate_three_reference_request, save_three_reference_inputs, resolve_reference_settings, verify_reference_snapshots
from tools.review.domains.image.image_generation import ImageGenerationManager
from tools.review.tests.test_image_generation import ImageGenerationTests


class ThreeReferenceGenerationTests(unittest.TestCase):
    def encode_reference_fixture(self, selected_image_color, selected_image_size=(512,512), selected_image_format='PNG'):
        current_image_buffer=io.BytesIO()
        Image.new('RGBA',selected_image_size,selected_image_color).save(current_image_buffer,format=selected_image_format)
        return base64.b64encode(current_image_buffer.getvalue()).decode()

    def test_snapshot_detects_changed_reference_before_generation(self):
        request={'action':'generate','steps':4,'width':512,'height':512,'prompt':'wall','images':[self.encode_reference_fixture('red')]}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            saved=save_three_reference_inputs(root,request)
            verify_reference_snapshots(root,saved)
            (root/'reference-1.png').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'무결성'):
                verify_reference_snapshots(root,saved)

    def test_reference_validation_and_order(self):
        current_image_values=[self.encode_reference_fixture(current_image_color) for current_image_color in ('red','green','blue')]
        current_request_record={'action':'generate','steps':30,'width':512,'height':512,'prompt':'참조 순서 유지','images':current_image_values}
        validate_three_reference_request(current_request_record)
        validate_three_reference_request({**current_request_record,'images':current_image_values[:1]})
        validate_three_reference_request({**current_request_record,'images':current_image_values[:2]})
        validate_three_reference_request({**current_request_record,'images':[]})
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_output_record=save_three_reference_inputs(Path(current_directory_name),current_request_record)
            for current_image_index,current_image_text in enumerate(current_image_values,1):
                self.assertEqual((Path(current_directory_name)/f'reference-{current_image_index}.png').read_bytes(),base64.b64decode(current_image_text))
            self.assertEqual(current_output_record['references'],['reference-1.png','reference-2.png','reference-3.png'])
            self.assertNotIn('images',current_output_record)
        for current_invalid_images in (current_image_values*2,['invalid']*3,[self.encode_reference_fixture((0,0,0,0))]*3,[self.encode_reference_fixture('red',(256,512))]*3,[self.encode_reference_fixture('red',selected_image_format='WEBP')]*3):
            with self.assertRaises(ValueError):
                validate_three_reference_request({**current_request_record,'images':current_invalid_images})
        with self.assertRaises(ValueError):
            validate_three_reference_request({**current_request_record,'model':'other'})

    def test_generation_mode_contract(self):
        for selected_step_count in (4,30):
            current_runtime_settings=resolve_reference_settings(selected_step_count)
            self.assertEqual(current_runtime_settings['selected_inference_steps'],selected_step_count)
            self.assertEqual(current_runtime_settings['enable_standalone_lightning_adapter'],selected_step_count==4)
            self.assertFalse(current_runtime_settings['enable_anypose_adapter'])
        for current_invalid_steps in (True,4.0,'4',20,None):
            with self.assertRaises(ValueError):
                resolve_reference_settings(current_invalid_steps)

    def test_tile_reference_job_path_is_allowed(self):
        for allowed_job_root in ALLOWED_REFERENCE_JOB_ROOTS:
            self.assertEqual(validate_three_reference_job_path(allowed_job_root/'2026-09-26_18-43-54-6b5f63d6'),(allowed_job_root/'2026-09-26_18-43-54-6b5f63d6').resolve())
        with self.assertRaises(ValueError):
            validate_three_reference_job_path(Path('/tmp/invalid-reference-job'))

    def test_route_prefix_isolation(self):
        current_http_handler=ImageGenerationTests().make_http_handler('/image-generation-2511/')
        self.assertFalse(ImageGenerationManager().handle_image_request(current_http_handler))
        self.assertTrue(ImageGenerationManager(three_reference_mode=True).handle_image_request(current_http_handler))
        self.assertEqual(current_http_handler.status,410)


if __name__=='__main__':
    unittest.main()
