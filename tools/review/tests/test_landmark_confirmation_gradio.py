"""기준점 후보 교체 확인과 선택 변경 거절을 검증한다."""
import unittest
from unittest.mock import patch
import gradio as gr
from tools.review.ui.gradio import anny_landmarks_app as current_landmark_module


class LandmarkConfirmationTests(unittest.TestCase):
    def test_missing_or_changed_selection_never_loads(self):
        with patch.object(current_landmark_module,'execute_landmark_request') as current_gateway_mock:
            for current_identifier_value,current_confirmation_flag,current_confirmed_value in [('',True,''),('a',False,'a'),('b',True,'a')]:
                with self.subTest(identifier=current_identifier_value),self.assertRaises(gr.Error):
                    current_landmark_module.load_candidate_record(current_identifier_value,current_confirmation_flag,current_confirmed_value)
            current_gateway_mock.assert_not_called()

    def test_confirmation_state_enables_only_selected_record(self):
        self.assertFalse(current_landmark_module.update_candidate_confirmation('',True)[1]['interactive'])
        self.assertEqual(current_landmark_module.update_candidate_confirmation('a',True)[0],'a')
        self.assertTrue(current_landmark_module.update_candidate_confirmation('a',True)[1]['interactive'])
        self.assertEqual(current_landmark_module.reset_candidate_confirmation()[:2],(False,''))
        self.assertFalse(current_landmark_module.reset_candidate_confirmation()[2]['interactive'])

    def test_matching_confirmation_loads_once_and_unchecks(self):
        current_result_record={'draft':{'points':{}},'review':{'warnings':[],'rig_comparison':[]}}
        with patch.object(current_landmark_module,'execute_landmark_request',return_value=current_result_record) as current_gateway_mock:
            current_loaded_values=current_landmark_module.load_candidate_record('a',True,'a')
        current_gateway_mock.assert_called_once_with('load',{'id':'a'})
        self.assertFalse(current_loaded_values[-1])
