import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {startImageLoadDeadline} from '../../gui/imageLoadDeadline.mjs';

test('이미지 완료 이벤트는 렌더 정리 전에 시간 제한을 취소한다',()=>{
 const source=readFileSync(new URL('../../gui/RecoverableImage.jsx',import.meta.url),'utf8');
 const load=source.split('onLoad={event=>{')[1].split('}} onError=')[0];
 const error=source.split('onError={event=>{')[1].split('}}/>')[0];
 for(const [body,expected] of [[load,'loaded'],[error,'failed']]){
  let timer,failed=0,loaded=0,failureKind='';
  const cancel=startImageLoadDeadline(()=>failed++,{setTimeout:fn=>(timer=fn),clearTimeout:()=>{}});
  const focused={},context=vm.createContext({cancelDeadline:{current:cancel},image:{current:focused},restoreFocus:{current:false},document:{activeElement:focused},setLoaded:()=>loaded++,setFailed:value=>{failed++;failureKind=value;}});
  vm.runInContext(`function handle(event){${body}}`,context);
  context.handle({currentTarget:{}});assert.equal(loaded,0);assert.equal(failed,0);
  context.handle({currentTarget:focused});timer();
  assert.equal(loaded,expected==='loaded'?1:0);
  assert.equal(failed,expected==='failed'?1:0);
  if(expected==='failed')assert.equal(failureKind,'error');
  assert.equal(context.restoreFocus.current,expected==='failed');
 }
});

test('이미지 제한 시간 초과는 로드 오류와 구분된다',()=>{
 const source=readFileSync(new URL('../../gui/RecoverableImage.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    if(loaded || failed)return;'),end=source.indexOf('  },[loaded,failed,revision,src]);',start)+'  },[loaded,failed,revision,src]);'.length;
 let timeout,kind='';const context=vm.createContext({loaded:false,failed:false,revision:0,src:'image',image:{current:{}},document:{activeElement:null},restoreFocus:{current:false},cancelDeadline:{current:null},useEffect:fn=>fn(),startImageLoadDeadline:fn=>{timeout=fn;return ()=>{};},setFailed:value=>kind=value});
 vm.runInContext(source.slice(start,end),context);timeout();assert.equal(kind,'timeout');
});
