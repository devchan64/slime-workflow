import test from "node:test";
import assert from "node:assert/strict";
import {observeLiveVisibility} from "../../gui/observeLiveVisibility.mjs";
import {readFileSync} from "node:fs";
import vm from "node:vm";

test('예약된 자동 갱신은 꺼짐·비가시·비활성·숨긴 탭 상태를 실행 직전에 확인한다',()=>{
  const source=readFileSync(new URL('../../gui/LiveRefresh.jsx',import.meta.url),'utf8');
  const effect=source.slice(source.indexOf('  useEffect(()=>{\n    if(!enabled || !visible || !active)'),source.indexOf('  return {ref,enabled'));
  let tick,stop,calls=0;const enabledRef={current:true},visibleRef={current:true},activeRef={current:true},document={visibilityState:'visible'};
  const context=vm.createContext({useEffect:fn=>stop=fn(),enabled:true,visible:true,active:true,enabledRef,visibleRef,activeRef,document,callback:{current:()=>calls++},LIVE_REFRESH_MS:30000,setInterval:fn=>(tick=fn,1),clearInterval:()=>{}});
  vm.runInContext(effect,context);tick();assert.equal(calls,1);
  for(const ref of [enabledRef,visibleRef,activeRef]){ref.current=false;tick();assert.equal(calls,1);ref.current=true;}
  document.visibilityState='hidden';tick();assert.equal(calls,1);document.visibilityState='visible';stop();tick();assert.equal(calls,1);
});

test('자동 갱신 설정과 가시성 관찰은 렌더 전에도 실행 상태를 갱신한다',()=>{
  const source=readFileSync(new URL('../../gui/LiveRefresh.jsx',import.meta.url),'utf8');
  const setter=source.slice(source.indexOf('  const setEnabled=useCallback'),source.indexOf('  const ref=useCallback'));
  const visibility=source.slice(source.indexOf('  useEffect(()=>{\n    visibleRef.current=false;'),source.indexOf('  useEffect(()=>{\n    if(!enabled'));
  let enabledState=true,visibleState=false,notify;const enabledRef={current:true},visibleRef={current:false};
  const context=vm.createContext({useCallback:fn=>fn,enabledRef,setEnabledState:value=>enabledState=value,useEffect:fn=>fn(),visibleRef,setVisible:value=>visibleState=value,element:{},document:{},window:{},globalThis:{IntersectionObserver:null},observeLiveVisibility:(_element,callback)=>notify=callback});
  vm.runInContext(setter+'\n globalThis.setForTest=setEnabled;',context);context.globalThis.setForTest(false);assert.equal(enabledRef.current,false);assert.equal(enabledState,false);
  vm.runInContext(visibility,context);notify(true);assert.equal(visibleRef.current,true);assert.equal(visibleState,true);notify(false);assert.equal(visibleRef.current,false);assert.equal(visibleState,false);
});

test("관찰 기능이 없으면 화면 위치와 탭 상태를 추적하고 종료 후 해제한다",()=>{
  const doc=new EventTarget(),view=new EventTarget(),observed=[];
  doc.visibilityState="visible";view.innerWidth=360;view.innerHeight=640;
  let top=20;
  const element={getBoundingClientRect:()=>({top,bottom:top+20,left:0,right:20})};
  const stop=observeLiveVisibility(element,value=>observed.push(value),{document:doc,window:view});
  assert.equal(observed.at(-1),true);
  top=700;view.dispatchEvent(new Event("scroll"));assert.equal(observed.at(-1),false);
  top=10;view.dispatchEvent(new Event("resize"));assert.equal(observed.at(-1),true);
  doc.visibilityState="hidden";doc.dispatchEvent(new Event("visibilitychange"));assert.equal(observed.at(-1),false);
  stop();const count=observed.length;view.dispatchEvent(new Event("scroll"));doc.dispatchEvent(new Event("visibilitychange"));assert.equal(observed.length,count);
});

test("대체 판정은 중첩 스크롤 영역에 가려진 항목을 갱신하지 않는다",()=>{
  const doc=new EventTarget(),view=new EventTarget(),observed=[];
  doc.visibilityState="visible";view.innerWidth=360;view.innerHeight=640;
  view.getComputedStyle=node=>node.style;
  const parent={style:{overflowX:"visible",overflowY:"auto"},getBoundingClientRect:()=>({left:0,right:360,top:100,bottom:200})};
  let top=250;
  const element={parentElement:parent,getBoundingClientRect:()=>({left:0,right:20,top,bottom:top+20})};
  const stop=observeLiveVisibility(element,value=>observed.push(value),{document:doc,window:view});
  assert.equal(observed.at(-1),false);
  top=190;view.dispatchEvent(new Event("scroll"));assert.equal(observed.at(-1),true);
  top=200;view.dispatchEvent(new Event("scroll"));assert.equal(observed.at(-1),false);
  stop();
});
