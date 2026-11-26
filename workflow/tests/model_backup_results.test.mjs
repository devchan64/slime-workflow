import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {backupDirectories, backupTargetLabel, modelBackupPage, verificationSummary, validBackupJob, validBackupComparison, validBackupMetadata, validBackupModels, backupActionReasons} from '../../gui/modelBackupResults.mjs';
import {validCatalogHistory} from '../../gui/modelCatalogSearch.mjs';

test('스냅샷만 있는 모델 선택은 자체 무결성으로 이동하고 다음 모델은 기본값으로 돌아간다', () => {
  const source = readFileSync(new URL('../../gui/ModelBackupCompare.jsx', import.meta.url), 'utf8');
  const start = source.indexOf('  function selectModel(model)'), end = source.indexOf('\n  useEffect(', start);
  assert.ok(start >= 0 && end > start);
  const context = vm.createContext({automaticSnapshotTarget: {current: false}, target: 'legacy', selected: '',
    setTarget(value) { context.target = value; }, setSelected(value) { context.selected = value; }});
  vm.runInContext(source.slice(start, end) + '\nthis.selectModel = selectModel;', context);
  context.selectModel({name: 'snapshot-only', local_present: false, snapshot_present: true});
  assert.equal(context.target, 'snapshot_manifest');
  assert.equal(context.selected, 'snapshot-only');
  context.selectModel({name: 'local', local_present: true, snapshot_present: true});
  assert.equal(context.target, 'canonical');
  context.target = 'latest_snapshot';
  context.selectModel({name: 'unknown', local_present: null, snapshot_present: true});
  assert.equal(context.target, 'latest_snapshot');
});

test('작업 결과 조회 시간 초과는 중복을 막고 대기를 해제한다', async () => {
  const source = readFileSync(new URL('../../gui/ModelBackupCompare.jsx', import.meta.url), 'utf8');
  const start = source.indexOf('  async function showJob(jobId)'), end = source.indexOf('  const pageSize', start);
  let timer, calls = 0, busy = false, error = '',loadingJobId=null;
  const context = vm.createContext({AbortController, untilAborted, requestErrorMessage, jobReadRequest: {current: null},
    setTimeout: fn => (timer = fn, 1), clearTimeout: () => {}, setBusy: value => busy = value,setLoadingJobId:value=>loadingJobId=value, setError: value => error = value, setFailedJobId: () => {},
    managementCommand: () => {calls++; return new Promise(() => {});}});
  vm.runInContext(source.slice(start, end), context);
  const first = context.showJob('job'); await context.showJob('job'); assert.equal(calls, 1);assert.equal(loadingJobId,'job');
  timer(); await first; assert.match(error, /시간이 초과/); assert.equal(busy, false);assert.equal(loadingJobId,null); assert.equal(context.jobReadRequest.current, null);
});

test('모델 목록 조회 시간 초과는 대기를 해제하고 재시도를 허용한다', async () => {
  const source = readFileSync(new URL('../../gui/ModelBackupCompare.jsx', import.meta.url), 'utf8');
  const start = source.indexOf('  useEffect(() => {\n    const controller = new AbortController();\n    let active');
  const end = source.indexOf('  }, [modelsRevision]);', start) + '  }, [modelsRevision]);'.length;
  let timer, cleanup, error = '', loading = false; const modelsRequestInFlight = {current: false};
  const context = vm.createContext({AbortController, untilAborted, requestErrorMessage, validBackupModels, modelsRequestInFlight, modelsRevision: 0,
    useEffect: fn => cleanup = fn(), setTimeout: fn => (timer = fn, 1), clearTimeout: () => {},
    managementCommand: () => new Promise(() => {}), setModelsLoading: value => loading = value,
    setModelsError: value => error = value, setModels: () => {}, setBackupError: () => {}, setSelected: () => {}});
  vm.runInContext(source.slice(start, end), context);
  assert.equal(loading, true); timer(); await new Promise(done => setImmediate(done));
  assert.match(error, /시간이 초과/); assert.equal(loading, false); assert.equal(modelsRequestInFlight.current, false); cleanup();
});

