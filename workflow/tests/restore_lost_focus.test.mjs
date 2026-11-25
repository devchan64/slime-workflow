import test from 'node:test';
import assert from 'node:assert/strict';
import {restoreLostFocus,visibleFocusTarget} from '../../gui/restoreLostFocus.mjs';

test('본문으로 초점을 잃은 경우에만 연결되고 활성화된 대상으로 복귀한다',()=>{
  const body={},doc={body,activeElement:body};let count=0;
  const target={isConnected:true,disabled:false,focus(){count++;}};
  assert.equal(restoreLostFocus(doc,target),true);assert.equal(count,1);
  doc.activeElement={};assert.equal(restoreLostFocus(doc,target),false);
  doc.activeElement=body;target.disabled=true;assert.equal(restoreLostFocus(doc,target),false);
  target.disabled=false;target.isConnected=false;assert.equal(restoreLostFocus(doc,target),false);
  assert.equal(restoreLostFocus(doc,null),false);assert.equal(count,1);
});

test('접힌 영역의 초점 대상은 보이는 바깥쪽 제목으로 돌아간다',()=>{
  const outerSummary={},innerSummary={};
  const outer={tagName:'DETAILS',open:false,parentElement:null,querySelector:()=>outerSummary};
  const inner={tagName:'DETAILS',open:false,parentElement:outer,querySelector:()=>innerSummary};
  const input={tagName:'INPUT',parentElement:inner};
  assert.equal(visibleFocusTarget(input),outerSummary);
  outer.open=true;assert.equal(visibleFocusTarget(input),innerSummary);
  inner.open=true;assert.equal(visibleFocusTarget(input),input);
  assert.equal(visibleFocusTarget(null),null);
});
