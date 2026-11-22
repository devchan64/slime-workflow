const receiptStates=new Set(["pending","delivering","accepted","applied","undelivered","unknown"]);
const confirmedStates=new Set(["accepted","applied","undelivered"]);

export function matchesLiveInstructionReceipt(row,pending,{confirmed=false}={}) {
  return Boolean(row && pending && [pending.request_id,pending.job_id,pending.text].every(value=>typeof value==="string" && value.length>0) &&
    ["steer","redirect"].includes(pending.mode) && row.request_id===pending.request_id && row.job_id===pending.job_id &&
    row.mode===pending.mode && row.text===pending.text && (confirmed ? confirmedStates : receiptStates).has(row.state));
}
