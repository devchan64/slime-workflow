import {test} from "node:test";
import assert from "node:assert/strict";
import {drawAlignment} from "../../gui/drawAlignment.js";
import {readFileSync} from "node:fs";
import vm from "node:vm";

test("정렬 저장 오류는 버튼에 남은 초점만 오류 안내로 옮긴다",()=>{
  const source=readFileSync(new URL('../../gui/EffectEditor.jsx',import.meta.url),'utf8');
  const effect=source.split('\n').find(line=>line.includes('if(inputError && restoreInputFocus.current)'));
  for(const where of ['button','body','other']){
    const body={},button={},other={};let focused=0;
    const context=vm.createContext({inputError:{message:'오류'},restoreInputFocus:{current:true},saveButton:{current:button},inputErrorRef:{current:{focus:()=>focused++}},document:{body,activeElement:{button,body,other}[where]},useEffect:fn=>fn()});
    vm.runInContext(effect,context);assert.equal(focused,where==='other'?0:1);assert.equal(context.restoreInputFocus.current,false);
  }
});

test("좌표 검증 실패는 이전 성공 안내만 지우고 저장 결과 미확인 경고는 보존한다",async()=>{
  const source=readFileSync(new URL('../../gui/EffectEditor.jsx',import.meta.url),'utf8');
  const code=source.slice(source.indexOf('  async function save(event){',source.indexOf('export function Alignment(')),source.indexOf('  const alphaInvalid=',source.indexOf('export function Alignment(')));
  for(const saveError of [false,true]){
    let message='이전 저장 안내',error=null,calls=0;const button={};
    const context=vm.createContext({values:{target:[0,0,1,1],frames:[],alpha:1},submitting:{current:false},saveError,setMessage:value=>message=value,restoreInputFocus:{current:false},saveButton:{current:button},document:{activeElement:button},setInputError:value=>error=value,effectAlignmentBoundsIssue:()=>({group:null,message:'좌표 오류'}),managementCommand:()=>calls++});
    vm.runInContext(code,context);await context.save({preventDefault(){}});
    assert.equal(message,saveError?'이전 저장 안내':'');assert.match(error.message,/저장하지 않았습니다/);assert.equal(calls,0);
  }
});

test("정렬 재생은 실제로 표시한 프레임을 캔버스에 기록한다",async()=>{
  const originalImage=globalThis.Image,originalRaf=globalThis.requestAnimationFrame;
  let nextFrame;
  globalThis.Image=class {width=400;height=200;set src(value){queueMicrotask(()=>this.onload());}};
  globalThis.requestAnimationFrame=callback=>{nextFrame=callback;return 1;};
  const ctx={clearRect(){},fillRect(){},drawImage(){},strokeRect(){},fillText(){}};
  const canvas={isConnected:true,getContext:()=>ctx};
  const renderer=`data:text/javascript,${encodeURIComponent("export const calculateEffectFramePlacement=()=>({left:0,top:0,width:1,height:1});export const sampleEffectAnimationFrame=()=>3;export const sampleMothAnimationFrame=()=>null;export const sampleFogAnimationFrame=()=>null;")}`;
  const detail={rendererModule:renderer,sheetImage:"sheet",document:{renderer:"effect",alignment:{texture:"effect"}}};
  const values={target:[0,0,1,1],frames:Array.from({length:8},()=>[0,0,1,1]),alpha:1};
  try{
    await drawAlignment(canvas,detail,values,true,0,false,false);
    nextFrame(performance.now());
    assert.equal(canvas.effectDisplayedFrame,3);
    canvas.effectPreviewRevision++;
  }finally{globalThis.Image=originalImage;globalThis.requestAnimationFrame=originalRaf;}
});
