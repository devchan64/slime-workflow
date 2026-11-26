import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('영상 저장 입력 조회는 화면 종료 신호로 요청 및 응답 본문 대기를 중단한다',async()=>{
 for(const file of ['I2VPage.jsx','MiniMaxH3Page.jsx','MiniMaxH3Ref2VAPage.jsx'])for(const stage of ['request','body']){
  const source=readFileSync(new URL('../../gui/'+file,import.meta.url),'utf8');const code=source.slice(source.indexOf('  async function readSavedInput('),source.indexOf('  function restoreSavedInput('));let requestSignal;
  const delayed=new Promise(()=>{}),response=stage==='request'?delayed:Promise.resolve({ok:true,json:()=>delayed});
  const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},currentInput:{current:{busy:false,pending:null}},current:{current:{busy:false,pending:null,checking:false}},imageChecking:{current:false},imageSelectionRevision:{current:0},imageVersion:{current:0},reviewRequest:{current:null},editVersion:{current:0},fetch:(_url,options)=>(requestSignal=options.signal,response),encodeURIComponent,setTimeout,clearTimeout});
  vm.runInContext(code,context);const controller=new AbortController(),pending=file==='MiniMaxH3Ref2VAPage.jsx'?context.readSavedInput('id',{signal:controller.signal}):context.readSavedInput('id',true,{signal:controller.signal});await new Promise(resolve=>setImmediate(resolve));controller.abort();await assert.rejects(pending,error=>error.name==='AbortError',file+' '+stage);assert.equal(requestSignal.aborted,true,file+' '+stage);
 }
});

test('영상 저장 입력의 잘못된 JSON은 형식 확인 안내로 바꾼다',async()=>{
 for(const file of ['I2VPage.jsx','MiniMaxH3Page.jsx','MiniMaxH3Ref2VAPage.jsx']){
  const source=readFileSync(new URL('../../gui/'+file,import.meta.url),'utf8');const code=source.slice(source.indexOf('  async function readSavedInput('),source.indexOf('  function restoreSavedInput('));
  const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},currentInput:{current:{busy:false,pending:null}},current:{current:{busy:false,pending:null,checking:false}},imageChecking:{current:false},imageSelectionRevision:{current:0},imageVersion:{current:0},reviewRequest:{current:null},editVersion:{current:0},fetch:async()=>({ok:true,json:async()=>{throw new SyntaxError('Unexpected token');}}),encodeURIComponent,setTimeout,clearTimeout});
  vm.runInContext(code,context);const controller=new AbortController();const pending=file==='MiniMaxH3Ref2VAPage.jsx'?context.readSavedInput('id',{signal:controller.signal}):context.readSavedInput('id',true,{signal:controller.signal});await assert.rejects(pending,/저장 입력 형식을 확인할 수 없습니다/,file);
 }
});
