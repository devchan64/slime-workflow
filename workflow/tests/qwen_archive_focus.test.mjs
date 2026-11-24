import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {qwenArchiveUrl} from '../../gui/qwenArchiveUrl.mjs';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

test('보관 결과 닫기는 사용 가능한 이력 초점을 복구한다',()=>{
  const source=readFileSync(new URL('../../gui/QwenArchive.jsx',import.meta.url),'utf8');
  const method='function closeResult(){'+source.split('function closeResult(){')[1].split('\n  async function readJob',1)[0];
  let selected='job',focused='';const document={body:{}};document.activeElement=document.body;
  const trigger={isConnected:true,disabled:true,focus(){focused='trigger';}},summary={isConnected:true,focus(){focused='summary';}};
  const context=vm.createContext({history:{state:{keep:true},replaceState(_state,_unused,url){this.url=url;}},location:{href:'http://localhost/archive?service=qwen&job=job'},qwenArchiveUrl,
    pendingFocus:{current:true},focusEpoch:{current:0},select:value=>selected=value,requestAnimationFrame:callback=>callback(),document,restoreLostFocus,
    triggerRef:{current:trigger},historyRef:{current:{querySelector:()=>summary}}});
  vm.runInContext(method,context);context.closeResult();assert.equal(selected,'');assert.equal(context.pendingFocus.current,false);assert.equal(focused,'summary');assert.equal(context.history.url.searchParams.has('job'),false);
  focused='';document.activeElement={};context.closeResult();assert.equal(focused,'');
});
test('보관 결과 닫기 뒤 새 선택이나 종료가 있으면 예약된 초점 복구를 건너뛴다',()=>{
  const source=readFileSync(new URL('../../gui/QwenArchive.jsx',import.meta.url),'utf8');
  const method='function closeResult(){'+source.split('function closeResult(){')[1].split('\n  async function readJob',1)[0];
  let scheduled,focused=false;const document={body:{}};document.activeElement=document.body;
  const context=vm.createContext({history:{state:null,replaceState(){}},location:{href:'http://localhost/archive?job=job'},qwenArchiveUrl,pendingFocus:{current:true},focusEpoch:{current:0},select:()=>{},requestAnimationFrame:fn=>scheduled=fn,document,restoreLostFocus,
    triggerRef:{current:{isConnected:true,disabled:false,focus(){focused=true;}}},historyRef:{current:null}});
  vm.runInContext(method,context);context.closeResult();context.focusEpoch.current++;scheduled();assert.equal(focused,false);
});
test('보관 결과를 열 때 잃은 초점을 복구하고 사용자가 옮긴 초점은 유지한다',()=>{
  const source=readFileSync(new URL('../../gui/QwenArchive.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  useEffect(()=>{\n    if(!id || !pendingFocus.current)'),end=source.indexOf('  },[id]);',start)+'  },[id]);'.length;assert.ok(start>=0 && end>start);
  for(const focusKind of ['body','trigger','other']){
    const body={},trigger={},other={},document={body,activeElement:focusKind==='body'?body:focusKind==='trigger'?trigger:other};let focused=false;
    const context=vm.createContext({document,id:'job',pendingFocus:{current:true},triggerRef:{current:trigger},resultRef:{current:{focus(){focused=true;}}},useEffect:fn=>fn()});
    vm.runInContext(source.slice(start,end),context);assert.equal(focused,focusKind!=='other');assert.equal(context.pendingFocus.current,false);
  }
});
