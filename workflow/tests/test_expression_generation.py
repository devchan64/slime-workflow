"""표정 프리셋과 공용 GUI·CLI 입력 계약을 검증한다."""
import base64
import contextlib
import io
import tempfile
import json
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from workflow.domains.image.expression_generation import ExpressionGenerationManager, build_expression_prompt, load_expression_configuration
from workflow.domains.image.three_reference_generation import save_three_reference_inputs, verify_reference_snapshots
from workflow.common import management_gateway


class ExpressionGenerationTests(unittest.TestCase):
    def create_reference_request(self, reference_image_count=1):
        reference_image_buffer = io.BytesIO()
        Image.new('RGB',(16,16),'white').save(reference_image_buffer,format='PNG')
        return {'action':'generate','prompt':'joy','images':[base64.b64encode(reference_image_buffer.getvalue()).decode()]*reference_image_count,'width':512,'height':512,'steps':40,'seed':10107}

    def test_all_presets_have_bounded_prompts(self):
        expression_preset_records = load_expression_configuration()['expressions']
        self.assertEqual(len(expression_preset_records),39)
        for current_expression_record in expression_preset_records:
            final_prompt_value, expression_source_record = build_expression_prompt(current_expression_record['id'])
            self.assertLess(len(final_prompt_value.split()),100)
            self.assertEqual(expression_source_record['prompt_word_count'],len(final_prompt_value.split()))

    def test_required_reference_count_and_invalid_fields(self):
        expression_job_service = ExpressionGenerationManager()
        for reference_image_count in (0,4):
            with self.assertRaises(ValueError):
                expression_job_service.validate_generation_request(self.create_reference_request(reference_image_count))
        for invalid_field_name, invalid_field_value in [('prompt','unknown'),('model','other'),('steps',4)]:
            current_request_record = self.create_reference_request()
            current_request_record[invalid_field_name] = invalid_field_value
            with self.assertRaises(ValueError):
                expression_job_service.validate_generation_request(current_request_record)

    def test_snapshots_and_expression_provenance_survive_storage(self):
        for reference_image_count in (1,2,3):
            current_request_record = ExpressionGenerationManager().validate_generation_request(self.create_reference_request(reference_image_count))
            with tempfile.TemporaryDirectory() as temporary_directory_name:
                current_job_directory = Path(temporary_directory_name)
                saved_request_record = {**current_request_record,**save_three_reference_inputs(current_job_directory,current_request_record)}
                self.assertEqual(saved_request_record['expression']['id'],'joy')
                self.assertEqual(len(saved_request_record['reference_snapshots']),reference_image_count)
                verify_reference_snapshots(current_job_directory,saved_request_record)

    def test_qwen21_resume_requires_fixed_adapter_and_saved_runner(self):
        from workflow.domains.image.expression_generation import verify_expression_saved_request
        current_request_record = ExpressionGenerationManager().validate_generation_request(self.create_reference_request())
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_job_directory = Path(current_directory_name)
            saved_request_record = save_three_reference_inputs(current_job_directory, current_request_record)
            verify_expression_saved_request(current_job_directory, saved_request_record)
            (current_job_directory / 'request.json').write_text(json.dumps(saved_request_record))
            (current_job_directory / 'gpu-command.json').write_text(json.dumps({'command': ['python', '/tmp/run_qwen_2511_three_reference.py']}))
            with self.assertRaisesRegex(ValueError, '폐기'):
                ExpressionGenerationManager().validate_generation_resume(current_job_directory)
            saved_request_record['expression_adapter']['scale'] = 0.1
            with self.assertRaisesRegex(ValueError, 'LoRA'):
                verify_expression_saved_request(current_job_directory, saved_request_record)

    def test_cli_reads_archived_history_and_rejects_generation(self):
        with patch.object(management_gateway, 'call_management_api', return_value={'records': []}) as current_api_mock, contextlib.redirect_stdout(io.StringIO()):
            management_gateway.execute_gateway_arguments('expression', ['history'])
            self.assertEqual(current_api_mock.call_args.args[1], '/expression-generator/history')
            current_api_mock.reset_mock()
            with self.assertRaisesRegex(ValueError, '아카이브'):
                management_gateway.execute_gateway_arguments('expression', ['generate', '--expression', 'joy', '--detach'])
            current_api_mock.assert_not_called()

    def test_history_and_lifecycle_routes_are_separate(self):
        expression_job_service = ExpressionGenerationManager()
        self.assertEqual(expression_job_service.history_storage_path().name, 'expression')
        for current_command_name in ('cancel', 'status', 'logs'):
            current_route_record = management_gateway.resolve_management_command('expression', current_command_name, {'id': '2026-10-01_00-00-00-12345678'})
            self.assertTrue(current_route_record[1].startswith('/expression-generator/'))
        with self.assertRaisesRegex(ValueError, '아카이브'):
            management_gateway.resolve_management_command('expression', 'resume', {'id': '2026-10-01_00-00-00-12345678'})

    def test_gateway_reads_archived_request_and_shared_history(self):
        from workflow.tests.test_management_gateway import GatewayContractTest
        current_request_record = self.create_reference_request(3)
        current_valid_request = ExpressionGenerationManager().validate_generation_request(current_request_record)
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            expression_job_service = ExpressionGenerationManager()
            expression_job_service.job_storage_root = Path(temporary_directory_name) / 'jobs'
            expression_history_path = Path(temporary_directory_name) / 'history'
            expression_history_path.mkdir()
            current_job_identifier = '2026-10-01_00-00-00-12345678'
            current_job_path = expression_job_service.job_storage_root / current_job_identifier
            current_job_path.mkdir(parents=True)
            current_saved_request = {**current_valid_request, **save_three_reference_inputs(current_job_path, current_valid_request)}
            (current_job_path / 'request.json').write_text(json.dumps(current_saved_request))
            current_history_record = {'id': current_job_identifier, 'request': current_saved_request, 'status': {'status': 'completed'}, 'job_path': str(current_job_path)}
            (expression_history_path / (current_job_identifier + '.json')).write_text(json.dumps(current_history_record))
            current_gateway_service = management_gateway.ManagementCommandGateway({'expression': expression_job_service.handle_image_request})
            current_http_handler = GatewayContractTest().create_request_handler('/management/command', {'service': 'expression', 'command': 'history', 'payload': {}})
            with patch.object(expression_job_service, 'history_storage_path', return_value=expression_history_path):
                current_gateway_service.handle(current_http_handler)
            self.assertEqual(current_http_handler.responses, [200])
            current_history_records = json.loads(current_http_handler.wfile.getvalue())['records']
            self.assertEqual(current_history_records[0]['request']['expression']['id'], 'joy')
            self.assertEqual(len(current_history_records[0]['request']['references']), 3)
            verify_reference_snapshots(current_job_path, current_history_records[0]['request'])

    def test_history_reset_preserves_other_generator(self):
        from workflow.domains.image import image_generation
        expression_job_service = ExpressionGenerationManager()
        reference_job_service = image_generation.ImageGenerationManager(three_reference_mode=True)
        self.assertNotEqual(expression_job_service.job_storage_root, reference_job_service.job_storage_root)
        self.assertNotEqual(expression_job_service.history_storage_path(), reference_job_service.history_storage_path())
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            for current_service_record, other_service_record in ((expression_job_service, reference_job_service), (reference_job_service, expression_job_service)):
                current_history_path = Path(temporary_directory_name)/'current'
                other_history_path = Path(temporary_directory_name)/'other'
                current_history_path.mkdir(exist_ok=True)
                other_history_path.mkdir(exist_ok=True)
                (current_history_path/'current.json').write_text(json.dumps({'id':'current','status':{'status':'completed'}}))
                (other_history_path/'other.json').write_text(json.dumps({'id':'other','status':{'status':'completed'}}))
                with patch.object(current_service_record,'job_storage_root',Path(temporary_directory_name)/'jobs'), patch.object(current_service_record,'history_storage_path',return_value=current_history_path), patch.object(other_service_record,'history_storage_path',return_value=other_history_path), patch.object(other_service_record,'job_storage_root',Path(temporary_directory_name)/'other-jobs'):
                    self.assertEqual([record['id'] for record in current_service_record.list_generation_history()], ['current'])
                    current_service_record.reset_generation_history()
                    self.assertEqual(current_service_record.list_generation_history(), [])
                    self.assertEqual([record['id'] for record in other_service_record.list_generation_history()], ['other'])
