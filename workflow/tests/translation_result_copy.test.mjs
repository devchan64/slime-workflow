import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../../gui/TranslationResult.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('  async function copy() {'),source.indexOf('  return <section className="translation-result"'));
test('번역문 복사는 최신 입력을 사용하고 복사 중 수정된 내용을 구분한다',async()=>{
 let resolve,copied,notice;const context=vm.createContext({copySequence:{current:0},draftRef:{current:'최신'},writeClipboardText:value=>(copied=value,new Promise(done=>resolve=done)),setNotice:value=>notice=value});
 vm.runInContext(code+'\nthis.copy=copy;',context);const promise=context.copy();assert.equal(copied,'최신');context.draftRef.current='변경';resolve();await promise;assert.match(notice,/이전 번역문/);
});
test('번역문 복사 실패는 잠긴 입력을 건드리지 않고 오류를 안내한다',async()=>{
 let focused=0,notice,settings;const body={},button={},document={body,activeElement:button};
 const context=vm.createContext({document,copySequence:{current:0},draftRef:{current:'원문'},copyRef:{current:button},textRef:{current:{isConnected:true,matches:()=>true,focus:()=>focused++,select:()=>{}}},writeClipboardText:async()=>{throw Error();},setNotice:(value,options)=>{notice=value;settings=options;}});
 vm.runInContext(code+'\nthis.copy=copy;',context);await context.copy();assert.equal(focused,0);assert.match(notice,/복사 단축키/);assert.equal(settings.error,true);
});
