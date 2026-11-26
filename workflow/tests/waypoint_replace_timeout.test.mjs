import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('교체 응답 지연 시 중복을 막고 접수 확인을 안내한다',async()=>{
 const source=readFileSync(new URL('../../gui/EffectEditor.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function confirm(){',source.indexOf('export function WaypointReplacement'));
 const code=source.slice(start,source.indexOf('  return <details ref={details}',start));
 let timer,busy=false,error='',calls=0,saved=0,uncertain;const button={},submitting={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:button},confirmButton:{current:button},restoreFocus:{current:false},submitting,pending:{requestId:'request-123',draft:{effect:{id:'effect'}},result:{review_sha256:'hash'}},busy:false,setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setError:value=>error=value,setBusy:value=>busy=value,onUncertain:(id,requestId)=>uncertain=[id,requestId],onSaved:()=>saved++,managementCommand:()=>{calls++;return new Promise(()=>{});}});
 vm.runInContext(code,context);const first=context.confirm();await context.confirm();assert.equal(calls,1);timer();await first;assert.equal(busy,false);assert.equal(submitting.current,null);assert.equal(saved,0);assert.deepEqual(uncertain,['effect','request-123']);assert.match(error,/원본과 접수 기록을 확인/);assert.match(error,/request-123/);assert.match(error,/응답 시간이 초과/);
});

test('교체 화면 종료 후 늦은 응답은 결과를 적용하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/EffectEditor.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function confirm(){',source.indexOf('export function WaypointReplacement'));
 const code=source.slice(start,source.indexOf('  return <details ref={details}',start));
 let resolve,saved=0,errors=0;const submitting={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:null},confirmButton:{current:null},restoreFocus:{current:false},submitting,pending:{requestId:'request-123',draft:{effect:{id:'effect'}},result:{review_sha256:'hash'}},busy:false,setTimeout:()=>1,clearTimeout:()=>{},setError:value=>{if(value)errors++},setBusy:()=>{},onSaved:()=>saved++,managementCommand:()=>new Promise(done=>resolve=done)});
 vm.runInContext(code,context);const running=context.confirm();const request=submitting.current;submitting.current=null;request.abort();resolve({state:'completed',id:'effect'});await running;assert.equal(saved,0);assert.equal(errors,0);
});
