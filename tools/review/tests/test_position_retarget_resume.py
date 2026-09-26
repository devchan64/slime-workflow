"""저장된 리타깃 방식이 렌더 재개 후에도 유지되는지 검사한다."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
from generators.momask import resume_render


class RetargetContractResumeTests(unittest.TestCase):
    def test_saved_contract_survives_resume(self):
        self.run_saved_contract_case(None)

    def test_historical_corrections_survive_resume(self):
        self.run_saved_contract_case({'upper_arm_twist_degrees': 8})

    def run_saved_contract_case(self, historical_correction_values):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            generation_job_path = Path(temporary_directory_name)
            render_output_path = generation_job_path / 'result/anny'
            image_output_path = render_output_path / 'down_left'
            image_output_path.mkdir(parents=True)
            Image.new('RGBA', (1, 1)).save(image_output_path / 'preview-0001.png')
            source_motion_path = generation_job_path / 'motion-run/motion'
            source_motion_path.mkdir(parents=True)
            np.savez(source_motion_path / 'motion.npz', joints=np.zeros((1, 22, 3)))
            (generation_job_path / 'motion-run/prompt.txt').write_text('검증용 모션')
            (generation_job_path / 'request.json').write_text(json.dumps({'action': 'standing', 'directions': ['down_left']}))
            (render_output_path / 'render_asset.py').write_text('  bpy.ops.render.render(write_still=True)')
            for current_file_name in ('baseline-model.json',):
                (render_output_path / current_file_name).write_text('{}')
            saved_contract_values = {'hand_pose': 'inherit-rest-local', 'arm_retarget': 'position-profile-transport-v2', 'skinning': 'dual-quaternion', 'profile_sha256': 'test-profile'}
            (render_output_path / 'retarget-contract.json').write_text(json.dumps(saved_contract_values))
            if historical_correction_values is not None:
                (render_output_path / 'arm-corrections.json').write_text(json.dumps(historical_correction_values))
            with patch.object(resume_render.subprocess, 'run'), patch('tools.review.domains.momask.openpose_maps.generate_openpose_maps'):
                resume_render.resume_render_frames(generation_job_path)
            result_record_values = json.loads((render_output_path / 'result.json').read_text())
            if historical_correction_values is None:
                self.assertNotIn('arm_corrections', result_record_values)
                self.assertFalse((render_output_path / 'arm-corrections.json').exists())
            else:
                self.assertEqual(result_record_values['arm_corrections'], historical_correction_values)
                self.assertEqual(json.loads((render_output_path / 'arm-corrections.json').read_text()), historical_correction_values)
            for current_field_name, current_field_value in saved_contract_values.items():
                self.assertEqual(result_record_values[current_field_name], current_field_value)
            self.assertEqual(json.loads((generation_job_path / 'result.json').read_text())['arm_retarget'], saved_contract_values['arm_retarget'])


if __name__ == '__main__':
    unittest.main()
