import {untilAborted} from './managementCommand.js';
import {validVideoJobId} from './videoJobId.mjs';

export async function readConversationVideoReceipt(command, session, formId, signal) {
  const bytes = new TextEncoder().encode(`${session}:${formId}`);
  const digest = new Uint8Array(await untilAborted(crypto.subtle.digest('SHA-256', bytes), signal));
  const requestId = 'vf_' + Array.from(digest, byte => byte.toString(16).padStart(2, '0')).join('');
  const value = await untilAborted(command('hermes-agent', 'hermes-video-form-status',
    {session_id: session, form_id: formId}, {signal}), signal);
  if (!value || value.request_id !== requestId || value.service !== 'wan22-fun-control' ||
      !['accepted', 'unknown', 'not_found', 'rejected'].includes(value.state) ||
      (value.state === 'accepted' && !validVideoJobId(value.job_id))) {
    throw new Error('접수 상태 응답을 확인할 수 없습니다. 다시 조회하세요.');
  }
  return value;
}
