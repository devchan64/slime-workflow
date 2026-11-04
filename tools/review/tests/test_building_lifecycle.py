"""격리된 원장에서 건물 등록과 삭제 계약을 확인한다."""
import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml
from PIL import Image
from tools.review.domains.map_assets.building_editor import execute_building_lifecycle
from tools.review.common.management_gateway import resolve_management_command

class BuildingLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.current_temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.current_temporary.cleanup)
        self.current_root=Path(self.current_temporary.name)
        (self.current_root/'assets/buildings').mkdir(parents=True)
        (self.current_root/'asset-registry.yaml').write_text('assets: []\n')
        current_image=Image.new('RGBA',(8,8),(0,0,0,0));current_image.putpixel((4,4),(1,2,3,255))
        current_stream=io.BytesIO();current_image.save(current_stream,format='PNG')
        self.current_encoded=base64.b64encode(current_stream.getvalue()).decode()
        self.current_request={'texture':'town-test-house-v1','generation':1,'requestId':'test-register','imageBase64':self.current_encoded,'properties':{'anchorX':.5,'anchorY':1}}

    def test_gateway_routes(self):
        self.assertEqual(resolve_management_command('map-assets','building-register',{}),('POST','/map-assets/editor-building-register'))
        self.assertEqual(resolve_management_command('map-assets','building-retire',{}),('POST','/map-assets/editor-building-retire'))

    def test_register_and_retire_keep_image(self):
        with patch('tools.review.domains.map_assets.building_editor.load_registered_tiles',return_value=(self.current_root,{})),patch('tools.review.domains.map_assets.building_editor.execute_content_api_request',return_value={'saved':True}) as current_remote:
            execute_building_lifecycle(self.current_request,'register')
            current_image=self.current_root/'assets/buildings/town-test-house-v1.png'
            self.assertTrue(current_image.exists())
            current_registry=yaml.safe_load((self.current_root/'asset-registry.yaml').read_text())
            self.assertEqual(current_registry['assets'][0]['path'],'assets/buildings/town-test-house-v1.png')
            execute_building_lifecycle({'texture':'town-test-house-v1','generation':2,'requestId':'test-retire'},'retire')
            self.assertTrue(current_image.exists())
            current_registry=yaml.safe_load((self.current_root/'asset-registry.yaml').read_text())
            self.assertEqual(current_registry['assets'][0]['source']['lifecycle_status'],'retired')
            self.assertEqual(current_remote.call_count,2)

    def test_bad_image_rejected_before_remote_write(self):
        self.current_request['imageBase64']=base64.b64encode(b'not png').decode()
        with patch('tools.review.domains.map_assets.building_editor.load_registered_tiles',return_value=(self.current_root,{})),patch('tools.review.domains.map_assets.building_editor.execute_content_api_request') as current_remote:
            with self.assertRaises(Exception):execute_building_lifecycle(self.current_request,'register')
            current_remote.assert_not_called()
            self.assertFalse(list((self.current_root/'assets/buildings').iterdir()))

    def test_backend_rejects_delete_without_touching_registry(self):
        with patch('tools.review.domains.map_assets.building_editor.load_registered_tiles',return_value=(self.current_root,{})),patch('tools.review.domains.map_assets.building_editor.execute_content_api_request',return_value={'saved':True}):
            execute_building_lifecycle(self.current_request,'register')
        current_registry_path=self.current_root/'asset-registry.yaml'
        current_registry_before=current_registry_path.read_bytes()
        with patch('tools.review.domains.map_assets.building_editor.load_registered_tiles',return_value=(self.current_root,{})),patch('tools.review.domains.map_assets.building_editor.execute_content_api_request',side_effect=ValueError('사용 중')):
            with self.assertRaisesRegex(ValueError,'사용 중'):
                execute_building_lifecycle({'texture':'town-test-house-v1','generation':2,'requestId':'test-retire'},'retire')
        self.assertEqual(current_registry_path.read_bytes(),current_registry_before)

    def test_ui_requires_selection_and_unchanged_confirmation(self):
        import gradio as gr
        from tools.review.ui.gradio.building_editor_panel import prepare_building_retirement,retire_building_editor_panel
        with self.assertRaises(gr.Error):prepare_building_retirement({})
        with self.assertRaises(gr.Error):prepare_building_retirement({'texture':'town-used-v1','maps':[{'map':'iseulon'}]})
        with patch('tools.review.ui.gradio.building_editor_panel.execute_remote_management_command') as current_remote:
            with self.assertRaises(gr.Error):retire_building_editor_panel({'generation':2},{'texture':'town-other-v1'}, {'texture':'town-test-v1'})
            current_remote.assert_not_called()
