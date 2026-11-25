import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

const source=readFileSync(new URL('../../gui/BillboardCrop.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('  async function save(){'),source.indexOf('  const result=review?.result;'));

test('크롭 오류·결과 초점은 사용자가 이동했으면 빼앗지 않는다',()=>{
  const effect=source.split('\n').find(line=>line.includes('restoreLostFocus(document,message ?'));
  for(const destination of ['body','other'])for(const failure of [true,false]){
    const body={},other={};let focus=0;const target={isConnected:true,disabled:false,focus:()=>focus++};
    const context=vm.createContext({busy:false,message:failure?'실패':'',review:failure?null:{},restoreFocus:{current:true},messageRef:{current:target},reviewRef:{current:target},rangeButton:{current:null},document:{body,activeElement:destination==='body'?body:other},restoreLostFocus,useEffect:fn=>fn()});
    vm.runInContext(effect,context);assert.equal(focus,destination==='body'?1:0);assert.equal(context.restoreFocus.current,false);
  }
});

test('크롭 저장 시간 초과는 결과 불확실을 알리고 중복 요청을 막는다',async()=>{
  let timer,calls=0,message='',busy=false,review={request:{texture:'asset',token:'token',alphaThreshold:5}};
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validCropSave:()=>true,source:{texture:'asset'},busy:false,review,restoreFocus:{current:false},
    saving:{current:false},saveRequest:{current:null},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setMessage:value=>message=value,setReview:value=>review=value,
    onSaved:()=>assert.fail('저장 확정 불가'),managementCommand:()=>{calls++;return new Promise(()=>{});}});
  vm.runInContext(code,context);const pending=context.save();await context.save();assert.equal(calls,1);timer();await pending;
  assert.equal(busy,false);assert.equal(review,null);assert.match(message,/진행 중일 수 있으므로/);assert.match(message,/시간이 초과/);
});

test('크롭 저장은 확인한 토큰과 기준이 일치할 때만 완료 처리한다',async()=>{
  for(const mismatch of ['token','alpha','none']){
    let completed=0,message='';const review={request:{texture:'asset',token:'token',alphaThreshold:5}};
    const result={saved:true,token:mismatch==='token'?'other':'token',alpha_threshold:mismatch==='alpha'?6:5};
    const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validCropSave:(value,request)=>value.saved===true && value.token===request.token && value.alpha_threshold===request.alphaThreshold,source:{texture:'asset'},busy:false,review,restoreFocus:{current:true},
      saving:{current:false},saveRequest:{current:null},setTimeout,clearTimeout,setBusy:()=>{},setMessage:value=>message=value,setReview:()=>{},onSaved:options=>{assert.equal(options.restoreFocus,true);completed++;},managementCommand:async()=>result});
    vm.runInContext(code,context);await context.save();assert.equal(completed,mismatch==='none'?1:0);
    if(mismatch!=='none')assert.match(message,/원본과 이력을 확인/);
  }
});
