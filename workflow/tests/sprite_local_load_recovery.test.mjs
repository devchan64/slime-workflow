import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

const source=readFileSync(new URL('../../gui/SpriteSheetEditor.jsx',import.meta.url),'utf8');
test('로컬 시트 읽기는 중복을 막고 시간 초과 후 재시도한다',async()=>{
 const code=source.slice(source.indexOf('  async function load(target=file,focused=false)'),source.indexOf('  return <details className="sprite-local-sheet">'));
 let timer,busy=false,error='',detail=null,calls=0,slow=true;const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,file:{},loadRequest:{current:null},restoreLoadFocus:{current:false},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setError:value=>error=value,setDetail:value=>detail=value,setRevision:()=>{},setPending:()=>{},readLocalSheet:()=>{calls++;return slow?new Promise(()=>{}):Promise.resolve({path:'test.png'});}});
 vm.runInContext(code,context);const first=context.load();await context.load();assert.equal(calls,1);timer();await first;assert.match(error,/시간이 초과/);assert.equal(busy,false);slow=false;await context.load();assert.equal(error,'');assert.equal(detail.path,'test.png');
});
test('로컬 시트 오류는 사라진 초점만 안내로 옮긴다',()=>{
 const effect=source.match(/useEffect\(\(\)=>\{if\(busy \|\| !restoreLoadFocus\.current\).*?\},\[busy,error,revision\]\);/s)?.[0];assert.ok(effect);
 for(const moved of [false,true]){let run,frame,focused=0;const body={},document={body,activeElement:moved?{}:body},target={isConnected:true,focus:()=>focused++};const context=vm.createContext({busy:false,error:'오류',revision:0,restoreLoadFocus:{current:true},loadErrorRef:{current:target},loadButtonRef:{current:null},document,restoreLostFocus,visibleFocusTarget:value=>value,useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});vm.runInContext(effect,context);run();frame();assert.equal(focused,moved?0:1);}
});

test('로컬 시트 확인 중 화면을 닫으면 늦은 파일을 적용하지 않는다',async()=>{
 const code=source.slice(source.indexOf('  async function load(target=file,focused=false)'),source.indexOf('  return <details className="sprite-local-sheet">'));
 let resolve,updates=0;const loadRequest={current:null},context=vm.createContext({AbortController,untilAborted,requestErrorMessage,file:{},loadRequest,restoreLoadFocus:{current:false},setTimeout,clearTimeout,setBusy:()=>updates++,setError:()=>updates++,setDetail:()=>updates++,setRevision:()=>updates++,setPending:()=>updates++,readLocalSheet:()=>new Promise(done=>resolve=done)});
 vm.runInContext(code,context);const waiting=context.load();const before=updates,controller=loadRequest.current;loadRequest.current=null;controller.abort();await waiting;resolve({path:'late.png'});await Promise.resolve();assert.equal(updates,before);
});

test('로컬 시트 읽기에 오류 정보가 없어도 파일 재시도를 안내한다',async()=>{
 const code=source.slice(source.indexOf('  async function load(target=file,focused=false)'),source.indexOf('  return <details className="sprite-local-sheet">'));
 let error='';const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,file:{},loadRequest:{current:null},restoreLoadFocus:{current:false},setTimeout,clearTimeout,setBusy:()=>{},setError:value=>error=value,setDetail:()=>{},setRevision:()=>{},setPending:()=>{},readLocalSheet:async()=>{throw null;}});
 vm.runInContext(code,context);await context.load();assert.match(error,/PNG 시트를 읽을 수 없습니다/);
});
