"""빌보드 가이드 입력 계약 검증."""
import unittest
from tools.review.domains.image.billboard_guide_prompt import (
    BILLBOARD_LAYOUT_PROFILES, BILLBOARD_DEFAULT_SUBJECT,
    load_billboard_guide_image, compose_billboard_guide_prompt,
)


class BillboardGuidePromptTests(unittest.TestCase):
    def test_registered_reference_profiles(self):
        self.assertEqual(len(BILLBOARD_LAYOUT_PROFILES), 22)
        for selected_profile_name in BILLBOARD_LAYOUT_PROFILES:
            self.assertEqual(load_billboard_guide_image(selected_profile_name).size, (1024, 1024))
            selected_prompt_text = compose_billboard_guide_prompt(selected_profile_name, BILLBOARD_DEFAULT_SUBJECT)
            self.assertLess(len(selected_prompt_text.split()), 100)
            self.assertIn('80%', selected_prompt_text)
            if selected_profile_name == '2x2-lake-boulders':
                self.assertIn('2x2 footprint', selected_prompt_text)
                self.assertIn('rounded lake-worn', selected_prompt_text)
                continue
            if selected_profile_name == '4x4-rooted-stump':
                self.assertIn('4x4 footprint', selected_prompt_text)
                self.assertIn('rear roots', selected_prompt_text)
                continue
            if selected_profile_name == '1x1-grass-cover':
                self.assertIn('height 35–50', selected_prompt_text)
                self.assertIn('no soil block', selected_prompt_text)
                continue
            if selected_profile_name == '1x1-rooted-grass':
                self.assertIn('Three rooted tufts', selected_prompt_text)
                self.assertIn('maximum 110', selected_prompt_text)
                continue
            if selected_profile_name == '2x1-weathered-rock':
                self.assertIn('No stacked slabs', selected_prompt_text)
            if selected_profile_name.endswith('medium'):
                self.assertIn('height 260 relative to tile width 260', selected_prompt_text)
            if selected_profile_name == '1x3-fallen-log':
                self.assertIn('upper-right to lower-left', selected_prompt_text)
                self.assertIn('height 80–105 relative to tile width 300', selected_prompt_text)
                self.assertNotIn('wall', selected_prompt_text)
                continue
            self.assertIn('rear flush' if selected_profile_name.endswith(('tall', 'medium')) else f"height { {'1x1-low-2x': 180, '1x1-low-4x': 360}.get(selected_profile_name, 90)}", selected_prompt_text)

    def test_invalid_inputs_rejected(self):
        for selected_profile_name in ('../secret', '4x4-low', ''):
            with self.assertRaises(ValueError):
                load_billboard_guide_image(selected_profile_name)
        for selected_subject_text in ('', 'rock ' * 100):
            with self.assertRaises(ValueError):
                compose_billboard_guide_prompt('3x1-tall', selected_subject_text)

    def test_interface_requires_guide(self):
        from tools.review.ui.gradio.qwen_2511_app import build_qwen_2511_interface
        selected_interface_blocks = build_qwen_2511_interface('http://127.0.0.1:8770', qwen21_mode_enabled=True, prop_mode_enabled=True, billboard_guide_enabled=True)
        selected_component_records = selected_interface_blocks.config['components']
        self.assertTrue(any(selected_component_record['props'].get('label') == '점유 열×행 · 형태' for selected_component_record in selected_component_records))
        selected_generate_record = next(selected_component_record for selected_component_record in selected_component_records if selected_component_record['props'].get('value') == '대기열에 추가')
        self.assertFalse(selected_generate_record['props']['interactive'])
