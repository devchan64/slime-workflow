export function anchorHistoryRequest(animation,version,page=null) {
  const payload={animation_id:animation.trim(),animation_version:version.trim(),limit:20};
  if(page)Object.assign(payload,{offset:page.next_offset,snapshot:page.snapshot});
  return payload;
}

export function validAnchorHistoryPage(result,payload,next) {
  const offset=payload.offset ?? 0;
  return Boolean(result && Number.isInteger(result.total) && result.total>=0 &&
    Number.isInteger(offset) && offset>=0 && offset<=result.total &&
    Array.isArray(result.records) && result.records.length<=payload.limit && offset+result.records.length<=result.total &&
    result.records.every(row=>row && typeof row.id==='string' && typeof row.created_at==='string' && Number.isInteger(row.frames) && row.frames>=0) && result.offset===offset &&
    /^[a-f0-9]{64}$/.test(result.snapshot || '') && (!next || result.snapshot===payload.snapshot) &&
    (result.next_offset===null ? offset+result.records.length===result.total : result.next_offset===offset+result.records.length && result.records.length>0 && result.next_offset<result.total));
}
