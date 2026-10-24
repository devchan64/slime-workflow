"""격리된 크롭 저장·픽셀 좌표 보존·실패 복구 검증."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml
from PIL import Image
from tools.review.domains.map_assets import crop, editor


class MapAssetCropTests(unittest.TestCase):
    def setUp(self):
        current_temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(current_temp_directory.cleanup)
        self.current_asset_root = Path(current_temp_directory.name) / 'slime-assets'
        self.current_image_path = self.current_asset_root / 'assets/billboards/sample.png'
        self.current_image_path.parent.mkdir(parents=True)
        current_source_image = Image.new('RGBA', (100, 120))
        current_source_image.paste((80, 90, 100, 255), (20, 30, 80, 100))
        current_source_image.putpixel((10, 30), (80, 90, 100, 6))
        current_source_image.save(self.current_image_path)
        self.current_property_values = dict(anchorX=.2, anchorY=.5, displayHeight=240, groundFootprintColumns=2, groundFootprintRows=1, billboardAnchorMode='tile-intersection', shadowScaleX=1, shadowScaleY=1)
        current_property_path = self.current_asset_root / 'assets/maps/sprite-display-properties.yaml'
        current_property_path.parent.mkdir(parents=True)
        current_property_path.write_text(yaml.safe_dump({'data': {'sample': self.current_property_values}}))
        current_property_hash = hashlib.sha256(current_property_path.read_bytes()).hexdigest()
        current_image_hash = hashlib.sha256(self.current_image_path.read_bytes()).hexdigest()
        (self.current_asset_root / 'asset-registry.yaml').write_text(yaml.safe_dump({'assets': [{'path': 'assets/billboards/sample.png', 'sha256': current_image_hash}, {'path': 'assets/maps/sprite-display-properties.yaml', 'sha256': current_property_hash}]}))
        self.current_catalog_record = {'billboards': [{'texture_key': 'sample', 'source_file': {'path': 'assets/billboards/sample.png'}}]}
        (self.current_image_path.parent / 'catalog.yaml').write_text(yaml.safe_dump(self.current_catalog_record))
        current_backend_path = self.current_asset_root.parent / 'slime-backend/map-data.lock.yaml'
        current_backend_path.parent.mkdir();current_backend_path.write_text('sha256: ' + current_property_hash)
        current_frontend_root = self.current_asset_root.parent / 'slime-frontend'
        current_frontend_root.mkdir()
        for current_lock_name in ('map-assets.lock.yaml', 'sprite-assets.lock.yaml'):
            (current_frontend_root / current_lock_name).write_text('sha256: ' + current_image_hash)
        for current_patch_value in (patch.object(editor, 'build_catalog_reference', return_value=self.current_catalog_record), patch.object(crop, 'build_catalog_reference', return_value=self.current_catalog_record), patch.object(crop, 'read_editor_snapshot', side_effect=lambda: editor.read_editor_snapshot(self.current_asset_root)), patch.object(crop, 'CROP_HISTORY_DIRECTORY', self.current_asset_root.parent / 'history')):
            current_patch_value.start();self.addCleanup(current_patch_value.stop)
        self.current_request_payload = {'texture': 'sample', 'revision': editor.read_editor_snapshot(self.current_asset_root)[3]}

    def test_pixel_world_position_and_commit(self):
        current_preview_result = crop.preview_billboard_crop(self.current_request_payload)
        self.assertEqual(current_preview_result['bounds'], [10, 30, 80, 100])
        current_new_properties = current_preview_result['properties']
        self.assertEqual(current_new_properties['displayHeight'], 140)
        for current_pixel_x, current_pixel_y in ((20, 30), (79, 99)):
            self.assertAlmostEqual(.2 * 160 - 100 + current_pixel_x * 2, current_new_properties['anchorX'] * 160 - 70 + (current_pixel_x - 10) * 2, delta=.8)
            self.assertAlmostEqual(.5 * 80 - 240 + current_pixel_y * 2, current_new_properties['anchorY'] * 80 - 140 + (current_pixel_y - 30) * 2, delta=.4)
        current_save_result = crop.save_billboard_crop({**self.current_request_payload, 'token': current_preview_result['token']})
        self.assertTrue(current_save_result['saved'])
        with Image.open(self.current_image_path) as current_saved_image:
            self.assertEqual(current_saved_image.size, (70, 70))
        current_next_request = {**self.current_request_payload, 'revision': editor.read_editor_snapshot(self.current_asset_root)[3]}
        current_next_preview = crop.preview_billboard_crop(current_next_request)
        self.assertFalse(current_next_preview['changed'])
        self.assertFalse(crop.save_billboard_crop({**current_next_request, 'token': current_next_preview['token']})['saved'])

    def test_stale_and_empty_rejected(self):
        with self.assertRaises(ValueError):crop.preview_billboard_crop({**self.current_request_payload, 'revision': 'stale'})
        with self.assertRaises(ValueError):crop.save_billboard_crop({**self.current_request_payload, 'token': 'invalid'})
        Image.new('RGBA', (100, 120)).save(self.current_image_path)
        with self.assertRaisesRegex(ValueError, '알파값 6 이상'):crop.preview_billboard_crop(self.current_request_payload)

    def test_catalog_failure_restores_every_file(self):
        current_preview_result = crop.preview_billboard_crop(self.current_request_payload)
        current_original_files = {current_file_path: current_file_path.read_bytes() for current_file_path in self.current_asset_root.parent.rglob('*') if current_file_path.is_file()}
        with patch.object(crop, 'build_catalog_reference', side_effect=ValueError('카탈로그 실패')):
            with self.assertRaises(ValueError):crop.save_billboard_crop({**self.current_request_payload, 'token': current_preview_result['token']})
        for current_file_path, current_file_bytes in current_original_files.items():
            self.assertEqual(current_file_path.read_bytes(), current_file_bytes)

    def test_square_shadow_geometry_is_preserved(self):
        current_property_path = self.current_asset_root / 'assets/maps/sprite-display-properties.yaml'
        current_property_document = yaml.safe_load(current_property_path.read_text())
        current_property_document['data']['sample']['groundFootprintColumns'] = 1
        current_property_path.write_text(yaml.safe_dump(current_property_document))
        current_request_payload = {**self.current_request_payload, 'revision': editor.read_editor_snapshot(self.current_asset_root)[3]}
        current_preview_result = crop.preview_billboard_crop(current_request_payload)
        current_new_properties = current_preview_result['properties']
        self.assertAlmostEqual(min(240 * .76, 176), min(current_new_properties['displayHeight'] * .76, 176) * current_new_properties['shadowScaleX'], delta=.6)
        self.assertAlmostEqual(min(240 * .76, 176), min(current_new_properties['displayHeight'] * .76, 176) * current_new_properties['shadowScaleY'], delta=.6)

    def test_gateway_and_ui_confirmation_contract(self):
        from tools.review.common.management_gateway import MANAGEMENT_COMMAND_ROUTES, MANAGEMENT_SERVICE_COMMANDS
        from tools.review.ui.gradio.asset_editor_app import preview_selected_asset_crop, confirm_selected_asset_crop
        self.assertIn('asset-crop', MANAGEMENT_SERVICE_COMMANDS['map-assets'])
        self.assertEqual(MANAGEMENT_COMMAND_ROUTES['asset-crop-preview'], ('POST', '/editor-crop-preview'))
        current_detail_record = {'texture':'sample','name':'샘플','properties':self.current_property_values}
        current_input_values = [.2,.5,2,1,240,'bottom',0,0,1,1,False]
        current_preview_record = crop.preview_billboard_crop(self.current_request_payload)
        with patch('tools.review.ui.gradio.asset_editor_app.execute_remote_management_command',return_value=current_preview_record) as current_remote_command:
            current_ui_result = preview_selected_asset_crop({'revision':self.current_request_payload['revision'],'assets':[current_detail_record]}, current_detail_record,*current_input_values)
            self.assertTrue(current_ui_result[1]['visible'])
            self.assertEqual(current_ui_result[0]['token'], current_preview_record['token'])
            with self.assertRaises(Exception):
                confirm_selected_asset_crop({'assets':[current_detail_record]}, {**current_detail_record,'texture':'other'}, current_ui_result[0],*current_input_values)
            self.assertEqual(current_remote_command.call_count,1)

    def test_alpha_five_excluded_and_six_retained(self):
        with Image.open(self.current_image_path) as current_source_image:
            current_source_image.putpixel((0, 0), (80, 90, 100, 5))
            current_source_image.putpixel((99, 119), (80, 90, 100, 5))
            current_source_image.save(self.current_image_path)
        current_preview_result = crop.preview_billboard_crop(self.current_request_payload)
        self.assertEqual(current_preview_result['bounds'], [10, 30, 80, 100])
        self.assertEqual(current_preview_result['alpha_threshold'], 5)
        Image.new('RGBA', (100, 120), (80, 90, 100, 5)).save(self.current_image_path)
        with self.assertRaisesRegex(ValueError, '알파값 6 이상'):
            crop.preview_billboard_crop(self.current_request_payload)

    def test_crop_uses_saved_catalog_after_property_save(self):
        from tools.review.ui.gradio.asset_editor_app import build_selected_crop_changes
        current_stale_detail={'texture':'sample','name':'샘플','properties':self.current_property_values}
        current_saved_detail={**current_stale_detail,'properties':{**self.current_property_values,'displayHeight':248.74}}
        current_catalog_record={'revision':'saved-revision','assets':[current_saved_detail]}
        current_input_values=[.2,.5,2,1,248.74,'bottom',0,0,1,1,False]
        self.assertEqual(build_selected_crop_changes(current_catalog_record,current_stale_detail,current_input_values),[])
        current_input_values[4]=250
        self.assertTrue(build_selected_crop_changes(current_catalog_record,current_stale_detail,current_input_values))
