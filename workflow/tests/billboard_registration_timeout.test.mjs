import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('신규 등록 지연은 중복을 막고 접수 ID와 결과 확인을 안내한다',async()=>{
 const source=readFileSync(new URL('../../gui/BillboardRegistration.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function save(){');const code=source.slice(start,source.indexOf('  return <details',start));
 let timer,busy=false,message='',isError=false,calls=0,saved=0,cleared=0;const button={},saving={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:button},saveButton:{current:button},restoreFocus:{current:false},saving,review:{requestId:'request-123'},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setMessage:value=>message=value,setMessageError:value=>isError=value,setReview:()=>cleared++,onSaved:()=>saved++,managementCommand:()=>{calls++;return new Promise(()=>{});}});
 vm.runInContext(code,context);const first=context.save();await context.save();assert.equal(calls,1);timer();await first;assert.equal(busy,false);assert.equal(isError,true);assert.equal(saving.current,null);assert.equal(saved,0);assert.equal(cleared,1);assert.match(message,/request-123/);assert.match(message,/목록과 접수 기록/);assert.match(message,/응답 시간이 초과/);
});
