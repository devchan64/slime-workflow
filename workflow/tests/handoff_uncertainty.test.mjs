import test from 'node:test';
import assert from 'node:assert/strict';
import {handoffUncertaintyKey,readHandoffUncertainty,markHandoffUncertainty,clearHandoffUncertainty} from '../../gui/handoffUncertainty.mjs';

test('불확실한 양도 변경은 같은 탭에서 다시 열어도 확인 전까지 유지된다',()=>{
  const values=new Map(),storage={getItem:key=>values.get(key) ?? null,setItem:(key,value)=>values.set(key,value),removeItem:key=>values.delete(key)};
  const key=handoffUncertaintyKey('session','request','service');
  assert.deepEqual(readHandoffUncertainty(storage,key),{uncertain:false,available:true});
  assert.equal(markHandoffUncertainty(storage,key),true);
  assert.deepEqual(readHandoffUncertainty(storage,key),{uncertain:true,available:true});
  assert.equal(readHandoffUncertainty(storage,handoffUncertaintyKey('other','request','service')).uncertain,false);
  assert.equal(clearHandoffUncertainty(storage,key),true);
  assert.equal(readHandoffUncertainty(storage,key).uncertain,false);
});

test('저장소가 없으면 변경 요청을 허용하지 않는다',()=>{
  const storage={getItem(){throw Error();},setItem(){throw Error();},removeItem(){throw Error();}};
  assert.deepEqual(readHandoffUncertainty(storage,'key'),{uncertain:true,available:false});
  assert.equal(markHandoffUncertainty(storage,'key'),false);
  assert.equal(clearHandoffUncertainty(storage,'key'),false);
});
