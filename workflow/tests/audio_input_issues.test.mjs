import test from 'node:test';
import assert from 'node:assert/strict';
import {audioInputIssues} from '../../gui/audioInputIssues.mjs';
test('music review requires tags, lyrics and generation readiness',()=>{
 assert.deepEqual(audioInputIssues({prompt:'flute',lyrics:'[Verse]\nHome'},true,{ready:true}),[]);
 assert.match(audioInputIssues({prompt:'',lyrics:''},true,{ready:true}).join(' '),/태그.*가사/);
 assert.match(audioInputIssues({prompt:'flute',lyrics:'verse'},true,{ready:true,generation_ready:false}).join(' '),/모델 준비/);
 assert.match(audioInputIssues({prompt:', ,',lyrics:'verse'},true,{ready:true}).join(' '),/태그/);
 assert.match(audioInputIssues({prompt:'',lyrics:''},false,null).join(' '),/효과음/);
});
