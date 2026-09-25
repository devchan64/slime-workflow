"""통합 CLI의 Qwen 요청을 GUI API 계약과 비교한다."""
import base64
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

COMMAND_MODULE_PATH = Path(__file__).resolve().parents[1]/'common/management_gateway.py'
sys.path.insert(0,str(COMMAND_MODULE_PATH.parents[1]))
COMMAND_MODULE_SPEC = importlib.util.spec_from_file_location('review.management_gateway',COMMAND_MODULE_PATH)
COMMAND_MODULE_VALUE = importlib.util.module_from_spec(COMMAND_MODULE_SPEC)
COMMAND_MODULE_SPEC.loader.exec_module(COMMAND_MODULE_VALUE)


class QwenCommandsTest(unittest.TestCase):
    def test_both_generation_routes(self):
        for service_name_value,route_prefix_value,default_seed_value in [('qwen-2512','/image-generation',251204),('qwen-2511','/image-generation-2511',10107)]:
            with patch.object(COMMAND_MODULE_VALUE,'call_management_api',return_value={'id':'2026-09-25_00-00-00-12345678','status':'running'}) as api_call_handle, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(COMMAND_MODULE_VALUE.execute_gateway_arguments(service_name_value,['generate','--prompt','한국어 프롬프트','--detach']),0)
            request_call_args=api_call_handle.call_args.args
            self.assertEqual(request_call_args[1],route_prefix_value+'/jobs')
            self.assertEqual(request_call_args[2]['seed'],default_seed_value)
            self.assertEqual(request_call_args[2]['prompt'],'한국어 프롬프트')
            self.assertEqual('images' in request_call_args[2],service_name_value=='qwen-2511')

    def test_reference_order_and_prompt_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            prompt_file_path=Path(temporary_directory_name)/'prompt.txt';prompt_file_path.write_text('참조 사용',encoding='utf-8')
            reference_file_path=Path(temporary_directory_name)/'reference.png';reference_file_path.write_bytes(b'png transport test')
            with patch.object(COMMAND_MODULE_VALUE,'call_management_api',return_value={'id':'2026-09-25_00-00-00-12345678'}) as api_call_handle, contextlib.redirect_stdout(io.StringIO()):
                COMMAND_MODULE_VALUE.execute_gateway_arguments('qwen-2511',['generate','--prompt-file',str(prompt_file_path),'--reference',str(reference_file_path),'--seed','42','--steps','30','--detach'])
            request_body_value=api_call_handle.call_args.args[2]
            self.assertEqual(request_body_value['images'],[base64.b64encode(reference_file_path.read_bytes()).decode()])
            self.assertEqual(request_body_value['seed'],42)
            self.assertEqual(request_body_value['steps'],30)

    def test_failed_generation_exit_status(self):
        with patch.object(COMMAND_MODULE_VALUE,'call_management_api',side_effect=[{'id':'2026-09-25_00-00-00-12345678'},{'status':'failed','error':'실패'}]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(COMMAND_MODULE_VALUE.execute_gateway_arguments('qwen-2512',['generate','--prompt','test']),1)

    def test_help_does_not_connect(self):
        with patch.object(COMMAND_MODULE_VALUE,'call_management_api') as api_call_handle, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as exit_context_value:
                COMMAND_MODULE_VALUE.execute_gateway_arguments('qwen-2511',['generate','--help'])
            self.assertEqual(exit_context_value.exception.code,0)
            api_call_handle.assert_not_called()

    def test_invalid_id_does_not_connect(self):
        with patch.object(COMMAND_MODULE_VALUE,'call_management_api') as api_call_handle:
            with self.assertRaises(ValueError):
                COMMAND_MODULE_VALUE.execute_gateway_arguments('qwen-2511',['status','../../etc/passwd'])
            api_call_handle.assert_not_called()


if __name__=='__main__':
    unittest.main()
