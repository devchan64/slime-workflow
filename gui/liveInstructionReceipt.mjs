const receiptStates=new Set(["pending","delivering","accepted","applied","undelivered","unknown"]);
const confirmedStates=new Set(["accepted","applied","undelivered"]);

export function validLiveInstructionRows(rows) {
  if (!Array.isArray(rows)) return false;
  const ids=new Set();
  for (const row of rows) {
    if (!row || typeof row.request_id!=="string" || !row.request_id || ids.has(row.request_id) || typeof row.job_id!=="string" || !row.job_id || typeof row.text!=="string" || !["steer","redirect"].includes(row.mode) || !receiptStates.has(row.state)) return false;
    if(row.recovery!=null && (typeof row.recovery!=="object" || Array.isArray(row.recovery) || !["queued","dispatching","dispatched","cancelled"].includes(row.recovery.state) || (row.recovery.job_id!=null && (typeof row.recovery.job_id!=="string" || !row.recovery.job_id))))return false;
    ids.add(row.request_id);
  }
  return true;
}

export function matchesLiveInstructionReceipt(row,pending,{confirmed=false}={}) {
  return Boolean(row && pending && [pending.request_id,pending.job_id,pending.text].every(value=>typeof value==="string" && value.length>0) &&
    ["steer","redirect"].includes(pending.mode) && row.request_id===pending.request_id && row.job_id===pending.job_id &&
    row.mode===pending.mode && row.text===pending.text && (confirmed ? confirmedStates : receiptStates).has(row.state));
}

export async function matchesLiveInstructionRecovery(result,receipt) {
  if (typeof result?.duplicate!=="boolean" || !receipt || typeof receipt.request_id!=="string" || typeof receipt.text!=="string" || result.request?.original_prompt!==receipt.text || !["queued","dispatching","dispatched","cancelled"].includes(result.request?.state) || (!result.duplicate && result.request.state!=="queued")) return false;
  const hash=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(receipt.request_id));
  const id="recovery_"+Array.from(new Uint8Array(hash),byte=>byte.toString(16).padStart(2,"0")).join("");
  return result.request?.request_id===id;
}
