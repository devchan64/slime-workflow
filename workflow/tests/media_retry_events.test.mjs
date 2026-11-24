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
  const context=vm.createContext({[ref]:{current},restoreImageFocus:{current:false},restoreVideoFocus:{current:false},document:{activeElement:current},[setter]:()=>count++});
  vm.runInContext(`function error(event){${body}}`,context);
  context.error({currentTarget:{}});assert.equal(count,0);
  context.error({currentTarget:current});assert.equal(count,1);
  assert.equal(context[ref==='videoRef'?'restoreVideoFocus':'restoreImageFocus'].current,true);
 }
});

test('결과 영상 오류와 재시도 후 잃어버린 초점만 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/MediaJobResult.jsx',import.meta.url),'utf8');
 const section=source.slice(source.indexOf('function MediaJobResultForSelection'));
 const effect=section.match(/useEffect\(\(\)=>\{if\(restoreVideoFocus\.current\).*?\},\[videoError,mediaRevision\]\);/)[0];
 for(const failed of [true,false])for(const moved of [true,false]){
  let focused='';const body={},other={};
  const context=vm.createContext({useEffect:fn=>fn(),restoreVideoFocus:{current:true},videoError:failed,mediaRevision:1,
   document:{body,activeElement:moved?other:body},videoRetryRef:{current:{focus:()=>focused='retry'}},videoRef:{current:{focus:()=>focused='video'}}});
  vm.runInContext(effect,context);
  assert.equal(focused,moved?'':failed?'retry':'video');
  assert.equal(context.restoreVideoFocus.current,false);
 }
});
