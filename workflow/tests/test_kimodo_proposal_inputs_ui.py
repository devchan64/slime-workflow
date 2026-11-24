import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class KimodoProposalInputsUiTests(unittest.TestCase):
    def test_sequence_prompt_connects_both_guidance_messages(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'generation.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'KimodoGeneration.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),Field=require(process.argv[1]).KimodoPromptField;
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Field,{value:'!',onChange:()=>{},reason:'문자 입력',reasonId:'reason',segmentHelp:'segments',segmentMismatch:true})));"""
            markup=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
        self.assertIn('aria-describedby="segments reason"',markup)
        self.assertIn('aria-invalid="true"',markup)
        self.assertIn('id="reason"',markup)
        self.assertIn('문자 입력',markup)

    def test_numeric_ranges_are_visible_and_connected_to_inputs(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'proposal.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'KimodoProposal.jsx','--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),Fields=require(process.argv[1]).KimodoProposalNumericFields;
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Fields,{proposal:{frames:30,steps:2,seed:1},onChange:()=>{}})));"""
            markup=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
        self.assertEqual(markup.count('<label>'),3)
        self.assertEqual(markup.count('step="1"'),3)
        for value in ('프레임 수','생성 단계','시드','min="30"','max="300"','min="2"','max="100"','min="0"','max="2147483647"'):
            self.assertIn(value,markup)


if __name__=='__main__':
    unittest.main()
