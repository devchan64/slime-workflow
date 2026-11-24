import test from 'node:test';
import assert from 'node:assert/strict';
import {readLocalImageBase64} from '../../gui/readLocalImage.mjs';

test('로컬 이미지 읽기 성공과 잘못된 결과를 구분한다',async()=>{
  let reader;
  class Reader {constructor(){reader=this;}readAsDataURL(file){this.file=file;}}
  const file={name:'image.png'},pending=readLocalImageBase64(file,{Reader});
  assert.equal(reader.file,file);reader.result='data:image/png;base64,YWJj';reader.onload();
  assert.equal(await pending,'YWJj');
  const invalid=readLocalImageBase64(file,{Reader});reader.result=null;reader.onload();
  await assert.rejects(invalid,/이미지를 읽을 수 없습니다/);
});

test('읽기가 지연되면 중단하고 늦은 이벤트를 무시한다',async()=>{
  let reader,timer;
  class Reader {constructor(){reader=this;}readAsDataURL(){}abort(){this.aborted=true;}}
  const timers={setTimeout(fn,ms){timer={fn,ms};return timer;},clearTimeout(handle){handle.cleared=true;}};
  const pending=readLocalImageBase64({}, {Reader,timers});
  const late=reader.onload;assert.equal(timer.ms,30000);timer.fn();
  await assert.rejects(pending,/시간이 초과/);
  assert.equal(reader.aborted,true);assert.equal(timer.cleared,true);assert.equal(reader.onload,null);
  late();
});

test('화면 종료 신호가 파일 읽기를 중단한다',async()=>{
  let reader;
  class Reader {constructor(){reader=this;}readAsDataURL(){}abort(){this.aborted=true;}}
  const controller=new AbortController();
  const pending=readLocalImageBase64({}, {Reader,signal:controller.signal});
  controller.abort();await assert.rejects(pending,{name:'AbortError'});
  assert.equal(reader.aborted,true);assert.equal(reader.onload,null);
  await assert.rejects(readLocalImageBase64({}, {Reader,signal:controller.signal}),{name:'AbortError'});
});