test('손상된 모델 목록은 기존 목록을 보존하고 정상 재조회로 복구한다',async()=>{
  const source=readFileSync(new URL('../../gui/ModelBackupCompare.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  useEffect(() => {\n    const controller = new AbortController();\n    let active');
  const end=source.indexOf('  }, [modelsRevision]);',start)+'  }, [modelsRevision]);'.length;
  const old=[{name:'old'}],good={models:[{name:'new',local_present:true,backup_present:null,snapshot_present:false}],backup_error:null};
  let models=old,error='',response={models:[null]},cleanup,cleared=0,notice='';
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validBackupModels,modelsRequestInFlight:{current:false},modelsRevision:0,selected:'old',setComparison:()=>cleared++,setMetadata:()=>cleared++,setSelectionNeedsConfirmation:()=>{},setSelectionNotice:value=>notice=value,
    useEffect:fn=>cleanup=fn(),setTimeout,clearTimeout,managementCommand:async()=>response,setModelsLoading:()=>{},setModelsError:value=>error=value,
    setModels:value=>models=value,setBackupError:()=>{},setSelected:()=>{}});
  vm.runInContext(source.slice(start,end),context);await new Promise(done=>setImmediate(done));
  assert.equal(models,old);assert.equal(cleared,0);assert.match(error,/응답이 올바르지/);cleanup();
  response=good;vm.runInContext(source.slice(start,end),context);await new Promise(done=>setImmediate(done));
  assert.equal(models,good.models);assert.equal(cleared,2);assert.match(notice,/old.*새 목록에 없어/);assert.equal(error,'');cleanup();
  assert.equal(validBackupModels({models:[{name:'same'},{name:'same'}]}),false);
  assert.equal(validBackupModels({models:[{name:'model',local_present:'false'}]}),false);
});

test('수동 이력 조회는 중복을 막고 시간 초과 후 재시도할 수 있다', async () => {
  const source = readFileSync(new URL('../../gui/ModelBackupCompare.jsx', import.meta.url), 'utf8');
  const start = source.indexOf('  async function refreshHistory(signal)');
  const end = source.indexOf('  useEffect(', start);
  let timer, calls = 0, loading = false, error = '', jobs, checkedAt;
  const context = vm.createContext({AbortController, untilAborted, requestErrorMessage, validCatalogHistory, historyRevision: {current: 0}, historyRequest: {current: null},
    setHistoryLoading: value => loading = value, setHistoryError: value => error = value, setJobs: value => jobs = value,setHistoryCheckedAt:value=>checkedAt=value,
    setTimeout: fn => (timer = fn, 1), clearTimeout: () => {},
    managementCommand: () => {calls++; return calls === 1 ? new Promise(() => {}) : Promise.resolve({records: [{job_id:'new'}]});}});
  vm.runInContext(source.slice(start, end), context);
  const first = context.reloadHistory(); await context.reloadHistory(); assert.equal(calls, 1);
  timer(); await first; assert.match(error, /시간이 초과/); assert.equal(loading, false);assert.equal(checkedAt,undefined);
  await context.reloadHistory(); assert.deepEqual(jobs, [{job_id:'new'}]); assert.equal(error, '');assert.ok(checkedAt);
});

test('늦은 이력 응답과 오류는 최신 조회 결과를 덮지 않는다', async () => {
  const source = readFileSync(new URL('../../gui/ModelBackupCompare.jsx', import.meta.url), 'utf8');
  const start = source.indexOf('  async function refreshHistory(signal)');
  const end = source.indexOf('  useEffect(', start);
  const pending = []; let jobs;
  const context = vm.createContext({validCatalogHistory, historyRevision: {current: 0}, setJobs: value => jobs = value, setHistoryError: () => {},setHistoryCheckedAt:()=>{},
    managementCommand: () => new Promise((resolve, reject) => pending.push({resolve, reject}))});
  vm.runInContext(source.slice(start, end), context);
  const old = context.refreshHistory(), latest = context.refreshHistory();
  pending[1].resolve({records: [{job_id:'new'}]}); await latest;
  pending[0].resolve({records: ['old']}); await old;
  assert.deepEqual(jobs, [{job_id:'new'}]);
  const staleFailure = context.refreshHistory(), next = context.refreshHistory();
  pending[3].resolve({records: [{job_id:'latest'}]}); await next;
  pending[2].reject(new Error('old failure')); await staleFailure;
  assert.deepEqual(jobs, [{job_id:'latest'}]);
});

test('손상된 백업 이력은 이전 이력을 유지하고 재조회할 수 있다',async()=>{
  const source=readFileSync(new URL('../../gui/ModelBackupCompare.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  async function refreshHistory(signal)'),end=source.indexOf('  useEffect(',start);
  const previous=[{job_id:'previous'}],good=[{job_id:'next',status:'completed'}];let jobs=previous,error='',response={records:[null]};
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validCatalogHistory,historyRevision:{current:0},historyRequest:{current:null},setTimeout,clearTimeout,
    setHistoryLoading:()=>{},setHistoryError:value=>error=value,setJobs:value=>jobs=value,setHistoryCheckedAt:()=>{},managementCommand:async()=>response});
  vm.runInContext(source.slice(start,end),context);await context.reloadHistory();
  assert.equal(jobs,previous);assert.match(error,/응답이 올바르지/);
  response={records:good};await context.reloadHistory();assert.equal(jobs,good);assert.equal(error,'');
});

