"""빌보드 숫자 입력의 오류 설명 연결을 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class BillboardNumericUiTests(unittest.TestCase):
    def test_crop_threshold_has_help_and_busy_reason(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'crop.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'BillboardCrop.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
              const {default:Crop,invalidCropThreshold}=require(process.argv[1]);
              for(const value of ['0','5','254'])assert.equal(invalidCropThreshold(value),false);
              for(const value of ['',null,'-1','255','1.5','not-a-number'])assert.equal(invalidCropThreshold(value),true);
              const html=server.renderToStaticMarkup(React.createElement(Crop,{source:{texture:'asset',revision:'r'},busy:true,setBusy:()=>{},onSaved:()=>{}}));
              const fieldset=html.match(/<fieldset[^>]*>/)[0],id=fieldset.match(/aria-describedby="([^"]+)"/)[1];
              assert.ok(html.includes('id="'+id+'" role="status"'));assert.match(fieldset,/disabled=""/);
              const input=html.match(/<input[^>]*type="number"[^>]*>/)[0],help=input.match(/aria-describedby="([^"]+)"/)[1];
              assert.ok(html.includes('id="'+help+'" class="billboard-crop-help"'));assert.match(input,/step="1"/);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_error_is_described_without_changing_label(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'billboard.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'BillboardProperties.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
              const Field=require(process.argv[1]).BillboardNumericField;
              const render=error=>server.renderToStaticMarkup(React.createElement(Field,{label:'표시 높이',value:'',required:true,error,onChange:()=>{}}));
              const invalid=render(['height-error','값을 입력하세요.']);
              assert.match(invalid,/<label>표시 높이<input[^>]*aria-invalid="true"[^>]*aria-describedby="height-error"[^>]*\\/><\\/label><span id="height-error">값을 입력하세요[.]<\\/span>/);
              const valid=render(null);assert.doesNotMatch(valid,/aria-invalid|aria-describedby|height-error/);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})


if __name__=='__main__':
    unittest.main()
