"""DWPose 오류가 직접 포즈 성공을 취소하지 않는지 검증한다."""
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from generators.kimodo.pose_outputs import export_kimodo_pose_outputs


class KimodoPoseOutputTests(unittest.TestCase):
    def test_dwpose_failure_preserves_direct_output(self):
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_attempt_root = Path(current_temporary_directory)
            (current_attempt_root/'soma-direct-pose.json').write_text('{"directions":{"front_left":{"video":"soma-direct-front_left.mp4"}}}')
            with patch('generators.kimodo.pose_outputs.subprocess.run',side_effect=[None,subprocess.CalledProcessError(1,['dwpose'])]):
                current_direct_record,current_dwpose_record,current_warning_records = export_kimodo_pose_outputs(current_attempt_root,current_attempt_root,{},Mock())
            self.assertIn('front_left',current_direct_record['directions'])
            self.assertEqual(current_dwpose_record['status'],'warning')
            self.assertTrue(current_warning_records)
            self.assertTrue((current_attempt_root/'dwpose-export.json').is_file())

    def test_direct_failure_remains_fatal(self):
        with patch('generators.kimodo.pose_outputs.subprocess.run',side_effect=subprocess.CalledProcessError(1,['direct'])) as current_process_mock:
            with self.assertRaises(subprocess.CalledProcessError):
                export_kimodo_pose_outputs(Path('/tmp'),Path('/tmp'),{},Mock())
            self.assertEqual(current_process_mock.call_count,1)