test('작업 결과 조회 성공과 이력 갱신 실패를 구분한다', async () => {
  const source = readFileSync(new URL('../../gui/ModelBackupCompare.jsx', import.meta.url), 'utf8');
  const start = source.indexOf('  async function showJob(jobId)');
  const end = source.indexOf('  const pageSize', start);
  let result, error = '', busy = false;
  const response = {job_id:'job',model:'kimodo',target:'canonical',status:'completed',result:{model:'kimodo',target:'canonical',complete:true,comparison_basis:'sha256',files:[]}};
  const context = vm.createContext({AbortController, untilAborted, requestErrorMessage, validBackupJob, jobReadRequest: {current: null}, setTimeout, clearTimeout, managementCommand: async () => response, refreshHistory: async () => {throw new Error('offline');},
    setBusy: value => busy = value, setLoadingJobId:()=>{},setError: value => error = value, setHistoryError: value => error = value, setJobResult: value => result = value, setShownJobId: () => {}, setFailedJobId: () => {},
    setComparisonOrigin: () => {}, setComparison: () => {}, setFilter: () => {}, setFileQuery: () => {}, setPage: () => {}});
  vm.runInContext(source.slice(start, end), context);
  await context.showJob('job');
  assert.equal(result, response);
  assert.match(error, /결과는 조회했지만 이력을 새로고침하지 못했습니다/);
  assert.equal(busy, false);
});

test('백업 작업 결과는 요청 ID와 파일 형식이 일치해야 한다',()=>{
  const job={job_id:'job',model:'model',target:'canonical',status:'completed',result:{model:'model',target:'canonical',complete:true,comparison_basis:'sha256',files:[{path:'model.bin',status:'verified'}]}};
  assert.equal(validBackupJob(job,'job'),true);
  assert.equal(validBackupJob(job,'other'),false);
  assert.equal(validBackupJob({...job,result:{...job.result,files:[{path:null,status:'verified'}]}},'job'),false);
  assert.equal(validBackupJob({...job,result:{...job.result,files:[null]}},'job'),false);
  assert.equal(validBackupJob({...job,result:{...job.result,model:'other'}},'job'),false);
  assert.equal(validBackupJob({...job,result:{...job.result,target:'legacy'}},'job'),false);
});

test('직접 비교 결과는 선택 대상과 파일 형식이 일치해야 한다',()=>{
  const result={model:'model',target:'canonical',complete:true,comparison_basis:'size_and_mtime',files:[{path:'a',status:'different'}],source_errors:[],backup_errors:[]};
  assert.equal(validBackupComparison(result,'model','canonical'),true);
  assert.equal(validBackupComparison(result,'other','canonical'),false);
  assert.equal(validBackupComparison(result,'model','legacy'),false);
  assert.equal(validBackupComparison({...result,files:[null]},'model','canonical'),false);
  assert.equal(validBackupComparison({...result,complete:'false'},'model','canonical'),false);
});

test('비교 조회 시간 초과 후 이전 결과를 유지하고 다시 조회할 수 있다',async()=>{
  const source=readFileSync(new URL('../../gui/ModelBackupCompare.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  async function compare(event)'),end=source.indexOf('  async function showMetadata(event)',start);
  const previous={model:'model',target:'canonical'},good={...previous,complete:true,comparison_basis:'size_and_mtime',files:[]};
  let timer,result=previous,error='',busy=false,calls=0;
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validBackupComparison,compareRequest:{current:null},selected:'model',target:'canonical',comparison:previous,
    setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setComparisonLoading:()=>{},setError:value=>error=value,
    setJobResult:()=>{},setComparison:value=>result=value,setComparisonOrigin:()=>{},setFilter:()=>{},setFileQuery:()=>{},setPage:()=>{},
    managementCommand:()=>{calls++;return calls===1?new Promise(()=>{}):Promise.resolve(good);}});
  vm.runInContext(source.slice(start,end),context);
  const first=context.compare();await context.compare();assert.equal(calls,1);timer();await first;
  assert.equal(result,previous);assert.match(error,/시간이 초과.*이전 비교 결과/);assert.equal(busy,false);
  await context.compare();assert.equal(result,good);assert.equal(error,'');assert.equal(busy,false);
});

