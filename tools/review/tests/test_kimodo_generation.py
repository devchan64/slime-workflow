"""Kimodo 입력·공용 명령·격리된 삭제·Gradio 구성 계약 검사."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS, validate_kimodo_request
from tools.review.common.management_gateway import resolve_management_command, MANAGEMENT_SERVICE_COMMANDS
from tools.review.domains.kimodo.generation import KimodoGenerationManager

class KimodoGenerationContractTests(unittest.TestCase):
    def setUp(self):
        self.current_request_record = {current_field_name:current_field_value for current_field_name,current_field_value in KIMODO_DEFAULT_SETTINGS.items() if current_field_name!='schema_version'}
        self.current_request_record['action']='generate'

    def test_invalid_inputs_rejected_before_queue(self):
        for current_field_name,current_field_value in [('openpose_scale_percent',True),('openpose_scale_percent',float('nan')),('openpose_scale_percent',0),('openpose_scale_percent',101),('frames',29),('frames',301),('steps',True),('seed',-1),('guidance_scale',float('nan')),('heading_degrees',181),('post_processing',1),('model','other'),('prompt','...'),('prompt','word '*101)]:
            with self.subTest(field=current_field_name,value=current_field_value),self.assertRaises(ValueError):
                validate_kimodo_request({**self.current_request_record,current_field_name:current_field_value})
        self.assertEqual(validate_kimodo_request(self.current_request_record)['images'],[])

    def test_horizontal_translation_preserves_motion(self):
        import numpy as np
        from generators.kimodo.motion_processing import remove_horizontal_translation
        from tools.review.ui.gradio.kimodo_app import build_kimodo_payload,restore_kimodo_inputs
        current_joint_names = ['Hips']+[f'joint_{current_joint_index}' for current_joint_index in range(76)]
        current_joint_positions = np.arange(3*77*3,dtype=float).reshape(3,77,3)
        current_root_positions = current_joint_positions[:,0].copy()
        current_rotation_values = np.ones((3,77,3,3))
        current_motion_output = dict(posed_joints=current_joint_positions,root_positions=current_root_positions,smooth_root_pos=current_root_positions.copy(),local_rot_mats=current_rotation_values)
        current_corrected_output = remove_horizontal_translation(current_motion_output,current_joint_names)
        np.testing.assert_allclose(current_corrected_output['posed_joints'][:,0,0],current_root_positions[0,0])
        np.testing.assert_allclose(current_corrected_output['posed_joints'][:,0,2],current_root_positions[0,2])
        np.testing.assert_array_equal(current_corrected_output['posed_joints'][:,:,1],current_joint_positions[:,:,1])
        np.testing.assert_allclose(current_corrected_output['posed_joints']-current_corrected_output['root_positions'][:,None,:],current_joint_positions-current_root_positions[:,None,:])
        np.testing.assert_array_equal(current_corrected_output['local_rot_mats'],current_rotation_values)
        np.testing.assert_array_equal(current_motion_output['posed_joints'],np.arange(3*77*3).reshape(3,77,3))
        current_legacy_request = dict(self.current_request_record)
        current_legacy_request.pop('remove_horizontal_motion')
        self.assertFalse(validate_kimodo_request(current_legacy_request)['remove_horizontal_motion'])
        self.assertFalse(restore_kimodo_inputs({'id':'old','request':current_legacy_request})[8])
        current_enabled_request = {**self.current_request_record,'remove_horizontal_motion':True}
        current_restored_inputs = restore_kimodo_inputs({'id':'new','request':current_enabled_request})[:-1]
        self.assertEqual(build_kimodo_payload(*current_restored_inputs),current_enabled_request)
        with self.assertRaises(ValueError):
            validate_kimodo_request({**self.current_request_record,'remove_horizontal_motion':1})

    def test_gateway_and_service_contract(self):
        self.assertEqual(resolve_management_command('kimodo','generate',self.current_request_record),('POST','/kimodo/jobs'))
        self.assertTrue({'history-delete','history-reset','prioritize','resume','cancel'} <= set(MANAGEMENT_SERVICE_COMMANDS['kimodo']))
        current_service_instance=KimodoGenerationManager()
        self.assertEqual(current_service_instance.route_prefix_value,'/kimodo')
        self.assertEqual(current_service_instance.select_generation_runner(),'generators/kimodo/worker.py')

    def test_gui_payload_restore_and_no_generation_during_build(self):
        from tools.review.ui.gradio.kimodo_app import build_kimodo_payload,restore_kimodo_inputs,build_kimodo_interface
        current_input_values=restore_kimodo_inputs({'id':'test','request':self.current_request_record})
        self.assertEqual(build_kimodo_payload(*current_input_values[:-1]),self.current_request_record)
        with self.assertRaises(ValueError):build_kimodo_payload('walk',30.5,100,42,2,0,False)
        def reject_generation_command(current_command_name,current_payload_record):
            if current_command_name=='generate':raise AssertionError('검사 중 생성 금지')
            return {'ready':False,'message':'격리 검사','items':[]}
        with patch('tools.review.ui.gradio.kimodo_app.normalize_kimodo_prompt',return_value='A person walks forward.'):
            current_interface_blocks=build_kimodo_interface('http://localhost:8770',reject_generation_command)
        current_component_labels=[current_component_record.get('props',{}).get('value') for current_component_record in current_interface_blocks.config['components']]
        for current_action_label in ('확인 후 대기열에 추가','추가하지 않기','선택 이력 삭제'):
            self.assertIn(current_action_label,current_component_labels)
        current_interface_blocks.close()

    def test_reset_removes_hidden_job_and_preserves_external_assets(self):
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_service_instance=KimodoGenerationManager()
            current_service_instance.job_storage_root=Path(current_temp_root)/'jobs'
            current_job_root=current_service_instance.job_storage_root/'2026-10-29_00-00-00-12345678'
            current_job_root.mkdir(parents=True)
            (current_job_root/'status.json').write_text(json.dumps({'status':'completed'}))
            (current_job_root/'.history-deleted').touch()
            (current_job_root/'motion.npz').write_bytes(b'test output')
            current_external_path=Path(current_temp_root)/'model.safetensors'
            current_external_path.write_bytes(b'preserve')
            with patch.object(current_service_instance,'history_storage_path',return_value=Path(current_temp_root)/'history'):
                current_cleanup_result=current_service_instance.reset_generation_history()
            self.assertEqual(current_cleanup_result['deleted_jobs'],1)
            self.assertGreater(current_cleanup_result['deleted_bytes'],0)
            self.assertFalse(current_job_root.exists())
            self.assertTrue(current_external_path.exists())

    def test_examples_update_only_prompt_and_frames(self):
        from tools.review.ui.gradio.kimodo_app import apply_kimodo_example,describe_kimodo_duration,load_kimodo_examples
        current_example_records=load_kimodo_examples()
        self.assertEqual(set(current_example_records),{'standing','male_runway_in_place','breathing'})
        self.assertEqual(apply_kimodo_example('standing')[:2],('A person stands still in a relaxed upright posture.',180))
        from tools.review.ui.gradio.kimodo_app import build_kimodo_payload
        current_example_payload = build_kimodo_payload(*apply_kimodo_example('male_runway_in_place'))
        self.assertEqual(current_example_payload['directions'],['front_left'])
        self.assertTrue(current_example_payload['remove_horizontal_motion'])
        self.assertEqual(current_example_payload['steps'],100)
        self.assertEqual(current_example_payload['heading_degrees'],0.0)
        self.assertIn('6초',describe_kimodo_duration(180))
        self.assertIn('정수',describe_kimodo_duration(30.5))
        self.assertIn('정수',describe_kimodo_duration(None))
        with self.assertRaises(ValueError):apply_kimodo_example('missing')

    def test_output_directions_validate_and_restore_legacy_history(self):
        from tools.review.ui.gradio.kimodo_app import restore_kimodo_inputs
        for current_direction_values in ([],['unknown'],['front','front'],'front',[1]):
            with self.assertRaises(ValueError):
                validate_kimodo_request({**self.current_request_record,'directions':current_direction_values})
        current_legacy_request=dict(self.current_request_record)
        current_legacy_request.pop('directions')
        self.assertEqual(validate_kimodo_request(current_legacy_request)['directions'],['front_left'])
        self.assertEqual(restore_kimodo_inputs({'id':'old','request':current_legacy_request})[7],['front_left'])
        self.assertEqual(validate_kimodo_request({**self.current_request_record,'directions':['front','right']})['directions'],['front','right'])

    def test_comparison_projection_and_missing_points(self):
        from PIL import Image
        from generators.kimodo.comparison import render_pose_comparison
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_attempt_root=Path(current_temp_directory)
            (current_attempt_root/'anny').mkdir()
            Image.new('RGBA',(512,512),(255,0,0,255)).save(current_attempt_root/'anny/frame.png')
            current_point_values=[0.0]*54
            current_point_values[3:9]=[100,100,1,200,200,1]
            current_image_record={'direction':'front','source_frame':1,'path':'frame.png','pose_keypoints_2d':current_point_values}
            current_comparison_image=render_pose_comparison(current_attempt_root,[current_image_record])
            self.assertEqual(current_comparison_image.size,(384,408))
            self.assertEqual(current_comparison_image.getpixel((20,200)),(0,0,0))
            self.assertNotEqual(current_comparison_image.getpixel((100,124)),(0,0,0))
            with self.assertRaisesRegex(ValueError,'COCO18'):
                render_pose_comparison(current_attempt_root,[{**current_image_record,'pose_keypoints_2d':[0]*3}])

    def test_comparison_result_preserves_original_download(self):
        from tools.review.ui.gradio.kimodo_app import render_kimodo_result
        current_result_markup=render_kimodo_result('id',{'video':'/kimodo/preview.mp4','comparison_video':'/kimodo/comparison.mp4','download':'/kimodo/frames.zip'},'http://localhost')
        self.assertIn('src="/kimodo/comparison.mp4"',current_result_markup)
        self.assertIn('href="/kimodo/preview.mp4"',current_result_markup)
        self.assertIn('/kimodo/frames.zip',current_result_markup)
        self.assertIn('리타게팅 후',current_result_markup)

    def test_pose_render_colors_and_missing_joints(self):
        import numpy as np
        from generators.kimodo.pose_rendering import render_body_pose_image
        current_pose_points = np.zeros((18,3))
        current_pose_points[1] = (50,50,1)
        current_pose_points[0] = (50,150,1)
        current_pose_image = render_body_pose_image(current_pose_points)
        self.assertEqual(current_pose_image.getpixel((50,100)),(0,0,153))
        self.assertEqual(current_pose_image.getpixel((50,50)),(255,85,0))
        self.assertEqual(current_pose_image.getpixel((50,150)),(255,0,0))
        current_pose_points[:] = 0
        current_pose_points[0] = (50,50,1)
        current_pose_points[14] = (150,50,1)
        current_pose_points[15] = (50,150,1)
        current_pose_image = render_body_pose_image(current_pose_points)
        self.assertEqual(current_pose_image.getpixel((100,50)),(51,0,153))
        self.assertEqual(current_pose_image.getpixel((50,100)),(153,0,153))
        current_pose_points[14:,2] = 0
        current_pose_image = render_body_pose_image(current_pose_points)
        self.assertEqual(current_pose_image.getpixel((100,50)),(0,0,0))
        self.assertEqual(current_pose_image.getpixel((50,100)),(0,0,0))

    def test_soma_pose_preserves_motion_and_missing_face(self):
        import numpy as np
        from generators.kimodo.soma_pose import project_soma_body_points, SOMA_BODY_JOINT_NAMES
        current_joint_names=list(dict.fromkeys(current_joint_name for current_joint_name in SOMA_BODY_JOINT_NAMES if current_joint_name))
        current_joint_names += [f'Unused{current_joint_index}' for current_joint_index in range(77-len(current_joint_names))]
        current_joint_positions=np.zeros((2,77,3))
        current_joint_positions[1,:,0]=1
        current_pose_points=project_soma_body_points(current_joint_positions,current_joint_names,'front')
        self.assertTrue(np.all(current_pose_points[:,[0,16,17]]==0))
        self.assertTrue(np.all(current_pose_points[:,[14,15],2]==1))
        self.assertGreater(current_pose_points[1,4,0],current_pose_points[0,4,0])
        np.testing.assert_allclose(current_pose_points[:,1,:2],(current_pose_points[:,2,:2]+current_pose_points[:,5,:2])/2)
        current_scaled_points=project_soma_body_points(current_joint_positions,current_joint_names,'front',current_scale_percent=85)
        np.testing.assert_allclose(current_scaled_points[:,1:16,:2]-256,(current_pose_points[:,1:16,:2]-256)*0.85)
        np.testing.assert_array_equal(current_scaled_points[:,:,2],current_pose_points[:,:,2])
        current_joint_positions[0,0,0]=float('nan')
        with self.assertRaisesRegex(ValueError,'위치 계약'):
            project_soma_body_points(current_joint_positions,current_joint_names,'front')
