import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('시트 내보내기 지연은 중복을 막고 시간 초과 후 재시도한다',async()=>{
 const source=readFileSync(new URL('../../gui/SpriteSheetEditor.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function exportSheet(event)'),source.indexOf('  async function save()',source.indexOf('  async function exportSheet(event)')));
 let timer,busy=false,error='',result=null,calls=0,slow=true;const rows=[{x:0,y:0,width:1,height:1,anchorX:0,anchorY:0}],button={},document={activeElement:button};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document,exportRequest:{current:null},exportFocus:{current:false},saving:{current:false},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setResult:value=>result=value,setError:value=>error=value,setReview:()=>{},rows,first:1,last:1,columns:1,fps:6,invalidOutputColumns:false,invalidSpriteFrameRange:()=>false,spriteFrameIssue:()=>false,sheetSizeIssues:[],gifSizeIssues:[],image:'png',bounds:null,frames:[{rect:{x:0,y:0,width:1,height:1}}],fields:['x','y','width','height','anchorX','anchorY'],managementCommand:()=>{calls++;return slow?new Promise(()=>{}):Promise.resolve({id:'result',image:'png',coordinates:{}});}});
 vm.runInContext(code,context);const event={preventDefault(){},currentTarget:{contains:value=>value===button},nativeEvent:{submitter:{value:''}}};const first=context.exportSheet(event);await context.exportSheet(event);assert.equal(calls,1);timer();await first;assert.match(error,/시간이 초과/);assert.equal(busy,false);slow=false;await context.exportSheet(event);assert.equal(result.id,'result');assert.equal(error,'');
});

test('원본 갱신 지연은 중복을 막고 결과 확인을 안내한다',async()=>{
 const source=readFileSync(new URL('../../gui/SpriteSheetEditor.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function save(){');
 const code=source.slice(start,source.indexOf('  return <form onSubmit={exportSheet}>',start));
 let timer,busy=false,error='',review={payload:{},bodyReference:null},calls=0,saved=0;
 const button={},controllerRef={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:button},reviewRef:{current:{contains:value=>value===button}},exportFocus:{current:false},saving:controllerRef,review,original:{path:'source.png',metadataSha256:'hash'},readBodyReference:()=>null,setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setError:value=>error=value,setReview:value=>review=value,onSaved:()=>saved++,managementCommand:()=>{calls++;return new Promise(()=>{});}});
 vm.runInContext(code,context);const first=context.save();await context.save();assert.equal(calls,1);timer();await first;assert.match(error,/원본과 갱신 기록을 확인/);assert.match(error,/시간이 초과/);assert.equal(busy,false);assert.equal(review,null);assert.equal(saved,0);assert.equal(controllerRef.current,null);assert.equal(context.exportFocus.current,true);
});
