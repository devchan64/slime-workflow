import test from 'node:test';
import assert from 'node:assert/strict';
import {effectAlignmentBoundsError as error,effectAlignmentBoundsIssue as issue} from '../../gui/effectAlignmentBounds.mjs';

test('대상과 모든 프레임의 범위·순서를 확인한다',()=>{
  const row=[0,0,1,1],value={target:row,frames:Array.from({length:8},()=>[...row])};
  assert.equal(error(value),'');
  assert.match(error({...value,target:[0,0,0,1]}),/대상 영역.*왼쪽/);
  assert.equal(issue({...value,target:[0,0,0,1]}).group,'target');
  const frames=value.frames.map(row=>[...row]);frames[2][0]='';
  assert.match(error({...value,frames}),/프레임 3.*왼쪽/);
  assert.equal(issue({...value,frames}).group,'frame:2');
  assert.match(error({...value,frames:frames.slice(0,7)}),/8개/);
  assert.match(error({...value,target:[0,0,1.1,1]}),/0~1/);
  assert.match(error({...value,target:[null,0,1,1]}),/0~1/);
  assert.match(error({...value,target:[false,0,1,1]}),/0~1/);
});

test('프레임 좌표가 저장 정밀도로 같아지면 오류를 확인한다',()=>{
  const row=[0.001,0,0.004,1],raw={target:[0,0,1,1],frames:Array.from({length:8},()=>[...row])};
  const rounded={...raw,frames:raw.frames.map(frame=>frame.map(value=>Math.round(value*100)/100))};
  assert.equal(error(raw),'');assert.match(error(rounded),/프레임 1.*왼쪽/);
});
