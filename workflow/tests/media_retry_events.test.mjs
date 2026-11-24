import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('비교 이미지와 오디오는 이전 요소의 오류를 무시한다',()=>{
 const source=readFileSync(new URL('../../gui/MediaJobResult.jsx',import.meta.url),'utf8');
 for(const [start,end,ref] of [['function ComparisonFigure','function SeamlessComparison','imageRef'],['function AudioTrack','export default function MediaJobResult','audioRef']]){
  const section=source.slice(source.indexOf(start),source.indexOf(end));
  const body=section.split('onError={event=>{')[1].split('}}/>')[0];
  const current={};let failed=0;
  const context=vm.createContext({[ref]:{current},restoreFocus:{current:false},document:{activeElement:current},setFailed:()=>failed++});
  vm.runInContext(`function error(event){${body}}`,context);
  context.error({currentTarget:{}});assert.equal(failed,0);assert.equal(context.restoreFocus.current,false);
  context.error({currentTarget:current});assert.equal(failed,1);assert.equal(context.restoreFocus.current,true);
 }
});

test('입력 포즈와 비교 영상은 현재 요소의 오류만 처리한다',()=>{
 const source=readFileSync(new URL('../../gui/MediaJobResult.jsx',import.meta.url),'utf8');
 const section=source.slice(source.indexOf('function SavedPoseVideo'),source.indexOf('export function MediaResultError'));
 const bodies=section.split('onError={event=>{').slice(1,3).map(value=>value.split('}}/>')[0]);
 for(const [body,ref,focus,setter] of [[bodies[0],'videoRef','restoreFocus','setFailed'],[bodies[1],'outputRef','restoreOutputFocus','setOutputFailed']]){
  const current={};let count=0;
  const context=vm.createContext({[ref]:{current},[focus]:{current:false},document:{activeElement:current},[setter]:()=>count++});
  vm.runInContext(`function error(event){${body}}`,context);
  context.error({currentTarget:{}});assert.equal(count,0);assert.equal(context[focus].current,false);
  context.error({currentTarget:current});assert.equal(count,1);assert.equal(context[focus].current,true);
 }
});

test('결과 이미지와 영상은 현재 요소의 오류만 표시한다',()=>{
 const source=readFileSync(new URL('../../gui/MediaJobResult.jsx',import.meta.url),'utf8');
 const section=source.slice(source.indexOf('  function renderResultImage('));
 const bodies=section.split('onError={event=>{').slice(1,3).map(value=>value.split('}}/>')[0]);
 for(const [body,ref,setter] of [[bodies[0],'imageRef','setImageError'],[bodies[1],'videoRef','setVideoError']]){
  const current={};let count=0;
  const context=vm.createContext({[ref]:{current},restoreImageFocus:{current:false},document:{activeElement:current},[setter]:()=>count++});
  vm.runInContext(`function error(event){${body}}`,context);
  context.error({currentTarget:{}});assert.equal(count,0);
  context.error({currentTarget:current});assert.equal(count,1);
 }
});
