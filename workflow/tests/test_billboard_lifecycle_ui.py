"""빌보드 폐기 검토의 표시 입력을 확인한다."""
import subprocess
import tempfile
import unittest
from pathlib import Path


class BillboardLifecycleUiTests(unittest.TestCase):
    def test_retirement_preview_rejects_wrong_target_and_malformed_impacts(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'lifecycle.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'BillboardLifecycle.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const assert=require('node:assert/strict'),{validRetirementPreview:valid,validResizeResult:resize}=require(process.argv[1]);
            const ok={texture:'tree',token:'a'.repeat(64),maps:[{map:'forest',removed:2}]};
            assert.equal(valid(ok,'tree'),true);
            for(const value of [null,{...ok,texture:'other'},{...ok,token:'a'}, {...ok,maps:[null]}, {...ok,maps:[{map:'forest',removed:-1}]}, {...ok,maps:[{map:'forest',removed:'2'}]}])assert.equal(valid(value,'tree'),false);
            const file={request:{path:'assets/billboards/tree.png',size:128},before:[512,256]};
            const db={request:{texture:'tree',size:128},before:[512,256]};
            assert.equal(resize({path:file.request.path,size:[128,64]},file,'tree'),true);
            assert.equal(resize({texture:'tree',after:[128,64]},db,'tree'),true);
            for(const value of [null,{path:'other',size:[128,64]},{path:file.request.path,size:[256,128]},{path:file.request.path,size:[128,-1]}])assert.equal(resize(value,file,'tree'),false);
            assert.equal(resize({texture:'other',after:[128,64]},db,'tree'),false);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True)