test('비교 조회 후에는 사라진 초점만 원래 버튼으로 복구한다',async()=>{
  const source=readFileSync(new URL('../../gui/ModelBackupCompare.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  async function compare(event)'),end=source.indexOf('  async function showMetadata(event)',start);
  for(const active of ['body','other']){
    const body={},other={};let focused=0,scheduled;const origin={isConnected:true,disabled:false,focus:()=>focused++};
    const document={body,activeElement:origin},result={model:'model',target:'canonical',complete:true,comparison_basis:'size_and_mtime',files:[]};
    const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validBackupComparison,compareRequest:{current:null},selected:'model',target:'canonical',comparison:null,document,
      setTimeout,clearTimeout,requestAnimationFrame:fn=>scheduled=fn,setBusy:()=>{},setComparisonLoading:()=>{},setError:()=>{},setJobResult:()=>{},setComparison:()=>{},setComparisonOrigin:()=>{},setFilter:()=>{},setFileQuery:()=>{},setPage:()=>{},managementCommand:async()=>result});
    vm.runInContext(source.slice(start,end),context);await context.compare({currentTarget:origin});document.activeElement=active==='body'?body:other;scheduled();
    assert.equal(focused,active==='body'?1:0);
  }
});

test('메타정보 조회 시간 초과 후 이전 결과를 유지하고 재조회한다',async()=>{
  const source=readFileSync(new URL('../../gui/ModelBackupCompare.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  async function showMetadata(event)'),end=source.indexOf('  async function submitRequest(',start);
  const previous={model:'model'},good={model:'model',services:[],declared_sources:[],declared_files:[],manifest_state:'missing'};
  let timer,result=previous,error='',busy=false,calls=0,checkedAt=null;
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validBackupMetadata,metadataRequest:{current:null},selected:'model',metadata:previous,
    setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setMetadataLoading:()=>{},setError:value=>error=value,setMetadata:value=>result=value,setMetadataCheckedAt:value=>checkedAt=value,
    managementCommand:()=>{calls++;return calls===1?new Promise(()=>{}):Promise.resolve(good);}});
  vm.runInContext(source.slice(start,end),context);const first=context.showMetadata();await context.showMetadata();assert.equal(calls,1);timer();await first;
  assert.equal(result,previous);assert.equal(checkedAt,null);assert.match(error,/시간이 초과.*이전 메타정보/);assert.equal(busy,false);
  await context.showMetadata();assert.equal(result,good);assert.ok(checkedAt);assert.equal(error,'');assert.equal(busy,false);
  assert.equal(validBackupMetadata({...good,services:[{}]},'model'),false);
  assert.equal(validBackupMetadata(good,'other'),false);
});

test('메타정보 조회 중 화면이 닫히면 늦은 응답을 반영하지 않는다',async()=>{
  const source=readFileSync(new URL('../../gui/ModelBackupCompare.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  async function showMetadata(event)'),end=source.indexOf('  async function submitRequest(',start);
  let resolve,updates=0;const metadataRequest={current:null};
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validBackupMetadata,metadataRequest,selected:'model',metadata:null,
    setTimeout,clearTimeout,setBusy:()=>{},setMetadataLoading:()=>{},setError:()=>{},setMetadata:()=>updates++,managementCommand:()=>new Promise(done=>resolve=done)});
  vm.runInContext(source.slice(start,end),context);const pending=context.showMetadata();
  const controller=metadataRequest.current;metadataRequest.current=null;controller.abort();
  resolve({model:'model',services:[],declared_sources:[],declared_files:[]});await pending;assert.equal(updates,0);
});

test('잘못된 작업 결과는 이전 결과를 유지하고 같은 작업을 다시 조회할 수 있다',async()=>{
  const source=readFileSync(new URL('../../gui/ModelBackupCompare.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  async function showJob(jobId)'),end=source.indexOf('  const pageSize',start);
  const old={job_id:'previous'},good={job_id:'job',model:'model',target:'canonical',status:'completed',result:{model:'model',target:'canonical',complete:true,comparison_basis:'sha256',files:[]}};
  let response={...good,job_id:'other'},result=old,error='',failed=null;
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validBackupJob,jobReadRequest:{current:null},setTimeout,clearTimeout,
    managementCommand:async()=>response,refreshHistory:async()=>{},setBusy:()=>{},setLoadingJobId:()=>{},setError:value=>error=value,setHistoryError:()=>{},setJobResult:value=>result=value,
    setShownJobId:()=>{},setFailedJobId:value=>failed=value,setComparisonOrigin:()=>{},setComparison:()=>{},setFilter:()=>{},setFileQuery:()=>{},setPage:()=>{}});
  vm.runInContext(source.slice(start,end),context);await context.showJob('job');
  assert.equal(result,old);assert.equal(failed,'job');assert.match(error,/작업 ID/);
  response=good;await context.showJob('job');assert.equal(result,good);assert.equal(failed,null);assert.equal(error,'');
});

