import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

const source=readFileSync(new URL('../../gui/WriterPage.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('  async function search(){'),source.indexOf('  const jobs='));
function fixture(command,initial='기존'){
 let selected=initial,notice,settings,matches,busy=false;
 const trigger={},button={},body={};
 const context=vm.createContext({AbortController,setTimeout,clearTimeout,untilAborted,document:{body,activeElement:button},restoreSearchFocus:{current:null},searchButton:{current:button},searchInput:{current:{}},searchRequest:{current:null},selectionEpoch:{current:0},resultTrigger:{current:trigger},selected:initial,query:'새 검색',matches:[{id:'기존'}],recent:null,setBusy:value=>busy=value,select:value=>selected=value,setMatches:value=>matches=value,setSearchedQuery:()=>{},setNotice:(value,options)=>{notice=value;settings=options;},managementCommand:command,requestErrorMessage:error=>error.message});
 vm.runInContext(code+'\nthis.search=search;',context);return {context,trigger,selected:()=>selected,notice:()=>notice,settings:()=>settings,matches:()=>matches,busy:()=>busy};
}
test('작가 이력 검색 실패는 기존 결과와 목록을 보존하고 오류를 안내한다',async()=>{
 const f=fixture(async()=>{throw Error('연결 실패');});await f.context.search();
 assert.equal(f.selected(),'기존');assert.equal(f.context.resultTrigger.current,f.trigger);assert.equal(f.matches(),undefined);assert.match(f.notice(),/마지막으로 확인한 검색 결과/);assert.equal(f.settings().error,true);assert.equal(f.busy(),false);
});
test('빈 검색 결과가 있는 상태에서 실패하면 이전 결과가 0건이었다고 안내한다',async()=>{
 const f=fixture(async()=>{throw Error('연결 실패');});f.context.matches=[];await f.context.search();
 assert.match(f.notice(),/마지막 검색 결과는 0건/);assert.doesNotMatch(f.notice(),/아래에는/);assert.equal(f.settings().error,true);assert.equal(f.busy(),false);
});
test('검색 중 새 작업을 선택하면 늦은 검색 응답이 선택과 안내를 덮지 않는다',async()=>{
 let resolve;const f=fixture(()=>new Promise(done=>resolve=done)),pending=f.context.search();
 f.context.selectionEpoch.current++;f.context.select('새 작업');
 resolve({jobs:[{id:'새 검색',mode:'write',stage:'done'}],count:1});await pending;
 assert.equal(f.selected(),'새 작업');assert.equal(f.context.resultTrigger.current,f.trigger);assert.equal(f.matches(),undefined);assert.equal(f.notice(),undefined);assert.equal(f.busy(),false);
});
test('작가 이력 검색 성공은 열린 결과를 유지하며 새 목록으로 전환한다',async()=>{
 const jobs=[{id:'새 검색',mode:'write',stage:'done'}],f=fixture(async()=>({jobs,count:1}));await f.context.search();
 assert.equal(f.selected(),'기존');assert.equal(f.context.resultTrigger.current,f.trigger);assert.equal(f.matches(),jobs);assert.equal(f.notice(),'');assert.equal(f.busy(),false);
});
test('열린 결과가 없으면 ID로 정확히 찾은 작업을 연다',async()=>{
 const jobs=[{id:'새 검색',mode:'write',stage:'done'}],f=fixture(async()=>({jobs,count:1}),'');await f.context.search();
 assert.equal(f.selected(),'새 검색');assert.equal(f.context.resultTrigger.current,null);assert.equal(f.matches(),jobs);assert.equal(f.notice(),'');assert.equal(f.busy(),false);
});
