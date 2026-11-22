import unittest

from workflow.domains.animationgpt.pipeline import validate_request


class AnimationGPTPipelineRequestTest(unittest.TestCase):
    def test_normalizes_defaults(self):
        self.assertEqual(validate_request({'prompt': '  one sword slash  ', 'seed': 42}), {
            'prompt': 'one sword slash', 'seed': 42, 'yaw_degrees': 0, 'scale': .8, 'include_face': False,
        })

    def test_rejects_unsupported_and_invalid_values(self):
        for change in ({'prompt': ''}, {'seed': True}, {'yaw_degrees': float('nan')},
                       {'scale': 0}, {'include_face': 1}, {'weapon_track': True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_request({'prompt': 'one sword slash', 'seed': 42, **change})


if __name__ == '__main__':
    unittest.main()
