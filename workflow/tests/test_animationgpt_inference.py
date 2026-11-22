import unittest
from workflow.domains.animationgpt.inference import parse_motion_tokens


class AnimationGPTTokenValidationTest(unittest.TestCase):
    def test_valid_sequence(self):
        self.assertEqual(parse_motion_tokens('prefix<motion_id_512><motion_id_3><motion_id_511><motion_id_513>'), [3, 511])

    def test_missing_or_invalid_boundaries_do_not_fall_back(self):
        for text in ('<motion_id_4><motion_id_513>', '<motion_id_512><motion_id_513>',
                     '<motion_id_512><motion_id_514><motion_id_513>',
                     '<motion_id_512>junk<motion_id_1><motion_id_513>',
                     '<motion_id_512><motion_id_1><motion_id_513><motion_id_513>'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_motion_tokens(text)
