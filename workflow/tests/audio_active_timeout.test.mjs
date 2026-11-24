import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';
import {validGenerationJobId} from '../../gui/generationJobId.mjs';

test('오디오 진행 작업 조회 지연은 별도 오류로 안내하고 종료 후 상태를 바꾸지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    let active=true,timedOut=false;const controller=new AbortController();let timeout;');
 const end=source.indexOf('  },[activeRevision]);',start)+'  },[activeRevision]);'.length;
 for(const close of [false,true]){
  let run,timer,error='',updates=0;const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validGenerationJobId,URLSearchParams,location:{search:''},embedded:true,activeRevision:0,activePending:{current:false},service:'sfx',useEffect:fn=>run=fn,
   setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setJob:()=>updates++,setActiveId:()=>updates++,setActiveLoading:()=>updates++,setActiveNotice:()=>updates++,setActiveError:value=>{error=value;updates++;},managementCommand:()=>new Promise(()=>{})});
  vm.runInContext(source.slice(start,end),context);const cleanup=run();const before=updates;if(close)cleanup();else timer();await new Promise(resolve=>setImmediate(resolve));
  if(close)assert.equal(updates,before);else assert.match(error,/시간이 초과/);
 }
});

test('오디오 진행 작업 재조회는 기존 선택을 보존하고 결과를 안내한다',async()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    let active=true,timedOut=false;const controller=new AbortController();let timeout;');
 const end=source.indexOf('  },[activeRevision]);',start)+'  },[activeRevision]);'.length;
 for(const id of ['2026-11-24_12-00-00-abcdef12',null]){
  let run,job='selected-job',activeId='',notice='',error='',loading=false;const activePending={current:false};
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validGenerationJobId,URLSearchParams,location:{search:''},embedded:true,activeRevision:1,activePending,service:'sfx',useEffect:fn=>run=fn,
   setTimeout:()=>1,clearTimeout:()=>{},setJob:fn=>job=fn(job),setActiveId:value=>activeId=value,setActiveLoading:value=>loading=value,setActiveNotice:value=>notice=value,setActiveError:value=>error=value,managementCommand:async()=>({id})});
  vm.runInContext(source.slice(start,end),context);const cleanup=run();await new Promise(resolve=>setImmediate(resolve));
  assert.equal(job,'selected-job');assert.equal(activeId,id || '');assert.equal(error,'');assert.equal(loading,false);assert.equal(activePending.current,false);assert.match(notice,id ? /확인했습니다/ : /없습니다/);cleanup();
 }
});

test('오디오 진행 작업 재조회 후 사라진 초점만 결과나 재시도 버튼으로 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(activeLoading \|\| !activeRetryFocus\.current\).*?\},\[activeLoading,activeError\]\);/s)?.[0];assert.ok(effect);
 for(const error of ['', '실패'])for(const moved of [false,true]){
  let run,focused='';const body={},other={},document={body,activeElement:moved?other:body};
  const target=name=>({isConnected:true,focus:()=>focused=name});
  const context=vm.createContext({document,restoreLostFocus,activeLoading:false,activeError:error,activeRetryFocus:{current:true},activeRetryRef:{current:target('retry')},activeErrorRef:{current:target('status')},useEffect:fn=>run=fn});
  vm.runInContext(effect,context);run();assert.equal(focused,moved?'':error?'retry':'status');
 }
});

test('오디오 진행 작업의 손상된 ID는 유휴 또는 정상 결과로 표시하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    let active=true,timedOut=false;const controller=new AbortController();let timeout;');
 const end=source.indexOf('  },[activeRevision]);',start)+'  },[activeRevision]);'.length;
 for(const response of [{},{id:''},{id:'../invalid'},{id:3}]){
  let run,error='',notice='',job='selected';
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validGenerationJobId,URLSearchParams,location:{search:''},embedded:true,activeRevision:1,activePending:{current:false},service:'sfx',useEffect:fn=>run=fn,
   setTimeout:()=>1,clearTimeout:()=>{},setJob:fn=>job=fn(job),setActiveId:()=>{},setActiveLoading:()=>{},setActiveNotice:value=>notice=value,setActiveError:value=>error=value,managementCommand:async()=>response});
  vm.runInContext(source.slice(start,end),context);const cleanup=run();await new Promise(resolve=>setImmediate(resolve));
  assert.match(error,/응답을 확인/);assert.equal(notice,'');assert.equal(job,'selected');cleanup();
 }
});

test('오디오 진행 결과 열기 후 사라진 초점만 상태 영역으로 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(!activeOpenFocus\.current\).*?\},\[job\]\);/s)?.[0];assert.ok(effect);
 for(const moved of [false,true]){
  let run,focused=0;const body={},other={},document={body,activeElement:moved?other:body};
  const context=vm.createContext({document,restoreLostFocus,job:'id',activeOpenFocus:{current:true},activeErrorRef:{current:{isConnected:true,focus:()=>focused++}},useEffect:fn=>run=fn});
  vm.runInContext(effect,context);run();assert.equal(focused,moved?0:1);assert.equal(context.activeOpenFocus.current,false);
 }
});
