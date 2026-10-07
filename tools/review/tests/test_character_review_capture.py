"""캐릭터 캡처 입력과 공용 명령 계약을 검증한다."""
import unittest
from tools.review.domains.character_review.capture import validate_capture_settings
from tools.review.common.management_gateway import resolve_management_command, identify_management_command


class CharacterReviewCaptureTest(unittest.TestCase):
    def test_capture_defaults_and_gateway_roundtrip(self):
        current_settings_record=validate_capture_settings({})
        self.assertEqual((current_settings_record['width'],current_settings_record['height']),(768,576))
        current_method_name,current_route_path=resolve_management_command('character-review','capture',current_settings_record)
        self.assertEqual(identify_management_command(current_route_path,current_method_name,current_settings_record),('character-review','capture',current_settings_record))

    def test_rejects_unknown_paths_urls_and_invalid_render_values(self):
        for current_invalid_payload in ({'url':'https://example.com'},{'output':'/tmp/arbitrary.png'},{'width':99999},{'row':7},{'outline':1},{'zoom':float('nan')},{'ground':'unknown'},{'rotation':True}):
            with self.subTest(payload=current_invalid_payload),self.assertRaises(ValueError):validate_capture_settings(current_invalid_payload)

    def test_preserves_selected_render_settings(self):
        current_settings_record=validate_capture_settings({'ground':'grass','column':2,'row':5,'zoom':2,'rim':False,'shadow':False})
        self.assertEqual(current_settings_record['ground'],'grass')
        self.assertEqual(current_settings_record['row'],5)
        self.assertFalse(current_settings_record['rim'])
        self.assertFalse(current_settings_record['shadow'])
