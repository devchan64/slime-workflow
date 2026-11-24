import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('Kimodo 영상 선택은 작업별로 분리되고 사라진 선택은 원본으로 대체된다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoMedia.jsx',import.meta.url),'utf8');
 assert.match(source,/key=\{JSON\.stringify\(\[id,job\.attempt\]\)\}/);
 const line=source.match(/const currentVideo=videos\.some.*?;/)[0];
 for(const [selected,expected] of [['comparison','comparison'],['removed','original']]){
  const context=vm.createContext({videos:[['원본','original'],['비교','comparison']],selected,job:{video:'original'}});
  assert.equal(vm.runInContext(line+' currentVideo;',context),expected);
 }
});

test('이전 Kimodo 영상의 오류는 현재 영상에 표시되지 않는다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoMedia.jsx',import.meta.url),'utf8');
 const body=source.split('onError={event=>{')[1].split('}}/>')[0];
 const current={};let error=false;
 const context=vm.createContext({videoRef:{current},restoreFocus:{current:false},document:{activeElement:current},setError:value=>error=value});
 vm.runInContext(`function fail(event){${body}}`,context);
 context.fail({currentTarget:{}});assert.equal(error,false);
 context.fail({currentTarget:current});assert.equal(error,true);assert.equal(context.restoreFocus.current,true);
});

test('사라진 영상 선택은 원본으로 갱신해 이전 선택이 자동 복귀하지 않는다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoMedia.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(selected!==currentVideo\)\{.*?\}\},\[selected,currentVideo\]\);/)[0];
 let next='',notice='';const context=vm.createContext({useEffect:fn=>fn(),selected:'removed',currentVideo:'original',select:value=>next=value,setSelectionNotice:value=>notice=value});
 vm.runInContext(effect,context);assert.equal(next,'original');assert.match(notice,/원본 모션/);
});

test('Kimodo 영상 재시도는 사라진 초점만 버튼 또는 영상으로 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoMedia.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(restoreFocus\.current\).*?\},\[error,revision\]\);/)[0];
 for(const failed of [true,false])for(const moved of [true,false]){
  const body={},other={};let focus='';
  const context=vm.createContext({useEffect:fn=>fn(),restoreFocus:{current:true},error:failed,revision:1,
   document:{body,activeElement:moved?other:body},retryRef:{current:{focus:()=>focus='retry'}},videoRef:{current:{focus:()=>focus='video'}}});
  vm.runInContext(effect,context);
  assert.equal(focus,moved?'':failed?'retry':'video');assert.equal(context.restoreFocus.current,false);
 }
});

test('중복 또는 잘못된 Kimodo 영상은 제외하고 정상 영상은 유지한다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoMedia.jsx',import.meta.url),'utf8');
 const section=source.slice(source.indexOf('  const videos=[['),source.indexOf('  const currentVideo='));
 const base='/kimodo/jobs/job/attempts/attempt/';
 const job={video:base+'preview.mp4',preprocess_videos:{'정상':base+'pose.mp4','중복':base+'pose.mp4',' ':base+'other.mp4','잘못된 경로':'/other.mp4'}};
 const context=vm.createContext({job,base});
 const result=vm.runInContext(section+' JSON.stringify({videos,invalidVideos});',context);
 const parsed=JSON.parse(result);assert.equal(parsed.invalidVideos,true);
 assert.deepEqual(parsed.videos,[['원본 모션',job.video],['정상',base+'pose.mp4']]);
});

test('Kimodo 서버가 생성하는 방향별 영상은 모두 선택할 수 있다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoMedia.jsx',import.meta.url),'utf8');
 const section=source.slice(source.indexOf('  const videos=[['),source.indexOf('  const currentVideo='));
 const base='/kimodo/jobs/job/attempts/attempt/';
 const job={video:base+'preview.mp4',comparison_video:base+'comparison.mp4',preprocess_videos:{
  'SOMA 렌더 · front_left':base+'soma-render-front_left.mp4',
  '직접 포즈 · front_left':base+'soma-direct-front_left.mp4',
  'DWPose 포즈 · front_left':base+'dwpose-front_left.mp4'}};
 const parsed=JSON.parse(vm.runInContext(section+' JSON.stringify({videos,invalidVideos});',vm.createContext({job,base})));
 assert.equal(parsed.invalidVideos,false);assert.equal(parsed.videos.length,5);
 assert.deepEqual(parsed.videos.slice(2).map(([,path])=>path),Object.values(job.preprocess_videos));
});
