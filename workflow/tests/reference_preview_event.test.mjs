import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {imageRetryUrl} from '../../gui/imageRetryUrl.mjs';

test('참조 미리보기는 이전 이미지의 오류를 무시한다',()=>{
 const source=readFileSync(new URL('../../gui/ReferenceImageInput.jsx',import.meta.url),'utf8');
 assert.match(source,/key=\{previewGeneration\.current\+":"\+previewRevision\}/);
 const body=source.split('onError={event=>{')[1].split('}}/>')[0];
 const current={};let failures=0;
 const context=vm.createContext({previewRef:{current},restorePreviewFocus:{current:false},document:{activeElement:current},setPreviewError:()=>failures++});
 vm.runInContext(`function error(event){${body}}`,context);
 context.error({currentTarget:{}});assert.equal(failures,0);assert.equal(context.restorePreviewFocus.current,false);
 context.error({currentTarget:current});assert.equal(failures,1);assert.equal(context.restorePreviewFocus.current,true);
});

test('참조 미리보기 재시도는 원격 주소만 갱신한다',()=>{
 const source=readFileSync(new URL('../../gui/ReferenceImageInput.jsx',import.meta.url),'utf8');
 assert.match(source,/src=\{previewRevision \? imageRetryUrl\(preview,previewRevision\) : preview\}/);
 assert.equal(imageRetryUrl('/image.png?version=1#view',2),'/image.png?version=1&retry=2#view');
 assert.equal(imageRetryUrl('blob:local-image',2),'blob:local-image');
 assert.equal(imageRetryUrl('data:image/png;base64,abc',2),'data:image/png;base64,abc');
});

test('새 참조 이미지는 이전 미리보기의 재시도 횟수를 물려받지 않는다',()=>{
 const text=readFileSync(new URL('../../gui/ReferenceImageInput.jsx',import.meta.url),'utf8');
 const start=text.indexOf('  useEffect(()=>{\n    requestRef.current+=1;');
 const effect=text.slice(start,text.indexOf('  },[source]);',start)+'  },[source]);'.length);
 let revision=5,preview='';
 const context=vm.createContext({useEffect:fn=>fn(),requestRef:{current:0},previewGeneration:{current:4},updateChecking:()=>{},setError:()=>{},setPreviewError:()=>{},
  retryPreview:value=>revision=value,restoreFocus:{current:false},source:'/new-image.png',setPreview:value=>preview=value});
 vm.runInContext(effect,context);
 assert.equal(revision,0);assert.equal(preview,'/new-image.png');assert.equal(context.previewGeneration.current,5);
});

test('VACE 입력 잠금 중에는 참조 이미지 드롭이 선택을 시작하지 않는다',async()=>{
 const page=readFileSync(new URL('../../gui/VacePage.jsx',import.meta.url),'utf8');
 assert.match(page,/<ReferenceImageInput disabled=\{busy \|\| !!pending \|\| Boolean\(handoff\.id\) \|\| !visible\}/);
 const source=readFileSync(new URL('../../gui/ReferenceImageInput.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function select(file){'),source.indexOf('  async function paste(){'));
 let started=0;
 const context=vm.createContext({disabledRef:{current:true},onSelectionStart:()=>started++});
 vm.runInContext(code,context);
 await context.select({name:'image.png'});
 assert.equal(started,0);
});

test('생성기 입력 잠금은 참조 이미지 드롭에도 전달된다',()=>{
 const read=name=>readFileSync(new URL('../../gui/'+name,import.meta.url),'utf8');
 assert.match(read('DwposePage.jsx'),/disabled=\{busy \|\| Boolean\(pending\) \|\| Boolean\(handoff\.id\)\}/);
 assert.match(read('FluxImagePage.jsx'),/source=\{files\[index\]\} disabled=\{!profile \|\| busy \|\| Boolean\(review\) \|\| Boolean\(handoffId\) \|\| \(receiptKey && receiptState!=="editing"\)/);
 assert.match(read('AnimateInputs.jsx'),/source=\{reference\} disabled=\{busy \|\| Boolean\(pending\)\}/);
 assert.match(read('FunControlPage.jsx'),/sourceSeed=\{sourceSeed\} busy=\{busy \|\| !!pending \|\| Boolean\(handoffId\)\}/);
 assert.match(read('FunControlSchema.jsx'),/<ReferenceImageInput disabled=\{c\.busy\}/);
});

test('검증 중 입력이 잠기면 나중에 잠금이 풀려도 이전 선택은 적용되지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/ReferenceImageInput.jsx',import.meta.url),'utf8');
 const select=source.slice(source.indexOf('  async function select(file){'),source.indexOf('  async function paste(){'));
 const lock=source.match(/useEffect\(\(\)=>\{if\(disabled\)\{requestRef\.current\+=1;.*?\}\},\[disabled\]\);/)[0];
 let resolve,applied=0,checking=false;
 const context=vm.createContext({disabledRef:{current:false},disabled:true,requestRef:{current:0},restorePasteFocus:{current:true},restoreFileFocus:{current:true},
  onSelectionStart:()=>{},referenceImageError:()=>'',accept:'image/png',maxBytes:null,document:{activeElement:null},input:{current:{}},
  setError:()=>{},updateChecking:value=>checking=value,verifyImage:()=>new Promise(done=>resolve=done),validate:null,onChange:()=>applied++,useEffect:fn=>fn()});
 vm.runInContext(select,context);
 const pending=context.select({name:'image.png'});assert.equal(checking,true);
 context.disabledRef.current=true;vm.runInContext(lock,context);assert.equal(checking,false);
 context.disabledRef.current=false;resolve();await pending;
 assert.equal(applied,0);assert.equal(context.restorePasteFocus.current,false);assert.equal(context.restoreFileFocus.current,false);
});

test('클립보드 읽기 중 입력이 잠기면 늦은 이미지가 선택되지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/ReferenceImageInput.jsx',import.meta.url),'utf8');
 const paste=source.slice(source.indexOf('  async function paste(){'),source.indexOf('  return <div role="group"'));
 const lock=source.match(/useEffect\(\(\)=>\{if\(disabled\)\{requestRef\.current\+=1;.*?\}\},\[disabled\]\);/)[0];
 let resolve,selected=0,checking=false;
 const context=vm.createContext({disabledRef:{current:false},disabled:true,requestRef:{current:0},restorePasteFocus:{current:false},restoreFileFocus:{current:false},
  document:{activeElement:null},pasteButton:{current:{}},onSelectionStart:()=>{},setError:()=>{},updateChecking:value=>checking=value,
  navigator:{clipboard:{read:()=>new Promise(done=>resolve=done)}},withinTime:value=>value,accept:'image/png',select:()=>selected++,useEffect:fn=>fn(),File:class {}});
 vm.runInContext(paste,context);
 const pending=context.paste();assert.equal(checking,true);
 context.disabledRef.current=true;vm.runInContext(lock,context);context.disabledRef.current=false;
 resolve([{types:['image/png'],getType:async()=>({})}]);await pending;
 assert.equal(selected,0);assert.equal(checking,false);
});
