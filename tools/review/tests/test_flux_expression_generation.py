"""FLUX 표정 페이지와 입력·이력 분리 계약."""
import base64
import importlib
import io
import unittest
from PIL import Image
from unittest.mock import patch
from tools.review.common.management_gateway import resolve_management_command, execute_gateway_arguments
from tools.review.domains.image.flux_expression_generation import FluxExpressionGenerationManager, build_flux_expression_prompt


class FluxExpressionGenerationTests(unittest.TestCase):
    def create_sample_request(self):
        current_image_buffer = io.BytesIO()
        Image.new('RGB',(16,16),'white').save(current_image_buffer,format='PNG')
        return {'action':'generate','prompt':'joy','images':[base64.b64encode(current_image_buffer.getvalue()).decode()],'width':768,'height':512,'steps':16,'seed':42}

    def test_request_uses_flux_and_one_reference(self):
        current_manager_value=FluxExpressionGenerationManager()
        current_request_record=current_manager_value.validate_generation_request(self.create_sample_request())
        self.assertEqual(current_request_record['expression_id'],'joy')
        self.assertEqual(current_request_record['prompt'],build_flux_expression_prompt('joy'))
        self.assertEqual(current_manager_value.select_generation_service(),'flux-expression')
        self.assertNotEqual(current_manager_value.history_storage_path().name,'expression')
        for current_reference_list in ([],self.create_sample_request()['images']*2):
            with self.assertRaises(ValueError):
                current_manager_value.validate_generation_request({**self.create_sample_request(),'images':current_reference_list})

    def test_korean_expression_addition_preserves_preset(self):
        current_manager_value=FluxExpressionGenerationManager()
        current_request_record=current_manager_value.validate_generation_request({**self.create_sample_request(),'translation_source_ko':'눈썹을 조금 올린다'})
        self.assertEqual(current_request_record['translation_source_ko'],'눈썹을 조금 올린다')
        self.assertEqual(current_request_record['translation_base_prompt'],build_flux_expression_prompt('joy'))
        self.assertEqual(current_request_record['prompt'],build_flux_expression_prompt('joy'))
        self.assertNotIn('common_style',current_request_record)

    def test_translated_expression_restores_preset_and_korean(self):
        import hashlib
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from tools.review.domains.image.three_reference_generation import save_three_reference_inputs
        current_restore_function=importlib.import_module('generators.flux-expression.page.interface').restore_flux_expression_inputs
        with TemporaryDirectory() as current_directory_name:
            current_identifier_value='2026-11-17_08-00-00-12345678'
            current_job_path=Path(current_directory_name)/current_identifier_value
            current_job_path.mkdir()
            current_request_record=FluxExpressionGenerationManager().validate_generation_request({**self.create_sample_request(),'translation_source_ko':'부드럽게 웃는다'})
            current_saved_record=save_three_reference_inputs(current_job_path,current_request_record)
            current_final_prompt=build_flux_expression_prompt('joy')+' Smile gently.'
            current_saved_record.update(prompt=current_final_prompt,prompt_sha256=hashlib.sha256(current_final_prompt.encode()).hexdigest(),translated_design='Smile gently.')
            current_restored_values=current_restore_function({'id':current_identifier_value,'request':current_saved_record},Path(current_directory_name))
            self.assertEqual(current_restored_values[1],'joy')
            self.assertEqual(current_restored_values[-1],'부드럽게 웃는다')

    def test_gateway_and_cli_use_flux(self):
        self.assertEqual(resolve_management_command('flux-expression','generate',{})[1],'/flux-expression-generator/jobs')
        with patch('tools.review.common.management_gateway.execute_management_command',return_value={'id':'test'}) as current_gateway_mock:
            from tempfile import TemporaryDirectory
            from pathlib import Path
            with TemporaryDirectory() as current_temporary_directory:
                current_image_path=Path(current_temporary_directory)/'face.png'
                current_image_path.write_bytes(base64.b64decode(self.create_sample_request()['images'][0]))
                execute_gateway_arguments('flux-expression',['generate','--expression','joy','--reference',str(current_image_path),'--translation-ko','눈썹을 올린다','--detach'])
            current_payload_value=current_gateway_mock.call_args.args[2]
            self.assertEqual((current_payload_value['width'],current_payload_value['height'],current_payload_value['steps']),(768,512,16))
            self.assertEqual(len(current_payload_value['images']),1)
            self.assertEqual(current_payload_value['translation_source_ko'],'눈썹을 올린다')

    def test_resume_checks_saved_inputs_and_runner(self):
        import json
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from tools.review.domains.image.flux_expression_generation import WORKFLOW_ROOT_PATH
        from tools.review.domains.image.three_reference_generation import save_three_reference_inputs
        current_manager_value = FluxExpressionGenerationManager()
        with TemporaryDirectory() as current_temporary_directory:
            current_job_root = Path(current_temporary_directory)
            current_saved_record = save_three_reference_inputs(current_job_root,current_manager_value.validate_generation_request(self.create_sample_request()))
            (current_job_root/'request.json').write_text(json.dumps(current_saved_record))
            (current_job_root/'gpu-command.json').write_text(json.dumps({'command':['python',str(WORKFLOW_ROOT_PATH/current_manager_value.select_generation_runner())]}))
            current_manager_value.validate_generation_resume(current_job_root)
            (current_job_root/'reference-1.png').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                current_manager_value.validate_generation_resume(current_job_root)

    def test_restore_expression_inputs_and_reject_changed_data(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        import gradio as gr
        from tools.review.domains.image.three_reference_generation import save_three_reference_inputs
        current_restore_function = importlib.import_module('generators.flux-expression.page.interface').restore_flux_expression_inputs
        with TemporaryDirectory() as current_temporary_directory:
            current_storage_root = Path(current_temporary_directory)
            current_job_identifier = '2026-11-16_18-23-00-f1a2b3c4'
            current_job_root = current_storage_root/current_job_identifier
            current_job_root.mkdir()
            current_request_record = save_three_reference_inputs(current_job_root,FluxExpressionGenerationManager().validate_generation_request(self.create_sample_request()))
            current_history_record = {'id':current_job_identifier,'request':current_request_record}
            current_restored_values = current_restore_function(current_history_record,current_storage_root)
            self.assertEqual(current_restored_values[0].size,(16,16))
            self.assertEqual(current_restored_values[1:],('joy',768,512,42,'',''))
            with self.assertRaises(gr.Error):
                current_restore_function({'id':current_job_identifier,'request':{**current_request_record,'prompt':'변조'}},current_storage_root)
            (current_job_root/'reference-1.png').write_bytes(b'changed')
            with self.assertRaises(gr.Error):
                current_restore_function(current_history_record,current_storage_root)

    def test_page_builds_in_management_shell(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from tools.review.common.management_asgi import build_management_blocks
        with TemporaryDirectory() as current_temporary_directory:
            current_source_path=Path(current_temporary_directory)/'menu.json'; current_source_path.write_text('{"pages": []}')
            with patch.dict('os.environ',{'SLIME_MANAGEMENT_MENU_SOURCE':str(current_source_path)}):
                current_page_value,_=build_management_blocks('flux-expression-generator',8770,current_source_path)
        self.assertGreater(len(current_page_value.blocks),0)
        current_config_record=current_page_value.get_config_file()
        self.assertTrue(any(current_component.get('props',{}).get('value')=='전달된 작업을 이력에서 찾기' for current_component in current_config_record['components']))
        self.assertTrue(any("searchParams.get('job')" in str(current_dependency.get('js','')) for current_dependency in current_config_record['dependencies']))
        current_page_module = importlib.import_module('generators.flux-expression.page.interface')
        self.assertEqual(current_page_module.load_default_face_reference().size, Image.open('baseline/player/default/default-face-front-v1.png').size)
