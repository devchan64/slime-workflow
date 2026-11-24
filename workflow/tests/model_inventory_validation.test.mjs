import test from 'node:test';
import assert from 'node:assert/strict';
import {validModelInventory} from '../../gui/modelInventoryValidation.mjs';

test('모델 파일 목록의 크기와 부분 조회 표시가 일치해야 한다',()=>{
  const model={files:[{path:'model/a',bytes:2},{path:'model/b',bytes:5}],count:2,total_bytes:7,truncated:false,incomplete:false};
  assert.equal(validModelInventory(model),true);
  assert.equal(validModelInventory({...model,incomplete:true}),true);
  assert.equal(validModelInventory({...model,files:[model.files[0]],count:2,truncated:true}),true);
  assert.equal(validModelInventory({...model,files:[model.files[0]],count:2,truncated:false}),false);
  assert.equal(validModelInventory({...model,incomplete:undefined}),false);
  assert.equal(validModelInventory({...model,total_bytes:6}),false);
  assert.equal(validModelInventory({...model,files:[model.files[0],model.files[0]]}),false);
  assert.equal(validModelInventory({...model,files:[{path:'model/a',bytes:-1}],count:1}),false);
  assert.equal(validModelInventory({files:[],count:0,total_bytes:0,truncated:false,incomplete:true}),true);
});
