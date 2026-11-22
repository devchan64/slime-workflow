"""빌보드 가이드 입력 계약 검증."""
import unittest
from workflow.domains.image.billboard_guide_prompt import (
    BILLBOARD_LAYOUT_PROFILES, BILLBOARD_DEFAULT_SUBJECT,
    load_billboard_guide_image, compose_billboard_guide_prompt,
)


class BillboardGuidePromptTests(unittest.TestCase):
    def test_registered_reference_profiles(self):
        self.assertEqual(len(BILLBOARD_LAYOUT_PROFILES), 22)
        for selected_profile_name in BILLBOARD_LAYOUT_PROFILES:
            self.assertEqual(load_billboard_guide_image(selected_profile_name).size, (1024, 1024))
            selected_prompt_text = compose_billboard_guide_prompt(selected_profile_name, BILLBOARD_DEFAULT_SUBJECT)
            self.assertLess(len(selected_prompt_text.split()), 100)
            self.assertIn('80%', selected_prompt_text)
            if selected_profile_name == '2x2-lake-boulders':
                self.assertIn('2x2 footprint', selected_prompt_text)
                self.assertIn('rounded lake-worn', selected_prompt_text)
                continue
            if selected_profile_name == '4x4-rooted-stump':
                self.assertIn('4x4 footprint', selected_prompt_text)
                self.assertIn('rear roots', selected_prompt_text)
                continue
            if selected_profile_name == '1x1-grass-cover':
                self.assertIn('height 35–50', selected_prompt_text)
                self.assertIn('no soil block', selected_prompt_text)
                continue
            if selected_profile_name == '1x1-rooted-grass':
                self.assertIn('Three rooted tufts', selected_prompt_text)
                self.assertIn('maximum 110', selected_prompt_text)
                continue
            if selected_profile_name == '2x1-weathered-rock':
                self.assertIn('No stacked slabs', selected_prompt_text)
            if selected_profile_name.endswith('medium'):
                self.assertIn('height 260 relative to tile width 260', selected_prompt_text)
            if selected_profile_name == '1x3-fallen-log':
                self.assertIn('upper-right to lower-left', selected_prompt_text)
                self.assertIn('height 80–105 relative to tile width 300', selected_prompt_text)
                self.assertNotIn('wall', selected_prompt_text)
                continue
            self.assertIn('rear flush' if selected_profile_name.endswith(('tall', 'medium')) else f"height { {'1x1-low-2x': 180, '1x1-low-4x': 360}.get(selected_profile_name, 90)}", selected_prompt_text)

    def test_invalid_inputs_rejected(self):
        for selected_profile_name in ('../secret', '4x4-low', ''):
            with self.assertRaises(ValueError):
                load_billboard_guide_image(selected_profile_name)
        for selected_subject_text in ('', 'rock ' * 100):
            with self.assertRaises(ValueError):
                compose_billboard_guide_prompt('3x1-tall', selected_subject_text)

    def test_flux_guides_are_distinct_and_validate_inputs(self):
        import base64
        from io import BytesIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from fastapi.testclient import TestClient
        from http.server import SimpleHTTPRequestHandler
        from PIL import Image
        from workflow.common.management_asgi import build_management_application
        from workflow.domains.image.building_prompt import BUILDING_STRUCTURE_RECORDS,load_building_layout_preset
        with TemporaryDirectory() as directory:
            root=Path(directory);app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with TestClient(app) as client:
                billboard=client.get('/management/assistant/flux-defaults/flux-billboard').json()
                building=client.get('/management/assistant/flux-defaults/flux-building').json()
                self.assertEqual(set(billboard['layouts']),set(BILLBOARD_LAYOUT_PROFILES))
                self.assertEqual({guide['id'] for guide in building['guides']},set(BUILDING_STRUCTURE_RECORDS))
                self.assertEqual(len(building['guides']),50)
                for identifier,record in BUILDING_STRUCTURE_RECORDS.items():
                    guide=next(item for item in building['guides'] if item['id']==identifier)
                    self.assertIn(str(record['floors'])+'층',guide['label'])
                for subject in ('','  ','stone '*100):
                    self.assertEqual(client.post('/management/assistant/flux-billboard-guide',json={'layout':'3x1-tall','subject':subject}).status_code,422)
                response=client.post('/management/assistant/flux-billboard-guide',json={'layout':'3x1-tall','subject':'stone house'})
                self.assertEqual(response.status_code,200,response.text)
                self.assertIn('stone house',response.json()['prompt'])
                self.assertEqual(Image.open(BytesIO(base64.b64decode(response.json()['image']))).size,(1024,1024))
                self.assertEqual(client.post('/management/assistant/flux-billboard-guide',json={'layout':'../invalid','subject':'stone'}).status_code,422)
                self.assertEqual(client.get('/management/assistant/flux-building-guide/building-structure-01').status_code,200)
        with self.assertRaises(ValueError):load_building_layout_preset('4x4-south',80)
        with self.assertRaises(ValueError):load_building_layout_preset('building-structure-01',160)
