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
        for current_field_name,current_field_value in [('frames',29),('frames',301),('steps',True),('seed',-1),('guidance_scale',float('nan')),('heading_degrees',181),('post_processing',1),('model','other'),('prompt','...'),('prompt','word '*101)]:
            with self.subTest(field=current_field_name,value=current_field_value),self.assertRaises(ValueError):
                validate_kimodo_request({**self.current_request_record,current_field_name:current_field_value})
        self.assertEqual(validate_kimodo_request(self.current_request_record)['images'],[])

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

    def test_anny_maps_soma_names_and_preserves_source_coordinates(self):
        import numpy as np
        from generators.kimodo.anny_export import load_anny_configuration,prepare_anny_channels
        current_config_record=load_anny_configuration()
        current_joint_names=current_config_record['source_joint_names']+[f'unmapped-{current_joint_index}' for current_joint_index in range(55)]
        current_joint_positions=np.arange(2*77*3,dtype=float).reshape(2,77,3)
        with tempfile.TemporaryDirectory() as current_temp_root:
            current_motion_path=Path(current_temp_root)/'motion.npz'
            np.savez(current_motion_path,posed_joints=current_joint_positions)
            current_selected_points=prepare_anny_channels(current_motion_path,{'skeleton':'somaskel77','fps':30,'joint_names':current_joint_names},current_config_record)
            np.testing.assert_array_equal(current_selected_points,current_joint_positions[:,:22])
            with self.assertRaises(ValueError):prepare_anny_channels(current_motion_path,{'skeleton':'somaskel77','fps':24,'joint_names':current_joint_names},current_config_record)
            current_joint_positions[0,0,0]=float('nan')
            np.savez(current_motion_path,posed_joints=current_joint_positions)
            with self.assertRaises(ValueError):prepare_anny_channels(current_motion_path,{'skeleton':'somaskel77','fps':30,'joint_names':current_joint_names},current_config_record)

    def test_anny_rejects_changed_baseline_hash(self):
        from generators.kimodo.anny_export import verify_anny_resources
        with patch('generators.kimodo.anny_export.hashlib.sha256') as current_hash_mock:
            current_hash_mock.return_value.hexdigest.return_value='0'*64
            with self.assertRaisesRegex(ValueError,'해시 불일치'):verify_anny_resources()

    def test_neck_rotation_preserves_head_independence(self):
        import numpy as np
        from generators.kimodo.anny_rotation import prepare_neck_rotation_channels
        with tempfile.TemporaryDirectory() as current_temp_directory:
            current_temp_root=Path(current_temp_directory)
            current_joint_names=['Neck1','Neck2','Head']+[f'joint-{current_joint_index}' for current_joint_index in range(74)]
            (current_temp_root/'skeleton.json').write_text(json.dumps({'skeleton':'somaskel77','joint_names':current_joint_names}))
            current_rotation_values=np.broadcast_to(np.eye(3),(2,77,3,3)).copy()
            current_rotation_values[1,2]=[[0,-1,0],[1,0,0],[0,0,1]]
            np.savez(current_temp_root/'motion.npz',global_rot_mats=current_rotation_values,posed_joints=np.zeros((2,77,3)))
            current_bone_channels,_=prepare_neck_rotation_channels(current_temp_root)
            np.testing.assert_allclose(current_bone_channels['neck03'],np.broadcast_to(np.eye(3),(2,3,3)))
            np.testing.assert_allclose(current_bone_channels['head'][0],np.eye(3))
            np.testing.assert_allclose(current_bone_channels['head'][1],[[0,0,-1],[0,1,0],[1,0,0]])
            current_rotation_values[0,2,0,0]=2
            np.savez(current_temp_root/'motion.npz',global_rot_mats=current_rotation_values,posed_joints=np.zeros((2,77,3)))
            with self.assertRaisesRegex(ValueError,'정규 직교'):prepare_neck_rotation_channels(current_temp_root)
