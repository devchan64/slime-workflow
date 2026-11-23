export function validChatQueue(view, session) {
  if (!view || view.id !== session || !Array.isArray(view.chat_queue)) return false;
  const ids = new Set();
  for (const row of view.chat_queue) {
    if (!row || typeof row.request_id !== "string" || !row.request_id || ids.has(row.request_id) || typeof row.prompt !== "string" || !Number.isInteger(row.revision) || row.revision < 1 || !["queued", "dispatching"].includes(row.state)) return false;
    ids.add(row.request_id);
  }
  return true;
}

export function matchesChatQueueReceipt(queueReceiptValue, pendingRequestValue) {
  if (!queueReceiptValue || queueReceiptValue.session_id !== pendingRequestValue.session_id || typeof queueReceiptValue.duplicate !== "boolean") return false;
  if (queueReceiptValue.queued === true) return queueReceiptValue.request?.request_id === pendingRequestValue.request_id &&
    queueReceiptValue.request?.original_prompt === pendingRequestValue.prompt && queueReceiptValue.request?.model_profile === pendingRequestValue.model_profile &&
    (queueReceiptValue.request_id === undefined || queueReceiptValue.request_id === pendingRequestValue.request_id) &&
    ["queued", "dispatching"].includes(queueReceiptValue.request?.state);
  return queueReceiptValue.queued === false && queueReceiptValue.duplicate === true && queueReceiptValue.request_id === pendingRequestValue.request_id;
}

// A request can no longer apply once its queue revision or state changes.
export function classifyQueueUpdate(view, session, pending) {
  if (!validChatQueue(view, session)) return "invalid";
  const row = view.chat_queue.find(item => item.request_id === pending.request_id);
  if (row?.state === "queued" && row.revision <= pending.revision) return "waiting";
  if (!pending.cancel && row?.state === "queued" && row.revision === pending.revision + 1 && row.prompt === pending.prompt) return "applied";
  return "changed";
}
