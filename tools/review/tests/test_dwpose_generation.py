"""단일 DWPose 입력과 공용 UI·CLI 계약 검증."""
import base64
import io
import unittest
from PIL import Image
from generators.dwpose.contracts import validate_dwpose_request
from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, MANAGEMENT_SERVICE_ROUTES
from tools.review.ui.gradio.dwpose_app import build_dwpose_interface


class DwposeGenerationTests(unittest.TestCase):
    def make_image_request(self, current_image_size=(832,480)):
        current_image_buffer = io.BytesIO()
        Image.new('RGB',current_image_size,'white').save(current_image_buffer,format='PNG')
        return {'action':'generate','images':[base64.b64encode(current_image_buffer.getvalue()).decode()]}

    def test_request_validation_contract(self):
        self.assertEqual(validate_dwpose_request(self.make_image_request())['frames'],1)
        for current_invalid_request in (self.make_image_request((480,480)), {**self.make_image_request(),'images':[]}, {**self.make_image_request(),'pose_include_face':1}, {**self.make_image_request(),'unknown':True}):
            with self.assertRaises(ValueError):
                validate_dwpose_request(current_invalid_request)

    def test_gateway_and_ui_contract(self):
        self.assertEqual(MANAGEMENT_SERVICE_ROUTES['dwpose'],'/dwpose')
        self.assertIn('generate',MANAGEMENT_SERVICE_COMMANDS['dwpose'])
        current_mock_calls = []
        current_interface_blocks = build_dwpose_interface('http://127.0.0.1:8770',lambda *current_command_args: current_mock_calls.append(current_command_args))
        self.assertTrue(current_interface_blocks.config['components'])
        self.assertEqual(current_mock_calls,[])


if __name__ == '__main__':
    unittest.main()
