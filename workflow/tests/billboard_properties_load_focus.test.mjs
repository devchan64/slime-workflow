import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('반올림 후 변경 없음 오류는 수정 가능한 안내로 표시한다',()=>{
  const code=readFileSync(new URL('../../gui/BillboardProperties.jsx',import.meta.url),'utf8');
  const match=code.match(/export function billboardPreviewError\(problem\)\{[^\n]+\}/);assert.ok(match);
  const context=vm.createContext({requestErrorMessage:problem=>problem.message});
  const format=vm.runInContext('('+match[0].replace('export ','')+')',context);
  assert.match(format({message:'관리 API 오류 (400): 변경 없는 에셋은 제외하세요: sample'}),/반올림 후 기존 값과 같아/);
  assert.equal(format({message:'연결 오류'}),'연결 오류');
});

test('빌보드 속성 조회가 끝나면 잃은 초점만 조회 버튼으로 복구한다',()=>{
  const code=readFileSync(new URL('../../gui/BillboardProperties.jsx',import.meta.url),'utf8');
  const start=code.indexOf('  useEffect(()=>{if(!busy && restoreLoadFocus.current)'),end=code.indexOf('\n',start);assert.ok(start>=0 && end>start);
  for(const state of ['body','other','disabled']){
    const body={},document={body,activeElement:state==='other'?{}:body};let focused=false;
    const context=vm.createContext({document,busy:false,source:null,notice:'',edits:{},restoreLoadFocus:{current:true},loadButton:{current:{disabled:state==='disabled',focus(){focused=true;}}},useEffect:fn=>fn()});
    vm.runInContext(code.slice(start,end),context);assert.equal(focused,state==='body');assert.equal(context.restoreLoadFocus.current,false);
  }
});
test('속성 검토 오류에서 잃은 초점만 검토 시작 위치로 돌린다',()=>{
  const code=readFileSync(new URL('../../gui/BillboardProperties.jsx',import.meta.url),'utf8');
  const start=code.indexOf('  useEffect(()=>{if(!busy && restoreReviewFocus.current)'),end=code.indexOf('\n',start);assert.ok(start>=0 && end>start);
  for(const state of ['body','other','success']){
    const body={},document={body,activeElement:state==='other'?{}:body};let focused=false;
    const context=vm.createContext({document,busy:false,notice:state==='success'?'':'오류',review:null,restoreReviewFocus:{current:true},reviewTrigger:{current:{isConnected:true,disabled:false,focus(){focused=true;}}},useEffect:fn=>fn()});
    vm.runInContext(code.slice(start,end),context);assert.equal(focused,state==='body');assert.equal(context.restoreReviewFocus.current,false);
  }
});
test('표시 높이는 서버가 허용하는 양수와 1024 경계를 따른다',()=>{
  const code=readFileSync(new URL('../../gui/BillboardProperties.jsx',import.meta.url),'utf8');
  const match=code.match(/export function invalidDisplayHeight\(value\)\{[^\n]+\}/);assert.ok(match);
  const check=vm.runInNewContext('('+match[0].replace('export ','')+')');
  for(const value of ['-1','0','0.0049','1024.1','Infinity'])assert.equal(check(value),true);
  for(const value of ['','0.005','1024'])assert.equal(check(value),false);
});
test('잘못된 표시 높이는 검토 요청 전에 거절한다',async()=>{
  const code=readFileSync(new URL('../../gui/BillboardProperties.jsx',import.meta.url),'utf8');
  const start=code.indexOf('  async function preview(event){'),end=code.indexOf('\n  async function save()',start);assert.ok(start>=0 && end>start);
  let calls=0,notice='',busy=false;
  const context=vm.createContext({document:{activeElement:{}},busy:false,source:{properties:{displayHeight:100}},edits:{displayHeight:'-1'},reviewTrigger:{current:null},restoreReviewFocus:{current:false},
    invalidDisplayHeight:value=>Number(value)<=0 || Number(value)>1024,setBusy:value=>busy=value,setNotice:value=>notice=value,setReview:()=>{},billboardPreviewError:problem=>problem.message,read:()=>{calls++;}});
  vm.runInContext(code.slice(start,end)+'\nthis.preview=preview;',context);await context.preview({preventDefault(){}});
  assert.equal(calls,0);assert.equal(busy,false);assert.match(notice,/0\.005부터 1024/);
});
test('점유 열과 행은 1부터 8까지 정수만 허용하고 잘못된 값은 전송하지 않는다',async()=>{
  const code=readFileSync(new URL('../../gui/BillboardProperties.jsx',import.meta.url),'utf8');
  const match=code.match(/export function invalidFootprint\(value\)\{[^\n]+\}/);assert.ok(match);
  const check=vm.runInNewContext('('+match[0].replace('export ','')+')');
  for(const value of ['0','9','1.5','Infinity'])assert.equal(check(value),true);
  for(const value of ['','1','8'])assert.equal(check(value),false);
  const start=code.indexOf('  async function preview(event){'),end=code.indexOf('\n  async function save()',start);assert.ok(start>=0 && end>start);
  for(const key of ['groundFootprintColumns','groundFootprintRows']){
    let calls=0,notice='';const context=vm.createContext({document:{activeElement:{}},busy:false,source:{properties:{}},edits:{[key]:'1.5'},reviewTrigger:{current:null},restoreReviewFocus:{current:false},invalidFootprint:check,invalidDisplayHeight:()=>false,setBusy:()=>{},setNotice:value=>notice=value,setReview:()=>{},billboardPreviewError:problem=>problem.message,read:()=>calls++});
    vm.runInContext(code.slice(start,end)+'\nthis.preview=preview;',context);await context.preview({preventDefault(){}});assert.equal(calls,0);assert.match(notice,/1부터 8까지/);
  }
});
test('그림자 이동은 -4부터 4까지 허용하며 범위 밖 입력은 전송하지 않는다',async()=>{
  const code=readFileSync(new URL('../../gui/BillboardProperties.jsx',import.meta.url),'utf8');
  const match=code.match(/export function invalidShadowOffset\(value\)\{[^\n]+\}/);assert.ok(match);
  const check=vm.runInNewContext('('+match[0].replace('export ','')+')');
  for(const value of ['-4.1','4.1','Infinity'])assert.equal(check(value),true);
  for(const value of ['','-4','0.25','4'])assert.equal(check(value),false);
  const start=code.indexOf('  async function preview(event){'),end=code.indexOf('\n  async function save()',start);assert.ok(start>=0 && end>start);
  for(const key of ['shadowOffsetColumn','shadowOffsetRow']){
    let calls=0,notice='';const context=vm.createContext({document:{activeElement:{}},busy:false,source:{properties:{}},edits:{[key]:'4.1'},reviewTrigger:{current:null},restoreReviewFocus:{current:false},invalidShadowOffset:check,invalidFootprint:()=>false,invalidDisplayHeight:()=>false,setBusy:()=>{},setNotice:value=>notice=value,setReview:()=>{},billboardPreviewError:problem=>problem.message,read:()=>calls++});
    vm.runInContext(code.slice(start,end)+'\nthis.preview=preview;',context);await context.preview({preventDefault(){}});assert.equal(calls,0);assert.match(notice,/-4부터 4까지/);
  }
});
test('그림자 배율은 버전과 축에 따른 하한을 적용하고 범위 밖 값은 전송하지 않는다',async()=>{
  const code=readFileSync(new URL('../../gui/BillboardProperties.jsx',import.meta.url),'utf8');
  const min=code.match(/export function shadowScaleMinimum\(key,version\)\{[^\n]+\}/),invalid=code.match(/export function invalidShadowScale\(value,key,version\)\{[^\n]+\}/);assert.ok(min && invalid);
  const context=vm.createContext({});vm.runInContext(min[0].replace('export ','')+'\n'+invalid[0].replace('export ','')+'\nthis.check=invalidShadowScale;',context);
  for(const [key,version,minimum] of [['shadowScaleX',1,0.1],['shadowScaleY',1,0.05],['shadowScaleX',2,0.001],['shadowScaleY',2,0.001]]){
    assert.equal(context.check(String(minimum),key,version),false);assert.equal(context.check(String(minimum/2),key,version),true);assert.equal(context.check('4',key,version),false);assert.equal(context.check('4.1',key,version),true);
    let calls=0,notice='';Object.assign(context,{document:{activeElement:{}},busy:false,source:{properties:{shadowSizeVersion:version}},edits:{[key]:String(minimum/2)},reviewTrigger:{current:null},restoreReviewFocus:{current:false},invalidFootprint:()=>false,invalidDisplayHeight:()=>false,invalidShadowOffset:()=>false,setBusy:()=>{},setNotice:value=>notice=value,setReview:()=>{},billboardPreviewError:problem=>problem.message,read:()=>calls++});
    const start=code.indexOf('  async function preview(event){'),end=code.indexOf('\n  async function save()',start);vm.runInContext(code.slice(start,end)+'\nthis.preview=preview;',context);await context.preview({preventDefault(){}});assert.equal(calls,0);assert.match(notice,/배율/);
  }
});
test('앵커 범위는 타일 기준과 기존 좌표 기준에 맞는다',()=>{
  const code=readFileSync(new URL('../../gui/BillboardProperties.jsx',import.meta.url),'utf8');
  const match=code.match(/export function invalidBillboardAnchor\(value,automatic\)\{[^\n]+\}/);assert.ok(match);
  const check=vm.runInNewContext('('+match[0].replace('export ','')+')');
  for(const value of ['-16','16','-0.5'])assert.equal(check(value,true),false);
  for(const value of ['-16.1','16.1'])assert.equal(check(value,true),true);
  for(const value of ['0','1'])assert.equal(check(value,false),false);
  for(const value of ['-0.01','1.01'])assert.equal(check(value,false),true);
});
test('최초 등록은 버전 2의 작은 그림자 배율로 검토할 수 있다',async()=>{
  const code=readFileSync(new URL('../../gui/BillboardProperties.jsx',import.meta.url),'utf8');
  const min=code.match(/export function shadowScaleMinimum\(key,version\)\{[^\n]+\}/),invalid=code.match(/export function invalidShadowScale\(value,key,version\)\{[^\n]+\}/);assert.ok(min && invalid);
  let calls=0;const context=vm.createContext({document:{activeElement:{}},busy:false,source:{initial:true,revision:'r',properties:{shadowScaleX:1}},edits:{shadowScaleX:'0.001'},texture:'x',reviewTrigger:{current:null},restoreReviewFocus:{current:false},invalidFootprint:()=>false,invalidDisplayHeight:()=>false,invalidShadowOffset:()=>false,invalidBillboardAnchor:()=>false,setBusy:()=>{},setNotice:()=>{},setReview:()=>{},billboardPreviewError:problem=>problem.message,read:async()=>{calls++;throw new Error('검사 종료');}});
  const start=code.indexOf('  async function preview(event){'),end=code.indexOf('\n  async function save()',start);vm.runInContext(min[0].replace('export ','')+'\n'+invalid[0].replace('export ','')+'\n'+code.slice(start,end)+'\nthis.preview=preview;',context);await context.preview({preventDefault(){}});assert.equal(calls,1);
});


