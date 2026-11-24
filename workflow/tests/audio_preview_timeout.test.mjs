import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('오디오 검토는 중복을 막고 지연 응답 시간 초과 뒤 재시도할 수 있다',async()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function preview(event)'),source.indexOf('  async function submit()'));
 let timer,fail=true,requests=0,notice='',noticeError=false,busy=false,review=null;const form={prompt:'p',lyrics:'l',seed:1,duration_seconds:30},reviewRequest={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,reviewRequest,interactionRef:{current:{busy:false,review:null}},formRef:{current:form},form,music:false,tagCount:1,service:'sfx',formPath:'/input',reviewEpoch:{current:0},reviewOrigin:{current:null},document:{activeElement:null},
  setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setNotice:(value,error=false)=>{notice=value;noticeError=error;},setReview:value=>review=value,confirmation:{current:{open:()=>({})}},handoff:{preview:async()=>{},clearReview:()=>{}},
  fetch:()=>{requests++;return fail ? new Promise(()=>{}) : Promise.resolve({ok:true,json:async()=>({final_prompt:'p'})});}});
 vm.runInContext(code,context);const event={preventDefault(){}};const first=context.preview(event);await context.preview(event);assert.equal(requests,1);timer();await first;
 assert.match(notice,/시간이 초과/);assert.equal(noticeError,true);assert.equal(busy,false);assert.equal(reviewRequest.current,null);
 fail=false;await context.preview(event);assert.equal(notice,'');assert.equal(noticeError,false);assert.equal(busy,false);assert.equal(review.prompt,'p');
});

test('음악 검토의 모델 상태·본문·양도 조회가 지연돼도 시간 초과된다',async()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function preview(event)'),source.indexOf('  async function submit()'));
 for(const stage of ['model','body','handoff']){
  let timer,notice='',busy=false,review=null,cleared=0;const form={prompt:'p',lyrics:'l',seed:1,duration_seconds:30},reviewRequest={current:null};
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,reviewRequest,interactionRef:{current:{busy:false,review:null}},formRef:{current:form},form,music:true,tagCount:1,service:'music',formPath:'/input',reviewEpoch:{current:0},reviewOrigin:{current:null},document:{activeElement:null},generationReady:()=>true,
   setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setNotice:value=>notice=value,setReview:value=>review=value,confirmation:{current:{open:()=>({})}},
   managementCommand:()=>stage==='model'?new Promise(()=>{}):Promise.resolve({ready:true}),fetch:async()=>({ok:true,json:()=>stage==='body'?new Promise(()=>{}):Promise.resolve({final_prompt:'p'})}),
   handoff:{preview:()=>stage==='handoff'?new Promise(()=>{}):Promise.resolve(),clearReview:()=>cleared++}});
  vm.runInContext(code,context);const pending=context.preview({preventDefault(){}});await new Promise(resolve=>setImmediate(resolve));timer();await pending;
  assert.match(notice,/시간이 초과/,stage);assert.equal(busy,false,stage);assert.equal(review,null,stage);assert.equal(cleared,1,stage);
 }
});

test('오디오 검토 중 입력 변경 또는 화면 종료 후 이전 결과를 표시하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function preview(event)'),source.indexOf('  async function submit()'));
 for(const scenario of ['edit','close']){
  let resolveFetch,notice='',review=null,updates=0;const form={prompt:'p',lyrics:'l',seed:1},formRef={current:form},reviewRequest={current:null};
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,reviewRequest,interactionRef:{current:{busy:false,review:null}},formRef,form,music:false,tagCount:1,service:'sfx',formPath:'/input',reviewEpoch:{current:0},reviewOrigin:{current:null},document:{activeElement:null},
   setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>updates++,setNotice:value=>{notice=value;updates++;},setReview:value=>{review=value;updates++;},confirmation:{current:{open:()=>({})}},handoff:{preview:async()=>{},clearReview:()=>{}},
   fetch:()=>new Promise(resolve=>resolveFetch=resolve)});
  vm.runInContext(code,context);const pending=context.preview({preventDefault(){}});
  if(scenario==='edit')formRef.current={...form,prompt:'changed'};else{const controller=reviewRequest.current;reviewRequest.current=null;controller.abort();}
  const before=updates;resolveFetch({ok:true,json:async()=>({final_prompt:'p'})});await pending;
  assert.equal(review,null,scenario);if(scenario==='edit')assert.match(notice,/입력이 변경/);else assert.equal(updates,before);
 }
});

