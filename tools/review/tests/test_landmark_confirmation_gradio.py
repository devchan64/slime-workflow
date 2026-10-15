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

    def test_unloaded_source_cannot_save_candidate(self):
        self.assertFalse(current_landmark_module.update_candidate_save_readiness(None)['interactive'])
        self.assertFalse(current_landmark_module.update_candidate_save_readiness({'source': {}, 'points': {}})['interactive'])
        self.assertTrue(current_landmark_module.update_candidate_save_readiness({'source': {}, 'points': {'left_shoulder_center': {}}})['interactive'])
        with patch.object(current_landmark_module, 'execute_landmark_request') as current_gateway_mock:
            with self.assertRaisesRegex(gr.Error, '원본을 불러온 뒤'):
                current_landmark_module.save_candidate_record(None)
            with self.assertRaisesRegex(gr.Error, '최소 한 개 기준점'):
                current_landmark_module.save_candidate_record({'source': {}, 'points': {}})
            current_gateway_mock.assert_not_called()

    def test_candidate_actions_follow_source_and_selected_point(self):
        current_point_name = 'left_shoulder_center'
        for current_draft_record, current_expected_values in (
            (None, [False, False, False]),
            ({'points': {}}, [True, False, False]),
            ({'points': {current_point_name: {}}}, [True, True, True]),
            ({'points': {'right_shoulder_center': {}}}, [True, False, False]),
        ):
            with self.subTest(draft=current_draft_record):
                current_updates = current_landmark_module.update_candidate_action_readiness(current_draft_record, current_point_name)
                self.assertEqual([current_update['interactive'] for current_update in current_updates], current_expected_values)

    def test_gateway_error_remains_visible_and_draft_unchanged(self):
        import copy
        current_draft_record = {'source': {}, 'points': {}}
        current_original_draft = copy.deepcopy(current_draft_record)
        with patch.object(current_landmark_module, 'execute_remote_management_command', side_effect=ValueError('기준점 지정 근거가 필요합니다.')) as current_gateway_mock:
            with self.assertRaisesRegex(gr.Error, '기준점 지정 근거가 필요합니다.'):
                current_landmark_module.update_candidate_point(current_draft_record, 'left_shoulder_center', 0, 0, 0, 'manual_xyz', '')
            current_gateway_mock.assert_called_once()
        self.assertEqual(current_draft_record, current_original_draft)

    def test_surface_pick_requires_finite_selected_coordinates(self):
        import subprocess
        current_script_text="const assert=require('node:assert/strict');global.window={};const checkReady="+current_landmark_module.LANDMARK_PICK_READINESS_SCRIPT+";"
        current_script_text+="assert.equal(checkReady()[0].interactive,false);for(const point of [null,[],[1,2],[1,2,NaN],[1,2,Infinity],['1',2,3]]){window.currentAnnyLandmarkViewer={currentPickedPoint:point};assert.equal(checkReady()[0].interactive,false);}window.currentAnnyLandmarkViewer={currentPickedPoint:[0,-1,2]};assert.equal(checkReady()[0].interactive,true);"
        subprocess.run(['node','-e',current_script_text],check=True,capture_output=True,text=True)
        current_interface_blocks=current_landmark_module.build_landmark_interface()
        current_pick_button=next(current_component for current_component in current_interface_blocks.blocks.values() if isinstance(current_component,gr.Button) and current_component.value=='선택 좌표 읽기')
        self.assertFalse(current_pick_button.interactive)
        current_timer_event=next(current_event for current_event in current_interface_blocks.config['dependencies'] if current_event.get('js')==current_landmark_module.LANDMARK_PICK_READINESS_SCRIPT)
        self.assertFalse(current_timer_event['queue'])
        self.assertFalse(current_timer_event['backend_fn'])
