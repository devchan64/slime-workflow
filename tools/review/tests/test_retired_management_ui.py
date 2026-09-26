"""Gradio 전환 완료 관리도구의 이전 UI가 다시 제공되지 않는지 검증한다."""
import io
import json
from types import SimpleNamespace
import unittest

from tools.review.domains.image.image_generation import ImageGenerationManager
from tools.review.domains.momask.momask_generation import MoMaskGenerationManager
from tools.review.domains.tile.tile_generation import TileGenerationManager
from tools.review.ui_assets import resolve_review_ui_asset


class RetiredManagementUiTests(unittest.TestCase):
    def create_http_handler(self, current_path_value):
        response_status_values=[]
        return SimpleNamespace(path=current_path_value,command='GET',headers={'Host':'127.0.0.1:8770'},server=SimpleNamespace(server_port=8770),rfile=io.BytesIO(),wfile=io.BytesIO(),response_status_values=response_status_values,send_response=response_status_values.append,send_header=lambda *current_header_values:None,end_headers=lambda:None)

    def test_retired_generator_root_paths_return_gone(self):
        for current_manager_value,current_path_value in ((ImageGenerationManager(),'/image-generation/'),(ImageGenerationManager(three_reference_mode=True),'/image-generation-2511/'),(TileGenerationManager(),'/tile-map-generator/')):
            current_http_handler=self.create_http_handler(current_path_value)
            with self.subTest(path=current_path_value):
                self.assertTrue(current_manager_value.handle_image_request(current_http_handler))
                self.assertEqual(current_http_handler.response_status_values,[410])
                self.assertIn('이전 관리 화면은 폐기되었습니다.',json.loads(current_http_handler.wfile.getvalue())['error'])

    def test_momask_legacy_root_returns_gone(self):
        current_http_handler=self.create_http_handler('/momask-generator/')
        self.assertTrue(MoMaskGenerationManager().handle(current_http_handler))
        self.assertEqual(current_http_handler.response_status_values,[410])

    def test_retired_ui_assets_are_not_registered(self):
        for current_asset_name in ('image-generation.html','three-reference-generation.html','tile-generation.js','character-animation.html','character-animation.js','character-animation-assets.js','momask-studio.css'):
            with self.subTest(asset=current_asset_name),self.assertRaises(ValueError):
                resolve_review_ui_asset(current_asset_name)
