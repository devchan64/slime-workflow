import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

const source=readFileSync(new URL('../../gui/RecordFolder.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('  async function request('),source.indexOf('  async function copy()'));
test('폴더 자동 조회는 다른 버튼의 초점을 복구 대상으로 삼지 않는다',async()=>{
 for(const manual of [false,true]){
  const body={},button={isConnected:true,disabled:false};let frame,focused=0;
  button.focus=()=>focused++;const document={body,activeElement:button};
  const context=vm.createContext({AbortController,untilAborted,document,pending:{current:null},copySequence:{current:0},service:'service',id:'job',path:'',setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setNoticeError:()=>{},setNotice:()=>{},setPath:()=>{},setStale:()=>{},requestAnimationFrame:fn=>frame=fn,fetch:async()=>({ok:true,json:async()=>({path:'/tmp/job'})})});
  vm.runInContext(code,context);await context.request('inspect',manual?button:null);document.activeElement=body;if(frame)frame();assert.equal(focused,manual?1:0);
 }
});
test('폴더 조회 시간 초과 직후 화면을 닫으면 늦은 알림과 초점을 표시하지 않는다',async()=>{
 let timer,notice=0,busy=0;const pending={current:null};
 const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},pending,copySequence:{current:0},service:'service',id:'job',path:'',setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:()=>busy++,setNoticeError:()=>{},setNotice:()=>notice++,setPath:()=>{},setStale:()=>{},requestAnimationFrame:()=>{},fetch:()=>new Promise(()=>{})});
 vm.runInContext(code,context);const waiting=context.request('inspect');timer();pending.current=null;await waiting;assert.equal(notice,1);assert.equal(busy,1);
});
test('폴더 조회 실패는 오류 상태로 알리고 정상 재조회는 해제한다',async()=>{
 let isError=false,notice='',ok=false;
 const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},pending:{current:null},copySequence:{current:0},service:'service',id:'job',path:'/old',setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setNoticeError:value=>isError=value,setNotice:value=>notice=value,setPath:()=>{},setStale:()=>{},requestErrorMessage:e=>e.message,requestAnimationFrame:()=>{},fetch:async()=>({ok,json:async()=>ok?{path:'/new'}:{error:'조회 실패'}})});
 vm.runInContext(code,context);await context.request('inspect');assert.equal(isError,true);assert.match(notice,/조회 실패/);
 ok=true;await context.request('inspect');assert.equal(isError,false);assert.equal(notice,'');
});
test('잘못된 폴더 응답은 재확인을 안내하고 이전 경로를 유지한다',async()=>{
 let notice='',stale=false,changed=false;
 const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},pending:{current:null},copySequence:{current:0},service:'service',id:'job',path:'/old',setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setNoticeError:()=>{},setNotice:value=>notice=value,setPath:()=>changed=true,setStale:value=>stale=value,requestErrorMessage:e=>e.message,requestAnimationFrame:()=>{},fetch:async()=>({ok:true,json:async()=>{throw new SyntaxError('Unexpected token');}})});
 vm.runInContext(code,context);await context.request('inspect');assert.match(notice,/폴더 응답을 확인할 수 없습니다/);assert.equal(stale,true);assert.equal(changed,false);
});
test('경로 복사 실패는 수동 선택을 안내하고 성공 시 오류 상태를 해제한다',async()=>{
 const copy=source.slice(source.indexOf('  async function copy()'),source.indexOf('  const openButton='));
 for(const fail of [true,false]){
  let error=!fail,notice='',focus=0,select=0;const body={},button={};
  const context=vm.createContext({copySequence:{current:0},path:'/tmp/job',document:{body,activeElement:button},copyButton:{current:button},pathInput:{current:{focus:()=>focus++,select:()=>select++}},writeClipboardText:async()=>{if(fail)throw Error('failed');},setNoticeError:value=>error=value,setNotice:value=>notice=value});
  vm.runInContext(copy,context);await context.copy();assert.equal(error,fail);
  assert.match(notice,fail?/복사 단축키/:/복사했습니다/);assert.equal(focus,fail?1:0);assert.equal(select,fail?1:0);
 }
});
