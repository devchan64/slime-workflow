import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('걷기 비교 단축키는 입력·링크와 수정 키를 방해하지 않는다',()=>{
  const html=readFileSync(new URL('../../gui/ui/asset_review/walk-sheet.html',import.meta.url),'utf8');
  const line=html.split('\n').find(value=>value.startsWith("document.addEventListener('keydown'"));
  let handler,played=0,frame,selector='';
  const context={document:{addEventListener:(_type,callback)=>handler=callback,querySelector:()=>({click:()=>played++})},selectedFrameIndex:2,reviewImagesReady:false,selectReviewFrame:value=>frame=value};
  vm.runInNewContext(line,context);
  function send({interactive=false,...properties}={}){
    let prevented=false;
    handler({target:{closest:value=>{selector=value;return interactive;}},preventDefault:()=>prevented=true,...properties});
    return prevented;
  }
  assert.equal(send({code:'Space'}),false);assert.equal(played,0);
  context.reviewImagesReady=true;
  assert.equal(send({interactive:true,code:'Space'}),false);
  assert.match(selector,/(^|,)a(,|$)/);assert.match(selector,/textarea/);assert.match(selector,/contenteditable/);
  assert.equal(send({ctrlKey:true,key:'ArrowRight'}),false);
  assert.equal(send({defaultPrevented:true,key:'ArrowRight'}),false);
  assert.equal(played,0);assert.equal(frame,undefined);
  assert.equal(send({code:'Space'}),true);assert.equal(played,1);
  assert.equal(send({key:'ArrowRight'}),true);assert.equal(frame,3);
});
