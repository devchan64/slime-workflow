import {test} from 'node:test';
import assert from 'node:assert/strict';
import {openInvalidDetails} from '../../gui/openInvalidDetails.mjs';

test('접힌 설정의 첫 오류만 펼쳐 초점을 이동한다',()=>{
 let focused=0,scheduled;
 const earlier={},target={isConnected:true,focus:()=>focused++};
 const details={open:false,contains:value=>value===target};
 const form={querySelector:()=>earlier};
 openInvalidDetails({target,currentTarget:form},details,fn=>scheduled=fn);
 assert.equal(details.open,false);assert.equal(scheduled,undefined);
 form.querySelector=()=>target;
 openInvalidDetails({target,currentTarget:form},details,fn=>scheduled=fn);
 assert.equal(details.open,true);scheduled();assert.equal(focused,1);
});

test('이미 펼쳐졌거나 제거된 입력에는 초점을 강제로 이동하지 않는다',()=>{
 let focused=0,scheduled;
 const target={isConnected:false,focus:()=>focused++},form={querySelector:()=>target};
 const details={open:true,contains:()=>true};
 openInvalidDetails({target,currentTarget:form},details,fn=>scheduled=fn);
 assert.equal(scheduled,undefined);
 details.open=false;openInvalidDetails({target,currentTarget:form},details,fn=>scheduled=fn);scheduled();
 assert.equal(focused,0);
});


test('오류가 열리는 동안 사용자가 옮긴 초점은 유지한다',()=>{
 let focused=0,scheduled;
 const origin={},other={},doc={activeElement:origin,body:{}};
 const target={isConnected:true,ownerDocument:doc,focus:()=>focused++};
 const details={open:false,contains:()=>true},form={querySelector:()=>target};
 openInvalidDetails({target,currentTarget:form},details,fn=>scheduled=fn);
 doc.activeElement=other;scheduled();assert.equal(focused,0);
});
