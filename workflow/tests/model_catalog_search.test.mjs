import test from 'node:test';
import assert from 'node:assert/strict';
import {installationJobs, relatedActivity, searchCatalog, sortCatalog} from '../../gui/modelCatalogSearch.mjs';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('카탈로그 조회 지연은 중복을 막고 이전 결과를 유지하며 재시도한다', async () => {
  const source=readFileSync(new URL('../../gui/ModelCatalog.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  async function load()'),end=source.indexOf('  return <section',start);
  for(const delayed of ['catalog-overview','backup-verify-history','backup-verify-status']) {
    let timeout,error='',busy=false,calls=0,slow=true,result='old';
    const requestRef={current:null};
    const component={alternate_installations:[{retained_original:true},{local_present:true,backup_target:'target'}]};
    const response={components:[component],unclassified:[]};
    const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,requestRef,setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setError:value=>error=value,setJobs:()=>{},setJobsError:()=>{},setVerificationRecords:()=>{},setResult:value=>result=value,setCheckedAt:()=>{},managementCommand:(_service,command)=>{calls++;if(slow && command===delayed)return new Promise(()=>{});return Promise.resolve(command==='catalog-overview' ? response : command==='backup-verify-history' ? {records:[{model:'target',operation:'verify',job_id:'job'}]} : {status:'completed'});}});
    vm.runInContext(source.slice(start,end),context);
    const first=context.load();await context.load();await new Promise(done=>setImmediate(done));const initialCalls=calls;
    timeout();await first;assert.match(error,/시간이 초과/);assert.equal(busy,false);assert.equal(result,'old');assert.equal(requestRef.current,null);
    slow=false;await context.load();assert.equal(result,response);assert.ok(calls>initialCalls);assert.equal(error,'');
  }
});

test('등록된 서비스에 정확히 일치하는 관측 기록만 연결한다', () => {
  const activity = {queue:{jobs:[{service:'shared', source_service:'music-heartmula'}, {service:'music-other'}]},
    reservations:{records:[{service:'music-heartmula'}, {service:'other'}]}};
  const result = relatedActivity(activity, ['music-heartmula']);
  assert.equal(result.queued.length, 1);
  assert.equal(result.reservations.length, 1);
  assert.equal(relatedActivity(null, []).queued.length, 0);
});

test('설치본의 작업은 다른 경로나 상위 폴더의 작업과 섞지 않는다', () => {
  const jobs = [{model:'models', job_id:'parent'}, {model:'catalog-heartmula', job_id:'new'},
    {model:'music', job_id:'old'}, {model:'catalog-heartmula', job_id:'older'}];
  assert.deepEqual(installationJobs(jobs, 'catalog-heartmula').map(job => job.job_id), ['new', 'older']);
  assert.deepEqual(installationJobs(null, 'catalog-heartmula'), []);
});

test('모델과 서비스, 이전·새 설치 경로를 검색하고 모든 검색어를 적용한다', () => {
  const entries = [
    {declaration: {id:'visual', label:'시각 모델', kind:'model', path:'old', source:'provider/model', revision:'abc', services:['flux-image']}, alternate_installations:[{path:'models/visual'}]},
    {declaration: {id:'other', label:'다른 모델', kind:'model', path:'other', services:[]}}
  ];
  assert.deepEqual(searchCatalog(entries, 'FLUX models').map(x => x.declaration.id), ['visual']);
  assert.deepEqual(searchCatalog(entries, 'provider other'), []);
  assert.equal(searchCatalog(entries, '').length, 2);
});

test('할당 크기순은 미관측을 마지막에 두고 원본 순서를 변경하지 않는다', () => {
  const entries = [{id:'unknown'}, {id:'small', storage_observation:{allocated_bytes:1}},
    {id:'large', storage_observation:{allocated_bytes:5}}];
  assert.deepEqual(sortCatalog(entries, 'allocated').map(x => x.id), ['large', 'small', 'unknown']);
  assert.deepEqual(entries.map(x => x.id), ['unknown', 'small', 'large']);
});
