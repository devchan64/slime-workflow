import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('MiniMax 저장 입력은 샘플러를 복원하고 대화 제안은 현재 기본 LCM만 허용한다',()=>{
 const source=readFileSync(new URL('../../gui/MiniMaxH3ImagePage.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  function restoreSavedInput('),end=source.indexOf('  function closeReview()',start);assert.ok(start>=0&&end>start);
 for(const [sampler,proposal,expected] of [['lcm',false,'lcm'],['euler',false,'euler'],[undefined,false,'euler'],['lcm',true,'lcm'],['euler',true,null],[undefined,true,null]]){
  let selected='unchanged';const context=vm.createContext({interaction:{current:{busy:false,pending:null,receiptState:'editing'}},checkingSlots:{current:new Set()},inputRevision:{current:0},sending:{current:false},separatePages:false,proposalScope:proposal?{}:null,setPrompt:()=>{},setSeed:()=>{},setSize:()=>{},setDownscale:()=>{},setSampler:value=>selected=value,setReferences:()=>{},setReferenceReset:()=>{},setError:()=>{},setNotice:()=>{},formRef:{current:null},requestAnimationFrame:()=>{}});
  vm.runInContext(source.slice(start,end),context);const request={prompt:'p',seed:42,sampler},record={checkingAtStart:false,revisionAtStart:0,scaled:false,output:{width:832},files:[],id:'job'};
  if(expected===null)assert.throws(()=>context.restoreSavedInput(request,record),/LCM 샘플러와 축소 없는 입력만/);else context.restoreSavedInput(request,record);
  assert.equal(selected,expected??'unchanged');
 }
});
