import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('빌보드 저장 지연은 중복을 막고 기존 검토와 접수 ID를 보존한다',async()=>{
 const source=readFileSync(new URL('../../gui/BillboardProperties.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function save(){');const code=source.slice(start,source.indexOf('  const hasEdits=',start));
 let timer,busy=false,notice='',calls=0,cleared=0;const button={},saving={current:null},review={id:'request-123',draft:{},result:{token:'token',review_sha256:'hash'}};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:button},saveButton:{current:button},restoreSaveFocus:{current:false},saving,texture:'asset',onSaveUncertain:()=>{},review,setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setNotice:()=>{},setSaveWarning:value=>notice=value,setReview:()=>cleared++,setSource:()=>cleared++,setEdits:()=>cleared++,onDirtyChange:()=>cleared++,managementCommand:()=>{calls++;return new Promise(()=>{});}});
 vm.runInContext(code,context);const first=context.save();await context.save();assert.equal(calls,1);timer();await first;assert.equal(busy,false);assert.equal(saving.current,null);assert.equal(cleared,0);assert.match(notice,/request-123/);assert.match(notice,/원본과 이력/);assert.match(notice,/응답 시간이 초과/);
});

test('빌보드 편집 화면 종료 후 늦은 저장 응답은 상태를 바꾸지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/BillboardProperties.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function save(){');const code=source.slice(start,source.indexOf('  const hasEdits=',start));
 let resolve,changes=0,notice='';const saving={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:null},saveButton:{current:null},restoreSaveFocus:{current:false},saving,texture:'asset',onSaveUncertain:()=>{},review:{id:'request-123',draft:{},result:{token:'token',review_sha256:'hash'}},setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setNotice:()=>{},setSaveWarning:value=>notice=value,setReview:()=>changes++,setSource:()=>changes++,setEdits:()=>changes++,onDirtyChange:()=>changes++,managementCommand:()=>new Promise(done=>resolve=done)});
 vm.runInContext(code,context);const running=context.save();const request=saving.current;saving.current=null;request.abort();resolve({state:'completed',saved:true});await running;assert.equal(changes,0);assert.equal(notice,'');
});
