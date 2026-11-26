import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {effectSaveFailure} from '../../gui/effectSaveResponse.mjs';

test('정렬 저장 지연 시 중복을 막고 요청 ID와 결과 확인을 안내한다',async()=>{
 const source=readFileSync(new URL('../../gui/EffectEditor.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function save(event){',source.indexOf('export function Alignment('));
 const code=source.slice(start,source.indexOf('  const alphaInvalid=',start));
 let timer,busy=false,message='',isError=false,calls=0,saved=0,uncertain;const button={},submitting={current:null};
 const context=vm.createContext({AbortController,untilAborted,effectSaveFailure,Error,document:{activeElement:button},saveButton:{current:button},restoreSaveFocus:{current:false},restoreInputFocus:{current:false},submitting,values:{target:[0,0,1,1],frames:[],alpha:1},effectAlignmentBoundsIssue:()=>null,detail:{document:{id:'effect'}},revision:'revision',crypto:{randomUUID:()=> 'request-123'},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setMessage:value=>message=value,setSaveError:value=>isError=value,setInputError:()=>{},onUncertain:(id,requestId)=>uncertain=[id,requestId],setRevision:()=>saved++,setValues:()=>saved++,setSavedValues:()=>saved++,managementCommand:()=>{calls++;return new Promise(()=>{});}});
 vm.runInContext(code,context);const event={preventDefault(){}};const first=context.save(event);await context.save(event);assert.equal(calls,1);timer();await first;assert.equal(busy,false);assert.equal(isError,true);assert.equal(saved,0);assert.deepEqual(uncertain,['effect','request-123']);assert.equal(submitting.current,null);assert.match(message,/원본과 이력을 확인/);assert.match(message,/request-123/);assert.match(message,/응답 시간이 초과/);
});

test('정렬 편집 화면 종료 후 늦은 저장 응답은 상태를 변경하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/EffectEditor.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function save(event){',source.indexOf('export function Alignment('));
 const code=source.slice(start,source.indexOf('  const alphaInvalid=',start));
 let resolve,mutations=0,errors=0;const submitting={current:null};
 const context=vm.createContext({AbortController,untilAborted,effectSaveFailure,Error,document:{activeElement:null},saveButton:{current:null},restoreSaveFocus:{current:false},restoreInputFocus:{current:false},submitting,values:{target:[0,0,1,1],frames:[],alpha:1},effectAlignmentBoundsIssue:()=>null,detail:{document:{id:'effect'}},revision:'revision',crypto:{randomUUID:()=> 'request-123'},setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setMessage:value=>{if(value)errors++},setSaveError:value=>{if(value)errors++},setInputError:()=>{},setRevision:()=>mutations++,setValues:()=>mutations++,setSavedValues:()=>mutations++,managementCommand:()=>new Promise(done=>resolve=done)});
 vm.runInContext(code,context);const running=context.save({preventDefault(){}});const request=submitting.current;submitting.current=null;request.abort();resolve({saved:true,revision:'a'.repeat(64),generation:1});await running;assert.equal(mutations,0);assert.equal(errors,0);
});
