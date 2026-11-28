import os
from pathlib import Path
import subprocess
import tempfile
import unittest

class ImageHistoryContextUiTests(unittest.TestCase):
    def test_invalid_legacy_image_job_opens_history_with_reselection(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'image.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'MiniMaxH3ImagePage.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict'),Page=require(process.argv[1]).default;
              global.location={search:'?job=invalid&session=abc',pathname:'/',href:'http://localhost/?job=invalid&session=abc'};global.window={location:global.location};global.sessionStorage={getItem:()=>null};
              for(const building of [false,true]){const html=server.renderToStaticMarkup(React.createElement(Page,{building}));assert.match(html,/작업 ID를 확인할 수 없습니다/);assert.match(html,/생성기 생성이력/);assert.ok(!html.includes('aria-label="생성 입력"'));assert.ok(html.includes('session=abc'));}"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_flux_session_and_building_form_are_retained(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            for source in ('FluxHistoryPage.jsx','MiniMaxImageHistoryPage.jsx'):
                bundle=Path(directory)/(source+'.cjs')
                subprocess.run([str(gui/'node_modules/.bin/esbuild'),source,'--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
                if source.startswith('Flux'):
                    script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');global.location={search:'?service=flux-building&session=abc'};const {default:Page,fluxHistoryUrl:url}=require(process.argv[1]);const html=server.renderToStaticMarkup(React.createElement(Page));assert.ok(html.includes('/management/frame/flux-building-generator/?session=abc'));assert.equal(url('flux-building','bad','abc'),'/management/frame/flux-image-history/?service=flux-building&session=abc');"""
                else:
                    script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');global.location={search:'?form=building&session=abc'};const {default:Page,minimaxImageHistoryUrl:url}=require(process.argv[1]);const html=server.renderToStaticMarkup(React.createElement(Page));assert.ok(html.includes('/management/frame/minimax-h3-building-generator/?session=abc'));assert.equal(url(true,undefined,'abc'),'/management/frame/minimax-h3-image-history/?form=building&session=abc');"""
                subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