test('비어 있는 숫자 속성은 검토 요청으로 전달하지 않는다',async()=>{
  const code=readFileSync(new URL('../../gui/BillboardProperties.jsx',import.meta.url),'utf8');
  const start=code.indexOf('  async function preview(event){'),end=code.indexOf('\n  async function save()',start);
  let calls=0,notice='';
  const context=vm.createContext({document:{activeElement:{}},busy:false,source:{properties:{displayHeight:100}},edits:{displayHeight:''},reviewTrigger:{current:null},restoreReviewFocus:{current:false},setBusy:()=>{},setNotice:value=>notice=value,setReview:()=>{},billboardPreviewError:problem=>problem.message,read:()=>calls++});
  vm.runInContext(code.slice(start,end)+'\nthis.preview=preview;',context);await context.preview({preventDefault(){}});
  assert.equal(calls,0);assert.match(notice,/비어 있는 숫자/);
});

test('원래 값으로 복구한 필드만 변경 목록에서 제거한다',()=>{
  const code=readFileSync(new URL('../../gui/BillboardProperties.jsx',import.meta.url),'utf8');
  const start=code.indexOf('  function edit(key,value){'),end=code.indexOf('\n  async function preview',start);
  let dirty=null,updated;
  const context=vm.createContext({source:{properties:{displayHeight:84.12,billboardBlocksMovement:false}},edits:{displayHeight:'85',shadowOffsetColumn:'1'},setEdits:value=>updated=value,onDirtyChange:value=>dirty=value,setReview:()=>{},setNotice:()=>{}});
  vm.runInContext(code.slice(start,end)+'\nthis.edit=edit;',context);
  context.edit('displayHeight','84.120');assert.deepEqual({...updated},{shadowOffsetColumn:'1'});assert.equal(dirty,true);
  context.edits=updated;context.edit('billboardBlocksMovement',false);assert.deepEqual({...updated},{shadowOffsetColumn:'1'});
  context.edits={};context.edit('displayHeight','');assert.deepEqual({...updated},{displayHeight:''});assert.equal(dirty,true);
  context.edits={displayHeight:'85'};context.edit('displayHeight','84.12');assert.deepEqual({...updated},{});assert.equal(dirty,false);
});
