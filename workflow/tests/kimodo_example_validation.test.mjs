import test from 'node:test';
import assert from 'node:assert/strict';
import {validKimodoExample,validKimodoExampleList} from '../../gui/kimodoExampleValidation.mjs';

test('예시의 참조·구간·키프레임 형식을 확인한다',()=>{
  const example={label:'걷기',prompt:'walk',frames:30,settings:{},references:[{name:'a.png',data:'YQ=='}]};
  assert.equal(validKimodoExample(example),true);
  for(const value of [{...example,references:[{}]},{...example,frames:'30'},{...example,frames:29},{...example,frames:301},{...example,settings:{directions:{}}},{...example,settings:{directions:null}},{...example,settings:{directions:['front','front']}},{...example,settings:{segment_frames:[{}]}},{...example,settings:{segment_frames:[16,16]}},{...example,settings:{keyframes:[{id:'bad',frame:1}]}}])
    assert.equal(validKimodoExample(value),false);
  assert.equal(validKimodoExample({...example,prompt:'walk\nstop',frames:32,settings:{directions:['front'],segment_frames:[16,16]}}),true);
  for(const settings of [{steps:{}},{steps:1},{seed:2147483648},{guidance_scale:Infinity},{heading_degrees:181},{openpose_scale_percent:9},{post_processing:'false'},{pose_include_hands:null},{camera_elevation_degrees:45}])
    assert.equal(validKimodoExample({...example,settings}),false);
  assert.equal(validKimodoExample({...example,settings:{steps:2,seed:0,guidance_scale:0,heading_degrees:-180,openpose_scale_percent:10,post_processing:false,camera_elevation_degrees:15}}),true);
});

test('예시 목록은 빈 목록을 허용하고 중복·손상된 표시 필드를 거부한다',()=>{
  const row={id:'walk',label:'걷기',prompt:'walk'};
  assert.equal(validKimodoExampleList([]),true);
  assert.equal(validKimodoExampleList([row]),true);
  for(const rows of [null,[row,row],[{...row,prompt:{}}],[{...row,id:''}]])assert.equal(validKimodoExampleList(rows),false);
});
