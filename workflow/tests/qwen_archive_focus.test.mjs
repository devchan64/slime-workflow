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
    pendingFocus:{current:true},select:value=>selected=value,requestAnimationFrame:callback=>callback(),document,restoreLostFocus,
    triggerRef:{current:trigger},historyRef:{current:{querySelector:()=>summary}}});
  vm.runInContext(method,context);context.closeResult();assert.equal(selected,'');assert.equal(context.pendingFocus.current,false);assert.equal(focused,'summary');assert.equal(context.history.url.searchParams.has('job'),false);
  focused='';document.activeElement={};context.closeResult();assert.equal(focused,'');
});
