"""생성 확인 행동의 표시와 중복 입력 차단을 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class GenerationReviewActionsUiTests(unittest.TestCase):
    def test_review_prompt_shows_matching_word_count(self):
        gui = Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)/'review-prompt.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'ReviewPrompt.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
              const Prompt=require(process.argv[1]).default;
              const render=text=>server.renderToStaticMarkup(React.createElement(Prompt,{label:'부정 프롬프트',text}));
              assert.match(render('blur  noise'),/부정 프롬프트 2단어/);
              assert.match(render(''),/없음/);assert.match(render(''),/0단어/);
              assert.match(render('  \\n  '),/없음/);assert.match(render('  \\n  '),/0단어/);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_review_states_and_blocked_clicks(self):
        gui = Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)/'actions.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'GenerationReviewActions.jsx', '--bundle',
                            '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)],
                           cwd=gui, check=True, capture_output=True, text=True)
            script = """const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
              const Actions=require(process.argv[1]).default;
              const render=props=>server.renderToStaticMarkup(React.createElement(Actions,props));
              const busy=render({busy:true});
              assert.match(busy,/role=\"status\"/);assert.match(busy,/접수하고 있습니다/);
              assert.equal((busy.match(/aria-disabled=\"true\"/g)||[]).length,2);
              assert.equal((busy.match(/aria-describedby=/g)||[]).length,2);
              const blocked=render({disabledReason:'모델 준비 필요'});
              assert.match(blocked,/aria-describedby=/);assert.match(blocked,/모델 준비 필요/);
              React.useId=()=> 'reason';
              let calls=0;const handle=()=>calls++;
              for(const props of [{busy:true},{disabledReason:'준비 필요'}]){
                const children=Actions({...props,onCancel:handle,onConfirm:handle}).props.children;
                children[3].props.onClick();
                if(props.busy)children[2].props.onClick();
              }
              assert.equal(calls,0);
              const ready=Actions({onCancel:handle,onConfirm:handle}).props.children;
              ready[2].props.onClick();ready[3].props.onClick();assert.equal(calls,2);"""
            subprocess.run(['node', '-e', script, str(bundle)], cwd=gui, check=True,
                           capture_output=True, text=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})


if __name__ == '__main__':
    unittest.main()
