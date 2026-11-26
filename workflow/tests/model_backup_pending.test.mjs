import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readPendingBackupRequest, validateBackupReceipt} from '../../gui/modelBackupPending.mjs';

test('resume retains original job and validates model and receipt', () => {
  const request = {command:'backup-resume', model:'sample', payload:{job_id:'d'.repeat(32)}};
  assert.deepEqual(readPendingBackupRequest({getItem:()=>JSON.stringify(request)}), request);
  const receipt={job_id:request.payload.job_id, model:'sample', operation:'sync', target:'canonical', status:'running'};
  assert.equal(validateBackupReceipt(request,receipt),receipt);
  assert.throws(()=>validateBackupReceipt(request,{...receipt,job_id:'e'.repeat(32)}));
  assert.throws(()=>validateBackupReceipt(request,{...receipt,model:'other'}));
  assert.equal(readPendingBackupRequest({getItem:()=>JSON.stringify({...request,payload:{job_id:'bad'}})}),null);
});

test('valid pending backup request retains its id and target across page reload', () => {
  const request = {command: 'backup-verify', payload: {model: 'sample', target: 'latest_snapshot', request_id: 'a'.repeat(32)}};
  const storage = {getItem: () => JSON.stringify(request)};
  assert.deepEqual(readPendingBackupRequest(storage), request);
});

test('snapshot integrity verification keeps its target when restored', () => {
  const request = {command: 'backup-verify', payload: {model: 'sample', target: 'snapshot_manifest', request_id: 'b'.repeat(32)}};
  assert.deepEqual(readPendingBackupRequest({getItem: () => JSON.stringify(request)}), request);
});

test('legacy verification keeps its target after reload', () => {
  const request = {command: 'backup-verify', payload: {model: 'catalog-flux-report-vision', target: 'legacy', request_id: 'c'.repeat(32)}};
  assert.deepEqual(readPendingBackupRequest({getItem: () => JSON.stringify(request)}), request);
  assert.equal(validateBackupReceipt(request, {job_id: 'c'.repeat(32), model: request.payload.model, operation: 'verify', status: 'running', target: 'legacy'}).target, 'legacy');
});

test('receipts must match the original job, model, operation and target', () => {
  const request = {command: 'backup-verify', payload: {model: 'sample', target: 'latest_snapshot', request_id: 'a'.repeat(32)}};
  const receipt = {job_id: 'a'.repeat(32), model: 'sample', operation: 'verify', status: 'running', target: 'latest_snapshot'};
  assert.equal(validateBackupReceipt(request, receipt), receipt);
  for (const change of [{job_id: 'b'.repeat(32)}, {model: 'other'}, {operation: 'sync'}, {status: 'ok'}, {target: 'canonical'}]) {
    assert.throws(() => validateBackupReceipt(request, {...receipt, ...change}));
  }
});

test('malformed or unsupported session records do not break the model page', () => {
  for (const value of ['{', '{}', 'null', JSON.stringify({command: 'backup-sync', payload: {model: 'm', request_id: 'bad'}}),
    JSON.stringify({command: 'backup-sync', payload: {model: 'm', request_id: 'a'.repeat(32), extra: 'x'}})]) {
    assert.equal(readPendingBackupRequest({getItem: () => value}), null);
  }
  assert.equal(readPendingBackupRequest({getItem: () => {throw new Error('storage unavailable');}}), null);
});
