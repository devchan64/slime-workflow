"""얼굴 앵커 비교의 관측 출처와 동일 몸 프레임 조건을 검증한다."""
import copy
import unittest
from generators.kimodo.multiview_face_comparison import compare_face_anchor_outputs
from generators.kimodo.multiview_provenance import calculate_multiview_observation_hash


class KimodoFaceComparisonTests(unittest.TestCase):
    def test_compares_visible_points_and_rejects_changed_body(self):
        current_points=[[float(current_joint),float(current_joint),.9] for current_joint in range(18)]
        current_reference={'keypoints':[copy.deepcopy(current_points) for _ in range(8)],'observation_sources':[{'bbox':[0,0,32,32]} for _ in range(8)]}
        current_weights={'schema':'kimodo-body18-view-weights-v1','views':[{'observation':current_index+1,'joints':[{'joint':current_joint,'weight':0 if current_joint==17 else 1,'reason':'검수'} for current_joint in range(18)]} for current_index in range(8)]}
        current_ratio={'weighted_body_face_candidate':{'joint_weight_table':current_weights,'observation_sha256':calculate_multiview_observation_hash(current_reference),'views':[{'observation':current_index+1,'face_fit_weights':[.9,.9,.9,.9,0.]} for current_index in range(8)]}}
        current_views={f'view_{current_index}':{'source_frames':[0],'body_points_832x480':[copy.deepcopy(current_points)]} for current_index in range(8)}
        current_baseline={'reference_proportions':current_ratio,'directions':current_views}
        current_candidate=copy.deepcopy(current_baseline)
        current_candidate['directions']['view_0']['body_points_832x480'][0][0][0]+=1
        current_mapping={f'view_{current_index}':current_index+1 for current_index in range(8)}
        current_report=compare_face_anchor_outputs(current_reference,current_baseline,current_candidate,current_mapping)
        self.assertEqual(current_report['summary']['0']['count'],8)
        self.assertEqual(current_report['summary']['17']['count'],0)
        self.assertGreater(current_report['summary']['0']['candidate'],0)
        self.assertEqual(current_report['body_joint_max_difference_px'],0)
        current_candidate['directions']['view_0']['body_points_832x480'][0][2][0]+=1
        with self.assertRaisesRegex(ValueError,'몸 관절'):
            compare_face_anchor_outputs(current_reference,current_baseline,current_candidate,current_mapping)
        current_reference['keypoints'][0][0][0]+=1
        with self.assertRaisesRegex(ValueError,'출처'):
            compare_face_anchor_outputs(current_reference,current_baseline,current_candidate,current_mapping)


if __name__=='__main__':
    unittest.main()
