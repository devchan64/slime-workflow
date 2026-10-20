"""전체 맵 캡처의 입력·이미지·게이트웨이 계약을 검증한다."""
import base64
import io
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from tools.review.domains.map_review.capture import validate_map_capture_settings, save_map_capture_result
from tools.review.common.management_gateway import resolve_management_command, identify_management_command

class MapReviewCaptureTest(unittest.TestCase):
    def test_map_gateway_roundtrip(self):
        current_payload_value=validate_map_capture_settings({'map':'ash-edge'})
        current_method_name,current_route_path=resolve_management_command('map-review','capture',current_payload_value)
        self.assertEqual(identify_management_command(current_route_path,current_method_name,current_payload_value),('map-review','capture',current_payload_value))

    def test_invalid_map_settings(self):
        for current_payload_value in ({},{'map':'../bad'},{'map':'ash-edge','width':80},{'map':'ash-edge','edges':1}):
            with self.assertRaises(ValueError):validate_map_capture_settings(current_payload_value)

    def test_map_png_validation(self):
        with tempfile.TemporaryDirectory() as current_directory_name:
            for current_alpha_value in (0,255):
                current_image_buffer=io.BytesIO()
                Image.new('RGBA',(80,40),(1,2,3,current_alpha_value)).save(current_image_buffer,format='PNG')
                current_result_payload={'map':'data:image/png;base64,'+base64.b64encode(current_image_buffer.getvalue()).decode()}
                if current_alpha_value:
                    current_saved_result=save_map_capture_result(current_result_payload,Path(current_directory_name))
                    self.assertTrue(Path(current_saved_result['map']).is_file())
                else:
                    with self.assertRaises(ValueError):save_map_capture_result(current_result_payload,Path(current_directory_name))

    def test_gui_uses_capture_gateway(self):
        from unittest.mock import patch
        from tools.review.ui.gradio.map_review_app import capture_map_review_images
        with patch('tools.review.common.management_client.execute_remote_management_command',return_value={'images':{'map':'/tmp/map.png'}}) as current_gateway_mock:
            self.assertEqual(capture_map_review_images('ash-edge'),['/tmp/map.png'])
            current_gateway_mock.assert_called_once_with('map-review','capture',{'map':'ash-edge'})

    def test_map_response_authenticated_storage(self):
        import json
        from unittest.mock import Mock, patch
        from tools.review.domains.character_review.capture import handle_capture_asset_request
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_storage_directory=Path(current_directory_name)
            current_job_directory=current_storage_directory/'sample'
            current_job_directory.mkdir()
            (current_job_directory/'active-token').write_text('sample-token')
            current_response_bytes=json.dumps({'map':'data:image/png;base64,test'}).encode()
            with patch('tools.review.domains.character_review.capture.CAPTURE_STORAGE_DIRECTORY',current_storage_directory):
                current_http_handler=Mock(command='POST',path='/management/capture/sample/sample-token/capture-result',headers={'X-Capture-Token':'sample-token','Content-Length':str(len(current_response_bytes))},rfile=io.BytesIO(current_response_bytes),wfile=io.BytesIO())
                self.assertTrue(handle_capture_asset_request(current_http_handler))
                current_http_handler.send_response.assert_called_once_with(200)
                self.assertEqual(json.loads((current_job_directory/'capture-response.json').read_text()),json.loads(current_response_bytes))
