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
from tools.review.domains.image.expression_generation import ExpressionGenerationManager, build_expression_prompt, load_expression_configuration
from tools.review.domains.image.three_reference_generation import save_three_reference_inputs, verify_reference_snapshots
from tools.review.common import management_gateway


class ExpressionGenerationTests(unittest.TestCase):
    def create_reference_request(self, reference_image_count=1):
        reference_image_buffer = io.BytesIO()
        Image.new('RGB',(16,16),'white').save(reference_image_buffer,format='PNG')
        return {'action':'generate','prompt':'joy','images':[base64.b64encode(reference_image_buffer.getvalue()).decode()]*reference_image_count,'width':512,'height':512,'steps':4,'seed':10107}

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
        for invalid_field_name, invalid_field_value in [('prompt','unknown'),('model','other'),('steps',20)]:
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

    def test_cli_uses_same_service_payload(self):
        current_request_record = self.create_reference_request()
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            current_reference_path = Path(temporary_directory_name)/'reference.png'
            current_reference_path.write_bytes(base64.b64decode(current_request_record['images'][0]))
            with patch.object(management_gateway,'call_management_api',return_value={'id':'test'}) as current_api_mock, contextlib.redirect_stdout(io.StringIO()):
                management_gateway.execute_gateway_arguments('expression',['generate','--expression','joy','--reference',str(current_reference_path),'--detach'])
            self.assertEqual(current_api_mock.call_args.args[1],'/expression-generator/jobs')
            self.assertEqual(current_api_mock.call_args.args[2],current_request_record)
            ExpressionGenerationManager().validate_generation_request(current_api_mock.call_args.args[2])

    def test_history_and_lifecycle_routes_are_separate(self):
        expression_job_service = ExpressionGenerationManager()
        self.assertEqual(expression_job_service.history_storage_path().name,'expression')
        for current_command_name in ('cancel','resume','status','logs'):
            current_route_record = management_gateway.resolve_management_command('expression',current_command_name,{'id':'2026-10-01_00-00-00-12345678'})
            self.assertTrue(current_route_record[1].startswith('/expression-generator/'))

    def test_gateway_persists_request_and_shared_history(self):
        from tools.review.tests.test_management_gateway import GatewayContractTest
        from tools.review.domains.image import image_generation
        current_request_record = self.create_reference_request(3)
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            expression_job_service = ExpressionGenerationManager()
            expression_job_service.job_storage_root = Path(temporary_directory_name)/'jobs'
            expression_history_path = Path(temporary_directory_name)/'history'
            current_gateway_service = management_gateway.ManagementCommandGateway({'expression':expression_job_service.handle_image_request})
            current_http_handler = GatewayContractTest().create_request_handler('/management/command',{'service':'expression','command':'generate','payload':current_request_record})
            with patch.object(expression_job_service,'history_storage_path',return_value=expression_history_path), patch.object(image_generation,'validate_image_runtime'), patch.object(image_generation,'launch_gpu_process',return_value=SimpleNamespace()), patch.object(image_generation.threading,'Thread'):
                current_gateway_service.handle(current_http_handler)
            self.assertEqual(current_http_handler.responses,[202])
            generation_job_identifier = json.loads(current_http_handler.wfile.getvalue())['id']
            saved_request_record = json.loads((expression_job_service.job_storage_root/generation_job_identifier/'request.json').read_text())
            saved_history_record = json.loads((expression_history_path/(generation_job_identifier+'.json')).read_text())
            self.assertEqual(saved_history_record['request'],saved_request_record)
            self.assertNotIn('images',saved_request_record)
            self.assertEqual(saved_request_record['expression']['id'],'joy')
            self.assertEqual(len(saved_request_record['references']),3)

    def test_history_reset_preserves_other_generator(self):
        from tools.review.domains.image import image_generation
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
                with patch.object(current_service_record,'history_storage_path',return_value=current_history_path), patch.object(other_service_record,'history_storage_path',return_value=other_history_path):
                    self.assertEqual([record['id'] for record in current_service_record.list_generation_history()], ['current'])
                    current_service_record.reset_generation_history()
                    self.assertEqual(current_service_record.list_generation_history(), [])
                    self.assertEqual([record['id'] for record in other_service_record.list_generation_history()], ['other'])