test('오디오 검토의 최종 프롬프트가 손상되면 양도 조회나 확인을 열지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function preview(event)'),source.indexOf('  async function submit()'));
 for(const result of [null,{}, {final_prompt:'  '}, {final_prompt:42}]){
  let notice='',review=null,handoffCalls=0;const form={prompt:'p',seed:1};
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,reviewRequest:{current:null},interactionRef:{current:{busy:false,review:null}},formRef:{current:form},form,music:false,tagCount:1,service:'sfx',formPath:'/input',reviewEpoch:{current:0},reviewOrigin:{current:null},document:{activeElement:null},
   setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setNotice:value=>notice=value,setReview:value=>review=value,confirmation:{current:{open:()=>({})}},handoff:{preview:async()=>handoffCalls++,clearReview:()=>{}},fetch:async()=>({ok:true,json:async()=>result})});
  vm.runInContext(code,context);await context.preview({preventDefault(){}});
  assert.match(notice,/최종 프롬프트/);assert.equal(review,null);assert.equal(handoffCalls,0);
 }
});

test('음악 모델 상태가 불리언이 아니면 생성·준비 검토를 열지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function preview(event)'),source.indexOf('  async function submit()'));
 for(const kind of ['generate','prepare']){
  let notice='',review=null,requests=0;const form={prompt:'p',lyrics:'l',seed:1,duration_seconds:30};
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,reviewRequest:{current:null},interactionRef:{current:{busy:false,review:null}},formRef:{current:form},form,music:true,tagCount:1,service:'music',formPath:'/input',reviewEpoch:{current:0},reviewOrigin:{current:null},document:{activeElement:null},generationReady:()=>true,
   setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setNotice:value=>notice=value,setReview:value=>review=value,confirmation:{current:{open:()=>({})}},handoff:{preview:async()=>{},clearReview:()=>{}},
   managementCommand:async()=>({ready:'yes',artifacts_ready:'yes'}),fetch:async()=>{requests++;return {ok:true,json:async()=>({final_prompt:'p'})};}});
  vm.runInContext(code,context);if(kind==='generate')await context.preview({preventDefault(){}});else await context.reviewPreparation();
  assert.match(notice,/상태를 확인할 수 없습니다/);assert.equal(review,null);assert.equal(requests,0);
 }
});

test('음악 준비 검토는 미준비 응답을 안내하고 지연 후 재시도할 수 있다',async()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function preview(event)'),source.indexOf('  async function submit()'));
 let timer,mode='missing',notice='',review=null,busy=false;const reviewRequest={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,reviewRequest,interactionRef:{current:{busy:false,review:null}},music:true,service:'music',reviewEpoch:{current:0},reviewOrigin:{current:null},document:{activeElement:null},
  setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setNotice:value=>notice=value,setReview:value=>review=value,confirmation:{current:{open:()=>({})}},
  managementCommand:()=>mode==='timeout'?new Promise(()=>{}):Promise.resolve(mode==='missing'?{ready:false}:{ready:false,artifacts_ready:true})});
 vm.runInContext(code,context);await context.reviewPreparation();assert.match(notice,/다운로드/);assert.equal(review,null);
 mode='timeout';const pending=context.reviewPreparation();timer();await pending;assert.match(notice,/시간이 초과/);assert.equal(busy,false);
 mode='ready';await context.reviewPreparation();assert.equal(notice,'');assert.equal(review.payload.action,'prepare');assert.equal(busy,false);
});
