"""좌표 변환 사전 기록의 수치와 입력 보존을 검증한다."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from generators.momask.retarget_audit import write_coordinate_audit


class CoordinateAuditTests(unittest.TestCase):
    def test_coordinate_archive_preserves_input_and_root_scale(self):
        source_joint_frames = np.array([[[0., 0., 0.], [0., 1., 0.]], [[2., 0., 0.], [2., 1., 0.]]])
        original_joint_frames = source_joint_frames.copy()
        profile_record_values = {'coordinate_matrix': [[1, 0, 0], [0, 0, -1], [0, 1, 0]], 'root_joint': 0, 'source_reference': {'joint_positions': [[0, 0, 0], [0, 1, 0]]},
                                 'segments': [{'segment_id': 'test_segment', 'transfer_mode': 'absolute_direction', 'source_primary': [0, 1], 'target_primary': ['start', 'end'], 'source_secondary': None, 'target_secondary': None, 'target_bones': ['start']}]}
        with tempfile.TemporaryDirectory() as temporary_directory_path, contextlib.redirect_stdout(io.StringIO()):
            write_coordinate_audit(temporary_directory_path, source_joint_frames, profile_record_values,
                                   {'start': (0, 0, 0), 'end': (1, 0, 0)}, 2., {'source_motion': 'test'})
            archive_record_values = np.load(Path(temporary_directory_path) / 'coordinate-transform.npz')
            np.testing.assert_array_equal(archive_record_values['source_joints'], original_joint_frames)
            np.testing.assert_array_equal(archive_record_values['converted_joints'][0, 1], [0, 0, 1])
            np.testing.assert_array_equal(archive_record_values['root_translations'][1], [4, 0, 0])
            audit_record_values = json.loads((Path(temporary_directory_path) / 'coordinate-transform.json').read_text())
            self.assertEqual(audit_record_values['segments'][0]['directions']['primary']['rest_alignment_degrees'], [90., 90.])
            self.assertTrue(audit_record_values['source_rest_pose_available'])
        np.testing.assert_array_equal(source_joint_frames, original_joint_frames)
