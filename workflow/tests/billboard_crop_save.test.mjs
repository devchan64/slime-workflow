import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {restoreLostFocus,visibleFocusTarget} from '../../gui/restoreLostFocus.mjs';

const source=readFileSync(new URL('../../gui/BillboardCrop.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('  async function save(){'),source.indexOf('  const result=review?.result;'));
const previewCode=source.slice(source.indexOf('export function invalidCropThreshold'),source.indexOf('\n}',source.indexOf('export function invalidCropThreshold'))+2).replace('export ','')+'\n'+source.slice(source.indexOf('  async function preview(auto)'),source.indexOf('  async function save()'));

test('잘못된 알파 기준에서도 자동 추천을 다시 검증해 확인 결과로 사용한다',async()=>{
  const calls=[];let threshold='',review=null,message='',busy=false;
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validCropPreview:()=>true,source:{texture:'asset',revision:'rev'},threshold:'',busy:false,requestRef:{current:null},setTimeout,clearTimeout,
    setThreshold:value=>threshold=value,setReview:value=>review=value,setMessage:value=>message=value,setBusy:value=>busy=value,
    managementCommand:async (_domain,_command,request)=>{calls.push({...request});return {alpha_threshold:42,token:calls.length===1?'recommended':'verified'};}});
  vm.runInContext(previewCode,context);await context.preview(true);
  assert.deepEqual(calls.map(call=>call.alphaThreshold),['auto',42]);assert.equal(threshold,'42');assert.equal(review.request.token,'verified');assert.equal(review.request.alphaThreshold,42);assert.equal(message,'');assert.equal(busy,false);
});

test('잘못된 알파 기준의 수동 확인은 요청을 보내지 않고 오류를 표시한다',async()=>{
  let calls=0,message='',busy=false;
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validCropPreview:()=>true,source:{texture:'asset'},threshold:'',busy:false,requestRef:{current:null},setTimeout,clearTimeout,
    setThreshold:()=>{},setReview:()=>{},setMessage:value=>message=value,setBusy:value=>busy=value,managementCommand:()=>{calls++;}});
  vm.runInContext(previewCode,context);await context.preview(false);
  assert.equal(calls,0);assert.match(message,/0~254/);assert.equal(busy,false);
});

test('자동 추천 범위 재확인이 실패하면 기존 입력을 유지한다',async()=>{
  for(const failure of ['error','mismatch']){
    let calls=0,threshold='7',review=null,message='',busy=false;
    const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validCropPreview:()=>true,source:{texture:'asset'},threshold:'7',busy:false,requestRef:{current:null},setTimeout,clearTimeout,
      setThreshold:value=>threshold=value,setReview:value=>review=value,setMessage:value=>message=value,setBusy:value=>busy=value,
      managementCommand:async()=>{calls++;if(calls===2 && failure==='error')throw new Error('조회 실패');return {alpha_threshold:calls===2?43:42,token:'token'};}});
    vm.runInContext(previewCode,context);await context.preview(true);
    assert.equal(calls,2);assert.equal(threshold,'7');assert.equal(review,null);assert.ok(message);assert.equal(busy,false);
  }
});

test('범위 재조회는 이전 저장 결과 미확인 경고를 지우지 않는다',async()=>{
  let warning='저장 결과 확인 필요',review=null;
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validCropPreview:()=>true,source:{texture:'asset'},threshold:'5',busy:false,requestRef:{current:null},setTimeout,clearTimeout,
    setThreshold:()=>{},setReview:value=>review=value,setMessage:()=>{},setSaveWarning:value=>warning=value,setBusy:()=>{},managementCommand:async()=>({alpha_threshold:5,token:'token'})});
  vm.runInContext(previewCode,context);await context.preview(false);
  assert.equal(warning,'저장 결과 확인 필요');assert.equal(review.request.token,'token');
});

test('크롭 오류·결과 초점은 사용자가 이동했으면 빼앗지 않는다',()=>{
  const effect=source.split('\n').find(line=>line.includes('restoreLostFocus(document,visibleFocusTarget('));
  for(const destination of ['body','other'])for(const failure of [true,false]){
    const body={},other={};let focus=0;const target={isConnected:true,disabled:false,focus:()=>focus++};
    const context=vm.createContext({busy:false,message:failure?'실패':'',saveWarning:'',review:failure?null:{},restoreFocus:{current:true},messageRef:{current:target},saveWarningRef:{current:target},reviewRef:{current:target},rangeButton:{current:null},document:{body,activeElement:destination==='body'?body:other},restoreLostFocus,visibleFocusTarget,useEffect:fn=>fn()});
    vm.runInContext(effect,context);assert.equal(focus,destination==='body'?1:0);assert.equal(context.restoreFocus.current,false);
  }
});

test('저장 경고가 남아도 새 검토는 검토 영역으로, 저장 실패는 경고로 초점을 복구한다',()=>{
  const effect=source.split('\n').find(line=>line.includes('restoreLostFocus(document,visibleFocusTarget('));
  for(const [hasReview,expected] of [[true,'review'],[false,'warning']]){
    const body={};let focused='';const target=name=>({isConnected:true,disabled:false,focus:()=>focused=name});
    const context=vm.createContext({busy:false,message:'',saveWarning:'저장 결과 확인 필요',review:hasReview?{}:null,restoreFocus:{current:true},messageRef:{current:target('message')},saveWarningRef:{current:target('warning')},reviewRef:{current:target('review')},rangeButton:{current:target('button')},document:{body,activeElement:body},restoreLostFocus,visibleFocusTarget,useEffect:fn=>fn()});
    vm.runInContext(effect,context);assert.equal(focused,expected);assert.equal(context.restoreFocus.current,false);
  }
});

test('크롭 저장 시간 초과는 결과 불확실을 알리고 중복 요청을 막는다',async()=>{
  let timer,calls=0,message='',busy=false,review={request:{texture:'asset',token:'token',alphaThreshold:5}};
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validCropSave:()=>true,source:{texture:'asset'},busy:false,review,restoreFocus:{current:false},
    saving:{current:false},saveRequest:{current:null},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setMessage:()=>{},setSaveWarning:value=>message=value,setReview:value=>review=value,
    onSaved:()=>assert.fail('저장 확정 불가'),managementCommand:()=>{calls++;return new Promise(()=>{});}});
  vm.runInContext(code,context);const pending=context.save();await context.save();assert.equal(calls,1);timer();await pending;
  assert.equal(busy,false);assert.equal(review,null);assert.match(message,/진행 중일 수 있으므로/);assert.match(message,/시간이 초과/);
});

test('크롭 저장은 확인한 토큰과 기준이 일치할 때만 완료 처리한다',async()=>{
  for(const mismatch of ['token','alpha','none']){
    let completed=0,message='';const review={request:{texture:'asset',token:'token',alphaThreshold:5}};
    const result={saved:true,token:mismatch==='token'?'other':'token',alpha_threshold:mismatch==='alpha'?6:5};
    const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validCropSave:(value,request)=>value.saved===true && value.token===request.token && value.alpha_threshold===request.alphaThreshold,source:{texture:'asset'},busy:false,review,restoreFocus:{current:true},
      saving:{current:false},saveRequest:{current:null},setTimeout,clearTimeout,setBusy:()=>{},setMessage:()=>{},setSaveWarning:value=>message=value,setReview:()=>{},onSaved:options=>{assert.equal(options.restoreFocus,true);completed++;},managementCommand:async()=>result});
    vm.runInContext(code,context);await context.save();assert.equal(completed,mismatch==='none'?1:0);
    if(mismatch!=='none')assert.match(message,/원본과 이력을 확인/);
  }
});
