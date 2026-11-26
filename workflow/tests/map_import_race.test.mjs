import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {visibleFocusTarget} from '../../gui/restoreLostFocus.mjs';
const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('  async function importDraft(file,focused=false){'),source.indexOf('  async function discardDraft(event){'));
test('지도 초안 읽기 중 중복 선택을 막고 시간 초과 뒤 다시 불러올 수 있다',async()=>{
 let timer,finish,reads=0,busy=false,error='',applied;const file={text:()=>{reads++;return reads===1?new Promise(done=>finish=done):Promise.resolve(JSON.stringify({map:'map',revision:'rev'}));}};
 const c=vm.createContext({AbortController,untilAborted,JSON,window:{},importRequest:{current:null},readRequest:{current:null},savingRef:{current:false},restoreImportFocus:{current:false},draft:{map:'map',revision:'rev'},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setImportError:value=>error=value,setReading:value=>busy=value,requestErrorMessage:e=>e.message,applyDraft:async value=>applied=value});
 vm.runInContext(code+'\nthis.importDraft=importDraft;',c);const first=c.importDraft(file);await c.importDraft(file);assert.equal(reads,1);timer();await first;assert.match(error,/시간이 초과/);assert.equal(busy,false);
 await c.importDraft(file);assert.equal(reads,2);assert.equal(applied.map,'map');finish(JSON.stringify({map:'old',revision:'rev'}));await Promise.resolve();assert.equal(applied.map,'map');
});
test('지도 검증이나 저장 중에는 새 초안 읽기를 시작하지 않는다',async()=>{
 let reads=0;const c=vm.createContext({importRequest:{current:null},readRequest:{current:{}},savingRef:{current:false}});vm.runInContext(code+'\nthis.importDraft=importDraft;',c);
 await c.importDraft({text:()=>reads++});c.readRequest.current=null;c.savingRef.current=true;await c.importDraft({text:()=>reads++});assert.equal(reads,0);
});
test('지도 초안 읽기 후 사용자가 이동한 초점과 잠긴 입력을 존중한다',()=>{
 const effect=source.match(/useEffect\(\(\)=>\{if\(reading \|\| !restoreImportFocus\.current\)return;.*?\},\[reading,importError\]\);/)?.[0];assert.ok(effect);
 for(const mode of ['lost','moved','disabled']){
  const body={},other={};let run,focused=0;const target={isConnected:true,matches:()=>mode==='disabled',focus:()=>focused++};
  const c=vm.createContext({useEffect:fn=>run=fn,reading:false,importError:'오류',restoreImportFocus:{current:true},importInputRef:{current:target},visibleFocusTarget,document:{body,activeElement:mode==='moved'?other:body},restoreLostFocus:(doc,node)=>{if(doc.activeElement===doc.body)node.focus();}});
  vm.runInContext(effect,c);run();assert.equal(focused,mode==='lost'?1:0);assert.equal(c.restoreImportFocus.current,false);
 }
});

test('초안을 닫을 때만 이전 파일 오류를 지운다',()=>{
 const effect=source.match(/useEffect\(\(\)=>\{if\(!draft\)setImportError\(""\);\},\[draft\]\);/)?.[0];assert.ok(effect);
 for(const draft of [null,{map:'field'}]){
  let run,error='파일 오류';const c=vm.createContext({useEffect:fn=>run=fn,draft,setImportError:value=>error=value});
  vm.runInContext(effect,c);run();assert.equal(error,draft?'파일 오류':'');
 }
});
