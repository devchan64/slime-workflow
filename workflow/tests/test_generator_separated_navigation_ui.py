"""독립 폼과 대화 내장 폼의 이력 탐색 계약을 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

class SeparatedGeneratorNavigationTests(unittest.TestCase):
    def test_legacy_video_and_audio_links_keep_original_service_and_session(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        cases=[('MiniMaxH3Page.jsx','default','minimax-h3-ref2va','/management/frame/minimax-h3-i2v-generator/'),
               ('MiniMaxH3Ref2VAPage.jsx','default','minimax-h3-i2v','/management/frame/minimax-h3-ref2va-generator/'),
               ('SoundEffectPage.jsx','HeartmulaPage','sfx-dasheng-audiogen','/management/frame/music-heartmula/'),
               ('SoundEffectPage.jsx','default','music-heartmula','/management/frame/sfx-dasheng-audiogen/')]
        with tempfile.TemporaryDirectory() as directory:
            for source,export,other_service,form in cases:
                with self.subTest(source=source,export=export):
                    bundle=Path(directory)/(source+'.cjs')
                    subprocess.run([str(gui/'node_modules/.bin/esbuild'),source,'--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
                    script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict'),Page=require(process.argv[1])[process.argv[2]];
                    const search='?job=2026-11-24_11-17-24-15f79014&session=test&service='+process.argv[3];
                    global.location={search,pathname:'/',href:'http://localhost/'+search};global.window={location:global.location};global.sessionStorage={getItem:()=>null};
                    const legacy=server.renderToStaticMarkup(React.createElement(Page));
                    assert.ok(legacy.includes('aria-label="생성기 페이지 이동"'),'legacy opens standalone history');
                    assert.ok(legacy.includes('href="'+process.argv[4]+'?session=test"'),'legacy keeps its original service and session');
                    const embedded=server.renderToStaticMarkup(React.createElement(Page,{embedded:true,session:'test'}));
                    assert.ok(embedded.includes('aria-label="생성기 영역 이동"'),'embedded form keeps its own navigation');"""
                    subprocess.run(['node','-e',script,str(bundle),export,other_service,form],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_current_work_observation_retry_contract(self):
        root=Path(__file__).resolve().parents[2]
        subprocess.run(['node','--test',str(root/'workflow/tests/active_generator_progress.test.mjs'),
                        str(root/'workflow/tests/history_observe_retry.test.mjs'),
                        str(root/'workflow/tests/generator_history_read_contract.test.mjs')],
                       cwd=root,check=True,capture_output=True,text=True)

    def test_history_input_links_keep_session_for_each_generator_family(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        cases=[('FluxHistoryPage.jsx','?service=flux-building&session=abc','/management/frame/flux-building-generator/?session=abc'),
               ('MiniMaxImageHistoryPage.jsx','?form=building&session=abc','/management/frame/minimax-h3-building-generator/?session=abc'),
               ('MiniMaxVideoHistoryPage.jsx','?service=minimax-h3-ref2va&session=abc','/management/frame/minimax-h3-ref2va-generator/?session=abc'),
               ('WanVideoHistoryPage.jsx','?service=wan22-vace&session=abc','/management/frame/wan22-vace-generator/?session=abc'),
               ('WanVideoHistoryPage.jsx','?service=wan22-i2v&session=abc','/management/frame/wan22-i2v-generator/?session=abc'),
               ('AudioHistoryPage.jsx','?service=music-heartmula&session=abc','/management/frame/music-heartmula/?session=abc'),
               ('KimodoHistoryPage.jsx','?session=abc','/management/frame/kimodo-generator/?session=abc'),
               ('DwposeHistoryPage.jsx','?session=abc','/management/frame/dwpose-generator/?session=abc')]
        with tempfile.TemporaryDirectory() as directory:
            for source,query,expected in cases:
                with self.subTest(source=source):
                    bundle=Path(directory)/(source+'.cjs')
                    subprocess.run([str(gui/'node_modules/.bin/esbuild'),source,'--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
                    script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict'),Page=require(process.argv[1]).default;
                    global.location={search:process.argv[2],pathname:'/',href:'http://localhost/'+process.argv[2]};global.window={location:global.location};global.sessionStorage={getItem:()=>null};
                    const html=server.renderToStaticMarkup(React.createElement(Page));assert.ok(html.includes('href="'+process.argv[3]+'"'),'input link must retain the session');assert.ok(html.includes('<span aria-current="page">생성기 생성이력</span>'),'current history must not reset selection');
                    global.location.search=process.argv[2]+'&job=invalid';const invalid=server.renderToStaticMarkup(React.createElement(Page));assert.ok(invalid.includes('작업 ID를 확인할 수 없습니다.'),'invalid job must be explained');"""
                    subprocess.run(['node','-e',script,str(bundle),query,expected],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_standalone_links_and_embedded_history_for_active_forms(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        cases=[('I2VPage.jsx','/management/frame/wan-video-history/'),('VacePage.jsx','/management/frame/wan-video-history/'),('FunControlPage.jsx','/management/frame/wan-video-history/'),('AnimatePage.jsx','/management/frame/wan-video-history/'),('DwposePage.jsx','/management/frame/dwpose-history/'),('KimodoPage.jsx','/management/frame/kimodo-history/')]
        with tempfile.TemporaryDirectory() as directory:
            for source,expected in cases:
                with self.subTest(source=source):
                    bundle=Path(directory)/(source+'.cjs')
                    subprocess.run([str(gui/'node_modules/.bin/esbuild'),source,'--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
                    script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict'),Page=require(process.argv[1]).default;
                      global.location={search:'?session=test',pathname:'/',href:'http://localhost/?session=test'};global.window={location:global.location};global.sessionStorage={getItem:()=>null};
                      const standalone=server.renderToStaticMarkup(React.createElement(Page));assert.ok(standalone.includes(process.argv[2]),'standalone history link');assert.ok(standalone.includes('target="_blank"'),'draft-preserving tab');assert.ok(standalone.includes('<span aria-current="page">생성기 입력폼</span>'),'current form does not reload and lose the draft');assert.ok(!standalone.includes('aria-label="생성기 영역 이동"'));
                      const embedded=server.renderToStaticMarkup(React.createElement(Page,{embedded:true,session:'test'}));assert.ok(embedded.includes('aria-label="생성기 영역 이동"'),'embedded navigation');assert.ok(embedded.includes('생성 이력'),'embedded history');
                      global.location.search='?job=2026-11-24_11-17-24-15f79014';const legacy=server.renderToStaticMarkup(React.createElement(Page));assert.ok(legacy.includes('aria-label="생성기 페이지 이동"'),'legacy job link retains history');assert.ok(legacy.includes('생성 이력'),'legacy history');"""
                    subprocess.run(['node','-e',script,str(bundle),expected,source],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
