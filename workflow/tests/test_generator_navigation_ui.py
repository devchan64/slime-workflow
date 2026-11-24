"""생성기 영역 이동의 초점 대상을 확인한다."""
from pathlib import Path
import subprocess
import tempfile
import unittest


class GeneratorNavigationUiTests(unittest.TestCase):
    def test_input_navigation_opens_nested_cards(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'navigation.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'GeneratorSectionNavigation.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const assert=require('node:assert/strict'),Navigation=require(process.argv[1]).default;
              const outer={tagName:'DETAILS',open:false,parentElement:null},inner={tagName:'DETAILS',open:false,parentElement:outer};
              let focused=false;const input={parentElement:inner,matches:()=>true,setAttribute(){},scrollIntoView(){assert.equal(inner.open,true);assert.equal(outer.open,true)},focus(){focused=true}};
              const tree=Navigation({inputRef:{current:input},historyRef:{current:null},resultRef:{current:null},openOnNavigate:true});
              tree.props.children[1][0].props.onClick();assert.equal(focused,true);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True)

    def test_result_navigation_opens_collapsed_history_before_focus(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'navigation.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'GeneratorSectionNavigation.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const assert=require('node:assert/strict'),Navigation=require(process.argv[1]).default;
              const history={tagName:'DETAILS',open:false,parentElement:null};
              let focused=false;
              const result={tagName:'SECTION',parentElement:history,matches:()=>true,setAttribute(){},scrollIntoView(){assert.equal(history.open,true)},focus(){focused=true}};
              const tree=Navigation({inputRef:{current:null},historyRef:{current:null},resultRef:{current:result},resultReady:true,openOnNavigate:true});
              tree.props.children[1][2].props.onClick();assert.equal(history.open,true);assert.equal(focused,true);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True)

    def test_pending_result_navigates_to_history_and_opens_it(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'navigation.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'GeneratorSectionNavigation.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const assert=require('node:assert/strict'),Navigation=require(process.argv[1]).default;
              let focused=false;const detail={open:false};
              const summary={matches:()=>true,setAttribute(){},scrollIntoView(){assert.equal(detail.open,true)},focus(){focused=true}};
              const history={tagName:'DIV',parentElement:null,querySelector:s=>s==='details'?detail:summary};
              const tree=Navigation({inputRef:{current:null},historyRef:{current:history},resultRef:{current:null},resultReady:true});
              tree.props.children[1][2].props.onClick();assert.equal(detail.open,true);assert.equal(focused,true);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True)

    def test_focuses_noninteractive_regions_without_changing_controls(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'navigation.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'GeneratorSectionNavigation.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const assert=require('node:assert/strict'),{focusGeneratorRegion:focus}=require(process.argv[1]);
              const events=[],element={matches:()=>false,setAttribute:(...args)=>events.push(args),scrollIntoView:arg=>events.push(arg),focus:arg=>events.push(arg)};
              focus(element);assert.deepEqual(events,[['tabindex','-1'],['data-generator-navigation-focus',''],{block:'start'},{preventScroll:true}]);
              events.length=0;element.matches=()=>true;focus(element);assert.deepEqual(events,[['data-generator-navigation-focus',''],{block:'start'},{preventScroll:true}]);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True)
