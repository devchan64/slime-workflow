import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

const source=readFileSync(new URL('../../gui/OperationsJobs.jsx',import.meta.url),'utf8');
const gpuStart=source.indexOf('  async function loadGpu(){'),gpuEnd=source.indexOf('  const [detail,',gpuStart);
const listStart=source.indexOf('  async function load(direction,event){'),listEnd=source.indexOf('  const page=result?.page;',listStart);
assert.ok(gpuStart>=0 && gpuEnd>gpuStart && listStart>=0 && listEnd>listStart);
test('운영 목록과 상세는 조회를 시작한 초점을 잃은 경우에만 결과로 이동한다',()=>{
  for(const kind of ['result','detail'])for(const success of [true,false])for(const moved of [true,false]){
    const needle=kind==='result'?'  useEffect(()=>{if(busy || !resultFocus.current)':'  useEffect(()=>{if(busy || !detailFocus.current)';
    const start=source.indexOf(needle),end=source.indexOf('\n',start);assert.ok(start>=0 && end>start);
    const body={},other={},document={body,activeElement:moved?other:body},focused=[];
    const target=name=>({isConnected:true,disabled:false,focus(){focused.push(name);}});
    const pending={trigger:target('trigger'),success},context=vm.createContext({document,restoreLostFocus,busy:false,result:{},listError:'',detail:{},error:'',detailError:'',
      resultFocus:{current:pending},detailFocus:{current:pending},resultHeadingRef:{current:target('result')},detailRef:{current:target('detail')},useEffect:fn=>fn()});
    vm.runInContext(source.slice(start,end),context);assert.deepEqual(focused,moved?[]:[success?kind:'trigger']);
  }
});
test('운영 목록 검색과 페이지 조회 성공은 열린 상세와 변경 내역을 유지한다',async()=>{
  for(const direction of ['first','older']){
    let finish,detail={id:'old'},aborted=false,updated=false;const deferred=new Promise(resolve=>finish=resolve);
    const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:{}},resultFocus:{current:null},listRequest:{current:null},diffRequest:{current:{abort(){aborted=true;}}},
      result:{page:{next_offset:30}},query:'',status:'전체',setTimeout,clearTimeout,setBusy:()=>{},setError:()=>{},setListError:()=>{},setResult:()=>updated=true,setResultQuery:()=>{},setDetail:value=>detail=value,
      validOperationsPage:()=>true,fetch:()=>deferred});
    vm.runInContext(source.slice(listStart,listEnd)+'\nthis.load=load;',context);const pending=context.load(direction);
    detail={id:'new'};finish({ok:true,json:async()=>({page:{}})});await pending;
    assert.equal(updated,true);assert.equal(detail.id,'new');assert.equal(aborted,false);
  }
});
test('운영 목록과 GPU 조회는 지연 시 이전 결과를 유지하고 다시 조회할 수 있다',async()=>{
  for(const kind of ['gpu','list'])for(const stage of ['fetch','json']){
    let timeout,finish,busy=false,error='',stale=false,updates=0,calls=0,slow=true;
    const delayed=new Promise(resolve=>finish=resolve),existing={page:{offset:0},value:'이전'};
    const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:{}},resultFocus:{current:null},gpuRequest:{current:null},listRequest:{current:null},diffRequest:{current:null},gpu:[existing],result:existing,query:'',status:'전체',
      setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setGpuError:value=>error=value,setListError:value=>error=value,setGpuStale:value=>stale=value,
      setCapture:()=>{},setRecovery:()=>{},setOutsideChecked:()=>{},setInspection:()=>{},setPriority:()=>{},setError:()=>{},setDetail:()=>{},setResultQuery:()=>{},setGpuCheckedAt:()=>{},
      setGpu:()=>updates++,setResult:()=>updates++,validGpuTables:()=>true,validOperationsPage:()=>true,
      fetch:()=>{calls++;if(!slow)return Promise.resolve({ok:true,json:async()=>kind==='gpu'?[]:{page:{}}});return stage==='fetch'?delayed:Promise.resolve({ok:true,json:()=>delayed});}});
    vm.runInContext((kind==='gpu'?source.slice(gpuStart,gpuEnd):source.slice(listStart,listEnd))+'\nthis.load='+(kind==='gpu'?'loadGpu':'load')+';',context);
    const pending=context.load('first');await context.load('first');assert.equal(calls,1);
    if(stage==='json')await new Promise(resolve=>setImmediate(resolve));timeout();await pending;
    assert.equal(busy,false);assert.match(error,/이전/);assert.equal(updates,0);if(kind==='gpu')assert.equal(stale,true);
    finish(stage==='fetch'?{ok:true,json:async()=>({})}:{});await new Promise(resolve=>setImmediate(resolve));assert.equal(updates,0);
    slow=false;await context.load('first');assert.equal(updates,1);assert.equal(busy,false);if(kind==='gpu')assert.equal(stale,false);
  }
});
