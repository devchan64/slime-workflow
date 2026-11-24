import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

test('FLUX 가이드 검색 초기화는 사라진 초점만 검색 입력으로 돌린다',()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('  function resetGuideSearch('),source.indexOf('  function guideUrl('));
 for(const moved of [false,true]){
  let frame,focused=0,query='old';const body={},button={},other={},document={body,activeElement:button};
  const context=vm.createContext({document,restoreLostFocus,guidePageFrame:{current:null},guideSearchRef:{current:{isConnected:true,focus:()=>focused++}},setGuideQuery:value=>query=value,setGuidePage:()=>{},setSelectedGuide:()=>{},requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(method,context);context.resetGuideSearch({currentTarget:button});document.activeElement=moved?other:body;frame();assert.equal(query,'');assert.equal(focused,moved?0:1);
 }
});

test('FLUX 가이드 페이지 경계에서 사라진 초점만 사용 가능한 버튼으로 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('  function moveGuidePage('),source.indexOf('  function guideUrl('));
 for(const moved of [false,true]){
  let frame,page=0,focused=0;const body={},other={},target={isConnected:true,disabled:true},document={body,activeElement:target};
  const context=vm.createContext({document,restoreLostFocus,guidePageFrame:{current:null},guidePagesRef:{current:{querySelector:()=>({isConnected:true,focus:()=>focused++})}},guideSearchRef:{current:null},setGuidePage:fn=>page=fn(page),setSelectedGuide:()=>{},requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(method,context);context.moveGuidePage({currentTarget:target},1);document.activeElement=moved?other:body;frame();assert.equal(page,1);assert.equal(focused,moved?0:1);
 }
});

test('FLUX 참조 도구 완료 후 사라진 초점만 원래 버튼으로 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    if(busy || !toolFocus.current)'),source.indexOf('  useEffect(()=>{setGuideNotice'));
 for(const moved of [false,true]){
  let frame,focused=0;const body={},other={},document={body,activeElement:moved?other:body};
  const context=vm.createContext({document,busy:false,toolFocus:{current:{isConnected:true,focus:()=>focused++}},inputFormRef:{current:{isConnected:true,focus:()=>focused++}},restoreLostFocus,useEffect:fn=>fn(),requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(effect,context);frame();assert.equal(focused,moved?0:1);
 }
});

test('FLUX 참조 도구 버튼이 사라지면 입력 영역으로 초점을 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    if(busy || !toolFocus.current)'),source.indexOf('  useEffect(()=>{setGuideNotice'));
 let frame,focused=0;const body={},document={body,activeElement:body};
 const context=vm.createContext({document,busy:false,toolFocus:{current:{isConnected:false}},inputFormRef:{current:{isConnected:true,focus:()=>focused++}},restoreLostFocus,useEffect:fn=>fn(),requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
 vm.runInContext(effect,context);frame();assert.equal(focused,1);
});

test('FLUX 검토와 프로필 복구 초점 예약은 화면 전환 시 취소된다',()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const effects=source.slice(source.indexOf('  useEffect(()=>{if(!review)return;'),source.indexOf('  const [selectedGuide'));
 let cleanups=[],cancelled=[];const body={},document={body,activeElement:body};
 const context=vm.createContext({document,review:{},reviewOrigin:{current:null},reviewRef:{current:{isConnected:true,focus:()=>{}}},profileRetryFocus:{current:true},profile:{},profileError:'',inputFormRef:{current:{}},profileRetryRef:{current:{}},useEffect:fn=>cleanups.push(fn()),requestAnimationFrame:()=>cleanups.length+1,cancelAnimationFrame:id=>cancelled.push(id)});
 vm.runInContext(effects,context);assert.equal(cleanups.length,2);cleanups.forEach(cleanup=>cleanup());assert.equal(cancelled.length,2);
});
