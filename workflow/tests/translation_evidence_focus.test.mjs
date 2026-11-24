import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('문서 검색이 끝나도 닫힌 패널이나 잠긴 입력으로 초점을 옮기지 않는다',()=>{
 const source=readFileSync(new URL('../../gui/TranslationEvidence.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(!busy && restoreFocus\.current\).*?\},\[busy\]\);/s)?.[0];assert.ok(effect);
 for(const mode of ['open','closed','disabled','moved']){
  const body={},other={};let run,focused=0;
  const context=vm.createContext({busy:false,restoreFocus:{current:true},document:{body,activeElement:mode==='moved'?other:body},detailsRef:{current:{open:mode!=='closed'}},searchButton:{current:{isConnected:true,matches:()=>mode==='disabled',focus:()=>focused++}},useEffect:fn=>run=fn});
  vm.runInContext(effect,context);run();assert.equal(focused,mode==='open'?1:0);assert.equal(context.restoreFocus.current,false);
 }
});
