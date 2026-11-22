"""신체 비율 기준·선택·실행 기록의 무결성 검증."""
import base64
import importlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from workflow.domains.image.qwen_21_generation import validate_styled_qwen_request, verify_qwen_saved_request
from workflow.domains.image.three_reference_generation import save_three_reference_inputs


class CharacterBodyReferenceTests(unittest.TestCase):
    def setUp(self):
        self.body_module = importlib.import_module('generators.character-generator.body_references')
        self.body_catalog = self.body_module.load_body_reference_catalog()
        self.request_values = {'action': 'generate', 'prompt': 'A character. ' + self.body_module.BODY_REFERENCE_ROLE_PROMPT, 'images': [], 'width': 768, 'height': 768, 'steps': 40, 'seed': 1}

    def test_catalog_images_and_version(self):
        self.assertEqual({current_record['id'] for current_record in self.body_catalog}, {'neutral-body-clothed'})
        for current_record in self.body_catalog:
            self.assertEqual(self.body_module.load_body_reference_image(current_record['id']).size, (768, 1152))
        with self.assertRaises(ValueError):
            self.body_module.load_body_reference_image('../outside')

    def test_reference_record_and_resume_uses_saved_image(self):
        for current_record in self.body_catalog:
            current_buffer = io.BytesIO()
            self.body_module.load_body_reference_image(current_record['id']).save(current_buffer, format='PNG')
            current_input = {**self.request_values, 'body_reference_id': current_record['id'], 'images': [base64.b64encode(current_buffer.getvalue()).decode()]}
            current_request = validate_styled_qwen_request(current_input)
            self.assertEqual(current_request['body_reference_sources'][0]['source_sha256'], current_record['sha256'])
            self.assertEqual(current_request['body_reference_sources'][0]['source'], 'baseline/mannequin/' + current_record['image'])
            with tempfile.TemporaryDirectory() as current_directory:
                current_root = Path(current_directory)
                current_saved = {**current_request, **save_three_reference_inputs(current_root, current_request)}
                current_saved.pop('images')
                with patch.object(self.body_module, 'load_body_reference_catalog', side_effect=AssertionError('현재 목록을 읽으면 안 됨')):
                    verify_qwen_saved_request(current_root, current_saved)
                    current_saved['body_reference_sources'][0]['source'] = 'prompts/references/mannequin/latest/' + current_record['image']
                    verify_qwen_saved_request(current_root, current_saved)
                current_saved['body_reference_sources'][0]['pixel_sha256'] = '0' * 64
                with self.assertRaises(ValueError):
                    verify_qwen_saved_request(current_root, current_saved)
        with self.assertRaisesRegex(ValueError, '첫 참조'):
            validate_styled_qwen_request({**self.request_values, 'body_reference_id': self.body_catalog[0]['id']})
        current_buffer = io.BytesIO()
        Image.new('RGB', (512, 512), 'white').save(current_buffer, format='PNG')
        with self.assertRaisesRegex(ValueError, '첫 참조'):
            validate_styled_qwen_request({**self.request_values, 'body_reference_id': self.body_catalog[0]['id'], 'images': [base64.b64encode(current_buffer.getvalue()).decode()]})

    def test_body_reference_search_and_selection(self):
        import json
        import subprocess
        root=Path(__file__).resolve().parents[2]
        script="""import {filterFluxGuides,addFluxRolePrompt} from './gui/fluxGuides.mjs';
          const [guides,role]=JSON.parse(process.argv[1]);
          if(filterFluxGuides(guides,'NEUTRAL-BODY-CLOTHED')[0]?.id!=='neutral-body-clothed')throw Error('search');
          if(filterFluxGuides(guides,'검색불가').length)throw Error('unknown');
          const prompt=addFluxRolePrompt('character',role);
          if(addFluxRolePrompt(prompt,role)!==prompt)throw Error('duplicate');"""
        result=subprocess.run(['node','--input-type=module','-e',script,json.dumps([self.body_catalog,self.body_module.BODY_REFERENCE_ROLE_PROMPT],ensure_ascii=False)],cwd=root,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_character_page_has_reference_selection(self):
        from http.server import SimpleHTTPRequestHandler
        from fastapi.testclient import TestClient
        from workflow.common.management_asgi import build_management_application
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with TestClient(app) as client:
                defaults=client.get('/management/assistant/flux-defaults/flux-character').json()
                self.assertEqual(defaults['guides'],self.body_catalog)
                self.assertEqual(defaults['rolePrompt'],self.body_module.BODY_REFERENCE_ROLE_PROMPT)
                response=client.get('/management/assistant/flux-character-guide/neutral-body-clothed')
                self.assertEqual(response.status_code,200)
                with Image.open(io.BytesIO(response.content)) as actual, self.body_module.load_body_reference_image('neutral-body-clothed') as original:
                    self.assertEqual(actual.tobytes(),original.tobytes())
                self.assertEqual(client.get('/management/assistant/flux-character-guide/unknown').status_code,404)


if __name__ == '__main__':
    unittest.main()
