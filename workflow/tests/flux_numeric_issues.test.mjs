import test from 'node:test';
import assert from 'node:assert/strict';
import {fluxNumericIssues} from '../../gui/fluxNumericIssues.mjs';

test('FLUX 크기·시드와 캐릭터 스텝의 경계를 검증한다',()=>{
 const valid={width:256,height:1664,steps:16,seed:0};
 assert.deepEqual(Object.values(fluxNumericIssues(valid,'flux-image')).filter(Boolean),[]);
 const invalid=fluxNumericIssues({width:257,height:'',steps:51,seed:-1},'flux-character');
 assert.ok(Object.values(invalid).every(Boolean));
 assert.equal(fluxNumericIssues({...valid,width:2048,seed:'4294967295'},'flux-character').width,'');
 assert.notEqual(fluxNumericIssues({...valid,width:2048},'flux-image').width,'');
});
