"""VNCCS 기준 경로·과거 기록·입력 순서·안전 한계 회귀 검사."""
import unittest
import base64
import contextlib
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from generators.image.vnccs_profile import build_vnccs_profile, validate_vnccs_profile
from generators.image.vnccs_runtime import build_vnccs_arguments, validate_vnccs_resources
from tools.review.domains.image.pose_transfer_generation import validate_pose_transfer_contract
from tools.review.domains.image.pose_transfer_generation import PoseTransferGenerationManager, load_pose_transfer_prompt
from tools.review.domains.image.three_reference_generation import save_three_reference_inputs
from tools.review.common import management_gateway


class VnccsRuntimeTests(unittest.TestCase):
    def build_current_request(self):
        return {'width':512,'height':512,'steps':40,'prompt':'Draw character from image2','vnccs':build_vnccs_profile()}

    def test_native_pipeline_arguments(self):
        current_pipeline_arguments=build_vnccs_arguments(self.build_current_request(),['identity','pose'],'generator','callback')
        self.assertEqual(current_pipeline_arguments['image'],['pose','identity'])
        self.assertEqual(current_pipeline_arguments['output_resolution'],512)
        self.assertEqual(current_pipeline_arguments['num_inference_steps'],40)
        self.assertNotIn('sigmas',current_pipeline_arguments)
        self.assertEqual(current_pipeline_arguments['true_cfg_scale'],1.0)

    def test_profile_override_rejected(self):
        current_request_record=self.build_current_request()
        current_request_record['vnccs']['quantization']='nf4'
        with self.assertRaises(ValueError):
            validate_vnccs_profile(current_request_record)
        self.assertEqual(build_vnccs_profile()['quantization'],'none')

    def test_selected_steps_contract(self):
        current_request_record = self.build_current_request()
        current_request_record.update(steps=25, vnccs=build_vnccs_profile(25))
        self.assertEqual(build_vnccs_arguments(current_request_record, ['identity','pose'], None, None)['num_inference_steps'], 25)
        current_request_record['vnccs']['steps'] = 40
        with self.assertRaises(ValueError):
            validate_vnccs_profile(current_request_record)

    def test_legacy_resume_contract_preserved(self):
        validate_pose_transfer_contract({'width':768,'height':768,'steps':20,'references':['reference-1.png','reference-2.png']},saved_request_enabled=True)
        with self.assertRaises(ValueError):
            validate_pose_transfer_contract({'width':768,'height':768,'steps':20,'references':['reference-1.png','reference-2.png'],'vnccs':build_vnccs_profile()},saved_request_enabled=True)

    def test_memory_and_time_limits(self):
        current_execution_profile=build_vnccs_profile()
        validate_vnccs_resources(20*1024**3,30*1024**3,100,current_execution_profile)
        for current_available_bytes,current_process_rss,current_elapsed_seconds in ((11*1024**3,0,0),(20*1024**3,43*1024**3,0),(20*1024**3,0,1201)):
            with self.assertRaises(RuntimeError):
                validate_vnccs_resources(current_available_bytes,current_process_rss,current_elapsed_seconds,current_execution_profile)

    def test_cli_gui_defaults_and_reference_order(self):
        with tempfile.TemporaryDirectory() as current_temporary_name:
            current_temporary_root=Path(current_temporary_name)/'pose-transfer'/'test-job'
            current_temporary_root.mkdir(parents=True)
            current_reference_paths=[]
            for current_role_name,current_color_name in (('identity','red'),('pose','blue')):
                current_reference_path=current_temporary_root/(current_role_name+'.png')
                Image.new('RGB',(32,32),current_color_name).save(current_reference_path)
                current_reference_paths.append(current_reference_path)
            with patch.object(management_gateway,'call_management_api',return_value={'id':'2026-10-09_00-00-00-12345678'}) as current_api_mock, contextlib.redirect_stdout(io.StringIO()):
                management_gateway.execute_gateway_arguments('pose-transfer',['generate','--reference',str(current_reference_paths[0]),'--reference',str(current_reference_paths[1]),'--steps','25','--detach'])
            current_payload_record=current_api_mock.call_args.args[2]
            self.assertEqual(current_payload_record['seed'],1695791623)
            self.assertEqual((current_payload_record['width'],current_payload_record['height'],current_payload_record['steps']),(512,512,25))
            self.assertEqual(current_payload_record['prompt'],load_pose_transfer_prompt())
            self.assertEqual(current_payload_record['images'],[base64.b64encode(current_reference_path.read_bytes()).decode() for current_reference_path in current_reference_paths])
            current_manager_value=PoseTransferGenerationManager()
            current_validated_record=current_manager_value.validate_generation_request(current_payload_record)
            current_saved_record={**{current_field_name:current_field_value for current_field_name,current_field_value in current_validated_record.items() if current_field_name!='images'},**save_three_reference_inputs(current_temporary_root,current_validated_record)}
            (current_temporary_root/'request.json').write_text(json.dumps(current_saved_record))
            current_manager_value.validate_generation_resume(current_temporary_root)
            current_saved_record['vnccs']['output_resolution']=1024
            (current_temporary_root/'request.json').write_text(json.dumps(current_saved_record))
            with self.assertRaises(ValueError):
                current_manager_value.validate_generation_resume(current_temporary_root)
