export function validChatQueue(view, session) {
  if (!view || view.id !== session || !Array.isArray(view.chat_queue)) return false;
  const ids = new Set();
  for (const row of view.chat_queue) {
    if (!row || typeof row.request_id !== "string" || !row.request_id || ids.has(row.request_id) || typeof row.prompt !== "string" || !Number.isInteger(row.revision) || row.revision < 1 || !["queued", "dispatching"].includes(row.state)) return false;
    ids.add(row.request_id);
  }
  return true;
}

// A request can no longer apply once its queue revision or state changes.
export function classifyQueueUpdate(view, session, pending) {
  if (!validChatQueue(view, session)) return "invalid";
  const row = view.chat_queue.find(item => item.request_id === pending.request_id);
  if (row?.state === "queued" && row.revision <= pending.revision) return "waiting";
  if (!pending.cancel && row?.state === "queued" && row.revision === pending.revision + 1 && row.prompt === pending.prompt) return "applied";
  return "changed";
}
