export function validGeneratorHistoryPage(page,offset,limit,snapshot) {
  if(!page || !Number.isSafeInteger(offset) || offset<0 || !Number.isSafeInteger(limit) || limit<1 ||
     !Number.isSafeInteger(page.total) || page.total<offset || page.offset!==offset ||
     !Array.isArray(page.records) || page.records.length>limit || offset+page.records.length>page.total ||
     !page.records.every(row=>row && typeof row.id==="string" && row.id.length>0 && typeof row.recorded_status==="string") ||
     new Set(page.records.map(row=>row.id)).size!==page.records.length ||
     typeof page.snapshot!=="string" || !/^[a-f0-9]{64}$/.test(page.snapshot) || (snapshot && page.snapshot!==snapshot))return false;
  const end=offset+page.records.length;
  return page.next_offset===null ? end===page.total : page.records.length===limit && page.next_offset===end && end<page.total;
}