test('snapshot self verification is labeled separately from local comparison', () => {
  assert.equal(backupTargetLabel('snapshot_manifest'), '스냅샷 자체 무결성');
  assert.equal(backupTargetLabel('latest_snapshot'), '최근 스냅샷과 비교');
  assert.equal(backupTargetLabel('unknown'), '대상 확인 불가');
});

test('백업 조작 사유는 기존 비활성 조건을 그대로 따른다',()=>{
  for(let bits=0;bits<128;bits++)for(const target of ['canonical','snapshot_manifest']){
    const [busy,modelsLoading,modelsError,backupError,hasSelected,localMissing,pendingRequest]=Array.from({length:7},(_,i)=>Boolean(bits & (1<<i)));
    const selected=hasSelected?'model':'';
    const reason=backupActionReasons({busy,modelsLoading,modelsError,backupError,selected,localMissing,target,pendingRequest});
    const common=busy||modelsLoading||modelsError||!selected;
    assert.equal(Boolean(reason.metadata),Boolean(common));
    assert.equal(Boolean(reason.compare),Boolean(common||backupError||localMissing||target==='snapshot_manifest'));
    assert.equal(Boolean(reason.verify),Boolean(common||backupError||(localMissing&&target!=='snapshot_manifest')||pendingRequest));
    assert.equal(Boolean(reason.sync),Boolean(common||backupError||localMissing||pendingRequest));
  }
  const changed=backupActionReasons({selected:'model',target:'canonical',selectionNeedsConfirmation:true});
  for(const reason of Object.values(changed))assert.match(reason,/직접 선택해 확인/);
});

test('all differences remain reachable after the first page', () => {
  const files = Array.from({length: 205}, (_, index) => ({path: `file-${index}`, status: index < 203 ? 'verified' : 'missing'}));
  const all = modelBackupPage(files, 'all', 2);
  assert.equal(all.total, 205);
  assert.equal(all.files.at(-1).path, 'file-204');
  const missing = modelBackupPage(files, 'missing', 0);
  assert.equal(missing.total, 2);
  assert.deepEqual(missing.files.map(file => file.path), ['file-203', 'file-204']);
  assert.equal(missing.counts.verified, 203);
});

test('a stale page number is clamped after results shrink', () => {
  const result = modelBackupPage([{path: 'a', status: 'missing'}], 'missing', 9);
  assert.equal(result.page, 0);
  assert.equal(result.files[0].path, 'a');
});

test('folder summaries include descendants and keep similarly named paths separate', () => {
  const files = [{path:'a/x/model', status:'verified'}, {path:'a/y/file', status:'missing'},
    {path:'ab/weight', status:'different'}, {path:'root.json', status:'verified'}];
  const root = backupDirectories(files);
  assert.deepEqual(root.map(x => [x.name, x.count]), [['a', 2], ['ab', 1]]);
  assert.deepEqual({...root[0].statuses}, {verified: 1, missing: 1});
  assert.deepEqual(backupDirectories(files, 'a').map(x => x.path), ['a/x', 'a/y']);
  assert.deepEqual(backupDirectories(files, 'a/x'), []);
});

test('verification summary distinguishes completion from matching all files', () => {
  const result = {comparison_basis: 'sha256', complete: true, files: [{status: 'verified'}]};
  assert.match(verificationSummary(result), /모든 파일.*일치/);
  assert.match(verificationSummary({...result, files: [{status: 'verified'}, {status: 'missing'}]}), /일치하지 않거나/);
  assert.match(verificationSummary({...result, complete: false}), /판단할 수 없습니다/);
  assert.match(verificationSummary({...result, files: []}), /검증할 파일이 없어/);
  assert.equal(verificationSummary({...result, comparison_basis: 'size_and_mtime'}), null);
  assert.equal(verificationSummary({...result, complete:'false'}), null);
  assert.equal(verificationSummary({...result, files:[null]}), null);
  assert.equal(verificationSummary({...result, files:[{status:null}]}), null);
});
