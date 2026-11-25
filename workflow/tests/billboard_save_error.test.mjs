import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('빌보드 저장 결과가 불명확하면 검토와 접수 ID를 유지하고 확인을 안내한다',async()=>{
  const source=readFileSync(new URL('../../gui/BillboardProperties.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  async function save(){'),end=source.indexOf('  const hasEdits=',start);
  assert.ok(start>=0 && end>start);
  for(const problem of [null,new Error('')]){
    let notice='',busy=false,reviewCleared=false;
    const context=vm.createContext({requestErrorMessage,document:{activeElement:null},saveButton:{current:null},restoreSaveFocus:{current:false},saving:{current:false},review:{id:'fixture-request',draft:{},result:{}},
      managementCommand:async()=>{throw problem;},setBusy:value=>busy=value,setNotice:value=>notice=value,
      setReview:()=>{reviewCleared=true;},setSource:()=>{},setEdits:()=>{},onDirtyChange:()=>{}});
    vm.runInContext(source.slice(start,end)+'\nthis.save=save;',context);await context.save();
    assert.match(notice,/fixture-request/);assert.match(notice,/다시 저장하기 전에/);
    assert.equal(reviewCleared,false);assert.equal(busy,false);assert.equal(context.saving.current,false);
  }
});
