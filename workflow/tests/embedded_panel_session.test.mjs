import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('세션 전환 시 열린 특수 생성 폼은 유지하고 이전 제안 입력은 지운다',()=>{
 const source=readFileSync(new URL('../../gui/app.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{setGeneratorPanel\(null\);setMountedGenerators\(\[\]\);.*?\},\[session\]\);/s)?.[0];assert.ok(effect);
 for(const [kimodo,fun] of [[true,false],[false,true],[false,false]]){
  let run;const values={},formInputSession={current:'old'};const context=vm.createContext({session:'new',formInputSession,showKimodo:kimodo,showFunControl:fun,useEffect:fn=>run=fn,setGeneratorPanel:v=>values.panel=v,setMountedGenerators:v=>values.generators=v,setFluxForms:v=>values.flux=v,setKimodoProposal:v=>values.proposal=v,setVideoFormId:v=>values.video=v,setSeedProposal:v=>values.seed=v,setKimodoMounted:v=>values.kimodo=v,setFunMounted:v=>values.fun=v});
  vm.runInContext(effect,context);run();assert.equal(values.panel,null);assert.equal(values.generators.length,0);assert.equal(values.flux.length,0);assert.equal(values.proposal,null);assert.equal(values.video,'');assert.equal(values.seed,null);assert.equal(values.kimodo,kimodo);assert.equal(values.fun,fun);assert.equal(formInputSession.current,'new');
 }
});
