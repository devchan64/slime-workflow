export function validSourceHistoryPage(page,service,offset,snapshot) {
  return Boolean(page && page.service===service && Array.isArray(page.records) &&
    page.records.every(row=>row && typeof row.id==='string' && typeof row.recorded_status==='string') &&
    Number.isInteger(page.total) && page.total>=0 && page.offset===offset &&
    Number.isInteger(page.unavailable_count) && page.unavailable_count>=0 &&
    /^[a-f0-9]{64}$/.test(page.snapshot || '') && (!snapshot || page.snapshot===snapshot) &&
    (page.next_offset===null || (Number.isInteger(page.next_offset) && page.next_offset>offset)));
}
