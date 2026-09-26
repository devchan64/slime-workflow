import unittest
from tools.review.domains.anny.anny_attributes import load_active_profile, load_profile_by_identifier, load_profile_attribute_defaults
from tools.review.ui_assets import resolve_review_ui_asset


class AnnyProfileTests(unittest.TestCase):
    def test_neutral_is_the_active_default_profile(self):
        active_profile_record=load_active_profile()
        self.assertEqual(active_profile_record['profile_id'],'neutral_v4')
        self.assertEqual(active_profile_record['label'],'중성형 v4')
        self.assertEqual(active_profile_record['source_asset_id'],'anny-neutral-v4')

    def test_retired_profiles_are_unavailable(self):
        for profile_identifier in ('female_type_a_v1','female_type_a_v2','male_type_a_v1'):
            with self.assertRaises(ValueError):
                load_profile_by_identifier(profile_identifier)

    def test_attribute_editor_has_direct_input_modal(self):
        rendered_page_text=resolve_review_ui_asset('anny-attributes.html').read_text()
        self.assertIn('attribute-direct-input-dialog',rendered_page_text)
        self.assertIn('직접 입력',rendered_page_text)
        self.assertIn('openDirectAttributeInput',rendered_page_text)
        self.assertIn('baseline-profile',rendered_page_text)


if __name__=='__main__':
    unittest.main()
