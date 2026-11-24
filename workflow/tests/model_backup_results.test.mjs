import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {backupDirectories, backupTargetLabel, modelBackupPage, verificationSummary} from '../../gui/modelBackupResults.mjs';

test('작업 결과 조회 시간 초과는 중복을 막고 대기를 해제한다', async () => {
  const source = readFileSync(new URL('../../gui/ModelBackupCompare.jsx', import.meta.url), 'utf8');
  const start = source.indexOf('  async function showJob(jobId)'), end = source.indexOf('  const pageSize', start);
  let timer, calls = 0, busy = false, error = '';
  const context = vm.createContext({AbortController, untilAborted, requestErrorMessage, jobReadRequest: {current: null},
    setTimeout: fn => (timer = fn, 1), clearTimeout: () => {}, setBusy: value => busy = value, setError: value => error = value, setFailedJobId: () => {},
    managementCommand: () => {calls++; return new Promise(() => {});}});
  vm.runInContext(source.slice(start, end), context);
  const first = context.showJob('job'); await context.showJob('job'); assert.equal(calls, 1);
  timer(); await first; assert.match(error, /시간이 초과/); assert.equal(busy, false); assert.equal(context.jobReadRequest.current, null);
});

test('모델 목록 조회 시간 초과는 대기를 해제하고 재시도를 허용한다', async () => {
  const source = readFileSync(new URL('../../gui/ModelBackupCompare.jsx', import.meta.url), 'utf8');
  const start = source.indexOf('  useEffect(() => {\n    const controller = new AbortController();\n    let active');
  const end = source.indexOf('  }, [modelsRevision]);', start) + '  }, [modelsRevision]);'.length;
  let timer, cleanup, error = '', loading = false; const modelsRequestInFlight = {current: false};
  const context = vm.createContext({AbortController, untilAborted, requestErrorMessage, modelsRequestInFlight, modelsRevision: 0,
    useEffect: fn => cleanup = fn(), setTimeout: fn => (timer = fn, 1), clearTimeout: () => {},
    managementCommand: () => new Promise(() => {}), setModelsLoading: value => loading = value,
    setModelsError: value => error = value, setModels: () => {}, setBackupError: () => {}, setSelected: () => {}});
  vm.runInContext(source.slice(start, end), context);
  assert.equal(loading, true); timer(); await new Promise(done => setImmediate(done));
  assert.match(error, /시간이 초과/); assert.equal(loading, false); assert.equal(modelsRequestInFlight.current, false); cleanup();
});

test('수동 이력 조회는 중복을 막고 시간 초과 후 재시도할 수 있다', async () => {
  const source = readFileSync(new URL('../../gui/ModelBackupCompare.jsx', import.meta.url), 'utf8');
  const start = source.indexOf('  async function refreshHistory(signal)');
  const end = source.indexOf('  useEffect(', start);
  let timer, calls = 0, loading = false, error = '', jobs;
  const context = vm.createContext({AbortController, untilAborted, requestErrorMessage, historyRevision: {current: 0}, historyRequest: {current: null},
    setHistoryLoading: value => loading = value, setHistoryError: value => error = value, setJobs: value => jobs = value,
    setTimeout: fn => (timer = fn, 1), clearTimeout: () => {},
    managementCommand: () => {calls++; return calls === 1 ? new Promise(() => {}) : Promise.resolve({records: ['new']});}});
  vm.runInContext(source.slice(start, end), context);
  const first = context.reloadHistory(); await context.reloadHistory(); assert.equal(calls, 1);
  timer(); await first; assert.match(error, /시간이 초과/); assert.equal(loading, false);
  await context.reloadHistory(); assert.deepEqual(jobs, ['new']); assert.equal(error, '');
});

test('늦은 이력 응답과 오류는 최신 조회 결과를 덮지 않는다', async () => {
  const source = readFileSync(new URL('../../gui/ModelBackupCompare.jsx', import.meta.url), 'utf8');
  const start = source.indexOf('  async function refreshHistory(signal)');
  const end = source.indexOf('  useEffect(', start);
  const pending = []; let jobs;
  const context = vm.createContext({historyRevision: {current: 0}, setJobs: value => jobs = value, setHistoryError: () => {},
    managementCommand: () => new Promise((resolve, reject) => pending.push({resolve, reject}))});
  vm.runInContext(source.slice(start, end), context);
  const old = context.refreshHistory(), latest = context.refreshHistory();
  pending[1].resolve({records: ['new']}); await latest;
  pending[0].resolve({records: ['old']}); await old;
  assert.deepEqual(jobs, ['new']);
  const staleFailure = context.refreshHistory(), next = context.refreshHistory();
  pending[3].resolve({records: ['latest']}); await next;
  pending[2].reject(new Error('old failure')); await staleFailure;
  assert.deepEqual(jobs, ['latest']);
});

test('작업 결과 조회 성공과 이력 갱신 실패를 구분한다', async () => {
  const source = readFileSync(new URL('../../gui/ModelBackupCompare.jsx', import.meta.url), 'utf8');
  const start = source.indexOf('  async function showJob(jobId)');
  const end = source.indexOf('  const pageSize', start);
  let result, error = '', busy = false;
  const response = {model: 'kimodo', status: 'completed', result: {files: []}};
  const context = vm.createContext({AbortController, untilAborted, requestErrorMessage, jobReadRequest: {current: null}, setTimeout, clearTimeout, managementCommand: async () => response, refreshHistory: async () => {throw new Error('offline');},
    setBusy: value => busy = value, setError: value => error = value, setHistoryError: value => error = value, setJobResult: value => result = value, setShownJobId: () => {}, setFailedJobId: () => {},
    setComparisonOrigin: () => {}, setComparison: () => {}, setFilter: () => {}, setFileQuery: () => {}, setPage: () => {}});
  vm.runInContext(source.slice(start, end), context);
  await context.showJob('job');
  assert.equal(result, response);
  assert.match(error, /결과는 조회했지만 이력을 새로고침하지 못했습니다/);
  assert.equal(busy, false);
});

test('snapshot self verification is labeled separately from local comparison', () => {
  assert.equal(backupTargetLabel('snapshot_manifest'), '스냅샷 자체 무결성');
  assert.equal(backupTargetLabel('latest_snapshot'), '최근 스냅샷과 비교');
  assert.equal(backupTargetLabel('unknown'), '대상 확인 불가');
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
});
