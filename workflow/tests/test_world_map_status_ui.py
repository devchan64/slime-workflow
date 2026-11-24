"""월드맵의 빈 결과와 재조회 안내를 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class WorldMapStatusTests(unittest.TestCase):
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
