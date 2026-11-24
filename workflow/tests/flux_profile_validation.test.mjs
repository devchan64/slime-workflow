import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validFluxProfile} from '../../gui/fluxProfileValidation.mjs';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('FLUX 기본 설정 재조회는 렌더 전 중복을 막는다',()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function retryProfile()'),source.indexOf('  usePageTitle('));
 let attempts=0,error='기존 오류';const button={},profilePending={current:false},profileRetryFocus={current:false};
 const context=vm.createContext({document:{activeElement:button},profilePending,profileRetryFocus,profileRetryRef:{current:button},setProfileError:value=>error=value,setAttempt:()=>attempts++});
 vm.runInContext(code,context);context.retryProfile();context.retryProfile();assert.equal(attempts,1);assert.equal(profilePending.current,true);assert.equal(profileRetryFocus.current,true);assert.equal(error,'');
});

test('FLUX 기본 설정은 표시와 입력에 필요한 형식을 확인한다',()=>{
 const base={label:'이미지',prompt:'',width:768,height:768,minimum:0};
 assert.equal(validFluxProfile(base),true);
 for(const change of [{description:{}},{subject:[]},{rolePrompt:{}},{width:0},{minimum:-1},{minimum:4},{guides:[{id:'',label:'가이드'}]},{layouts:[{}]}])
  assert.equal(validFluxProfile({...base,...change}),false);
});

test('FLUX 기본 설정은 시간 초과 후 재조회하고 늦은 응답을 무시한다',async()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    const controller=new AbortController();\n    let active=true,timedOut=false;'),source.indexOf('  async function readJob('));
 const valid={label:'이미지',prompt:'example',width:768,height:768,minimum:0};
 let cleanup,timer,finish,error='',profile=null,attempts=0;
 const context=vm.createContext({AbortController,untilAborted,validFluxProfile,profilePending:{current:true},service:'flux-image',attempt:0,initialInputs:null,useEffect:fn=>cleanup=fn(),setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setProfileError:value=>error=value,setForm:()=>{},setStage:()=>{},setLayout:()=>{},setSubject:()=>{},setProfile:value=>profile=value,fetch:()=>++attempts===1?new Promise(resolve=>finish=resolve):Promise.resolve({ok:true,json:async()=>valid})});
 vm.runInContext(effect,context);timer();await new Promise(done=>setImmediate(done));assert.match(error,/시간이 초과/);
 cleanup();context.attempt=1;vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));assert.equal(error,'');assert.equal(profile,valid);
 finish({ok:true,json:async()=>({...valid,label:'늦은 결과'})});await new Promise(done=>setImmediate(done));assert.equal(profile,valid);cleanup();
});
