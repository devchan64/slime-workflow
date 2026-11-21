"""폐기된 MoMask 재개가 저장된 제작 기록을 변경하지 않는지 검증한다."""
from pathlib import Path
import tempfile
import unittest
from generators.momask.resume_render import resume_render_frames


class PositionRetargetResumeTests(unittest.TestCase):
    def test_retired_resume_preserves_saved_contract(self):
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_job_directory = Path(current_temporary_directory)
            saved_contract_path = current_job_directory / 'retarget-contract.json'
            saved_contract_bytes = b'{"hand_pose":"inherit-rest-local"}'
            saved_contract_path.write_bytes(saved_contract_bytes)
            with self.assertRaisesRegex(ValueError, '폐기'):
                resume_render_frames(current_job_directory)
            self.assertEqual(saved_contract_path.read_bytes(), saved_contract_bytes)
