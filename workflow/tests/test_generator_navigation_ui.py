"""생성기 영역 이동의 초점 대상을 확인한다."""
from pathlib import Path
import subprocess
import tempfile
import unittest


class GeneratorNavigationUiTests(unittest.TestCase):
    def test_focuses_noninteractive_regions_without_changing_controls(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'navigation.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'GeneratorSectionNavigation.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const assert=require('node:assert/strict'),{focusGeneratorRegion:focus}=require(process.argv[1]);
              const events=[],element={matches:()=>false,setAttribute:(...args)=>events.push(args),scrollIntoView:arg=>events.push(arg),focus:arg=>events.push(arg)};
              focus(element);assert.deepEqual(events,[['tabindex','-1'],{block:'start'},{preventScroll:true}]);
              events.length=0;element.matches=()=>true;focus(element);assert.equal(events.length,2);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True)
