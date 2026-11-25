"""지도 초안 파일 입력의 오류 설명 연결을 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class MapDraftFileInputTests(unittest.TestCase):
    def test_initial_map_controls_describe_loading(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'map.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'MapReview.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""global.location={pathname:'/management/frame/field-map',search:'',href:'http://localhost/management/frame/field-map',origin:'http://localhost'};
const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict'),{default:MapReview,mapSelectionReasons}=require(process.argv[1]);
const html=server.renderToStaticMarkup(React.createElement(MapReview));
assert.match(html,/<fieldset class="map-view-controls" disabled="" aria-describedby="status"/);
assert.match(html,/<p role="status" id="status">지도를 불러오는 중입니다[.]<\\/p>/);
assert.equal(mapSelectionReasons({draft:{},field:true,reading:true,saving:true}),'map-change-reason map-saving-status');
assert.equal(mapSelectionReasons({draft:null,field:true,reading:true,saving:false}),'map-reading-status');
assert.equal(mapSelectionReasons({draft:null,field:false,reading:false}),undefined);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_coordinate_errors_are_connected_to_each_input(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'map.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'MapReview.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
const Input=require(process.argv[1]).MapCoordinateInput;
const render=value=>server.renderToStaticMarkup(React.createElement(Input,{axis:'열',value,onChange:()=>{}}));
for(const value of ['', '-1', '1.5']){const html=render(value);const id=html.match(/aria-describedby=\"([^\"]+)\"/)[1];assert.match(html,/aria-invalid=\"true\"/);assert.ok(html.includes('id=\"'+id+'\">0 이상의 정수를 입력하세요.'));}
for(const value of ['0','12'])assert.doesNotMatch(render(value),/aria-invalid|aria-describedby|0 이상의 정수를 입력하세요/);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_map_canvas_exposes_visible_keyboard_help(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'map.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'MapReview.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
const Page=require(process.argv[1]).default;
function render(path){global.location=new URL('http://localhost'+path);return server.renderToStaticMarkup(React.createElement(Page));}
const field=render('/management/assistant/field-map/');
assert.match(field,/<p id="map-keyboard-help">.*Shift\\+방향키.*열·행 입력/);
assert.match(field,/<canvas[^>]*aria-describedby="map-keyboard-help"/);
assert.match(field,/<p id="map-cell-selection-help">.*열·행을 입력/);
assert.match(field,/<button aria-describedby="map-cell-selection-help"[^>]*>선택 셀 속성 조회<\\/button>/);
const town=render('/management/assistant/town-map/');assert.match(town,/id="map-keyboard-help"/);assert.doesNotMatch(town,/열·행 입력으로도/);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_error_and_pending_reason_are_connected(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'map.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'MapReview.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
const Input=require(process.argv[1]).MapDraftFileInput;
const render=props=>server.renderToStaticMarkup(React.createElement(Input,{onFile:()=>{},...props}));
const error=render({cellDirty:true,error:'잘못된 파일'});
assert.match(error,/aria-invalid="true"/);assert.match(error,/aria-describedby="map-cell-pending-reason map-import-error"/);assert.match(error,/id="map-import-error" role="alert"/);
const normal=render({cellDirty:false,error:''});assert.doesNotMatch(normal,/aria-invalid|aria-describedby|map-import-error/);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_navigation_connects_all_applicable_reasons(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'map.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'MapReview.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
const Nav=require(process.argv[1]).MapReviewNavigation;
const render=props=>server.renderToStaticMarkup(React.createElement(Nav,{field:true,destination:x=>'/'+x,onNavigate:()=>{},...props}));
const all=render({saving:true,cellDirty:true,unsafeAutosave:true});
assert.equal((all.match(/aria-describedby="map-saving-status map-cell-pending-reason map-storage-failure"/g)||[]).length,2);
assert.ok(all.includes('href="/town"'));assert.ok(all.includes('href="/battle"'));
assert.doesNotMatch(render({saving:false,cellDirty:false,unsafeAutosave:false}),/aria-describedby/);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
