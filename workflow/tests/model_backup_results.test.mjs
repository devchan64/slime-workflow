import {test} from 'node:test';
import assert from 'node:assert/strict';
import {modelBackupPage} from '../../gui/modelBackupResults.mjs';

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
