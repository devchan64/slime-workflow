import test from 'node:test';
import assert from 'node:assert/strict';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

test('본문으로 초점을 잃은 경우에만 연결되고 활성화된 대상으로 복귀한다',()=>{
  const body={},doc={body,activeElement:body};let count=0;
  const target={isConnected:true,disabled:false,focus(){count++;}};
  assert.equal(restoreLostFocus(doc,target),true);assert.equal(count,1);
  doc.activeElement={};assert.equal(restoreLostFocus(doc,target),false);
  doc.activeElement=body;target.disabled=true;assert.equal(restoreLostFocus(doc,target),false);
  target.disabled=false;target.isConnected=false;assert.equal(restoreLostFocus(doc,target),false);
  assert.equal(restoreLostFocus(doc,null),false);assert.equal(count,1);
});
