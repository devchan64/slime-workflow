"""캐릭터 캡처 입력과 공용 명령 계약을 검증한다."""
import unittest
from tools.review.domains.character_review.capture import validate_capture_settings
from tools.review.common.management_gateway import resolve_management_command, identify_management_command


class CharacterReviewCaptureTest(unittest.TestCase):
    def test_capture_defaults_and_gateway_roundtrip(self):
        current_settings_record=validate_capture_settings({})
        self.assertEqual((current_settings_record['width'],current_settings_record['height']),(768,576))
        self.assertEqual(current_settings_record['outline_width'],1)
        self.assertEqual(current_settings_record['zoom'],2)
        current_method_name,current_route_path=resolve_management_command('character-review','capture',current_settings_record)
        self.assertEqual(identify_management_command(current_route_path,current_method_name,current_settings_record),('character-review','capture',current_settings_record))

    def test_rejects_unknown_paths_urls_and_invalid_render_values(self):
        for current_invalid_payload in ({'url':'https://example.com'},{'output':'/tmp/arbitrary.png'},{'outline_width':0},{'outline_width':5},{'outline_width':float('nan')},{'outline_width':True},{'width':99999},{'row':3},{'column':3},{'outline':1},{'zoom':float('nan')},{'ground':'unknown'},{'rotation':True}):
            with self.subTest(payload=current_invalid_payload),self.assertRaises(ValueError):validate_capture_settings(current_invalid_payload)

    def test_preserves_selected_render_settings(self):
        current_settings_record=validate_capture_settings({'ground':'grass','column':2,'row':2,'zoom':2,'rim':False,'shadow':False})
        self.assertEqual(current_settings_record['ground'],'grass')
        self.assertEqual(current_settings_record['row'],2)
        self.assertFalse(current_settings_record['rim'])
        self.assertFalse(current_settings_record['shadow'])

    def test_gui_capture_uses_configured_remote_gateway(self):
        from unittest.mock import patch
        from tools.review.ui.gradio.map_review_app import capture_character_review_images
        current_settings_record = validate_capture_settings({})
        with patch.dict('os.environ', {'SLIME_MANAGEMENT_GATEWAY_URL':'http://127.0.0.1:18999'}), patch('tools.review.common.management_gateway.call_management_api', return_value={'images':{'front':'/tmp/audit-front.png'}}) as current_transport_mock:
            self.assertEqual(capture_character_review_images(current_settings_record), ['/tmp/audit-front.png'])
            self.assertEqual(current_transport_mock.call_args.args, ('http://127.0.0.1:18999','/character-review/capture',current_settings_record,True))
        with patch.dict('os.environ', {'SLIME_MANAGEMENT_GATEWAY_URL':'https://untrusted.example'}), patch('tools.review.common.management_gateway.call_management_api') as current_transport_mock:
            with self.assertRaisesRegex(ValueError, '게이트웨이'):
                capture_character_review_images(current_settings_record)
            current_transport_mock.assert_not_called()

    def test_rejects_transparent_capture_but_preserves_visible_pixels(self):
        import io
        from PIL import Image
        from tools.review.domains.character_review.capture import validate_capture_image
        current_settings_record={'width':256,'height':256}
        current_image_object=Image.new('RGBA',(512,512))
        for current_visible_pixel in (False,True):
            if current_visible_pixel:current_image_object.putpixel((256,256),(1,2,3,255))
            current_image_stream=io.BytesIO()
            current_image_object.save(current_image_stream,format='PNG')
            if current_visible_pixel:
                self.assertEqual(validate_capture_image(current_image_stream.getvalue(),current_settings_record).size,(512,512))
            else:
                with self.assertRaisesRegex(ValueError,'비어'):
                    validate_capture_image(current_image_stream.getvalue(),current_settings_record)

    def test_shared_capture_routes_and_expired_session(self):
        import io
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import Mock, patch
        from tools.review.domains.character_review.capture import handle_capture_asset_request
        with TemporaryDirectory() as current_temporary_directory:
            current_storage_directory=Path(current_temporary_directory)
            current_job_directory=current_storage_directory/'sample'
            (current_job_directory/'web').mkdir(parents=True)
            (current_job_directory/'web/capture.html').write_text('capture')
            (current_job_directory/'active-token').write_text('secret')
            with patch('tools.review.domains.character_review.capture.CAPTURE_STORAGE_DIRECTORY',current_storage_directory):
                for current_request_path,current_expected_success in (
                    ('/management/capture/sample/secret/capture.html',True),
                    ('/management/capture/sample/wrong/capture.html',False),
                    ('/management/capture/sample/secret/%2e%2e/active-token',False),
                ):
                    current_http_handler=Mock(command='GET',path=current_request_path,wfile=io.BytesIO())
                    self.assertTrue(handle_capture_asset_request(current_http_handler))
                    self.assertEqual(current_http_handler.send_response.called,current_expected_success)
                current_response_bytes=json.dumps({'error':'render failed'}).encode()
                current_http_handler=Mock(command='POST',path='/management/capture/sample/secret/capture-result',headers={'X-Capture-Token':'secret','Content-Length':str(len(current_response_bytes))},rfile=io.BytesIO(current_response_bytes),wfile=io.BytesIO())
                handle_capture_asset_request(current_http_handler)
                self.assertEqual(json.loads((current_job_directory/'capture-response.json').read_text()),{'error':'render failed'})
                (current_job_directory/'active-token').unlink()
                current_http_handler=Mock(command='GET',path='/management/capture/sample/secret/capture.html',wfile=io.BytesIO())
                handle_capture_asset_request(current_http_handler)
                current_http_handler.send_error.assert_called_once()

    def test_review_rejects_separate_ports(self):
        import contextlib
        import io
        from tools.review.serve import parse_review_arguments
        self.assertEqual(parse_review_arguments(['--port','8770']).port,8770)
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            parse_review_arguments(['--port','8788'])
