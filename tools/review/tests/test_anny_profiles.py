import unittest
from tools.review.domains.anny.anny_attributes import load_active_profile, load_profile_by_identifier, load_profile_attribute_defaults
from tools.review.ui_assets import resolve_review_ui_asset


class AnnyProfileTests(unittest.TestCase):
    def test_female_type_a_is_the_active_default_profile(self):
        active_profile_record=load_active_profile()
        self.assertEqual(active_profile_record['profile_id'],'female_type_a_v1')
        self.assertEqual(active_profile_record['label'],'여성 타입 A · 버전 1')
        self.assertEqual(active_profile_record['source_asset_id'],'anny-39eab167-v1')

    def test_male_type_a_increases_torso_width(self):
        male_profile_record=load_profile_by_identifier('male_type_a_v1')
        self.assertEqual(male_profile_record['label'],'남성형 Type A')
        self.assertEqual(load_profile_attribute_defaults(male_profile_record)['local_changes_kwargs']['torso-scale-horiz-incr'],0.5)

    def test_attribute_editor_has_direct_input_modal(self):
        rendered_page_text=resolve_review_ui_asset('anny-attributes.html').read_text()
        self.assertIn('attribute-direct-input-dialog',rendered_page_text)
        self.assertIn('직접 입력',rendered_page_text)
        self.assertIn('openDirectAttributeInput',rendered_page_text)
        self.assertIn('baseline-profile',rendered_page_text)


if __name__=='__main__':
    unittest.main()
