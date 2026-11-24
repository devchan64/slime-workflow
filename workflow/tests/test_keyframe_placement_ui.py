"""키프레임 중복 출력 프레임의 오류 연결을 확인한다."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


class KeyframePlacementUiTests(unittest.TestCase):
    def test_loading_and_placement_reasons_are_connected_to_actions(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'keyframe.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'KeyframeCatalog.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),Actions=require(process.argv[1]).KeyframeActions;
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Actions,{row:{id:'key',tag:'pose'},selected:'',loading:true,loadingReasonId:'loading',disabled:true,disabledReasonId:'limit',choose:()=>{},add:()=>{},onPreview:()=>{}})));"""
            markup=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
        self.assertEqual(markup.count('disabled=""'),3)
        self.assertEqual(markup.count('aria-describedby="loading"'),2)
        self.assertIn('aria-describedby="limit loading"',markup)

    def test_pagination_describes_loading_and_error_on_displayed_page(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'keyframe.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'KeyframeCatalog.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),Pagination=require(process.argv[1]).KeyframePagination;
              const page={offset:0,next_offset:20,snapshot:'s'};
              for(const props of [{loading:true,error:''},{loading:false,error:'failed'}]) console.log(server.renderToStaticMarkup(React.createElement(Pagination,{page,reasonId:'hint',...props})));"""
            lines=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}).splitlines()
        self.assertIn('목록 조회가 끝나면',lines[0])
        self.assertIn('목록을 다시 조회한 뒤',lines[1])
        for markup in lines:
            self.assertIn('aria-describedby="hint"',markup)
            self.assertIn('disabled=""',markup)
            self.assertNotIn('이전 키프레임',markup)
            self.assertIn('다음 키프레임',markup)

    def test_maximum_placement_reason_is_visible(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'keyframe.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'KeyframeCatalog.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),Catalog=require(process.argv[1]).default;
              const rows=Array.from({length:20},(_,i)=>({id:String(i).padStart(32,'0'),tag:'자세',frame:i+1}));
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Catalog,{query:'',initialFrames:'30',initialRows:rows})));"""
            markup=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
        self.assertIn('키프레임은 최대 20개까지 배치할 수 있습니다.',markup)

    def test_duplicate_frames_are_described_and_block_validation(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'keyframe.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'KeyframeCatalog.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),Catalog=require(process.argv[1]).default;
              const rows=[{id:'a'.repeat(32),tag:'첫째',frame:'1'},{id:'b'.repeat(32),tag:'둘째',frame:1}];
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Catalog,{query:'',initialFrames:'30',initialRows:rows})));"""
            markup=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
        self.assertEqual(markup.count('aria-invalid="true"'),2)
        self.assertIn('aria-label="1번째 첫째 '+('a'*32)+' 출력 프레임"',markup)
        self.assertIn('aria-label="2번째 둘째 '+('b'*32)+' 출력 프레임"',markup)
        identifier=re.search(r'<p id="([^"]+)" role="alert">출력 프레임은 중복',markup).group(1)
        self.assertEqual(markup.count(f'aria-describedby="{identifier}"'),3)
        self.assertRegex(markup,r'<button[^>]*disabled=""[^>]*>원본과 배치 검증</button>')


if __name__ == '__main__':
    unittest.main()
