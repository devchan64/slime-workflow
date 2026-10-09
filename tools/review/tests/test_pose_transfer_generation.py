"""포즈 변환 입력 수·역할·해상도·CLI 계약 검증."""
import base64
import ast
from pathlib import Path
import io
import unittest
from unittest.mock import patch
from PIL import Image
from tools.review.domains.image.pose_transfer_generation import PoseTransferGenerationManager, load_pose_transfer_prompt
from tools.review.common import management_gateway


class PoseTransferContractTests(unittest.TestCase):
    def test_gui_new_submission_validation(self):
        from tools.review.domains.image.qwen_21_generation import validate_qwen_plain_request
        current_source_path = Path(__file__).resolve().parents[1] / 'ui/gradio/qwen_2511_app.py'
        current_source_tree = ast.parse(current_source_path.read_text())
        current_validation_call = next(current_ast_node for current_ast_node in ast.walk(current_source_tree) if isinstance(current_ast_node, ast.Call) and isinstance(current_ast_node.func, ast.Name) and current_ast_node.func.id == 'validate_qwen_plain_request')
        current_call_code = compile(ast.Expression(current_validation_call), str(current_source_path), 'eval')
        for current_step_value in (25, 40):
            current_request_record = {**self.create_request_record(), 'steps': current_step_value}
            current_validated_record = eval(current_call_code, {'validate_qwen_plain_request':validate_qwen_plain_request, 'generation_request_value':current_request_record, 'vnccs_transfer_enabled':True})
            self.assertEqual(current_validated_record['steps'], current_step_value)
        with self.assertRaises(ValueError):
            eval(current_call_code, {'validate_qwen_plain_request':validate_qwen_plain_request, 'generation_request_value':{**self.create_request_record(), 'steps':25}, 'vnccs_transfer_enabled':False})

    def create_request_record(self):
        image_output_buffer = io.BytesIO()
        Image.new('RGB', (32,32), 'white').save(image_output_buffer, format='PNG')
        encoded_image_value = base64.b64encode(image_output_buffer.getvalue()).decode()
        return {'action':'generate','prompt':load_pose_transfer_prompt(),'images':[encoded_image_value,encoded_image_value],'width':512,'height':512,'steps':40,'seed':10107,'tag':''}

    def test_sizes_and_steps(self):
        for selected_size_value in (512,):
            for selected_step_value in (25,40):
                current_request_record = self.create_request_record()
                current_request_record.update(width=selected_size_value,height=selected_size_value,steps=selected_step_value)
                validated_request_record = PoseTransferGenerationManager().validate_generation_request(current_request_record)
                self.assertEqual(validated_request_record['steps'],selected_step_value)
                self.assertEqual(validated_request_record['vnccs']['dtype'],'bfloat16')
                self.assertEqual(validated_request_record['vnccs']['reference_order'],['pose','identity'])

    def test_invalid_inputs_fail(self):
        for changed_field_values in ({'images':[]},{'images':['one']},{'images':['one','two','three']},{'width':1024,'height':1024},{'width':768,'height':768},{'width':512,'height':768},{'steps':4},{'steps':20},{'steps':30},{'steps':50}):
            with self.assertRaises(ValueError):
                PoseTransferGenerationManager().validate_generation_request({**self.create_request_record(),**changed_field_values})

    def test_cli_requires_exactly_two_references(self):
        with self.assertRaisesRegex(ValueError,'두 번'):
            management_gateway.execute_gateway_cli(['command','pose-transfer','generate','--detach'])

    def test_history_storage_is_separate(self):
        manager_instance_value = PoseTransferGenerationManager()
        self.assertEqual(manager_instance_value.job_storage_root.name,'pose-transfer')
        self.assertEqual(manager_instance_value.history_storage_path().name,'pose-transfer')
