import {test} from 'node:test';
import assert from 'node:assert/strict';
import {backupDirectories, backupTargetLabel, modelBackupPage, verificationSummary} from '../../gui/modelBackupResults.mjs';

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
