"""2.1 입력 원문·참조 10장·기록 검증·CLI 계약 회귀 검사."""
import base64
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

from tools.review.domains.image.qwen_21_generation import validate_qwen_plain_request, verify_qwen_saved_request, QwenPlainGenerationManager
from tools.review.domains.image.three_reference_generation import save_three_reference_inputs, validate_three_reference_request
from tools.review.common.management_gateway import execute_gateway_arguments


class QwenPlainGenerationTests(unittest.TestCase):
    def create_reference_request(self, reference_image_count=0):
        current_image_buffer = io.BytesIO()
        Image.new('RGB', (16, 16), 'red').save(current_image_buffer, format='PNG')
        return {'action':'generate','prompt':'  붉은 사과.\n흰 배경.  ','images':[base64.b64encode(current_image_buffer.getvalue()).decode()]*reference_image_count,
            'width':512,'height':512,'steps':40,'seed':10107}

    def test_original_prompt_is_unchanged(self):
        current_request_record = self.create_reference_request()
        validated_request_record = validate_qwen_plain_request(current_request_record)
        self.assertEqual(validated_request_record['prompt'], current_request_record['prompt'])
        self.assertEqual(validated_request_record['qwen21']['additional_prompt'], '')
        self.assertEqual(validated_request_record['qwen21']['prompt_sha256'],hashlib.sha256(current_request_record['prompt'].encode()).hexdigest())
        self.assertEqual(validated_request_record['images'], [])

    def test_ten_references_and_invalid_inputs(self):
        self.assertEqual(len(validate_qwen_plain_request(self.create_reference_request(10))['images']),10)
        for invalid_request_record in (self.create_reference_request(11), {**self.create_reference_request(),'steps':4}, {**self.create_reference_request(),'prompt':'word '*100}, {**self.create_reference_request(),'model':'other'}):
            with self.assertRaises(ValueError):
                validate_qwen_plain_request(invalid_request_record)
        with self.assertRaises(ValueError):
            validate_three_reference_request({**self.create_reference_request(4),'steps':4})

    def test_snapshot_ten_resume_and_prompt_tampering(self):
        current_request_record = validate_qwen_plain_request(self.create_reference_request(10))
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_job_root = Path(temporary_directory_name)
            saved_request_record = {**current_request_record, **save_three_reference_inputs(current_job_root,current_request_record)}
            saved_request_record.pop('images')
            self.assertTrue((current_job_root/'reference-10.png').is_file())
            verify_qwen_saved_request(current_job_root,saved_request_record)
            saved_request_record['prompt'] += ' 변경'
            with self.assertRaises(ValueError):
                verify_qwen_saved_request(current_job_root,saved_request_record)

    def test_cli_raw_prompt_and_ten_references(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_reference_path = Path(temporary_directory_name)/'input.png'
            current_reference_path.write_bytes(base64.b64decode(self.create_reference_request(1)['images'][0]))
            current_prompt_text = self.create_reference_request()['prompt']
            current_command_values=['generate','--prompt',current_prompt_text,'--detach']
            for current_reference_index in range(10):
                current_command_values += ['--reference',str(current_reference_path)]
            with patch('tools.review.common.management_gateway.call_management_api',return_value={'id':'test'}) as gateway_call_mock, contextlib.redirect_stdout(io.StringIO()):
                execute_gateway_arguments('qwen-21',current_command_values)
            current_payload_record=gateway_call_mock.call_args.args[2]
            self.assertEqual(current_payload_record['prompt'],current_prompt_text)
            self.assertEqual(current_payload_record['steps'],40)
            self.assertEqual(len(current_payload_record['images']),10)
            validate_qwen_plain_request(current_payload_record)

    def test_history_and_runner_are_separate(self):
        current_service_manager=QwenPlainGenerationManager()
        self.assertEqual(current_service_manager.history_storage_path().name,'qwen-21')
        self.assertEqual(current_service_manager.job_storage_root.name,'qwen-image-21')
        self.assertTrue(current_service_manager.select_generation_runner().endswith('run_qwen_21_reference.py'))
