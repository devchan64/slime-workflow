import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

test('초안 되돌리기와 다시 실행은 사라진 초점만 결과 안내로 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(!reading && feedback && restorePreviewFocus\.current\).*?\},\[reading,feedback\]\);/)?.[0];assert.ok(effect);
 for(const action of ['undo','redo'])for(const moved of [false,true]){
  const handler=source.match(new RegExp('onClick=\\{(event=>\\{restorePreviewFocus\\.current=document\\.activeElement===event\\.currentTarget;applyDraft\\([^}]*?"'+action+'"\\);\\})\\}'))?.[1];assert.ok(handler);
  let focused=0,called='';const body={},button={},document={body,activeElement:button},restorePreviewFocus={current:false};
  const context=vm.createContext({document,restorePreviewFocus,applyDraft:(_draft,name)=>called=name,past:[{}],future:[{}],useEffect:fn=>fn(),reading:false,feedback:'검증 완료',feedbackRef:{current:{isConnected:true,focus:()=>focused++}},restoreLostFocus});
  vm.runInContext('('+handler+')',context)({currentTarget:button});document.activeElement=moved?{}:body;vm.runInContext(effect,context);
  assert.equal(called,action);assert.equal(focused,moved?0:1);
 }
});

test('빌보드 편집은 처리 시작 시에만 버튼 초점을 기록한다',async()=>{
 const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function applyDraft('),source.indexOf('  async function save(event)'));
 for(const blocked of [false,true]){
  const button={},restorePreviewFocus={current:false};
  const context=vm.createContext({document:{activeElement:button},restorePreviewFocus,readRequest:{current:blocked?{}:null},savingRef:{current:false},importRequest:{current:null},window:{},cellDirty:false,setReading:()=>{},setPreview:()=>{},setFeedback:()=>{},readMap:async()=>{throw Error('network');},requestErrorMessage:error=>error.message});
  vm.runInContext(code,context);await context.applyDraft({},'edit',null,{currentTarget:button});
  assert.equal(restorePreviewFocus.current,!blocked);
 }
 assert.match(source,/function addObject\(event\)[\s\S]*?"edit",null,event\)/);
 assert.match(source,/function moveObject\(event\)[\s\S]*?"edit",null,event\)/);
 assert.equal((source.match(/onClick=\{event=>applyDraft\([^\n]*?"edit",null,event\)\}/g)||[]).length,2);
});
