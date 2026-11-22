export function anchorHistoryRequest(animation,version,page=null) {
  const payload={animation_id:animation.trim(),animation_version:version.trim(),limit:20};
  if(page)Object.assign(payload,{offset:page.next_offset,snapshot:page.snapshot});
  return payload;
}

export function validAnchorHistoryPage(result,payload,next) {
  const offset=payload.offset ?? 0;
  return Boolean(result && Array.isArray(result.records) && result.offset===offset &&
    /^[a-f0-9]{64}$/.test(result.snapshot || '') && (!next || result.snapshot===payload.snapshot) &&
    (result.next_offset===null || (result.next_offset===offset+result.records.length && result.records.length>0)));
}
