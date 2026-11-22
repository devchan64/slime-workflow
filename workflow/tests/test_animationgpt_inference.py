import unittest
from workflow.domains.animationgpt.inference import motion_decoder_constraints, parse_motion_tokens


class AnimationGPTTokenValidationTest(unittest.TestCase):
    def test_generation_only_allows_motion_codes_and_nonempty_end(self):
        class Tokenizer:
            def convert_tokens_to_ids(self, name): return 100 + int(name.removeprefix('<motion_id_').removesuffix('>'))
            def convert_ids_to_tokens(self, value): return f'<motion_id_{value-100}>'
        initial, end, allowed = motion_decoder_constraints(Tokenizer(), 0, codebook_size=3)
        self.assertEqual(initial, [0, 103])
        self.assertEqual(allowed(0, initial), [100, 101, 102])
        self.assertEqual(allowed(0, initial+[100]), [100, 101, 102, 104])
        self.assertEqual(end, 104)

    def test_generation_rejects_duplicate_token_ids(self):
        class Tokenizer:
            def convert_tokens_to_ids(self, name): return 0
        with self.assertRaisesRegex(ValueError, '등록'):
            motion_decoder_constraints(Tokenizer(), 99, codebook_size=3)

    def test_valid_sequence(self):
        self.assertEqual(parse_motion_tokens('prefix<motion_id_512><motion_id_3><motion_id_511><motion_id_513>'), [3, 511])

    def test_missing_or_invalid_boundaries_do_not_fall_back(self):
        for text in ('<motion_id_4><motion_id_513>', '<motion_id_512><motion_id_513>',
                     '<motion_id_512><motion_id_514><motion_id_513>',
                     '<motion_id_512>junk<motion_id_1><motion_id_513>',
                     '<motion_id_512><motion_id_1><motion_id_513><motion_id_513>'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_motion_tokens(text)
