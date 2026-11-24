import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readPendingBackupRequest, validateBackupReceipt} from '../../gui/modelBackupPending.mjs';

test('valid pending backup request retains its id and target across page reload', () => {
  const request = {command: 'backup-verify', payload: {model: 'sample', target: 'latest_snapshot', request_id: 'a'.repeat(32)}};
  const storage = {getItem: () => JSON.stringify(request)};
  assert.deepEqual(readPendingBackupRequest(storage), request);
});

test('snapshot integrity verification keeps its target when restored', () => {
  const request = {command: 'backup-verify', payload: {model: 'sample', target: 'snapshot_manifest', request_id: 'b'.repeat(32)}};
  assert.deepEqual(readPendingBackupRequest({getItem: () => JSON.stringify(request)}), request);
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
