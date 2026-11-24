"""MiniMax H3 독립·대화 내 화면의 기본 렌더 계약."""
import os
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


class MiniMaxH3UiContractTests(unittest.TestCase):
    def test_saved_input_distinguishes_user_and_final_word_counts(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'saved-input.cjs'
            subprocess.run([str(gui / 'node_modules/.bin/esbuild'), 'SavedGeneratorInputs.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile=' + str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
              const Details=require(process.argv[1]).SavedInputDetails;
              const html=server.renderToStaticMarkup(React.createElement(Details,{request:{user_prompt:'red house',prompt:'red house in a garden',negative_prompt:'blur noise',translation_source_ko:'빨간 집'},details:'saved'}));
              assert.match(html,/사용자 프롬프트 2단어/);assert.match(html,/저장 프롬프트 5단어/);assert.match(html,/부정 프롬프트 2단어/);assert.match(html,/번역 원문 2단어/);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_image_saved_status_matches_common_input_display(self):
        from workflow.domains.minimax_h3_image.generation import MiniMaxH3ImageManager
        root = Path(__file__).resolve().parents[2]
        request = {'action':'generate','prompt':'a small red house','images':[],
                   'width':1024,'height':1024,'steps':6,'seed':42}
        manager = MiniMaxH3ImageManager()
        saved = manager.validate_generation_request(request)
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory) / '2026-11-24_12-34-56-1234abcd'
            job.mkdir()
            (job / 'request.json').write_text(json.dumps(saved), encoding='utf-8')
            status = manager.enrich_generation_status(job, {'status':'completed'})
        script = """import assert from 'node:assert/strict';
          import {historyInputSummary,historyInputDetails} from './gui/historyInputSummary.mjs';
          let input='';for await(const part of process.stdin)input+=part;const data=JSON.parse(input);
          assert.equal(data.id,'2026-11-24_12-34-56-1234abcd');
          const summary=historyInputSummary(data.request,'minimax-h3-image').join(' ');
          assert.match(summary,/1024 × 1024/);assert.match(summary,/6스텝/);assert.match(summary,/시드 42/);
          assert.match(historyInputDetails(data.request),/a small red house/);"""
        subprocess.run(['node','--input-type=module','-e',script], cwd=root, input=json.dumps(status), text=True, check=True, capture_output=True)

    def test_image_review_reasons_and_initial_render(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'minimax-image.cjs'
            subprocess.run([str(gui / 'node_modules/.bin/esbuild'), 'MiniMaxH3ImagePage.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--external:react-dom', '--outfile=' + str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
              global.location={search:''};const {default:Page,minimaxImageReasons:reasons}=require(process.argv[1]);
              assert.equal(reasons({model:{generation_ready:true},prompt:'test',seed:42}).filter(Boolean).length,0);
              assert.match(reasons({model:{generation_ready:true},prompt:' ',seed:-1}).filter(Boolean).join(' '),/프롬프트.*시드/);
              for(const embedded of [false,true]){const html=server.renderToStaticMarkup(React.createElement(Page,{embedded}));
                assert.match(html,/모델 준비 상태를 확인하세요/);assert.match(html,/프롬프트를 입력하세요/);assert.match(html,/aria-describedby=/);
                assert.match(html,/aria-label="생성기 영역 이동"/);assert.match(html,/생성 입력/);assert.match(html,/생성 이력/);assert.match(html,/작업 결과/);}"""
            subprocess.run(['node', '-e', script, str(bundle)], cwd=gui, check=True, capture_output=True, text=True, env={**os.environ, 'NODE_PATH': str(gui / 'node_modules')})

    def test_standalone_and_embedded_render(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'minimax.cjs'
            subprocess.run([str(gui / 'node_modules/.bin/esbuild'), 'MiniMaxH3Page.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--external:react-dom', '--outfile=' + str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server');
              global.location={search:''};
              const Page=require(process.argv[1]).default;
              for(const embedded of [false,true]){
                const html=server.renderToStaticMarkup(React.createElement(Page,{embedded,session:'session-test'}));
                for(const text of ['MiniMax H3 I2V 영상 생성','생성 입력','첫 프레임 이미지','장면·동작 프롬프트','생성 요청 검토'])
                  if(!html.includes(text))throw Error('missing '+text+' embedded='+embedded);
                if(html.includes('헤르메스 대화로 돌아가기')===embedded)throw Error('return link mismatch');
              }"""
            subprocess.run(['node', '-e', script, str(bundle)], cwd=gui, check=True, capture_output=True, text=True, env={**os.environ, 'NODE_PATH': str(gui / 'node_modules')})


if __name__ == '__main__':
    unittest.main()
