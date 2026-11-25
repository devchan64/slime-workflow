import test from 'node:test';
import assert from 'node:assert/strict';
import {audioInputIssues} from '../../gui/audioInputIssues.mjs';
test('music review requires tags, lyrics and generation readiness',()=>{
 assert.deepEqual(audioInputIssues({prompt:'flute',lyrics:'[Verse]\nHome',seed:42,duration_seconds:30},true,{ready:true}),[]);
 assert.match(audioInputIssues({prompt:'',lyrics:''},true,{ready:true}).join(' '),/태그.*가사/);
 assert.match(audioInputIssues({prompt:'flute',lyrics:'verse'},true,{ready:true,generation_ready:false}).join(' '),/모델 준비/);
 assert.match(audioInputIssues({prompt:', ,',lyrics:'verse'},true,{ready:true}).join(' '),/태그/);
 assert.match(audioInputIssues({prompt:'',lyrics:''},false,null).join(' '),/효과음/);
});
test('음악 출력 시간은 5~300초 범위를 검증한다',()=>{
 for(const duration_seconds of ['',4,301])assert.match(audioInputIssues({prompt:'piano',lyrics:'[Verse]',seed:0,duration_seconds},true,{ready:true}).join(' '),/출력 시간/);
 for(const duration_seconds of [5,'300',5.5])assert.deepEqual(audioInputIssues({prompt:'piano',lyrics:'[Verse]',seed:0,duration_seconds},true,{ready:true}),[]);
});
test('오디오 시드는 정수 범위와 빈 입력을 검증한다',()=>{
 for(const seed of ['',-1,1.5,4294967296])assert.match(audioInputIssues({prompt:'sound',seed},false,null).join(' '),/시드/);
 for(const seed of [0,'4294967295'])assert.deepEqual(audioInputIssues({prompt:'sound',seed},false,null),[]);
});
