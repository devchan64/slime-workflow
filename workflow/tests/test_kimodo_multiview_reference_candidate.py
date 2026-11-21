"""가중 3D 골격의 비율 후보 계약과 원본 보존을 확인한다."""
import copy
import unittest

from generators.kimodo.multiview_reference_candidate import build_multiview_ratio_candidate
from generators.kimodo.reference_proportions import REFERENCE_SEGMENT_GROUPS


class KimodoMultiviewCandidateTests(unittest.TestCase):
    def test_candidate_uses_3d_ratios_and_preserves_original(self):
        current_reference={'schema':'body18-reference-ratios-v4','ratios':{current_name:1. for current_name in REFERENCE_SEGMENT_GROUPS},'body_axis':{'vertical_nose_shoulder_to_torso':.5}}
        current_body=[[-.2,.5,0],[-.3,.3,0],[-.3,.1,0],[.2,.5,0],[.3,.3,0],[.3,.1,0],[-.1,0,0],[-.1,-.3,0],[-.1,-.6,0],[.1,0,0],[.1,-.3,0],[.1,-.6,0]]
        current_faces=[[0,.75,.1],[-.03,.8,.1],[.03,.8,.1],[-.1,.8,0],[.1,.8,0]]
        current_weights={'schema':'kimodo-body18-view-weights-v1','views':[{'observation':current_index+1,'joints':[{'joint':current_joint,'weight':1.,'reason':'검수'} for current_joint in range(18)]} for current_index in range(8)]}
        current_skeleton={'schema':'kimodo-multiview-body-face-experiment-v1','body18_joint_indices':list(range(2,14)),'face_joint_indices':[0,14,15,16,17],'body_joint_positions':current_body,'face_joint_positions':current_faces,'joint_weight_table':current_weights}
        current_original=copy.deepcopy(current_reference)
        current_candidate=build_multiview_ratio_candidate(current_reference,current_skeleton)
        self.assertEqual(current_reference,current_original)
        self.assertAlmostEqual(current_candidate['ratios']['shoulder_width'],.8)
        self.assertAlmostEqual(current_candidate['body_axis']['vertical_nose_shoulder_to_torso'],.5)
        self.assertEqual(current_candidate['baseline_3d_candidate_ratios'],current_original['ratios'])
        current_skeleton['excluded_body']=[0,2]
        with self.assertRaisesRegex(ValueError,'제외 관측'):
            build_multiview_ratio_candidate(current_reference,current_skeleton)


if __name__=='__main__':
    unittest.main()
