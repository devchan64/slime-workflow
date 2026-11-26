import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('GPU 양도 조회와 변경 실패를 구분해 안전한 안내를 표시한다',async()=>{
 const source=readFileSync(new URL('../../gui/GpuHandoffStatus.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function perform('),end=source.indexOf('  const summary=',start);assert.ok(start>=0&&end>start);
 for(const mutation of [false,true]){
  let error='',uncertain=false,busy=false;const context=vm.createContext({AbortController,setTimeout,clearTimeout,requestErrorMessage,actionPending:{current:false},statusRequest:{current:null},scope:'x',currentScope:{current:'x'},uncertain:false,session:'s',id:'i',service:'test',uncertaintyKey:'k',handoffSessionStorage:()=>null,markHandoffUncertainty:()=>true,executeGpuHandoffCommand:async()=>{throw new TypeError('Failed to fetch');},managementCommand:()=>{},setBusy:value=>busy=value,setError:value=>error=value,setUncertain:value=>uncertain=value});
  vm.runInContext(source.slice(start,end),context);await context.perform('command',{},mutation);
  assert.match(error,mutation?/다시 변경하기 전에 GPU 양도 상태를 확인/:/연결 상태를 확인/);assert.equal(uncertain,mutation);assert.equal(busy,false);
 }
});

test('GPU 양도 조회 중 화면 종료 후 늦은 응답은 화면을 갱신하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/GpuHandoffStatus.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function perform('),end=source.indexOf('  const summary=',start);let reject,updates=0;
 const statusRequest={current:null},context=vm.createContext({AbortController,setTimeout,clearTimeout,requestErrorMessage,actionPending:{current:false},statusRequest,scope:'x',currentScope:{current:'x'},uncertain:false,session:'s',id:'i',service:'test',uncertaintyKey:'k',handoffSessionStorage:()=>null,executeGpuHandoffCommand:()=>new Promise((_,fail)=>reject=fail),managementCommand:()=>{},setBusy:()=>updates++,setError:()=>updates++,setUncertain:()=>updates++,onUpdate:()=>updates++});
 vm.runInContext(source.slice(start,end),context);const task=context.perform('command',{},false);const controller=statusRequest.current;statusRequest.current=null;controller.abort();const before=updates;reject(new DOMException('중단','AbortError'));await task;assert.equal(updates,before);
});
