import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('작업 일정 새로고침은 이전 목록 요청을 중단하고 최신 응답만 적용한다',async()=>{
 const source=readFileSync(new URL('../../gui/app.jsx',import.meta.url),'utf8');
 const section=source.slice(source.indexOf('  const [workflow,setWorkflow]'),source.indexOf('  const steps=',source.indexOf('  const [workflow,setWorkflow]')));
 const effect=section.slice(section.indexOf('  useEffect('));
 assert.ok(effect.includes('[session,revision]'));
 let cleanup,workflow=null,error='',calls=[];
 const context=vm.createContext({AbortController,session:'session',revision:0,
  useEffect:fn=>{cleanup=fn();},setTimeout:()=>1,clearTimeout:()=>{},setWorkflow:value=>workflow=value,setWorkflowError:value=>error=value,
  validSessionQueueResult:value=>Array.isArray(value.steps),requestErrorMessage:problem=>problem.message,
  callUntilAborted:(_name,_payload,signal)=>{let resolve;const promise=new Promise(done=>resolve=done);calls.push({resolve,signal});return untilAborted(promise,signal);}});
 vm.runInContext(effect,context);assert.equal(calls.length,1);
 cleanup();assert.equal(calls[0].signal.aborted,true);context.revision=1;vm.runInContext(effect,context);assert.equal(calls.length,2);
 const latest={steps:[{id:'latest'}]};calls[1].resolve(latest);await new Promise(done=>setImmediate(done));
 calls[0].resolve({steps:[{id:'old'}]});await new Promise(done=>setImmediate(done));
 assert.equal(workflow,latest);assert.equal(error,'');cleanup();
});
