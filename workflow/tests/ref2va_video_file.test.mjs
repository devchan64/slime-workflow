import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validRef2vaVideoFile} from '../../gui/ref2vaVideoFile.mjs';

test('영상 파일은 크기와 형식을 확인하고 MIME이 없는 MP4 이름을 허용한다',()=>{
  assert.equal(validRef2vaVideoFile({name:'video.mp4',type:'video/mp4',size:1024}),true);
  assert.equal(validRef2vaVideoFile({name:'VIDEO.MP4',type:'',size:1024}),true);
  assert.equal(validRef2vaVideoFile({name:'image.png',type:'',size:1024}),false);
  assert.equal(validRef2vaVideoFile({name:'video.mp4',type:'image/png',size:1024}),false);
  assert.equal(validRef2vaVideoFile({name:'video.mp4',type:'video/mp4',size:0}),false);
  assert.equal(validRef2vaVideoFile({name:'video.mp4',type:'video/mp4',size:27*1024*1024+1}),false);
});
