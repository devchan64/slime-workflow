"""Gradio 전환 완료 관리도구의 이전 UI가 다시 제공되지 않는지 검증한다."""
import io
import json
from types import SimpleNamespace
import unittest

from tools.review.domains.image.image_generation import ImageGenerationManager
from tools.review.common.retired_momask import RetiredMoMaskHandler as MoMaskGenerationManager
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

    def test_hidden_generator_ui_rejected_but_record_routes_preserved(self):
        import ast
        from pathlib import Path
        from unittest.mock import Mock
        from urllib.parse import urlsplit, parse_qs
        from tools.review import serve
        current_source_tree = ast.parse(Path(serve.__file__).read_text())
        current_reject_method = next(current_node for current_node in ast.walk(current_source_tree)
                                     if isinstance(current_node, ast.FunctionDef) and current_node.name == 'reject_retired_generator')
        current_compiled_module = ast.fix_missing_locations(ast.Module(body=[current_reject_method], type_ignores=[]))
        current_runtime_scope = {'urlsplit':urlsplit, 'parse_qs':parse_qs}
        exec(compile(current_compiled_module, serve.__file__, 'exec'), current_runtime_scope)
        for current_tool_name, current_service_path in (
                ('image-generator','/image-generation'), ('three-reference-generator','/image-generation-2511'),
                ('floor-tile-generator','/floor-tile-generator'), ('seamless-tile-generator','/seamless-tile-generator')):
            for current_ui_path in ('/?tool='+current_tool_name, '/management/frame/'+current_tool_name+'/', current_service_path+'/'):
                current_http_handler = SimpleNamespace(path=current_ui_path, send_error=Mock())
                with self.subTest(path=current_ui_path):
                    self.assertTrue(current_runtime_scope['reject_retired_generator'](current_http_handler))
                    self.assertEqual(current_http_handler.send_error.call_args.args[0],410)
            for current_record_suffix in ('/history','/jobs/example/result.png'):
                current_http_handler = SimpleNamespace(path=current_service_path+current_record_suffix, send_error=Mock())
                with self.subTest(path=current_http_handler.path):
                    self.assertFalse(current_runtime_scope['reject_retired_generator'](current_http_handler))
                    current_http_handler.send_error.assert_not_called()
