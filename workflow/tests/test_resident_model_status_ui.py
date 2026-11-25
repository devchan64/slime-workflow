"""상주 모델 설정의 접근성 안내를 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class ResidentModelStatusUiTests(unittest.TestCase):
    def test_initial_switch_describes_loading(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'resident.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'ResidentModelStatus.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
const {default:Component,DflashSwitch}=require(process.argv[1]);
const html=server.renderToStaticMarkup(React.createElement(Component,{session:'session'}));
const input=html.match(/<input[^>]*role="switch"[^>]*>/)[0],id=input.match(/aria-describedby="([^"]+)"/)[1];
assert.match(input,/disabled=""/);assert.ok(html.includes('id="'+id+'" class="generator-visually-hidden">DFlash2 설정을 조회하고 있습니다.'));
for(const [props,message,disabled] of [
 [{settings:null,settingsError:'연결 실패',saving:false},'설정을 조회하지 못했습니다.',true],
 [{settings:{enabled:false,available:false},settingsError:'',saving:false},'초안 모델 다운로드를 완료하면',true],
 [{settings:{enabled:true,available:false},settingsError:'',saving:false},'다음 모델 로딩부터 적용합니다.',false],
 [{settings:{enabled:true,available:true},settingsError:'',saving:true},'설정을 저장하고 있습니다.',true]]){
 const result=server.renderToStaticMarkup(React.createElement(DflashSwitch,{...props,onChange:()=>{}}));
 assert.ok(result.includes(message));assert.equal(/disabled=""/.test(result),disabled);
 assert.equal(result.includes('class="dflash-status-help"'),Boolean(props.settingsError || (props.settings && !props.settings.enabled && !props.settings.available)));
}"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
