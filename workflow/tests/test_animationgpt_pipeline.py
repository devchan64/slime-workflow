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

class AnimationGPTPipelineExecutionTest(unittest.TestCase):
    def test_incompatible_vace_length_preserves_generated_motion(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import numpy as np
        from workflow.domains.animationgpt.pipeline import run_pipeline
        from workflow.common.animationgpt_model_download import ANIMATIONGPT_MODEL_DIRECTORY

        def run_worker(*args, **kwargs):
            data = json.loads(kwargs['input'])
            destination = Path(data['output'])
            points = np.zeros((120, 22, 3), dtype=np.float32)
            points[:, :, 1] = np.arange(22) / 22
            np.save(destination / 'joints.npy', points)
            (destination / 'motion.json').write_text(json.dumps({'fps': 20}), encoding='utf-8')
            class Completed:
                returncode = 0
            return Completed()

        with tempfile.TemporaryDirectory() as directory, \
             patch('workflow.domains.animationgpt.pipeline.validate_upstream'), \
             patch('workflow.common.animationgpt_model_download.inspect_animationgpt_model_files', return_value=True), \
             patch('workflow.domains.animationgpt.pipeline.subprocess.run', side_effect=run_worker):
            output = Path(directory) / 'output'
            result = run_pipeline({'prompt': 'one handed sword', 'seed': 43}, output, '.', ANIMATIONGPT_MODEL_DIRECTORY)
            self.assertTrue((output / 'joints.npy').exists())
            self.assertIsNone(result['pose_manifest'])
            self.assertIn('4n+1', result['pose_unavailable_reason'])
            self.assertEqual(json.loads((output / 'result.json').read_text())['pose_segments'], 0)
