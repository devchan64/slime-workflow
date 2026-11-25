import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {restoreLostFocus,visibleFocusTarget} from '../../gui/restoreLostFocus.mjs';

test('오디오 대화 제안 조회가 지연되면 기본 입력으로 복구한다',async()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    const controller=new AbortController();');
 const end=source.indexOf('  },[inputRevision]);',start)+'  },[inputRevision]);'.length;
 let run,timer,resolveProposal,proposalSignal,form=null,notice='',error='';const defaults={prompt:'p',seed:1,loop_request:false,tag:'',lyrics:'l',duration_seconds:30},inputPending={current:true};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,formPath:'/input',music:true,embedded:false,query:new URLSearchParams('proposal_job=j&proposal_offset=0'),session:'s',service:'music',inputRevision:0,inputPending,
  useEffect:fn=>run=fn,setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setInputError:value=>error=value,setForm:fn=>form=fn(form),setNotice:value=>notice=value,
  fetch:async()=>({ok:true,json:async()=>defaults}),readGenerationProposal:(_command,_scope,{signal})=>(proposalSignal=signal,new Promise(resolve=>resolveProposal=resolve)),managementCommand:()=>{},audioProposalInputs:()=>({prompt:'late'})});
 vm.runInContext(source.slice(start,end),context);const cleanup=run();await new Promise(resolve=>setImmediate(resolve));timer();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(proposalSignal.aborted,true);assert.equal(form,defaults);assert.match(notice,/기본 입력/);assert.equal(error,'');assert.equal(inputPending.current,false);
 resolveProposal({});await new Promise(resolve=>setImmediate(resolve));assert.equal(form,defaults);assert.match(notice,/기본 입력/);cleanup();
});

test('오디오 기본 입력 조회 중 화면 종료 후에는 상태를 변경하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    const controller=new AbortController();');
 const end=source.indexOf('  },[inputRevision]);',start)+'  },[inputRevision]);'.length;
 let run,resolveFetch,updates=0;const fetchResult=new Promise(resolve=>resolveFetch=resolve);
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,formPath:'/input',music:false,embedded:true,query:new URLSearchParams(),inputRevision:0,inputPending:{current:true},
  useEffect:fn=>run=fn,setTimeout:()=>1,clearTimeout:()=>{},setInputError:()=>updates++,setForm:()=>updates++,setNotice:()=>updates++,fetch:()=>fetchResult});
 vm.runInContext(source.slice(start,end),context);const cleanup=run();cleanup();const before=updates;
 resolveFetch({ok:true,json:async()=>({prompt:'p',seed:1,loop_request:false,tag:''})});await new Promise(resolve=>setImmediate(resolve));assert.equal(updates,before);
});

test('오디오 기본 입력 재시도는 중복을 막고 잃은 초점만 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const start=source.indexOf('onClick={()=>{if(inputPending.current)return;');
 const end=source.indexOf('}}>기본 입력 다시 불러오기',start);
 const handler=source.slice(start+'onClick={'.length,end+1);
 const effect=source.match(/useEffect\(\(\)=>\{\s*if\(!inputRetryFocus\.current.*?\},\[form,inputError\]\);/s)?.[0];
 assert.ok(start>=0 && end>start && effect);
 for(const [moved,folded] of [[false,false],[true,false],[false,true]]){
  let run,frame,count=0,focused=0,summaryFocused=0,cancelled=0;const body={},button={},other={},document={body,activeElement:button};
  const summary={isConnected:true,focus:()=>summaryFocused++},details={tagName:'DETAILS',open:!folded,querySelector:()=>summary,parentElement:null};
  const context=vm.createContext({document,restoreLostFocus,visibleFocusTarget,inputPending:{current:false},inputRetryFocus:{current:false},inputRetryRef:{current:button},promptRef:{current:{isConnected:true,parentElement:details,focus:()=>focused++}},form:{},inputError:'',
   setInputError:()=>{},retryInput:()=>count++,useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>cancelled++});
  vm.runInContext('globalThis.retry='+handler+';'+effect,context);context.retry();context.retry();const cleanup=run();document.activeElement=moved?other:body;frame();cleanup();
  assert.equal(count,1);assert.equal(focused,moved || folded?0:1);assert.equal(summaryFocused,!moved && folded?1:0);assert.equal(cancelled,1);
 }
});
