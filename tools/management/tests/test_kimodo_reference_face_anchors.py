"""등록 참조의 얼굴 비율·출처·머리 운동을 검증한다."""
import unittest
from unittest.mock import patch
import numpy as np

from generators.kimodo.reference_face_anchors import load_reference_face_template, apply_registered_reference_face


class ReferenceFaceAnchorTests(unittest.TestCase):
    def test_reference_face_replaces_all_five_and_preserves_body(self):
        current_template_record, current_source_record = load_reference_face_template()
        current_body_frames = np.zeros((2, 18, 3))
        current_body_frames[:, 2:14] = current_template_record['body_joint_positions']
        current_body_frames[:, [0,14,15,16,17]] = 99
        current_head_frames = np.array([[0,1.5,0], [1,1.5,0]])
        current_head_rotations = np.array([np.eye(3), [[0,0,1],[0,1,0],[-1,0,0]]])
        current_ratio_record = {'reference_image_sha256': [current_source_record['reference_sha256']]}
        current_output_frames, current_output_source = apply_registered_reference_face(current_body_frames, current_head_frames, current_head_rotations, current_ratio_record)
        current_face_indices = [0,14,15,16,17]
        np.testing.assert_allclose(current_output_frames[0,current_face_indices], current_template_record['face_joint_positions'], atol=1e-12)
        np.testing.assert_allclose(current_output_frames[:,1:14], current_body_frames[:,1:14])
        current_expected_points = current_head_frames[1] + (current_output_frames[0,current_face_indices]-current_head_frames[0]) @ current_head_rotations[1].T
        np.testing.assert_allclose(current_output_frames[1,current_face_indices], current_expected_points)
        self.assertEqual(current_output_source['reference_sha256'],current_source_record['reference_sha256'])

    def test_other_reference_does_not_receive_default_character_face(self):
        current_body_frames = np.zeros((1,18,3))
        current_output_frames, current_output_source = apply_registered_reference_face(current_body_frames,None,None,{'reference_image_sha256':['0'*64]})
        self.assertIs(current_output_frames,current_body_frames)
        self.assertIsNone(current_output_source)

    def test_changed_reference_image_is_rejected(self):
        from pathlib import Path
        current_original_reader = Path.read_bytes
        def read_changed_reference(current_file_path):
            if current_file_path.name == 'default-eight-directions-v1.png':
                return b'changed'
            return current_original_reader(current_file_path)
        with patch.object(Path,'read_bytes',read_changed_reference):
            with self.assertRaisesRegex(ValueError,'해시'):
                load_reference_face_template()
