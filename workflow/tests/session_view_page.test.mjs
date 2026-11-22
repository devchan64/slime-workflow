import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validSessionViewPage} from '../../gui/sessionViewPage.mjs';
const session='a'.repeat(32),snapshot='b'.repeat(64);
const page={id:session,messages:[{text:'질문',job:{status:{status:'completed'},tool_activity:{events:[{type:'tool_use',name:'terminal'}]}}}],message_count:2,offset:1,next_offset:null,snapshot};
test('session view accepts a matching history page with tool activity',()=>{
  assert.equal(validSessionViewPage(page,session,{offset:1,snapshot},6),true);
  assert.equal(validSessionViewPage(page,session,{offset:1,snapshot:'c'.repeat(64)},6),false);
  assert.equal(validSessionViewPage(page,session,null,6),false);
  assert.equal(validSessionViewPage({...page,next_offset:2},session,{offset:1,snapshot},6),false);
});
test('empty sessions and saved forms do not require a job',()=>{
  const empty={id:session,messages:[],message_count:0,offset:0,next_offset:null,snapshot};
  assert.equal(validSessionViewPage(empty,session,null,6),true);
  assert.equal(validSessionViewPage({...empty,messages:[{text:'저장된 입력',form_id:'f'.repeat(32),job:null}],message_count:1},session,null,6),true);
});
test('session view rejects malformed messages and tool events',()=>{
  for(const messages of [[null],[{text:12}],[{text:'질문',job:{tool_activity:{events:[null]}}}],[{text:'질문',job:{tool_activity:{events:{}}}}],
    [{text:'질문',job:{tool_activity:{events:[{type:'tool_result',name:{}}]}}}],
    [{text:'질문',job:{tool_activity:{history_table:{title:'이력',summary:'1건',columns:['작업'],rows:[null]}}}}]])
    assert.equal(validSessionViewPage({...page,messages},session,{offset:1,snapshot},6),false);
});
