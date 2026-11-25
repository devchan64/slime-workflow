import {test} from 'node:test';
import assert from 'node:assert/strict';
import {managementCommand} from '../../gui/managementCommand.js';

test('작가 요청은 세션 토큰을 조회해 전달하고 토큰이 없으면 실행하지 않는다',async()=>{
 const previous=globalThis.fetch, calls=[];
 try {
  globalThis.fetch=async (_url,options)=>{calls.push({command:JSON.parse(options.body).command,token:options.headers['X-Writer-Token']});return {ok:true,json:async()=>calls.length===1?{csrf_token:'session-token'}:{jobs:[],count:0}};};
  assert.deepEqual(await managementCommand('writer-agent','writer-history',{query:''}),{jobs:[],count:0});
  assert.deepEqual(calls,[{command:'writer-token',token:undefined},{command:'writer-history',token:'session-token'}]);
  calls.length=0;
  globalThis.fetch=async (_url,options)=>{calls.push(JSON.parse(options.body).command);return {ok:true,json:async()=>({})};};
  await assert.rejects(managementCommand('writer-agent','writer-history',{query:''}),/작가 세션/);
  assert.deepEqual(calls,['writer-token']);
  calls.length=0;
  globalThis.fetch=async (_url,options)=>{calls.push(JSON.parse(options.body).command);return {ok:false,json:async()=>{throw new SyntaxError('Unexpected token');}};};
  await assert.rejects(managementCommand('writer-agent','writer-history',{query:''}),/작가 세션/);
  assert.deepEqual(calls,['writer-token']);
 } finally {globalThis.fetch=previous;}
});

test('다른 서비스와 작가 상태 조회는 토큰 요청을 추가하지 않고 중단 신호를 전달한다',async()=>{
 const previous=globalThis.fetch, calls=[], controller=new AbortController();
 try {
  globalThis.fetch=async (_url,options)=>{calls.push({body:JSON.parse(options.body),signal:options.signal,token:options.headers['X-Writer-Token']});return {ok:true,json:async()=>({ready:true})};};
  await managementCommand('writer-agent','writer-state',{}, {signal:controller.signal});
  await managementCommand('prompt-translation','translation-status',{id:'job'}, {signal:controller.signal});
  assert.deepEqual(calls.map(call=>call.body.command),['writer-state','translation-status']);
  assert.ok(calls.every(call=>call.signal===controller.signal && call.token===undefined));
 } finally {globalThis.fetch=previous;}
});

test('토큰 조회가 중단 뒤 늦게 끝나도 작가 명령을 보내지 않는다',async()=>{
 const previous=globalThis.fetch, calls=[], controller=new AbortController();
 let release;
 try {
  globalThis.fetch=async (_url,options)=>{calls.push(JSON.parse(options.body).command);return {ok:true,json:()=>new Promise(resolve=>{release=resolve;})};};
  const request=managementCommand('writer-agent','writer-history',{query:''},{signal:controller.signal});
  await new Promise(resolve=>setImmediate(resolve));
  controller.abort();release({csrf_token:'late-token'});
  await assert.rejects(request,error=>error.name==='AbortError');
  assert.deepEqual(calls,['writer-token']);
 } finally {globalThis.fetch=previous;}
});

test('토큰 조회의 연결 실패와 응답 처리 중단을 각각 보존한다',async()=>{
 const previous=globalThis.fetch, calls=[], controller=new AbortController();
 try {
  globalThis.fetch=async (_url,options)=>{calls.push(JSON.parse(options.body).command);throw new TypeError('Failed to fetch');};
  await assert.rejects(managementCommand('writer-agent','writer-history',{}),error=>error instanceof TypeError && error.message==='Failed to fetch');
  globalThis.fetch=async (_url,options)=>{calls.push(JSON.parse(options.body).command);return {ok:true,json:async()=>{controller.abort();throw new SyntaxError('interrupted');}};};
  await assert.rejects(managementCommand('writer-agent','writer-history',{}, {signal:controller.signal}),error=>error.name==='AbortError');
  assert.deepEqual(calls,['writer-token','writer-token']);
 } finally {globalThis.fetch=previous;}
});
