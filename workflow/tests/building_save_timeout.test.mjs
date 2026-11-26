import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('건물 속성 저장 지연은 중복을 막고 실제 속성 확인을 안내한다',async()=>{
 const source=readFileSync(new URL('../../gui/BuildingEditor.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function save(event){',source.indexOf('export function BuildingProperties'));
 const code=source.slice(start,source.indexOf('  return <form className="building-properties-form"',start));
 let timer,busy=false,error='',calls=0,saved=0,uncertain='';const button={},saving={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:button},saveButton:{current:button},restoreSaveFocus:{current:false},saving,changed:true,busy:false,fieldIssues:{},sizeError:'',values:{shadowShape:'circle'},fields:[],building:{texture:'building'},generation:1,expected:{},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setError:value=>error=value,onSaveUncertain:value=>uncertain=value,onSaved:()=>saved++,managementCommand:()=>{calls++;return new Promise(()=>{});}});
 vm.runInContext(code,context);const event={preventDefault(){}};const first=context.save(event);await context.save(event);assert.equal(calls,1);timer();await first;assert.equal(busy,false);assert.equal(saved,0);assert.equal(uncertain,'building');assert.equal(saving.current,null);assert.equal(context.restoreSaveFocus.current,true);assert.match(error,/실제 속성을 확인/);assert.match(error,/응답 시간이 초과/);
});

test('건물 편집 화면 종료 후 늦은 저장 응답은 완료 처리를 하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/BuildingEditor.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function save(event){',source.indexOf('export function BuildingProperties'));
 const code=source.slice(start,source.indexOf('  return <form className="building-properties-form"',start));
 let resolve,saved=0,error='';const saving={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:null},saveButton:{current:null},restoreSaveFocus:{current:false},saving,changed:true,busy:false,fieldIssues:{},sizeError:'',values:{shadowShape:'circle'},fields:[],building:{texture:'building'},generation:1,expected:{},setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setError:value=>error=value,onSaved:()=>saved++,managementCommand:()=>new Promise(done=>resolve=done)});
 vm.runInContext(code,context);const running=context.save({preventDefault(){}});const request=saving.current;saving.current=null;request.abort();resolve({});await running;assert.equal(saved,0);assert.equal(error,'');
});
