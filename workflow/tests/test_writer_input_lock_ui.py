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
              const React=require('react'),server=require('react-dom/server'),Actions=require(process.argv[1]).default;
              for(const mode of ['normal','uncertain','proposal']){uncertain=mode==='uncertain';const props=mode==='proposal'?{proposalScope:{job:'id'}}:{};console.log(server.renderToStaticMarkup(React.createElement(Actions,props)));}"""
            lines = subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')}).splitlines()
        self.assertEqual(len(lines),3)
        self.assertNotIn('<fieldset disabled=',lines[0])
        for markup in lines[1:]:
            self.assertRegex(markup,r'<fieldset disabled="" aria-describedby="[^"]+"')
        self.assertIn('이전 요청의 접수 여부',lines[1])
        self.assertIn('대화 제안의 접수 상태를 확인하세요',lines[2])


if __name__ == '__main__':
    unittest.main()
