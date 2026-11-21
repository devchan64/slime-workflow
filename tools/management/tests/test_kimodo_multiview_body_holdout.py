"""몸 관측 제외 검증의 선택과 오류 기록을 확인한다."""
import unittest
from unittest.mock import patch
from generators.kimodo.multiview_body_holdout import calculate_body_holdout_report


class KimodoBodyHoldoutTests(unittest.TestCase):
    def test_selected_observation_excluded_and_duplicate_rejected(self):
        current_reference={'keypoints':[[[0.,0.,.9] for _ in range(18)] for _ in range(8)]}
        current_views=[{'body_xy':[[3.,4.] for _ in range(12)]} for _ in range(8)]
        current_selection=[{'observation':1,'joint':2}]
        with patch('generators.kimodo.multiview_body_holdout.calculate_multiview_observation_hash',return_value='hash'),patch('generators.kimodo.multiview_body_holdout.fit_multiview_body_face',return_value={'views':current_views}) as current_fit:
            current_result=calculate_body_holdout_report(current_reference,{},[],{},current_selection)
            self.assertEqual(current_fit.call_args.kwargs['current_excluded_body'],(0,2))
            self.assertEqual(current_result['excluded_observations'][0]['error_px'],5.)
            with self.assertRaisesRegex(ValueError,'중복'):
                calculate_body_holdout_report(current_reference,{},[],{},current_selection*2)
            with self.assertRaisesRegex(ValueError,'번호'):
                calculate_body_holdout_report(current_reference,{},[],{},[{'observation':1,'joint':8}])


if __name__=='__main__':
    unittest.main()
