"""얼굴 제외 검증이 관측을 실제로 제외하고 출처를 검사하는지 확인한다."""
import unittest
from unittest.mock import patch

from generators.kimodo.multiview_face_holdout import calculate_face_holdout_report
from generators.kimodo.multiview_provenance import calculate_multiview_fit_context_hash


class KimodoFaceHoldoutTests(unittest.TestCase):
    def test_face_observation_is_excluded_and_reported(self):
        current_reference={'keypoints':[[[0.,0.,.9] for _ in range(18)] for _ in range(8)]}
        current_weights={'example':'same'}
        current_views=[{'face_fit_weights':[.9,0.,0.,0.,0.] if current_index==0 else [0.]*5} for current_index in range(8)]
        current_baseline={'observation_sha256':'hash','joint_weight_table':current_weights,'views':current_views}
        current_body={'observation_sha256':'hash','joint_weight_table':current_weights,'excluded_observations':[{'observation':1,'joint':2,'error_px':2.}]}
        current_fit={'views':[{'face_xy':[[3.,4.]]*5} for _ in range(8)]}
        with patch('generators.kimodo.multiview_face_holdout.calculate_multiview_observation_hash',return_value='hash'), patch('generators.kimodo.multiview_joint_weights.validate_multiview_joint_weights',return_value=[[1.]*18 for _ in range(8)]), patch('generators.kimodo.multiview_face_holdout.fit_multiview_body_face',return_value=current_fit) as current_fit_mock:
            current_visibility=[[False]*5 for _ in range(8)];current_visibility[0][0]=True
            current_context=calculate_multiview_fit_context_hash('hash',{},current_visibility,current_weights)
            current_baseline['fit_context_sha256']=current_context;current_body['fit_context_sha256']=current_context
            with self.assertRaisesRegex(ValueError,'출처'):
                calculate_face_holdout_report(current_reference,{'changed':True},current_visibility,current_weights,current_baseline,current_body)
            current_report=calculate_face_holdout_report(current_reference,{},current_visibility,current_weights,current_baseline,current_body)
            self.assertEqual(current_fit_mock.call_args.kwargs['current_excluded_face'],(0,0))
            self.assertEqual(current_report['excluded_observations'][-1]['error_px'],5.)
            with self.assertRaisesRegex(ValueError,'가중치'):
                calculate_face_holdout_report(current_reference,{},[],{'example':'changed'},current_baseline,current_body)


if __name__=='__main__':
    unittest.main()
