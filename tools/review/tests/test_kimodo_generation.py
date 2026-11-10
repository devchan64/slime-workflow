"""Kimodo 입력·공용 명령·격리된 삭제·Gradio 구성 계약 검사."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS, validate_kimodo_request
from tools.review.common.management_gateway import resolve_management_command, MANAGEMENT_SERVICE_COMMANDS
from tools.review.domains.kimodo.generation import KimodoGenerationManager


def write_keyframe_test_previews(current_attempt_root,current_frame_count):
    import hashlib
    from PIL import Image
    current_frame_hashes=[]
    for current_frame_index in range(current_frame_count):
        current_frame_path=current_attempt_root/f'output-{current_frame_index:03d}.png'
        Image.new('RGB',(8,8),(current_frame_index,0,0)).save(current_frame_path)
        current_frame_hashes.append(hashlib.sha256(current_frame_path.read_bytes()).hexdigest())
    return current_frame_hashes


class KimodoGenerationContractTests(unittest.TestCase):
    def test_multiview_gui_payload_and_history_roundtrip(self):
        from PIL import Image
        from tools.review.ui.gradio.kimodo_app import build_kimodo_payload,restore_kimodo_inputs
        current_view_text='45 0 135 90 225 315 180 270'
        with tempfile.TemporaryDirectory() as current_temporary_root:
            current_job_root=Path(current_temporary_root)/'trial'
            current_job_root.mkdir()
            current_image_path=current_job_root/'reference-1.png'
            Image.new('RGB',(64,64),'white').save(current_image_path)
            current_inputs=('stand still',90,10,42,2,0,True,['front'],False,True,[str(current_image_path)],85,False,False,'',None,[],0,current_view_text)
            current_payload_record=build_kimodo_payload(*current_inputs)
            self.assertEqual(current_payload_record['proportion_multiview_angles'],[45,0,135,90,225,315,180,270])
            current_saved_request={**current_payload_record,'references':['reference-1.png']}
            current_saved_request.pop('proportion_images')
            with patch('tools.review.ui.gradio.kimodo_app.KIMODO_JOB_STORAGE',Path(current_temporary_root)):
                current_restored_values=restore_kimodo_inputs({'id':'trial','request':current_saved_request})
            self.assertEqual(build_kimodo_payload(*current_restored_values[:-1])['proportion_multiview_angles'],current_payload_record['proportion_multiview_angles'])
            with self.assertRaisesRegex(ValueError,'각도 8개'):
                build_kimodo_payload(*current_inputs[:-1],'0 45')

    def test_reference_joint_edits_require_matching_image_and_unique_target(self):
        import base64,hashlib,io
        from PIL import Image
        current_image_buffer=io.BytesIO()
        Image.new('RGB',(64,64),'white').save(current_image_buffer,format='PNG')
        current_image_bytes=current_image_buffer.getvalue()
        current_edit_record={'image':1,'person':1,'joint':2,'original':[10,10],'edited':[10,12],'image_sha256':hashlib.sha256(current_image_bytes).hexdigest()}
        current_request_record={**self.current_request_record,'proportion_images':[base64.b64encode(current_image_bytes).decode()],'proportion_joint_edits':[current_edit_record]}
        self.assertEqual(validate_kimodo_request(current_request_record)['proportion_joint_edits'],[current_edit_record])
        with self.assertRaisesRegex(ValueError,'이미지'):
            validate_kimodo_request({**current_request_record,'proportion_joint_edits':[{**current_edit_record,'image_sha256':'0'*64}]})
        with self.assertRaisesRegex(ValueError,'중복'):
            validate_kimodo_request({**current_request_record,'proportion_joint_edits':[current_edit_record,current_edit_record]})
        current_view_angles=[45,0,135,90,225,315,180,270]
        self.assertEqual(validate_kimodo_request({**current_request_record,'proportion_multiview_angles':current_view_angles})['proportion_multiview_angles'],current_view_angles)
        with self.assertRaisesRegex(ValueError,'각도 8개'):
            validate_kimodo_request({**current_request_record,'proportion_multiview_angles':[0,45]})

    def test_camera_elevation_rotation_and_input_validation(self):
        import numpy as np
        from generators.kimodo.soma_render import build_soma_camera_rotation
        from generators.kimodo.soma_pose import project_recorded_camera_points
        np.testing.assert_allclose(build_soma_camera_rotation(0,0),np.eye(3))
        for current_elevation_angle in (15,30):
            current_rotation_matrix=build_soma_camera_rotation(0,current_elevation_angle)
            current_camera_record={'rotation_matrix':current_rotation_matrix.tolist(),'center_position':[0,0,0],'half_height':1,'width':832,'height':480}
            current_points=project_recorded_camera_points(np.array([[0,0,0],[0,0,1]]),current_camera_record)
            self.assertGreater(current_points[1,1],current_points[0,1])
            self.assertEqual(validate_kimodo_request({**self.current_request_record,'camera_elevation_degrees':current_elevation_angle})['camera_elevation_degrees'],current_elevation_angle)
            from tools.review.ui.gradio.kimodo_app import build_kimodo_payload,restore_kimodo_inputs
            current_saved_request={**self.current_request_record,'camera_elevation_degrees':current_elevation_angle}
            self.assertEqual(build_kimodo_payload(*restore_kimodo_inputs({'id':'elevation-test','request':current_saved_request})[:-1])['camera_elevation_degrees'],current_elevation_angle)
        for current_bad_angle in (-15,1,45,15.0,True):
            with self.assertRaises(ValueError):
                validate_kimodo_request({**self.current_request_record,'camera_elevation_degrees':current_bad_angle})
    def setUp(self):
        self.current_request_record = {current_field_name:current_field_value for current_field_name,current_field_value in KIMODO_DEFAULT_SETTINGS.items() if current_field_name!='schema_version'}
        self.current_request_record['action']='generate'

    def test_invalid_inputs_rejected_before_queue(self):
        for current_field_name,current_field_value in [('openpose_scale_percent',True),('openpose_scale_percent',float('nan')),('openpose_scale_percent',0),('openpose_scale_percent',101),('frames',29),('frames',301),('steps',True),('seed',-1),('guidance_scale',float('nan')),('heading_degrees',181),('post_processing',1),('model','other'),('prompt','...'),('prompt','word '*101)]:
            with self.subTest(field=current_field_name,value=current_field_value),self.assertRaises(ValueError):
                validate_kimodo_request({**self.current_request_record,current_field_name:current_field_value})
        self.assertEqual(validate_kimodo_request(self.current_request_record)['images'],[])

    def test_motion_sequence_contract(self):
        from generators.kimodo.motion_sequence import resolve_motion_segments
        current_prompt_text='A person stands.\nA person sits down.\nA person stands up.'
        self.assertEqual(resolve_motion_segments(current_prompt_text,300,[90,120,90])[1],[90,120,90])
        for current_segment_frames in ([100,100], [90,90,90], [True,149,150]):
            with self.assertRaises(ValueError):
                resolve_motion_segments(current_prompt_text,300,current_segment_frames)
        current_sequence_request={**self.current_request_record,'prompt':current_prompt_text,'frames':300,'segment_frames':[90,120,90]}
        self.assertEqual(validate_kimodo_request(current_sequence_request)['segment_frames'],[90,120,90])
        from tools.review.ui.gradio.kimodo_app import build_kimodo_payload,restore_kimodo_inputs
        self.assertEqual(build_kimodo_payload(*restore_kimodo_inputs({'id':'sequence','request':current_sequence_request})[:-1]),current_sequence_request)

    def test_keyframe_snapshot_preserves_selected_frame(self):
        import numpy as np
        from tools.review.domains.kimodo.keyframe_storage import KIMODO_FRAME_ARRAY_SHAPES, save_kimodo_keyframe_record
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_temp_root = Path(current_temp_directory)
            current_job_identifier = '2026-11-06_12-00-00-12345678'
            current_attempt_identifier = 'a' * 32
            current_attempt_root = current_temp_root/'jobs'/current_job_identifier/'attempts'/current_attempt_identifier
            current_attempt_root.mkdir(parents=True)
            (current_attempt_root.parent.parent/'status.json').write_text(json.dumps({'status': 'completed'}))
            current_frame_hashes=write_keyframe_test_previews(current_attempt_root,3)
            (current_attempt_root/'result.json').write_text(json.dumps({'attempt': current_attempt_identifier, 'frames': 3, 'fps': 30, 'frame_sha256':current_frame_hashes}))
            (current_attempt_root/'skeleton.json').write_text(json.dumps({'skeleton': 'somaskel77', 'fps': 30, 'joint_names': list(range(77)), 'parents': list(range(77))}))
            np.savez_compressed(current_attempt_root/'motion.npz', **{current_name: np.arange(3*np.prod(current_shape)).reshape((3,*current_shape)) for current_name,current_shape in KIMODO_FRAME_ARRAY_SHAPES.items()})
            current_store_root = current_temp_root/'keyframes'
            current_record = save_kimodo_keyframe_record(current_job_identifier,current_attempt_identifier,2,'복싱',current_job_storage=current_temp_root/'jobs',current_keyframe_storage=current_store_root)
            with np.load(current_store_root/current_record['id']/'motion.npz') as current_saved_arrays:
                self.assertEqual(current_saved_arrays['root_positions'].tolist(), [[3,4,5]])
            self.assertEqual(current_record['source_frame'], 2)
            self.assertEqual(current_record['tag'], '복싱')
            (current_attempt_root/'result.json').write_text(json.dumps({'attempt': current_attempt_identifier, 'frames': 3, 'fps': 30, 'remove_horizontal_motion': True, 'frame_sha256':current_frame_hashes}))
            with self.assertRaisesRegex(ValueError,'motion-in-place'):
                save_kimodo_keyframe_record(current_job_identifier,current_attempt_identifier,2,'보정',current_job_storage=current_temp_root/'jobs',current_keyframe_storage=current_store_root)
            np.savez_compressed(current_attempt_root/'motion-in-place.npz', **{current_name: np.full((3,*current_shape),7) for current_name,current_shape in KIMODO_FRAME_ARRAY_SHAPES.items()})
            current_corrected_record = save_kimodo_keyframe_record(current_job_identifier,current_attempt_identifier,2,'보정',current_job_storage=current_temp_root/'jobs',current_keyframe_storage=current_store_root)
            self.assertEqual(current_corrected_record['source_motion'],'motion-in-place.npz')
            with np.load(current_store_root/current_corrected_record['id']/'motion.npz') as current_saved_arrays:
                self.assertEqual(current_saved_arrays['root_positions'].tolist(), [[7,7,7]])
            with self.assertRaises(ValueError):
                save_kimodo_keyframe_record(current_job_identifier,current_attempt_identifier,4,'복싱',current_job_storage=current_temp_root/'jobs',current_keyframe_storage=current_store_root)
            import shutil
            from tools.review.domains.kimodo.keyframe_storage import load_kimodo_keyframe_snapshot
            shutil.rmtree(current_attempt_root.parent.parent)
            self.assertTrue((current_store_root/current_record['id']/'preview.png').is_file())
            self.assertEqual(load_kimodo_keyframe_snapshot(current_store_root,current_record['id'])[0]['tag'], '복싱')

    def test_keyframe_placements_snapshot_and_constraints(self):
        import numpy as np
        import shutil
        from tools.review.domains.kimodo.keyframe_storage import KIMODO_FRAME_ARRAY_SHAPES, save_kimodo_keyframe_record, snapshot_kimodo_keyframes, build_kimodo_keyframe_constraints, validate_kimodo_keyframe_placements
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_temp_root = Path(current_temp_directory)
            current_job_identifier = '2026-11-06_12-00-00-12345678'
            current_attempt_identifier = 'a'*32
            current_attempt_root = current_temp_root/'jobs'/current_job_identifier/'attempts'/current_attempt_identifier
            current_attempt_root.mkdir(parents=True)
            (current_attempt_root.parent.parent/'status.json').write_text(json.dumps({'status':'completed'}))
            current_frame_hashes=write_keyframe_test_previews(current_attempt_root,2)
            (current_attempt_root/'result.json').write_text(json.dumps({'attempt':current_attempt_identifier,'frames':2,'fps':30,'frame_sha256':current_frame_hashes}))
            (current_attempt_root/'skeleton.json').write_text(json.dumps({'skeleton':'somaskel77','fps':30,'joint_names':[str(current_index) for current_index in range(77)],'parents':list(range(77))}))
            current_source_arrays = {current_name:np.zeros((2,*current_shape)) for current_name,current_shape in KIMODO_FRAME_ARRAY_SHAPES.items()}
            current_source_arrays['local_rot_mats'][:] = np.eye(3)
            current_source_arrays['global_rot_mats'][:] = np.eye(3)
            current_source_arrays['root_positions'][:] = [[2,1,3],[3,1,5]]
            current_source_arrays['smooth_root_pos'][:] = [[2,1,3],[3,1,5]]
            np.savez_compressed(current_attempt_root/'motion.npz',**current_source_arrays)
            current_store_root = current_temp_root/'keyframes'
            current_first_record = save_kimodo_keyframe_record(current_job_identifier,current_attempt_identifier,1,'시작',current_job_storage=current_temp_root/'jobs',current_keyframe_storage=current_store_root)
            current_last_record = save_kimodo_keyframe_record(current_job_identifier,current_attempt_identifier,2,'종료',current_job_storage=current_temp_root/'jobs',current_keyframe_storage=current_store_root)
            current_placements = validate_kimodo_keyframe_placements([{'id':current_last_record['id'],'frame':30},{'id':current_first_record['id'],'frame':1}],30)
            current_new_job_root = current_temp_root/'new-job'
            current_new_job_root.mkdir()
            current_snapshots = snapshot_kimodo_keyframes(current_new_job_root,current_placements,current_keyframe_storage=current_store_root)
            shutil.rmtree(current_store_root)
            current_records = build_kimodo_keyframe_constraints(current_new_job_root,{'frames':30,'keyframes':current_placements,'keyframe_snapshots':current_snapshots})
            self.assertEqual(current_records[0]['frame_indices'],[0,29])
            self.assertEqual(current_records[0]['root_positions'],[[0.0,1.0,0.0],[1.0,1.0,2.0]])
            with self.assertRaises(ValueError):
                validate_kimodo_keyframe_placements([{'id':current_first_record['id'],'frame':1},{'id':current_last_record['id'],'frame':1}],30)
            (current_new_job_root/'keyframes'/current_first_record['id']/'motion.npz').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'해시'):
                build_kimodo_keyframe_constraints(current_new_job_root,{'frames':30,'keyframes':current_placements,'keyframe_snapshots':current_snapshots})

    def test_retired_constraints_are_rejected(self):
        from tools.review.ui.gradio.kimodo_app import build_kimodo_payload,restore_kimodo_inputs
        current_legacy_request = {**self.current_request_record,'pose_constraints':[{'frame':0}]}
        with self.assertRaises(ValueError):
            validate_kimodo_request(current_legacy_request)
        current_restored_inputs = restore_kimodo_inputs({'id':'legacy','request':current_legacy_request})[:-1]
        self.assertNotIn('pose_constraints',build_kimodo_payload(*current_restored_inputs))

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

    def test_attached_reference_cannot_be_silently_ignored(self):
        from tools.review.ui.gradio.kimodo_app import build_kimodo_payload,check_kimodo_readiness
        with self.assertRaisesRegex(ValueError,'비율 적용이 꺼져'):
            build_kimodo_payload('A person walks.',90,20,42,2,0,False,['front_left'],False,False,['unused.png'])
        self.assertFalse(check_kimodo_readiness(True,'walk',['front_left'],False,['unused.png']))
        self.assertTrue(check_kimodo_readiness(True,'walk',['front_left'],True,['unused.png']))

    def test_gateway_and_service_contract(self):
        self.assertEqual(resolve_management_command('kimodo','generate',self.current_request_record),('POST','/kimodo/jobs'))
        self.assertEqual(resolve_management_command('kimodo','keyframe-save',{}),('POST','/kimodo/keyframes/save'))
        self.assertEqual(resolve_management_command('kimodo','keyframe-list',{}),('POST','/kimodo/keyframes/list'))
        self.assertTrue({'history-delete','history-reset','prioritize','resume','cancel'} <= set(MANAGEMENT_SERVICE_COMMANDS['kimodo']))
        current_service_instance=KimodoGenerationManager()
        self.assertEqual(current_service_instance.route_prefix_value,'/kimodo')
        self.assertEqual(current_service_instance.select_generation_runner(),'generators/kimodo/worker.py')

    def test_keyframe_gateway_save_list_and_generation_snapshot(self):
        import io
        import numpy as np
        from email.message import Message
        from tools.review.common.management_gateway import execute_management_command
        from tools.review.domains.kimodo.keyframe_storage import KIMODO_FRAME_ARRAY_SHAPES
        class CaptureGatewayResponse:
            def __init__(self):
                self.headers = Message()
                self.wfile = io.BytesIO()
                self.status = None
            def send_response(self,current_status_value): self.status = current_status_value
            def send_header(self,current_name_value,current_header_value): pass
            def end_headers(self): pass
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_temp_root=Path(current_temp_directory)
            current_service_instance=KimodoGenerationManager()
            current_service_instance.job_storage_root=current_temp_root/'jobs'
            current_service_instance.keyframe_storage_root=current_temp_root/'keyframes'
            current_job_identifier='2026-11-06_12-00-00-12345678'
            current_attempt_identifier='a'*32
            current_attempt_root=current_service_instance.job_storage_root/current_job_identifier/'attempts'/current_attempt_identifier
            current_attempt_root.mkdir(parents=True)
            (current_attempt_root.parent.parent/'status.json').write_text(json.dumps({'status':'completed'}))
            current_frame_hashes=write_keyframe_test_previews(current_attempt_root,3)
            (current_attempt_root/'result.json').write_text(json.dumps({'attempt':current_attempt_identifier,'frames':3,'fps':30,'frame_sha256':current_frame_hashes}))
            (current_attempt_root/'skeleton.json').write_text(json.dumps({'skeleton':'somaskel77','fps':30,'joint_names':[str(current_index) for current_index in range(77)],'parents':list(range(77))}))
            current_motion_arrays={current_name:np.zeros((3,*current_shape)) for current_name,current_shape in KIMODO_FRAME_ARRAY_SHAPES.items()}
            current_motion_arrays['local_rot_mats'][:]=np.eye(3)
            np.savez_compressed(current_attempt_root/'motion.npz',**current_motion_arrays)
            current_handler_values={'kimodo':current_service_instance.handle_image_request}
            current_gateway_response=CaptureGatewayResponse()
            execute_management_command('kimodo','keyframe-save',{'job_id':current_job_identifier,'attempt_id':current_attempt_identifier,'frame':2,'tag':'가드'},gateway_request_handler=current_gateway_response,service_handler_values=current_handler_values)
            self.assertEqual(current_gateway_response.status,200)
            current_saved_record=json.loads(current_gateway_response.wfile.getvalue())
            current_gateway_response=CaptureGatewayResponse()
            execute_management_command('kimodo','keyframe-list',{},gateway_request_handler=current_gateway_response,service_handler_values=current_handler_values)
            self.assertEqual(json.loads(current_gateway_response.wfile.getvalue())['records'][0]['id'],current_saved_record['id'])
            current_gateway_response=CaptureGatewayResponse()
            execute_management_command('kimodo','keyframe-preview',{'id':current_saved_record['id']},gateway_request_handler=current_gateway_response,service_handler_values=current_handler_values)
            self.assertEqual(current_gateway_response.status,200)
            import base64
            self.assertEqual(base64.b64decode(json.loads(current_gateway_response.wfile.getvalue())['image_base64']),(current_attempt_root/'output-001.png').read_bytes())
            current_generation_request={**self.current_request_record,'post_processing':True,'keyframes':[{'id':current_saved_record['id'],'frame':1},{'id':current_saved_record['id'],'frame':30}]}
            current_validated_request=current_service_instance.validate_generation_request(current_generation_request)
            current_new_job_root=current_temp_root/'new-job'
            current_new_job_root.mkdir()
            current_saved_request=current_service_instance.save_generation_attachments(current_new_job_root,current_validated_request)
            self.assertEqual(len(current_saved_request['keyframe_snapshots']),2)
            self.assertTrue((current_new_job_root/'keyframes'/current_saved_record['id']/'motion.npz').is_file())
            with self.assertRaisesRegex(ValueError,'후처리'):
                current_service_instance.validate_generation_request({**current_generation_request,'post_processing':False})
            current_sequence_request = {**current_generation_request,'prompt':'A person stands.\nA person raises an arm.','segment_frames':[30,60]}
            self.assertEqual(current_service_instance.validate_generation_request(current_sequence_request)['segment_frames'],[30,60])

    def test_empty_sequence_constraint_crop_is_safe_and_restored(self):
        import torch
        from generators.kimodo.sequence_constraints import support_empty_sequence_constraints
        class TestConstraint:
            def __init__(self):
                self.frame_indices = torch.tensor([0,35])
            def crop_move(self, current_start_frame, current_end_frame):
                return (current_start_frame,current_end_frame)
        current_original_method = TestConstraint.crop_move
        current_constraint_value = TestConstraint()
        with support_empty_sequence_constraints(TestConstraint):
            self.assertEqual(current_constraint_value.crop_move(0,30),(0,30))
            current_empty_constraint = current_constraint_value.crop_move(40,60)
            self.assertIsInstance(current_empty_constraint,TestConstraint)
            self.assertEqual(current_empty_constraint.frame_indices.numel(),0)
            self.assertIsNone(current_empty_constraint.update_constraints({},{}))
        self.assertIs(TestConstraint.crop_move,current_original_method)

    def test_keyframe_gui_cli_request_contract(self):
        import contextlib
        import io
        from tools.review.common.management_gateway import execute_gateway_arguments
        from tools.review.ui.gradio.kimodo_app import build_kimodo_payload,restore_kimodo_inputs,check_kimodo_readiness
        current_keyframe_identifier='b'*32
        current_request_record={**self.current_request_record,'post_processing':True,'keyframes':[{'id':current_keyframe_identifier,'frame':1},{'id':current_keyframe_identifier,'frame':30}]}
        current_restored_values=restore_kimodo_inputs({'id':'existing','request':current_request_record})
        self.assertEqual(build_kimodo_payload(*current_restored_values[:-1]),current_request_record)
        self.assertTrue(check_kimodo_readiness(True,'walk',['front'],False,None,[[current_keyframe_identifier,1]],True,'',None,False))
        self.assertFalse(check_kimodo_readiness(True,'walk',['front'],False,None,[[current_keyframe_identifier,1]],False,'',None,False))
        self.assertFalse(check_kimodo_readiness(True,'walk',['front'],False,None,[[current_keyframe_identifier,1]],True,'',None,True))
        with self.assertRaisesRegex(ValueError,'수평 이동'):
            validate_kimodo_request({**current_request_record,'remove_horizontal_motion':True})
        with self.assertRaisesRegex(ValueError,'양 끝'):
            validate_kimodo_request({**current_request_record,'endpoint_pose_id':'relaxed-standing-v1'})
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_payload_path=Path(current_temp_directory)/'request.json'
            current_payload_record={'job_id':'2026-11-06_12-00-00-12345678','attempt_id':'a'*32,'frame':2,'tag':'가드'}
            current_payload_path.write_text(json.dumps(current_payload_record),encoding='utf-8')
            with patch('tools.review.common.management_gateway.call_management_api',return_value={'id':'saved'}) as current_api_mock,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(execute_gateway_arguments('kimodo',['keyframe-save','--payload-file',str(current_payload_path)]),0)
            self.assertEqual(current_api_mock.call_args.args[1:3],('/kimodo/keyframes/save',current_payload_record))

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
        self.assertEqual(set(current_example_records),{'male_runway_in_place','relaxed_shoulder_width_standing','male_floor_rest_cycle','boxing_jab_straight_combination'})
        from tools.review.ui.gradio.kimodo_app import build_kimodo_payload
        current_standing_payload = build_kimodo_payload(*apply_kimodo_example('relaxed_shoulder_width_standing'))
        self.assertEqual(current_standing_payload['frames'],180)
        self.assertEqual(current_standing_payload['seed'],1681778616)
        self.assertEqual(current_standing_payload['prompt'],'A man stands still like a male fashion model.')
        self.assertEqual(current_standing_payload['directions'],['front_right_30'])
        self.assertFalse(current_standing_payload['remove_horizontal_motion'])
        current_example_payload = build_kimodo_payload(*apply_kimodo_example('male_runway_in_place'))
        self.assertEqual(current_example_payload['directions'],['front_right_30'])
        self.assertTrue(current_example_payload['remove_horizontal_motion'])
        self.assertEqual(current_example_payload['steps'],100)
        self.assertEqual(current_example_payload['heading_degrees'],0.0)
        from tools.review.ui.gradio.kimodo_app import apply_complete_kimodo_example
        import hashlib
        current_standing_values = apply_complete_kimodo_example('relaxed_shoulder_width_standing')
        current_standing_request = build_kimodo_payload(*current_standing_values)
        self.assertEqual(current_standing_request['openpose_scale_percent'],85)
        self.assertTrue(current_standing_request['post_processing'])
        self.assertFalse(current_standing_request['pose_include_hands'])
        self.assertFalse(current_standing_request['pose_include_face'])
        self.assertTrue(current_standing_values[9])
        from tools.review.ui.gradio.kimodo_app import load_proportion_examples
        self.assertEqual(Path(load_proportion_examples()['character_eight_directions']['images'][0]),Path('baseline/player/default/default-eight-directions-v1.png').resolve())
        self.assertEqual(hashlib.sha256(Path(current_standing_values[10][0]).read_bytes()).digest(),hashlib.sha256(Path(load_proportion_examples()['character_eight_directions']['images'][0]).read_bytes()).digest())
        current_combination_values = apply_complete_kimodo_example('boxing_jab_straight_combination')
        current_combination_request = build_kimodo_payload(*current_combination_values)
        self.assertFalse(current_combination_request['pose_include_hands'])
        self.assertEqual(current_combination_request['seed'],404)
        self.assertEqual(current_combination_request['directions'],['front','front_right_15'])
        self.assertEqual(current_combination_request['camera_elevation_degrees'],30)
        self.assertEqual(current_combination_request['frames'],40)
        self.assertNotIn('keyframes',current_combination_request)
        self.assertEqual(current_combination_request['prompt'],'A boxer throws a quick left jab, then pivots on the right foot and throws a right straight punch. Both hands return to guard.')
        self.assertIn('6초',describe_kimodo_duration(180))
        self.assertIn('정수',describe_kimodo_duration(30.5))
        self.assertIn('정수',describe_kimodo_duration(None))
        with self.assertRaises(ValueError):apply_kimodo_example('missing')

    def test_collapsed_input_summary_reports_conflicts_and_counts(self):
        from tools.review.ui.gradio.kimodo_app import describe_kimodo_input_summary
        current_summary=describe_kimodo_input_summary(True,['reference.png'],[['keyframe',1]],True,False)
        for current_expected in ('신체 비율: 적용 · 1장','키프레임: 1개','공식 후처리: 켜짐','수평 이동 제거: 꺼짐'):
            self.assertIn(current_expected,current_summary)
        self.assertIn('설정 확인 필요',describe_kimodo_input_summary(False,['reference.png'],[],False,False))
        current_full_summary=describe_kimodo_input_summary(True,['/tmp/body.png'],[],True,False,202,180,['front_right_30'],15)
        for current_expected_text in ('시드: 202','180프레임','전방 우측 -30°','고도: 15°','body.png'):
            self.assertIn(current_expected_text,current_full_summary)

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
        self.assertEqual(validate_kimodo_request({**self.current_request_record,'directions':['front_left_30','front_right_30']})['directions'],['front_left_30','front_right_30'])
        self.assertEqual(validate_kimodo_request({**self.current_request_record,'directions':['front','front_right_15']})['directions'],['front','front_right_15'])

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

    def test_result_previews_explain_status_and_conversion(self):
        from tools.review.ui.gradio.kimodo_app import render_kimodo_result
        current_status_record = {'video':'/preview.mp4','download':'/frames.zip','direct_pose_status':'completed','dwpose_status':'warning','dwpose_error':'19프레임 검출 실패','preprocess_videos':{'SOMA 렌더 · front':'/render.mp4','직접 포즈 · front':'/direct.mp4'}}
        current_result_markup = render_kimodo_result('job',current_status_record,'http://localhost')
        for current_expected_text in ('직접 포즈: 생성 완료','DWPose: 생성 오류','19프레임 검출 실패','원본 동작 검수용','SOMA 관절을 투영','16fps로 변환'):
            self.assertIn(current_expected_text,current_result_markup)
        self.assertNotIn('DWPose 포즈 · front',current_result_markup)

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

class KimodoPoseLibraryTests(unittest.TestCase):
    def test_registered_pose_endpoints_and_request_roundtrip(self):
        from generators.kimodo.pose_library import load_soma_pose_arrays,build_soma_endpoint_records
        from tools.review.ui.gradio.kimodo_app import build_kimodo_payload,restore_kimodo_inputs,apply_complete_kimodo_example,load_kimodo_examples
        current_pose_record,current_motion_arrays=load_soma_pose_arrays('relaxed-standing-v1')
        self.assertEqual(current_motion_arrays['posed_joints'].shape,(1,77,3))
        current_constraint_record=build_soma_endpoint_records(current_pose_record['id'],210)[0]
        self.assertEqual(current_constraint_record['frame_indices'],[0,209])
        self.assertEqual(current_constraint_record['local_joints_rot'][0],current_constraint_record['local_joints_rot'][1])
        self.assertEqual(current_constraint_record['root_positions'][0],current_constraint_record['root_positions'][1])
        current_request_record={current_field_name:current_field_value for current_field_name,current_field_value in KIMODO_DEFAULT_SETTINGS.items() if current_field_name!='schema_version'}
        current_request_record.update(action='generate',endpoint_pose_id=current_pose_record['id'],post_processing=True,heading_degrees=0)
        current_migrated_request=build_kimodo_payload(*restore_kimodo_inputs({'id':'test','request':current_request_record})[:-1])
        self.assertNotIn('endpoint_pose_id',current_migrated_request)
        self.assertEqual(current_migrated_request['keyframes'],[{'id':'b0000000000000000000000000000004','frame':1},{'id':'b0000000000000000000000000000004','frame':current_request_record['frames']}])
        self.assertEqual(validate_kimodo_request(current_request_record)['keyframes'],current_migrated_request['keyframes'])
        from tools.review.domains.kimodo.keyframe_storage import snapshot_kimodo_keyframes,build_kimodo_keyframe_constraints
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_job_root=Path(current_temp_directory)
            current_snapshots=snapshot_kimodo_keyframes(current_job_root,current_migrated_request['keyframes'])
            current_new_constraints=build_kimodo_keyframe_constraints(current_job_root,{**current_migrated_request,'keyframe_snapshots':current_snapshots})[0]
            self.assertEqual(current_new_constraints,build_soma_endpoint_records(current_pose_record['id'],current_request_record['frames'])[0])
        for current_patch_record in ({'endpoint_pose_id':'../bad'},{'endpoint_pose_id':42},{'post_processing':False},{'heading_degrees':45}):
            with self.assertRaises(ValueError):validate_kimodo_request({**current_request_record,**current_patch_record})
        self.assertEqual(apply_complete_kimodo_example(next(iter(load_kimodo_examples())))[-4:],(None,[],0,''))

    def test_pose_library_rejects_modified_files(self):
        from generators.kimodo.pose_library import KIMODO_POSE_LIBRARY_ROOT,load_soma_pose_catalog
        import shutil
        with tempfile.TemporaryDirectory() as current_temporary_directory:
            current_catalog_directory=Path(current_temporary_directory)/'poses'
            shutil.copytree(KIMODO_POSE_LIBRARY_ROOT,current_catalog_directory)
            (current_catalog_directory/'relaxed-standing-v1/skeleton.yaml').write_text('invalid')
            with patch('generators.kimodo.pose_library.KIMODO_POSE_LIBRARY_ROOT',current_catalog_directory),self.assertRaisesRegex(ValueError,'해시'):
                load_soma_pose_catalog()
