import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

function setup(digest,command){
 const source=readFileSync(new URL('../../gui/BuildingEditor.jsx',import.meta.url),'utf8');
 const start=source.indexOf('export async function buildingCommand(');
 const code=source.slice(start,source.indexOf('\nexport function BuildingRegistration',start)).replace('export async function','async function');
 let timer,dispatched=0,signal;
 const context=vm.createContext({TextEncoder,Uint8Array,AbortController,DOMException,untilAborted,crypto:{subtle:{digest}},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},managementCommand:(service,action,payload,options)=>{signal=options.signal;return command(service,action,payload,options);}});
 vm.runInContext(code,context);
 return {run:()=>context.buildingCommand('register',{texture:'town-test-v1'},{onDispatch:()=>dispatched++}),timeout:()=>timer(),get dispatched(){return dispatched},get signal(){return signal}};
}

test('요청 응답 지연은 중단되고 발송 후 불확실한 결과로 보고된다',async()=>{
 const s=setup(async()=>new Uint8Array([1]).buffer,()=>new Promise(()=>{}));
 const result=s.run();await new Promise(resolve=>setImmediate(resolve));assert.equal(s.dispatched,1);s.timeout();await assert.rejects(result,/요청 응답 시간이 초과/);assert.equal(s.signal.aborted,true);
});

test('요청 준비 지연은 발송하지 않고 중단된다',async()=>{
 const s=setup(()=>new Promise(()=>{}),()=>{throw Error('unexpected dispatch')});
 const result=s.run();s.timeout();await assert.rejects(result,/요청 준비 시간이 초과/);assert.equal(s.dispatched,0);
});
