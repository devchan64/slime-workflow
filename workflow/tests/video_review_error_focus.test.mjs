import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

for(const name of ['I2VPage.jsx','FunControlPage.jsx','MiniMaxH3Page.jsx','AnimateInputs.jsx'])test(`${name} 검토 오류 후 사라진 초점만 복구한다`,()=>{
 const source=readFileSync(new URL(`../../gui/${name}`,import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(busy \|\| pending \|\| !error \|\| !reviewOrigin\.current\).*?\},\[busy,pending,error\]\);/s)?.[0];assert.ok(effect);
 for(const moved of [false,true]){
  let run,frame,focused=0;const body={},button={isConnected:true,focus:()=>focused++},document={body,activeElement:moved?{}:body},reviewOrigin={current:button};
  const context=vm.createContext({busy:false,pending:null,error:'오류',reviewOrigin,document,restoreLostFocus,visibleFocusTarget:value=>value,useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(effect,context);run();frame();assert.equal(focused,moved?0:1);assert.equal(reviewOrigin.current,null);
 }
});
