import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class WriterInputLockUiTests(unittest.TestCase):
    def test_uncertain_and_proposal_locks_explain_disabled_input(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'writer-actions.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'WriterActions.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--external:react-dom', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """global.location={search:'',pathname:'/'};let uncertain=false;global.sessionStorage={getItem:()=>uncertain?'1':null};
              const React=require('react'),server=require('react-dom/server'),{default:Actions,writerProposalModeLabel,WriterWorkspaceState}=require(process.argv[1]);
              if(writerProposalModeLabel('toString')!=='toString' || writerProposalModeLabel('write')!=='작성 제안' || writerProposalModeLabel({})!=='작업 종류 확인 불가')throw Error('작업 종류 표시 오류');
              const workspace={configured:true,ready:true,trained:true};
              const state=stale=>server.renderToStaticMarkup(React.createElement(WriterWorkspaceState,{workspace,stale}));
              if(!state(false).includes('요청할 수 있습니다') || !state(true).includes('요청할 수 없습니다') || state(true).includes('요청할 수 있습니다'))throw Error('이전 준비 상태 안내 오류');
              const active=server.renderToStaticMarkup(React.createElement(WriterWorkspaceState,{workspace:{...workspace,active_job:'job'},stale:true}));
              if(!active.includes('마지막 조회에서 진행 중인 작업'))throw Error('이전 작업 상태 안내 오류');
              for(const mode of ['normal','uncertain','proposal']){uncertain=mode==='uncertain';const props=mode==='proposal'?{proposalScope:{job:'id'}}:{};console.log(server.renderToStaticMarkup(React.createElement(Actions,props)));}"""
            lines = subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}).splitlines()
        self.assertEqual(len(lines),3)
        self.assertNotIn('<fieldset disabled=',lines[0])
        self.assertIn('aria-disabled="true"',lines[0])
        self.assertIn('작업 준비 상태를 확인하고 있습니다.',lines[0])
        for markup in lines[1:]:
            self.assertRegex(markup,r'<fieldset disabled="" aria-describedby="[^"]+"')
        self.assertIn('이전 요청의 접수 여부',lines[1])
        self.assertIn('대화 제안의 접수 상태를 확인하세요',lines[2])


if __name__ == '__main__':
    unittest.main()
