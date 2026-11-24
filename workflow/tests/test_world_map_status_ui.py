"""월드맵의 빈 결과와 재조회 안내를 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class WorldMapStatusTests(unittest.TestCase):
    def test_thumbnail_retry_query_reaches_same_registered_image(self):
        import ast
        import io
        from types import SimpleNamespace
        from unittest.mock import patch
        from urllib.parse import urlsplit
        from workflow.common import map_asset_http

        root = Path(__file__).resolve().parents[2]
        source = ast.parse((root/'gui/serve.py').read_text())
        handler = next(node for node in ast.walk(source) if isinstance(node, ast.ClassDef) and node.name == 'ReviewRequestHandler')
        method = next(node for node in handler.body if isinstance(node, ast.FunctionDef) and node.name == 'do_GET')
        module = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
        scope = {'urlsplit': urlsplit}
        exec(compile(module, str(root/'gui/serve.py'), 'exec'), scope)
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory)/'map.png'
            image.write_bytes(b'isolated thumbnail')
            def resolve(path, asset_root, records, prefix):
                self.assertEqual(path, 'assets/ui/world-map/thumbnails/map.png')
                self.assertEqual(prefix, 'assets/ui/world-map/thumbnails')
                return image, {}
            def request(path):
                response = SimpleNamespace(path=path, wfile=io.BytesIO(), headers={}, status=None,
                    reject_retired_generator=lambda: False)
                response.send_response = lambda status: setattr(response, 'status', status)
                response.send_header = lambda name, value: response.headers.__setitem__(name, value)
                response.end_headers = lambda: None
                scope['do_GET'](response)
                return response
            with patch('workflow.domains.character_review.capture.handle_capture_asset_request', return_value=False), \
                 patch.object(map_asset_http, 'load_registered_tiles', return_value=(Path(directory), {})), \
                 patch.object(map_asset_http, 'resolve_registered_asset', side_effect=resolve):
                original = request('/management/map-assets/thumbnails/map.png?v=abc')
                retried = request('/management/map-assets/thumbnails/map.png?v=abc&retry=1')
            for response in (original, retried):
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers['Content-Type'], 'image/png')
                self.assertEqual(response.wfile.getvalue(), b'isolated thumbnail')

    def test_map_thumbnail_has_visible_failure_placeholder(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'world.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'WorldMap.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
const Thumbnail=require(process.argv[1]).WorldMapThumbnail;
const render=failed=>server.renderToStaticMarkup(React.createElement('svg',null,React.createElement(Thumbnail,{src:'/image?retry=2',x:100,y:100,failed})));
assert.match(render(false),/<image href="\\/image\\?retry=2"/);const failed=render(true);assert.match(failed,/미리보기 없음/);assert.doesNotMatch(failed,/<image/);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_empty_result_remains_visible_during_retry_and_error(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'world.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'WorldMap.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
const Status=require(process.argv[1]).WorldMapStatus;
const render=props=>server.renderToStaticMarkup(React.createElement(Status,props));
const base={loaded:true,mapCount:0,loading:false,error:''};
assert.match(render(base),/등록된 맵이 없습니다/);
for(const changes of [{loading:true},{error:'조회 실패'}]) {const text=render({...base,...changes});assert.match(text,/마지막으로 조회한 목록에 등록된 맵이 없습니다/);assert.match(text,/마지막 조회 결과/);}
assert.doesNotMatch(render({...base,loaded:false,loading:true}),/등록된 맵이 없습니다/);
assert.doesNotMatch(render({...base,mapCount:1}),/등록된 맵이 없습니다/);"""
            subprocess.run(['node', '-e', script, str(bundle)], cwd=gui, check=True, capture_output=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
