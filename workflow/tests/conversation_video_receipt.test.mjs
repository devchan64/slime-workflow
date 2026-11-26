import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readConversationVideoReceipt} from '../../gui/conversationVideoReceipt.mjs';

test('저장 영상 폼의 접수 상태와 작업 ID를 확인한다', async () => {
  const controller = new AbortController();
  const job = '2026-11-26_12-34-56-abcdef12';
  const identity = {service: 'wan22-fun-control', request_id: 'vf_'+createHash('sha256').update('session:form').digest('hex')};
  const result = await readConversationVideoReceipt(async (service, command, payload, options) => {
    assert.equal(service, 'hermes-agent');
    assert.equal(command, 'hermes-video-form-status');
    assert.deepEqual(payload, {session_id: 'session', form_id: 'form'});
    assert.equal(options.signal, controller.signal);
    return {...identity, state: 'accepted', job_id: job};
  }, 'session', 'form', controller.signal);
  assert.equal(result.job_id, job);
  for (const state of ['unknown', 'not_found', 'rejected']) {
    const receipt = await readConversationVideoReceipt(async () => ({...identity,state}), 'session', 'form', controller.signal);
    assert.equal(receipt.state, state);
  }
  for (const receipt of [{...identity,state: 'accepted', job_id: '../bad'}, {...identity,state: 'unexpected'}, {...identity,state:'not_found',service:'other'}, {...identity,state:'not_found',request_id:'vf_wrong'}, null]) {
    await assert.rejects(readConversationVideoReceipt(async () => receipt, 'session', 'form', controller.signal), /응답을 확인할 수 없습니다/);
  }
});

test('저장 영상 폼 조회가 중단되면 늦은 응답을 사용하지 않는다', async () => {
  const controller = new AbortController();
  let finish, started;
  const ready = new Promise(resolve => {started = resolve;});
  const pending = readConversationVideoReceipt(() => new Promise(resolve => {finish = resolve; started();}), 'session', 'form', controller.signal);
  await ready;
  controller.abort();
  await assert.rejects(pending, {name: 'AbortError'});
  finish({state: 'not_found'});
});
