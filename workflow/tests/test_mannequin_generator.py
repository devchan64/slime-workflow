"""마네킨 제작 단계와 공용 생성 요청 연결 검증."""
import base64
import importlib
import io
import unittest

from workflow.domains.image.qwen_21_generation import validate_styled_qwen_request


class MannequinGeneratorTests(unittest.TestCase):
    def test_clothed_preset_uses_faced_body_and_preserves_face(self):
        current_module = importlib.import_module('generators.mannequin-generator.page.interface')
        current_description, current_preview, current_unused = current_module.preview_mannequin_preset('clothed')
        current_prompt, current_first_image, current_second_image = current_module.load_mannequin_preset('clothed')
        self.assertIn('neutral-body-faced-four-directions.png', current_description)
        self.assertIn('Preserve the existing facial features and expression', current_prompt)
        self.assertNotIn('no facial features', current_prompt.lower())
        self.assertEqual(current_preview.tobytes(), current_first_image.tobytes())
        self.assertIsNone(current_unused)
        self.assertIsNone(current_second_image)
        self.assertEqual(current_first_image.mode,'RGB')

    def test_presets_produce_valid_requests(self):
        import io
        from workflow.domains.image.flux_image_generation import FluxImageGenerationManager
        current_module = importlib.import_module('generators.mannequin-generator.page.interface')
        for current_key in current_module.MANNEQUIN_PRESET_RECORDS:
            with self.subTest(preset=current_key):
                current_prompt, *current_images = current_module.load_mannequin_preset(current_key)
                current_bytes=[]
                for image in filter(None,current_images):
                    buffer=io.BytesIO();image.save(buffer,format='PNG');current_bytes.append(base64.b64encode(buffer.getvalue()).decode())
                current_request = FluxImageGenerationManager('flux-mannequin').validate_generation_request({'action':'generate','prompt':current_prompt,'images':current_bytes,'width':768,'height':768,'steps':16,'seed':10107})
                self.assertEqual(current_request['steps'],16)
                self.assertEqual(len(current_bytes), 2 if current_key == 'face-on-body' else 1)
        current_description, current_body_preview, current_face_preview = current_module.preview_mannequin_preset('face-on-body')
        self.assertIn('참조 1: `neutral-body-four-directions.png`', current_description)
        self.assertIn('참조 2: `neutral-head-basic-four-directions.png`', current_description)
        self.assertEqual(current_body_preview.tobytes(), current_module.load_mannequin_preset('jointed')[1].tobytes())
        self.assertEqual(current_face_preview.tobytes(), current_module.load_mannequin_preset('face')[1].tobytes())
        current_description, current_preview, current_unused = current_module.preview_mannequin_preset('jointed')
        self.assertIn('neutral-body-four-directions.png', current_description)
        self.assertIsNotNone(current_preview)
        self.assertIsNone(current_unused)
        with self.assertRaises(ValueError):
            current_module.load_mannequin_preset('../outside')

    def test_mannequin_service_is_separate_from_general_qwen(self):
        from workflow.domains.image.mannequin_generation import MannequinGenerationManager
        from workflow.domains.image.qwen_21_generation import QwenPlainGenerationManager
        from workflow.common.management_gateway import MANAGEMENT_SERVICE_ROUTES, MANAGEMENT_SERVICE_COMMANDS
        from workflow.domains.image.three_reference_generation import validate_three_reference_job_path
        current_mannequin_manager = MannequinGenerationManager()
        current_general_manager = QwenPlainGenerationManager()
        self.assertNotEqual(current_mannequin_manager.job_storage_root, current_general_manager.job_storage_root)
        self.assertNotEqual(current_mannequin_manager.history_storage_path(), current_general_manager.history_storage_path())
        self.assertEqual(MANAGEMENT_SERVICE_ROUTES['mannequin-generator'], '/mannequin-generator')
        self.assertEqual(MANAGEMENT_SERVICE_COMMANDS['mannequin-generator'], MANAGEMENT_SERVICE_COMMANDS['qwen-21'])
        self.assertEqual(validate_three_reference_job_path(current_mannequin_manager.job_storage_root / 'example'), (current_mannequin_manager.job_storage_root / 'example').resolve())

    def test_page_integrates_with_management_menu(self):
        from http.server import SimpleHTTPRequestHandler
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from fastapi.testclient import TestClient
        from workflow.common.management_asgi import build_management_application
        from workflow.common.management_catalog import REACT_REVIEW_PATHS
        current_module=importlib.import_module('generators.mannequin-generator.page.interface')
        self.assertEqual(REACT_REVIEW_PATHS['flux-mannequin-generator'],'/management/frame/flux-mannequin-generator/')
        with TemporaryDirectory() as directory:
            root=Path(directory);app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with TestClient(app) as client:
                defaults=client.get('/management/assistant/flux-defaults/flux-mannequin').json()
                self.assertEqual({stage['id'] for stage in defaults['stages']},set(current_module.MANNEQUIN_PRESET_RECORDS))
                for stage,record in current_module.MANNEQUIN_PRESET_RECORDS.items():
                    response=client.get('/management/assistant/flux-mannequin-stage/'+stage)
                    self.assertEqual(response.status_code,200,response.text)
                    data=response.json();self.assertEqual(data['prompt'],record[3])
                    self.assertEqual(len(data['images']),2 if stage=='face-on-body' else 1)
                    self.assertEqual((data['width'],data['height']),(1024,1024) if stage=='face' else (768,1152))


if __name__ == '__main__':
    unittest.main()
